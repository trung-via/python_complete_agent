from __future__ import annotations

import multiprocessing
import os
import tempfile
from pathlib import Path
from typing import Any

import pytest

from src.core.idempotency_contract import (
    ClaimStatus,
    IdempotencyRecord,
    RecordKey,
    RecordStatus,
)
from src.core.idempotency_store_v2 import JsonlIdempotencyStore


def _make_key() -> RecordKey:
    return RecordKey(
        operation_key="upload:sha256_abc",
        idempotency_key="req_001",
    )


def _claim_worker(
    db_path: str,
    barrier: Any,
    owner_id: str,
    result_queue: Any,
) -> None:
    """
    Run a real cross-process claim against the same JSONL store.

    Each worker creates its own store instance before waiting at the barrier,
    ensuring both processes start with the same persisted snapshot.
    """
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


def _read_records(db_path: str) -> list[dict[str, Any]]:
    import json

    records: list[dict[str, Any]] = []

    with open(db_path, "r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                records.append(json.loads(line))

    return records


def test_two_store_instances_expose_stale_snapshot_race() -> None:
    """
    Documents the current blocker: independent store instances do not
    re-read the JSONL file before claim(), so both can claim the same key.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        key = _make_key()

        store_a = JsonlIdempotencyStore(db_path=db_path)
        store_b = JsonlIdempotencyStore(db_path=db_path)

        first = store_a.claim(key, "owner-a")
        second = store_b.claim(key, "owner-b")

        assert first.status == ClaimStatus.CLAIMED

        # This is expected to FAIL until claim() uses cross-instance
        # synchronization / filesystem locking.
        assert second.status == ClaimStatus.ALREADY_IN_PROGRESS


@pytest.mark.skipif(
    multiprocessing.get_start_method(allow_none=True) == "fork"
    and os.name == "nt",
    reason="Windows multiprocessing requires a different process setup.",
)
def test_two_processes_only_one_claims_key() -> None:
    """
    Verifies the production-level invariant that exactly one process may
    successfully claim a previously unseen idempotency key.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")

        # Ensure the file exists before worker initialization so both
        # processes observe the same initial store state.
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
            result
            for result in results
            if result.get("status") == ClaimStatus.CLAIMED.value
        ]

        already_in_progress = [
            result
            for result in results
            if result.get("status") == ClaimStatus.ALREADY_IN_PROGRESS.value
        ]

        # This is expected to FAIL until filesystem-level atomic claiming
        # is implemented.
        assert len(successful_claims) == 1
        assert len(already_in_progress) == 1


def test_claim_persistence_failure_does_not_commit_memory_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Verifies the commit invariant for claim():

        persistence failure => transition must not become visible as committed.

    The current implementation mutates _records before _append(), so this
    test exposes the memory/disk divergence blocker.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        key = _make_key()
        store = JsonlIdempotencyStore(db_path=db_path)

        def fail_append(record: IdempotencyRecord) -> None:
            raise OSError("simulated disk full")

        monkeypatch.setattr(store, "_append", fail_append)

        with pytest.raises(OSError):
            store.claim(key, "owner-a")

        # This is expected to FAIL against the current implementation:
        # _records was updated before _append() raised.
        assert store.get(key) is None

        reloaded = JsonlIdempotencyStore(db_path=db_path)

        assert reloaded.get(key) is None


def test_complete_persistence_failure_does_not_commit_memory_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Verifies the commit invariant for complete():

        persistence failure => record must remain IN_PROGRESS.

    The current implementation updates _records before _append(), so memory
    becomes COMPLETED while durable storage remains IN_PROGRESS.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        key = _make_key()
        store = JsonlIdempotencyStore(db_path=db_path)

        claim = store.claim(key, "owner-a")

        assert claim.status == ClaimStatus.CLAIMED

        def fail_append(record: IdempotencyRecord) -> None:
            raise OSError("simulated disk full")

        monkeypatch.setattr(store, "_append", fail_append)

        with pytest.raises(OSError):
            store.complete(
                key,
                "owner-a",
                data={"file_id": "drive-123"},
            )

        # This is expected to FAIL against the current implementation:
        # memory has already been changed to COMPLETED.
        current = store.get(key)
        assert current is not None
        assert current.status == RecordStatus.IN_PROGRESS

        # Disk should still contain the original IN_PROGRESS record.
        reloaded = JsonlIdempotencyStore(db_path=db_path)
        durable = reloaded.get(key)

        assert durable is not None
        assert durable.status == RecordStatus.IN_PROGRESS


def test_fail_persistence_failure_does_not_commit_memory_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Covers the same persistence invariant for fail().

    This is intentionally separate from complete() because both transition
    paths must preserve the same commit semantics.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        key = _make_key()
        store = JsonlIdempotencyStore(db_path=db_path)

        claim = store.claim(key, "owner-a")

        assert claim.status == ClaimStatus.CLAIMED

        def fail_append(record: IdempotencyRecord) -> None:
            raise OSError("simulated disk full")

        monkeypatch.setattr(store, "_append", fail_append)

        with pytest.raises(OSError):
            store.fail(
                key,
                "owner-a",
                retryable=True,
                data={"reason": "temporary failure"},
            )

        current = store.get(key)
        assert current is not None
        assert current.status == RecordStatus.IN_PROGRESS

        reloaded = JsonlIdempotencyStore(db_path=db_path)
        durable = reloaded.get(key)

        assert durable is not None
        assert durable.status == RecordStatus.IN_PROGRESS
