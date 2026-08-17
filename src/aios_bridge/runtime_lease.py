"""
Runtime Executor Lease Store for AIOS Bridge (ADR-019 / TASK-029).
Provides atomic create-if-absent lease persistence, strict active verification, and compare-and-release.
"""
from __future__ import annotations

import os
from pathlib import Path
import time
from typing import Any

from .continuity.errors import ContinuityStateValidationError
from .continuity.lease import (
    ExecutorLease,
    _validate_exact_hex_sha_64,
    _validate_task_id,
    validate_executor_lease_binding,
)
from .continuity.state import MAX_SERIALIZED_BYTES


class AtomicExecutorLeaseStore:
    """
    Atomic filesystem store for single-active-executor leases (C8 / C9 / C11 / ADR-019).
    Uses OS-level atomic exclusive creation (O_CREAT | O_EXCL) to guarantee MAX_ACTIVE_EXECUTORS_PER_TASK = 1.
    """

    def __init__(self, lease_root: Path | str, workspace_id: str) -> None:
        self.lease_root = Path(lease_root).resolve()
        _validate_exact_hex_sha_64(workspace_id, "workspace_id")
        self.workspace_id = workspace_id
        self.lease_root.mkdir(parents=True, exist_ok=True)

    def _get_task_dir(self, task_id: str) -> Path:
        _validate_task_id(task_id, "task_id")
        return self.lease_root / task_id

    def _get_active_path(self, task_id: str) -> Path:
        return self._get_task_dir(task_id) / "ACTIVE.json"

    def _get_history_dir(self, task_id: str) -> Path:
        return self._get_task_dir(task_id) / "history"

    def load_active(self, task_id: str) -> ExecutorLease | None:
        """
        Strictly loads active lease for task_id.
        Returns None only when ACTIVE.json does not exist.
        Empty, corrupt, mismatched, or oversized files fail closed with ContinuityStateValidationError (C10).
        """
        active_file = self._get_active_path(task_id)
        if not active_file.exists():
            return None

        if active_file.is_dir():
            raise ContinuityStateValidationError(
                f"Active lease path '{active_file}' is a directory, expected file"
            )

        try:
            with open(active_file, "rb") as f:
                raw_bytes = f.read(MAX_SERIALIZED_BYTES + 1)
        except Exception as e:
            raise ContinuityStateValidationError(
                f"Failed reading active lease file for {task_id}: {e}"
            ) from e

        if len(raw_bytes) == 0:
            raise ContinuityStateValidationError(
                f"Active lease file for {task_id} is corrupt: file is empty (0 bytes)"
            )

        if len(raw_bytes) > MAX_SERIALIZED_BYTES:
            raise ContinuityStateValidationError(
                f"Active lease file for {task_id} exceeds maximum allowed size ({len(raw_bytes)} > {MAX_SERIALIZED_BYTES})"
            )

        lease = ExecutorLease.from_json(raw_bytes)

        if lease.task_id != task_id:
            raise ContinuityStateValidationError(
                f"Active lease task_id '{lease.task_id}' does not match directory namespace '{task_id}'"
            )

        if lease.workspace_id != self.workspace_id:
            raise ContinuityStateValidationError(
                f"Active lease workspace_id '{lease.workspace_id}' does not match store workspace_id '{self.workspace_id}'"
            )

        return lease

    def require_active(self, expected: ExecutorLease) -> ExecutorLease:
        """
        Strictly verifies that active lease matches expected lease in all fields and fingerprint (C10 / C20).
        """
        if not isinstance(expected, ExecutorLease):
            raise ContinuityStateValidationError(
                f"expected must be an ExecutorLease instance, got: {type(expected).__name__}"
            )

        active = self.load_active(expected.task_id)
        if active is None:
            raise ContinuityStateValidationError(
                f"No active executor lease found for {expected.task_id}"
            )

        validate_executor_lease_binding(
            active,
            task_id=expected.task_id,
            workspace_id=expected.workspace_id,
            executor_id=expected.executor_id,
            operation=expected.operation,
            execution_fingerprint=expected.execution_fingerprint,
        )

        if active.lease_id != expected.lease_id:
            raise ContinuityStateValidationError(
                f"Active lease_id '{active.lease_id}' != expected '{expected.lease_id}' for {expected.task_id}"
            )

        if active.fingerprint() != expected.fingerprint():
            raise ContinuityStateValidationError(
                f"Active lease fingerprint '{active.fingerprint()}' != expected '{expected.fingerprint()}' for {expected.task_id}"
            )

        return active

    def acquire(self, lease: ExecutorLease) -> ExecutorLease:
        """
        Atomically acquires exclusive lease for task_id using O_CREAT | O_EXCL (C9 / ADR-019).
        Fails closed on collision, corruption, or workspace mismatch.
        """
        if not isinstance(lease, ExecutorLease):
            raise ContinuityStateValidationError(
                f"lease must be an ExecutorLease instance, got: {type(lease).__name__}"
            )

        if lease.workspace_id != self.workspace_id:
            raise ContinuityStateValidationError(
                f"Lease workspace_id '{lease.workspace_id}' does not match store workspace_id '{self.workspace_id}'"
            )

        task_dir = self._get_task_dir(lease.task_id)
        task_dir.mkdir(parents=True, exist_ok=True)
        active_file = self._get_active_path(lease.task_id)

        canonical_bytes = lease.to_canonical_json().encode("utf-8")
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0)

        fd: int | None = None
        try:
            fd = os.open(str(active_file), flags, 0o600)
            os.write(fd, canonical_bytes)
            try:
                os.fsync(fd)
            except OSError:
                pass
            os.close(fd)
            fd = None
            return lease
        except FileExistsError:
            # Another lease file exists: strictly load it to surface exact diagnostic
            existing = self.load_active(lease.task_id)
            if existing is not None:
                raise ContinuityStateValidationError(
                    f"Task {lease.task_id} is already leased to executor '{existing.executor_id}' (lease_id={existing.lease_id!r})"
                )
            # If load_active returned None (impossible for FileExistsError unless unlinked concurrently), fail closed
            raise ContinuityStateValidationError(
                f"Task {lease.task_id} lease acquisition conflict on '{active_file}'"
            )
        except Exception as e:
            if fd is not None:
                try:
                    os.close(fd)
                except Exception:
                    pass
            # Best-effort cleanup of our own newly created file if we failed during write
            if active_file.exists():
                try:
                    active_file.unlink()
                except Exception:
                    pass
            raise ContinuityStateValidationError(
                f"Failed acquiring lease for {lease.task_id}: {e}"
            ) from e

    def release(self, expected: ExecutorLease) -> ExecutorLease:
        """
        Atomically releases lease via compare-and-release to history (C11 / ADR-019).
        Refuses release if current active lease does not match expected exact lease.
        """
        if not isinstance(expected, ExecutorLease):
            raise ContinuityStateValidationError(
                f"expected must be an ExecutorLease instance, got: {type(expected).__name__}"
            )

        # 1. Strict compare-and-validate against current active lease
        self.require_active(expected)

        # 2. Prepare history directory
        history_dir = self._get_history_dir(expected.task_id)
        history_dir.mkdir(parents=True, exist_ok=True)
        timestamp = int(time.time())
        dest_file = history_dir / f"RELEASED-{expected.lease_id}-{timestamp}.json"

        # 3. Atomic rename out of ACTIVE.json
        active_file = self._get_active_path(expected.task_id)
        try:
            os.replace(str(active_file), str(dest_file))
        except Exception as e:
            raise ContinuityStateValidationError(
                f"Failed to atomically release lease for {expected.task_id}: {e}"
            ) from e

        return expected
