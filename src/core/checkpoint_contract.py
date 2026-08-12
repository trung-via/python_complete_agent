from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class RunState(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    LLM_WAITING = "LLM_WAITING"
    TOOL_EXECUTING = "TOOL_EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    HALTED = "HALTED"


class CheckpointEventType(str, Enum):
    TASK_START = "TASK_START"
    RUN_STARTED = "RUN_STARTED"
    LLM_REQUESTED = "LLM_REQUESTED"
    LLM_RESPONDED = "LLM_RESPONDED"
    TOOL_CALL_CREATED = "TOOL_CALL_CREATED"
    TOOL_ATTEMPT_STARTED = "TOOL_ATTEMPT_STARTED"
    TOOL_ATTEMPT_ENDED = "TOOL_ATTEMPT_ENDED"
    TOOL_RESULT_RECEIVED = "TOOL_RESULT_RECEIVED"
    TOOL_CALL_REJECTED = "TOOL_CALL_REJECTED"
    LLM_FINAL_RESPONSE = "LLM_FINAL_RESPONSE"
    RUN_COMPLETED = "RUN_COMPLETED"
    RUN_FAILED = "RUN_FAILED"
    RUN_HALTED = "RUN_HALTED"
    TASK_END = "TASK_END"


class CheckpointCorruptionError(Exception):
    """Raised when a checkpoint line/event is malformed or breaks per-run sequence/timestamp monotonicity."""

    def __init__(self, run_id: str, message: str) -> None:
        self.run_id = run_id
        self.message = message
        super().__init__(f"Corrupt checkpoint event for run '{run_id}': {message}")


class CheckpointStateError(Exception):
    """Raised when a valid event attempts an illegal state machine transition."""

    def __init__(
        self,
        run_id: str,
        current_state: RunState,
        attempted_event: CheckpointEventType,
    ) -> None:
        self.run_id = run_id
        self.current_state = current_state
        self.attempted_event = attempted_event
        super().__init__(
            f"Invalid checkpoint state transition for run '{run_id}': "
            f"cannot process event {attempted_event.value!r} while in state {current_state.value!r}"
        )


@dataclass(frozen=True)
class CheckpointEvent:
    run_id: str
    sequence_id: int
    timestamp: float
    event_type: CheckpointEventType
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "run_id": self.run_id,
            "sequence_id": self.sequence_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type.value,
            "event": self.event_type.value,
            "payload": self.payload,
        }
        if isinstance(self.payload, dict):
            for k, v in self.payload.items():
                if k not in d:
                    d[k] = v
        return d

    @classmethod
    def from_dict(cls, data: Any, line_number: Optional[int] = None) -> CheckpointEvent:
        prefix = f"<line:{line_number}> " if line_number is not None else ""

        if not isinstance(data, dict):
            raise CheckpointCorruptionError(
                "<unknown>",
                f"{prefix}Expected JSON object, got {type(data).__name__}",
            )

        required = {"run_id", "sequence_id", "timestamp", "event_type"}
        missing = required.difference(data)
        if missing:
            raise CheckpointCorruptionError(
                str(data.get("run_id", "<unknown>")),
                f"{prefix}Missing required fields: {sorted(missing)}",
            )

        run_id = data["run_id"]
        if not isinstance(run_id, str) or not run_id.strip():
            raise CheckpointCorruptionError(
                str(run_id),
                f"{prefix}run_id must be a non-empty string",
            )

        sequence_id = data["sequence_id"]
        if isinstance(sequence_id, bool) or not isinstance(sequence_id, int):
            raise CheckpointCorruptionError(
                run_id,
                f"{prefix}sequence_id must be an integer, got {type(sequence_id).__name__}",
            )
        if sequence_id < 1:
            raise CheckpointCorruptionError(
                run_id,
                f"{prefix}sequence_id must be >= 1, got {sequence_id}",
            )

        timestamp = data["timestamp"]
        if isinstance(timestamp, bool) or not isinstance(timestamp, (int, float)):
            raise CheckpointCorruptionError(
                run_id,
                f"{prefix}timestamp must be a number, got {type(timestamp).__name__}",
            )

        raw_event_type = data["event_type"]
        try:
            event_type = CheckpointEventType(raw_event_type)
        except (TypeError, ValueError):
            raise CheckpointCorruptionError(
                run_id,
                f"{prefix}Invalid event_type: {raw_event_type!r}",
            )

        payload = data.get("payload", {})
        if payload is None:
            payload = {}
        elif not isinstance(payload, dict):
            raise CheckpointCorruptionError(
                run_id,
                f"{prefix}payload must be a JSON object, got {type(payload).__name__}",
            )

        return cls(
            run_id=run_id,
            sequence_id=sequence_id,
            timestamp=float(timestamp),
            event_type=event_type,
            payload=payload,
        )


