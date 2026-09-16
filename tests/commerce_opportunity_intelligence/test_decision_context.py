"""Focused deterministic tests for the bounded P7.3 semantic authority."""

from __future__ import annotations

import ast
import json
from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.commerce_opportunity_intelligence import (
    COMMERCE_OPPORTUNITY_INTELLIGENCE_P7_3,
    DecisionContext,
    OpportunityHypothesis,
    OpportunityIntelligenceValidationError,
    create_opportunity_hypothesis,
)


AS_OF = datetime(2026, 9, 16, 8, 30, tzinfo=timezone(timedelta(hours=7)))
CREATED_AT = datetime(2026, 9, 16, 9, 45, tzinfo=timezone.utc)


def context(**overrides: object) -> DecisionContext:
    values: dict[str, object] = {
        "context_id": "decision-context-7",
        "decision_question": "Should this subject receive deeper opportunity research?",
        "objective": "Identify a bounded affiliate opportunity worth testing.",
        "as_of": AS_OF,
    }
    values.update(overrides)
    return DecisionContext(**values)  # type: ignore[arg-type]


def hypothesis(**overrides: object) -> OpportunityHypothesis:
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


def test_authority_identifier_and_valid_context_preserve_caller_values_and_order():
    value = context(
        market="Vietnam",
        audience="Value-seeking mobile shoppers",
        channel="TikTok Affiliate",
        time_horizon="Thirty days",
        decision_deadline=AS_OF + timedelta(days=2),
        constraints=("No inventory ownership", "Human approval before spend"),
        alternatives=("Research candidate B", "Stop research"),
        economic_constraints=("Positive contribution margin", "Budget <= 5000000 VND"),
        risk_constraints=("No unapproved claims", "Refund exposure must be bounded"),
    )

    assert (
        COMMERCE_OPPORTUNITY_INTELLIGENCE_P7_3
        == "COMMERCE_OPPORTUNITY_INTELLIGENCE_P7_3"
    )
    assert value.context_id == "decision-context-7"
    assert value.as_of is AS_OF
    assert value.constraints == (
        "No inventory ownership",
        "Human approval before spend",
    )
    assert value.alternatives == ("Research candidate B", "Stop research")
    assert value.economic_constraints[0] == "Positive contribution margin"
    assert value.risk_constraints[1] == "Refund exposure must be bounded"


def test_optional_context_dimensions_remain_explicitly_absent():
    value = context()

    assert value.market is None
    assert value.audience is None
    assert value.channel is None
    assert value.time_horizon is None
    assert value.decision_deadline is None
    assert value.constraints == ()
    assert value.alternatives == ()
    assert value.economic_constraints == ()
    assert value.risk_constraints == ()
    assert value.to_dict()["market"] is None


@pytest.mark.parametrize("name", ["context_id", "decision_question", "objective"])
def test_required_context_text_fails_closed_when_blank(name: str):
    with pytest.raises(OpportunityIntelligenceValidationError, match="must not be blank"):
        context(**{name: " \t "})


@pytest.mark.parametrize("name", ["as_of", "decision_deadline"])
def test_context_timestamps_must_be_timezone_aware(name: str):
    values = {name: datetime(2026, 9, 16, 8, 30)}
    with pytest.raises(OpportunityIntelligenceValidationError, match="timezone-aware"):
        context(**values)


def test_context_deadline_cannot_precede_as_of():
    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match="must not precede as_of",
    ):
        context(decision_deadline=AS_OF - timedelta(microseconds=1))


@pytest.mark.parametrize(
    ("name", "values"),
    [
        ("constraints", ("one", "one")),
        ("alternatives", ("one", "")),
        ("economic_constraints", ("one", " \n")),
        ("risk_constraints", {"unordered", "collection"}),
    ],
)
def test_context_collections_reject_duplicates_blanks_and_unordered_values(
    name: str,
    values: object,
):
    with pytest.raises(OpportunityIntelligenceValidationError):
        context(**{name: values})


def test_context_text_values_are_bounded():
    with pytest.raises(OpportunityIntelligenceValidationError, match="at most 256"):
        context(context_id="x" * 257)
    with pytest.raises(OpportunityIntelligenceValidationError, match="at most 4096"):
        context(constraints=("x" * 4097,))


def test_context_projection_is_stable_json_serializable_and_order_preserving():
    value = context(
        market="VN",
        constraints=("second only by caller wording", "first only by caller wording"),
        alternatives=("alternative-z", "alternative-a"),
    )

    expected = {
        "context_id": "decision-context-7",
        "decision_question": "Should this subject receive deeper opportunity research?",
        "objective": "Identify a bounded affiliate opportunity worth testing.",
        "as_of": "2026-09-16T08:30:00+07:00",
        "market": "VN",
        "audience": None,
        "channel": None,
        "time_horizon": None,
        "decision_deadline": None,
        "constraints": ["second only by caller wording", "first only by caller wording"],
        "alternatives": ["alternative-z", "alternative-a"],
        "economic_constraints": [],
        "risk_constraints": [],
    }
    assert value.to_dict() == expected
    assert value.to_dict() == expected
    assert json.loads(json.dumps(value.to_dict())) == expected


