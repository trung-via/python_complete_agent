"""Comprehensive test suite for AIOS Usage & Efficiency Telemetry (ADR-013 / ADR-014)."""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from src.aios_bridge.continuity import (
    BrainOperation,
    BrainUsageRecord,
    ContinuityStateValidationError,
    EfficiencyMetrics,
    ExecutorAction,
    ExecutorUsageRecord,
    HumanUsage,
    TaskUsageRecord,
    TokenMeasurement,
    UsageSource,
    aggregate_token_ranges,
    calculate_context_efficiency_ratio,
    estimate_tokens_from_bytes,
)


def _make_valid_task_usage_dict() -> dict:
    """Returns a valid dictionary representation of a TaskUsageRecord."""
    return {
        "schema_version": "1",
        "task_id": "TASK-020",
        "brain_usage": [
            {
                "brain_id": "chatgpt-chat",
                "operation": "TASK_AND_PLAN",
                "round": 1,
                "turns": 1,
                "input_bytes": 10240,
                "output_bytes": 4096,
                "patch_bytes": 2048,
                "full_file_reads": 2,
                "artifact_reads": 3,
                "external_api_calls": 0,
                "tokens": {
                    "source": "REPORTED",
                    "min_tokens": 5000,
                    "max_tokens": 5000,
                    "method": None,
                },
            }
        ],
        "executor_usage": [
            {
                "executor_id": "antigravity",
                "action": "RUN",
                "runs": 1,
                "input_bytes": 20480,
                "output_bytes": 8192,
                "test_runs": 3,
                "external_api_calls": 0,
                "tokens": {
                    "source": "ESTIMATED",
                    "min_tokens": 6000,
                    "max_tokens": 9000,
                    "method": "utf8-bytes-div4-v1",
                },
            }
        ],
        "human_usage": {
            "approvals": 1,
            "manual_sync": 0,
            "manual_pending": 0,
            "manual_watch": 0,
            "human_copy_paste_bytes": None,
        },
        "efficiency": {
            "brain_context_bytes": 10000,
            "useful_context_bytes": 8000,
            "redundant_context_bytes": 1500,
            "escalated_context_bytes": 500,
            "context_efficiency_ratio": 0.8,
            "full_file_read_rate": 0.1,
        },
    }


def test_valid_schema_v1_parse_and_attributes():
    """Valid TaskUsageRecord parses successfully with expected fields and types."""
    data = _make_valid_task_usage_dict()
    record = TaskUsageRecord.from_dict(data)

    assert record.schema_version == "1"
    assert record.task_id == "TASK-020"
    assert len(record.brain_usage) == 1
    assert record.brain_usage[0].brain_id == "chatgpt-chat"
    assert record.brain_usage[0].operation == BrainOperation.TASK_AND_PLAN
    assert record.brain_usage[0].tokens.source == UsageSource.REPORTED
    assert record.brain_usage[0].tokens.min_tokens == 5000
    assert record.brain_usage[0].tokens.max_tokens == 5000

    assert len(record.executor_usage) == 1
    assert record.executor_usage[0].executor_id == "antigravity"
    assert record.executor_usage[0].action == ExecutorAction.RUN
    assert record.executor_usage[0].tokens.source == UsageSource.ESTIMATED
    assert record.executor_usage[0].tokens.min_tokens == 6000
    assert record.executor_usage[0].tokens.max_tokens == 9000

    assert record.human_usage.approvals == 1
    assert record.efficiency.context_efficiency_ratio == 0.8


def test_token_measurement_semantics_reported_estimated_unknown():
    """Validates REPORTED (exact min=max), ESTIMATED (bounded range + method), and UNKNOWN."""
    # REPORTED valid
    m_rep = TokenMeasurement(source=UsageSource.REPORTED, min_tokens=1000, max_tokens=1000)
    assert m_rep.source == UsageSource.REPORTED
    assert m_rep.min_tokens == 1000

    # REPORTED invalid if min != max
    with pytest.raises(ContinuityStateValidationError, match="min_tokens == max_tokens"):
        TokenMeasurement(source=UsageSource.REPORTED, min_tokens=1000, max_tokens=1001)

    # REPORTED invalid if None
    with pytest.raises(ContinuityStateValidationError, match="requires exact min_tokens"):
        TokenMeasurement(source=UsageSource.REPORTED, min_tokens=None, max_tokens=None)

    # ESTIMATED valid
    m_est = TokenMeasurement(
        source=UsageSource.ESTIMATED, min_tokens=1000, max_tokens=2000, method="model-div4"
    )
    assert m_est.source == UsageSource.ESTIMATED
    assert m_est.min_tokens == 1000
    assert m_est.max_tokens == 2000

    # ESTIMATED invalid if min > max
    with pytest.raises(ContinuityStateValidationError, match="cannot exceed max_tokens"):
        TokenMeasurement(
            source=UsageSource.ESTIMATED, min_tokens=2001, max_tokens=2000, method="model-div4"
        )

    # ESTIMATED invalid if method missing
    with pytest.raises(ContinuityStateValidationError, match="requires a non-empty method"):
        TokenMeasurement(source=UsageSource.ESTIMATED, min_tokens=1000, max_tokens=2000, method="")

    # UNKNOWN valid
    m_unk = TokenMeasurement(source=UsageSource.UNKNOWN)
    assert m_unk.source == UsageSource.UNKNOWN
    assert m_unk.min_tokens is None
    assert m_unk.max_tokens is None
    assert m_unk.method is None

    # UNKNOWN invalid if tokens supplied
    with pytest.raises(ContinuityStateValidationError, match="UNKNOWN token measurement must have min_tokens=None"):
        TokenMeasurement(source=UsageSource.UNKNOWN, min_tokens=100)

    # UNKNOWN invalid if method supplied
    with pytest.raises(ContinuityStateValidationError, match="UNKNOWN token measurement must have method=None"):
        TokenMeasurement(source=UsageSource.UNKNOWN, method="some-method")


