import os
import json
import logging
from typing import Optional
from src.core.types import ToolResult, ToolStatus

logger = logging.getLogger(__name__)

class IdempotencyStore:
    """
    Guarantees idempotency by caching the results of successful tool executions.
    If a tool with the exact same idempotency_key is executed again (e.g. due to retry or recovery within the same run),
    the cached result is returned instead of re-running the side effects.
    """
    def __init__(self, db_path: str = "data/idempotency_store.jsonl"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        # Load existing cache into memory for fast lookups
        self._cache = {}
        self._load_cache()

    def _load_cache(self):
        if not os.path.exists(self.db_path):
            return
            
        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        if "key" in record and "result" in record:
                            self._cache[record["key"]] = ToolResult.from_dict(record["result"])
                    except json.JSONDecodeError:
                        logger.warning("Corrupted line in idempotency store.")
        except Exception as e:
            logger.error(f"Failed to load idempotency store: {e}")

    def get(self, idempotency_key: str) -> Optional[ToolResult]:
        """Returns the cached ToolResult if it exists."""
        return self._cache.get(idempotency_key)

    def save(self, idempotency_key: str, result: ToolResult):
        """
        Saves the ToolResult to the store. 
        Only SUCCESS or PARTIAL_SUCCESS results should be cached.
        """
        if result.status not in (ToolStatus.SUCCESS, ToolStatus.PARTIAL_SUCCESS):
            return

        self._cache[idempotency_key] = result
        
        try:
            record = {
                "key": idempotency_key,
                "result": result.to_dict()
            }
            with open(self.db_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
            logger.info(f"Saved idempotency key {idempotency_key} to store.")
        except Exception as e:
            logger.critical(f"CRITICAL: Failed to write to IdempotencyStore! Error: {e}")
            from src.core.errors import SystemStateError
            raise SystemStateError(f"Idempotency store write failed: {e}")
