"""Focused regressions for TASK-122 canonical profile lexical retrieval."""

from dataclasses import FrozenInstanceError, fields, replace
from datetime import datetime, timezone
from inspect import Parameter, signature
from unittest.mock import patch

import pytest

import src.product_intelligence.canonical_retrieval as retrieval_module
from src.product_intelligence import (
    CanonicalProfileFactEvidence,
    CanonicalProfileMediaEvidence,
    CanonicalProfileObservation,
    CanonicalProfileRetrievalError,
    CanonicalRetrievalField,
    CanonicalRetrievalMatchClass,
    CanonicalRetrievalWitness,
    CanonicalVariantProfile,
    CanonicalVariantRetrievalHit,
    SourceObservationIdentity,
    retrieve_canonical_variant_profiles,
)
from src.product_source.models import (
    MediaProvenance,
    MediaRole,
    OriginalMediaRef,
    ProductFact,
)


OBSERVED_AT = datetime(2026, 8, 31, tzinfo=timezone.utc)


def member(name: str, *, platform: str | None = None) -> SourceObservationIdentity:
    return SourceObservationIdentity(
        source_pack_id=f"pack-{name}",
        platform=platform or f"Platform {name}",
        source_product_id=f"opaque-product-{name}",
        product_url=f"https://opaque.example/{name}",
        observed_at=OBSERVED_AT,
    )


def observation(
    source_member: SourceObservationIdentity,
    *,
    title: str | None = None,
    shop_name: str | None = None,
    brand: str | None = None,
    model_sku: str | None = None,
    description_text: str | None = None,
    collector: str = "opaque collector",
) -> CanonicalProfileObservation:
    return CanonicalProfileObservation(
        member=source_member,
        collector=collector,
        title=title,
        shop_name=shop_name,
        brand=brand,
        model_sku=model_sku,
        description_text=description_text,
    )


def fact_evidence(
    source_member: SourceObservationIdentity,
    key: str,
    value: str,
    unit: str | None = None,
    *,
    source_section: str = "opaque section",
    provenance: str = "opaque provenance",
) -> CanonicalProfileFactEvidence:
    return CanonicalProfileFactEvidence(
        member=source_member,
        fact=ProductFact(
            key=key,
            value=value,
            unit=unit,
            source_section=source_section,
            provenance=provenance,
        ),
    )


def media_evidence(
    source_member: SourceObservationIdentity,
    *,
    alt_text: str | None,
    variant_label: str | None,
    opaque: str = "media",
) -> CanonicalProfileMediaEvidence:
    return CanonicalProfileMediaEvidence(
        member=source_member,
        media=OriginalMediaRef(
            source_url=f"https://opaque.example/{opaque}.webp",
            platform=f"opaque media platform {opaque}",
            role=MediaRole.VARIANT,
            provenance=MediaProvenance.SEMANTIC_VARIANT_MEDIA,
            ordinal=0,
            alt_text=alt_text,
            variant_label=variant_label,
            sha256_hash=f"opaque-hash-{opaque}",
            local_filename=f"opaque-{opaque}.webp",
        ),
    )


def profile(
    variant_id: str,
    observations: tuple[CanonicalProfileObservation, ...],
    *,
    facts: tuple[CanonicalProfileFactEvidence, ...] = (),
    media: tuple[CanonicalProfileMediaEvidence, ...] = (),
    members: tuple[SourceObservationIdentity, ...] | None = None,
) -> CanonicalVariantProfile:
    ordered_members = members or tuple(value.member for value in observations)
    return CanonicalVariantProfile(
        variant_id=variant_id,
        family_id=f"opaque-family-{variant_id}",
        members=ordered_members,
        observations=observations,
        fact_evidence=facts,
        media_evidence=media,
    )


