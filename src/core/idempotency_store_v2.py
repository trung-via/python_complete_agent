from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, Optional

from src.core.idempotency_contract import (
    ClaimResult,
    ClaimStatus,
    IdempotencyCorruptionError,
    IdempotencyOwnershipError,
    IdempotencyRecord,
    IdempotencyStateError,
    RecordKey,
    RecordStatus,
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

    def _inject_raw(self, canonical: str, raw: Any) -> None:
        """Backdoor for corruption tests. Bypasses all validation."""
        self._records[canonical] = raw

    def claim(self, key: RecordKey, owner_id: str) -> ClaimResult:
        """Attempt to claim an idempotency record."""
        if not isinstance(owner_id, str):
            raise TypeError(
                f"owner_id must be str, got {type(owner_id).__name__}"
            )
        if not owner_id:
            raise ValueError("owner_id cannot be empty")

        canonical = key.canonical
        existing = self._records.get(canonical)

        if existing is not None and not isinstance(existing, IdempotencyRecord):
            raise IdempotencyCorruptionError(
                canonical,
                f"Expected IdempotencyRecord, got {type(existing).__name__}",
            )

        if existing is None:
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
            return ClaimResult(
                status=ClaimStatus.CLAIMED,
                record=record,
            )

        status = existing.status

        if status == RecordStatus.IN_PROGRESS:
            return ClaimResult(
                status=ClaimStatus.ALREADY_IN_PROGRESS,
                record=existing,
            )

        if status == RecordStatus.COMPLETED:
            return ClaimResult(
                status=ClaimStatus.ALREADY_COMPLETED,
                record=existing,
            )

        if status == RecordStatus.FAILED:
            return ClaimResult(
                status=ClaimStatus.FAILED_PERMANENT,
                record=existing,
            )

        if status in (RecordStatus.RECOVERABLE, RecordStatus.NEW):
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
            return ClaimResult(
                status=ClaimStatus.CLAIMED,
                record=record,
            )

        raise IdempotencyCorruptionError(
            canonical,
            f"Unknown RecordStatus: {status}",
        )

    def complete(
        self,
        key: RecordKey,
        owner_id: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Transition IN_PROGRESS to COMPLETED."""
        canonical = key.canonical
        record = self._get_validated(canonical)

        if record is None:
            raise IdempotencyStateError(
                key,
                RecordStatus.NEW,
                RecordStatus.COMPLETED,
            )

        if record.owner_id != owner_id:
            raise IdempotencyOwnershipError(
                key,
                owner_id,
                record.owner_id,
            )

        if record.status != RecordStatus.IN_PROGRESS:
            raise IdempotencyStateError(
                key,
                record.status,
                RecordStatus.COMPLETED,
            )

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
        """Transition IN_PROGRESS to FAILED or RECOVERABLE."""
        canonical = key.canonical
        target = (
            RecordStatus.RECOVERABLE
            if retryable
            else RecordStatus.FAILED
        )
        record = self._get_validated(canonical)

        if record is None:
            raise IdempotencyStateError(key, RecordStatus.NEW, target)

        if record.owner_id != owner_id:
            raise IdempotencyOwnershipError(
                key,
                owner_id,
                record.owner_id,
            )

        if record.status != RecordStatus.IN_PROGRESS:
            raise IdempotencyStateError(
                key,
                record.status,
                target,
            )

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
        return self._get_validated(key.canonical)

    def _get_validated(
        self,
        canonical: str,
    ) -> Optional[IdempotencyRecord]:
        """Fetch and validate a record."""
        raw = self._records.get(canonical)

        if raw is None:
            return None

        if not isinstance(raw, IdempotencyRecord):
            raise IdempotencyCorruptionError(
                canonical,
                f"Expected IdempotencyRecord, got {type(raw).__name__}",
            )

        return raw


class JsonlIdempotencyStore:
    """
    Persistent JSONL implementation of IdempotencyStoreProtocol.

    Records are loaded into memory for reads. Every state transition appends
    the complete current record to the JSONL file.

    Persistence follows a commit-before-memory-update invariant: the in-memory
    record is changed only after the corresponding JSONL append succeeds.

    This implementation does not provide cross-process atomicity. It is
    intended as the persistent bridge before filesystem locking is introduced.
    """

    def __init__(
        self,
        db_path: str = "data/idempotency_store_v2.jsonl",
    ) -> None:
        self.db_path = db_path
        self._records: Dict[str, IdempotencyRecord] = {}

        self._ensure_parent_directory()
        self._load()

    def claim(self, key: RecordKey, owner_id: str) -> ClaimResult:
        """Attempt to claim an idempotency record."""
        self._validate_owner_id(owner_id)

        canonical = key.canonical
        existing = self._records.get(canonical)

        if existing is None:
            record = self._new_claim(key, owner_id, attempt=1)

            # Persistence is the commit point. Do not mutate memory first.
            self._append(record)
            self._records[canonical] = record

            return ClaimResult(
                status=ClaimStatus.CLAIMED,
                record=record,
            )

        record = self._validate_record(canonical, existing)

        if record.status == RecordStatus.IN_PROGRESS:
            return ClaimResult(
                status=ClaimStatus.ALREADY_IN_PROGRESS,
                record=record,
            )

        if record.status == RecordStatus.COMPLETED:
            return ClaimResult(
                status=ClaimStatus.ALREADY_COMPLETED,
                record=record,
            )

        if record.status == RecordStatus.FAILED:
            return ClaimResult(
                status=ClaimStatus.FAILED_PERMANENT,
                record=record,
            )

        if record.status in (
            RecordStatus.RECOVERABLE,
            RecordStatus.NEW,
        ):
            claimed = self._new_claim(
                key,
                owner_id,
                attempt=record.attempt + 1,
                created_at=record.created_at,
            )

            # Persistence is the commit point. Keep the previous memory
            # state if persistence fails.
            self._append(claimed)
            self._records[canonical] = claimed

            return ClaimResult(
                status=ClaimStatus.CLAIMED,
                record=claimed,
            )

        raise IdempotencyCorruptionError(
            canonical,
            f"Unknown RecordStatus: {record.status!r}",
        )

    def complete(
        self,
        key: RecordKey,
        owner_id: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Transition IN_PROGRESS to COMPLETED."""
        self._transition(
            key=key,
            owner_id=owner_id,
            target_status=RecordStatus.COMPLETED,
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
        """Transition IN_PROGRESS to FAILED or RECOVERABLE."""
        target_status = (
            RecordStatus.RECOVERABLE
            if retryable
            else RecordStatus.FAILED
        )

        self._transition(
            key=key,
            owner_id=owner_id,
            target_status=target_status,
            data=data,
        )

    def get(self, key: RecordKey) -> Optional[IdempotencyRecord]:
        """Return a validated record or None."""
        record = self._records.get(key.canonical)

        if record is None:
            return None

        return self._validate_record(key.canonical, record)

    def _transition(
        self,
        *,
        key: RecordKey,
        owner_id: str,
        target_status: RecordStatus,
        data: Optional[Dict[str, Any]],
    ) -> None:
        self._validate_owner_id(owner_id)

        record = self.get(key)

        if record is None:
            raise IdempotencyStateError(
                key,
                RecordStatus.NEW,
                target_status,
            )

        if record.owner_id != owner_id:
            raise IdempotencyOwnershipError(
                key,
                owner_id,
                record.owner_id,
            )

        if record.status != RecordStatus.IN_PROGRESS:
            raise IdempotencyStateError(
                key,
                record.status,
                target_status,
            )

        updated = IdempotencyRecord(
            key=key,
            status=target_status,
            created_at=record.created_at,
            updated_at=time.time(),
            owner_id=record.owner_id,
            attempt=record.attempt,
            data=data,
        )

        # Persistence is the commit point. If _append() raises, _records
        # remains IN_PROGRESS and therefore consistent with durable state.
        self._append(updated)
        self._records[key.canonical] = updated

    def _load(self) -> None:
        """Load the latest valid record for every canonical key."""
        if not os.path.exists(self.db_path):
            return

        try:
            with open(self.db_path, "r", encoding="utf-8") as handle:
                for line_number, line in enumerate(handle, start=1):
                    stripped = line.strip()

                    if not stripped:
                        continue

                    try:
                        payload = json.loads(stripped)
                    except json.JSONDecodeError as exc:
                        raise IdempotencyCorruptionError(
                            f"<line:{line_number}>",
                            f"Invalid JSON: {exc.msg}",
                        ) from exc

                    record = self._record_from_dict(payload, line_number)
                    canonical = record.key.canonical

                    if canonical in self._records:
                        previous = self._records[canonical]

                        if record.updated_at < previous.updated_at:
                            raise IdempotencyCorruptionError(
                                canonical,
                                (
                                    "Record update timestamp moved backwards "
                                    f"at line {line_number}"
                                ),
                            )

                    self._records[canonical] = record

        except IdempotencyCorruptionError:
            raise
        except OSError as exc:
            raise IdempotencyCorruptionError(
                "<store>",
                f"Failed to read JSONL store: {exc}",
            ) from exc

    def _append(self, record: IdempotencyRecord) -> None:
        """Append the complete current record to persistent storage."""
        payload = self._record_to_dict(record)

        try:
            with open(self.db_path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, sort_keys=True) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
        except OSError as exc:
            raise OSError(
                f"Failed to persist idempotency record: {exc}"
            ) from exc

    @staticmethod
    def _record_to_dict(
        record: IdempotencyRecord,
    ) -> Dict[str, Any]:
        return {
            "key": {
                "operation_key": record.key.operation_key,
                "idempotency_key": record.key.idempotency_key,
            },
            "status": record.status.value,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
            "owner_id": record.owner_id,
            "attempt": record.attempt,
            "data": record.data,
        }

    @staticmethod
    def _record_from_dict(
        payload: Any,
        line_number: int,
    ) -> IdempotencyRecord:
        if not isinstance(payload, dict):
            raise IdempotencyCorruptionError(
                f"<line:{line_number}>",
                f"Expected object, got {type(payload).__name__}",
            )

        required = {
            "key",
            "status",
            "created_at",
            "updated_at",
            "owner_id",
            "attempt",
            "data",
        }

        missing = required.difference(payload)

        if missing:
            raise IdempotencyCorruptionError(
                f"<line:{line_number}>",
                f"Missing fields: {sorted(missing)}",
            )

        key_data = payload["key"]

        if not isinstance(key_data, dict):
            raise IdempotencyCorruptionError(
                f"<line:{line_number}>",
                "key must be an object",
            )

        try:
            key = RecordKey(
                operation_key=key_data["operation_key"],
                idempotency_key=key_data["idempotency_key"],
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise IdempotencyCorruptionError(
                f"<line:{line_number}>",
                f"Invalid RecordKey: {exc}",
            ) from exc

        try:
            status = RecordStatus(payload["status"])
        except (TypeError, ValueError) as exc:
            raise IdempotencyCorruptionError(
                key.canonical,
                f"Invalid RecordStatus: {payload['status']!r}",
            ) from exc

        created_at = payload["created_at"]
        updated_at = payload["updated_at"]
        owner_id = payload["owner_id"]
        attempt = payload["attempt"]

        if not isinstance(created_at, (int, float)):
            raise IdempotencyCorruptionError(
                key.canonical,
                "created_at must be numeric",
            )

        if not isinstance(updated_at, (int, float)):
            raise IdempotencyCorruptionError(
                key.canonical,
                "updated_at must be numeric",
            )

        if not isinstance(owner_id, str) or not owner_id:
            raise IdempotencyCorruptionError(
                key.canonical,
                "owner_id must be a non-empty string",
            )

        if isinstance(attempt, bool) or not isinstance(attempt, int):
            raise IdempotencyCorruptionError(
                key.canonical,
                "attempt must be an integer",
            )

        if attempt < 1:
            raise IdempotencyCorruptionError(
                key.canonical,
                "attempt must be >= 1",
            )

        data = payload["data"]

        if data is not None and not isinstance(data, dict):
            raise IdempotencyCorruptionError(
                key.canonical,
                "data must be an object or null",
            )

        try:
            return IdempotencyRecord(
                key=key,
                status=status,
                created_at=float(created_at),
                updated_at=float(updated_at),
                owner_id=owner_id,
                attempt=attempt,
                data=data,
            )
        except (TypeError, ValueError) as exc:
            raise IdempotencyCorruptionError(
                key.canonical,
                f"Invalid record: {exc}",
            ) from exc

    @staticmethod
    def _validate_record(
        canonical: str,
        raw: Any,
    ) -> IdempotencyRecord:
        if not isinstance(raw, IdempotencyRecord):
            raise IdempotencyCorruptionError(
                canonical,
                f"Expected IdempotencyRecord, got {type(raw).__name__}",
            )

        if raw.key.canonical != canonical:
            raise IdempotencyCorruptionError(
                canonical,
                (
                    "RecordKey canonical mismatch: "
                    f"{raw.key.canonical!r}"
                ),
            )

        if not isinstance(raw.status, RecordStatus):
            raise IdempotencyCorruptionError(
                canonical,
                "status is not a RecordStatus",
            )

        if not raw.owner_id:
            raise IdempotencyCorruptionError(
                canonical,
                "owner_id cannot be empty",
            )

        if raw.attempt < 1:
            raise IdempotencyCorruptionError(
                canonical,
                "attempt must be >= 1",
            )

        if raw.updated_at < raw.created_at:
            raise IdempotencyCorruptionError(
                canonical,
                "updated_at cannot be earlier than created_at",
            )

        if raw.data is not None and not isinstance(raw.data, dict):
            raise IdempotencyCorruptionError(
                canonical,
                "data must be a dictionary or None",
            )

        return raw

    def _ensure_parent_directory(self) -> None:
        directory = os.path.dirname(self.db_path)

        if directory:
            os.makedirs(directory, exist_ok=True)

    @staticmethod
    def _new_claim(
        key: RecordKey,
        owner_id: str,
        *,
        attempt: int,
        created_at: Optional[float] = None,
    ) -> IdempotencyRecord:
        now = time.time()

        return IdempotencyRecord(
            key=key,
            status=RecordStatus.IN_PROGRESS,
            created_at=now if created_at is None else created_at,
            updated_at=now,
            owner_id=owner_id,
            attempt=attempt,
            data=None,
        )

    @staticmethod
    def _validate_owner_id(owner_id: str) -> None:
        if not isinstance(owner_id, str):
            raise TypeError(
                f"owner_id must be str, got {type(owner_id).__name__}"
            )

        if not owner_id:
            raise ValueError("owner_id cannot be empty")
