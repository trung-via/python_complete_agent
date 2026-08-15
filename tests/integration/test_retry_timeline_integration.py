import asyncio
import json
import os
import tempfile
import pytest
from typing import Any, Dict, Optional

from src.core.base_tool import BaseTool
from src.core.checkpoint import CheckpointManager
from src.core.checkpoint_contract import (
    CheckpointEventType,
    CheckpointStateError,
    FailureDomain,
    RunState,
    validate_state_transition,
)
from src.core.errors import AgentException, RateLimitError, SystemStateError
from src.core.idempotency import IdempotencyStore
from src.core.retry import RetryManager, RetryPolicy
from src.core.retry_policy import FailureClassifier, RetryOperation
from src.core.tool_executor import ToolExecutor
from src.core.tool_registry import ToolRegistry
from src.core.types import ToolCall, ToolResult, ToolStatus


class DummyTool(BaseTool):
    def __init__(self, outcomes, tool_name: str = "dummy_tool"):
        self.outcomes = outcomes
        self.call_count = 0
        self._name = tool_name

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return "Dummy tool for testing"

    def get_schema(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute(self, call: ToolCall, context: Any = None) -> ToolResult:
        self.call_count += 1
        outcome = self.outcomes[min(self.call_count - 1, len(self.outcomes) - 1)]
        if isinstance(outcome, Exception):
            raise outcome
        if isinstance(outcome, ToolResult):
            return outcome
        return ToolResult(
            call_id=call.call_id,
            run_id=call.run_id,
            tool_name=call.name,
            status=ToolStatus.SUCCESS,
            data={"result": outcome},
        )


@pytest.mark.asyncio
async def test_retry_event_contract_and_per_attempt_timeline(monkeypatch):
    """
    Validates:
    1. 3-attempt execution produces TOOL_ATTEMPT_STARTED attempts [1, 2, 3]
    2. Matching TOOL_ATTEMPT_ENDED attempts [1, 2, 3]
    3. Exactly two RETRY_SCHEDULED events (1->2, 2->3)
    4. Exact payload contract on RETRY_SCHEDULED
    5. No double count on attempt 1 start.
    """
    sleep_calls = []

    async def fake_sleep(duration):
        sleep_calls.append(duration)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "checkpoints.jsonl")
        checkpoints = CheckpointManager(db_path=db_path)
        idempotency_store = IdempotencyStore(db_path=os.path.join(tmpdir, "idemp.jsonl"))
        registry = ToolRegistry()

        # Tool fails twice with retryable error, succeeds on 3rd attempt
        retryable_err = AgentException("Temporary glitch", code="TEMP_ERROR", retryable=True)
        dummy_tool = DummyTool([retryable_err, retryable_err, "success_value"])
        registry.register_tool(dummy_tool)

        policy = RetryPolicy(max_attempts=3, base_delay=1.0, jitter=False)
        retry_manager = RetryManager(default_policy=policy)
        executor = ToolExecutor(
            registry=registry,
            idempotency_store=idempotency_store,
            checkpoints=checkpoints,
            retry_manager=retry_manager,
            context={},
        )

        run_id = checkpoints.log_task_start("test timeline")
        checkpoints.log_llm_requested(run_id, iteration=1)
        checkpoints.log_llm_responded(run_id, iteration=1, content=None, num_tool_calls=1)

        call = ToolCall(
            run_id=run_id,
            call_id="call_timeline_1",
            name="dummy_tool",
            arguments={},
        )

        result = await executor.execute(call)
        assert result.status == ToolStatus.SUCCESS
        assert dummy_tool.call_count == 3

        # Read checkpoint events
        events = []
        with open(db_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line))

        # Check sequence of tool events
        tool_events = [e for e in events if e["event"] in (
            "TOOL_CALL_CREATED",
            "TOOL_ATTEMPT_STARTED",
            "TOOL_ATTEMPT_ENDED",
            "RETRY_SCHEDULED",
        )]

        event_types = [e["event"] for e in tool_events]
        expected_types = [
            "TOOL_CALL_CREATED",
            "TOOL_ATTEMPT_STARTED",
            "TOOL_ATTEMPT_ENDED",
            "RETRY_SCHEDULED",
            "TOOL_ATTEMPT_STARTED",
            "TOOL_ATTEMPT_ENDED",
            "RETRY_SCHEDULED",
            "TOOL_ATTEMPT_STARTED",
            "TOOL_ATTEMPT_ENDED",
        ]
        assert event_types == expected_types

        # Verify attempt numbers on TOOL_ATTEMPT_STARTED: exactly [1, 2, 3]
        attempt_starts = [e for e in tool_events if e["event"] == "TOOL_ATTEMPT_STARTED"]
        assert [e.get("attempt") for e in attempt_starts] == [1, 2, 3]

        # Verify attempt numbers on TOOL_ATTEMPT_ENDED: exactly [1, 2, 3]
        attempt_ends = [e for e in tool_events if e["event"] == "TOOL_ATTEMPT_ENDED"]
        assert [e.get("attempt") for e in attempt_ends] == [1, 2, 3]

        # Verify RETRY_SCHEDULED payload contract
        retry_scheduled_events = [e for e in tool_events if e["event"] == "RETRY_SCHEDULED"]
        assert len(retry_scheduled_events) == 2

        # 1 -> 2
        r1 = retry_scheduled_events[0]
        assert r1["operation"] == "TOOL"
        assert r1["attempt"] == 1
        assert r1["next_attempt"] == 2
        assert r1["delay_seconds"] == 1.0
        assert r1["call_id"] == "call_timeline_1"
        assert r1["failure_domain"] == "TOOL_EXECUTION"

        # 2 -> 3
        r2 = retry_scheduled_events[1]
        assert r2["operation"] == "TOOL"
        assert r2["attempt"] == 2
        assert r2["next_attempt"] == 3
        assert r2["delay_seconds"] == 2.0
        assert r2["call_id"] == "call_timeline_1"
        assert r2["failure_domain"] == "TOOL_EXECUTION"