def test_public_surface_signature_enums_and_immutable_values_are_bounded():
    assert retrieval_module.__all__ == [
        "CanonicalProfileRetrievalError",
        "CanonicalRetrievalField",
        "CanonicalRetrievalMatchClass",
        "CanonicalRetrievalWitness",
        "CanonicalVariantRetrievalHit",
        "retrieve_canonical_variant_profiles",
    ]
    assert tuple(CanonicalRetrievalField) == tuple(
        CanonicalRetrievalField[name]
        for name in (
            "PLATFORM",
            "TITLE",
            "SHOP_NAME",
            "BRAND",
            "MODEL_SKU",
            "DESCRIPTION_TEXT",
            "FACT_KEY",
            "FACT_VALUE",
            "FACT_UNIT",
            "MEDIA_ALT_TEXT",
            "MEDIA_VARIANT_LABEL",
        )
    )
    assert tuple(CanonicalRetrievalMatchClass) == tuple(
        CanonicalRetrievalMatchClass[name]
        for name in (
            "EXACT_VALUE",
            "PHRASE",
            "SINGLE_FIELD_ALL_TERMS",
            "CROSS_FIELD_ALL_TERMS",
        )
    )
    parameters = tuple(
        signature(retrieve_canonical_variant_profiles).parameters.values()
    )
    assert tuple(value.name for value in parameters) == ("profiles", "query", "limit")
    assert parameters[0].kind is Parameter.POSITIONAL_OR_KEYWORD
    assert all(value.kind is Parameter.KEYWORD_ONLY for value in parameters[1:])
    assert parameters[2].default == 10

    source_member = member("immutable")
    source = observation(source_member, title="Immutable")
    witness = CanonicalRetrievalWitness(
        source_evidence=source,
        field=CanonicalRetrievalField.TITLE,
        value="Immutable",
        normalized_query_terms=("immutable",),
    )
    hit = CanonicalVariantRetrievalHit(
        profile=profile("immutable", (source,)),
        match_class=CanonicalRetrievalMatchClass.EXACT_VALUE,
        witnesses=(witness,),
    )
    assert tuple(value.name for value in fields(witness)) == (
        "source_evidence",
        "field",
        "value",
        "normalized_query_terms",
    )
    assert tuple(value.name for value in fields(hit)) == (
        "profile",
        "match_class",
        "witnesses",
    )
    with pytest.raises(FrozenInstanceError):
        witness.value = "changed"
    with pytest.raises(FrozenInstanceError):
        hit.witnesses = ()


def test_exact_inputs_empty_corpus_duplicate_ids_and_no_match():
    assert retrieve_canonical_variant_profiles((), query="valid") == ()

    source = observation(member("valid"), title="valid")
    value = profile("opaque/id", (source,))
    assert retrieve_canonical_variant_profiles((value,), query="absent") == ()

    for invalid_corpus in (None, (value, object())):
        with pytest.raises(CanonicalProfileRetrievalError):
            retrieve_canonical_variant_profiles(invalid_corpus, query="valid")
    with pytest.raises(CanonicalProfileRetrievalError):
        retrieve_canonical_variant_profiles(
            (value, replace(value)),
            query="valid",
        )


def test_query_normalization_is_exact_bounded_and_does_not_strip_accents():
    source = observation(
        member("unicode"),
        title="ＦＯＯ—Straße café",
        description_text="stemmed running",
    )
    value = profile("unicode", (source,))

    hit = retrieve_canonical_variant_profiles((value,), query="foo STRASSE café")[0]
    assert hit.match_class is CanonicalRetrievalMatchClass.EXACT_VALUE
    assert hit.witnesses[0].value == "ＦＯＯ—Straße café"
    assert hit.witnesses[0].normalized_query_terms == ("foo", "strasse", "café")
    assert retrieve_canonical_variant_profiles((value,), query="cafe") == ()
    accent_hit = retrieve_canonical_variant_profiles((value,), query="café")[0]
    assert accent_hit.witnesses[0].value == "ＦＯＯ—Straße café"
    assert retrieve_canonical_variant_profiles((value,), query="run") == ()

    class Query(str):
        pass

    invalid_queries = (
        None,
        1,
        Query("foo"),
        "---",
        " ".join(str(i) for i in range(13)),
    )
    for invalid_query in invalid_queries:
        with pytest.raises(CanonicalProfileRetrievalError):
            retrieve_canonical_variant_profiles((value,), query=invalid_query)


