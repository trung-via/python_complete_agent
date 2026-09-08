"""Human-governed descriptive truth derived from exact canonical evidence.

TASK-171 reconciles only the five descriptive values already retained by one
TASK-121 ``CanonicalVariantProfile``.  It is a pure derivative projection: all
source evidence remains intact, and genuine conflicts have no winner unless a
caller supplies an explicit valid Human decision.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from src.product_intelligence.canonical_profile import (
    CanonicalProfileObservation,
    CanonicalVariantProfile,
)
from src.product_intelligence.entity_resolution import SourceObservationIdentity


class CanonicalTruthError(ValueError):
    """Raised when descriptive reconciliation input is incoherent."""


class CanonicalTruthField(Enum):
    """The complete ordered TASK-171 descriptive-field boundary."""

    TITLE = "TITLE"
    SHOP_NAME = "SHOP_NAME"
    BRAND = "BRAND"
    MODEL_SKU = "MODEL_SKU"
    DESCRIPTION_TEXT = "DESCRIPTION_TEXT"


class CanonicalTruthDecisionAction(Enum):
    """The complete set of explicit Human conflict actions."""

    SELECT_SOURCE = "SELECT_SOURCE"
    LEAVE_UNRESOLVED = "LEAVE_UNRESOLVED"


@dataclass(frozen=True)
class CanonicalTruthDecision:
    """One caller-supplied Human decision for a descriptive conflict."""

    field: CanonicalTruthField
    action: CanonicalTruthDecisionAction
    actor: str
    decided_at: datetime
    selected_member: SourceObservationIdentity | None


class CanonicalTruthResolutionStatus(Enum):
    """The complete set of deterministic descriptive resolution states."""

    NO_EVIDENCE = "NO_EVIDENCE"
    UNCONTESTED = "UNCONTESTED"
    HUMAN_SELECTED = "HUMAN_SELECTED"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True)
class CanonicalTruthEvidenceOption:
    """One exact value and every canonical member supporting it."""

    value: str
    supporting_members: tuple[SourceObservationIdentity, ...]


@dataclass(frozen=True)
class CanonicalTruthFieldResolution:
    """The derivative resolution of one ordered descriptive field."""

    field: CanonicalTruthField
    status: CanonicalTruthResolutionStatus
    resolved_value: str | None
    supporting_members: tuple[SourceObservationIdentity, ...]
    options: tuple[CanonicalTruthEvidenceOption, ...]
    decision: CanonicalTruthDecision | None


@dataclass(frozen=True)
class CanonicalVariantTruth:
    """Immutable descriptive truth projection for one canonical variant."""

    variant_id: str
    family_id: str
    members: tuple[SourceObservationIdentity, ...]
    field_resolutions: tuple[CanonicalTruthFieldResolution, ...]


_FIELD_ATTRIBUTES = {
    CanonicalTruthField.TITLE: "title",
    CanonicalTruthField.SHOP_NAME: "shop_name",
    CanonicalTruthField.BRAND: "brand",
    CanonicalTruthField.MODEL_SKU: "model_sku",
    CanonicalTruthField.DESCRIPTION_TEXT: "description_text",
}


def reconcile_canonical_variant_truth(
    profile: CanonicalVariantProfile,
    *,
    decisions: Iterable[CanonicalTruthDecision] = (),
) -> CanonicalVariantTruth:
    """Resolve exact descriptive evidence without replacing or preferring it."""

    if type(profile) is not CanonicalVariantProfile:
        raise CanonicalTruthError("profile must be an exact CanonicalVariantProfile")

    options_by_field = {
        field: _evidence_options(profile, field) for field in CanonicalTruthField
    }
    decision_by_field = _validated_decisions(decisions, options_by_field)

    resolutions = tuple(
        _resolve_field(field, options_by_field[field], decision_by_field.get(field))
        for field in CanonicalTruthField
    )
    return CanonicalVariantTruth(
        variant_id=profile.variant_id,
        family_id=profile.family_id,
        members=profile.members,
        field_resolutions=resolutions,
    )


def _evidence_options(
    profile: CanonicalVariantProfile,
    field: CanonicalTruthField,
) -> tuple[CanonicalTruthEvidenceOption, ...]:
    grouped: list[tuple[str, list[SourceObservationIdentity]]] = []
    attribute = _FIELD_ATTRIBUTES[field]

    for observation in profile.observations:
        if type(observation) is not CanonicalProfileObservation:
            raise CanonicalTruthError(
                "profile observations must be exact CanonicalProfileObservation values"
            )
        member = _canonical_member(profile, observation.member)
        value = getattr(observation, attribute)
        if value is None:
            continue
        if type(value) is not str:
            raise CanonicalTruthError(
                "descriptive evidence values must be exact strings or None"
            )

        existing = next((item for item in grouped if item[0] == value), None)
        if existing is None:
            grouped.append((value, [member]))
        else:
            existing[1].append(member)

    return tuple(
        CanonicalTruthEvidenceOption(value=value, supporting_members=tuple(members))
        for value, members in grouped
    )


def _canonical_member(
    profile: CanonicalVariantProfile,
    observed_member: SourceObservationIdentity,
) -> SourceObservationIdentity:
    if type(observed_member) is not SourceObservationIdentity:
        raise CanonicalTruthError(
            "profile observations must retain exact SourceObservationIdentity members"
        )
    matches = tuple(member for member in profile.members if member == observed_member)
    if len(matches) != 1 or type(matches[0]) is not SourceObservationIdentity:
        raise CanonicalTruthError(
            "each profile observation must identify exactly one canonical member"
        )
    return matches[0]


def _validated_decisions(
    decisions: Iterable[CanonicalTruthDecision],
    options_by_field: dict[
        CanonicalTruthField, tuple[CanonicalTruthEvidenceOption, ...]
    ],
) -> dict[CanonicalTruthField, CanonicalTruthDecision]:
    try:
        supplied = tuple(decisions)
    except TypeError as exc:
        raise CanonicalTruthError(
            "decisions must be an iterable of exact CanonicalTruthDecision values"
        ) from exc

    result: dict[CanonicalTruthField, CanonicalTruthDecision] = {}
    for decision in supplied:
        _validate_decision_shape(decision)
        if decision.field in result:
            raise CanonicalTruthError("at most one decision may target each field")

        options = options_by_field[decision.field]
        if len(options) <= 1:
            raise CanonicalTruthError(
                "Human decisions may target genuinely conflicting fields only"
            )
        _validate_conflict_action(decision, options)
        result[decision.field] = decision
    return result


def _validate_decision_shape(decision: CanonicalTruthDecision) -> None:
    if type(decision) is not CanonicalTruthDecision:
        raise CanonicalTruthError(
            "decisions must contain exact CanonicalTruthDecision values only"
        )
    if type(decision.field) is not CanonicalTruthField:
        raise CanonicalTruthError("decision field must be an exact CanonicalTruthField")
    if type(decision.action) is not CanonicalTruthDecisionAction:
        raise CanonicalTruthError(
            "decision action must be an exact CanonicalTruthDecisionAction"
        )
    if type(decision.actor) is not str or not decision.actor.strip():
        raise CanonicalTruthError("decision actor must be a nonblank exact string")
    if type(decision.decided_at) is not datetime:
        raise CanonicalTruthError("decision decided_at must be an exact datetime")
    try:
        aware = (
            decision.decided_at.tzinfo is not None
            and decision.decided_at.utcoffset() is not None
        )
    except (OverflowError, TypeError, ValueError) as exc:
        raise CanonicalTruthError(
            "decision decided_at must be timezone-aware"
        ) from exc
    if not aware:
        raise CanonicalTruthError("decision decided_at must be timezone-aware")
    if (
        decision.selected_member is not None
        and type(decision.selected_member) is not SourceObservationIdentity
    ):
        raise CanonicalTruthError(
            "decision selected_member must be an exact SourceObservationIdentity or None"
        )


def _validate_conflict_action(
    decision: CanonicalTruthDecision,
    options: tuple[CanonicalTruthEvidenceOption, ...],
) -> None:
    if decision.action is CanonicalTruthDecisionAction.LEAVE_UNRESOLVED:
        if decision.selected_member is not None:
            raise CanonicalTruthError(
                "LEAVE_UNRESOLVED must not carry a selected member"
            )
        return

    if decision.selected_member is None:
        raise CanonicalTruthError("SELECT_SOURCE requires a selected member")
    matches = tuple(
        option
        for option in options
        if any(member == decision.selected_member for member in option.supporting_members)
    )
    if len(matches) != 1:
        raise CanonicalTruthError(
            "SELECT_SOURCE must select one canonical member carrying conflict evidence"
        )


def _resolve_field(
    field: CanonicalTruthField,
    options: tuple[CanonicalTruthEvidenceOption, ...],
    decision: CanonicalTruthDecision | None,
) -> CanonicalTruthFieldResolution:
    if not options:
        return CanonicalTruthFieldResolution(
            field=field,
            status=CanonicalTruthResolutionStatus.NO_EVIDENCE,
            resolved_value=None,
            supporting_members=(),
            options=(),
            decision=None,
        )
    if len(options) == 1:
        option = options[0]
        return CanonicalTruthFieldResolution(
            field=field,
            status=CanonicalTruthResolutionStatus.UNCONTESTED,
            resolved_value=option.value,
            supporting_members=option.supporting_members,
            options=options,
            decision=None,
        )
    if decision is None or (
        decision.action is CanonicalTruthDecisionAction.LEAVE_UNRESOLVED
    ):
        return CanonicalTruthFieldResolution(
            field=field,
            status=CanonicalTruthResolutionStatus.UNRESOLVED,
            resolved_value=None,
            supporting_members=(),
            options=options,
            decision=decision,
        )

    selected = next(
        option
        for option in options
        if any(member == decision.selected_member for member in option.supporting_members)
    )
    return CanonicalTruthFieldResolution(
        field=field,
        status=CanonicalTruthResolutionStatus.HUMAN_SELECTED,
        resolved_value=selected.value,
        supporting_members=selected.supporting_members,
        options=options,
        decision=decision,
    )


__all__ = [
    "CanonicalTruthError",
    "CanonicalTruthField",
    "CanonicalTruthDecisionAction",
    "CanonicalTruthDecision",
    "CanonicalTruthResolutionStatus",
    "CanonicalTruthEvidenceOption",
    "CanonicalTruthFieldResolution",
    "CanonicalVariantTruth",
    "reconcile_canonical_variant_truth",
]