def test_non_negative_integer_and_bool_rejection():
    """Booleans, negative numbers, and wrong types are strictly rejected across all records."""
    d = _make_valid_task_usage_dict()

    # Bool in int field
    d_bool = _make_valid_task_usage_dict()
    d_bool["brain_usage"][0]["full_file_reads"] = True
    with pytest.raises(ContinuityStateValidationError, match="must be an integer"):
        TaskUsageRecord.from_dict(d_bool)

    # Negative integer
    d_neg = _make_valid_task_usage_dict()
    d_neg["brain_usage"][0]["turns"] = 0  # turns min_val is 1
    with pytest.raises(ContinuityStateValidationError, match="must be >= 1"):
        TaskUsageRecord.from_dict(d_neg)

    d_neg_bytes = _make_valid_task_usage_dict()
    d_neg_bytes["executor_usage"][0]["input_bytes"] = -5
    with pytest.raises(ContinuityStateValidationError, match="must be >= 0"):
        TaskUsageRecord.from_dict(d_neg_bytes)


def test_actor_task_and_action_validation():
    """Actor IDs must be safe lowercase, task IDs must match TASK-\\d+, action must be RUN/FIX."""
    # Invalid actor ID
    d_bad_actor = _make_valid_task_usage_dict()
    d_bad_actor["brain_usage"][0]["brain_id"] = "ChatGPT_Pro"
    with pytest.raises(ContinuityStateValidationError, match="conservative lowercase identifier"):
        TaskUsageRecord.from_dict(d_bad_actor)

    # Invalid task ID
    d_bad_task = _make_valid_task_usage_dict()
    d_bad_task["task_id"] = "task-020"
    with pytest.raises(ContinuityStateValidationError, match="case-sensitive"):
        TaskUsageRecord.from_dict(d_bad_task)

    # Invalid executor action
    d_bad_action = _make_valid_task_usage_dict()
    d_bad_action["executor_usage"][0]["action"] = "DEPLOY"
    with pytest.raises(ContinuityStateValidationError, match="Invalid ExecutorAction"):
        TaskUsageRecord.from_dict(d_bad_action)


def test_unknown_fields_rejection():
    """Unknown fields are rejected fail-closed at all layers."""
    # Root level
    d_root = _make_valid_task_usage_dict()
    d_root["extra"] = "forbidden"
    with pytest.raises(ContinuityStateValidationError, match="Unknown root fields"):
        TaskUsageRecord.from_dict(d_root)

    # Brain record level
    d_brain = _make_valid_task_usage_dict()
    d_brain["brain_usage"][0]["prompt_text"] = "hello"
    with pytest.raises(ContinuityStateValidationError, match="Unknown fields in brain_usage"):
        TaskUsageRecord.from_dict(d_brain)

    # Human record level
    d_human = _make_valid_task_usage_dict()
    d_human["human_usage"]["notes"] = "approved"
    with pytest.raises(ContinuityStateValidationError, match="Unknown fields in human_usage"):
        TaskUsageRecord.from_dict(d_human)


def test_deterministic_canonical_json_and_fingerprint():
    """TaskUsageRecord serializes to stable canonical JSON and produces identical fingerprints."""
    d = _make_valid_task_usage_dict()
    r1 = TaskUsageRecord.from_dict(d)
    json1 = r1.to_canonical_json()
    fp1 = r1.fingerprint()

    r2 = TaskUsageRecord.from_json(json1)
    json2 = r2.to_canonical_json()
    fp2 = r2.fingerprint()

    assert json1 == json2
    assert fp1 == fp2
    assert len(fp1) == 64


def test_estimate_tokens_from_bytes_helper():
    """estimate_tokens_from_bytes produces ESTIMATED tokens with explicit method and never REPORTED."""
    est = estimate_tokens_from_bytes(1000, method="utf8-bytes-div4-v1")
    assert est.source == UsageSource.ESTIMATED
    assert est.min_tokens == 200  # 1000 // 5
    assert est.max_tokens == 334  # (1000 + 2) // 3
    assert est.method == "utf8-bytes-div4-v1"

    # Zero bytes
    est_zero = estimate_tokens_from_bytes(0)
    assert est_zero.source == UsageSource.ESTIMATED
    assert est_zero.min_tokens == 0
    assert est_zero.max_tokens == 0


