"""Tests for AIOS Bridge Kernel v1 PUBLISH Pipeline (ADR-068 / TASK-098)."""

import pytest
import subprocess
from pathlib import Path

from src.aios_bridge.kernel.model import KernelTaskRecord, save_task_record, compute_fingerprint, KernelStatus
from src.aios_bridge.kernel.publish import complete_kernel_task, KernelPublishError
from src.aios_bridge.kernel import gitops, publish


def test_complete_empty_delta_rejected_before_test(tmp_path, monkeypatch):
    """Proof: EMPTY_DELTA_COMPLETE_REJECTED_BEFORE_TEST: PASS."""
    record = KernelTaskRecord(
        task_id="TASK-098",
        action="RUN",
        executor_id="antigravity",
        base_main_sha="a" * 40,
        target_branch="ai/task-098",
        authorized_artifact_sha="b" * 40,
        allowed_paths=["aios_kernel.py"],
        allowed_paths_fingerprint=compute_fingerprint(["aios_kernel.py"]),
        verify_command_fingerprint=compute_fingerprint({"t0": ["pytest"]}),
        verify_commands={"t0": ["pytest"]},
        pre_execution_head="c" * 40,
        status="AUTHORIZED",
    )
    save_task_record(record, repo_root=tmp_path)

    monkeypatch.setattr(gitops, "get_current_branch", lambda cwd: "ai/task-098")
    monkeypatch.setattr(gitops, "collect_worktree_changed_paths", lambda pre, cwd: [])

    test_ran = []
    monkeypatch.setattr(publish, "run_kernel_verify", lambda rec, root: test_ran.append(True))

    with pytest.raises(KernelPublishError, match="Executor produced no worktree delta"):
        complete_kernel_task("TASK-098", repo_root=tmp_path)

    assert len(test_ran) == 0


def test_complete_out_of_scope_rejected_before_test(tmp_path, monkeypatch):
    """Proof: OUT_OF_SCOPE_COMPLETE_REJECTED_BEFORE_TEST: PASS."""
    record = KernelTaskRecord(
        task_id="TASK-098",
        action="RUN",
        executor_id="antigravity",
        base_main_sha="a" * 40,
        target_branch="ai/task-098",
        authorized_artifact_sha="b" * 40,
        allowed_paths=["aios_kernel.py"],
        allowed_paths_fingerprint=compute_fingerprint(["aios_kernel.py"]),
        verify_command_fingerprint=compute_fingerprint({"t0": ["pytest"]}),
        verify_commands={"t0": ["pytest"]},
        pre_execution_head="c" * 40,
        status="AUTHORIZED",
    )
    save_task_record(record, repo_root=tmp_path)

    monkeypatch.setattr(gitops, "get_current_branch", lambda cwd: "ai/task-098")
    # Dirty file outside allowed_paths
    monkeypatch.setattr(gitops, "collect_worktree_changed_paths", lambda pre, cwd: ["aios_kernel.py", "unauthorized.py"])

    test_ran = []
    monkeypatch.setattr(publish, "run_kernel_verify", lambda rec, root: test_ran.append(True))

    with pytest.raises(KernelPublishError, match="outside authorized allowed_paths"):
        complete_kernel_task("TASK-098", repo_root=tmp_path)

    assert len(test_ran) == 0


