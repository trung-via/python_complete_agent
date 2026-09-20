"""Focused deterministic tests for the bounded P7.5 semantic authority."""

from __future__ import annotations

import ast
import json
from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.commerce_opportunity_intelligence import (
    COMMERCE_OPPORTUNITY_INTELLIGENCE_P7_5,
    TIKTOK_AFFILIATE_EVIDENCE_DIMENSIONS,
    VALUE_OF_INFORMATION_DISPOSITIONS,
    DecisionContext,
    OpportunityHypothesis,
    OpportunityIntelligenceValidationError,
    TikTokAffiliateEvidenceProfile,
    ValueOfInformationInquiry,
    ValueOfInformationPlan,
    create_value_of_information_plan,
)


AS_OF = datetime(2026, 9, 16, 8, 30, tzinfo=timezone(timedelta(hours=7)))
CREATED_AT = datetime(2026, 9, 16, 9, 45, tzinfo=timezone.utc)


def sample_context(**overrides: object) -> DecisionContext:
    values: dict[str, object] = {
        "context_id": "decision-context-7",
        "decision_question": "Should this subject receive deeper opportunity research?",
        "objective": "Identify a bounded affiliate opportunity worth testing.",
        "as_of": AS_OF,
    }
    values.update(overrides)
    return DecisionContext(**values)  # type: ignore[arg-type]


def sample_hypothesis(**overrides: object) -> OpportunityHypothesis:
    values: dict[str, object] = {
        "hypothesis_id": "hypothesis-11",
        "decision_context_id": "decision-context-7",
        "subject_ref": "opaque://candidate/not-validated?source=x#variant-y",
        "falsifiable_claim": (
            "The subject can produce positive contribution margin in the stated context."
        ),
        "created_at": CREATED_AT,
        "assumptions": ("The supplied commission terms remain available.",),
        "supporting_evidence_refs": ("evidence:external:2", "evidence:external:1"),
        "counter_evidence_refs": ("evidence:external:9",),
        "important_unknowns": ("Audience conversion rate is unknown.",),
        "disconfirming_conditions": (
            "Observed contribution margin is non-positive at the bounded exposure.",
        ),
        "expected_outcomes": ("A measurable positive contribution margin.",),
    }
    values.update(overrides)
    return OpportunityHypothesis(**values)  # type: ignore[arg-type]


def sample_profile(**overrides: object) -> TikTokAffiliateEvidenceProfile:
    values: dict[str, object] = {
        "profile_id": "profile-tiktok-101",
        "decision_context_id": "decision-context-7",
        "hypothesis_id": "hypothesis-11",
        "as_of": AS_OF,
        "affiliate_economics": ("ref://evidence/economics/1",),
        "market_traction": ("ref://evidence/traction/1", "ref://evidence/traction/2"),
        "creator_ecosystem": ("ref://evidence/creators/1",),
        "content_activity": ("ref://evidence/content/1",),
        "audience_channel_fit": ("ref://evidence/audience/1",),
        "competition_saturation": (),
    }
    values.update(overrides)
    return TikTokAffiliateEvidenceProfile(**values)  # type: ignore[arg-type]


def sample_inquiry(**overrides: object) -> ValueOfInformationInquiry:
    values: dict[str, object] = {
        "inquiry_id": "inquiry-1",
        "evidence_dimension": "affiliate_economics",
        "information_question": "What is the net affiliate commission rate and payout reliability?",
        "explanation": "Low commission rate would make positive contribution margin impossible.",
        "disposition": "CONTINUE",
        "rationale": "Commission terms are critical to unit economics.",
        "expected_decision_impact": "High: would invert entry decision if below 10%.",
        "uncertainty_reduction": "Substantial: resolves uncertainty about net margin.",
        "cost": "Low: public seller program terms inspection.",
        "latency": "Minutes: immediate inspection.",
        "access_risk": "Minimal: publicly listed creator program terms.",
        "fragility": "Low: terms rarely fluctuate intra-day.",
        "reliability": "High: verified seller commission schedule.",
        "opportunity_cost": "Negligible: immediate check before creator outreach.",
        "decision_deadline": "Before outreach campaign launch.",
    }
    values.update(overrides)
    return ValueOfInformationInquiry(**values)  # type: ignore[arg-type]


