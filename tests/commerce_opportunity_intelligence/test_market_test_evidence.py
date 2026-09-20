"""Focused deterministic tests for the bounded P7.6 semantic authority."""

from __future__ import annotations

import ast
import json
from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.commerce_opportunity_intelligence import (
    COMMERCE_OPPORTUNITY_INTELLIGENCE_P7_6,
    MARKET_TEST_EVIDENCE_DIMENSIONS,
    DecisionContext,
    MarketTestEvidenceProfile,
    OpportunityHypothesis,
    OpportunityIntelligenceValidationError,
    create_market_test_evidence_profile,
)


AS_OF = datetime(2026, 9, 20, 14, 0, tzinfo=timezone(timedelta(hours=7)))
TEST_STARTED_AT = datetime(2026, 9, 20, 10, 0, tzinfo=timezone(timedelta(hours=7)))
TEST_ENDED_AT = datetime(2026, 9, 20, 12, 0, tzinfo=timezone(timedelta(hours=7)))
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


def sample_profile(**overrides: object) -> MarketTestEvidenceProfile:
    values: dict[str, object] = {
        "profile_id": "profile-market-test-1",
        "test_id": "test-intervention-42",
        "decision_context_id": "decision-context-7",
        "hypothesis_id": "hypothesis-11",
        "test_design_ref": "opaque://design/creative-variant-a",
        "authorization_ref": "opaque://auth/human-approved-budget-100",
        "action_ref": "opaque://action/ad-spend-campaign-run-7",
        "test_started_at": TEST_STARTED_AT,
        "test_ended_at": TEST_ENDED_AT,
        "as_of": AS_OF,
        "exposure_evidence_refs": ("ref://evidence/exposure/1",),
        "funnel_evidence_refs": ("ref://evidence/funnel/1", "ref://evidence/funnel/2"),
        "economic_evidence_refs": ("ref://evidence/economics/1",),
        "quality_evidence_refs": ("ref://evidence/quality/1",),
    }
    values.update(overrides)
    return MarketTestEvidenceProfile(**values)  # type: ignore[arg-type]


def test_authority_identifier_and_ordered_dimensions():
    assert (
        COMMERCE_OPPORTUNITY_INTELLIGENCE_P7_6
        == "COMMERCE_OPPORTUNITY_INTELLIGENCE_P7_6"
    )
    assert MARKET_TEST_EVIDENCE_DIMENSIONS == (
        "exposure_evidence_refs",
        "funnel_evidence_refs",
        "economic_evidence_refs",
        "quality_evidence_refs",
    )


def test_valid_profile_preserves_caller_values_and_order():
    profile = sample_profile(
        funnel_evidence_refs=("ref://funnel/b", "ref://funnel/a"),
    )

    assert profile.profile_id == "profile-market-test-1"
    assert profile.test_id == "test-intervention-42"
    assert profile.decision_context_id == "decision-context-7"
    assert profile.hypothesis_id == "hypothesis-11"
    assert profile.test_design_ref == "opaque://design/creative-variant-a"
    assert profile.authorization_ref == "opaque://auth/human-approved-budget-100"
    assert profile.action_ref == "opaque://action/ad-spend-campaign-run-7"
    assert profile.test_started_at is TEST_STARTED_AT
    assert profile.test_ended_at is TEST_ENDED_AT
    assert profile.as_of is AS_OF
    assert profile.exposure_evidence_refs == ("ref://evidence/exposure/1",)
    assert profile.funnel_evidence_refs == (
        "ref://funnel/b",
        "ref://funnel/a",
    )
    assert profile.economic_evidence_refs == ("ref://evidence/economics/1",)
    assert profile.quality_evidence_refs == ("ref://evidence/quality/1",)


def test_profile_requires_at_least_one_supplied_evidence_reference():
    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match="must contain at least one evidence reference across dimensions",
    ):
        sample_profile(
            exposure_evidence_refs=(),
            funnel_evidence_refs=(),
            economic_evidence_refs=(),
            quality_evidence_refs=(),
        )


def test_empty_dimension_is_unrepresented_not_zero_or_failure():
    profile = sample_profile(
        exposure_evidence_refs=("ref://exposure/1",),
        funnel_evidence_refs=(),
        economic_evidence_refs=(),
        quality_evidence_refs=(),
    )

    assert profile.represented_dimensions() == ("exposure_evidence_refs",)
    assert profile.unrepresented_dimensions() == (
        "funnel_evidence_refs",
        "economic_evidence_refs",
        "quality_evidence_refs",
    )

    projection = profile.to_dict()
    assert projection["represented_dimensions"] == ["exposure_evidence_refs"]
    assert projection["unrepresented_dimensions"] == [
        "funnel_evidence_refs",
        "economic_evidence_refs",
        "quality_evidence_refs",
    ]
    assert projection["funnel_evidence_refs"] == []
    assert projection["economic_evidence_refs"] == []
    assert projection["quality_evidence_refs"] == []


