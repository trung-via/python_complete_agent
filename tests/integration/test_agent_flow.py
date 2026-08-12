import pytest
import os
import tempfile
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
def executor():
    with tempfile.TemporaryDirectory() as tmpdir:
        registry = ToolRegistry()
        registry.register_tool(DummyTool())
        registry.register_tool(DummyPartialTool())
        
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
async def test_idempotency_cache_hit(executor):
    call = ToolCall(name="dummy", arguments={"val": 5}, call_id="1", run_id="r1")
    
    # First execution (Miss)
    res1 = await executor.execute(call)
    assert res1.status == ToolStatus.SUCCESS
    
    tool = executor.registry.get_tool("dummy")
    assert tool.call_count == 1
    
    # Second execution (Hit)
    res2 = await executor.execute(call)
    assert res2.status == ToolStatus.SUCCESS
    assert tool.call_count == 1  # Did not increment, served from cache!
    
@pytest.mark.asyncio
async def test_partial_success_not_cached(executor):
    call = ToolCall(name="dummy_partial", arguments={"val": 5}, call_id="1", run_id="r1")
    
    # First execution (Miss)
    res1 = await executor.execute(call)
    assert res1.status == ToolStatus.PARTIAL_SUCCESS
    
    tool = executor.registry.get_tool("dummy_partial")
    assert tool.call_count == 1
    
    # Second execution (Miss again because it was PARTIAL)
    res2 = await executor.execute(call)
    assert res2.status == ToolStatus.PARTIAL_SUCCESS
    assert tool.call_count == 2
