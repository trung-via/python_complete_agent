from __future__ import annotations

import json
import os
import tempfile
from typing import Any

import pytest

from src.core.idempotency_contract import RecordKey, RecordStatus
from src.core.idempotency_store_v2 import JsonlIdempotencyStore


def _make_key(op: str, idem: str) -> RecordKey:
    return RecordKey(operation_key=op, idempotency_key=idem)


def test_compact_reduces_multiversion_jsonl_to_latest_records() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        store = JsonlIdempotencyStore(db_path=db_path)

        k1 = _make_key("op:upload", "key_1")
        k2 = _make_key("op:download", "key_2")

        # Key 1 transition: claim -> complete
        store.claim(k1, "owner-1")
        store.complete(k1, "owner-1", data={"res": 1})

        # Key 2 transition: claim -> fail -> reclaim -> complete
        store.claim(k2, "owner-2")
        store.fail(k2, "owner-2", retryable=True, data={"err": "timeout"})
        store.claim(k2, "owner-3")
        store.complete(k2, "owner-3", data={"res": 2})

        # Before compact: lines in file = 1 + 1 + 1 + 1 + 1 + 1 = 6 lines
        with open(db_path, "r", encoding="utf-8") as f:
            lines_before = [line for line in f if line.strip()]
        assert len(lines_before) == 6

        # Compact
        store.compact()

        # After compact: exactly 2 lines (1 per unique key)
        with open(db_path, "r", encoding="utf-8") as f:
            lines_after = [line for line in f if line.strip()]
        assert len(lines_after) == 2

        # Verify state is intact
        r1 = store.get(k1)
        r2 = store.get(k2)

        assert r1 is not None and r1.status == RecordStatus.COMPLETED and r1.data == {"res": 1}
        assert r2 is not None and r2.status == RecordStatus.COMPLETED and r2.data == {"res": 2}


def test_compact_sorts_records_deterministically_by_canonical_key() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        store = JsonlIdempotencyStore(db_path=db_path)

        keys = [
            _make_key("op:c", "key_3"),
            _make_key("op:a", "key_1"),
            _make_key("op:b", "key_2"),
        ]

        for k in keys:
            store.claim(k, "owner-1")

        store.compact()

        with open(db_path, "r", encoding="utf-8") as f:
            lines = [json.loads(line.strip()) for line in f if line.strip()]

        canonicals = [
            RecordKey(l["key"]["operation_key"], l["key"]["idempotency_key"]).canonical
            for l in lines
        ]

        assert canonicals == sorted(canonicals)


def test_compact_write_failure_cleans_up_tmp_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        store = JsonlIdempotencyStore(db_path=db_path)
        k = _make_key("op:write", "key_1")
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

        # Temp file must be cleaned up
        assert not os.path.exists(tmp_path)

        # Original data file must be preserved
        r = store.get(k)
        assert r is not None and r.status == RecordStatus.IN_PROGRESS


def test_compact_replace_failure_preserves_original_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        store = JsonlIdempotencyStore(db_path=db_path)
        k = _make_key("op:replace", "key_1")
        store.claim(k, "owner-1")

        def fail_replace(src: str, dst: str) -> None:
            raise OSError("simulated replace error")

        monkeypatch.setattr(os, "replace", fail_replace)

        with pytest.raises(OSError, match="Failed to replace snapshot"):
            store.compact()

        # Original store data must be intact
        reloaded = JsonlIdempotencyStore(db_path=db_path)
        r = reloaded.get(k)
        assert r is not None and r.status == RecordStatus.IN_PROGRESS


def test_restart_after_compact_loads_correct_state() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        store1 = JsonlIdempotencyStore(db_path=db_path)
        k = _make_key("op:restart", "key_1")

        store1.claim(k, "owner-1")
        store1.complete(k, "owner-1", data={"saved": True})
        store1.compact()

        store2 = JsonlIdempotencyStore(db_path=db_path)
        r = store2.get(k)
        assert r is not None
        assert r.status == RecordStatus.COMPLETED
        assert r.data == {"saved": True}