def sample_plan(**overrides: object) -> ValueOfInformationPlan:
    values: dict[str, object] = {
        "plan_id": "plan-voi-101",
        "decision_context_id": "decision-context-7",
        "hypothesis_id": "hypothesis-11",
        "profile_id": "profile-tiktok-101",
        "as_of": AS_OF,
        "inquiries": (sample_inquiry(),),
        "disposition": "CONTINUE",
        "rationale": "Key unit economics require resolution before further commitment.",
    }
    values.update(overrides)
    return ValueOfInformationPlan(**values)  # type: ignore[arg-type]


def test_authority_identifier_and_ordered_dispositions():
    assert (
        COMMERCE_OPPORTUNITY_INTELLIGENCE_P7_5
        == "COMMERCE_OPPORTUNITY_INTELLIGENCE_P7_5"
    )
    assert VALUE_OF_INFORMATION_DISPOSITIONS == (
        "CONTINUE",
        "DEFER",
        "STOP",
    )


def test_valid_inquiry_preserves_caller_values_and_nine_considerations():
    inquiry = sample_inquiry(
        inquiry_id="inq-custom",
        evidence_dimension="creator_ecosystem",
        information_question="How many active creators post videos for this product?",
        explanation="Creator density determines whether organic reach is viable.",
        disposition="DEFER",
        rationale="Creator discovery is expensive; check economics first.",
        expected_decision_impact="Moderate: indicates organic reach viability.",
        uncertainty_reduction="Moderate: clarifies creator supply.",
        cost="Medium: requires sampling recent posts.",
        latency="Hours: batch query.",
        access_risk="Low: public feed.",
        fragility="Medium: creator churn is frequent.",
        reliability="Medium: estimated from recent 30-day posts.",
        opportunity_cost="Moderate: delays decision by half day.",
        decision_deadline="2026-09-25T12:00:00+07:00",
    )

    assert inquiry.inquiry_id == "inq-custom"
    assert inquiry.evidence_dimension == "creator_ecosystem"
    assert inquiry.information_question == (
        "How many active creators post videos for this product?"
    )
    assert inquiry.explanation == (
        "Creator density determines whether organic reach is viable."
    )
    assert inquiry.decision_relevance == inquiry.explanation
    assert inquiry.disposition == "DEFER"
    assert inquiry.rationale == "Creator discovery is expensive; check economics first."
    assert inquiry.expected_decision_impact == "Moderate: indicates organic reach viability."
    assert inquiry.uncertainty_reduction == "Moderate: clarifies creator supply."
    assert inquiry.cost == "Medium: requires sampling recent posts."
    assert inquiry.latency == "Hours: batch query."
    assert inquiry.access_risk == "Low: public feed."
    assert inquiry.fragility == "Medium: creator churn is frequent."
    assert inquiry.reliability == "Medium: estimated from recent 30-day posts."
    assert inquiry.opportunity_cost == "Moderate: delays decision by half day."
    assert inquiry.decision_deadline == "2026-09-25T12:00:00+07:00"


def test_inquiry_accepts_timezone_aware_datetime_for_deadline():
    deadline = AS_OF + timedelta(days=3)
    inquiry = sample_inquiry(decision_deadline=deadline)
    assert inquiry.decision_deadline == deadline.isoformat()


def test_valid_plan_preserves_caller_values_and_order():
    inq1 = sample_inquiry(inquiry_id="inq-1", disposition="CONTINUE")
    inq2 = sample_inquiry(
        inquiry_id="inq-2",
        evidence_dimension="market_traction",
        disposition="DEFER",
    )
    plan = sample_plan(inquiries=[inq1, inq2], disposition="CONTINUE")

    assert plan.plan_id == "plan-voi-101"
    assert plan.decision_context_id == "decision-context-7"
    assert plan.hypothesis_id == "hypothesis-11"
    assert plan.profile_id == "profile-tiktok-101"
    assert plan.as_of is AS_OF
    assert plan.inquiries == (inq1, inq2)
    assert plan.disposition == "CONTINUE"
    assert plan.rationale == (
        "Key unit economics require resolution before further commitment."
    )


