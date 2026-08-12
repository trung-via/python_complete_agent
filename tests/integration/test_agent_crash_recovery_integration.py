from __future__ import annotations

import os
import tempfile
from typing import Any, Dict, List, Optional

import pytest

from src.agent.loop import AgentLoop
from src.agent.messages import LLMMessage
from src.agent.policy import RunPolicy
from src.core.checkpoint import CheckpointManager
from src.core.idempotency_contract import RecordKey
from src.core.idempotency_store_v2 import JsonlIdempotencyStore
from src.core.retry import RetryManager
from src.core.tool_executor import ToolExecutor
from src.core.tool_registry import ToolRegistry
from src.core.types import ToolCall, ToolResult, ToolStatus
from src.providers.base import LLMProvider, LLMResponse, ProviderToolCall


class MockLLM(LLMProvider):
    def __init__(self, responses: List[LLMResponse]) -> None:
        self.responses = responses
        self.call_count = 0

    async def generate(
        self,
        messages: List[LLMMessage],
        tools: List[dict],
    ) -> LLMResponse:
        resp = self.responses[self.call_count]
        self.call_count += 1
        return resp


class DummyExecutionTool:
    def __init__(self, name: str = "expensive_tool") -> None:
        self.name = name
        self.description = "expensive calculation tool"
        self.execute_count = 0

    def get_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}}

    async def execute(self, call: ToolCall, context: Dict[str, Any]) -> ToolResult:
        self.execute_count += 1
        return ToolResult(
            call_id=call.call_id,
            run_id=call.run_id,
            tool_name=call.name,
            status=ToolStatus.SUCCESS,
            data={"val": f"computed_{self.execute_count}"},
        )


def _make_response(
    content: Optional[str],
    tool_calls: List[ProviderToolCall] | None = None,
) -> LLMResponse:
    return LLMResponse(
        provider="mock",
        provider_response_id="resp-1",
        content=content,
        tool_calls=tool_calls or [],
    )


def _setup_harness(
    tmp_path: Any,
    llm_responses: List[LLMResponse],
    tool: DummyExecutionTool,
    store: Optional[JsonlIdempotencyStore] = None,
) -> tuple[AgentLoop, JsonlIdempotencyStore, CheckpointManager]:
    db_path = str(tmp_path / "idempotency.jsonl")
    cp_path = str(tmp_path / "checkpoints.jsonl")

    registry = ToolRegistry()
    registry.register_tool(tool)

    if store is None:
        store = JsonlIdempotencyStore(db_path=db_path)
    checkpoints = CheckpointManager(db_path=cp_path)
    retry_manager = RetryManager()

    tool_executor = ToolExecutor(
        registry=registry,
        idempotency_store=store,
        retry_manager=retry_manager,
        checkpoints=checkpoints,
        context={},
    )

    llm = MockLLM(llm_responses)
    loop = AgentLoop(
        llm_provider=llm,
        tool_executor=tool_executor,
        tool_registry=registry,
        checkpoints=checkpoints,
        policy=RunPolicy(max_iterations=5, max_tool_calls=5, timeout_seconds=10),
    )
    return loop, store, checkpoints


@pytest.mark.asyncio
async def test_agent_crash_before_llm_responded_resume(tmp_path: Any) -> None:
    # Boundary 1: Crash before LLM_RESPONDED
    cp_path = str(tmp_path / "checkpoints.jsonl")
    checkpoints = CheckpointManager(db_path=cp_path)

    run_id = "run-b1"
    checkpoints.log_run_started(run_id, "sys", "user")
    checkpoints.log_llm_requested(run_id, iteration=1)

    tool = DummyExecutionTool()
    responses = [
        _make_response(content="Final Answer B1"),
    ]
    loop, _, _ = _setup_harness(tmp_path, responses, tool)

    # Resume run_id
    result = await loop.resume(run_id)

    assert result == "Final Answer B1"
    assert tool.execute_count == 0


@pytest.mark.asyncio
async def test_agent_crash_after_llm_responded_resume(tmp_path: Any) -> None:
    # Boundary 2: Crash after LLM_RESPONDED with tool call before execution
    cp_path = str(tmp_path / "checkpoints.jsonl")
    checkpoints = CheckpointManager(db_path=cp_path)

    run_id = "run-b2"
    checkpoints.log_run_started(run_id, "sys", "do calculation")
    checkpoints.log_llm_requested(run_id, iteration=1)
    checkpoints.log_llm_responded(
        run_id,
        iteration=1,
        content="Calling tool...",
        num_tool_calls=1,
        tool_calls=[
            {"call_id": "c1", "name": "expensive_tool", "arguments": {"x": 10}}
        ],
    )

    tool = DummyExecutionTool()
    responses = [
        _make_response(content="Task complete with computed_1"),
    ]
    loop, _, _ = _setup_harness(tmp_path, responses, tool)

    result = await loop.resume(run_id)

    assert result == "Task complete with computed_1"
    assert tool.execute_count == 1


