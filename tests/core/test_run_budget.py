from __future__ import annotations

import asyncio
import json
import os
import tempfile
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock

import pytest

from src.agent.loop import AgentLoop
from src.agent.messages import LLMMessage
from src.agent.policy import RunPolicy
from src.core.cancellation import RunCancellationController
from src.core.checkpoint import CheckpointManager
from src.core.checkpoint_contract import CheckpointEvent, CheckpointEventType
from src.core.errors import RecoveryStateError
from src.core.idempotency_store_v2 import JsonlIdempotencyStore
from src.core.retry import RetryManager
from src.core.run_budget import (
    BudgetDecision,
    BudgetDimension,
    BudgetUsage,
    RunBudgetEngine,
)
from src.core.tool_executor import ToolExecutor
from src.core.tool_registry import ToolRegistry
from src.core.types import ToolCall, ToolResult, ToolStatus
from src.providers.base import LLMProvider, LLMResponse, ProviderToolCall


# ===========================================================================
# 1. Unit Tests: RunBudgetEngine Decision Logic
# ===========================================================================


def test_budget_engine_allows_exact_iterations_and_rejects_n_plus_one():
    policy = RunPolicy(max_iterations=3, max_tool_calls=10, timeout_seconds=10)

    # 0 -> 1: OK
    d1 = RunBudgetEngine.decide(policy, BudgetUsage(iterations_used=0, tool_calls_used=0), requested_iterations=1)
    assert d1.allowed is True
    assert d1.exhausted_dimension is None

    # 2 -> 3: OK (exact limit)
    d3 = RunBudgetEngine.decide(policy, BudgetUsage(iterations_used=2, tool_calls_used=0), requested_iterations=1)
    assert d3.allowed is True

    # 3 -> 4: REJECTED
    d4 = RunBudgetEngine.decide(policy, BudgetUsage(iterations_used=3, tool_calls_used=0), requested_iterations=1)
    assert d4.allowed is False
    assert d4.exhausted_dimension == BudgetDimension.ITERATIONS
    assert d4.reason == "MAX_ITERATIONS_REACHED"


def test_budget_engine_allows_exact_tool_calls_and_rejects_n_plus_one():
    policy = RunPolicy(max_iterations=10, max_tool_calls=2, timeout_seconds=10)

    # 0 -> 1: OK
    d1 = RunBudgetEngine.decide(policy, BudgetUsage(iterations_used=1, tool_calls_used=0), requested_tool_calls=1)
    assert d1.allowed is True

    # 1 -> 2: OK (exact limit)
    d2 = RunBudgetEngine.decide(policy, BudgetUsage(iterations_used=1, tool_calls_used=1), requested_tool_calls=1)
    assert d2.allowed is True

    # 2 -> 3: REJECTED
    d3 = RunBudgetEngine.decide(policy, BudgetUsage(iterations_used=1, tool_calls_used=2), requested_tool_calls=1)
    assert d3.allowed is False
    assert d3.exhausted_dimension == BudgetDimension.TOOL_CALLS
    assert d3.reason == "MAX_TOOL_CALLS_REACHED"


def test_zero_iteration_or_tool_budgets_fail_before_work():
    zero_iter_policy = RunPolicy(max_iterations=0, max_tool_calls=5, timeout_seconds=10)
    d_iter = RunBudgetEngine.decide(zero_iter_policy, BudgetUsage(0, 0), requested_iterations=1)
    assert d_iter.allowed is False
    assert d_iter.exhausted_dimension == BudgetDimension.ITERATIONS
    assert d_iter.reason == "MAX_ITERATIONS_REACHED"

    zero_tool_policy = RunPolicy(max_iterations=5, max_tool_calls=0, timeout_seconds=10)
    d_tool = RunBudgetEngine.decide(zero_tool_policy, BudgetUsage(1, 0), requested_tool_calls=1)
    assert d_tool.allowed is False
    assert d_tool.exhausted_dimension == BudgetDimension.TOOL_CALLS
    assert d_tool.reason == "MAX_TOOL_CALLS_REACHED"


# ===========================================================================
# 2. Policy Validation Tests
# ===========================================================================