def test_plan_helpers_by_disposition_and_dimension():
    inq_cont = sample_inquiry(
        inquiry_id="inq-cont",
        evidence_dimension="affiliate_economics",
        disposition="CONTINUE",
    )
    inq_def = sample_inquiry(
        inquiry_id="inq-def",
        evidence_dimension="creator_ecosystem",
        disposition="DEFER",
    )
    inq_stop = sample_inquiry(
        inquiry_id="inq-stop",
        evidence_dimension="competition_saturation",
        disposition="STOP",
    )

    plan = sample_plan(
        inquiries=[inq_cont, inq_def, inq_stop],
        disposition="CONTINUE",
    )

    assert plan.inquiries_by_disposition("CONTINUE") == (inq_cont,)
    assert plan.inquiries_by_disposition("DEFER") == (inq_def,)
    assert plan.inquiries_by_disposition("STOP") == (inq_stop,)
    assert plan.inquiries_by_dimension("affiliate_economics") == (inq_cont,)
    assert plan.inquiries_by_dimension("creator_ecosystem") == (inq_def,)
    assert plan.inquiries_by_dimension("competition_saturation") == (inq_stop,)
    assert plan.inquiries_by_dimension("market_traction") == ()


def test_empty_inquiries_allowed_only_with_overall_stop():
    plan = sample_plan(
        inquiries=(),
        disposition="STOP",
        rationale="No further inquiries justified under current market signals.",
    )
    assert plan.inquiries == ()
    assert plan.disposition == "STOP"

    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match="empty inquiry sets are allowed only with overall STOP",
    ):
        sample_plan(
            inquiries=(),
            disposition="CONTINUE",
            rationale="Cannot continue with empty inquiries.",
        )

    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match="empty inquiry sets are allowed only with overall STOP",
    ):
        sample_plan(
            inquiries=(),
            disposition="DEFER",
            rationale="Cannot defer with empty inquiries.",
        )


def test_coherence_overall_continue_requires_at_least_one_continue_inquiry():
    inq_defer = sample_inquiry(disposition="DEFER")
    inq_stop = sample_inquiry(inquiry_id="inq-2", disposition="STOP")

    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match="overall CONTINUE requires at least one inquiry with CONTINUE",
    ):
        sample_plan(
            inquiries=[inq_defer, inq_stop],
            disposition="CONTINUE",
            rationale="Invalid: no inquiry has CONTINUE.",
        )

    inq_continue = sample_inquiry(inquiry_id="inq-3", disposition="CONTINUE")
    valid_plan = sample_plan(
        inquiries=[inq_defer, inq_continue],
        disposition="CONTINUE",
        rationale="Valid: at least one inquiry has CONTINUE.",
    )
    assert valid_plan.disposition == "CONTINUE"


def test_coherence_overall_stop_forbids_continue_inquiry():
    inq_continue = sample_inquiry(disposition="CONTINUE")
    inq_stop = sample_inquiry(inquiry_id="inq-2", disposition="STOP")

    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match="overall STOP must contain no CONTINUE inquiry",
    ):
        sample_plan(
            inquiries=[inq_continue, inq_stop],
            disposition="STOP",
            rationale="Invalid: overall STOP cannot contain CONTINUE inquiry.",
        )

    valid_stop_plan = sample_plan(
        inquiries=[inq_stop],
        disposition="STOP",
        rationale="Valid: all inquiries are STOP/DEFER.",
    )
    assert valid_stop_plan.disposition == "STOP"


def test_coherence_overall_defer_requires_at_least_one_defer_and_no_continue():
    inq_continue = sample_inquiry(disposition="CONTINUE")
    inq_defer = sample_inquiry(inquiry_id="inq-2", disposition="DEFER")
    inq_stop = sample_inquiry(inquiry_id="inq-3", disposition="STOP")

    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match="overall DEFER must contain no CONTINUE inquiry",
    ):
        sample_plan(
            inquiries=[inq_continue, inq_defer],
            disposition="DEFER",
            rationale="Invalid: overall DEFER cannot contain CONTINUE inquiry.",
        )

    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match="overall DEFER requires at least one inquiry with DEFER",
    ):
        sample_plan(
            inquiries=[inq_stop],
            disposition="DEFER",
            rationale="Invalid: overall DEFER requires at least one DEFER inquiry.",
        )

    valid_defer_plan = sample_plan(
        inquiries=[inq_defer, inq_stop],
        disposition="DEFER",
        rationale="Valid: contains DEFER and no CONTINUE.",
    )
    assert valid_defer_plan.disposition == "DEFER"


