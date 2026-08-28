"""AIOS Bridge Kernel v1 AUTHORIZE Pipeline (ADR-068 / TASK-098)."""

import json
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

from src.aios_bridge.kernel.model import (
    KernelTaskRecord,
    KernelStatus,
    KernelAction,
    KernelExecutor,
    compute_fingerprint,
    save_task_record,
    load_task_record,
)
from src.aios_bridge.kernel import gitops


class KernelAuthorityError(RuntimeError):
    pass


def parse_marker_json(content: str, prefix: str) -> Any:
    lines = [line[len(prefix) :].strip() for line in content.splitlines() if line.startswith(prefix)]
    if len(lines) != 1:
        raise KernelAuthorityError(f"Artifact must contain exactly one {prefix} marker; found {len(lines)}")
    try:
        return json.loads(lines[0])
    except Exception as exc:
        raise KernelAuthorityError(f"Malformed JSON in {prefix} marker: {exc}")


def read_remote_control_file(repo_root: Path, rel_path: str, remote: str = "origin", control_branch: str = "ai-control") -> Tuple[str, str]:
    """Reads a file and its exact blob SHA from the remote control branch snapshot only (B098.1 fail-closed)."""
    # Fetch control branch freshly
    res_fetch = gitops.git_cmd(["fetch", remote, control_branch], cwd=repo_root, check=False)
    if res_fetch.returncode != 0:
        raise KernelAuthorityError(f"Failed to fetch remote control branch '{remote}/{control_branch}' (exit={res_fetch.returncode})")

    # Read blob sha
    res_sha = gitops.git_cmd(["rev-parse", f"{remote}/{control_branch}:{rel_path}"], cwd=repo_root, check=False)
    if res_sha.returncode != 0 or not res_sha.stdout.strip():
        raise KernelAuthorityError(f"Failed to resolve remote blob SHA for '{rel_path}' on '{remote}/{control_branch}'")
    blob_sha = res_sha.stdout.strip()

    # Read content
    res_content = gitops.git_cmd(["show", f"{remote}/{control_branch}:{rel_path}"], cwd=repo_root, check=False)
    if res_content.returncode != 0 or not res_content.stdout:
        raise KernelAuthorityError(f"Failed to read content for '{rel_path}' from '{remote}/{control_branch}'")

    return res_content.stdout, blob_sha


