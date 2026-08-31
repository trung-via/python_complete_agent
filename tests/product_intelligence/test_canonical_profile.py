"""Regressions for TASK-121 canonical variant evidence projection."""

from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timezone
from inspect import Parameter, signature
from unittest.mock import patch

import pytest

import src.product_intelligence.canonical_profile as canonical_profile_module
from src.product_intelligence import (
    CanonicalCatalogState,
    CanonicalProfileFactEvidence,
    CanonicalProfileMediaEvidence,
    CanonicalProfileObservation,
    CanonicalVariantProfile,
    CanonicalVariantProfileError,
    EntityResolutionResult,
    FamilyMergeDecision,
    MultiObservationResolutionGraph,
    ProductRelationship,
    ResolutionEvidence,
    SellableVariantDecision,
    SourceObservationIdentity,
    build_canonical_variant_profile,
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
from src.product_source.models import (
    MediaProvenance,
    MediaRole,
    OriginalMediaRef,
    ProductFact,
    ProductSourcePack,
)


OBSERVED_AT = datetime(2026, 8, 30, 12, 30, tzinfo=timezone.utc)


def identity(name: str) -> SourceObservationIdentity:
    return SourceObservationIdentity(
        source_pack_id=f"pack-{name}",
        platform=f"Market-{name}",
        source_product_id=f"product-{name}",
        product_url=f"https://market.example/{name}?opaque=Yes",
        observed_at=OBSERVED_AT,
    )


def registered_catalog():
    members = {name: identity(name) for name in ("a", "b")}
    result = EntityResolutionResult(
        relationship=ProductRelationship.EXACT_VARIANT_MATCH,
        confidence=0.97,
        left=members["b"],
        right=members["a"],
        reasons=("direct-exact",),
        evidence=(ResolutionEvidence("direct-exact", "preserved"),),
    )
    graph = MultiObservationResolutionGraph(
        observations=(members["b"], members["a"]),
        pairwise_results=(result,),
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
    family = create_canonical_family(family_decision, family_id="Family/Opaque")
    variant_proposal = create_sellable_variant_proposal(family, family.members)
    variant_decision = create_sellable_variant_decision_record(
        variant_proposal,
        decision=SellableVariantDecision.APPROVE,
        actor="variant-reviewer",
        decided_at=datetime(2026, 8, 31, 10, 0, tzinfo=timezone.utc),
    )
    variant = create_canonical_sellable_variant(
        variant_decision,
        variant_id="Variant/Opaque",
    )
    catalog = register_canonical_family(
        create_empty_canonical_catalog(), family
    ).catalog
    return register_canonical_variant(catalog, variant).catalog, variant


def fact(name: str, value: str, unit: str | None = None) -> ProductFact:
    return ProductFact(
        key=name,
        value=value,
        unit=unit,
        source_section=f"section-{name}",
        provenance=f"provenance-{name}",
    )


def media(name: str, ordinal: int) -> OriginalMediaRef:
    return OriginalMediaRef(
        source_url=f"https://cdn.example/{name}?signature=retain-in-memory",
        platform=f"platform-{name}",
        role=MediaRole.VARIANT if ordinal else MediaRole.PRIMARY,
        provenance=(
            MediaProvenance.SEMANTIC_VARIANT_MEDIA
            if ordinal
            else MediaProvenance.STRUCTURED_PRODUCT_DATA
        ),
        ordinal=ordinal,
        alt_text=None if ordinal else f" alt {name} ",
        variant_label=f"Variant {name}",
        content_type="image/webp",
        byte_size=100 + ordinal,
        sha256_hash=f"sha-{name}",
        perceptual_hash=f"phash-{name}",
        local_filename=f"{name}.webp",
    )


def pack_for(
    member: SourceObservationIdentity,
    *,
    collector: str,
    title: str | None,
    shop_name: str | None,
    brand: str | None,
    model_sku: str | None,
    description_text: str | None,
    facts: tuple[ProductFact, ...] = (),
    media_refs: tuple[OriginalMediaRef, ...] = (),
) -> ProductSourcePack:
    return ProductSourcePack(
        source_pack_id=member.source_pack_id,
        platform=member.platform,
        product_url=member.product_url,
        observed_at=member.observed_at,
        collector=collector,
        title=title,
        source_product_id=member.source_product_id,
        shop_name=shop_name,
        brand=brand,
        model_sku=model_sku,
        description_text=description_text,
        facts=facts,
        media=media_refs,
    )


def evidence_packs(variant):
    first_fact = fact("Color", "Red")
    equal_looking_fact = fact("Color", "Red")
    conflicting_fact = fact("Color", "BLUE", "tone")
    first_media = media("a-primary", 0)
    second_media = media("a-variant", 1)
    conflicting_media = media("b-primary", 0)
    first, second = variant.members
    packs = (
        pack_for(
            first,
            collector=" Collector A ",
            title="  Exact TITLE A  ",
            shop_name=None,
            brand="Brand-A",
            model_sku=None,
            description_text="Description A\nUnchanged",
            facts=(first_fact, equal_looking_fact),
            media_refs=(first_media, second_media),
        ),
        pack_for(
            second,
            collector="collector-b",
            title=None,
            shop_name="SHOP B",
            brand="brand-a",
            model_sku=" SKU-B ",
            description_text=None,
            facts=(conflicting_fact,),
            media_refs=(conflicting_media,),
        ),
    )
    return packs


def test_public_surface_and_value_types_are_exact_and_immutable():
    assert canonical_profile_module.__all__ == [
        "CanonicalVariantProfileError",
        "CanonicalProfileObservation",
        "CanonicalProfileFactEvidence",
        "CanonicalProfileMediaEvidence",
        "CanonicalVariantProfile",
        "build_canonical_variant_profile",
    ]
    parameters = tuple(signature(build_canonical_variant_profile).parameters.values())
    assert tuple(parameter.name for parameter in parameters) == (
        "catalog",
        "variant_id",
        "source_packs",
    )
    assert parameters[0].kind is Parameter.POSITIONAL_OR_KEYWORD
    assert all(
        parameter.kind is Parameter.KEYWORD_ONLY for parameter in parameters[1:]
    )

    catalog, variant = registered_catalog()
    profile = build_canonical_variant_profile(
        catalog,
        variant_id=variant.variant_id,
        source_packs=evidence_packs(variant),
    )
    assert tuple(field.name for field in fields(profile)) == (
        "variant_id",
        "family_id",
        "members",
        "observations",
        "fact_evidence",
        "media_evidence",
    )
    with pytest.raises(FrozenInstanceError):
        profile.variant_id = "changed"
    with pytest.raises(FrozenInstanceError):
        profile.observations[0].title = "changed"
    with pytest.raises(FrozenInstanceError):
        profile.fact_evidence[0].fact = fact("changed", "changed")
    with pytest.raises(FrozenInstanceError):
        profile.media_evidence[0].media = media("changed", 0)


def test_lookup_requires_exact_catalog_and_one_registered_opaque_variant_id():
    catalog, variant = registered_catalog()
    packs = evidence_packs(variant)

    profile = build_canonical_variant_profile(
        catalog,
        variant_id="Variant/Opaque",
        source_packs=packs,
    )
    assert profile.variant_id == variant.variant_id
    assert profile.family_id == variant.family_id
    assert profile.members is variant.members

    for invalid_catalog in (object(), None, "catalog"):
        with pytest.raises(CanonicalVariantProfileError):
            build_canonical_variant_profile(
                invalid_catalog,
                variant_id=variant.variant_id,
                source_packs=packs,
            )
    for invalid_id in (None, 1, "variant/opaque", " Variant/Opaque ", ""):
        with pytest.raises(CanonicalVariantProfileError):
            build_canonical_variant_profile(
                catalog,
                variant_id=invalid_id,
                source_packs=packs,
            )


def test_source_pack_binding_fails_closed_for_missing_extra_duplicate_and_wrong():
    catalog, variant = registered_catalog()
    first, second = evidence_packs(variant)
    unmatched_member = identity("unmatched")
    unmatched = pack_for(
        unmatched_member,
        collector="other",
        title="other",
        shop_name=None,
        brand=None,
        model_sku=None,
        description_text=None,
    )
    invalid_inputs = (
        (first,),
        (first, second, unmatched),
        (first, first),
        (first, unmatched),
        (first, object()),
    )

    for source_packs in invalid_inputs:
        with pytest.raises(CanonicalVariantProfileError):
            build_canonical_variant_profile(
                catalog,
                variant_id=variant.variant_id,
                source_packs=source_packs,
            )
    with pytest.raises(CanonicalVariantProfileError):
        build_canonical_variant_profile(
            catalog,
            variant_id=variant.variant_id,
            source_packs=None,
        )


def test_permutation_preserves_member_order_descriptive_conflicts_and_none():
    catalog, variant = registered_catalog()
    packs = evidence_packs(variant)

    forward = build_canonical_variant_profile(
        catalog,
        variant_id=variant.variant_id,
        source_packs=packs,
    )
    reversed_input = build_canonical_variant_profile(
        catalog,
        variant_id=variant.variant_id,
        source_packs=tuple(reversed(packs)),
    )

    assert reversed_input == forward
    assert tuple(observation.member for observation in forward.observations) == (
        variant.members
    )
    assert all(
        observation.member is member
        for observation, member in zip(forward.observations, variant.members)
    )
    assert forward.observations[0] == CanonicalProfileObservation(
        member=variant.members[0],
        collector=" Collector A ",
        title="  Exact TITLE A  ",
        shop_name=None,
        brand="Brand-A",
        model_sku=None,
        description_text="Description A\nUnchanged",
    )
    assert forward.observations[1].title is None
    assert forward.observations[1].shop_name == "SHOP B"
    assert forward.observations[1].brand == "brand-a"
    assert forward.observations[1].model_sku == " SKU-B "
    assert forward.observations[1].description_text is None
    assert not any(name.startswith("best_") for name in dir(forward))


def test_facts_and_media_retain_exact_objects_provenance_conflicts_and_order():
    catalog, variant = registered_catalog()
    packs = evidence_packs(variant)
    profile = build_canonical_variant_profile(
        catalog,
        variant_id=variant.variant_id,
        source_packs=packs,
    )

    assert tuple(value.fact for value in profile.fact_evidence) == (
        *packs[0].facts,
        *packs[1].facts,
    )
    assert tuple(value.media for value in profile.media_evidence) == (
        *packs[0].media,
        *packs[1].media,
    )
    assert all(
        projected.fact is original
        for projected, original in zip(
            profile.fact_evidence, (*packs[0].facts, *packs[1].facts)
        )
    )
    assert all(
        projected.media is original
        for projected, original in zip(
            profile.media_evidence, (*packs[0].media, *packs[1].media)
        )
    )
    assert tuple(value.member for value in profile.fact_evidence) == (
        variant.members[0],
        variant.members[0],
        variant.members[1],
    )
    assert tuple(value.member for value in profile.media_evidence) == (
        variant.members[0],
        variant.members[0],
        variant.members[1],
    )
    assert all(
        value.member is variant.members[0] for value in profile.fact_evidence[:2]
    )
    assert profile.fact_evidence[2].member is variant.members[1]
    assert all(
        value.member is variant.members[0] for value in profile.media_evidence[:2]
    )
    assert profile.media_evidence[2].member is variant.members[1]
    assert profile.fact_evidence[0].fact == profile.fact_evidence[1].fact
    assert len(profile.fact_evidence) == 3
    assert profile.fact_evidence[2].fact.value == "BLUE"
    assert profile.media_evidence[1].media.alt_text is None
    assert profile.media_evidence[2].media.local_filename == "b-primary.webp"


def test_repeated_value_equal_inputs_are_deterministic_and_unchanged():
    first_catalog, first_variant = registered_catalog()
    second_catalog, second_variant = registered_catalog()
    first_packs = evidence_packs(first_variant)
    second_packs = evidence_packs(second_variant)
    before = (first_catalog, first_packs)

    first_profile = build_canonical_variant_profile(
        first_catalog,
        variant_id=first_variant.variant_id,
        source_packs=first_packs,
    )
    repeated = build_canonical_variant_profile(
        first_catalog,
        variant_id=first_variant.variant_id,
        source_packs=first_packs,
    )
    reconstructed = build_canonical_variant_profile(
        second_catalog,
        variant_id=second_variant.variant_id,
        source_packs=second_packs,
    )

    assert first_catalog == second_catalog and first_catalog is not second_catalog
    assert first_packs == second_packs and first_packs is not second_packs
    assert repeated == first_profile == reconstructed
    assert (first_catalog, first_packs) == before
    assert all(
        observation.member is member
        for observation, member in zip(
            reconstructed.observations, second_variant.members
        )
    )


def test_projection_calls_no_upstream_work_or_external_io():
    catalog, variant = registered_catalog()
    packs = evidence_packs(variant)

    with (
        patch("src.product_intelligence.entity_resolution.resolve_product_entities") as resolver,
        patch("src.product_intelligence.entity_resolution_graph.resolve_multi_observations") as graph,
        patch("src.product_intelligence.entity_grouping.group_resolution_graph") as grouping,
        patch("src.product_intelligence.sellable_variant_evidence.project_sellable_variant_evidence") as projection,
        patch("src.product_intelligence.canonical_family.create_canonical_family") as family_admission,
        patch("src.product_intelligence.canonical_variant.create_canonical_sellable_variant") as variant_admission,
        patch("src.product_intelligence.canonical_catalog.register_canonical_family") as family_registration,
        patch("src.product_intelligence.canonical_catalog.register_canonical_variant") as variant_registration,
        patch("builtins.open") as filesystem_open,
        patch("sqlite3.connect") as sqlite_connect,
        patch("urllib.request.urlopen") as network,
        patch("subprocess.run") as subprocess_run,
        patch("time.time") as clock,
        patch("random.random") as random_value,
        patch("uuid.uuid4") as uuid_value,
        patch("os.getenv") as environment,
    ):
        profile = build_canonical_variant_profile(
            catalog,
            variant_id=variant.variant_id,
            source_packs=packs,
        )

    for mocked in (
        resolver,
        graph,
        grouping,
        projection,
        family_admission,
        variant_admission,
        family_registration,
        variant_registration,
        filesystem_open,
        sqlite_connect,
        network,
        subprocess_run,
        clock,
        random_value,
        uuid_value,
        environment,
    ):
        mocked.assert_not_called()
    assert isinstance(profile, CanonicalVariantProfile)
    assert all(
        isinstance(value, CanonicalProfileFactEvidence)
        for value in profile.fact_evidence
    )
    assert all(
        isinstance(value, CanonicalProfileMediaEvidence)
        for value in profile.media_evidence
    )
