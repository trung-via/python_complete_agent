from __future__ import annotations

import json
import multiprocessing
import os
import tempfile
from pathlib import Path
from typing import Any

import pytest

from src.core.idempotency_contract import (
    ClaimStatus,
    IdempotencyCorruptionError,
    IdempotencyRecord,
    RecordKey,
    RecordStatus,
)
from src.core.idempotency_store_v2 import JsonlIdempotencyStore


def _make_key(op_key: str = "upload:file_123", idem_key: str = "req_001") -> RecordKey:
    return RecordKey(
        operation_key=op_key,
        idempotency_key=idem_key,
    )


def _claim_worker(
    db_path: str,
    barrier: Any,
    owner_id: str,
    result_queue: Any,
) -> None:
    store = JsonlIdempotencyStore(db_path=db_path)
    key = _make_key()

    barrier.wait()

    try:
        result = store.claim(key, owner_id)
        result_queue.put(
            {
                "owner_id": owner_id,
                "status": result.status.value,
                "attempt": result.record.attempt if result.record else None,
            }
        )
    except Exception as exc:
        result_queue.put(
            {
                "owner_id": owner_id,
                "error": f"{type(exc).__name__}: {exc}",
            }
        )


# ============================================================================
# 1. Test Claim Atomicity & Concurrency
# ============================================================================


def test_two_store_instances_same_process_claim_atomicity() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        key = _make_key()

        store_a = JsonlIdempotencyStore(db_path=db_path)
        store_b = JsonlIdempotencyStore(db_path=db_path)

        first = store_a.claim(key, "owner-a")
        second = store_b.claim(key, "owner-b")

        assert first.status == ClaimStatus.CLAIMED
        assert second.status == ClaimStatus.ALREADY_IN_PROGRESS


@pytest.mark.skipif(
    multiprocessing.get_start_method(allow_none=True) == "fork"
    and os.name == "nt",
    reason="Windows multiprocessing requires spawn.",
)
def test_two_real_processes_claim_atomicity() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        Path(db_path).touch()

        context = multiprocessing.get_context("spawn")
        barrier = context.Barrier(2)
        result_queue = context.Queue()

        workers = [
            context.Process(
                target=_claim_worker,
                args=(db_path, barrier, f"owner-{index}", result_queue),
            )
            for index in range(2)
        ]

        for worker in workers:
            worker.start()

        results = [result_queue.get(timeout=10) for _ in workers]

        for worker in workers:
            worker.join(timeout=10)
            assert worker.exitcode == 0

        successful_claims = [
            r for r in results if r.get("status") == ClaimStatus.CLAIMED.value
        ]
        in_progress_claims = [
            r
            for r in results
            if r.get("status") == ClaimStatus.ALREADY_IN_PROGRESS.value
        ]

        assert len(successful_claims) == 1
        assert len(in_progress_claims) == 1


# ============================================================================
# 2. Test Persistence-Before-Memory Invariant
# ============================================================================


def test_claim_persistence_failure_reverts_memory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        key = _make_key()
        store = JsonlIdempotencyStore(db_path=db_path)

        def fail_append(record: IdempotencyRecord) -> None:
            raise OSError("disk write error")

        monkeypatch.setattr(store, "_append", fail_append)

        with pytest.raises(OSError):
            store.claim(key, "owner-a")

        assert store.get(key) is None

        reloaded = JsonlIdempotencyStore(db_path=db_path)
        assert reloaded.get(key) is None


