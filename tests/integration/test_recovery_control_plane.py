from __future__ import annotations

import asyncio
import json
import os
import tempfile
from typing import Any, Dict, Optional
import pytest

from src.agent.loop import AgentLoop
from src.agent.policy import RunPolicy
from src.core.checkpoint import CheckpointManager
from src.core.checkpoint_contract import CheckpointCorruptionError, RunState
from src.core.errors import RecoveryStateError
from src.core.idempotency_contract import RecordKey
from src.core.idempotency_store_v2 import JsonlIdempotencyStore
from src.core.recovery_controller import RecoveryController
from src.core.retry import RetryManager
from src.core.tool_executor import ToolExecutor
from src.core.tool_registry import ToolRegistry
from src.core.types import ToolCall, ToolResult, ToolStatus
from src.providers.base import LLMResponse


class CountingMockTool:
    def __init__(self, name: str = "counter_tool", result_data: Optional[Dict[str, Any]] = None):
        self.name = name
        self.description = "Mock tool for testing"
        self.result_data = result_data or {"count": 1}
        self.execute_count = 0

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {"x": {"type": "integer"}},
        }

    async def execute(self, call: ToolCall, context: Optional[Dict[str, Any]] = None) -> ToolResult:
        self.execute_count += 1
        return ToolResult(
            call_id=call.call_id,
            run_id=call.run_id,
            tool_name=self.name,
            status=ToolStatus.SUCCESS,
            data=self.result_data,
        )


class MockLLM:
    def __init__(self, responses: Optional[list] = None):
        self.responses = responses or []
        self.call_count = 0

    async def generate(self, messages, tools_schema):
        if self.call_count < len(self.responses):
            resp = self.responses[self.call_count]
            self.call_count += 1
            return resp
        raise RuntimeError("No more mock responses")


def make_test_loop(tmp_path: Any, tool: CountingMockTool, llm_responses: list) -> AgentLoop:
    db_path = str(tmp_path / "idempotency.jsonl")
    cp_path = str(tmp_path / "checkpoints.jsonl")

    registry = ToolRegistry()
    registry.register_tool(tool)

    store = JsonlIdempotencyStore(db_path=db_path)
    checkpoints = CheckpointManager(db_path=cp_path)
    retry_mgr = RetryManager()
    executor = ToolExecutor(
        registry=registry,
        idempotency_store=store,
        retry_manager=retry_mgr,
        checkpoints=checkpoints,
        context={},
    )
    llm = MockLLM(llm_responses)

    return AgentLoop(
        llm_provider=llm,
        tool_executor=executor,
        tool_registry=registry,
        checkpoints=checkpoints,
        policy=RunPolicy(max_iterations=5, max_tool_calls=5, timeout_seconds=10.0),
    )


@pytest.mark.asyncio
async def test_recovery_completed_run_zero_execution(tmp_path: Any):
    tool = CountingMockTool()
    loop = make_test_loop(tmp_path, tool, [])

    # Pre-populate completed run
    run_id = loop.checkpoints.log_task_start("test prompt")
    loop.checkpoints.log_llm_requested(run_id, iteration=1)
    loop.checkpoints.log_llm_responded(run_id, iteration=1, content="completed answer", num_tool_calls=0)
    loop.checkpoints.log_task_end(run_id, success=True, retry_count=0)

    res = await RecoveryController.resume(loop, run_id)

    assert res == "completed answer"
    assert tool.execute_count == 0
    assert loop.llm.call_count == 0


@pytest.mark.asyncio
async def test_recovery_non_recoverable_rejected(tmp_path: Any):
    tool = CountingMockTool()
    loop = make_test_loop(tmp_path, tool, [])

    run_id = loop.checkpoints.log_task_start("test prompt")
    loop.checkpoints.log_run_failed(run_id, "permanent error")

    with pytest.raises(RecoveryStateError, match="terminal state"):
        await RecoveryController.resume(loop, run_id)

    assert tool.execute_count == 0


@pytest.mark.asyncio
async def test_recovery_corrupt_checkpoint_fail_closed(tmp_path: Any):
    tool = CountingMockTool()
    loop = make_test_loop(tmp_path, tool, [])

    cp_path = loop.checkpoints.db_path
    with open(cp_path, "w", encoding="utf-8") as f:
        f.write('{"run_id": "r1", "sequence_id": 1, "timestamp": 100.0, "event_type": "TASK_START"}\n')
        f.write("CORRUPTED_JSON_LINE\n")

    with pytest.raises(CheckpointCorruptionError, match="integrity verification failed"):
        await RecoveryController.resume(loop, "r1")

    assert tool.execute_count == 0


