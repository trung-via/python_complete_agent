"""Regressions for the bounded sellable-variant evidence projection."""

from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timezone
from itertools import combinations
from unittest.mock import patch

import pytest

from src.product_intelligence import (
    EntityResolutionResult,
    FamilyMergeDecision,
    MultiObservationResolutionGraph,
    ProductRelationship,
    ResolutionEvidence,
    SellableVariantEvidenceError,
    SourceObservationIdentity,
    create_canonical_family,
    create_family_merge_decision_record,
    create_family_merge_proposal,
    group_resolution_graph,
    project_sellable_variant_evidence,
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
):
    names = sorted({name for pair in relationships for name in pair})
    identities = {name: identity(name) for name in names}
    results = []
    for left_name, right_name in combinations(names, 2):
        relationship = relationships[(left_name, right_name)]
        code = f"{left_name}{right_name}-{relationship.value}"
        results.append(
            EntityResolutionResult(
                relationship=relationship,
                confidence={
                    ProductRelationship.EXACT_VARIANT_MATCH: 0.98,
                    ProductRelationship.SAME_PRODUCT_FAMILY: 0.86,
                    ProductRelationship.UNCERTAIN: 0.99,
                    ProductRelationship.DIFFERENT_PRODUCT: 0.99,
                }[relationship],
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
    proposal = create_family_merge_proposal(
        graph,
        group_resolution_graph(graph).groups[0],
    )
    decision = create_family_merge_decision_record(
        proposal,
        decision=FamilyMergeDecision.APPROVE,
        actor="human-reviewer",
        decided_at=datetime(2026, 8, 31, 9, 30, tzinfo=timezone.utc),
    )
    return create_canonical_family(decision, family_id="family-variant-evidence")


@pytest.mark.parametrize(
    "direct_relationship",
    [
        ProductRelationship.UNCERTAIN,
        ProductRelationship.SAME_PRODUCT_FAMILY,
        ProductRelationship.DIFFERENT_PRODUCT,
    ],
)
def test_exact_chain_preserves_direct_nonexact_pair_and_reports_one_gap(
    direct_relationship,
):
    family = family_from_relationships(
        {
            ("a", "b"): ProductRelationship.EXACT_VARIANT_MATCH,
            ("a", "c"): direct_relationship,
            ("b", "c"): ProductRelationship.EXACT_VARIANT_MATCH,
        }
    )
    pair_by_names = {
        (pair.left.source_product_id, pair.right.source_product_id): pair
        for pair in family.approval.proposal.pair_evidence
    }

    projection = project_sellable_variant_evidence(family)

    assert projection.source_family is family
    assert projection.direct_exact_evidence == (
        pair_by_names[("a", "b")],
        pair_by_names[("b", "c")],
    )
    assert all(
        projected is preserved
        for projected, preserved in zip(
            projection.direct_exact_evidence,
            (pair_by_names[("a", "b")], pair_by_names[("b", "c")]),
        )
    )
    assert projection.exactness_gap_count == 1
    gap = projection.exactness_gaps[0]
    assert gap.direct_evidence is pair_by_names[("a", "c")]
    assert gap.direct_evidence.relationship is direct_relationship
    assert gap.witness_path[0] is pair_by_names[("a", "b")]
    assert gap.witness_path[1] is pair_by_names[("b", "c")]


def test_all_exact_clique_has_no_gaps_or_variant_identity_output():
    family = family_from_relationships(
        {
            pair: ProductRelationship.EXACT_VARIANT_MATCH
            for pair in combinations(("a", "b", "c"), 2)
        }
    )

    projection = project_sellable_variant_evidence(family)

    assert projection.direct_exact_count == 3
    assert projection.exactness_gaps == ()
    assert tuple(field.name for field in fields(projection)) == (
        "source_family",
        "direct_exact_evidence",
        "exactness_gaps",
    )
    forbidden = {
        "variant_id",
        "group_id",
        "component_id",
        "aggregate_confidence",
        "canonical_profile",
        "human_decision",
        "auto_merge",
        "persist",
        "catalog",
    }
    assert forbidden.isdisjoint(dir(projection))


def test_no_exact_connectivity_fabricates_no_gap_or_direct_proof():
    family = family_from_relationships(
        {
            ("a", "b"): ProductRelationship.EXACT_VARIANT_MATCH,
            ("a", "c"): ProductRelationship.SAME_PRODUCT_FAMILY,
            ("b", "c"): ProductRelationship.SAME_PRODUCT_FAMILY,
        }
    )

    projection = project_sellable_variant_evidence(family)

    assert projection.direct_exact_count == 1
    assert projection.exactness_gaps == ()


def test_multiple_paths_choose_shortest_then_canonical_member_order():
    family = family_from_relationships(
        {
            ("a", "b"): ProductRelationship.EXACT_VARIANT_MATCH,
            ("a", "c"): ProductRelationship.EXACT_VARIANT_MATCH,
            ("a", "d"): ProductRelationship.UNCERTAIN,
            ("b", "c"): ProductRelationship.SAME_PRODUCT_FAMILY,
            ("b", "d"): ProductRelationship.EXACT_VARIANT_MATCH,
            ("c", "d"): ProductRelationship.EXACT_VARIANT_MATCH,
        }
    )
    pairs = {
        (pair.left.source_product_id, pair.right.source_product_id): pair
        for pair in family.approval.proposal.pair_evidence
    }

    first = project_sellable_variant_evidence(family)
    second = project_sellable_variant_evidence(family)
    target = next(
        gap for gap in first.exactness_gaps
        if gap.direct_evidence is pairs[("a", "d")]
    )

    assert target.witness_path == (pairs[("a", "b")], pairs[("b", "d")])
    assert target.witness_path[0] is pairs[("a", "b")]
    assert target.witness_path[1] is pairs[("b", "d")]
    assert first == second


def test_projection_is_immutable_and_wrong_inputs_fail_closed():
    family = family_from_relationships(
        {
            ("a", "b"): ProductRelationship.EXACT_VARIANT_MATCH,
            ("a", "c"): ProductRelationship.UNCERTAIN,
            ("b", "c"): ProductRelationship.EXACT_VARIANT_MATCH,
        }
    )
    projection = project_sellable_variant_evidence(family)

    with pytest.raises(FrozenInstanceError):
        projection.direct_exact_evidence = ()
    with pytest.raises(FrozenInstanceError):
        projection.exactness_gaps[0].witness_path = ()
    for invalid in (family.approval, family.members, object(), None):
        with pytest.raises(SellableVariantEvidenceError):
            project_sellable_variant_evidence(invalid)


def test_projection_reexecutes_nothing_and_has_no_external_side_effects():
    family = family_from_relationships(
        {
            ("a", "b"): ProductRelationship.EXACT_VARIANT_MATCH,
            ("a", "c"): ProductRelationship.UNCERTAIN,
            ("b", "c"): ProductRelationship.EXACT_VARIANT_MATCH,
        }
    )

    with (
        patch("src.product_intelligence.entity_resolution.resolve_product_entities") as pairwise,
        patch("src.product_intelligence.entity_resolution_graph.resolve_multi_observations") as multi,
        patch("src.product_intelligence.entity_grouping.group_resolution_graph") as grouping,
        patch("src.product_intelligence.family_merge_approval.create_family_merge_proposal") as proposal,
        patch("src.product_intelligence.canonical_family.create_canonical_family") as admission,
        patch("uuid.uuid4") as uuid_generator,
        patch("random.random") as random_generator,
        patch("time.time") as clock,
        patch("os.getenv") as environment,
        patch("builtins.open") as filesystem_open,
    ):
        projection = project_sellable_variant_evidence(family)

    pairwise.assert_not_called()
    multi.assert_not_called()
    grouping.assert_not_called()
    proposal.assert_not_called()
    admission.assert_not_called()
    uuid_generator.assert_not_called()
    random_generator.assert_not_called()
    clock.assert_not_called()
    environment.assert_not_called()
    filesystem_open.assert_not_called()
    assert projection.source_family is family