def test_complete_persistence_failure_preserves_in_progress(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        key = _make_key()
        store = JsonlIdempotencyStore(db_path=db_path)

        claim = store.claim(key, "owner-a")
        assert claim.status == ClaimStatus.CLAIMED

        def fail_append(record: IdempotencyRecord) -> None:
            raise OSError("disk write error")

        monkeypatch.setattr(store, "_append", fail_append)

        with pytest.raises(OSError):
            store.complete(key, "owner-a", data={"file_id": "123"})

        current = store.get(key)
        assert current is not None
        assert current.status == RecordStatus.IN_PROGRESS

        reloaded = JsonlIdempotencyStore(db_path=db_path)
        durable = reloaded.get(key)
        assert durable is not None
        assert durable.status == RecordStatus.IN_PROGRESS


def test_fail_persistence_failure_preserves_in_progress(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        key = _make_key()
        store = JsonlIdempotencyStore(db_path=db_path)

        claim = store.claim(key, "owner-a")
        assert claim.status == ClaimStatus.CLAIMED

        def fail_append(record: IdempotencyRecord) -> None:
            raise OSError("disk write error")

        monkeypatch.setattr(store, "_append", fail_append)

        with pytest.raises(OSError):
            store.fail(key, "owner-a", retryable=True, data={"err": "timeout"})

        current = store.get(key)
        assert current is not None
        assert current.status == RecordStatus.IN_PROGRESS

        reloaded = JsonlIdempotencyStore(db_path=db_path)
        durable = reloaded.get(key)
        assert durable is not None
        assert durable.status == RecordStatus.IN_PROGRESS


# ============================================================================
# 3. Test Restart Durability across All States
# ============================================================================


def test_restart_durability_claimed_becomes_in_progress() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        key = _make_key()

        store1 = JsonlIdempotencyStore(db_path=db_path)
        claim1 = store1.claim(key, "owner-1")
        assert claim1.status == ClaimStatus.CLAIMED

        store2 = JsonlIdempotencyStore(db_path=db_path)
        claim2 = store2.claim(key, "owner-2")
        assert claim2.status == ClaimStatus.ALREADY_IN_PROGRESS
        assert claim2.record is not None
        assert claim2.record.status == RecordStatus.IN_PROGRESS
        assert claim2.record.owner_id == "owner-1"


def test_restart_durability_completed_replays() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        key = _make_key()

        store1 = JsonlIdempotencyStore(db_path=db_path)
        store1.claim(key, "owner-1")
        store1.complete(key, "owner-1", data={"output": "hello"})

        store2 = JsonlIdempotencyStore(db_path=db_path)
        claim2 = store2.claim(key, "owner-2")

        assert claim2.status == ClaimStatus.ALREADY_COMPLETED
        assert claim2.record is not None
        assert claim2.record.data == {"output": "hello"}


def test_restart_durability_recoverable_reclaims_with_attempt_increment() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        key = _make_key()

        store1 = JsonlIdempotencyStore(db_path=db_path)
        store1.claim(key, "owner-1")
        store1.fail(key, "owner-1", retryable=True, data={"reason": "temp_500"})

        store2 = JsonlIdempotencyStore(db_path=db_path)
        claim2 = store2.claim(key, "owner-2")

        assert claim2.status == ClaimStatus.CLAIMED
        assert claim2.record is not None
        assert claim2.record.owner_id == "owner-2"
        assert claim2.record.attempt == 2
        assert claim2.record.status == RecordStatus.IN_PROGRESS


def test_restart_durability_failed_blocks_permanently() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        key = _make_key()

        store1 = JsonlIdempotencyStore(db_path=db_path)
        store1.claim(key, "owner-1")
        store1.fail(key, "owner-1", retryable=False, data={"reason": "bad_schema"})

        store2 = JsonlIdempotencyStore(db_path=db_path)
        claim2 = store2.claim(key, "owner-2")

        assert claim2.status == ClaimStatus.FAILED_PERMANENT
        assert claim2.record is not None
        assert claim2.record.status == RecordStatus.FAILED


# ============================================================================
# 4. Test Corrupt JSONL Records
# ============================================================================


def _write_jsonl(db_path: str, lines: list[str | dict[str, Any]]) -> None:
    with open(db_path, "w", encoding="utf-8") as handle:
        for line in lines:
            if isinstance(line, dict):
                handle.write(json.dumps(line) + "\n")
            else:
                handle.write(line + "\n")


def test_corrupt_jsonl_malformed_json_raises_corruption_error() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        _write_jsonl(db_path, ["{this is not json}"])

        with pytest.raises(IdempotencyCorruptionError, match="Invalid JSON"):
            JsonlIdempotencyStore(db_path=db_path)


def test_corrupt_jsonl_missing_required_fields_raises_corruption_error() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        bad_payload = {
            "key": {"operation_key": "op1", "idempotency_key": "id1"},
            "status": "IN_PROGRESS",
            # missing created_at, updated_at, owner_id, attempt, data
        }
        _write_jsonl(db_path, [bad_payload])

        with pytest.raises(IdempotencyCorruptionError, match="Missing fields"):
            JsonlIdempotencyStore(db_path=db_path)


def test_corrupt_jsonl_invalid_status_raises_corruption_error() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        bad_payload = {
            "key": {"operation_key": "op1", "idempotency_key": "id1"},
            "status": "INVALID_STATUS_NAME",
            "created_at": 100.0,
            "updated_at": 100.0,
            "owner_id": "owner-1",
            "attempt": 1,
            "data": None,
        }
        _write_jsonl(db_path, [bad_payload])

        with pytest.raises(IdempotencyCorruptionError, match="Invalid RecordStatus"):
            JsonlIdempotencyStore(db_path=db_path)


def test_corrupt_jsonl_invalid_record_key_raises_corruption_error() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        bad_payload = {
            "key": {"operation_key": "", "idempotency_key": "id1"},  # empty op_key
            "status": "IN_PROGRESS",
            "created_at": 100.0,
            "updated_at": 100.0,
            "owner_id": "owner-1",
            "attempt": 1,
            "data": None,
        }
        _write_jsonl(db_path, [bad_payload])

        with pytest.raises(IdempotencyCorruptionError, match="Invalid RecordKey"):
            JsonlIdempotencyStore(db_path=db_path)


def test_corrupt_jsonl_invalid_attempt_raises_corruption_error() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        bad_payload = {
            "key": {"operation_key": "op1", "idempotency_key": "id1"},
            "status": "IN_PROGRESS",
            "created_at": 100.0,
            "updated_at": 100.0,
            "owner_id": "owner-1",
            "attempt": 0,  # attempt < 1
            "data": None,
        }
        _write_jsonl(db_path, [bad_payload])

        with pytest.raises(IdempotencyCorruptionError, match="attempt must be >= 1"):
            JsonlIdempotencyStore(db_path=db_path)


def test_corrupt_jsonl_timestamp_rollback_raises_corruption_error() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        rec1 = {
            "key": {"operation_key": "op1", "idempotency_key": "id1"},
            "status": "IN_PROGRESS",
            "created_at": 100.0,
            "updated_at": 200.0,
            "owner_id": "owner-1",
            "attempt": 1,
            "data": None,
        }
        rec2 = {
            "key": {"operation_key": "op1", "idempotency_key": "id1"},
            "status": "COMPLETED",
            "created_at": 100.0,
            "updated_at": 150.0,  # timestamp rollback!
            "owner_id": "owner-1",
            "attempt": 1,
            "data": {},
        }
        _write_jsonl(db_path, [rec1, rec2])

        with pytest.raises(
            IdempotencyCorruptionError, match="moved backwards"
        ):
            JsonlIdempotencyStore(db_path=db_path)


# ============================================================================
# 5. Test Lock Cleanup on Exceptions
# ============================================================================


def test_lock_cleanup_on_exception_allows_subsequent_acquire(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        key = _make_key()
        store1 = JsonlIdempotencyStore(db_path=db_path)

        def blow_up(*args: Any, **kwargs: Any) -> None:
            raise RuntimeError("unexpected error inside critical section")

        monkeypatch.setattr(store1, "_reload_locked", blow_up)

        with pytest.raises(RuntimeError, match="unexpected error inside critical section"):
            store1.claim(key, "owner-1")

        # Next store instance should acquire lock cleanly without deadlocking
        store2 = JsonlIdempotencyStore(db_path=db_path)
        claim2 = store2.claim(key, "owner-2")
        assert claim2.status == ClaimStatus.CLAIMED


# ============================================================================
# 6. Test Snapshot Refresh
# ============================================================================


def test_snapshot_refresh_store_b_sees_latest_state_from_store_a() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        key = _make_key()

        # Both stores created up front
        store_a = JsonlIdempotencyStore(db_path=db_path)
        store_b = JsonlIdempotencyStore(db_path=db_path)

        # Store A claims and completes
        claim_a = store_a.claim(key, "owner-a")
        assert claim_a.status == ClaimStatus.CLAIMED

        store_a.complete(key, "owner-a", data={"file": "uploaded"})

        # Store B get() must auto-refresh and see COMPLETED
        record_b = store_b.get(key)
        assert record_b is not None
        assert record_b.status == RecordStatus.COMPLETED
        assert record_b.data == {"file": "uploaded"}

        # Store B claim() must return ALREADY_COMPLETED
        claim_b = store_b.claim(key, "owner-b")
        assert claim_b.status == ClaimStatus.ALREADY_COMPLETED
