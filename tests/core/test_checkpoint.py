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
        # State machine contract: RUNNING → LLM_WAITING (via LLM_REQUESTED)
        # → TOOL_EXECUTING (via LLM_RESPONDED with tool calls)
        manager.log_llm_requested(run_id, iteration=1)
        manager.log_llm_responded(run_id, iteration=1, content="calling tool", num_tool_calls=1)
        manager.log_tool_call_created(run_id, "call_1", "tool_x", {"a": 1})
        manager.log_tool_call_rejected(run_id, "call_2", "invalid schema")
        manager.log_tool_attempt_started(run_id, "call_1")
        manager.log_tool_attempt_ended(run_id, "call_1", attempt=1, status="FAILURE", error_msg="timeout")
        manager.log_tool_attempt_ended(run_id, "call_1", attempt=2, status="SUCCESS")
        manager.log_task_end(run_id, success=True, retry_count=0)

        # Verify file contents: 9 events total
        # TASK_START, LLM_REQUESTED, LLM_RESPONDED, TOOL_CALL_CREATED,
        # TOOL_CALL_REJECTED, TOOL_ATTEMPT_STARTED, TOOL_ATTEMPT_ENDED x2, TASK_END
        events = []
        with open(db_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line))

        assert len(events) == 9
        assert events[0]["event"] == "TASK_START"
        assert events[1]["event"] == "LLM_REQUESTED"
        assert events[2]["event"] == "LLM_RESPONDED"
        assert events[3]["event"] == "TOOL_CALL_CREATED"
        assert events[3]["tool_name"] == "tool_x"
        assert events[4]["event"] == "TOOL_CALL_REJECTED"
        assert events[4]["reason"] == "invalid schema"
        assert events[5]["event"] == "TOOL_ATTEMPT_STARTED"
        assert events[6]["event"] == "TOOL_ATTEMPT_ENDED"
        assert events[6]["attempt"] == 1
        assert events[7]["status"] == "SUCCESS"
        assert events[8]["event"] == "TASK_END"


def test_checkpoint_write_failure_raises_system_error(monkeypatch):
    manager = CheckpointManager(db_path="/invalid_dir_that_doesnt_exist/db.jsonl")

    with pytest.raises(SystemStateError):
        manager.log_task_start("test")
