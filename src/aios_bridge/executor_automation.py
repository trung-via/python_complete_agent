"""Pure E4 executor automation composition and validation helpers (ADR-032)."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import PurePosixPath
import re
from typing import Mapping, Sequence

from src.aios_bridge.continuity.errors import ContinuityStateValidationError
from src.aios_bridge.continuity.executor import (
    ExecutionCapability,
    ExecutionOperation,
    ExecutionRequest,
    ExecutionResult,
    ExecutionResultStatus,
    ExecutorCapabilities,
    PreparedExecution,
    validate_execution_request_against_state,
    validate_execution_result_against_request,
    validate_executor_eligibility,
    validate_prepared_execution_against_request,
)
from src.aios_bridge.continuity.lease import (
    ExecutorLease,
    validate_executor_lease_binding,
)
from src.aios_bridge.continuity.state import (
    ArtifactRef,
    BranchState,
    BrainState,
    ContinuityArtifacts,
    ContinuityPhase,
    ContinuityState,
    ExecutorState,
    FreshnessStatus,
    NextOperation,
    SCHEMA_VERSION,
    StateObservation,
    check_freshness,
)
from src.aios_bridge.executor_context import (
    ExecutorAuthorizationBinding,
    ExecutorContextPack,
    augment_executor_context_pack_for_fix,
    build_executor_context_pack,
)
from src.aios_bridge.fix_review import FixContextPack, FixImpactAnalysis
from src.aios_bridge.validation import ValidationPlan, validation_plan_for_task


EXECUTOR_CONTEXT_REFS_MARKER = "EXECUTOR_CONTEXT_REFS_JSON:"
EXECUTOR_ALLOWED_PATHS_MARKER = "EXECUTOR_ALLOWED_PATHS_JSON:"
MAX_AUTOMATION_CONTEXT_REFS = 7

_TASK_ID_RE = re.compile(r"^TASK-\d+$")
_BLOB_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_FINGERPRINT_RE = re.compile(r"^[0-9a-f]{64}$")
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
_FORBIDDEN_ALLOWED_NAMESPACES = (
    ".ai/results",
    ".ai/auth",
    ".ai/inbox",
    ".ai/state",
    ".ai/bridge",
)


def _error(message: str) -> ContinuityStateValidationError:
    return ContinuityStateValidationError(message)


def _validate_repo_path(path: object, field_name: str) -> str:
    if type(path) is not str or not path or path != path.strip():
        raise _error(f"{field_name} must be an exact non-empty path string")
    if "\\" in path or _CONTROL_RE.search(path):
        raise _error(f"{field_name} must be a control-free POSIX path")
    pure = PurePosixPath(path)
    parts = path.split("/")
    if pure.is_absolute() or path.startswith("/") or any(
        part in {"", ".", ".."} for part in parts
    ):
        raise _error(f"{field_name} must be a canonical repository-relative path")
    if str(pure) != path:
        raise _error(f"{field_name} must be canonical")
    return path


def _validate_context_path(path: object, field_name: str) -> str:
    validated = _validate_repo_path(path, field_name)
    if not validated.startswith(".ai/"):
        raise _error(f"{field_name} must live under .ai/")
    return validated


def _validate_allowed_path(path: object, field_name: str) -> str:
    validated = _validate_repo_path(path, field_name)
    if validated == ".git" or validated.startswith(".git/"):
        raise _error(f"{field_name} cannot grant .git scope")
    for namespace in _FORBIDDEN_ALLOWED_NAMESPACES:
        if validated == namespace or validated.startswith(f"{namespace}/"):
            raise _error(f"{field_name} cannot grant Bridge/runtime control scope")
    return validated


@dataclass(frozen=True)
class ExecutorContextRefSpec:
    path: str
    blob_sha: str

    def __post_init__(self) -> None:
        _validate_context_path(self.path, "ExecutorContextRefSpec.path")
        if type(self.blob_sha) is not str or not _BLOB_SHA_RE.fullmatch(self.blob_sha):
            raise _error("ExecutorContextRefSpec.blob_sha must be exact lowercase 40-hex")


@dataclass(frozen=True)
class ExecutorAutomationMarkers:
    context_refs: tuple[ExecutorContextRefSpec, ...]
    allowed_paths: tuple[str, ...]

    def __post_init__(self) -> None:
        if type(self.context_refs) is not tuple or not self.context_refs:
            raise _error("context_refs must be an exact non-empty tuple")
        if len(self.context_refs) > MAX_AUTOMATION_CONTEXT_REFS:
            raise _error("context_refs exceeds MAX_AUTOMATION_CONTEXT_REFS")
        if any(type(item) is not ExecutorContextRefSpec for item in self.context_refs):
            raise _error("context_refs must contain exact ExecutorContextRefSpec values")
        if type(self.allowed_paths) is not tuple or not self.allowed_paths:
            raise _error("allowed_paths must be an exact non-empty tuple")
        for index, path in enumerate(self.allowed_paths):
            _validate_allowed_path(path, f"allowed_paths[{index}]")


def _single_marker_value(content: str, prefix: str) -> str:
    occurrences = [line[len(prefix) :].strip() for line in content.splitlines() if line.startswith(prefix)]
    if len(occurrences) != 1:
        raise _error(f"Artifact must contain exactly one {prefix} marker; found {len(occurrences)}")
    if not occurrences[0]:
        raise _error(f"{prefix} marker payload must not be empty")
    return occurrences[0]


def parse_executor_automation_markers(
    content: str,
    *,
    work_path: str,
) -> ExecutorAutomationMarkers:
    """Parse the two exact machine-readable E4 markers without prose inference."""
    if type(content) is not str:
        raise _error("Executor automation artifact content must be exact str")
    canonical_work_path = _validate_context_path(work_path, "work_path")
    try:
        context_data = json.loads(_single_marker_value(content, EXECUTOR_CONTEXT_REFS_MARKER))
        allowed_data = json.loads(_single_marker_value(content, EXECUTOR_ALLOWED_PATHS_MARKER))
    except (TypeError, ValueError) as exc:
        raise _error(f"Malformed executor automation marker JSON: {exc}") from exc

    if type(context_data) is not list or not 1 <= len(context_data) <= MAX_AUTOMATION_CONTEXT_REFS:
        raise _error("Context marker root must be a bounded non-empty JSON list")
    context_refs: list[ExecutorContextRefSpec] = []
    context_paths: set[str] = set()
    for index, item in enumerate(context_data):
        if type(item) is not dict or set(item) != {"path", "blob_sha"}:
            raise _error(f"Context marker entry {index} must have exact path/blob_sha keys")
        spec = ExecutorContextRefSpec(path=item["path"], blob_sha=item["blob_sha"])
        if spec.path == canonical_work_path:
            raise _error("Context marker cannot duplicate the active work artifact")
        if spec.path in context_paths:
            raise _error(f"Duplicate context marker path: {spec.path}")
        context_paths.add(spec.path)
        context_refs.append(spec)

    if type(allowed_data) is not list or not allowed_data:
        raise _error("Allowed-path marker root must be a non-empty JSON list")
    allowed_paths: list[str] = []
    allowed_seen: set[str] = set()
    for index, item in enumerate(allowed_data):
        path = _validate_allowed_path(item, f"allowed_paths[{index}]")
        if path in allowed_seen:
            raise _error(f"Duplicate allowed path: {path}")
        allowed_seen.add(path)
        allowed_paths.append(path)

    return ExecutorAutomationMarkers(tuple(context_refs), tuple(allowed_paths))


@dataclass(frozen=True)
class ExecutorAutomationIds:
    request_id: str
    execution_id: str
    invocation_id: str


def derive_executor_automation_ids(
    task_id: str,
    lease_fingerprint: str,
) -> ExecutorAutomationIds:
    if type(task_id) is not str or not _TASK_ID_RE.fullmatch(task_id):
        raise _error("task_id must match exact case-sensitive '^TASK-\\d+$'")
    if type(lease_fingerprint) is not str or not _FINGERPRINT_RE.fullmatch(lease_fingerprint):
        raise _error("lease_fingerprint must be exact lowercase 64-hex")
    stem = task_id.lower()
    suffix = lease_fingerprint[:16]
    return ExecutorAutomationIds(
        request_id=f"req-{stem}-{suffix}",
        execution_id=f"exec-{stem}-{suffix}",
        invocation_id=f"invoke-{stem}-{suffix}",
    )


@dataclass(frozen=True)
class ExecutorAutomationLaunchPlan:
    continuity_state: ContinuityState
    execution_request: ExecutionRequest
    prepared_execution: PreparedExecution
    context_pack: ExecutorContextPack
    validation_plan: ValidationPlan | None


def _require_exact_tuple(value: object, item_type: type, field_name: str) -> tuple:
    if type(value) is not tuple or any(type(item) is not item_type for item in value):
        raise _error(f"{field_name} must be an exact tuple of {item_type.__name__}")
    return value


def build_executor_automation_launch_plan(
    *,
    task_id: str,
    operation: ExecutionOperation,
    executor_id: str,
    main_branch: str,
    main_sha: str,
    target_branch: str,
    task_head_sha: str,
    work_ref: ArtifactRef,
    context_refs: tuple[ArtifactRef, ...],
    prior_result_ref: ArtifactRef | None,
    required_capabilities: tuple[ExecutionCapability, ...],
    executor_capabilities: ExecutorCapabilities,
    executor_lease: ExecutorLease,
    authorization_binding: ExecutorAuthorizationBinding,
    artifact_payloads: Mapping[str, bytes],
    transport_id: str,
    fix_context_pack: FixContextPack | None = None,
    fix_impact_analysis: FixImpactAnalysis | None = None,
) -> ExecutorAutomationLaunchPlan:
    """Build and validate the deterministic M1/M4/E3 launch plan without I/O."""
    if type(operation) is not ExecutionOperation:
        raise _error("operation must be an exact ExecutionOperation")
    if type(work_ref) is not ArtifactRef:
        raise _error("work_ref must be an exact ArtifactRef")
    context_refs = _require_exact_tuple(context_refs, ArtifactRef, "context_refs")
    required_capabilities = _require_exact_tuple(
        required_capabilities, ExecutionCapability, "required_capabilities"
    )
    if type(executor_capabilities) is not ExecutorCapabilities:
        raise _error("executor_capabilities must be exact ExecutorCapabilities")
    if type(executor_lease) is not ExecutorLease:
        raise _error("executor_lease must be exact ExecutorLease")
    if type(authorization_binding) is not ExecutorAuthorizationBinding:
        raise _error("authorization_binding must be exact ExecutorAuthorizationBinding")
    if not isinstance(artifact_payloads, Mapping):
        raise _error("artifact_payloads must be a Mapping")

    expected_task_path = f".ai/tasks/{task_id}.md"
    expected_review_path = f".ai/reviews/REVIEW-{task_id[5:]}.md"
    expected_result_path = f".ai/results/RESULT-{task_id[5:]}.md"
    if operation is ExecutionOperation.RUN:
        if work_ref.path != expected_task_path or prior_result_ref is not None:
            raise _error("RUN requires canonical TASK work_ref and no prior result")
        task_ref = work_ref
        contracts = context_refs
        result_ref = None
        review_ref = None
        phase = ContinuityPhase.RUNNING
    else:
        if work_ref.path != expected_review_path:
            raise _error("FIX requires canonical REVIEW work_ref")
        task_matches = tuple(ref for ref in context_refs if ref.path == expected_task_path)
        if len(task_matches) != 1:
            raise _error("FIX context_refs must contain exactly one canonical TASK ref")
        if type(prior_result_ref) is not ArtifactRef or prior_result_ref.path != expected_result_path:
            raise _error("FIX requires the canonical prior RESULT ref")
        task_ref = task_matches[0]
        contracts = tuple(ref for ref in context_refs if ref.path != expected_task_path)
        result_ref = prior_result_ref
        review_ref = work_ref
        phase = ContinuityPhase.FIXING

    validate_executor_lease_binding(
        executor_lease,
        task_id=task_id,
        workspace_id=authorization_binding.workspace_id,
        executor_id=executor_id,
        operation=operation,
        execution_fingerprint=authorization_binding.execution_fingerprint,
    )
    binding_expectations = {
        "schema_version": SCHEMA_VERSION,
        "task_id": task_id,
        "operation": operation,
        "executor_id": executor_id,
        "target_branch": target_branch,
        "artifact_path": work_ref.path,
        "artifact_blob_sha": work_ref.blob_sha,
        "lease_id": executor_lease.lease_id,
        "lease_fingerprint": executor_lease.fingerprint(),
        "workspace_id": executor_lease.workspace_id,
        "execution_fingerprint": executor_lease.execution_fingerprint,
        "status": "ACTIVE",
    }
    for field_name, expected in binding_expectations.items():
        if getattr(authorization_binding, field_name) != expected:
            raise _error(f"authorization binding {field_name} mismatch")

    state = ContinuityState(
        schema_version=SCHEMA_VERSION,
        task_id=task_id,
        phase=phase,
        next_operation=NextOperation.WAIT_FOR_RESULT,
        main=BranchState(branch=main_branch, sha=main_sha),
        task_branch=BranchState(branch=target_branch, sha=task_head_sha),
        artifacts=ContinuityArtifacts(
            task=task_ref,
            contracts=contracts,
            result=result_ref,
            review=review_ref,
        ),
        brain=BrainState(),
        executor=ExecutorState(last_id=executor_id),
    )
    observed_refs = [state.artifacts.task, *state.artifacts.contracts]
    if state.artifacts.result is not None:
        observed_refs.append(state.artifacts.result)
    if state.artifacts.review is not None:
        observed_refs.append(state.artifacts.review)
    freshness = check_freshness(
        state,
        StateObservation(
            main_sha=main_sha,
            task_branch_sha=task_head_sha,
            artifact_blobs={ref.path: ref.blob_sha for ref in observed_refs},
        ),
    )
    if freshness.status is not FreshnessStatus.FRESH:
        raise _error(f"Launch ContinuityState is not fresh: {freshness.status.value}")

    ids = derive_executor_automation_ids(task_id, executor_lease.fingerprint())
    request = ExecutionRequest(
        schema_version=SCHEMA_VERSION,
        task_id=task_id,
        request_id=ids.request_id,
        executor_id=executor_id,
        operation=operation,
        state_fingerprint=state.fingerprint(),
        target_branch=target_branch,
        expected_task_head_sha=task_head_sha,
        work_ref=work_ref,
        context_refs=context_refs,
        required_capabilities=required_capabilities,
        expected_result_path=expected_result_path,
    )
    validate_execution_request_against_state(request, state)
    validate_executor_eligibility(request, executor_capabilities)
    prepared = PreparedExecution(
        schema_version=SCHEMA_VERSION,
        task_id=task_id,
        request_id=request.request_id,
        executor_id=executor_id,
        execution_id=ids.execution_id,
        request_fingerprint=request.fingerprint(),
    )
    validate_prepared_execution_against_request(prepared, request)
    context_pack = build_executor_context_pack(
        request,
        prepared,
        executor_lease,
        authorization_binding,
        artifact_payloads,
        invocation_id=ids.invocation_id,
        transport_id=transport_id,
    )
    if (fix_context_pack is None) != (fix_impact_analysis is None):
        raise _error("Slice-C FIX context pack and impact analysis must be supplied together")
    if fix_context_pack is not None:
        if operation is not ExecutionOperation.FIX:
            raise _error("Slice-C context is valid only for FIX launch plans")
        if type(fix_context_pack) is not FixContextPack or type(fix_impact_analysis) is not FixImpactAnalysis:
            raise _error("Slice-C launch evidence must use exact contract types")
        context_pack = augment_executor_context_pack_for_fix(
            context_pack,
            fix_context_pack,
            fix_impact_analysis,
        )
    task_payload = artifact_payloads[task_ref.path]
    try:
        task_content = task_payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise _error("canonical task payload must be strict UTF-8") from exc
    validation_plan = validation_plan_for_task(task_content)
    return ExecutorAutomationLaunchPlan(
        state, request, prepared, context_pack, validation_plan
    )


def validate_executor_worktree_delta(
    *,
    pre_branch: str,
    post_branch: str,
    pre_head_sha: str,
    post_head_sha: str,
    dirty_paths: Sequence[str],
    allowed_paths: Sequence[str],
) -> tuple[str, ...]:
    if type(pre_branch) is not str or not pre_branch or pre_branch != post_branch:
        raise _error("Executor changed the authorized branch")
    if (
        type(pre_head_sha) is not str
        or not _BLOB_SHA_RE.fullmatch(pre_head_sha)
        or type(post_head_sha) is not str
        or not _BLOB_SHA_RE.fullmatch(post_head_sha)
        or pre_head_sha != post_head_sha
    ):
        raise _error("Executor changed the authorized HEAD")
    if isinstance(dirty_paths, (str, bytes)) or not isinstance(dirty_paths, Sequence):
        raise _error("dirty_paths must be a sequence")
    if isinstance(allowed_paths, (str, bytes)) or not isinstance(allowed_paths, Sequence):
        raise _error("allowed_paths must be a sequence")
    allowed = {_validate_allowed_path(path, "allowed_paths") for path in allowed_paths}
    if len(allowed) != len(allowed_paths):
        raise _error("allowed_paths must be unique")
    dirty = {_validate_repo_path(path, "dirty_paths") for path in dirty_paths}
    if len(dirty) != len(dirty_paths):
        raise _error("dirty_paths must be unique")
    if not dirty:
        raise _error("Executor produced no worktree delta")
    out_of_scope = sorted(dirty - allowed)
    if out_of_scope:
        raise _error(f"Executor modified out-of-scope paths: {out_of_scope}")
    return tuple(sorted(dirty))


def build_published_execution_result(
    request: ExecutionRequest,
    *,
    published_sha: str,
    result_ref: ArtifactRef,
) -> ExecutionResult:
    if type(request) is not ExecutionRequest:
        raise _error("request must be an exact ExecutionRequest")
    result = ExecutionResult(
        schema_version=request.schema_version,
        task_id=request.task_id,
        request_id=request.request_id,
        executor_id=request.executor_id,
        operation=request.operation,
        status=ExecutionResultStatus.SUCCESS,
        implementation_sha=published_sha,
        result_ref=result_ref,
        evidence_refs=(),
        error_code=None,
    )
    validate_execution_result_against_request(result, request)
    return result


__all__ = [
    "EXECUTOR_ALLOWED_PATHS_MARKER",
    "EXECUTOR_CONTEXT_REFS_MARKER",
    "MAX_AUTOMATION_CONTEXT_REFS",
    "ExecutorAutomationIds",
    "ExecutorAutomationLaunchPlan",
    "ExecutorAutomationMarkers",
    "ExecutorContextRefSpec",
    "build_executor_automation_launch_plan",
    "build_published_execution_result",
    "derive_executor_automation_ids",
    "parse_executor_automation_markers",
    "validate_executor_worktree_delta",
]