def test_complete_verify_failure_blocks_with_zero_commit_push(tmp_path, monkeypatch):
    """Proof: VERIFY_FAILURE_TERMINAL_STATE: BLOCKED & VERIFY_FAILURE_COMMIT_PUSH_COUNT: 0."""
    record = KernelTaskRecord(
        task_id="TASK-098",
        action="RUN",
        executor_id="antigravity",
        base_main_sha="a" * 40,
        target_branch="ai/task-098",
        authorized_artifact_sha="b" * 40,
        allowed_paths=["aios_kernel.py"],
        allowed_paths_fingerprint=compute_fingerprint(["aios_kernel.py"]),
        verify_command_fingerprint=compute_fingerprint({"t0": ["pytest"]}),
        verify_commands={"t0": ["pytest"]},
        pre_execution_head="c" * 40,
        status="AUTHORIZED",
    )
    save_task_record(record, repo_root=tmp_path)

    monkeypatch.setattr(gitops, "get_current_branch", lambda cwd: "ai/task-098")
    monkeypatch.setattr(gitops, "collect_worktree_changed_paths", lambda pre, cwd: ["aios_kernel.py"])
    monkeypatch.setattr(gitops, "get_remote_ref_sha", lambda r, b, cwd: "a" * 40)
    monkeypatch.setattr(gitops, "capture_publication_trust", lambda r, cwd: {"remote": r})
    monkeypatch.setattr(gitops, "verify_publication_trust", lambda s, cwd: None)

    # Verification fails
    failed_vr = publish.KernelVerifyResult(passed=False, exit_code=1, t0_executed=True, t1_executed=False, output="fail")
    monkeypatch.setattr(publish, "run_kernel_verify", lambda rec, root: failed_vr)

    git_commits = []
    git_pushes = []
    def mock_git_cmd(args, cwd=None, check=True):
        if "commit" in args:
            git_commits.append(args)
        if "push" in args:
            git_pushes.append(args)
        return type("Res", (), {"returncode": 0, "stdout": "", "stderr": ""})()
    monkeypatch.setattr(gitops, "git_cmd", mock_git_cmd)

    res = complete_kernel_task("TASK-098", repo_root=tmp_path)

    assert res.success is False
    assert res.status == KernelStatus.BLOCKED.value
    assert len(git_commits) == 0
    assert len(git_pushes) == 0


def test_complete_verify_pass_publishes_once(tmp_path, monkeypatch):
    """Proof: PUBLISH_COMMIT_COUNT: 1 & PUBLISH_PUSH_COUNT: 1 & PUBLISH_REMOTE_HEAD_POST_VERIFY: PASS."""
    record = KernelTaskRecord(
        task_id="TASK-098",
        action="RUN",
        executor_id="antigravity",
        base_main_sha="a" * 40,
        target_branch="ai/task-098",
        authorized_artifact_sha="b" * 40,
        allowed_paths=["aios_kernel.py"],
        allowed_paths_fingerprint=compute_fingerprint(["aios_kernel.py"]),
        verify_command_fingerprint=compute_fingerprint({"t0": ["pytest"]}),
        verify_commands={"t0": ["pytest"]},
        pre_execution_head="c" * 40,
        status="AUTHORIZED",
    )
    save_task_record(record, repo_root=tmp_path)

    monkeypatch.setattr(gitops, "get_current_branch", lambda cwd: "ai/task-098")
    monkeypatch.setattr(gitops, "collect_worktree_changed_paths", lambda pre, cwd: ["aios_kernel.py"])
    monkeypatch.setattr(gitops, "get_remote_ref_sha", lambda r, b, cwd: "a" * 40 if b == "main" else "pub_head_98")
    monkeypatch.setattr(gitops, "get_head_sha", lambda cwd: "pub_head_98")
    monkeypatch.setattr(gitops, "capture_publication_trust", lambda r, cwd: {"remote": r})
    monkeypatch.setattr(gitops, "verify_publication_trust", lambda s, cwd: None)

    pass_vr = publish.KernelVerifyResult(passed=True, exit_code=0, t0_executed=True, t1_executed=True, output="pass")
    monkeypatch.setattr(publish, "run_kernel_verify", lambda rec, root: pass_vr)

    git_commits = []
    git_pushes = []
    def mock_git_cmd(args, cwd=None, check=True):
        if "commit" in args:
            git_commits.append(args)
        if "push" in args:
            git_pushes.append(args)
        return type("Res", (), {"returncode": 0, "stdout": "", "stderr": ""})()
    monkeypatch.setattr(gitops, "git_cmd", mock_git_cmd)

    res = complete_kernel_task("TASK-098", repo_root=tmp_path)

    assert res.success is True
    assert res.status == KernelStatus.PUBLISHED.value
    assert res.published_head_sha == "pub_head_98"
    assert len(git_commits) == 1
    assert len(git_pushes) == 1
