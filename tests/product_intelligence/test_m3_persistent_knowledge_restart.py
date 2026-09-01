"""TASK-125 restart proof for the complete persistent M3 knowledge path."""

from datetime import datetime, timezone
import socket
from unittest.mock import patch

from src.product_intelligence import (
    EntityResolutionResult,
    FamilyMergeDecision,
    MultiObservationResolutionGraph,
    ProductRelationship,
    ResolutionEvidence,
    SellableVariantDecision,
    SourceObservationIdentity,
    build_canonical_rag_context,
    build_canonical_variant_profile,
    create_canonical_family,
    create_canonical_sellable_variant,
    create_family_merge_decision_record,
    create_family_merge_proposal,
    create_sellable_variant_decision_record,
    create_sellable_variant_proposal,
    create_sqlite_canonical_catalog,
    group_resolution_graph,
    load_sqlite_canonical_catalog,
    register_sqlite_canonical_family,
    register_sqlite_canonical_variant,
    render_canonical_rag_context,
    retrieve_canonical_variant_profiles,
)
from src.product_source import deserialize_product_source_pack
from src.product_source.models import (
    MediaProvenance,
    MediaRole,
    OriginalMediaRef,
    ProductFact,
    ProductSourcePack,
)
from src.product_source.serialization import serialize_source_pack


OBSERVED_AT = datetime(2026, 8, 31, 9, 45, tzinfo=timezone.utc)


def _source_pack(name: str, *, title: str, color: str) -> ProductSourcePack:
    return ProductSourcePack(
        source_pack_id=f"restart-pack-{name}",
        platform=f"market-{name}",
        product_url=f"https://market.example/{name}/listing",
        observed_at=OBSERVED_AT,
        collector=f"collector-{name}",
        title=title,
        source_product_id=f"listing-{name}",
        shop_name=f"shop-{name}",
        brand="Restart Brand",
        model_sku=None,
        description_text=f"Persisted {color} seller evidence",
        facts=(
            ProductFact(
                key="Model",
                value="Restart One",
                unit=None,
                source_section="specifications",
                provenance="structured_table",
            ),
            ProductFact(
                key="Color",
                value=color,
                unit=None,
                source_section="specifications",
                provenance="structured_table",
            ),
        ),
        media=(
            OriginalMediaRef(
                source_url=f"https://cdn.example/{name}/primary.webp",
                platform=f"market-{name}",
                role=MediaRole.PRIMARY,
                provenance=MediaProvenance.STRUCTURED_PRODUCT_DATA,
                ordinal=0,
                alt_text=f"{color} restart product",
                variant_label=color,
                content_type="image/webp",
                byte_size=256,
                sha256_hash=("a" if name == "a" else "b") * 64,
                local_filename=f"orig_000_{name}.webp",
            ),
        ),
        diagnostic_codes=(f"PERSISTED_{name.upper()}",),
    )


def _persist_catalog_and_sources(tmp_path):
    """Create durable inputs without returning any constructed domain object."""

    packs = (
        _source_pack("a", title="Restart Product Blue", color="Ultramarine"),
        _source_pack("b", title="Blue Product After Restart", color="Ultramarine"),
    )
    source_paths = tuple(
        serialize_source_pack(pack, str(tmp_path / f"source-{index}"))
        for index, pack in enumerate(packs)
    )
    members = tuple(SourceObservationIdentity.from_pack(pack) for pack in packs)
    pair = EntityResolutionResult(
        relationship=ProductRelationship.EXACT_VARIANT_MATCH,
        confidence=0.99,
        left=members[1],
        right=members[0],
        reasons=("persisted direct exact evidence",),
        evidence=(
            ResolutionEvidence(
                "PERSISTED_EXACT_VARIANT",
                "Human-reviewed exact variant across persisted observations",
            ),
        ),
    )
    graph = MultiObservationResolutionGraph(
        observations=tuple(reversed(members)),
        pairwise_results=(pair,),
        conflicts=(),
    )
    family_proposal = create_family_merge_proposal(
        graph,
        group_resolution_graph(graph).groups[0],
    )
    family_decision = create_family_merge_decision_record(
        family_proposal,
        decision=FamilyMergeDecision.APPROVE,
        actor="restart family reviewer",
        decided_at=datetime(2026, 8, 31, 10, tzinfo=timezone.utc),
    )
    family = create_canonical_family(family_decision, family_id="family-restart")
    variant_proposal = create_sellable_variant_proposal(family, family.members)
    variant_decision = create_sellable_variant_decision_record(
        variant_proposal,
        decision=SellableVariantDecision.APPROVE,
        actor="restart variant reviewer",
        decided_at=datetime(2026, 8, 31, 11, tzinfo=timezone.utc),
    )
    variant = create_canonical_sellable_variant(
        variant_decision,
        variant_id="variant-restart",
    )

    catalog_path = tmp_path / "canonical-catalog.sqlite"
    create_sqlite_canonical_catalog(catalog_path)
    register_sqlite_canonical_family(catalog_path, family)
    register_sqlite_canonical_variant(catalog_path, variant)
    return catalog_path, source_paths


def test_m3_knowledge_restarts_from_sqlite_and_typed_source_manifests(tmp_path):
    catalog_path, source_paths = _persist_catalog_and_sources(tmp_path)

    def _network_forbidden(*args, **kwargs):
        raise AssertionError("the M3 restart path must perform no network work")

    with patch.object(socket, "socket", side_effect=_network_forbidden):
        catalog = load_sqlite_canonical_catalog(catalog_path)
        rehydrated = tuple(
            deserialize_product_source_pack(path)
            for path in reversed(source_paths)
        )
        profile = build_canonical_variant_profile(
            catalog,
            variant_id="variant-restart",
            source_packs=rehydrated,
        )
        hits = retrieve_canonical_variant_profiles(
            (profile,),
            query="Ultramarine",
            limit=5,
        )
        context = build_canonical_rag_context(
            (profile,),
            question="Which persisted color evidence survived restart?",
            retrieval_query="Ultramarine",
            max_hits=5,
            max_context_utf8_bytes=32768,
        )
        rendered = render_canonical_rag_context(context)
        repeated = render_canonical_rag_context(
            build_canonical_rag_context(
                (profile,),
                question="Which persisted color evidence survived restart?",
                retrieval_query="Ultramarine",
                max_hits=5,
                max_context_utf8_bytes=32768,
            )
        )

    variant = catalog.variants[0]
    assert profile.members == variant.members
    assert tuple(observation.member for observation in profile.observations) == variant.members
    assert tuple(pack.source_pack_id for pack in rehydrated) == (
        "restart-pack-b",
        "restart-pack-a",
    )
    assert tuple(observation.member.source_pack_id for observation in profile.observations) == (
        "restart-pack-a",
        "restart-pack-b",
    )
    assert all(member.observed_at == OBSERVED_AT for member in profile.members)
    assert [item.fact.value for item in profile.fact_evidence] == [
        "Restart One",
        "Ultramarine",
        "Restart One",
        "Ultramarine",
    ]
    assert [item.media.alt_text for item in profile.media_evidence] == [
        "Ultramarine restart product",
        "Ultramarine restart product",
    ]
    assert len(hits) == 1
    assert hits[0].profile is profile
    assert context.hits[0].hit.profile is profile
    assert rendered == repeated
    assert '"schema":"canonical_variant_rag_context"' in rendered
    assert '"value":"Ultramarine"' in rendered
