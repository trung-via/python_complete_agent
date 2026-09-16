"""P7.3 decision context and opportunity hypothesis semantics.

This module is a pure value boundary.  It does not discover subjects, own
evidence, score opportunities, recommend actions, make decisions, or advance a
lifecycle.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


COMMERCE_OPPORTUNITY_INTELLIGENCE_P7_3 = (
    "COMMERCE_OPPORTUNITY_INTELLIGENCE_P7_3"
)

_MAX_IDENTIFIER_LENGTH = 256
_MAX_REFERENCE_LENGTH = 512
_MAX_TEXT_LENGTH = 4096


class OpportunityIntelligenceValidationError(ValueError):
    """A P7.3 semantic value failed deterministic validation."""


def _bounded_string(value: object, *, name: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise OpportunityIntelligenceValidationError(f"{name} must be a string")
    if not value.strip():
        raise OpportunityIntelligenceValidationError(f"{name} must not be blank")
    if len(value) > maximum:
        raise OpportunityIntelligenceValidationError(
            f"{name} must contain at most {maximum} characters"
        )
    return value


def _optional_bounded_string(value: object, *, name: str) -> str | None:
    if value is None:
        return None
    return _bounded_string(value, name=name, maximum=_MAX_TEXT_LENGTH)


def _ordered_strings(
    values: object,
    *,
    name: str,
    maximum: int = _MAX_TEXT_LENGTH,
) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise OpportunityIntelligenceValidationError(
            f"{name} must be an ordered collection of strings"
        )

    preserved = tuple(
        _bounded_string(item, name=f"{name}[{index}]", maximum=maximum)
        for index, item in enumerate(values)
    )
    if len(set(preserved)) != len(preserved):
        raise OpportunityIntelligenceValidationError(
            f"{name} must not contain duplicate values"
        )
    return preserved


def _aware_datetime(value: object, *, name: str) -> datetime:
    if not isinstance(value, datetime):
        raise OpportunityIntelligenceValidationError(f"{name} must be a datetime")
    try:
        offset = value.utcoffset()
    except (OverflowError, ValueError) as exc:
        raise OpportunityIntelligenceValidationError(
            f"{name} must have a valid timezone offset"
        ) from exc
    if value.tzinfo is None or offset is None:
        raise OpportunityIntelligenceValidationError(
            f"{name} must be timezone-aware"
        )
    return value


@dataclass(frozen=True)
class DecisionContext:
    """Immutable context for one commerce decision at an explicit as-of time.

    Optional dimensions stay absent when the caller does not supply them.  This
    value contains context only; it is not a decision or recommendation.
    """

    context_id: str
    decision_question: str
    objective: str
    as_of: datetime
    market: str | None = None
    audience: str | None = None
    channel: str | None = None
    time_horizon: str | None = None
    decision_deadline: datetime | None = None
    constraints: tuple[str, ...] = field(default_factory=tuple)
    alternatives: tuple[str, ...] = field(default_factory=tuple)
    economic_constraints: tuple[str, ...] = field(default_factory=tuple)
    risk_constraints: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "context_id",
            _bounded_string(
                self.context_id,
                name="context_id",
                maximum=_MAX_IDENTIFIER_LENGTH,
            ),
        )
        object.__setattr__(
            self,
            "decision_question",
            _bounded_string(
                self.decision_question,
                name="decision_question",
                maximum=_MAX_TEXT_LENGTH,
            ),
        )
        object.__setattr__(
            self,
            "objective",
            _bounded_string(
                self.objective,
                name="objective",
                maximum=_MAX_TEXT_LENGTH,
            ),
        )
        object.__setattr__(self, "as_of", _aware_datetime(self.as_of, name="as_of"))

        for name in ("market", "audience", "channel", "time_horizon"):
            object.__setattr__(
                self,
                name,
                _optional_bounded_string(getattr(self, name), name=name),
            )

        if self.decision_deadline is not None:
            deadline = _aware_datetime(
                self.decision_deadline,
                name="decision_deadline",
            )
            if deadline < self.as_of:
                raise OpportunityIntelligenceValidationError(
                    "decision_deadline must not precede as_of"
                )
            object.__setattr__(self, "decision_deadline", deadline)

        for name in (
            "constraints",
            "alternatives",
            "economic_constraints",
            "risk_constraints",
        ):
            object.__setattr__(
                self,
                name,
                _ordered_strings(getattr(self, name), name=name),
            )

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic JSON-serializable projection."""

        return {
            "context_id": self.context_id,
            "decision_question": self.decision_question,
            "objective": self.objective,
            "as_of": self.as_of.isoformat(),
            "market": self.market,
            "audience": self.audience,
            "channel": self.channel,
            "time_horizon": self.time_horizon,
            "decision_deadline": (
                self.decision_deadline.isoformat()
                if self.decision_deadline is not None
                else None
            ),
            "constraints": list(self.constraints),
            "alternatives": list(self.alternatives),
            "economic_constraints": list(self.economic_constraints),
            "risk_constraints": list(self.risk_constraints),
        }


