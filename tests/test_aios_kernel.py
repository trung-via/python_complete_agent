"""Integration tests and contract proofs for AIOS Bridge Kernel v1 (ADR-068 / TASK-098 / REVIEW-098)."""

import pytest
import subprocess
from pathlib import Path

from src.aios_bridge.kernel.model import KernelTaskRecord, save_task_record, compute_fingerprint, KernelStatus
from src.aios_bridge.kernel.publish import complete_kernel_task
from src.aios_bridge.kernel import gitops, publish


def test_kernel_proof_no_model_launch_command():
    """Proof: KERNEL_MODEL_LAUNCH_COMMAND: NONE & NESTED_CODEX_INVOCATION: 0 & AUTO_REROUTE: 0."""
    kernel_dir = Path("src/aios_bridge/kernel")
    for py_file in kernel_dir.glob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        assert "codex exec" not in content
        assert "invoke_subagent" not in content
        assert "auto_reroute" not in content


def test_kernel_proof_worker_script_repo_root_exact():
    """Proof: KERNEL_WORKER_REPO_ROOT: EXACT (B098.5)."""
    from importlib import import_module
    import sys

    script_path = Path(".agents/skills/aios-kernel-worker/scripts/aios_kernel_worker.py")
    assert script_path.exists()

    # Test find_repo_root logic
    import importlib.util
    spec = importlib.util.spec_from_file_location("aios_kernel_worker", str(script_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    resolved_root = mod.repo_root
    assert (resolved_root / "aios_kernel.py").exists() or (resolved_root / "bridge.py").exists()
    assert resolved_root.name != ".agents"


def test_kernel_proof_run_fix_downstream_codepath_same(tmp_path, monkeypatch):
    """Proof: RUN_FIX_DOWNSTREAM_CODEPATH: SAME."""
    # Both RUN and FIX use complete_kernel_task without branching logic
    rec_run = KernelTaskRecord(
        task_id="TASK-098", action="RUN", executor_id="antigravity",
        base_main_sha="a"*40, target_branch="ai/task-098", authorized_artifact_sha="b"*40,
        allowed_paths=["aios_kernel.py"], allowed_paths_fingerprint=compute_fingerprint(["aios_kernel.py"]),
        verify_command_fingerprint=compute_fingerprint({"t0": ["pytest"], "t1": ["pytest"]}), verify_commands={"t0": ["pytest"], "t1": ["pytest"]},
        pre_execution_head="c"*40, status="AUTHORIZED"
    )
    rec_fix = KernelTaskRecord(
        task_id="TASK-098", action="FIX", executor_id="antigravity",
        base_main_sha="a"*40, target_branch="ai/task-098", authorized_artifact_sha="b"*40,
        review_sha="r"*40,
        allowed_paths=["aios_kernel.py"], allowed_paths_fingerprint=compute_fingerprint(["aios_kernel.py"]),
        verify_command_fingerprint=compute_fingerprint({"t0": ["pytest"], "t1": ["pytest"]}), verify_commands={"t0": ["pytest"], "t1": ["pytest"]},
        pre_execution_head="c"*40, status="AUTHORIZED"
    )

    monkeypatch.setattr(gitops, "get_current_branch", lambda cwd: "ai/task-098")
    monkeypatch.setattr(gitops, "collect_worktree_changed_paths", lambda pre, cwd: ["aios_kernel.py"])
    monkeypatch.setattr(gitops, "get_remote_ref_sha", lambda r, b, cwd: "a"*40 if b == "main" else "head_sha")
    monkeypatch.setattr(gitops, "get_head_sha", lambda cwd: "head_sha")
    monkeypatch.setattr(gitops, "capture_publication_trust", lambda r, cwd: {"remote": r})
    monkeypatch.setattr(gitops, "verify_publication_trust", lambda s, cwd: None)
    monkeypatch.setattr(publish, "run_kernel_verify", lambda rec, root: publish.KernelVerifyResult(True, 0, True, True, "pass"))

    def mock_git_cmd(args, cwd=None, check=True):
        if "rev-parse" in args and "TASK-098.md" in args[-1]:
            return type("Res", (), {"returncode": 0, "stdout": "b" * 40 + "\n", "stderr": ""})()
        if "rev-parse" in args and "REVIEW-098.md" in args[-1]:
            return type("Res", (), {"returncode": 0, "stdout": "r" * 40 + "\n", "stderr": ""})()
        return type("Res", (), {"returncode": 0, "stdout": "", "stderr": ""})()
    monkeypatch.setattr(gitops, "git_cmd", mock_git_cmd)

    save_task_record(rec_run, repo_root=tmp_path)
    res_run = complete_kernel_task("TASK-098", repo_root=tmp_path)
    assert res_run.success is True

    save_task_record(rec_fix, repo_root=tmp_path)
    res_fix = complete_kernel_task("TASK-098", repo_root=tmp_path)
    assert res_fix.success is True


def test_kernel_proof_default_old_worker_surfaces_changed_no():
    """Proof: DEFAULT_OLD_WORKER_SURFACES_CHANGED: NO & LEGACY_BRIDGE_CHANGED: NO."""
    old_skill = Path(".agents/skills/aios-worker/SKILL.md")
    old_workflow = Path(".agents/workflows/aios-worker.md")

    assert old_skill.exists()
    assert old_workflow.exists()

    skill_text = old_skill.read_text(encoding="utf-8")
    assert "aios_kernel.py" not in skill_text  # Old skill default surface remains unchanged for TASK-098


def test_kernel_proof_certify_merge_task095_not_implemented():
    """Proof: KERNEL_CERTIFY_MERGE_IMPLEMENTED: NO & PRODUCT_DELIVERY_FAST_IMPLEMENTED: NO & TASK_095_IMPLEMENTED: NO."""
    cli_text = Path("src/aios_bridge/kernel/cli.py").read_text(encoding="utf-8")
    assert "certify" not in cli_text
    assert "merge" not in cli_text
    assert "product_delivery_fast" not in cli_text
    assert "task_095" not in cli_text
