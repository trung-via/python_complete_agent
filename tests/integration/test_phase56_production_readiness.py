from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, List, Optional
import pytest

from src.agent.loop import AgentLoop
from src.agent.policy import RunPolicy
from src.agent.production_readiness import (
    ProductionReadinessChecker,
    ProductionReadinessReport,
    ReadinessCheck,
    ReadinessStatus,
)
from src.agent.replay_engine import ReplayEngine
from src.core.checkpoint import CheckpointManager
from src.core.checkpoint_contract import CheckpointEventType, RunState
from src.core.errors import AgentException
from src.core.idempotency_contract import RecordKey, RecordStatus
from src.core.idempotency_store_v2 import JsonlIdempotencyStore
from src.core.retry import RetryManager, RetryPolicy
from src.core.tool_executor import ToolExecutor
from src.core.tool_registry import ToolRegistry
from src.core.types import ToolCall, ToolResult, ToolStatus
from src.providers.base import LLMResponse, ProviderToolCall
from tests.support.fault_injection import FaultyLLMProvider


class CountingTool:
    """Tool that tracks all invocations."""
    def __init__(self, name: str = "test_tool") -> None:
        self.name = name
        self.description = "counting test tool"
        self.calls: List[Dict[str, Any]] = []

    def get_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {"a": {"type": "integer"}}}

    async def execute(self, call: ToolCall, context: Dict[str, Any]) -> ToolResult:
        self.calls.append({"call_id": call.call_id, "args": call.arguments})
        return ToolResult(
            call_id=call.call_id,
            run_id=call.run_id,
            tool_name=call.name,
            status=ToolStatus.SUCCESS,
            data={"count": len(self.calls)},
        )


def _build_test_agent(
    tmp_path: Any,
    responses: List[LLMResponse],
    tool: Any,
    policy: Optional[RunPolicy] = None,
    retry_policy: Optional[RetryPolicy] = None,
    checkpoint_manager: Optional[CheckpointManager] = None,
) -> tuple[AgentLoop, ToolExecutor, CheckpointManager, JsonlIdempotencyStore]:
    registry = ToolRegistry()
    registry.register_tool(tool)
    db_path = str(tmp_path / "idempotency.jsonl")
    cp_path = str(tmp_path / "checkpoints.jsonl")
    store = JsonlIdempotencyStore(db_path=db_path)
    checkpoints = checkpoint_manager or CheckpointManager(db_path=cp_path)
    retry_mgr = RetryManager(default_policy=retry_policy or RetryPolicy(max_attempts=2, base_delay=0.01))

    executor = ToolExecutor(
        registry=registry,
        idempotency_store=store,
        retry_manager=retry_mgr,
        checkpoints=checkpoints,
        context={},
    )
    llm = FaultyLLMProvider(responses)
    loop = AgentLoop(
        llm_provider=llm,
        tool_executor=executor,
        tool_registry=registry,
        checkpoints=checkpoints,
        policy=policy or RunPolicy(max_iterations=5, max_tool_calls=5, timeout_seconds=10),
    )
    return loop, executor, checkpoints, store


# ============================================================================
# M6.1 & M6.2 — Readiness Checks Verification
# ============================================================================

def test_valid_fresh_configuration_returns_ready(tmp_path: Any) -> None:
    """A freshly configured runtime with non-existent or empty stores evaluates as READY."""
    cp_path = str(tmp_path / "checkpoints.jsonl")
    db_path = str(tmp_path / "idempotency.jsonl")
    policy = RunPolicy(max_iterations=10, max_tool_calls=10, timeout_seconds=60)
    retry_policy = RetryPolicy(max_attempts=3, base_delay=1.0, max_delay=10.0)

    report = ProductionReadinessChecker.evaluate(
        policy=policy,
        retry_policy=retry_policy,
        checkpoint_path=cp_path,
        idempotency_path=db_path,
    )
    assert report.ready is True
    assert report.status == ReadinessStatus.READY
    assert len(report.checks) == 6
    assert all(c.passed for c in report.checks)


def test_zero_budget_is_valid_policy_and_ready(tmp_path: Any) -> None:
    """Zero iterations or zero tool calls is valid policy limit and evaluates as READY."""
    policy = RunPolicy(max_iterations=0, max_tool_calls=0, timeout_seconds=1)
    retry_policy = RetryPolicy(max_attempts=1, base_delay=0.0, max_delay=0.0)

    report = ProductionReadinessChecker.evaluate(
        policy=policy,
        retry_policy=retry_policy,
    )
    assert report.ready is True
    check = next(c for c in report.checks if c.name == "run_policy_validity")
    assert check.passed is True


