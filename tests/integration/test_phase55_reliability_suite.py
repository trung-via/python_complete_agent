from __future__ import annotations

import multiprocessing
import os
import tempfile
from typing import Any, Dict, List, Optional

import pytest

from src.agent.integrity_verifier import RunIntegrityVerifier
from src.agent.loop import AgentLoop
from src.agent.messages import LLMMessage
from src.agent.policy import RunPolicy
from src.core.checkpoint import CheckpointManager
from src.core.checkpoint_contract import CheckpointStateError, RunState
from src.core.errors import RecoveryStateError, SystemStateError
from src.core.idempotency_contract import RecordKey
from src.core.idempotency_store_v2 import JsonlIdempotencyStore
from src.core.retry import RetryManager
from src.core.tool_executor import ToolExecutor
from src.core.tool_registry import ToolRegistry
from src.core.types import ToolCall, ToolResult, ToolStatus
from src.providers.base import LLMProvider, LLMResponse, ProviderToolCall


class ReliabilityLLM(LLMProvider):
    def __init__(self, responses: List[LLMResponse]) -> None:
        self.responses = responses
        self.call_count = 0

    async def generate(
        self,
        messages: List[LLMMessage],
        tools: List[dict],
    ) -> LLMResponse:
        if self.call_count >= len(self.responses):
            return LLMResponse(
                provider="mock",
                provider_response_id="fallback",
                content="Fallback Done",
                tool_calls=[],
            )
        resp = self.responses[self.call_count]
        self.call_count += 1
        return resp


class CountingExecutionTool:
    def __init__(self, name: str = "counter_tool") -> None:
        self.name = name
        self.description = "counter tool for E2E testing"
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


def _make_resp(
    content: Optional[str],
    tool_calls: List[ProviderToolCall] | None = None,
) -> LLMResponse:
    return LLMResponse(
        provider="mock",
        provider_response_id="r-e2e",
        content=content,
        tool_calls=tool_calls or [],
    )


def _build_agent_harness(
    tmp_path: Any,
    responses: List[LLMResponse],
    tool: CountingExecutionTool,
    store: Optional[JsonlIdempotencyStore] = None,
    checkpoints: Optional[CheckpointManager] = None,
) -> tuple[AgentLoop, JsonlIdempotencyStore, CheckpointManager]:
    db_path = str(tmp_path / "idempotency.jsonl")
    cp_path = str(tmp_path / "checkpoints.jsonl")

    registry = ToolRegistry()
    registry.register_tool(tool)

    if store is None:
        store = JsonlIdempotencyStore(db_path=db_path)
    if checkpoints is None:
        checkpoints = CheckpointManager(db_path=cp_path)
    retry_manager = RetryManager()

    executor = ToolExecutor(
        registry=registry,
        idempotency_store=store,
        retry_manager=retry_manager,
        checkpoints=checkpoints,
        context={},
    )

    llm = ReliabilityLLM(responses)
    loop = AgentLoop(
        llm_provider=llm,
        tool_executor=executor,
        tool_registry=registry,
        checkpoints=checkpoints,
        policy=RunPolicy(max_iterations=5, max_tool_calls=5, timeout_seconds=10),
    )
    return loop, store, checkpoints


@pytest.mark.asyncio
async def test_e2e_multi_crash_cascade_and_resumption(tmp_path: Any) -> None:
    # 1. LLM Crash -> Resume -> Tool Execution -> Terminal Checkpoint -> Verify
    tool = CountingExecutionTool()
    cp_path = str(tmp_path / "checkpoints.jsonl")

    # Step A: Run started, LLM requested, but process crashes before LLM_RESPONDED
    checkpoints = CheckpointManager(db_path=cp_path)
    run_id = "run-cascade"
    checkpoints.log_run_started(run_id, "sys", "usr")
    checkpoints.log_llm_requested(run_id, iteration=1)

    # Step B: Resume on fresh process instance
    responses1 = [
        _make_resp(
            content="Calling tool",
            tool_calls=[ProviderToolCall(provider_call_id="c1", name="counter_tool", arguments={})],
        ),
        _make_resp(content="Final Answer Cascade"),
    ]
    loop1, store1, _ = _build_agent_harness(tmp_path, responses1, tool, checkpoints=checkpoints)

    result = await loop1.resume(run_id)

    assert result == "Final Answer Cascade"
    assert tool.execute_count == 1

    # Step C: Integrity Verification after completion
    report = RunIntegrityVerifier.verify(cp_path, run_id, idempotency_store=store1)
    assert report.valid is True
    assert report.state == RunState.COMPLETED
    assert report.completed_tool_calls == 1


