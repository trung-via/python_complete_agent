"""Durable ACTIVE/CONSUMED runtime storage for one-shot paid API grants."""
from __future__ import annotations

import contextlib
import hashlib
import os
from pathlib import Path
import re
import threading
from typing import Iterator

if os.name == "nt":
    import msvcrt
else:
    import fcntl

from .continuity.errors import ContinuityStateValidationError
from .continuity.state import MAX_SERIALIZED_BYTES
from .paid_api_grant import PaidApiGrant


_TASK_ID_PATTERN = re.compile(r"TASK-[0-9]+")
_GRANT_ID_PATTERN = re.compile(r"[a-z0-9]+(?:[a-z0-9_.:-]*[a-z0-9])?")
_WORKSPACE_ID_PATTERN = re.compile(r"[0-9a-f]{64}")
_MAX_GRANT_ID_LENGTH = 96

_GLOBAL_THREAD_LOCK = threading.Lock()
_TASK_THREAD_LOCKS: dict[str, threading.RLock] = {}


def _validation_error(message: str, cause: Exception | None = None) -> ContinuityStateValidationError:
    error = ContinuityStateValidationError(message)
    if cause is not None:
        error.__cause__ = cause
    return error


def _validate_task_id(task_id: object) -> str:
    if type(task_id) is not str or _TASK_ID_PATTERN.fullmatch(task_id) is None:
        raise ContinuityStateValidationError("task_id is invalid")
    return task_id


def _validate_grant_id(grant_id: object) -> str:
    if (
        type(grant_id) is not str
        or len(grant_id) > _MAX_GRANT_ID_LENGTH
        or _GRANT_ID_PATTERN.fullmatch(grant_id) is None
    ):
        raise ContinuityStateValidationError("grant_id is invalid")
    return grant_id


def _validate_workspace_id(workspace_id: object) -> str:
    if type(workspace_id) is not str or _WORKSPACE_ID_PATTERN.fullmatch(workspace_id) is None:
        raise ContinuityStateValidationError("workspace_id is invalid")
    return workspace_id


def _validate_now(now_epoch_seconds: object) -> int:
    if type(now_epoch_seconds) is not int or now_epoch_seconds < 0:
        raise ContinuityStateValidationError(
            "now_epoch_seconds must be an exact non-negative integer"
        )
    return now_epoch_seconds


def _get_task_thread_lock(task_dir: Path) -> threading.RLock:
    key = str(task_dir)
    with _GLOBAL_THREAD_LOCK:
        if key not in _TASK_THREAD_LOCKS:
            _TASK_THREAD_LOCKS[key] = threading.RLock()
        return _TASK_THREAD_LOCKS[key]


@contextlib.contextmanager
def _task_mutation_guard(task_dir: Path) -> Iterator[None]:
    """Serialize mutations for one task across threads and processes."""
    thread_lock = _get_task_thread_lock(task_dir)
    with thread_lock:
        try:
            task_dir.mkdir(parents=True, exist_ok=True)
            lock_path = task_dir / ".paid_api_grant_mutation.lock"
            fd = os.open(
                str(lock_path),
                os.O_CREAT | os.O_RDWR | getattr(os, "O_BINARY", 0),
                0o600,
            )
        except OSError as exc:
            raise _validation_error("failed to open paid API grant mutation guard", exc)

        try:
            os.lseek(fd, 0, os.SEEK_SET)
            if os.name == "nt":
                msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
            else:
                fcntl.flock(fd, fcntl.LOCK_EX)
            try:
                yield
            finally:
                if os.name == "nt":
                    try:
                        os.lseek(fd, 0, os.SEEK_SET)
                        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                    except Exception:
                        pass
                else:
                    try:
                        fcntl.flock(fd, fcntl.LOCK_UN)
                    except Exception:
                        pass
        except ContinuityStateValidationError:
            raise
        except OSError as exc:
            raise _validation_error("failed to lock paid API grant mutation guard", exc)
        finally:
            try:
                os.close(fd)
            except OSError:
                pass


