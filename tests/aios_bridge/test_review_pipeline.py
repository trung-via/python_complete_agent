from dataclasses import FrozenInstanceError

import pytest

from src.aios_bridge.review_pipeline import (
    ChangedPathClass,
    DependencyBlastRadius,
    FindingRecord,
    FindingStatus,
    ImpactConfidence,
    ProofCarryForwardDecision,
    ProofRecord,
    ProofStatus,
    ReviewContractError,
    ReviewEffort,
    ReviewState,
    RiskEvidence,
    RiskTaskClass,
    TaskPipelineMode,
    derive_review_first_final_state,
    evaluate_proof_carry_forward,
    review_state_creates_merge_authority,
    route_review_effort,
    parse_task_pipeline_mode,
    transition_finding_status,
    transition_review_state,
)
from src.aios_bridge.certification_job import CertificationJob, CertificationJobStatus
from src.aios_bridge.validation import ValidationProfile


FP_A = "a" * 64
FP_B = "b" * 64
FP_C = "c" * 64
SHA_A = "a" * 40


def finding(**overrides):
    values = {
        "finding_id": "finding-1",
        "introduced_review_round": 1,
        "severity": "HIGH",
        "affected_surfaces": ("src/one.py", "tests/test_one.py"),
        "status": FindingStatus.NEW,
        "fixed_by_sha": None,
        "required_proof_ids": ("proof-1",),
        "closure_review_round": None,
    }
    values.update(overrides)
    return FindingRecord(**values)


def proof(**overrides):
    values = {
        "proof_id": "proof-1",
        "subject": "review pipeline",
        "subject_fingerprint": FP_A,
        "dependency_fingerprint": FP_B,
        "evidence_fingerprint": FP_C,
        "source_review_round": 1,
        "status": ProofStatus.VALID,
    }
    values.update(overrides)
    return ProofRecord(**values)


def risk(**overrides):
    values = {
        "task_class": RiskTaskClass.STANDARD,
        "changed_path_classes": (ChangedPathClass.PRODUCT_CODE,),
        "dependency_blast_radius": DependencyBlastRadius.BOUNDED,
        "public_api_or_contract_impact": False,
        "authority_or_security_impact": False,
        "schema_or_storage_impact": False,
        "test_infrastructure_impact": False,
        "roadmap_or_control_plane_criticality": False,
        "impact_confidence": ImpactConfidence.KNOWN,
    }
    values.update(overrides)
    return RiskEvidence(**values)


def test_review_state_machine_is_closed_and_semantic_acceptance_is_non_authoritative():
    assert tuple(item.value for item in ReviewState) == (
        "READY_FOR_SEMANTIC_REVIEW",
        "CHANGES_REQUIRED",
        "SEMANTICALLY_ACCEPTED_PENDING_T2",
        "CERTIFICATION_RUNNING",
        "CERTIFIED",
        "FINAL_PASS",
        "SUPERSEDED",
    )
    accepted = transition_review_state(
        ReviewState.READY_FOR_SEMANTIC_REVIEW,
        ReviewState.SEMANTICALLY_ACCEPTED_PENDING_T2,
    )
    assert review_state_creates_merge_authority(accepted) is False
    with pytest.raises(ValueError):
        ReviewState("APPROVED")


def test_final_pass_requires_certified_state_and_superseded_fails_closed():
    with pytest.raises(ReviewContractError, match="invalid review transition"):
        transition_review_state(
            ReviewState.SEMANTICALLY_ACCEPTED_PENDING_T2,
            ReviewState.FINAL_PASS,
        )
    assert transition_review_state(
        ReviewState.CERTIFIED, ReviewState.FINAL_PASS
    ) is ReviewState.FINAL_PASS
    assert review_state_creates_merge_authority(ReviewState.FINAL_PASS) is True
    with pytest.raises(ReviewContractError, match="invalid review transition"):
        transition_review_state(ReviewState.SUPERSEDED, ReviewState.FINAL_PASS)


def test_finding_registry_is_immutable_machine_readable_and_closed():
    record = finding()
    assert FindingRecord.from_dict(record.to_dict()) == record
    assert tuple(item.value for item in FindingStatus) == (
        "NEW",
        "OPEN",
        "FIX_SUBMITTED",
        "VERIFYING",
        "CLOSED",
        "REOPENED",
    )
    with pytest.raises(FrozenInstanceError):
        record.status = FindingStatus.OPEN
    with pytest.raises(ValueError):
        FindingStatus("IGNORED")


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("affected_surfaces", ("src/one.py", "src/one.py"), "duplicate affected surface"),
        ("required_proof_ids", ("proof-1", "proof-1"), "duplicate required proof ID"),
    ),
)
def test_finding_registry_rejects_duplicate_bounded_values(field, value, message):
    with pytest.raises(ReviewContractError, match=message):
        finding(**{field: value})