def test_partial_dimension_representation_preserves_fixed_order():
    profile = sample_profile(
        exposure_evidence_refs=("ref://exposure/1",),
        funnel_evidence_refs=(),
        economic_evidence_refs=("ref://econ/1",),
        quality_evidence_refs=(),
    )

    assert profile.represented_dimensions() == (
        "exposure_evidence_refs",
        "economic_evidence_refs",
    )
    assert profile.unrepresented_dimensions() == (
        "funnel_evidence_refs",
        "quality_evidence_refs",
    )


@pytest.mark.parametrize("dim", MARKET_TEST_EVIDENCE_DIMENSIONS)
def test_dimension_rejects_duplicates_within_same_dimension(dim: str):
    duplicate_refs = ("ref://item/1", "ref://item/1")
    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match="must not contain duplicate values",
    ):
        sample_profile(**{dim: duplicate_refs})


def test_same_opaque_reference_may_appear_across_different_dimensions():
    shared_ref = "ref://evidence/shared-post-intervention/99"
    profile = sample_profile(
        exposure_evidence_refs=(shared_ref,),
        funnel_evidence_refs=(shared_ref,),
        economic_evidence_refs=(),
        quality_evidence_refs=(),
    )

    assert shared_ref in profile.exposure_evidence_refs
    assert shared_ref in profile.funnel_evidence_refs


def test_pure_factory_binds_profile_to_exact_context_and_hypothesis():
    dc = sample_context()
    oh = sample_hypothesis()

    profile = create_market_test_evidence_profile(
        decision_context=dc,
        hypothesis=oh,
        profile_id="profile-factory-1",
        test_id="test-factory-1",
        test_design_ref="ref://design/1",
        authorization_ref="ref://auth/1",
        action_ref="ref://action/1",
        test_started_at=TEST_STARTED_AT,
        test_ended_at=TEST_ENDED_AT,
        as_of=AS_OF,
        exposure_evidence_refs=["ref://exposure/1"],
        funnel_evidence_refs=["ref://funnel/1"],
    )

    assert profile.profile_id == "profile-factory-1"
    assert profile.test_id == "test-factory-1"
    assert profile.decision_context_id == dc.context_id
    assert profile.hypothesis_id == oh.hypothesis_id
    assert profile.test_design_ref == "ref://design/1"
    assert profile.authorization_ref == "ref://auth/1"
    assert profile.action_ref == "ref://action/1"
    assert profile.test_started_at is TEST_STARTED_AT
    assert profile.test_ended_at is TEST_ENDED_AT
    assert profile.as_of is AS_OF
    assert profile.exposure_evidence_refs == ("ref://exposure/1",)
    assert profile.funnel_evidence_refs == ("ref://funnel/1",)
    assert profile.economic_evidence_refs == ()
    assert profile.quality_evidence_refs == ()


def test_pure_factory_accepts_opportunity_hypothesis_keyword():
    dc = sample_context()
    oh = sample_hypothesis()

    profile = create_market_test_evidence_profile(
        decision_context=dc,
        opportunity_hypothesis=oh,
        profile_id="profile-factory-kw",
        test_id="test-factory-kw",
        test_design_ref="ref://design/1",
        authorization_ref="ref://auth/1",
        action_ref="ref://action/1",
        test_started_at=TEST_STARTED_AT,
        test_ended_at=TEST_ENDED_AT,
        as_of=AS_OF,
        exposure_evidence_refs=["ref://exposure/1"],
    )

    assert profile.hypothesis_id == oh.hypothesis_id


def test_factory_rejects_conflicting_hypothesis_arguments():
    dc = sample_context()
    oh1 = sample_hypothesis(hypothesis_id="hyp-1")
    oh2 = sample_hypothesis(hypothesis_id="hyp-2")

    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match="cannot supply conflicting hypothesis arguments",
    ):
        create_market_test_evidence_profile(
            decision_context=dc,
            hypothesis=oh1,
            opportunity_hypothesis=oh2,
            profile_id="p1",
            test_id="t1",
            test_design_ref="ref://d",
            authorization_ref="ref://a",
            action_ref="ref://act",
            test_started_at=TEST_STARTED_AT,
            test_ended_at=TEST_ENDED_AT,
            as_of=AS_OF,
            exposure_evidence_refs=["ref://e"],
        )


