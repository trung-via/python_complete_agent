"""Deterministic executable task/review authoring preflight and publisher guard (ADR-044 / TASK-071)."""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from src.aios_bridge.continuity.errors import ContinuityStateValidationError
from src.aios_bridge.continuity.executor import ExecutionOperation
from src.aios_bridge.executor_automation import (
    ExecutorAutomationMarkers,
    parse_executor_automation_markers,
)
from src.aios_bridge.runtime_dispatch import (
    ExecutorPolicyCandidateSpec,
    ExecutorDispatchPolicySpec,
    parse_executor_dispatch_policy_marker,
)


CANONICAL_E4_PUBLISHER_PROFILE = "CANONICAL_E4"
SUPPORTED_PUBLISHER_PROFILES = frozenset({CANONICAL_E4_PUBLISHER_PROFILE, "DEFAULT"})

_FORBIDDEN_CUSTOM_RESULT_MARKERS = (
    "REQUIRED_RESULT_KEYS_JSON:",
    "CUSTOM_RESULT_SCHEMA_JSON:",
    "PUBLISHER_REQUIRED_KEYS_JSON:",
    "RESULT_SCHEMA_OVERRIDE_JSON:",
)


class ExecutableArtifactPreflightError(ContinuityStateValidationError):
    """Fail-closed error raised when an executable artifact fails preflight validation."""


@dataclass(frozen=True)
class ExecutableArtifactPreflight:
    """Immutable preflight record for an authorized executable task/review artifact."""
    work_path: str
    operation: ExecutionOperation
    selected_executor: str
    markers: ExecutorAutomationMarkers
    policy: ExecutorDispatchPolicySpec
    candidate: ExecutorPolicyCandidateSpec

    def __post_init__(self) -> None:
        if not isinstance(self.work_path, str) or not self.work_path.strip():
            raise ExecutableArtifactPreflightError("work_path must be non-empty string")
        if not isinstance(self.operation, ExecutionOperation):
            raise ExecutableArtifactPreflightError(
                f"operation must be ExecutionOperation: got {self.operation!r}"
            )
        if not isinstance(self.selected_executor, str) or not self.selected_executor.strip():
            raise ExecutableArtifactPreflightError("selected_executor must be non-empty string")
        if not isinstance(self.markers, ExecutorAutomationMarkers):
            raise ExecutableArtifactPreflightError("markers must be ExecutorAutomationMarkers")
        if not isinstance(self.policy, ExecutorDispatchPolicySpec):
            raise ExecutableArtifactPreflightError("policy must be ExecutorDispatchPolicySpec")
        if not isinstance(self.candidate, ExecutorPolicyCandidateSpec):
            raise ExecutableArtifactPreflightError("candidate must be ExecutorPolicyCandidateSpec")


def validate_publisher_profile(content: str) -> None:
    """
    Validate that an executable artifact adheres to the canonical E4 publisher profile.
    Rejects artifacts that declare unsupported arbitrary custom RESULT schema requirements.
    """
    if not isinstance(content, str):
        raise ExecutableArtifactPreflightError("Artifact content must be string")

    for marker in _FORBIDDEN_CUSTOM_RESULT_MARKERS:
        if marker in content:
            raise ExecutableArtifactPreflightError(
                f"Unsupported custom RESULT requirement marker rejected: {marker}"
            )

    match = re.search(r"PUBLISHER_PROFILE:\s*(\S+)", content)
    if match:
        profile = match.group(1).strip()
        if profile not in SUPPORTED_PUBLISHER_PROFILES:
            raise ExecutableArtifactPreflightError(
                f"Unsupported publisher profile '{profile}'; must be one of {sorted(SUPPORTED_PUBLISHER_PROFILES)}"
            )


def preflight_executable_artifact(
    content: str,
    *,
    work_path: str,
    operation: ExecutionOperation,
    selected_executor: str,
) -> ExecutableArtifactPreflight:
    """
    Deterministically validate executable TASK/REVIEW artifact markers and dispatch policy.
    Reuses canonical E4 automation and dispatch parsers without creating any authority
    or performing any network/subprocess/model actions.
    """
    if not isinstance(content, str) or not content.strip():
        raise ExecutableArtifactPreflightError("Executable artifact content must be non-empty str")
    if not isinstance(work_path, str) or not work_path.strip():
        raise ExecutableArtifactPreflightError("work_path must be non-empty str")
    if not isinstance(operation, ExecutionOperation):
        raise ExecutableArtifactPreflightError(
            f"operation must be ExecutionOperation: got {operation!r}"
        )
    if not isinstance(selected_executor, str) or not selected_executor.strip():
        raise ExecutableArtifactPreflightError("selected_executor must be non-empty str")

    # 1. Enforce publisher profile authoring guard
    validate_publisher_profile(content)

    # 2. Parse automation markers (EXECUTOR_CONTEXT_REFS_JSON and EXECUTOR_ALLOWED_PATHS_JSON)
    try:
        markers = parse_executor_automation_markers(content, work_path=work_path)
    except ContinuityStateValidationError as exc:
        raise ExecutableArtifactPreflightError(str(exc)) from exc
    except Exception as exc:
        raise ExecutableArtifactPreflightError(f"Malformed executor automation markers: {exc}") from exc

    # 3. Parse dispatch policy marker (DISPATCH_EXECUTOR_POLICY_JSON)
    try:
        policy = parse_executor_dispatch_policy_marker(content)
    except ContinuityStateValidationError as exc:
        raise ExecutableArtifactPreflightError(str(exc)) from exc
    except Exception as exc:
        raise ExecutableArtifactPreflightError(f"Malformed dispatch policy marker: {exc}") from exc

    # 4. Validate requested RUN/FIX operation against dispatch policy
    if policy.operation is not operation:
        raise ExecutableArtifactPreflightError(
            f"Dispatch policy operation mismatches requested operation ({operation.value} vs {policy.operation.value})"
        )

    # 5. Validate Human-selected executor is an exact declared candidate
    candidates = [c for c in policy.candidates if c.executor_id == selected_executor]
    if len(candidates) != 1:
        declared = [c.executor_id for c in policy.candidates]
        raise ExecutableArtifactPreflightError(
            f"Authorized executor '{selected_executor}' must appear exactly once in policy candidates (declared: {declared})"
        )
    candidate = candidates[0]

    # 6. Validate candidate supports requested operation
    if operation not in candidate.supported_operations:
        raise ExecutableArtifactPreflightError(
            f"Authorized executor '{selected_executor}' does not support requested operation '{operation.value}'"
        )

    # 7. Validate candidate supports all required capabilities
    missing_caps = [cap for cap in policy.required_capabilities if cap not in candidate.supported_capabilities]
    if missing_caps:
        missing_names = [cap.value for cap in missing_caps]
        raise ExecutableArtifactPreflightError(
            f"Selected executor '{selected_executor}' lacks required capabilities: {missing_names}"
        )

    return ExecutableArtifactPreflight(
        work_path=work_path,
        operation=operation,
        selected_executor=selected_executor,
        markers=markers,
        policy=policy,
        candidate=candidate,
    )


__all__ = [
    "CANONICAL_E4_PUBLISHER_PROFILE",
    "SUPPORTED_PUBLISHER_PROFILES",
    "ExecutableArtifactPreflight",
    "ExecutableArtifactPreflightError",
    "validate_publisher_profile",
    "preflight_executable_artifact",
]
