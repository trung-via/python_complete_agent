import json

import pytest

from src.aios_bridge.result_evidence import (
    ResultEvidence,
    ResultEvidenceError,
    parse_result_evidence,
)


def make_evidence(**overrides):
    values = {
        "schema_version": "1",
        "task_id": "TASK-092",
        "action": "RUN",
        "executor_id": "codex",
        "pipeline_mode": "REVIEW_FIRST_CERTIFICATION",
        "candidate_head_sha": "a" * 40,
        "base_main_sha": "b" * 40,
        "validation_profile": "CONTROL_PLANE_STRICT_COMPAT",
        "full_canonical_owner": "CERTIFICATION_BOUNDARY",
        "candidate_stage_aios_managed_t2_execution_count": 0,
        "certification_deferred": True,
        "semantic_review_required": True,
        "targeted_test_status": "PASS",
        "publication_trust_status": "VERIFIED",
        "transport_status": "COMPLETED",
        "actual_changed_paths": ("bridge.py", "src/aios_bridge/result_evidence.py"),
    }
    values.update(overrides)
    return ResultEvidence(**values)


def test_compact_result_canonical_round_trip_and_single_source():
    evidence = make_evidence()
    text = "# RESULT-092\n\n" + evidence.render_marker() + "\n"
    parsed = parse_result_evidence(text)
    assert parsed == evidence
    assert parsed.canonical_json() == evidence.canonical_json()
    assert len(parsed.fingerprint()) == 64
    assert text.count("RESULT_EVIDENCE_JSON:") == 1


def test_compact_result_duplicate_or_unknown_field_fails_closed():
    evidence = make_evidence()
    marker = evidence.render_marker()
    with pytest.raises(ResultEvidenceError):
        parse_result_evidence(marker + "\n" + marker)
    data = evidence.to_dict()
    data["unknown"] = True
    with pytest.raises(ResultEvidenceError):
        ResultEvidence.from_dict(data)


def test_compact_result_contradictory_t2_facts_fail_closed():
    with pytest.raises(ResultEvidenceError):
        make_evidence(candidate_stage_aios_managed_t2_execution_count=1)
    with pytest.raises(ResultEvidenceError):
        make_evidence(certification_deferred=False)


def test_compact_result_rejects_raw_log_or_reasoning_fields():
    with pytest.raises(ResultEvidenceError):
        make_evidence(review_risk_evidence={"raw_stdout": "pytest output"})
    with pytest.raises(ResultEvidenceError):
        make_evidence(slice_c_impact_evidence={"model_reasoning": "hidden"})


def test_canonical_json_is_compact_and_sorted():
    encoded = make_evidence().canonical_json()
    assert encoded == json.dumps(json.loads(encoded), sort_keys=True, separators=(",", ":"))