def _best_effort_fsync_directory(directory: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        fd = os.open(str(directory), flags)
    except OSError:
        return
    try:
        try:
            os.fsync(fd)
        except OSError:
            pass
    finally:
        try:
            os.close(fd)
        except OSError:
            pass


class AtomicPaidApiGrantStore:
    """Atomic external-runtime store for paid API grant state transitions."""

    def __init__(self, grant_root: Path | str, workspace_id: str) -> None:
        self.grant_root = Path(grant_root).resolve()
        self.workspace_id = _validate_workspace_id(workspace_id)
        try:
            self.grant_root.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise _validation_error("failed to create paid API grant root", exc)

    def _task_dir(self, task_id: str) -> Path:
        return self.grant_root / _validate_task_id(task_id)

    def _state_paths(self, task_id: str, grant_id: str) -> tuple[Path, Path]:
        task_dir = self._task_dir(task_id)
        grant_id = _validate_grant_id(grant_id)
        grant_key = hashlib.sha256(grant_id.encode("utf-8")).hexdigest()
        return (
            task_dir / "active" / f"{grant_key}.json",
            task_dir / "consumed" / f"{grant_key}.json",
        )

    def _validate_grant(self, grant: object, *, argument_name: str) -> PaidApiGrant:
        if type(grant) is not PaidApiGrant:
            raise ContinuityStateValidationError(
                f"{argument_name} must be an exact PaidApiGrant"
            )
        if grant.workspace_id != self.workspace_id:
            raise ContinuityStateValidationError(
                f"{argument_name} workspace_id does not match the store workspace_id"
            )
        if grant.grant_fingerprint != grant.fingerprint():
            raise ContinuityStateValidationError(
                f"{argument_name} grant fingerprint is stale or forged"
            )
        return grant

    @staticmethod
    def _require_unexpired(grant: PaidApiGrant, now_epoch_seconds: int) -> None:
        if now_epoch_seconds >= grant.expires_at_epoch_seconds:
            raise ContinuityStateValidationError("paid API grant is expired")

    def _strict_read_state(
        self,
        path: Path,
        *,
        task_id: str,
        grant_id: str,
    ) -> PaidApiGrant:
        if path.is_dir():
            raise ContinuityStateValidationError("paid API grant state path is a directory")
        try:
            with path.open("rb") as state_file:
                raw_bytes = state_file.read(MAX_SERIALIZED_BYTES + 1)
        except OSError as exc:
            raise _validation_error("failed to read paid API grant state", exc)

        if not raw_bytes:
            raise ContinuityStateValidationError("paid API grant state is empty")
        if len(raw_bytes) > MAX_SERIALIZED_BYTES:
            raise ContinuityStateValidationError("paid API grant state exceeds maximum size")

        try:
            grant = PaidApiGrant.from_json(raw_bytes)
        except ValueError as exc:
            raise _validation_error("paid API grant state is invalid", exc)

        if grant.task_id != task_id:
            raise ContinuityStateValidationError(
                "paid API grant task_id does not match its namespace"
            )
        if grant.grant_id != grant_id:
            raise ContinuityStateValidationError(
                "paid API grant grant_id does not match its namespace"
            )
        if grant.workspace_id != self.workspace_id:
            raise ContinuityStateValidationError(
                "paid API grant workspace_id does not match the store"
            )
        if grant.grant_fingerprint != grant.fingerprint():
            raise ContinuityStateValidationError(
                "paid API grant fingerprint is stale or forged"
            )
        return grant

    def _inspect_key(
        self,
        task_id: str,
        grant_id: str,
    ) -> tuple[PaidApiGrant | None, PaidApiGrant | None]:
        active_path, consumed_path = self._state_paths(task_id, grant_id)
        active_exists = active_path.exists()
        consumed_exists = consumed_path.exists()

        if active_exists and consumed_exists:
            raise ContinuityStateValidationError(
                "paid API grant has contradictory ACTIVE and CONSUMED state"
            )

        active = (
            self._strict_read_state(active_path, task_id=task_id, grant_id=grant_id)
            if active_exists
            else None
        )
        consumed = (
            self._strict_read_state(consumed_path, task_id=task_id, grant_id=grant_id)
            if consumed_exists
            else None
        )
        return active, consumed

    @staticmethod
    def _require_exact_match(
        actual: PaidApiGrant,
        expected: PaidApiGrant,
        *,
        state_name: str,
    ) -> None:
        if actual != expected:
            raise ContinuityStateValidationError(
                f"{state_name} paid API grant does not exactly match expected"
            )
        if actual.fingerprint() != expected.fingerprint():
            raise ContinuityStateValidationError(
                f"{state_name} paid API grant fingerprint does not exactly match expected"
            )

    def load_active(self, task_id: str, grant_id: str) -> PaidApiGrant | None:
        active, _ = self._inspect_key(task_id, grant_id)
        return active

    def load_consumed(self, task_id: str, grant_id: str) -> PaidApiGrant | None:
        _, consumed = self._inspect_key(task_id, grant_id)
        return consumed

    def activate(
        self,
        grant: PaidApiGrant,
        *,
        now_epoch_seconds: int,
    ) -> PaidApiGrant:
        grant = self._validate_grant(grant, argument_name="grant")
        now_epoch_seconds = _validate_now(now_epoch_seconds)
        self._require_unexpired(grant, now_epoch_seconds)

        canonical_bytes = grant.to_canonical_json().encode("utf-8")
        if not canonical_bytes or len(canonical_bytes) > MAX_SERIALIZED_BYTES:
            raise ContinuityStateValidationError(
                "serialized paid API grant exceeds maximum size"
            )

        task_dir = self._task_dir(grant.task_id)
        active_path, consumed_path = self._state_paths(grant.task_id, grant.grant_id)
        with _task_mutation_guard(task_dir):
            active, consumed = self._inspect_key(grant.task_id, grant.grant_id)
            if active is not None or consumed is not None:
                raise ContinuityStateValidationError(
                    "paid API grant has already been activated or consumed"
                )

            try:
                active_path.parent.mkdir(parents=True, exist_ok=True)
                consumed_path.parent.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                raise _validation_error("failed to create paid API grant state directories", exc)

            created_by_this_call = False
            activation_verified = False
            fd: int | None = None
            try:
                flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0)
                fd = os.open(str(active_path), flags, 0o600)
                created_by_this_call = True

                total_written = 0
                while total_written < len(canonical_bytes):
                    written = os.write(fd, canonical_bytes[total_written:])
                    if written <= 0:
                        raise ContinuityStateValidationError(
                            "failed to fully write paid API grant state"
                        )
                    total_written += written
                try:
                    os.fsync(fd)
                except OSError as exc:
                    raise _validation_error("failed to durably sync paid API grant state", exc)
                os.close(fd)
                fd = None
                _best_effort_fsync_directory(active_path.parent)

                loaded = self._strict_read_state(
                    active_path,
                    task_id=grant.task_id,
                    grant_id=grant.grant_id,
                )
                self._require_exact_match(loaded, grant, state_name="ACTIVE")
                activation_verified = True
                return loaded
            except FileExistsError as exc:
                raise _validation_error("paid API grant activation collided with existing state", exc)
            except Exception as exc:
                if isinstance(exc, ContinuityStateValidationError):
                    error = exc
                else:
                    error = _validation_error("failed to activate paid API grant", exc)
                raise error
            finally:
                if fd is not None:
                    try:
                        os.close(fd)
                    except OSError:
                        pass
                if created_by_this_call and not activation_verified:
                    try:
                        active_path.unlink()
                        _best_effort_fsync_directory(active_path.parent)
                    except OSError:
                        pass

    def require_active(
        self,
        expected: PaidApiGrant,
        *,
        now_epoch_seconds: int,
    ) -> PaidApiGrant:
        expected = self._validate_grant(expected, argument_name="expected")
        now_epoch_seconds = _validate_now(now_epoch_seconds)
        active = self.load_active(expected.task_id, expected.grant_id)
        if active is None:
            raise ContinuityStateValidationError("paid API grant is not ACTIVE")
        self._require_exact_match(active, expected, state_name="ACTIVE")
        self._require_unexpired(active, now_epoch_seconds)
        return active

    def consume(
        self,
        expected: PaidApiGrant,
        *,
        now_epoch_seconds: int,
    ) -> PaidApiGrant:
        expected = self._validate_grant(expected, argument_name="expected")
        now_epoch_seconds = _validate_now(now_epoch_seconds)
        task_dir = self._task_dir(expected.task_id)
        active_path, consumed_path = self._state_paths(
            expected.task_id,
            expected.grant_id,
        )

        with _task_mutation_guard(task_dir):
            active, consumed = self._inspect_key(expected.task_id, expected.grant_id)
            if active is None:
                if consumed is not None:
                    raise ContinuityStateValidationError(
                        "paid API grant is already CONSUMED"
                    )
                raise ContinuityStateValidationError("paid API grant is not ACTIVE")
            if consumed is not None:
                raise ContinuityStateValidationError(
                    "paid API grant has contradictory ACTIVE and CONSUMED state"
                )

            self._require_exact_match(active, expected, state_name="ACTIVE")
            self._require_unexpired(active, now_epoch_seconds)
            if consumed_path.exists():
                raise ContinuityStateValidationError(
                    "CONSUMED paid API grant destination already exists"
                )

            try:
                os.replace(str(active_path), str(consumed_path))
            except OSError as exc:
                raise _validation_error("failed to atomically consume paid API grant", exc)

            _best_effort_fsync_directory(active_path.parent)
            _best_effort_fsync_directory(consumed_path.parent)

            # Once the move succeeds, every later failure leaves CONSUMED terminal.
            consumed_grant = self._strict_read_state(
                consumed_path,
                task_id=expected.task_id,
                grant_id=expected.grant_id,
            )
            self._require_exact_match(consumed_grant, expected, state_name="CONSUMED")
            if active_path.exists():
                raise ContinuityStateValidationError(
                    "ACTIVE paid API grant state remains after consume"
                )
            return consumed_grant
