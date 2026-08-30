"""Platform-neutral, bounded multi-observation resolution graph.

Evaluates collections of ProductSourcePack observations through the existing
pairwise entity resolution authority, preserves all pairwise decisions, and
reports auditable product-family consistency conflicts without clustering,
merging, canonical product ID assignment, or catalog persistence.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Collection, Iterable, Optional, Sequence

from src.product_intelligence.entity_resolution import (
    EntityResolutionResult,
    ProductRelationship,
    SourceObservationIdentity,
    resolve_product_entities,
)
from src.product_source.models import ProductSourcePack

MIN_OBSERVATIONS = 2
MAX_OBSERVATIONS = 100


class MultiObservationResolutionError(ValueError):
    """Raised when multi-observation inputs violate cardinality or identity invariants."""


@dataclass(frozen=True)
class PairwiseConflictEvidence:
    """Compact auditable pair contributing to a consistency conflict."""
    left: SourceObservationIdentity
    right: SourceObservationIdentity
    relationship: ProductRelationship
    confidence: float
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ProductFamilyConsistencyConflict:
    """Auditable product-family consistency conflict across observations.

    Occurs when observations connected through positive product-family relationships
    (EXACT_VARIANT_MATCH or SAME_PRODUCT_FAMILY) also contain a direct DIFFERENT_PRODUCT
    relationship within that positively connected component.
    """
    conflict_type: str
    contradictory_pair: PairwiseConflictEvidence
    positive_path: tuple[PairwiseConflictEvidence, ...]
    affected_identities: tuple[SourceObservationIdentity, ...]
    detail: str


@dataclass(frozen=True)
class MultiObservationResolutionGraph:
    """Immutable multi-observation resolution result."""
    observations: tuple[SourceObservationIdentity, ...]
    pairwise_results: tuple[EntityResolutionResult, ...]
    conflicts: tuple[ProductFamilyConsistencyConflict, ...]

    @property
    def has_conflicts(self) -> bool:
        return len(self.conflicts) > 0


def _validate_observations(observations: Sequence[ProductSourcePack]) -> tuple[SourceObservationIdentity, ...]:
    if not isinstance(observations, (list, tuple)):
        try:
            observations = list(observations)
        except Exception:
            raise MultiObservationResolutionError("observations must be a sequence of ProductSourcePack")

    n = len(observations)
    if n < MIN_OBSERVATIONS or n > MAX_OBSERVATIONS:
        raise MultiObservationResolutionError(
            f"Observation count must be between {MIN_OBSERVATIONS} and {MAX_OBSERVATIONS}, got {n}"
        )

    identities: list[SourceObservationIdentity] = []
    seen: set[SourceObservationIdentity] = set()

    for idx, pack in enumerate(observations):
        if not isinstance(pack, ProductSourcePack):
            raise MultiObservationResolutionError(
                f"Observation at index {idx} is not a ProductSourcePack: {type(pack)}"
            )
        identity = SourceObservationIdentity.from_pack(pack)
        if identity in seen:
            raise MultiObservationResolutionError(
                f"Duplicate exact SourceObservationIdentity detected: {identity}"
            )
        seen.add(identity)
        identities.append(identity)

    return tuple(identities)


def _to_conflict_evidence(res: EntityResolutionResult) -> PairwiseConflictEvidence:
    return PairwiseConflictEvidence(
        left=res.left,
        right=res.right,
        relationship=res.relationship,
        confidence=res.confidence,
        reasons=res.reasons,
    )


def _find_positive_path(
    start: SourceObservationIdentity,
    target: SourceObservationIdentity,
    adj: dict[SourceObservationIdentity, list[tuple[SourceObservationIdentity, EntityResolutionResult]]],
) -> Optional[list[EntityResolutionResult]]:
    """BFS to find shortest path of positive pairwise relationships between start and target."""
    queue: deque[tuple[SourceObservationIdentity, list[EntityResolutionResult]]] = deque([(start, [])])
    visited: set[SourceObservationIdentity] = {start}

    while queue:
        current, path = queue.popleft()
        if current == target and path:
            return path
        for neighbor, res in adj.get(current, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [res]))
    return None


def _find_conflicts(
    identities: tuple[SourceObservationIdentity, ...],
    pairwise_results: tuple[EntityResolutionResult, ...],
) -> tuple[ProductFamilyConsistencyConflict, ...]:
    positive_relationships = {ProductRelationship.EXACT_VARIANT_MATCH, ProductRelationship.SAME_PRODUCT_FAMILY}

    adj: dict[SourceObservationIdentity, list[tuple[SourceObservationIdentity, EntityResolutionResult]]] = {
        ident: [] for ident in identities
    }

    pair_map: dict[frozenset[SourceObservationIdentity], EntityResolutionResult] = {}

    for res in pairwise_results:
        key = frozenset([res.left, res.right])
        pair_map[key] = res
        if res.relationship in positive_relationships:
            adj[res.left].append((res.right, res))
            adj[res.right].append((res.left, res))

    conflicts: list[ProductFamilyConsistencyConflict] = []

    for res in pairwise_results:
        if res.relationship is ProductRelationship.DIFFERENT_PRODUCT:
            u, v = res.left, res.right
            path = _find_positive_path(u, v, adj)
            if path is not None:
                positive_path_evidence = tuple(_to_conflict_evidence(edge) for edge in path)
                nodes_in_path: list[SourceObservationIdentity] = [u]
                curr = u
                for edge in path:
                    nxt = edge.right if edge.left == curr else edge.left
                    nodes_in_path.append(nxt)
                    curr = nxt

                conflict = ProductFamilyConsistencyConflict(
                    conflict_type="POSITIVE_FAMILY_CHAIN_CONTRADICTS_DIFFERENT_PRODUCT",
                    contradictory_pair=_to_conflict_evidence(res),
                    positive_path=positive_path_evidence,
                    affected_identities=tuple(nodes_in_path),
                    detail=(
                        f"Observations {u.source_pack_id} and {v.source_pack_id} have a direct DIFFERENT_PRODUCT "
                        f"relationship but are connected by a {len(path)}-hop positive product-family chain."
                    ),
                )
                conflicts.append(conflict)

    return tuple(conflicts)


def resolve_multi_observations(
    observations: Sequence[ProductSourcePack],
) -> MultiObservationResolutionGraph:
    """Evaluate a bounded collection of observations and return an immutable resolution graph."""
    identities = _validate_observations(observations)
    n = len(observations)

    pairwise_results: list[EntityResolutionResult] = []
    for i in range(n):
        for j in range(i + 1, n):
            result = resolve_product_entities(observations[i], observations[j])
            pairwise_results.append(result)

    conflicts = _find_conflicts(identities, tuple(pairwise_results))

    return MultiObservationResolutionGraph(
        observations=identities,
        pairwise_results=tuple(pairwise_results),
        conflicts=conflicts,
    )


# Domain-specific aliases
resolve_product_observation_graph = resolve_multi_observations
resolve_product_graph = resolve_multi_observations
MultiObservationGraph = MultiObservationResolutionGraph
ProductObservationGraph = MultiObservationResolutionGraph
ProductObservationConflict = ProductFamilyConsistencyConflict


class MultiObservationEntityResolver:
    """Stateless facade for multi-observation resolution graph evaluation."""

    def resolve(self, observations: Sequence[ProductSourcePack]) -> MultiObservationResolutionGraph:
        return resolve_multi_observations(observations)