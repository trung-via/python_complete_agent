from __future__ import annotations

import json
import logging
import os
import threading
import time
from contextlib import contextmanager
from typing import Any, Dict, Iterator, Optional

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

    def __init__(self, ttl_seconds: Optional[float] = 86400) -> None:
        self._validate_ttl_seconds(ttl_seconds)
        self.ttl_seconds = ttl_seconds
        self._records: Dict[str, IdempotencyRecord] = {}

    @staticmethod
    def _validate_ttl_seconds(ttl_seconds: Optional[float]) -> None:
        if ttl_seconds is not None:
            if isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, (int, float)):
                raise TypeError(
                    f"ttl_seconds must be a number or None, got {type(ttl_seconds).__name__}"
                )
            if ttl_seconds <= 0:
                raise ValueError("ttl_seconds must be > 0")

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
            now = time.time()
            if (
                self.ttl_seconds is not None
                and (now - existing.updated_at) > self.ttl_seconds
            ):
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
        record = self._get_validated(key.canonical)
        if (
            record is not None
            and record.status == RecordStatus.IN_PROGRESS
            and self.ttl_seconds is not None
            and (time.time() - record.updated_at) > self.ttl_seconds
        ):
            return IdempotencyRecord(
                key=record.key,
                status=RecordStatus.RECOVERABLE,
                created_at=record.created_at,
                updated_at=record.updated_at,
                owner_id=record.owner_id,
                attempt=record.attempt,
                data=record.data,
            )
        return record

    def compact(self) -> None:
        """No-op for in-memory store."""
        pass

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

    The store uses a dedicated filesystem lock to serialize mutations across
    processes. Every mutation refreshes the in-memory snapshot while holding
    that lock before deciding the next state.

    Persistence follows a commit-before-memory-update invariant: the in-memory
    record is changed only after the corresponding JSONL append succeeds.

    The lock file is separate from the JSONL data file so that readers and
    writers never need to lock the append-only data file itself.
    """

    _LOCAL_LOCKS: Dict[str, threading.RLock] = {}
    _LOCAL_LOCKS_GUARD = threading.Lock()

    def __init__(
        self,
        db_path: str = "data/idempotency_store_v2.jsonl",
        ttl_seconds: Optional[float] = 86400,
    ) -> None:
        self._validate_ttl_seconds(ttl_seconds)
        self.db_path = db_path
        self.lock_path = f"{db_path}.lock"
        self.ttl_seconds = ttl_seconds
        self._records: Dict[str, IdempotencyRecord] = {}

        self._ensure_parent_directory()

        with self._store_lock():
            self._reload_locked()

    @staticmethod
    def _validate_ttl_seconds(ttl_seconds: Optional[float]) -> None:
        if ttl_seconds is not None:
            if isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, (int, float)):
                raise TypeError(
                    f"ttl_seconds must be a number or None, got {type(ttl_seconds).__name__}"
                )
            if ttl_seconds <= 0:
                raise ValueError("ttl_seconds must be > 0")

    # ------------------------------------------------------------------
    # Protocol methods
    # ------------------------------------------------------------------

    def claim(
        self,
        key: RecordKey,
        owner_id: str,
    ) -> ClaimResult:
        """Attempt to claim an idempotency record atomically."""
        self._validate_owner_id(owner_id)

        with self._store_lock():
            self._reload_locked()

            canonical = key.canonical
            existing = self._records.get(canonical)

            if existing is None:
                record = self._new_claim(
                    key,
                    owner_id,
                    attempt=1,
                )

                self._append(record)
                self._records[canonical] = record

                return ClaimResult(
                    status=ClaimStatus.CLAIMED,
                    record=record,
                )

            record = self._validate_record(
                canonical,
                existing,
            )

            if record.status == RecordStatus.IN_PROGRESS:
                now = time.time()
                if (
                    self.ttl_seconds is not None
                    and (now - record.updated_at) > self.ttl_seconds
                ):
                    claimed = self._new_claim(
                        key,
                        owner_id,
                        attempt=record.attempt + 1,
                        created_at=record.created_at,
                    )
                    self._append(claimed)
                    self._records[canonical] = claimed
                    return ClaimResult(
                        status=ClaimStatus.CLAIMED,
                        record=claimed,
                    )

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
        """Transition IN_PROGRESS to COMPLETED atomically."""
        with self._store_lock():
            self._reload_locked()

            self._transition_locked(
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
        """Transition IN_PROGRESS to FAILED or RECOVERABLE atomically."""
        target_status = (
            RecordStatus.RECOVERABLE
            if retryable
            else RecordStatus.FAILED
        )

        with self._store_lock():
            self._reload_locked()

            self._transition_locked(
                key=key,
                owner_id=owner_id,
                target_status=target_status,
                data=data,
            )

    def get(
        self,
        key: RecordKey,
    ) -> Optional[IdempotencyRecord]:
        """
        Return the latest validated record.

        Reads are also refreshed under the process lock so callers do not
        observe an indefinitely stale snapshot.
        """
        with self._store_lock():
            self._reload_locked()

            record = self._records.get(key.canonical)

            if record is None:
                return None

            validated = self._validate_record(
                key.canonical,
                record,
            )

            if (
                validated.status == RecordStatus.IN_PROGRESS
                and self.ttl_seconds is not None
                and (time.time() - validated.updated_at) > self.ttl_seconds
            ):
                return IdempotencyRecord(
                    key=validated.key,
                    status=RecordStatus.RECOVERABLE,
                    created_at=validated.created_at,
                    updated_at=validated.updated_at,
                    owner_id=validated.owner_id,
                    attempt=validated.attempt,
                    data=validated.data,
                )

            return validated

    def compact(self) -> None:
        """
        Rewrite JSONL file to retain only the latest record per canonical key.

        Executed atomically under _store_lock() using temp file replacement.
        """
        with self._store_lock():
            self._reload_locked()
            tmp_path = self._write_snapshot_locked(self._records)
            self._replace_snapshot_locked(tmp_path)
            self._reload_locked()

    # ------------------------------------------------------------------
    # Atomic transition & Snapshot helpers
    # ------------------------------------------------------------------

    def _write_snapshot_locked(
        self,
        records: Dict[str, IdempotencyRecord],
    ) -> str:
        """
        Write records to a temporary file sorted deterministically by canonical key.

        Caller must hold _store_lock().
        """
        tmp_path = f"{self.db_path}.tmp"
        sorted_records = sorted(
            records.values(),
            key=lambda r: r.key.canonical,
        )

        try:
            with open(tmp_path, "w", encoding="utf-8") as handle:
                for record in sorted_records:
                    payload = self._record_to_dict(record)
                    handle.write(
                        json.dumps(payload, sort_keys=True) + "\n"
                    )
                handle.flush()
                os.fsync(handle.fileno())
            return tmp_path
        except Exception as exc:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
            raise OSError(f"Failed to write snapshot: {exc}") from exc

    def _replace_snapshot_locked(self, tmp_path: str) -> None:
        """
        Atomically replace the db_path data file with tmp_path.

        Caller must hold _store_lock(). Lock file is untouched.
        """
        try:
            os.replace(tmp_path, self.db_path)
        except Exception as exc:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
            raise OSError(f"Failed to replace snapshot: {exc}") from exc

    # ------------------------------------------------------------------
    # Atomic transition
    # ------------------------------------------------------------------

    def _transition_locked(
        self,
        *,
        key: RecordKey,
        owner_id: str,
        target_status: RecordStatus,
        data: Optional[Dict[str, Any]],
    ) -> None:
        self._validate_owner_id(owner_id)

        record = self._records.get(key.canonical)

        if record is None:
            raise IdempotencyStateError(
                key,
                RecordStatus.NEW,
                target_status,
            )

        record = self._validate_record(
            key.canonical,
            record,
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

        # Durable commit happens before the in-memory state transition.
        self._append(updated)
        self._records[key.canonical] = updated

    # ------------------------------------------------------------------
    # Persistence loading
    # ------------------------------------------------------------------

    def _reload_locked(self) -> None:
        """
        Replace the memory snapshot with the latest durable JSONL state.

        Caller must hold the filesystem lock. Refreshing before each mutation
        closes the stale-snapshot race between independent store instances.
        """
        self._records.clear()
        self._load()

    def _load(self) -> None:
        """Load the latest valid record for every canonical key."""
        if not os.path.exists(self.db_path):
            return

        try:
            with open(
                self.db_path,
                "r",
                encoding="utf-8",
            ) as handle:
                for line_number, line in enumerate(
                    handle,
                    start=1,
                ):
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

                    record = self._record_from_dict(
                        payload,
                        line_number,
                    )

                    canonical = record.key.canonical

                    if canonical in self._records:
                        previous = self._records[canonical]

                        if record.updated_at < previous.updated_at:
                            raise IdempotencyCorruptionError(
                                canonical,
                                (
                                    "Record update timestamp moved "
                                    f"backwards at line {line_number}"
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

    def _append(
        self,
        record: IdempotencyRecord,
    ) -> None:
        """
        Append the complete record and fsync it.

        This method assumes the caller already holds the filesystem lock.
        """
        payload = self._record_to_dict(record)

        try:
            with open(
                self.db_path,
                "a",
                encoding="utf-8",
            ) as handle:
                handle.write(
                    json.dumps(
                        payload,
                        sort_keys=True,
                    )
                    + "\n"
                )
                handle.flush()
                os.fsync(handle.fileno())

        except OSError as exc:
            raise OSError(
                f"Failed to persist idempotency record: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Cross-process filesystem locking
    # ------------------------------------------------------------------

    @contextmanager
    def _store_lock(self) -> Iterator[None]:
        """
        Acquire both an in-process and OS-level exclusive lock.

        The in-process lock prevents two store instances in the same Python
        process from entering the OS locking layer concurrently. The OS lock
        serializes independent processes.
        """
        local_lock = self._get_local_lock(self.lock_path)

        with local_lock:
            handle = None

            try:
                handle = open(
                    self.lock_path,
                    "a+b",
                )

                self._acquire_os_lock(handle)

                try:
                    yield
                finally:
                    self._release_os_lock(handle)

            except OSError:
                raise
            finally:
                if handle is not None:
                    handle.close()

    @classmethod
    def _get_local_lock(
        cls,
        lock_path: str,
    ) -> threading.RLock:
        """Return the process-local lock associated with a lock path."""
        normalized = os.path.abspath(lock_path)

        with cls._LOCAL_LOCKS_GUARD:
            lock = cls._LOCAL_LOCKS.get(normalized)

            if lock is None:
                lock = threading.RLock()
                cls._LOCAL_LOCKS[normalized] = lock

            return lock

    @staticmethod
    def _acquire_os_lock(handle: Any) -> None:
        """Acquire an exclusive blocking OS-level file lock."""
        if os.name == "nt":
            import msvcrt

            handle.seek(0)

            if handle.tell() == 0:
                handle.write(b"\0")
                handle.flush()

            handle.seek(0)
            msvcrt.locking(
                handle.fileno(),
                msvcrt.LK_LOCK,
                1,
            )
            return

        import fcntl

        fcntl.flock(
            handle.fileno(),
            fcntl.LOCK_EX,
        )

    @staticmethod
    def _release_os_lock(handle: Any) -> None:
        """Release an OS-level file lock."""
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            msvcrt.locking(
                handle.fileno(),
                msvcrt.LK_UNLCK,
                1,
            )
            return

        import fcntl

        fcntl.flock(
            handle.fileno(),
            fcntl.LOCK_UN,
        )

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    @staticmethod
    def _record_to_dict(
        record: IdempotencyRecord,
    ) -> Dict[str, Any]:
        """Serialize an IdempotencyRecord into JSON-compatible data."""
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
        """Deserialize and validate one JSONL record."""
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
        """Validate an in-memory record before returning or mutating it."""
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

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _ensure_parent_directory(self) -> None:
        """Create the parent directory for the store and lock files."""
        directory = os.path.dirname(
            os.path.abspath(self.db_path)
        )

        os.makedirs(
            directory,
            exist_ok=True,
        )

    @staticmethod
    def _new_claim(
        key: RecordKey,
        owner_id: str,
        *,
        attempt: int,
        created_at: Optional[float] = None,
    ) -> IdempotencyRecord:
        """Create a new IN_PROGRESS record."""
        now = time.time()

        return IdempotencyRecord(
            key=key,
            status=RecordStatus.IN_PROGRESS,
            created_at=(
                now
                if created_at is None
                else created_at
            ),
            updated_at=now,
            owner_id=owner_id,
            attempt=attempt,
            data=None,
        )

    @staticmethod
    def _validate_owner_id(
        owner_id: str,
    ) -> None:
        """Validate an idempotency record owner identifier."""
        if not isinstance(owner_id, str):
            raise TypeError(
                f"owner_id must be str, got {type(owner_id).__name__}"
            )

        if not owner_id:
            raise ValueError(
                "owner_id cannot be empty"
            )
