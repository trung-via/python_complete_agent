"""Tests for AIOS Bridge Kernel v1 CLI Entry Point (ADR-068 / TASK-098)."""

import pytest
import sys
import json
from pathlib import Path

from src.aios_bridge.kernel.cli import main
from src.aios_bridge.kernel.model import KernelTaskRecord, save_task_record


def test_cli_status(tmp_path, monkeypatch, capsys):
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
        verify_commands={"t0": ["pytest"]},
        pre_execution_head="c" * 40,
        status="AUTHORIZED",
    )
    save_task_record(record, repo_root=tmp_path)
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(sys, "argv", ["aios_kernel", "status", "TASK-098"])
    main()

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["task_id"] == "TASK-098"
    assert data["status"] == "AUTHORIZED"


def test_cli_cancel(tmp_path, monkeypatch, capsys):
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
        verify_commands={"t0": ["pytest"]},
        pre_execution_head="c" * 40,
        status="AUTHORIZED",
    )
    save_task_record(record, repo_root=tmp_path)
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(sys, "argv", ["aios_kernel", "cancel", "TASK-098"])
    main()

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["status"] == "CANCELLED"
    assert data["task_id"] == "TASK-098"
