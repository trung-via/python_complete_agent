"""Tests for AIOS Bridge Kernel v1 Context Generator (ADR-068 / TASK-098)."""

import pytest
from pathlib import Path

from src.aios_bridge.kernel.model import KernelTaskRecord, save_task_record
from src.aios_bridge.kernel.context import get_compact_context, KernelContextError


def test_get_compact_context_bounded_fields(tmp_path):
    """Proof: CONTEXT_FIELD_SET_BOUNDED: PASS."""
    record = KernelTaskRecord(
        task_id="TASK-098",
        action="RUN",
        executor_id="antigravity",
        base_main_sha="a" * 40,
        target_branch="ai/task-098",
        authorized_artifact_sha="b" * 40,
        allowed_paths=["aios_kernel.py", "bridge.py"],
        allowed_paths_fingerprint="fp1",
        verify_command_fingerprint="fp2",
        verify_commands={"t0": ["pytest"]},
        pre_execution_head="c" * 40,
        status="AUTHORIZED",
    )
    save_task_record(record, repo_root=tmp_path)

    ctx = get_compact_context("TASK-098", repo_root=tmp_path)

    assert ctx["task_id"] == "TASK-098"
    assert ctx["action"] == "RUN"
    assert ctx["executor_id"] == "antigravity"
    assert ctx["target_branch"] == "ai/task-098"
    assert ctx["base_main_sha"] == "a" * 40
    assert ctx["task_file"] == ".ai/tasks/TASK-098.md"
    assert ctx["review_file"] is None
    assert ctx["allowed_paths"] == ["aios_kernel.py", "bridge.py"]
    assert ctx["bounded_semantic_refs"] == [".ai/tasks/TASK-098.md"]

    # Ensure no internal diagnostics or extra fields leaked
    forbidden_keys = {"lease_id", "lease_fingerprint", "execution_fingerprint", "manifest", "roadmap_body"}
    assert forbidden_keys.isdisjoint(ctx.keys())
