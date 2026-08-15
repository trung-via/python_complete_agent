from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional
import pytest

from src.agent.integrity_verifier import RunIntegrityVerifier
from src.agent.loop import AgentLoop
from src.agent.policy import RunPolicy
from src.core.checkpoint import CheckpointManager
from src.core.checkpoint_contract import RunState
from src.core.errors import AgentException
from src.core.idempotency_store_v2 import JsonlIdempotencyStore
from src.core.retry import RetryManager, RetryPolicy
from src.core.tool_executor import ToolExecutor
from src.core.tool_registry import ToolRegistry
from src.core.types import ToolCall, ToolResult, ToolStatus
from src.providers.base import LLMResponse, ProviderToolCall
from tests.support.fault_injection import FaultyLLMProvider


class SoakCountingTool:
    """Tool that tracks all invocations for soak tests."""
    def __init__(self, name: str = "test_tool") -> None:
        self.name = name
        self.description = "soak counting test tool"
        self.calls: List[Dict[str, Any]] = []

    def get_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {"round": {"type": "integer"}, "r": {"type": "integer"}}}

    async def execute(self, call: ToolCall, context: Dict[str, Any]) -> ToolResult:
        self.calls.append({"call_id": call.call_id, "args": call.arguments})
        return ToolResult(
            call_id=call.call_id,
            run_id=call.run_id,
            tool_name=call.name,
            status=ToolStatus.SUCCESS,
            data={"count": len(self.calls)},
        )


class SoakFlakyTool:
    """Tool that fails transiently then succeeds."""
    def __init__(self, fail_attempts: int = 1, name: str = "test_tool") -> None:
        self.name = name
        self.description = "soak flaky retry tool"
        self.fail_attempts = fail_attempts
        self.attempts = 0

    def get_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {"round": {"type": "integer"}}}

    async def execute(self, call: ToolCall, context: Dict[str, Any]) -> ToolResult:
        self.attempts += 1
        if self.attempts <= self.fail_attempts:
            raise AgentException(message="503 Service Unavailable", code="HTTP_503", retryable=True)
        return ToolResult(
            call_id=call.call_id,
            run_id=call.run_id,
            tool_name=call.name,
            status=ToolStatus.SUCCESS,
            data={"attempt": self.attempts},
        )


def _setup_soak_agent(
    db_path: str,
    cp_path: str,
    responses: List[LLMResponse],
    tool: Any,
    policy: Optional[RunPolicy] = None,
    retry_policy: Optional[RetryPolicy] = None,
) -> tuple[AgentLoop, ToolExecutor, CheckpointManager, JsonlIdempotencyStore]:
    registry = ToolRegistry()
    registry.register_tool(tool)
    store = JsonlIdempotencyStore(db_path=db_path)
    checkpoints = CheckpointManager(db_path=cp_path)
    retry_mgr = RetryManager(default_policy=retry_policy or RetryPolicy(max_attempts=3, base_delay=0.001, jitter=False))

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
# M6.4 — Bounded Deterministic Soak Verification
# ============================================================================

@pytest.mark.asyncio
async def test_soak_repeated_fresh_run_lifecycle_matrix(tmp_path: Any) -> None:
    """
    Soak round 1..10: Repeated fresh run -> tool execution -> final response.
    Verifies that state is clean across repeated runs sharing stores, no cross-run bleed,
    and integrity verifies 100% valid after each round.
    """
    db_path = str(tmp_path / "idempotency.jsonl")
    cp_path = str(tmp_path / "checkpoints.jsonl")

    num_rounds = 10
    for round_idx in range(1, num_rounds + 1):
        tool = SoakCountingTool()
        run_id = f"soak-fresh-run-{round_idx}"
        responses = [
            LLMResponse(
                provider="mock",
                provider_response_id=f"r1_{round_idx}",
                content=None,
                tool_calls=[ProviderToolCall(f"c_fresh_{round_idx}", "test_tool", {"round": round_idx})],
            ),
            LLMResponse(
                provider="mock",
                provider_response_id=f"r2_{round_idx}",
                content=f"Answer {round_idx}",
                tool_calls=[],
            ),
        ]
        loop, _, _, store = _setup_soak_agent(db_path, cp_path, responses, tool)

        result = await loop.run(run_id, "sys", f"usr_{round_idx}")
        assert result == f"Answer {round_idx}"
        assert len(tool.calls) == 1

        # Audit integrity
        report = RunIntegrityVerifier.verify(cp_path, run_id, idempotency_store=store)
        assert report.valid is True
        assert report.state == RunState.COMPLETED
        assert len(report.issues) == 0


