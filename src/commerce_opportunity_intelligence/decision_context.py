"""P7.3 decision context and opportunity hypothesis semantics.

This module is a pure value boundary.  It does not discover subjects, own
evidence, score opportunities, recommend actions, make decisions, or advance a
lifecycle.
"""

from __future__ import annotations

import re
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

_FORBIDDEN_PUBLIC_STRING_PATTERNS = (
    (
        "object representation",
        re.compile(r"<[^>\r\n]*\bobject\s+at\s+0x[0-9a-f]+>", re.IGNORECASE),
    ),
    ("memory address", re.compile(r"\b0x[0-9a-f]{6,}\b", re.IGNORECASE)),
    (
        "secret material",
        re.compile(
            r"(?:"
            r"-----BEGIN\s+(?:[A-Z]+\s+)*PRIVATE KEY-----"
            r"|\bAKIA[0-9A-Z]{16}\b"
            r"|\bsk-[A-Za-z0-9_-]{12,}\b"
            r"|\bBearer\s+[A-Za-z0-9._~+/-]+=*"
            r"|[\"']?(?:api[-_ ]?key|access[-_ ]?token|refresh[-_ ]?token|"
            r"client[-_ ]?secret|password|passwd|authorization|secret)"
            r"[\"']?\s*[:=]\s*[\"']?\S+"
            r")",
            re.IGNORECASE,
        ),
    ),
    (
        "cookie or session data",
        re.compile(
            r"(?:"
            r"\b(?:set-cookie|cookie)\s*:\s*\S+"
            r"|[\"']?(?:session(?:id|_id|token)?|phpsessid|jsessionid|"
            r"__Host-[A-Za-z0-9_-]+|__Secure-[A-Za-z0-9_-]+)"
            r"[\"']?\s*[:=]\s*[\"']?\S+"
            r")",
            re.IGNORECASE,
        ),
    ),
    (
        "model prompt",
        re.compile(
            r"(?:<\|(?:system|user|assistant|developer)(?:_start|_end)?\|>"
            r"|\[/?INST\]"
            r"|[\"']?role[\"']?\s*:\s*[\"'](?:system|developer)[\"']"
            r"|\b(?:system|developer)\s*:\s*\S+"
            r"|\bignore\s+(?:all\s+)?previous\s+instructions\b"
            r"|\b(?:system|developer|model)\s+(?:prompt|message|instructions?)"
            r"\s*[:=])",
            re.IGNORECASE,
        ),
    ),
    (
        "hidden execution metadata",
        re.compile(
            r"(?:"
            r"[\"']?(?:run[_ -]?id|tool[_ -]?call[_ -]?id|trace[_ -]?id|"
            r"span[_ -]?id|request[_ -]?id|executor|reviewed[_ -]?sha|"
            r"head[_ -]?sha)[\"']?\s*[:=]\s*[\"']?\S+"
            r"|\b(?:RUN|REVIEW|REMEDIATION|FINDING|REPAIR)-\d+-\d+\b"
            r")",
            re.IGNORECASE,
        ),
    ),
    (
        "raw HTML",
        re.compile(
            r"(?:<!DOCTYPE\s+html\b|<!--|</?[A-Za-z][^>]*>)",
            re.IGNORECASE,
        ),
    ),
)


class OpportunityIntelligenceValidationError(ValueError):
    """A P7.3 semantic value failed deterministic validation."""


def _public_projection_string(value: str, *, name: str) -> str:
    for forbidden_class, pattern in _FORBIDDEN_PUBLIC_STRING_PATTERNS:
        if pattern.search(value):
            raise OpportunityIntelligenceValidationError(
                f"{name} must not contain {forbidden_class}"
            )
    return value


def _public_projection_optional(value: str | None, *, name: str) -> str | None:
    if value is None:
        return None
    return _public_projection_string(value, name=name)


def _public_projection_ordered(values: tuple[str, ...], *, name: str) -> list[str]:
    return [
        _public_projection_string(item, name=f"{name}[{index}]")
        for index, item in enumerate(values)
    ]


def _bounded_string(value: object, *, name: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise OpportunityIntelligenceValidationError(f"{name} must be a string")
    if not value.strip():
        raise OpportunityIntelligenceValidationError(f"{name} must not be blank")
    if len(value) > maximum:
        raise OpportunityIntelligenceValidationError(
            f"{name} must contain at most {maximum} characters"
        )
    return _public_projection_string(value, name=name)


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
            "context_id": _public_projection_string(
                self.context_id,
                name="context_id",
            ),
            "decision_question": _public_projection_string(
                self.decision_question,
                name="decision_question",
            ),
            "objective": _public_projection_string(self.objective, name="objective"),
            "as_of": self.as_of.isoformat(),
            "market": _public_projection_optional(self.market, name="market"),
            "audience": _public_projection_optional(self.audience, name="audience"),
            "channel": _public_projection_optional(self.channel, name="channel"),
            "time_horizon": _public_projection_optional(
                self.time_horizon,
                name="time_horizon",
            ),
            "decision_deadline": (
                self.decision_deadline.isoformat()
                if self.decision_deadline is not None
                else None
            ),
            "constraints": _public_projection_ordered(
                self.constraints,
                name="constraints",
            ),
            "alternatives": _public_projection_ordered(
                self.alternatives,
                name="alternatives",
            ),
            "economic_constraints": _public_projection_ordered(
                self.economic_constraints,
                name="economic_constraints",
            ),
            "risk_constraints": _public_projection_ordered(
                self.risk_constraints,
                name="risk_constraints",
            ),
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
            "hypothesis_id": _public_projection_string(
                self.hypothesis_id,
                name="hypothesis_id",
            ),
            "decision_context_id": _public_projection_string(
                self.decision_context_id,
                name="decision_context_id",
            ),
            "subject_ref": _public_projection_string(
                self.subject_ref,
                name="subject_ref",
            ),
            "falsifiable_claim": _public_projection_string(
                self.falsifiable_claim,
                name="falsifiable_claim",
            ),
            "created_at": self.created_at.isoformat(),
            "assumptions": _public_projection_ordered(
                self.assumptions,
                name="assumptions",
            ),
            "supporting_evidence_refs": _public_projection_ordered(
                self.supporting_evidence_refs,
                name="supporting_evidence_refs",
            ),
            "counter_evidence_refs": _public_projection_ordered(
                self.counter_evidence_refs,
                name="counter_evidence_refs",
            ),
            "important_unknowns": _public_projection_ordered(
                self.important_unknowns,
                name="important_unknowns",
            ),
            "disconfirming_conditions": _public_projection_ordered(
                self.disconfirming_conditions,
                name="disconfirming_conditions",
            ),
            "expected_outcomes": _public_projection_ordered(
                self.expected_outcomes,
                name="expected_outcomes",
            ),
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