@dataclass
class ReconstructedSession:
    run_id: str
    system_prompt: str = ""
    user_prompt: str = ""
    messages: List[Dict[str, Any]] = field(default_factory=list)
    last_state: RunState = RunState.PENDING
    completed_tool_calls: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    pending_tool_calls: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    next_sequence_id: int = 1
    last_event: Optional[CheckpointEvent] = None


def validate_event_sequence(events: List[CheckpointEvent]) -> None:
    """
    Validate per-run sequence_id and timestamp monotonicity across events.

    Events can contain multiple runs interleaved, but per run_id:
    - sequence_id must start at 1 and increment strictly by +1.
    - timestamp must be non-decreasing (monotonic per run).
    """
    last_sequence: Dict[str, int] = {}
    last_timestamp: Dict[str, float] = {}

    for event in events:
        run_id = event.run_id
        seq = event.sequence_id
        ts = event.timestamp

        if run_id not in last_sequence:
            if seq != 1:
                raise CheckpointCorruptionError(
                    run_id,
                    f"First sequence_id for run must be 1, got {seq}",
                )
        else:
            prev_seq = last_sequence[run_id]
            if seq == prev_seq:
                raise CheckpointCorruptionError(
                    run_id,
                    f"Duplicate sequence_id {seq} for run",
                )
            if seq < prev_seq:
                raise CheckpointCorruptionError(
                    run_id,
                    f"Sequence_id rollback for run (previous: {prev_seq}, current: {seq})",
                )
            if seq > prev_seq + 1:
                raise CheckpointCorruptionError(
                    run_id,
                    f"Sequence_id gap for run (expected: {prev_seq + 1}, got: {seq})",
                )

            prev_ts = last_timestamp[run_id]
            if ts < prev_ts:
                raise CheckpointCorruptionError(
                    run_id,
                    f"Timestamp rollback for run (previous: {prev_ts}, current: {ts})",
                )

        last_sequence[run_id] = seq
        last_timestamp[run_id] = ts


def validate_state_transition(
    current_state: RunState,
    event: CheckpointEvent,
) -> RunState:
    """
    Validate state transition for a valid event against current_state.

    Returns the new RunState after applying event.
    Raises CheckpointStateError if the transition is illegal.
    """
    evt_type = event.event_type

    # Terminal states reject any further state transitions
    if current_state in (RunState.COMPLETED, RunState.FAILED, RunState.HALTED):
        raise CheckpointStateError(event.run_id, current_state, evt_type)

    if current_state == RunState.PENDING:
        if evt_type in (CheckpointEventType.TASK_START, CheckpointEventType.RUN_STARTED):
            return RunState.RUNNING
        raise CheckpointStateError(event.run_id, current_state, evt_type)

    if current_state == RunState.RUNNING:
        if evt_type == CheckpointEventType.LLM_REQUESTED:
            return RunState.LLM_WAITING
        if evt_type == CheckpointEventType.RUN_FAILED:
            return RunState.FAILED
        if evt_type == CheckpointEventType.RUN_HALTED:
            return RunState.HALTED
        raise CheckpointStateError(event.run_id, current_state, evt_type)

    if current_state == RunState.LLM_WAITING:
        if evt_type == CheckpointEventType.LLM_RESPONDED:
            num_tool_calls = event.payload.get("num_tool_calls", 0)
            if num_tool_calls > 0:
                return RunState.TOOL_EXECUTING
            return RunState.COMPLETED
        if evt_type == CheckpointEventType.LLM_FINAL_RESPONSE:
            return RunState.COMPLETED
        if evt_type == CheckpointEventType.RUN_FAILED:
            return RunState.FAILED
        if evt_type == CheckpointEventType.RUN_HALTED:
            return RunState.HALTED
        raise CheckpointStateError(event.run_id, current_state, evt_type)

    if current_state == RunState.TOOL_EXECUTING:
        if evt_type in (
            CheckpointEventType.TOOL_CALL_CREATED,
            CheckpointEventType.TOOL_ATTEMPT_STARTED,
            CheckpointEventType.TOOL_ATTEMPT_ENDED,
            CheckpointEventType.TOOL_CALL_REJECTED,
        ):
            return RunState.TOOL_EXECUTING
        if evt_type == CheckpointEventType.TOOL_RESULT_RECEIVED:
            # Check if all tools in iteration are complete or transitioning back to LLM_WAITING
            is_iteration_complete = event.payload.get("iteration_complete", True)
            if is_iteration_complete:
                return RunState.LLM_WAITING
            return RunState.TOOL_EXECUTING
        if evt_type == CheckpointEventType.RUN_COMPLETED:
            return RunState.COMPLETED
        if evt_type == CheckpointEventType.RUN_FAILED:
            return RunState.FAILED
        if evt_type == CheckpointEventType.RUN_HALTED:
            return RunState.HALTED
        raise CheckpointStateError(event.run_id, current_state, evt_type)

    raise CheckpointStateError(event.run_id, current_state, evt_type)
