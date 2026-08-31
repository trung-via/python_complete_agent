"""Tests for the evidence-complete Human family merge approval boundary."""

from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from src.product_intelligence import (
    EntityResolutionResult,
    FamilyMergeApprovalError,
    FamilyMergeDecision,
    FamilyMergeDecisionRecord,
    FamilyMergePairEvidence,
    FamilyMergeProposal,
    MultiObservationResolutionGraph,
    PairwiseConflictEvidence,
    ProductFamilyConsistencyConflict,
    ProductRelationship,
    ProvisionalGroupStatus,
    ResolutionEvidence,
    SourceObservationIdentity,
    create_family_merge_decision,
    create_family_merge_decision_record,
    create_family_merge_proposal,
    group_resolution_graph,
    record_family_merge_decision,
)


DECIDED_AT = datetime(2026, 8, 31, 9, 30, tzinfo=timezone.utc)


def identity(name: str) -> SourceObservationIdentity:
    return SourceObservationIdentity(
        source_pack_id=f"pack-{name}",
        platform="test-market",
        source_product_id=name,
        product_url=f"https://market.example/{name}",
        observed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def pair(
    left: SourceObservationIdentity,
    right: SourceObservationIdentity,
    relationship: ProductRelationship,
    confidence: float,
    code: str,
) -> EntityResolutionResult:
    return EntityResolutionResult(
        relationship=relationship,
        confidence=confidence,
        left=left,
        right=right,
        reasons=(f"reason-{code}",),
        evidence=(ResolutionEvidence(code, f"detail-{code}"),),
    )


def positive_connected_graph() -> MultiObservationResolutionGraph:
    a, b, c = identity("a"), identity("b"), identity("c")
    return MultiObservationResolutionGraph(
        observations=(c, a, b),
        pairwise_results=(
            pair(c, a, ProductRelationship.UNCERTAIN, 0.23, "AC-UNCERTAIN"),
            pair(b, c, ProductRelationship.EXACT_VARIANT_MATCH, 0.98, "BC-EXACT"),
            pair(a, b, ProductRelationship.SAME_PRODUCT_FAMILY, 0.86, "AB-FAMILY"),
        ),
        conflicts=(),
    )


def canonical_positive_group(graph: MultiObservationResolutionGraph):
    result = group_resolution_graph(graph)
    assert len(result.groups) == 1
    assert result.groups[0].status is ProvisionalGroupStatus.POSITIVE_CONNECTED
    return result.groups[0]


def test_proposal_is_evidence_complete_and_preserves_internal_uncertain_pair():
    graph = positive_connected_graph()
    group = canonical_positive_group(graph)

    proposal = create_family_merge_proposal(graph, group)

    assert isinstance(proposal, FamilyMergeProposal)
    assert proposal.members is group.members
    assert proposal.member_count == 3
    assert len(proposal.pair_evidence) == 3
    assert all(isinstance(value, FamilyMergePairEvidence) for value in proposal.pair_evidence)
    assert tuple((value.left, value.right) for value in proposal.pair_evidence) == (
        (group.members[0], group.members[1]),
        (group.members[0], group.members[2]),
        (group.members[1], group.members[2]),
    )

    source_by_pair = {
        frozenset((value.left, value.right)): value
        for value in graph.pairwise_results
    }
    for value in proposal.pair_evidence:
        source = source_by_pair[frozenset((value.left, value.right))]
        assert value.relationship is source.relationship
        assert value.confidence == source.confidence
        assert value.reasons is source.reasons
        assert value.evidence is source.evidence

    uncertain = [
        value
        for value in proposal.pair_evidence
        if value.relationship is ProductRelationship.UNCERTAIN
    ]
    assert len(uncertain) == 1
    assert not hasattr(proposal, "decision")
    assert not hasattr(proposal, "approved")


def test_pair_orientation_and_sequence_are_invariant_to_graph_permutation():
    baseline_graph = positive_connected_graph()
    baseline_group = canonical_positive_group(baseline_graph)
    baseline = create_family_merge_proposal(baseline_graph, baseline_group)

    reversed_graph = MultiObservationResolutionGraph(
        observations=tuple(reversed(baseline_graph.observations)),
        pairwise_results=tuple(
            replace(value, left=value.right, right=value.left)
            for value in reversed(baseline_graph.pairwise_results)
        ),
        conflicts=(),
    )
    reversed_group = canonical_positive_group(reversed_graph)

    assert create_family_merge_proposal(reversed_graph, reversed_group) == baseline


def test_singleton_and_conflicted_groups_fail_closed():
    a, b, c = identity("a"), identity("b"), identity("c")
    singleton_graph = MultiObservationResolutionGraph(
        observations=(a, b),
        pairwise_results=(pair(a, b, ProductRelationship.UNCERTAIN, 0.1, "AB"),),
        conflicts=(),
    )
    singleton = group_resolution_graph(singleton_graph).groups[0]
    assert singleton.status is ProvisionalGroupStatus.SINGLETON
    with pytest.raises(FamilyMergeApprovalError, match="POSITIVE_CONNECTED"):
        create_family_merge_proposal(singleton_graph, singleton)

    ab = pair(a, b, ProductRelationship.SAME_PRODUCT_FAMILY, 0.86, "AB")
    bc = pair(b, c, ProductRelationship.SAME_PRODUCT_FAMILY, 0.86, "BC")
    ac = pair(a, c, ProductRelationship.DIFFERENT_PRODUCT, 0.99, "AC")
    contradiction = PairwiseConflictEvidence(
        left=a,
        right=c,
        relationship=ac.relationship,
        confidence=ac.confidence,
        reasons=ac.reasons,
    )
    conflict = ProductFamilyConsistencyConflict(
        conflict_type="POSITIVE_FAMILY_CHAIN_CONTRADICTS_DIFFERENT_PRODUCT",
        contradictory_pair=contradiction,
        positive_path=(
            PairwiseConflictEvidence(a, b, ab.relationship, ab.confidence, ab.reasons),
            PairwiseConflictEvidence(b, c, bc.relationship, bc.confidence, bc.reasons),
        ),
        affected_identities=(a, b, c),
        detail="preserved graph conflict",
    )
    conflicted_graph = MultiObservationResolutionGraph(
        observations=(a, b, c),
        pairwise_results=(ab, bc, ac),
        conflicts=(conflict,),
    )
    conflicted = group_resolution_graph(conflicted_graph).groups[0]
    assert conflicted.status is ProvisionalGroupStatus.CONFLICTED
    with pytest.raises(FamilyMergeApprovalError, match="POSITIVE_CONNECTED"):
        create_family_merge_proposal(conflicted_graph, conflicted)


def test_forged_stale_absent_and_duplicate_member_groups_fail_lineage_check():
    graph = positive_connected_graph()
    group = canonical_positive_group(graph)
    outsider = identity("outsider")

    forged = replace(group, members=(group.members[0], group.members[1]))
    stale = replace(group, members=(group.members[0], group.members[1], outsider))
    duplicated = replace(group, members=(group.members[0], group.members[0]))
    absent = replace(
        group,
        members=(identity("x"), identity("y")),
    )

    for invalid_group in (forged, stale, duplicated, absent):
        with pytest.raises(FamilyMergeApprovalError, match="canonical group"):
            create_family_merge_proposal(graph, invalid_group)


def test_missing_duplicate_and_nonmember_induced_pairs_fail_closed():
    graph = positive_connected_graph()
    group = canonical_positive_group(graph)

    missing = replace(graph, pairwise_results=graph.pairwise_results[1:])
    missing_group = canonical_positive_group(missing)
    with pytest.raises(FamilyMergeApprovalError, match="exactly one result"):
        create_family_merge_proposal(missing, missing_group)

    duplicate = replace(
        graph,
        pairwise_results=graph.pairwise_results + (graph.pairwise_results[0],),
    )
    duplicate_group = canonical_positive_group(duplicate)
    with pytest.raises(FamilyMergeApprovalError, match="exactly one result"):
        create_family_merge_proposal(duplicate, duplicate_group)

    outsider = identity("outsider")
    nonmember = replace(
        graph,
        pairwise_results=graph.pairwise_results
        + (pair(group.members[0], outsider, ProductRelationship.UNCERTAIN, 0.1, "OUT"),),
    )
    nonmember_group = canonical_positive_group(nonmember)
    with pytest.raises(FamilyMergeApprovalError, match="non-member endpoint"):
        create_family_merge_proposal(nonmember, nonmember_group)


def test_explicit_approve_and_reject_preserve_exact_proposal():
    graph = positive_connected_graph()
    proposal = create_family_merge_proposal(graph, canonical_positive_group(graph))

    approve = create_family_merge_decision_record(
        proposal,
        decision=FamilyMergeDecision.APPROVE,
        actor="human-reviewer",
        decided_at=DECIDED_AT,
    )
    reject = record_family_merge_decision(
        proposal,
        decision=FamilyMergeDecision.REJECT,
        actor="human-reviewer",
        decided_at=DECIDED_AT,
    )

    assert isinstance(approve, FamilyMergeDecisionRecord)
    assert approve.proposal is proposal
    assert approve.decision is FamilyMergeDecision.APPROVE
    assert reject.proposal is proposal
    assert reject.decision is FamilyMergeDecision.REJECT
    assert create_family_merge_decision(
        proposal,
        decision=FamilyMergeDecision.APPROVE,
        actor="human-reviewer",
        decided_at=DECIDED_AT,
    ) == approve


@pytest.mark.parametrize("decision", [None, "APPROVE", True])
def test_decision_must_be_explicit_enum(decision):
    graph = positive_connected_graph()
    proposal = create_family_merge_proposal(graph, canonical_positive_group(graph))
    with pytest.raises(FamilyMergeApprovalError, match="explicit FamilyMergeDecision"):
        create_family_merge_decision_record(
            proposal,
            decision=decision,
            actor="reviewer",
            decided_at=DECIDED_AT,
        )


@pytest.mark.parametrize("actor", [None, "", "   ", "line\nbreak", "line\rbreak", "nul\x00actor"])
def test_actor_must_be_explicit_nonempty_and_single_line(actor):
    graph = positive_connected_graph()
    proposal = create_family_merge_proposal(graph, canonical_positive_group(graph))
    with pytest.raises(FamilyMergeApprovalError, match="actor"):
        create_family_merge_decision_record(
            proposal,
            decision=FamilyMergeDecision.REJECT,
            actor=actor,
            decided_at=DECIDED_AT,
        )


@pytest.mark.parametrize(
    "decided_at",
    [None, "2026-08-31T09:30:00Z", datetime(2026, 8, 31, 9, 30)],
)
def test_decided_at_must_be_explicit_timezone_aware_datetime(decided_at):
    graph = positive_connected_graph()
    proposal = create_family_merge_proposal(graph, canonical_positive_group(graph))
    with pytest.raises(FamilyMergeApprovalError, match="decided_at"):
        create_family_merge_decision_record(
            proposal,
            decision=FamilyMergeDecision.APPROVE,
            actor="reviewer",
            decided_at=decided_at,
        )


def test_values_are_immutable_and_proposal_cannot_be_forged_directly():
    graph = positive_connected_graph()
    proposal = create_family_merge_proposal(graph, canonical_positive_group(graph))
    record = create_family_merge_decision_record(
        proposal,
        decision=FamilyMergeDecision.APPROVE,
        actor="reviewer",
        decided_at=DECIDED_AT,
    )

    with pytest.raises(FrozenInstanceError):
        proposal.members = ()
    with pytest.raises(FrozenInstanceError):
        proposal.pair_evidence[0].confidence = 0.0
    with pytest.raises(FrozenInstanceError):
        record.decision = FamilyMergeDecision.REJECT
    with pytest.raises(FamilyMergeApprovalError, match="must be created"):
        FamilyMergeProposal(
            members=proposal.members,
            pair_evidence=proposal.pair_evidence,
        )


def test_proposal_creation_reexecutes_nothing_and_has_no_io_side_effects():
    graph = positive_connected_graph()
    group = canonical_positive_group(graph)

    with (
        patch("src.product_intelligence.entity_resolution.resolve_product_entities") as pairwise,
        patch("src.product_intelligence.entity_resolution_graph.resolve_multi_observations") as multi,
        patch("src.product_intelligence.entity_resolution_graph.MultiObservationEntityResolver.resolve") as facade,
        patch("builtins.open") as filesystem_open,
    ):
        proposal = create_family_merge_proposal(graph, group)
        record = create_family_merge_decision_record(
            proposal,
            decision=FamilyMergeDecision.APPROVE,
            actor="reviewer",
            decided_at=DECIDED_AT,
        )

    pairwise.assert_not_called()
    multi.assert_not_called()
    facade.assert_not_called()
    filesystem_open.assert_not_called()
    assert record.proposal == proposal


def test_public_values_expose_no_identity_or_automation_authority():
    graph = positive_connected_graph()
    proposal = create_family_merge_proposal(graph, canonical_positive_group(graph))
    forbidden = {
        "proposal_id",
        "group_id",
        "family_id",
        "product_id",
        "variant_id",
        "merge_confidence",
        "aggregate_confidence",
        "automatic_merge",
        "merge",
        "persist",
        "enqueue",
    }
    assert forbidden.isdisjoint(dir(proposal))
