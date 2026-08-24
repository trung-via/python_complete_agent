"""Provider-neutral P0 validation ownership, plan, and telemetry contracts."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
import re
from typing import Any, Sequence

from src.aios_bridge.continuity.errors import ContinuityStateValidationError


class ValidationTier(str, Enum):
    T0_MICRO = "T0_MICRO"
    T1_TARGETED_IMPACT = "T1_TARGETED_IMPACT"
    T2_FULL_CANONICAL = "T2_FULL_CANONICAL"
    T3_RELEASE = "T3_RELEASE"


class ValidationOwner(str, Enum):
    EXECUTOR = "EXECUTOR"
    CERTIFICATION_BOUNDARY = "CERTIFICATION_BOUNDARY"
    RELEASE_BOUNDARY = "RELEASE_BOUNDARY"


class ValidationProfile(str, Enum):
    CONTROL_PLANE_STRICT_COMPAT = "CONTROL_PLANE_STRICT_COMPAT"


_CANONICAL_OWNERS = {
    ValidationTier.T0_MICRO: ValidationOwner.EXECUTOR,
    ValidationTier.T1_TARGETED_IMPACT: ValidationOwner.EXECUTOR,
    ValidationTier.T2_FULL_CANONICAL: ValidationOwner.CERTIFICATION_BOUNDARY,
    ValidationTier.T3_RELEASE: ValidationOwner.RELEASE_BOUNDARY,
}
_ROADMAP_BINDING_MARKER = "ROADMAP_BINDING_JSON:"
_LEAN_ROADMAP_ID = "AIOS-BRIDGE-LEAN-EXECUTION"
_FULL_SUITE_RE = re.compile(
    r"(?:^|\s)(?:python(?:\.exe)?\s+-m\s+)?pytest\s+['\"]?tests/?['\"]?(?=\s|$)",
    re.IGNORECASE,
)


def _error(message: str) -> ContinuityStateValidationError:
    return ContinuityStateValidationError(message)


def validation_owner(tier: ValidationTier) -> ValidationOwner:
    if type(tier) is not ValidationTier:
        raise _error("tier must be an exact ValidationTier")
    return _CANONICAL_OWNERS[tier]


@dataclass(frozen=True)
class ValidationPlan:
    profile_id: ValidationProfile
    executor_test_tiers: tuple[ValidationTier, ...]
    certification_test_tiers: tuple[ValidationTier, ...]
    diff_check_required: bool
    expected_full_suite_execution_count: int

    def __post_init__(self) -> None:
        if type(self.profile_id) is not ValidationProfile:
            raise _error("profile_id must be an exact ValidationProfile")
        for name, tiers in (
            ("executor_test_tiers", self.executor_test_tiers),
            ("certification_test_tiers", self.certification_test_tiers),
        ):
            if type(tiers) is not tuple or any(type(tier) is not ValidationTier for tier in tiers):
                raise _error(f"{name} must be an exact tuple of ValidationTier values")
            if len(set(tiers)) != len(tiers):
                raise _error(f"{name} must not contain duplicate tiers")
        if set(self.executor_test_tiers) & set(self.certification_test_tiers):
            raise _error("validation tiers must have exactly one execution-plan owner")
        expected_executor = {ValidationTier.T0_MICRO, ValidationTier.T1_TARGETED_IMPACT}
        if set(self.executor_test_tiers) != expected_executor:
            raise _error("T0/T1 must be owned exactly by the executor")
        if self.certification_test_tiers != (ValidationTier.T2_FULL_CANONICAL,):
            raise _error("exactly one certification boundary must own T2")
        if type(self.diff_check_required) is not bool:
            raise _error("diff_check_required must be an exact bool")
        if type(self.expected_full_suite_execution_count) is not int:
            raise _error("expected_full_suite_execution_count must be an exact integer")
        if self.expected_full_suite_execution_count != 1:
            raise _error("strict compatibility requires exactly one full-suite execution")

    def to_dict(self) -> dict[str, Any]:
        return {
            "certification_test_tiers": [tier.value for tier in self.certification_test_tiers],
            "diff_check_required": self.diff_check_required,
            "executor_test_tiers": [tier.value for tier in self.executor_test_tiers],
            "expected_full_suite_execution_count": self.expected_full_suite_execution_count,
            "profile_id": self.profile_id.value,
        }

    @classmethod
    def from_dict(cls, data: object) -> "ValidationPlan":
        if type(data) is not dict or set(data) != {
            "profile_id",
            "executor_test_tiers",
            "certification_test_tiers",
            "diff_check_required",
            "expected_full_suite_execution_count",
        }:
            raise _error("ValidationPlan must contain the exact bounded field set")
        try:
            return cls(
                profile_id=ValidationProfile(data["profile_id"]),
                executor_test_tiers=tuple(ValidationTier(item) for item in data["executor_test_tiers"]),
                certification_test_tiers=tuple(
                    ValidationTier(item) for item in data["certification_test_tiers"]
                ),
                diff_check_required=data["diff_check_required"],
                expected_full_suite_execution_count=data["expected_full_suite_execution_count"],
            )
        except (TypeError, ValueError) as exc:
            raise _error(f"Malformed ValidationPlan: {exc}") from exc


CONTROL_PLANE_STRICT_COMPAT_PLAN = ValidationPlan(
    profile_id=ValidationProfile.CONTROL_PLANE_STRICT_COMPAT,
    executor_test_tiers=(
        ValidationTier.T0_MICRO,
        ValidationTier.T1_TARGETED_IMPACT,
    ),
    certification_test_tiers=(ValidationTier.T2_FULL_CANONICAL,),
    diff_check_required=True,
    expected_full_suite_execution_count=1,
)


def validation_plan_for_task(task_content: str) -> ValidationPlan | None:
    """Resolve P0 semantics from the exact roadmap binding; legacy tasks stay unchanged."""
    if type(task_content) is not str:
        raise _error("task_content must be exact text")
    values = [
        line[len(_ROADMAP_BINDING_MARKER) :].strip()
        for line in task_content.splitlines()
        if line.startswith(_ROADMAP_BINDING_MARKER)
    ]
    if not values:
        return None
    if len(values) != 1:
        raise _error("Task must contain at most one ROADMAP_BINDING_JSON marker")
    try:
        binding = json.loads(values[0])
    except (TypeError, ValueError) as exc:
        raise _error(f"Malformed roadmap binding while resolving validation plan: {exc}") from exc
    if type(binding) is not dict:
        raise _error("Roadmap binding must be a JSON object")
    if binding.get("roadmap_id") != _LEAN_ROADMAP_ID:
        return None
    return CONTROL_PLANE_STRICT_COMPAT_PLAN


def classify_validation_command(command: str) -> ValidationTier:
    if type(command) is not str or not command.strip():
        raise _error("validation command must be exact non-empty text")
    normalized = command.replace("\\", "/")
    if _FULL_SUITE_RE.search(normalized) and not re.search(r"tests/[^\s'\"]+", normalized):
        return ValidationTier.T2_FULL_CANONICAL
    return ValidationTier.T1_TARGETED_IMPACT


def executor_commands_for_plan(
    commands: Sequence[str], plan: ValidationPlan
) -> tuple[str, ...]:
    """Drop legacy T2 requests when the certification boundary already owns T2."""
    if isinstance(commands, (str, bytes)) or not isinstance(commands, Sequence):
        raise _error("commands must be a sequence of command strings")
    if type(plan) is not ValidationPlan:
        raise _error("plan must be an exact ValidationPlan")
    retained: list[str] = []
    for command in commands:
        tier = classify_validation_command(command)
        if tier in plan.executor_test_tiers:
            retained.append(command)
        elif tier not in plan.certification_test_tiers:
            raise _error("validation ownership is ambiguous; strict certification retained")
    return tuple(retained)


@dataclass(frozen=True)
class ValidationEvidence:
    task_id: str
    action: str
    executor_id: str
    validation_profile: ValidationProfile
    full_suite_execution_count: int
    expected_full_suite_execution_count: int
    targeted_test_execution_count: int
    full_suite_duration_seconds: float | None = None
    targeted_test_duration_seconds: float | None = None

    def __post_init__(self) -> None:
        if type(self.task_id) is not str or not re.fullmatch(r"TASK-\d+", self.task_id):
            raise _error("task_id must match exact TASK-<digits>")
        if self.action not in {"RUN", "FIX"}:
            raise _error("action must be exact RUN or FIX")
        if type(self.executor_id) is not str or not re.fullmatch(
            r"[a-z0-9]+(?:[a-z0-9._\-:]+)*", self.executor_id
        ):
            raise _error("executor_id must be a bounded provider-neutral canonical ID")
        if type(self.validation_profile) is not ValidationProfile:
            raise _error("validation_profile must be an exact ValidationProfile")
        for name in (
            "full_suite_execution_count",
            "expected_full_suite_execution_count",
            "targeted_test_execution_count",
        ):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise _error(f"{name} must be an exact non-negative integer")
        for name in ("full_suite_duration_seconds", "targeted_test_duration_seconds"):
            value = getattr(self, name)
            if value is not None and (type(value) not in {int, float} or value < 0):
                raise _error(f"{name} must be unknown or a non-negative observed duration")

    @property
    def validation_duplication_detected(self) -> bool:
        return self.full_suite_execution_count > self.expected_full_suite_execution_count

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "executor_id": self.executor_id,
            "expected_full_suite_execution_count": self.expected_full_suite_execution_count,
            "full_suite_duration_seconds": self.full_suite_duration_seconds,
            "full_suite_execution_count": self.full_suite_execution_count,
            "targeted_test_duration_seconds": self.targeted_test_duration_seconds,
            "targeted_test_execution_count": self.targeted_test_execution_count,
            "task_id": self.task_id,
            "validation_duplication_detected": self.validation_duplication_detected,
            "validation_profile": self.validation_profile.value,
        }


def require_certification_for_publication(
    plan: ValidationPlan,
    evidence: ValidationEvidence,
    *,
    full_suite_succeeded: bool,
) -> None:
    if type(plan) is not ValidationPlan or type(evidence) is not ValidationEvidence:
        raise _error("publication certification requires exact plan and evidence")
    if evidence.validation_profile is not plan.profile_id:
        raise _error("validation evidence profile does not match the plan")
    if evidence.expected_full_suite_execution_count != plan.expected_full_suite_execution_count:
        raise _error("validation evidence expected count does not match the plan")
    if evidence.validation_duplication_detected:
        raise _error("VALIDATION_DUPLICATION_DETECTED")
    if not full_suite_succeeded:
        raise _error("failed T2 cannot publish")
    if evidence.full_suite_execution_count != plan.expected_full_suite_execution_count:
        raise _error("full canonical certification was not executed exactly once")


__all__ = [
    "CONTROL_PLANE_STRICT_COMPAT_PLAN",
    "ValidationEvidence",
    "ValidationOwner",
    "ValidationPlan",
    "ValidationProfile",
    "ValidationTier",
    "classify_validation_command",
    "executor_commands_for_plan",
    "require_certification_for_publication",
    "validation_owner",
    "validation_plan_for_task",
]
