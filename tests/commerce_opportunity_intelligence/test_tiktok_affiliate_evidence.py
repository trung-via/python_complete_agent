"""Focused deterministic tests for the bounded P7.4 semantic authority."""

from __future__ import annotations

import ast
import json
from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.commerce_opportunity_intelligence import (
    COMMERCE_OPPORTUNITY_INTELLIGENCE_P7_4,
    TIKTOK_AFFILIATE_EVIDENCE_DIMENSIONS,
    DecisionContext,
    OpportunityHypothesis,
    OpportunityIntelligenceValidationError,
    create_tiktok_affiliate_evidence_profile,
)
from src.commerce_opportunity_intelligence.tiktok_affiliate_evidence import (
    TikTokAffiliateEvidenceProfile,
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
        "competition_saturation": ("ref://evidence/competition/1",),
    }
    values.update(overrides)
    return TikTokAffiliateEvidenceProfile(**values)  # type: ignore[arg-type]


def test_authority_identifier_and_ordered_dimensions():
    assert (
        COMMERCE_OPPORTUNITY_INTELLIGENCE_P7_4
        == "COMMERCE_OPPORTUNITY_INTELLIGENCE_P7_4"
    )
    assert TIKTOK_AFFILIATE_EVIDENCE_DIMENSIONS == (
        "affiliate_economics",
        "market_traction",
        "creator_ecosystem",
        "content_activity",
        "audience_channel_fit",
        "competition_saturation",
    )


def test_valid_profile_preserves_caller_values_and_order():
    profile = sample_profile(
        market_traction=("ref://evidence/traction/b", "ref://evidence/traction/a"),
    )

    assert profile.profile_id == "profile-tiktok-101"
    assert profile.decision_context_id == "decision-context-7"
    assert profile.hypothesis_id == "hypothesis-11"
    assert profile.as_of is AS_OF
    assert profile.affiliate_economics == ("ref://evidence/economics/1",)
    assert profile.market_traction == (
        "ref://evidence/traction/b",
        "ref://evidence/traction/a",
    )
    assert profile.creator_ecosystem == ("ref://evidence/creators/1",)
    assert profile.content_activity == ("ref://evidence/content/1",)
    assert profile.audience_channel_fit == ("ref://evidence/audience/1",)
    assert profile.competition_saturation == ("ref://evidence/competition/1",)


def test_empty_dimensions_are_allowed_and_truthfully_projected():
    profile = sample_profile(
        affiliate_economics=(),
        market_traction=(),
        creator_ecosystem=(),
        content_activity=(),
        audience_channel_fit=(),
        competition_saturation=(),
    )

    assert profile.represented_dimensions() == ()
    assert profile.unrepresented_dimensions() == TIKTOK_AFFILIATE_EVIDENCE_DIMENSIONS

    projection = profile.to_dict()
    assert projection["represented_dimensions"] == []
    assert projection["unrepresented_dimensions"] == list(
        TIKTOK_AFFILIATE_EVIDENCE_DIMENSIONS
    )
    assert projection["affiliate_economics"] == []


def test_partial_dimension_representation_preserves_fixed_order():
    profile = sample_profile(
        affiliate_economics=("ref://evidence/economics/1",),
        market_traction=(),
        creator_ecosystem=(),
        content_activity=("ref://evidence/content/1",),
        audience_channel_fit=(),
        competition_saturation=(),
    )

    assert profile.represented_dimensions() == (
        "affiliate_economics",
        "content_activity",
    )
    assert profile.unrepresented_dimensions() == (
        "market_traction",
        "creator_ecosystem",
        "audience_channel_fit",
        "competition_saturation",
    )


def test_same_opaque_reference_may_appear_across_different_dimensions():
    shared_ref = "ref://evidence/shared-creator-and-content/42"
    profile = sample_profile(
        creator_ecosystem=(shared_ref,),
        content_activity=(shared_ref,),
    )

    assert shared_ref in profile.creator_ecosystem
    assert shared_ref in profile.content_activity


def test_pure_factory_binds_profile_to_exact_context_and_hypothesis():
    dc = sample_context()
    oh = sample_hypothesis()

    profile = create_tiktok_affiliate_evidence_profile(
        decision_context=dc,
        hypothesis=oh,
        profile_id="profile-factory-1",
        as_of=AS_OF,
        affiliate_economics=["ref://econ/1"],
        market_traction=["ref://traction/1"],
    )

    assert profile.profile_id == "profile-factory-1"
    assert profile.decision_context_id == dc.context_id
    assert profile.hypothesis_id == oh.hypothesis_id
    assert profile.as_of is AS_OF
    assert profile.affiliate_economics == ("ref://econ/1",)
    assert profile.market_traction == ("ref://traction/1",)
    assert profile.creator_ecosystem == ()


