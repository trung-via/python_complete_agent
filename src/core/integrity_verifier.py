from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any, Dict, List, Optional, Tuple

from src.agent.replay_engine import ReplayEngine
from src.core.checkpoint_contract import (
    CheckpointCorruptionError,
    CheckpointEvent,
    CheckpointStateError,
    RunState,
    validate_event_sequence,
    validate_state_transition,
)
from src.core.idempotency_contract import RecordStatus
from src.core.idempotency_store_v2 import JsonlIdempotencyStore
from src.core.recovery_diagnostics import RecoveryAnalyzer, RecoveryPotential


@dataclass(frozen=True)
class RunIntegrityReport:
    """
    Immutable audit report for a run's checkpoint integrity and state.
    """

    run_id: str
    valid: bool
    state: RunState = RunState.PENDING
    checkpoint_count: int = 0
    pending_tool_calls: int = 0
    completed_tool_calls: int = 0
    recovery_potential: Optional[RecoveryPotential] = None
    issues: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "valid": self.valid,
            "state": self.state.value,
            "checkpoint_count": self.checkpoint_count,
            "pending_tool_calls": self.pending_tool_calls,
            "completed_tool_calls": self.completed_tool_calls,
            "recovery_potential": self.recovery_potential.value
            if self.recovery_potential
            else None,
            "issues": list(self.issues),
        }


class RunIntegrityVerifier:
    """
    Read-only verification engine for auditing agent run integrity.

    Strictly read-only: never modifies, appends, or repairs files.
    - Session integrity errors (corrupt JSON, sequence gaps, invalid state transitions,
      terminal inconsistencies) result in `RunIntegrityReport(valid=False, issues=...)`.
    - Infrastructure / IO errors (file not found, permission denied, OSError) raise exceptions.
    """

    @staticmethod
    def verify(
        db_path: str,
        run_id: str,
        idempotency_store: Optional[JsonlIdempotencyStore] = None,
    ) -> RunIntegrityReport:
        # Step 1: Infrastructure check. Non-existent file or IO error raises exception directly.
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Checkpoint store file does not exist: {db_path}")

        issues: List[str] = []

        # Step 2: Read physical log and parse JSON/Checkpoint events
        all_events: List[CheckpointEvent] = []
        target_events: List[CheckpointEvent] = []

        try:
            with open(db_path, "r", encoding="utf-8") as handle:
                for line_number, line in enumerate(handle, start=1):
                    stripped = line.strip()
                    if not stripped:
                        continue

                    try:
                        data = json.loads(stripped)
                    except json.JSONDecodeError as exc:
                        issues.append(f"Line {line_number}: Invalid JSON syntax: {exc.msg}")
                        continue

                    try:
                        evt = CheckpointEvent.from_dict(data, line_number=line_number)
                        all_events.append(evt)
                        if evt.run_id == run_id:
                            target_events.append(evt)
                    except CheckpointCorruptionError as exc:
                        issues.append(f"Line {line_number}: {exc.message}")

        except (OSError, PermissionError) as exc:
            # Infrastructure/IO failures are propagated directly as per contract
            raise exc

        if not target_events:
            issues.append(f"No checkpoint events found for run_id: '{run_id}'")
            return RunIntegrityReport(
                run_id=run_id,
                valid=False,
                issues=tuple(issues),
            )

        # Step 3: Sequence continuity & timestamp monotonicity across physical file
        if all_events:
            try:
                validate_event_sequence(all_events)
            except CheckpointCorruptionError as exc:
                issues.append(f"Sequence/Timestamp corruption: {exc.message}")

        # Step 4: State Machine transition validity for target_events
        curr_state = RunState.PENDING
        for evt in target_events:
            try:
                curr_state = validate_state_transition(curr_state, evt)
            except CheckpointStateError as exc:
                issues.append(f"State transition error: {exc}")
                break

        # Step 5: Session reconstruction & tool call consistency
        pending_count = 0
        completed_count = 0
        session = None
        try:
            session = ReplayEngine.reconstruct_session(db_path, run_id)
            pending_count = len(session.pending_tool_calls)
            completed_count = len(session.completed_tool_calls)

            # Terminal consistency check: COMPLETED state must not have pending tool calls
            if session.last_state == RunState.COMPLETED and pending_count > 0:
                issues.append(
                    f"Session in COMPLETED state has {pending_count} unhandled pending tool call(s)"
                )
        except CheckpointCorruptionError as exc:
            issues.append(f"ReplayEngine session reconstruction failed: {exc.message}")
        except CheckpointStateError as exc:
            issues.append(f"ReplayEngine state transition error: {exc}")

        # Step 6: IdempotencyStore cross-verification if provided
        if idempotency_store is not None and session is not None:
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

        # Step 7: Recovery Potential classification cross-verification
        recovery_diag = RecoveryAnalyzer.analyze(run_id, db_path)
        recovery_potential = recovery_diag.recovery_potential

        if recovery_potential == RecoveryPotential.CORRUPT and not issues:
            issues.append(f"RecoveryAnalyzer reported corrupt session: {recovery_diag.error_message}")

        is_valid = len(issues) == 0

        return RunIntegrityReport(
            run_id=run_id,
            valid=is_valid,
            state=curr_state,
            checkpoint_count=len(target_events),
            pending_tool_calls=pending_count,
            completed_tool_calls=completed_count,
            recovery_potential=recovery_potential,
            issues=tuple(issues),
        )
