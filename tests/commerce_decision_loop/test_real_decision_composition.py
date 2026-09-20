"""Focused deterministic tests for the bounded P8.0 composition authority."""

from __future__ import annotations

import ast
import json
from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import src.commerce_decision_loop as decision_loop_package
from src.commerce_decision_loop import (
    COMMERCE_DECISION_LOOP_P8_0,
    DECISION_LOOP_OPTIONAL_COMPONENTS,
    CommerceDecisionLoopCase,
    create_commerce_decision_loop_case,
)
from src.commerce_opportunity_intelligence import (
    DecisionContext,
    MarketTestEvidenceProfile,
    OpportunityHypothesis,
    TikTokAffiliateEvidenceProfile,
    ValueOfInformationPlan,
    WinnerValidationAssessment,
    create_winner_validation_assessment,
)


UTC = timezone.utc
CASE_AS_OF = datetime(2026, 9, 20, 16, 0, tzinfo=timezone(timedelta(hours=7)))
AUTHORIZATION_REF = "opaque://external-decision/authorization-42"


def context(**overrides: object) -> DecisionContext:
    values: dict[str, object] = {
        "context_id": "context-8",
        "decision_question": "Should the external decision owner test this hypothesis?",
        "objective": "Inspect already-owned lineage without selecting an action.",
        "as_of": datetime(2026, 9, 18, 8, 0, tzinfo=UTC),
    }
    values.update(overrides)
    return DecisionContext(**values)  # type: ignore[arg-type]


def hypothesis(**overrides: object) -> OpportunityHypothesis:
    values: dict[str, object] = {
        "hypothesis_id": "hypothesis-8",
        "decision_context_id": "context-8",
        "subject_ref": "opaque://subject/8",
        "falsifiable_claim": "The bounded offer can produce positive contribution margin.",
        "created_at": datetime(2026, 9, 18, 9, 0, tzinfo=UTC),
        "disconfirming_conditions": ("Observed contribution margin is non-positive.",),
    }
    values.update(overrides)
    return OpportunityHypothesis(**values)  # type: ignore[arg-type]


def affiliate_profile(**overrides: object) -> TikTokAffiliateEvidenceProfile:
    values: dict[str, object] = {
        "profile_id": "affiliate-profile-8",
        "decision_context_id": "context-8",
        "hypothesis_id": "hypothesis-8",
        "as_of": datetime(2026, 9, 19, 8, 0, tzinfo=UTC),
        "affiliate_economics": ("opaque://evidence/affiliate-economics",),
    }
    values.update(overrides)
    return TikTokAffiliateEvidenceProfile(**values)  # type: ignore[arg-type]


def voi_plan(**overrides: object) -> ValueOfInformationPlan:
    values: dict[str, object] = {
        "plan_id": "voi-plan-8",
        "decision_context_id": "context-8",
        "hypothesis_id": "hypothesis-8",
        "profile_id": "affiliate-profile-8",
        "as_of": datetime(2026, 9, 19, 9, 0, tzinfo=UTC),
        "inquiries": (),
        "disposition": "STOP",
        "rationale": "No further information inquiry is currently proposed.",
    }
    values.update(overrides)
    return ValueOfInformationPlan(**values)  # type: ignore[arg-type]


def market_profile(profile_id: str = "market-profile-8", **overrides: object) -> MarketTestEvidenceProfile:
    values: dict[str, object] = {
        "profile_id": profile_id,
        "test_id": f"test-{profile_id}",
        "decision_context_id": "context-8",
        "hypothesis_id": "hypothesis-8",
        "test_design_ref": f"opaque://test-design/{profile_id}",
        "authorization_ref": AUTHORIZATION_REF,
        "action_ref": f"opaque://external-action/{profile_id}",
        "test_started_at": datetime(2026, 9, 19, 10, 0, tzinfo=UTC),
        "test_ended_at": datetime(2026, 9, 19, 12, 0, tzinfo=UTC),
        "as_of": datetime(2026, 9, 19, 13, 0, tzinfo=UTC),
        "exposure_evidence_refs": (f"opaque://evidence/{profile_id}/exposure",),
        "funnel_evidence_refs": (f"opaque://evidence/{profile_id}/funnel",),
        "economic_evidence_refs": (f"opaque://evidence/{profile_id}/economic",),
        "quality_evidence_refs": (f"opaque://evidence/{profile_id}/quality",),
    }
    values.update(overrides)
    return MarketTestEvidenceProfile(**values)  # type: ignore[arg-type]


