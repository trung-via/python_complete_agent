"""Tests for platform-neutral provisional product-family grouping."""

from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone
import itertools
from unittest.mock import patch

import pytest

from src.product_intelligence import (
    EntityResolutionResult,
    MultiObservationResolutionGraph,
    ProductFamilyConsistencyConflict,
    ProductFamilyGrouper,
    ProductRelationship,
    ProvisionalGroupingResult,
    ProvisionalGroupStatus,
    ProvisionalProductFamilyGroup,
    ResolutionEvidence,
    SourceObservationIdentity,
    group_multi_observations,
    group_product_graph,
    group_product_resolution_graph,
    group_resolution_graph,
    resolve_multi_observations,
)
from src.product_intelligence.entity_resolution import resolve_product_entities
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


def test_positive_connected_family_and_exact_partition():
    p1 = pack("1", facts=identity_facts(color="Black"))
    p2 = pack("2", facts=identity_facts(color="White"))
    p3 = pack("3", facts=identity_facts(color="Blue"))

    graph = resolve_multi_observations([p1, p2, p3])
    res = group_resolution_graph(graph)

    assert isinstance(res, ProvisionalGroupingResult)
    assert res.group_count == 1
    assert res.observation_count == 3
    assert res.conflicted_group_count == 0

    group = res.groups[0]
    assert isinstance(group, ProvisionalProductFamilyGroup)
    assert group.status is ProvisionalGroupStatus.POSITIVE_CONNECTED
    assert group.member_count == 3
    assert not group.has_conflicts
    assert len(group.conflicts) == 0

    # Verify exact partition: every identity appears once
    identities_in_groups = [m for g in res.groups for m in g.members]
    assert len(identities_in_groups) == len(graph.observations)
    assert set(identities_in_groups) == set(graph.observations)


def test_singleton_observations_and_different_product_isolation():
    # p1 and p2 are same family, p3 is completely different brand
    p1 = pack("1", facts=identity_facts(brand="Acme", model="Phone X"))
    p2 = pack("2", facts=identity_facts(brand="Acme", model="Phone X", color="White"))
    p3 = pack("3", facts=(fact("Brand", "BetaBrand"), fact("Model", "BetaModel")))

    graph = resolve_multi_observations([p1, p2, p3])
    res = group_resolution_graph(graph)

    assert res.group_count == 2
    assert res.observation_count == 3

    # Group 1 is the 2-member POSITIVE_CONNECTED component
    # Group 2 is the 1-member SINGLETON component
    statuses = [g.status for g in res.groups]
    assert ProvisionalGroupStatus.POSITIVE_CONNECTED in statuses
    assert ProvisionalGroupStatus.SINGLETON in statuses

    singleton_group = next(g for g in res.groups if g.status is ProvisionalGroupStatus.SINGLETON)
    assert singleton_group.member_count == 1
    assert singleton_group.members[0] == graph.observations[2]
    assert not singleton_group.has_conflicts


def test_uncertain_boundary_does_not_bridge_components():
    # A has Brand Alpha Model 1
    # B is sparse / ambiguous (title "Phone", no brand/model)
    # C has Brand Beta Model 2
    # Pairwise: A&B UNCERTAIN, B&C UNCERTAIN, A&C DIFFERENT_PRODUCT
    pack_a = pack("1", facts=(fact("Brand", "Alpha"), fact("Model", "One")))
    pack_b = pack("2", title="Generic Phone")
    pack_c = pack("3", facts=(fact("Brand", "Beta"), fact("Model", "Two")))

    graph = resolve_multi_observations([pack_a, pack_b, pack_c])
    res = group_resolution_graph(graph)

    # All 3 should be isolated singletons
    assert res.group_count == 3
    assert res.observation_count == 3
    for g in res.groups:
        assert g.status is ProvisionalGroupStatus.SINGLETON
        assert g.member_count == 1
        assert not g.has_conflicts


def test_conflicted_positive_component_preserves_task109_conflict():
    # Positive chain: pack_a <-> pack_b <-> pack_c, with direct DIFFERENT_PRODUCT pack_a <-> pack_c
    t1 = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc)

    pack_a = pack("100", platform="shopee", observed_at=t1, title="Acme Phone X single unit", facts=(fact("Brand", "Acme"), fact("Model", "Phone X")))
    pack_b = pack("100", platform="shopee", observed_at=t2, title="Acme Phone X", facts=(fact("Brand", "Acme"), fact("Model", "Phone X")))
    pack_c = pack("200", platform="shopee", observed_at=t1, title="Acme Phone X 3 pack", facts=(fact("Brand", "Acme"), fact("Model", "Phone X")))

    graph = resolve_multi_observations([pack_a, pack_b, pack_c])
    assert graph.has_conflicts

    res = group_resolution_graph(graph)
    assert res.group_count == 1
    assert res.conflicted_group_count == 1

    group = res.groups[0]
    assert group.status is ProvisionalGroupStatus.CONFLICTED
    assert group.member_count == 3
    assert group.has_conflicts
    assert len(group.conflicts) == 1
    assert group.conflicts[0] == graph.conflicts[0]