def test_plan_rejects_duplicate_inquiry_ids():
    inq1 = sample_inquiry(inquiry_id="inq-duplicate")
    inq2 = sample_inquiry(inquiry_id="inq-duplicate", evidence_dimension="market_traction")

    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match="must not contain duplicate inquiry_id values",
    ):
        sample_plan(inquiries=[inq1, inq2])


def test_pure_factory_binds_plan_to_exact_context_hypothesis_and_profile():
    dc = sample_context()
    oh = sample_hypothesis()
    profile = sample_profile()
    inq = sample_inquiry()

    plan = create_value_of_information_plan(
        decision_context=dc,
        hypothesis=oh,
        profile=profile,
        plan_id="plan-factory-1",
        as_of=AS_OF,
        inquiries=[inq],
        disposition="CONTINUE",
        rationale="Evaluating critical affiliate economics.",
    )

    assert plan.plan_id == "plan-factory-1"
    assert plan.decision_context_id == dc.context_id
    assert plan.hypothesis_id == oh.hypothesis_id
    assert plan.profile_id == profile.profile_id
    assert plan.as_of is AS_OF
    assert plan.inquiries == (inq,)
    assert plan.disposition == "CONTINUE"


def test_pure_factory_accepts_alias_keywords():
    dc = sample_context()
    oh = sample_hypothesis()
    profile = sample_profile()
    inq = sample_inquiry()

    plan = create_value_of_information_plan(
        decision_context=dc,
        opportunity_hypothesis=oh,
        evidence_profile=profile,
        plan_id="plan-factory-kw",
        as_of=AS_OF,
        inquiries=[inq],
        disposition="CONTINUE",
        rationale="Testing keyword alias parameters.",
    )

    assert plan.hypothesis_id == oh.hypothesis_id
    assert plan.profile_id == profile.profile_id


def test_factory_rejects_conflicting_or_missing_arguments():
    dc = sample_context()
    oh1 = sample_hypothesis(hypothesis_id="hyp-1")
    oh2 = sample_hypothesis(hypothesis_id="hyp-2")
    prof1 = sample_profile(profile_id="prof-1")
    prof2 = sample_profile(profile_id="prof-2")

    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match="cannot supply conflicting hypothesis arguments",
    ):
        create_value_of_information_plan(
            decision_context=dc,
            hypothesis=oh1,
            opportunity_hypothesis=oh2,
            profile=prof1,
            plan_id="p1",
            as_of=AS_OF,
            disposition="STOP",
            rationale="Stopping.",
        )

    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match="cannot supply conflicting profile arguments",
    ):
        create_value_of_information_plan(
            decision_context=dc,
            hypothesis=oh1,
            profile=prof1,
            evidence_profile=prof2,
            plan_id="p1",
            as_of=AS_OF,
            disposition="STOP",
            rationale="Stopping.",
        )

    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match="hypothesis must be an OpportunityHypothesis",
    ):
        create_value_of_information_plan(
            decision_context=dc,
            profile=prof1,
            plan_id="p1",
            as_of=AS_OF,
            disposition="STOP",
            rationale="Stopping.",
        )

    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match="profile must be a TikTokAffiliateEvidenceProfile",
    ):
        create_value_of_information_plan(
            decision_context=dc,
            hypothesis=oh1,
            plan_id="p1",
            as_of=AS_OF,
            disposition="STOP",
            rationale="Stopping.",
        )


