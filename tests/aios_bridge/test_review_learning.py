import pytest

from src.aios_bridge.review_learning import (
    GuardrailPromotionTarget,
    PromotionFindingEvidence,
    ReviewLearningError,
    recommend_guardrail_promotion,
)
from src.aios_bridge.review_pipeline import (
    ChangedPathClass,
    DependencyBlastRadius,
    FindingRecord,
    FindingRegistry,
    FindingStatus,
    ImpactConfidence,
    ReviewEffort,
    RiskEvidence,
    RiskTaskClass,
    transition_registry_finding,
)


def promotion(finding_id, *, finding_class="AUTHORITY_DRIFT", severity="HIGH"):
    return PromotionFindingEvidence(
        finding_id=finding_id,
        normalized_finding_class=finding_class,
        guardrail_key="exact-head-binding",
        severity=severity,
        status=FindingStatus.CLOSED,
        allowed_targets=(GuardrailPromotionTarget.REGRESSION_TEST,),
    )


def risk():
    return RiskEvidence(
        task_class=RiskTaskClass.STANDARD,
        changed_path_classes=(ChangedPathClass.PRODUCT_CODE,),
        dependency_blast_radius=DependencyBlastRadius.LOCAL,
        public_api_or_contract_impact=False,
        authority_or_security_impact=False,
        schema_or_storage_impact=False,
        test_infrastructure_impact=False,
        roadmap_or_control_plane_criticality=False,
        impact_confidence=ImpactConfidence.KNOWN,
    )


def test_low_value_single_finding_not_promoted():
    result = recommend_guardrail_promotion((promotion("F-1", finding_class="NIT"),))
    assert result.target is GuardrailPromotionTarget.NONE
    assert result.repository_mutation_authorized is False
    assert result.authority_expanded is False


def test_recurring_evidence_can_produce_bounded_promotion_candidate():
    result = recommend_guardrail_promotion((promotion("F-1"), promotion("F-2")))
    assert result.target is GuardrailPromotionTarget.REGRESSION_TEST
    assert result.evidence_finding_ids == ("F-1", "F-2")
    assert result.canonical_json() == recommend_guardrail_promotion(
        (promotion("F-2"), promotion("F-1"))
    ).canonical_json()


def test_raw_similarity_without_same_key_and_class_fails_closed():
    second = PromotionFindingEvidence(
        finding_id="F-2",
        normalized_finding_class="AUTHORITY_DRIFT",
        guardrail_key="different-key",
        severity="HIGH",
        status=FindingStatus.CLOSED,
        allowed_targets=(GuardrailPromotionTarget.REGRESSION_TEST,),
    )
    with pytest.raises(ReviewLearningError):
        recommend_guardrail_promotion((promotion("F-1"), second))


def test_finding_registry_exact_head_round_and_transition_binding():
    finding = FindingRecord(
        finding_id="F-1",
        introduced_review_round=1,
        severity="HIGH",
        affected_surfaces=("bridge.py",),
        status=FindingStatus.NEW,
        required_proof_ids=(),
    )
    registry = FindingRegistry(
        finding_records=(finding,),
        review_round=1,
        candidate_head_sha="a" * 40,
        review_effort=ReviewEffort.STANDARD,
        risk_evidence=risk(),
    )
    updated = transition_registry_finding(
        registry,
        "F-1",
        FindingStatus.OPEN,
        candidate_head_sha="b" * 40,
        review_round=2,
    )
    assert updated.candidate_head_sha == "b" * 40
    assert updated.review_round == 2
    assert updated.finding_records[0].status is FindingStatus.OPEN
    assert FindingRegistry.from_dict(updated.to_dict()) == updated

