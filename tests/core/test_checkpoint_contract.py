from __future__ import annotations

from typing import Any, Dict

import pytest

from src.core.checkpoint_contract import (
    CheckpointCorruptionError,
    CheckpointEvent,
    CheckpointEventType,
    CheckpointStateError,
    ReconstructedSession,
    RunState,
    validate_event_sequence,
    validate_state_transition,
)


def _make_event(
    run_id: str = "run-1",
    seq: int = 1,
    ts: float = 100.0,
    evt_type: CheckpointEventType = CheckpointEventType.RUN_STARTED,
    payload: Dict[str, Any] | None = None,
) -> CheckpointEvent:
    return CheckpointEvent(
        run_id=run_id,
        sequence_id=seq,
        timestamp=ts,
        event_type=evt_type,
        payload=payload or {},
    )


def test_event_serialization_roundtrip() -> None:
    evt = _make_event(
        run_id="run-test-1",
        seq=1,
        ts=1700000000.0,
        evt_type=CheckpointEventType.RUN_STARTED,
        payload={"system_prompt": "sys", "user_prompt": "usr"},
    )

    d = evt.to_dict()
    restored = CheckpointEvent.from_dict(d)

    assert restored == evt
    assert restored.run_id == "run-test-1"
    assert restored.sequence_id == 1
    assert restored.timestamp == 1700000000.0
    assert restored.event_type == CheckpointEventType.RUN_STARTED
    assert restored.payload == {"system_prompt": "sys", "user_prompt": "usr"}


def test_malformed_events_raise_corruption_error() -> None:
    # Not a dict
    with pytest.raises(CheckpointCorruptionError, match="Expected JSON object"):
        CheckpointEvent.from_dict("not-a-dict")

    # Missing fields
    with pytest.raises(CheckpointCorruptionError, match="Missing required fields"):
        CheckpointEvent.from_dict({"run_id": "r1", "sequence_id": 1})

    # Empty run_id
    with pytest.raises(CheckpointCorruptionError, match="run_id must be a non-empty string"):
        CheckpointEvent.from_dict(
            {"run_id": "", "sequence_id": 1, "timestamp": 100.0, "event_type": "RUN_STARTED"}
        )

    # Bool or invalid sequence_id
    with pytest.raises(CheckpointCorruptionError, match="sequence_id must be an integer"):
        CheckpointEvent.from_dict(
            {"run_id": "r1", "sequence_id": True, "timestamp": 100.0, "event_type": "RUN_STARTED"}
        )

    # Negative sequence_id
    with pytest.raises(CheckpointCorruptionError, match="sequence_id must be >= 1"):
        CheckpointEvent.from_dict(
            {"run_id": "r1", "sequence_id": 0, "timestamp": 100.0, "event_type": "RUN_STARTED"}
        )

    # Invalid timestamp
    with pytest.raises(CheckpointCorruptionError, match="timestamp must be a number"):
        CheckpointEvent.from_dict(
            {"run_id": "r1", "sequence_id": 1, "timestamp": "invalid", "event_type": "RUN_STARTED"}
        )

    # Invalid event_type
    with pytest.raises(CheckpointCorruptionError, match="Invalid event_type"):
        CheckpointEvent.from_dict(
            {"run_id": "r1", "sequence_id": 1, "timestamp": 100.0, "event_type": "UNKNOWN_EVT"}
        )


def test_per_run_sequence_isolation() -> None:
    events = [
        _make_event(run_id="run-A", seq=1, ts=100.0, evt_type=CheckpointEventType.RUN_STARTED),
        _make_event(run_id="run-B", seq=1, ts=101.0, evt_type=CheckpointEventType.RUN_STARTED),
        _make_event(run_id="run-A", seq=2, ts=102.0, evt_type=CheckpointEventType.LLM_REQUESTED),
        _make_event(run_id="run-B", seq=2, ts=103.0, evt_type=CheckpointEventType.LLM_REQUESTED),
        _make_event(run_id="run-A", seq=3, ts=104.0, evt_type=CheckpointEventType.LLM_RESPONDED),
    ]

    # Interleaved runs A (seq 1, 2, 3) and B (seq 1, 2) must pass validation
    validate_event_sequence(events)


