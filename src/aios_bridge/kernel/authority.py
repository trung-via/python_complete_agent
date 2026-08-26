"""AIOS Bridge Kernel v1 AUTHORIZE Pipeline (ADR-068 / TASK-098)."""

import json
from pathlib import Path
from typing import List, Optional, Dict, Any

from src.aios_bridge.kernel.model import (
    KernelTaskRecord,
    KernelStatus,
    KernelAction,
    KernelExecutor,
    compute_fingerprint,
    save_task_record,
    load_task_record,
)
from src.aios_bridge.kernel.gitops import get_current_branch, get_head_sha, git_cmd


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


def read_control_file(repo_root: Path, rel_path: str, remote: str = "origin", control_branch: str = "ai-control") -> str:
    """Reads a file from remote control branch or local .ai fallback."""
    # First attempt: git show remote/control_branch:rel_path
    res = git_cmd(["show", f"{remote}/{control_branch}:{rel_path}"], cwd=repo_root, check=False)
    if res.returncode == 0 and res.stdout.strip():
        return res.stdout

    # Fallback attempt for test environments: local disk at repo_root / rel_path
    local_file = repo_root / rel_path
    if local_file.exists():
        return local_file.read_text(encoding="utf-8")

    raise KernelAuthorityError(f"Failed to read control file '{rel_path}' from {remote}/{control_branch} or local workspace")


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

    # Fetch control branch
    remote = config.get("remote", "origin")
    control_branch = config.get("control_branch", "ai-control")
    git_cmd(["fetch", remote, control_branch], cwd=repo_root, check=False)

    # 1. Read TASK artifact from control snapshot
    task_rel_path = f".ai/tasks/{formatted_id}.md"
    task_content = read_control_file(repo_root, task_rel_path, remote, control_branch)
    task_sha = hashlib_sha(task_content)

    review_sha = None
    if norm_action == KernelAction.FIX.value:
        review_rel_path = f".ai/reviews/REVIEW-{task_num:03d}.md"
        review_content = read_control_file(repo_root, review_rel_path, remote, control_branch)
        if "STATUS: CHANGES_REQUIRED" not in review_content:
            raise KernelAuthorityError(f"Review '{review_rel_path}' is not in CHANGES_REQUIRED status.")
        review_sha = hashlib_sha(review_content)

    # 2. Parse allowed_paths ONLY from exact machine control snapshot
    allowed_paths_raw = parse_marker_json(task_content, "EXECUTOR_ALLOWED_PATHS_JSON:")
    if not isinstance(allowed_paths_raw, list) or not allowed_paths_raw:
        raise KernelAuthorityError("EXECUTOR_ALLOWED_PATHS_JSON must be a non-empty list of string paths")
    allowed_paths = [str(p) for p in allowed_paths_raw]

    # 3. Parse KERNEL_VERIFY_COMMAND_JSON ONLY from exact machine control snapshot
    verify_commands_raw = parse_marker_json(task_content, "KERNEL_VERIFY_COMMAND_JSON:")
    if not isinstance(verify_commands_raw, dict):
        raise KernelAuthorityError("KERNEL_VERIFY_COMMAND_JSON must be a dictionary with 't0' and/or 't1' arrays")
    
    verify_commands = {
        "t0": list(verify_commands_raw.get("t0", [])),
        "t1": list(verify_commands_raw.get("t1", [])),
    }

    # 4. Resolve base main SHA and prepare branch
    base_main_sha = get_head_sha(cwd=repo_root)  # or remote main sha if fetched
    remote_main_sha = git_cmd(["rev-parse", f"{remote}/{config.get('base_branch', 'main')}"], cwd=repo_root, check=False).stdout.strip()
    if remote_main_sha:
        base_main_sha = remote_main_sha

    # 5. Build and save minimal atomic record
    allowed_paths_fp = compute_fingerprint(allowed_paths)
    verify_cmd_fp = compute_fingerprint(verify_commands)
    pre_execution_head = get_head_sha(cwd=repo_root)

    record = KernelTaskRecord(
        task_id=formatted_id,
        action=norm_action,
        executor_id=norm_executor,
        base_main_sha=base_main_sha,
        target_branch=expected_branch,
        authorized_artifact_sha=task_sha,
        review_sha=review_sha,
        allowed_paths=allowed_paths,
        allowed_paths_fingerprint=allowed_paths_fp,
        verify_command_fingerprint=verify_cmd_fp,
        verify_commands=verify_commands,
        pre_execution_head=pre_execution_head,
        status=KernelStatus.AUTHORIZED.value,
    )

    save_task_record(record, repo_root)
    return record


def hashlib_sha(content: str) -> str:
    import hashlib
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