@pytest.mark.asyncio
async def test_soak_repeated_crash_resume_lifecycle_matrix(tmp_path: Any) -> None:
    """
    Soak round 1..5: Interrupted run with pending tool resumed to completion.
    Verifies state recovery without duplicate side effect across multiple crash cycles.
    """
    db_path = str(tmp_path / "idempotency.jsonl")
    cp_path = str(tmp_path / "checkpoints.jsonl")

    num_rounds = 5
    for round_idx in range(1, num_rounds + 1):
        tool = SoakCountingTool()
        run_id = f"soak-resume-run-{round_idx}"
        cm = CheckpointManager(db_path=cp_path)
        # Pre-seed crash state
        cm.log_run_started(run_id, "sys", "usr")
        cm.log_llm_requested(run_id, iteration=1)
        cm.log_llm_responded(
            run_id,
            iteration=1,
            content=None,
            num_tool_calls=1,
            tool_calls=[{"call_id": f"c_res_{round_idx}", "name": "test_tool", "arguments": {"r": round_idx}}],
        )

        responses = [
            LLMResponse(
                provider="mock",
                provider_response_id=f"resp_res_{round_idx}",
                content=f"Resumed Answer {round_idx}",
                tool_calls=[],
            ),
        ]
        loop, _, _, store = _setup_soak_agent(db_path, cp_path, responses, tool)

        result = await loop.resume(run_id)
        assert result == f"Resumed Answer {round_idx}"
        assert len(tool.calls) == 1

        report = RunIntegrityVerifier.verify(cp_path, run_id, idempotency_store=store)
        assert report.valid is True
        assert report.state == RunState.COMPLETED


@pytest.mark.asyncio
async def test_soak_repeated_retry_success_lifecycle_matrix(tmp_path: Any) -> None:
    """
    Soak round 1..5: Tool fails transiently on attempt 1, succeeds on attempt 2.
    Verifies retry accounting and timeline checkpoints across repeated cycles.
    """
    db_path = str(tmp_path / "idempotency.jsonl")
    cp_path = str(tmp_path / "checkpoints.jsonl")

    num_rounds = 5
    for round_idx in range(1, num_rounds + 1):
        tool = SoakFlakyTool(fail_attempts=1)
        run_id = f"soak-retry-run-{round_idx}"
        responses = [
            LLMResponse(
                provider="mock",
                provider_response_id=f"r1_{round_idx}",
                content=None,
                tool_calls=[ProviderToolCall(f"c_retry_{round_idx}", "test_tool", {"round": round_idx})],
            ),
            LLMResponse(
                provider="mock",
                provider_response_id=f"r2_{round_idx}",
                content=f"Retry Succeeded {round_idx}",
                tool_calls=[],
            ),
        ]
        loop, _, _, store = _setup_soak_agent(db_path, cp_path, responses, tool)

        result = await loop.run(run_id, "sys", f"usr_{round_idx}")
        assert result == f"Retry Succeeded {round_idx}"
        assert tool.attempts == 2

        report = RunIntegrityVerifier.verify(cp_path, run_id, idempotency_store=store)
        assert report.valid is True
        assert report.state == RunState.COMPLETED


@pytest.mark.asyncio
async def test_soak_repeated_budget_exhaustion_matrix(tmp_path: Any) -> None:
    """
    Soak round 1..5: Repeated runs hitting max_iterations limit.
    Verifies deterministic HALTED state and budget consistency across rounds.
    """
    db_path = str(tmp_path / "idempotency.jsonl")
    cp_path = str(tmp_path / "checkpoints.jsonl")

    num_rounds = 5
    for round_idx in range(1, num_rounds + 1):
        tool = SoakCountingTool()
        run_id = f"soak-budget-run-{round_idx}"
        # Infinite tool loop responses
        responses = [
            LLMResponse(provider="mock", provider_response_id="1", content=None, tool_calls=[ProviderToolCall(f"c1_{round_idx}", "test_tool", {})]),
            LLMResponse(provider="mock", provider_response_id="2", content=None, tool_calls=[ProviderToolCall(f"c2_{round_idx}", "test_tool", {})]),
            LLMResponse(provider="mock", provider_response_id="3", content=None, tool_calls=[ProviderToolCall(f"c3_{round_idx}", "test_tool", {})]),
        ]
        policy = RunPolicy(max_iterations=2, max_tool_calls=10, timeout_seconds=10)
        loop, _, _, store = _setup_soak_agent(db_path, cp_path, responses, tool, policy=policy)

        result = await loop.run(run_id, "sys", "usr")
        assert result is None

        report = RunIntegrityVerifier.verify(cp_path, run_id, idempotency_store=store)
        assert report.valid is True
        assert report.state == RunState.HALTED


@pytest.mark.asyncio
async def test_soak_repeated_cancellation_lifecycle_matrix(tmp_path: Any) -> None:
    """
    Soak round 1..5: Runs cancelled before execution.
    Verifies that cancellation consistently blocks all tool side effects and maintains valid state.
    """
    db_path = str(tmp_path / "idempotency.jsonl")
    cp_path = str(tmp_path / "checkpoints.jsonl")

    num_rounds = 5
    for round_idx in range(1, num_rounds + 1):
        tool = SoakCountingTool()
        run_id = f"soak-cancel-run-{round_idx}"
        responses = [
            LLMResponse(provider="mock", provider_response_id="1", content=None, tool_calls=[ProviderToolCall(f"c_can_{round_idx}", "test_tool", {})]),
        ]
        loop, _, _, store = _setup_soak_agent(db_path, cp_path, responses, tool)

        # Pre-cancel run
        loop.cancellation_controller.cancel(run_id, reason="Soak Pre-Cancel")

        result = await loop.run(run_id, "sys", "usr")
        assert result is None
        assert len(tool.calls) == 0

        report = RunIntegrityVerifier.verify(cp_path, run_id, idempotency_store=store)
        assert report.valid is True
        assert report.state == RunState.HALTED