@pytest.mark.asyncio
async def test_agent_crash_during_tool_execution_resume(tmp_path: Any) -> None:
    # Boundary 3: Crash during tool execution (store has IN_PROGRESS claim, expires via TTL)
    import time

    db_path = str(tmp_path / "idempotency.jsonl")
    cp_path = str(tmp_path / "checkpoints.jsonl")

    store = JsonlIdempotencyStore(db_path=db_path, ttl_seconds=1)
    checkpoints = CheckpointManager(db_path=cp_path)

    run_id = "run-b3"
    checkpoints.log_run_started(run_id, "sys", "work")
    checkpoints.log_llm_requested(run_id, iteration=1)
    checkpoints.log_llm_responded(
        run_id,
        iteration=1,
        content="Running tool",
        num_tool_calls=1,
        tool_calls=[
            {"call_id": "c1", "name": "expensive_tool", "arguments": {}}
        ],
    )

    # Claim key manually to simulate in-progress execution before crash
    call = ToolCall(name="expensive_tool", arguments={}, call_id="c1", run_id=run_id)
    key = RecordKey("tool:expensive_tool", call.idempotency_key)
    store.claim(key, "worker-crashed")

    # Wait 1.1s for TTL expiry of abandoned claim
    time.sleep(1.1)

    # Resume on fresh loop with same store
    tool = DummyExecutionTool()
    responses = [
        _make_response(content="Done after recovery"),
    ]
    loop, _, _ = _setup_harness(tmp_path, responses, tool, store=store)

    result = await loop.resume(run_id)

    assert result == "Done after recovery"
    assert tool.execute_count == 1


@pytest.mark.asyncio
async def test_agent_crash_after_idempotency_complete_before_checkpoint_result(
    tmp_path: Any,
) -> None:
    # Boundary 4 (Crucial Acceptance Boundary):
    # IdempotencyStore marked COMPLETED, but process crashed BEFORE logging TOOL_RESULT_RECEIVED checkpoint!
    db_path = str(tmp_path / "idempotency.jsonl")
    cp_path = str(tmp_path / "checkpoints.jsonl")

    store = JsonlIdempotencyStore(db_path=db_path)
    checkpoints = CheckpointManager(db_path=cp_path)

    run_id = "run-b4"
    checkpoints.log_run_started(run_id, "sys", "do calculation")
    checkpoints.log_llm_requested(run_id, iteration=1)
    checkpoints.log_llm_responded(
        run_id,
        iteration=1,
        content="Calling expensive tool",
        num_tool_calls=1,
        tool_calls=[
            {"call_id": "c1", "name": "expensive_tool", "arguments": {"param": 100}}
        ],
    )

    # Simulate tool executed and completed in IdempotencyStore V2 before crash
    call = ToolCall(
        name="expensive_tool", arguments={"param": 100}, call_id="c1", run_id=run_id
    )
    key = RecordKey("tool:expensive_tool", call.idempotency_key)

    store.claim(key, "worker-1")
    cached_tool_result = ToolResult(
        call_id="c1",
        run_id=run_id,
        tool_name="expensive_tool",
        status=ToolStatus.SUCCESS,
        data={"cached_result": "expensive_output_v1"},
    )
    store.complete(key, "worker-1", data={"result": cached_tool_result.to_dict()})

    # NO TOOL_RESULT_RECEIVED written to checkpoints.jsonl! (Process crashed)

    # Fresh process/agent instance resumes
    tool = DummyExecutionTool()
    responses = [
        _make_response(content="Final Answer with cached_result"),
    ]
    loop, _, _ = _setup_harness(tmp_path, responses, tool)

    # Resume run_id
    result = await loop.resume(run_id)

    # 1. Result matches
    assert result == "Final Answer with cached_result"

    # 2. Tool code was NOT executed again (0 duplicate execution!)
    assert tool.execute_count == 0

    # 3. Checkpoint log now contains TOOL_RESULT_RECEIVED
    events_raw = []
    with open(cp_path, "r", encoding="utf-8") as f:
        events_raw = [line for line in f if "TOOL_RESULT_RECEIVED" in line]
    assert len(events_raw) == 1
