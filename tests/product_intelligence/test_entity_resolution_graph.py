"""Tests for multi-observation product entity resolution graph."""

from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone
import itertools

import pytest

from src.product_intelligence.entity_resolution import ProductRelationship
from src.product_intelligence.entity_resolution_graph import (
    MAX_OBSERVATIONS,
    MIN_OBSERVATIONS,
    MultiObservationEntityResolver,
    MultiObservationResolutionError,
    MultiObservationResolutionGraph,
    PairwiseConflictEvidence,
    ProductFamilyConsistencyConflict,
    resolve_multi_observations,
    resolve_product_graph,
    resolve_product_observation_graph,
)
from src.product_source.models import ProductFact, ProductSourcePack


def fact(key: str, value: str) -> ProductFact:
    return ProductFact(key, value, "specifications", "structured")


def pack(identifier: str, platform: str = "shopee", observed_at: datetime = None, **kwargs) -> ProductSourcePack:
    if observed_at is None:
        observed_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return ProductSourcePack(
        source_pack_id=f"{platform}_{identifier}",
        platform=platform,
        product_url=f"https://{platform}.example/{identifier}",
        source_product_id=identifier,
        observed_at=observed_at,
        collector="test",
        **kwargs,
    )


def identity_facts(brand: str = "Acme", model: str = "Phone X", color: str = "Black") -> tuple[ProductFact, ...]:
    return (fact("Brand", brand), fact("Model", model), fact("Color", color))


