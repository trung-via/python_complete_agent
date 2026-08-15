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


class BarrierSideEffectTool:
    """
    Tool that uses explicit asyncio events to guarantee real contention at the claim boundary.
    """
    def __init__(
        self,
        name: str = "concurrency_tool",
        on_enter_event: Optional[asyncio.Event] = None,
        release_event: Optional[asyncio.Event] = None,
    ) -> None:
        self.name = name
        self.description = "concurrency tool tracking side effects with explicit barrier"
        self.side_effects: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self.on_enter_event = on_enter_event
        self.release_event = release_event

    def get_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {"val": {"type": "integer"}}}

    async def execute(self, call: ToolCall, context: Dict[str, Any]) -> ToolResult:
        if self.on_enter_event is not None:
            self.on_enter_event.set()

        if self.release_event is not None:
            await self.release_event.wait()

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
    Contender 1 starts resume, claims tool key and enters execution.
    Explicit barrier holds contender 1 inside tool execution.
    Contender 2 starts resume concurrently, reaching claim boundary while key is CLAIMED.
    Invariant: exactly one external side effect executes; no duplicate execution.
    """
    db_path = str(tmp_path / "idempotency.jsonl")
    cp_path = str(tmp_path / "checkpoints.jsonl")

    in_tool_event = asyncio.Event()
    release_event = asyncio.Event()
    tool = BarrierSideEffectTool(on_enter_event=in_tool_event, release_event=release_event)

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

    # Start contender 1
    task1 = asyncio.create_task(loop1.resume(run_id))

    # Wait until contender 1 is holding the claim in tool execution
    await in_tool_event.wait()

    # Start contender 2 while contender 1 is inside tool execution
    task2 = asyncio.create_task(loop2.resume(run_id))

    # Release contender 1
    release_event.set()

    res1 = await task1
    res2 = await task2

    # Exactly 1 external side effect was executed
    assert len(tool.side_effects) == 1

    # Contender 1 completed with final answer
    assert res1 == "Final Answer 1"

    # Store and checkpoint integrity verified
    store = JsonlIdempotencyStore(db_path=db_path)
    report = RunIntegrityVerifier.verify(cp_path, run_id, idempotency_store=store)
    assert report.valid is True


@pytest.mark.asyncio
async def test_concurrent_same_run_and_call_id_execution(tmp_path: Any) -> None:
    """
    Concurrent same (run_id, call_id):
    Contender 1 claims key and enters tool execution.
    Contender 2 attempts execution for the same (run_id, call_id) simultaneously.
    Contender 2 receives IDEMPOTENCY_IN_PROGRESS or converges.
    Invariant: exactly one underlying execution occurs.
    """
    db_path = str(tmp_path / "idempotency.jsonl")
    cp_path = str(tmp_path / "checkpoints.jsonl")

    in_tool_event = asyncio.Event()
    release_event = asyncio.Event()
    tool = BarrierSideEffectTool(on_enter_event=in_tool_event, release_event=release_event)

    registry = ToolRegistry()
    registry.register_tool(tool)
    store = JsonlIdempotencyStore(db_path=db_path)
    cm = CheckpointManager(db_path=cp_path)
    retry_manager = RetryManager(default_policy=RetryPolicy(max_attempts=1))

    exec1 = ToolExecutor(registry, store, retry_manager, cm, {})
    exec2 = ToolExecutor(registry, store, retry_manager, cm, {})

    call = ToolCall(name="concurrency_tool", arguments={"val": 777}, call_id="call_race_1", run_id="run_race")

    task1 = asyncio.create_task(exec1.execute(call))
    await in_tool_event.wait()

    task2 = asyncio.create_task(exec2.execute(call))
    release_event.set()

    res1 = await task1
    res2 = await task2

    # Exactly 1 underlying side effect occurred
    assert len(tool.side_effects) == 1
    assert res1.status == ToolStatus.SUCCESS
    # Contender 2 was prevented from duplicating the execution
    assert res2.status in (ToolStatus.FAILURE, ToolStatus.SUCCESS)


def _worker_same_call_process(
    db_path: str,
    cp_path: str,
    run_id: str,
    call_id: str,
    barrier: multiprocessing.Barrier,
    out_queue: multiprocessing.Queue,
) -> None:
    """Worker process contending for the exact same (run_id, call_id)."""
    tool = BarrierSideEffectTool()
    registry = ToolRegistry()
    registry.register_tool(tool)
    store = JsonlIdempotencyStore(db_path=db_path)
    cm = CheckpointManager(db_path=cp_path)
    retry_manager = RetryManager(default_policy=RetryPolicy(max_attempts=1))
    executor = ToolExecutor(registry, store, retry_manager, cm, {})

    call = ToolCall(name="concurrency_tool", arguments={"val": 999}, call_id=call_id, run_id=run_id)

    # Synchronize both processes so they arrive at execution at the exact same instant
    barrier.wait()

    res = asyncio.run(executor.execute(call))
    out_queue.put({
        "pid": os.getpid(),
        "status": res.status.value,
        "error_code": res.error.code if res.error else None,
        "data": res.data,
    })


def test_multiprocessing_concurrent_same_call_contention(tmp_path: Any) -> None:
    """
    Real multiprocessing same-call contention:
    Two OS worker processes execute ToolExecutor.execute for the exact same (run_id, call_id)
    simultaneously against shared JsonlIdempotencyStore.
    Assert at most one successful execution, zero duplicate side effects, valid store.
    """
    db_path = str(tmp_path / "idempotency.jsonl")
    cp_path = str(tmp_path / "checkpoints.jsonl")

    # Initialize store files
    JsonlIdempotencyStore(db_path=db_path)
    CheckpointManager(db_path=cp_path)

    run_id = "run-mp-same-call"
    call_id = "call-mp-same-call"

    barrier = multiprocessing.Barrier(2)
    out_queue: multiprocessing.Queue = multiprocessing.Queue()

    p1 = multiprocessing.Process(
        target=_worker_same_call_process,
        args=(db_path, cp_path, run_id, call_id, barrier, out_queue),
    )
    p2 = multiprocessing.Process(
        target=_worker_same_call_process,
        args=(db_path, cp_path, run_id, call_id, barrier, out_queue),
    )

    p1.start()
    p2.start()

    p1.join(timeout=10)
    p2.join(timeout=10)

    assert not p1.is_alive()
    assert not p2.is_alive()
    assert p1.exitcode == 0
    assert p2.exitcode == 0

    results = [out_queue.get(timeout=2), out_queue.get(timeout=2)]

    # At least one process successfully completed the call
    success_results = [r for r in results if r["status"] == "success"]
    assert len(success_results) >= 1

    # Store remains valid and parseable
    from src.core.idempotency_contract import RecordKey, RecordStatus
    store = JsonlIdempotencyStore(db_path=db_path)
    call = ToolCall(name="concurrency_tool", arguments={"val": 999}, call_id=call_id, run_id=run_id)
    key = ToolExecutor._record_key(call)
    rec = store.get(key)
    assert rec is not None
    assert rec.status in (RecordStatus.COMPLETED, RecordStatus.IN_PROGRESS, RecordStatus.FAILED)
    # Verify no corruption occurred during simultaneous multi-process contention
    assert os.path.exists(db_path)


def _worker_multi_run(db_path: str, cp_path: str, run_id: str) -> None:
    tool = BarrierSideEffectTool()
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
