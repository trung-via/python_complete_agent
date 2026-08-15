from __future__ import annotations

import asyncio
import json
import os
import time
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
from src.core.retry_policy import RetryDecision, RetryPolicyEngine, RetryReason
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
    invalid_retry = RetryPolicy(max_attempts=0)

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


def test_idempotency_lifecycle_inconsistency_fails_closed_without_modifying_file(tmp_path: Any) -> None:
    """
    Syntactically valid JSONL with an impossible lifecycle transition (e.g. COMPLETED -> IN_PROGRESS)
    fails closed (NOT_READY) and leaves file unmodified.
    """
    db_path = str(tmp_path / "idempotency.jsonl")
    rec1 = {
        "key": {"operation_key": "tool:test", "idempotency_key": "run_1"},
        "status": "COMPLETED",
        "updated_at": 100.0,
        "owner_id": "owner1",
        "attempt": 1,
        "data": {"res": "ok"},
    }
    # Illegal reopening of terminal COMPLETED record
    rec2 = {
        "key": {"operation_key": "tool:test", "idempotency_key": "run_1"},
        "status": "IN_PROGRESS",
        "updated_at": 101.0,
        "owner_id": "owner2",
        "attempt": 2,
    }
    content = f"{json.dumps(rec1)}\n{json.dumps(rec2)}\n"
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
    assert "illegal transition from terminal status COMPLETED to IN_PROGRESS" in check.reason

    with open(db_path, "r", encoding="utf-8") as f:
        assert f.read() == content


def test_readiness_evaluation_is_strictly_read_only(tmp_path: Any) -> None:
    """
    Readiness evaluation does not create directories, does not create .lock files,
    does not modify store files, and makes 0 provider/tool calls.
    """
    # Target in a non-existent subfolder
    sub_dir = tmp_path / "non_existent_subdir"
    cp_path = str(sub_dir / "checkpoints.jsonl")
    db_path = str(sub_dir / "idempotency.jsonl")
    lock_path = f"{db_path}.lock"

    report = ProductionReadinessChecker.evaluate(
        policy=RunPolicy(),
        retry_policy=RetryPolicy(),
        checkpoint_path=cp_path,
        idempotency_path=db_path,
    )
    assert report.ready is True

    # Assert non-existent directory was NOT created
    assert not os.path.exists(str(sub_dir))
    # Assert lock file was NOT created
    assert not os.path.exists(lock_path)


def test_cross_store_pending_recoverable_call_missing_record_fails_closed(tmp_path: Any) -> None:
    """Pending recoverable call in non-terminal run with missing required idempotency record produces NOT_READY."""
    cp_path = str(tmp_path / "checkpoints.jsonl")
    db_path = str(tmp_path / "idempotency.jsonl")

    cm = CheckpointManager(db_path=cp_path)
    run_id = "run-pending-missing-idem"
    cm.log_run_started(run_id, "sys", "usr")
    cm.log_llm_requested(run_id, iteration=1)
    cm.log_llm_responded(
        run_id,
        iteration=1,
        content=None,
        num_tool_calls=1,
        tool_calls=[{"call_id": "c_pending_1", "name": "my_tool", "arguments": {"x": 1}}],
    )
    # Leave in TOOL_EXECUTING / LLM_WAITING state without completed record in idempotency
    with open(db_path, "w", encoding="utf-8") as f:
        pass

    report = ProductionReadinessChecker.evaluate(
        policy=RunPolicy(),
        retry_policy=RetryPolicy(),
        checkpoint_path=cp_path,
        idempotency_path=db_path,
    )
    assert report.ready is False
    check = next(c for c in report.checks if c.name == "cross_store_consistency")
    assert check.passed is False
    assert "missing required idempotency record" in check.reason


