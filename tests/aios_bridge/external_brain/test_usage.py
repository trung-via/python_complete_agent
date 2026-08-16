"""Unit tests for UsageRecord and JsonlUsageLedger adhering to ADR-007."""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from src.aios_bridge.external_brain import (
    ContractValidationError,
    JsonlUsageLedger,
    ModelResponseStatus,
    UsageLedger,
    UsageRecord,
)


def test_usage_record_immutability_and_validation():
    """UsageRecord enforces ADR-007 schema, non-negative tokens, and immutability."""
    rec = UsageRecord(
        schema_version="1",
        timestamp_utc="2026-08-16T10:00:00+00:00",
        request_id="req-1",
        task_id="TASK-016",
        provider="minimax",
        requested_model="MiniMax-M3",
        actual_model="MiniMax-M3",
        status=ModelResponseStatus.SUCCESS,
        provider_input_tokens=100,
        provider_output_tokens=50,
        provider_reasoning_tokens=20,
        provider_cached_tokens=10,
        latency_ms=200,
        context_fingerprint="abc123sha",
        context_counted_tokens=120,
        context_counter_id="utf8_conservative",
        context_count_is_exact=True,
    )

    assert rec.schema_version == "1"
    assert rec.timestamp_utc == "2026-08-16T10:00:00+00:00"
    assert rec.requested_model == "MiniMax-M3"
    assert rec.actual_model == "MiniMax-M3"
    assert rec.status == ModelResponseStatus.SUCCESS

    # Frozen
    with pytest.raises(AttributeError):
        rec.provider_input_tokens = 200  # type: ignore

    # Negative tokens rejected
    with pytest.raises(ContractValidationError, match="provider_input_tokens must be a non-negative integer"):
        UsageRecord(
            schema_version="1",
            timestamp_utc="2026-08-16T10:00:00+00:00",
            request_id="req-1",
            task_id="TASK-016",
            provider="minimax",
            requested_model="MiniMax-M3",
            actual_model="MiniMax-M3",
            status=ModelResponseStatus.SUCCESS,
            provider_input_tokens=-1,
        )

    # Boolean token count rejected
    with pytest.raises(ContractValidationError, match="provider_input_tokens must be a non-negative integer"):
        UsageRecord(
            schema_version="1",
            timestamp_utc="2026-08-16T10:00:00+00:00",
            request_id="req-1",
            task_id="TASK-016",
            provider="minimax",
            requested_model="MiniMax-M3",
            actual_model="MiniMax-M3",
            status=ModelResponseStatus.SUCCESS,
            provider_input_tokens=True,  # type: ignore
        )


def test_usage_record_separates_provider_and_m2_telemetry():
    """UsageRecord maintains explicit separate labeling for provider tokens and M2 context estimate."""
    rec = UsageRecord(
        schema_version="1",
        timestamp_utc="2026-08-16T10:00:00+00:00",
        request_id="req-1",
        task_id="TASK-016",
        provider="minimax",
        requested_model=None,  # request.model was omitted
        actual_model="MiniMax-M3",
        status=ModelResponseStatus.SUCCESS,
        provider_input_tokens=150,
        provider_output_tokens=75,
        context_fingerprint="sha256context",
        context_counted_tokens=180,
        context_counter_id="utf8_conservative",
        context_count_is_exact=False,
    )

    d = rec.to_dict()
    assert d["provider_input_tokens"] == 150
    assert d["provider_output_tokens"] == 75
    assert d["context_counted_tokens"] == 180
    assert d["requested_model"] is None
    assert d["actual_model"] == "MiniMax-M3"
    assert d["status"] == "SUCCESS"

    # Strictly no prompt, context body, output content, headers, or secrets
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


def test_jsonl_usage_ledger_append(tmp_path: Path):
    """JsonlUsageLedger synchronously appends valid JSONL entries to file path."""
    log_file = tmp_path / "logs" / "usage.jsonl"
    ledger = JsonlUsageLedger(log_file)
    assert isinstance(ledger, UsageLedger)

    rec1 = UsageRecord(
        schema_version="1",
        timestamp_utc="2026-08-16T10:00:00+00:00",
        request_id="req-1",
        task_id="TASK-016",
        provider="minimax",
        requested_model="MiniMax-M3",
        actual_model="MiniMax-M3",
        status=ModelResponseStatus.SUCCESS,
        provider_input_tokens=100,
        provider_output_tokens=50,
    )
    rec2 = UsageRecord(
        schema_version="1",
        timestamp_utc="2026-08-16T10:01:00+00:00",
        request_id="req-2",
        task_id="TASK-016",
        provider="minimax",
        requested_model="MiniMax-M3",
        actual_model="MiniMax-M3",
        status=ModelResponseStatus.RATE_LIMITED,
        error_code="RATE_LIMITED",
    )

    ledger.append(rec1)
    ledger.append(rec2)

    assert log_file.exists()
    lines = log_file.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2

    parsed1 = json.loads(lines[0])
    parsed2 = json.loads(lines[1])

    assert parsed1["request_id"] == "req-1"
    assert parsed1["status"] == "SUCCESS"
    assert parsed1["provider_input_tokens"] == 100
    assert parsed2["request_id"] == "req-2"
    assert parsed2["error_code"] == "RATE_LIMITED"