def test_factory_rejects_mismatched_context_binding():
    dc = sample_context(context_id="context-alpha")
    oh = sample_hypothesis(decision_context_id="context-beta")

    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match="must match the supplied DecisionContext",
    ):
        create_market_test_evidence_profile(
            decision_context=dc,
            hypothesis=oh,
            profile_id="p1",
            test_id="t1",
            test_design_ref="ref://d",
            authorization_ref="ref://a",
            action_ref="ref://act",
            test_started_at=TEST_STARTED_AT,
            test_ended_at=TEST_ENDED_AT,
            as_of=AS_OF,
            exposure_evidence_refs=["ref://e"],
        )


def test_factory_rejects_invalid_context_or_hypothesis_types():
    dc = sample_context()
    oh = sample_hypothesis()

    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match="must be a DecisionContext",
    ):
        create_market_test_evidence_profile(
            decision_context="not-a-context",  # type: ignore[arg-type]
            hypothesis=oh,
            profile_id="p1",
            test_id="t1",
            test_design_ref="ref://d",
            authorization_ref="ref://a",
            action_ref="ref://act",
            test_started_at=TEST_STARTED_AT,
            test_ended_at=TEST_ENDED_AT,
            as_of=AS_OF,
            exposure_evidence_refs=["ref://e"],
        )

    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match="must be an OpportunityHypothesis",
    ):
        create_market_test_evidence_profile(
            decision_context=dc,
            hypothesis="not-a-hypothesis",  # type: ignore[arg-type]
            profile_id="p1",
            test_id="t1",
            test_design_ref="ref://d",
            authorization_ref="ref://a",
            action_ref="ref://act",
            test_started_at=TEST_STARTED_AT,
            test_ended_at=TEST_ENDED_AT,
            as_of=AS_OF,
            exposure_evidence_refs=["ref://e"],
        )

    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match="must be an OpportunityHypothesis",
    ):
        create_market_test_evidence_profile(
            decision_context=dc,
            profile_id="p1",
            test_id="t1",
            test_design_ref="ref://d",
            authorization_ref="ref://a",
            action_ref="ref://act",
            test_started_at=TEST_STARTED_AT,
            test_ended_at=TEST_ENDED_AT,
            as_of=AS_OF,
            exposure_evidence_refs=["ref://e"],
        )


def test_factory_rejects_decision_deadline_kwarg():
    dc = sample_context()
    oh = sample_hypothesis()

    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match="decision deadline is canonically owned by DecisionContext",
    ):
        create_market_test_evidence_profile(
            decision_context=dc,
            hypothesis=oh,
            profile_id="p1",
            test_id="t1",
            test_design_ref="ref://d",
            authorization_ref="ref://a",
            action_ref="ref://act",
            test_started_at=TEST_STARTED_AT,
            test_ended_at=TEST_ENDED_AT,
            as_of=AS_OF,
            exposure_evidence_refs=["ref://e"],
            decision_deadline=AS_OF,
        )


def test_factory_rejects_unexpected_kwargs():
    dc = sample_context()
    oh = sample_hypothesis()

    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match="unexpected arguments: extra_arg",
    ):
        create_market_test_evidence_profile(
            decision_context=dc,
            hypothesis=oh,
            profile_id="p1",
            test_id="t1",
            test_design_ref="ref://d",
            authorization_ref="ref://a",
            action_ref="ref://act",
            test_started_at=TEST_STARTED_AT,
            test_ended_at=TEST_ENDED_AT,
            as_of=AS_OF,
            exposure_evidence_refs=["ref://e"],
            extra_arg="unexpected",
        )


def test_time_window_ordering_enforced():
    earlier = datetime(2026, 9, 20, 9, 0, tzinfo=timezone.utc)
    middle = datetime(2026, 9, 20, 10, 0, tzinfo=timezone.utc)
    later = datetime(2026, 9, 20, 11, 0, tzinfo=timezone.utc)

    # valid: earlier <= middle <= later
    profile = sample_profile(
        test_started_at=earlier,
        test_ended_at=middle,
        as_of=later,
    )
    assert profile.test_started_at == earlier
    assert profile.test_ended_at == middle
    assert profile.as_of == later

    # valid: all equal
    equal_profile = sample_profile(
        test_started_at=middle,
        test_ended_at=middle,
        as_of=middle,
    )
    assert equal_profile.test_started_at == equal_profile.test_ended_at == equal_profile.as_of

    # invalid: test_started_at > test_ended_at
    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match="test_started_at must be less than or equal to test_ended_at",
    ):
        sample_profile(
            test_started_at=middle,
            test_ended_at=earlier,
            as_of=later,
        )

    # invalid: test_ended_at > as_of
    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match="test_ended_at must be less than or equal to as_of",
    ):
        sample_profile(
            test_started_at=earlier,
            test_ended_at=later,
            as_of=middle,
        )


