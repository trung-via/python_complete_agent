"""Tests for AIOS Bridge Kernel v1 AUTHORIZE Pipeline (ADR-068 / TASK-098)."""

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
        'KERNEL_VERIFY_COMMAND_JSON: {"t0": ["pytest t0"], "t1": ["pytest t1"]}\n'
    )

    monkeypatch.setattr(gitops, "git_cmd", lambda *args, **kw: type("Res", (), {"returncode": 0, "stdout": "head_123\n", "stderr": ""})())
    
    # Mock read_control_file inside authority
    import src.aios_bridge.kernel.authority as auth_mod
    monkeypatch.setattr(auth_mod, "read_control_file", lambda root, rel, remote, branch: task_content)

    rec = authorize_kernel_task("TASK-098", "RUN", "antigravity", repo_root=tmp_path)

    assert rec.task_id == "TASK-098"
    assert rec.action == "RUN"
    assert rec.executor_id == "antigravity"
    assert rec.allowed_paths == ["aios_kernel.py", "bridge.py"]
    assert rec.verify_commands == {"t0": ["pytest t0"], "t1": ["pytest t1"]}
    assert rec.status == "AUTHORIZED"


def test_authorize_kernel_task_fix_requires_changes_required_review(tmp_path, monkeypatch):
    """Proof: FIX requires exact CHANGES_REQUIRED review artifact."""
    task_content = (
        'PUBLISHER_PROFILE: CANONICAL_E4\n'
        'EXECUTOR_ALLOWED_PATHS_JSON: ["aios_kernel.py"]\n'
        'KERNEL_VERIFY_COMMAND_JSON: {"t0": ["pytest"]}\n'
    )
    review_content_invalid = (
        'STATUS: APPROVED\n'
        'EXECUTOR_ALLOWED_PATHS_JSON: ["aios_kernel.py"]\n'
    )

    import src.aios_bridge.kernel.authority as auth_mod
    monkeypatch.setattr(gitops, "git_cmd", lambda *args, **kw: type("Res", (), {"returncode": 0, "stdout": "head_123\n", "stderr": ""})())

    def mock_read(root, rel, remote, branch):
        if "tasks" in rel:
            return task_content
        return review_content_invalid

    monkeypatch.setattr(auth_mod, "read_control_file", mock_read)

    with pytest.raises(KernelAuthorityError, match="not in CHANGES_REQUIRED status"):
        authorize_kernel_task("TASK-098", "FIX", "antigravity", repo_root=tmp_path)
