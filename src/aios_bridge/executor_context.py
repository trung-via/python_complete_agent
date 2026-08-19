"""Pure bounded Executor context-pack composition (ADR-031 / E3)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import re
from typing import Any, Mapping

from src.aios_bridge.continuity.errors import ContinuityStateValidationError
from src.aios_bridge.continuity.executor import (
    ExecutionCapability,
    ExecutionOperation,
    ExecutionRequest,
    PreparedExecution,
    validate_prepared_execution_against_request,
)
from src.aios_bridge.continuity.executor_transport import (
    MAX_INVOCATION_PAYLOAD_BYTES,
    ExecutorInvocation,
    validate_executor_invocation,
    validate_invocation_payload,
)
from src.aios_bridge.continuity.lease import (
    ExecutorLease,
    validate_executor_lease_binding,
)
from src.aios_bridge.continuity.state import ArtifactRef, SCHEMA_VERSION


CONTEXT_FORMAT_VERSION = "aios-executor-context-v1"
CONTEXT_INSTRUCTION_PROFILE = "thin-executor-v1"
ACTIVE_AUTHORIZATION_STATUS = "ACTIVE"

MAX_CONTEXT_ARTIFACTS = 8
MAX_CONTEXT_ARTIFACT_BYTES = 131_072
MAX_CONTEXT_RAW_ARTIFACT_BYTES = 196_608
MAX_CONTEXT_PACK_BYTES = 262_144

_MAX_CANONICAL_ID_LENGTH = 64
_TASK_ID_PATTERN = re.compile(r"^TASK-\d+$")
_CANONICAL_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:[a-z0-9._\-:]+)*$")
_GIT_BLOB_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_FINGERPRINT_PATTERN = re.compile(r"^[0-9a-f]{64}$")

_FIXED_INSTRUCTION_BLOCK = """AUTHORITY NOTICE
This context pack is transport material bound to externally verified authorization evidence. The pack itself does not grant or extend RUN, FIX, or MERGE authority.

