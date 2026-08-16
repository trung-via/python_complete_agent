"""Unit tests for UsageRecord and JsonlUsageLedger."""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from src.aios_bridge.external_brain import (
    ContractValidationError,
    JsonlUsageLedger,
    UsageLedger,
    UsageRecord,
)


def test_usage_record_immutability_and_validation():
    """UsageRecord enforces required fields and non-negative integer token counts."""
    rec = UsageRecord(
        request_id="req-1",
        task_id="TASK-016",
        provider="minimax",
        model="MiniMax-M3",
        operation="PLAN",
        status="SUCCESS",
        input_tokens=100,
        output_tokens=50,
        latency_ms=200,
    )

    assert rec.total_tokens == 150
    assert rec.recorded_at is not None

    # Frozen
    with pytest.raises(AttributeError):
        rec.input_tokens = 200  # type: ignore

    # Negative tokens rejected
    with pytest.raises(ContractValidationError, match="input_tokens must be a non-negative integer"):
        UsageRecord(
            request_id="req-1",
            task_id="TASK-016",
            provider="minimax",
            model="MiniMax-M3",
            operation="PLAN",
            status="SUCCESS",
            input_tokens=-1,
        )

    # Boolean token count rejected
    with pytest.raises(ContractValidationError, match="input_tokens must be a non-negative integer"):
        UsageRecord(
            request_id="req-1",
            task_id="TASK-016",
            provider="minimax",
            model="MiniMax-M3",
            operation="PLAN",
            status="SUCCESS",
            input_tokens=True,  # type: ignore
        )


def test_usage_record_no_content_or_secret_fields():
    """UsageRecord schema strictly contains telemetry metadata and no content payloads."""
    rec = UsageRecord(
        request_id="req-1",
        task_id="TASK-016",
        provider="minimax",
        model="MiniMax-M3",
        operation="PLAN",
        status="SUCCESS",
        input_tokens=100,
        output_tokens=50,
        context_fingerprint="abc123sha",
        context_token_count=120,
    )

    d = rec.to_dict()
    forbidden_keys = {
        "content",
        "prompt",
        "instruction",
        "messages",
        "context",
        "headers",
        "api_key",
        "authorization",
        "token",
    }
    for k in forbidden_keys:
        assert k not in d


@pytest.mark.asyncio
async def test_jsonl_usage_ledger_append(tmp_path: Path):
    """JsonlUsageLedger appends valid JSONL entries to file path in temp dir."""
    log_file = tmp_path / "logs" / "usage.jsonl"
    ledger = JsonlUsageLedger(log_file)
    assert isinstance(ledger, UsageLedger)

    rec1 = UsageRecord(
        request_id="req-1",
        task_id="TASK-016",
        provider="minimax",
        model="MiniMax-M3",
        operation="PLAN",
        status="SUCCESS",
        input_tokens=100,
        output_tokens=50,
    )
    rec2 = UsageRecord(
        request_id="req-2",
        task_id="TASK-016",
        provider="minimax",
        model="MiniMax-M3",
        operation="REVIEW",
        status="FAILED",
        error_code="RATE_LIMITED",
    )

    await ledger.append(rec1)
    await ledger.append(rec2)

    assert log_file.exists()
    lines = log_file.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2

    parsed1 = json.loads(lines[0])
    parsed2 = json.loads(lines[1])

    assert parsed1["request_id"] == "req-1"
    assert parsed1["status"] == "SUCCESS"
    assert parsed2["request_id"] == "req-2"
    assert parsed2["error_code"] == "RATE_LIMITED"
