"""Pure, bounded finding-to-guardrail promotion recommendations."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import re
from typing import Any

from src.aios_bridge.continuity.errors import ContinuityStateValidationError
from src.aios_bridge.review_pipeline import FindingStatus


_IDENTIFIER_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
_CLASS_RE = re.compile(r"\A[A-Z][A-Z0-9_]{0,63}\Z")
_LOW_VALUE_CLASSES = frozenset({"STYLE", "NIT", "TYPO", "FORMATTING"})


class ReviewLearningError(ContinuityStateValidationError):
    """Malformed learning evidence or an unsafe promotion request."""


def _error(message: str) -> ReviewLearningError:
    return ReviewLearningError(message)


class GuardrailPromotionTarget(str, Enum):
    NONE = "NONE"
    REGRESSION_TEST = "REGRESSION_TEST"
    STATIC_RULE = "STATIC_RULE"
    ARCHITECTURE_INVARIANT = "ARCHITECTURE_INVARIANT"
    TASK_TEMPLATE_RULE = "TASK_TEMPLATE_RULE"
    ADR_CANDIDATE = "ADR_CANDIDATE"


_TARGET_PRIORITY = (
    GuardrailPromotionTarget.REGRESSION_TEST,
    GuardrailPromotionTarget.STATIC_RULE,
    GuardrailPromotionTarget.ARCHITECTURE_INVARIANT,
    GuardrailPromotionTarget.TASK_TEMPLATE_RULE,
    GuardrailPromotionTarget.ADR_CANDIDATE,
)


@dataclass(frozen=True, slots=True)
class PromotionFindingEvidence:
    finding_id: str
    normalized_finding_class: str
    guardrail_key: str
    severity: str
    status: FindingStatus
    allowed_targets: tuple[GuardrailPromotionTarget, ...]
    regression_evidence: bool = False

    def __post_init__(self) -> None:
        for name in ("finding_id", "guardrail_key"):
            value = getattr(self, name)
            if type(value) is not str or _IDENTIFIER_RE.fullmatch(value) is None:
                raise _error(f"{name} must be a bounded canonical identifier")
        for name in ("normalized_finding_class", "severity"):
            value = getattr(self, name)
            if type(value) is not str or _CLASS_RE.fullmatch(value) is None:
                raise _error(f"{name} must be a canonical uppercase token")
        if type(self.status) is not FindingStatus:
            raise _error("status must reuse the exact FindingStatus lifecycle")
        if type(self.allowed_targets) is not tuple or not self.allowed_targets:
            raise _error("allowed_targets must be a non-empty exact tuple")
        if any(type(item) is not GuardrailPromotionTarget for item in self.allowed_targets):
            raise _error("allowed_targets must contain only closed promotion targets")
        if GuardrailPromotionTarget.NONE in self.allowed_targets:
            raise _error("NONE is a decision, not an allowed adoption target")
        if len(set(self.allowed_targets)) != len(self.allowed_targets):
            raise _error("allowed_targets must be duplicate-free")
        if type(self.regression_evidence) is not bool:
            raise _error("regression_evidence must be an exact bool")
        if self.status is FindingStatus.REOPENED and not self.regression_evidence:
            raise _error("REOPENED promotion evidence requires an evidence-backed regression")
        if self.status not in {FindingStatus.CLOSED, FindingStatus.REOPENED}:
            raise _error("only CLOSED or evidence-backed REOPENED findings may be promoted")

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed_targets": [item.value for item in self.allowed_targets],
            "finding_id": self.finding_id,
            "guardrail_key": self.guardrail_key,
            "normalized_finding_class": self.normalized_finding_class,
            "regression_evidence": self.regression_evidence,
            "severity": self.severity,
            "status": self.status.value,
        }


@dataclass(frozen=True, slots=True)
class GuardrailPromotionRecommendation:
    normalized_finding_class: str
    guardrail_key: str
    recurrence_count: int
    evidence_finding_ids: tuple[str, ...]
    target: GuardrailPromotionTarget
    authority_expanded: bool = False
    repository_mutation_authorized: bool = False

    def __post_init__(self) -> None:
        if type(self.normalized_finding_class) is not str or _CLASS_RE.fullmatch(self.normalized_finding_class) is None:
            raise _error("normalized_finding_class must be a canonical token")
        if type(self.guardrail_key) is not str or _IDENTIFIER_RE.fullmatch(self.guardrail_key) is None:
            raise _error("guardrail_key must be a bounded canonical identifier")
        if type(self.recurrence_count) is not int or self.recurrence_count < 1 or self.recurrence_count > 128:
            raise _error("recurrence_count must be bounded")
        if type(self.evidence_finding_ids) is not tuple or len(self.evidence_finding_ids) != self.recurrence_count:
            raise _error("evidence_finding_ids must exactly support recurrence_count")
        if tuple(sorted(set(self.evidence_finding_ids))) != self.evidence_finding_ids:
            raise _error("evidence_finding_ids must be sorted and duplicate-free")
        if type(self.target) is not GuardrailPromotionTarget:
            raise _error("target must be a closed promotion target")
        if self.authority_expanded is not False or self.repository_mutation_authorized is not False:
            raise _error("promotion recommendations never mutate or expand authority")

    def to_dict(self) -> dict[str, Any]:
        return {
            "authority_expanded": self.authority_expanded,
            "evidence_finding_ids": list(self.evidence_finding_ids),
            "guardrail_key": self.guardrail_key,
            "normalized_finding_class": self.normalized_finding_class,
            "recurrence_count": self.recurrence_count,
            "repository_mutation_authorized": self.repository_mutation_authorized,
            "target": self.target.value,
        }

    def canonical_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    def fingerprint(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


def recommend_guardrail_promotion(
    evidence: tuple[PromotionFindingEvidence, ...],
) -> GuardrailPromotionRecommendation:
    """Produce one deterministic recommendation from normalized machine evidence."""
    if type(evidence) is not tuple or not evidence:
        raise _error("evidence must be a non-empty exact tuple")
    if any(type(item) is not PromotionFindingEvidence for item in evidence):
        raise _error("evidence must contain exact PromotionFindingEvidence values")
    ids = tuple(sorted(item.finding_id for item in evidence))
    if len(set(ids)) != len(ids):
        raise _error("promotion evidence finding IDs must be duplicate-free")
    classes = {item.normalized_finding_class for item in evidence}
    keys = {item.guardrail_key for item in evidence}
    if len(classes) != 1 or len(keys) != 1:
        raise _error("raw prose similarity is insufficient; normalized class and guardrail key must match")
    finding_class = next(iter(classes))
    guardrail_key = next(iter(keys))
    recurrence = len(evidence)
    severities = {item.severity for item in evidence}
    common_targets = set(evidence[0].allowed_targets)
    for item in evidence[1:]:
        common_targets.intersection_update(item.allowed_targets)

    threshold = 2 if severities & {"CRITICAL", "HIGH"} else 3
    target = GuardrailPromotionTarget.NONE
    if finding_class not in _LOW_VALUE_CLASSES and recurrence >= threshold:
        target = next((item for item in _TARGET_PRIORITY if item in common_targets), GuardrailPromotionTarget.NONE)
    return GuardrailPromotionRecommendation(
        normalized_finding_class=finding_class,
        guardrail_key=guardrail_key,
        recurrence_count=recurrence,
        evidence_finding_ids=ids,
        target=target,
    )


__all__ = [
    "GuardrailPromotionRecommendation", "GuardrailPromotionTarget", "PromotionFindingEvidence",
    "ReviewLearningError", "recommend_guardrail_promotion",
]