def test_factory_rejects_mismatched_identity_bindings():
    dc = sample_context(context_id="context-a")
    oh_bad_ctx = sample_hypothesis(decision_context_id="context-b")
    prof = sample_profile(decision_context_id="context-a", hypothesis_id="hypothesis-11")

    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match="hypothesis decision_context_id must match the supplied DecisionContext",
    ):
        create_value_of_information_plan(
            decision_context=dc,
            hypothesis=oh_bad_ctx,
            profile=prof,
            plan_id="p1",
            as_of=AS_OF,
            disposition="STOP",
            rationale="Stopping.",
        )

    oh_good = sample_hypothesis(decision_context_id="context-a", hypothesis_id="hypothesis-11")
    prof_bad_ctx = sample_profile(decision_context_id="context-b", hypothesis_id="hypothesis-11")

    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match="profile decision_context_id must match the supplied DecisionContext",
    ):
        create_value_of_information_plan(
            decision_context=dc,
            hypothesis=oh_good,
            profile=prof_bad_ctx,
            plan_id="p1",
            as_of=AS_OF,
            disposition="STOP",
            rationale="Stopping.",
        )

    prof_bad_hyp = sample_profile(decision_context_id="context-a", hypothesis_id="hypothesis-999")

    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match="profile hypothesis_id must match the supplied OpportunityHypothesis",
    ):
        create_value_of_information_plan(
            decision_context=dc,
            hypothesis=oh_good,
            profile=prof_bad_hyp,
            plan_id="p1",
            as_of=AS_OF,
            disposition="STOP",
            rationale="Stopping.",
        )


def test_factory_rejects_invalid_types():
    dc = sample_context()
    oh = sample_hypothesis()
    prof = sample_profile()

    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match="decision_context must be a DecisionContext",
    ):
        create_value_of_information_plan(
            decision_context="not-a-context",  # type: ignore[arg-type]
            hypothesis=oh,
            profile=prof,
            plan_id="p1",
            as_of=AS_OF,
            disposition="STOP",
            rationale="Stopping.",
        )

    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match="hypothesis must be an OpportunityHypothesis",
    ):
        create_value_of_information_plan(
            decision_context=dc,
            hypothesis="not-a-hypothesis",  # type: ignore[arg-type]
            profile=prof,
            plan_id="p1",
            as_of=AS_OF,
            disposition="STOP",
            rationale="Stopping.",
        )

    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match="profile must be a TikTokAffiliateEvidenceProfile",
    ):
        create_value_of_information_plan(
            decision_context=dc,
            hypothesis=oh,
            profile="not-a-profile",  # type: ignore[arg-type]
            plan_id="p1",
            as_of=AS_OF,
            disposition="STOP",
            rationale="Stopping.",
        )


def test_represented_and_unrepresented_dimensions_eligible_for_inquiries():
    profile = sample_profile(
        affiliate_economics=("ref://econ/1",),
        competition_saturation=(),
    )
    assert "affiliate_economics" in profile.represented_dimensions()
    assert "competition_saturation" in profile.unrepresented_dimensions()

    inq_represented = sample_inquiry(
        inquiry_id="inq-rep",
        evidence_dimension="affiliate_economics",
        explanation="Representation does not imply sufficiency; checking tier breakdown.",
        disposition="CONTINUE",
    )
    inq_unrepresented = sample_inquiry(
        inquiry_id="inq-unrep",
        evidence_dimension="competition_saturation",
        explanation="Unrepresented dimension: checking competitor ad spend density.",
        disposition="DEFER",
    )

    plan = sample_plan(
        inquiries=[inq_represented, inq_unrepresented],
        disposition="CONTINUE",
    )

    assert len(plan.inquiries) == 2
    assert plan.inquiries[0].evidence_dimension == "affiliate_economics"
    assert plan.inquiries[1].evidence_dimension == "competition_saturation"


@pytest.mark.parametrize("disposition", VALUE_OF_INFORMATION_DISPOSITIONS)
def test_valid_dispositions_accepted(disposition: str):
    if disposition == "CONTINUE":
        inq = sample_inquiry(disposition="CONTINUE")
        plan = sample_plan(inquiries=[inq], disposition="CONTINUE")
    elif disposition == "DEFER":
        inq = sample_inquiry(disposition="DEFER")
        plan = sample_plan(inquiries=[inq], disposition="DEFER")
    else:
        inq = sample_inquiry(disposition="STOP")
        plan = sample_plan(inquiries=[inq], disposition="STOP")

    assert inq.disposition == disposition
    assert plan.disposition == disposition


