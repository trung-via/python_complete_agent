"""
Unit tests for Runtime Atomic Executor Lease Store (ADR-019 / TASK-029).
Validates atomic create-if-absent, concurrent race linearization, corrupt file fail-closed, and compare-and-release.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import threading
import pytest

from src.aios_bridge.continuity.errors import ContinuityStateValidationError
from src.aios_bridge.continuity.executor import ExecutionOperation
from src.aios_bridge.continuity.lease import ExecutorLease
from src.aios_bridge.runtime_lease import AtomicExecutorLeaseStore


def _sample_lease(
    task_id: str = "TASK-029",
    lease_id: str = "lease-task-029-001",
    workspace_id: str = "1" * 64,
    executor_id: str = "antigravity",
    operation: ExecutionOperation = ExecutionOperation.RUN,
    execution_fingerprint: str = "2" * 64,
) -> ExecutorLease:
    return ExecutorLease(
        schema_version="1",
        lease_id=lease_id,
        task_id=task_id,
        workspace_id=workspace_id,
        executor_id=executor_id,
        operation=operation,
        execution_fingerprint=execution_fingerprint,
    )


def test_atomic_lease_store_acquire_and_load_active(tmp_path: Path):
    """First acquisition succeeds and load_active strictly returns the active lease."""
    ws_id = "1" * 64
    store = AtomicExecutorLeaseStore(lease_root=tmp_path, workspace_id=ws_id)
    lease = _sample_lease(workspace_id=ws_id)

    # 1. No active lease initially
    assert store.load_active(lease.task_id) is None

    # 2. Acquire succeeds
    acquired = store.acquire(lease)
    assert acquired == lease

    # 3. Active lease exists and matches
    active = store.load_active(lease.task_id)
    assert active == lease
    assert active.fingerprint() == lease.fingerprint()


def test_atomic_lease_store_acquire_conflict_fails_closed(tmp_path: Path):
    """Second acquisition attempt for an already-leased task fails closed (C9)."""
    ws_id = "1" * 64
    store = AtomicExecutorLeaseStore(lease_root=tmp_path, workspace_id=ws_id)
    lease1 = _sample_lease(lease_id="lease-01", workspace_id=ws_id)
    lease2 = _sample_lease(lease_id="lease-02", workspace_id=ws_id)

    store.acquire(lease1)

    with pytest.raises(ContinuityStateValidationError, match="already leased"):
        store.acquire(lease2)

    # First lease remains intact
    assert store.load_active(lease1.task_id) == lease1


def test_atomic_lease_store_workspace_mismatch_fails_closed(tmp_path: Path):
    """Acquiring a lease with mismatched workspace ID fails closed."""
    store = AtomicExecutorLeaseStore(lease_root=tmp_path, workspace_id="1" * 64)
    lease_other_ws = _sample_lease(workspace_id="2" * 64)

    with pytest.raises(ContinuityStateValidationError, match="workspace_id"):
        store.acquire(lease_other_ws)


def test_atomic_lease_store_concurrent_race_linearization(tmp_path: Path):
    """
    Two independent store instances concurrently attempting acquisition for the same task
    yields exactly one winner and one conflict (AIP-12).
    """
    ws_id = "1" * 64
    task_id = "TASK-029"

    store1 = AtomicExecutorLeaseStore(lease_root=tmp_path, workspace_id=ws_id)
    store2 = AtomicExecutorLeaseStore(lease_root=tmp_path, workspace_id=ws_id)

    lease1 = _sample_lease(task_id=task_id, lease_id="lease-contender-1", workspace_id=ws_id)
    lease2 = _sample_lease(task_id=task_id, lease_id="lease-contender-2", workspace_id=ws_id)

    barrier = threading.Barrier(2)
    results: list[tuple[str, Exception | ExecutorLease]] = []
    lock = threading.Lock()

    def _attempt(contender_name: str, store_instance: AtomicExecutorLeaseStore, lease_candidate: ExecutorLease):
        barrier.wait()
        try:
            res = store_instance.acquire(lease_candidate)
            with lock:
                results.append((contender_name, res))
        except Exception as e:
            with lock:
                results.append((contender_name, e))

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(_attempt, "c1", store1, lease1)
        f2 = executor.submit(_attempt, "c2", store2, lease2)
        f1.result()
        f2.result()

    successes = [r for r in results if isinstance(r[1], ExecutorLease)]
    conflicts = [r for r in results if isinstance(r[1], Exception)]

    assert len(successes) == 1, f"Expected exactly 1 success, got {len(successes)}"
    assert len(conflicts) == 1, f"Expected exactly 1 conflict, got {len(conflicts)}"
    assert isinstance(conflicts[0][1], ContinuityStateValidationError)

    winner_lease = successes[0][1]
    active_lease = store1.load_active(task_id)
    assert active_lease == winner_lease


def test_corrupt_empty_and_oversized_active_file_blocks_and_fails_closed(tmp_path: Path):
    """Corrupt, empty, or oversized active lease file fails closed without auto-repair or overwrite (C9 / C10)."""
    ws_id = "1" * 64
    store = AtomicExecutorLeaseStore(lease_root=tmp_path, workspace_id=ws_id)
    task_id = "TASK-029"
    active_path = tmp_path / task_id / "ACTIVE.json"
    active_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Empty file (0 bytes)
    active_path.write_bytes(b"")
    with pytest.raises(ContinuityStateValidationError, match="empty"):
        store.load_active(task_id)

    # Acquisition on existing empty file fails closed
    new_lease = _sample_lease(task_id=task_id, workspace_id=ws_id)
    with pytest.raises(ContinuityStateValidationError):
        store.acquire(new_lease)

    # 2. Corrupt JSON
    active_path.write_bytes(b"{bad json")
    with pytest.raises(ContinuityStateValidationError, match="Malformed JSON"):
        store.load_active(task_id)

    with pytest.raises(ContinuityStateValidationError):
        store.acquire(new_lease)

    # 3. Oversized file (> 16 KiB)
    active_path.write_bytes(b" " * 20000)
    with pytest.raises(ContinuityStateValidationError, match="exceeds maximum allowed size"):
        store.load_active(task_id)

    with pytest.raises(ContinuityStateValidationError):
        store.acquire(new_lease)


def test_require_active_validation(tmp_path: Path):
    """require_active strictly verifies active lease identity, fingerprint, and binding (C10 / C20)."""
    ws_id = "1" * 64
    store = AtomicExecutorLeaseStore(lease_root=tmp_path, workspace_id=ws_id)
    lease = _sample_lease(workspace_id=ws_id)

    # 1. No active lease fails
    with pytest.raises(ContinuityStateValidationError, match="No active executor lease found"):
        store.require_active(lease)

    # 2. Match succeeds
    store.acquire(lease)
    assert store.require_active(lease) == lease

    # 3. Mismatched lease_id fails
    stale_lease = _sample_lease(lease_id="lease-stale", workspace_id=ws_id)
    with pytest.raises(ContinuityStateValidationError, match="lease_id"):
        store.require_active(stale_lease)

    # 4. Mismatched execution_fingerprint fails
    drifted_lease = _sample_lease(execution_fingerprint="9" * 64, workspace_id=ws_id)
    with pytest.raises(ContinuityStateValidationError, match="execution_fingerprint"):
        store.require_active(drifted_lease)


def test_compare_and_release_lifecycle(tmp_path: Path):
    """release performs strict compare-and-release to history; stale releases are refused (C11)."""
    ws_id = "1" * 64
    store = AtomicExecutorLeaseStore(lease_root=tmp_path, workspace_id=ws_id)
    lease1 = _sample_lease(lease_id="lease-01", workspace_id=ws_id)

    store.acquire(lease1)

    # 1. Stale release attempt (wrong lease_id) is refused and active lease remains intact
    stale_candidate = _sample_lease(lease_id="lease-old", workspace_id=ws_id)
    with pytest.raises(ContinuityStateValidationError, match="lease_id"):
        store.release(stale_candidate)

    assert store.load_active(lease1.task_id) == lease1

    # 2. Exact release succeeds
    released = store.release(lease1)
    assert released == lease1
    assert store.load_active(lease1.task_id) is None

    # 3. History record created
    history_files = list((tmp_path / lease1.task_id / "history").glob("RELEASED-*.json"))
    assert len(history_files) == 1

    # 4. Now a new lease can be acquired cleanly
    lease2 = _sample_lease(lease_id="lease-02", workspace_id=ws_id)
    store.acquire(lease2)
    assert store.load_active(lease2.task_id) == lease2
