"""Regressions for explicit sellable-variant proposal and Human decisions."""

from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timezone
from itertools import combinations
from unittest.mock import patch

import pytest

from src.product_intelligence import (
    CanonicalProductFamily,
    EntityResolutionResult,
    FamilyMergeDecision,
    MultiObservationResolutionGraph,
    ProductRelationship,
    ResolutionEvidence,
    SellableVariantApprovalError,
    SellableVariantDecision,
    SellableVariantDecisionRecord,
    SellableVariantProposal,
    SourceObservationIdentity,
    create_canonical_family,
    create_family_merge_decision_record,
    create_family_merge_proposal,
    create_sellable_variant_decision_record,
    create_sellable_variant_proposal,
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


def family_from_relationships(
    relationships: dict[tuple[str, str], ProductRelationship],
) -> CanonicalProductFamily:
    names = sorted({name for pair in relationships for name in pair})
    identities = {name: identity(name) for name in names}
    results = []
    for left_name, right_name in combinations(names, 2):
        relationship = relationships[(left_name, right_name)]
        code = f"{left_name}{right_name}-{relationship.value}"
        results.append(
            EntityResolutionResult(
                relationship=relationship,
                confidence=0.97,
                left=identities[right_name],
                right=identities[left_name],
                reasons=(code,),
                evidence=(ResolutionEvidence(code, "preserved"),),
            )
        )
    graph = MultiObservationResolutionGraph(
        observations=tuple(reversed(tuple(identities.values()))),
        pairwise_results=tuple(reversed(results)),
        conflicts=(),
    )
    family_proposal = create_family_merge_proposal(
        graph,
        group_resolution_graph(graph).groups[0],
    )
    family_decision = create_family_merge_decision_record(
        family_proposal,
        decision=FamilyMergeDecision.APPROVE,
        actor="family-reviewer",
        decided_at=datetime(2026, 8, 31, 8, 0, tzinfo=timezone.utc),
    )
    return create_canonical_family(
        family_decision,
        family_id="family-sellable-variant-approval",
    )


def isolated_family() -> CanonicalProductFamily:
    return family_from_relationships(
        {
            ("a", "b"): ProductRelationship.EXACT_VARIANT_MATCH,
            ("a", "c"): ProductRelationship.SAME_PRODUCT_FAMILY,
            ("b", "c"): ProductRelationship.SAME_PRODUCT_FAMILY,
        }
    )


def member(family: CanonicalProductFamily, name: str) -> SourceObservationIdentity:
    return next(value for value in family.members if value.source_product_id == name)


def test_explicit_pair_and_isolated_singleton_preserve_projection_and_exact_objects():
    family = isolated_family()
    a, b, c = (member(family, name) for name in ("a", "b", "c"))
    preserved_ab = next(
        pair
        for pair in family.approval.proposal.pair_evidence
        if {pair.left.source_product_id, pair.right.source_product_id} == {"a", "b"}
    )

    pair_proposal = create_sellable_variant_proposal(family, (b, a))
    singleton_proposal = create_sellable_variant_proposal(family, (c,))

    assert pair_proposal.source_family is family
    assert pair_proposal.projection.source_family is family
    assert pair_proposal.evidence_projection is pair_proposal.projection
    assert pair_proposal.members == (a, b)
    assert pair_proposal.selected_members is pair_proposal.members
    assert pair_proposal.pair_evidence == (preserved_ab,)
    assert pair_proposal.pair_evidence[0] is preserved_ab
    assert singleton_proposal.members == (c,)
    assert singleton_proposal.pair_evidence == ()
    assert tuple(field.name for field in fields(pair_proposal)) == (
        "projection",
        "members",
        "pair_evidence",
    )


@pytest.mark.parametrize(
    "selected",
    [
        None,
        [],
        (),
        "a",
    ],
)
def test_wrong_or_empty_selection_container_fails_closed(selected):
    with pytest.raises(SellableVariantApprovalError):
        create_sellable_variant_proposal(isolated_family(), selected)


def test_duplicate_outside_and_wrong_family_inputs_fail_closed():
    family = isolated_family()
    a = member(family, "a")
    outside = identity("outside")

    for selected in ((a, a), (outside,), (a, outside)):
        with pytest.raises(SellableVariantApprovalError):
            create_sellable_variant_proposal(family, selected)
    for invalid_family in (family.approval, object(), None):
        with pytest.raises(SellableVariantApprovalError):
            create_sellable_variant_proposal(invalid_family, (a,))


@pytest.mark.parametrize(
    "nonexact",
    [
        ProductRelationship.SAME_PRODUCT_FAMILY,
        ProductRelationship.UNCERTAIN,
        ProductRelationship.DIFFERENT_PRODUCT,
    ],
)
def test_selected_nonexact_pair_fails_even_with_other_exact_connectivity(nonexact):
    family = family_from_relationships(
        {
            ("a", "b"): ProductRelationship.EXACT_VARIANT_MATCH,
            ("a", "c"): nonexact,
            ("b", "c"): ProductRelationship.EXACT_VARIANT_MATCH,
        }
    )
    a, b, c = (member(family, name) for name in ("a", "b", "c"))

    with pytest.raises(SellableVariantApprovalError):
        create_sellable_variant_proposal(family, (c, a, b))


@pytest.mark.parametrize(
    "gap_relationship",
    [ProductRelationship.UNCERTAIN, ProductRelationship.SAME_PRODUCT_FAMILY],
)
def test_exactness_gap_rejects_full_pairs_and_every_singleton(gap_relationship):
    family = family_from_relationships(
        {
            ("a", "b"): ProductRelationship.EXACT_VARIANT_MATCH,
            ("a", "c"): gap_relationship,
            ("b", "c"): ProductRelationship.EXACT_VARIANT_MATCH,
        }
    )
    a, b, c = (member(family, name) for name in ("a", "b", "c"))

    for selected in ((a, b, c), (a, b), (b, c), (a,), (b,), (c,)):
        with pytest.raises(SellableVariantApprovalError):
            create_sellable_variant_proposal(family, selected)


def test_internal_nonexact_and_crossing_exact_edges_each_fail_closed():
    family = family_from_relationships(
        {
            ("a", "b"): ProductRelationship.EXACT_VARIANT_MATCH,
            ("a", "c"): ProductRelationship.EXACT_VARIANT_MATCH,
            ("b", "c"): ProductRelationship.SAME_PRODUCT_FAMILY,
            ("a", "d"): ProductRelationship.SAME_PRODUCT_FAMILY,
            ("b", "d"): ProductRelationship.SAME_PRODUCT_FAMILY,
            ("c", "d"): ProductRelationship.SAME_PRODUCT_FAMILY,
        }
    )
    a, b, c = (member(family, name) for name in ("a", "b", "c"))

    with pytest.raises(SellableVariantApprovalError):
        create_sellable_variant_proposal(family, (a, b))
    with pytest.raises(SellableVariantApprovalError):
        create_sellable_variant_proposal(family, (a, b, c))


def test_proposal_is_immutable_factory_only_and_deterministic():
    family = isolated_family()
    a, b = member(family, "a"), member(family, "b")
    first = create_sellable_variant_proposal(family, (a, b))
    second = create_sellable_variant_proposal(family, (b, a))

    assert first == second
    assert first.projection == second.projection
    assert first.projection is not second.projection
    assert first.pair_evidence[0] is second.pair_evidence[0]
    with pytest.raises(FrozenInstanceError):
        first.members = ()
    with pytest.raises(SellableVariantApprovalError):
        SellableVariantProposal(
            projection=first.projection,
            members=first.members,
            pair_evidence=first.pair_evidence,
        )


@pytest.mark.parametrize(
    "decision",
    [SellableVariantDecision.APPROVE, SellableVariantDecision.REJECT],
)
def test_explicit_human_approve_and_reject_are_immutable_and_bounded(decision):
    family = isolated_family()
    proposal = create_sellable_variant_proposal(
        family,
        (member(family, "a"), member(family, "b")),
    )
    decided_at = datetime(2026, 8, 31, 10, 15, tzinfo=timezone.utc)

    record = create_sellable_variant_decision_record(
        proposal,
        decision=decision,
        actor="variant-reviewer",
        decided_at=decided_at,
    )

    assert record.proposal is proposal
    assert record.decision is decision
    assert record.actor == "variant-reviewer"
    assert record.decided_at is decided_at
    with pytest.raises(FrozenInstanceError):
        record.decision = SellableVariantDecision.REJECT
    forbidden = {
        "variant_id",
        "profile",
        "aggregate_confidence",
        "persist",
        "catalog",
        "unselected_relationships",
        "complete_partition",
    }
    assert forbidden.isdisjoint(dir(record))


@pytest.mark.parametrize("invalid_proposal", [object(), None])
def test_decision_rejects_noncanonical_proposals(invalid_proposal):
    with pytest.raises(SellableVariantApprovalError):
        create_sellable_variant_decision_record(
            invalid_proposal,
            decision=SellableVariantDecision.APPROVE,
            actor="reviewer",
            decided_at=datetime(2026, 8, 31, tzinfo=timezone.utc),
        )


def test_decision_rejects_invalid_decision_actor_and_time():
    family = isolated_family()
    proposal = create_sellable_variant_proposal(family, (member(family, "c"),))
    aware = datetime(2026, 8, 31, tzinfo=timezone.utc)

    invalid_values = (
        {"decision": "APPROVE", "actor": "reviewer", "decided_at": aware},
        {"decision": None, "actor": "reviewer", "decided_at": aware},
        {"decision": SellableVariantDecision.APPROVE, "actor": "", "decided_at": aware},
        {"decision": SellableVariantDecision.APPROVE, "actor": "  ", "decided_at": aware},
        {"decision": SellableVariantDecision.APPROVE, "actor": "a\nb", "decided_at": aware},
        {"decision": SellableVariantDecision.APPROVE, "actor": "a\x00b", "decided_at": aware},
        {
            "decision": SellableVariantDecision.APPROVE,
            "actor": "reviewer",
            "decided_at": datetime(2026, 8, 31),
        },
        {"decision": SellableVariantDecision.APPROVE, "actor": "reviewer", "decided_at": None},
    )
    for values in invalid_values:
        with pytest.raises(SellableVariantApprovalError):
            create_sellable_variant_decision_record(proposal, **values)


def test_proposal_calls_projection_once_and_reexecutes_no_upstream_or_external_work():
    family = isolated_family()
    a, b = member(family, "a"), member(family, "b")

    with (
        patch(
            "src.product_intelligence.sellable_variant_approval.project_sellable_variant_evidence",
            wraps=__import__(
                "src.product_intelligence.sellable_variant_evidence",
                fromlist=["project_sellable_variant_evidence"],
            ).project_sellable_variant_evidence,
        ) as projection,
        patch("src.product_intelligence.entity_resolution.resolve_product_entities") as pairwise,
        patch("src.product_intelligence.entity_resolution_graph.resolve_multi_observations") as multi,
        patch("src.product_intelligence.entity_grouping.group_resolution_graph") as grouping,
        patch("src.product_intelligence.family_merge_approval.create_family_merge_proposal") as family_proposal,
        patch("src.product_intelligence.canonical_family.create_canonical_family") as admission,
        patch("uuid.uuid4") as uuid_generator,
        patch("random.random") as random_generator,
        patch("time.time") as clock,
        patch("os.getenv") as environment,
        patch("builtins.open") as filesystem_open,
    ):
        proposal = create_sellable_variant_proposal(family, (b, a))

    projection.assert_called_once_with(family)
    pairwise.assert_not_called()
    multi.assert_not_called()
    grouping.assert_not_called()
    family_proposal.assert_not_called()
    admission.assert_not_called()
    uuid_generator.assert_not_called()
    random_generator.assert_not_called()
    clock.assert_not_called()
    environment.assert_not_called()
    filesystem_open.assert_not_called()
    assert proposal.members == (a, b)


def test_decision_performs_no_projection_or_external_work():
    family = isolated_family()
    proposal = create_sellable_variant_proposal(family, (member(family, "c"),))

    with (
        patch("src.product_intelligence.sellable_variant_approval.project_sellable_variant_evidence") as projection,
        patch("uuid.uuid4") as uuid_generator,
        patch("random.random") as random_generator,
        patch("time.time") as clock,
        patch("os.getenv") as environment,
        patch("builtins.open") as filesystem_open,
    ):
        record = create_sellable_variant_decision_record(
            proposal,
            decision=SellableVariantDecision.REJECT,
            actor="reviewer",
            decided_at=datetime(2026, 8, 31, tzinfo=timezone.utc),
        )

    projection.assert_not_called()
    uuid_generator.assert_not_called()
    random_generator.assert_not_called()
    clock.assert_not_called()
    environment.assert_not_called()
    filesystem_open.assert_not_called()
    assert record.proposal is proposal
