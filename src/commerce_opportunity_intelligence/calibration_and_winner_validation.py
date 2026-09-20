"""P7.7 semantic hypothesis calibration and winner validation.

This pure value boundary interprets caller-selected P7.6 evidence references
against one exact P7.3 decision context and hypothesis. It does not own the
underlying evidence, calculate probabilities or scores, establish causality,
advance a lifecycle, approve a decision, recommend an action, or mutate Product
Intelligence policy.
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
from .market_test_evidence import (
    MARKET_TEST_EVIDENCE_DIMENSIONS,
    MarketTestEvidenceProfile,
)


COMMERCE_OPPORTUNITY_INTELLIGENCE_P7_7 = (
    "COMMERCE_OPPORTUNITY_INTELLIGENCE_P7_7"
)

HYPOTHESIS_CALIBRATION_DISPOSITIONS: tuple[str, ...] = (
    "ALIGNED",
    "MIXED",
    "MISALIGNED",
    "INCONCLUSIVE",
)

WINNER_VALIDATION_DISPOSITIONS: tuple[str, ...] = (
    "SUPPORTED",
    "CONTRADICTED",
    "INCONCLUSIVE",
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
        re.compile(r"(?:<!DOCTYPE\s+html\b|<!--|</?[A-Za-z][^>]*>)", re.IGNORECASE),
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


def _ordered_strings(
    values: object,
    *,
    name: str,
    maximum: int,
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


def _disposition(value: object, *, name: str, allowed: tuple[str, ...]) -> str:
    result = _bounded_string(value, name=name, maximum=64)
    if result not in allowed:
        expected = ", ".join(allowed)
        raise OpportunityIntelligenceValidationError(
            f"{name} must be one of: {expected}"
        )
    return result


@dataclass(frozen=True, init=False)
class WinnerValidationAssessment:
    """Immutable, contextual interpretation of exact P7.6 evidence profiles.

    The two dispositions are caller-authored bounded semantic judgments. They
    are neither scores nor probabilities, and this value does not imply causal
    attribution, approval, a lifecycle transition, or scalability.
    """

    assessment_id: str
    decision_context_id: str
    hypothesis_id: str
    as_of: datetime
    market_test_profile_ids: tuple[str, ...] = field(default_factory=tuple)
    hypothesis_calibration: str = "INCONCLUSIVE"
    winner_validation: str = "INCONCLUSIVE"
    calibration_rationale: str = ""
    validation_rationale: str = ""
    supporting_evidence_refs: tuple[str, ...] = field(default_factory=tuple)
    counter_evidence_refs: tuple[str, ...] = field(default_factory=tuple)
    unresolved_uncertainties: tuple[str, ...] = field(default_factory=tuple)

    def __init__(
        self,
        assessment_id: str,
        decision_context_id: str,
        hypothesis_id: str,
        as_of: datetime,
        market_test_profile_ids: Sequence[str],
        hypothesis_calibration: str,
        winner_validation: str,
        calibration_rationale: str,
        validation_rationale: str,
        supporting_evidence_refs: Sequence[str] = (),
        counter_evidence_refs: Sequence[str] = (),
        unresolved_uncertainties: Sequence[str] = (),
    ) -> None:
        for name, value in (
            ("assessment_id", assessment_id),
            ("decision_context_id", decision_context_id),
            ("hypothesis_id", hypothesis_id),
        ):
            object.__setattr__(
                self,
                name,
                _bounded_string(value, name=name, maximum=_MAX_IDENTIFIER_LENGTH),
            )

        object.__setattr__(self, "as_of", _aware_datetime(as_of, name="as_of"))
        profile_ids = _ordered_strings(
            market_test_profile_ids,
            name="market_test_profile_ids",
            maximum=_MAX_IDENTIFIER_LENGTH,
        )
        if not profile_ids:
            raise OpportunityIntelligenceValidationError(
                "market_test_profile_ids must contain at least one profile id"
            )
        object.__setattr__(self, "market_test_profile_ids", profile_ids)

        calibration = _disposition(
            hypothesis_calibration,
            name="hypothesis_calibration",
            allowed=HYPOTHESIS_CALIBRATION_DISPOSITIONS,
        )
        validation = _disposition(
            winner_validation,
            name="winner_validation",
            allowed=WINNER_VALIDATION_DISPOSITIONS,
        )
        object.__setattr__(self, "hypothesis_calibration", calibration)
        object.__setattr__(self, "winner_validation", validation)

        for name, value in (
            ("calibration_rationale", calibration_rationale),
            ("validation_rationale", validation_rationale),
        ):
            object.__setattr__(
                self,
                name,
                _bounded_string(value, name=name, maximum=_MAX_TEXT_LENGTH),
            )

        supporting = _ordered_strings(
            supporting_evidence_refs,
            name="supporting_evidence_refs",
            maximum=_MAX_REFERENCE_LENGTH,
        )
        counter = _ordered_strings(
            counter_evidence_refs,
            name="counter_evidence_refs",
            maximum=_MAX_REFERENCE_LENGTH,
        )
        uncertainties = _ordered_strings(
            unresolved_uncertainties,
            name="unresolved_uncertainties",
            maximum=_MAX_TEXT_LENGTH,
        )
        object.__setattr__(self, "supporting_evidence_refs", supporting)
        object.__setattr__(self, "counter_evidence_refs", counter)
        object.__setattr__(self, "unresolved_uncertainties", uncertainties)

        if calibration == "ALIGNED" and not supporting:
            raise OpportunityIntelligenceValidationError(
                "ALIGNED hypothesis calibration requires supporting evidence"
            )
        if calibration == "MISALIGNED" and not counter:
            raise OpportunityIntelligenceValidationError(
                "MISALIGNED hypothesis calibration requires counter evidence"
            )
        if calibration == "MIXED" and (not supporting or not counter):
            raise OpportunityIntelligenceValidationError(
                "MIXED hypothesis calibration requires supporting and counter evidence"
            )
        if calibration == "INCONCLUSIVE" and not uncertainties:
            raise OpportunityIntelligenceValidationError(
                "INCONCLUSIVE hypothesis calibration requires unresolved uncertainty"
            )
        if validation == "SUPPORTED" and not supporting:
            raise OpportunityIntelligenceValidationError(
                "SUPPORTED winner validation requires supporting evidence"
            )
        if validation == "CONTRADICTED" and not counter:
            raise OpportunityIntelligenceValidationError(
                "CONTRADICTED winner validation requires counter evidence"
            )
        if validation == "INCONCLUSIVE" and not uncertainties:
            raise OpportunityIntelligenceValidationError(
                "INCONCLUSIVE winner validation requires unresolved uncertainty"
            )

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic JSON-serializable public projection."""
        return {
            "assessment_id": _public_projection_string(
                self.assessment_id, name="assessment_id"
            ),
            "decision_context_id": _public_projection_string(
                self.decision_context_id, name="decision_context_id"
            ),
            "hypothesis_id": _public_projection_string(
                self.hypothesis_id, name="hypothesis_id"
            ),
            "as_of": self.as_of.isoformat(),
            "market_test_profile_ids": list(self.market_test_profile_ids),
            "hypothesis_calibration": self.hypothesis_calibration,
            "winner_validation": self.winner_validation,
            "calibration_rationale": _public_projection_string(
                self.calibration_rationale, name="calibration_rationale"
            ),
            "validation_rationale": _public_projection_string(
                self.validation_rationale, name="validation_rationale"
            ),
            "supporting_evidence_refs": list(self.supporting_evidence_refs),
            "counter_evidence_refs": list(self.counter_evidence_refs),
            "unresolved_uncertainties": list(self.unresolved_uncertainties),
        }


