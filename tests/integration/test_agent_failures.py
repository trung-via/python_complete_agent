import pytest
import os
import tempfile
from unittest.mock import Mock, AsyncMock, patch
from src.agent_controller import AgentController
from src.core.types import ToolCall, ToolResult, ToolStatus
from src.core.base_tool import BaseTool
from src.core.errors import SystemStateError

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
            status=ToolStatus.SUCCESS,
            data={"called": True}
        )

@pytest.fixture
def agent():
    with tempfile.TemporaryDirectory() as tmpdir:
        ai = Mock()
        ai.plan_action = AsyncMock()
        
        agent = AgentController()
        agent.ai = ai
        agent.gdrive_folder_id = "test_folder"
        
        from src.core.checkpoint import CheckpointManager
        from src.core.idempotency import IdempotencyStore
        agent.checkpoints = CheckpointManager(db_path=os.path.join(tmpdir, "checkpoints.jsonl"))
        agent.idempotency_store = IdempotencyStore(db_path=os.path.join(tmpdir, "idempotency.jsonl"))
        
        agent.registry.register_tool(DummyTool())
        
        yield agent

@pytest.mark.asyncio
async def test_system_state_error_propagates(agent):
    call = ToolCall(name="dummy", arguments={"val": 5}, call_id="1", run_id="r1")
    agent.ai.plan_action.return_value = call
    
    # Mock idempotency_store.save to raise SystemStateError
    agent.idempotency_store.save = Mock(side_effect=SystemStateError("Disk is full!"))
    
    # execute_task should NOT swallow this error; it should raise it to halt the loop
    with pytest.raises(SystemStateError, match="Disk is full!"):
        await agent.execute_task(call, "r1")

@pytest.mark.asyncio
async def test_validation_failure_emits_rejected_event(agent):
    # Invalid call (missing required 'val')
    call = ToolCall(name="dummy", arguments={}, call_id="1", run_id="r1")
    agent.ai.plan_action.return_value = call
    
    res = await agent.execute_task(call, "r1")
    
    # Check that it returns False due to validation
    assert res is False
    
    # Read checkpoints to verify TOOL_CALL_REJECTED
    import json
    events = []
    with open(agent.checkpoints.db_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))
                
    assert any(e["event"] == "TOOL_CALL_REJECTED" and "required property" in e.get("reason", "") for e in events)
    assert not any(e["event"] == "TOOL_ATTEMPT_STARTED" for e in events)
