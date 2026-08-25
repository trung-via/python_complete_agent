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
    CONTROL_PLANE_STRICT = "CONTROL_PLANE_STRICT"
    PRODUCT_DELIVERY_FAST = "PRODUCT_DELIVERY_FAST"


class ExecutorAdHocT2Observability(str, Enum):
    OBSERVED = "OBSERVED"
    UNAVAILABLE = "UNAVAILABLE"


_CANONICAL_OWNERS = {
    ValidationTier.T0_MICRO: ValidationOwner.EXECUTOR,
    ValidationTier.T1_TARGETED_IMPACT: ValidationOwner.EXECUTOR,
    ValidationTier.T2_FULL_CANONICAL: ValidationOwner.CERTIFICATION_BOUNDARY,
    ValidationTier.T3_RELEASE: ValidationOwner.RELEASE_BOUNDARY,
}
_ROADMAP_BINDING_MARKER = "ROADMAP_BINDING_JSON:"
_VALIDATION_PROFILE_MARKER = "VALIDATION_PROFILE:"
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
        if self.profile_id is ValidationProfile.PRODUCT_DELIVERY_FAST:
            raise _error(
                "PRODUCT_DELIVERY_FAST admission blocked: missing "
                "capability-batch/integration-lane authority"
            )
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
            raise _error("strict validation requires exactly one full-suite execution")

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

CONTROL_PLANE_STRICT_PLAN = ValidationPlan(
    profile_id=ValidationProfile.CONTROL_PLANE_STRICT,
    executor_test_tiers=(
        ValidationTier.T0_MICRO,
        ValidationTier.T1_TARGETED_IMPACT,
    ),
    certification_test_tiers=(ValidationTier.T2_FULL_CANONICAL,),
    diff_check_required=True,
    expected_full_suite_execution_count=1,
)