def test_cross_store_unrelated_completed_record_for_same_tool_does_not_mask_missing(tmp_path: Any) -> None:
    """
    If an unrelated COMPLETED record exists for the same tool name but different idempotency key,
    it must NOT satisfy the check for a completed call and must fail closed (NOT_READY).
    """
    cp_path = str(tmp_path / "checkpoints.jsonl")
    db_path = str(tmp_path / "idempotency.jsonl")

    cm = CheckpointManager(db_path=cp_path)
    run_id = "run-unrelated-mask"
    cm.log_run_started(run_id, "sys", "usr")
    cm.log_llm_requested(run_id, iteration=1)
    cm.log_llm_responded(
        run_id,
        iteration=1,
        content=None,
        num_tool_calls=1,
        tool_calls=[{"call_id": "c_target_1", "name": "my_tool", "arguments": {"x": 1}}],
    )
    cm.log_tool_call_created(run_id, "c_target_1", "my_tool", {"x": 1})
    cm.log_tool_result_received(run_id, "c_target_1", "success", "my_tool", {"res": "ok"})
    cm.log_run_completed(run_id)

    # In idempotency store, record an UNRELATED completed call for 'my_tool' with different args/key
    unrelated_key = {"operation_key": "tool:my_tool", "idempotency_key": "different_run_other_key"}
    unrelated_rec = {
        "key": unrelated_key,
        "status": "COMPLETED",
        "updated_at": 100.0,
        "owner_id": "owner1",
        "attempt": 1,
        "data": {"res": "other"},
    }
    with open(db_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(unrelated_rec) + "\n")

    report = ProductionReadinessChecker.evaluate(
        policy=RunPolicy(),
        retry_policy=RetryPolicy(),
        checkpoint_path=cp_path,
        idempotency_path=db_path,
    )
    assert report.ready is False
    check = next(c for c in report.checks if c.name == "cross_store_consistency")
    assert check.passed is False
    assert "missing exact idempotency record" in check.reason


def test_cross_store_exact_consistent_state_returns_ready(tmp_path: Any) -> None:
    """Exact matching completed records across checkpoint and idempotency stores evaluate as READY."""
    tool = CountingTool(name="test_tool")
    responses = [
        LLMResponse(provider="mock", provider_response_id="1", content=None, tool_calls=[ProviderToolCall("c1", "test_tool", {"a": 42})]),
        LLMResponse(provider="mock", provider_response_id="2", content="Done Exact", tool_calls=[]),
    ]
    loop, _, checkpoints, store = _build_test_agent(tmp_path, responses, tool)

    # Run complete lifecycle
    asyncio.run(loop.run("run-exact-ready", "sys", "usr"))

    report = ProductionReadinessChecker.evaluate_agent(loop)
    assert report.ready is True
    check = next(c for c in report.checks if c.name == "cross_store_consistency")
    assert check.passed is True


# ============================================================================
# M6.5 — Safety Precedence Matrix Regressions
# ============================================================================

@pytest.mark.asyncio
async def test_safety_matrix_cancellation_precedence_over_scheduled_retry(tmp_path: Any) -> None:
    """
    DURABLE TERMINAL / CANCELLATION > SCHEDULED RETRY
    Attempt 1 fails transiently, RETRY_SCHEDULED is durably recorded, run is cancelled
    during backoff before attempt 2. Invariant: Attempt 2 never executes (attempts == 1).
    """
    class FlakyToolWithAttemptCount:
        def __init__(self) -> None:
            self.name = "flaky_matrix_tool"
            self.description = "flaky tool"
            self.attempts = 0

        def get_schema(self) -> Dict[str, Any]:
            return {"type": "object", "properties": {}}

        async def execute(self, call: ToolCall, context: Dict[str, Any]) -> ToolResult:
            self.attempts += 1
            if self.attempts == 1:
                raise AgentException(message="503 Unavailable", code="HTTP_503", retryable=True)
            return ToolResult(call_id=call.call_id, run_id=call.run_id, tool_name=call.name, status=ToolStatus.SUCCESS)

    db_path = str(tmp_path / "idempotency.jsonl")
    cp_path = str(tmp_path / "checkpoints.jsonl")
    store = JsonlIdempotencyStore(db_path=db_path)
    checkpoints = CheckpointManager(db_path=cp_path)
    tool = FlakyToolWithAttemptCount()

    registry = ToolRegistry()
    registry.register_tool(tool)

    run_id = "run-cancel-during-backoff"
    checkpoints.log_run_started(run_id, "sys", "usr")

    class CancellingRetryManager(RetryManager):
        async def execute_with_retry(self, operation: Any, *args: Any, **kwargs: Any) -> Any:
            orig_on_retry = kwargs.get("on_retry_scheduled")
            def hook_on_retry(att: int, next_att: int, delay: float, reason: str, domain: str) -> None:
                if orig_on_retry:
                    orig_on_retry(att, next_att, delay, reason, domain)
                # Durably cancel the run right after retry is scheduled
                checkpoints.log_run_halted(run_id, reason="EXTERNAL_CANCELLATION")

            kwargs["on_retry_scheduled"] = hook_on_retry
            return await super().execute_with_retry(operation, *args, **kwargs)

    retry_manager = CancellingRetryManager(default_policy=RetryPolicy(max_attempts=3, base_delay=0.01, jitter=False))
    executor = ToolExecutor(registry, store, retry_manager, checkpoints, {})

    call = ToolCall(name="flaky_matrix_tool", arguments={}, call_id="c_cancel_matrix", run_id=run_id)
    result = await executor.execute(call)

    # Invariant: Attempt 2 NEVER executed
    assert tool.attempts == 1
    assert result.status == ToolStatus.FAILURE


