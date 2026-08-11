import pytest
import tempfile
import os
import json
from unittest.mock import Mock, AsyncMock
from src.agent.loop import AgentLoop
from src.agent.policy import RunPolicy
from src.agent.messages import LLMMessage, MessageRole
from src.providers.base import LLMResponse, ProviderToolCall
from src.core.tool_executor import ToolExecutor
from src.core.tool_registry import ToolRegistry
from src.core.checkpoint import CheckpointManager
from src.core.types import ToolResult, ToolStatus
from src.core.errors import AgentException, SystemStateError

@pytest.fixture
def components():
    with tempfile.TemporaryDirectory() as tmpdir:
        registry = ToolRegistry()
        checkpoints = CheckpointManager(db_path=os.path.join(tmpdir, "checkpoints.jsonl"))
        
        mock_provider = Mock()
        mock_provider.generate = AsyncMock()
        
        mock_executor = Mock()
        mock_executor.execute = AsyncMock()
        
        yield mock_provider, mock_executor, registry, checkpoints

@pytest.mark.asyncio
async def test_agent_loop_max_iterations(components):
    provider, executor, registry, checkpoints = components
    
    policy = RunPolicy(max_iterations=2)
    loop = AgentLoop(provider, executor, registry, checkpoints, policy)
    
    # LLM always returns a tool call, never a final answer
    provider.generate.return_value = LLMResponse(
        provider="test",
        provider_response_id="123",
        content=None,
        tool_calls=[ProviderToolCall(provider_call_id="c1", name="dummy", arguments={})]
    )
    
    # Tool always succeeds
    executor.execute.return_value = ToolResult(
        call_id="c1", run_id="r1", tool_name="dummy", status=ToolStatus.SUCCESS
    )
    
    res = await loop.run("r1", "system", "user")
    
    # Should halt because of max iterations
    assert res is None
    assert provider.generate.call_count == 2
    
    # Checkpoint should log RUN_HALTED
    events = []
    with open(checkpoints.db_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))
                
    assert any(e["event"] == "RUN_HALTED" and "MAX_ITERATIONS_REACHED" in e["reason"] for e in events)

@pytest.mark.asyncio
async def test_agent_loop_final_answer(components):
    provider, executor, registry, checkpoints = components
    
    policy = RunPolicy(max_iterations=5)
    loop = AgentLoop(provider, executor, registry, checkpoints, policy)
    
    # LLM returns final answer
    provider.generate.return_value = LLMResponse(
        provider="test",
        provider_response_id="123",
        content="This is the final answer.",
        tool_calls=[]
    )
    
    res = await loop.run("r1", "system", "user")
    
    assert res == "This is the final answer."
    assert provider.generate.call_count == 1
    assert executor.execute.call_count == 0

@pytest.mark.asyncio
async def test_agent_loop_system_error_halts(components):
    provider, executor, registry, checkpoints = components
    
    policy = RunPolicy(max_iterations=5)
    loop = AgentLoop(provider, executor, registry, checkpoints, policy)
    
    provider.generate.return_value = LLMResponse(
        provider="test",
        provider_response_id="123",
        content=None,
        tool_calls=[ProviderToolCall(provider_call_id="c1", name="dummy", arguments={})]
    )
    
    # Tool throws SystemStateError
    executor.execute.side_effect = SystemStateError("Disk failure!")
    
    res = await loop.run("r1", "system", "user")
    
    assert res is None
    assert provider.generate.call_count == 1
    assert executor.execute.call_count == 1
    
    # Checkpoint should log RUN_HALTED due to SystemStateError
    events = []
    with open(checkpoints.db_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))
                
    assert any(e["event"] == "RUN_HALTED" and "SYSTEM_STATE_ERROR" in e["reason"] for e in events)

@pytest.mark.asyncio
async def test_agent_loop_multi_step_reasoning(components):
    provider, executor, registry, checkpoints = components
    
    policy = RunPolicy(max_iterations=5)
    loop = AgentLoop(provider, executor, registry, checkpoints, policy)
    
    # Provider returns:
    # 1. Tool Call A
    # 2. Tool Call B
    # 3. Final Answer
    provider.generate.side_effect = [
        LLMResponse(
            provider="test", provider_response_id="1", content=None,
            tool_calls=[ProviderToolCall(provider_call_id="c1", name="tool_A", arguments={"a": 1})]
        ),
        LLMResponse(
            provider="test", provider_response_id="2", content=None,
            tool_calls=[ProviderToolCall(provider_call_id="c2", name="tool_B", arguments={"b": 2})]
        ),
        LLMResponse(
            provider="test", provider_response_id="3", content="Final Answer here.",
            tool_calls=[]
        )
    ]
    
    # Executor always succeeds
    async def mock_execute(call):
        return ToolResult(
            call_id=call.call_id, run_id=call.run_id, tool_name=call.name, 
            status=ToolStatus.SUCCESS, data={"result": f"success_{call.name}"}
        )
    executor.execute.side_effect = mock_execute
    
    res = await loop.run("r1", "system msg", "user msg")
    
    assert res == "Final Answer here."
    assert provider.generate.call_count == 3
    assert executor.execute.call_count == 2
    
    # Retrieve the message history passed to the last LLM call
    last_call_messages = provider.generate.call_args_list[-1][0][0]
    roles = [msg.role for msg in last_call_messages]
    
    # Expected roles:
    # 1. SYSTEM
    # 2. USER
    # 3. ASSISTANT (tool_A)
    # 4. TOOL (result A)
    # 5. ASSISTANT (tool_B)
    # 6. TOOL (result B)
    # 7. ASSISTANT (final)
    assert roles == [
        MessageRole.SYSTEM,
        MessageRole.USER,
        MessageRole.ASSISTANT,
        MessageRole.TOOL,
        MessageRole.ASSISTANT,
        MessageRole.TOOL,
        MessageRole.ASSISTANT
    ]
    
    # Verify TOOL messages contain the right call_ids
    assert last_call_messages[3].tool_call_id == "c1"
    assert last_call_messages[5].tool_call_id == "c2"

@pytest.mark.asyncio
async def test_agent_loop_agent_exception_handled(components):
    provider, executor, registry, checkpoints = components
    
    policy = RunPolicy(max_iterations=5)
    loop = AgentLoop(provider, executor, registry, checkpoints, policy)
    
    # Provider raises AgentException
    provider.generate.side_effect = AgentException(message="Provider rate limit exceeded", code="RATE_LIMIT")
    
    res = await loop.run("r1", "system", "user")
    
    assert res is None
    assert provider.generate.call_count == 1
    
    # Checkpoint should log RUN_FAILED
    events = []
    with open(checkpoints.db_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))
                
    assert any(e["event"] == "RUN_FAILED" and "Provider rate limit exceeded" in e["error"] for e in events)
