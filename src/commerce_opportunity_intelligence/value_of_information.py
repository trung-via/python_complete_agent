"""P7.5 Value-of-Information planning semantics.

This module is a pure value boundary.  It does not acquire evidence, own
evidence, score opportunities, rank inquiries, recommend actions, make
decisions, authorize collection, establish TEST_READY, or advance a lifecycle.
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
from .tiktok_affiliate_evidence import (
    TIKTOK_AFFILIATE_EVIDENCE_DIMENSIONS,
    TikTokAffiliateEvidenceProfile,
)


COMMERCE_OPPORTUNITY_INTELLIGENCE_P7_5 = (
    "COMMERCE_OPPORTUNITY_INTELLIGENCE_P7_5"
)

VALUE_OF_INFORMATION_DISPOSITIONS: tuple[str, ...] = (
    "CONTINUE",
    "DEFER",
    "STOP",
)

_MAX_IDENTIFIER_LENGTH = 256
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


def _validate_disposition(value: object, *, name: str) -> str:
    if not isinstance(value, str):
        raise OpportunityIntelligenceValidationError(f"{name} must be a string")
    if value not in VALUE_OF_INFORMATION_DISPOSITIONS:
        raise OpportunityIntelligenceValidationError(
            f"{name} must be one of {VALUE_OF_INFORMATION_DISPOSITIONS}"
        )
    return value


def _validate_evidence_dimension(value: object, *, name: str) -> str:
    if not isinstance(value, str):
        raise OpportunityIntelligenceValidationError(f"{name} must be a string")
    if value not in TIKTOK_AFFILIATE_EVIDENCE_DIMENSIONS:
        raise OpportunityIntelligenceValidationError(
            f"{name} must be one of {TIKTOK_AFFILIATE_EVIDENCE_DIMENSIONS}"
        )
    return value


@dataclass(frozen=True)
class ValueOfInformationInquiry:
    """Immutable inquiry representing one caller-authored information question.

    Contains planning claims and considerations for evaluating whether additional
    evidence across one P7.4 evidence dimension is worth acquiring. Does not own
    evidence, authorize acquisition, or establish commercial truth.
    """

    inquiry_id: str
    evidence_dimension: str
    information_question: str
    explanation: str
    disposition: str
    rationale: str
    expected_decision_impact: str
    uncertainty_reduction: str
    cost: str
    latency: str
    access_risk: str
    fragility: str
    reliability: str
    opportunity_cost: str
    decision_deadline: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "inquiry_id",
            _bounded_string(
                self.inquiry_id,
                name="inquiry_id",
                maximum=_MAX_IDENTIFIER_LENGTH,
            ),
        )
        object.__setattr__(
            self,
            "evidence_dimension",
            _validate_evidence_dimension(
                self.evidence_dimension,
                name="evidence_dimension",
            ),
        )
        object.__setattr__(
            self,
            "information_question",
            _bounded_string(
                self.information_question,
                name="information_question",
                maximum=_MAX_TEXT_LENGTH,
            ),
        )
        object.__setattr__(
            self,
            "explanation",
            _bounded_string(
                self.explanation,
                name="explanation",
                maximum=_MAX_TEXT_LENGTH,
            ),
        )
        object.__setattr__(
            self,
            "disposition",
            _validate_disposition(self.disposition, name="disposition"),
        )
        object.__setattr__(
            self,
            "rationale",
            _bounded_string(
                self.rationale,
                name="rationale",
                maximum=_MAX_TEXT_LENGTH,
            ),
        )
        for consideration in (
            "expected_decision_impact",
            "uncertainty_reduction",
            "cost",
            "latency",
            "access_risk",
            "fragility",
            "reliability",
            "opportunity_cost",
        ):
            object.__setattr__(
                self,
                consideration,
                _bounded_string(
                    getattr(self, consideration),
                    name=consideration,
                    maximum=_MAX_TEXT_LENGTH,
                ),
            )

        if isinstance(self.decision_deadline, datetime):
            deadline_str = _aware_datetime(
                self.decision_deadline,
                name="decision_deadline",
            ).isoformat()
            object.__setattr__(self, "decision_deadline", deadline_str)
        else:
            object.__setattr__(
                self,
                "decision_deadline",
                _bounded_string(
                    self.decision_deadline,
                    name="decision_deadline",
                    maximum=_MAX_TEXT_LENGTH,
                ),
            )

    @property
    def decision_relevance(self) -> str:
        """Alias for explanation describing why the answer could change the decision."""
        return self.explanation

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic JSON-serializable projection."""
        return {
            "inquiry_id": _public_projection_string(
                self.inquiry_id,
                name="inquiry_id",
            ),
            "evidence_dimension": _public_projection_string(
                self.evidence_dimension,
                name="evidence_dimension",
            ),
            "information_question": _public_projection_string(
                self.information_question,
                name="information_question",
            ),
            "explanation": _public_projection_string(
                self.explanation,
                name="explanation",
            ),
            "disposition": self.disposition,
            "rationale": _public_projection_string(
                self.rationale,
                name="rationale",
            ),
            "expected_decision_impact": _public_projection_string(
                self.expected_decision_impact,
                name="expected_decision_impact",
            ),
            "uncertainty_reduction": _public_projection_string(
                self.uncertainty_reduction,
                name="uncertainty_reduction",
            ),
            "cost": _public_projection_string(self.cost, name="cost"),
            "latency": _public_projection_string(self.latency, name="latency"),
            "access_risk": _public_projection_string(
                self.access_risk,
                name="access_risk",
            ),
            "fragility": _public_projection_string(
                self.fragility,
                name="fragility",
            ),
            "reliability": _public_projection_string(
                self.reliability,
                name="reliability",
            ),
            "opportunity_cost": _public_projection_string(
                self.opportunity_cost,
                name="opportunity_cost",
            ),
            "decision_deadline": _public_projection_string(
                self.decision_deadline,
                name="decision_deadline",
            ),
        }


