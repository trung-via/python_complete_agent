from __future__ import annotations

import asyncio
import json
import os
import threading
from typing import Any, Dict, List, Optional
import pytest

from src.agent.integrity_verifier import RunIntegrityVerifier
from src.agent.loop import AgentLoop
from src.agent.messages import LLMMessage, MessageRole
from src.agent.policy import RunPolicy
from src.core.cancellation import ControlEvent, RunCancellationController
from src.core.checkpoint import CheckpointManager
from src.core.checkpoint_contract import (
    CheckpointCorruptionError,
    CheckpointEventType,
    CheckpointStateError,
    RunState,
)
from src.core.errors import AgentException, RecoveryStateError, SystemStateError
from src.core.idempotency_store_v2 import JsonlIdempotencyStore
from src.core.retry import RetryManager, RetryPolicy
from src.core.run_budget import BudgetUsage, RunBudgetEngine
from src.core.tool_executor import ToolExecutor
from src.core.tool_registry import ToolRegistry
from src.core.types import ToolCall, ToolResult, ToolStatus
from src.providers.base import LLMProvider, LLMResponse, ProviderToolCall
from tests.support.fault_injection import (
    FaultInjector,
    FaultPoint,
    FaultyCheckpointManager,
    FaultyLLMProvider,
    FaultyTool,
    FaultInjectionException,
)


class BaseCountingTool:
    def __init__(self, name: str = "test_tool") -> None:
        self.name = name
        self.description = "counting tool"
        self.execute_count = 0
        self.executed_calls: List[ToolCall] = []

    def get_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {"val": {"type": "integer"}}}

    async def execute(self, call: ToolCall, context: Dict[str, Any]) -> ToolResult:
        self.execute_count += 1
        self.executed_calls.append(call)
        return ToolResult(
            call_id=call.call_id,
            run_id=call.run_id,
            tool_name=call.name,
            status=ToolStatus.SUCCESS,
            data={"execute_count": self.execute_count, "arguments": call.arguments},
        )