def test_bounded_cardinality_and_exact_pairwise_delegation():
    p1 = pack("1", facts=identity_facts(color="Black"))
    p2 = pack("2", facts=identity_facts(color="White"))
    p3 = pack("3", facts=identity_facts(color="Blue"))

    # Cardinality below 2 must fail
    with pytest.raises(MultiObservationResolutionError, match="Observation count must be between"):
        resolve_multi_observations([p1])

    # 3 observations -> 3 * 2 / 2 = 3 pairs
    graph = resolve_multi_observations([p1, p2, p3])
    assert isinstance(graph, MultiObservationResolutionGraph)
    assert len(graph.observations) == 3
    assert len(graph.pairwise_results) == 3
    assert not graph.has_conflicts
    assert len(graph.conflicts) == 0

    # Check that pairwise results are SAME_PRODUCT_FAMILY
    for pair_res in graph.pairwise_results:
        assert pair_res.relationship is ProductRelationship.SAME_PRODUCT_FAMILY

    # Check max boundary validation
    packs_101 = [pack(str(i), observed_at=datetime(2026, 1, 1, i // 60, i % 60, tzinfo=timezone.utc)) for i in range(101)]
    with pytest.raises(MultiObservationResolutionError, match="Observation count must be between"):
        resolve_multi_observations(packs_101)


def test_repeated_listing_observations_with_different_observed_at():
    base = pack("1", facts=identity_facts())
    later = replace(base, observed_at=datetime(2026, 1, 2, tzinfo=timezone.utc))
    another = pack("2", facts=identity_facts())

    graph = resolve_multi_observations([base, later, another])
    assert len(graph.observations) == 3
    assert graph.observations[0].source_pack_id == graph.observations[1].source_pack_id
    assert graph.observations[0].observed_at != graph.observations[1].observed_at
    assert len(graph.pairwise_results) == 3


def test_duplicate_exact_observation_identity_fails_before_pairwise():
    p1 = pack("1", facts=identity_facts())
    p2 = pack("2", facts=identity_facts())
    # Exact duplicate of p1
    p1_dup = pack("1", facts=identity_facts())

    with pytest.raises(MultiObservationResolutionError, match="Duplicate exact SourceObservationIdentity"):
        resolve_multi_observations([p1, p2, p1_dup])


def test_input_permutation_produces_consistent_semantics_and_diagnostics():
    # Construct a chain of positive relationships with a direct DIFFERENT_PRODUCT relationship
    # pack_a: Platform shopee, ID 100, no Brand/Model (relies on SCOPED_LISTING_MATCH with B)
    # pack_b: Platform shopee, ID 100, Brand Acme, Model Phone X (matches A on SCOPED_LISTING_MATCH, matches C on BRAND_MODEL_MATCH)
    # pack_c: Platform tiktok, ID 200, Brand Acme, Model Phone X, title "Phone X 3 pack" (matches B on BRAND_MODEL_MATCH; wait, multipack with B would be DIFFERENT_PRODUCT)
    # Let's check:
    # A: Shopee 100, observed_at t1, title "Phone X single", facts=(Brand Acme, Model Phone X)
    # B: Shopee 100, observed_at t2, title "Phone X", facts=(Brand Acme, Model Phone X)
    # C: Shopee 200, observed_at t1, title "Phone X 3 pack", facts=(Brand Acme, Model Phone X)
    # Pairwise:
    # A & B: EXACT_VARIANT_MATCH (or SAME_PRODUCT_FAMILY)
    # B & C: SAME_PRODUCT_FAMILY (B is not explicit single, C is 3 pack, but let's check composition: B text "Phone X" has no composition -> lc None, rc multi -> no conflict! Family strength 3 -> SAME_PRODUCT_FAMILY)
    # A & C: A title "Phone X single" (single) vs C title "Phone X 3 pack" (multi) -> COMPOSITION_CONFLICT -> DIFFERENT_PRODUCT!

    t1 = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc)

    pack_a = pack("100", platform="shopee", observed_at=t1, title="Acme Phone X single unit", facts=(fact("Brand", "Acme"), fact("Model", "Phone X")))
    pack_b = pack("100", platform="shopee", observed_at=t2, title="Acme Phone X", facts=(fact("Brand", "Acme"), fact("Model", "Phone X")))
    pack_c = pack("200", platform="shopee", observed_at=t1, title="Acme Phone X 3 pack", facts=(fact("Brand", "Acme"), fact("Model", "Phone X")))

    permutations = list(itertools.permutations([pack_a, pack_b, pack_c]))
    assert len(permutations) == 6

    for p_order in permutations:
        graph = resolve_multi_observations(p_order)
        assert graph.has_conflicts
        assert len(graph.conflicts) == 1
        conflict = graph.conflicts[0]
        assert conflict.conflict_type == "POSITIVE_FAMILY_CHAIN_CONTRADICTS_DIFFERENT_PRODUCT"
        # The contradictory pair is pack_a and pack_c
        contra_nodes = {conflict.contradictory_pair.left, conflict.contradictory_pair.right}
        expected_nodes = {graph.observations[i] for i, p in enumerate(p_order) if p in (pack_a, pack_c)}
        assert contra_nodes == expected_nodes

        # The positive path connects pack_a to pack_b and pack_b to pack_c
        path_pairs = [
            {step.left, step.right}
            for step in conflict.positive_path
        ]
        assert len(path_pairs) == 2


def test_consistent_positive_family_has_no_conflict():
    p1 = pack("1", facts=identity_facts(color="Black"))
    p2 = pack("2", facts=identity_facts(color="White"))
    p3 = pack("3", facts=identity_facts(color="Blue"))
    p4 = pack("4", facts=identity_facts(color="Red"))

    graph = resolve_multi_observations([p1, p2, p3, p4])
    assert not graph.has_conflicts
    assert len(graph.conflicts) == 0
    assert len(graph.pairwise_results) == 6  # 4 * 3 / 2
    # Ensure no cluster or canonical IDs fabricated
    assert not hasattr(graph, "cluster_id")
    assert not hasattr(graph, "canonical_product_id")


def test_uncertain_relationships_do_not_create_positive_chain_or_conflict():
    # A has Brand Alpha Model 1
    # B is sparse / ambiguous (title "Phone", no brand/model)
    # C has Brand Beta Model 2
    # Pairwise:
    # A & B: UNCERTAIN
    # B & C: UNCERTAIN
    # A & C: DIFFERENT_PRODUCT (Alpha Model 1 vs Beta Model 2)
    pack_a = pack("1", facts=(fact("Brand", "Alpha"), fact("Model", "One")))
    pack_b = pack("2", title="Generic Phone")
    pack_c = pack("3", facts=(fact("Brand", "Beta"), fact("Model", "Two")))

    graph = resolve_multi_observations([pack_a, pack_b, pack_c])
    # UNCERTAIN does not connect A and C in positive family graph, so no conflict should be raised
    assert not graph.has_conflicts
    assert len(graph.conflicts) == 0


def test_immutability_and_facade():
    p1 = pack("1", facts=identity_facts())
    p2 = pack("2", facts=identity_facts())

    resolver = MultiObservationEntityResolver()
    graph = resolver.resolve([p1, p2])

    with pytest.raises(FrozenInstanceError):
        graph.observations = ()

    # Verify public aliases
    g2 = resolve_product_graph([p1, p2])
    g3 = resolve_product_observation_graph([p1, p2])
    assert len(g2.pairwise_results) == 1
    assert len(g3.pairwise_results) == 1