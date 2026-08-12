import pytest
import os
import tempfile
import json
from unittest.mock import Mock, AsyncMock
from src.core.types import ToolCall, ToolResult, ToolStatus
from src.core.base_tool import BaseTool
from src.core.tool_executor import ToolExecutor
from src.core.checkpoint import CheckpointManager
from src.core.idempotency import IdempotencyStore
from src.core.retry import RetryManager
from src.core.tool_registry import ToolRegistry
from src.core.errors import AgentException, SystemStateError

class DummyTool(BaseTool):
    name = "dummy"
    description = "A dummy tool"
    parameters = {"type": "object", "properties": {"val": {"type": "integer"}}, "required": ["val"]}
    
    def get_schema(self):
        return self.parameters
        
    async def execute(self, call, context):
        return ToolResult(
            call_id=call.call_id,
            run_id=call.run_id,
            tool_name=self.name,
            status=ToolStatus.SUCCESS
        )

@pytest.fixture
def executor():
    with tempfile.TemporaryDirectory() as tmpdir:
        registry = ToolRegistry()
        registry.register_tool(DummyTool())
        
        checkpoints = CheckpointManager(db_path=os.path.join(tmpdir, "checkpoints.jsonl"))
        idempotency_store = IdempotencyStore(db_path=os.path.join(tmpdir, "idempotency.jsonl"))
        retry_manager = RetryManager()
        
        executor = ToolExecutor(
            registry=registry,
            idempotency_store=idempotency_store,
            retry_manager=retry_manager,
            checkpoints=checkpoints,
            context={}
        )
        yield executor

@pytest.mark.asyncio
async def test_system_state_error_propagates(executor):
    call = ToolCall(name="dummy", arguments={"val": 5}, call_id="1", run_id="r1")
    
    # Mock idempotency_store.save to raise SystemStateError
    executor.idempotency_store.save = Mock(side_effect=SystemStateError("Disk is full!"))
    
    # execute_task should let SystemStateError crash the agent, NOT catch it as False
    with pytest.raises(SystemStateError):
        await executor.execute(call)

@pytest.mark.asyncio
async def test_validation_failure_emits_rejected_event(executor):
    # Invalid call (missing required 'val')
    call = ToolCall(name="dummy", arguments={}, call_id="1", run_id="r1")
    
    res = await executor.execute(call)
    
    assert res.status == ToolStatus.FAILURE
    assert res.error.code == "VALIDATION_ERROR"
    
    # Verify events
    events = []
    with open(executor.checkpoints.db_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))
                
    event_names = [e["event"] for e in events]
    assert "TOOL_CALL_CREATED" in event_names
    assert "TOOL_CALL_REJECTED" in event_names
    assert "TOOL_ATTEMPT_STARTED" not in event_names
