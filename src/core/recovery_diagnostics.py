"""
Recovery Diagnostics Module

Provides read-only analysis of checkpoint state to determine recovery potential.
Strictly deterministic: same input → same output, never mutates filesystem.

Classification:
- COMPLETED: Run finished successfully
- RECOVERABLE: Run can continue from current state
- NON_RECOVERABLE: Run in terminal failure state
- CORRUPT: Checkpoint corrupted or integrity violation
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional
import logging

from src.agent.replay_engine import ReplayEngine
from src.core.checkpoint_contract import (
    CheckpointCorruptionError,
    CheckpointStateError,
    FailureDomain,
    RunState,
)

logger = logging.getLogger(__name__)


class RecoveryPotential(str, Enum):
    """Classification of recovery capability for a run."""

    COMPLETED = "COMPLETED"
    """Run already finished successfully. Result deterministic."""

    RECOVERABLE = "RECOVERABLE"
    """Run can continue from current state. No duplicates via idempotency."""

    NON_RECOVERABLE = "NON_RECOVERABLE"
    """Run in terminal failure state. Cannot resume."""

    CORRUPT = "CORRUPT"
    """Checkpoint corrupted. Fail-closed, no auto-repair."""


@dataclass
class RecoveryDiagnostics:
    """
    Read-only diagnostic report from recovery analysis.

    Deterministic: analyzing same run_id repeatedly produces identical output.
    """

    run_id: str
    current_state: RunState
    recovery_potential: RecoveryPotential
    failure_domain: Optional[FailureDomain] = None
    error_message: str = ""
    pending_tool_calls: int = 0
    completed_tool_calls: int = 0

    def can_resume(self) -> bool:
        """True if recovery is possible without corruption."""
        return self.recovery_potential in (
            RecoveryPotential.COMPLETED,
            RecoveryPotential.RECOVERABLE,
        )

    def is_deterministic(self) -> bool:
        """True if result is guaranteed same on re-analysis."""
        return self.recovery_potential != RecoveryPotential.CORRUPT

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/serialization."""
        return {
            "run_id": self.run_id,
            "current_state": self.current_state.value,
            "recovery_potential": self.recovery_potential.value,
            "failure_domain": self.failure_domain.value
            if self.failure_domain
            else None,
            "error_message": self.error_message,
            "pending_tool_calls": self.pending_tool_calls,
            "completed_tool_calls": self.completed_tool_calls,
        }


class RecoveryAnalyzer:
    """
    Deterministic, read-only analysis of checkpoint state.

    Never mutates filesystem. Same input always produces same output.
    Failure classification:
    - COMPLETED: Run has finished
    - RECOVERABLE: Run can continue
    - NON_RECOVERABLE: Run in terminal failure state
    - CORRUPT: Checkpoint integrity violation
    """

    @staticmethod
    def analyze(
        run_id: str,
        db_path: str,
    ) -> RecoveryDiagnostics:
        """
        Analyze checkpoint and determine recovery potential.

        Args:
            run_id: Run identifier
            db_path: Path to checkpoint JSONL file

        Returns:
            RecoveryDiagnostics with classification and metadata

        Raises:
            Nothing. All errors result in CORRUPT classification.
        """
        try:
            # Reconstruct session from checkpoint (read-only)
            events = ReplayEngine.load_events_for_run(db_path, run_id)

            if not events:
                return RecoveryDiagnostics(
                    run_id=run_id,
                    current_state=RunState.PENDING,
                    recovery_potential=RecoveryPotential.CORRUPT,
                    error_message=f"No checkpoint events found for run '{run_id}'",
                )

            session = ReplayEngine.reconstruct_session(db_path, run_id)

            # Classify based on current state
            if session.last_state == RunState.COMPLETED:
                return RecoveryDiagnostics(
                    run_id=run_id,
                    current_state=RunState.COMPLETED,
                    recovery_potential=RecoveryPotential.COMPLETED,
                    pending_tool_calls=len(session.pending_tool_calls),
                    completed_tool_calls=len(session.completed_tool_calls),
                )

            if session.last_state == RunState.FAILED:
                # Extract failure domain from events if possible
                failure_domain = _extract_failure_domain(events)
                return RecoveryDiagnostics(
                    run_id=run_id,
                    current_state=RunState.FAILED,
                    recovery_potential=RecoveryPotential.NON_RECOVERABLE,
                    failure_domain=failure_domain,
                    error_message="Run in FAILED terminal state",
                    pending_tool_calls=len(session.pending_tool_calls),
                    completed_tool_calls=len(session.completed_tool_calls),
                )

            if session.last_state == RunState.HALTED:
                # Extract halt reason if possible
                failure_domain = _extract_failure_domain(events)
                halt_reason = _extract_halt_reason(events)
                return RecoveryDiagnostics(
                    run_id=run_id,
                    current_state=RunState.HALTED,
                    recovery_potential=RecoveryPotential.NON_RECOVERABLE,
                    failure_domain=failure_domain,
                    error_message=f"Run in HALTED terminal state: {halt_reason}",
                    pending_tool_calls=len(session.pending_tool_calls),
                    completed_tool_calls=len(session.completed_tool_calls),
                )

            # Recoverable states: PENDING, RUNNING, LLM_WAITING, TOOL_EXECUTING
            return RecoveryDiagnostics(
                run_id=run_id,
                current_state=session.last_state,
                recovery_potential=RecoveryPotential.RECOVERABLE,
                pending_tool_calls=len(session.pending_tool_calls),
                completed_tool_calls=len(session.completed_tool_calls),
                error_message=f"Run can continue from state {session.last_state.value}",
            )

        except CheckpointCorruptionError as e:
            return RecoveryDiagnostics(
                run_id=run_id,
                current_state=RunState.PENDING,
                recovery_potential=RecoveryPotential.CORRUPT,
                error_message=f"Checkpoint corruption: {e.message}",
            )

        except CheckpointStateError as e:
            return RecoveryDiagnostics(
                run_id=run_id,
                current_state=RunState.PENDING,
                recovery_potential=RecoveryPotential.CORRUPT,
                error_message=f"Invalid state transition: {str(e)}",
            )

        except Exception as e:
            return RecoveryDiagnostics(
                run_id=run_id,
                current_state=RunState.PENDING,
                recovery_potential=RecoveryPotential.CORRUPT,
                error_message=f"Unexpected error during analysis: {str(e)}",
            )


def _extract_failure_domain(events: list) -> Optional[FailureDomain]:
    """
    Attempt to infer failure domain from event sequence.

    This is best-effort; if unable to determine, returns None.
    """
    for event in reversed(events):
        payload = event.payload or {}

        # Check for LLM-specific failures
        if event.event_type.value == "LLM_RESPONDED":
            if "error" in payload:
                return FailureDomain.LLM_PROVIDER

        # Check for tool-specific failures
        if event.event_type.value in ("TOOL_RESULT_RECEIVED", "TOOL_ATTEMPT_ENDED"):
            if payload.get("status") == "failure" or "error" in payload:
                return FailureDomain.TOOL_EXECUTION

        # Check for checkpoint-specific failures
        if "error" in payload and "checkpoint" in payload.get("error", "").lower():
            return FailureDomain.CHECKPOINT_STORE

    return None


def _extract_halt_reason(events: list) -> str:
    """Extract halt reason from RUN_HALTED event if present."""
    for event in reversed(events):
        if event.event_type.value == "RUN_HALTED":
            reason = event.payload.get("reason", "Unknown reason")
            return str(reason)

    return "Unknown halt reason"