def test_sequence_gap_rejected() -> None:
    events = [
        _make_event(run_id="run-A", seq=1, ts=100.0),
        _make_event(run_id="run-A", seq=3, ts=101.0),  # Gap: 1 -> 3
    ]

    with pytest.raises(CheckpointCorruptionError, match="Sequence_id gap for run"):
        validate_event_sequence(events)


def test_sequence_duplicate_rejected() -> None:
    events = [
        _make_event(run_id="run-A", seq=1, ts=100.0),
        _make_event(run_id="run-A", seq=1, ts=101.0),  # Duplicate seq 1
    ]

    with pytest.raises(CheckpointCorruptionError, match="Duplicate sequence_id 1"):
        validate_event_sequence(events)


def test_sequence_rollback_rejected() -> None:
    events = [
        _make_event(run_id="run-A", seq=1, ts=100.0),
        _make_event(run_id="run-A", seq=2, ts=101.0),
        _make_event(run_id="run-A", seq=1, ts=102.0),  # Rollback seq 2 -> 1
    ]

    with pytest.raises(CheckpointCorruptionError, match="Sequence_id rollback for run"):
        validate_event_sequence(events)


def test_timestamp_rollback_rejected() -> None:
    events = [
        _make_event(run_id="run-A", seq=1, ts=100.0),
        _make_event(run_id="run-A", seq=2, ts=99.0),  # Timestamp rollback 100.0 -> 99.0
    ]

    with pytest.raises(CheckpointCorruptionError, match="Timestamp rollback for run"):
        validate_event_sequence(events)


def test_valid_state_transitions() -> None:
    state = RunState.PENDING

    # RUN_STARTED -> RUNNING
    state = validate_state_transition(state, _make_event(evt_type=CheckpointEventType.RUN_STARTED))
    assert state == RunState.RUNNING

    # LLM_REQUESTED -> LLM_WAITING
    state = validate_state_transition(state, _make_event(evt_type=CheckpointEventType.LLM_REQUESTED))
    assert state == RunState.LLM_WAITING

    # LLM_RESPONDED (with tool calls) -> TOOL_EXECUTING
    state = validate_state_transition(
        state,
        _make_event(evt_type=CheckpointEventType.LLM_RESPONDED, payload={"num_tool_calls": 2}),
    )
    assert state == RunState.TOOL_EXECUTING

    # TOOL_RESULT_RECEIVED (iteration_complete=True) -> LLM_WAITING
    state = validate_state_transition(
        state,
        _make_event(evt_type=CheckpointEventType.TOOL_RESULT_RECEIVED, payload={"iteration_complete": True}),
    )
    assert state == RunState.LLM_WAITING

    # LLM_RESPONDED (no tool calls) -> COMPLETED
    state = validate_state_transition(
        state,
        _make_event(evt_type=CheckpointEventType.LLM_RESPONDED, payload={"num_tool_calls": 0}),
    )
    assert state == RunState.COMPLETED


def test_invalid_state_transition_raises_state_error() -> None:
    # Cannot jump from PENDING directly to TOOL_RESULT_RECEIVED
    with pytest.raises(CheckpointStateError, match="cannot process event 'TOOL_RESULT_RECEIVED' while in state 'PENDING'"):
        validate_state_transition(RunState.PENDING, _make_event(evt_type=CheckpointEventType.TOOL_RESULT_RECEIVED))

    # Cannot transition out of terminal COMPLETED state
    with pytest.raises(CheckpointStateError, match="cannot process event 'LLM_REQUESTED' while in state 'COMPLETED'"):
        validate_state_transition(RunState.COMPLETED, _make_event(evt_type=CheckpointEventType.LLM_REQUESTED))


def test_reconstructed_session_default_contract() -> None:
    session = ReconstructedSession(run_id="run-123")
    assert session.run_id == "run-123"
    assert session.last_state == RunState.PENDING
    assert session.next_sequence_id == 1
    assert session.messages == []
    assert session.completed_tool_calls == {}
    assert session.pending_tool_calls == {}
