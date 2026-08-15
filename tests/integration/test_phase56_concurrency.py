from __future__ import annotations

import asyncio
import multiprocessing
import os
import threading
from typing import Any, Dict, List, Optional
import pytest

from src.agent.integrity_verifier import RunIntegrityVerifier
from src.agent.loop import AgentLoop
from src.agent.messages import LLMMessage
from src.agent.policy import RunPolicy
from src.core.checkpoint import CheckpointManager
from src.core.checkpoint_contract import RunState
from src.core.idempotency_store_v2 import JsonlIdempotencyStore
from src.core.retry import RetryManager, RetryPolicy
from src.core.tool_executor import ToolExecutor
from src.core.tool_registry import ToolRegistry
from src.core.types import ToolCall, ToolResult, ToolStatus
from src.providers.base import LLMResponse, ProviderToolCall
from tests.support.fault_injection import FaultyLLMProvider


class GlobalSideEffectTool:
    def __init__(self, name: str = "concurrency_tool") -> None:
        self.name = name
        self.description = "concurrency tool tracking side effects"
        self.side_effects: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def get_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {"val": {"type": "integer"}}}

    async def execute(self, call: ToolCall, context: Dict[str, Any]) -> ToolResult:
        with self._lock:
            self.side_effects.append({"call_id": call.call_id, "args": call.arguments})
            count = len(self.side_effects)

        return ToolResult(
            call_id=call.call_id,
            run_id=call.run_id,
            tool_name=call.name,
            status=ToolStatus.SUCCESS,
            data={"count": count},
        )


def _build_concurrency_agent(
    tmp_path: Any,
    responses: List[LLMResponse],
    tool: Any,
    db_path: str,
    cp_path: str,
    policy: Optional[RunPolicy] = None,
) -> AgentLoop:
    registry = ToolRegistry()
    registry.register_tool(tool)
    store = JsonlIdempotencyStore(db_path=db_path)
    checkpoints = CheckpointManager(db_path=cp_path)
    retry_manager = RetryManager(default_policy=RetryPolicy(max_attempts=2, base_delay=0.01))

    executor = ToolExecutor(
        registry=registry,
        idempotency_store=store,
        retry_manager=retry_manager,
        checkpoints=checkpoints,
        context={},
    )
    llm = FaultyLLMProvider(responses)
    return AgentLoop(
        llm_provider=llm,
        tool_executor=executor,
        tool_registry=registry,
        checkpoints=checkpoints,
        policy=policy or RunPolicy(max_iterations=5, max_tool_calls=5, timeout_seconds=10),
    )


# ============================================================================
# M5.4 — Concurrent Resume / Duplicate Execution Safety
# ============================================================================

@pytest.mark.asyncio
async def test_same_run_two_concurrent_resume_contenders(tmp_path: Any) -> None:
    """
    Same run, two resume contenders:
    Interrupted run has pending tool call c1.
    Two workers attempt recovery simultaneously on shared stores.
    Safety invariant: at most one external side effect executes for stable call_id c1.
    """
    db_path = str(tmp_path / "idempotency.jsonl")
    cp_path = str(tmp_path / "checkpoints.jsonl")
    tool = GlobalSideEffectTool()

    run_id = "run-concurrent-resume"
    cm = CheckpointManager(db_path=cp_path)
    cm.log_run_started(run_id, "sys", "usr")
    cm.log_llm_requested(run_id, iteration=1)
    cm.log_llm_responded(
        run_id,
        iteration=1,
        content=None,
        num_tool_calls=1,
        tool_calls=[{"call_id": "c_concurrent_1", "name": "concurrency_tool", "arguments": {"val": 100}}],
    )

    responses1 = [
        LLMResponse(provider="mock", provider_response_id="2", content="Final Answer 1", tool_calls=[]),
    ]
    responses2 = [
        LLMResponse(provider="mock", provider_response_id="2", content="Final Answer 2", tool_calls=[]),
    ]

    loop1 = _build_concurrency_agent(tmp_path, responses1, tool, db_path, cp_path)
    loop2 = _build_concurrency_agent(tmp_path, responses2, tool, db_path, cp_path)

    # Launch two concurrent resume attempts
    res1, res2 = await asyncio.gather(
        loop1.resume(run_id),
        loop2.resume(run_id),
        return_exceptions=True,
    )

    # External side effect must be executed at most once
    assert len(tool.side_effects) <= 1

    # At least one contender completed successfully or cleanly resolved
    valid_results = [r for r in [res1, res2] if isinstance(r, str)]
    assert len(valid_results) >= 1

    # Durable checkpoints remain consistent and valid
    store = JsonlIdempotencyStore(db_path=db_path)
    report = RunIntegrityVerifier.verify(cp_path, run_id, idempotency_store=store)
    assert report.valid is True


