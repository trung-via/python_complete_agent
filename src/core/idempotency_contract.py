"""
Phase 5.3-A — Idempotency Contract

Defines the canonical types, enums, protocols, and errors for the
idempotency subsystem. This module is purely declarative: no I/O,
no concurrency primitives, no persistence.

Key concepts:
    RecordKey       = (operation_key, idempotency_key) composite identity
    RecordStatus    = lifecycle state of a record
    ClaimStatus     = outcome of a claim() call
    ClaimResult     = typed return value carrying status + record
    IdempotencyRecord = full metadata for a claimed operation
    IdempotencyStoreProtocol = abstract contract for any store impl
"""
from __future__ import annotations

import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Any, Dict, Protocol


# ---------------------------------------------------------------------------
# Lifecycle & Claim Enums
# ---------------------------------------------------------------------------

class RecordStatus(str, Enum):
    """
    Lifecycle states for an idempotency record.

    NEW           → just created, not yet executing
    IN_PROGRESS   → actively being executed by an owner
    COMPLETED     → finished successfully (terminal)
    FAILED        → finished with permanent failure (terminal)
    RECOVERABLE   → finished with retryable failure (eligible for re-claim)
    """
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RECOVERABLE = "RECOVERABLE"


class ClaimStatus(str, Enum):
    """
    Possible outcomes of a claim() call.

    CLAIMED              → caller now owns this operation
    ALREADY_IN_PROGRESS  → another owner is executing
    ALREADY_COMPLETED    → operation already succeeded (replay result)
    FAILED_RETRYABLE     → previous attempt failed but is retryable
    FAILED_PERMANENT     → previous attempt failed permanently
    """
    CLAIMED = "CLAIMED"
    ALREADY_IN_PROGRESS = "ALREADY_IN_PROGRESS"
    ALREADY_COMPLETED = "ALREADY_COMPLETED"
    FAILED_RETRYABLE = "FAILED_RETRYABLE"
    FAILED_PERMANENT = "FAILED_PERMANENT"


# Terminal statuses: once a record reaches these, the lifecycle is over
# (unless recovery policy explicitly re-opens RECOVERABLE).
TERMINAL_STATUSES = frozenset({RecordStatus.COMPLETED, RecordStatus.FAILED})


# ---------------------------------------------------------------------------
# Composite Key
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class RecordKey:
    """
    Composite identity for an idempotency record.

    operation_key    = identity of the logical operation
                       (same operation → same lifecycle)
    idempotency_key  = identity of a specific request/attempt
                       (prevents duplicate execution)

    Canonical form: "{operation_key}::{idempotency_key}"
    Scope guarantee: different operation_keys NEVER collide,
                     even with identical idempotency_keys.
    """
    operation_key: str
    idempotency_key: str

    def __post_init__(self):
        if not self.operation_key:
            raise ValueError("operation_key cannot be empty")
        if not self.idempotency_key:
            raise ValueError("idempotency_key cannot be empty")

    @property
    def canonical(self) -> str:
        """Unique string for storage lookup / hashing."""
        return f"{self.operation_key}::{self.idempotency_key}"


# ---------------------------------------------------------------------------
# Record & Claim Result
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class IdempotencyRecord:
    """
    Full metadata for a claimed operation.

    Fields:
        key         — composite (operation_key, idempotency_key)
        status      — current lifecycle state
        created_at  — epoch timestamp of initial claim
        updated_at  — epoch timestamp of last state transition
        owner_id    — identity of the owning worker (format TBD in P5.3-C)
        attempt     — 1-indexed attempt counter
        data        — arbitrary payload (e.g. serialized ToolResult)
    """
    key: RecordKey
    status: RecordStatus
    created_at: float
    updated_at: float
    owner_id: str
    attempt: int
    data: Optional[Dict[str, Any]] = None


@dataclass(frozen=True, slots=True)
class ClaimResult:
    """
    Return value of claim().

    status  — one of ClaimStatus indicating what happened
    record  — the current IdempotencyRecord (present for all statuses
              except when the store is empty for this key and claim succeeds)
    """
    status: ClaimStatus
    record: Optional[IdempotencyRecord] = None


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class IdempotencyError(Exception):
    """Base error for idempotency subsystem."""
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class IdempotencyOwnershipError(IdempotencyError):
    """Raised when a non-owner tries to transition a record it doesn't own."""
    def __init__(self, key: RecordKey, expected_owner: str, actual_owner: str):
        super().__init__(
            f"Ownership violation on {key.canonical}: "
            f"expected owner '{expected_owner}', actual owner '{actual_owner}'"
        )
        self.key = key
        self.expected_owner = expected_owner
        self.actual_owner = actual_owner


class IdempotencyStateError(IdempotencyError):
    """Raised when an invalid state transition is attempted."""
    def __init__(self, key: RecordKey, current_status: RecordStatus, target_status: RecordStatus):
        super().__init__(
            f"Invalid state transition on {key.canonical}: "
            f"{current_status.value} → {target_status.value}"
        )
        self.key = key
        self.current_status = current_status
        self.target_status = target_status


class IdempotencyCorruptionError(IdempotencyError):
    """Raised when a record is malformed or corrupt. Never silently succeed."""
    def __init__(self, key_canonical: str, reason: str):
        super().__init__(
            f"Corrupt idempotency record '{key_canonical}': {reason}"
        )
        self.key_canonical = key_canonical
        self.reason = reason


# ---------------------------------------------------------------------------
# Protocol (Abstract Contract)
# ---------------------------------------------------------------------------

class IdempotencyStoreProtocol(Protocol):
    """
    Abstract contract for any idempotency store implementation.

    Guarantees:
        1. claim() is an atomic decision — no check-then-act race
        2. State transitions are validated (no COMPLETED → IN_PROGRESS)
        3. Ownership is enforced (only the claimer can transition)
        4. Corrupt records raise IdempotencyCorruptionError explicitly

    Atomicity mechanism is NOT specified here — that's P5.3-B/C.
    """

    def claim(self, key: RecordKey, owner_id: str) -> ClaimResult:
        """
        Atomically attempt to claim an operation.

        Returns:
            ClaimResult with appropriate ClaimStatus:
            - CLAIMED: caller now owns this record (status = IN_PROGRESS)
            - ALREADY_IN_PROGRESS: another owner holds this record
            - ALREADY_COMPLETED: operation already succeeded
            - FAILED_RETRYABLE: previous attempt failed, eligible for retry
            - FAILED_PERMANENT: previous attempt failed permanently
        """
        ...

    def complete(
        self, key: RecordKey, owner_id: str, data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Transition IN_PROGRESS → COMPLETED.

        Raises:
            IdempotencyOwnershipError: if owner_id doesn't match
            IdempotencyStateError: if current status is not IN_PROGRESS
        """
        ...

    def fail(
        self,
        key: RecordKey,
        owner_id: str,
        *,
        retryable: bool,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Transition IN_PROGRESS → FAILED or RECOVERABLE.

        Args:
            retryable: True → RECOVERABLE, False → FAILED

        Raises:
            IdempotencyOwnershipError: if owner_id doesn't match
            IdempotencyStateError: if current status is not IN_PROGRESS
        """
        ...

    def get(self, key: RecordKey) -> Optional[IdempotencyRecord]:
        """
        Read-only lookup. Returns None if no record exists.

        Raises:
            IdempotencyCorruptionError: if the stored data is malformed
        """
        ...
