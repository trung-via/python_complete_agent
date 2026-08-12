from __future__ import annotations

import asyncio
import os
import tempfile
from typing import Any, Dict, Optional
import pytest

from src.agent.loop import AgentLoop
from src.agent.policy import RunPolicy
from src.core.cancellation import RunCancellationController
from src.core.checkpoint import CheckpointManager
from src.core.errors import RecoveryStateError
from src.core.idempotency_store_v2 import JsonlIdempotencyStore
from src.core.recovery_controller import RecoveryController
from src.core.retry import RetryManager
from src.core.tool_executor import ToolExecutor
from src.core.tool_registry import ToolRegistry
from src.core.types import ToolCall, ToolResult, ToolStatus
from src.providers.base import LLMResponse


class CountingMockTool:
    def __init__(self, name: str = "counter_tool"):
        self.name = name
        self.description = "Mock tool"
        self.execute_count = 0

    def get_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {"x": {"type": "integer"}}}

    async def execute(self, call: ToolCall, context: Optional[Dict[str, Any]] = None) -> ToolResult:
        self.execute_count += 1
        return ToolResult(
            call_id=call.call_id,
            run_id=call.run_id,
            tool_name=self.name,
            status=ToolStatus.SUCCESS,
            data={"count": self.execute_count},
        )


class MockLLM:
    def __init__(self, responses: Optional[list] = None):
        self.responses = responses or []
        self.call_count = 0

    async def generate(self, messages, tools_schema):
        if self.call_count < len(self.responses):
            resp = self.responses[self.call_count]
            self.call_count += 1
            return resp
        raise RuntimeError("No more mock responses")


def make_test_loop(tmp_path: Any, tool: CountingMockTool, llm_responses: list) -> AgentLoop:
    db_path = str(tmp_path / "idempotency.jsonl")
    cp_path = str(tmp_path / "checkpoints.jsonl")

    registry = ToolRegistry()
    registry.register_tool(tool)

    store = JsonlIdempotencyStore(db_path=db_path)
    checkpoints = CheckpointManager(db_path=cp_path)
    retry_mgr = RetryManager()
    executor = ToolExecutor(
        registry=registry,
        idempotency_store=store,
        retry_manager=retry_mgr,
        checkpoints=checkpoints,
        context={},
    )
    llm = MockLLM(llm_responses)

    return AgentLoop(
        llm_provider=llm,
        tool_executor=executor,
        tool_registry=registry,
        checkpoints=checkpoints,
        policy=RunPolicy(max_iterations=5, max_tool_calls=5, timeout_seconds=10.0),
    )


@pytest.mark.asyncio
async def test_cancel_before_llm_request_halts_execution(tmp_path: Any):
    tool = CountingMockTool()
    loop = make_test_loop(tmp_path, tool, [])

    run_id = "run_cancel_before_llm"
    # Pre-cancel before starting run
    loop.cancellation_controller.cancel(run_id, reason="User cancelled prior to start")

    res = await loop.run(run_id, "sys", "usr")

    assert res is None
    assert loop.llm.call_count == 0
    assert tool.execute_count == 0


@pytest.mark.asyncio
async def test_cancel_before_tool_dispatch_halts_execution(tmp_path: Any):
    tool = CountingMockTool()
    resp1 = LLMResponse(
        content="call tool",
        tool_calls=[{"call_id": "c1", "name": tool.name, "arguments": {"x": 1}}],
        provider="mock",
        provider_response_id="r1",
    )
    loop = make_test_loop(tmp_path, tool, [resp1])

    run_id = "run_cancel_before_tool"

    # Pre-cancel so that when LLM responds, tool loop sees cancellation
    loop.cancellation_controller.cancel(run_id, reason="User cancelled after LLM")

    res = await loop.run(run_id, "sys", "usr")

    assert res is None
    assert tool.execute_count == 0


@pytest.mark.asyncio
async def test_resuming_cancelled_run_fails_closed(tmp_path: Any):
    tool = CountingMockTool()
    loop = make_test_loop(tmp_path, tool, [])

    run_id = "run_cancelled_resume"
    loop.checkpoints.log_task_start("prompt")
    # Cancel run durably
    loop.cancellation_controller.cancel(run_id, reason="Explicit user cancel")

    # RecoveryController must reject resuming HALTED/Cancelled run
    with pytest.raises(RecoveryStateError, match="terminal state"):
        await RecoveryController.resume(loop, run_id)

    assert tool.execute_count == 0


@pytest.mark.asyncio
async def test_no_new_llm_or_tool_calls_after_cancellation(tmp_path: Any):
    tool = CountingMockTool()
    loop = make_test_loop(tmp_path, tool, [])

    run_id = "run_no_new_calls"
    loop.checkpoints.log_task_start("prompt")
    loop.cancellation_controller.cancel(run_id, reason="User stop")

    res = await loop.run(run_id, "sys", "usr")
    assert res is None
    assert tool.execute_count == 0
    assert loop.llm.call_count == 0
