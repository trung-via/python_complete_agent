from __future__ import annotations

import os
from typing import Any, Dict, Optional

import pytest

from src.core.checkpoint import CheckpointManager
from src.core.errors import AgentException, SystemStateError
from src.core.idempotency_contract import ClaimStatus, RecordKey
from src.core.idempotency_store_v2 import JsonlIdempotencyStore
from src.core.retry import RetryManager, RetryPolicy
from src.core.tool_executor import ToolExecutor
from src.core.tool_registry import ToolRegistry
from src.core.types import ToolCall, ToolResult, ToolStatus


class DummyTool:
    def __init__(
        self,
        name: str = "test_tool",
        result_data: Optional[Dict[str, Any]] = None,
        error: Optional[Exception] = None,
    ) -> None:
        self.name = name
        self.result_data = result_data or {"status": "ok"}
        self.error = error
        self.execute_count = 0

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "param": {"type": "string"},
            },
        }

    async def execute(self, call: ToolCall, context: Dict[str, Any]) -> ToolResult:
        self.execute_count += 1

        if self.error is not None:
            raise self.error

        return ToolResult(
            call_id=call.call_id,
            run_id=call.run_id,
            tool_name=call.name,
            status=ToolStatus.SUCCESS,
            data=self.result_data,
        )


def make_call(
    *,
    call_id: str = "call-1",
    run_id: str = "run-1",
    name: str = "test_tool",
    arguments: Optional[Dict[str, Any]] = None,
) -> ToolCall:
    return ToolCall(
        name=name,
        arguments=arguments or {"param": "value"},
        call_id=call_id,
        run_id=run_id,
    )


def make_executor(
    db_path: str,
    tool: DummyTool,
    checkpoints_path: str,
    max_attempts: int = 1,
) -> tuple[ToolExecutor, JsonlIdempotencyStore]:
    registry = ToolRegistry()
    registry.register_tool(tool)

    store = JsonlIdempotencyStore(db_path=db_path)
    checkpoints = CheckpointManager(db_path=checkpoints_path)
    retry_manager = RetryManager(
        default_policy=RetryPolicy(max_attempts=max_attempts, base_delay=0.001)
    )

    executor = ToolExecutor(
        registry=registry,
        idempotency_store=store,
        retry_manager=retry_manager,
        checkpoints=checkpoints,
        context={},
    )
    return executor, store


@pytest.mark.asyncio
async def test_end_to_end_success_persists_and_replays_across_store_restarts(
    tmp_path: Any,
) -> None:
    db_path = str(tmp_path / "idempotency.jsonl")
    cp_path = str(tmp_path / "checkpoints.jsonl")

    call = make_call()
    tool1 = DummyTool(result_data={"output_file": "gdrive://file_123"})
    executor1, _ = make_executor(db_path, tool1, cp_path)

    # 1. First execution — writes to JSONL
    result1 = await executor1.execute(call)

    assert result1.status == ToolStatus.SUCCESS
    assert result1.data == {"output_file": "gdrive://file_123"}
    assert tool1.execute_count == 1

    # 2. Re-instantiate a fresh store and executor from disk
    tool2 = DummyTool(result_data={"output_file": "SHOULD_NOT_BE_RETURNED"})
    executor2, store2 = make_executor(db_path, tool2, cp_path)

    # 3. Second execution — replays from JSONL, tool2 must NOT run
    result2 = await executor2.execute(call)

    assert result2.status == ToolStatus.SUCCESS
    assert result2.data == {"output_file": "gdrive://file_123"}
    assert tool2.execute_count == 0

    # 4. Verify durable record in store2
    record_key = RecordKey("tool:test_tool", call.idempotency_key)
    durable_record = store2.get(record_key)

    assert durable_record is not None
    assert durable_record.status.value == "COMPLETED"