def test_invalid_disposition_fails_closed():
    with pytest.raises(OpportunityIntelligenceValidationError, match="must be one of"):
        sample_inquiry(disposition="UNKNOWN_ACTION")

    with pytest.raises(OpportunityIntelligenceValidationError, match="must be one of"):
        sample_plan(disposition="APPROVE")


@pytest.mark.parametrize("dim", TIKTOK_AFFILIATE_EVIDENCE_DIMENSIONS)
def test_valid_evidence_dimensions_accepted(dim: str):
    inquiry = sample_inquiry(evidence_dimension=dim)
    assert inquiry.evidence_dimension == dim


def test_invalid_evidence_dimension_fails_closed():
    with pytest.raises(OpportunityIntelligenceValidationError, match="must be one of"):
        sample_inquiry(evidence_dimension="general_sentiment")


@pytest.mark.parametrize(
    "name",
    ["plan_id", "decision_context_id", "hypothesis_id", "profile_id"],
)
def test_plan_identifiers_fail_closed_when_blank_or_invalid(name: str):
    with pytest.raises(OpportunityIntelligenceValidationError, match="must not be blank"):
        sample_plan(**{name: "  \t "})
    with pytest.raises(OpportunityIntelligenceValidationError, match="must be a string"):
        sample_plan(**{name: 12345})
    with pytest.raises(OpportunityIntelligenceValidationError, match="at most 256"):
        sample_plan(**{name: "x" * 257})
    with pytest.raises(OpportunityIntelligenceValidationError, match="single-line"):
        sample_plan(**{name: "val\nid"})


@pytest.mark.parametrize(
    "name",
    [
        "inquiry_id",
        "information_question",
        "explanation",
        "rationale",
        "expected_decision_impact",
        "uncertainty_reduction",
        "cost",
        "latency",
        "access_risk",
        "fragility",
        "reliability",
        "opportunity_cost",
        "decision_deadline",
    ],
)
def test_inquiry_string_fields_fail_closed_when_blank_or_multiline(name: str):
    with pytest.raises(OpportunityIntelligenceValidationError, match="must not be blank"):
        sample_inquiry(**{name: "  \t "})
    with pytest.raises(OpportunityIntelligenceValidationError, match="single-line"):
        sample_inquiry(**{name: "line1\nline2"})
    with pytest.raises(OpportunityIntelligenceValidationError, match="single-line"):
        sample_inquiry(**{name: "line1\rline2"})


def test_inquiry_id_bounded_to_256():
    with pytest.raises(OpportunityIntelligenceValidationError, match="at most 256"):
        sample_inquiry(inquiry_id="i" * 257)


def test_inquiry_text_fields_bounded_to_4096():
    with pytest.raises(OpportunityIntelligenceValidationError, match="at most 4096"):
        sample_inquiry(information_question="q" * 4097)


def test_as_of_must_be_timezone_aware():
    with pytest.raises(OpportunityIntelligenceValidationError, match="timezone-aware"):
        sample_plan(as_of=datetime(2026, 9, 16, 8, 30))


