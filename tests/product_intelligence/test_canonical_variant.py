"""Regressions for bounded canonical sellable-variant admission."""

from dataclasses import FrozenInstanceError, fields, replace
from datetime import datetime, timezone
from inspect import Parameter, signature
from itertools import combinations
from unittest.mock import patch

import pytest

from src.product_intelligence import (
    CanonicalSellableVariant,
    CanonicalVariantAdmissionError,
    EntityResolutionResult,
    FamilyMergeDecision,
    MultiObservationResolutionGraph,
    ProductRelationship,
    ResolutionEvidence,
    SellableVariantDecision,
    SourceObservationIdentity,
    create_canonical_family,
    create_canonical_sellable_variant,
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


def approved_family():
    relationships = {
        ("a", "b"): ProductRelationship.EXACT_VARIANT_MATCH,
        ("a", "c"): ProductRelationship.SAME_PRODUCT_FAMILY,
        ("b", "c"): ProductRelationship.SAME_PRODUCT_FAMILY,
    }
    identities = {name: identity(name) for name in ("a", "b", "c")}
    results = []
    for left_name, right_name in combinations(identities, 2):
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
    family_approval = create_family_merge_decision_record(
        family_proposal,
        decision=FamilyMergeDecision.APPROVE,
        actor="family-reviewer",
        decided_at=datetime(2026, 8, 31, 8, 0, tzinfo=timezone.utc),
    )
    return create_canonical_family(family_approval, family_id="family-opaque/01")


def member(family, name: str) -> SourceObservationIdentity:
    return next(value for value in family.members if value.source_product_id == name)


def decision_for(family, names, decision=SellableVariantDecision.APPROVE):
    proposal = create_sellable_variant_proposal(
        family,
        tuple(member(family, name) for name in names),
    )
    return create_sellable_variant_decision_record(
        proposal,
        decision=decision,
        actor="variant-reviewer",
        decided_at=datetime(2026, 8, 31, 10, 15, tzinfo=timezone.utc),
    )


def test_public_boundary_has_only_exact_decision_and_keyword_only_variant_id():
    parameters = tuple(signature(create_canonical_sellable_variant).parameters.values())

    assert tuple(parameter.name for parameter in parameters) == (
        "decision_record",
        "variant_id",
    )
    assert parameters[0].kind is Parameter.POSITIONAL_OR_KEYWORD
    assert parameters[1].kind is Parameter.KEYWORD_ONLY

    approval = decision_for(approved_family(), ("c",))
    with pytest.raises(TypeError):
        create_canonical_sellable_variant(approval, "variant-positional")
    for extra in ("family", "family_id", "members", "projection", "evidence"):
        with pytest.raises(TypeError):
            create_canonical_sellable_variant(
                approval,
                variant_id="variant-extra",
                **{extra: object()},
            )


@pytest.mark.parametrize("names", [("c",), ("a", "b")])
def test_approve_admits_singleton_and_multi_member_exact_lineage(names):
    family = approved_family()
    approval = decision_for(family, names)

    variant = create_canonical_sellable_variant(
        approval,
        variant_id="Opaque:Variant/Case-01",
    )

    assert variant.variant_id == "Opaque:Variant/Case-01"
    assert variant.approval is approval
    assert variant.proposal is approval.proposal
    assert variant.source_family is approval.proposal.source_family
    assert variant.source_family is family
    assert variant.family_id is family.family_id
    assert variant.members is approval.proposal.members
    assert variant.member_count == len(names)
    assert variant.proposal.projection is approval.proposal.projection
    assert variant.proposal.pair_evidence is approval.proposal.pair_evidence
    assert tuple(field.name for field in fields(variant)) == ("variant_id", "approval")


def test_reject_wrong_record_types_and_substitutes_fail_closed():
    family = approved_family()
    rejected = decision_for(family, ("c",), SellableVariantDecision.REJECT)
    approved = decision_for(family, ("c",))

    class DecisionSubstitute(type(approved)):
        pass

    substitute = DecisionSubstitute(
        proposal=approved.proposal,
        decision=approved.decision,
        actor=approved.actor,
        decided_at=approved.decided_at,
    )
    for invalid in (rejected, approved.proposal, substitute, object(), None):
        with pytest.raises(CanonicalVariantAdmissionError):
            create_canonical_sellable_variant(invalid, variant_id="variant-rejected")


@pytest.mark.parametrize(
    "invalid_id",
    [None, 1, "", " ", " leading", "trailing ", "a\nb", "a\rb", "a\x00b"],
)
def test_invalid_variant_ids_fail_closed(invalid_id):
    approval = decision_for(approved_family(), ("c",))

    with pytest.raises(CanonicalVariantAdmissionError):
        create_canonical_sellable_variant(approval, variant_id=invalid_id)


def test_opaque_variant_id_is_preserved_without_generation_or_normalization():
    approval = decision_for(approved_family(), ("c",))
    opaque_id = "Vendor::ID/AbC_001?literal=yes"

    variant = create_canonical_sellable_variant(approval, variant_id=opaque_id)

    assert variant.variant_id is opaque_id


def test_variant_is_immutable_factory_only_and_repeatable_without_registry_claims():
    approval = decision_for(approved_family(), ("a", "b"))
    first = create_canonical_sellable_variant(approval, variant_id="variant-repeat")
    second = create_canonical_sellable_variant(approval, variant_id="variant-repeat")

    assert first == second
    assert first is not second
    assert first.approval is second.approval is approval
    with pytest.raises(FrozenInstanceError):
        first.variant_id = "changed"
    with pytest.raises(CanonicalVariantAdmissionError):
        CanonicalSellableVariant(variant_id="forged", approval=approval)
    with pytest.raises(CanonicalVariantAdmissionError):
        replace(first, variant_id="forged-replacement")


def test_public_schema_exposes_no_profile_persistence_or_partition_authority():
    variant = create_canonical_sellable_variant(
        decision_for(approved_family(), ("c",)),
        variant_id="variant-schema",
    )
    forbidden = {
        "color",
        "size",
        "capacity",
        "sku",
        "media",
        "profile",
        "aggregate_confidence",
        "catalog",
        "persistence_handle",
        "retrieval_key",
        "complete_partition",
        "persist",
        "mutate",
    }

    assert forbidden.isdisjoint(dir(variant))


def test_admission_reexecutes_no_upstream_factory_or_external_work():
    approval = decision_for(approved_family(), ("a", "b"))

    with (
        patch("src.product_intelligence.sellable_variant_evidence.project_sellable_variant_evidence") as projection,
        patch("src.product_intelligence.sellable_variant_approval.create_sellable_variant_proposal") as variant_proposal,
        patch("src.product_intelligence.sellable_variant_approval.create_sellable_variant_decision_record") as variant_decision,
        patch("src.product_intelligence.canonical_family.create_canonical_family") as family_admission,
        patch("src.product_intelligence.family_merge_approval.create_family_merge_proposal") as family_proposal,
        patch("src.product_intelligence.entity_resolution.resolve_product_entities") as pairwise,
        patch("src.product_intelligence.entity_resolution_graph.resolve_multi_observations") as multi,
        patch("src.product_intelligence.entity_grouping.group_resolution_graph") as grouping,
        patch("uuid.uuid4") as uuid_generator,
        patch("random.random") as random_generator,
        patch("time.time") as clock,
        patch("os.getenv") as environment,
        patch("builtins.open") as filesystem_open,
    ):
        variant = create_canonical_sellable_variant(
            approval,
            variant_id="variant-no-work",
        )

    projection.assert_not_called()
    variant_proposal.assert_not_called()
    variant_decision.assert_not_called()
    family_admission.assert_not_called()
    family_proposal.assert_not_called()
    pairwise.assert_not_called()
    multi.assert_not_called()
    grouping.assert_not_called()
    uuid_generator.assert_not_called()
    random_generator.assert_not_called()
    clock.assert_not_called()
    environment.assert_not_called()
    filesystem_open.assert_not_called()
    assert variant.approval is approval