def test_negative_budgets_fail_closed_in_policy_validation():
    with pytest.raises(ValueError, match="max_iterations must be non-negative"):
        RunPolicy(max_iterations=-1)

    with pytest.raises(ValueError, match="max_tool_calls must be non-negative"):
        RunPolicy(max_tool_calls=-5)


def test_non_positive_timeout_fails_closed_in_policy_validation():
    with pytest.raises(ValueError, match="timeout_seconds must be positive"):
        RunPolicy(timeout_seconds=0)

    with pytest.raises(ValueError, match="timeout_seconds must be positive"):
        RunPolicy(timeout_seconds=-10)


# ===========================================================================
# 3. Durable Usage Reconstruction Tests
# ===========================================================================


def test_reconstruct_usage_counts_distinct_iterations_and_logical_tool_calls():
    events = [
        CheckpointEvent(
            sequence_id=1,
            timestamp="2026-08-15T12:00:00Z",
            run_id="run-1",
            event_type=CheckpointEventType.RUN_STARTED,
            payload={},
        ),
        CheckpointEvent(
            sequence_id=2,
            timestamp="2026-08-15T12:00:01Z",
            run_id="run-1",
            event_type=CheckpointEventType.LLM_REQUESTED,
            payload={"iteration": 1},
        ),
        CheckpointEvent(
            sequence_id=3,
            timestamp="2026-08-15T12:00:02Z",
            run_id="run-1",
            event_type=CheckpointEventType.LLM_RESPONDED,
            payload={"iteration": 1, "tool_calls": [{"call_id": "call_A", "name": "tool_a"}]},
        ),
        CheckpointEvent(
            sequence_id=4,
            timestamp="2026-08-15T12:00:03Z",
            run_id="run-1",
            event_type=CheckpointEventType.TOOL_RESULT_RECEIVED,
            payload={"call_id": "call_A", "tool_name": "tool_a", "status": "SUCCESS"},
        ),
        CheckpointEvent(
            sequence_id=5,
            timestamp="2026-08-15T12:00:04Z",
            run_id="run-1",
            event_type=CheckpointEventType.LLM_REQUESTED,
            payload={"iteration": 2},
        ),
    ]

    usage = RunBudgetEngine.reconstruct_usage(events)
    assert usage.iterations_used == 2
    assert usage.tool_calls_used == 1


def test_reconstruct_usage_does_not_double_count_retried_tool_attempts():
    """A retried tool with multiple attempts sharing the same call_id counts as 1 logical tool call."""
    events = [
        CheckpointEvent(
            sequence_id=1,
            timestamp="2026-08-15T12:00:00Z",
            run_id="run-2",
            event_type=CheckpointEventType.RUN_STARTED,
            payload={},
        ),
        CheckpointEvent(
            sequence_id=2,
            timestamp="2026-08-15T12:00:01Z",
            run_id="run-2",
            event_type=CheckpointEventType.LLM_REQUESTED,
            payload={"iteration": 1},
        ),
        CheckpointEvent(
            sequence_id=3,
            timestamp="2026-08-15T12:00:02Z",
            run_id="run-2",
            event_type=CheckpointEventType.LLM_RESPONDED,
            payload={"iteration": 1, "tool_calls": [{"call_id": "call_retry_1", "name": "flaky_tool"}]},
        ),
        # Attempt 1
        CheckpointEvent(
            sequence_id=4,
            timestamp="2026-08-15T12:00:03Z",
            run_id="run-2",
            event_type=CheckpointEventType.TOOL_ATTEMPT_STARTED,
            payload={"call_id": "call_retry_1", "attempt": 1},
        ),
        CheckpointEvent(
            sequence_id=5,
            timestamp="2026-08-15T12:00:04Z",
            run_id="run-2",
            event_type=CheckpointEventType.RETRY_SCHEDULED,
            payload={"call_id": "call_retry_1", "attempt": 1, "next_attempt": 2},
        ),
        # Attempt 2
        CheckpointEvent(
            sequence_id=6,
            timestamp="2026-08-15T12:00:05Z",
            run_id="run-2",
            event_type=CheckpointEventType.TOOL_ATTEMPT_STARTED,
            payload={"call_id": "call_retry_1", "attempt": 2},
        ),
        CheckpointEvent(
            sequence_id=7,
            timestamp="2026-08-15T12:00:06Z",
            run_id="run-2",
            event_type=CheckpointEventType.TOOL_ATTEMPT_ENDED,
            payload={"call_id": "call_retry_1", "attempt": 2, "status": "SUCCESS"},
        ),
        CheckpointEvent(
            sequence_id=8,
            timestamp="2026-08-15T12:00:07Z",
            run_id="run-2",
            event_type=CheckpointEventType.TOOL_RESULT_RECEIVED,
            payload={"call_id": "call_retry_1", "tool_name": "flaky_tool", "status": "SUCCESS"},
        ),
    ]

    usage = RunBudgetEngine.reconstruct_usage(events)
    assert usage.iterations_used == 1
    # Exactly 1 logical tool call, NOT 2 or 3!
    assert usage.tool_calls_used == 1


