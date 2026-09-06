"""Human review and durable admission composition for sellable variants.

TASK-141 preserves the exact TASK-116 proposal and decision lineage while
delegating canonical admission to TASK-117 and SQLite registration to TASK-120.
It owns no selection, evidence, identity, catalog, codec, or storage semantics.
"""

from dataclasses import InitVar as _InitVar, dataclass as _dataclass
from datetime import datetime as _datetime
from os import PathLike as _PathLike

from src.product_intelligence.canonical_catalog import (
    CatalogRegistrationResult as _CatalogRegistrationResult,
)
from src.product_intelligence.canonical_catalog_sqlite import (
    register_sqlite_canonical_variant as _register_sqlite_canonical_variant,
)
from src.product_intelligence.canonical_family import (
    CanonicalProductFamily as _CanonicalProductFamily,
)
from src.product_intelligence.canonical_variant import (
    CanonicalSellableVariant as _CanonicalSellableVariant,
    create_canonical_sellable_variant as _create_canonical_sellable_variant,
)
from src.product_intelligence.entity_resolution import (
    SourceObservationIdentity as _SourceObservationIdentity,
)
from src.product_intelligence.sellable_variant_approval import (
    SellableVariantDecision as _SellableVariantDecision,
    SellableVariantDecisionRecord as _SellableVariantDecisionRecord,
    SellableVariantProposal as _SellableVariantProposal,
    create_sellable_variant_decision_record as _create_sellable_variant_decision_record,
    create_sellable_variant_proposal as _create_sellable_variant_proposal,
)


class SellableVariantWorkflowError(ValueError):
    """Raised when exact TASK-141 review lineage is not preserved."""


_REVIEW_FACTORY = object()
_DURABLE_ADMISSION_FACTORY = object()


@_dataclass(frozen=True, slots=True)
class SellableVariantReview:
    """One immutable wrapper around the exact reviewed TASK-116 proposal."""

    proposal: _SellableVariantProposal
    _lineage: _InitVar[object] = None

    def __post_init__(self, _lineage: object) -> None:
        if _lineage is not _REVIEW_FACTORY:
            raise SellableVariantWorkflowError(
                "SellableVariantReview must be created by "
                "prepare_sellable_variant_review"
            )


@_dataclass(frozen=True, slots=True)
class DurableSellableVariantAdmissionResult:
    """Exact values returned by the delegated durable admission path."""

    decision_record: _SellableVariantDecisionRecord
    variant: _CanonicalSellableVariant
    registration: _CatalogRegistrationResult
    _lineage: _InitVar[object] = None

    def __post_init__(self, _lineage: object) -> None:
        if _lineage is not _DURABLE_ADMISSION_FACTORY:
            raise SellableVariantWorkflowError(
                "DurableSellableVariantAdmissionResult must be created by "
                "durably_admit_reviewed_sellable_variant"
            )


def prepare_sellable_variant_review(
    family: _CanonicalProductFamily,
    selected_members: tuple[_SourceObservationIdentity, ...],
) -> SellableVariantReview:
    """Prepare one review from the caller's exact family and selection."""

    proposal = _create_sellable_variant_proposal(family, selected_members)
    if (
        type(proposal) is not _SellableVariantProposal
        or proposal.source_family is not family
    ):
        raise SellableVariantWorkflowError(
            "TASK-116 proposal must retain the exact reviewed source family"
        )
    return SellableVariantReview(proposal=proposal, _lineage=_REVIEW_FACTORY)


def record_reviewed_sellable_variant_decision(
    review: SellableVariantReview,
    *,
    decision: _SellableVariantDecision,
    actor: str,
    decided_at: _datetime,
) -> _SellableVariantDecisionRecord:
    """Record one explicit Human decision over the exact reviewed proposal."""

    if type(review) is not SellableVariantReview:
        raise SellableVariantWorkflowError(
            "review must be an exact SellableVariantReview"
        )
    return _create_sellable_variant_decision_record(
        review.proposal,
        decision=decision,
        actor=actor,
        decided_at=decided_at,
    )


def durably_admit_reviewed_sellable_variant(
    review: SellableVariantReview,
    decision_record: _SellableVariantDecisionRecord,
    *,
    variant_id: str,
    database_path: _PathLike[str] | str,
) -> DurableSellableVariantAdmissionResult:
    """Admit and durably register one exact reviewed TASK-116 decision."""

    if type(review) is not SellableVariantReview:
        raise SellableVariantWorkflowError(
            "review must be an exact SellableVariantReview"
        )
    if type(decision_record) is not _SellableVariantDecisionRecord:
        raise SellableVariantWorkflowError(
            "decision_record must be an exact SellableVariantDecisionRecord"
        )
    if decision_record.proposal is not review.proposal:
        raise SellableVariantWorkflowError(
            "decision_record must retain the exact reviewed proposal"
        )

    variant = _create_canonical_sellable_variant(
        decision_record,
        variant_id=variant_id,
    )
    if type(variant) is not _CanonicalSellableVariant:
        raise SellableVariantWorkflowError(
            "TASK-117 admission returned an invalid canonical variant"
        )

    registration = _register_sqlite_canonical_variant(database_path, variant)
    if type(registration) is not _CatalogRegistrationResult:
        raise SellableVariantWorkflowError(
            "TASK-120 registration returned an invalid result"
        )

    return DurableSellableVariantAdmissionResult(
        decision_record=decision_record,
        variant=variant,
        registration=registration,
        _lineage=_DURABLE_ADMISSION_FACTORY,
    )


__all__ = [
    "SellableVariantWorkflowError",
    "SellableVariantReview",
    "DurableSellableVariantAdmissionResult",
    "prepare_sellable_variant_review",
    "record_reviewed_sellable_variant_decision",
    "durably_admit_reviewed_sellable_variant",
]
