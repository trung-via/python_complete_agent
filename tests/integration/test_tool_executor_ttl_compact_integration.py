from __future__ import annotations

import multiprocessing
import os
import time
from typing import Any, Dict, Optional

import pytest

from src.core.checkpoint import CheckpointManager
from src.core.idempotency_contract import ClaimStatus, RecordKey, RecordStatus
from src.core.idempotency_store_v2 import JsonlIdempotencyStore
from src.core.retry import RetryManager
from src.core.tool_executor import ToolExecutor
from src.core.tool_registry import ToolRegistry
from src.core.types import ToolCall, ToolResult, ToolStatus


class DummyTool:
    def __init__(self, name: str = "test_tool") -> None:
        self.name = name
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


def make_call(call_id: str = "c1", idempotency_key: str = "idem-1") -> ToolCall:
    call = ToolCall(
        name="test_tool",
        arguments={},
        call_id=call_id,
        run_id="run-1",
    )
    call.idempotency_key = idempotency_key
    return call


def make_executor(
    db_path: str,
    tool: DummyTool,
    checkpoints_path: str,
    ttl_seconds: Optional[float] = 5,
) -> tuple[ToolExecutor, JsonlIdempotencyStore]:
    registry = ToolRegistry()
    registry.register_tool(tool)
    store = JsonlIdempotencyStore(db_path=db_path, ttl_seconds=ttl_seconds)
    checkpoints = CheckpointManager(db_path=checkpoints_path)
    retry_manager = RetryManager()

    executor = ToolExecutor(
        registry=registry,
        idempotency_store=store,
        retry_manager=retry_manager,
        checkpoints=checkpoints,
        context={},
    )
    return executor, store


@pytest.mark.asyncio
async def test_executor_crash_ttl_expired_reclaim_and_recovery(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    db_path = str(tmp_path / "idempotency.jsonl")
    cp_path = str(tmp_path / "checkpoints.jsonl")

    call = make_call(idempotency_key="idem-ttl")
    tool1 = DummyTool()
    executor1, store1 = make_executor(db_path, tool1, cp_path, ttl_seconds=5)

    now = time.time()
    monkeypatch.setattr(time, "time", lambda: now)

    # Worker 1 claims manually (simulating crash mid-execution)
    key = RecordKey("tool:test_tool", call.idempotency_key)
    claim1 = store1.claim(key, "worker-1")
    assert claim1.status == ClaimStatus.CLAIMED

    # Advance time by 10s past TTL (5s)
    monkeypatch.setattr(time, "time", lambda: now + 10)

    # Worker 2 attempts execution via ToolExecutor
    tool2 = DummyTool()
    executor2, store2 = make_executor(db_path, tool2, cp_path, ttl_seconds=5)

    res2 = await executor2.execute(call)

    assert res2.status == ToolStatus.SUCCESS
    assert tool2.execute_count == 1
    assert res2.data == {"count": 1}

    # Verify attempt counter on final record
    rec = store2.get(key)
    assert rec is not None
    assert rec.status == RecordStatus.COMPLETED
    assert rec.attempt == 2


@pytest.mark.asyncio
async def test_executor_compact_during_agent_lifecycle(tmp_path: Any) -> None:
    db_path = str(tmp_path / "idempotency.jsonl")
    cp_path = str(tmp_path / "checkpoints.jsonl")

    tool = DummyTool()
    executor, store = make_executor(db_path, tool, cp_path)

    # Execute 3 distinct calls
    c1 = make_call("c1", "idem-1")
    c2 = make_call("c2", "idem-2")
    c3 = make_call("c3", "idem-3")

    await executor.execute(c1)
    await executor.execute(c2)
    await executor.execute(c3)

    # Run maintenance compact
    store.compact()

    # Create fresh executor after compact
    tool2 = DummyTool()
    executor2, store2 = make_executor(db_path, tool2, cp_path)

    # Replay c1
    res1 = await executor2.execute(c1)

    assert res1.status == ToolStatus.SUCCESS
    assert res1.data == {"count": 1}
    assert tool2.execute_count == 0


@pytest.mark.asyncio
async def test_executor_prune_and_replay_behavior(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    db_path = str(tmp_path / "idempotency.jsonl")
    cp_path = str(tmp_path / "checkpoints.jsonl")

    call = make_call(idempotency_key="idem-prune")
    tool1 = DummyTool()
    executor1, store1 = make_executor(db_path, tool1, cp_path)

    now = time.time()
    monkeypatch.setattr(time, "time", lambda: now)

    await executor1.execute(call)

    # Advance time past prune window (100s)
    monkeypatch.setattr(time, "time", lambda: now + 100)

    # Prune records older than 50s
    store1.prune(max_age_seconds=50)

    # New executor executes same call -> executed fresh as attempt 1 since pruned
    tool2 = DummyTool()
    executor2, store2 = make_executor(db_path, tool2, cp_path)

    res2 = await executor2.execute(call)

    assert res2.status == ToolStatus.SUCCESS
    assert tool2.execute_count == 1


@pytest.mark.asyncio
async def test_executor_repair_after_partial_trailing_write(tmp_path: Any) -> None:
    db_path = str(tmp_path / "idempotency.jsonl")
    cp_path = str(tmp_path / "checkpoints.jsonl")

    tool1 = DummyTool()
    executor1, store1 = make_executor(db_path, tool1, cp_path)

    c1 = make_call("c1", "idem-1")
    await executor1.execute(c1)

    # Simulate trailing corruption
    with open(db_path, "a", encoding="utf-8") as f:
        f.write('{"key": {"operation_key": "tool:test_tool", "idempotency_key": "c2"}, "status": "IN_PROG')

    # Explicit maintenance repair
    repaired = store1.repair()
    assert repaired is True

    # Next call executes cleanly
    c2 = make_call("c2", "idem-2")
    res2 = await executor1.execute(c2)

    assert res2.status == ToolStatus.SUCCESS