@dataclass(frozen=True)
class OpportunityHypothesis:
    """Immutable, falsifiable claim tied to one exact decision context."""

    hypothesis_id: str
    decision_context_id: str
    subject_ref: str
    falsifiable_claim: str
    created_at: datetime
    assumptions: tuple[str, ...] = field(default_factory=tuple)
    supporting_evidence_refs: tuple[str, ...] = field(default_factory=tuple)
    counter_evidence_refs: tuple[str, ...] = field(default_factory=tuple)
    important_unknowns: tuple[str, ...] = field(default_factory=tuple)
    disconfirming_conditions: tuple[str, ...] = field(default_factory=tuple)
    expected_outcomes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        for name in ("hypothesis_id", "decision_context_id"):
            object.__setattr__(
                self,
                name,
                _bounded_string(
                    getattr(self, name),
                    name=name,
                    maximum=_MAX_IDENTIFIER_LENGTH,
                ),
            )
        object.__setattr__(
            self,
            "subject_ref",
            _bounded_string(
                self.subject_ref,
                name="subject_ref",
                maximum=_MAX_REFERENCE_LENGTH,
            ),
        )
        object.__setattr__(
            self,
            "falsifiable_claim",
            _bounded_string(
                self.falsifiable_claim,
                name="falsifiable_claim",
                maximum=_MAX_TEXT_LENGTH,
            ),
        )
        object.__setattr__(
            self,
            "created_at",
            _aware_datetime(self.created_at, name="created_at"),
        )

        for name in (
            "assumptions",
            "important_unknowns",
            "disconfirming_conditions",
            "expected_outcomes",
        ):
            object.__setattr__(
                self,
                name,
                _ordered_strings(getattr(self, name), name=name),
            )
        for name in ("supporting_evidence_refs", "counter_evidence_refs"):
            object.__setattr__(
                self,
                name,
                _ordered_strings(
                    getattr(self, name),
                    name=name,
                    maximum=_MAX_REFERENCE_LENGTH,
                ),
            )

        if not self.disconfirming_conditions:
            raise OpportunityIntelligenceValidationError(
                "disconfirming_conditions must contain at least one condition"
            )
        overlap = set(self.supporting_evidence_refs).intersection(
            self.counter_evidence_refs
        )
        if overlap:
            raise OpportunityIntelligenceValidationError(
                "supporting and counter evidence references must not overlap"
            )

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic JSON-serializable projection."""

        return {
            "hypothesis_id": self.hypothesis_id,
            "decision_context_id": self.decision_context_id,
            "subject_ref": self.subject_ref,
            "falsifiable_claim": self.falsifiable_claim,
            "created_at": self.created_at.isoformat(),
            "assumptions": list(self.assumptions),
            "supporting_evidence_refs": list(self.supporting_evidence_refs),
            "counter_evidence_refs": list(self.counter_evidence_refs),
            "important_unknowns": list(self.important_unknowns),
            "disconfirming_conditions": list(self.disconfirming_conditions),
            "expected_outcomes": list(self.expected_outcomes),
        }


def create_opportunity_hypothesis(
    *,
    decision_context: DecisionContext,
    hypothesis_id: str,
    decision_context_id: str,
    subject_ref: str,
    falsifiable_claim: str,
    created_at: datetime,
    assumptions: Sequence[str] = (),
    supporting_evidence_refs: Sequence[str] = (),
    counter_evidence_refs: Sequence[str] = (),
    important_unknowns: Sequence[str] = (),
    disconfirming_conditions: Sequence[str],
    expected_outcomes: Sequence[str] = (),
) -> OpportunityHypothesis:
    """Purely construct a hypothesis bound to the supplied exact context."""

    if not isinstance(decision_context, DecisionContext):
        raise OpportunityIntelligenceValidationError(
            "decision_context must be a DecisionContext"
        )
    supplied_context_id = _bounded_string(
        decision_context_id,
        name="decision_context_id",
        maximum=_MAX_IDENTIFIER_LENGTH,
    )
    if supplied_context_id != decision_context.context_id:
        raise OpportunityIntelligenceValidationError(
            "decision_context_id must match the supplied DecisionContext"
        )
    return OpportunityHypothesis(
        hypothesis_id=hypothesis_id,
        decision_context_id=supplied_context_id,
        subject_ref=subject_ref,
        falsifiable_claim=falsifiable_claim,
        created_at=created_at,
        assumptions=assumptions,  # type: ignore[arg-type]
        supporting_evidence_refs=supporting_evidence_refs,  # type: ignore[arg-type]
        counter_evidence_refs=counter_evidence_refs,  # type: ignore[arg-type]
        important_unknowns=important_unknowns,  # type: ignore[arg-type]
        disconfirming_conditions=disconfirming_conditions,  # type: ignore[arg-type]
        expected_outcomes=expected_outcomes,  # type: ignore[arg-type]
    )
