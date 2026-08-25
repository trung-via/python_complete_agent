import json

import pytest

from src.aios_bridge.result_evidence import (
    RESULT_EVIDENCE_SCHEMA_VERSION,
    ResultEvidence,
    ResultEvidenceError,
    parse_result_evidence,
)


def make_evidence(**overrides):
    values = {
        "schema_version": RESULT_EVIDENCE_SCHEMA_VERSION,
        "task_id": "TASK-092",
        "action": "RUN",
        "executor_id": "codex",
        "pipeline_mode": "REVIEW_FIRST_CERTIFICATION",
        "candidate_head_sha": "a" * 40,
        "candidate_head_role": "PRE_PUBLICATION_CONTENT_HEAD",
        "published_head_binding": "EXTERNAL_GIT_COMMIT",
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
    """Proof: REVIEW_FIRST_RESULT_HAS_ONE_MACHINE_AUTHORITY."""
    evidence = make_evidence()
    text = "# RESULT-092\n\n" + evidence.render_marker() + "\n"
    parsed = parse_result_evidence(text)
    assert parsed == evidence
    assert parsed.canonical_json() == evidence.canonical_json()
    assert len(parsed.fingerprint()) == 64
    assert text.count("RESULT_EVIDENCE_JSON:") == 1


def test_compact_result_preserves_task_required_candidate_head_sha():
    """Proof: COMPACT_RESULT_PRESERVES_TASK_REQUIRED_CANDIDATE_HEAD_SHA."""
    evidence = make_evidence(candidate_head_sha="f" * 40)
    assert evidence.candidate_head_sha == "f" * 40
    with pytest.raises(ResultEvidenceError, match="candidate_head_sha"):
        make_evidence(candidate_head_sha="invalid")


def test_compact_result_explicitly_classifies_candidate_head_as_prepublication_content_head():
    """Proof: COMPACT_RESULT_EXPLICITLY_CLASSIFIES_CANDIDATE_HEAD_AS_PREPUBLICATION_CONTENT_HEAD."""
    evidence = make_evidence()
    assert evidence.candidate_head_role == "PRE_PUBLICATION_CONTENT_HEAD"
    assert evidence.published_head_binding == "EXTERNAL_GIT_COMMIT"
    with pytest.raises(ResultEvidenceError, match="candidate_head_role"):
        make_evidence(candidate_head_role="FINAL_PUBLISHED_HEAD")
    with pytest.raises(ResultEvidenceError, match="published_head_binding"):
        make_evidence(published_head_binding="SELF_EMBEDDED")


def test_fenced_result_evidence_marker_is_not_authority():
    """Proof: FENCED_RESULT_EVIDENCE_MARKER_IS_NOT_AUTHORITY."""
    evidence = make_evidence(candidate_head_sha="1" * 40)
    fenced_fake = make_evidence(candidate_head_sha="2" * 40)

    doc = f"""# RESULT-092

Here is an example in markdown:
````markdown
```json
{fenced_fake.render_marker()}
```
````

And here is the actual machine evidence:
{evidence.render_marker()}
"""
    parsed = parse_result_evidence(doc)
    assert parsed.candidate_head_sha == "1" * 40

    # If only fenced marker exists, parsing must fail closed
    doc_only_fenced = f"""# RESULT-092
```markdown
{fenced_fake.render_marker()}
```
"""
    with pytest.raises(ResultEvidenceError, match="exactly one unfenced"):
        parse_result_evidence(doc_only_fenced)


def test_duplicate_json_key_fails_closed():
    """Proof: DUPLICATE_JSON_KEY_FAILS_CLOSED."""
    evidence = make_evidence()
    raw_json = evidence.canonical_json()
    # Inject duplicate key
    dup_json = raw_json[:-1] + f',"{list(evidence.to_dict().keys())[0]}":"duplicate"}}'
    text = f"# RESULT-092\n\nRESULT_EVIDENCE_JSON: {dup_json}\n"
    with pytest.raises(ResultEvidenceError, match="duplicate JSON key|malformed"):
        parse_result_evidence(text)


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