@pytest.mark.asyncio
async def test_concurrent_same_run_and_call_id_execution(tmp_path: Any) -> None:
    """
    Concurrent same (run_id, call_id):
    Two executors attempt to execute the exact same ToolCall simultaneously against shared store.
    One executes tool, second contender receives completed result from idempotency store.
    No duplicate execution occurs.
    """
    db_path = str(tmp_path / "idempotency.jsonl")
    cp_path = str(tmp_path / "checkpoints.jsonl")
    tool = GlobalSideEffectTool()

    registry = ToolRegistry()
    registry.register_tool(tool)
    store = JsonlIdempotencyStore(db_path=db_path)
    cm = CheckpointManager(db_path=cp_path)
    retry_manager = RetryManager(default_policy=RetryPolicy(max_attempts=1))

    exec1 = ToolExecutor(registry, store, retry_manager, cm, {})
    exec2 = ToolExecutor(registry, store, retry_manager, cm, {})

    call = ToolCall(name="concurrency_tool", arguments={"val": 777}, call_id="call_race_1", run_id="run_race")

    res1, res2 = await asyncio.gather(
        exec1.execute(call),
        exec2.execute(call),
    )

    # Exactly 1 underlying side effect
    assert len(tool.side_effects) == 1
    assert res1.status == ToolStatus.SUCCESS or res2.status == ToolStatus.SUCCESS


def _worker_multi_run(db_path: str, cp_path: str, run_id: str) -> None:
    tool = GlobalSideEffectTool()
    registry = ToolRegistry()
    registry.register_tool(tool)
    store = JsonlIdempotencyStore(db_path=db_path)
    cm = CheckpointManager(db_path=cp_path)
    retry_manager = RetryManager()
    executor = ToolExecutor(registry, store, retry_manager, cm, {})

    responses = [
        LLMResponse(
            provider="mock",
            provider_response_id="1",
            content=None,
            tool_calls=[ProviderToolCall("c_worker", "concurrency_tool", {"worker": run_id})],
        ),
        LLMResponse(
            provider="mock",
            provider_response_id="2",
            content=f"Done {run_id}",
            tool_calls=[],
        ),
    ]
    llm = FaultyLLMProvider(responses)
    loop = AgentLoop(
        llm_provider=llm,
        tool_executor=executor,
        tool_registry=registry,
        checkpoints=cm,
        policy=RunPolicy(max_iterations=5, max_tool_calls=5, timeout_seconds=10),
    )
    asyncio.run(loop.run(run_id, "sys", f"usr_{run_id}"))


def test_four_process_concurrent_runs_with_shared_stores(tmp_path: Any) -> None:
    """
    4 OS processes running concurrent independent AgentLoops sharing checkpoint and idempotency stores.
    All runs complete and pass full integrity verification.
    """
    db_path = str(tmp_path / "idempotency.jsonl")
    cp_path = str(tmp_path / "checkpoints.jsonl")

    # Initialize store files
    JsonlIdempotencyStore(db_path=db_path)
    CheckpointManager(db_path=cp_path)

    procs: list[multiprocessing.Process] = []
    num_workers = 4

    for idx in range(num_workers):
        run_id = f"run-proc-{idx}"
        p = multiprocessing.Process(
            target=_worker_multi_run,
            args=(db_path, cp_path, run_id),
        )
        procs.append(p)
        p.start()

    for p in procs:
        p.join(timeout=15)
        assert not p.is_alive()
        assert p.exitcode == 0

    # Verify integrity of each worker run
    store = JsonlIdempotencyStore(db_path=db_path)
    for idx in range(num_workers):
        run_id = f"run-proc-{idx}"
        report = RunIntegrityVerifier.verify(cp_path, run_id, idempotency_store=store)
        assert report.valid is True
        assert report.state == RunState.COMPLETED
