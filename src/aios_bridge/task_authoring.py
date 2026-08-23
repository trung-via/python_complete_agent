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
    ExecutorDispatchPolicySpec,
    ExecutorPolicyCandidateSpec,
    parse_executor_dispatch_policy_marker,
)


CANONICAL_E4_PUBLISHER_PROFILE = "CANONICAL_E4"
SUPPORTED_PUBLISHER_PROFILES = frozenset({CANONICAL_E4_PUBLISHER_PROFILE, "DEFAULT"})

CANONICAL_RESULT_KEYS = frozenset({
    "STATUS",
    "ACTION",
    "TASK_ID",
    "EXECUTOR_ID",
    "EXECUTOR_FAILOVER",
    "FAILOVER_FROM_EXECUTOR",
    "FAILOVER_TO_EXECUTOR",
    "FAILOVER_SOURCE_PUBLISHED_SHA",
    "FAILOVER_PROOF_FINGERPRINT",
    "FAILOVER_REVIEW_BLOB_SHA",
    "HOT_HANDOFF",
    "HOT_HANDOFF_CHECKPOINT_FINGERPRINT",
    "HOT_HANDOFF_FROM_EXECUTOR",
    "HOT_HANDOFF_TO_EXECUTOR",
    "BASE_SHA",
    "TARGETED_TESTS",
    "FULL_REPO_TESTS",
    "BRIDGE_TESTS",
    "CONTINUITY_TESTS",
    "REGRESSIONS",
    "SUMMARY",
    "DIFF_STAT",
    "TESTS",
    "GIT_DIFF_CHECK",
    "DIAGNOSTIC_EVIDENCE",
    "M6_REAL_PROOF_ANTIGRAVITY_TO_CODEX",
    "M6_REAL_PROOF_CODEX_TO_ANTIGRAVITY",
    "M7_THIRD_EXECUTOR_PORTABILITY",
    "SUPPORTED_RUNTIME_EXECUTORS",
    "CONTINUITY_CORE_CHANGED",
    "M5_LEASE_SEMANTICS_CHANGED",
    "M6_FAILOVER_CONTRACT_CHANGED",
    "M7_EXECUTOR_SET_CHANGED",
    "AUTOMATIC_BRAIN_ROUTING",
    "AUTOMATIC_EXECUTOR_ROUTING",
    "HOT_HANDOFF_ADDED",
    "FOURTH_EXECUTOR_ADDED",
    "CHAT_UI_AUTOMATION",
    "PAID_EXTERNAL_API_CALLS",
    "LIVE_EXTERNAL_CALLS_AUTOMATED_TESTS",
    "M7_REAL_PROOF_ANTIGRAVITY_TO_CLAUDE_CODE",
    "M7_REAL_PROOF_CLAUDE_CODE_TO_ANTIGRAVITY",
    "M8_MULTI_AGENT_CONTINUITY_HARNESS",
    "M8_SHARED_BOUNDARY_SHA",
    "M8_BRAIN_PROOF",
    "M8_EXECUTOR_PROOF",
    "M8_COMPOSITE_CHAIN",
})

_FORBIDDEN_MARKER_NAMES = (
    "REQUIRED_RESULT_KEYS_JSON:",
    "CUSTOM_RESULT_SCHEMA_JSON:",
    "PUBLISHER_REQUIRED_KEYS_JSON:",
    "RESULT_SCHEMA_OVERRIDE_JSON:",
)