def test_pure_factory_accepts_opportunity_hypothesis_keyword():
    dc = sample_context()
    oh = sample_hypothesis()

    profile = create_tiktok_affiliate_evidence_profile(
        decision_context=dc,
        opportunity_hypothesis=oh,
        profile_id="profile-factory-kw",
        as_of=AS_OF,
    )

    assert profile.hypothesis_id == oh.hypothesis_id


def test_factory_rejects_mismatched_context_binding():
    dc = sample_context(context_id="context-alpha")
    oh = sample_hypothesis(decision_context_id="context-beta")

    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match="must match the supplied DecisionContext",
    ):
        create_tiktok_affiliate_evidence_profile(
            decision_context=dc,
            hypothesis=oh,
            profile_id="profile-bad-binding",
            as_of=AS_OF,
        )


def test_factory_rejects_invalid_context_or_hypothesis_types():
    dc = sample_context()
    oh = sample_hypothesis()

    with pytest.raises(OpportunityIntelligenceValidationError, match="must be a DecisionContext"):
        create_tiktok_affiliate_evidence_profile(
            decision_context="not-a-context",  # type: ignore[arg-type]
            hypothesis=oh,
            profile_id="p1",
            as_of=AS_OF,
        )

    with pytest.raises(OpportunityIntelligenceValidationError, match="must be an OpportunityHypothesis"):
        create_tiktok_affiliate_evidence_profile(
            decision_context=dc,
            hypothesis="not-a-hypothesis",  # type: ignore[arg-type]
            profile_id="p1",
            as_of=AS_OF,
        )

    with pytest.raises(OpportunityIntelligenceValidationError, match="must be an OpportunityHypothesis"):
        create_tiktok_affiliate_evidence_profile(
            decision_context=dc,
            profile_id="p1",
            as_of=AS_OF,
        )


@pytest.mark.parametrize("dim", TIKTOK_AFFILIATE_EVIDENCE_DIMENSIONS)
def test_factory_rejects_unordered_collections(dim: str):
    dc = sample_context()
    oh = sample_hypothesis()

    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match="ordered collection",
    ):
        create_tiktok_affiliate_evidence_profile(
            decision_context=dc,
            hypothesis=oh,
            profile_id="profile-factory-unordered",
            as_of=AS_OF,
            **{dim: {"ref://evidence/1", "ref://evidence/2"}},
        )


def test_factory_preserves_ordered_caller_input_across_all_dimensions():
    dc = sample_context()
    oh = sample_hypothesis()

    ordered_inputs = {
        "affiliate_economics": ["ref://econ/2", "ref://econ/1"],
        "market_traction": ("ref://traction/z", "ref://traction/a"),
        "creator_ecosystem": ["ref://creators/beta", "ref://creators/alpha"],
        "content_activity": ("ref://content/second", "ref://content/first"),
        "audience_channel_fit": ["ref://audience/b", "ref://audience/a"],
        "competition_saturation": ("ref://comp/2", "ref://comp/1"),
    }

    profile = create_tiktok_affiliate_evidence_profile(
        decision_context=dc,
        hypothesis=oh,
        profile_id="profile-factory-ordered",
        as_of=AS_OF,
        **ordered_inputs,
    )

    for dim, expected in ordered_inputs.items():
        assert getattr(profile, dim) == tuple(expected)


@pytest.mark.parametrize("dim", TIKTOK_AFFILIATE_EVIDENCE_DIMENSIONS)
def test_factory_preserves_ordered_caller_input_for_each_dimension(dim: str):
    dc = sample_context()
    oh = sample_hypothesis()
    ordered_items = [f"ref://{dim}/second", f"ref://{dim}/first"]

    profile = create_tiktok_affiliate_evidence_profile(
        decision_context=dc,
        hypothesis=oh,
        profile_id=f"profile-factory-order-{dim}",
        as_of=AS_OF,
        **{dim: ordered_items},
    )

    assert getattr(profile, dim) == (f"ref://{dim}/second", f"ref://{dim}/first")


@pytest.mark.parametrize("name", ["profile_id", "decision_context_id", "hypothesis_id"])
def test_identity_fields_fail_closed_when_blank_or_non_string(name: str):
    with pytest.raises(OpportunityIntelligenceValidationError, match="must not be blank"):
        sample_profile(**{name: "  \t "})
    with pytest.raises(OpportunityIntelligenceValidationError, match="must be a string"):
        sample_profile(**{name: 12345})


def test_identity_fields_are_bounded_and_single_line():
    with pytest.raises(OpportunityIntelligenceValidationError, match="at most 256"):
        sample_profile(profile_id="x" * 257)

    with pytest.raises(OpportunityIntelligenceValidationError, match="single-line"):
        sample_profile(profile_id="profile\nid")


def test_as_of_must_be_timezone_aware():
    with pytest.raises(OpportunityIntelligenceValidationError, match="timezone-aware"):
        sample_profile(as_of=datetime(2026, 9, 16, 8, 30))


