"""Tests for AIOS Bridge Kernel v1 Data Models (ADR-068 / TASK-098)."""

import pytest
import tempfile
from pathlib import Path

from src.aios_bridge.kernel.model import (
    KernelTaskRecord,
    KernelStatus,
    KernelAction,
    KernelExecutor,
    compute_fingerprint,
    save_task_record,
    load_task_record,
)


def test_kernel_task_record_serialization():
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

    data = record.to_dict()
    restored = KernelTaskRecord.from_dict(data)

    assert restored.task_id == "TASK-098"
    assert restored.action == "RUN"
    assert restored.executor_id == "antigravity"
    assert restored.allowed_paths == ["aios_kernel.py", "bridge.py"]
    assert restored.status == KernelStatus.AUTHORIZED.value


def test_kernel_task_record_persistence(tmp_path):
    record = KernelTaskRecord(
        task_id="TASK-098",
        action="FIX",
        executor_id="codex",
        base_main_sha="1" * 40,
        target_branch="ai/task-098",
        authorized_artifact_sha="2" * 40,
        review_sha="3" * 40,
        allowed_paths=["aios_kernel.py"],
        allowed_paths_fingerprint="fp_allowed",
        verify_command_fingerprint="fp_verify",
        verify_commands={"t0": ["pytest t0"], "t1": ["pytest t1"]},
        pre_execution_head="4" * 40,
        status="AUTHORIZED",
    )

    save_task_record(record, repo_root=tmp_path)
    loaded = load_task_record("TASK-098", repo_root=tmp_path)

    assert loaded is not None
    assert loaded.task_id == "TASK-098"
    assert loaded.action == "FIX"
    assert loaded.executor_id == "codex"
    assert loaded.review_sha == "3" * 40
    assert loaded.verify_commands == {"t0": ["pytest t0"], "t1": ["pytest t1"]}


def test_compute_fingerprint():
    fp1 = compute_fingerprint(["path1", "path2"])
    fp2 = compute_fingerprint(["path1", "path2"])
    fp3 = compute_fingerprint(["path2", "path1"])

    assert fp1 == fp2
    assert fp1 != fp3