@dataclass(frozen=True)
class ValueOfInformationPlan:
    """Immutable plan composing inquiries for one commerce opportunity hypothesis.

    Binds to exact DecisionContext, OpportunityHypothesis, and
    TikTokAffiliateEvidenceProfile identities at an explicit as-of time.
    Carries an ordered tuple of inquiries and one overall advisory disposition
    and rationale. Does not authorize acquisition or make commerce decisions.
    """

    plan_id: str
    decision_context_id: str
    hypothesis_id: str
    profile_id: str
    as_of: datetime
    inquiries: tuple[ValueOfInformationInquiry, ...] = field(
        default_factory=tuple
    )
    disposition: str = "STOP"
    rationale: str = ""

    def __post_init__(self) -> None:
        for name in ("plan_id", "decision_context_id", "hypothesis_id", "profile_id"):
            object.__setattr__(
                self,
                name,
                _bounded_string(
                    getattr(self, name),
                    name=name,
                    maximum=_MAX_IDENTIFIER_LENGTH,
                ),
            )
        object.__setattr__(self, "as_of", _aware_datetime(self.as_of, name="as_of"))

        if isinstance(self.inquiries, (str, bytes)) or not isinstance(
            self.inquiries, Sequence
        ):
            raise OpportunityIntelligenceValidationError(
                "inquiries must be an ordered collection"
            )

        for index, item in enumerate(self.inquiries):
            if not isinstance(item, ValueOfInformationInquiry):
                raise OpportunityIntelligenceValidationError(
                    f"inquiries[{index}] must be a ValueOfInformationInquiry"
                )

        frozen_inquiries = tuple(self.inquiries)
        inquiry_ids = tuple(inq.inquiry_id for inq in frozen_inquiries)
        if len(set(inquiry_ids)) != len(inquiry_ids):
            raise OpportunityIntelligenceValidationError(
                "inquiries must not contain duplicate inquiry_id values"
            )
        object.__setattr__(self, "inquiries", frozen_inquiries)

        object.__setattr__(
            self,
            "disposition",
            _validate_disposition(self.disposition, name="disposition"),
        )
        object.__setattr__(
            self,
            "rationale",
            _bounded_string(
                self.rationale,
                name="rationale",
                maximum=_MAX_TEXT_LENGTH,
            ),
        )

        inquiry_dispositions = [inq.disposition for inq in frozen_inquiries]
        has_continue = any(d == "CONTINUE" for d in inquiry_dispositions)
        has_defer = any(d == "DEFER" for d in inquiry_dispositions)

        if len(frozen_inquiries) == 0:
            if self.disposition != "STOP":
                raise OpportunityIntelligenceValidationError(
                    "empty inquiry sets are allowed only with overall STOP"
                )
        elif self.disposition == "CONTINUE":
            if not has_continue:
                raise OpportunityIntelligenceValidationError(
                    "overall CONTINUE requires at least one inquiry with CONTINUE"
                )
        elif self.disposition == "STOP":
            if has_continue:
                raise OpportunityIntelligenceValidationError(
                    "overall STOP must contain no CONTINUE inquiry"
                )
        elif self.disposition == "DEFER":
            if has_continue:
                raise OpportunityIntelligenceValidationError(
                    "overall DEFER must contain no CONTINUE inquiry"
                )
            if not has_defer:
                raise OpportunityIntelligenceValidationError(
                    "overall DEFER requires at least one inquiry with DEFER"
                )

    def inquiries_by_disposition(
        self, disposition: str
    ) -> tuple[ValueOfInformationInquiry, ...]:
        """Return the subset of inquiries carrying the specified planning disposition."""
        valid_disposition = _validate_disposition(disposition, name="disposition")
        return tuple(
            inq for inq in self.inquiries if inq.disposition == valid_disposition
        )

    def inquiries_by_dimension(
        self, dimension: str
    ) -> tuple[ValueOfInformationInquiry, ...]:
        """Return the subset of inquiries addressing the specified evidence dimension."""
        valid_dimension = _validate_evidence_dimension(dimension, name="dimension")
        return tuple(
            inq for inq in self.inquiries if inq.evidence_dimension == valid_dimension
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic JSON-serializable projection."""
        return {
            "plan_id": _public_projection_string(self.plan_id, name="plan_id"),
            "decision_context_id": _public_projection_string(
                self.decision_context_id,
                name="decision_context_id",
            ),
            "hypothesis_id": _public_projection_string(
                self.hypothesis_id,
                name="hypothesis_id",
            ),
            "profile_id": _public_projection_string(
                self.profile_id,
                name="profile_id",
            ),
            "as_of": self.as_of.isoformat(),
            "inquiries": [inq.to_dict() for inq in self.inquiries],
            "disposition": self.disposition,
            "rationale": _public_projection_string(
                self.rationale,
                name="rationale",
            ),
        }


def create_value_of_information_plan(
    *,
    decision_context: DecisionContext,
    hypothesis: OpportunityHypothesis | None = None,
    opportunity_hypothesis: OpportunityHypothesis | None = None,
    profile: TikTokAffiliateEvidenceProfile | None = None,
    evidence_profile: TikTokAffiliateEvidenceProfile | None = None,
    plan_id: str,
    as_of: datetime,
    inquiries: Sequence[ValueOfInformationInquiry] = (),
    disposition: str,
    rationale: str,
) -> ValueOfInformationPlan:
    """Purely construct a Value-of-Information plan bound to exact context, hypothesis, and profile."""
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

    if profile is not None and evidence_profile is not None:
        if profile is not evidence_profile:
            raise OpportunityIntelligenceValidationError(
                "cannot supply conflicting profile arguments"
            )
        target_profile = profile
    elif profile is not None:
        target_profile = profile
    elif evidence_profile is not None:
        target_profile = evidence_profile
    else:
        raise OpportunityIntelligenceValidationError(
            "profile must be a TikTokAffiliateEvidenceProfile"
        )

    if not isinstance(target_profile, TikTokAffiliateEvidenceProfile):
        raise OpportunityIntelligenceValidationError(
            "profile must be a TikTokAffiliateEvidenceProfile"
        )

    if target_hypothesis.decision_context_id != decision_context.context_id:
        raise OpportunityIntelligenceValidationError(
            "hypothesis decision_context_id must match the supplied DecisionContext"
        )

    if target_profile.decision_context_id != decision_context.context_id:
        raise OpportunityIntelligenceValidationError(
            "profile decision_context_id must match the supplied DecisionContext"
        )

    if target_profile.hypothesis_id != target_hypothesis.hypothesis_id:
        raise OpportunityIntelligenceValidationError(
            "profile hypothesis_id must match the supplied OpportunityHypothesis"
        )

    return ValueOfInformationPlan(
        plan_id=plan_id,
        decision_context_id=decision_context.context_id,
        hypothesis_id=target_hypothesis.hypothesis_id,
        profile_id=target_profile.profile_id,
        as_of=as_of,
        inquiries=inquiries,  # type: ignore[arg-type]
        disposition=disposition,
        rationale=rationale,
    )