_PUBLISHER_PROFILE_LINE_RE = re.compile(r"^PUBLISHER_PROFILE:\s*(\S+)", re.MULTILINE)
_CUSTOM_RESULT_SECTION_RE = re.compile(
    r"(?im)^##\s+RESULT\s+Evidence\b\s*\n([\s\S]*?)(?=^##|\Z)"
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


def validate_publisher_profile_marker(
    profile: str | None,
    *,
    allow_missing: bool = False,
) -> str:
    """Validate a standalone publisher profile value."""
    if profile is None or not str(profile).strip():
        if allow_missing:
            return CANONICAL_E4_PUBLISHER_PROFILE
        raise ExecutableArtifactPreflightError("Missing required PUBLISHER_PROFILE")
    p = str(profile).strip()
    if p not in SUPPORTED_PUBLISHER_PROFILES:
        raise ExecutableArtifactPreflightError(
            f"Unsupported publisher profile '{p}'; must be one of {sorted(SUPPORTED_PUBLISHER_PROFILES)}"
        )
    return CANONICAL_E4_PUBLISHER_PROFILE if p == "DEFAULT" else p


def validate_publisher_profile(
    content: str,
    *,
    require_explicit_profile: bool = False,
) -> str:
    """
    Validate that an executable artifact adheres to the canonical E4 publisher profile.
    Rejects artifacts that declare unsupported arbitrary custom RESULT schema requirements,
    duplicate/conflicting PUBLISHER_PROFILE markers, or non-canonical result key mandates (TASK-070 failure class).
    """
    if not isinstance(content, str):
        raise ExecutableArtifactPreflightError("Artifact content must be string")

    # Only inspect non-fenced lines for top-level marker declarations
    unfenced_lines = []
    in_fence = False
    for line in content.splitlines():
        trimmed = line.strip()
        if trimmed.startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            unfenced_lines.append(line)

    unfenced_text = "\n".join(unfenced_lines)

    # 1. Check for forbidden top-level marker definitions
    for marker_name in _FORBIDDEN_MARKER_NAMES:
        for line in unfenced_lines:
            if line.strip().startswith(marker_name):
                raise ExecutableArtifactPreflightError(
                    f"Unsupported custom RESULT requirement marker rejected: {marker_name}"
                )

    # 2. Check line-anchored PUBLISHER_PROFILE markers
    profile_matches = _PUBLISHER_PROFILE_LINE_RE.findall(unfenced_text)
    if len(profile_matches) > 1:
        distinct = set(profile_matches)
        if len(distinct) > 1:
            raise ExecutableArtifactPreflightError(
                f"Conflicting PUBLISHER_PROFILE markers found: {profile_matches}"
            )
        raise ExecutableArtifactPreflightError(
            f"Duplicate PUBLISHER_PROFILE marker found: {profile_matches}"
        )
    elif len(profile_matches) == 1:
        declared_profile = profile_matches[0].strip()
        if declared_profile not in SUPPORTED_PUBLISHER_PROFILES:
            raise ExecutableArtifactPreflightError(
                f"Unsupported publisher profile '{declared_profile}'; must be one of {sorted(SUPPORTED_PUBLISHER_PROFILES)}"
            )
        active_profile = CANONICAL_E4_PUBLISHER_PROFILE if declared_profile == "DEFAULT" else declared_profile
    else:
        if require_explicit_profile:
            raise ExecutableArtifactPreflightError("Missing required PUBLISHER_PROFILE marker")
        active_profile = CANONICAL_E4_PUBLISHER_PROFILE

    # 3. TASK-070 Failure Class Guard:
    # Check for custom ## RESULT Evidence section attempting to enforce non-canonical result keys
    section_match = _CUSTOM_RESULT_SECTION_RE.search(unfenced_text)
    if section_match:
        section_text = section_match.group(1)
        # Scan for required key lists like "must report at minimum:\nKEY1\nKEY2" or line-by-line keys
        tokens = re.findall(r"\b([A-Z][A-Z0-9_]{3,})\b", section_text)
        for token in tokens:
            if token in ("RESULT", "Evidence", "MUST", "REPORT", "AT", "MINIMUM", "REQUIRED", "KEYS", "TRUE", "FALSE", "PASS", "FAIL", "READY"):
                continue
            if token not in CANONICAL_RESULT_KEYS and not token.startswith("TASK_") and not token.startswith("STEP_"):
                raise ExecutableArtifactPreflightError(
                    f"Unsupported custom RESULT requirement key '{token}' rejected under {active_profile} profile"
                )

    return active_profile


def preflight_executable_artifact(
    content: str,
    *,
    work_path: str,
    operation: ExecutionOperation,
    selected_executor: str,
    require_explicit_profile: bool = False,
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
    validate_publisher_profile(content, require_explicit_profile=require_explicit_profile)

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
            f"Authorized executor '{selected_executor}' lacks required capabilities: {missing_names}"
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
    "CANONICAL_RESULT_KEYS",
    "ExecutableArtifactPreflight",
    "ExecutableArtifactPreflightError",
    "validate_publisher_profile_marker",
    "validate_publisher_profile",
    "preflight_executable_artifact",
]
