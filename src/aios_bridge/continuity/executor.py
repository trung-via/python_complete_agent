"""
Executor-Neutral Contract for Open Multi-Agent Continuity OS (ADR-010 Milestone 4 / ADR-018 / TASK-028).
Provides vendor-neutral, transport-neutral execution request, result, capability, and preparation models.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import re
from typing import Any, Mapping, Protocol, Sequence, runtime_checkable

from .errors import ContinuityStateValidationError
from .state import (
    MAX_SERIALIZED_BYTES,
    SCHEMA_VERSION,
    ArtifactRef,
    ContinuityState,
    _validate_actor_id,
    _validate_artifact_path,
    _validate_exact_hex_sha,
    _validate_safe_git_ref,
)

_TASK_ID_PATTERN = re.compile(r"^TASK-\d+$")
_REQUEST_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:[a-z0-9_.\-:]+)*$")
_ERROR_CODE_PATTERN = re.compile(r"^[A-Za-z0-9_.\-]+$")
_TASK_TOKEN_PATTERN = re.compile(r"(?<![A-Za-z0-9])(TASK-\d+)(?![A-Za-z0-9])")
_REVIEW_TOKEN_PATTERN = re.compile(r"(?<![A-Za-z0-9])(REVIEW-\d+)(?![A-Za-z0-9])")
_RESULT_TOKEN_PATTERN = re.compile(r"(?<![A-Za-z0-9])(RESULT-\d+)(?![A-Za-z0-9])")

MAX_REQUEST_ID_LENGTH = 64
MAX_ERROR_CODE_LENGTH = 64
MAX_CONTEXT_REFS = 32
MAX_EVIDENCE_REFS = 32

FORBIDDEN_AUTHORITY_KEYS = {
    "approved",
    "human_approved",
    "authorization_token",
    "api_key",
    "cookie",
    "cookies",
    "auth_header",
    "session_secret",
    "merge_allowed",
    "token",
    "auth",
}


class ExecutionOperation(str, Enum):
    """Canonical M4 Executor operation domain (RUN and FIX only; MERGE is forbidden)."""
    RUN = "RUN"
    FIX = "FIX"


class ExecutionResultStatus(str, Enum):
    """Execution resolution status of an executor task invocation."""
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REJECTED = "REJECTED"
    INCOMPLETE = "INCOMPLETE"


class ExecutionCapability(str, Enum):
    """Closed vocabulary of vendor-neutral declarative execution capabilities."""
    REPOSITORY_READ = "REPOSITORY_READ"
    FILESYSTEM_WRITE = "FILESYSTEM_WRITE"
    SHELL = "SHELL"
    TEST_EXECUTION = "TEST_EXECUTION"
    LOCAL_GIT = "LOCAL_GIT"
    BROWSER = "BROWSER"


def _validate_task_id(task_id: Any, field_name: str = "task_id") -> str:
    if isinstance(task_id, bool) or not isinstance(task_id, str):
        raise ContinuityStateValidationError(f"{field_name} must be a non-empty string")
    if not _TASK_ID_PATTERN.match(task_id):
        raise ContinuityStateValidationError(
            f"{field_name} must match exact case-sensitive '^TASK-\\d+$', got: {task_id!r}"
        )
    return task_id


def _validate_canonical_actor_id(actor_id: Any, field_name: str) -> str:
    """Validates exact canonical actor ID with zero whitespace padding."""
    if isinstance(actor_id, bool) or not isinstance(actor_id, str):
        raise ContinuityStateValidationError(f"{field_name} must be a non-empty string")
    if actor_id != actor_id.strip() or not actor_id:
        raise ContinuityStateValidationError(
            f"{field_name} must not contain leading or trailing whitespace: {actor_id!r}"
        )
    canonical = _validate_actor_id(actor_id, field_name)
    if actor_id != canonical:
        raise ContinuityStateValidationError(
            f"{field_name} must be exact canonical actor ID, got: {actor_id!r}"
        )
    return canonical


def _validate_canonical_request_id(request_id: Any, field_name: str = "request_id") -> str:
    """Validates exact canonical request/execution ID with zero whitespace padding."""
    if isinstance(request_id, bool) or not isinstance(request_id, str) or not request_id:
        raise ContinuityStateValidationError(f"{field_name} must be a non-empty string")
    if request_id != request_id.strip():
        raise ContinuityStateValidationError(
            f"{field_name} must not contain leading or trailing whitespace: {request_id!r}"
        )
    if len(request_id) > MAX_REQUEST_ID_LENGTH:
        raise ContinuityStateValidationError(
            f"{field_name} length ({len(request_id)}) exceeds maximum allowed ({MAX_REQUEST_ID_LENGTH})"
        )
    if not _REQUEST_ID_PATTERN.match(request_id):
        raise ContinuityStateValidationError(
            f"{field_name} must be a conservative lowercase identifier (e.g. 'req-task-028-01'), got: {request_id!r}"
        )
    return request_id


def _validate_canonical_safe_git_ref(ref: Any, field_name: str) -> str:
    """Validates exact canonical safe git ref with zero whitespace padding."""
    if isinstance(ref, bool) or not isinstance(ref, str) or not ref:
        raise ContinuityStateValidationError(f"{field_name} must be a non-empty string")
    if ref != ref.strip():
        raise ContinuityStateValidationError(
            f"{field_name} must not contain leading or trailing whitespace: {ref!r}"
        )
    canonical = _validate_safe_git_ref(ref, field_name)
    if ref != canonical:
        raise ContinuityStateValidationError(
            f"{field_name} must be exact canonical git ref, got: {ref!r}"
        )
    return canonical


def _validate_canonical_artifact_path(path: Any, field_name: str) -> str:
    """Validates exact canonical artifact path with zero whitespace padding."""
    if isinstance(path, bool) or not isinstance(path, str) or not path:
        raise ContinuityStateValidationError(f"{field_name} must be a non-empty string")
    if path != path.strip():
        raise ContinuityStateValidationError(
            f"{field_name} must not contain leading or trailing whitespace: {path!r}"
        )
    canonical = _validate_artifact_path(path, field_name)
    if path != canonical:
        raise ContinuityStateValidationError(
            f"{field_name} must be exact canonical artifact path, got: {path!r}"
        )
    return canonical


def _validate_exact_state_fingerprint(fp: Any, field_name: str = "state_fingerprint") -> str:
    if isinstance(fp, bool) or not isinstance(fp, str) or not fp:
        raise ContinuityStateValidationError(f"{field_name} must be a non-empty string")
    if fp != fp.strip():
        raise ContinuityStateValidationError(
            f"{field_name} must not contain leading or trailing whitespace: {fp!r}"
        )
    if not re.match(r"^[0-9a-f]{64}$", fp):
        raise ContinuityStateValidationError(
            f"{field_name} must be an exact 64-character lowercase hex SHA-256 string, got: {fp!r}"
        )
    return fp


def _validate_exact_hex_sha_optional(sha: Any, field_name: str) -> str | None:
    if sha is None:
        return None
    if isinstance(sha, bool) or not isinstance(sha, str) or not sha:
        raise ContinuityStateValidationError(f"{field_name} must be a non-empty string or None")
    if sha != sha.strip():
        raise ContinuityStateValidationError(
            f"{field_name} must not contain leading or trailing whitespace: {sha!r}"
        )
    return _validate_exact_hex_sha(sha, field_name)


def _validate_work_ref_role(work_ref: ArtifactRef, operation: ExecutionOperation, task_id: str) -> None:
    """Validates exact role and active task binding for work_ref (C5 / AIP-3)."""
    if not isinstance(work_ref, ArtifactRef):
        raise ContinuityStateValidationError(
            f"work_ref must be an ArtifactRef instance, got: {type(work_ref).__name__}"
        )

    task_num_str = task_id.split("-", 1)[1]
    if operation == ExecutionOperation.RUN:
        expected_path = f".ai/tasks/{task_id}.md"
        if work_ref.path != expected_path:
            raise ContinuityStateValidationError(
                f"RUN work_ref path '{work_ref.path}' must match exact expected task path '{expected_path}'"
            )
        tokens = _TASK_TOKEN_PATTERN.findall(work_ref.path)
        if not tokens or any(t != task_id for t in tokens):
            raise ContinuityStateValidationError(
                f"RUN work_ref path '{work_ref.path}' contains invalid task token (expected '{task_id}')"
            )
    elif operation == ExecutionOperation.FIX:
        expected_path = f".ai/reviews/REVIEW-{task_num_str}.md"
        if work_ref.path != expected_path:
            raise ContinuityStateValidationError(
                f"FIX work_ref path '{work_ref.path}' must match exact expected review path '{expected_path}'"
            )
        tokens = _REVIEW_TOKEN_PATTERN.findall(work_ref.path)
        expected_token = f"REVIEW-{task_num_str}"
        if not tokens or any(t != expected_token for t in tokens):
            raise ContinuityStateValidationError(
                f"FIX work_ref path '{work_ref.path}' contains invalid review token (expected '{expected_token}')"
            )


def _validate_expected_result_path(path: str, task_id: str) -> str:
    """Validates exact expected result path for active task."""
    task_num_str = task_id.split("-", 1)[1]
    expected = f".ai/results/RESULT-{task_num_str}.md"
    if path != expected:
        raise ContinuityStateValidationError(
            f"expected_result_path '{path}' must match exact expected result path '{expected}' for {task_id}"
        )
    tokens = _RESULT_TOKEN_PATTERN.findall(path)
    expected_token = f"RESULT-{task_num_str}"
    if not tokens or any(t != expected_token for t in tokens):
        raise ContinuityStateValidationError(
            f"expected_result_path '{path}' contains invalid result token (expected '{expected_token}')"
        )
    return path


@dataclass(frozen=True)
class ExecutorCapabilities:
    """Declarative capability declaration for an execution actor (C8 / AIP-6)."""
    executor_id: str
    supported_operations: tuple[ExecutionOperation, ...]
    supported_capabilities: tuple[ExecutionCapability, ...]
    declarative_only: bool = True
    capacity_metadata: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if type(self.declarative_only) is not bool or self.declarative_only is not True:
            raise ContinuityStateValidationError(
                f"declarative_only must be boolean True in ExecutorCapabilities, got: {self.declarative_only!r}"
            )
        _validate_canonical_actor_id(self.executor_id, "executor_id")

        # supported_operations: sequence validation and deterministic sorting
        if not isinstance(self.supported_operations, (list, tuple)):
            raise ContinuityStateValidationError(
                f"supported_operations must be a list or tuple, got: {type(self.supported_operations).__name__}"
            )

        parsed_ops: list[ExecutionOperation] = []
        seen_ops: set[str] = set()
        for idx, op in enumerate(self.supported_operations):
            if not isinstance(op, ExecutionOperation):
                try:
                    op = ExecutionOperation(op)
                except Exception as e:
                    valid_ops = ", ".join(o.value for o in ExecutionOperation)
                    raise ContinuityStateValidationError(
                        f"Invalid ExecutionOperation at index {idx}: {op!r}. Valid values: {valid_ops}"
                    ) from e
            if op.value in seen_ops:
                raise ContinuityStateValidationError(
                    f"Duplicate ExecutionOperation in supported_operations: {op.value!r}"
                )
            seen_ops.add(op.value)
            parsed_ops.append(op)

        # Sort canonically by enum value order
        parsed_ops.sort(key=lambda o: o.value)
        object.__setattr__(self, "supported_operations", tuple(parsed_ops))

        # supported_capabilities: sequence validation and deterministic sorting
        if not isinstance(self.supported_capabilities, (list, tuple)):
            raise ContinuityStateValidationError(
                f"supported_capabilities must be a list or tuple, got: {type(self.supported_capabilities).__name__}"
            )

        parsed_caps: list[ExecutionCapability] = []
        seen_caps: set[str] = set()
        for idx, cap in enumerate(self.supported_capabilities):
            if not isinstance(cap, ExecutionCapability):
                try:
                    cap = ExecutionCapability(cap)
                except Exception as e:
                    valid_caps = ", ".join(c.value for c in ExecutionCapability)
                    raise ContinuityStateValidationError(
                        f"Invalid ExecutionCapability at index {idx}: {cap!r}. Valid values: {valid_caps}"
                    ) from e
            if cap.value in seen_caps:
                raise ContinuityStateValidationError(
                    f"Duplicate ExecutionCapability in supported_capabilities: {cap.value!r}"
                )
            seen_caps.add(cap.value)
            parsed_caps.append(cap)

        parsed_caps.sort(key=lambda c: c.value)
        object.__setattr__(self, "supported_capabilities", tuple(parsed_caps))

        if self.capacity_metadata is not None:
            if not isinstance(self.capacity_metadata, Mapping):
                raise ContinuityStateValidationError(
                    f"capacity_metadata must be a Mapping or None, got: {type(self.capacity_metadata).__name__}"
                )
            for k in self.capacity_metadata:
                if not isinstance(k, str) or not k:
                    raise ContinuityStateValidationError("capacity_metadata keys must be non-empty strings")
            object.__setattr__(self, "capacity_metadata", dict(self.capacity_metadata))

        raw_canonical = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        utf8_bytes = raw_canonical.encode("utf-8")
        if len(utf8_bytes) > MAX_SERIALIZED_BYTES:
            raise ContinuityStateValidationError(
                f"Serialized ExecutorCapabilities exceeds size limit ({len(utf8_bytes)} > {MAX_SERIALIZED_BYTES})"
            )

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "declarative_only": self.declarative_only,
            "executor_id": self.executor_id,
            "supported_capabilities": [c.value for c in self.supported_capabilities],
            "supported_operations": [o.value for o in self.supported_operations],
        }
        if self.capacity_metadata is not None:
            data["capacity_metadata"] = dict(self.capacity_metadata)
        return data

    def to_canonical_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    def fingerprint(self) -> str:
        return hashlib.sha256(self.to_canonical_json().encode("utf-8")).hexdigest()

    @classmethod
    def from_dict(cls, data: Any) -> ExecutorCapabilities:
        if not isinstance(data, dict):
            raise ContinuityStateValidationError(
                f"ExecutorCapabilities root must be a dict, got: {type(data).__name__}"
            )

        allowed_keys = {
            "declarative_only",
            "executor_id",
            "supported_capabilities",
            "supported_operations",
            "capacity_metadata",
        }
        extra_keys = set(data.keys()) - allowed_keys
        if extra_keys:
            raise ContinuityStateValidationError(
                f"Unknown fields in ExecutorCapabilities: {sorted(extra_keys)}"
            )

        for req in ["executor_id", "supported_operations", "supported_capabilities", "declarative_only"]:
            if req not in data:
                raise ContinuityStateValidationError(f"Missing required field '{req}' in ExecutorCapabilities")

        return cls(
            executor_id=data["executor_id"],
            supported_operations=data["supported_operations"],
            supported_capabilities=data["supported_capabilities"],
            declarative_only=data["declarative_only"],
            capacity_metadata=data.get("capacity_metadata"),
        )

    @classmethod
    def from_json(cls, json_str: str | bytes) -> ExecutorCapabilities:
        if isinstance(json_str, bytes):
            if len(json_str) > MAX_SERIALIZED_BYTES:
                raise ContinuityStateValidationError(
                    f"Input JSON byte size ({len(json_str)}) exceeds maximum allowed ({MAX_SERIALIZED_BYTES})"
                )
            decoded = json_str.decode("utf-8")
        elif isinstance(json_str, str):
            utf8_bytes = json_str.encode("utf-8")
            if len(utf8_bytes) > MAX_SERIALIZED_BYTES:
                raise ContinuityStateValidationError(
                    f"Input JSON byte size ({len(utf8_bytes)}) exceeds maximum allowed ({MAX_SERIALIZED_BYTES})"
                )
            decoded = json_str
        else:
            raise ContinuityStateValidationError(
                f"from_json expects str or bytes, got: {type(json_str).__name__}"
            )

        try:
            data = json.loads(decoded)
        except Exception as e:
            raise ContinuityStateValidationError(f"Malformed JSON for ExecutorCapabilities: {e}") from e

        return cls.from_dict(data)


@dataclass(frozen=True)
class ExecutionRequest:
    """Canonical representation of an execution intent for an execution actor (C3 / C4)."""
    schema_version: str
    task_id: str
    request_id: str
    executor_id: str
    operation: ExecutionOperation
    state_fingerprint: str
    target_branch: str
    expected_task_head_sha: str | None
    work_ref: ArtifactRef
    context_refs: tuple[ArtifactRef, ...]
    required_capabilities: tuple[ExecutionCapability, ...]
    expected_result_path: str

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ContinuityStateValidationError(
                f"Unsupported schema_version in ExecutionRequest: {self.schema_version!r} (expected {SCHEMA_VERSION!r})"
            )

        _validate_task_id(self.task_id, "task_id")
        _validate_canonical_request_id(self.request_id, "request_id")
        _validate_canonical_actor_id(self.executor_id, "executor_id")

        if not isinstance(self.operation, ExecutionOperation):
            try:
                object.__setattr__(self, "operation", ExecutionOperation(self.operation))
            except Exception as e:
                valid_ops = ", ".join(o.value for o in ExecutionOperation)
                raise ContinuityStateValidationError(
                    f"Invalid ExecutionOperation: {self.operation!r}. Valid values: {valid_ops}"
                ) from e

        _validate_exact_state_fingerprint(self.state_fingerprint, "state_fingerprint")
        _validate_canonical_safe_git_ref(self.target_branch, "target_branch")
        _validate_exact_hex_sha_optional(self.expected_task_head_sha, "expected_task_head_sha")

        # work_ref validation
        _validate_work_ref_role(self.work_ref, self.operation, self.task_id)

        # expected_result_path validation
        _validate_canonical_artifact_path(self.expected_result_path, "expected_result_path")
        _validate_expected_result_path(self.expected_result_path, self.task_id)

        # context_refs sequence validation
        if not isinstance(self.context_refs, (list, tuple)):
            raise ContinuityStateValidationError(
                f"context_refs must be a list or tuple, got: {type(self.context_refs).__name__}"
            )

        if len(self.context_refs) > MAX_CONTEXT_REFS:
            raise ContinuityStateValidationError(
                f"context_refs count ({len(self.context_refs)}) exceeds maximum allowed ({MAX_CONTEXT_REFS})"
            )

        parsed_context: list[ArtifactRef] = []
        seen_paths: set[str] = set()
        for idx, ref in enumerate(self.context_refs):
            if not isinstance(ref, ArtifactRef):
                raise ContinuityStateValidationError(
                    f"context_refs[{idx}] must be an ArtifactRef instance, got: {type(ref).__name__}"
                )
            if ref.path in seen_paths:
                raise ContinuityStateValidationError(
                    f"Duplicate context_ref path in ExecutionRequest: {ref.path!r}"
                )
            if ref.path == self.work_ref.path:
                raise ContinuityStateValidationError(
                    f"context_ref path '{ref.path}' collides with work_ref.path"
                )
            seen_paths.add(ref.path)
            parsed_context.append(ref)

        object.__setattr__(self, "context_refs", tuple(parsed_context))

        # required_capabilities validation
        if not isinstance(self.required_capabilities, (list, tuple)):
            raise ContinuityStateValidationError(
                f"required_capabilities must be a list or tuple, got: {type(self.required_capabilities).__name__}"
            )

        parsed_req_caps: list[ExecutionCapability] = []
        seen_req_caps: set[str] = set()
        for idx, cap in enumerate(self.required_capabilities):
            if not isinstance(cap, ExecutionCapability):
                try:
                    cap = ExecutionCapability(cap)
                except Exception as e:
                    valid_caps = ", ".join(c.value for c in ExecutionCapability)
                    raise ContinuityStateValidationError(
                        f"Invalid ExecutionCapability at index {idx}: {cap!r}. Valid values: {valid_caps}"
                    ) from e
            if cap.value in seen_req_caps:
                raise ContinuityStateValidationError(
                    f"Duplicate ExecutionCapability in required_capabilities: {cap.value!r}"
                )
            seen_req_caps.add(cap.value)
            parsed_req_caps.append(cap)

        parsed_req_caps.sort(key=lambda c: c.value)
        object.__setattr__(self, "required_capabilities", tuple(parsed_req_caps))

        raw_canonical = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        utf8_bytes = raw_canonical.encode("utf-8")
        if len(utf8_bytes) > MAX_SERIALIZED_BYTES:
            raise ContinuityStateValidationError(
                f"Serialized ExecutionRequest exceeds size limit ({len(utf8_bytes)} > {MAX_SERIALIZED_BYTES})"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "context_refs": [ref.to_dict() for ref in self.context_refs],
            "executor_id": self.executor_id,
            "expected_result_path": self.expected_result_path,
            "expected_task_head_sha": self.expected_task_head_sha,
            "operation": self.operation.value,
            "request_id": self.request_id,
            "required_capabilities": [c.value for c in self.required_capabilities],
            "schema_version": self.schema_version,
            "state_fingerprint": self.state_fingerprint,
            "target_branch": self.target_branch,
            "task_id": self.task_id,
            "work_ref": self.work_ref.to_dict(),
        }

    def to_canonical_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    def fingerprint(self) -> str:
        return hashlib.sha256(self.to_canonical_json().encode("utf-8")).hexdigest()

    @classmethod
    def from_dict(cls, data: Any) -> ExecutionRequest:
        if not isinstance(data, dict):
            raise ContinuityStateValidationError(
                f"ExecutionRequest root must be a dict, got: {type(data).__name__}"
            )

        forbidden_present = set(data.keys()) & FORBIDDEN_AUTHORITY_KEYS
        if forbidden_present:
            raise ContinuityStateValidationError(
                f"Forbidden authority/secret fields in ExecutionRequest: {sorted(forbidden_present)}"
            )

        allowed_keys = {
            "context_refs",
            "executor_id",
            "expected_result_path",
            "expected_task_head_sha",
            "operation",
            "request_id",
            "required_capabilities",
            "schema_version",
            "state_fingerprint",
            "target_branch",
            "task_id",
            "work_ref",
        }
        extra_keys = set(data.keys()) - allowed_keys
        if extra_keys:
            raise ContinuityStateValidationError(
                f"Unknown fields in ExecutionRequest: {sorted(extra_keys)}"
            )

        for req in [
            "schema_version",
            "task_id",
            "request_id",
            "executor_id",
            "operation",
            "state_fingerprint",
            "target_branch",
            "expected_task_head_sha",
            "work_ref",
            "context_refs",
            "required_capabilities",
            "expected_result_path",
        ]:
            if req not in data:
                raise ContinuityStateValidationError(f"Missing required field '{req}' in ExecutionRequest")

        work_ref = ArtifactRef.from_dict(data["work_ref"])
        context_refs = tuple(ArtifactRef.from_dict(r) for r in data["context_refs"])

        return cls(
            schema_version=data["schema_version"],
            task_id=data["task_id"],
            request_id=data["request_id"],
            executor_id=data["executor_id"],
            operation=data["operation"],
            state_fingerprint=data["state_fingerprint"],
            target_branch=data["target_branch"],
            expected_task_head_sha=data["expected_task_head_sha"],
            work_ref=work_ref,
            context_refs=context_refs,
            required_capabilities=data["required_capabilities"],
            expected_result_path=data["expected_result_path"],
        )

    @classmethod
    def from_json(cls, json_str: str | bytes) -> ExecutionRequest:
        if isinstance(json_str, bytes):
            if len(json_str) > MAX_SERIALIZED_BYTES:
                raise ContinuityStateValidationError(
                    f"Input JSON byte size ({len(json_str)}) exceeds maximum allowed ({MAX_SERIALIZED_BYTES})"
                )
            decoded = json_str.decode("utf-8")
        elif isinstance(json_str, str):
            utf8_bytes = json_str.encode("utf-8")
            if len(utf8_bytes) > MAX_SERIALIZED_BYTES:
                raise ContinuityStateValidationError(
                    f"Input JSON byte size ({len(utf8_bytes)}) exceeds maximum allowed ({MAX_SERIALIZED_BYTES})"
                )
            decoded = json_str
        else:
            raise ContinuityStateValidationError(
                f"from_json expects str or bytes, got: {type(json_str).__name__}"
            )

        try:
            data = json.loads(decoded)
        except Exception as e:
            raise ContinuityStateValidationError(f"Malformed JSON for ExecutionRequest: {e}") from e

        return cls.from_dict(data)


@dataclass(frozen=True)
class PreparedExecution:
    """Immutable receipt binding adapter preparation to an exact request (C10). Not a lease."""
    schema_version: str
    task_id: str
    request_id: str
    executor_id: str
    execution_id: str
    request_fingerprint: str

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ContinuityStateValidationError(
                f"Unsupported schema_version in PreparedExecution: {self.schema_version!r} (expected {SCHEMA_VERSION!r})"
            )
        _validate_task_id(self.task_id, "task_id")
        _validate_canonical_request_id(self.request_id, "request_id")
        _validate_canonical_actor_id(self.executor_id, "executor_id")
        _validate_canonical_request_id(self.execution_id, "execution_id")
        _validate_exact_state_fingerprint(self.request_fingerprint, "request_fingerprint")

        raw_canonical = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        utf8_bytes = raw_canonical.encode("utf-8")
        if len(utf8_bytes) > MAX_SERIALIZED_BYTES:
            raise ContinuityStateValidationError(
                f"Serialized PreparedExecution exceeds size limit ({len(utf8_bytes)} > {MAX_SERIALIZED_BYTES})"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "executor_id": self.executor_id,
            "request_fingerprint": self.request_fingerprint,
            "request_id": self.request_id,
            "schema_version": self.schema_version,
            "task_id": self.task_id,
        }

    def to_canonical_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    def fingerprint(self) -> str:
        return hashlib.sha256(self.to_canonical_json().encode("utf-8")).hexdigest()

    @classmethod
    def from_dict(cls, data: Any) -> PreparedExecution:
        if not isinstance(data, dict):
            raise ContinuityStateValidationError(
                f"PreparedExecution root must be a dict, got: {type(data).__name__}"
            )

        forbidden_present = set(data.keys()) & (
            FORBIDDEN_AUTHORITY_KEYS | {"lease", "lease_id", "lease_owner", "lease_expiry", "generation"}
        )
        if forbidden_present:
            raise ContinuityStateValidationError(
                f"Forbidden lease/secret fields in PreparedExecution: {sorted(forbidden_present)}"
            )

        allowed_keys = {
            "execution_id",
            "executor_id",
            "request_fingerprint",
            "request_id",
            "schema_version",
            "task_id",
        }
        extra_keys = set(data.keys()) - allowed_keys
        if extra_keys:
            raise ContinuityStateValidationError(
                f"Unknown fields in PreparedExecution: {sorted(extra_keys)}"
            )

        for req in allowed_keys:
            if req not in data:
                raise ContinuityStateValidationError(f"Missing required field '{req}' in PreparedExecution")

        return cls(
            schema_version=data["schema_version"],
            task_id=data["task_id"],
            request_id=data["request_id"],
            executor_id=data["executor_id"],
            execution_id=data["execution_id"],
            request_fingerprint=data["request_fingerprint"],
        )

    @classmethod
    def from_json(cls, json_str: str | bytes) -> PreparedExecution:
        if isinstance(json_str, bytes):
            if len(json_str) > MAX_SERIALIZED_BYTES:
                raise ContinuityStateValidationError(
                    f"Input JSON byte size ({len(json_str)}) exceeds maximum allowed ({MAX_SERIALIZED_BYTES})"
                )
            decoded = json_str.decode("utf-8")
        elif isinstance(json_str, str):
            utf8_bytes = json_str.encode("utf-8")
            if len(utf8_bytes) > MAX_SERIALIZED_BYTES:
                raise ContinuityStateValidationError(
                    f"Input JSON byte size ({len(utf8_bytes)}) exceeds maximum allowed ({MAX_SERIALIZED_BYTES})"
                )
            decoded = json_str
        else:
            raise ContinuityStateValidationError(
                f"from_json expects str or bytes, got: {type(json_str).__name__}"
            )

        try:
            data = json.loads(decoded)
        except Exception as e:
            raise ContinuityStateValidationError(f"Malformed JSON for PreparedExecution: {e}") from e

        return cls.from_dict(data)


@dataclass(frozen=True)
class ExecutionResult:
    """Canonical representation of an execution outcome from an execution actor (C11 / AIP-7)."""
    schema_version: str
    task_id: str
    request_id: str
    executor_id: str
    operation: ExecutionOperation
    status: ExecutionResultStatus
    implementation_sha: str | None = None
    result_ref: ArtifactRef | None = None
    evidence_refs: tuple[ArtifactRef, ...] = ()
    error_code: str | None = None

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ContinuityStateValidationError(
                f"Unsupported schema_version in ExecutionResult: {self.schema_version!r} (expected {SCHEMA_VERSION!r})"
            )
        _validate_task_id(self.task_id, "task_id")
        _validate_canonical_request_id(self.request_id, "request_id")
        _validate_canonical_actor_id(self.executor_id, "executor_id")

        if not isinstance(self.operation, ExecutionOperation):
            try:
                object.__setattr__(self, "operation", ExecutionOperation(self.operation))
            except Exception as e:
                valid_ops = ", ".join(o.value for o in ExecutionOperation)
                raise ContinuityStateValidationError(
                    f"Invalid ExecutionOperation: {self.operation!r}. Valid values: {valid_ops}"
                ) from e

        if not isinstance(self.status, ExecutionResultStatus):
            try:
                object.__setattr__(self, "status", ExecutionResultStatus(self.status))
            except Exception as e:
                valid_statuses = ", ".join(s.value for s in ExecutionResultStatus)
                raise ContinuityStateValidationError(
                    f"Invalid ExecutionResultStatus: {self.status!r}. Valid values: {valid_statuses}"
                ) from e

        # evidence_refs validation
        if not isinstance(self.evidence_refs, (list, tuple)):
            raise ContinuityStateValidationError(
                f"evidence_refs must be a list or tuple, got: {type(self.evidence_refs).__name__}"
            )

        if len(self.evidence_refs) > MAX_EVIDENCE_REFS:
            raise ContinuityStateValidationError(
                f"evidence_refs count ({len(self.evidence_refs)}) exceeds maximum allowed ({MAX_EVIDENCE_REFS})"
            )

        parsed_ev: list[ArtifactRef] = []
        seen_paths: set[str] = set()
        for idx, ref in enumerate(self.evidence_refs):
            if not isinstance(ref, ArtifactRef):
                raise ContinuityStateValidationError(
                    f"evidence_refs[{idx}] must be an ArtifactRef instance, got: {type(ref).__name__}"
                )
            if ref.path in seen_paths:
                raise ContinuityStateValidationError(
                    f"Duplicate evidence_ref path in ExecutionResult: {ref.path!r}"
                )
            seen_paths.add(ref.path)
            parsed_ev.append(ref)

        object.__setattr__(self, "evidence_refs", tuple(parsed_ev))

        # Payload matrix validation (C11 / AIP-7)
        if self.status == ExecutionResultStatus.SUCCESS:
            if self.implementation_sha is None:
                raise ContinuityStateValidationError(
                    "SUCCESS ExecutionResult requires non-null implementation_sha"
                )
            _validate_exact_hex_sha(self.implementation_sha, "implementation_sha")

            if self.result_ref is None or not isinstance(self.result_ref, ArtifactRef):
                raise ContinuityStateValidationError(
                    "SUCCESS ExecutionResult requires non-null result_ref of type ArtifactRef"
                )
            _validate_expected_result_path(self.result_ref.path, self.task_id)

            if self.error_code is not None:
                raise ContinuityStateValidationError(
                    "SUCCESS ExecutionResult cannot have non-null error_code"
                )
        else:
            if self.implementation_sha is not None:
                raise ContinuityStateValidationError(
                    f"{self.status.value} ExecutionResult cannot contain implementation_sha"
                )
            if self.result_ref is not None:
                raise ContinuityStateValidationError(
                    f"{self.status.value} ExecutionResult cannot contain result_ref"
                )
            if (
                isinstance(self.error_code, bool)
                or not isinstance(self.error_code, str)
                or not self.error_code
                or self.error_code != self.error_code.strip()
                or len(self.error_code) > MAX_ERROR_CODE_LENGTH
                or not _ERROR_CODE_PATTERN.match(self.error_code)
            ):
                raise ContinuityStateValidationError(
                    f"{self.status.value} ExecutionResult requires bounded error_code matching '^[A-Za-z0-9_.\\-]+$', got: {self.error_code!r}"
                )

        raw_canonical = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        utf8_bytes = raw_canonical.encode("utf-8")
        if len(utf8_bytes) > MAX_SERIALIZED_BYTES:
            raise ContinuityStateValidationError(
                f"Serialized ExecutionResult exceeds size limit ({len(utf8_bytes)} > {MAX_SERIALIZED_BYTES})"
            )

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "error_code": self.error_code,
            "evidence_refs": [ref.to_dict() for ref in self.evidence_refs],
            "executor_id": self.executor_id,
            "implementation_sha": self.implementation_sha,
            "operation": self.operation.value,
            "request_id": self.request_id,
            "result_ref": self.result_ref.to_dict() if self.result_ref is not None else None,
            "schema_version": self.schema_version,
            "status": self.status.value,
            "task_id": self.task_id,
        }
        return data

    def to_canonical_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    def fingerprint(self) -> str:
        return hashlib.sha256(self.to_canonical_json().encode("utf-8")).hexdigest()

    @classmethod
    def from_dict(cls, data: Any) -> ExecutionResult:
        if not isinstance(data, dict):
            raise ContinuityStateValidationError(
                f"ExecutionResult root must be a dict, got: {type(data).__name__}"
            )

        forbidden_present = set(data.keys()) & FORBIDDEN_AUTHORITY_KEYS
        if forbidden_present:
            raise ContinuityStateValidationError(
                f"Forbidden authority/secret fields in ExecutionResult: {sorted(forbidden_present)}"
            )

        allowed_keys = {
            "error_code",
            "evidence_refs",
            "executor_id",
            "implementation_sha",
            "operation",
            "request_id",
            "result_ref",
            "schema_version",
            "status",
            "task_id",
        }
        extra_keys = set(data.keys()) - allowed_keys
        if extra_keys:
            raise ContinuityStateValidationError(
                f"Unknown fields in ExecutionResult: {sorted(extra_keys)}"
            )

        for req in [
            "schema_version",
            "task_id",
            "request_id",
            "executor_id",
            "operation",
            "status",
            "implementation_sha",
            "result_ref",
            "evidence_refs",
            "error_code",
        ]:
            if req not in data:
                raise ContinuityStateValidationError(f"Missing required field '{req}' in ExecutionResult")

        res_ref = ArtifactRef.from_dict(data["result_ref"]) if data["result_ref"] is not None else None
        ev_refs = tuple(ArtifactRef.from_dict(r) for r in data["evidence_refs"])

        return cls(
            schema_version=data["schema_version"],
            task_id=data["task_id"],
            request_id=data["request_id"],
            executor_id=data["executor_id"],
            operation=data["operation"],
            status=data["status"],
            implementation_sha=data["implementation_sha"],
            result_ref=res_ref,
            evidence_refs=ev_refs,
            error_code=data["error_code"],
        )

    @classmethod
    def from_json(cls, json_str: str | bytes) -> ExecutionResult:
        if isinstance(json_str, bytes):
            if len(json_str) > MAX_SERIALIZED_BYTES:
                raise ContinuityStateValidationError(
                    f"Input JSON byte size ({len(json_str)}) exceeds maximum allowed ({MAX_SERIALIZED_BYTES})"
                )
            decoded = json_str.decode("utf-8")
        elif isinstance(json_str, str):
            utf8_bytes = json_str.encode("utf-8")
            if len(utf8_bytes) > MAX_SERIALIZED_BYTES:
                raise ContinuityStateValidationError(
                    f"Input JSON byte size ({len(utf8_bytes)}) exceeds maximum allowed ({MAX_SERIALIZED_BYTES})"
                )
            decoded = json_str
        else:
            raise ContinuityStateValidationError(
                f"from_json expects str or bytes, got: {type(json_str).__name__}"
            )

        try:
            data = json.loads(decoded)
        except Exception as e:
            raise ContinuityStateValidationError(f"Malformed JSON for ExecutionResult: {e}") from e

        return cls.from_dict(data)


def validate_execution_request_against_state(
    request: ExecutionRequest,
    state: ContinuityState,
) -> None:
    """
    Pure validation of an ExecutionRequest against authoritative canonical ContinuityState (C7 / AIP-5).
    Fails closed on any task, state fingerprint, branch, SHA, work_ref, or context ref mismatch.
    """
    if not isinstance(request, ExecutionRequest):
        raise ContinuityStateValidationError(
            f"request must be an ExecutionRequest instance, got: {type(request).__name__}"
        )
    if not isinstance(state, ContinuityState):
        raise ContinuityStateValidationError(
            f"state must be a ContinuityState instance, got: {type(state).__name__}"
        )

    if request.task_id != state.task_id:
        raise ContinuityStateValidationError(
            f"ExecutionRequest task_id '{request.task_id}' != state.task_id '{state.task_id}'"
        )

    state_fp = state.fingerprint()
    if request.state_fingerprint != state_fp:
        raise ContinuityStateValidationError(
            f"ExecutionRequest state_fingerprint '{request.state_fingerprint}' != state.fingerprint() '{state_fp}'"
        )

    if request.target_branch != state.task_branch.branch:
        raise ContinuityStateValidationError(
            f"ExecutionRequest target_branch '{request.target_branch}' != state.task_branch.branch '{state.task_branch.branch}'"
        )

    if request.expected_task_head_sha != state.task_branch.sha:
        raise ContinuityStateValidationError(
            f"ExecutionRequest expected_task_head_sha '{request.expected_task_head_sha}' != state.task_branch.sha '{state.task_branch.sha}'"
        )

    # Validate work_ref against authoritative state artifacts
    if request.operation == ExecutionOperation.RUN:
        auth_task = state.artifacts.task
        if auth_task is None:
            raise ContinuityStateValidationError(
                f"Authoritative state artifacts.task is missing for RUN request on {state.task_id}"
            )
        if (
            request.work_ref.path != auth_task.path
            or request.work_ref.ref != auth_task.ref
            or request.work_ref.blob_sha != auth_task.blob_sha
        ):
            raise ContinuityStateValidationError(
                f"RUN work_ref '{request.work_ref.to_dict()}' does not match authoritative state.artifacts.task '{auth_task.to_dict()}'"
            )
    elif request.operation == ExecutionOperation.FIX:
        auth_review = state.artifacts.review
        if auth_review is None:
            raise ContinuityStateValidationError(
                f"Authoritative state artifacts.review is missing for FIX request on {state.task_id}"
            )
        if (
            request.work_ref.path != auth_review.path
            or request.work_ref.ref != auth_review.ref
            or request.work_ref.blob_sha != auth_review.blob_sha
        ):
            raise ContinuityStateValidationError(
                f"FIX work_ref '{request.work_ref.to_dict()}' does not match authoritative state.artifacts.review '{auth_review.to_dict()}'"
            )

    # Check overlapping context refs against authoritative state artifacts
    authoritative_refs: list[ArtifactRef] = []
    if state.artifacts.task is not None:
        authoritative_refs.append(state.artifacts.task)
    if state.artifacts.plan is not None:
        authoritative_refs.append(state.artifacts.plan)
    if state.artifacts.result is not None:
        authoritative_refs.append(state.artifacts.result)
    if state.artifacts.review is not None:
        authoritative_refs.append(state.artifacts.review)
    authoritative_refs.extend(state.artifacts.contracts)

    auth_by_path = {ref.path: ref for ref in authoritative_refs}

    for ctx in request.context_refs:
        if ctx.path in auth_by_path:
            expected_auth = auth_by_path[ctx.path]
            if ctx.ref != expected_auth.ref or ctx.blob_sha != expected_auth.blob_sha:
                raise ContinuityStateValidationError(
                    f"context_ref '{ctx.path}' ref/blob_sha ('{ctx.ref}', '{ctx.blob_sha}') "
                    f"mismatches authoritative state ref/blob_sha ('{expected_auth.ref}', '{expected_auth.blob_sha}')"
                )


def validate_executor_eligibility(
    request: ExecutionRequest,
    capabilities: ExecutorCapabilities,
) -> None:
    """
    Pure capability eligibility gate for an ExecutionRequest (C9 / AIP-6).
    Fails closed on actor mismatch, unsupported operation, or missing required capability.
    """
    if not isinstance(request, ExecutionRequest):
        raise ContinuityStateValidationError(
            f"request must be an ExecutionRequest instance, got: {type(request).__name__}"
        )
    if not isinstance(capabilities, ExecutorCapabilities):
        raise ContinuityStateValidationError(
            f"capabilities must be an ExecutorCapabilities instance, got: {type(capabilities).__name__}"
        )

    if capabilities.declarative_only is not True:
        raise ContinuityStateValidationError("ExecutorCapabilities must be declarative_only=True")

    if capabilities.executor_id != request.executor_id:
        raise ContinuityStateValidationError(
            f"Executor identity mismatch: capabilities.executor_id '{capabilities.executor_id}' != request.executor_id '{request.executor_id}'"
        )

    if request.operation not in capabilities.supported_operations:
        raise ContinuityStateValidationError(
            f"Executor '{capabilities.executor_id}' does not support operation '{request.operation.value}'. "
            f"Supported: {[o.value for o in capabilities.supported_operations]}"
        )

    supported_cap_set = set(capabilities.supported_capabilities)
    missing_caps = [c for c in request.required_capabilities if c not in supported_cap_set]
    if missing_caps:
        raise ContinuityStateValidationError(
            f"Executor '{capabilities.executor_id}' is missing required capabilities: {[c.value for c in missing_caps]}"
        )


def validate_execution_result_against_request(
    result: ExecutionResult,
    request: ExecutionRequest,
) -> None:
    """
    Pure validation of an ExecutionResult against its originating ExecutionRequest (C12).
    Fails closed on identity, task, operation, status, target path, branch, or SHA mismatch.
    """
    if not isinstance(result, ExecutionResult):
        raise ContinuityStateValidationError(
            f"result must be an ExecutionResult instance, got: {type(result).__name__}"
        )
    if not isinstance(request, ExecutionRequest):
        raise ContinuityStateValidationError(
            f"request must be an ExecutionRequest instance, got: {type(request).__name__}"
        )

    if result.schema_version != request.schema_version:
        raise ContinuityStateValidationError(
            f"ExecutionResult schema_version '{result.schema_version}' != request.schema_version '{request.schema_version}'"
        )

    if result.task_id != request.task_id:
        raise ContinuityStateValidationError(
            f"ExecutionResult task_id '{result.task_id}' != request.task_id '{request.task_id}'"
        )

    if result.request_id != request.request_id:
        raise ContinuityStateValidationError(
            f"ExecutionResult request_id '{result.request_id}' != request.request_id '{request.request_id}'"
        )

    if result.executor_id != request.executor_id:
        raise ContinuityStateValidationError(
            f"ExecutionResult executor_id '{result.executor_id}' != request.executor_id '{request.executor_id}'"
        )

    if result.operation != request.operation:
        raise ContinuityStateValidationError(
            f"ExecutionResult operation '{result.operation.value}' != request.operation '{request.operation.value}'"
        )

    if result.status == ExecutionResultStatus.SUCCESS:
        if result.result_ref is None:
            raise ContinuityStateValidationError("SUCCESS ExecutionResult missing result_ref")
        if result.result_ref.path != request.expected_result_path:
            raise ContinuityStateValidationError(
                f"SUCCESS result_ref.path '{result.result_ref.path}' != request.expected_result_path '{request.expected_result_path}'"
            )
        if result.result_ref.ref != request.target_branch:
            raise ContinuityStateValidationError(
                f"SUCCESS result_ref.ref '{result.result_ref.ref}' != request.target_branch '{request.target_branch}'"
            )
        if result.implementation_sha is None:
            raise ContinuityStateValidationError("SUCCESS ExecutionResult missing implementation_sha")
        if result.error_code is not None:
            raise ContinuityStateValidationError("SUCCESS ExecutionResult cannot contain error_code")


@runtime_checkable
class ExecutorAdapter(Protocol):
    """Vendor-neutral Protocol for execution adapters (C13 / AIP-8)."""
    @property
    def executor_id(self) -> str:
        """Exact canonical actor ID."""
        ...

    def capabilities(self) -> ExecutorCapabilities:
        """Declarative capability contract for this adapter."""
        ...

    def prepare(self, request: ExecutionRequest) -> PreparedExecution:
        """Prepares execution context bound to an exact request fingerprint."""
        ...

    def collect_result(self, execution_id: str) -> ExecutionResult:
        """Collects execution result for a previously prepared execution ID."""
        ...