def test_reconstruct_usage_counts_distinct_tool_call_ids():
    events = [
        CheckpointEvent(
            sequence_id=1,
            timestamp="2026-08-15T12:00:00Z",
            run_id="run-3",
            event_type=CheckpointEventType.LLM_RESPONDED,
            payload={
                "iteration": 1,
                "tool_calls": [
                    {"call_id": "call_1", "name": "t1"},
                    {"call_id": "call_2", "name": "t2"},
                    {"call_id": "call_3", "name": "t3"},
                ],
            },
        ),
    ]
    usage = RunBudgetEngine.reconstruct_usage(events)
    assert usage.iterations_used == 1
    assert usage.tool_calls_used == 3


# ===========================================================================
# 4. Integration Harness & AgentLoop Tests
# ===========================================================================


class MockLLM(LLMProvider):
    def __init__(self, responses: List[LLMResponse]) -> None:
        self.responses = responses
        self.call_count = 0

    async def generate(self, messages: List[LLMMessage], tools: List[dict]) -> LLMResponse:
        resp = self.responses[self.call_count]
        self.call_count += 1
        return resp


class CountingTool:
    def __init__(self, name: str = "test_tool") -> None:
        self.name = name
        self.description = "counting tool"
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
            data={"count": self.execute_count},
        )


def _setup_loop(
    tmp_path: Any,
    responses: List[LLMResponse],
    tool: CountingTool,
    policy: RunPolicy,
) -> tuple[AgentLoop, CheckpointManager]:
    db_path = str(tmp_path / "idempotency.jsonl")
    cp_path = str(tmp_path / "checkpoints.jsonl")

    registry = ToolRegistry()
    registry.register_tool(tool)

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

    llm = MockLLM(responses)
    loop = AgentLoop(
        llm_provider=llm,
        tool_executor=tool_executor,
        tool_registry=registry,
        checkpoints=checkpoints,
        policy=policy,
    )
    return loop, checkpoints


@pytest.mark.asyncio
async def test_fresh_run_max_iterations_exhaustion(tmp_path: Any):
    tool = CountingTool()
    # LLM keeps returning tool calls
    responses = [
        LLMResponse(provider="mock", provider_response_id="1", content=None, tool_calls=[ProviderToolCall("c1", "test_tool", {})]),
        LLMResponse(provider="mock", provider_response_id="2", content=None, tool_calls=[ProviderToolCall("c2", "test_tool", {})]),
        LLMResponse(provider="mock", provider_response_id="3", content=None, tool_calls=[ProviderToolCall("c3", "test_tool", {})]),
    ]
    policy = RunPolicy(max_iterations=2, max_tool_calls=10, timeout_seconds=10)
    loop, checkpoints = _setup_loop(tmp_path, responses, tool, policy)

    res = await loop.run("run-iter-limit", "sys", "user")
    assert res is None

    # Checkpoint contains MAX_ITERATIONS_REACHED
    from src.agent.replay_engine import ReplayEngine
    events = ReplayEngine.load_events_for_run(checkpoints.db_path, "run-iter-limit")
    assert any(e.event_type == CheckpointEventType.RUN_HALTED and e.payload.get("reason") == "MAX_ITERATIONS_REACHED" for e in events)