def test_timestamps_must_be_timezone_aware():
    naive = datetime(2026, 9, 20, 10, 0)

    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match="test_started_at must be timezone-aware",
    ):
        sample_profile(test_started_at=naive)

    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match="test_ended_at must be timezone-aware",
    ):
        sample_profile(test_ended_at=naive)

    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match="as_of must be timezone-aware",
    ):
        sample_profile(as_of=naive)


def test_timestamps_must_be_datetime_type():
    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match="test_started_at must be a datetime",
    ):
        sample_profile(test_started_at="2026-09-20T10:00:00Z")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "field_name",
    ["profile_id", "test_id", "decision_context_id", "hypothesis_id"],
)
def test_identifier_fields_fail_closed_on_invalid_string(field_name: str):
    with pytest.raises(OpportunityIntelligenceValidationError, match="must be a string"):
        sample_profile(**{field_name: 12345})
    with pytest.raises(OpportunityIntelligenceValidationError, match="must not be blank"):
        sample_profile(**{field_name: "   "})
    with pytest.raises(OpportunityIntelligenceValidationError, match="single-line"):
        sample_profile(**{field_name: "id\nnewline"})
    with pytest.raises(OpportunityIntelligenceValidationError, match="single-line"):
        sample_profile(**{field_name: "id\rcarriage"})
    with pytest.raises(OpportunityIntelligenceValidationError, match="at most 256"):
        sample_profile(**{field_name: "x" * 257})


@pytest.mark.parametrize(
    "field_name",
    ["test_design_ref", "authorization_ref", "action_ref"],
)
def test_lineage_ref_fields_fail_closed_on_invalid_string(field_name: str):
    with pytest.raises(OpportunityIntelligenceValidationError, match="must be a string"):
        sample_profile(**{field_name: 999})
    with pytest.raises(OpportunityIntelligenceValidationError, match="must not be blank"):
        sample_profile(**{field_name: ""})
    with pytest.raises(OpportunityIntelligenceValidationError, match="single-line"):
        sample_profile(**{field_name: "ref\nnewline"})
    with pytest.raises(OpportunityIntelligenceValidationError, match="at most 512"):
        sample_profile(**{field_name: "x" * 513})


@pytest.mark.parametrize("dim", MARKET_TEST_EVIDENCE_DIMENSIONS)
def test_dimension_refs_fail_closed_on_invalid_items(dim: str):
    with pytest.raises(OpportunityIntelligenceValidationError, match="must be a string"):
        sample_profile(**{dim: (123,)})
    with pytest.raises(OpportunityIntelligenceValidationError, match="must not be blank"):
        sample_profile(**{dim: ("  ",)})
    with pytest.raises(OpportunityIntelligenceValidationError, match="single-line"):
        sample_profile(**{dim: ("ref\nnewline",)})
    with pytest.raises(OpportunityIntelligenceValidationError, match="at most 512"):
        sample_profile(**{dim: ("x" * 513,)})


@pytest.mark.parametrize("dim", MARKET_TEST_EVIDENCE_DIMENSIONS)
def test_dimension_refs_reject_unordered_collections(dim: str):
    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match="ordered collection",
    ):
        sample_profile(**{dim: {"ref://evidence/1", "ref://evidence/2"}})


def test_profile_rejects_decision_deadline_direct_instantiation():
    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match="decision deadline is canonically owned by DecisionContext",
    ):
        MarketTestEvidenceProfile(
            profile_id="p1",
            test_id="t1",
            decision_context_id="dc1",
            hypothesis_id="h1",
            test_design_ref="ref://d",
            authorization_ref="ref://a",
            action_ref="ref://act",
            test_started_at=TEST_STARTED_AT,
            test_ended_at=TEST_ENDED_AT,
            as_of=AS_OF,
            exposure_evidence_refs=("ref://e",),
            decision_deadline=AS_OF,
        )