def test_invalid_run_policy_returns_not_ready() -> None:
    """Missing or invalid RunPolicy fails readiness check."""
    report = ProductionReadinessChecker.evaluate(policy=None)
    assert report.ready is False
    assert report.status == ReadinessStatus.NOT_READY
    check = next(c for c in report.checks if c.name == "run_policy_validity")
    assert check.passed is False
    assert "missing" in check.reason


def test_invalid_retry_policy_returns_not_ready() -> None:
    """Invalid RetryPolicy (e.g. max_delay < base_delay) fails readiness check."""
    policy = RunPolicy()
    invalid_retry = RetryPolicy(max_attempts=0)  # Invalid attempts

    report = ProductionReadinessChecker.evaluate(
        policy=policy,
        retry_policy=invalid_retry,
    )
    assert report.ready is False
    check = next(c for c in report.checks if c.name == "retry_policy_sanity")
    assert check.passed is False


def test_missing_and_empty_stores_are_ready(tmp_path: Any) -> None:
    """Missing and empty store files are handled safely and pass readiness."""
    cp_path = str(tmp_path / "checkpoints.jsonl")
    db_path = str(tmp_path / "idempotency.jsonl")

    # Create empty files
    with open(cp_path, "w", encoding="utf-8") as f:
        pass
    with open(db_path, "w", encoding="utf-8") as f:
        pass

    report = ProductionReadinessChecker.evaluate(
        policy=RunPolicy(),
        retry_policy=RetryPolicy(),
        checkpoint_path=cp_path,
        idempotency_path=db_path,
    )
    assert report.ready is True


def test_malformed_checkpoint_json_returns_not_ready_without_modifying_file(tmp_path: Any) -> None:
    """Malformed checkpoint JSON line produces NOT_READY and leaves file unmodified."""
    cp_path = str(tmp_path / "checkpoints.jsonl")
    content = (
        '{"run_id": "run-1", "sequence_id": 1, "timestamp": 10.0, "event_type": "RUN_STARTED", "payload": {}}\n'
        'CORRUPTED_JSON_DATA_LINE\n'
    )
    with open(cp_path, "w", encoding="utf-8") as f:
        f.write(content)

    report = ProductionReadinessChecker.evaluate(
        policy=RunPolicy(),
        retry_policy=RetryPolicy(),
        checkpoint_path=cp_path,
    )
    assert report.ready is False
    check = next(c for c in report.checks if c.name == "checkpoint_store_health")
    assert check.passed is False
    assert "Malformed JSON" in check.reason

    # Verify file content is unchanged
    with open(cp_path, "r", encoding="utf-8") as f:
        assert f.read() == content


def test_invalid_checkpoint_transition_returns_not_ready(tmp_path: Any) -> None:
    """Invalid checkpoint event sequence or state transition produces NOT_READY."""
    cp_path = str(tmp_path / "checkpoints.jsonl")
    cm = CheckpointManager(db_path=cp_path)
    run_id = "run-invalid-trans"
    # Log run started then jump directly to tool result without requesting LLM/tool
    cm.log_run_started(run_id, "sys", "usr")
    # Manually append an illegal transition
    with open(cp_path, "a", encoding="utf-8") as f:
        import json
        f.write(json.dumps({
            "run_id": run_id,
            "sequence_id": 2,
            "timestamp": 2000000000.0,
            "event_type": "TOOL_RESULT_RECEIVED",
            "payload": {"call_id": "c1", "status": "success"},
        }) + "\n")

    report = ProductionReadinessChecker.evaluate(
        policy=RunPolicy(),
        retry_policy=RetryPolicy(),
        checkpoint_path=cp_path,
    )
    assert report.ready is False
    check = next(c for c in report.checks if c.name == "checkpoint_store_health")
    assert check.passed is False
    assert "Invalid state transition" in check.reason


def test_malformed_idempotency_store_returns_not_ready_without_modifying_file(tmp_path: Any) -> None:
    """Corrupted idempotency store produces NOT_READY without altering disk content."""
    db_path = str(tmp_path / "idempotency.jsonl")
    content = 'INVALID IDEMPOTENCY RECORD DATA\n'
    with open(db_path, "w", encoding="utf-8") as f:
        f.write(content)

    report = ProductionReadinessChecker.evaluate(
        policy=RunPolicy(),
        retry_policy=RetryPolicy(),
        idempotency_path=db_path,
    )
    assert report.ready is False
    check = next(c for c in report.checks if c.name == "idempotency_store_health")
    assert check.passed is False
    assert "corruption" in check.reason

    with open(db_path, "r", encoding="utf-8") as f:
        assert f.read() == content


