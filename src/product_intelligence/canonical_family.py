"""Canonical product-family admission from explicit Human approval.

This module binds one caller-supplied opaque family identity to the exact member
tuple in one existing approved TASK-112 decision record.  It performs no
resolution, grouping, proposal construction, identity generation, aggregation,
persistence, or external operation.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass

from src.product_intelligence.entity_resolution import SourceObservationIdentity
from src.product_intelligence.family_merge_approval import (
    FamilyMergeDecision,
    FamilyMergeDecisionRecord,
)


class CanonicalFamilyAdmissionError(ValueError):
    """Raised when canonical product-family admission is not authorized."""


_CANONICAL_FAMILY_ADMISSION = object()


@dataclass(frozen=True)
class CanonicalProductFamily:
    """One immutable family identity and its exact Human-approved lineage."""

    family_id: str
    members: tuple[SourceObservationIdentity, ...]
    approval: FamilyMergeDecisionRecord
    _admission: InitVar[object] = None

    def __post_init__(self, _admission: object) -> None:
        if _admission is not _CANONICAL_FAMILY_ADMISSION:
            raise CanonicalFamilyAdmissionError(
                "CanonicalProductFamily must be created by explicit approved admission"
            )

    @property
    def member_count(self) -> int:
        return len(self.members)


def create_canonical_family(
    decision_record: FamilyMergeDecisionRecord,
    *,
    family_id: str,
) -> CanonicalProductFamily:
    """Admit the exact approved member tuple under an explicit opaque identity."""

    if type(decision_record) is not FamilyMergeDecisionRecord:
        raise CanonicalFamilyAdmissionError(
            "decision_record must be an exact FamilyMergeDecisionRecord"
        )
    if decision_record.decision is not FamilyMergeDecision.APPROVE:
        raise CanonicalFamilyAdmissionError(
            "decision_record must contain explicit Human APPROVE"
        )
    _validate_family_id(family_id)

    return CanonicalProductFamily(
        family_id=family_id,
        members=decision_record.proposal.members,
        approval=decision_record,
        _admission=_CANONICAL_FAMILY_ADMISSION,
    )


def _validate_family_id(family_id: object) -> None:
    if not isinstance(family_id, str):
        raise CanonicalFamilyAdmissionError(
            "family_id must be an explicit non-empty string"
        )
    if not family_id or family_id != family_id.strip():
        raise CanonicalFamilyAdmissionError(
            "family_id must be non-empty with no leading or trailing whitespace"
        )
    if "\x00" in family_id or family_id.splitlines() != [family_id]:
        raise CanonicalFamilyAdmissionError(
            "family_id must be a NUL-free single-line string"
        )


__all__ = [
    "CanonicalFamilyAdmissionError",
    "CanonicalProductFamily",
    "create_canonical_family",
]