def test_profile_rejects_unexpected_args_or_kwargs():
    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match="unexpected positional arguments",
    ):
        MarketTestEvidenceProfile(
            "p1", "t1", "dc1", "h1", "d", "a", "act",
            TEST_STARTED_AT, TEST_ENDED_AT, AS_OF,
            ("ref://e",), (), (), (),
            "extra_positional_arg",
        )

    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match="unexpected keyword arguments: mystery",
    ):
        MarketTestEvidenceProfile(
            profile_id="p1",
            test_id="t1",
            decision_context_id="dc1",
            hypothesis_id="h1",
            test_design_ref="ref://d",
            authorization_ref="ref://a",
            action_ref="ref://act",
            test_started_at=TEST_STARTED_AT,
            test_ended_at=TEST_ENDED_AT,
            as_of=AS_OF,
            exposure_evidence_refs=("ref://e",),
            mystery="bad",
        )


def test_values_are_immutable_and_collections_are_frozen():
    caller_list = ["ref://exp/1", "ref://exp/2"]
    profile = sample_profile(exposure_evidence_refs=caller_list)

    caller_list.append("ref://exp/mutated")
    assert profile.exposure_evidence_refs == ("ref://exp/1", "ref://exp/2")

    with pytest.raises(FrozenInstanceError):
        profile.profile_id = "new-id"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        profile.exposure_evidence_refs = ("new",)  # type: ignore[misc]


def test_profile_projection_is_stable_and_json_serializable():
    profile = sample_profile(
        exposure_evidence_refs=("ref://exp/2", "ref://exp/1"),
        funnel_evidence_refs=(),
        economic_evidence_refs=("ref://econ/1",),
        quality_evidence_refs=(),
    )

    expected = {
        "profile_id": "profile-market-test-1",
        "test_id": "test-intervention-42",
        "decision_context_id": "decision-context-7",
        "hypothesis_id": "hypothesis-11",
        "test_design_ref": "opaque://design/creative-variant-a",
        "authorization_ref": "opaque://auth/human-approved-budget-100",
        "action_ref": "opaque://action/ad-spend-campaign-run-7",
        "test_started_at": "2026-09-20T10:00:00+07:00",
        "test_ended_at": "2026-09-20T12:00:00+07:00",
        "as_of": "2026-09-20T14:00:00+07:00",
        "exposure_evidence_refs": ["ref://exp/2", "ref://exp/1"],
        "funnel_evidence_refs": [],
        "economic_evidence_refs": ["ref://econ/1"],
        "quality_evidence_refs": [],
        "represented_dimensions": [
            "exposure_evidence_refs",
            "economic_evidence_refs",
        ],
        "unrepresented_dimensions": [
            "funnel_evidence_refs",
            "quality_evidence_refs",
        ],
    }

    assert profile.to_dict() == expected
    assert json.loads(json.dumps(profile.to_dict())) == expected


@pytest.mark.parametrize(
    ("overrides", "forbidden_class"),
    [
        (
            {"exposure_evidence_refs": ("ref://api_key=super-secret-value",)},
            "secret material",
        ),
        (
            {"authorization_ref": "Bearer eyJhbGciOi..."},
            "secret material",
        ),
        (
            {"funnel_evidence_refs": ("ref://<script>alert(1)</script>",)},
            "raw HTML",
        ),
        (
            {"action_ref": "Cookie: sessionid=secret"},
            "cookie or session",
        ),
        (
            {"test_design_ref": "<|system|> prompt leak"},
            "model prompt",
        ),
        (
            {"economic_evidence_refs": ('{"run_id":"RUN-224-001"}',)},
            "hidden execution metadata",
        ),
        (
            {"profile_id": "<Object at 0x7ffdeadbeef>"},
            "object representation",
        ),
        (
            {"quality_evidence_refs": ("memory at 0x7ffdeadbeef",)},
            "memory address",
        ),
    ],
)
def test_profile_public_projection_content_fails_closed(
    overrides: dict[str, object],
    forbidden_class: str,
):
    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match=forbidden_class,
    ):
        sample_profile(**overrides)


def test_projection_rechecks_forbidden_content_before_emitting_public_values():
    profile = sample_profile()
    object.__setattr__(profile, "profile_id", "password=private-secret")

    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match="secret material",
    ):
        profile.to_dict()


def test_profile_exposes_no_decision_score_recommendation_or_lifecycle_state():
    forbidden = {
        "approval",
        "approved",
        "decision",
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
        "pass_fail",
        "success",
        "pass",
        "fail",
        "causal_effect",
        "calibration",
        "policy_learning",
    }

    assert forbidden.isdisjoint(field.name for field in fields(MarketTestEvidenceProfile))


def test_module_has_no_external_system_or_generated_identity_dependencies():
    module_path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "commerce_opportunity_intelligence"
        / "market_test_evidence.py"
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
