"""P7.6 Market test and funnel evidence profile semantics.

This module is a pure value boundary. It organizes caller-supplied opaque
evidence references across four fixed post-intervention dimensions bound to P7.3
DecisionContext and OpportunityHypothesis. It does not design, authorize, or
execute tests; score test success; claim causation; classify a winner; or
advance a lifecycle.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .decision_context import (
    DecisionContext,
    OpportunityHypothesis,
    OpportunityIntelligenceValidationError,
)


COMMERCE_OPPORTUNITY_INTELLIGENCE_P7_6 = (
    "COMMERCE_OPPORTUNITY_INTELLIGENCE_P7_6"
)

MARKET_TEST_EVIDENCE_DIMENSIONS: tuple[str, ...] = (
    "exposure_evidence_refs",
    "funnel_evidence_refs",
    "economic_evidence_refs",
    "quality_evidence_refs",
)

_MAX_IDENTIFIER_LENGTH = 256
_MAX_REFERENCE_LENGTH = 512
_UNSET = object()

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
            r"|[\"']?(?:session(?:id|_id|token|_token)?|phpsessid|jsessionid|"
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


def _public_projection_string(value: str, *, name: str) -> str:
    for forbidden_class, pattern in _FORBIDDEN_PUBLIC_STRING_PATTERNS:
        if pattern.search(value):
            raise OpportunityIntelligenceValidationError(
                f"{name} must not contain {forbidden_class}"
            )
    return value


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
    if "\r" in value or "\n" in value:
        raise OpportunityIntelligenceValidationError(
            f"{name} must be a single-line string"
        )
    if len(value) > maximum:
        raise OpportunityIntelligenceValidationError(
            f"{name} must contain at most {maximum} characters"
        )
    return _public_projection_string(value, name=name)


def _bounded_ref(value: object, *, name: str) -> str:
    if not isinstance(value, str):
        raise OpportunityIntelligenceValidationError(f"{name} must be a string")
    if not value.strip():
        raise OpportunityIntelligenceValidationError(f"{name} must not be blank")
    if "\r" in value or "\n" in value:
        raise OpportunityIntelligenceValidationError(
            f"{name} must be a single-line string"
        )
    if len(value) > _MAX_REFERENCE_LENGTH:
        raise OpportunityIntelligenceValidationError(
            f"{name} must contain at most {_MAX_REFERENCE_LENGTH} characters"
        )
    return _public_projection_string(value, name=name)


def _ordered_refs(values: object, *, name: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise OpportunityIntelligenceValidationError(
            f"{name} must be an ordered collection of strings"
        )
    preserved = tuple(
        _bounded_ref(item, name=f"{name}[{index}]")
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


@dataclass(frozen=True, init=False)
class MarketTestEvidenceProfile:
    """Immutable evidence profile for one market test intervention.

    Owns only the organization of opaque caller-supplied evidence references
    across four fixed semantic dimensions (exposure, funnel, economic, quality).
    Does not own underlying evidence, authorize tests, execute interventions,
    judge success, or validate winners.
    """

    profile_id: str
    test_id: str
    decision_context_id: str
    hypothesis_id: str
    test_design_ref: str
    authorization_ref: str
    action_ref: str
    test_started_at: datetime
    test_ended_at: datetime
    as_of: datetime
    exposure_evidence_refs: tuple[str, ...] = field(default_factory=tuple)
    funnel_evidence_refs: tuple[str, ...] = field(default_factory=tuple)
    economic_evidence_refs: tuple[str, ...] = field(default_factory=tuple)
    quality_evidence_refs: tuple[str, ...] = field(default_factory=tuple)

    def __init__(
        self,
        profile_id: str,
        test_id: str,
        decision_context_id: str,
        hypothesis_id: str,
        test_design_ref: str,
        authorization_ref: str,
        action_ref: str,
        test_started_at: datetime,
        test_ended_at: datetime,
        as_of: datetime,
        exposure_evidence_refs: Sequence[str] = (),
        funnel_evidence_refs: Sequence[str] = (),
        economic_evidence_refs: Sequence[str] = (),
        quality_evidence_refs: Sequence[str] = (),
        *args: Any,
        decision_deadline: Any = _UNSET,
        **kwargs: Any,
    ) -> None:
        if args:
            raise OpportunityIntelligenceValidationError(
                "MarketTestEvidenceProfile received unexpected positional arguments"
            )
        if decision_deadline is not _UNSET:
            raise OpportunityIntelligenceValidationError(
                "MarketTestEvidenceProfile does not accept an independent decision_deadline; "
                "decision deadline is canonically owned by DecisionContext"
            )
        if kwargs:
            unexpected = ", ".join(sorted(kwargs.keys()))
            raise OpportunityIntelligenceValidationError(
                f"MarketTestEvidenceProfile received unexpected keyword arguments: {unexpected}"
            )

        object.__setattr__(
            self,
            "profile_id",
            _bounded_string(
                profile_id,
                name="profile_id",
                maximum=_MAX_IDENTIFIER_LENGTH,
            ),
        )
        object.__setattr__(
            self,
            "test_id",
            _bounded_string(
                test_id,
                name="test_id",
                maximum=_MAX_IDENTIFIER_LENGTH,
            ),
        )
        object.__setattr__(
            self,
            "decision_context_id",
            _bounded_string(
                decision_context_id,
                name="decision_context_id",
                maximum=_MAX_IDENTIFIER_LENGTH,
            ),
        )
        object.__setattr__(
            self,
            "hypothesis_id",
            _bounded_string(
                hypothesis_id,
                name="hypothesis_id",
                maximum=_MAX_IDENTIFIER_LENGTH,
            ),
        )
        object.__setattr__(
            self,
            "test_design_ref",
            _bounded_ref(
                test_design_ref,
                name="test_design_ref",
            ),
        )
        object.__setattr__(
            self,
            "authorization_ref",
            _bounded_ref(
                authorization_ref,
                name="authorization_ref",
            ),
        )
        object.__setattr__(
            self,
            "action_ref",
            _bounded_ref(
                action_ref,
                name="action_ref",
            ),
        )

        started = _aware_datetime(test_started_at, name="test_started_at")
        ended = _aware_datetime(test_ended_at, name="test_ended_at")
        as_of_dt = _aware_datetime(as_of, name="as_of")

        if started > ended:
            raise OpportunityIntelligenceValidationError(
                "test_started_at must be less than or equal to test_ended_at"
            )
        if ended > as_of_dt:
            raise OpportunityIntelligenceValidationError(
                "test_ended_at must be less than or equal to as_of"
            )

        object.__setattr__(self, "test_started_at", started)
        object.__setattr__(self, "test_ended_at", ended)
        object.__setattr__(self, "as_of", as_of_dt)

        dim_values = {
            "exposure_evidence_refs": exposure_evidence_refs,
            "funnel_evidence_refs": funnel_evidence_refs,
            "economic_evidence_refs": economic_evidence_refs,
            "quality_evidence_refs": quality_evidence_refs,
        }
        for dim in MARKET_TEST_EVIDENCE_DIMENSIONS:
            object.__setattr__(
                self,
                dim,
                _ordered_refs(dim_values[dim], name=dim),
            )

        total_refs = sum(
            len(getattr(self, dim)) for dim in MARKET_TEST_EVIDENCE_DIMENSIONS
        )
        if total_refs == 0:
            raise OpportunityIntelligenceValidationError(
                "MarketTestEvidenceProfile must contain at least one evidence reference across dimensions"
            )

    def represented_dimensions(self) -> tuple[str, ...]:
        """Return the names of dimensions that have at least one supplied reference."""
        return tuple(
            dim
            for dim in MARKET_TEST_EVIDENCE_DIMENSIONS
            if len(getattr(self, dim)) > 0
        )

    def unrepresented_dimensions(self) -> tuple[str, ...]:
        """Return the names of dimensions that have no supplied references."""
        return tuple(
            dim
            for dim in MARKET_TEST_EVIDENCE_DIMENSIONS
            if len(getattr(self, dim)) == 0
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic JSON-serializable projection."""
        return {
            "profile_id": _public_projection_string(
                self.profile_id,
                name="profile_id",
            ),
            "test_id": _public_projection_string(
                self.test_id,
                name="test_id",
            ),
            "decision_context_id": _public_projection_string(
                self.decision_context_id,
                name="decision_context_id",
            ),
            "hypothesis_id": _public_projection_string(
                self.hypothesis_id,
                name="hypothesis_id",
            ),
            "test_design_ref": _public_projection_string(
                self.test_design_ref,
                name="test_design_ref",
            ),
            "authorization_ref": _public_projection_string(
                self.authorization_ref,
                name="authorization_ref",
            ),
            "action_ref": _public_projection_string(
                self.action_ref,
                name="action_ref",
            ),
            "test_started_at": self.test_started_at.isoformat(),
            "test_ended_at": self.test_ended_at.isoformat(),
            "as_of": self.as_of.isoformat(),
            "exposure_evidence_refs": _public_projection_ordered(
                self.exposure_evidence_refs,
                name="exposure_evidence_refs",
            ),
            "funnel_evidence_refs": _public_projection_ordered(
                self.funnel_evidence_refs,
                name="funnel_evidence_refs",
            ),
            "economic_evidence_refs": _public_projection_ordered(
                self.economic_evidence_refs,
                name="economic_evidence_refs",
            ),
            "quality_evidence_refs": _public_projection_ordered(
                self.quality_evidence_refs,
                name="quality_evidence_refs",
            ),
            "represented_dimensions": list(self.represented_dimensions()),
            "unrepresented_dimensions": list(self.unrepresented_dimensions()),
        }


