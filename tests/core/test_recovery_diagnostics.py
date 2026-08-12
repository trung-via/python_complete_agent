from __future__ import annotations

import json
import os
import tempfile
from typing import Any, Dict, List, Optional

import pytest

from src.agent.loop import AgentLoop
from src.agent.policy import RunPolicy
from src.core.checkpoint import CheckpointManager
from src.core.checkpoint_contract import CheckpointCorruptionError
from src.core.errors import RecoveryStateError
from src.core.idempotency_store_v2 import JsonlIdempotencyStore
from src.core.retry import RetryManager
from src.core.tool_executor import ToolExecutor
from src.core.tool_registry import ToolRegistry
from src.providers.base import LLMProvider, LLMResponse


class DummyLLM(LLMProvider):
    async def generate(
        self,
        messages: List[Any],
        tools: List[dict],
    ) -> LLMResponse:
        return LLMResponse(
            provider="mock",
            provider_response_id="r1",
            content="Final answer",
            tool_calls=[],
        )


def _setup_loop(tmp_path: Any) -> tuple[AgentLoop, CheckpointManager]:
    cp_path = str(tmp_path / "checkpoints.jsonl")
    db_path = str(tmp_path / "idempotency.jsonl")

    registry = ToolRegistry()
    store = JsonlIdempotencyStore(db_path=db_path)
    checkpoints = CheckpointManager(db_path=cp_path)
    retry_manager = RetryManager()

    tool_executor = ToolExecutor(
        registry=registry,
        idempotency_store=store,
        retry_manager=retry_manager,
        checkpoints=checkpoints,
        context={},
    )

    llm = DummyLLM()
    loop = AgentLoop(
        llm_provider=llm,
        tool_executor=tool_executor,
        tool_registry=registry,
        checkpoints=checkpoints,
        policy=RunPolicy(),
    )
    return loop, checkpoints


@pytest.mark.asyncio
async def test_resume_non_existent_run_raises_recovery_state_error(tmp_path: Any) -> None:
    loop, _ = _setup_loop(tmp_path)
    with pytest.raises(RecoveryStateError, match="not found in checkpoints"):
        await loop.resume("run-does-not-exist")


@pytest.mark.asyncio
async def test_resume_terminal_failed_or_halted_raises_recovery_state_error(
    tmp_path: Any,
) -> None:
    loop, checkpoints = _setup_loop(tmp_path)

    run_fail = "run-failed"
    checkpoints.log_run_started(run_fail, "sys", "usr")
    checkpoints.log_run_failed(run_fail, "critical failure")

    with pytest.raises(RecoveryStateError, match="Cannot resume run 'run-failed' in terminal state FAILED"):
        await loop.resume(run_fail)

    run_halt = "run-halted"
    checkpoints.log_run_started(run_halt, "sys", "usr")
    checkpoints.log_run_halted(run_halt, "timeout reached")

    with pytest.raises(RecoveryStateError, match="Cannot resume run 'run-halted' in terminal state HALTED"):
        await loop.resume(run_halt)


@pytest.mark.asyncio
async def test_resume_corrupt_checkpoint_raises_checkpoint_corruption_error(
    tmp_path: Any,
) -> None:
    cp_path = str(tmp_path / "checkpoints.jsonl")

    # Manually write sequence gap to simulate corruption
    run_id = "run-corrupt"
    events = [
        {
            "run_id": run_id,
            "sequence_id": 1,
            "timestamp": 100.0,
            "event_type": "RUN_STARTED",
            "payload": {"system_prompt": "sys", "user_prompt": "usr"},
        },
        {
            "run_id": run_id,
            "sequence_id": 5,  # Gap 1 -> 5!
            "timestamp": 101.0,
            "event_type": "LLM_REQUESTED",
            "payload": {"iteration": 1},
        },
    ]

    with open(cp_path, "w", encoding="utf-8") as f:
        for evt in events:
            f.write(json.dumps(evt) + "\n")

    loop, _ = _setup_loop(tmp_path)

    # Fail-closed: raises CheckpointCorruptionError
    with pytest.raises(CheckpointCorruptionError, match="Sequence_id gap"):
        await loop.resume(run_id)


@pytest.mark.asyncio
async def test_deterministic_classification_reproducibility(tmp_path: Any) -> None:
    cp_path = str(tmp_path / "checkpoints.jsonl")
    run_id = "run-repeat-corrupt"

    events = [
        {
            "run_id": run_id,
            "sequence_id": 1,
            "timestamp": 100.0,
            "event_type": "RUN_STARTED",
            "payload": {},
        },
        {
            "run_id": run_id,
            "sequence_id": 2,
            "timestamp": 99.0,  # Timestamp rollback!
            "event_type": "LLM_REQUESTED",
            "payload": {},
        },
    ]

    with open(cp_path, "w", encoding="utf-8") as f:
        for evt in events:
            f.write(json.dumps(evt) + "\n")

    loop, _ = _setup_loop(tmp_path)

    # Re-run recovery 3 times -> exact same exception and error message
    err_msg1 = ""
    err_msg2 = ""
    err_msg3 = ""

    try:
        await loop.resume(run_id)
    except CheckpointCorruptionError as e:
        err_msg1 = str(e)

    try:
        await loop.resume(run_id)
    except CheckpointCorruptionError as e:
        err_msg2 = str(e)

    try:
        await loop.resume(run_id)
    except CheckpointCorruptionError as e:
        err_msg3 = str(e)

    assert err_msg1 != ""
    assert err_msg1 == err_msg2 == err_msg3
