"""Explicit Human decision boundary for sellable-variant proposals.

The boundary consumes exactly one admitted canonical product family and one
caller-selected member tuple.  TASK-115 is the sole variant-evidence authority:
the proposal preserves its exact projection and admits a selection only when it
is an all-pairs direct-exact set closed under every preserved direct exact edge.
No variant identity, profile, partition, persistence, or external work occurs.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass
from datetime import datetime
from enum import Enum

from src.product_intelligence.canonical_family import CanonicalProductFamily
from src.product_intelligence.entity_resolution import (
    ProductRelationship,
    SourceObservationIdentity,
)
from src.product_intelligence.family_merge_approval import FamilyMergePairEvidence
from src.product_intelligence.sellable_variant_evidence import (
    SellableVariantEvidenceProjection,
    project_sellable_variant_evidence,
)


class SellableVariantApprovalError(ValueError):
    """Raised when a sellable-variant proposal or decision is invalid."""


class SellableVariantDecision(str, Enum):
    """The only explicit Human decisions at the proposal boundary."""

    APPROVE = "APPROVE"
    REJECT = "REJECT"


_PROPOSAL_LINEAGE = object()


@dataclass(frozen=True)
class SellableVariantProposal:
    """One immutable, evidence-complete selection inside one source family."""

    projection: SellableVariantEvidenceProjection
    members: tuple[SourceObservationIdentity, ...]
    pair_evidence: tuple[FamilyMergePairEvidence, ...]
    _lineage: InitVar[object] = None

    def __post_init__(self, _lineage: object) -> None:
        if _lineage is not _PROPOSAL_LINEAGE:
            raise SellableVariantApprovalError(
                "SellableVariantProposal must be created by the canonical "
                "sellable-variant proposal factory"
            )

    @property
    def source_family(self) -> CanonicalProductFamily:
        """Return the exact canonical family retained by the projection."""

        return self.projection.source_family

    @property
    def evidence_projection(self) -> SellableVariantEvidenceProjection:
        """Compatibility name for the exact retained TASK-115 projection."""

        return self.projection

    @property
    def selected_members(self) -> tuple[SourceObservationIdentity, ...]:
        """Return the exact selected tuple in canonical source-family order."""

        return self.members

    @property
    def member_count(self) -> int:
        return len(self.members)


@dataclass(frozen=True)
class SellableVariantDecisionRecord:
    """One immutable explicit Human decision over one exact proposal."""

    proposal: SellableVariantProposal
    decision: SellableVariantDecision
    actor: str
    decided_at: datetime

    def __post_init__(self) -> None:
        _validate_proposal(self.proposal)
        if type(self.decision) is not SellableVariantDecision:
            raise SellableVariantApprovalError(
                "decision must be an explicit SellableVariantDecision"
            )
        _validate_actor(self.actor)
        _validate_decided_at(self.decided_at)


def create_sellable_variant_proposal(
    family: CanonicalProductFamily,
    selected_members: tuple[SourceObservationIdentity, ...],
) -> SellableVariantProposal:
    """Create one explicit direct-exact, exact-edge-closed proposal.

    The caller supplies the selection; this operation never discovers or ranks
    groups.  The TASK-115 projection is constructed exactly once and is the
    only source consulted for variant relationship evidence.
    """

    if type(family) is not CanonicalProductFamily:
        raise SellableVariantApprovalError(
            "family must be an exact CanonicalProductFamily"
        )
    if type(selected_members) is not tuple or not selected_members:
        raise SellableVariantApprovalError(
            "selected_members must be an explicit non-empty tuple"
        )

    family_positions = {member: index for index, member in enumerate(family.members)}
    if len(family_positions) != len(family.members):
        raise SellableVariantApprovalError("canonical family members must be unique")

    try:
        selected_positions = tuple(family_positions[member] for member in selected_members)
    except (KeyError, TypeError) as exc:
        raise SellableVariantApprovalError(
            "every selected member must belong to the canonical family"
        ) from exc
    if len(set(selected_positions)) != len(selected_positions):
        raise SellableVariantApprovalError("selected members must be unique")

    selected_position_set = set(selected_positions)
    canonical_members = tuple(
        member
        for position, member in enumerate(family.members)
        if position in selected_position_set
    )

    projection = project_sellable_variant_evidence(family)
    if (
        type(projection) is not SellableVariantEvidenceProjection
        or projection.source_family is not family
    ):
        raise SellableVariantApprovalError(
            "TASK-115 projection must preserve the exact canonical source family"
        )

    exact_pairs = _index_direct_exact_evidence(projection, family_positions)

    # Closure is checked before internal completeness so every proper subset of
    # an exact-connected gap fails at the edge boundary without transitive repair.
    for (left, right) in exact_pairs:
        if (left in selected_position_set) != (right in selected_position_set):
            raise SellableVariantApprovalError(
                "selected members must be closed under direct exact edges"
            )

    selected_pair_evidence: list[FamilyMergePairEvidence] = []
    canonical_positions = tuple(sorted(selected_position_set))
    for left_offset, left in enumerate(canonical_positions):
        for right in canonical_positions[left_offset + 1 :]:
            pair = exact_pairs.get((left, right))
            if pair is None:
                raise SellableVariantApprovalError(
                    "every selected pair must have preserved direct exact evidence"
                )
            selected_pair_evidence.append(pair)

    expected_pair_count = len(canonical_members) * (len(canonical_members) - 1) // 2
    if len(selected_pair_evidence) != expected_pair_count:
        raise SellableVariantApprovalError(
            "proposal must retain exactly one direct exact value for every selected pair"
        )

    return _build_sellable_variant_proposal(
        projection=projection,
        members=canonical_members,
        pair_evidence=tuple(selected_pair_evidence),
    )


def _rehydrate_sellable_variant_proposal(
    *,
    projection: SellableVariantEvidenceProjection,
    members: tuple[SourceObservationIdentity, ...],
    pair_evidence: tuple[FamilyMergePairEvidence, ...],
) -> SellableVariantProposal:
    """Rehydrate retained proposal lineage without projecting or discovering it."""

    return _build_sellable_variant_proposal(
        projection=projection,
        members=members,
        pair_evidence=pair_evidence,
    )


def _build_sellable_variant_proposal(
    *,
    projection: SellableVariantEvidenceProjection,
    members: tuple[SourceObservationIdentity, ...],
    pair_evidence: tuple[FamilyMergePairEvidence, ...],
) -> SellableVariantProposal:
    if type(projection) is not SellableVariantEvidenceProjection:
        raise SellableVariantApprovalError(
            "proposal projection must be an exact SellableVariantEvidenceProjection"
        )
    family = projection.source_family
    if type(family) is not CanonicalProductFamily:
        raise SellableVariantApprovalError(
            "proposal projection must retain an exact canonical source family"
        )
    if type(members) is not tuple or not members:
        raise SellableVariantApprovalError(
            "proposal members must be an explicit non-empty tuple"
        )
    if type(pair_evidence) is not tuple:
        raise SellableVariantApprovalError(
            "proposal pair evidence must be an exact tuple"
        )

    family_positions = {member: position for position, member in enumerate(family.members)}
    if len(family_positions) != len(family.members):
        raise SellableVariantApprovalError("canonical family members must be unique")
    try:
        member_positions = tuple(family_positions[member] for member in members)
    except (KeyError, TypeError) as exc:
        raise SellableVariantApprovalError(
            "every proposal member must belong to the canonical family"
        ) from exc
    if len(set(member_positions)) != len(member_positions):
        raise SellableVariantApprovalError("proposal members must be unique")
    if member_positions != tuple(sorted(member_positions)):
        raise SellableVariantApprovalError(
            "proposal members must follow canonical source-family order"
        )
    if any(members[index] is not family.members[position] for index, position in enumerate(member_positions)):
        raise SellableVariantApprovalError(
            "proposal members must reuse source-family observation values"
        )

    exact_pairs = _index_direct_exact_evidence(projection, family_positions)
    selected_positions = set(member_positions)
    for left, right in exact_pairs:
        if (left in selected_positions) != (right in selected_positions):
            raise SellableVariantApprovalError(
                "selected members must be closed under direct exact edges"
            )

    expected_pairs = tuple(
        exact_pairs[(left, right)]
        for offset, left in enumerate(member_positions)
        for right in member_positions[offset + 1 :]
        if (left, right) in exact_pairs
    )
    expected_pair_count = len(members) * (len(members) - 1) // 2
    if len(expected_pairs) != expected_pair_count or len(pair_evidence) != expected_pair_count:
        raise SellableVariantApprovalError(
            "every selected pair must have preserved direct exact evidence"
        )
    if any(actual is not expected for actual, expected in zip(pair_evidence, expected_pairs)):
        raise SellableVariantApprovalError(
            "proposal pair evidence must reuse source-family evidence in canonical order"
        )

    return SellableVariantProposal(
        projection=projection,
        members=members,
        pair_evidence=pair_evidence,
        _lineage=_PROPOSAL_LINEAGE,
    )


def create_sellable_variant_decision_record(
    proposal: SellableVariantProposal,
    *,
    decision: SellableVariantDecision,
    actor: str,
    decided_at: datetime,
) -> SellableVariantDecisionRecord:
    """Record one explicit Human decision without mutation or side effects."""

    return SellableVariantDecisionRecord(
        proposal=proposal,
        decision=decision,
        actor=actor,
        decided_at=decided_at,
    )


def _index_direct_exact_evidence(
    projection: SellableVariantEvidenceProjection,
    family_positions: dict[SourceObservationIdentity, int],
) -> dict[tuple[int, int], FamilyMergePairEvidence]:
    indexed: dict[tuple[int, int], FamilyMergePairEvidence] = {}
    for pair in projection.direct_exact_evidence:
        if (
            type(pair) is not FamilyMergePairEvidence
            or pair.relationship is not ProductRelationship.EXACT_VARIANT_MATCH
        ):
            raise SellableVariantApprovalError(
                "TASK-115 direct exact evidence must contain preserved exact pairs"
            )
        try:
            left = family_positions[pair.left]
            right = family_positions[pair.right]
        except (KeyError, TypeError) as exc:
            raise SellableVariantApprovalError(
                "TASK-115 direct exact endpoints must belong to the source family"
            ) from exc
        if left == right:
            raise SellableVariantApprovalError(
                "TASK-115 direct exact evidence must join distinct members"
            )
        key = (min(left, right), max(left, right))
        if key in indexed:
            raise SellableVariantApprovalError(
                "TASK-115 must preserve at most one direct exact value per pair"
            )
        indexed[key] = pair
    return indexed


def _validate_proposal(proposal: object) -> None:
    if type(proposal) is not SellableVariantProposal:
        raise SellableVariantApprovalError(
            "proposal must be an exact canonical SellableVariantProposal"
        )
    if (
        type(proposal.projection) is not SellableVariantEvidenceProjection
        or proposal.projection.source_family is not proposal.source_family
        or not proposal.members
    ):
        raise SellableVariantApprovalError("proposal lineage is invalid")
    expected_pair_count = len(proposal.members) * (len(proposal.members) - 1) // 2
    if len(proposal.pair_evidence) != expected_pair_count:
        raise SellableVariantApprovalError("proposal is not evidence-complete")


def _validate_actor(actor: object) -> None:
    if not isinstance(actor, str) or not actor.strip():
        raise SellableVariantApprovalError(
            "actor must be an explicit non-empty string"
        )
    if "\x00" in actor or actor.splitlines() != [actor]:
        raise SellableVariantApprovalError(
            "actor must be a NUL-free single-line identifier"
        )


def _validate_decided_at(decided_at: object) -> None:
    if not isinstance(decided_at, datetime):
        raise SellableVariantApprovalError(
            "decided_at must be an explicit datetime"
        )
    try:
        offset = decided_at.utcoffset()
    except (OverflowError, ValueError) as exc:
        raise SellableVariantApprovalError(
            "decided_at must be timezone-aware"
        ) from exc
    if decided_at.tzinfo is None or offset is None:
        raise SellableVariantApprovalError("decided_at must be timezone-aware")


# Concise aliases for callers that name the operation rather than the record.
create_sellable_variant_decision = create_sellable_variant_decision_record
record_sellable_variant_decision = create_sellable_variant_decision_record


__all__ = [
    "SellableVariantApprovalError",
    "SellableVariantDecision",
    "SellableVariantDecisionRecord",
    "SellableVariantProposal",
    "create_sellable_variant_decision",
    "create_sellable_variant_decision_record",
    "create_sellable_variant_proposal",
    "record_sellable_variant_decision",
]
