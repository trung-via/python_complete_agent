"""Deterministic composition of existing family-review preparation authorities."""

from dataclasses import InitVar as _InitVar, dataclass as _dataclass

from src.product_intelligence.entity_grouping import (
    ProvisionalGroupingResult as _ProvisionalGroupingResult,
    ProvisionalGroupStatus as _ProvisionalGroupStatus,
    ProvisionalProductFamilyGroup as _ProvisionalProductFamilyGroup,
    group_resolution_graph as _group_resolution_graph,
)
from src.product_intelligence.entity_resolution_graph import (
    MultiObservationResolutionGraph as _MultiObservationResolutionGraph,
    resolve_multi_observations as _resolve_multi_observations,
)
from src.product_intelligence.family_merge_approval import (
    FamilyMergeProposal as _FamilyMergeProposal,
    create_family_merge_proposal as _create_family_merge_proposal,
)
from src.product_intelligence.source_evidence_intake import (
    SourceEvidenceInventory as _SourceEvidenceInventory,
)


class FamilyKnowledgeReviewPlanningError(ValueError):
    """Raised when family-review planning input or composition is invalid."""


_PLAN_LINEAGE = object()


@_dataclass(frozen=True, slots=True)
class FamilyKnowledgeReviewPlan:
    """Immutable lineage-preserving result of family-review preparation."""

    inventory: _SourceEvidenceInventory
    graph: _MultiObservationResolutionGraph
    groups: tuple[_ProvisionalProductFamilyGroup, ...]
    proposals: tuple[_FamilyMergeProposal, ...]
    _lineage: _InitVar[object] = None

    def __post_init__(self, _lineage: object) -> None:
        if _lineage is not _PLAN_LINEAGE:
            raise FamilyKnowledgeReviewPlanningError(
                "FamilyKnowledgeReviewPlan must be created by "
                "plan_family_knowledge_review"
            )


def plan_family_knowledge_review(
    inventory: _SourceEvidenceInventory,
) -> FamilyKnowledgeReviewPlan:
    """Compose resolution, grouping, and actionable family proposal creation."""

    if type(inventory) is not _SourceEvidenceInventory:
        raise FamilyKnowledgeReviewPlanningError(
            "inventory must be an exact SourceEvidenceInventory"
        )

    graph = _resolve_multi_observations(inventory.source_packs)
    if type(graph) is not _MultiObservationResolutionGraph:
        raise FamilyKnowledgeReviewPlanningError(
            "resolution returned an invalid graph"
        )

    grouping = _group_resolution_graph(graph)
    if type(grouping) is not _ProvisionalGroupingResult:
        raise FamilyKnowledgeReviewPlanningError(
            "grouping returned an invalid result"
        )
    groups = grouping.groups
    if type(groups) is not tuple or any(
        type(group) is not _ProvisionalProductFamilyGroup for group in groups
    ):
        raise FamilyKnowledgeReviewPlanningError(
            "grouping returned invalid canonical groups"
        )

    proposals: list[_FamilyMergeProposal] = []
    for group in groups:
        if (
            group.status is _ProvisionalGroupStatus.POSITIVE_CONNECTED
            and group.conflicts == ()
        ):
            proposal = _create_family_merge_proposal(graph, group)
            if type(proposal) is not _FamilyMergeProposal:
                raise FamilyKnowledgeReviewPlanningError(
                    "proposal creation returned an invalid proposal"
                )
            if proposal.members is not group.members:
                raise FamilyKnowledgeReviewPlanningError(
                    "proposal does not retain its canonical group members"
                )
            proposals.append(proposal)

    return FamilyKnowledgeReviewPlan(
        inventory=inventory,
        graph=graph,
        groups=groups,
        proposals=tuple(proposals),
        _lineage=_PLAN_LINEAGE,
    )


__all__ = [
    "FamilyKnowledgeReviewPlanningError",
    "FamilyKnowledgeReviewPlan",
    "plan_family_knowledge_review",
]