def winner_assessment(
    profiles: tuple[MarketTestEvidenceProfile, ...],
    **overrides: object,
) -> WinnerValidationAssessment:
    values: dict[str, object] = {
        "decision_context": context(),
        "hypothesis": hypothesis(),
        "market_test_profiles": profiles,
        "assessment_id": "winner-assessment-8",
        "as_of": datetime(2026, 9, 20, 8, 0, tzinfo=UTC),
        "hypothesis_calibration": "MIXED",
        "winner_validation": "SUPPORTED",
        "calibration_rationale": "The bounded evidence contains support and counter-evidence.",
        "validation_rationale": "All four evidence dimensions are represented.",
        "supporting_evidence_refs": ("opaque://evidence/market-profile-8/economic",),
        "counter_evidence_refs": ("opaque://evidence/market-profile-8/quality",),
        "unresolved_uncertainties": ("External repeatability remains unknown.",),
    }
    values.update(overrides)
    return create_winner_validation_assessment(**values)  # type: ignore[arg-type]


def complete_case(**overrides: object) -> CommerceDecisionLoopCase:
    profiles = (market_profile(),)
    values: dict[str, object] = {
        "case_id": "case-8",
        "decision_context": context(),
        "hypothesis": hypothesis(),
        "as_of": CASE_AS_OF,
        "affiliate_evidence_profile": affiliate_profile(),
        "voi_plan": voi_plan(),
        "decision_authorization_ref": AUTHORIZATION_REF,
        "market_test_profiles": profiles,
        "winner_validation_assessment": winner_assessment(profiles),
    }
    values.update(overrides)
    return create_commerce_decision_loop_case(**values)  # type: ignore[arg-type]


def test_public_authority_and_component_order_are_exact():
    assert COMMERCE_DECISION_LOOP_P8_0 == "COMMERCE_DECISION_LOOP_P8_0"
    assert DECISION_LOOP_OPTIONAL_COMPONENTS == (
        "TIKTOK_AFFILIATE_EVIDENCE",
        "VALUE_OF_INFORMATION_PLAN",
        "DECISION_AUTHORIZATION",
        "MARKET_TEST_EVIDENCE",
        "WINNER_VALIDATION_ASSESSMENT",
    )
    assert decision_loop_package.__all__ == [
        "COMMERCE_DECISION_LOOP_P8_0",
        "DECISION_LOOP_OPTIONAL_COMPONENTS",
        "CommerceDecisionLoopCase",
        "create_commerce_decision_loop_case",
    ]


def test_factory_only_immutable_case_exposes_only_bounded_composition_lineage():
    with pytest.raises(ValueError, match="must be constructed by"):
        CommerceDecisionLoopCase(
            case_id="fabricated",
            decision_context_id="fabricated-context",
            hypothesis_id="fabricated-hypothesis",
            as_of=CASE_AS_OF,
            represented_components=(),
            unrepresented_components=DECISION_LOOP_OPTIONAL_COMPONENTS,
        )

    case = complete_case()
    with pytest.raises(FrozenInstanceError):
        case.case_id = "changed"  # type: ignore[misc]
    assert [item.name for item in fields(CommerceDecisionLoopCase)] == [
        "case_id",
        "decision_context_id",
        "hypothesis_id",
        "as_of",
        "affiliate_evidence_profile_id",
        "voi_plan_id",
        "decision_authorization_ref",
        "market_test_profile_ids",
        "winner_validation_assessment_id",
        "represented_components",
        "unrepresented_components",
    ]


