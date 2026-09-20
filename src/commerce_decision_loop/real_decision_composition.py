"""P8.0 bounded composition of already-owned commerce decision artifacts.

This module owns only exact cross-domain lineage composition and a deterministic
representation-gap view.  It does not own or transmit the evidence, intelligence,
decision, approval, action, outcome, product-truth, roadmap, or domain semantics of
the values it composes.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.commerce_opportunity_intelligence import (
    DecisionContext,
    MarketTestEvidenceProfile,
    OpportunityHypothesis,
    TikTokAffiliateEvidenceProfile,
    ValueOfInformationPlan,
    WinnerValidationAssessment,
)


COMMERCE_DECISION_LOOP_P8_0 = "COMMERCE_DECISION_LOOP_P8_0"

DECISION_LOOP_OPTIONAL_COMPONENTS: tuple[str, ...] = (
    "TIKTOK_AFFILIATE_EVIDENCE",
    "VALUE_OF_INFORMATION_PLAN",
    "DECISION_AUTHORIZATION",
    "MARKET_TEST_EVIDENCE",
    "WINNER_VALIDATION_ASSESSMENT",
)

_MAX_IDENTIFIER_LENGTH = 256
_MAX_REFERENCE_LENGTH = 512
_FACTORY_CONSTRUCTION_TOKEN = object()

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


class _CommerceDecisionLoopValidationError(ValueError):
    """A P8.0 composition value failed deterministic validation."""


def _bounded_public_string(value: object, *, name: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise _CommerceDecisionLoopValidationError(f"{name} must be a string")
    if not value.strip():
        raise _CommerceDecisionLoopValidationError(f"{name} must not be blank")
    if "\r" in value or "\n" in value:
        raise _CommerceDecisionLoopValidationError(
            f"{name} must be a single-line string"
        )
    if len(value) > maximum:
        raise _CommerceDecisionLoopValidationError(
            f"{name} must contain at most {maximum} characters"
        )
    for forbidden_class, pattern in _FORBIDDEN_PUBLIC_STRING_PATTERNS:
        if pattern.search(value):
            raise _CommerceDecisionLoopValidationError(
                f"{name} must not contain {forbidden_class}"
            )
    return value


def _aware_datetime(value: object, *, name: str) -> datetime:
    if not isinstance(value, datetime):
        raise _CommerceDecisionLoopValidationError(f"{name} must be a datetime")
    try:
        offset = value.utcoffset()
    except (OverflowError, ValueError) as exc:
        raise _CommerceDecisionLoopValidationError(
            f"{name} must have a valid timezone offset"
        ) from exc
    if value.tzinfo is None or offset is None:
        raise _CommerceDecisionLoopValidationError(
            f"{name} must be timezone-aware"
        )
    return value


@dataclass(frozen=True, init=False)
class CommerceDecisionLoopCase:
    """Immutable lineage-only composition for one caller-identified case.

    Represented and unrepresented components are only a partition of the five
    optional inputs.  They are not a score, confidence, readiness, lifecycle,
    recommendation, authorization, or automatic successor selection.
    """

    case_id: str
    decision_context_id: str
    hypothesis_id: str
    as_of: datetime
    affiliate_evidence_profile_id: str | None = None
    voi_plan_id: str | None = None
    decision_authorization_ref: str | None = None
    market_test_profile_ids: tuple[str, ...] = field(default_factory=tuple)
    winner_validation_assessment_id: str | None = None
    represented_components: tuple[str, ...] = field(default_factory=tuple)
    unrepresented_components: tuple[str, ...] = field(default_factory=tuple)

    def __init__(
        self,
        *,
        case_id: str,
        decision_context_id: str,
        hypothesis_id: str,
        as_of: datetime,
        affiliate_evidence_profile_id: str | None = None,
        voi_plan_id: str | None = None,
        decision_authorization_ref: str | None = None,
        market_test_profile_ids: Sequence[str] = (),
        winner_validation_assessment_id: str | None = None,
        represented_components: Sequence[str] = (),
        unrepresented_components: Sequence[str] = (),
        _factory_construction_token: object | None = None,
    ) -> None:
        if _factory_construction_token is not _FACTORY_CONSTRUCTION_TOKEN:
            raise _CommerceDecisionLoopValidationError(
                "CommerceDecisionLoopCase must be constructed by "
                "create_commerce_decision_loop_case"
            )

        object.__setattr__(self, "case_id", _bounded_public_string(
            case_id, name="case_id", maximum=_MAX_IDENTIFIER_LENGTH
        ))
        object.__setattr__(self, "decision_context_id", _bounded_public_string(
            decision_context_id, name="decision_context_id", maximum=_MAX_IDENTIFIER_LENGTH
        ))
        object.__setattr__(self, "hypothesis_id", _bounded_public_string(
            hypothesis_id, name="hypothesis_id", maximum=_MAX_IDENTIFIER_LENGTH
        ))
        object.__setattr__(self, "as_of", _aware_datetime(as_of, name="as_of"))

        for name, value, maximum in (
            ("affiliate_evidence_profile_id", affiliate_evidence_profile_id, _MAX_IDENTIFIER_LENGTH),
            ("voi_plan_id", voi_plan_id, _MAX_IDENTIFIER_LENGTH),
            ("decision_authorization_ref", decision_authorization_ref, _MAX_REFERENCE_LENGTH),
            ("winner_validation_assessment_id", winner_validation_assessment_id, _MAX_IDENTIFIER_LENGTH),
        ):
            object.__setattr__(
                self,
                name,
                None if value is None else _bounded_public_string(
                    value, name=name, maximum=maximum
                ),
            )

        profile_ids = tuple(
            _bounded_public_string(
                item,
                name=f"market_test_profile_ids[{index}]",
                maximum=_MAX_IDENTIFIER_LENGTH,
            )
            for index, item in enumerate(market_test_profile_ids)
        )
        if len(set(profile_ids)) != len(profile_ids):
            raise _CommerceDecisionLoopValidationError(
                "market_test_profile_ids must not contain duplicate values"
            )
        object.__setattr__(self, "market_test_profile_ids", profile_ids)

        represented = tuple(represented_components)
        unrepresented = tuple(unrepresented_components)
        if (
            represented
            != tuple(
                component
                for component in DECISION_LOOP_OPTIONAL_COMPONENTS
                if component in represented
            )
            or unrepresented
            != tuple(
                component
                for component in DECISION_LOOP_OPTIONAL_COMPONENTS
                if component in unrepresented
            )
            or set(represented).intersection(unrepresented)
            or set(represented).union(unrepresented)
            != set(DECISION_LOOP_OPTIONAL_COMPONENTS)
        ):
            raise _CommerceDecisionLoopValidationError(
                "component projections must exactly partition the canonical components"
            )
        object.__setattr__(self, "represented_components", represented)
        object.__setattr__(self, "unrepresented_components", unrepresented)

    def to_dict(self) -> dict[str, Any]:
        """Return the deterministic, bounded, JSON-serializable public projection."""

        return {
            "case_id": _bounded_public_string(
                self.case_id, name="case_id", maximum=_MAX_IDENTIFIER_LENGTH
            ),
            "decision_context_id": _bounded_public_string(
                self.decision_context_id,
                name="decision_context_id",
                maximum=_MAX_IDENTIFIER_LENGTH,
            ),
            "hypothesis_id": _bounded_public_string(
                self.hypothesis_id,
                name="hypothesis_id",
                maximum=_MAX_IDENTIFIER_LENGTH,
            ),
            "as_of": self.as_of.isoformat(),
            "affiliate_evidence_profile_id": self.affiliate_evidence_profile_id,
            "voi_plan_id": self.voi_plan_id,
            "decision_authorization_ref": self.decision_authorization_ref,
            "market_test_profile_ids": list(self.market_test_profile_ids),
            "winner_validation_assessment_id": self.winner_validation_assessment_id,
            "represented_components": list(self.represented_components),
            "unrepresented_components": list(self.unrepresented_components),
        }


def create_commerce_decision_loop_case(
    *,
    case_id: str,
    decision_context: DecisionContext,
    hypothesis: OpportunityHypothesis,
    as_of: datetime,
    affiliate_evidence_profile: TikTokAffiliateEvidenceProfile | None = None,
    voi_plan: ValueOfInformationPlan | None = None,
    decision_authorization_ref: str | None = None,
    market_test_profiles: Sequence[MarketTestEvidenceProfile] = (),
    winner_validation_assessment: WinnerValidationAssessment | None = None,
) -> CommerceDecisionLoopCase:
    """Purely compose exact P7 values without acquiring any input authority."""

    if not isinstance(decision_context, DecisionContext):
        raise _CommerceDecisionLoopValidationError(
            "decision_context must be a DecisionContext"
        )
    if not isinstance(hypothesis, OpportunityHypothesis):
        raise _CommerceDecisionLoopValidationError(
            "hypothesis must be an OpportunityHypothesis"
        )
    if hypothesis.decision_context_id != decision_context.context_id:
        raise _CommerceDecisionLoopValidationError(
            "hypothesis decision_context_id must match the supplied DecisionContext"
        )

    case_as_of = _aware_datetime(as_of, name="as_of")
    if case_as_of < decision_context.as_of:
        raise _CommerceDecisionLoopValidationError(
            "case as_of must not be earlier than DecisionContext as_of"
        )
    if case_as_of < hypothesis.created_at:
        raise _CommerceDecisionLoopValidationError(
            "case as_of must not be earlier than OpportunityHypothesis created_at"
        )

    if affiliate_evidence_profile is not None:
        if not isinstance(affiliate_evidence_profile, TikTokAffiliateEvidenceProfile):
            raise _CommerceDecisionLoopValidationError(
                "affiliate_evidence_profile must be a TikTokAffiliateEvidenceProfile"
            )
        if affiliate_evidence_profile.decision_context_id != decision_context.context_id:
            raise _CommerceDecisionLoopValidationError(
                "affiliate evidence decision_context_id must match the supplied DecisionContext"
            )
        if affiliate_evidence_profile.hypothesis_id != hypothesis.hypothesis_id:
            raise _CommerceDecisionLoopValidationError(
                "affiliate evidence hypothesis_id must match the supplied OpportunityHypothesis"
            )
        if case_as_of < affiliate_evidence_profile.as_of:
            raise _CommerceDecisionLoopValidationError(
                "case as_of must not be earlier than affiliate evidence as_of"
            )

    if voi_plan is not None:
        if not isinstance(voi_plan, ValueOfInformationPlan):
            raise _CommerceDecisionLoopValidationError(
                "voi_plan must be a ValueOfInformationPlan"
            )
        if affiliate_evidence_profile is None:
            raise _CommerceDecisionLoopValidationError(
                "voi_plan requires affiliate_evidence_profile"
            )
        if voi_plan.decision_context_id != decision_context.context_id:
            raise _CommerceDecisionLoopValidationError(
                "VOI plan decision_context_id must match the supplied DecisionContext"
            )
        if voi_plan.hypothesis_id != hypothesis.hypothesis_id:
            raise _CommerceDecisionLoopValidationError(
                "VOI plan hypothesis_id must match the supplied OpportunityHypothesis"
            )
        if voi_plan.profile_id != affiliate_evidence_profile.profile_id:
            raise _CommerceDecisionLoopValidationError(
                "VOI plan profile_id must match the supplied affiliate evidence profile"
            )
        if case_as_of < voi_plan.as_of:
            raise _CommerceDecisionLoopValidationError(
                "case as_of must not be earlier than VOI plan as_of"
            )

    authorization_ref = None
    if decision_authorization_ref is not None:
        authorization_ref = _bounded_public_string(
            decision_authorization_ref,
            name="decision_authorization_ref",
            maximum=_MAX_REFERENCE_LENGTH,
        )

    if isinstance(market_test_profiles, (str, bytes)) or not isinstance(
        market_test_profiles, Sequence
    ):
        raise _CommerceDecisionLoopValidationError(
            "market_test_profiles must be an ordered collection"
        )
    profiles = tuple(market_test_profiles)
    if profiles and authorization_ref is None:
        raise _CommerceDecisionLoopValidationError(
            "market_test_profiles require decision_authorization_ref"
        )

    profile_ids: list[str] = []
    for index, profile in enumerate(profiles):
        if not isinstance(profile, MarketTestEvidenceProfile):
            raise _CommerceDecisionLoopValidationError(
                f"market_test_profiles[{index}] must be a MarketTestEvidenceProfile"
            )
        if profile.decision_context_id != decision_context.context_id:
            raise _CommerceDecisionLoopValidationError(
                f"market_test_profiles[{index}] decision_context_id must match the supplied DecisionContext"
            )
        if profile.hypothesis_id != hypothesis.hypothesis_id:
            raise _CommerceDecisionLoopValidationError(
                f"market_test_profiles[{index}] hypothesis_id must match the supplied OpportunityHypothesis"
            )
        if case_as_of < profile.as_of:
            raise _CommerceDecisionLoopValidationError(
                f"case as_of must not be earlier than market_test_profiles[{index}] as_of"
            )
        if profile.authorization_ref != authorization_ref:
            raise _CommerceDecisionLoopValidationError(
                f"market_test_profiles[{index}] authorization_ref must exactly match decision_authorization_ref"
            )
        profile_ids.append(profile.profile_id)
    if len(set(profile_ids)) != len(profile_ids):
        raise _CommerceDecisionLoopValidationError(
            "market_test_profiles must not contain duplicate profile_id values"
        )

    if winner_validation_assessment is not None:
        if not isinstance(winner_validation_assessment, WinnerValidationAssessment):
            raise _CommerceDecisionLoopValidationError(
                "winner_validation_assessment must be a WinnerValidationAssessment"
            )
        if not profiles:
            raise _CommerceDecisionLoopValidationError(
                "winner_validation_assessment requires market_test_profiles"
            )
        if winner_validation_assessment.decision_context_id != decision_context.context_id:
            raise _CommerceDecisionLoopValidationError(
                "winner assessment decision_context_id must match the supplied DecisionContext"
            )
        if winner_validation_assessment.hypothesis_id != hypothesis.hypothesis_id:
            raise _CommerceDecisionLoopValidationError(
                "winner assessment hypothesis_id must match the supplied OpportunityHypothesis"
            )
        if winner_validation_assessment.market_test_profile_ids != tuple(profile_ids):
            raise _CommerceDecisionLoopValidationError(
                "winner assessment market_test_profile_ids must exactly match bound profile order"
            )
        if case_as_of < winner_validation_assessment.as_of:
            raise _CommerceDecisionLoopValidationError(
                "case as_of must not be earlier than winner assessment as_of"
            )

    presence = {
        "TIKTOK_AFFILIATE_EVIDENCE": affiliate_evidence_profile is not None,
        "VALUE_OF_INFORMATION_PLAN": voi_plan is not None,
        "DECISION_AUTHORIZATION": authorization_ref is not None,
        "MARKET_TEST_EVIDENCE": bool(profiles),
        "WINNER_VALIDATION_ASSESSMENT": winner_validation_assessment is not None,
    }
    represented = tuple(
        component for component in DECISION_LOOP_OPTIONAL_COMPONENTS if presence[component]
    )
    unrepresented = tuple(
        component for component in DECISION_LOOP_OPTIONAL_COMPONENTS if not presence[component]
    )

    return CommerceDecisionLoopCase(
        case_id=case_id,
        decision_context_id=decision_context.context_id,
        hypothesis_id=hypothesis.hypothesis_id,
        as_of=case_as_of,
        affiliate_evidence_profile_id=(
            affiliate_evidence_profile.profile_id
            if affiliate_evidence_profile is not None
            else None
        ),
        voi_plan_id=voi_plan.plan_id if voi_plan is not None else None,
        decision_authorization_ref=authorization_ref,
        market_test_profile_ids=profile_ids,
        winner_validation_assessment_id=(
            winner_validation_assessment.assessment_id
            if winner_validation_assessment is not None
            else None
        ),
        represented_components=represented,
        unrepresented_components=unrepresented,
        _factory_construction_token=_FACTORY_CONSTRUCTION_TOKEN,
    )
