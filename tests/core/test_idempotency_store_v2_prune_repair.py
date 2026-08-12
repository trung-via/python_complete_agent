from __future__ import annotations

import json
import os
import tempfile
import time

import pytest

from src.core.idempotency_contract import (
    IdempotencyCorruptionError,
    RecordKey,
    RecordStatus,
)
from src.core.idempotency_store_v2 import JsonlIdempotencyStore


def _make_key(op: str, idem: str) -> RecordKey:
    return RecordKey(operation_key=op, idempotency_key=idem)


def test_prune_invalid_max_age_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        store = JsonlIdempotencyStore(db_path=db_path)

        with pytest.raises(ValueError, match="max_age_seconds must be > 0"):
            store.prune(0)

        with pytest.raises(ValueError, match="max_age_seconds must be > 0"):
            store.prune(-10)

        with pytest.raises(TypeError, match="max_age_seconds must be a number"):
            store.prune(True)  # type: ignore[arg-type]


def test_prune_removes_old_terminal_records_and_retains_active_ones(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        store = JsonlIdempotencyStore(db_path=db_path)

        k_completed_old = _make_key("op:comp", "old")
        k_failed_old = _make_key("op:fail", "old")
        k_completed_fresh = _make_key("op:comp", "fresh")
        k_in_progress_old = _make_key("op:prog", "old")

        now = time.time()
        monkeypatch.setattr(time, "time", lambda: now)

        # Old records created at 'now'
        store.claim(k_completed_old, "owner-1")
        store.complete(k_completed_old, "owner-1")

        store.claim(k_failed_old, "owner-1")
        store.fail(k_failed_old, "owner-1", retryable=False)

        store.claim(k_in_progress_old, "owner-1")

        # Advance time by 100 seconds
        monkeypatch.setattr(time, "time", lambda: now + 100)

        # Fresh completed record created at 'now + 100'
        store.claim(k_completed_fresh, "owner-1")
        store.complete(k_completed_fresh, "owner-1")

        # Prune records older than 50s (now + 100 - 50 = now + 50)
        store.prune(max_age_seconds=50)

        # Old COMPLETED and FAILED must be pruned
        assert store.get(k_completed_old) is None
        assert store.get(k_failed_old) is None

        # Fresh COMPLETED must be retained
        assert store.get(k_completed_fresh) is not None

        # Old IN_PROGRESS must NOT be pruned
        assert store.get(k_in_progress_old) is not None


def test_repair_on_valid_file_returns_false() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        store = JsonlIdempotencyStore(db_path=db_path)
        k = _make_key("op:valid", "k1")
        store.claim(k, "owner-1")

        assert store.repair() is False
        assert store.get(k) is not None


def test_repair_truncates_incomplete_trailing_line() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        store = JsonlIdempotencyStore(db_path=db_path)
        k1 = _make_key("op:valid", "k1")
        store.claim(k1, "owner-1")

        # Append incomplete JSON line at EOF
        with open(db_path, "a", encoding="utf-8") as f:
            f.write('{"key": {"operation_key": "op:bad", "idempotency_key": "k2"}, "status": "IN_PROG')

        # Reading before repair raises corruption error
        with pytest.raises(IdempotencyCorruptionError):
            JsonlIdempotencyStore(db_path=db_path)

        # Conservative repair truncates trailing incomplete line
        repaired = store.repair()
        assert repaired is True

        # Store now loads cleanly and retains k1
        store2 = JsonlIdempotencyStore(db_path=db_path)
        assert store2.get(k1) is not None


def test_repair_on_middle_corruption_raises_fatal_error() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        store = JsonlIdempotencyStore(db_path=db_path)
        k1 = _make_key("op:first", "k1")
        k2 = _make_key("op:second", "k2")

        store.claim(k1, "owner-1")
        store.claim(k2, "owner-1")

        # Insert corruption in middle of file between k1 and k2
        lines = []
        with open(db_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        lines.insert(1, "{this is corrupt middle line}\n")
        with open(db_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

        # repair() must reject middle corruption as fatal
        with pytest.raises(
            IdempotencyCorruptionError, match="Fatal non-trailing corruption"
        ):
            store.repair()
