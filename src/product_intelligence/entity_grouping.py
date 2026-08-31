"""Platform-neutral, immutable provisional product-family grouping.

Partitions observation identities from an existing MultiObservationResolutionGraph
into deterministic, immutable provisional groups based exclusively on existing
positive-family connectivity, preserving TASK-109 conflict visibility without
re-running entity resolution, inferring transitive relationships, approving merges,
assigning canonical identities, or deriving aggregate confidence.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Sequence

from src.product_intelligence.entity_resolution import (
    ProductRelationship,
    SourceObservationIdentity,
)
from src.product_intelligence.entity_resolution_graph import (
    MultiObservationResolutionGraph,
    ProductFamilyConsistencyConflict,
)


class ProvisionalGroupStatus(str, Enum):
    """Status of a provisional product-family group."""
    SINGLETON = "SINGLETON"
    POSITIVE_CONNECTED = "POSITIVE_CONNECTED"
    CONFLICTED = "CONFLICTED"


@dataclass(frozen=True)
class ProvisionalProductFamilyGroup:
    """Immutable provisional product-family group partition."""
    members: tuple[SourceObservationIdentity, ...]
    status: ProvisionalGroupStatus
    conflicts: tuple[ProductFamilyConsistencyConflict, ...]

    @property
    def member_count(self) -> int:
        return len(self.members)

    @property
    def has_conflicts(self) -> bool:
        return len(self.conflicts) > 0


@dataclass(frozen=True)
class ProvisionalGroupingResult:
    """Immutable result of partitioning a resolution graph into provisional groups."""
    groups: tuple[ProvisionalProductFamilyGroup, ...]

    @property
    def group_count(self) -> int:
        return len(self.groups)

    @property
    def observation_count(self) -> int:
        return sum(g.member_count for g in self.groups)

    @property
    def conflicted_group_count(self) -> int:
        return sum(1 for g in self.groups if g.status is ProvisionalGroupStatus.CONFLICTED)


def _identity_canonical_key(identity: SourceObservationIdentity) -> tuple:
    """Deterministic canonical sort key based on exact SourceObservationIdentity fields."""
    return (
        identity.source_pack_id,
        identity.platform,
        identity.source_product_id or "",
        identity.product_url,
        identity.observed_at.isoformat() if identity.observed_at else "",
    )


def _conflict_canonical_key(conflict: ProductFamilyConsistencyConflict) -> tuple:
    """Deterministic canonical sort key for consistency conflicts."""
    contra_left = _identity_canonical_key(conflict.contradictory_pair.left)
    contra_right = _identity_canonical_key(conflict.contradictory_pair.right)
    return (
        min(contra_left, contra_right),
        max(contra_left, contra_right),
        conflict.conflict_type,
        conflict.detail,
    )


def group_resolution_graph(
    graph: MultiObservationResolutionGraph,
) -> ProvisionalGroupingResult:
    """Deterministically partition a MultiObservationResolutionGraph into provisional groups.

    Accepts exactly one existing MultiObservationResolutionGraph and returns an
    immutable ProvisionalGroupingResult. Performs zero entity resolution re-execution.
    """
    if not isinstance(graph, MultiObservationResolutionGraph):
        raise TypeError(
            f"graph must be an instance of MultiObservationResolutionGraph, got {type(graph)}"
        )

    observations = graph.observations
    positive_relationships = {
        ProductRelationship.EXACT_VARIANT_MATCH,
        ProductRelationship.SAME_PRODUCT_FAMILY,
    }

    # Build adjacency map for positive-family connections only
    adj: dict[SourceObservationIdentity, set[SourceObservationIdentity]] = {
        ident: set() for ident in observations
    }

    for res in graph.pairwise_results:
        if res.relationship in positive_relationships:
            if res.left in adj and res.right in adj:
                adj[res.left].add(res.right)
                adj[res.right].add(res.left)

    # Find connected components deterministically
    visited: set[SourceObservationIdentity] = set()
    components: list[list[SourceObservationIdentity]] = []

    # Sort observations by canonical key before traversal to guarantee deterministic order
    sorted_observations = sorted(observations, key=_identity_canonical_key)

    for ident in sorted_observations:
        if ident in visited:
            continue
        component: list[SourceObservationIdentity] = []
        queue = deque([ident])
        visited.add(ident)
        while queue:
            curr = queue.popleft()
            component.append(curr)
            for neighbor in adj.get(curr, ()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        components.append(component)

    # Associate conflicts with components
    groups: list[ProvisionalProductFamilyGroup] = []

    for comp in components:
        comp_set = set(comp)
        canonical_members = tuple(sorted(comp, key=_identity_canonical_key))

        # Relevant conflicts already present on the input graph
        comp_conflicts = [
            c for c in graph.conflicts
            if c.contradictory_pair.left in comp_set or c.contradictory_pair.right in comp_set
        ]
        sorted_conflicts = tuple(sorted(comp_conflicts, key=_conflict_canonical_key))

        if len(canonical_members) == 1:
            status = ProvisionalGroupStatus.SINGLETON
        elif len(sorted_conflicts) > 0:
            status = ProvisionalGroupStatus.CONFLICTED
        else:
            status = ProvisionalGroupStatus.POSITIVE_CONNECTED

        groups.append(
            ProvisionalProductFamilyGroup(
                members=canonical_members,
                status=status,
                conflicts=sorted_conflicts,
            )
        )

    # Deterministically order groups based on their members tuple key
    sorted_groups = sorted(
        groups,
        key=lambda g: tuple(_identity_canonical_key(m) for m in g.members),
    )

    return ProvisionalGroupingResult(groups=tuple(sorted_groups))


# Public domain aliases
group_product_resolution_graph = group_resolution_graph
group_product_graph = group_resolution_graph
group_multi_observations = group_resolution_graph


class ProductFamilyGrouper:
    """Stateless facade for product-family grouping projection."""

    def group(
        self, graph: MultiObservationResolutionGraph
    ) -> ProvisionalGroupingResult:
        return group_resolution_graph(graph)