def test_valid_hypothesis_is_falsifiable_and_preserves_opaque_subject_and_times():
    value = hypothesis()

    assert value.hypothesis_id == "hypothesis-11"
    assert value.decision_context_id == "decision-context-7"
    assert value.subject_ref == "opaque://candidate/not-validated?source=x#variant-y"
    assert value.created_at is CREATED_AT
    assert value.supporting_evidence_refs == (
        "evidence:external:2",
        "evidence:external:1",
    )
    assert value.disconfirming_conditions


def test_pure_factory_binds_hypothesis_to_exact_context():
    decision_context = context()
    value = create_opportunity_hypothesis(
        decision_context=decision_context,
        hypothesis_id="hypothesis-factory",
        decision_context_id="decision-context-7",
        subject_ref="caller-controlled opaque ref",
        falsifiable_claim="The bounded expected outcome will occur.",
        created_at=CREATED_AT,
        assumptions=("One explicit assumption",),
        important_unknowns=("One explicit unknown",),
        disconfirming_conditions=("The bounded expected outcome does not occur.",),
        expected_outcomes=("The bounded expected outcome occurs.",),
    )

    assert value.decision_context_id == decision_context.context_id
    assert value.subject_ref == "caller-controlled opaque ref"
    assert value.supporting_evidence_refs == ()
    assert value.counter_evidence_refs == ()


def test_factory_rejects_mismatched_context_binding():
    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match="must match the supplied DecisionContext",
    ):
        create_opportunity_hypothesis(
            decision_context=context(),
            hypothesis_id="hypothesis-wrong-context",
            decision_context_id="another-context",
            subject_ref="opaque subject",
            falsifiable_claim="A bounded outcome will occur.",
            created_at=CREATED_AT,
            disconfirming_conditions=("The bounded outcome does not occur.",),
        )


def test_hypothesis_allows_empty_supporting_and_counter_evidence():
    value = hypothesis(supporting_evidence_refs=(), counter_evidence_refs=())

    assert value.supporting_evidence_refs == ()
    assert value.counter_evidence_refs == ()


def test_hypothesis_requires_at_least_one_disconfirming_condition():
    with pytest.raises(
        OpportunityIntelligenceValidationError,
        match="at least one condition",
    ):
        hypothesis(disconfirming_conditions=())


def test_hypothesis_identity_subject_claim_and_time_fail_closed_when_malformed():
    for name in ("hypothesis_id", "decision_context_id", "subject_ref", "falsifiable_claim"):
        with pytest.raises(
            OpportunityIntelligenceValidationError,
            match="must not be blank",
        ):
            hypothesis(**{name: " \t"})

    with pytest.raises(OpportunityIntelligenceValidationError, match="timezone-aware"):
        hypothesis(created_at=datetime(2026, 9, 16, 9, 45))
    with pytest.raises(OpportunityIntelligenceValidationError, match="at most 512"):
        hypothesis(subject_ref="x" * 513)


@pytest.mark.parametrize(
    ("supporting", "counter"),
    [
        (("evidence:a", "evidence:a"), ()),
        ((), ("evidence:b", "evidence:b")),
        (("evidence:shared",), ("evidence:shared",)),
        (("",), ()),
    ],
)
def test_evidence_references_fail_closed_on_duplicates_blanks_or_overlap(
    supporting: tuple[str, ...],
    counter: tuple[str, ...],
):
    with pytest.raises(OpportunityIntelligenceValidationError):
        hypothesis(
            supporting_evidence_refs=supporting,
            counter_evidence_refs=counter,
        )


def test_hypothesis_projection_is_stable_and_json_serializable():
    projection = hypothesis().to_dict()

    assert projection == {
        "hypothesis_id": "hypothesis-11",
        "decision_context_id": "decision-context-7",
        "subject_ref": "opaque://candidate/not-validated?source=x#variant-y",
        "falsifiable_claim": (
            "The subject can produce positive contribution margin in the stated context."
        ),
        "created_at": "2026-09-16T09:45:00+00:00",
        "assumptions": ["The supplied commission terms remain available."],
        "supporting_evidence_refs": ["evidence:external:2", "evidence:external:1"],
        "counter_evidence_refs": ["evidence:external:9"],
        "important_unknowns": ["Audience conversion rate is unknown."],
        "disconfirming_conditions": [
            "Observed contribution margin is non-positive at the bounded exposure."
        ],
        "expected_outcomes": ["A measurable positive contribution margin."],
    }
    assert json.loads(json.dumps(projection)) == projection


def test_values_are_immutable_and_collections_are_frozen():
    decision_context = context(constraints=["caller list"])
    opportunity_hypothesis = hypothesis(assumptions=["caller list"])

    assert decision_context.constraints == ("caller list",)
    assert opportunity_hypothesis.assumptions == ("caller list",)
    with pytest.raises(FrozenInstanceError):
        decision_context.objective = "replacement"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        opportunity_hypothesis.falsifiable_claim = "replacement"  # type: ignore[misc]


def test_values_expose_no_decision_score_recommendation_or_lifecycle_state():
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
    }

    assert forbidden.isdisjoint(field.name for field in fields(DecisionContext))
    assert forbidden.isdisjoint(field.name for field in fields(OpportunityHypothesis))


def test_module_has_no_external_system_or_generated_identity_dependencies():
    module_path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "commerce_opportunity_intelligence"
        / "decision_context.py"
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
        "typing",
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