@pytest.mark.asyncio
async def test_fresh_run_max_tool_calls_exhaustion(tmp_path: Any):
    tool = CountingTool()
    responses = [
        LLMResponse(
            provider="mock",
            provider_response_id="1",
            content=None,
            tool_calls=[
                ProviderToolCall("c1", "test_tool", {"x": 1}),
                ProviderToolCall("c2", "test_tool", {"x": 2}),
                ProviderToolCall("c3", "test_tool", {"x": 3}),
            ],
        ),
    ]
    policy = RunPolicy(max_iterations=5, max_tool_calls=2, timeout_seconds=10)
    loop, checkpoints = _setup_loop(tmp_path, responses, tool, policy)

    res = await loop.run("run-tool-limit", "sys", "user")
    assert res is None

    # Exactly 2 tool calls executed, 3rd was rejected
    assert tool.execute_count == 2
    from src.agent.replay_engine import ReplayEngine
    events = ReplayEngine.load_events_for_run(checkpoints.db_path, "run-tool-limit")
    assert any(e.event_type == CheckpointEventType.RUN_HALTED and e.payload.get("reason") == "MAX_TOOL_CALLS_REACHED" for e in events)


@pytest.mark.asyncio
async def test_resume_preserves_and_enforces_consumed_iteration_budget(tmp_path: Any):
    """Resume cannot reset iteration budget."""
    cp_path = str(tmp_path / "checkpoints.jsonl")
    checkpoints = CheckpointManager(db_path=cp_path)

    run_id = "run-resume-iter"
    checkpoints.log_run_started(run_id, "sys", "user")
    checkpoints.log_llm_requested(run_id, iteration=1)
    checkpoints.log_llm_responded(run_id, iteration=1, content=None, num_tool_calls=1, tool_calls=[{"call_id": "c1", "name": "test_tool", "arguments": {"x": 1}}])
    checkpoints.log_tool_result_received(run_id, "c1", "success", tool_name="test_tool", result={"status": "success"})
    checkpoints.log_llm_requested(run_id, iteration=2)
    checkpoints.log_llm_responded(run_id, iteration=2, content=None, num_tool_calls=1, tool_calls=[{"call_id": "c2", "name": "test_tool", "arguments": {"x": 2}}])
    checkpoints.log_tool_result_received(run_id, "c2", "success", tool_name="test_tool", result={"status": "success"})

    # Prior iterations used == 2. Policy allows max_iterations=2.
    policy = RunPolicy(max_iterations=2, max_tool_calls=10, timeout_seconds=10)
    tool = CountingTool()
    responses = [
        LLMResponse(provider="mock", provider_response_id="3", content="Final response after resume", tool_calls=[]),
    ]
    loop, _ = _setup_loop(tmp_path, responses, tool, policy)

    # Resume must immediately halt because 2/2 iterations were already used
    res = await loop.resume(run_id)
    assert res is None

    from src.agent.replay_engine import ReplayEngine
    events = ReplayEngine.load_events_for_run(checkpoints.db_path, run_id)
    assert any(e.event_type == CheckpointEventType.RUN_HALTED and e.payload.get("reason") == "MAX_ITERATIONS_REACHED" for e in events)


@pytest.mark.asyncio
async def test_resume_preserves_and_enforces_consumed_tool_budget(tmp_path: Any):
    """Resume cannot reset tool-call budget."""
    cp_path = str(tmp_path / "checkpoints.jsonl")
    checkpoints = CheckpointManager(db_path=cp_path)

    run_id = "run-resume-tools"
    checkpoints.log_run_started(run_id, "sys", "user")
    checkpoints.log_llm_requested(run_id, iteration=1)
    checkpoints.log_llm_responded(
        run_id,
        iteration=1,
        content=None,
        num_tool_calls=2,
        tool_calls=[
            {"call_id": "c1", "name": "test_tool", "arguments": {"x": 1}},
            {"call_id": "c2", "name": "test_tool", "arguments": {"x": 2}},
        ],
    )
    # c1 completed before crash, c2 was pending
    checkpoints.log_tool_result_received(run_id, "c1", "success", tool_name="test_tool", result={"status": "success"})

    # Policy max_tool_calls=1. c1 already used 1.
    policy = RunPolicy(max_iterations=5, max_tool_calls=1, timeout_seconds=10)
    tool = CountingTool()
    responses = []
    loop, _ = _setup_loop(tmp_path, responses, tool, policy)

    # Resume attempts to execute pending tool c2, but budget is exhausted!
    res = await loop.resume(run_id)
    assert res is None
    assert tool.execute_count == 0  # c2 was rejected before execution!

    from src.agent.replay_engine import ReplayEngine
    events = ReplayEngine.load_events_for_run(checkpoints.db_path, run_id)
    assert any(e.event_type == CheckpointEventType.RUN_HALTED and e.payload.get("reason") == "MAX_TOOL_CALLS_REACHED" for e in events)