@pytest.mark.asyncio
async def test_interleaved_runs_reconstruction_and_verification(tmp_path: Any) -> None:
    cp_path = str(tmp_path / "checkpoints.jsonl")
    cm = CheckpointManager(db_path=cp_path)

    run_a = "run-interleave-A"
    run_b = "run-interleave-B"

    cm.log_run_started(run_a, "sys_a", "usr_a")
    cm.log_run_started(run_b, "sys_b", "usr_b")

    cm.log_llm_requested(run_a, iteration=1)
    cm.log_llm_requested(run_b, iteration=1)

    cm.log_llm_responded(run_a, iteration=1, content="Done A", num_tool_calls=0)
    cm.log_run_completed(run_a)

    cm.log_llm_responded(run_b, iteration=1, content="Done B", num_tool_calls=0)
    cm.log_run_completed(run_b)

    report_a = RunIntegrityVerifier.verify(cp_path, run_a)
    assert report_a.valid is True
    assert report_a.state == RunState.COMPLETED

    report_b = RunIntegrityVerifier.verify(cp_path, run_b)
    assert report_b.valid is True
    assert report_b.state == RunState.COMPLETED


@pytest.mark.asyncio
async def test_sequential_resume_and_terminal_immutability(tmp_path: Any) -> None:
    tool = CountingExecutionTool()
    responses = [_make_resp(content="Sequential Done")]
    loop, _, checkpoints = _build_agent_harness(tmp_path, responses, tool)

    run_id = "run-seq-term"
    checkpoints.log_run_started(run_id, "sys", "usr")

    # First resume completes run
    res1 = await loop.resume(run_id)
    assert res1 == "Sequential Done"

    # Second resume returns completed content deterministically
    res2 = await loop.resume(run_id)
    assert res2 == "Sequential Done"

    # Terminal state immutability: attempting to append to completed run raises CheckpointStateError
    with pytest.raises(CheckpointStateError):
        checkpoints.log_llm_requested(run_id, iteration=2)


@pytest.mark.asyncio
async def test_maintenance_compact_and_prune_resilience(tmp_path: Any) -> None:
    # Verify that compacting and pruning JsonlIdempotencyStore preserves resume contract
    tool = CountingExecutionTool()
    responses = [
        _make_resp(
            content="Calling tool",
            tool_calls=[ProviderToolCall(provider_call_id="c1", name="counter_tool", arguments={})],
        ),
        _make_resp(content="Finished after maintenance"),
    ]
    loop, store, checkpoints = _build_agent_harness(tmp_path, responses, tool)

    run_id = "run-maint"
    checkpoints.log_run_started(run_id, "sys", "usr")

    # Compact & Prune store
    store.compact()
    store.prune(max_age_seconds=86400)

    # Resume succeeds cleanly
    result = await loop.resume(run_id)
    assert result == "Finished after maintenance"
    assert tool.execute_count == 1


def _worker_multiprocess_run(cp_path: str, run_id: str) -> None:
    cm = CheckpointManager(db_path=cp_path)
    cm.log_run_started(run_id, "sys", f"usr_{run_id}")
    cm.log_llm_requested(run_id, iteration=1)
    cm.log_llm_responded(
        run_id,
        iteration=1,
        content="tool call",
        num_tool_calls=1,
        tool_calls=[{"call_id": "c1", "name": "t1", "arguments": {}}],
    )
    cm.log_tool_result_received(run_id, "c1", status="success", tool_name="t1", result={"val": 1})
    cm.log_llm_requested(run_id, iteration=2)
    cm.log_llm_responded(run_id, iteration=2, content=f"resp_{run_id}", num_tool_calls=0)
    cm.log_run_completed(run_id)


def test_multiprocess_concurrent_reliability_and_integrity(tmp_path: Any) -> None:
    cp_path = str(tmp_path / "checkpoints.jsonl")

    # Initialize checkpoint file
    CheckpointManager(db_path=cp_path)

    procs: list[multiprocessing.Process] = []
    num_workers = 4

    for idx in range(num_workers):
        run_id = f"run-mp-{idx}"
        p = multiprocessing.Process(
            target=_worker_multiprocess_run,
            args=(cp_path, run_id),
        )
        procs.append(p)
        p.start()

    for p in procs:
        p.join(timeout=10)
        assert not p.is_alive()
        assert p.exitcode == 0

    # Verify integrity of every worker run
    for idx in range(num_workers):
        run_id = f"run-mp-{idx}"
        report = RunIntegrityVerifier.verify(cp_path, run_id)
        assert report.valid is True
        assert report.state == RunState.COMPLETED
