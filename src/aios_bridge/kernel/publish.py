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

    remote = config.get("remote", "origin")
    control_branch = config.get("control_branch", "ai-control")
    base_branch = config.get("base_branch", "main")
    task_num = int(record.task_id.replace("TASK-", "").replace("task-", ""))

    try:
        # 2. Check current branch
        branch = gitops.get_current_branch(cwd=repo_root)
        if branch != record.target_branch:
            raise KernelPublishError(f"Current branch '{branch}' does not match authorized target branch '{record.target_branch}'")

        # 3. Check worktree delta before test
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

        # 6. Revalidate control snapshot artifacts and blobs (B098.1)
        gitops.git_cmd(["fetch", remote, control_branch], cwd=repo_root, check=False)
        task_rel_path = f".ai/tasks/{record.task_id}.md"
        res_task_blob = gitops.git_cmd(["rev-parse", f"{remote}/{control_branch}:{task_rel_path}"], cwd=repo_root, check=False)
        current_task_blob = res_task_blob.stdout.strip() if res_task_blob.returncode == 0 else None
        if not current_task_blob:
            raise KernelPublishError(f"Control task artifact '{task_rel_path}' missing on '{remote}/{control_branch}'")
        if current_task_blob != record.authorized_artifact_sha:
            raise KernelPublishError(
                f"Control task artifact '{task_rel_path}' blob drifted on '{remote}/{control_branch}' (expected {record.authorized_artifact_sha}, got {current_task_blob})"
            )

        if record.action == "FIX" and record.review_sha:
            review_rel_path = f".ai/reviews/REVIEW-{task_num:03d}.md"
            res_rev_blob = gitops.git_cmd(["rev-parse", f"{remote}/{control_branch}:{review_rel_path}"], cwd=repo_root, check=False)
            current_rev_blob = res_rev_blob.stdout.strip() if res_rev_blob.returncode == 0 else None
            if not current_rev_blob:
                raise KernelPublishError(f"Control review artifact '{review_rel_path}' missing on '{remote}/{control_branch}'")
            if current_rev_blob != record.review_sha:
                raise KernelPublishError(
                    f"Control review artifact '{review_rel_path}' blob drifted on '{remote}/{control_branch}' (expected {record.review_sha}, got {current_rev_blob})"
                )

        # 7. Check base main SHA
        gitops.git_cmd(["fetch", remote, base_branch], cwd=repo_root, check=False)
        remote_main_sha = gitops.get_remote_ref_sha(remote, base_branch, cwd=repo_root)
        if remote_main_sha and remote_main_sha != record.base_main_sha:
            raise KernelPublishError(f"Remote main SHA '{remote_main_sha}' drifted from authorized base '{record.base_main_sha}'")

        # 8. Capture publication trust preflight
        trust_snapshot = gitops.capture_publication_trust(remote, cwd=repo_root)
        gitops.verify_publication_trust(trust_snapshot, cwd=repo_root)

        pre_verify_head = gitops.get_head_sha(cwd=repo_root)

        # 9. Execute VERIFY (canonical T0/T1 exactly once)
        verify_res = run_kernel_verify(record, repo_root)

        if not verify_res.passed or not verify_res.t0_executed or not verify_res.t1_executed:
            record.status = KernelStatus.BLOCKED.value
            save_task_record(record, repo_root)
            return KernelPublishResult(
                success=False,
                status=KernelStatus.BLOCKED.value,
                error=f"Verification failed with exit code {verify_res.exit_code}",
                verify_result=verify_res,
            )

        # 10. Post-VERIFY publication revalidation (B098.4)
        post_verify_branch = gitops.get_current_branch(cwd=repo_root)
        if post_verify_branch != record.target_branch:
            raise KernelPublishError(f"Post-verify branch '{post_verify_branch}' does not match target '{record.target_branch}'")

        post_verify_head = gitops.get_head_sha(cwd=repo_root)
        if post_verify_head != pre_verify_head:
            raise KernelPublishError(f"Post-verify HEAD '{post_verify_head}' drifted from pre-verify head '{pre_verify_head}'")

        gitops.git_cmd(["fetch", remote, base_branch], cwd=repo_root, check=False)
        post_remote_main_sha = gitops.get_remote_ref_sha(remote, base_branch, cwd=repo_root)
        if post_remote_main_sha and post_remote_main_sha != record.base_main_sha:
            raise KernelPublishError(f"Post-verify remote main '{post_remote_main_sha}' drifted from base '{record.base_main_sha}'")

        post_changed_paths = gitops.collect_worktree_changed_paths(record.pre_execution_head, cwd=repo_root)
        if not post_changed_paths:
            raise KernelPublishError("Executor produced no worktree delta after tests")

        post_disallowed = [p for p in post_changed_paths if p not in record.allowed_paths]
        if post_disallowed:
            raise KernelPublishError(f"Post-verify changed paths {post_disallowed} outside allowed_paths {record.allowed_paths}")

        gitops.verify_publication_trust(trust_snapshot, cwd=repo_root)

        # 11. Generate RESULT file with verified evidence
        results_dir = repo_root / ".ai" / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        result_rel_path = f".ai/results/RESULT-{task_num:03d}.md"
        result_path = repo_root / result_rel_path

        t0_status = "PASS" if (verify_res.t0_executed and verify_res.passed) else "FAIL"
        t1_status = "PASS" if (verify_res.t1_executed and verify_res.passed) else "FAIL"

        result_content = f"""# RESULT-{task_num:03d} — AIOS Bridge Kernel v1 Candidate

STATUS: PASS
PUBLISHER_PROFILE: CANONICAL_E4
TASK_ID: {record.task_id}
ACTION: {record.action}
EXECUTOR_ID: {record.executor_id}
BASE_MAIN_SHA: {record.base_main_sha}
TARGET_BRANCH: {record.target_branch}
PRE_EXECUTION_HEAD: {record.pre_execution_head}
VERIFY_T0_STATUS: {t0_status}
VERIFY_T1_STATUS: {t1_status}
PUBLICATION_TRUST_STATUS: VERIFIED
"""
        result_path.write_text(result_content, encoding="utf-8")

        # 12. Stage ONLY exact intended paths (B098.4 - no unrestricted git add .)
        target_stage_paths = post_changed_paths + [result_rel_path]
        gitops.git_cmd(["add", *target_stage_paths], cwd=repo_root)
        gitops.git_cmd(["commit", "-m", f"RESULT-{task_num:03d}: complete candidate"], cwd=repo_root)
        gitops.git_cmd(["push", remote, record.target_branch], cwd=repo_root)

        # 13. Revalidate fresh remote published ref identity (B098.4)
        published_sha = gitops.get_head_sha(cwd=repo_root)
        gitops.git_cmd(["fetch", remote, record.target_branch], cwd=repo_root, check=False)
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

    except Exception as exc:
        # B098.3: Terminalize to BLOCKED for every preflight/trust/verification failure
        record.status = KernelStatus.BLOCKED.value
        save_task_record(record, repo_root)
        return KernelPublishResult(
            success=False,
            status=KernelStatus.BLOCKED.value,
            error=str(exc),
        )
