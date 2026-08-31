"""Focused regressions for TASK-119 canonical catalog snapshot representation."""

from datetime import datetime, timedelta, timezone
from itertools import combinations
import json
from unittest.mock import patch

import pytest

from src.product_intelligence import (
    CANONICAL_CATALOG_SCHEMA,
    CANONICAL_CATALOG_SCHEMA_VERSION,
    CanonicalCatalogCodecError,
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
    decode_canonical_catalog,
    encode_canonical_catalog,
    group_resolution_graph,
    register_canonical_family,
    register_canonical_variant,
)


def _family():
    names = ("a", "b", "c")
    observed = datetime(2026, 8, 31, 15, 45, 12, 123456, tzinfo=timezone(timedelta(hours=7)))
    members = {
        name: SourceObservationIdentity(
            source_pack_id=f" pack/{name} ",
            platform="Thị trường 🛒",
            source_product_id=None if name == "c" else f"opaque:{name}",
            product_url=f"https://example.test/{name}?q=é",
            observed_at=observed,
        )
        for name in names
    }
    results = []
    for left_name, right_name in combinations(names, 2):
        relationship = (
            ProductRelationship.EXACT_VARIANT_MATCH
            if (left_name, right_name) == ("a", "b")
            else ProductRelationship.SAME_PRODUCT_FAMILY
        )
        results.append(
            EntityResolutionResult(
                relationship=relationship,
                confidence=0.875,
                left=members[right_name],
                right=members[left_name],
                reasons=(f"reason {left_name}/{right_name}",),
                evidence=(ResolutionEvidence(f"E-{left_name}{right_name}", "évidence"),),
            )
        )
    graph = MultiObservationResolutionGraph(
        observations=tuple(reversed(tuple(members.values()))),
        pairwise_results=tuple(reversed(results)),
        conflicts=(),
    )
    proposal = create_family_merge_proposal(graph, group_resolution_graph(graph).groups[0])
    decision = create_family_merge_decision_record(
        proposal,
        decision=FamilyMergeDecision.APPROVE,
        actor="reviewer/家庭",
        decided_at=datetime(2026, 8, 31, 17, 0, tzinfo=timezone(timedelta(hours=7))),
    )
    return create_canonical_family(decision, family_id="opaque.family/é")


def _catalog():
    family = _family()
    catalog = register_canonical_family(create_empty_canonical_catalog(), family).catalog
    for selected, variant_id in ((family.members[:2], "variant/pair"), ((family.members[2],), "variant/single")):
        proposal = create_sellable_variant_proposal(family, selected)
        decision = create_sellable_variant_decision_record(
            proposal,
            decision=SellableVariantDecision.APPROVE,
            actor="variant reviewer",
            decided_at=datetime(2026, 8, 31, 12, 30, tzinfo=timezone.utc),
        )
        variant = create_canonical_sellable_variant(decision, variant_id=variant_id)
        catalog = register_canonical_variant(catalog, variant).catalog
    return catalog


def test_empty_payload_is_exact_and_round_trips_to_a_new_value_equal_catalog():
    catalog = create_empty_canonical_catalog()
    payload = encode_canonical_catalog(catalog)

    assert CANONICAL_CATALOG_SCHEMA == "product_intelligence.canonical_catalog"
    assert CANONICAL_CATALOG_SCHEMA_VERSION == 1
    assert payload == (
        b'{"families":[],"schema":"product_intelligence.canonical_catalog",'
        b'"variants":[],"version":1}'
    )
    decoded = decode_canonical_catalog(payload)
    assert decoded == catalog and decoded is not catalog
    assert encode_canonical_catalog(decoded) == payload


def test_family_and_variants_round_trip_values_and_restore_source_aliasing():
    catalog = _catalog()
    payload = encode_canonical_catalog(catalog)
    decoded = decode_canonical_catalog(payload)

    assert decoded == catalog and decoded is not catalog
    family = decoded.families[0]
    source_pairs = family.approval.proposal.pair_evidence
    for variant in decoded.variants:
        assert variant.source_family is family
        assert all(member is family.members[family.members.index(member)] for member in variant.members)
        assert all(any(pair is source for source in source_pairs) for pair in variant.proposal.pair_evidence)
        assert all(any(pair is source for source in source_pairs) for pair in variant.proposal.projection.direct_exact_evidence)
        for gap in variant.proposal.projection.exactness_gaps:
            assert any(gap.direct_evidence is source for source in source_pairs)
            assert all(any(edge is source for source in source_pairs) for edge in gap.witness_path)
    assert encode_canonical_catalog(decoded) == payload


def test_equivalent_aware_instants_and_independent_construction_are_identical_bytes():
    first = _catalog()
    second = _catalog()

    assert second == first and second is not first
    assert encode_canonical_catalog(second) == encode_canonical_catalog(first)
    text = encode_canonical_catalog(first).decode("utf-8")
    assert "2026-08-31T08:45:12.123456Z" in text
    assert text.endswith("}") and "\n" not in text and " " not in text


@pytest.mark.parametrize(
    "payload",
    (
        b"\xef\xbb\xbf{}",
        b"\xff",
        b"{}",
        b'{"families":[],"schema":"product_intelligence.canonical_catalog","variants":[],"version":1}\n',
        b'{"families":[],"schema":"product_intelligence.canonical_catalog","schema":"product_intelligence.canonical_catalog","variants":[],"version":1}',
        b'{"families":[],"schema":"product_intelligence.canonical_catalog","variants":[],"version":NaN}',
    ),
)
def test_decode_rejects_malformed_duplicate_nonfinite_and_noncanonical_payloads(payload):
    with pytest.raises(CanonicalCatalogCodecError):
        decode_canonical_catalog(payload)


def test_decode_rejects_broken_reference_lineage():
    document = json.loads(encode_canonical_catalog(_catalog()))
    document["variants"][0]["members"] = [99]
    tampered = json.dumps(document, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()

    with pytest.raises(CanonicalCatalogCodecError):
        decode_canonical_catalog(tampered)


def test_decode_uses_registration_but_no_inference_or_public_workflow_factories():
    payload = encode_canonical_catalog(_catalog())
    with (
        patch("src.product_intelligence.entity_resolution.resolve_product_entities") as resolver,
        patch("src.product_intelligence.entity_grouping.group_resolution_graph") as grouping,
        patch("src.product_intelligence.sellable_variant_evidence.project_sellable_variant_evidence") as projector,
        patch("src.product_intelligence.family_merge_approval.create_family_merge_proposal") as family_proposal,
        patch("src.product_intelligence.sellable_variant_approval.create_sellable_variant_proposal") as variant_proposal,
        patch("src.product_intelligence.family_merge_approval.create_family_merge_decision_record") as family_decision,
        patch("src.product_intelligence.sellable_variant_approval.create_sellable_variant_decision_record") as variant_decision,
        patch("builtins.open") as filesystem,
    ):
        decoded = decode_canonical_catalog(payload)

    for operation in (
        resolver,
        grouping,
        projector,
        family_proposal,
        variant_proposal,
        family_decision,
        variant_decision,
        filesystem,
    ):
        operation.assert_not_called()
    assert decoded == _catalog()
