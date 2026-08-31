"""Canonical sellable-variant admission from exact Human approval lineage.

This module binds one caller-supplied opaque variant identity to one existing
TASK-116 APPROVE record.  It derives every family and member view from that
exact record and performs no projection, proposal construction, identity
generation, aggregation, persistence, or external operation.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass

from src.product_intelligence.canonical_family import CanonicalProductFamily
from src.product_intelligence.entity_resolution import SourceObservationIdentity
from src.product_intelligence.sellable_variant_approval import (
    SellableVariantDecision,
    SellableVariantDecisionRecord,
    SellableVariantProposal,
)


class CanonicalVariantAdmissionError(ValueError):
    """Raised when canonical sellable-variant admission is not authorized."""


_CANONICAL_VARIANT_ADMISSION = object()


@dataclass(frozen=True)
class CanonicalSellableVariant:
    """One immutable variant identity and its exact Human-approved lineage."""

    variant_id: str
    approval: SellableVariantDecisionRecord
    _admission: InitVar[object] = None

    def __post_init__(self, _admission: object) -> None:
        if _admission is not _CANONICAL_VARIANT_ADMISSION:
            raise CanonicalVariantAdmissionError(
                "CanonicalSellableVariant must be created by explicit approved admission"
            )

    @property
    def proposal(self) -> SellableVariantProposal:
        """Return the exact TASK-116 proposal retained by the approval."""

        return self.approval.proposal

    @property
    def source_family(self) -> CanonicalProductFamily:
        """Return the exact source family reached through the approved proposal."""

        return self.approval.proposal.source_family

    @property
    def family_id(self) -> str:
        """Return identity derived only from the exact source family."""

        return self.source_family.family_id

    @property
    def members(self) -> tuple[SourceObservationIdentity, ...]:
        """Return the exact approved TASK-116 member tuple in canonical order."""

        return self.approval.proposal.members

    @property
    def member_count(self) -> int:
        return len(self.members)


def create_canonical_sellable_variant(
    decision_record: SellableVariantDecisionRecord,
    *,
    variant_id: str,
) -> CanonicalSellableVariant:
    """Admit one exact approved proposal under an explicit opaque identity."""

    if type(decision_record) is not SellableVariantDecisionRecord:
        raise CanonicalVariantAdmissionError(
            "decision_record must be an exact SellableVariantDecisionRecord"
        )
    if decision_record.decision is not SellableVariantDecision.APPROVE:
        raise CanonicalVariantAdmissionError(
            "decision_record must contain explicit Human APPROVE"
        )
    _validate_variant_id(variant_id)

    return CanonicalSellableVariant(
        variant_id=variant_id,
        approval=decision_record,
        _admission=_CANONICAL_VARIANT_ADMISSION,
    )


def _validate_variant_id(variant_id: object) -> None:
    if not isinstance(variant_id, str):
        raise CanonicalVariantAdmissionError(
            "variant_id must be an explicit non-empty string"
        )
    if not variant_id or variant_id != variant_id.strip():
        raise CanonicalVariantAdmissionError(
            "variant_id must be non-empty with no leading or trailing whitespace"
        )
    if "\x00" in variant_id or variant_id.splitlines() != [variant_id]:
        raise CanonicalVariantAdmissionError(
            "variant_id must be a NUL-free single-line string"
        )


__all__ = [
    "CanonicalSellableVariant",
    "CanonicalVariantAdmissionError",
    "create_canonical_sellable_variant",
]