@pytest.mark.asyncio
async def test_retryable_failure_persists_and_allows_reclaim_with_incremented_attempt(
    tmp_path: Any,
) -> None:
    db_path = str(tmp_path / "idempotency.jsonl")
    cp_path = str(tmp_path / "checkpoints.jsonl")

    call = make_call()

    # 1. First attempt fails with a retryable error (max_attempts=1)
    tool1 = DummyTool(
        error=AgentException("rate limited", code="RATE_LIMIT", retryable=True),
    )
    executor1, _ = make_executor(db_path, tool1, cp_path, max_attempts=1)

    res1 = await executor1.execute(call)

    assert res1.status == ToolStatus.FAILURE
    assert tool1.execute_count == 1

    # 2. Second executor from disk claims the same key — must reclaim with attempt=2
    tool2 = DummyTool(result_data={"recovered": True})
    executor2, store2 = make_executor(db_path, tool2, cp_path)

    res2 = await executor2.execute(call)

    assert res2.status == ToolStatus.SUCCESS
    assert res2.data == {"recovered": True}
    assert tool2.execute_count == 1

    # 3. Verify attempt counter on final durable record
    record_key = RecordKey("tool:test_tool", call.idempotency_key)
    record = store2.get(record_key)

    assert record is not None
    assert record.attempt == 2
    assert record.status.value == "COMPLETED"


@pytest.mark.asyncio
async def test_permanent_failure_persists_and_blocks_subsequent_attempts(
    tmp_path: Any,
) -> None:
    db_path = str(tmp_path / "idempotency.jsonl")
    cp_path = str(tmp_path / "checkpoints.jsonl")

    call = make_call()

    # 1. First attempt fails with a non-retryable error
    tool1 = DummyTool(
        error=AgentException("invalid format", code="BAD_INPUT", retryable=False),
    )
    executor1, _ = make_executor(db_path, tool1, cp_path)

    res1 = await executor1.execute(call)

    assert res1.status == ToolStatus.FAILURE

    # 2. Second executor attempts the same key — blocked as FAILED_PERMANENT
    tool2 = DummyTool(result_data={"should_not_run": True})
    executor2, _ = make_executor(db_path, tool2, cp_path)

    res2 = await executor2.execute(call)

    assert res2.status == ToolStatus.FAILURE
    assert res2.error is not None
    assert res2.error.code == "IDEMPOTENCY_FAILED_PERMANENT"
    assert tool2.execute_count == 0


@pytest.mark.asyncio
async def test_cross_instance_race_only_one_executor_runs_tool(
    tmp_path: Any,
) -> None:
    db_path = str(tmp_path / "idempotency.jsonl")
    cp_path = str(tmp_path / "checkpoints.jsonl")

    call = make_call()

    tool1 = DummyTool(result_data={"worker": 1})
    executor1, _ = make_executor(db_path, tool1, cp_path)

    tool2 = DummyTool(result_data={"worker": 2})
    executor2, _ = make_executor(db_path, tool2, cp_path)

    # Worker 1 claims and executes
    res1 = await executor1.execute(call)
    assert res1.status == ToolStatus.SUCCESS

    # Worker 2 tries to claim the same key concurrently/subsequently
    res2 = await executor2.execute(call)
    assert res2.status == ToolStatus.SUCCESS
    assert res2.data == {"worker": 1}  # Replayed worker 1's result
    assert tool2.execute_count == 0


@pytest.mark.asyncio
async def test_persistence_failure_during_completion_raises_system_state_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    db_path = str(tmp_path / "idempotency.jsonl")
    cp_path = str(tmp_path / "checkpoints.jsonl")

    call = make_call()
    tool = DummyTool(result_data={"val": 1})
    executor, store = make_executor(db_path, tool, cp_path)

    original_append = store._append

    def patched_append(record: Any) -> None:
        if record.status.value == "COMPLETED":
            raise OSError("simulated disk failure on complete")
        original_append(record)

    monkeypatch.setattr(store, "_append", patched_append)

    with pytest.raises(SystemStateError, match="completion persistence failed"):
        await executor.execute(call)

    assert tool.execute_count == 1