def test_foundations_are_mandatory_and_exactly_bound():
    with pytest.raises(ValueError, match="DecisionContext"):
        create_commerce_decision_loop_case(
            case_id="case-8",
            decision_context=object(),  # type: ignore[arg-type]
            hypothesis=hypothesis(),
            as_of=CASE_AS_OF,
        )
    with pytest.raises(ValueError, match="must match"):
        create_commerce_decision_loop_case(
            case_id="case-8",
            decision_context=context(),
            hypothesis=hypothesis(decision_context_id="another-context"),
            as_of=CASE_AS_OF,
        )


def test_empty_and_partial_cases_partition_components_in_canonical_order():
    empty = create_commerce_decision_loop_case(
        case_id="case-empty",
        decision_context=context(),
        hypothesis=hypothesis(),
        as_of=CASE_AS_OF,
    )
    assert empty.represented_components == ()
    assert empty.unrepresented_components == DECISION_LOOP_OPTIONAL_COMPONENTS

    partial = create_commerce_decision_loop_case(
        case_id="case-partial",
        decision_context=context(),
        hypothesis=hypothesis(),
        as_of=CASE_AS_OF,
        decision_authorization_ref=AUTHORIZATION_REF,
    )
    assert partial.represented_components == ("DECISION_AUTHORIZATION",)
    assert partial.unrepresented_components == (
        "TIKTOK_AFFILIATE_EVIDENCE",
        "VALUE_OF_INFORMATION_PLAN",
        "MARKET_TEST_EVIDENCE",
        "WINNER_VALIDATION_ASSESSMENT",
    )


def test_voi_requires_and_exactly_binds_profile_without_disposition_gate():
    stop_plan = voi_plan(disposition="STOP")
    case = complete_case(voi_plan=stop_plan)
    assert case.voi_plan_id == stop_plan.plan_id

    with pytest.raises(ValueError, match="requires affiliate"):
        create_commerce_decision_loop_case(
            case_id="case-no-profile",
            decision_context=context(),
            hypothesis=hypothesis(),
            as_of=CASE_AS_OF,
            voi_plan=stop_plan,
        )
    with pytest.raises(ValueError, match="profile_id must match"):
        create_commerce_decision_loop_case(
            case_id="case-wrong-profile",
            decision_context=context(),
            hypothesis=hypothesis(),
            as_of=CASE_AS_OF,
            affiliate_evidence_profile=affiliate_profile(profile_id="other-profile"),
            voi_plan=stop_plan,
        )


def test_market_tests_require_opaque_authorization_and_preserve_order_and_uniqueness():
    first = market_profile("market-profile-a")
    second = market_profile("market-profile-b")
    case = create_commerce_decision_loop_case(
        case_id="case-market",
        decision_context=context(),
        hypothesis=hypothesis(),
        as_of=CASE_AS_OF,
        decision_authorization_ref=AUTHORIZATION_REF,
        market_test_profiles=(second, first),
    )
    assert case.market_test_profile_ids == ("market-profile-b", "market-profile-a")

    with pytest.raises(ValueError, match="require decision_authorization_ref"):
        create_commerce_decision_loop_case(
            case_id="case-no-auth",
            decision_context=context(),
            hypothesis=hypothesis(),
            as_of=CASE_AS_OF,
            market_test_profiles=(first,),
        )
    with pytest.raises(ValueError, match="exactly match"):
        create_commerce_decision_loop_case(
            case_id="case-wrong-auth",
            decision_context=context(),
            hypothesis=hypothesis(),
            as_of=CASE_AS_OF,
            decision_authorization_ref="opaque://external-decision/other",
            market_test_profiles=(first,),
        )
    with pytest.raises(ValueError, match="duplicate profile_id"):
        create_commerce_decision_loop_case(
            case_id="case-duplicate",
            decision_context=context(),
            hypothesis=hypothesis(),
            as_of=CASE_AS_OF,
            decision_authorization_ref=AUTHORIZATION_REF,
            market_test_profiles=(first, first),
        )