def test_limit_requires_exact_int_range():
    source = observation(member("limit"), title="valid")
    value = profile("limit", (source,))
    for invalid_limit in (True, False, 0, 101, -1, 1.0, "1", None):
        with pytest.raises(CanonicalProfileRetrievalError):
            retrieve_canonical_variant_profiles(
                (value,),
                query="valid",
                limit=invalid_limit,
            )


def test_only_bounded_evidence_fields_are_searchable_and_keep_sources():
    source_member = member("opaque-token", platform="Platform Searchable")
    source = observation(
        source_member,
        title="Title Searchable",
        shop_name="Shop Searchable",
        brand="Brand Searchable",
        model_sku="Model Searchable",
        description_text="Description Searchable",
        collector="Collector Forbidden",
    )
    fact = fact_evidence(
        source_member,
        "FactKey Searchable",
        "FactValue Searchable",
        "FactUnit Searchable",
        source_section="Section Forbidden",
        provenance="Provenance Forbidden",
    )
    media = media_evidence(
        source_member,
        alt_text="Alt Searchable",
        variant_label="VariantLabel Searchable",
        opaque="url-hash-filename-forbidden",
    )
    value = profile("variant-id-forbidden", (source,), facts=(fact,), media=(media,))
    searchable = {
        "platform": (CanonicalRetrievalField.PLATFORM, source),
        "title": (CanonicalRetrievalField.TITLE, source),
        "shop": (CanonicalRetrievalField.SHOP_NAME, source),
        "brand": (CanonicalRetrievalField.BRAND, source),
        "model": (CanonicalRetrievalField.MODEL_SKU, source),
        "description": (CanonicalRetrievalField.DESCRIPTION_TEXT, source),
        "factkey": (CanonicalRetrievalField.FACT_KEY, fact),
        "factvalue": (CanonicalRetrievalField.FACT_VALUE, fact),
        "factunit": (CanonicalRetrievalField.FACT_UNIT, fact),
        "alt": (CanonicalRetrievalField.MEDIA_ALT_TEXT, media),
        "variantlabel": (CanonicalRetrievalField.MEDIA_VARIANT_LABEL, media),
    }
    for query, (expected_field, expected_source) in searchable.items():
        hit = retrieve_canonical_variant_profiles((value,), query=query)[0]
        assert hit.witnesses[0].field is expected_field
        assert hit.witnesses[0].source_evidence is expected_source

    for forbidden in (
        "collector",
        "section",
        "provenance",
        "variant-id-forbidden",
        "opaque-token",
        "url-hash-filename-forbidden",
    ):
        assert retrieve_canonical_variant_profiles((value,), query=forbidden) == ()


def test_all_terms_required_and_four_match_classes_use_strongest_precedence():
    values = []
    for variant_id, title, brand in (
        ("exact", "red shoe", None),
        ("phrase", "premium red shoe edition", None),
        ("single", "shoe premium red", None),
        ("cross", "red", "shoe"),
        ("partial", "red", None),
    ):
        source = observation(member(variant_id), title=title, brand=brand)
        values.append(profile(variant_id, (source,)))

    exact_hits = retrieve_canonical_variant_profiles(values, query="red shoe")
    assert tuple(hit.match_class for hit in exact_hits) == (
        CanonicalRetrievalMatchClass.EXACT_VALUE,
        CanonicalRetrievalMatchClass.PHRASE,
        CanonicalRetrievalMatchClass.SINGLE_FIELD_ALL_TERMS,
        CanonicalRetrievalMatchClass.CROSS_FIELD_ALL_TERMS,
    )
    assert all(hit.profile.variant_id != "partial" for hit in exact_hits)

    repeated = retrieve_canonical_variant_profiles(values, query="red red shoe")
    assert tuple(hit.profile.variant_id for hit in repeated) == (
        "exact",
        "phrase",
        "single",
        "cross",
    )
    assert tuple(hit.match_class for hit in repeated) == (
        CanonicalRetrievalMatchClass.SINGLE_FIELD_ALL_TERMS,
        CanonicalRetrievalMatchClass.SINGLE_FIELD_ALL_TERMS,
        CanonicalRetrievalMatchClass.SINGLE_FIELD_ALL_TERMS,
        CanonicalRetrievalMatchClass.CROSS_FIELD_ALL_TERMS,
    )


