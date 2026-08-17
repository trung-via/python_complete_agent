"""
Unit tests for Runtime Atomic Executor Lease Store (ADR-019 / TASK-029).
Validates atomic create-if-absent, concurrent race linearization, corrupt file fail-closed, and compare-and-release.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import threading
import time
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


def test_deterministic_compare_and_release_toctou_interleaving_proof(tmp_path: Path):
    """
    Validates R1-1: Proves deterministically using a test seam hook in release() with ZERO sleep that:
    1. While Releaser 1 has validated require_active(lease_a) and is paused inside its critical section,
       direct non-blocking probes prove that the in-process RLock and OS file lock are held.
    2. Competing contender (Acquirer B) is launched and cannot finish while the lock is held.
    3. Once Releaser 1 finishes release and unblocks, Acquirer B acquires Lease B.
    4. Stale Releaser 3 attempting to release Lease A fails closed with ContinuityStateValidationError
       and CANNOT remove Lease B.
    """
    from src.aios_bridge.runtime_lease import _get_task_thread_lock

    ws_id = "1" * 64
    task_id = "TASK-029"
    store1 = AtomicExecutorLeaseStore(lease_root=tmp_path, workspace_id=ws_id)
    store2 = AtomicExecutorLeaseStore(lease_root=tmp_path, workspace_id=ws_id)
    store3 = AtomicExecutorLeaseStore(lease_root=tmp_path, workspace_id=ws_id)

    # 1. Lease A active
    lease_a = _sample_lease(task_id=task_id, lease_id="lease-a", workspace_id=ws_id)
    store1.acquire(lease_a)
    assert store1.load_active(task_id) == lease_a

    lease_b = _sample_lease(task_id=task_id, lease_id="lease-b", workspace_id=ws_id)

    hook_entered = threading.Event()
    hook_continue = threading.Event()
    contender_finished = threading.Event()
    contender_result = {}

    def pre_replace_hook(l):
        # 1. Deterministic lock probe: non-blocking probe on in-process task thread lock MUST fail
        task_thread_lock = _get_task_thread_lock(task_id)
        # Attempt non-blocking acquire from a temporary probe thread
        probe_results = {}
        def _probe_in_process_lock():
            probe_results["acquired"] = task_thread_lock.acquire(blocking=False)
            if probe_results["acquired"]:
                task_thread_lock.release()

        t_probe = threading.Thread(target=_probe_in_process_lock)
        t_probe.start()
        t_probe.join()
        assert probe_results.get("acquired") is False, "Task thread lock must be actively held by Releaser 1"

        # 2. Deterministic OS file lock probe: non-blocking lock on .lease_mutation.lock MUST fail
        lock_file = tmp_path / task_id / ".lease_mutation.lock"
        probe_fd = os.open(str(lock_file), os.O_RDWR | getattr(os, "O_BINARY", 0))
        try:
            if os.name == "nt":
                import msvcrt
                with pytest.raises(OSError):
                    msvcrt.locking(probe_fd, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                with pytest.raises((BlockingIOError, OSError)):
                    fcntl.flock(probe_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        finally:
            os.close(probe_fd)

        hook_entered.set()
        # Wait until test runner signals to continue (zero sleep)
        hook_continue.wait(timeout=5.0)

    def _competing_acquirer():
        try:
            res = store2.acquire(lease_b)
            contender_result["acquirer_b"] = res
        except Exception as e:
            contender_result["acquirer_b"] = e
        finally:
            contender_finished.set()

    with ThreadPoolExecutor(max_workers=2) as executor:
        f_releaser = executor.submit(lambda: store1.release(lease_a, _test_pre_replace_hook=pre_replace_hook))

        # Wait until Releaser 1 is inside critical section and has validated active lease
        hook_entered.wait(timeout=5.0)

        # Launch contender while Releaser 1 is inside critical section
        f_contender = executor.submit(_competing_acquirer)

        # Verify that contender cannot be finished while hook_continue is not set
        assert not contender_finished.is_set(), "Contender cannot finish while Releaser 1 holds critical section"

        # Signal Releaser 1 to complete os.replace and release lock
        hook_continue.set()

        released_a = f_releaser.result()
        f_contender.result()

    assert released_a == lease_a
    assert contender_result["acquirer_b"] == lease_b

    # Now Stale Releaser 3 attempts to release lease A -> MUST FAIL CLOSED
    with pytest.raises(ContinuityStateValidationError, match="lease_id"):
        store3.release(lease_a)

    # Invariant: Active lease MUST BE Lease B and was NEVER removed by stale releaser!
    assert store1.load_active(task_id) == lease_b


def test_concurrent_compare_and_release_interleaving_race_protection(tmp_path: Path):
    """
    Validates R1-1: Concurrent race where Releaser 1, Acquirer B, and Stale Releaser 2 interact concurrently.
    Proves that even when Stale Releaser 2 runs concurrently with or after Acquirer B, Lease B is NEVER removed,
    and Stale Releaser 2 fails closed.
    """
    ws_id = "1" * 64
    task_id = "TASK-029"
    store1 = AtomicExecutorLeaseStore(lease_root=tmp_path, workspace_id=ws_id)
    store2 = AtomicExecutorLeaseStore(lease_root=tmp_path, workspace_id=ws_id)
    store3 = AtomicExecutorLeaseStore(lease_root=tmp_path, workspace_id=ws_id)

    # 1. Lease A is active initially
    lease_a = _sample_lease(task_id=task_id, lease_id="lease-a", workspace_id=ws_id)
    store1.acquire(lease_a)
    assert store1.load_active(task_id) == lease_a

    lease_b = _sample_lease(task_id=task_id, lease_id="lease-b", workspace_id=ws_id)

    release_a_done = threading.Event()
    acquire_b_done = threading.Event()
    results = {}
    lock = threading.Lock()

    def _worker_release_a():
        try:
            res = store1.release(lease_a)
            with lock:
                results["releaser_1"] = res
        except Exception as e:
            with lock:
                results["releaser_1"] = e
        finally:
            release_a_done.set()

    def _worker_acquire_b():
        release_a_done.wait(timeout=5.0)
        try:
            res = store2.acquire(lease_b)
            with lock:
                results["acquirer_b"] = res
        except Exception as e:
            with lock:
                results["acquirer_b"] = e
        finally:
            acquire_b_done.set()

    def _worker_stale_release_a():
        acquire_b_done.wait(timeout=5.0)
        try:
            res = store3.release(lease_a)
            with lock:
                results["stale_releaser_2"] = res
        except Exception as e:
            with lock:
                results["stale_releaser_2"] = e

    with ThreadPoolExecutor(max_workers=3) as executor:
        f1 = executor.submit(_worker_release_a)
        f2 = executor.submit(_worker_acquire_b)
        f3 = executor.submit(_worker_stale_release_a)
        f1.result()
        f2.result()
        f3.result()

    # Releaser 1 succeeded
    assert results["releaser_1"] == lease_a
    # Acquirer B succeeded
    assert results["acquirer_b"] == lease_b
    # Stale Releaser 2 failed closed with ContinuityStateValidationError
    assert isinstance(results["stale_releaser_2"], ContinuityStateValidationError)
    assert "lease_id" in str(results["stale_releaser_2"])

    # Invariant: Active lease MUST BE Lease B and was NEVER removed by stale releaser!
    assert store1.load_active(task_id) == lease_b


def test_cross_process_lease_mutation_guard(tmp_path: Path):
    """
    Validates R1-1: OS file lock synchronization across independent Python processes.
    """
    import subprocess
    import sys

    ws_id = "1" * 64
    task_id = "TASK-029"
    sync_file = tmp_path / "sync.txt"
    repo_path = Path.cwd().resolve()

    code = f"""
