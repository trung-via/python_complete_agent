"""Evidence-complete Human approval boundary for provisional product families.

This module projects one exact canonical TASK-111 positive-connected group over
its existing TASK-109 graph evidence.  It does not execute entity resolution,
infer pairwise truth, create canonical identity, merge observations, or persist
the resulting proposal or decision.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass
from datetime import datetime
from enum import Enum

from src.product_intelligence.entity_grouping import (
    ProvisionalGroupStatus,
    ProvisionalProductFamilyGroup,
    group_resolution_graph,
)
from src.product_intelligence.entity_resolution import (
    EntityResolutionResult,
    ProductRelationship,
    ResolutionEvidence,
    SourceObservationIdentity,
)
from src.product_intelligence.entity_resolution_graph import (
    MultiObservationResolutionGraph,
)


class FamilyMergeApprovalError(ValueError):
    """Raised when a family merge proposal or Human decision is invalid."""


class FamilyMergeDecision(str, Enum):
    """The only explicit Human decisions at the family merge boundary."""

    APPROVE = "APPROVE"
    REJECT = "REJECT"


@dataclass(frozen=True)
class FamilyMergePairEvidence:
    """One canonically oriented, otherwise unchanged TASK-108 pair result."""

    left: SourceObservationIdentity
    right: SourceObservationIdentity
    relationship: ProductRelationship
    confidence: float
    reasons: tuple[str, ...]
    evidence: tuple[ResolutionEvidence, ...]


_PROPOSAL_LINEAGE = object()


@dataclass(frozen=True)
class FamilyMergeProposal:
    """Immutable evidence-complete proposal for one canonical TASK-111 group."""

    members: tuple[SourceObservationIdentity, ...]
    pair_evidence: tuple[FamilyMergePairEvidence, ...]
    _lineage: InitVar[object] = None

    def __post_init__(self, _lineage: object) -> None:
        if _lineage is not _PROPOSAL_LINEAGE:
            raise FamilyMergeApprovalError(
                "FamilyMergeProposal must be created from an existing graph and "
                "its exact canonical group"
            )

    @property
    def member_count(self) -> int:
        return len(self.members)


@dataclass(frozen=True)
class FamilyMergeDecisionRecord:
    """Immutable record of one explicit Human decision on an exact proposal."""

    proposal: FamilyMergeProposal
    decision: FamilyMergeDecision
    actor: str
    decided_at: datetime

    def __post_init__(self) -> None:
        _validate_proposal(self.proposal)
        if not isinstance(self.decision, FamilyMergeDecision):
            raise FamilyMergeApprovalError(
                "decision must be an explicit FamilyMergeDecision"
            )
        _validate_actor(self.actor)
        _validate_decided_at(self.decided_at)


def create_family_merge_proposal(
    graph: MultiObservationResolutionGraph,
    group: ProvisionalProductFamilyGroup,
) -> FamilyMergeProposal:
    """Create a proposal from one graph and one exact canonical group projection.

    The existing TASK-111 projection is called only to prove the supplied group's
    lineage.  All proposal semantics are copied from preserved TASK-109 pairwise
    results; no entity-resolution operation is called.
    """

    if not isinstance(graph, MultiObservationResolutionGraph):
        raise FamilyMergeApprovalError(
            "graph must be an existing MultiObservationResolutionGraph"
        )
    if not isinstance(group, ProvisionalProductFamilyGroup):
        raise FamilyMergeApprovalError(
            "group must be an existing ProvisionalProductFamilyGroup"
        )

    canonical_groups = group_resolution_graph(graph).groups
    if sum(candidate == group for candidate in canonical_groups) != 1:
        raise FamilyMergeApprovalError(
            "group must match exactly one canonical group projected from graph"
        )
    if (
        group.status is not ProvisionalGroupStatus.POSITIVE_CONNECTED
        or group.conflicts != ()
    ):
        raise FamilyMergeApprovalError(
            "only a conflict-free POSITIVE_CONNECTED canonical group is approvable"
        )

    member_positions = {member: index for index, member in enumerate(group.members)}
    if len(member_positions) != len(group.members):
        raise FamilyMergeApprovalError("canonical group members must be unique")

    observation_identities = set(graph.observations)
    induced_results: dict[tuple[int, int], list[EntityResolutionResult]] = {}
    for result in graph.pairwise_results:
        if not isinstance(result, EntityResolutionResult):
            raise FamilyMergeApprovalError(
                "graph pairwise results must be EntityResolutionResult values"
            )
        if not isinstance(result.left, SourceObservationIdentity) or not isinstance(
            result.right, SourceObservationIdentity
        ):
            raise FamilyMergeApprovalError(
                "graph pairwise result endpoints must be SourceObservationIdentity values"
            )
        if (
            result.left not in observation_identities
            or result.right not in observation_identities
        ):
            raise FamilyMergeApprovalError(
                "pairwise result endpoints must belong to graph observations"
            )

        left_position = member_positions.get(result.left)
        right_position = member_positions.get(result.right)
        if left_position is None or right_position is None:
            continue
        if left_position == right_position:
            raise FamilyMergeApprovalError(
                "induced pair evidence must reference two distinct members"
            )

        pair_position = tuple(sorted((left_position, right_position)))
        induced_results.setdefault(pair_position, []).append(result)

    pair_evidence: list[FamilyMergePairEvidence] = []
    member_count = len(group.members)
    for left_position in range(member_count):
        for right_position in range(left_position + 1, member_count):
            pair_position = (left_position, right_position)
            matches = induced_results.get(pair_position, ())
            if len(matches) != 1:
                raise FamilyMergeApprovalError(
                    "graph must contain exactly one result for every induced "
                    "unordered member pair"
                )
            preserved = matches[0]
            pair_evidence.append(
                FamilyMergePairEvidence(
                    left=group.members[left_position],
                    right=group.members[right_position],
                    relationship=preserved.relationship,
                    confidence=preserved.confidence,
                    reasons=preserved.reasons,
                    evidence=preserved.evidence,
                )
            )

    expected_pair_count = member_count * (member_count - 1) // 2
    if len(induced_results) != expected_pair_count:
        raise FamilyMergeApprovalError(
            "graph contains malformed or duplicated induced pair evidence"
        )

    return _build_family_merge_proposal(
        members=group.members,
        pair_evidence=tuple(pair_evidence),
    )


def _rehydrate_family_merge_proposal(
    *,
    members: tuple[SourceObservationIdentity, ...],
    pair_evidence: tuple[FamilyMergePairEvidence, ...],
) -> FamilyMergeProposal:
    """Rehydrate one already-admitted proposal without upstream inference.

    This deliberately private entry point exists only for the canonical snapshot
    codec.  It shares the structural builder used by the public graph-backed path
    while leaving the anti-forgery dataclass boundary intact.
    """

    return _build_family_merge_proposal(
        members=members,
        pair_evidence=pair_evidence,
    )


def _build_family_merge_proposal(
    *,
    members: tuple[SourceObservationIdentity, ...],
    pair_evidence: tuple[FamilyMergePairEvidence, ...],
) -> FamilyMergeProposal:
    if type(members) is not tuple or len(members) < 2:
        raise FamilyMergeApprovalError(
            "proposal members must be an explicit tuple of at least two observations"
        )
    if any(type(member) is not SourceObservationIdentity for member in members):
        raise FamilyMergeApprovalError(
            "proposal members must be exact SourceObservationIdentity values"
        )
    if len(set(members)) != len(members):
        raise FamilyMergeApprovalError("proposal members must be unique")
    if type(pair_evidence) is not tuple:
        raise FamilyMergeApprovalError("proposal pair evidence must be an exact tuple")

    expected_endpoints = tuple(
        (members[left], members[right])
        for left in range(len(members))
        for right in range(left + 1, len(members))
    )
    if len(pair_evidence) != len(expected_endpoints):
        raise FamilyMergeApprovalError("proposal is not evidence-complete")
    for pair, (left, right) in zip(pair_evidence, expected_endpoints):
        if type(pair) is not FamilyMergePairEvidence:
            raise FamilyMergeApprovalError(
                "proposal pair evidence must contain exact FamilyMergePairEvidence values"
            )
        if pair.left is not left or pair.right is not right:
            raise FamilyMergeApprovalError(
                "proposal pair evidence must follow canonical member-pair order"
            )

    return FamilyMergeProposal(
        members=members,
        pair_evidence=pair_evidence,
        _lineage=_PROPOSAL_LINEAGE,
    )


def create_family_merge_decision_record(
    proposal: FamilyMergeProposal,
    *,
    decision: FamilyMergeDecision,
    actor: str,
    decided_at: datetime,
) -> FamilyMergeDecisionRecord:
    """Record an explicit Human decision without mutation or side effects."""

    return FamilyMergeDecisionRecord(
        proposal=proposal,
        decision=decision,
        actor=actor,
        decided_at=decided_at,
    )


def _validate_proposal(proposal: object) -> None:
    if not isinstance(proposal, FamilyMergeProposal):
        raise FamilyMergeApprovalError(
            "proposal must be an exact FamilyMergeProposal"
        )
    expected_pair_count = len(proposal.members) * (len(proposal.members) - 1) // 2
    if len(proposal.members) < 2 or len(proposal.pair_evidence) != expected_pair_count:
        raise FamilyMergeApprovalError("proposal is not evidence-complete")


def _validate_actor(actor: object) -> None:
    if not isinstance(actor, str) or not actor.strip():
        raise FamilyMergeApprovalError(
            "actor must be an explicit non-empty string"
        )
    if any(character in actor for character in ("\r", "\n", "\x00")):
        raise FamilyMergeApprovalError("actor must be a single-line identifier")


def _validate_decided_at(decided_at: object) -> None:
    if not isinstance(decided_at, datetime):
        raise FamilyMergeApprovalError(
            "decided_at must be an explicit datetime"
        )
    try:
        offset = decided_at.utcoffset()
    except (OverflowError, ValueError) as exc:
        raise FamilyMergeApprovalError(
            "decided_at must be timezone-aware"
        ) from exc
    if decided_at.tzinfo is None or offset is None:
        raise FamilyMergeApprovalError("decided_at must be timezone-aware")


# Concise aliases for callers that name the operation rather than the record.
create_family_merge_decision = create_family_merge_decision_record
record_family_merge_decision = create_family_merge_decision_record


__all__ = [
    "FamilyMergeApprovalError",
    "FamilyMergeDecision",
    "FamilyMergeDecisionRecord",
    "FamilyMergePairEvidence",
    "FamilyMergeProposal",
    "create_family_merge_decision",
    "create_family_merge_decision_record",
    "create_family_merge_proposal",
    "record_family_merge_decision",
]
