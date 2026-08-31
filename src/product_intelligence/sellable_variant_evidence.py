"""Read-only sellable-variant evidence over one canonical product family.

The projection preserves direct pair evidence and uses exact-edge connectivity
only to expose diagnostics.  It does not infer pairwise truth, form variant
groups, allocate identity, aggregate confidence, or perform external work.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from src.product_intelligence.canonical_family import CanonicalProductFamily
from src.product_intelligence.entity_resolution import ProductRelationship
from src.product_intelligence.family_merge_approval import FamilyMergePairEvidence


class SellableVariantEvidenceError(ValueError):
    """Raised when a sellable-variant evidence projection cannot be derived."""


@dataclass(frozen=True)
class SellableVariantExactnessGap:
    """One authoritative non-exact pair and a diagnostic all-exact path."""

    direct_evidence: FamilyMergePairEvidence
    witness_path: tuple[FamilyMergePairEvidence, ...]

    @property
    def witness_edge_count(self) -> int:
        return len(self.witness_path)


@dataclass(frozen=True)
class SellableVariantEvidenceProjection:
    """Bounded evidence view derived from one admitted canonical family."""

    source_family: CanonicalProductFamily
    direct_exact_evidence: tuple[FamilyMergePairEvidence, ...]
    exactness_gaps: tuple[SellableVariantExactnessGap, ...]

    @property
    def direct_exact_count(self) -> int:
        return len(self.direct_exact_evidence)

    @property
    def exactness_gap_count(self) -> int:
        return len(self.exactness_gaps)


def project_sellable_variant_evidence(
    family: CanonicalProductFamily,
) -> SellableVariantEvidenceProjection:
    """Project preserved direct exact evidence and exact-connectivity gaps.

    ``family`` is the sole semantic input.  The operation reads only pair
    evidence already retained by its approval provenance and preserves those
    exact objects in the result.
    """

    if type(family) is not CanonicalProductFamily:
        raise SellableVariantEvidenceError(
            "family must be an exact CanonicalProductFamily"
        )

    members = family.members
    member_positions = {member: position for position, member in enumerate(members)}
    if len(member_positions) != len(members):
        raise SellableVariantEvidenceError(
            "canonical family members must be unique"
        )

    pair_by_position = _index_preserved_pairs(
        family.approval.proposal.pair_evidence,
        member_positions,
    )
    expected_pair_count = len(members) * (len(members) - 1) // 2
    if len(pair_by_position) != expected_pair_count:
        raise SellableVariantEvidenceError(
            "canonical family must retain exactly one evidence value for every pair"
        )

    ordered_pairs = tuple(
        pair_by_position[(left, right)]
        for left in range(len(members))
        for right in range(left + 1, len(members))
    )
    direct_exact_evidence = tuple(
        pair
        for pair in ordered_pairs
        if pair.relationship is ProductRelationship.EXACT_VARIANT_MATCH
    )

    exact_adjacency: dict[
        int, list[tuple[int, FamilyMergePairEvidence]]
    ] = {position: [] for position in range(len(members))}
    for (left, right), pair in pair_by_position.items():
        if pair.relationship is ProductRelationship.EXACT_VARIANT_MATCH:
            exact_adjacency[left].append((right, pair))
            exact_adjacency[right].append((left, pair))
    for neighbors in exact_adjacency.values():
        neighbors.sort(key=lambda neighbor: neighbor[0])

    gaps: list[SellableVariantExactnessGap] = []
    for left in range(len(members)):
        for right in range(left + 1, len(members)):
            direct_evidence = pair_by_position[(left, right)]
            if (
                direct_evidence.relationship
                is ProductRelationship.EXACT_VARIANT_MATCH
            ):
                continue
            witness_path = _canonical_shortest_exact_path(
                left,
                right,
                exact_adjacency,
            )
            if witness_path is not None:
                gaps.append(
                    SellableVariantExactnessGap(
                        direct_evidence=direct_evidence,
                        witness_path=witness_path,
                    )
                )

    return SellableVariantEvidenceProjection(
        source_family=family,
        direct_exact_evidence=direct_exact_evidence,
        exactness_gaps=tuple(gaps),
    )


def _index_preserved_pairs(
    pair_evidence: tuple[FamilyMergePairEvidence, ...],
    member_positions: dict[object, int],
) -> dict[tuple[int, int], FamilyMergePairEvidence]:
    indexed: dict[tuple[int, int], FamilyMergePairEvidence] = {}
    for pair in pair_evidence:
        if type(pair) is not FamilyMergePairEvidence:
            raise SellableVariantEvidenceError(
                "family pair evidence must contain exact FamilyMergePairEvidence values"
            )
        try:
            left = member_positions[pair.left]
            right = member_positions[pair.right]
        except (KeyError, TypeError) as exc:
            raise SellableVariantEvidenceError(
                "family pair evidence endpoints must be canonical family members"
            ) from exc
        if left == right:
            raise SellableVariantEvidenceError(
                "family pair evidence must reference two distinct members"
            )
        key = (min(left, right), max(left, right))
        if key in indexed:
            raise SellableVariantEvidenceError(
                "canonical family must retain exactly one evidence value for every pair"
            )
        indexed[key] = pair
    return indexed


def _canonical_shortest_exact_path(
    start: int,
    end: int,
    adjacency: dict[int, list[tuple[int, FamilyMergePairEvidence]]],
) -> tuple[FamilyMergePairEvidence, ...] | None:
    """Return shortest exact path, breaking ties by member-position sequence."""

    queue = deque([(start, ())])
    visited = {start}
    while queue:
        current, path = queue.popleft()
        for neighbor, pair in adjacency[current]:
            if neighbor in visited:
                continue
            next_path = path + (pair,)
            if neighbor == end:
                return next_path
            visited.add(neighbor)
            queue.append((neighbor, next_path))
    return None


# Concise compatibility names for callers that name either the operation or gap.
ExactnessGap = SellableVariantExactnessGap
create_sellable_variant_evidence_projection = project_sellable_variant_evidence


__all__ = [
    "ExactnessGap",
    "SellableVariantEvidenceError",
    "SellableVariantEvidenceProjection",
    "SellableVariantExactnessGap",
    "create_sellable_variant_evidence_projection",
    "project_sellable_variant_evidence",
]