def authorize_kernel_task(
    task_id: str,
    action: str,
    executor_id: str,
    repo_root: Optional[Path] = None,
    config: Optional[Dict[str, Any]] = None,
) -> KernelTaskRecord:
    if repo_root is None:
        repo_root = Path.cwd()

    if config is None:
        config = {
            "remote": "origin",
            "control_branch": "ai-control",
            "base_branch": "main",
            "task_branch_prefix": "ai/task-",
        }

    norm_action = action.upper()
    if norm_action not in (KernelAction.RUN.value, KernelAction.FIX.value):
        raise KernelAuthorityError(f"Invalid action '{action}'. Must be RUN or FIX.")

    norm_executor = executor_id.lower()
    if norm_executor not in (KernelExecutor.CODEX.value, KernelExecutor.ANTIGRAVITY.value):
        raise KernelAuthorityError(f"Invalid executor_id '{executor_id}'. Must be codex or antigravity.")

    task_num = int(task_id.replace("TASK-", "").replace("task-", ""))
    formatted_id = f"TASK-{task_num:03d}"
    expected_branch = f"{config['task_branch_prefix']}{task_num:03d}"

    remote = config.get("remote", "origin")
    control_branch = config.get("control_branch", "ai-control")
    base_branch = config.get("base_branch", "main")

    # 1. Read TASK artifact strictly from remote control snapshot (B098.1)
    task_rel_path = f".ai/tasks/{formatted_id}.md"
    task_content, task_blob_sha = read_remote_control_file(repo_root, task_rel_path, remote, control_branch)

    # 2. Validate dispatch policy and selected executor (B098.1)
    dispatch_policy = parse_marker_json(task_content, "DISPATCH_EXECUTOR_POLICY_JSON:")
    if not isinstance(dispatch_policy, dict):
        raise KernelAuthorityError("DISPATCH_EXECUTOR_POLICY_JSON must be a dictionary")

    candidates = dispatch_policy.get("candidates", [])
    matched_candidate = None
    for cand in candidates:
        if cand.get("executor_id") == norm_executor:
            if norm_action in cand.get("supported_operations", []):
                matched_candidate = cand
                break
    if not matched_candidate:
        raise KernelAuthorityError(
            f"Selected executor '{norm_executor}' is not authorized for action '{norm_action}' in DISPATCH_EXECUTOR_POLICY_JSON"
        )

    # 3. For FIX: read REVIEW artifact strictly from remote control snapshot and require exact CHANGES_REQUIRED
    review_blob_sha = None
    if norm_action == KernelAction.FIX.value:
        review_rel_path = f".ai/reviews/REVIEW-{task_num:03d}.md"
        review_content, review_blob_sha = read_remote_control_file(repo_root, review_rel_path, remote, control_branch)
        if "STATUS: CHANGES_REQUIRED" not in review_content:
            raise KernelAuthorityError(f"Review '{review_rel_path}' is not in CHANGES_REQUIRED status.")
        if formatted_id not in review_content:
            raise KernelAuthorityError(f"Review '{review_rel_path}' does not bind to '{formatted_id}'.")

    # 4. Parse allowed_paths ONLY from exact machine control snapshot
    allowed_paths_raw = parse_marker_json(task_content, "EXECUTOR_ALLOWED_PATHS_JSON:")
    if not isinstance(allowed_paths_raw, list) or not allowed_paths_raw:
        raise KernelAuthorityError("EXECUTOR_ALLOWED_PATHS_JSON must be a non-empty list of string paths")
    allowed_paths = [str(p) for p in allowed_paths_raw]

    # 5. Parse and validate KERNEL_VERIFY_COMMAND_JSON (B098.2 - require non-empty T0 and T1)
    verify_commands_raw = parse_marker_json(task_content, "KERNEL_VERIFY_COMMAND_JSON:")
    if not isinstance(verify_commands_raw, dict):
        raise KernelAuthorityError("KERNEL_VERIFY_COMMAND_JSON must be a dictionary")

    t0_cmd = verify_commands_raw.get("t0")
    t1_cmd = verify_commands_raw.get("t1")
    if not isinstance(t0_cmd, list) or len(t0_cmd) == 0:
        raise KernelAuthorityError("KERNEL_VERIFY_COMMAND_JSON must contain a non-empty list for 't0'")
    if not isinstance(t1_cmd, list) or len(t1_cmd) == 0:
        raise KernelAuthorityError("KERNEL_VERIFY_COMMAND_JSON must contain a non-empty list for 't1'")

    # Ensure no extra unexpected tiers
    unexpected_tiers = set(verify_commands_raw.keys()) - {"t0", "t1"}
    if unexpected_tiers:
        raise KernelAuthorityError(f"Unexpected verification tiers in KERNEL_VERIFY_COMMAND_JSON: {unexpected_tiers}")

    verify_commands = {
        "t0": [str(c) for c in t0_cmd],
        "t1": [str(c) for c in t1_cmd],
    }

    # 6. Fetch fresh remote main SHA and prepare branch (B098.1)
    res_fetch_base = gitops.git_cmd(["fetch", remote, base_branch], cwd=repo_root, check=False)
    if res_fetch_base.returncode != 0:
        raise KernelAuthorityError(f"Failed to fetch remote base branch '{remote}/{base_branch}'")

    base_main_sha = gitops.git_cmd(["rev-parse", f"{remote}/{base_branch}"], cwd=repo_root).stdout.strip()
    if not base_main_sha:
        raise KernelAuthorityError(f"Could not resolve remote base main SHA for '{remote}/{base_branch}'")

    dirty_before_prep = gitops.collect_dirty_paths(cwd=repo_root)
    if dirty_before_prep:
        raise KernelAuthorityError(f"Working tree has uncommitted dirty paths before branch preparation: {dirty_before_prep}")

    # Switch/reset task branch from exact remote base main
    gitops.git_cmd(["checkout", "-B", expected_branch, base_main_sha], cwd=repo_root)
    pre_execution_head = gitops.get_head_sha(cwd=repo_root)
    if pre_execution_head != base_main_sha:
        raise KernelAuthorityError(f"Task branch prepared head '{pre_execution_head}' does not match base main '{base_main_sha}'")

    # 7. Build and save minimal atomic record
    allowed_paths_fp = compute_fingerprint(allowed_paths)
    verify_cmd_fp = compute_fingerprint(verify_commands)

    record = KernelTaskRecord(
        task_id=formatted_id,
        action=norm_action,
        executor_id=norm_executor,
        base_main_sha=base_main_sha,
        target_branch=expected_branch,
        authorized_artifact_sha=task_blob_sha,
        review_sha=review_blob_sha,
        allowed_paths=allowed_paths,
        allowed_paths_fingerprint=allowed_paths_fp,
        verify_command_fingerprint=verify_cmd_fp,
        verify_commands=verify_commands,
        pre_execution_head=pre_execution_head,
        status=KernelStatus.AUTHORIZED.value,
    )

    save_task_record(record, repo_root)
    return record