THIN EXECUTOR RULES
- Obey the exact WORK artifact and bounded CONTEXT artifacts below.
- Do not redesign or widen scope beyond those artifacts.
- Do not self-select or change the executor.
- Do not mutate Bridge authorization, lease, dispatch, failover, or hot-handoff state.
- Do not commit, push, publish RESULT, or merge.
- Run only executor-side targeted tests authorized by the control artifacts.
- Stop after bounded implementation/testing and report files changed, test results, and blockers to the caller."""


def _validation_error(message: str) -> ContinuityStateValidationError:
    return ContinuityStateValidationError(message)


def _validate_exact_string(value: object, field_name: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise _validation_error(f"{field_name} must be an exact non-empty string")
    return value


def _validate_task_id(value: object, field_name: str = "task_id") -> str:
    if type(value) is not str or not _TASK_ID_PATTERN.fullmatch(value):
        raise _validation_error(f"{field_name} must match exact case-sensitive TASK-<digits>")
    return value


def _validate_canonical_id(value: object, field_name: str) -> str:
    if (
        type(value) is not str
        or not value
        or value != value.strip()
        or len(value) > _MAX_CANONICAL_ID_LENGTH
        or not _CANONICAL_ID_PATTERN.fullmatch(value)
    ):
        raise _validation_error(f"{field_name} must be a bounded canonical lowercase ID")
    return value


def _validate_git_blob_sha(value: object, field_name: str) -> str:
    if type(value) is not str or not _GIT_BLOB_SHA_PATTERN.fullmatch(value):
        raise _validation_error(f"{field_name} must be an exact lowercase Git blob SHA-1")
    return value


def _validate_fingerprint(value: object, field_name: str) -> str:
    if type(value) is not str or not _FINGERPRINT_PATTERN.fullmatch(value):
        raise _validation_error(f"{field_name} must be an exact lowercase SHA-256 fingerprint")
    return value


def _validate_operation(value: object, field_name: str = "operation") -> ExecutionOperation:
    if isinstance(value, ExecutionOperation):
        return value
    try:
        return ExecutionOperation(value)
    except (TypeError, ValueError) as exc:
        raise _validation_error(f"{field_name} must be exact RUN or FIX") from exc


@dataclass(frozen=True)
class ExecutorAuthorizationBinding:
    schema_version: str
    task_id: str
    operation: ExecutionOperation
    executor_id: str
    target_branch: str
    artifact_path: str
    artifact_blob_sha: str
    lease_id: str
    lease_fingerprint: str
    workspace_id: str
    execution_fingerprint: str
    status: str = ACTIVE_AUTHORIZATION_STATUS

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise _validation_error("Unsupported schema_version in ExecutorAuthorizationBinding")
        _validate_task_id(self.task_id)
        object.__setattr__(self, "operation", _validate_operation(self.operation))
        _validate_canonical_id(self.executor_id, "executor_id")
        _validate_exact_string(self.target_branch, "target_branch")
        _validate_exact_string(self.artifact_path, "artifact_path")
        _validate_git_blob_sha(self.artifact_blob_sha, "artifact_blob_sha")
        _validate_canonical_id(self.lease_id, "lease_id")
        _validate_fingerprint(self.lease_fingerprint, "lease_fingerprint")
        _validate_fingerprint(self.workspace_id, "workspace_id")
        _validate_fingerprint(self.execution_fingerprint, "execution_fingerprint")
        if type(self.status) is not str or self.status != ACTIVE_AUTHORIZATION_STATUS:
            raise _validation_error("authorization binding status must be exact ACTIVE")

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_blob_sha": self.artifact_blob_sha,
            "artifact_path": self.artifact_path,
            "execution_fingerprint": self.execution_fingerprint,
            "executor_id": self.executor_id,
            "lease_fingerprint": self.lease_fingerprint,
            "lease_id": self.lease_id,
            "operation": self.operation.value,
            "schema_version": self.schema_version,
            "status": self.status,
            "target_branch": self.target_branch,
            "task_id": self.task_id,
            "workspace_id": self.workspace_id,
        }

    def to_canonical_json(self) -> str:
        return json.dumps(
            self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )

    def fingerprint(self) -> str:
        return hashlib.sha256(self.to_canonical_json().encode("utf-8")).hexdigest()


class ContextArtifactRole(str, Enum):
    WORK = "WORK"
    CONTEXT = "CONTEXT"


@dataclass(frozen=True)
class ContextArtifactManifestEntry:
    role: ContextArtifactRole
    ordinal: int
    path: str
    ref: str
    blob_sha: str
    content_sha256: str
    size_bytes: int

    def __post_init__(self) -> None:
        if not isinstance(self.role, ContextArtifactRole):
            raise _validation_error("role must be an exact ContextArtifactRole")
        if type(self.ordinal) is not int or self.ordinal < 0:
            raise _validation_error("ordinal must be an exact non-negative integer")
        _validate_exact_string(self.path, "path")
        _validate_exact_string(self.ref, "ref")
        _validate_git_blob_sha(self.blob_sha, "blob_sha")
        _validate_fingerprint(self.content_sha256, "content_sha256")
        if (
            type(self.size_bytes) is not int
            or not 1 <= self.size_bytes <= MAX_CONTEXT_ARTIFACT_BYTES
        ):
            raise _validation_error("size_bytes must be an exact bounded positive integer")

    def to_dict(self) -> dict[str, Any]:
        return {
            "blob_sha": self.blob_sha,
            "content_sha256": self.content_sha256,
            "ordinal": self.ordinal,
            "path": self.path,
            "ref": self.ref,
            "role": self.role.value,
            "size_bytes": self.size_bytes,
        }


@dataclass(frozen=True)
class ExecutorContextManifest:
    schema_version: str
    format_version: str
    instruction_profile: str
    task_id: str
    operation: ExecutionOperation
    request_id: str
    executor_id: str
    transport_id: str
    target_branch: str
    workspace_id: str
    execution_id: str
    request_fingerprint: str
    prepared_execution_fingerprint: str
    lease_id: str
    lease_fingerprint: str
    execution_fingerprint: str
    authorization_binding_fingerprint: str
    expected_task_head_sha: str | None
    expected_result_path: str
    required_capabilities: tuple[ExecutionCapability, ...]
    artifacts: tuple[ContextArtifactManifestEntry, ...]

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise _validation_error("Unsupported schema_version in ExecutorContextManifest")
        if self.format_version != CONTEXT_FORMAT_VERSION:
            raise _validation_error("Unsupported context format_version")
        if self.instruction_profile != CONTEXT_INSTRUCTION_PROFILE:
            raise _validation_error("Unsupported context instruction_profile")
        _validate_task_id(self.task_id)
        object.__setattr__(self, "operation", _validate_operation(self.operation))
        _validate_canonical_id(self.request_id, "request_id")
        _validate_canonical_id(self.executor_id, "executor_id")
        _validate_canonical_id(self.transport_id, "transport_id")
        _validate_exact_string(self.target_branch, "target_branch")
        _validate_fingerprint(self.workspace_id, "workspace_id")
        _validate_canonical_id(self.execution_id, "execution_id")
        _validate_fingerprint(self.request_fingerprint, "request_fingerprint")
        _validate_fingerprint(
            self.prepared_execution_fingerprint, "prepared_execution_fingerprint"
        )
        _validate_canonical_id(self.lease_id, "lease_id")
        _validate_fingerprint(self.lease_fingerprint, "lease_fingerprint")
        _validate_fingerprint(self.execution_fingerprint, "execution_fingerprint")
        _validate_fingerprint(
            self.authorization_binding_fingerprint,
            "authorization_binding_fingerprint",
        )
        if self.expected_task_head_sha is not None:
            _validate_git_blob_sha(self.expected_task_head_sha, "expected_task_head_sha")
        _validate_exact_string(self.expected_result_path, "expected_result_path")

        if type(self.required_capabilities) is not tuple:
            raise _validation_error("required_capabilities must be an exact tuple")
        seen_capabilities: set[ExecutionCapability] = set()
        for capability in self.required_capabilities:
            if not isinstance(capability, ExecutionCapability):
                raise _validation_error("required_capabilities must contain exact enum values")
            if capability in seen_capabilities:
                raise _validation_error("required_capabilities must be unique")
            seen_capabilities.add(capability)

        if type(self.artifacts) is not tuple or not 1 <= len(self.artifacts) <= MAX_CONTEXT_ARTIFACTS:
            raise _validation_error("artifacts must be an exact bounded non-empty tuple")
        seen_paths: set[str] = set()
        for ordinal, entry in enumerate(self.artifacts):
            if not isinstance(entry, ContextArtifactManifestEntry):
                raise _validation_error("artifacts must contain manifest entries")
            if entry.ordinal != ordinal:
                raise _validation_error("artifact ordinals must be contiguous from zero")
            expected_role = (
                ContextArtifactRole.WORK
                if ordinal == 0
                else ContextArtifactRole.CONTEXT
            )
            if entry.role is not expected_role:
                raise _validation_error("artifact roles must be WORK then CONTEXT")
            if entry.path in seen_paths:
                raise _validation_error("artifact paths must be unique")
            seen_paths.add(entry.path)

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifacts": [entry.to_dict() for entry in self.artifacts],
            "authorization_binding_fingerprint": self.authorization_binding_fingerprint,
            "execution_fingerprint": self.execution_fingerprint,
            "execution_id": self.execution_id,
            "executor_id": self.executor_id,
            "expected_result_path": self.expected_result_path,
            "expected_task_head_sha": self.expected_task_head_sha,
            "format_version": self.format_version,
            "instruction_profile": self.instruction_profile,
            "lease_fingerprint": self.lease_fingerprint,
            "lease_id": self.lease_id,
            "operation": self.operation.value,
            "prepared_execution_fingerprint": self.prepared_execution_fingerprint,
            "request_fingerprint": self.request_fingerprint,
            "request_id": self.request_id,
            "required_capabilities": [
                capability.value for capability in self.required_capabilities
            ],
            "schema_version": self.schema_version,
            "target_branch": self.target_branch,
            "task_id": self.task_id,
            "transport_id": self.transport_id,
            "workspace_id": self.workspace_id,
        }

    def to_canonical_json(self) -> str:
        return json.dumps(
            self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )

    def fingerprint(self) -> str:
        return hashlib.sha256(self.to_canonical_json().encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ExecutorContextPack:
    manifest: ExecutorContextManifest
    payload: bytes
    invocation: ExecutorInvocation

    def __post_init__(self) -> None:
        if type(self.manifest) is not ExecutorContextManifest:
            raise _validation_error("manifest must be an exact ExecutorContextManifest")
        if type(self.payload) is not bytes or not self.payload:
            raise _validation_error("payload must be exact non-empty bytes")
        if len(self.payload) > MAX_CONTEXT_PACK_BYTES:
            raise _validation_error("payload exceeds MAX_CONTEXT_PACK_BYTES")
        if type(self.invocation) is not ExecutorInvocation:
            raise _validation_error("invocation must be an exact ExecutorInvocation")
        validate_invocation_payload(self.invocation, self.payload)

        shared = {
            "task_id": self.manifest.task_id,
            "operation": self.manifest.operation,
            "request_id": self.manifest.request_id,
            "executor_id": self.manifest.executor_id,
            "transport_id": self.manifest.transport_id,
            "target_branch": self.manifest.target_branch,
            "workspace_id": self.manifest.workspace_id,
            "execution_id": self.manifest.execution_id,
            "request_fingerprint": self.manifest.request_fingerprint,
            "prepared_execution_fingerprint": self.manifest.prepared_execution_fingerprint,
            "lease_fingerprint": self.manifest.lease_fingerprint,
            "execution_fingerprint": self.manifest.execution_fingerprint,
        }
        for field_name, expected in shared.items():
            if getattr(self.invocation, field_name) != expected:
                raise _validation_error(
                    f"manifest {field_name} does not match ExecutorInvocation"
                )


def _git_blob_sha1(content: bytes) -> str:
    header = b"blob " + str(len(content)).encode("ascii") + b"\0"
    return hashlib.sha1(header + content).hexdigest()


def _validate_artifact_content(
    ref: ArtifactRef,
    payload: object,
    *,
    role: ContextArtifactRole,
    ordinal: int,
) -> ContextArtifactManifestEntry:
    if type(ref) is not ArtifactRef:
        raise _validation_error("artifact ref must be an exact ArtifactRef")
    if type(payload) is not bytes:
        raise _validation_error("artifact payload must be exact bytes")
    if not payload:
        raise _validation_error("artifact payload must not be empty")
    if len(payload) > MAX_CONTEXT_ARTIFACT_BYTES:
        raise _validation_error("artifact payload exceeds MAX_CONTEXT_ARTIFACT_BYTES")
    if b"\x00" in payload:
        raise _validation_error("artifact payload must not contain NUL bytes")
    try:
        payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise _validation_error("artifact payload must be valid UTF-8") from exc
    if _git_blob_sha1(payload) != ref.blob_sha:
        raise _validation_error("artifact payload does not match exact Git blob SHA-1")
    return ContextArtifactManifestEntry(
        role=role,
        ordinal=ordinal,
        path=ref.path,
        ref=ref.ref,
        blob_sha=ref.blob_sha,
        content_sha256=hashlib.sha256(payload).hexdigest(),
        size_bytes=len(payload),
    )


def _validate_authorization_binding(
    binding: ExecutorAuthorizationBinding,
    request: ExecutionRequest,
    prepared: PreparedExecution,
    lease: ExecutorLease,
) -> None:
    if type(binding) is not ExecutorAuthorizationBinding:
        raise _validation_error("authorization_binding must be exact binding evidence")
    if type(request) is not ExecutionRequest:
        raise _validation_error("execution_request must be an exact ExecutionRequest")
    if type(prepared) is not PreparedExecution:
        raise _validation_error("prepared_execution must be an exact PreparedExecution")
    if type(lease) is not ExecutorLease:
        raise _validation_error("executor_lease must be an exact ExecutorLease")

    validate_prepared_execution_against_request(prepared, request)
    request_fields = {
        "schema_version": request.schema_version,
        "task_id": request.task_id,
        "operation": request.operation,
        "executor_id": request.executor_id,
        "target_branch": request.target_branch,
        "artifact_path": request.work_ref.path,
        "artifact_blob_sha": request.work_ref.blob_sha,
    }
    for field_name, expected in request_fields.items():
        if getattr(binding, field_name) != expected:
            raise _validation_error(
                f"authorization binding {field_name} does not match ExecutionRequest"
            )

    lease_fields = {
        "schema_version": lease.schema_version,
        "task_id": lease.task_id,
        "operation": lease.operation,
        "executor_id": lease.executor_id,
        "lease_id": lease.lease_id,
        "lease_fingerprint": lease.fingerprint(),
        "workspace_id": lease.workspace_id,
        "execution_fingerprint": lease.execution_fingerprint,
    }
    for field_name, expected in lease_fields.items():
        if getattr(binding, field_name) != expected:
            raise _validation_error(
                f"authorization binding {field_name} does not match ExecutorLease"
            )

    validate_executor_lease_binding(
        lease,
        task_id=request.task_id,
        workspace_id=binding.workspace_id,
        executor_id=request.executor_id,
        operation=request.operation,
        execution_fingerprint=binding.execution_fingerprint,
    )


def _validate_artifact_set(
    request: ExecutionRequest,
    artifact_payloads: Mapping[str, bytes],
) -> tuple[tuple[ContextArtifactManifestEntry, bytes], ...]:
    ordered_refs = (request.work_ref, *request.context_refs)
    if not 1 <= len(ordered_refs) <= MAX_CONTEXT_ARTIFACTS:
        raise _validation_error("artifact count exceeds MAX_CONTEXT_ARTIFACTS")
    paths = [ref.path for ref in ordered_refs]
    if len(set(paths)) != len(paths):
        raise _validation_error("artifact paths must be unique")
    if not isinstance(artifact_payloads, Mapping):
        raise _validation_error("artifact_payloads must be a Mapping")
    keys = tuple(artifact_payloads.keys())
    if any(type(key) is not str for key in keys):
        raise _validation_error("artifact_payloads keys must be exact strings")
    if set(keys) != set(paths):
        raise _validation_error("artifact_payloads key set must exactly match request refs")

    ordered: list[tuple[ContextArtifactManifestEntry, bytes]] = []
    total_size = 0
    for ordinal, ref in enumerate(ordered_refs):
        payload = artifact_payloads[ref.path]
        role = ContextArtifactRole.WORK if ordinal == 0 else ContextArtifactRole.CONTEXT
        entry = _validate_artifact_content(
            ref,
            payload,
            role=role,
            ordinal=ordinal,
        )
        total_size += entry.size_bytes
        ordered.append((entry, payload))
    if total_size > MAX_CONTEXT_RAW_ARTIFACT_BYTES:
        raise _validation_error(
            "aggregate artifact bytes exceed MAX_CONTEXT_RAW_ARTIFACT_BYTES"
        )
    return tuple(ordered)


def _render_payload(
    manifest: ExecutorContextManifest,
    ordered: tuple[tuple[ContextArtifactManifestEntry, bytes], ...],
) -> bytes:
    parts: list[bytes] = [
        b"AIOS_EXECUTOR_CONTEXT_PACK_V1\n",
        _FIXED_INSTRUCTION_BLOCK.encode("utf-8"),
        b"\n",
        f"MANIFEST_SHA256: {manifest.fingerprint()}\n".encode("utf-8"),
        f"MANIFEST_JSON: {manifest.to_canonical_json()}\n\n".encode("utf-8"),
    ]
    for entry, content in ordered:
        parts.append(
            (
                f"ARTIFACT {entry.ordinal} BEGIN\n"
                f"ROLE: {entry.role.value}\n"
                f"PATH: {entry.path}\n"
                f"REF: {entry.ref}\n"
                f"BLOB_SHA: {entry.blob_sha}\n"
                f"CONTENT_SHA256: {entry.content_sha256}\n"
                f"SIZE_BYTES: {entry.size_bytes}\n"
                "CONTENT_BEGIN\n"
            ).encode("utf-8")
        )
        parts.append(content)
        parts.append(
            f"\nCONTENT_END\nARTIFACT {entry.ordinal} END\n\n".encode("utf-8")
        )
    parts.append(b"AIOS_EXECUTOR_CONTEXT_PACK_END\n")
    payload = b"".join(parts)
    try:
        payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise _validation_error("rendered context pack must be valid UTF-8") from exc
    if not payload:
        raise _validation_error("rendered context pack must not be empty")
    if MAX_CONTEXT_PACK_BYTES > MAX_INVOCATION_PAYLOAD_BYTES:
        raise _validation_error("E3 context pack bound exceeds E1 payload bound")
    if len(payload) > MAX_CONTEXT_PACK_BYTES:
        raise _validation_error("rendered payload exceeds MAX_CONTEXT_PACK_BYTES")
    if len(payload) > MAX_INVOCATION_PAYLOAD_BYTES:
        raise _validation_error("rendered payload exceeds E1 payload bound")
    return payload


def build_executor_context_pack(
    execution_request: ExecutionRequest,
    prepared_execution: PreparedExecution,
    executor_lease: ExecutorLease,
    authorization_binding: ExecutorAuthorizationBinding,
    artifact_payloads: Mapping[str, bytes],
    *,
    invocation_id: str,
    transport_id: str,
) -> ExecutorContextPack:
    _validate_authorization_binding(
        authorization_binding,
        execution_request,
        prepared_execution,
        executor_lease,
    )
    ordered = _validate_artifact_set(execution_request, artifact_payloads)
    entries = tuple(entry for entry, _ in ordered)

    manifest = ExecutorContextManifest(
        schema_version=execution_request.schema_version,
        format_version=CONTEXT_FORMAT_VERSION,
        instruction_profile=CONTEXT_INSTRUCTION_PROFILE,
        task_id=execution_request.task_id,
        operation=execution_request.operation,
        request_id=execution_request.request_id,
        executor_id=execution_request.executor_id,
        transport_id=transport_id,
        target_branch=execution_request.target_branch,
        workspace_id=executor_lease.workspace_id,
        execution_id=prepared_execution.execution_id,
        request_fingerprint=execution_request.fingerprint(),
        prepared_execution_fingerprint=prepared_execution.fingerprint(),
        lease_id=executor_lease.lease_id,
        lease_fingerprint=executor_lease.fingerprint(),
        execution_fingerprint=executor_lease.execution_fingerprint,
        authorization_binding_fingerprint=authorization_binding.fingerprint(),
        expected_task_head_sha=execution_request.expected_task_head_sha,
        expected_result_path=execution_request.expected_result_path,
        required_capabilities=execution_request.required_capabilities,
        artifacts=entries,
    )
    payload = _render_payload(manifest, ordered)
    invocation = ExecutorInvocation(
        schema_version=execution_request.schema_version,
        invocation_id=invocation_id,
        task_id=execution_request.task_id,
        request_id=execution_request.request_id,
        executor_id=execution_request.executor_id,
        transport_id=transport_id,
        operation=execution_request.operation,
        workspace_id=executor_lease.workspace_id,
        target_branch=execution_request.target_branch,
        execution_id=prepared_execution.execution_id,
        request_fingerprint=execution_request.fingerprint(),
        prepared_execution_fingerprint=prepared_execution.fingerprint(),
        lease_fingerprint=executor_lease.fingerprint(),
        execution_fingerprint=executor_lease.execution_fingerprint,
        payload_sha256=hashlib.sha256(payload).hexdigest(),
        payload_size_bytes=len(payload),
    )
    validate_executor_invocation(
        invocation,
        execution_request,
        prepared_execution,
        executor_lease,
    )
    validate_invocation_payload(invocation, payload)
    return ExecutorContextPack(
        manifest=manifest,
        payload=payload,
        invocation=invocation,
    )


__all__ = [
    "ACTIVE_AUTHORIZATION_STATUS",
    "CONTEXT_FORMAT_VERSION",
    "CONTEXT_INSTRUCTION_PROFILE",
    "MAX_CONTEXT_ARTIFACTS",
    "MAX_CONTEXT_ARTIFACT_BYTES",
    "MAX_CONTEXT_RAW_ARTIFACT_BYTES",
    "MAX_CONTEXT_PACK_BYTES",
    "ContextArtifactRole",
    "ContextArtifactManifestEntry",
    "ExecutorAuthorizationBinding",
    "ExecutorContextManifest",
    "ExecutorContextPack",
    "build_executor_context_pack",
]