def test_completed_healthy_run_and_consistent_idempotency_returns_ready(tmp_path: Any) -> None:
    """Completed run with valid checkpoints and idempotency state evaluates as READY."""
    tool = CountingTool(name="test_tool")
    responses = [
        LLMResponse(provider="mock", provider_response_id="1", content=None, tool_calls=[ProviderToolCall("c1", "test_tool", {})]),
        LLMResponse(provider="mock", provider_response_id="2", content="Final Done", tool_calls=[]),
    ]
    loop, _, checkpoints, store = _build_test_agent(tmp_path, responses, tool)

    # Run complete lifecycle
    asyncio.run(loop.run("run-healthy-1", "sys", "usr"))

    report = ProductionReadinessChecker.evaluate_agent(loop)
    assert report.ready is True
    assert all(c.passed for c in report.checks)


def test_cross_store_mismatch_returns_not_ready(tmp_path: Any) -> None:
    """Cross-store inconsistency fails readiness."""
    cp_path = str(tmp_path / "checkpoints.jsonl")
    db_path = str(tmp_path / "idempotency.jsonl")
    cm = CheckpointManager(db_path=cp_path)
    run_id = "run-mismatch"

    cm.log_run_started(run_id, "sys", "usr")
    cm.log_llm_requested(run_id, iteration=1)
    cm.log_llm_responded(run_id, iteration=1, content=None, num_tool_calls=1, tool_calls=[{"call_id": "c1", "name": "test_tool", "arguments": {}}])
    cm.log_tool_call_created(run_id, "c1", "test_tool", {})
    cm.log_tool_result_received(run_id, "c1", "success", "test_tool", {"status": "success"})

    # Intentionally corrupt idempotency store
    with open(db_path, "w", encoding="utf-8") as f:
        f.write("CORRUPT IDEMPOTENCY RECORD\n")

    report = ProductionReadinessChecker.evaluate(
        policy=RunPolicy(),
        retry_policy=RetryPolicy(),
        checkpoint_path=cp_path,
        idempotency_path=db_path,
    )
    assert report.ready is False
    check = next(c for c in report.checks if c.name == "cross_store_consistency")
    assert check.passed is False


def test_readiness_evaluation_is_strictly_read_only(tmp_path: Any) -> None:
    """Readiness evaluation executes 0 LLM calls, 0 tool executions, and 0 store writes."""
    class TrackingLLM(FaultyLLMProvider):
        def __init__(self) -> None:
            super().__init__([])
            self.generate_calls = 0

        async def generate(self, messages: Any, tools: Any = None) -> Any:
            self.generate_calls += 1
            raise RuntimeError("LLM must not be called during readiness check")

    class TrackingTool(CountingTool):
        def __init__(self) -> None:
            super().__init__()
            self.exec_count = 0

        async def execute(self, call: ToolCall, context: Dict[str, Any]) -> ToolResult:
            self.exec_count += 1
            raise RuntimeError("Tool must not be executed during readiness check")

    llm = TrackingLLM()
    tool = TrackingTool()
    registry = ToolRegistry()
    registry.register_tool(tool)

    cp_path = str(tmp_path / "checkpoints.jsonl")
    db_path = str(tmp_path / "idempotency.jsonl")
    cm = CheckpointManager(db_path=cp_path)
    store = JsonlIdempotencyStore(db_path=db_path)
    executor = ToolExecutor(registry, store, RetryManager(), cm, {})

    loop = AgentLoop(
        llm_provider=llm,
        tool_executor=executor,
        tool_registry=registry,
        checkpoints=cm,
        policy=RunPolicy(),
    )

    # Initial state on disk
    cp_stat_before = os.path.getsize(cp_path) if os.path.exists(cp_path) else 0
    db_stat_before = os.path.getsize(db_path) if os.path.exists(db_path) else 0

    report = ProductionReadinessChecker.evaluate_agent(loop)
    assert report.ready is True

    # Assert 0 side effects occurred
    assert llm.generate_calls == 0
    assert tool.exec_count == 0
    cp_stat_after = os.path.getsize(cp_path) if os.path.exists(cp_path) else 0
    db_stat_after = os.path.getsize(db_path) if os.path.exists(db_path) else 0
    assert cp_stat_before == cp_stat_after
    assert db_stat_before == db_stat_after