def test_plan_projection_is_stable_and_json_serializable():
    inq = sample_inquiry(inquiry_id="inq-proj", disposition="CONTINUE")
    plan = sample_plan(inquiries=[inq], disposition="CONTINUE")

    expected_inquiry = {
        "inquiry_id": "inq-proj",
        "evidence_dimension": "affiliate_economics",
        "information_question": "What is the net affiliate commission rate and payout reliability?",
        "explanation": "Low commission rate would make positive contribution margin impossible.",
        "disposition": "CONTINUE",
        "rationale": "Commission terms are critical to unit economics.",
        "expected_decision_impact": "High: would invert entry decision if below 10%.",
        "uncertainty_reduction": "Substantial: resolves uncertainty about net margin.",
        "cost": "Low: public seller program terms inspection.",
        "latency": "Minutes: immediate inspection.",
        "access_risk": "Minimal: publicly listed creator program terms.",
        "fragility": "Low: terms rarely fluctuate intra-day.",
        "reliability": "High: verified seller commission schedule.",
        "opportunity_cost": "Negligible: immediate check before creator outreach.",
        "decision_deadline": "Before outreach campaign launch.",
    }

    expected_plan = {
        "plan_id": "plan-voi-101",
        "decision_context_id": "decision-context-7",
        "hypothesis_id": "hypothesis-11",
        "profile_id": "profile-tiktok-101",
        "as_of": "2026-09-16T08:30:00+07:00",
        "inquiries": [expected_inquiry],
        "disposition": "CONTINUE",
        "rationale": "Key unit economics require resolution before further commitment.",
    }

    assert inq.to_dict() == expected_inquiry
    assert plan.to_dict() == expected_plan
    assert json.loads(json.dumps(plan.to_dict())) == expected_plan


@pytest.mark.parametrize(
    ("field_name", "forbidden_value", "forbidden_class"),
    [
        ("information_question", "Question with api_key=super-secret-value", "secret material"),
        ("explanation", "Bearer eyJhbGciOi...", "secret material"),
        ("rationale", "<script>alert(1)</script>", "raw HTML"),
        ("expected_decision_impact", "Cookie: sessionid=secret", "cookie or session"),
        ("uncertainty_reduction", "<|system|> prompt leak", "model prompt"),
        ("cost", '{"run_id":"RUN-223-001"}', "hidden execution metadata"),
        ("inquiry_id", "<Object at 0x7ffdeadbeef>", "object representation"),
        ("latency", "latency at 0x7ffdeadbeef", "memory address"),
    ],
)
def test_inquiry_public_projection_content_fails_closed(
    field_name: str,
    forbidden_value: str,
    forbidden_class: str,
):
    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match=forbidden_class,
    ):
        sample_inquiry(**{field_name: forbidden_value})


@pytest.mark.parametrize(
    ("field_name", "forbidden_value", "forbidden_class"),
    [
        ("plan_id", "<Object at 0x7ffdeadbeef>", "object representation"),
        ("rationale", "Bearer secret-token", "secret material"),
    ],
)
def test_plan_public_projection_content_fails_closed(
    field_name: str,
    forbidden_value: str,
    forbidden_class: str,
):
    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match=forbidden_class,
    ):
        sample_plan(**{field_name: forbidden_value})


def test_values_are_immutable_and_collections_are_frozen():
    inq = sample_inquiry()
    plan = sample_plan(inquiries=[inq])

    with pytest.raises(FrozenInstanceError):
        inq.inquiry_id = "new-id"  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        plan.plan_id = "new-plan"  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        plan.inquiries = ()  # type: ignore[misc]


def test_entities_expose_no_commerce_decision_score_rank_or_lifecycle_state():
    forbidden = {
        "approval",
        "approved",
        "score",
        "rank",
        "recommendation",
        "status",
        "stage",
        "test_ready",
        "validated_winner",
        "scalable_winner",
        "confidence",
        "winner",
        "priority",
        "acquisition_order",
        "lifecycle_state",
    }

    inquiry_fields = {f.name for f in fields(ValueOfInformationInquiry)}
    plan_fields = {f.name for f in fields(ValueOfInformationPlan)}

    assert forbidden.isdisjoint(inquiry_fields)
    assert forbidden.isdisjoint(plan_fields)


def test_module_has_no_external_system_or_generated_identity_dependencies():
    module_path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "commerce_opportunity_intelligence"
        / "value_of_information.py"
    )
    source = module_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_roots = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_roots.update(
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )

    assert imported_roots <= {
        "__future__",
        "collections",
        "dataclasses",
        "datetime",
        "re",
        "typing",
        "decision_context",
        "tiktok_affiliate_evidence",
    }
    for forbidden_call in (
        "datetime.now",
        "datetime.utcnow",
        "uuid",
        "random",
        "subprocess",
        "socket",
        "requests",
        "httpx",
        "open(",
        "getenv",
        "environ",
        "sqlite",
        "queue",
        "aios",
    ):
        assert forbidden_call not in source.lower()
