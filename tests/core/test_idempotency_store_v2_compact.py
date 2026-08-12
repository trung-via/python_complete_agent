from __future__ import annotations

import json
import os
import tempfile
from typing import Any

import pytest

from src.core.idempotency_contract import (
    ClaimStatus,
    RecordKey,
    RecordStatus,
)
from src.core.idempotency_store_v2 import JsonlIdempotencyStore


def _make_key(op: str = "op:compact", idem: str = "key_1") -> RecordKey:
    return RecordKey(operation_key=op, idempotency_key=idem)


# 1. compact_empty_store
def test_compact_empty_store() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        store = JsonlIdempotencyStore(db_path=db_path)
        store.compact()

        if os.path.exists(db_path):
            with open(db_path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
            assert len(lines) == 0


# 2. compact_keeps_latest_record_per_key
def test_compact_keeps_latest_record_per_key() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        store = JsonlIdempotencyStore(db_path=db_path)
        k = _make_key("op:mutating", "k1")

        # Mutations: claim (attempt 1) -> fail (retryable) -> claim (attempt 2) -> complete
        store.claim(k, "owner-1")
        store.fail(k, "owner-1", retryable=True, data={"v": 1})
        store.claim(k, "owner-2")
        store.complete(k, "owner-2", data={"v": 2})

        store.compact()

        # Should retain only attempt 2 COMPLETED
        r = store.get(k)
        assert r is not None
        assert r.status == RecordStatus.COMPLETED
        assert r.attempt == 2
        assert r.owner_id == "owner-2"
        assert r.data == {"v": 2}


# 3. compact_preserves_all_record_states
def test_compact_preserves_all_record_states() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        store = JsonlIdempotencyStore(db_path=db_path)

        k_prog = _make_key("op:state", "in_prog")
        k_comp = _make_key("op:state", "completed")
        k_rec = _make_key("op:state", "recoverable")
        k_fail = _make_key("op:state", "failed")

        store.claim(k_prog, "owner-1")

        store.claim(k_comp, "owner-1")
        store.complete(k_comp, "owner-1", data={"done": True})

        store.claim(k_rec, "owner-1")
        store.fail(k_rec, "owner-1", retryable=True)

        store.claim(k_fail, "owner-1")
        store.fail(k_fail, "owner-1", retryable=False)

        store.compact()

        assert store.get(k_prog).status == RecordStatus.IN_PROGRESS  # type: ignore[union-attr]
        assert store.get(k_comp).status == RecordStatus.COMPLETED  # type: ignore[union-attr]
        assert store.get(k_rec).status == RecordStatus.RECOVERABLE  # type: ignore[union-attr]
        assert store.get(k_fail).status == RecordStatus.FAILED  # type: ignore[union-attr]


# 4. compact_reduces_jsonl_line_count
def test_compact_reduces_jsonl_line_count() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        store = JsonlIdempotencyStore(db_path=db_path)

        k1 = _make_key("op:line", "k1")
        k2 = _make_key("op:line", "k2")

        store.claim(k1, "owner-1")
        store.complete(k1, "owner-1")

        store.claim(k2, "owner-1")
        store.fail(k2, "owner-1", retryable=True)
        store.claim(k2, "owner-2")

        # Lines before compact = 2 for k1 + 3 for k2 = 5 lines
        with open(db_path, "r", encoding="utf-8") as f:
            lines_before = [l for l in f if l.strip()]
        assert len(lines_before) == 5

        store.compact()

        # Lines after compact = 2 unique keys
        with open(db_path, "r", encoding="utf-8") as f:
            lines_after = [l for l in f if l.strip()]
        assert len(lines_after) == 2


# 5. compact_is_restart_durable
def test_compact_is_restart_durable() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        store1 = JsonlIdempotencyStore(db_path=db_path)
        k = _make_key("op:durable", "k1")

        store1.claim(k, "owner-1")
        store1.complete(k, "owner-1", data={"state": "persisted"})
        store1.compact()

        store2 = JsonlIdempotencyStore(db_path=db_path)
        r = store2.get(k)
        assert r is not None
        assert r.status == RecordStatus.COMPLETED
        assert r.data == {"state": "persisted"}


# 6. compact_atomic_replace_failure_preserves_state
def test_compact_atomic_replace_failure_preserves_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        store = JsonlIdempotencyStore(db_path=db_path)
        k = _make_key("op:replace_err", "k1")
        store.claim(k, "owner-1")

        def fail_replace(src: str, dst: str) -> None:
            raise OSError("simulated replace failure")

        monkeypatch.setattr(os, "replace", fail_replace)

        with pytest.raises(OSError, match="Failed to replace snapshot"):
            store.compact()

        reloaded = JsonlIdempotencyStore(db_path=db_path)
        r = reloaded.get(k)
        assert r is not None
        assert r.status == RecordStatus.IN_PROGRESS


# 7. compact_temp_file_is_cleaned_on_failure
def test_compact_temp_file_is_cleaned_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        store = JsonlIdempotencyStore(db_path=db_path)
        k = _make_key("op:write_err", "k1")
        store.claim(k, "owner-1")

        tmp_path = f"{db_path}.tmp"

        original_open = open

        def failing_open(file: Any, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
            if str(file).endswith(".tmp"):
                raise OSError("simulated disk full")
            return original_open(file, mode, *args, **kwargs)

        monkeypatch.setattr("builtins.open", failing_open)

        with pytest.raises(OSError, match="Failed to write snapshot"):
            store.compact()

        assert not os.path.exists(tmp_path)


# 8. compact_concurrent_with_claim
def test_compact_concurrent_with_claim() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        store_a = JsonlIdempotencyStore(db_path=db_path)
        store_b = JsonlIdempotencyStore(db_path=db_path)

        k1 = _make_key("op:race", "k1")
        k2 = _make_key("op:race", "k2")

        store_a.claim(k1, "owner-a")
        store_a.compact()

        # Store B claims new key k2 cleanly
        claim_b = store_b.claim(k2, "owner-b")
        assert claim_b.status == ClaimStatus.CLAIMED

        # Store B sees store A's compacted claim k1
        claim_b_k1 = store_b.claim(k1, "owner-b")
        assert claim_b_k1.status == ClaimStatus.ALREADY_IN_PROGRESS


# 9. compact_concurrent_with_complete
def test_compact_concurrent_with_complete() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        store_a = JsonlIdempotencyStore(db_path=db_path)
        store_b = JsonlIdempotencyStore(db_path=db_path)

        k = _make_key("op:race_comp", "k1")

        store_a.claim(k, "owner-a")
        store_a.compact()

        # Store A completes under lock
        store_a.complete(k, "owner-a", data={"done": 1})

        # Store B auto-refreshes and sees completion
        rec_b = store_b.get(k)
        assert rec_b is not None
        assert rec_b.status == RecordStatus.COMPLETED
        assert rec_b.data == {"done": 1}


# 10. compact_replay_after_compaction
def test_compact_replay_after_compaction() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        store1 = JsonlIdempotencyStore(db_path=db_path)
        k = _make_key("op:replay", "k1")

        store1.claim(k, "owner-1")
        store1.complete(k, "owner-1", data={"output": "result_abc"})

        store1.compact()

        # Fresh store instance attempts claim
        store2 = JsonlIdempotencyStore(db_path=db_path)
        claim2 = store2.claim(k, "owner-2")

        assert claim2.status == ClaimStatus.ALREADY_COMPLETED
        assert claim2.record is not None
        assert claim2.record.data == {"output": "result_abc"}
