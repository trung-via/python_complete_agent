"""Tests for bounded canonical product-family admission."""

from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from src.product_intelligence import (
    CanonicalFamilyAdmissionError,
    CanonicalProductFamily,
    EntityResolutionResult,
    FamilyMergeDecision,
    MultiObservationResolutionGraph,
    ProductRelationship,
    ResolutionEvidence,
    SourceObservationIdentity,
    create_canonical_family,
    create_family_merge_decision_record,
    create_family_merge_proposal,
    group_resolution_graph,
)


def identity(name: str) -> SourceObservationIdentity:
    return SourceObservationIdentity(
        source_pack_id=f"pack-{name}",
        platform="test-market",
        source_product_id=name,
        product_url=f"https://market.example/{name}",
        observed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def approved_decision():
    a, b, c = identity("a"), identity("b"), identity("c")
    graph = MultiObservationResolutionGraph(
        observations=(c, a, b),
        pairwise_results=(
            EntityResolutionResult(
                relationship=ProductRelationship.UNCERTAIN,
                confidence=0.23,
                left=c,
                right=a,
                reasons=("direct uncertainty retained",),
                evidence=(ResolutionEvidence("AC-UNCERTAIN", "preserved"),),
            ),
            EntityResolutionResult(
                relationship=ProductRelationship.EXACT_VARIANT_MATCH,
                confidence=0.98,
                left=b,
                right=c,
                reasons=("exact pair retained",),
                evidence=(ResolutionEvidence("BC-EXACT", "preserved"),),
            ),
            EntityResolutionResult(
                relationship=ProductRelationship.SAME_PRODUCT_FAMILY,
                confidence=0.86,
                left=a,
                right=b,
                reasons=("family pair retained",),
                evidence=(ResolutionEvidence("AB-FAMILY", "preserved"),),
            ),
        ),
        conflicts=(),
    )
    proposal = create_family_merge_proposal(
        graph,
        group_resolution_graph(graph).groups[0],
    )
    return create_family_merge_decision_record(
        proposal,
        decision=FamilyMergeDecision.APPROVE,
        actor="human-reviewer",
        decided_at=datetime(2026, 8, 31, 9, 30, tzinfo=timezone.utc),
    )


def test_approve_admits_exact_members_identity_and_provenance():
    decision = approved_decision()

    family = create_canonical_family(
        decision,
        family_id="external:Family Ω/001",
    )

    assert isinstance(family, CanonicalProductFamily)
    assert family.family_id == "external:Family Ω/001"
    assert family.members is decision.proposal.members
    assert family.approval is decision
    assert family.member_count == len(decision.proposal.members)
    assert tuple(item.relationship for item in family.approval.proposal.pair_evidence) == (
        ProductRelationship.SAME_PRODUCT_FAMILY,
        ProductRelationship.UNCERTAIN,
        ProductRelationship.EXACT_VARIANT_MATCH,
    )


def test_reject_and_wrong_decision_record_types_fail_closed():
    approved = approved_decision()
    rejected = create_family_merge_decision_record(
        approved.proposal,
        decision=FamilyMergeDecision.REJECT,
        actor="human-reviewer",
        decided_at=approved.decided_at,
    )

    for invalid in (rejected, approved.proposal, object(), None):
        with pytest.raises(CanonicalFamilyAdmissionError):
            create_canonical_family(invalid, family_id="family-001")


@pytest.mark.parametrize(
    "family_id",
    [None, 1, True, "", " ", " family", "family ", "family\nnext", "family\rnext", "family\x00id"],
)
def test_family_id_validation_fails_closed(family_id):
    with pytest.raises(CanonicalFamilyAdmissionError, match="family_id"):
        create_canonical_family(approved_decision(), family_id=family_id)


def test_result_is_immutable_deterministic_and_cannot_be_forged_directly():
    decision = approved_decision()
    first = create_canonical_family(decision, family_id="family-001")
    second = create_canonical_family(decision, family_id="family-001")

    assert first == second
    with pytest.raises(FrozenInstanceError):
        first.family_id = "replacement"
    with pytest.raises(FrozenInstanceError):
        first.members = ()
    with pytest.raises(CanonicalFamilyAdmissionError, match="must be created"):
        CanonicalProductFamily(
            family_id="family-001",
            members=decision.proposal.members,
            approval=decision,
        )


def test_admission_reexecutes_nothing_and_performs_no_external_side_effect():
    decision = approved_decision()

    with (
        patch("src.product_intelligence.entity_resolution.resolve_product_entities") as pairwise,
        patch("src.product_intelligence.entity_resolution_graph.resolve_multi_observations") as multi,
        patch("src.product_intelligence.entity_grouping.group_resolution_graph") as grouping,
        patch("src.product_intelligence.family_merge_approval.create_family_merge_proposal") as proposal,
        patch("uuid.uuid4") as uuid_generator,
        patch("random.random") as random_generator,
        patch("time.time") as clock,
        patch("os.getenv") as environment,
        patch("builtins.open") as filesystem_open,
    ):
        family = create_canonical_family(decision, family_id="family-001")

    pairwise.assert_not_called()
    multi.assert_not_called()
    grouping.assert_not_called()
    proposal.assert_not_called()
    uuid_generator.assert_not_called()
    random_generator.assert_not_called()
    clock.assert_not_called()
    environment.assert_not_called()
    filesystem_open.assert_not_called()
    assert family.approval is decision


def test_public_record_exposes_no_variant_profile_or_catalog_authority():
    family = create_canonical_family(approved_decision(), family_id="family-001")
    assert tuple(field.name for field in fields(family)) == (
        "family_id",
        "members",
        "approval",
    )
    forbidden = {
        "product_id",
        "variant_id",
        "group_id",
        "proposal_id",
        "aggregate_confidence",
        "merge_confidence",
        "canonical_profile",
        "automatic_merge",
        "persist",
        "catalog",
    }
    assert forbidden.isdisjoint(dir(family))