def test_multiple_disjoint_groups_with_mixed_statuses():
    # Family 1: 2 positive connected items
    f1_a = pack("10", facts=identity_facts(brand="BrandA", model="Model1"))
    f1_b = pack("11", facts=identity_facts(brand="BrandA", model="Model1", color="Red"))

    # Family 2: 1 singleton
    f2_a = pack("20", facts=identity_facts(brand="BrandB", model="Model2"))

    # Family 3: Conflicted component (3 items)
    t1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    t2 = datetime(2026, 1, 2, tzinfo=timezone.utc)
    f3_a = pack("30", platform="shopee", observed_at=t1, title="BrandC Gadget single", facts=(fact("Brand", "BrandC"), fact("Model", "ModC")))
    f3_b = pack("30", platform="shopee", observed_at=t2, title="BrandC Gadget", facts=(fact("Brand", "BrandC"), fact("Model", "ModC")))
    f3_c = pack("31", platform="shopee", observed_at=t1, title="BrandC Gadget 3 pack", facts=(fact("Brand", "BrandC"), fact("Model", "ModC")))

    graph = resolve_multi_observations([f1_a, f1_b, f2_a, f3_a, f3_b, f3_c])
    res = group_resolution_graph(graph)

    assert res.group_count == 3
    assert res.observation_count == 6
    assert res.conflicted_group_count == 1

    statuses = {g.status for g in res.groups}
    assert statuses == {
        ProvisionalGroupStatus.POSITIVE_CONNECTED,
        ProvisionalGroupStatus.SINGLETON,
        ProvisionalGroupStatus.CONFLICTED,
    }


def test_permutation_invariance_and_canonical_ordering():
    t1 = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc)

    pack_a = pack("100", platform="shopee", observed_at=t1, title="Acme Phone X single unit", facts=(fact("Brand", "Acme"), fact("Model", "Phone X")))
    pack_b = pack("100", platform="shopee", observed_at=t2, title="Acme Phone X", facts=(fact("Brand", "Acme"), fact("Model", "Phone X")))
    pack_c = pack("200", platform="shopee", observed_at=t1, title="Acme Phone X 3 pack", facts=(fact("Brand", "Acme"), fact("Model", "Phone X")))
    pack_d = pack("300", facts=identity_facts(brand="OtherBrand", model="OtherModel"))

    items = [pack_a, pack_b, pack_c, pack_d]
    baseline_graph = resolve_multi_observations(items)
    baseline_result = group_resolution_graph(baseline_graph)

    for perm in itertools.permutations(items):
        graph = resolve_multi_observations(perm)
        result = group_resolution_graph(graph)

        assert result.group_count == baseline_result.group_count
        assert result.conflicted_group_count == baseline_result.conflicted_group_count
        assert len(result.groups) == len(baseline_result.groups)

        for g_res, g_base in zip(result.groups, baseline_result.groups):
            assert g_res.status == g_base.status
            assert g_res.members == g_base.members
            assert g_res.conflicts == g_base.conflicts


def test_zero_calls_to_pairwise_or_multi_observation_resolver():
    p1 = pack("1", facts=identity_facts())
    p2 = pack("2", facts=identity_facts())
    graph = resolve_multi_observations([p1, p2])

    with patch("src.product_intelligence.entity_resolution.resolve_product_entities") as mock_pair:
        with patch("src.product_intelligence.entity_resolution_graph.resolve_multi_observations") as mock_multi:
            res = group_resolution_graph(graph)
            assert mock_pair.call_count == 0
            assert mock_multi.call_count == 0

    assert res.group_count == 1


def test_immutability_and_facade():
    p1 = pack("1", facts=identity_facts())
    p2 = pack("2", facts=identity_facts())
    graph = resolve_multi_observations([p1, p2])

    grouper = ProductFamilyGrouper()
    res = grouper.group(graph)

    with pytest.raises(FrozenInstanceError):
        res.groups = ()

    with pytest.raises(FrozenInstanceError):
        res.groups[0].members = ()

    # Verify public aliases
    res2 = group_product_graph(graph)
    res3 = group_product_resolution_graph(graph)
    res4 = group_multi_observations(graph)
    assert res2 == res
    assert res3 == res
    assert res4 == res


def test_type_error_on_invalid_input():
    with pytest.raises(TypeError, match="MultiObservationResolutionGraph"):
        group_resolution_graph("invalid_input")


def test_permutation_regression_distinct_source_product_id_none_vs_empty():
    """Prove that distinct observations differing only by source_product_id=None vs '' yield identical group ordering when permuted."""
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    p_none = ProductSourcePack(
        source_pack_id="pack_shared",
        platform="shopee",
        product_url="https://shopee.example/item",
        source_product_id=None,
        observed_at=t0,
        collector="test",
        facts=identity_facts(brand="Alpha", model="One"),
    )
    p_empty = ProductSourcePack(
        source_pack_id="pack_shared",
        platform="shopee",
        product_url="https://shopee.example/item",
        source_product_id="",
        observed_at=t0,
        collector="test",
        facts=identity_facts(brand="Beta", model="Two"),
    )

    id_none = SourceObservationIdentity.from_pack(p_none)
    id_empty = SourceObservationIdentity.from_pack(p_empty)
    assert id_none != id_empty

    # Forward permutation
    graph_fwd = resolve_multi_observations([p_none, p_empty])
    res_fwd = group_resolution_graph(graph_fwd)

    # Reversed permutation
    graph_rev = resolve_multi_observations([p_empty, p_none])
    res_rev = group_resolution_graph(graph_rev)

    assert res_fwd.group_count == 2
    assert res_rev.group_count == 2
    assert res_fwd.groups == res_rev.groups


