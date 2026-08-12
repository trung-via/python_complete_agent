from __future__ import annotations

import os
import tempfile
import time
from typing import Any

import pytest

from src.core.idempotency_contract import (
    IdempotencyCorruptionError,
    RecordKey,
    RecordStatus,
)
from src.core.idempotency_store_v2 import JsonlIdempotencyStore


def _make_key(op: str = "op:prune_test", idem: str = "key_1") -> RecordKey:
    return RecordKey(operation_key=op, idempotency_key=idem)


# 1. test_prune_old_completed_removed
def test_prune_old_completed_removed(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        store = JsonlIdempotencyStore(db_path=db_path)
        k = _make_key("op:comp", "old")

        now = time.time()
        monkeypatch.setattr(time, "time", lambda: now)

        store.claim(k, "owner-1")
        store.complete(k, "owner-1", data={"output": 123})

        # Advance time by 100s (> 50s max_age)
        monkeypatch.setattr(time, "time", lambda: now + 100)

        store.prune(max_age_seconds=50)

        assert store.get(k) is None


# 2. test_prune_old_failed_removed
def test_prune_old_failed_removed(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        store = JsonlIdempotencyStore(db_path=db_path)
        k = _make_key("op:fail", "old")

        now = time.time()
        monkeypatch.setattr(time, "time", lambda: now)

        store.claim(k, "owner-1")
        store.fail(k, "owner-1", retryable=False, data={"err": "fatal"})

        # Advance time by 100s
        monkeypatch.setattr(time, "time", lambda: now + 100)

        store.prune(max_age_seconds=50)

        assert store.get(k) is None


# 3. test_prune_recent_terminal_records_retained
def test_prune_recent_terminal_records_retained(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        store = JsonlIdempotencyStore(db_path=db_path)
        k = _make_key("op:comp", "fresh")

        now = time.time()
        monkeypatch.setattr(time, "time", lambda: now)

        store.claim(k, "owner-1")
        store.complete(k, "owner-1")

        # Advance time by 20s (< 50s max_age)
        monkeypatch.setattr(time, "time", lambda: now + 20)

        store.prune(max_age_seconds=50)

        r = store.get(k)
        assert r is not None
        assert r.status == RecordStatus.COMPLETED


# 4. test_prune_in_progress_retained
def test_prune_in_progress_retained(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        store = JsonlIdempotencyStore(db_path=db_path, ttl_seconds=None)
        k = _make_key("op:prog", "old")

        now = time.time()
        monkeypatch.setattr(time, "time", lambda: now)

        store.claim(k, "owner-1")

        # Advance time by 1000s (> 50s max_age)
        monkeypatch.setattr(time, "time", lambda: now + 1000)

        store.prune(max_age_seconds=50)

        r = store.get(k)
        assert r is not None
        assert r.status == RecordStatus.IN_PROGRESS


# 5. test_prune_recoverable_retained
def test_prune_recoverable_retained(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        store = JsonlIdempotencyStore(db_path=db_path)
        k = _make_key("op:rec", "old")

        now = time.time()
        monkeypatch.setattr(time, "time", lambda: now)

        store.claim(k, "owner-1")
        store.fail(k, "owner-1", retryable=True)

        # Advance time by 1000s
        monkeypatch.setattr(time, "time", lambda: now + 1000)

        store.prune(max_age_seconds=50)

        r = store.get(k)
        assert r is not None
        assert r.status == RecordStatus.RECOVERABLE


# 6. test_prune_age_boundary
def test_prune_age_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        store = JsonlIdempotencyStore(db_path=db_path)

        k_exact = _make_key("op:boundary", "exact")
        k_older = _make_key("op:boundary", "older")

        now = time.time()

        # Create k_older at time 'now - 1'
        monkeypatch.setattr(time, "time", lambda: now - 1)
        store.claim(k_older, "owner-1")
        store.complete(k_older, "owner-1")

        # Create k_exact at time 'now'
        monkeypatch.setattr(time, "time", lambda: now)
        store.claim(k_exact, "owner-1")
        store.complete(k_exact, "owner-1")

        # Prune at time 'now + 50'
        monkeypatch.setattr(time, "time", lambda: now + 50)
        store.prune(max_age_seconds=50)

        # Exact age (50s) is retained (50 <= 50), older (51s) is pruned (51 > 50)
        assert store.get(k_exact) is not None
        assert store.get(k_older) is None


# 7. test_prune_restart_durability
def test_prune_restart_durability(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        store1 = JsonlIdempotencyStore(db_path=db_path)
        k_old = _make_key("op:restart", "old")
        k_fresh = _make_key("op:restart", "fresh")

        now = time.time()
        monkeypatch.setattr(time, "time", lambda: now)

        store1.claim(k_old, "owner-1")
        store1.complete(k_old, "owner-1")

        monkeypatch.setattr(time, "time", lambda: now + 100)

        store1.claim(k_fresh, "owner-1")
        store1.complete(k_fresh, "owner-1")

        store1.prune(max_age_seconds=50)

        # Reload store from disk
        store2 = JsonlIdempotencyStore(db_path=db_path)

        assert store2.get(k_old) is None
        assert store2.get(k_fresh) is not None


# 8. test_prune_persistence_failure_preserves_memory_and_file
def test_prune_persistence_failure_preserves_memory_and_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        store = JsonlIdempotencyStore(db_path=db_path)
        k = _make_key("op:fail_prune", "k1")

        now = time.time()
        monkeypatch.setattr(time, "time", lambda: now)

        store.claim(k, "owner-1")
        store.complete(k, "owner-1")

        monkeypatch.setattr(time, "time", lambda: now + 100)

        def fail_replace(src: str, dst: str) -> None:
            raise OSError("simulated prune replace failure")

        monkeypatch.setattr(os, "replace", fail_replace)

        with pytest.raises(OSError, match="Failed to replace snapshot"):
            store.prune(max_age_seconds=50)

        # Memory and disk file must retain original state
        assert store.get(k) is not None
        reloaded = JsonlIdempotencyStore(db_path=db_path)
        assert reloaded.get(k) is not None


# 9. test_repair_trailing_partial_line_repaired
def test_repair_trailing_partial_line_repaired() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        store = JsonlIdempotencyStore(db_path=db_path)
        k1 = _make_key("op:repair", "k1")
        store.claim(k1, "owner-1")

        # Append trailing broken JSON line
        with open(db_path, "a", encoding="utf-8") as f:
            f.write('{"key": {"operation_key": "op:repair", "idempotency_key": "k2"}, "status": "IN_PROG')

        repaired = store.repair()
        assert repaired is True

        store2 = JsonlIdempotencyStore(db_path=db_path)
        assert store2.get(k1) is not None


# 10. test_repair_trailing_newline_noop
def test_repair_trailing_newline_noop() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        store = JsonlIdempotencyStore(db_path=db_path)
        k = _make_key("op:newline", "k1")
        store.claim(k, "owner-1")

        # Trailing empty newline
        with open(db_path, "a", encoding="utf-8") as f:
            f.write("\n\n")

        repaired = store.repair()
        assert repaired is False
        assert store.get(k) is not None


# 11. test_repair_valid_file_noop
def test_repair_valid_file_noop() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        store = JsonlIdempotencyStore(db_path=db_path)
        k = _make_key("op:valid", "k1")
        store.claim(k, "owner-1")

        assert store.repair() is False


# 12. test_repair_middle_corruption_remains_fatal
def test_repair_middle_corruption_remains_fatal() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        store = JsonlIdempotencyStore(db_path=db_path)
        k1 = _make_key("op:mid", "k1")
        k2 = _make_key("op:mid", "k2")

        store.claim(k1, "owner-1")
        store.claim(k2, "owner-1")

        lines = []
        with open(db_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        lines.insert(1, "{this is corrupt middle line}\n")
        with open(db_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

        with pytest.raises(
            IdempotencyCorruptionError, match="Fatal non-trailing corruption"
        ):
            store.repair()


# 13. test_repair_restart_after_repair
def test_repair_restart_after_repair() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        store1 = JsonlIdempotencyStore(db_path=db_path)
        k1 = _make_key("op:restart_rep", "k1")
        store1.claim(k1, "owner-1")
        store1.complete(k1, "owner-1", data={"valid": True})

        with open(db_path, "a", encoding="utf-8") as f:
            f.write('{"truncated": true')

        repaired = store1.repair()
        assert repaired is True

        store2 = JsonlIdempotencyStore(db_path=db_path)
        r = store2.get(k1)
        assert r is not None
        assert r.status == RecordStatus.COMPLETED
        assert r.data == {"valid": True}


# 14. test_repair_persistence_failure
def test_repair_persistence_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        store = JsonlIdempotencyStore(db_path=db_path)
        k1 = _make_key("op:fail_rep", "k1")
        store.claim(k1, "owner-1")

        with open(db_path, "a", encoding="utf-8") as f:
            f.write('{"corrupted_tail": true')

        original_open = open

        def failing_open(file: Any, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
            if "a+b" in mode or "w" in mode:
                raise OSError("simulated truncate write error")
            return original_open(file, mode, *args, **kwargs)

        monkeypatch.setattr("builtins.open", failing_open)

        with pytest.raises(OSError, match="simulated truncate write error"):
            store.repair()