def test_aggregate_token_ranges_helper():
    """aggregate_token_ranges accurately sums token ranges across heterogeneous measurements."""
    m1 = TokenMeasurement(source=UsageSource.REPORTED, min_tokens=1000, max_tokens=1000)
    m2 = TokenMeasurement(source=UsageSource.ESTIMATED, min_tokens=2000, max_tokens=4000, method="audit")
    m3 = TokenMeasurement(source=UsageSource.UNKNOWN)

    total_min, total_max = aggregate_token_ranges([m1, m2, m3])
    assert total_min == 3000
    assert total_max == 5000

    # All UNKNOWN
    unk_min, unk_max = aggregate_token_ranges([m3, TokenMeasurement(source=UsageSource.UNKNOWN)])
    assert unk_min is None
    assert unk_max is None


def test_calculate_context_efficiency_ratio_helper():
    """calculate_context_efficiency_ratio computes rounded ratio or returns None when unknown."""
    assert calculate_context_efficiency_ratio(8000, 10000) == 0.8
    assert calculate_context_efficiency_ratio(1, 3) == 0.3333
    assert calculate_context_efficiency_ratio(None, 10000) is None
    assert calculate_context_efficiency_ratio(8000, None) is None
    assert calculate_context_efficiency_ratio(0, 0) is None

    # Error when useful > total
    with pytest.raises(ContinuityStateValidationError, match="cannot exceed total_bytes"):
        calculate_context_efficiency_ratio(10001, 10000)


def test_impossible_efficiency_partition_rejection():
    """Efficiency partition components exceeding total brain_context_bytes are rejected."""
    d = _make_valid_task_usage_dict()
    d["efficiency"]["brain_context_bytes"] = 10000
    d["efficiency"]["useful_context_bytes"] = 8000
    d["efficiency"]["redundant_context_bytes"] = 3000  # 8000 + 3000 = 11000 > 10000

    with pytest.raises(ContinuityStateValidationError, match="Impossible efficiency partition"):
        TaskUsageRecord.from_dict(d)


def test_task_019_historical_baseline_artifact_validates_cleanly():
    """The committed .ai/metrics/TASK-019-USAGE.json artifact must parse and remain ESTIMATED."""
    baseline_path = Path(__file__).resolve().parent.parent.parent.parent / ".ai" / "metrics" / "TASK-019-USAGE.json"
    assert baseline_path.exists(), f"Baseline artifact missing at {baseline_path}"

    content = baseline_path.read_text(encoding="utf-8")
    record = TaskUsageRecord.from_json(content)

    assert record.task_id == "TASK-019"
    assert record.schema_version == "1"
    assert len(record.brain_usage) == 3
    for b in record.brain_usage:
        assert b.tokens.source == UsageSource.ESTIMATED
        assert b.tokens.method == "historical-audit-estimate-v1"

    assert len(record.executor_usage) == 2
    for ex in record.executor_usage:
        assert ex.tokens.source == UsageSource.ESTIMATED
        assert ex.tokens.method == "historical-audit-estimate-v1"

    # Verify bounds match TASK-020 spec
    # ChatGPT TASK_AND_PLAN: 22k–30k
    assert record.brain_usage[0].tokens.min_tokens == 22000
    assert record.brain_usage[0].tokens.max_tokens == 30000

    # ChatGPT REVIEW R1: 28k–38k
    assert record.brain_usage[1].tokens.min_tokens == 28000
    assert record.brain_usage[1].tokens.max_tokens == 38000

    # ChatGPT REVIEW R2: 30k–45k
    assert record.brain_usage[2].tokens.min_tokens == 30000
    assert record.brain_usage[2].tokens.max_tokens == 45000

    # Antigravity RUN: 35k–60k
    assert record.executor_usage[0].tokens.min_tokens == 35000
    assert record.executor_usage[0].tokens.max_tokens == 60000

    # Antigravity FIX: 23k–38k
    assert record.executor_usage[1].tokens.min_tokens == 23000
    assert record.executor_usage[1].tokens.max_tokens == 38000


def test_size_limit_16kib_fail_closed():
    """Oversized TaskUsageRecord fails closed in constructor, from_dict, and from_json."""
    d = _make_valid_task_usage_dict()
    many_brain_records = []
    for i in range(250):
        many_brain_records.append({
            "brain_id": "chatgpt-chat",
            "operation": "TASK_AND_PLAN",
            "round": i + 1,
            "turns": 1,
            "tokens": {
                "source": "ESTIMATED",
                "min_tokens": 1000,
                "max_tokens": 2000,
                "method": "long-method-string-padding-for-testing-16kib-limit-overflow",
            },
        })
    d["brain_usage"] = many_brain_records

    with pytest.raises(ContinuityStateValidationError, match="exceeds MAX_SERIALIZED_BYTES"):
        TaskUsageRecord.from_dict(d)

    huge_json = json.dumps(d)
    assert len(huge_json.encode("utf-8")) > 16384
    with pytest.raises(ContinuityStateValidationError, match="exceeds maximum allowable size"):
        TaskUsageRecord.from_json(huge_json)