@pytest.mark.asyncio
async def test_recovery_io_error_propagates(tmp_path: Any):
    tool = CountingMockTool()
    loop = make_test_loop(tmp_path, tool, [])
    loop.checkpoints.db_path = str(tmp_path / "non_existent_dir" / "cp.jsonl")

    with pytest.raises(FileNotFoundError):
        await RecoveryController.resume(loop, "r_any")


@pytest.mark.asyncio
async def test_recovery_read_only_inspection(tmp_path: Any):
    tool = CountingMockTool()
    loop = make_test_loop(tmp_path, tool, [])

    run_id = loop.checkpoints.log_task_start("test prompt")
    loop.checkpoints.log_llm_requested(run_id, iteration=1)

    cp_path = loop.checkpoints.db_path
    size_before = os.path.getsize(cp_path)
    mtime_before = os.path.getmtime(cp_path)

    inspection = RecoveryController.inspect(cp_path, run_id)
    assert inspection.valid is True

    size_after = os.path.getsize(cp_path)
    mtime_after = os.path.getmtime(cp_path)

    assert size_before == size_after
    assert mtime_before == mtime_after


@pytest.mark.asyncio
async def test_recovery_pending_tool_already_in_idempotency_store_replayed(tmp_path: Any):
    tool = CountingMockTool(result_data={"val": 42})

    resp2 = LLMResponse(content="final answer after tool", tool_calls=[], provider="mock", provider_response_id="res_2")
    loop = make_test_loop(tmp_path, tool, [resp2])

    run_id = "run-idem-pending"

    # Simulate crash right after LLM_RESPONDED with a tool call
    loop.checkpoints.log_run_started(run_id, "sys", "usr")
    loop.checkpoints.log_llm_requested(run_id, iteration=1)
    tc_payload = {"call_id": "call_99", "name": tool.name, "arguments": {"x": 1}}
    loop.checkpoints.log_llm_responded(
        run_id, iteration=1, content="calling tool", num_tool_calls=1, tool_calls=[tc_payload]
    )

    # Pre-complete the idempotency record in IdempotencyStore V2
    call = ToolCall(name=tool.name, arguments={"x": 1}, call_id="call_99", run_id=run_id)
    key = RecordKey(f"tool:{tool.name}", call.idempotency_key)
    loop.tool_executor.idempotency_store.claim(key, "worker-prev")
    res_obj = ToolResult(call_id="call_99", run_id=run_id, tool_name=tool.name, status=ToolStatus.SUCCESS, data={"val": 42})
    loop.tool_executor.idempotency_store.complete(key, "worker-prev", data={"result": res_obj.to_dict()})

    # Resume using RecoveryController
    final_res = await RecoveryController.resume(loop, run_id)

    assert final_res == "final answer after tool"
    assert tool.execute_count == 0


@pytest.mark.asyncio
async def test_concurrent_resume_zero_duplicate_tool_execution(tmp_path: Any):
    tool = CountingMockTool(result_data={"result": "ok"})
    resp2 = LLMResponse(content="final answer", tool_calls=[], provider="mock", provider_response_id="res_2")

    loop1 = make_test_loop(tmp_path, tool, [resp2])
    loop2 = make_test_loop(tmp_path, tool, [resp2])

    run_id = "run-concurrent-resume"
    loop1.checkpoints.log_run_started(run_id, "sys", "usr")
    loop1.checkpoints.log_llm_requested(run_id, iteration=1)
    tc_payload = {"call_id": "call_conc", "name": tool.name, "arguments": {"a": 1}}
    loop1.checkpoints.log_llm_responded(
        run_id, iteration=1, content="call tool", num_tool_calls=1, tool_calls=[tc_payload]
    )

    # Launch concurrent resumes
    res1, res2 = await asyncio.gather(
        RecoveryController.resume(loop1, run_id),
        RecoveryController.resume(loop2, run_id),
    )

    assert res1 == "final answer"
    assert res2 == "final answer"
    assert tool.execute_count == 1
