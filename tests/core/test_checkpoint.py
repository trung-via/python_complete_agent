import pytest
import tempfile
import os
import json
from src.core.checkpoint import CheckpointManager
from src.core.errors import SystemStateError

def test_checkpoint_state_machine_events():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "checkpoints.jsonl")
        manager = CheckpointManager(db_path=db_path)
        
        run_id = manager.log_task_start("do something")
        manager.log_tool_call_created(run_id, "call_1", "tool_x", {"a": 1})
        manager.log_tool_call_rejected(run_id, "call_2", "invalid schema")
        manager.log_tool_attempt_started(run_id, "call_1")
        manager.log_tool_attempt_ended(run_id, "call_1", attempt=1, status="FAILURE", error_msg="timeout")
        manager.log_tool_attempt_ended(run_id, "call_1", attempt=2, status="SUCCESS")
        manager.log_task_end(run_id, success=True, retry_count=0)
        
        # Verify file contents
        events = []
        with open(db_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line))
                    
        assert len(events) == 7
        assert events[0]["event"] == "TASK_START"
        assert events[1]["event"] == "TOOL_CALL_CREATED"
        assert events[1]["tool_name"] == "tool_x"
        assert events[2]["event"] == "TOOL_CALL_REJECTED"
        assert events[2]["reason"] == "invalid schema"
        assert events[3]["event"] == "TOOL_ATTEMPT_STARTED"
        assert events[4]["event"] == "TOOL_ATTEMPT_ENDED"
        assert events[4]["attempt"] == 1
        assert events[5]["status"] == "SUCCESS"
        assert events[6]["event"] == "TASK_END"

def test_checkpoint_write_failure_raises_system_error(monkeypatch):
    manager = CheckpointManager(db_path="/invalid_dir_that_doesnt_exist/db.jsonl")
    
    with pytest.raises(SystemStateError):
        manager.log_task_start("test")
