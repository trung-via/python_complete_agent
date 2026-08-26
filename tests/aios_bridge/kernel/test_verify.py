"""Tests for AIOS Bridge Kernel v1 Deterministic VERIFY Pipeline (ADR-068 / TASK-098)."""

import pytest
import subprocess
from pathlib import Path

from src.aios_bridge.kernel.model import KernelTaskRecord
from src.aios_bridge.kernel.verify import run_kernel_verify, KernelVerifyResult


def test_run_kernel_verify_t0_t1_invocation_counts(tmp_path, monkeypatch):
    """Proof: T0_AUTHORITATIVE_INVOCATION_COUNT_PER_COMPLETE: 1 & T1_AUTHORITATIVE_INVOCATION_COUNT_PER_COMPLETE: 1."""
    record = KernelTaskRecord(
        task_id="TASK-098",
        action="RUN",
        executor_id="antigravity",
        base_main_sha="a" * 40,
        target_branch="ai/task-098",
        authorized_artifact_sha="b" * 40,
        allowed_paths=["aios_kernel.py"],
        allowed_paths_fingerprint="fp1",
        verify_command_fingerprint="fp2",
        verify_commands={
            "t0": ["t0_cmd_1", "t0_cmd_2"],
            "t1": ["t1_cmd_1"],
        },
        pre_execution_head="c" * 40,
        status="AUTHORIZED",
    )

    t0_calls = []
    t1_calls = []

    import src.aios_bridge.kernel.verify as verify_mod

    def mock_run_cmd(cmd_array, cwd):
        if "t0_cmd_1" in cmd_array:
            t0_calls.append(cmd_array)
            return subprocess.CompletedProcess(cmd_array, 0, "t0 pass", "")
        if "t1_cmd_1" in cmd_array:
            t1_calls.append(cmd_array)
            return subprocess.CompletedProcess(cmd_array, 0, "t1 pass", "")
        return subprocess.CompletedProcess(cmd_array, 0, "", "")

    monkeypatch.setattr(verify_mod, "run_command_array", mock_run_cmd)

    res = run_kernel_verify(record, repo_root=tmp_path)

    assert res.passed is True
    assert len(t0_calls) == 1
    assert len(t1_calls) == 1
    assert res.t0_executed is True
    assert res.t1_executed is True


def test_run_kernel_verify_t0_failure_stops_before_t1(tmp_path, monkeypatch):
    """Proof: If T0 fails, T1 is NOT executed."""
    record = KernelTaskRecord(
        task_id="TASK-098",
        action="RUN",
        executor_id="antigravity",
        base_main_sha="a" * 40,
        target_branch="ai/task-098",
        authorized_artifact_sha="b" * 40,
        allowed_paths=["aios_kernel.py"],
        allowed_paths_fingerprint="fp1",
        verify_command_fingerprint="fp2",
        verify_commands={
            "t0": ["t0_cmd_failing"],
            "t1": ["t1_cmd_never_reached"],
        },
        pre_execution_head="c" * 40,
        status="AUTHORIZED",
    )

    t0_calls = []
    t1_calls = []

    import src.aios_bridge.kernel.verify as verify_mod

    def mock_run_cmd(cmd_array, cwd):
        if "t0_cmd_failing" in cmd_array:
            t0_calls.append(cmd_array)
            return subprocess.CompletedProcess(cmd_array, 1, "t0 fail", "error")
        if "t1_cmd_never_reached" in cmd_array:
            t1_calls.append(cmd_array)
            return subprocess.CompletedProcess(cmd_array, 0, "", "")
        return subprocess.CompletedProcess(cmd_array, 0, "", "")

    monkeypatch.setattr(verify_mod, "run_command_array", mock_run_cmd)

    res = run_kernel_verify(record, repo_root=tmp_path)

    assert res.passed is False
    assert res.exit_code == 1
    assert len(t0_calls) == 1
    assert len(t1_calls) == 0
    assert res.t0_executed is True
    assert res.t1_executed is False