def test_order_limit_and_corpus_permutation_are_canonical():
    profiles = tuple(
        profile(
            variant_id,
            (observation(member(variant_id), title=title, brand=brand),),
        )
        for variant_id, title, brand in (
            ("z", "red shoe", None),
            ("a", "red shoe", None),
            ("p", "premium red shoe edition", None),
            ("s", "shoe then red", None),
            ("c", "red", "shoe"),
        )
    )
    forward = retrieve_canonical_variant_profiles(profiles, query="red shoe")
    reversed_input = retrieve_canonical_variant_profiles(
        tuple(reversed(profiles)), query="red shoe"
    )
    assert forward == reversed_input
    assert tuple(hit.profile.variant_id for hit in forward) == ("a", "z", "p", "s", "c")
    limited = retrieve_canonical_variant_profiles(
        profiles, query="red shoe", limit=2
    )
    assert limited == forward[:2]


def test_canonical_witness_order_and_minimum_cross_field_tie_breaking():
    first = member("first")
    second = member("second")
    first_observation = observation(
        first,
        title="alpha",
        shop_name="beta",
        brand="alpha beta",
    )
    second_observation = observation(second, title="gamma", brand="beta gamma")
    value = profile(
        "tie",
        (first_observation, second_observation),
        members=(first, second),
    )

    hit = retrieve_canonical_variant_profiles((value,), query="alpha beta gamma")[0]
    assert hit.match_class is CanonicalRetrievalMatchClass.CROSS_FIELD_ALL_TERMS
    assert tuple(witness.field for witness in hit.witnesses) == (
        CanonicalRetrievalField.TITLE,
        CanonicalRetrievalField.BRAND,
    )
    assert tuple(witness.value for witness in hit.witnesses) == (
        "alpha",
        "beta gamma",
    )
    assert hit.witnesses[0].source_evidence is first_observation
    assert hit.witnesses[1].source_evidence is second_observation
    assert hit.witnesses[0].normalized_query_terms == ("alpha",)
    assert hit.witnesses[1].normalized_query_terms == ("beta", "gamma")


def test_profile_identity_conflicts_determinism_and_no_external_authorities():
    first_member = member("conflict-first")
    second_member = member("conflict-second")
    first = observation(first_member, title="scarlet", brand="same")
    second = observation(second_member, title="blue", brand="same")
    value = profile("conflict", (first, second), members=(first_member, second_member))
    before = value

    with (
        patch("src.product_intelligence.ranking.CandidateRanker") as ranker,
        patch("src.product_intelligence.scoring.WinningProductScorer") as scorer,
        patch(
            "src.product_intelligence.entity_resolution.resolve_product_entities"
        ) as resolver,
        patch(
            "src.product_intelligence.entity_grouping.group_resolution_graph"
        ) as grouping,
        patch(
            "src.product_intelligence.canonical_catalog.register_canonical_variant"
        ) as registration,
        patch("builtins.open") as filesystem,
        patch("sqlite3.connect") as sqlite,
        patch("urllib.request.urlopen") as network,
        patch("subprocess.run") as subprocess_run,
        patch("time.time") as clock,
        patch("random.random") as random_value,
        patch("uuid.uuid4") as uuid_value,
        patch("os.getenv") as environment,
    ):
        first_result = retrieve_canonical_variant_profiles(
            (value,), query="scarlet blue"
        )
        repeated = retrieve_canonical_variant_profiles((value,), query="scarlet blue")

    assert first_result == repeated
    assert first_result[0].profile is value
    assert value is before
    assert tuple(witness.source_evidence for witness in first_result[0].witnesses) == (
        first,
        second,
    )
    for mocked in (
        ranker,
        scorer,
        resolver,
        grouping,
        registration,
        filesystem,
        sqlite,
        network,
        subprocess_run,
        clock,
        random_value,
        uuid_value,
        environment,
    ):
        mocked.assert_not_called()