@pytest.mark.asyncio
async def test_safety_matrix_retry_policy_engine_stop_precedence_over_retry_continuation(tmp_path: Any) -> None:
    """
    RetryPolicyEngine STOP > RETRY CONTINUATION
    Proves that when policy engine returns STOP (e.g. fatal 400 or max attempts exceeded),
    retry continuation immediately halts and returns fatal failure without attempt N+1.
    """
    class FatalErrorTool:
        def __init__(self) -> None:
            self.name = "fatal_tool"
            self.description = "fatal tool"
            self.attempts = 0

        def get_schema(self) -> Dict[str, Any]:
            return {"type": "object", "properties": {}}

        async def execute(self, call: ToolCall, context: Dict[str, Any]) -> ToolResult:
            self.attempts += 1
            # Fatal non-retryable 400 Bad Request
            raise AgentException(message="400 Bad Request", code="HTTP_400", retryable=False)

    db_path = str(tmp_path / "idempotency.jsonl")
    cp_path = str(tmp_path / "checkpoints.jsonl")
    store = JsonlIdempotencyStore(db_path=db_path)
    checkpoints = CheckpointManager(db_path=cp_path)
    tool = FatalErrorTool()

    registry = ToolRegistry()
    registry.register_tool(tool)
    retry_manager = RetryManager(default_policy=RetryPolicy(max_attempts=3, base_delay=0.01))
    executor = ToolExecutor(registry, store, retry_manager, checkpoints, {})

    run_id = "run-stop-precedence"
    call = ToolCall(name="fatal_tool", arguments={}, call_id="c_stop_1", run_id=run_id)
    result = await executor.execute(call)

    # Invariant: Non-retryable STOP prevented retry continuation
    assert tool.attempts == 1
    assert result.status == ToolStatus.FAILURE
    assert result.error is not None
    assert result.error.code == "HTTP_400"


@pytest.mark.asyncio
async def test_safety_matrix_stable_call_id_precedence_over_duplicate_budget_charge(tmp_path: Any) -> None:
    """
    EXISTING STABLE call_id > DUPLICATE LOGICAL BUDGET CHARGE
    Proves that when resuming an interrupted run with an existing stable call_id,
    the tool call budget is NOT double-charged and side effect is not re-executed.
    """
    tool = CountingTool(name="test_tool")
    db_path = str(tmp_path / "idempotency.jsonl")
    cp_path = str(tmp_path / "checkpoints.jsonl")

    # Policy allows exactly 1 tool call
    policy = RunPolicy(max_iterations=5, max_tool_calls=1, timeout_seconds=10)

    # 1. Execute tool call and complete it
    call = ToolCall(name="test_tool", arguments={"a": 1}, call_id="c_stable_budget_1", run_id="run_budget_dedupe")
    store = JsonlIdempotencyStore(db_path=db_path)
    cm = CheckpointManager(db_path=cp_path)
    cm.log_run_started("run_budget_dedupe", "sys", "usr")
    cm.log_llm_requested("run_budget_dedupe", iteration=1)
    cm.log_llm_responded("run_budget_dedupe", iteration=1, content=None, num_tool_calls=1, tool_calls=[{"call_id": "c_stable_budget_1", "name": "test_tool", "arguments": {"a": 1}}])

    registry = ToolRegistry()
    registry.register_tool(tool)
    executor = ToolExecutor(registry, store, RetryManager(), cm, {})
    res1 = await executor.execute(call)
    assert res1.status == ToolStatus.SUCCESS
    assert len(tool.calls) == 1

    # Checkpoint tool result
    cm.log_tool_result_received("run_budget_dedupe", "c_stable_budget_1", "success", "test_tool", {"count": 1})

    # 2. Resume run
    responses = [
        LLMResponse(provider="mock", provider_response_id="2", content="Final Resumed Done", tool_calls=[]),
    ]
    llm = FaultyLLMProvider(responses)
    loop = AgentLoop(
        llm_provider=llm,
        tool_executor=executor,
        tool_registry=registry,
        checkpoints=cm,
        policy=policy,
    )

    final_answer = await loop.resume("run_budget_dedupe")
    assert final_answer == "Final Resumed Done"

    # Invariant: Side effect was NOT duplicated
    assert len(tool.calls) == 1
    # Run completed successfully without false MAX_TOOL_CALLS_REACHED halt
    events = ReplayEngine.load_events_for_run(cp_path, "run_budget_dedupe")
    assert events[-1].event_type == CheckpointEventType.RUN_COMPLETED