@pytest.mark.parametrize("dim", TIKTOK_AFFILIATE_EVIDENCE_DIMENSIONS)
def test_dimension_refs_fail_closed_on_duplicates_within_dimension(dim: str):
    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match="must not contain duplicate values",
    ):
        sample_profile(**{dim: ("ref://evidence/dup", "ref://evidence/dup")})


@pytest.mark.parametrize("dim", TIKTOK_AFFILIATE_EVIDENCE_DIMENSIONS)
def test_dimension_refs_fail_closed_on_blank_or_non_string(dim: str):
    with pytest.raises(OpportunityIntelligenceValidationError, match="must not be blank"):
        sample_profile(**{dim: ("   ",)})
    with pytest.raises(OpportunityIntelligenceValidationError, match="must be a string"):
        sample_profile(**{dim: (123,)})


@pytest.mark.parametrize("dim", TIKTOK_AFFILIATE_EVIDENCE_DIMENSIONS)
def test_dimension_refs_must_be_single_line_and_bounded(dim: str):
    with pytest.raises(OpportunityIntelligenceValidationError, match="single-line"):
        sample_profile(**{dim: ("ref://evidence\nmultiline",)})
    with pytest.raises(OpportunityIntelligenceValidationError, match="single-line"):
        sample_profile(**{dim: ("ref://evidence\rcarriage",)})
    with pytest.raises(OpportunityIntelligenceValidationError, match="at most 512"):
        sample_profile(**{dim: ("x" * 513,)})


@pytest.mark.parametrize("dim", TIKTOK_AFFILIATE_EVIDENCE_DIMENSIONS)
def test_dimension_refs_reject_unordered_collections(dim: str):
    with pytest.raises(OpportunityIntelligenceValidationError, match="ordered collection"):
        sample_profile(**{dim: {"ref://evidence/1", "ref://evidence/2"}})


def test_profile_projection_is_stable_and_json_serializable():
    profile = sample_profile(
        affiliate_economics=("ref://econ/2", "ref://econ/1"),
        market_traction=(),
    )

    expected = {
        "profile_id": "profile-tiktok-101",
        "decision_context_id": "decision-context-7",
        "hypothesis_id": "hypothesis-11",
        "as_of": "2026-09-16T08:30:00+07:00",
        "affiliate_economics": ["ref://econ/2", "ref://econ/1"],
        "market_traction": [],
        "creator_ecosystem": ["ref://evidence/creators/1"],
        "content_activity": ["ref://evidence/content/1"],
        "audience_channel_fit": ["ref://evidence/audience/1"],
        "competition_saturation": ["ref://evidence/competition/1"],
        "represented_dimensions": [
            "affiliate_economics",
            "creator_ecosystem",
            "content_activity",
            "audience_channel_fit",
            "competition_saturation",
        ],
        "unrepresented_dimensions": [
            "market_traction",
        ],
    }

    assert profile.to_dict() == expected
    assert json.loads(json.dumps(profile.to_dict())) == expected


@pytest.mark.parametrize(
    ("overrides", "forbidden_class"),
    [
        (
            {"affiliate_economics": ("ref://api_key=super-secret-value",)},
            "secret material",
        ),
        (
            {"creator_ecosystem": ("ref://Bearer eyJhbGciOi...",)},
            "secret material",
        ),
        (
            {"content_activity": ("ref://<script>alert(1)</script>",)},
            "raw HTML",
        ),
        (
            {"audience_channel_fit": ("Cookie: sessionid=secret",)},
            "cookie or session",
        ),
        (
            {"competition_saturation": ("<|system|> prompt leak",)},
            "model prompt",
        ),
        (
            {"market_traction": ('{"run_id":"RUN-222-001"}',)},
            "hidden execution metadata",
        ),
        (
            {"profile_id": "<Object at 0x7ffdeadbeef>"},
            "object representation",
        ),
        (
            {"affiliate_economics": ("memory at 0x7ffdeadbeef",)},
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


def test_values_are_immutable_and_collections_are_frozen():
    caller_list = ["ref://econ/1", "ref://econ/2"]
    profile = sample_profile(affiliate_economics=caller_list)

    caller_list.append("ref://econ/mutated")
    assert profile.affiliate_economics == ("ref://econ/1", "ref://econ/2")

    with pytest.raises(FrozenInstanceError):
        profile.profile_id = "new-id"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        profile.affiliate_economics = ("new",)  # type: ignore[misc]


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
    }

    assert forbidden.isdisjoint(field.name for field in fields(TikTokAffiliateEvidenceProfile))


def test_module_has_no_external_system_or_generated_identity_dependencies():
    module_path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "commerce_opportunity_intelligence"
        / "tiktok_affiliate_evidence.py"
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
