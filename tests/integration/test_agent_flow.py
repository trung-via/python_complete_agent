import pytest
import os
import tempfile
from unittest.mock import Mock, AsyncMock
from src.agent_controller import AgentController
from src.core.types import ToolCall, ToolResult, ToolStatus
from src.core.base_tool import BaseTool

class DummyTool(BaseTool):
    name = "dummy"
    description = "A dummy tool"
    parameters = {"type": "object", "properties": {"val": {"type": "integer"}}, "required": ["val"]}
    
    def __init__(self):
        self.call_count = 0
        
    def get_schema(self):
        return self.parameters
        
    async def execute(self, call, context):
        self.call_count += 1
        return ToolResult(
            call_id=call.call_id,
            run_id=call.run_id,
            tool_name=self.name,
            status=ToolStatus.SUCCESS,
            data={"called": self.call_count}
        )

class DummyPartialTool(BaseTool):
    name = "dummy_partial"
    description = "A dummy partial tool"
    parameters = {"type": "object", "properties": {"val": {"type": "integer"}}, "required": ["val"]}
    
    def __init__(self):
        self.call_count = 0
        
    def get_schema(self):
        return self.parameters
        
    async def execute(self, call, context):
        self.call_count += 1
        return ToolResult(
            call_id=call.call_id,
            run_id=call.run_id,
            tool_name=self.name,
            status=ToolStatus.PARTIAL_SUCCESS,
            data={"called": self.call_count}
        )

@pytest.fixture
def agent():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Mock dependencies
        ai = Mock()
        ai.plan_action = AsyncMock()
        
        # Configure AgentController
        agent = AgentController()
        agent.ai = ai
        agent.gdrive_folder_id = "test_folder"
        
        from src.core.checkpoint import CheckpointManager
        from src.core.idempotency import IdempotencyStore
        agent.checkpoints = CheckpointManager(db_path=os.path.join(tmpdir, "checkpoints.jsonl"))
        agent.idempotency_store = IdempotencyStore(db_path=os.path.join(tmpdir, "idempotency.jsonl"))
        
        agent.registry.register_tool(DummyTool())
        agent.registry.register_tool(DummyPartialTool())
        
        yield agent

@pytest.mark.asyncio
async def test_idempotency_cache_hit(agent):
    call = ToolCall(name="dummy", arguments={"val": 5}, call_id="1", run_id="r1")
    agent.ai.plan_action.return_value = call
    
    # First execution (Miss)
    res1 = await agent.execute_task(call, "r1")
    assert res1 is True
    
    tool = agent.registry.get_tool("dummy")
    assert tool.call_count == 1
    
    # Second execution (Hit)
    res2 = await agent.execute_task(call, "r1")
    assert res2 is True
    assert tool.call_count == 1  # Did not increment, served from cache!
    
@pytest.mark.asyncio
async def test_partial_success_not_cached(agent):
    call = ToolCall(name="dummy_partial", arguments={"val": 5}, call_id="1", run_id="r1")
    agent.ai.plan_action.return_value = call
    
    # First execution (Miss)
    res1 = await agent.execute_task(call, "r1")
    assert res1 is True
    
    tool = agent.registry.get_tool("dummy_partial")
    assert tool.call_count == 1
    
    # Second execution (Not cached because PARTIAL_SUCCESS)
    res2 = await agent.execute_task(call, "r1")
    assert res2 is True
    assert tool.call_count == 2  # Executed again!