def create_market_test_evidence_profile(
    *,
    decision_context: DecisionContext,
    hypothesis: OpportunityHypothesis | None = None,
    opportunity_hypothesis: OpportunityHypothesis | None = None,
    profile_id: str,
    test_id: str,
    test_design_ref: str,
    authorization_ref: str,
    action_ref: str,
    test_started_at: datetime,
    test_ended_at: datetime,
    as_of: datetime,
    exposure_evidence_refs: Sequence[str] = (),
    funnel_evidence_refs: Sequence[str] = (),
    economic_evidence_refs: Sequence[str] = (),
    quality_evidence_refs: Sequence[str] = (),
    **kwargs: Any,
) -> MarketTestEvidenceProfile:
    """Purely construct a market test evidence profile bound to exact context and hypothesis."""
    if kwargs:
        if "decision_deadline" in kwargs:
            raise OpportunityIntelligenceValidationError(
                "create_market_test_evidence_profile does not accept an independent decision_deadline; "
                "decision deadline is canonically owned by DecisionContext"
            )
        unexpected = ", ".join(sorted(kwargs.keys()))
        raise OpportunityIntelligenceValidationError(
            f"create_market_test_evidence_profile received unexpected arguments: {unexpected}"
        )

    if not isinstance(decision_context, DecisionContext):
        raise OpportunityIntelligenceValidationError(
            "decision_context must be a DecisionContext"
        )

    if hypothesis is not None and opportunity_hypothesis is not None:
        if hypothesis is not opportunity_hypothesis:
            raise OpportunityIntelligenceValidationError(
                "cannot supply conflicting hypothesis arguments"
            )
        target_hypothesis = hypothesis
    elif hypothesis is not None:
        target_hypothesis = hypothesis
    elif opportunity_hypothesis is not None:
        target_hypothesis = opportunity_hypothesis
    else:
        raise OpportunityIntelligenceValidationError(
            "hypothesis must be an OpportunityHypothesis"
        )

    if not isinstance(target_hypothesis, OpportunityHypothesis):
        raise OpportunityIntelligenceValidationError(
            "hypothesis must be an OpportunityHypothesis"
        )

    if target_hypothesis.decision_context_id != decision_context.context_id:
        raise OpportunityIntelligenceValidationError(
            "hypothesis decision_context_id must match the supplied DecisionContext"
        )

    return MarketTestEvidenceProfile(
        profile_id=profile_id,
        test_id=test_id,
        decision_context_id=decision_context.context_id,
        hypothesis_id=target_hypothesis.hypothesis_id,
        test_design_ref=test_design_ref,
        authorization_ref=authorization_ref,
        action_ref=action_ref,
        test_started_at=test_started_at,
        test_ended_at=test_ended_at,
        as_of=as_of,
        exposure_evidence_refs=exposure_evidence_refs,
        funnel_evidence_refs=funnel_evidence_refs,
        economic_evidence_refs=economic_evidence_refs,
        quality_evidence_refs=quality_evidence_refs,
    )
