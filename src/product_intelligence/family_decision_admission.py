"""Planned Human family decision and durable admission composition boundary."""

from dataclasses import InitVar as _InitVar, dataclass as _dataclass
from datetime import datetime as _datetime
from os import PathLike as _PathLike

from src.product_intelligence.canonical_catalog import (
    CatalogRegistrationResult as _CatalogRegistrationResult,
)
from src.product_intelligence.canonical_catalog_sqlite import (
    register_sqlite_canonical_family as _register_sqlite_canonical_family,
)
from src.product_intelligence.canonical_family import (
    CanonicalProductFamily as _CanonicalProductFamily,
    create_canonical_family as _create_canonical_family,
)
from src.product_intelligence.family_merge_approval import (
    FamilyMergeDecision as _FamilyMergeDecision,
    FamilyMergeDecisionRecord as _FamilyMergeDecisionRecord,
    FamilyMergeProposal as _FamilyMergeProposal,
    create_family_merge_decision_record as _create_family_merge_decision_record,
)
from src.product_intelligence.family_review_planning import (
    FamilyKnowledgeReviewPlan as _FamilyKnowledgeReviewPlan,
)


class FamilyDecisionAdmissionError(ValueError):
    """Raised when a decision or admission is outside its exact review plan."""


_DURABLE_ADMISSION = object()


@_dataclass(frozen=True, slots=True)
class DurableFamilyAdmissionResult:
    """Immutable result of one canonical family admission and registration."""

    decision_record: _FamilyMergeDecisionRecord
    family: _CanonicalProductFamily
    registration: _CatalogRegistrationResult
    _lineage: _InitVar[object] = None

    def __post_init__(self, _lineage: object) -> None:
        if _lineage is not _DURABLE_ADMISSION:
            raise FamilyDecisionAdmissionError(
                "DurableFamilyAdmissionResult must be created by "
                "durably_admit_planned_family"
            )


def record_planned_family_decision(
    plan: _FamilyKnowledgeReviewPlan,
    proposal: _FamilyMergeProposal,
    *,
    decision: _FamilyMergeDecision,
    actor: str,
    decided_at: _datetime,
) -> _FamilyMergeDecisionRecord:
    """Record one explicit Human decision for an exact proposal in ``plan``."""

    _require_exact_planned_proposal(plan, proposal)
    return _create_family_merge_decision_record(
        proposal,
        decision=decision,
        actor=actor,
        decided_at=decided_at,
    )


def durably_admit_planned_family(
    plan: _FamilyKnowledgeReviewPlan,
    decision_record: _FamilyMergeDecisionRecord,
    *,
    family_id: str,
    database_path: _PathLike[str] | str,
) -> DurableFamilyAdmissionResult:
    """Admit and durably register one exact planned Human family decision."""

    if type(decision_record) is not _FamilyMergeDecisionRecord:
        raise FamilyDecisionAdmissionError(
            "decision_record must be an exact FamilyMergeDecisionRecord"
        )
    _require_exact_planned_proposal(plan, decision_record.proposal)

    family = _create_canonical_family(decision_record, family_id=family_id)
    if type(family) is not _CanonicalProductFamily:
        raise FamilyDecisionAdmissionError(
            "family admission returned an invalid canonical family"
        )

    registration = _register_sqlite_canonical_family(database_path, family)
    if type(registration) is not _CatalogRegistrationResult:
        raise FamilyDecisionAdmissionError(
            "durable registration returned an invalid result"
        )

    return DurableFamilyAdmissionResult(
        decision_record=decision_record,
        family=family,
        registration=registration,
        _lineage=_DURABLE_ADMISSION,
    )


def _require_exact_planned_proposal(
    plan: object,
    proposal: object,
) -> None:
    if type(plan) is not _FamilyKnowledgeReviewPlan:
        raise FamilyDecisionAdmissionError(
            "plan must be an exact FamilyKnowledgeReviewPlan"
        )
    if type(proposal) is not _FamilyMergeProposal:
        raise FamilyDecisionAdmissionError(
            "proposal must be an exact FamilyMergeProposal"
        )
    if type(plan.proposals) is not tuple or any(
        type(candidate) is not _FamilyMergeProposal for candidate in plan.proposals
    ):
        raise FamilyDecisionAdmissionError(
            "plan must retain exact FamilyMergeProposal objects"
        )
    if sum(candidate is proposal for candidate in plan.proposals) != 1:
        raise FamilyDecisionAdmissionError(
            "proposal must be retained by exact object identity exactly once in plan"
        )


__all__ = [
    "FamilyDecisionAdmissionError",
    "DurableFamilyAdmissionResult",
    "record_planned_family_decision",
    "durably_admit_planned_family",
]
