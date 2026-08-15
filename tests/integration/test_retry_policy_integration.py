from __future__ import annotations

import asyncio
import os
import tempfile
from typing import Any, Dict, Optional
import pytest

from src.agent.loop import AgentLoop
from src.agent.policy import RunPolicy
from src.core.checkpoint import CheckpointManager
from src.core.checkpoint_contract import CheckpointCorruptionError, FailureDomain, RunState
from src.core.idempotency_contract import RecordKey
from src.core.idempotency_store_v2 import JsonlIdempotencyStore
from src.core.retry import RetryManager, RetryPolicy
from src.core.retry_policy import (
    RetryContext,
    RetryDecision,
    RetryOperation,
    RetryPolicyEngine,
    RetryReason,
)
from src.core.tool_executor import ToolExecutor
from src.core.tool_registry import ToolRegistry
from src.core.types import ToolCall, ToolResult, ToolStatus


class RetryMockTool:
    def __init__(self, name: str = "retry_mock_tool", fail_attempts: int = 1):
        self.name = name
        self.description = "Mock tool for testing retries"
        self.fail_attempts = fail_attempts
        self.execute_count = 0
        self.call_ids_received = []
        self.idempotency_keys_received = []

    def get_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {"x": {"type": "integer"}}}

    async def execute(self, call: ToolCall, context: Optional[Dict[str, Any]] = None) -> ToolResult:
        self.execute_count += 1
        self.call_ids_received.append(call.call_id)
        self.idempotency_keys_received.append(call.idempotency_key)

        if self.execute_count <= self.fail_attempts:
            return ToolResult(
                call_id=call.call_id,
                run_id=call.run_id,
                tool_name=self.name,
                status=ToolStatus.FAILURE,
                data={"error": "transient error"},
                error=ToolResult.from_dict({
                    "call_id": call.call_id,
                    "run_id": call.run_id,
                    "tool_name": self.name,
                    "status": "failure",
                    "error": {"code": "TRANSIENT_ERROR", "message": "transient error", "retryable": True},
                }).error,
            )

        return ToolResult(
            call_id=call.call_id,
            run_id=call.run_id,
            tool_name=self.name,
            status=ToolStatus.SUCCESS,
            data={"val": "ok"},
        )


@pytest.mark.asyncio
async def test_tool_retry_preserves_exact_call_id_and_idempotency_key(tmp_path: Any):
    tool = RetryMockTool(fail_attempts=2)

    db_path = str(tmp_path / "idempotency.jsonl")
    cp_path = str(tmp_path / "checkpoints.jsonl")

    registry = ToolRegistry()
    registry.register_tool(tool)

    store = JsonlIdempotencyStore(db_path=db_path)
    checkpoints = CheckpointManager(db_path=cp_path)
    # Configure 3 max_attempts, fast 0.01s base delay for tests
    retry_mgr = RetryManager(default_policy=RetryPolicy(max_attempts=3, base_delay=0.01))
    executor = ToolExecutor(
        registry=registry,
        idempotency_store=store,
        retry_manager=retry_mgr,
        checkpoints=checkpoints,
        context={},
    )

    call = ToolCall(name=tool.name, arguments={"x": 10}, call_id="call_retry_100", run_id="run_retry_test")

    result = await executor.execute(call)

    assert result.status == ToolStatus.SUCCESS
    assert tool.execute_count == 3
    # Critical Invariant: All attempts must use the EXACT SAME call_id and idempotency_key!
    assert len(set(tool.call_ids_received)) == 1
    assert tool.call_ids_received[0] == "call_retry_100"
    assert len(set(tool.idempotency_keys_received)) == 1


def test_retry_policy_engine_corruption_never_retries():
    ctx = RetryContext(
        operation=RetryOperation.TOOL,
        attempt=1,
        max_attempts=5,
        failure_domain=FailureDomain.CORRUPTION_INTEGRITY,
        transient=True,
    )
    decision = RetryPolicyEngine.decide(ctx)
    assert decision.should_retry is False
    assert decision.reason == RetryReason.CORRUPTION


def test_retry_policy_engine_max_attempts_boundary_stops():
    # Boundary test: attempt == max_attempts MUST return should_retry=False
    ctx = RetryContext(
        operation=RetryOperation.TOOL,
        attempt=3,
        max_attempts=3,
        failure_domain=FailureDomain.TOOL_EXECUTION,
        transient=True,
    )
    decision = RetryPolicyEngine.decide(ctx)
    assert decision.should_retry is False
    assert decision.reason == RetryReason.MAX_ATTEMPTS_EXCEEDED
    assert decision.next_attempt == 3


@pytest.mark.asyncio
async def test_retry_manager_respects_rate_limit_retry_after(monkeypatch: pytest.MonkeyPatch):
    slept_delays = []

    async def mock_sleep(delay: float):
        slept_delays.append(delay)

    monkeypatch.setattr(asyncio, "sleep", mock_sleep)

    retry_mgr = RetryManager(default_policy=RetryPolicy(max_attempts=3, base_delay=2.0))

    call_count = 0

    async def rate_limited_op():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            from src.core.errors import RateLimitError
            raise RateLimitError("Rate limit exceeded", details={"retry_after": 7.5})
        return "success_val"

    result = await retry_mgr.execute_with_retry(rate_limited_op)

    assert result == "success_val"
    assert call_count == 2
    assert slept_delays == [7.5]


@pytest.mark.asyncio
async def test_retry_manager_respects_rate_limit_retry_after_tool_result(monkeypatch: pytest.MonkeyPatch):
    slept_delays = []

    async def mock_sleep(delay: float):
        slept_delays.append(delay)

    monkeypatch.setattr(asyncio, "sleep", mock_sleep)

    retry_mgr = RetryManager(default_policy=RetryPolicy(max_attempts=3, base_delay=2.0))

    call_count = 0

    async def rate_limited_tool():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            from src.core.errors import RateLimitError
            return ToolResult(
                call_id="c1",
                run_id="r1",
                tool_name="t1",
                status=ToolStatus.FAILURE,
                error=RateLimitError("Too Many Requests", details={"retry_after": 4.2}),
            )
        return ToolResult(
            call_id="c1",
            run_id="r1",
            tool_name="t1",
            status=ToolStatus.SUCCESS,
            data={"done": True},
        )

    result = await retry_mgr.execute_with_retry(rate_limited_tool)

    assert result.status == ToolStatus.SUCCESS
    assert call_count == 2
    assert slept_delays == [4.2]

