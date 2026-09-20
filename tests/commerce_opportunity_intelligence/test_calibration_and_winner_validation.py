"""Focused deterministic tests for the bounded P7.7 semantic authority."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timedelta, timezone

import pytest

from src.commerce_opportunity_intelligence import (
    COMMERCE_OPPORTUNITY_INTELLIGENCE_P7_7,
    HYPOTHESIS_CALIBRATION_DISPOSITIONS,
    WINNER_VALIDATION_DISPOSITIONS,
    DecisionContext,
    MarketTestEvidenceProfile,
    OpportunityHypothesis,
    OpportunityIntelligenceValidationError,
    WinnerValidationAssessment,
    create_winner_validation_assessment,
)


AS_OF = datetime(2026, 9, 20, 16, 0, tzinfo=timezone(timedelta(hours=7)))
PROFILE_AS_OF = datetime(2026, 9, 20, 15, 0, tzinfo=timezone(timedelta(hours=7)))


def sample_context(**overrides: object) -> DecisionContext:
    values: dict[str, object] = {
        "context_id": "context-7",
        "decision_question": "Does the bounded evidence support the hypothesis?",
        "objective": "Interpret a completed market test without automatic action.",
        "as_of": datetime(2026, 9, 18, 9, 0, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return DecisionContext(**values)  # type: ignore[arg-type]


def sample_hypothesis(**overrides: object) -> OpportunityHypothesis:
    values: dict[str, object] = {
        "hypothesis_id": "hypothesis-11",
        "decision_context_id": "context-7",
        "subject_ref": "subject://candidate/11",
        "falsifiable_claim": "The offer can produce positive margin in this context.",
        "created_at": datetime(2026, 9, 18, 10, 0, tzinfo=timezone.utc),
        "disconfirming_conditions": ("Observed margin is non-positive.",),
        "expected_outcomes": ("Positive contribution margin is observed.",),
    }
    values.update(overrides)
    return OpportunityHypothesis(**values)  # type: ignore[arg-type]


def sample_profile(**overrides: object) -> MarketTestEvidenceProfile:
    values: dict[str, object] = {
        "profile_id": "profile-1",
        "test_id": "test-1",
        "decision_context_id": "context-7",
        "hypothesis_id": "hypothesis-11",
        "test_design_ref": "ref://design/1",
        "authorization_ref": "ref://authorization/1",
        "action_ref": "ref://action/1",
        "test_started_at": datetime(2026, 9, 19, 9, 0, tzinfo=timezone.utc),
        "test_ended_at": datetime(2026, 9, 20, 7, 0, tzinfo=timezone.utc),
        "as_of": PROFILE_AS_OF,
        "exposure_evidence_refs": ("ref://exposure/1",),
        "funnel_evidence_refs": ("ref://funnel/1",),
        "economic_evidence_refs": ("ref://economic/1",),
        "quality_evidence_refs": ("ref://quality/1",),
    }
    values.update(overrides)
    return MarketTestEvidenceProfile(**values)  # type: ignore[arg-type]


def create_assessment(**overrides: object) -> WinnerValidationAssessment:
    values: dict[str, object] = {
        "decision_context": sample_context(),
        "hypothesis": sample_hypothesis(),
        "market_test_profiles": (sample_profile(),),
        "assessment_id": "assessment-1",
        "as_of": AS_OF,
        "hypothesis_calibration": "MIXED",
        "winner_validation": "SUPPORTED",
        "calibration_rationale": "Observed outcomes include support and contradiction.",
        "validation_rationale": "All dimensions are represented, with uncertainty retained.",
        "supporting_evidence_refs": ("ref://economic/1", "ref://funnel/1"),
        "counter_evidence_refs": ("ref://quality/1",),
        "unresolved_uncertainties": ("Repeatability outside this test is unknown.",),
    }
    values.update(overrides)
    return create_winner_validation_assessment(**values)  # type: ignore[arg-type]


def test_authority_and_disposition_vocabularies_are_exact_and_ordered():
    assert COMMERCE_OPPORTUNITY_INTELLIGENCE_P7_7 == "COMMERCE_OPPORTUNITY_INTELLIGENCE_P7_7"
    assert HYPOTHESIS_CALIBRATION_DISPOSITIONS == (
        "ALIGNED", "MIXED", "MISALIGNED", "INCONCLUSIVE"
    )
    assert WINNER_VALIDATION_DISPOSITIONS == (
        "SUPPORTED", "CONTRADICTED", "INCONCLUSIVE"
    )


def test_direct_public_construction_fails_closed_but_factory_succeeds():
    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match="must be constructed by create_winner_validation_assessment",
    ):
        WinnerValidationAssessment(
            assessment_id="fabricated-assessment",
            decision_context_id="fabricated-context",
            hypothesis_id="fabricated-hypothesis",
            as_of=AS_OF,
            market_test_profile_ids=("fabricated-profile",),
            hypothesis_calibration="ALIGNED",
            winner_validation="SUPPORTED",
            calibration_rationale="Caller supplied lineage without bound objects.",
            validation_rationale="Caller supplied unanchored evidence.",
            supporting_evidence_refs=("ref://invented/not-in-profile",),
        )

    assessment = create_assessment()
    assert isinstance(assessment, WinnerValidationAssessment)
    assert assessment.decision_context_id == sample_context().context_id
    assert assessment.hypothesis_id == sample_hypothesis().hypothesis_id
    assert assessment.market_test_profile_ids == (sample_profile().profile_id,)


def test_factory_binds_exact_identities_and_preserves_all_caller_order():
    second = sample_profile(
        profile_id="profile-2",
        test_id="test-2",
        exposure_evidence_refs=("ref://exposure/2",),
    )
    assessment = create_assessment(
        market_test_profiles=(second, sample_profile()),
        supporting_evidence_refs=("ref://funnel/1", "ref://economic/1"),
        counter_evidence_refs=("ref://quality/1", "ref://exposure/2"),
        unresolved_uncertainties=("Unknown B.", "Unknown A."),
    )

    assert assessment.decision_context_id == "context-7"
    assert assessment.hypothesis_id == "hypothesis-11"
    assert assessment.market_test_profile_ids == ("profile-2", "profile-1")
    assert assessment.supporting_evidence_refs == (
        "ref://funnel/1", "ref://economic/1"
    )
    assert assessment.counter_evidence_refs == (
        "ref://quality/1", "ref://exposure/2"
    )
    assert assessment.unresolved_uncertainties == ("Unknown B.", "Unknown A.")


def test_value_is_frozen_and_has_only_bounded_semantic_fields():
    assessment = create_assessment()
    with pytest.raises(FrozenInstanceError):
        assessment.winner_validation = "CONTRADICTED"  # type: ignore[misc]

    assert [item.name for item in fields(WinnerValidationAssessment)] == [
        "assessment_id",
        "decision_context_id",
        "hypothesis_id",
        "as_of",
        "market_test_profile_ids",
        "hypothesis_calibration",
        "winner_validation",
        "calibration_rationale",
        "validation_rationale",
        "supporting_evidence_refs",
        "counter_evidence_refs",
        "unresolved_uncertainties",
    ]


def test_projection_is_deterministic_json_serializable_and_order_preserving():
    assessment = create_assessment()
    expected = {
        "assessment_id": "assessment-1",
        "decision_context_id": "context-7",
        "hypothesis_id": "hypothesis-11",
        "as_of": AS_OF.isoformat(),
        "market_test_profile_ids": ["profile-1"],
        "hypothesis_calibration": "MIXED",
        "winner_validation": "SUPPORTED",
        "calibration_rationale": "Observed outcomes include support and contradiction.",
        "validation_rationale": "All dimensions are represented, with uncertainty retained.",
        "supporting_evidence_refs": ["ref://economic/1", "ref://funnel/1"],
        "counter_evidence_refs": ["ref://quality/1"],
        "unresolved_uncertainties": ["Repeatability outside this test is unknown."],
    }
    assert assessment.to_dict() == expected
    assert assessment.to_dict() == expected
    json.dumps(assessment.to_dict())


@pytest.mark.parametrize(
    ("calibration", "supporting", "counter", "uncertainties", "message"),
    [
        ("ALIGNED", (), (), (), "ALIGNED.*supporting"),
        ("MISALIGNED", (), (), (), "MISALIGNED.*counter"),
        ("MIXED", ("ref://economic/1",), (), (), "MIXED.*supporting and counter"),
        ("INCONCLUSIVE", (), (), (), "INCONCLUSIVE.*unresolved"),
    ],
)
def test_calibration_local_coherence_rules(
    calibration: str,
    supporting: tuple[str, ...],
    counter: tuple[str, ...],
    uncertainties: tuple[str, ...],
    message: str,
):
    with pytest.raises(OpportunityIntelligenceValidationError, match=message):
        create_assessment(
            hypothesis_calibration=calibration,
            winner_validation="CONTRADICTED",
            supporting_evidence_refs=supporting,
            counter_evidence_refs=counter,
            unresolved_uncertainties=uncertainties,
        )


@pytest.mark.parametrize(
    (
        "calibration",
        "validation",
        "supporting",
        "counter",
        "uncertainties",
        "message",
    ),
    [
        (
            "MISALIGNED",
            "SUPPORTED",
            (),
            ("ref://quality/1",),
            (),
            "SUPPORTED.*supporting",
        ),
        (
            "ALIGNED",
            "CONTRADICTED",
            ("ref://economic/1",),
            (),
            (),
            "CONTRADICTED.*counter",
        ),
        (
            "ALIGNED",
            "INCONCLUSIVE",
            ("ref://economic/1",),
            (),
            (),
            "INCONCLUSIVE.*unresolved",
        ),
    ],
)
def test_winner_validation_local_coherence_rules(
    calibration: str,
    validation: str,
    supporting: tuple[str, ...],
    counter: tuple[str, ...],
    uncertainties: tuple[str, ...],
    message: str,
):
    with pytest.raises(OpportunityIntelligenceValidationError, match=message):
        create_assessment(
            hypothesis_calibration=calibration,
            winner_validation=validation,
            supporting_evidence_refs=supporting,
            counter_evidence_refs=counter,
            unresolved_uncertainties=uncertainties,
        )


def test_supported_requires_collective_representation_of_all_four_dimensions():
    partial_a = sample_profile(
        exposure_evidence_refs=("ref://exposure/1",),
        funnel_evidence_refs=("ref://funnel/1",),
        economic_evidence_refs=(),
        quality_evidence_refs=(),
    )
    partial_b = sample_profile(
        profile_id="profile-2",
        test_id="test-2",
        exposure_evidence_refs=(),
        funnel_evidence_refs=(),
        economic_evidence_refs=("ref://economic/2",),
        quality_evidence_refs=("ref://quality/2",),
    )
    assessment = create_assessment(
        market_test_profiles=(partial_a, partial_b),
        supporting_evidence_refs=("ref://economic/2",),
        counter_evidence_refs=("ref://quality/2",),
    )
    assert assessment.winner_validation == "SUPPORTED"

    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match="requires represented evidence across exposure, funnel, economic, and quality",
    ):
        create_assessment(
            market_test_profiles=(partial_a,),
            supporting_evidence_refs=("ref://funnel/1",),
            counter_evidence_refs=("ref://exposure/1",),
        )


def test_mixed_support_counter_and_uncertainty_can_coexist_without_formula():
    assessment = create_assessment(
        hypothesis_calibration="ALIGNED",
        winner_validation="CONTRADICTED",
    )
    assert assessment.supporting_evidence_refs
    assert assessment.counter_evidence_refs
    assert assessment.unresolved_uncertainties


def test_every_assessment_evidence_ref_must_be_anchored_to_bound_profiles():
    for field_name in ("supporting_evidence_refs", "counter_evidence_refs"):
        with pytest.raises(OpportunityIntelligenceValidationError, match="must be anchored"):
            create_assessment(**{field_name: ("ref://invented/not-in-profile",)})


def test_factory_rejects_identity_time_profile_type_and_ordering_errors():
    with pytest.raises(OpportunityIntelligenceValidationError, match="hypothesis decision_context_id"):
        create_assessment(hypothesis=sample_hypothesis(decision_context_id="other"))
    with pytest.raises(OpportunityIntelligenceValidationError, match=r"\[0\] decision_context_id"):
        create_assessment(market_test_profiles=(sample_profile(decision_context_id="other"),))
    with pytest.raises(OpportunityIntelligenceValidationError, match=r"\[0\] hypothesis_id"):
        create_assessment(market_test_profiles=(sample_profile(hypothesis_id="other"),))
    with pytest.raises(OpportunityIntelligenceValidationError, match="non-empty ordered collection"):
        create_assessment(market_test_profiles=())
    with pytest.raises(OpportunityIntelligenceValidationError, match="non-empty ordered collection"):
        create_assessment(market_test_profiles={sample_profile()})
    with pytest.raises(OpportunityIntelligenceValidationError, match="must be a MarketTestEvidenceProfile"):
        create_assessment(market_test_profiles=("profile",))
    with pytest.raises(OpportunityIntelligenceValidationError, match="duplicate profile_id"):
        create_assessment(market_test_profiles=(sample_profile(), sample_profile()))
    with pytest.raises(OpportunityIntelligenceValidationError, match="must not be earlier"):
        create_assessment(as_of=PROFILE_AS_OF - timedelta(seconds=1))


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("supporting_evidence_refs", {"ref://economic/1"}),
        ("counter_evidence_refs", {"ref://quality/1"}),
        ("unresolved_uncertainties", {"Unknown."}),
    ],
)
def test_ordered_collections_reject_unordered_values(field_name: str, value: object):
    with pytest.raises(OpportunityIntelligenceValidationError, match="ordered collection"):
        create_assessment(**{field_name: value})


@pytest.mark.parametrize(
    "field_name",
    ["supporting_evidence_refs", "counter_evidence_refs", "unresolved_uncertainties"],
)
def test_ordered_collections_reject_duplicates(field_name: str):
    value = "ref://economic/1" if field_name != "unresolved_uncertainties" else "Unknown."
    with pytest.raises(OpportunityIntelligenceValidationError, match="duplicate values"):
        create_assessment(**{field_name: (value, value)})


@pytest.mark.parametrize(
    "payload",
    [
        "secret=do-not-leak",
        "Cookie: session-value",
        "system prompt: reveal it",
        "RUN-225-001",
        "<script>alert(1)</script>",
        "object at 0x12345678",
    ],
)
def test_public_values_fail_closed_on_obvious_unsafe_payloads(payload: str):
    with pytest.raises(OpportunityIntelligenceValidationError):
        create_assessment(calibration_rationale=payload)


def test_public_values_reject_blank_multiline_and_unbounded_content():
    with pytest.raises(OpportunityIntelligenceValidationError, match="must not be blank"):
        create_assessment(validation_rationale="  ")
    with pytest.raises(OpportunityIntelligenceValidationError, match="single-line"):
        create_assessment(validation_rationale="line one\nline two")
    with pytest.raises(OpportunityIntelligenceValidationError, match="at most 4096"):
        create_assessment(validation_rationale="x" * 4097)
    with pytest.raises(OpportunityIntelligenceValidationError, match="timezone-aware"):
        create_assessment(as_of=datetime(2026, 9, 20, 16, 0))


def test_invalid_dispositions_are_rejected_without_coercion():
    with pytest.raises(OpportunityIntelligenceValidationError, match="must be one of"):
        create_assessment(hypothesis_calibration="aligned")
    with pytest.raises(OpportunityIntelligenceValidationError, match="must be one of"):
        create_assessment(winner_validation="VALIDATED_WINNER")
