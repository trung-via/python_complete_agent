"""P7.4 TikTok affiliate evidence profile semantics.

This module is a pure value boundary.  It does not acquire evidence, own
evidence, score opportunities, recommend actions, make decisions, or advance a
lifecycle.
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


COMMERCE_OPPORTUNITY_INTELLIGENCE_P7_4 = (
    "COMMERCE_OPPORTUNITY_INTELLIGENCE_P7_4"
)

TIKTOK_AFFILIATE_EVIDENCE_DIMENSIONS: tuple[str, ...] = (
    "affiliate_economics",
    "market_traction",
    "creator_ecosystem",
    "content_activity",
    "audience_channel_fit",
    "competition_saturation",
)

_MAX_IDENTIFIER_LENGTH = 256
_MAX_REFERENCE_LENGTH = 512

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


@dataclass(frozen=True)
class TikTokAffiliateEvidenceProfile:
    """Immutable evidence profile for one TikTok affiliate opportunity hypothesis.

    Owns only the organization of opaque caller-supplied evidence references
    across six fixed semantic dimensions.  Does not own the referenced evidence,
    score opportunities, or recommend actions.
    """

    profile_id: str
    decision_context_id: str
    hypothesis_id: str
    as_of: datetime
    affiliate_economics: tuple[str, ...] = field(default_factory=tuple)
    market_traction: tuple[str, ...] = field(default_factory=tuple)
    creator_ecosystem: tuple[str, ...] = field(default_factory=tuple)
    content_activity: tuple[str, ...] = field(default_factory=tuple)
    audience_channel_fit: tuple[str, ...] = field(default_factory=tuple)
    competition_saturation: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        for name in ("profile_id", "decision_context_id", "hypothesis_id"):
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

        for dim in TIKTOK_AFFILIATE_EVIDENCE_DIMENSIONS:
            object.__setattr__(
                self,
                dim,
                _ordered_refs(getattr(self, dim), name=dim),
            )

    def represented_dimensions(self) -> tuple[str, ...]:
        """Return the names of dimensions that have at least one supplied reference."""
        return tuple(
            dim
            for dim in TIKTOK_AFFILIATE_EVIDENCE_DIMENSIONS
            if len(getattr(self, dim)) > 0
        )

    def unrepresented_dimensions(self) -> tuple[str, ...]:
        """Return the names of dimensions that have no supplied references."""
        return tuple(
            dim
            for dim in TIKTOK_AFFILIATE_EVIDENCE_DIMENSIONS
            if len(getattr(self, dim)) == 0
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic JSON-serializable projection."""
        return {
            "profile_id": _public_projection_string(
                self.profile_id,
                name="profile_id",
            ),
            "decision_context_id": _public_projection_string(
                self.decision_context_id,
                name="decision_context_id",
            ),
            "hypothesis_id": _public_projection_string(
                self.hypothesis_id,
                name="hypothesis_id",
            ),
            "as_of": self.as_of.isoformat(),
            "affiliate_economics": _public_projection_ordered(
                self.affiliate_economics,
                name="affiliate_economics",
            ),
            "market_traction": _public_projection_ordered(
                self.market_traction,
                name="market_traction",
            ),
            "creator_ecosystem": _public_projection_ordered(
                self.creator_ecosystem,
                name="creator_ecosystem",
            ),
            "content_activity": _public_projection_ordered(
                self.content_activity,
                name="content_activity",
            ),
            "audience_channel_fit": _public_projection_ordered(
                self.audience_channel_fit,
                name="audience_channel_fit",
            ),
            "competition_saturation": _public_projection_ordered(
                self.competition_saturation,
                name="competition_saturation",
            ),
            "represented_dimensions": list(self.represented_dimensions()),
            "unrepresented_dimensions": list(self.unrepresented_dimensions()),
        }


def create_tiktok_affiliate_evidence_profile(
    *,
    decision_context: DecisionContext,
    hypothesis: OpportunityHypothesis | None = None,
    opportunity_hypothesis: OpportunityHypothesis | None = None,
    profile_id: str,
    as_of: datetime,
    affiliate_economics: Sequence[str] = (),
    market_traction: Sequence[str] = (),
    creator_ecosystem: Sequence[str] = (),
    content_activity: Sequence[str] = (),
    audience_channel_fit: Sequence[str] = (),
    competition_saturation: Sequence[str] = (),
) -> TikTokAffiliateEvidenceProfile:
    """Purely construct a TikTok affiliate evidence profile bound to the supplied exact context and hypothesis."""
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

    return TikTokAffiliateEvidenceProfile(
        profile_id=profile_id,
        decision_context_id=decision_context.context_id,
        hypothesis_id=target_hypothesis.hypothesis_id,
        as_of=as_of,
        affiliate_economics=tuple(affiliate_economics),
        market_traction=tuple(market_traction),
        creator_ecosystem=tuple(creator_ecosystem),
        content_activity=tuple(content_activity),
        audience_channel_fit=tuple(audience_channel_fit),
        competition_saturation=tuple(competition_saturation),
    )