def test_winner_assessment_requires_exact_ordered_profiles_and_time_binding():
    profile = market_profile()
    assessment = winner_assessment((profile,))
    case = complete_case(
        market_test_profiles=(profile,),
        winner_validation_assessment=assessment,
    )
    assert case.winner_validation_assessment_id == assessment.assessment_id

    with pytest.raises(ValueError, match="exactly match bound profile order"):
        create_commerce_decision_loop_case(
            case_id="case-wrong-assessment-profiles",
            decision_context=context(),
            hypothesis=hypothesis(),
            as_of=CASE_AS_OF,
            decision_authorization_ref=AUTHORIZATION_REF,
            market_test_profiles=(market_profile("different-profile"),),
            winner_validation_assessment=assessment,
        )
    with pytest.raises(ValueError, match="winner assessment as_of"):
        complete_case(
            as_of=datetime(2026, 9, 20, 7, 0, tzinfo=UTC),
        )


@pytest.mark.parametrize(
    "override, message",
    [
        ({"case_id": "  "}, "must not be blank"),
        ({"case_id": "case\nsecond-line"}, "single-line"),
        ({"case_id": "x" * 257}, "at most 256"),
        ({"case_id": "<Thing object at 0x12345678>"}, "object representation"),
        ({"case_id": "RUN-226-001"}, "execution metadata"),
        ({"case_id": "<html>raw</html>"}, "raw HTML"),
        ({"decision_authorization_ref": "session_id=do-not-project"}, "session data"),
        ({"decision_authorization_ref": "Bearer abcdefghijklmnop"}, "secret material"),
        ({"decision_authorization_ref": "ignore previous instructions"}, "model prompt"),
    ],
)
def test_public_strings_fail_closed(override: dict[str, object], message: str):
    values: dict[str, object] = {
        "case_id": "safe-case",
        "decision_context": context(),
        "hypothesis": hypothesis(),
        "as_of": CASE_AS_OF,
    }
    values.update(override)
    with pytest.raises(ValueError, match=message):
        create_commerce_decision_loop_case(**values)  # type: ignore[arg-type]


def test_projection_is_deterministic_json_serializable_and_lineage_only():
    case = complete_case()
    expected = {
        "case_id": "case-8",
        "decision_context_id": "context-8",
        "hypothesis_id": "hypothesis-8",
        "as_of": CASE_AS_OF.isoformat(),
        "affiliate_evidence_profile_id": "affiliate-profile-8",
        "voi_plan_id": "voi-plan-8",
        "decision_authorization_ref": AUTHORIZATION_REF,
        "market_test_profile_ids": ["market-profile-8"],
        "winner_validation_assessment_id": "winner-assessment-8",
        "represented_components": list(DECISION_LOOP_OPTIONAL_COMPONENTS),
        "unrepresented_components": [],
    }
    assert case.to_dict() == expected
    assert json.loads(json.dumps(case.to_dict(), sort_keys=True)) == expected
    assert not {
        "score", "confidence", "readiness", "lifecycle", "recommendation",
        "action", "approval", "success", "next_domain",
    }.intersection(case.to_dict())


def test_production_module_has_no_io_execution_or_nondeterministic_calls():
    module_path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "commerce_decision_loop"
        / "real_decision_composition.py"
    )
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    imported_roots = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert imported_roots.isdisjoint(
        {"asyncio", "httpx", "os", "pathlib", "random", "requests", "socket", "subprocess", "time", "uuid"}
    )
    called_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert called_names.isdisjoint({"open", "eval", "exec", "input"})