def test_closed_finding_stays_closed_without_explicit_reopen_evidence():
    closed = finding(
        status=FindingStatus.CLOSED,
        fixed_by_sha=SHA_A,
        closure_review_round=2,
    )
    with pytest.raises(ReviewContractError, match="explicit evidence"):
        transition_finding_status(closed, FindingStatus.REOPENED)
    reopened = transition_finding_status(
        closed, FindingStatus.REOPENED, reopen_evidence=True
    )
    assert reopened.status is FindingStatus.REOPENED
    assert closed.status is FindingStatus.CLOSED


def test_finding_lifecycle_rejects_invalid_status_transition():
    with pytest.raises(ReviewContractError, match="invalid finding transition"):
        transition_finding_status(finding(), FindingStatus.CLOSED)
    verifying = finding(
        status=FindingStatus.VERIFYING,
        fixed_by_sha=SHA_A,
    )
    closed = transition_finding_status(
        verifying, FindingStatus.CLOSED, closure_review_round=3
    )
    assert closed.fixed_by_sha == SHA_A
    assert closed.closure_review_round == 3


def test_verifying_finding_returns_to_open_but_cannot_reopen_directly():
    verifying = finding(status=FindingStatus.VERIFYING)
    assert transition_finding_status(
        verifying, FindingStatus.OPEN
    ).status is FindingStatus.OPEN
    with pytest.raises(ReviewContractError, match="invalid finding transition"):
        transition_finding_status(verifying, FindingStatus.REOPENED)


def test_closing_finding_requires_complete_closure_evidence():
    verifying = finding(status=FindingStatus.VERIFYING)
    with pytest.raises(ReviewContractError, match="requires fixed_by_sha"):
        transition_finding_status(verifying, FindingStatus.CLOSED)
    closed = transition_finding_status(
        verifying,
        FindingStatus.CLOSED,
        fixed_by_sha=SHA_A,
        closure_review_round=2,
    )
    assert closed.status is FindingStatus.CLOSED
    assert closed.fixed_by_sha == SHA_A
    assert closed.closure_review_round == 2


@pytest.mark.parametrize(
    "overrides",
    (
        {"fixed_by_sha": None, "closure_review_round": 2},
        {"fixed_by_sha": SHA_A, "closure_review_round": None},
    ),
)
def test_direct_and_machine_readable_closed_findings_require_both_closure_fields(
    overrides,
):
    with pytest.raises(ReviewContractError, match="closed finding requires"):
        finding(status=FindingStatus.CLOSED, **overrides)

    data = finding().to_dict()
    data.update(status=FindingStatus.CLOSED.value, **overrides)
    with pytest.raises(ReviewContractError, match="closed finding requires"):
        FindingRecord.from_dict(data)


@pytest.mark.parametrize("field", ("affected_surfaces", "required_proof_ids"))
@pytest.mark.parametrize("value", ("one", 1, {"one": "two"}, ("one",)))
def test_finding_machine_readable_sequences_require_exact_lists(field, value):
    data = finding().to_dict()
    data[field] = value
    with pytest.raises(ReviewContractError, match=f"{field} must be an exact list"):
        FindingRecord.from_dict(data)


def test_proof_record_is_immutable_fingerprint_bound_and_machine_readable():
    record = proof()
    assert ProofRecord.from_dict(record.to_dict()) == record
    with pytest.raises(FrozenInstanceError):
        record.status = ProofStatus.INVALIDATED
    with pytest.raises(ReviewContractError, match="64-hex"):
        proof(subject_fingerprint="unknown")


def test_unchanged_valid_proof_carries_forward():
    assert evaluate_proof_carry_forward(
        proof(), FP_A, FP_B
    ) is ProofCarryForwardDecision.CARRY_FORWARD_ALLOWED


def test_changed_subject_or_dependency_invalidates_proof():
    assert evaluate_proof_carry_forward(
        proof(), FP_C, FP_B
    ) is ProofCarryForwardDecision.INVALIDATE
    assert evaluate_proof_carry_forward(
        proof(), FP_A, FP_C
    ) is ProofCarryForwardDecision.INVALIDATE


@pytest.mark.parametrize("status", (ProofStatus.NEW, ProofStatus.INVALIDATED))
def test_new_or_invalidated_proof_cannot_carry_forward(status):
    assert evaluate_proof_carry_forward(
        proof(status=status), FP_A, FP_B
    ) is ProofCarryForwardDecision.CARRY_FORWARD_FORBIDDEN


def test_malformed_current_proof_fingerprint_fails_closed():
    with pytest.raises(ReviewContractError, match="64-hex"):
        evaluate_proof_carry_forward(proof(), "UNKNOWN", FP_B)


def test_risk_review_classes_are_closed_and_router_is_deterministic():
    assert tuple(item.value for item in ReviewEffort) == (
        "FAST",
        "STANDARD",
        "DEEP",
        "CRITICAL_SECOND_REVIEW",
    )
    evidence = risk()
    assert RiskEvidence.from_dict(evidence.to_dict()) == evidence
    assert route_review_effort(evidence) is ReviewEffort.STANDARD
    assert route_review_effort(evidence) is route_review_effort(evidence)


