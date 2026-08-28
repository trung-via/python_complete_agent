"""Tests for AIOS Bridge Kernel v1 AUTHORIZE Pipeline (ADR-068 / TASK-098 / B098.1 / B098.2)."""

import pytest
import subprocess
from pathlib import Path

from src.aios_bridge.kernel.authority import authorize_kernel_task, KernelAuthorityError
from src.aios_bridge.kernel import gitops


def test_authorize_kernel_task_run_success(tmp_path, monkeypatch):
    """Proof: AUTHORIZE_EXACT_TASK_REVIEW_BINDING: PASS & ALLOWED_PATHS_MACHINE_DERIVED: PASS."""
    task_content = (
        'PUBLISHER_PROFILE: CANONICAL_E4\n'
        'EXECUTOR_CONTEXT_REFS_JSON: [{"path": ".ai/decisions/ADR-001.md", "blob_sha": "a" * 40}]\n'
        'EXECUTOR_ALLOWED_PATHS_JSON: ["aios_kernel.py", "bridge.py"]\n'
        'DISPATCH_EXECUTOR_POLICY_JSON: {"operation": "RUN", "candidates": [{"executor_id": "antigravity", "supported_operations": ["RUN"]}]}\n'
        'KERNEL_VERIFY_COMMAND_JSON: {"t0": ["pytest t0"], "t1": ["pytest t1"]}\n'
    )

    def mock_git_cmd(args, cwd=None, check=True):
        if "rev-parse" in args and "origin/main" in args[-1]:
            return type("Res", (), {"returncode": 0, "stdout": "main_base_sha\n", "stderr": ""})()
        if "rev-parse" in args and "TASK-098.md" in args[-1]:
            return type("Res", (), {"returncode": 0, "stdout": "task_blob_123\n", "stderr": ""})()
        if "rev-parse" in args and "HEAD" in args[-1]:
            return type("Res", (), {"returncode": 0, "stdout": "main_base_sha\n", "stderr": ""})()
        if "show" in args and "TASK-098.md" in args[-1]:
            return type("Res", (), {"returncode": 0, "stdout": task_content, "stderr": ""})()
        if "checkout" in args:
            return type("Res", (), {"returncode": 0, "stdout": "", "stderr": ""})()
        return type("Res", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr(gitops, "git_cmd", mock_git_cmd)
    monkeypatch.setattr(gitops, "collect_dirty_paths", lambda cwd: [])
    monkeypatch.setattr(gitops, "get_head_sha", lambda cwd: "main_base_sha")

    rec = authorize_kernel_task("TASK-098", "RUN", "antigravity", repo_root=tmp_path)

    assert rec.task_id == "TASK-098"
    assert rec.action == "RUN"
    assert rec.executor_id == "antigravity"
    assert rec.allowed_paths == ["aios_kernel.py", "bridge.py"]
    assert rec.verify_commands == {"t0": ["pytest t0"], "t1": ["pytest t1"]}
    assert rec.authorized_artifact_sha == "task_blob_123"
    assert rec.base_main_sha == "main_base_sha"
    assert rec.pre_execution_head == "main_base_sha"
    assert rec.status == "AUTHORIZED"


def test_authorize_kernel_task_rejects_unauthorized_executor(tmp_path, monkeypatch):
    """Proof: DISPATCH_EXECUTOR_AUTHORITY: EXACT (B098.1)."""
    task_content = (
        'PUBLISHER_PROFILE: CANONICAL_E4\n'
        'EXECUTOR_ALLOWED_PATHS_JSON: ["aios_kernel.py"]\n'
        'DISPATCH_EXECUTOR_POLICY_JSON: {"operation": "RUN", "candidates": [{"executor_id": "codex", "supported_operations": ["RUN"]}]}\n'
        'KERNEL_VERIFY_COMMAND_JSON: {"t0": ["pytest t0"], "t1": ["pytest t1"]}\n'
    )

    def mock_git_cmd(args, cwd=None, check=True):
        if "show" in args:
            return type("Res", (), {"returncode": 0, "stdout": task_content, "stderr": ""})()
        if "rev-parse" in args:
            return type("Res", (), {"returncode": 0, "stdout": "blob_sha\n", "stderr": ""})()
        return type("Res", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr(gitops, "git_cmd", mock_git_cmd)

    with pytest.raises(KernelAuthorityError, match="Selected executor 'antigravity' is not authorized"):
        authorize_kernel_task("TASK-098", "RUN", "antigravity", repo_root=tmp_path)


def test_authorize_kernel_task_requires_nonempty_t0_and_t1(tmp_path, monkeypatch):
    """Proof: T0_REQUIRED_NONEMPTY & T1_REQUIRED_NONEMPTY: PASS (B098.2)."""
    task_content_empty_t1 = (
        'PUBLISHER_PROFILE: CANONICAL_E4\n'
        'EXECUTOR_ALLOWED_PATHS_JSON: ["aios_kernel.py"]\n'
        'DISPATCH_EXECUTOR_POLICY_JSON: {"operation": "RUN", "candidates": [{"executor_id": "antigravity", "supported_operations": ["RUN"]}]}\n'
        'KERNEL_VERIFY_COMMAND_JSON: {"t0": ["pytest t0"], "t1": []}\n'
    )

    def mock_git_cmd(args, cwd=None, check=True):
        if "show" in args:
            return type("Res", (), {"returncode": 0, "stdout": task_content_empty_t1, "stderr": ""})()
        if "rev-parse" in args:
            return type("Res", (), {"returncode": 0, "stdout": "blob_sha\n", "stderr": ""})()
        return type("Res", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr(gitops, "git_cmd", mock_git_cmd)

    with pytest.raises(KernelAuthorityError, match="must contain a non-empty list for 't1'"):
        authorize_kernel_task("TASK-098", "RUN", "antigravity", repo_root=tmp_path)


def test_authorize_kernel_task_fix_requires_changes_required_review(tmp_path, monkeypatch):
    """Proof: FIX requires exact CHANGES_REQUIRED review artifact binding (B098.1)."""
    task_content = (
        'PUBLISHER_PROFILE: CANONICAL_E4\n'
        'EXECUTOR_ALLOWED_PATHS_JSON: ["aios_kernel.py"]\n'
        'DISPATCH_EXECUTOR_POLICY_JSON: {"operation": "FIX", "candidates": [{"executor_id": "antigravity", "supported_operations": ["FIX"]}]}\n'
        'KERNEL_VERIFY_COMMAND_JSON: {"t0": ["pytest t0"], "t1": ["pytest t1"]}\n'
    )
    review_content_invalid = (
        'STATUS: APPROVED\n'
        'TASK_ID: TASK-098\n'
    )

    def mock_git_cmd(args, cwd=None, check=True):
        if "show" in args and "TASK-098.md" in args[-1]:
            return type("Res", (), {"returncode": 0, "stdout": task_content, "stderr": ""})()
        if "show" in args and "REVIEW-098.md" in args[-1]:
            return type("Res", (), {"returncode": 0, "stdout": review_content_invalid, "stderr": ""})()
        if "rev-parse" in args:
            return type("Res", (), {"returncode": 0, "stdout": "blob_sha\n", "stderr": ""})()
        return type("Res", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr(gitops, "git_cmd", mock_git_cmd)

    with pytest.raises(KernelAuthorityError, match="not in CHANGES_REQUIRED status"):
        authorize_kernel_task("TASK-098", "FIX", "antigravity", repo_root=tmp_path)