@pytest.mark.asyncio
async def test_multi_step_crash_resume_budget_integration_scenario(tmp_path: Any):
    """
    Integration Scenario from TASK-007:
    policy: max_iterations=3, max_tool_calls=2
    run consumes iteration 1 + tool A
    process interruption
    resume consumes iteration 2 + tool B
    next requested tool C -> HALT MAX_TOOL_CALLS_REACHED
    no tool C execution occurs
    """
    cp_path = str(tmp_path / "checkpoints.jsonl")
    checkpoints = CheckpointManager(db_path=cp_path)

    run_id = "scenario-1"
    # Step 1: Run consumes iteration 1 + tool A
    checkpoints.log_run_started(run_id, "sys", "user")
    checkpoints.log_llm_requested(run_id, iteration=1)
    checkpoints.log_llm_responded(
        run_id,
        iteration=1,
        content=None,
        num_tool_calls=1,
        tool_calls=[{"call_id": "call_A", "name": "test_tool", "arguments": {"x": "A"}}],
    )
    checkpoints.log_tool_result_received(run_id, "call_A", "success", tool_name="test_tool", result={"status": "success"})

    # Process interruption happens here.
    # Resume starts with policy max_iterations=3, max_tool_calls=2
    policy = RunPolicy(max_iterations=3, max_tool_calls=2, timeout_seconds=10)
    tool = CountingTool()
    # Resumed LLM emits tool B in iteration 2, then tool C in iteration 3
    responses = [
        LLMResponse(provider="mock", provider_response_id="2", content=None, tool_calls=[ProviderToolCall("call_B", "test_tool", {"x": "B"})]),
        LLMResponse(provider="mock", provider_response_id="3", content=None, tool_calls=[ProviderToolCall("call_C", "test_tool", {"x": "C"})]),
    ]
    loop, _ = _setup_loop(tmp_path, responses, tool, policy)

    res = await loop.resume(run_id)
    assert res is None

    # tool B was executed (count = 1), tool C was rejected before execution!
    assert tool.execute_count == 1

    from src.agent.replay_engine import ReplayEngine
    events = ReplayEngine.load_events_for_run(checkpoints.db_path, run_id)
    assert any(e.event_type == CheckpointEventType.RUN_HALTED and e.payload.get("reason") == "MAX_TOOL_CALLS_REACHED" for e in events)


@pytest.mark.asyncio
async def test_timeout_halts_with_timeout_reached(tmp_path: Any):
    """Timeout path logs TIMEOUT_REACHED correctly."""
    tool = CountingTool()

    async def slow_generate(*args, **kwargs):
        await asyncio.sleep(0.5)
        return LLMResponse(provider="mock", provider_response_id="1", content="done", tool_calls=[])

    mock_llm = Mock()
    mock_llm.generate = slow_generate

    db_path = str(tmp_path / "idempotency.jsonl")
    cp_path = str(tmp_path / "checkpoints.jsonl")
    registry = ToolRegistry()
    registry.register_tool(tool)
    checkpoints = CheckpointManager(db_path=cp_path)
    tool_executor = ToolExecutor(registry=registry, idempotency_store=JsonlIdempotencyStore(db_path=db_path), retry_manager=RetryManager(), checkpoints=checkpoints, context={})

    loop = AgentLoop(
        llm_provider=mock_llm,
        tool_executor=tool_executor,
        tool_registry=registry,
        checkpoints=checkpoints,
        policy=RunPolicy(max_iterations=5, max_tool_calls=5, timeout_seconds=0.05),
    )

    res = await loop.run("run-timeout", "sys", "user")
    assert res is None

    from src.agent.replay_engine import ReplayEngine
    events = ReplayEngine.load_events_for_run(checkpoints.db_path, "run-timeout")
    assert any(e.event_type == CheckpointEventType.RUN_HALTED and e.payload.get("reason") == "TIMEOUT_REACHED" for e in events)