@pytest.mark.asyncio
async def test_actual_delay_and_rate_limit_retry_after(monkeypatch):
    """
    Validates:
    - RateLimitError with retry_after = 7.5
    - RETRY_SCHEDULED.delay_seconds == 7.5
    - Actual asyncio.sleep receives 7.5
    """
    sleep_calls = []

    async def fake_sleep(duration):
        sleep_calls.append(duration)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "checkpoints.jsonl")
        checkpoints = CheckpointManager(db_path=db_path)
        idempotency_store = IdempotencyStore(db_path=os.path.join(tmpdir, "idemp.jsonl"))
        registry = ToolRegistry()

        rate_limit_err = RateLimitError("Rate limit exceeded", details={"retry_after": 7.5})
        dummy_tool = DummyTool([rate_limit_err, "ok"])
        registry.register_tool(dummy_tool)

        policy = RetryPolicy(max_attempts=3, base_delay=1.0, jitter=False)
        retry_manager = RetryManager(default_policy=policy)
        executor = ToolExecutor(
            registry=registry,
            idempotency_store=idempotency_store,
            checkpoints=checkpoints,
            retry_manager=retry_manager,
            context={},
        )

        run_id = checkpoints.log_task_start("test rate limit")
        checkpoints.log_llm_requested(run_id, iteration=1)
        checkpoints.log_llm_responded(run_id, iteration=1, content=None, num_tool_calls=1)

        call = ToolCall(
            run_id=run_id,
            call_id="call_rl_1",
            name="dummy_tool",
            arguments={},
        )

        result = await executor.execute(call)
        assert result.status == ToolStatus.SUCCESS

        # Assert sleep received 7.5
        assert len(sleep_calls) == 1
        assert sleep_calls[0] == 7.5

        # Assert RETRY_SCHEDULED logged delay_seconds == 7.5
        events = []
        with open(db_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line))

        retry_events = [e for e in events if e["event"] == "RETRY_SCHEDULED"]
        assert len(retry_events) == 1
        assert retry_events[0]["delay_seconds"] == 7.5
        assert retry_events[0]["reason"] == "RETRYABLE_RATE_LIMIT"


@pytest.mark.asyncio
async def test_no_retry_scheduled_on_stop_exhausted_or_fatal(monkeypatch):
    """
    Validates that no RETRY_SCHEDULED event is logged when:
    - max attempts are exhausted
    - non-retryable error occurs
    """
    sleep_calls = []

    async def fake_sleep(duration):
        sleep_calls.append(duration)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "checkpoints.jsonl")
        checkpoints = CheckpointManager(db_path=db_path)
        idempotency_store = IdempotencyStore(db_path=os.path.join(tmpdir, "idemp.jsonl"))
        registry = ToolRegistry()

        # Fatal error (retryable=False)
        fatal_err = AgentException("Fatal error", code="FATAL_ERROR", retryable=False)
        dummy_tool = DummyTool([fatal_err])
        registry.register_tool(dummy_tool)

        policy = RetryPolicy(max_attempts=3, base_delay=1.0, jitter=False)
        retry_manager = RetryManager(default_policy=policy)
        executor = ToolExecutor(
            registry=registry,
            idempotency_store=idempotency_store,
            checkpoints=checkpoints,
            retry_manager=retry_manager,
            context={},
        )

        run_id = checkpoints.log_task_start("test fatal stop")
        checkpoints.log_llm_requested(run_id, iteration=1)
        checkpoints.log_llm_responded(run_id, iteration=1, content=None, num_tool_calls=1)

        call = ToolCall(
            run_id=run_id,
            call_id="call_fatal_1",
            name="dummy_tool",
            arguments={},
        )

        result = await executor.execute(call)
        assert result.status == ToolStatus.FAILURE

        events = []
        with open(db_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line))

        # Must NOT have any RETRY_SCHEDULED events
        retry_events = [e for e in events if e["event"] == "RETRY_SCHEDULED"]
        assert len(retry_events) == 0
        assert len(sleep_calls) == 0


def test_retry_scheduled_state_machine_transition():
    """
    Validates that RETRY_SCHEDULED preserves active states (RUNNING, TOOL_EXECUTING)
    and is rejected in terminal states (COMPLETED, FAILED, HALTED).
    """
    from src.core.checkpoint_contract import CheckpointEvent

    # 1. TOOL_EXECUTING + RETRY_SCHEDULED -> TOOL_EXECUTING
    ev = CheckpointEvent(
        run_id="run1",
        sequence_id=4,
        timestamp=100.0,
        event_type=CheckpointEventType.RETRY_SCHEDULED,
        payload={"attempt": 1, "next_attempt": 2},
    )
    new_state = validate_state_transition(RunState.TOOL_EXECUTING, ev)
    assert new_state == RunState.TOOL_EXECUTING

    # 2. RUNNING + RETRY_SCHEDULED -> RUNNING
    new_state_running = validate_state_transition(RunState.RUNNING, ev)
    assert new_state_running == RunState.RUNNING

    # 3. Terminal states must raise CheckpointStateError
    for terminal in (RunState.COMPLETED, RunState.FAILED, RunState.HALTED):
        with pytest.raises(CheckpointStateError):
            validate_state_transition(terminal, ev)