def _setup_agent(
    tmp_path: Any,
    responses: List[LLMResponse],
    tool: Any,
    policy: Optional[RunPolicy] = None,
    checkpoint_manager: Optional[CheckpointManager] = None,
    idempotency_store: Optional[JsonlIdempotencyStore] = None,
) -> tuple[AgentLoop, JsonlIdempotencyStore, CheckpointManager]:
    db_path = str(tmp_path / "idempotency.jsonl")
    cp_path = str(tmp_path / "checkpoints.jsonl")

    registry = ToolRegistry()
    registry.register_tool(tool)

    store = idempotency_store or JsonlIdempotencyStore(db_path=db_path)
    checkpoints = checkpoint_manager or CheckpointManager(db_path=cp_path)
    retry_manager = RetryManager(default_policy=RetryPolicy(max_attempts=3, base_delay=0.01, max_delay=0.05, jitter=False))

    executor = ToolExecutor(
        registry=registry,
        idempotency_store=store,
        retry_manager=retry_manager,
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
    return loop, store, checkpoints


# ============================================================================
# M5.2 — Crash Boundary Verification
# ============================================================================

@pytest.mark.asyncio
async def test_crash_after_llm_response_before_tool_execution_resumes_cleanly(tmp_path: Any) -> None:
    """Crash after LLM response but before tool execution; resume reconstructs and executes pending tool."""
    tool = BaseCountingTool()
    cp_path = str(tmp_path / "checkpoints.jsonl")
    checkpoints = CheckpointManager(db_path=cp_path)

    run_id = "run-crash-before-tool"
    checkpoints.log_run_started(run_id, "sys", "usr")
    checkpoints.log_llm_requested(run_id, iteration=1)
    checkpoints.log_llm_responded(
        run_id,
        iteration=1,
        content=None,
        num_tool_calls=1,
        tool_calls=[{"call_id": "c1", "name": "test_tool", "arguments": {"val": 10}}],
    )
    # Process crash happens here (before tool execution or tool result checkpoint)

    responses = [
        LLMResponse(provider="mock", provider_response_id="2", content="Final Answer After Resume", tool_calls=[]),
    ]
    loop, store, _ = _setup_agent(tmp_path, responses, tool, checkpoint_manager=checkpoints)

    result = await loop.resume(run_id)
    assert result == "Final Answer After Resume"
    assert tool.execute_count == 1

    report = RunIntegrityVerifier.verify(cp_path, run_id, idempotency_store=store)
    assert report.valid is True
    assert report.state == RunState.COMPLETED
    assert report.completed_tool_calls == 1


@pytest.mark.asyncio
async def test_tool_side_effect_succeeds_but_checkpoint_fails_resumes_without_duplicate_effect(tmp_path: Any) -> None:
    """Tool side effect persists in idempotency store, but checkpoint fails before TOOL_RESULT_RECEIVED."""
    tool = BaseCountingTool()
    db_path = str(tmp_path / "idempotency.jsonl")
    cp_path = str(tmp_path / "checkpoints.jsonl")
    store = JsonlIdempotencyStore(db_path=db_path)
    checkpoints = CheckpointManager(db_path=cp_path)

    run_id = "run-side-effect-no-dup"
    call = ToolCall(name="test_tool", arguments={"val": 42}, call_id="call_side_effect", run_id=run_id)

    # Step 1: Tool executed and completed in idempotency store
    registry = ToolRegistry()
    registry.register_tool(tool)
    retry_manager = RetryManager(default_policy=RetryPolicy(max_attempts=2, base_delay=0.01))
    executor = ToolExecutor(registry, store, retry_manager, checkpoints, {})

    # Execute tool directly to complete idempotency record
    res = await executor.execute(call)
    assert res.status == ToolStatus.SUCCESS
    assert tool.execute_count == 1

    # Step 2: Simulate crash state in checkpoint (only LLM_RESPONDED exists, TOOL_RESULT_RECEIVED was lost/crashed)
    cp_crash_path = str(tmp_path / "checkpoints_resumed.jsonl")
    cp_resumed = CheckpointManager(db_path=cp_crash_path)
    cp_resumed.log_run_started(run_id, "sys", "usr")
    cp_resumed.log_llm_requested(run_id, iteration=1)
    cp_resumed.log_llm_responded(
        run_id,
        iteration=1,
        content=None,
        num_tool_calls=1,
        tool_calls=[{"call_id": "call_side_effect", "name": "test_tool", "arguments": {"val": 42}}],
    )

    # Step 3: Resume on new agent instance sharing the idempotency store
    responses = [
        LLMResponse(provider="mock", provider_response_id="2", content="Final Answer Replayed", tool_calls=[]),
    ]
    loop2, _, _ = _setup_agent(
        tmp_path,
        responses,
        tool,
        checkpoint_manager=cp_resumed,
        idempotency_store=store,
    )

    final_result = await loop2.resume(run_id)
    assert final_result == "Final Answer Replayed"
    # Idempotency prevented duplicate side effect: tool.execute_count remains 1!
    assert tool.execute_count == 1


@pytest.mark.asyncio
async def test_crash_after_retry_scheduled_before_next_attempt_resumes_safely(tmp_path: Any) -> None:
    """Crash after RETRY_SCHEDULED; resume reconstructs pending tool without double-charging budget."""
    class FlakyFailOnceTool:
        def __init__(self) -> None:
            self.name = "flaky_tool"
            self.description = "flaky tool"
            self.attempts = 0

        def get_schema(self) -> Dict[str, Any]:
            return {"type": "object", "properties": {}}

        async def execute(self, call: ToolCall, context: Dict[str, Any]) -> ToolResult:
            self.attempts += 1
            if self.attempts == 1:
                raise AgentException(message="503 Service Unavailable", code="HTTP_503", retryable=True)
            return ToolResult(call_id=call.call_id, run_id=call.run_id, tool_name=call.name, status=ToolStatus.SUCCESS, data={"status": "recovered"})

    flaky = FlakyFailOnceTool()
    cp_path = str(tmp_path / "checkpoints.jsonl")
    checkpoints = CheckpointManager(db_path=cp_path)

    run_id = "run-crash-retry"
    checkpoints.log_run_started(run_id, "sys", "usr")
    checkpoints.log_llm_requested(run_id, iteration=1)
    checkpoints.log_llm_responded(
        run_id,
        iteration=1,
        content=None,
        num_tool_calls=1,
        tool_calls=[{"call_id": "c_flaky", "name": "flaky_tool", "arguments": {}}],
    )
    checkpoints.log_tool_attempt_started(run_id, "c_flaky", attempt=1, tool_name="flaky_tool")
    checkpoints.log_retry_scheduled(run_id, "TOOL", attempt=1, next_attempt=2, delay_seconds=0.01, reason="HTTP_503", failure_domain="NETWORK", call_id="c_flaky")
    # Crash occurs right after RETRY_SCHEDULED before attempt 2 executes

    policy = RunPolicy(max_iterations=5, max_tool_calls=1, timeout_seconds=10)
    responses = [
        LLMResponse(provider="mock", provider_response_id="2", content="Recovered Answer", tool_calls=[]),
    ]
    loop, _, _ = _setup_agent(tmp_path, responses, flaky, policy=policy, checkpoint_manager=checkpoints)

    result = await loop.resume(run_id)
    assert result == "Recovered Answer"
    # Logical tool call used == 1
    from src.agent.replay_engine import ReplayEngine
    events = ReplayEngine.load_events_for_run(checkpoints.db_path, run_id)
    usage = RunBudgetEngine.reconstruct_usage(events)
    assert usage.tool_calls_used == 1


# ============================================================================
# M5.3 — Cancellation Race Verification
# ============================================================================

@pytest.mark.asyncio
async def test_cancellation_vs_next_llm_iteration(tmp_path: Any) -> None:
    """Cancellation arriving before next LLM iteration blocks new LLM request immediately."""
    tool = BaseCountingTool()
    responses = [
        LLMResponse(provider="mock", provider_response_id="1", content=None, tool_calls=[ProviderToolCall("c1", "test_tool", {"val": 1})]),
        LLMResponse(provider="mock", provider_response_id="2", content="Should Not Run", tool_calls=[]),
    ]
    policy = RunPolicy(max_iterations=5, max_tool_calls=5, timeout_seconds=10)
    loop, _, checkpoints = _setup_agent(tmp_path, responses, tool, policy=policy)

    run_id = "run-cancel-iter"
    # Pre-cancel before starting run
    loop.cancellation_controller.cancel(run_id, reason="User Cancelled")

    result = await loop.run(run_id, "sys", "usr")
    assert result is None
    assert tool.execute_count == 0


@pytest.mark.asyncio
async def test_cancellation_vs_pending_tool_execution_on_resume(tmp_path: Any) -> None:
    """Cancellation arriving before pending tool batch in resume blocks all pending tool calls."""
    tool = BaseCountingTool()
    cp_path = str(tmp_path / "checkpoints.jsonl")
    checkpoints = CheckpointManager(db_path=cp_path)

    run_id = "run-cancel-pending"
    checkpoints.log_run_started(run_id, "sys", "usr")
    checkpoints.log_llm_requested(run_id, iteration=1)
    checkpoints.log_llm_responded(
        run_id,
        iteration=1,
        content=None,
        num_tool_calls=1,
        tool_calls=[{"call_id": "c_pending", "name": "test_tool", "arguments": {"val": 99}}],
    )

    loop, _, _ = _setup_agent(tmp_path, [], tool, checkpoint_manager=checkpoints)
    # Cancel run before resume
    loop.cancellation_controller.cancel(run_id, reason="Cancelled Before Resume")

    with pytest.raises(RecoveryStateError, match="Cannot resume run .* in terminal state HALTED"):
        await loop.resume(run_id)

    assert tool.execute_count == 0  # Pending tool was NEVER executed


@pytest.mark.asyncio
async def test_concurrent_repeated_cancellations_are_idempotent(tmp_path: Any) -> None:
    """Concurrent repeated cancel calls are idempotent and result in exactly one durable write."""
    cp_path = str(tmp_path / "checkpoints.jsonl")
    checkpoints = CheckpointManager(db_path=cp_path)
    controller = RunCancellationController(checkpoints)

    run_id = "run-concurrent-cancels"
    checkpoints.log_run_started(run_id, "sys", "usr")

    async def _cancel_worker(idx: int) -> None:
        controller.cancel(run_id, reason=f"Cancel from worker {idx}")

    tasks = [asyncio.create_task(_cancel_worker(i)) for i in range(10)]
    await asyncio.gather(*tasks)

    token = controller.get_token(run_id)
    assert token.is_cancelled is True

    # Exactly 1 RUN_HALTED event in durable checkpoints
    from src.agent.replay_engine import ReplayEngine
    events = ReplayEngine.load_events_for_run(checkpoints.db_path, run_id)
    halted_events = [e for e in events if e.event_type == CheckpointEventType.RUN_HALTED]
    assert len(halted_events) == 1


@pytest.mark.asyncio
async def test_cancellation_checkpoint_write_failure_does_not_falsely_advance_memory_state(tmp_path: Any) -> None:
    """If checkpoint write fails during cancellation, memory token remains uncancelled."""
    cp_path = str(tmp_path / "checkpoints.jsonl")
    faulty_cp = FaultyCheckpointManager(db_path=cp_path, fail_on_event_types={CheckpointEventType.RUN_HALTED})
    controller = RunCancellationController(faulty_cp)

    run_id = "run-cancel-write-fail"
    token = controller.get_token(run_id)

    with pytest.raises(OSError, match="Simulated checkpoint write failure"):
        controller.cancel(run_id, reason="Should Fail Closed")

    # In-memory token must NOT be marked cancelled
    assert token.is_cancelled is False


@pytest.mark.asyncio
async def test_durable_cancellation_blocks_all_future_resumes(tmp_path: Any) -> None:
    """Once a run is halted/cancelled in durable checkpoint, resume fails closed."""
    tool = BaseCountingTool()
    cp_path = str(tmp_path / "checkpoints.jsonl")
    checkpoints = CheckpointManager(db_path=cp_path)

    run_id = "run-durable-cancelled"
    checkpoints.log_run_started(run_id, "sys", "usr")
    checkpoints.log_run_halted(run_id, reason="CANCEL: User Abort")

    loop, _, _ = _setup_agent(tmp_path, [], tool, checkpoint_manager=checkpoints)

    with pytest.raises(RecoveryStateError, match="Cannot resume run .* in terminal state HALTED"):
        await loop.resume(run_id)

    assert tool.execute_count == 0


# ============================================================================
# M5.5 — Budget × Retry × Resume Interaction Matrix
# ============================================================================

@pytest.mark.asyncio
async def test_budget_interaction_max_tool_calls_1_with_retry_and_crash_resume(tmp_path: Any) -> None:
    """Policy max_tool_calls=1 with retried attempts across crash/resume counts as 1 logical tool call."""
    tool = BaseCountingTool()
    cp_path = str(tmp_path / "checkpoints.jsonl")
    checkpoints = CheckpointManager(db_path=cp_path)

    run_id = "run-budget-retry-matrix"
    checkpoints.log_run_started(run_id, "sys", "usr")
    checkpoints.log_llm_requested(run_id, iteration=1)
    checkpoints.log_llm_responded(
        run_id,
        iteration=1,
        content=None,
        num_tool_calls=1,
        tool_calls=[{"call_id": "c1", "name": "test_tool", "arguments": {"val": 1}}],
    )
    # Attempt 1 started and ended with failure before crash
    checkpoints.log_tool_attempt_started(run_id, "c1", attempt=1, tool_name="test_tool")
    checkpoints.log_tool_attempt_ended(run_id, "c1", attempt=1, status="FAILURE", error_msg="503")
    checkpoints.log_retry_scheduled(run_id, "TOOL", attempt=1, next_attempt=2, delay_seconds=0.01, reason="503", failure_domain="NETWORK", call_id="c1")

    # Policy permits exactly 1 tool call
    policy = RunPolicy(max_iterations=5, max_tool_calls=1, timeout_seconds=10)
    responses = [
        LLMResponse(provider="mock", provider_response_id="2", content="Final Answer Matrix", tool_calls=[]),
    ]
    loop, _, _ = _setup_agent(tmp_path, responses, tool, policy=policy, checkpoint_manager=checkpoints)

    result = await loop.resume(run_id)
    assert result == "Final Answer Matrix"
    assert tool.execute_count == 1

    from src.agent.replay_engine import ReplayEngine
    events = ReplayEngine.load_events_for_run(checkpoints.db_path, run_id)
    usage = RunBudgetEngine.reconstruct_usage(events)
    assert usage.tool_calls_used == 1


@pytest.mark.asyncio
async def test_consumed_iteration_budget_persists_through_crash_resume(tmp_path: Any) -> None:
    """Policy max_iterations=2 already consumed before crash; resume halts immediately."""
    tool = BaseCountingTool()
    cp_path = str(tmp_path / "checkpoints.jsonl")
    checkpoints = CheckpointManager(db_path=cp_path)

    run_id = "run-iter-persist"
    checkpoints.log_run_started(run_id, "sys", "usr")
    checkpoints.log_llm_requested(run_id, iteration=1)
    checkpoints.log_llm_responded(run_id, iteration=1, content=None, num_tool_calls=1, tool_calls=[{"call_id": "c1", "name": "test_tool", "arguments": {}}])
    checkpoints.log_tool_result_received(run_id, "c1", "success", tool_name="test_tool", result={"status": "success"})
    checkpoints.log_llm_requested(run_id, iteration=2)
    checkpoints.log_llm_responded(run_id, iteration=2, content=None, num_tool_calls=1, tool_calls=[{"call_id": "c2", "name": "test_tool", "arguments": {}}])
    checkpoints.log_tool_result_received(run_id, "c2", "success", tool_name="test_tool", result={"status": "success"})

    policy = RunPolicy(max_iterations=2, max_tool_calls=10, timeout_seconds=10)
    loop, _, _ = _setup_agent(tmp_path, [], tool, policy=policy, checkpoint_manager=checkpoints)

    result = await loop.resume(run_id)
    assert result is None
    from src.agent.replay_engine import ReplayEngine
    events = ReplayEngine.load_events_for_run(checkpoints.db_path, run_id)
    assert any(e.event_type == CheckpointEventType.RUN_HALTED and e.payload.get("reason") == "MAX_ITERATIONS_REACHED" for e in events)


# ============================================================================
# M5.6 — Corruption & Persistence Fail-Closed Matrix
# ============================================================================

@pytest.mark.asyncio
async def test_malformed_checkpoint_json_fails_closed_without_modification(tmp_path: Any) -> None:
    """Malformed checkpoint JSON line raises RecoveryStateError (CORRUPT) and does not modify the file."""
    cp_path = str(tmp_path / "checkpoints.jsonl")
    with open(cp_path, "w", encoding="utf-8") as f:
        f.write('{"run_id": "run-corrupt", "sequence_id": 1, "timestamp": 100.0, "event_type": "RUN_STARTED", "payload": {}}\n')
        f.write('INVALID JSON LINE CORRUPTED DATA\n')

    tool = BaseCountingTool()
    loop, _, _ = _setup_agent(tmp_path, [], tool, checkpoint_manager=CheckpointManager(db_path=cp_path))

    with pytest.raises(RecoveryStateError, match="corrupted"):
        await loop.resume("run-corrupt")

    # Verify file content is unchanged
    with open(cp_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    assert len(lines) == 2
    assert "INVALID JSON LINE" in lines[1]


@pytest.mark.asyncio
async def test_application_raw_oserror_not_falsely_promoted_to_checkpoint_system_error(tmp_path: Any) -> None:
    """Application/tool raw OSError is treated as tool failure, NOT falsely promoted to SystemStateError."""
    class FileToolRaisingOSError:
        def __init__(self) -> None:
            self.name = "file_tool"
            self.description = "tool raising file not found"

        def get_schema(self) -> Dict[str, Any]:
            return {"type": "object", "properties": {}}

        async def execute(self, call: ToolCall, context: Dict[str, Any]) -> ToolResult:
            raise FileNotFoundError("User file /path/to/missing.txt does not exist")

    tool = FileToolRaisingOSError()
    db_path = str(tmp_path / "idempotency.jsonl")
    cp_path = str(tmp_path / "checkpoints.jsonl")
    store = JsonlIdempotencyStore(db_path=db_path)
    checkpoints = CheckpointManager(db_path=cp_path)

    registry = ToolRegistry()
    registry.register_tool(tool)
    retry_manager = RetryManager(default_policy=RetryPolicy(max_attempts=1))
    executor = ToolExecutor(registry, store, retry_manager, checkpoints, {})

    call = ToolCall(name="file_tool", arguments={}, call_id="call_os_err", run_id="run_os_err")
    result = await executor.execute(call)

    # Must return ToolResult with FAILURE, not raise SystemStateError
    assert result.status == ToolStatus.FAILURE
    assert result.error is not None
    assert "missing.txt" in result.error.message


@pytest.mark.asyncio
async def test_terminal_state_immutability_enforced_against_new_events(tmp_path: Any) -> None:
    """Once a run enters a terminal state, appending new events raises CheckpointStateError."""
    cp_path = str(tmp_path / "checkpoints.jsonl")
    cm = CheckpointManager(db_path=cp_path)
    run_id = "run-terminal-immutability"

    cm.log_run_started(run_id, "sys", "usr")
    cm.log_llm_requested(run_id, iteration=1)
    cm.log_llm_responded(run_id, iteration=1, content="All Done", num_tool_calls=0)
    cm.log_run_completed(run_id)

    # Attempting to log a new LLM request or tool call on a completed run must raise CheckpointStateError
    with pytest.raises(CheckpointStateError):
        cm.log_llm_requested(run_id, iteration=2)

    with pytest.raises(CheckpointStateError):
        cm.log_tool_call_created(run_id, "c_extra", "tool", {})


@pytest.mark.asyncio
async def test_cancellation_after_retryable_failure_before_retry_continuation_stops_attempt_n_plus_one(tmp_path: Any) -> None:
    """
    Cancellation arrives while tool is in retry backoff before attempt N+1.
    Continuation guard stops retry; attempt N+1 never executes.
    """
    class FailOnceTool:
        def __init__(self) -> None:
            self.name = "cancel_during_retry_tool"
            self.description = "tool failing on attempt 1"
            self.attempts = 0

        def get_schema(self) -> Dict[str, Any]:
            return {"type": "object", "properties": {}}

        async def execute(self, call: ToolCall, context: Dict[str, Any]) -> ToolResult:
            self.attempts += 1
            if self.attempts == 1:
                raise AgentException(message="503 Service Unavailable", code="HTTP_503", retryable=True)
            return ToolResult(call_id=call.call_id, run_id=call.run_id, tool_name=call.name, status=ToolStatus.SUCCESS, data={"attempts": self.attempts})

    db_path = str(tmp_path / "idempotency.jsonl")
    cp_path = str(tmp_path / "checkpoints.jsonl")
    store = JsonlIdempotencyStore(db_path=db_path)
    checkpoints = CheckpointManager(db_path=cp_path)
    controller = RunCancellationController(checkpoints)

    run_id = "run-cancel-during-retry"
    checkpoints.log_run_started(run_id, "sys", "usr")

    tool = FailOnceTool()
    registry = ToolRegistry()
    registry.register_tool(tool)

    class CancellingRetryManager(RetryManager):
        async def execute_with_retry(self, operation: Any, *args: Any, **kwargs: Any) -> Any:
            orig_on_retry = kwargs.get("on_retry_scheduled")
            def hook_on_retry(att: int, next_att: int, delay: float, reason: str, domain: str) -> None:
                if orig_on_retry:
                    orig_on_retry(att, next_att, delay, reason, domain)
                # Durably cancel the run immediately after retry is scheduled
                controller.cancel(run_id, reason="Cancelled Before Attempt 2")

            kwargs["on_retry_scheduled"] = hook_on_retry
            return await super().execute_with_retry(operation, *args, **kwargs)

    retry_manager = CancellingRetryManager(default_policy=RetryPolicy(max_attempts=3, base_delay=0.01, jitter=False))
    executor = ToolExecutor(registry, store, retry_manager, checkpoints, {})

    call = ToolCall(name="cancel_during_retry_tool", arguments={}, call_id="c_cancel_retry", run_id=run_id)

    result = await executor.execute(call)

    # Invariant: Attempt 2 NEVER executes because cancellation won before attempt 2
    assert tool.attempts == 1
    assert result.status == ToolStatus.FAILURE


@pytest.mark.asyncio
async def test_terminal_state_before_retry_continuation_stops_attempt_n_plus_one(tmp_path: Any) -> None:
    """
    Run is marked terminal (HALTED/FAILED/COMPLETED) before scheduled retry continuation.
    Continuation guard stops retry; attempt N+1 never executes.
    """
    class FailOnceTool:
        def __init__(self) -> None:
            self.name = "term_during_retry_tool"
            self.description = "tool failing on attempt 1"
            self.attempts = 0

        def get_schema(self) -> Dict[str, Any]:
            return {"type": "object", "properties": {}}

        async def execute(self, call: ToolCall, context: Dict[str, Any]) -> ToolResult:
            self.attempts += 1
            if self.attempts == 1:
                raise AgentException(message="503 Service Unavailable", code="HTTP_503", retryable=True)
            return ToolResult(call_id=call.call_id, run_id=call.run_id, tool_name=call.name, status=ToolStatus.SUCCESS)

    db_path = str(tmp_path / "idempotency.jsonl")
    cp_path = str(tmp_path / "checkpoints.jsonl")
    store = JsonlIdempotencyStore(db_path=db_path)
    checkpoints = CheckpointManager(db_path=cp_path)

    run_id = "run-term-during-retry"
    checkpoints.log_run_started(run_id, "sys", "usr")

    tool = FailOnceTool()
    registry = ToolRegistry()
    registry.register_tool(tool)

    class TerminatingRetryManager(RetryManager):
        async def execute_with_retry(self, operation: Any, *args: Any, **kwargs: Any) -> Any:
            orig_on_retry = kwargs.get("on_retry_scheduled")
            def hook_on_retry(att: int, next_att: int, delay: float, reason: str, domain: str) -> None:
                if orig_on_retry:
                    orig_on_retry(att, next_att, delay, reason, domain)
                # Durably halt the run immediately after retry is scheduled
                checkpoints.log_run_halted(run_id, reason="RUN_HALTED_EXTERNALLY")

            kwargs["on_retry_scheduled"] = hook_on_retry
            return await super().execute_with_retry(operation, *args, **kwargs)

    retry_manager = TerminatingRetryManager(default_policy=RetryPolicy(max_attempts=3, base_delay=0.01, jitter=False))
    executor = ToolExecutor(registry, store, retry_manager, checkpoints, {})

    call = ToolCall(name="term_during_retry_tool", arguments={}, call_id="c_term_retry", run_id=run_id)

    result = await executor.execute(call)

    # Attempt 2 never executes
    assert tool.attempts == 1
    assert result.status == ToolStatus.FAILURE


@pytest.mark.asyncio
async def test_retry_continuation_inspection_error_fails_closed_without_next_attempt(tmp_path: Any) -> None:
    """
    If durable state inspection fails (e.g. corrupted checkpoint) before retry continuation,
    the continuation guard FAILS CLOSED, raising SystemStateError, and attempt N+1 never executes.
    """
    class FlakyFailOnceTool:
        def __init__(self) -> None:
            self.name = "flaky_corrupt_tool"
            self.description = "flaky tool"
            self.attempts = 0

        def get_schema(self) -> Dict[str, Any]:
            return {"type": "object", "properties": {}}

        async def execute(self, call: ToolCall, context: Dict[str, Any]) -> ToolResult:
            self.attempts += 1
            if self.attempts == 1:
                raise AgentException(message="503 Service Unavailable", code="HTTP_503", retryable=True)
            return ToolResult(call_id=call.call_id, run_id=call.run_id, tool_name=call.name, status=ToolStatus.SUCCESS)

    db_path = str(tmp_path / "idempotency.jsonl")
    cp_path = str(tmp_path / "checkpoints.jsonl")
    store = JsonlIdempotencyStore(db_path=db_path)
    checkpoints = CheckpointManager(db_path=cp_path)

    run_id = "run-corrupt-during-retry"
    checkpoints.log_run_started(run_id, "sys", "usr")

    tool = FlakyFailOnceTool()
    registry = ToolRegistry()
    registry.register_tool(tool)

    class CorruptingRetryManager(RetryManager):
        async def execute_with_retry(self, operation: Any, *args: Any, **kwargs: Any) -> Any:
            orig_on_retry = kwargs.get("on_retry_scheduled")
            def hook_on_retry(att: int, next_att: int, delay: float, reason: str, domain: str) -> None:
                if orig_on_retry:
                    orig_on_retry(att, next_att, delay, reason, domain)
                # Corrupt the checkpoint file right after retry is scheduled
                with open(cp_path, "a", encoding="utf-8") as f:
                    f.write("MALFORMED JSON CORRUPTION DATA\n")

            kwargs["on_retry_scheduled"] = hook_on_retry
            return await super().execute_with_retry(operation, *args, **kwargs)

    retry_manager = CorruptingRetryManager(default_policy=RetryPolicy(max_attempts=3, base_delay=0.01, jitter=False))
    executor = ToolExecutor(registry, store, retry_manager, checkpoints, {})

    call = ToolCall(name="flaky_corrupt_tool", arguments={}, call_id="c_corrupt_retry", run_id=run_id)

    with pytest.raises(SystemStateError, match="Failed to verify run state before retry continuation"):
        await executor.execute(call)

    # Invariant: Attempt 2 NEVER executed because continuation guard failed closed
    assert tool.attempts == 1


@pytest.mark.asyncio
async def test_invalid_checkpoint_transition_sequence_fails_closed(tmp_path: Any) -> None:
    """Illegal checkpoint state transition raises CheckpointStateError and fails closed."""
    from src.core.checkpoint_contract import validate_state_transition, CheckpointEvent
    run_id = "run-illegal-transition"

    # Attempt to process TOOL_RESULT_RECEIVED while in PENDING state
    event = CheckpointEvent(
        run_id=run_id,
        sequence_id=1,
        timestamp=100.0,
        event_type=CheckpointEventType.TOOL_RESULT_RECEIVED,
        payload={"call_id": "c1", "status": "success"},
    )
    with pytest.raises(CheckpointStateError):
        validate_state_transition(RunState.PENDING, event)


@pytest.mark.asyncio
async def test_explicit_persistence_boundary_failure_is_classified_as_system_state_error(tmp_path: Any) -> None:
    """Storage / persistence failure during completion raises SystemStateError."""
    class FaultyCompletionStore(JsonlIdempotencyStore):
        def complete(self, key: RecordKey, owner_id: str, *, data: Optional[Dict[str, Any]] = None) -> Any:
            raise OSError("Disk write failed during idempotency completion")

    db_path = str(tmp_path / "idempotency.jsonl")
    cp_path = str(tmp_path / "checkpoints.jsonl")
    store = FaultyCompletionStore(db_path=db_path)
    checkpoints = CheckpointManager(db_path=cp_path)
    tool = BaseCountingTool()

    registry = ToolRegistry()
    registry.register_tool(tool)
    retry_manager = RetryManager(default_policy=RetryPolicy(max_attempts=1))
    executor = ToolExecutor(registry, store, retry_manager, checkpoints, {})

    call = ToolCall(name="test_tool", arguments={}, call_id="c_persist_fail", run_id="run_persist_fail")
    with pytest.raises(SystemStateError, match="Idempotency completion persistence failed"):
        await executor.execute(call)

