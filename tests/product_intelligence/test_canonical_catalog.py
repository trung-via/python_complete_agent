"""Regressions for TASK-118 pure canonical catalog integrity."""

from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone
from itertools import combinations
from unittest.mock import patch

import pytest

from src.product_intelligence import (
    CanonicalCatalogIntegrityError,
    CanonicalCatalogState,
    CatalogRegistrationResult,
    CatalogRegistrationStatus,
    EntityResolutionResult,
    FamilyMergeDecision,
    MultiObservationResolutionGraph,
    ProductRelationship,
    ResolutionEvidence,
    SellableVariantDecision,
    SourceObservationIdentity,
    create_canonical_family,
    create_canonical_sellable_variant,
    create_empty_canonical_catalog,
    create_family_merge_decision_record,
    create_family_merge_proposal,
    create_sellable_variant_decision_record,
    create_sellable_variant_proposal,
    group_resolution_graph,
    register_canonical_family,
    register_canonical_variant,
)


def make_family(
    prefix: str,
    family_id: str,
    *,
    actor: str = "family-reviewer",
    member_names: tuple[str, ...] = ("a", "b", "c", "d"),
):
    members = {
        name: SourceObservationIdentity(
            source_pack_id=f"pack-{prefix}-{name}",
            platform="test-market",
            source_product_id=f"{prefix}-{name}",
            product_url=f"https://market.example/{prefix}/{name}",
            observed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        for name in member_names
    }
    results = []
    for left_name, right_name in combinations(member_names, 2):
        relationship = (
            ProductRelationship.EXACT_VARIANT_MATCH
            if (left_name, right_name) == ("a", "b")
            else ProductRelationship.SAME_PRODUCT_FAMILY
        )
        code = f"{prefix}-{left_name}{right_name}-{relationship.value}"
        results.append(
            EntityResolutionResult(
                relationship=relationship,
                confidence=0.97,
                left=members[right_name],
                right=members[left_name],
                reasons=(code,),
                evidence=(ResolutionEvidence(code, "preserved"),),
            )
        )
    graph = MultiObservationResolutionGraph(
        observations=tuple(reversed(tuple(members.values()))),
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
        actor=actor,
        decided_at=datetime(2026, 8, 31, 8, 0, tzinfo=timezone.utc),
    )
    return create_canonical_family(decision, family_id=family_id)


def make_variant(
    family,
    names: tuple[str, ...],
    variant_id: str,
    *,
    actor: str = "variant-reviewer",
):
    selected = tuple(
        member
        for name in names
        for member in family.members
        if member.source_product_id == f"{family.members[0].source_product_id[:-1]}{name}"
    )
    proposal = create_sellable_variant_proposal(family, selected)
    decision = create_sellable_variant_decision_record(
        proposal,
        decision=SellableVariantDecision.APPROVE,
        actor=actor,
        decided_at=datetime(2026, 8, 31, 10, 15, tzinfo=timezone.utc),
    )
    return create_canonical_sellable_variant(decision, variant_id=variant_id)


def catalog_with_family(family):
    return register_canonical_family(create_empty_canonical_catalog(), family).catalog


def test_empty_state_status_and_result_are_immutable_and_state_is_factory_only():
    catalog = create_empty_canonical_catalog()

    assert catalog.families == ()
    assert catalog.variants == ()
    assert tuple(CatalogRegistrationStatus) == (
        CatalogRegistrationStatus.INSERTED,
        CatalogRegistrationStatus.ALREADY_PRESENT,
    )
    with pytest.raises(FrozenInstanceError):
        catalog.families = ()
    with pytest.raises(CanonicalCatalogIntegrityError):
        CanonicalCatalogState(families=(), variants=())
    with pytest.raises(CanonicalCatalogIntegrityError):
        replace(catalog, families=())

    result = CatalogRegistrationResult(
        catalog=catalog,
        status=CatalogRegistrationStatus.ALREADY_PRESENT,
    )
    with pytest.raises(FrozenInstanceError):
        result.status = CatalogRegistrationStatus.INSERTED


def test_family_insert_and_value_equal_repeat_are_pure_and_identity_preserving():
    empty = create_empty_canonical_catalog()
    family = make_family("one", "Family/Z")

    inserted = register_canonical_family(empty, family)
    reconstructed = make_family("one", "Family/Z")
    repeated = register_canonical_family(inserted.catalog, reconstructed)

    assert inserted.status is CatalogRegistrationStatus.INSERTED
    assert inserted.catalog is not empty
    assert inserted.catalog.families == (family,)
    assert inserted.catalog.families[0] is family
    assert inserted.catalog.variants is empty.variants
    assert reconstructed == family and reconstructed is not family
    assert repeated.status is CatalogRegistrationStatus.ALREADY_PRESENT
    assert repeated.catalog is inserted.catalog


def test_family_id_lineage_and_member_conflicts_leave_catalog_unchanged():
    family = make_family("one", "family-1")
    catalog = catalog_with_family(family)
    conflicts = (
        make_family("two", "family-1"),
        make_family("one", "family-other"),
        make_family("one", "family-overlap", actor="different-reviewer"),
    )

    for conflict in conflicts:
        with pytest.raises(CanonicalCatalogIntegrityError):
            register_canonical_family(catalog, conflict)
        assert catalog.families == (family,)
        assert catalog.variants == ()


def test_variant_requires_value_equal_registered_source_family_without_auto_admission():
    source_family = make_family("one", "family-1")
    variant = make_variant(source_family, ("c",), "variant-1")
    empty = create_empty_canonical_catalog()

    with pytest.raises(CanonicalCatalogIntegrityError):
        register_canonical_variant(empty, variant)
    assert empty.families == empty.variants == ()

    equal_registered_family = make_family("one", "family-1")
    catalog = catalog_with_family(equal_registered_family)
    inserted = register_canonical_variant(catalog, variant)
    assert inserted.status is CatalogRegistrationStatus.INSERTED
    assert inserted.catalog.variants[0] is variant
    assert inserted.catalog.variants[0].source_family is source_family

    conflicting_family = make_family(
        "one",
        "family-1",
        actor="conflicting-family-reviewer",
    )
    conflicting_catalog = catalog_with_family(conflicting_family)
    with pytest.raises(CanonicalCatalogIntegrityError):
        register_canonical_variant(conflicting_catalog, variant)
    assert conflicting_catalog.variants == ()


def test_variant_insert_repeat_id_lineage_and_member_conflicts():
    family = make_family("one", "family-1")
    catalog = catalog_with_family(family)
    variant = make_variant(family, ("a", "b"), "variant-1")
    inserted = register_canonical_variant(catalog, variant)

    reconstructed_family = make_family("one", "family-1")
    reconstructed = make_variant(
        reconstructed_family,
        ("a", "b"),
        "variant-1",
    )
    repeated = register_canonical_variant(inserted.catalog, reconstructed)
    assert reconstructed == variant and reconstructed is not variant
    assert repeated.status is CatalogRegistrationStatus.ALREADY_PRESENT
    assert repeated.catalog is inserted.catalog

    conflicts = (
        make_variant(family, ("c",), "variant-1"),
        make_variant(family, ("a", "b"), "variant-other"),
        make_variant(
            family,
            ("a", "b"),
            "variant-overlap",
            actor="different-variant-reviewer",
        ),
    )
    for conflict in conflicts:
        with pytest.raises(CanonicalCatalogIntegrityError):
            register_canonical_variant(inserted.catalog, conflict)
        assert inserted.catalog.variants == (variant,)


def test_partial_variant_coverage_is_valid_and_ids_are_canonically_ordered():
    family_z = make_family("z", "family-z")
    family_a = make_family("a", "family-a")

    first_order = create_empty_canonical_catalog()
    for family in (family_z, family_a):
        first_order = register_canonical_family(first_order, family).catalog
    second_order = create_empty_canonical_catalog()
    for family in (family_a, family_z):
        second_order = register_canonical_family(second_order, family).catalog

    assert tuple(family.family_id for family in first_order.families) == (
        "family-a",
        "family-z",
    )
    assert first_order == second_order

    variant_z = make_variant(family_z, ("a", "b"), "variant-z")
    variant_a = make_variant(family_z, ("c",), "variant-a")
    forward = catalog_with_family(family_z)
    for variant in (variant_z, variant_a):
        forward = register_canonical_variant(forward, variant).catalog
    reverse = catalog_with_family(family_z)
    for variant in (variant_a, variant_z):
        reverse = register_canonical_variant(reverse, variant).catalog

    assert tuple(variant.variant_id for variant in forward.variants) == (
        "variant-a",
        "variant-z",
    )
    assert forward == reverse
    assigned = {member for variant in forward.variants for member in variant.members}
    unassigned = tuple(member for member in family_z.members if member not in assigned)
    assert tuple(member.source_product_id for member in unassigned) == ("z-d",)


def test_wrong_types_public_surface_and_zero_upstream_or_external_work():
    catalog = create_empty_canonical_catalog()
    family = make_family("one", "family-1")
    catalog = register_canonical_family(catalog, family).catalog
    variant = make_variant(family, ("c",), "variant-1")

    for invalid_catalog in (None, object(), ()):
        with pytest.raises(CanonicalCatalogIntegrityError):
            register_canonical_family(invalid_catalog, family)
        with pytest.raises(CanonicalCatalogIntegrityError):
            register_canonical_variant(invalid_catalog, variant)
    with pytest.raises(CanonicalCatalogIntegrityError):
        register_canonical_family(catalog, object())
    with pytest.raises(CanonicalCatalogIntegrityError):
        register_canonical_variant(catalog, object())

    import src.product_intelligence.canonical_catalog as module

    forbidden = (
        "update",
        "upsert",
        "delete",
        "merge",
        "reassign",
        "serialize",
        "persist",
        "retrieve",
        "profile",
    )
    assert not any(fragment in name.lower() for name in module.__all__ for fragment in forbidden)

    with (
        patch("src.product_intelligence.canonical_family.create_canonical_family") as family_factory,
        patch("src.product_intelligence.canonical_variant.create_canonical_sellable_variant") as variant_factory,
        patch("src.product_intelligence.sellable_variant_evidence.project_sellable_variant_evidence") as projection,
        patch("src.product_intelligence.sellable_variant_approval.create_sellable_variant_proposal") as proposal,
        patch("src.product_intelligence.sellable_variant_approval.create_sellable_variant_decision_record") as decision,
        patch("src.product_intelligence.entity_resolution.resolve_product_entities") as pairwise,
        patch("src.product_intelligence.entity_resolution_graph.resolve_multi_observations") as multi,
        patch("src.product_intelligence.entity_grouping.group_resolution_graph") as grouping,
        patch("uuid.uuid4") as uuid_generator,
        patch("random.random") as random_generator,
        patch("time.time") as clock,
        patch("os.getenv") as environment,
        patch("builtins.open") as filesystem_open,
    ):
        result = register_canonical_variant(catalog, variant)

    for mocked in (
        family_factory,
        variant_factory,
        projection,
        proposal,
        decision,
        pairwise,
        multi,
        grouping,
        uuid_generator,
        random_generator,
        clock,
        environment,
        filesystem_open,
    ):
        mocked.assert_not_called()
    assert result.catalog.variants == (variant,)
