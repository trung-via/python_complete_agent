"""
Phase 5.3-A — In-Memory Reference Implementation of IdempotencyStoreProtocol

This is a testing-only implementation. It validates contract semantics
(lifecycle, ownership, corruption detection) without any persistence
or concurrency primitives.

Production implementations (P5.3-B/C) will add:
    - JSONL persistence
    - Filesystem locking
    - Dead-PID / stale-claim recovery
"""
from __future__ import annotations

import time
import logging
from typing import Optional, Dict, Any

from src.core.idempotency_contract import (
    RecordKey,
    RecordStatus,
    ClaimStatus,
    ClaimResult,
    IdempotencyRecord,
    IdempotencyCorruptionError,
    IdempotencyOwnershipError,
    IdempotencyStateError,
    TERMINAL_STATUSES,
)

logger = logging.getLogger(__name__)


class InMemoryIdempotencyStore:
    """
    Reference in-memory implementation of IdempotencyStoreProtocol.

    Stores records in a plain dict keyed by RecordKey.canonical.
    No thread safety, no disk I/O — purely for contract validation in tests.
    """

    def __init__(self) -> None:
        self._records: Dict[str, IdempotencyRecord] = {}

    # -- For testing: allow direct injection of corrupt data --
    def _inject_raw(self, canonical: str, raw: Any) -> None:
        """Backdoor for corruption tests. Bypasses all validation."""
        self._records[canonical] = raw

    # ------------------------------------------------------------------
    # Protocol methods
    # ------------------------------------------------------------------

    def claim(self, key: RecordKey, owner_id: str) -> ClaimResult:
        """
        Atomically attempt to claim an operation.

        Decision table:
            No record           → CLAIMED (create IN_PROGRESS)
            IN_PROGRESS          → ALREADY_IN_PROGRESS
            COMPLETED            → ALREADY_COMPLETED
            FAILED               → FAILED_PERMANENT
            RECOVERABLE          → CLAIMED (re-claim: IN_PROGRESS, owner=owner_id, attempt+1)
        """
        if not isinstance(owner_id, str):
            raise TypeError(f"owner_id must be str, got {type(owner_id).__name__}")
        if not owner_id:
            raise ValueError("owner_id cannot be empty")

        canonical = key.canonical
        existing = self._records.get(canonical)

        # Corruption guard: if something non-IdempotencyRecord got in
        if existing is not None and not isinstance(existing, IdempotencyRecord):
            raise IdempotencyCorruptionError(
                canonical, f"Expected IdempotencyRecord, got {type(existing).__name__}"
            )

        if existing is None:
            # Fresh claim
            now = time.time()
            record = IdempotencyRecord(
                key=key,
                status=RecordStatus.IN_PROGRESS,
                created_at=now,
                updated_at=now,
                owner_id=owner_id,
                attempt=1,
                data=None,
            )
            self._records[canonical] = record
            return ClaimResult(status=ClaimStatus.CLAIMED, record=record)

        # Existing record — route by status
        status = existing.status

        if status == RecordStatus.IN_PROGRESS:
            return ClaimResult(status=ClaimStatus.ALREADY_IN_PROGRESS, record=existing)

        if status == RecordStatus.COMPLETED:
            return ClaimResult(status=ClaimStatus.ALREADY_COMPLETED, record=existing)

        if status == RecordStatus.FAILED:
            return ClaimResult(status=ClaimStatus.FAILED_PERMANENT, record=existing)

        if status == RecordStatus.RECOVERABLE:
            # Re-claim: transfer ownership, transition to IN_PROGRESS, increment attempt
            now = time.time()
            record = IdempotencyRecord(
                key=key,
                status=RecordStatus.IN_PROGRESS,
                created_at=existing.created_at,
                updated_at=now,
                owner_id=owner_id,
                attempt=existing.attempt + 1,
                data=None,
            )
            self._records[canonical] = record
            return ClaimResult(status=ClaimStatus.CLAIMED, record=record)

        # If we get here, status is NEW or something unexpected
        if status == RecordStatus.NEW:
            # NEW should not normally persist (claim immediately goes to IN_PROGRESS),
            # but handle gracefully: treat as claimable
            now = time.time()
            record = IdempotencyRecord(
                key=key,
                status=RecordStatus.IN_PROGRESS,
                created_at=existing.created_at,
                updated_at=now,
                owner_id=owner_id,
                attempt=existing.attempt + 1,
                data=None,
            )
            self._records[canonical] = record
            return ClaimResult(status=ClaimStatus.CLAIMED, record=record)

        raise IdempotencyCorruptionError(
            canonical, f"Unknown RecordStatus: {status}"
        )

    def complete(
        self, key: RecordKey, owner_id: str, data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Transition IN_PROGRESS → COMPLETED. Owner-only."""
        canonical = key.canonical
        record = self._get_validated(canonical)

        if record is None:
            raise IdempotencyStateError(key, RecordStatus.NEW, RecordStatus.COMPLETED)

        if record.owner_id != owner_id:
            raise IdempotencyOwnershipError(key, owner_id, record.owner_id)

        if record.status != RecordStatus.IN_PROGRESS:
            raise IdempotencyStateError(key, record.status, RecordStatus.COMPLETED)

        self._records[canonical] = IdempotencyRecord(
            key=key,
            status=RecordStatus.COMPLETED,
            created_at=record.created_at,
            updated_at=time.time(),
            owner_id=record.owner_id,
            attempt=record.attempt,
            data=data,
        )

    def fail(
        self,
        key: RecordKey,
        owner_id: str,
        *,
        retryable: bool,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Transition IN_PROGRESS → FAILED or RECOVERABLE. Owner-only."""
        canonical = key.canonical
        target = RecordStatus.RECOVERABLE if retryable else RecordStatus.FAILED
        record = self._get_validated(canonical)

        if record is None:
            raise IdempotencyStateError(key, RecordStatus.NEW, target)

        if record.owner_id != owner_id:
            raise IdempotencyOwnershipError(key, owner_id, record.owner_id)

        if record.status != RecordStatus.IN_PROGRESS:
            raise IdempotencyStateError(key, record.status, target)

        self._records[canonical] = IdempotencyRecord(
            key=key,
            status=target,
            created_at=record.created_at,
            updated_at=time.time(),
            owner_id=record.owner_id,
            attempt=record.attempt,
            data=data,
        )

    def get(self, key: RecordKey) -> Optional[IdempotencyRecord]:
        """Read-only lookup. Raises on corruption."""
        canonical = key.canonical
        return self._get_validated(canonical)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get_validated(self, canonical: str) -> Optional[IdempotencyRecord]:
        """Fetch and validate a record. Raises IdempotencyCorruptionError on bad data."""
        raw = self._records.get(canonical)
        if raw is None:
            return None
        if not isinstance(raw, IdempotencyRecord):
            raise IdempotencyCorruptionError(
                canonical, f"Expected IdempotencyRecord, got {type(raw).__name__}"
            )
        return raw
