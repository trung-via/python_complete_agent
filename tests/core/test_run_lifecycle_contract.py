from __future__ import annotations

import os
import tempfile

import pytest

from src.core.checkpoint import CheckpointManager
from src.core.checkpoint_contract import (
    CheckpointStateError,
    FailureDomain,
    RunState,
    RunSummary,
)


def test_failure_domain_enum_values() -> None:
    domains = {fd.value for fd in FailureDomain}
    expected = {
        "USER_APP",
        "LLM_PROVIDER",
        "TOOL_EXECUTION",
        "CHECKPOINT_STORE",
        "CORRUPTION_INTEGRITY",
        "PROCESS_CRASH",
    }
    assert domains == expected


def test_terminal_state_immutability_completed() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "checkpoints.jsonl")
        cm = CheckpointManager(db_path=db_path)
        run_id = "run-term-comp"

        cm.log_run_started(run_id, "sys", "usr")
        cm.log_llm_requested(run_id, iteration=1)
        cm.log_llm_responded(run_id, iteration=1, content="Done!", num_tool_calls=0)

        # State is now COMPLETED
        assert cm._last_states[run_id] == RunState.COMPLETED

        # Any late event append attempt must raise CheckpointStateError
        with pytest.raises(CheckpointStateError, match="cannot process event"):
            cm.log_llm_requested(run_id, iteration=2)


def test_terminal_state_immutability_failed_and_halted() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "checkpoints.jsonl")
        cm = CheckpointManager(db_path=db_path)

        run_fail = "run-fail"
        cm.log_run_started(run_fail, "sys", "usr")
        cm.log_run_failed(run_fail, error="Provider error")
        assert cm._last_states[run_fail] == RunState.FAILED

        with pytest.raises(CheckpointStateError):
            cm.log_llm_requested(run_fail, iteration=1)

        run_halt = "run-halt"
        cm.log_run_started(run_halt, "sys", "usr")
        cm.log_run_halted(run_halt, reason="timeout")
        assert cm._last_states[run_halt] == RunState.HALTED

        with pytest.raises(CheckpointStateError):
            cm.log_run_completed(run_halt)


def test_get_run_summary() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "checkpoints.jsonl")
        cm = CheckpointManager(db_path=db_path)
        run_id = "run-summary-test"

        cm.log_run_started(run_id, "sys", "usr")
        cm.log_llm_requested(run_id, iteration=1)
        cm.log_llm_responded(
            run_id, iteration=1, content="tooling", num_tool_calls=2
        )
        cm.log_tool_result_received(run_id, "c1", status="success", iteration_complete=True)
        cm.log_llm_requested(run_id, iteration=2)
        cm.log_llm_responded(run_id, iteration=2, content="All complete", num_tool_calls=0)

        summary = cm.get_run_summary(run_id)
        assert summary is not None
        assert summary.run_id == run_id
        assert summary.final_state == RunState.COMPLETED
        assert summary.iteration_count == 2
        assert summary.tool_call_count == 2
        assert summary.start_timestamp > 0
        assert summary.end_timestamp is not None
        assert summary.end_timestamp >= summary.start_timestamp
