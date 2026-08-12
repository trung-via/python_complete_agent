from __future__ import annotations

import os
import tempfile
import time
from typing import Any

import pytest

from src.core.idempotency_contract import (
    ClaimStatus,
    IdempotencyRecord,
    RecordKey,
    RecordStatus,
)
from src.core.idempotency_store_v2 import (
    InMemoryIdempotencyStore,
    JsonlIdempotencyStore,
)


def _make_key(op_key: str = "op:ttl_test", idem_key: str = "idem_001") -> RecordKey:
    return RecordKey(operation_key=op_key, idempotency_key=idem_key)


def test_ttl_invalid_values_rejected() -> None:
    with pytest.raises(ValueError, match="ttl_seconds must be > 0"):
        JsonlIdempotencyStore(db_path="dummy.jsonl", ttl_seconds=0)

    with pytest.raises(ValueError, match="ttl_seconds must be > 0"):
        JsonlIdempotencyStore(db_path="dummy.jsonl", ttl_seconds=-10)

    with pytest.raises(TypeError, match="ttl_seconds must be a number or None"):
        JsonlIdempotencyStore(db_path="dummy.jsonl", ttl_seconds=True)

    with pytest.raises(TypeError, match="ttl_seconds must be a number or None"):
        InMemoryIdempotencyStore(ttl_seconds="100")  # type: ignore[arg-type]


def test_in_memory_store_ttl_unexpired_returns_already_in_progress() -> None:
    store = InMemoryIdempotencyStore(ttl_seconds=60)
    key = _make_key()

    claim1 = store.claim(key, "owner-1")
    assert claim1.status == ClaimStatus.CLAIMED

    claim2 = store.claim(key, "owner-2")
    assert claim2.status == ClaimStatus.ALREADY_IN_PROGRESS

    rec = store.get(key)
    assert rec is not None
    assert rec.status == RecordStatus.IN_PROGRESS


def test_in_memory_store_ttl_expired_reclaims_atomically(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = InMemoryIdempotencyStore(ttl_seconds=10)
    key = _make_key()

    now = time.time()
    monkeypatch.setattr(time, "time", lambda: now)

    claim1 = store.claim(key, "owner-1")
    assert claim1.status == ClaimStatus.CLAIMED
    assert claim1.record.attempt == 1

    # Advance time past TTL (15s > 10s)
    monkeypatch.setattr(time, "time", lambda: now + 15)

    # get() should reflect RECOVERABLE
    rec = store.get(key)
    assert rec is not None
    assert rec.status == RecordStatus.RECOVERABLE

    # claim() should succeed and increment attempt
    claim2 = store.claim(key, "owner-2")
    assert claim2.status == ClaimStatus.CLAIMED
    assert claim2.record.attempt == 2
    assert claim2.record.owner_id == "owner-2"
    assert claim2.record.created_at == claim1.record.created_at
    assert claim2.record.updated_at == now + 15


def test_jsonl_store_ttl_unexpired_returns_already_in_progress() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        store = JsonlIdempotencyStore(db_path=db_path, ttl_seconds=60)
        key = _make_key()

        claim1 = store.claim(key, "owner-1")
        assert claim1.status == ClaimStatus.CLAIMED

        claim2 = store.claim(key, "owner-2")
        assert claim2.status == ClaimStatus.ALREADY_IN_PROGRESS

        rec = store.get(key)
        assert rec is not None
        assert rec.status == RecordStatus.IN_PROGRESS


def test_jsonl_store_ttl_expired_reclaims_atomically(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        store1 = JsonlIdempotencyStore(db_path=db_path, ttl_seconds=5)
        key = _make_key()

        now = time.time()
        monkeypatch.setattr(time, "time", lambda: now)

        claim1 = store1.claim(key, "owner-1")
        assert claim1.status == ClaimStatus.CLAIMED
        assert claim1.record.attempt == 1

        # Advance time by 10s (> 5s TTL)
        monkeypatch.setattr(time, "time", lambda: now + 10)

        # Fresh store instance reading disk
        store2 = JsonlIdempotencyStore(db_path=db_path, ttl_seconds=5)

        # get() reflects RECOVERABLE due to expiration
        rec = store2.get(key)
        assert rec is not None
        assert rec.status == RecordStatus.RECOVERABLE

        # Second store claims the expired claim
        claim2 = store2.claim(key, "owner-2")
        assert claim2.status == ClaimStatus.CLAIMED
        assert claim2.record.attempt == 2
        assert claim2.record.owner_id == "owner-2"
        assert claim2.record.created_at == claim1.record.created_at
        assert claim2.record.updated_at == now + 10


def test_jsonl_store_ttl_none_never_expires(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        store = JsonlIdempotencyStore(db_path=db_path, ttl_seconds=None)
        key = _make_key()

        now = time.time()
        monkeypatch.setattr(time, "time", lambda: now)

        claim1 = store.claim(key, "owner-1")
        assert claim1.status == ClaimStatus.CLAIMED

        # Advance time by 1000 days
        monkeypatch.setattr(time, "time", lambda: now + 86400 * 1000)

        claim2 = store.claim(key, "owner-2")
        assert claim2.status == ClaimStatus.ALREADY_IN_PROGRESS

        rec = store.get(key)
        assert rec is not None
        assert rec.status == RecordStatus.IN_PROGRESS


def test_ttl_reclaim_persistence_failure_reverts_memory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        store = JsonlIdempotencyStore(db_path=db_path, ttl_seconds=5)
        key = _make_key()

        now = time.time()
        monkeypatch.setattr(time, "time", lambda: now)

        claim1 = store.claim(key, "owner-1")
        assert claim1.status == ClaimStatus.CLAIMED

        # Advance time past TTL
        monkeypatch.setattr(time, "time", lambda: now + 10)

        # Inject disk failure on append
        def fail_append(record: IdempotencyRecord) -> None:
            raise OSError("simulated disk full")

        monkeypatch.setattr(store, "_append", fail_append)

        with pytest.raises(OSError, match="simulated disk full"):
            store.claim(key, "owner-2")

        # Memory snapshot must preserve original claim
        rec = store.get(key)
        assert rec is not None
        assert rec.owner_id == "owner-1"
