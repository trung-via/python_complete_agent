from __future__ import annotations

import multiprocessing
import os
import tempfile
from typing import Any

import pytest

from src.core.checkpoint import CheckpointManager
from src.core.checkpoint_contract import CheckpointEvent
from src.core.errors import SystemStateError


def _worker_log_events(db_path: str, run_id: str, count: int) -> None:
    cm = CheckpointManager(db_path=db_path)
    for i in range(count):
        cm.log_run_started(run_id, f"sys_{i}", f"user_{i}")


def test_sequence_auto_increment_per_run() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "checkpoints.jsonl")
        cm = CheckpointManager(db_path=db_path)

        run_a = "run-A"
        run_b = "run-B"

        cm.log_run_started(run_a, "sys_a", "usr_a")  # seq 1
        cm.log_run_started(run_b, "sys_b", "usr_b")  # seq 1
        cm.log_llm_requested(run_a, iteration=1)      # seq 2
        cm.log_llm_requested(run_b, iteration=1)      # seq 2
        cm.log_run_completed(run_a)                  # seq 3

        assert cm._last_sequences[run_a] == 3
        assert cm._last_sequences[run_b] == 2


def test_commit_before_memory_update_write_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "checkpoints.jsonl")
        cm = CheckpointManager(db_path=db_path)
        run_id = "run-fail"

        cm.log_run_started(run_id, "sys", "usr")  # seq 1
        assert cm._last_sequences[run_id] == 1

        original_open = open

        def failing_open(file: Any, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
            if mode == "a" and str(file).endswith("checkpoints.jsonl"):
                raise OSError("simulated disk append failure")
            return original_open(file, mode, *args, **kwargs)

        monkeypatch.setattr("builtins.open", failing_open)

        # Append fails -> raises SystemStateError
        with pytest.raises(SystemStateError, match="Checkpoint write failed"):
            cm.log_llm_requested(run_id, iteration=1)

        # Memory sequence must NOT advance (remains 1)
        assert cm._last_sequences[run_id] == 1


def test_restart_durability_and_reload() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "checkpoints.jsonl")
        cm1 = CheckpointManager(db_path=db_path)
        run_id = "run-restart"

        cm1.log_run_started(run_id, "sys", "usr")
        cm1.log_llm_requested(run_id, iteration=1)
        cm1.log_run_completed(run_id)

        # Restart fresh instance
        cm2 = CheckpointManager(db_path=db_path)
        assert cm2._last_sequences[run_id] == 3


def test_multiprocess_concurrent_event_logging() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "checkpoints.jsonl")

        # Initialize file
        CheckpointManager(db_path=db_path)

        procs: list[multiprocessing.Process] = []
        num_workers = 4
        events_per_worker = 10

        for idx in range(num_workers):
            run_id = f"run-proc-{idx}"
            p = multiprocessing.Process(
                target=_worker_log_events,
                args=(db_path, run_id, events_per_worker),
            )
            procs.append(p)
            p.start()

        for p in procs:
            p.join(timeout=10)
            assert not p.is_alive()
            assert p.exitcode == 0

        # Verify all events logged cleanly
        cm_check = CheckpointManager(db_path=db_path)

        for idx in range(num_workers):
            run_id = f"run-proc-{idx}"
            assert cm_check._last_sequences[run_id] == events_per_worker