def test_low_bounded_non_critical_risk_can_route_fast():
    evidence = risk(
        task_class=RiskTaskClass.LOW_BOUNDED_NON_CRITICAL,
        changed_path_classes=(ChangedPathClass.TESTS,),
        dependency_blast_radius=DependencyBlastRadius.LOCAL,
    )
    assert route_review_effort(evidence) is ReviewEffort.FAST


@pytest.mark.parametrize(
    "overrides",
    (
        {"authority_or_security_impact": True},
        {"changed_path_classes": (ChangedPathClass.AUTHORITY_OR_SECURITY,)},
    ),
)
def test_authority_or_security_criticality_requires_second_review(overrides):
    assert route_review_effort(risk(**overrides)) is ReviewEffort.CRITICAL_SECOND_REVIEW


def test_unknown_impact_routes_conservatively_without_model_selection():
    evidence = risk(
        task_class=RiskTaskClass.HIGH_IMPACT,
        dependency_blast_radius=DependencyBlastRadius.UNKNOWN,
        impact_confidence=ImpactConfidence.UNKNOWN,
    )
    assert route_review_effort(evidence) is ReviewEffort.DEEP


def test_risk_evidence_is_finite_and_rejects_duplicate_path_classes():
    with pytest.raises(ReviewContractError, match="duplicate changed path class"):
        risk(
            changed_path_classes=(
                ChangedPathClass.TESTS,
                ChangedPathClass.TESTS,
            )
        )


def test_pipeline_mode_missing_is_legacy_and_exact_opt_in_activates():
    assert parse_task_pipeline_mode("# TASK-091\n") is (
        TaskPipelineMode.LEGACY_CERTIFY_ON_PUBLISH
    )
    assert parse_task_pipeline_mode(
        "# TASK-091\nREVIEW_PIPELINE_MODE: REVIEW_FIRST_CERTIFICATION\n",
        task_id="TASK-091",
    ) is TaskPipelineMode.REVIEW_FIRST_CERTIFICATION


@pytest.mark.parametrize(
    "content",
    (
        "REVIEW_PIPELINE_MODE: REVIEW_FIRST_CERTIFICATION\n"
        "REVIEW_PIPELINE_MODE: REVIEW_FIRST_CERTIFICATION\n",
        "REVIEW_PIPELINE_MODE: FUTURE_MODE\n",
        "REVIEW_PIPELINE_MODE: LEGACY_CERTIFY_ON_PUBLISH\n",
    ),
)
def test_pipeline_mode_duplicate_or_unknown_fails_closed(content):
    with pytest.raises(ReviewContractError):
        parse_task_pipeline_mode(content, task_id="TASK-091")


def test_fenced_pipeline_example_does_not_activate_and_task_090_stays_legacy():
    fenced = """# TASK-090
```text
REVIEW_PIPELINE_MODE: REVIEW_FIRST_CERTIFICATION
```
"""
    assert parse_task_pipeline_mode(fenced, task_id="TASK-090") is (
        TaskPipelineMode.LEGACY_CERTIFY_ON_PUBLISH
    )
    assert parse_task_pipeline_mode(
        "REVIEW_PIPELINE_MODE: REVIEW_FIRST_CERTIFICATION\n",
        task_id="TASK-090",
    ) is TaskPipelineMode.LEGACY_CERTIFY_ON_PUBLISH


def test_final_pass_requires_exact_certification_pass_binding():
    passed = CertificationJob(
        job_id="cert-task-091-a",
        task_id="TASK-091",
        candidate_head_sha=SHA_A,
        candidate_fingerprint=FP_A,
        validation_profile=ValidationProfile.CONTROL_PLANE_STRICT_COMPAT,
        certification_command_identity="sha256:" + "d" * 64,
        status=CertificationJobStatus.CERTIFICATION_PASS,
        started_at="2026-08-25T00:00:00Z",
        completed_at="2026-08-25T00:00:01Z",
        terminal_result_digest="e" * 64,
        aios_managed_t2_execution_count=1,
        t2_exit_status=0,
        t2_succeeded=True,
        duration_seconds=1.0,
    )
    kwargs = {
        "task_id": "TASK-091",
        "review_state": ReviewState.SEMANTICALLY_ACCEPTED_PENDING_T2,
        "approved": True,
        "auto_merge_eligible": True,
        "certification_job": passed,
        "candidate_head_sha": SHA_A,
        "candidate_fingerprint": FP_A,
        "validation_profile": ValidationProfile.CONTROL_PLANE_STRICT_COMPAT,
        "certification_command_identity": "sha256:" + "d" * 64,
    }
    assert derive_review_first_final_state(**kwargs) is ReviewState.FINAL_PASS
    with pytest.raises(ReviewContractError, match="identity mismatch"):
        derive_review_first_final_state(
            **{**kwargs, "candidate_fingerprint": FP_B}
        )
    with pytest.raises(ReviewContractError, match="requires APPROVED YES"):
        derive_review_first_final_state(**{**kwargs, "approved": False})
