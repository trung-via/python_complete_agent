import json
import os
import uuid
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class CheckpointManager:
    """
    Manages state checkpoints for the autonomous agent.
    Replaces the simple completed.txt task ledger.
    """
    def __init__(self, db_path: str = "checkpoints.jsonl"):
        self.db_path = db_path
        
    def log_task_start(self, task_context: str) -> str:
        """Logs the start of a task and returns a unique run_id."""
        run_id = str(uuid.uuid4())
        self._write_event({
            "run_id": run_id,
            "event": "TASK_START",
            "task_context": task_context,
            "status": "PENDING",
            "retry_count": 0
        })
        return run_id
        
    def log_tool_call(self, run_id: str, call_id: str, tool_name: str, arguments: dict):
        self._write_event({
            "run_id": run_id,
            "event": "TOOL_CALL",
            "call_id": call_id,
            "tool_name": tool_name,
            "arguments": arguments
        })
        
    def log_task_end(self, run_id: str, success: bool, retry_count: int, data: dict = None):
        self._write_event({
            "run_id": run_id,
            "event": "TASK_END",
            "status": "SUCCESS" if success else "FAILED",
            "retry_count": retry_count,
            "data": data or {}
        })
        
    def _write_event(self, payload: dict):
        import time
        payload["timestamp"] = time.time()
        try:
            with open(self.db_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload) + "\n")
        except Exception as e:
            logger.critical(f"CRITICAL: Failed to write checkpoint event! Agent state is compromised. Error: {e}")
            from src.core.errors import SystemStateError
            raise SystemStateError(f"Checkpoint write failed: {e}")

    def get_completed_tasks(self) -> List[str]:
        """Reads the ledger to find which tasks successfully completed."""
        if not os.path.exists(self.db_path):
            return []
            
        task_starts = {}
        completed = set()
        
        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip(): continue
                    try:
                        evt = json.loads(line)
                        run_id = evt.get("run_id")
                        if evt.get("event") == "TASK_START":
                            task_starts[run_id] = evt.get("task_context")
                        elif evt.get("event") == "TASK_END":
                            if evt.get("status") == "SUCCESS":
                                task_context = task_starts.get(run_id)
                                if task_context:
                                    completed.add(task_context)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.error(f"Failed to read checkpoints: {e}")
            
        return list(completed)
