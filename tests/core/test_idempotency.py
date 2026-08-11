import pytest
import os
import tempfile
import json
from src.core.idempotency import IdempotencyStore
from src.core.types import ToolResult, ToolStatus

def test_idempotency_store_save_and_get():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "idempotency.jsonl")
        store = IdempotencyStore(db_path=db_path)
        
        result = ToolResult("call1", "run1", "tool", ToolStatus.SUCCESS, data={"x": 1})
        store.save("key_123", result)
        
        # Verify memory cache
        cached = store.get("key_123")
        assert cached is not None
        assert cached.call_id == "call1"
        assert cached.status == ToolStatus.SUCCESS
        
        # Verify persistent disk loading
        store2 = IdempotencyStore(db_path=db_path)
        cached2 = store2.get("key_123")
        assert cached2 is not None
        assert cached2.data == {"x": 1}

def test_idempotency_store_empty_dirname_edge_case():
    # Should not crash when given just a filename (no directory)
    # the os.makedirs guard handles this
    try:
        # We write to the current directory safely
        store = IdempotencyStore(db_path="temp_idempotency_test.jsonl")
        assert store is not None
    finally:
        if os.path.exists("temp_idempotency_test.jsonl"):
            os.remove("temp_idempotency_test.jsonl")