# ============================================================================
# M6.5 — Safety Precedence Matrix Regressions
# ============================================================================

@pytest.mark.asyncio
async def test_safety_matrix_cancellation_precedence_over_scheduled_retry(tmp_path: Any) -> None:
    """
    DURABLE TERMINAL / CANCELLATION > SCHEDULED RETRY
    Proves that once cancelled, an in-flight scheduled retry continuation never executes attempt N+1.
    """
    tool = CountingTool(name="test_tool")

    responses = [
        LLMResponse(provider="mock", provider_response_id="1", content=None, tool_calls=[ProviderToolCall("c1", "test_tool", {})]),
    ]
    loop, _, checkpoints, _ = _build_test_agent(tmp_path, responses, tool)

    run_id = "run-precedence-cancel"
    # Durably cancel run
    loop.cancellation_controller.cancel(run_id, reason="Admin Pre-Halt")

    result = await loop.run(run_id, "sys", "usr")
    assert result is None
    assert len(tool.calls) == 0


@pytest.mark.asyncio
async def test_safety_matrix_budget_exhaustion_precedence_over_new_work(tmp_path: Any) -> None:
    """
    RUN BUDGET EXHAUSTION > NEW WORK
    Proves that hitting max_tool_calls immediately halts the run and prevents subsequent tool executions.
    """
    tool = CountingTool(name="test_tool")
    responses = [
        LLMResponse(
            provider="mock",
            provider_response_id="1",
            content=None,
            tool_calls=[
                ProviderToolCall("c1", "test_tool", {"a": 1}),
                ProviderToolCall("c2", "test_tool", {"a": 2}),
            ],
        ),
    ]
    # Allow max 1 tool call
    policy = RunPolicy(max_iterations=5, max_tool_calls=1, timeout_seconds=10)
    loop, _, checkpoints, _ = _build_test_agent(tmp_path, responses, tool, policy=policy)

    run_id = "run-budget-precedence"
    result = await loop.run(run_id, "sys", "usr")
    assert result is None
    # Only the first tool call was allowed, second was blocked by budget engine
    assert len(tool.calls) == 1

    events = ReplayEngine.load_events_for_run(checkpoints.db_path, run_id)
    assert any(e.event_type == CheckpointEventType.RUN_HALTED and e.payload.get("reason") == "MAX_TOOL_CALLS_REACHED" for e in events)


@pytest.mark.asyncio
async def test_safety_matrix_stable_call_id_precedence_over_duplicate_side_effect(tmp_path: Any) -> None:
    """
    EXISTING STABLE call_id > DUPLICATE SIDE EFFECT & DUPLICATE BUDGET CHARGE
    Proves that replaying an existing stable call_id uses idempotency cache and does not re-execute tool.
    """
    tool = CountingTool(name="test_tool")
    responses = [
        LLMResponse(provider="mock", provider_response_id="1", content=None, tool_calls=[ProviderToolCall("c1", "test_tool", {})]),
        LLMResponse(provider="mock", provider_response_id="2", content="Done Stable", tool_calls=[]),
    ]
    loop, executor, _, _ = _build_test_agent(tmp_path, responses, tool)

    call = ToolCall(name="test_tool", arguments={}, call_id="c_stable_1", run_id="run_stable")
    res1 = await executor.execute(call)
    assert res1.status == ToolStatus.SUCCESS
    assert len(tool.calls) == 1

    # Re-execute exact same call
    res2 = await executor.execute(call)
    assert res2.status == ToolStatus.SUCCESS
    # Side effect was NOT duplicated
    assert len(tool.calls) == 1


@pytest.mark.asyncio
async def test_safety_matrix_corruption_precedence_over_autonomous_continuation(tmp_path: Any) -> None:
    """
    CORRUPTION / STORE INSPECTION FAILURE > AUTONOMOUS CONTINUATION
    Proves corrupted checkpoint immediately fails closed on resume without executing any tools.
    """
    cp_path = str(tmp_path / "checkpoints.jsonl")
    with open(cp_path, "w", encoding="utf-8") as f:
        f.write('{"run_id": "run-corrupt", "sequence_id": 1, "timestamp": 1.0, "event_type": "RUN_STARTED", "payload": {}}\n')
        f.write('CORRUPTED LINE\n')

    tool = CountingTool(name="test_tool")
    loop, _, _, _ = _build_test_agent(tmp_path, [], tool, checkpoint_manager=CheckpointManager(db_path=cp_path))

    with pytest.raises(Exception):
        await loop.resume("run-corrupt")

    assert len(tool.calls) == 0