@pytest.mark.asyncio
async def test_cancellation_wins_over_budget_execution(tmp_path: Any):
    """Cancellation prevents execution and is not overridden by budget handling."""
    tool = CountingTool()
    policy = RunPolicy(max_iterations=5, max_tool_calls=5, timeout_seconds=10)
    loop, checkpoints = _setup_loop(tmp_path, [], tool, policy)

    loop.cancellation_controller.cancel("run-cancel", "User cancelled task")

    res = await loop.run("run-cancel", "sys", "user")
    assert res is None
    assert tool.execute_count == 0


class FlakyTool:
    def __init__(self, name: str = "flaky_tool") -> None:
        self.name = name
        self.description = "flaky tool"
        self.attempts = 0

    def get_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}}

    async def execute(self, call: ToolCall, context: Dict[str, Any]) -> ToolResult:
        self.attempts += 1
        if self.attempts == 1:
            from src.core.errors import AgentException
            raise AgentException(message="Transient 503 error", code="HTTP_503", retryable=True)
        return ToolResult(
            call_id=call.call_id,
            run_id=call.run_id,
            tool_name=call.name,
            status=ToolStatus.SUCCESS,
            data={"result": "recovered"},
        )


@pytest.mark.asyncio
async def test_tool_retry_attempts_do_not_inflate_logical_tool_call_budget(tmp_path: Any):
    """
    Retry scenario from TASK-007:
    policy max_tool_calls=1
    LLM requests tool A
    A fails once, retries, then succeeds
    run must not halt merely because A used 2 attempts
    logical tool budget used == 1
    """
    flaky = FlakyTool()
    db_path = str(tmp_path / "idempotency.jsonl")
    cp_path = str(tmp_path / "checkpoints.jsonl")

    registry = ToolRegistry()
    registry.register_tool(flaky)

    store = JsonlIdempotencyStore(db_path=db_path)
    checkpoints = CheckpointManager(db_path=cp_path)
    from src.core.retry import RetryPolicy
    retry_manager = RetryManager(default_policy=RetryPolicy(max_attempts=3, base_delay=0.01, max_delay=0.1, jitter=False))

    tool_executor = ToolExecutor(
        registry=registry,
        idempotency_store=store,
        retry_manager=retry_manager,
        checkpoints=checkpoints,
        context={},
    )

    responses = [
        LLMResponse(provider="mock", provider_response_id="1", content=None, tool_calls=[ProviderToolCall("call_flaky", "flaky_tool", {})]),
        LLMResponse(provider="mock", provider_response_id="2", content="Final Answer Success", tool_calls=[]),
    ]
    llm = MockLLM(responses)
    # Policy permits exactly 1 logical tool call
    policy = RunPolicy(max_iterations=5, max_tool_calls=1, timeout_seconds=10)
    loop = AgentLoop(
        llm_provider=llm,
        tool_executor=tool_executor,
        tool_registry=registry,
        checkpoints=checkpoints,
        policy=policy,
    )

    res = await loop.run("run-retry-budget", "sys", "user")
    # Must successfully complete with final answer!
    assert res == "Final Answer Success"
    assert flaky.attempts == 2  # 2 attempts were made under the hood

    # Check reconstructed budget usage
    from src.agent.replay_engine import ReplayEngine
    events = ReplayEngine.load_events_for_run(checkpoints.db_path, "run-retry-budget")
    usage = RunBudgetEngine.reconstruct_usage(events)
    assert usage.iterations_used == 2
    assert usage.tool_calls_used == 1  # Exactly 1 logical tool call!


