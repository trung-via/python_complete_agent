"""AIOS Bridge Kernel v1 PUBLISH Pipeline (ADR-068 / TASK-098)."""

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Optional, Dict, Any, List

from src.aios_bridge.kernel.model import (
    KernelTaskRecord,
    KernelStatus,
    compute_fingerprint,
    save_task_record,
    load_task_record,
)
from src.aios_bridge.kernel import gitops
from src.aios_bridge.kernel.verify import run_kernel_verify, KernelVerifyResult


class KernelPublishError(RuntimeError):
    pass


@dataclass
class KernelPublishResult:
    success: bool
    status: str
    published_head_sha: Optional[str] = None
    error: Optional[str] = None
    verify_result: Optional[KernelVerifyResult] = None


def complete_kernel_task(
    task_id: str,
    repo_root: Optional[Path] = None,
    config: Optional[Dict[str, Any]] = None,
) -> KernelPublishResult:
    if repo_root is None:
        repo_root = Path.cwd()

    if config is None:
        config = {
            "remote": "origin",
            "control_branch": "ai-control",
            "base_branch": "main",
            "task_branch_prefix": "ai/task-",
        }

    # 1. Load exact task record
    record = load_task_record(task_id, repo_root)
    if not record:
        raise KernelPublishError(f"No task record found for '{task_id}'")

    if record.status != KernelStatus.AUTHORIZED.value:
        raise KernelPublishError(f"Task '{task_id}' is in status '{record.status}', required status is AUTHORIZED")

    # 2. Check current branch
    branch = gitops.get_current_branch(cwd=repo_root)
    if branch != record.target_branch:
        raise KernelPublishError(f"Current branch '{branch}' does not match authorized target branch '{record.target_branch}'")

    # 3. Check worktree delta
    changed_paths = gitops.collect_worktree_changed_paths(record.pre_execution_head, cwd=repo_root)
    if not changed_paths:
        raise KernelPublishError("Executor produced no worktree delta")

    # 4. Check allowed_paths scope
    disallowed = [p for p in changed_paths if p not in record.allowed_paths]
    if disallowed:
        raise KernelPublishError(f"Changed paths {disallowed} outside authorized allowed_paths {record.allowed_paths}")

    # 5. Verify fingerprints
    if compute_fingerprint(record.allowed_paths) != record.allowed_paths_fingerprint:
        raise KernelPublishError("allowed_paths_fingerprint tampering detected")
    if compute_fingerprint(record.verify_commands) != record.verify_command_fingerprint:
        raise KernelPublishError("verify_command_fingerprint tampering detected")

    # 6. Check base main SHA
    remote = config.get("remote", "origin")
    base_branch = config.get("base_branch", "main")
    remote_main_sha = gitops.get_remote_ref_sha(remote, base_branch, cwd=repo_root)
    if remote_main_sha and remote_main_sha != record.base_main_sha:
        raise KernelPublishError(f"Remote main SHA '{remote_main_sha}' drifted from authorized base '{record.base_main_sha}'")

    # 7. Capture publication trust preflight
    trust_snapshot = gitops.capture_publication_trust(remote, cwd=repo_root)
    gitops.verify_publication_trust(trust_snapshot, cwd=repo_root)

    # 8. Execute VERIFY (canonical T0/T1 exactly once)
    verify_res = run_kernel_verify(record, repo_root)

    if not verify_res.passed:
        # Fail closed: update status to BLOCKED, preserve work, 0 commits, 0 pushes
        record.status = KernelStatus.BLOCKED.value
        save_task_record(record, repo_root)
        return KernelPublishResult(
            success=False,
            status=KernelStatus.BLOCKED.value,
            error=f"Verification failed with exit code {verify_res.exit_code}",
            verify_result=verify_res,
        )

    # 9. If PASS, revalidate publication trust post-test
    gitops.verify_publication_trust(trust_snapshot, cwd=repo_root)

    # 10. Generate RESULT file
    results_dir = repo_root / ".ai" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    task_num = int(record.task_id.replace("TASK-", "").replace("task-", ""))
    result_path = results_dir / f"RESULT-{task_num:03d}.md"

    current_head = gitops.get_head_sha(cwd=repo_root)
    result_content = f"""# RESULT-{task_num:03d} — AIOS Bridge Kernel v1 Candidate

STATUS: PASS
PUBLISHER_PROFILE: CANONICAL_E4
TASK_ID: {record.task_id}
ACTION: {record.action}
EXECUTOR_ID: {record.executor_id}
BASE_MAIN_SHA: {record.base_main_sha}
TARGET_BRANCH: {record.target_branch}
PRE_EXECUTION_HEAD: {record.pre_execution_head}
VERIFY_T0_STATUS: PASS
VERIFY_T1_STATUS: PASS
PUBLICATION_TRUST_STATUS: VERIFIED
"""
    result_path.write_text(result_content, encoding="utf-8")

    # 11. Commit once & Push once
    gitops.git_cmd(["add", "."], cwd=repo_root)
    gitops.git_cmd(["commit", "-m", f"RESULT-{task_num:03d}: complete candidate"], cwd=repo_root)
    gitops.git_cmd(["push", remote, record.target_branch], cwd=repo_root)

    # 12. Revalidate exact published identity
    published_sha = gitops.get_head_sha(cwd=repo_root)
    remote_published_sha = gitops.get_remote_ref_sha(remote, record.target_branch, cwd=repo_root)
    if remote_published_sha and remote_published_sha != published_sha:
        raise KernelPublishError(f"Remote branch SHA '{remote_published_sha}' does not match local published SHA '{published_sha}'")

    record.status = KernelStatus.PUBLISHED.value
    record.published_head_sha = published_sha
    save_task_record(record, repo_root)

    return KernelPublishResult(
        success=True,
        status=KernelStatus.PUBLISHED.value,
        published_head_sha=published_sha,
        verify_result=verify_res,
    )
