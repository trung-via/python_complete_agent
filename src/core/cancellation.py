from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import threading
from typing import Any, Dict, Optional

from src.core.checkpoint import CheckpointManager


class ControlEvent(str, Enum):
    CANCEL = "CANCEL"
    TIMEOUT = "TIMEOUT"


@dataclass(frozen=True)
class CancellationReason:
    event: ControlEvent
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "control_event": self.event.value,
            "reason": self.reason,
        }


class CancellationToken:
    """
    Thread-safe and async-safe cancellation token bound to a run_id.
    """

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self._is_cancelled = False
        self._reason: Optional[CancellationReason] = None
        self._lock = threading.Lock()

    @property
    def is_cancelled(self) -> bool:
        with self._lock:
            return self._is_cancelled

    @property
    def reason(self) -> Optional[CancellationReason]:
        with self._lock:
            return self._reason

    def _mark_cancelled(self, reason: CancellationReason) -> None:
        with self._lock:
            if not self._is_cancelled:
                self._is_cancelled = True
                self._reason = reason


class RunCancellationController:
    """
    Controller for managing run cancellation.

    Guarantees:
    - Commits durable RUN_HALTED event to CheckpointManager FIRST.
    - Only after durable write succeeds, in-memory CancellationToken is marked cancelled.
    - Multiple cancel calls are idempotent.
    - Checkpoint write failures raise exceptions (fail-closed) and do not advance in-memory state.
    """

    def __init__(self, checkpoints: CheckpointManager) -> None:
        self.checkpoints = checkpoints
        self._tokens: Dict[str, CancellationToken] = {}
        self._lock = threading.Lock()

    def get_token(self, run_id: str) -> CancellationToken:
        with self._lock:
            if run_id not in self._tokens:
                self._tokens[run_id] = CancellationToken(run_id)
            return self._tokens[run_id]

    def cancel(
        self,
        run_id: str,
        reason: str = "CANCELLED_BY_USER",
        event: ControlEvent = ControlEvent.CANCEL,
    ) -> CancellationToken:
        token = self.get_token(run_id)

        # Idempotency check: if already cancelled, return existing token
        if token.is_cancelled:
            return token

        cancel_reason = CancellationReason(event=event, reason=reason)

        # 1. Commit durable RUN_HALTED checkpoint FIRST
        self.checkpoints.log_run_halted(
            run_id,
            reason=f"{event.value}: {reason}",
        )

        # 2. Update memory ONLY AFTER checkpoint write succeeds
        token._mark_cancelled(cancel_reason)
        return token