@dataclass(frozen=True)
class ValidationProfilePolicy:
    """Closed P1 profile metadata; admission authority remains external."""

    profile_id: ValidationProfile
    task_level_t0_t1_required: bool
    task_level_review_first_semantic_review_required: bool
    task_level_final_t2: bool
    capability_level_final_t2_required: bool
    diff_check_required: bool
    known_impact_required: bool
    direct_task_main_merge_allowed: bool
    capability_batch_authority_required: bool
    integration_lane_authority_required: bool
    executable_without_capability_authority: bool

    def __post_init__(self) -> None:
        if type(self.profile_id) is not ValidationProfile:
            raise _error("profile_id must be an exact ValidationProfile")
        for name in (
            "task_level_t0_t1_required",
            "task_level_review_first_semantic_review_required",
            "task_level_final_t2",
            "capability_level_final_t2_required",
            "diff_check_required",
            "known_impact_required",
            "direct_task_main_merge_allowed",
            "capability_batch_authority_required",
            "integration_lane_authority_required",
            "executable_without_capability_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise _error(f"{name} must be an exact bool")

    def to_dict(self) -> dict[str, bool | str]:
        return {
            "capability_batch_authority_required": self.capability_batch_authority_required,
            "capability_level_final_t2_required": self.capability_level_final_t2_required,
            "diff_check_required": self.diff_check_required,
            "direct_task_main_merge_allowed": self.direct_task_main_merge_allowed,
            "executable_without_capability_authority": (
                self.executable_without_capability_authority
            ),
            "integration_lane_authority_required": self.integration_lane_authority_required,
            "known_impact_required": self.known_impact_required,
            "profile_id": self.profile_id.value,
            "task_level_final_t2": self.task_level_final_t2,
            "task_level_review_first_semantic_review_required": (
                self.task_level_review_first_semantic_review_required
            ),
            "task_level_t0_t1_required": self.task_level_t0_t1_required,
        }


CONTROL_PLANE_STRICT_COMPAT_POLICY = ValidationProfilePolicy(
    profile_id=ValidationProfile.CONTROL_PLANE_STRICT_COMPAT,
    task_level_t0_t1_required=True,
    task_level_review_first_semantic_review_required=True,
    task_level_final_t2=True,
    capability_level_final_t2_required=False,
    diff_check_required=True,
    known_impact_required=False,
    direct_task_main_merge_allowed=True,
    capability_batch_authority_required=False,
    integration_lane_authority_required=False,
    executable_without_capability_authority=True,
)

CONTROL_PLANE_STRICT_POLICY = ValidationProfilePolicy(
    profile_id=ValidationProfile.CONTROL_PLANE_STRICT,
    task_level_t0_t1_required=True,
    task_level_review_first_semantic_review_required=True,
    task_level_final_t2=True,
    capability_level_final_t2_required=False,
    diff_check_required=True,
    known_impact_required=False,
    direct_task_main_merge_allowed=True,
    capability_batch_authority_required=False,
    integration_lane_authority_required=False,
    executable_without_capability_authority=True,
)

PRODUCT_DELIVERY_FAST_POLICY = ValidationProfilePolicy(
    profile_id=ValidationProfile.PRODUCT_DELIVERY_FAST,
    task_level_t0_t1_required=True,
    task_level_review_first_semantic_review_required=True,
    task_level_final_t2=False,
    capability_level_final_t2_required=True,
    diff_check_required=True,
    known_impact_required=True,
    direct_task_main_merge_allowed=False,
    capability_batch_authority_required=True,
    integration_lane_authority_required=True,
    executable_without_capability_authority=False,
)

_PROFILE_POLICIES = {
    ValidationProfile.CONTROL_PLANE_STRICT_COMPAT: CONTROL_PLANE_STRICT_COMPAT_POLICY,
    ValidationProfile.CONTROL_PLANE_STRICT: CONTROL_PLANE_STRICT_POLICY,
    ValidationProfile.PRODUCT_DELIVERY_FAST: PRODUCT_DELIVERY_FAST_POLICY,
}


def validation_policy_for_profile(profile: ValidationProfile) -> ValidationProfilePolicy:
    if type(profile) is not ValidationProfile:
        raise _error("profile must be an exact ValidationProfile")
    return _PROFILE_POLICIES[profile]


def _top_level_lines(content: str) -> list[str]:
    """Return lines outside Markdown backtick/tilde fences."""
    lines: list[str] = []
    fence: tuple[str, int] | None = None
    for line in content.splitlines():
        stripped = line.lstrip()
        match = re.match(r"(`{3,}|~{3,})", stripped)
        if match:
            run = match.group(1)
            token = run[0]
            if fence is None:
                fence = (token, len(run))
            elif (
                fence[0] == token
                and len(run) >= fence[1]
                and stripped[len(run) :].strip() == ""
            ):
                fence = None
            continue
        if fence is None:
            lines.append(line)
    return lines


def _top_level_marker_values(lines: Sequence[str], marker: str) -> list[str]:
    return [
        line[len(marker) :].strip()
        for line in lines
        if line.startswith(marker)
    ]


def validation_profile_for_task(task_content: str) -> ValidationProfile | None:
    """Resolve only explicit profile authority, preserving Lean historical identity."""
    if type(task_content) is not str:
        raise _error("task_content must be exact text")

    top_level_lines = _top_level_lines(task_content)
    profile_declarations = [
        line
        for line in top_level_lines
        if re.match(r"VALIDATION_PROFILE(?:\s|:|$)", line)
    ]
    profile_values = _top_level_marker_values(
        top_level_lines, _VALIDATION_PROFILE_MARKER
    )
    if len(profile_declarations) != len(profile_values):
        raise _error("Malformed top-level VALIDATION_PROFILE marker")
    if len(profile_values) > 1:
        raise _error("Task must contain at most one top-level VALIDATION_PROFILE marker")
    if profile_values:
        value = profile_values[0]
        if not value:
            raise _error("VALIDATION_PROFILE marker must not be empty")
        try:
            return ValidationProfile(value)
        except ValueError as exc:
            raise _error(f"Unknown VALIDATION_PROFILE: {value!r}") from exc

    roadmap_values = _top_level_marker_values(
        top_level_lines, _ROADMAP_BINDING_MARKER
    )
    if not roadmap_values:
        return None
    if len(roadmap_values) != 1:
        raise _error("Task must contain at most one ROADMAP_BINDING_JSON marker")
    try:
        binding = json.loads(roadmap_values[0])
    except (TypeError, ValueError) as exc:
        raise _error(
            f"Malformed roadmap binding while resolving validation profile: {exc}"
        ) from exc
    if type(binding) is not dict:
        raise _error("Roadmap binding must be a JSON object")
    if binding.get("roadmap_id") != _LEAN_ROADMAP_ID:
        return None
    return ValidationProfile.CONTROL_PLANE_STRICT_COMPAT


def validation_plan_for_task(task_content: str) -> ValidationPlan | None:
    """Resolve an executable plan while fast admission remains unavailable."""
    profile = validation_profile_for_task(task_content)
    if profile is None:
        return None
    if profile is ValidationProfile.CONTROL_PLANE_STRICT_COMPAT:
        return CONTROL_PLANE_STRICT_COMPAT_PLAN
    if profile is ValidationProfile.CONTROL_PLANE_STRICT:
        return CONTROL_PLANE_STRICT_PLAN
    raise _error(
        "PRODUCT_DELIVERY_FAST admission blocked: missing "
        "capability-batch/integration-lane authority"
    )


def product_delivery_fast_impact_is_eligible(impact_confidence: object) -> bool:
    """Conservative adapter to the existing closed Slice-C impact vocabulary."""
    from src.aios_bridge.review_pipeline import ImpactConfidence

    return (
        type(impact_confidence) is ImpactConfidence
        and impact_confidence is ImpactConfidence.KNOWN
    )


def classify_validation_command(command: str) -> ValidationTier:
    if type(command) is not str or not command.strip():
        raise _error("validation command must be exact non-empty text")
    normalized = command.replace("\\", "/")
    if _FULL_SUITE_RE.search(normalized):
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


def certification_commands_for_plan(
    commands: Sequence[str], plan: ValidationPlan
) -> tuple[str, ...]:
    """Select the sole AIOS-managed T2 command and reject duplicate scheduling."""
    if isinstance(commands, (str, bytes)) or not isinstance(commands, Sequence):
        raise _error("commands must be a sequence of command strings")
    if type(plan) is not ValidationPlan:
        raise _error("plan must be an exact ValidationPlan")
    retained: list[str] = []
    for command in commands:
        tier = classify_validation_command(command)
        if tier in plan.certification_test_tiers:
            retained.append(command)
        elif tier not in plan.executor_test_tiers:
            raise _error("validation ownership is ambiguous; strict certification retained")
    actual_count = len(retained)
    expected_count = plan.expected_full_suite_execution_count
    if actual_count > expected_count:
        raise _error("AIOS_MANAGED_T2_DUPLICATION_DETECTED")
    if actual_count != expected_count:
        raise _error("AIOS-managed certification must schedule T2 exactly once")
    return tuple(retained)


def review_first_candidate_test_command(
    command: str | None,
    plan: ValidationPlan,
) -> tuple[str | None, bool]:
    """Defer a legacy T2 command while retaining a bounded candidate-stage T1."""
    if type(plan) is not ValidationPlan:
        raise _error("plan must be an exact ValidationPlan")
    if command is None:
        return None, False
    tier = classify_validation_command(command)
    if tier in plan.certification_test_tiers:
        return None, True
    if tier not in plan.executor_test_tiers:
        raise _error("candidate publication command has no exact validation owner")
    return command, False


@dataclass(frozen=True)
class ValidationEvidence:
    task_id: str
    action: str
    executor_id: str
    validation_profile: ValidationProfile
    full_suite_execution_count: int
    expected_full_suite_execution_count: int
    targeted_test_execution_count: int | None
    full_suite_duration_seconds: float | None = None
    targeted_test_duration_seconds: float | None = None
    executor_ad_hoc_t2_observability: ExecutorAdHocT2Observability = (
        ExecutorAdHocT2Observability.UNAVAILABLE
    )
    executor_ad_hoc_t2_execution_count: int | None = None

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
        for name in ("full_suite_execution_count", "expected_full_suite_execution_count"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise _error(f"{name} must be an exact non-negative integer")
        if self.targeted_test_execution_count is not None and (
            type(self.targeted_test_execution_count) is not int
            or self.targeted_test_execution_count < 0
        ):
            raise _error(
                "targeted_test_execution_count must be UNKNOWN or an exact non-negative integer"
            )
        for name in ("full_suite_duration_seconds", "targeted_test_duration_seconds"):
            value = getattr(self, name)
            if value is not None and (type(value) not in {int, float} or value < 0):
                raise _error(f"{name} must be unknown or a non-negative observed duration")
        if type(self.executor_ad_hoc_t2_observability) is not ExecutorAdHocT2Observability:
            raise _error(
                "executor_ad_hoc_t2_observability must be an exact observability value"
            )
        ad_hoc_count = self.executor_ad_hoc_t2_execution_count
        if self.executor_ad_hoc_t2_observability is ExecutorAdHocT2Observability.UNAVAILABLE:
            if ad_hoc_count is not None:
                raise _error("unavailable executor ad-hoc T2 count must remain UNKNOWN")
        elif type(ad_hoc_count) is not int or ad_hoc_count < 0:
            raise _error("observed executor ad-hoc T2 count must be a non-negative integer")
        if (
            self.targeted_test_execution_count is None
            and self.targeted_test_duration_seconds is not None
        ):
            raise _error("unknown targeted test count cannot have an observed duration")

    @property
    def expected_aios_managed_t2_execution_count(self) -> int:
        return self.expected_full_suite_execution_count

    @property
    def aios_managed_t2_execution_count(self) -> int:
        return self.full_suite_execution_count

    @property
    def aios_managed_t2_duplication_detected(self) -> bool:
        return self.full_suite_execution_count > self.expected_full_suite_execution_count

    @property
    def validation_duplication_detected(self) -> bool:
        """Compatibility alias whose scope is AIOS-managed validation only."""
        return self.aios_managed_t2_duplication_detected

    @property
    def global_t2_execution_count(self) -> int | None:
        if self.executor_ad_hoc_t2_observability is ExecutorAdHocT2Observability.UNAVAILABLE:
            return None
        assert self.executor_ad_hoc_t2_execution_count is not None
        return self.full_suite_execution_count + self.executor_ad_hoc_t2_execution_count

    @staticmethod
    def _observed_or_unknown(value: int | float | None) -> int | float | str:
        return "UNKNOWN" if value is None else value

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "aios_managed_t2_duplication_detected": (
                self.aios_managed_t2_duplication_detected
            ),
            "aios_managed_t2_execution_count": self.aios_managed_t2_execution_count,
            "evidence_scope": "AIOS_MANAGED_VALIDATION_AND_EXECUTOR_AD_HOC_BOUNDARY",
            "executor_id": self.executor_id,
            "executor_ad_hoc_t2_execution_count": self._observed_or_unknown(
                self.executor_ad_hoc_t2_execution_count
            ),
            "executor_ad_hoc_t2_observability": (
                self.executor_ad_hoc_t2_observability.value
            ),
            "expected_aios_managed_t2_execution_count": (
                self.expected_aios_managed_t2_execution_count
            ),
            "full_canonical_owner": ValidationOwner.CERTIFICATION_BOUNDARY.value,
            "full_suite_duration_seconds": self._observed_or_unknown(
                self.full_suite_duration_seconds
            ),
            "global_t2_execution_count": self._observed_or_unknown(
                self.global_t2_execution_count
            ),
            "targeted_test_duration_seconds": self._observed_or_unknown(
                self.targeted_test_duration_seconds
            ),
            "targeted_test_execution_count": self._observed_or_unknown(
                self.targeted_test_execution_count
            ),
            "task_id": self.task_id,
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
    if evidence.aios_managed_t2_duplication_detected:
        raise _error("AIOS_MANAGED_T2_DUPLICATION_DETECTED")
    if (
        evidence.executor_ad_hoc_t2_observability
        is ExecutorAdHocT2Observability.OBSERVED
        and evidence.executor_ad_hoc_t2_execution_count
    ):
        raise _error(
            "VALIDATION_POLICY_VIOLATION: executor ad-hoc T2 observed while certification owns T2"
        )
    if not full_suite_succeeded:
        raise _error("failed T2 cannot publish")
    if evidence.full_suite_execution_count != plan.expected_full_suite_execution_count:
        raise _error("full canonical certification was not executed exactly once")


def require_review_first_candidate_publication(
    plan: ValidationPlan,
    evidence: ValidationEvidence,
) -> None:
    """Prove candidate publication deferred every AIOS-managed T2 execution."""
    if type(plan) is not ValidationPlan or type(evidence) is not ValidationEvidence:
        raise _error("review-first candidate publication requires exact plan and evidence")
    if evidence.validation_profile is not plan.profile_id:
        raise _error("validation evidence profile does not match the plan")
    if evidence.expected_full_suite_execution_count != plan.expected_full_suite_execution_count:
        raise _error("validation evidence expected count does not match the final plan")
    if evidence.aios_managed_t2_execution_count != 0:
        raise _error("review-first candidate publication must execute zero AIOS-managed T2")
    if evidence.aios_managed_t2_duplication_detected:
        raise _error("AIOS_MANAGED_T2_DUPLICATION_DETECTED")
    if (
        evidence.executor_ad_hoc_t2_observability
        is ExecutorAdHocT2Observability.OBSERVED
        and evidence.executor_ad_hoc_t2_execution_count
    ):
        raise _error("review-first candidate publication observed an early ad-hoc T2")


__all__ = [
    "CONTROL_PLANE_STRICT_COMPAT_POLICY",
    "CONTROL_PLANE_STRICT_COMPAT_PLAN",
    "CONTROL_PLANE_STRICT_POLICY",
    "CONTROL_PLANE_STRICT_PLAN",
    "ExecutorAdHocT2Observability",
    "PRODUCT_DELIVERY_FAST_POLICY",
    "ValidationEvidence",
    "ValidationOwner",
    "ValidationPlan",
    "ValidationProfile",
    "ValidationProfilePolicy",
    "ValidationTier",
    "classify_validation_command",
    "certification_commands_for_plan",
    "executor_commands_for_plan",
    "product_delivery_fast_impact_is_eligible",
    "require_certification_for_publication",
    "require_review_first_candidate_publication",
    "review_first_candidate_test_command",
    "validation_owner",
    "validation_plan_for_task",
    "validation_policy_for_profile",
    "validation_profile_for_task",
]
