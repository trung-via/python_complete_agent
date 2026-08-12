from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from typing import Any, Dict, List, Optional

from src.agent.replay_engine import ReplayEngine
from src.core.checkpoint_contract import (
    CheckpointCorruptionError,
    CheckpointEvent,
    CheckpointEventType,
    CheckpointStateError,
    RunState,
    validate_event_sequence,
    validate_state_transition,
)
from src.core.idempotency_contract import RecordKey, RecordStatus
from src.core.idempotency_store_v2 import JsonlIdempotencyStore


@dataclass
class RunIntegrityReport:
    run_id: str
    valid: bool
    state: RunState = RunState.PENDING
    checkpoint_count: int = 0
    pending_tool_calls: int = 0
    completed_tool_calls: int = 0
    issues: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "valid": self.valid,
            "state": self.state.value,
            "checkpoint_count": self.checkpoint_count,
            "pending_tool_calls": self.pending_tool_calls,
            "completed_tool_calls": self.completed_tool_calls,
            "issues": list(self.issues),
        }


class RunIntegrityVerifier:
    """
    Read-only verification engine that audits checkpoint sequence, timestamp monotonicity,
    state-machine transitions, tool-call tracking, and optional idempotency-store consistency.

    Strictly read-only: never modifies or mutates the filesystem.
    """

    @staticmethod
    def verify(
        db_path: str,
        run_id: str,
        idempotency_store: Optional[JsonlIdempotencyStore] = None,
    ) -> RunIntegrityReport:
        issues: List[str] = []

        if not os.path.exists(db_path):
            return RunIntegrityReport(
                run_id=run_id,
                valid=False,
                issues=[f"Checkpoint database file does not exist: {db_path}"],
            )

        events: List[CheckpointEvent] = []

        # Audit 1: JSON Syntax Integrity
        try:
            with open(db_path, "r", encoding="utf-8") as f:
                for line_idx, line in enumerate(f, start=1):
                    stripped = line.strip()
                    if not stripped:
                        continue
                    try:
                        data = json.loads(stripped)
                        if isinstance(data, dict) and data.get("run_id") == run_id:
                            evt = CheckpointEvent.from_dict(data, line_number=line_idx)
                            events.append(evt)
                    except json.JSONDecodeError as exc:
                        issues.append(f"Line {line_idx}: Invalid JSON syntax: {exc}")
                    except CheckpointCorruptionError as exc:
                        issues.append(f"Line {line_idx}: {exc.message}")
        except Exception as exc:
            return RunIntegrityReport(
                run_id=run_id,
                valid=False,
                issues=[f"Failed to read checkpoint file: {exc}"],
            )

        if not events:
            return RunIntegrityReport(
                run_id=run_id,
                valid=False,
                issues=[f"No checkpoint events found for run_id: '{run_id}'"],
            )

        # Audit 2: Sequence Continuity & Timestamp Monotonicity
        try:
            validate_event_sequence(events)
        except CheckpointCorruptionError as exc:
            issues.append(f"Sequence/Timestamp validation error: {exc.message}")

        # Audit 3: State Machine Transition Validity
        curr_state = RunState.PENDING
        for evt in events:
            try:
                curr_state = validate_state_transition(curr_state, evt)
            except CheckpointStateError as exc:
                issues.append(f"State transition error: {exc}")
                break

        # Audit 4 & 5: Session Reconstruction & Pending/Completed Tool Call Consistency
        pending_count = 0
        completed_count = 0
        try:
            session = ReplayEngine.reconstruct_session(db_path, run_id)
            pending_count = len(session.pending_tool_calls)
            completed_count = len(session.completed_tool_calls)

            # Verification check: If state is COMPLETED, pending_tool_calls must be 0
            if session.last_state == RunState.COMPLETED and pending_count > 0:
                issues.append(
                    f"Session in COMPLETED state has {pending_count} unhandled pending tool call(s)"
                )
        except Exception as exc:
            issues.append(f"ReplayEngine session reconstruction failed: {exc}")

        # Audit 6: Cross-verification with IdempotencyStore if provided
        if idempotency_store is not None:
            try:
                snapshot = idempotency_store.get_all_records()
                for cid, tool_result in session.completed_tool_calls.items():
                    target_scope = f"tool:{tool_result.tool_name}" if tool_result.tool_name else ""
                    matching_records = [
                        rec
                        for k, rec in snapshot.items()
                        if (not target_scope or k.operation_key == target_scope)
                        and rec.status == RecordStatus.COMPLETED
                    ]
                    if not matching_records:
                        issues.append(
                            f"Completed tool call '{cid}' ({tool_result.tool_name}) missing COMPLETED record in IdempotencyStore"
                        )
            except Exception as exc:
                issues.append(f"IdempotencyStore cross-verification error: {exc}")

        is_valid = len(issues) == 0
        return RunIntegrityReport(
            run_id=run_id,
            valid=is_valid,
            state=curr_state,
            checkpoint_count=len(events),
            pending_tool_calls=pending_count,
            completed_tool_calls=completed_count,
            issues=issues,
        )