import sys, time
from pathlib import Path
sys.path.insert(0, r"{repo_path}")
from src.aios_bridge.runtime_lease import AtomicExecutorLeaseStore
from src.aios_bridge.continuity.lease import ExecutorLease
from src.aios_bridge.continuity.executor import ExecutionOperation

store = AtomicExecutorLeaseStore(lease_root=Path(r"{tmp_path}"), workspace_id="{ws_id}")
lease = ExecutorLease(
    schema_version="1",
    lease_id="lease-proc-1",
    task_id="{task_id}",
    workspace_id="{ws_id}",
    executor_id="antigravity",
    operation=ExecutionOperation.RUN,
    execution_fingerprint="2" * 64,
)
store.acquire(lease)
Path(r"{sync_file}").write_text("acquired", encoding="utf-8")
time.sleep(0.5)
"""
    p = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for _ in range(50):
            if sync_file.exists():
                break
            time.sleep(0.05)
        assert sync_file.exists()

        # In current process, acquiring another lease for same task must fail closed immediately
        store = AtomicExecutorLeaseStore(lease_root=tmp_path, workspace_id=ws_id)
        lease2 = _sample_lease(task_id=task_id, lease_id="lease-proc-2", workspace_id=ws_id)
        with pytest.raises(ContinuityStateValidationError, match="already leased"):
            store.acquire(lease2)
    finally:
        p.wait()


def test_failed_writer_cleanup_safety_when_open_fails(tmp_path: Path, monkeypatch):
    """
    Validates R1-2: Failed writer cleanup NEVER unlinks somebody else's lease when failure occurs during/before open.
    """
    ws_id = "1" * 64
    store = AtomicExecutorLeaseStore(lease_root=tmp_path, workspace_id=ws_id)
    task_id = "TASK-029"

    # Pre-existing active lease
    existing_lease = _sample_lease(task_id=task_id, lease_id="lease-existing", workspace_id=ws_id)
    store.acquire(existing_lease)

    # Fault-inject os.open to raise an unexpected error when contender attempts opening ACTIVE.json
    real_open = os.open
    def fake_open(path, flags, mode=0o777):
        if "ACTIVE.json" in str(path):
            raise PermissionError("Simulated filesystem permission error before file creation")
        return real_open(path, flags, mode)

    monkeypatch.setattr(os, "open", fake_open)

    contender_lease = _sample_lease(task_id=task_id, lease_id="lease-contender", workspace_id=ws_id)
    with pytest.raises(ContinuityStateValidationError, match="Simulated filesystem permission error"):
        store.acquire(contender_lease)

    # Unpatch and verify existing lease was NOT unlinked!
    monkeypatch.undo()
    assert store.load_active(task_id) == existing_lease


def test_failed_writer_cleanup_only_removes_own_created_file_on_write_error(tmp_path: Path, monkeypatch):
    """
    Validates R1-2 & R1-3: When this call created the file but failed during write, it unlinks the broken file.
    """
    ws_id = "1" * 64
    store = AtomicExecutorLeaseStore(lease_root=tmp_path, workspace_id=ws_id)
    task_id = "TASK-029"

    def fake_write(fd, data):
        raise OSError("Simulated disk I/O failure during write")

    monkeypatch.setattr(os, "write", fake_write)

    lease = _sample_lease(task_id=task_id, workspace_id=ws_id)
    with pytest.raises(ContinuityStateValidationError, match="Simulated disk I/O failure"):
        store.acquire(lease)

    monkeypatch.undo()
    # Incomplete file was cleanly unlinked and load_active returns None
    assert store.load_active(task_id) is None


def test_partial_write_fault_injection_fails_closed(tmp_path: Path, monkeypatch):
    """
    Validates R1-3: os.write returning 0 bytes causes acquire to fail closed.
    """
    ws_id = "1" * 64
    store = AtomicExecutorLeaseStore(lease_root=tmp_path, workspace_id=ws_id)
    task_id = "TASK-029"

    def fake_write(fd, data):
        return 0  # 0 bytes written

    monkeypatch.setattr(os, "write", fake_write)

    lease = _sample_lease(task_id=task_id, workspace_id=ws_id)
    with pytest.raises(ContinuityStateValidationError, match="Zero bytes written"):
        store.acquire(lease)

    monkeypatch.undo()
    assert store.load_active(task_id) is None


def test_fsync_failure_fault_injection_fails_closed(tmp_path: Path, monkeypatch):
    """
    Validates R1-3: os.fsync raising OSError causes acquire to fail closed.
    """
    ws_id = "1" * 64
    store = AtomicExecutorLeaseStore(lease_root=tmp_path, workspace_id=ws_id)
    task_id = "TASK-029"

    def fake_fsync(fd):
        raise OSError(5, "Simulated hardware I/O error on fsync")

    monkeypatch.setattr(os, "fsync", fake_fsync)

    lease = _sample_lease(task_id=task_id, workspace_id=ws_id)
    with pytest.raises(ContinuityStateValidationError, match="Durable fsync failed"):
        store.acquire(lease)

    monkeypatch.undo()
    assert store.load_active(task_id) is None