def create_winner_validation_assessment(
    *,
    decision_context: DecisionContext,
    hypothesis: OpportunityHypothesis,
    market_test_profiles: Sequence[MarketTestEvidenceProfile],
    assessment_id: str,
    as_of: datetime,
    hypothesis_calibration: str,
    winner_validation: str,
    calibration_rationale: str,
    validation_rationale: str,
    supporting_evidence_refs: Sequence[str] = (),
    counter_evidence_refs: Sequence[str] = (),
    unresolved_uncertainties: Sequence[str] = (),
) -> WinnerValidationAssessment:
    """Purely construct an assessment bound to exact P7.3 and P7.6 values."""
    if not isinstance(decision_context, DecisionContext):
        raise OpportunityIntelligenceValidationError(
            "decision_context must be a DecisionContext"
        )
    if not isinstance(hypothesis, OpportunityHypothesis):
        raise OpportunityIntelligenceValidationError(
            "hypothesis must be an OpportunityHypothesis"
        )
    if hypothesis.decision_context_id != decision_context.context_id:
        raise OpportunityIntelligenceValidationError(
            "hypothesis decision_context_id must match the supplied DecisionContext"
        )
    if isinstance(market_test_profiles, (str, bytes)) or not isinstance(
        market_test_profiles, Sequence
    ):
        raise OpportunityIntelligenceValidationError(
            "market_test_profiles must be a non-empty ordered collection"
        )
    if not market_test_profiles:
        raise OpportunityIntelligenceValidationError(
            "market_test_profiles must be a non-empty ordered collection"
        )

    profile_ids: list[str] = []
    anchored_refs: set[str] = set()
    represented_dimensions: set[str] = set()
    bound_profiles: list[MarketTestEvidenceProfile] = []
    for index, profile in enumerate(market_test_profiles):
        if not isinstance(profile, MarketTestEvidenceProfile):
            raise OpportunityIntelligenceValidationError(
                f"market_test_profiles[{index}] must be a MarketTestEvidenceProfile"
            )
        if profile.decision_context_id != decision_context.context_id:
            raise OpportunityIntelligenceValidationError(
                f"market_test_profiles[{index}] decision_context_id must match the supplied DecisionContext"
            )
        if profile.hypothesis_id != hypothesis.hypothesis_id:
            raise OpportunityIntelligenceValidationError(
                f"market_test_profiles[{index}] hypothesis_id must match the supplied OpportunityHypothesis"
            )
        profile_ids.append(profile.profile_id)
        bound_profiles.append(profile)
        for dimension in MARKET_TEST_EVIDENCE_DIMENSIONS:
            refs = getattr(profile, dimension)
            if refs:
                represented_dimensions.add(dimension)
                anchored_refs.update(refs)

    if len(set(profile_ids)) != len(profile_ids):
        raise OpportunityIntelligenceValidationError(
            "market_test_profiles must not contain duplicate profile_id values"
        )

    assessment_as_of = _aware_datetime(as_of, name="as_of")
    if any(assessment_as_of < profile.as_of for profile in bound_profiles):
        raise OpportunityIntelligenceValidationError(
            "assessment as_of must not be earlier than any bound profile as_of"
        )

    supporting = _ordered_strings(
        supporting_evidence_refs,
        name="supporting_evidence_refs",
        maximum=_MAX_REFERENCE_LENGTH,
    )
    counter = _ordered_strings(
        counter_evidence_refs,
        name="counter_evidence_refs",
        maximum=_MAX_REFERENCE_LENGTH,
    )
    for name, refs in (
        ("supporting_evidence_refs", supporting),
        ("counter_evidence_refs", counter),
    ):
        unanchored = [ref for ref in refs if ref not in anchored_refs]
        if unanchored:
            raise OpportunityIntelligenceValidationError(
                f"{name} must be anchored to a bound MarketTestEvidenceProfile evidence dimension"
            )

    if (
        winner_validation == "SUPPORTED"
        and represented_dimensions != set(MARKET_TEST_EVIDENCE_DIMENSIONS)
    ):
        raise OpportunityIntelligenceValidationError(
            "SUPPORTED winner validation requires represented evidence across exposure, funnel, economic, and quality dimensions"
        )

    return WinnerValidationAssessment(
        assessment_id=assessment_id,
        decision_context_id=decision_context.context_id,
        hypothesis_id=hypothesis.hypothesis_id,
        as_of=assessment_as_of,
        market_test_profile_ids=profile_ids,
        hypothesis_calibration=hypothesis_calibration,
        winner_validation=winner_validation,
        calibration_rationale=calibration_rationale,
        validation_rationale=validation_rationale,
        supporting_evidence_refs=supporting,
        counter_evidence_refs=counter,
        unresolved_uncertainties=unresolved_uncertainties,
    )
