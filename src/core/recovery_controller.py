from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any, Dict, Optional, TYPE_CHECKING

from src.agent.replay_engine import ReplayEngine
from src.core.checkpoint_contract import CheckpointCorruptionError
from src.core.errors import RecoveryStateError
from src.core.integrity_verifier import RunIntegrityReport, RunIntegrityVerifier
from src.core.recovery_diagnostics import RecoveryAnalyzer, RecoveryDiagnostics, RecoveryPotential

if TYPE_CHECKING:
    from src.agent.loop import AgentLoop


@dataclass(frozen=True)
class RecoveryInspection:
    """
    Immutable, deterministic inspection report uniting integrity verification
    and recovery diagnostics for a run.
    """

    run_id: str
    integrity_report: RunIntegrityReport
    diagnostics: RecoveryDiagnostics

    @property
    def valid(self) -> bool:
        """True if the checkpoint data structure and sequence are completely valid."""
        return self.integrity_report.valid

    @property
    def can_resume(self) -> bool:
        """True if the run is valid and classified as RECOVERABLE or COMPLETED."""
        return self.valid and self.diagnostics.can_resume()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "valid": self.valid,
            "integrity": self.integrity_report.to_dict(),
            "diagnostics": self.diagnostics.to_dict(),
        }


class RecoveryController:
    """
    Control plane orchestration layer for inspecting and safely resuming agent runs.

    Guarantees:
    - Never mutates checkpoints, replays messages, or executes tools directly.
    - `inspect()` is strictly read-only and deterministic; propagates IO/infrastructure errors.
    - `resume()` enforces the decision matrix before delegating execution to AgentLoop.resume().
    """

    @staticmethod
    def inspect(db_path: str, run_id: str) -> RecoveryInspection:
        """
        Perform a non-mutating inspection of run_id in db_path.

        Infrastructure/IO errors (e.g. FileNotFoundError, PermissionError, OSError) propagate directly.
        Logical corruption or invalid session entries return an inspection with valid=False.
        """
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Checkpoint database file does not exist: {db_path}")

        integrity_report = RunIntegrityVerifier.verify(db_path, run_id)
        diagnostics = RecoveryAnalyzer.analyze(run_id, db_path)

        return RecoveryInspection(
            run_id=run_id,
            integrity_report=integrity_report,
            diagnostics=diagnostics,
        )

    @classmethod
    async def resume(cls, loop: AgentLoop, run_id: str) -> Optional[str]:
        """
        Safely resume an interrupted run using loop.

        Decision Matrix:
        1. Infrastructure/IO errors -> propagate exception directly.
        2. valid=False (invalid session / corrupt checkpoint) -> raise CheckpointCorruptionError (fail closed).
        3. valid=True & COMPLETED -> return cached result directly without executing tools/LLM.
        4. valid=True & NON_RECOVERABLE (FAILED / HALTED) -> raise RecoveryStateError.
        5. valid=True & RECOVERABLE -> delegate execution strictly to loop.resume(run_id).
        """
        db_path = loop.checkpoints.db_path
        inspection = cls.inspect(db_path, run_id)

        # Gate 1: Checkpoint/Session Integrity Check (fail closed)
        if not inspection.valid:
            issues_str = "; ".join(inspection.integrity_report.issues)
            raise CheckpointCorruptionError(
                run_id,
                f"Cannot resume run '{run_id}': integrity verification failed ({issues_str})",
            )

        diag = inspection.diagnostics

        # Gate 2: COMPLETED -> return cached answer without LLM or tool execution
        if diag.recovery_potential == RecoveryPotential.COMPLETED:
            session = ReplayEngine.reconstruct_session(db_path, run_id)
            for msg in reversed(session.messages):
                if msg.role.value == "assistant" and msg.content:
                    return msg.content
            return None

        # Gate 3: NON_RECOVERABLE (FAILED / HALTED) -> raise RecoveryStateError
        if diag.recovery_potential == RecoveryPotential.NON_RECOVERABLE:
            raise RecoveryStateError(
                f"Cannot resume run '{run_id}' in terminal state {diag.current_state.value}: {diag.error_message}"
            )

        # Gate 4: CORRUPT classification check
        if diag.recovery_potential == RecoveryPotential.CORRUPT:
            raise CheckpointCorruptionError(
                run_id,
                f"Cannot resume run '{run_id}': classified as CORRUPT ({diag.error_message})",
            )

        # Gate 5: RECOVERABLE -> delegate to AgentLoop.resume()
        if diag.recovery_potential == RecoveryPotential.RECOVERABLE:
            return await loop.resume(run_id)

        raise RecoveryStateError(f"Unknown recovery potential for run '{run_id}': {diag.recovery_potential}")
