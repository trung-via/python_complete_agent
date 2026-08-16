"""
Brain-Neutral Contract for Open Multi-Agent Continuity OS (ADR-010 Milestone 2 / TASK-023 Hardening).
Provides vendor-independent request, result, capability, and context representation.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import re
from typing import Any, Mapping, Sequence

from .errors import ContinuityStateValidationError
from .state import (
    MAX_SERIALIZED_BYTES,
    SCHEMA_VERSION,
    ArtifactRef,
    BrainOperation,
    _validate_actor_id,
    _validate_artifact_path,
    _validate_exact_hex_sha,
)

_TASK_ID_PATTERN = re.compile(r"^TASK-\d+$")
_REQUEST_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:[a-z0-9_.\-:]+)*$")
_ERROR_CODE_PATTERN = re.compile(r"^[A-Za-z0-9_.\-]+$")
_TASK_TOKEN_PATTERN = re.compile(r"(?<![A-Za-z0-9])TASK-(\d+)(?![A-Za-z0-9])", re.IGNORECASE)

MAX_REQUEST_ID_LENGTH = 64
MAX_ERROR_CODE_LENGTH = 64
MAX_OBJECTIVE_LENGTH = 4096
MAX_CONTEXT_REFS = 32
MAX_DESCRIPTION_LENGTH = 256


class BrainResultStatus(str, Enum):
    """Execution / resolution status of an advisory Brain request."""
    SUCCESS = "SUCCESS"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    INCOMPLETE = "INCOMPLETE"


class BrainOutputType(str, Enum):
    """Categorization of expected or produced Brain output."""
    TASK_ARTIFACT = "TASK_ARTIFACT"
    PLAN_ARTIFACT = "PLAN_ARTIFACT"
    REVIEW_ARTIFACT = "REVIEW_ARTIFACT"
    DIAGNOSIS_ARTIFACT = "DIAGNOSIS_ARTIFACT"
    PATCH_PROPOSAL_ARTIFACT = "PATCH_PROPOSAL_ARTIFACT"
    BOUNDED_TEXT = "BOUNDED_TEXT"


OPERATION_OUTPUT_TYPE_COMPATIBILITY: dict[BrainOperation, frozenset[BrainOutputType]] = {
    BrainOperation.TASK: frozenset({BrainOutputType.TASK_ARTIFACT}),
    BrainOperation.TASK_AND_PLAN: frozenset({BrainOutputType.TASK_ARTIFACT, BrainOutputType.PLAN_ARTIFACT}),
    BrainOperation.PLAN: frozenset({BrainOutputType.PLAN_ARTIFACT}),
    BrainOperation.REVIEW: frozenset({BrainOutputType.REVIEW_ARTIFACT}),
    BrainOperation.DIAGNOSIS: frozenset({BrainOutputType.DIAGNOSIS_ARTIFACT, BrainOutputType.BOUNDED_TEXT}),
    BrainOperation.PATCH_PROPOSAL: frozenset({BrainOutputType.PATCH_PROPOSAL_ARTIFACT, BrainOutputType.BOUNDED_TEXT}),
}


def _validate_non_negative_int(val: Any, field_name: str, allow_none: bool = False, min_val: int = 0) -> int | None:
    if val is None:
        if allow_none:
            return None
        raise ContinuityStateValidationError(f"{field_name} cannot be null/None")
    if isinstance(val, bool) or not isinstance(val, int):
        raise ContinuityStateValidationError(f"{field_name} must be an integer, got: {type(val).__name__}")
    if val < min_val:
        raise ContinuityStateValidationError(f"{field_name} must be >= {min_val}, got: {val}")
    return val


def _validate_task_id(task_id: Any, field_name: str = "task_id") -> str:
    if isinstance(task_id, bool) or not isinstance(task_id, str):
        raise ContinuityStateValidationError(f"{field_name} must be a non-empty string")
    if not _TASK_ID_PATTERN.match(task_id):
        raise ContinuityStateValidationError(
            f"{field_name} must match exact case-sensitive '^TASK-\\d+$', got: {task_id!r}"
        )
    return task_id


def _validate_request_id(request_id: Any, field_name: str = "request_id") -> str:
    if isinstance(request_id, bool) or not isinstance(request_id, str) or not request_id.strip():
        raise ContinuityStateValidationError(f"{field_name} must be a non-empty string")
    req_str = request_id.strip()
    if len(req_str) > MAX_REQUEST_ID_LENGTH:
        raise ContinuityStateValidationError(
            f"{field_name} length ({len(req_str)}) exceeds maximum allowed ({MAX_REQUEST_ID_LENGTH})"
        )
    if not _REQUEST_ID_PATTERN.match(req_str):
        raise ContinuityStateValidationError(
            f"{field_name} must be a conservative lowercase identifier (e.g. 'req-task-021-r1'), got: {request_id!r}"
        )
    return req_str


def _validate_canonical_actor_id(actor_id: Any, field_name: str) -> str:
    """Validates exact canonical actor ID with zero whitespace padding (C1 / AIP-1)."""
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


def _validate_canonical_request_id(request_id: Any, field_name: str) -> str:
    """Validates exact canonical request ID with zero whitespace padding (C1 / AIP-1)."""
    if isinstance(request_id, bool) or not isinstance(request_id, str):
        raise ContinuityStateValidationError(f"{field_name} must be a non-empty string")
    if request_id != request_id.strip() or not request_id:
        raise ContinuityStateValidationError(
            f"{field_name} must not contain leading or trailing whitespace: {request_id!r}"
        )
    canonical = _validate_request_id(request_id, field_name)
    if request_id != canonical:
        raise ContinuityStateValidationError(
            f"{field_name} must be exact canonical request ID, got: {request_id!r}"
        )
    return canonical


def _validate_canonical_artifact_path(path: Any, field_name: str) -> str:
    """Validates exact canonical artifact path with zero whitespace padding (C2 / AIP-1)."""
    if isinstance(path, bool) or not isinstance(path, str):
        raise ContinuityStateValidationError(f"{field_name} must be a non-empty string")
    if path != path.strip() or not path:
        raise ContinuityStateValidationError(
            f"{field_name} must not contain leading or trailing whitespace: {path!r}"
        )
    canonical = _validate_artifact_path(path, field_name)
    if path != canonical:
        raise ContinuityStateValidationError(
            f"{field_name} must be exact canonical artifact path, got: {path!r}"
        )
    return canonical


def _validate_error_code(error_code: Any, field_name: str = "error_code") -> str | None:
    if error_code is None:
        return None
    if isinstance(error_code, bool) or not isinstance(error_code, str) or not error_code.strip():
        raise ContinuityStateValidationError(f"{field_name} must be a non-empty string or None")
    code_str = error_code.strip()
    if len(code_str) > MAX_ERROR_CODE_LENGTH:
        raise ContinuityStateValidationError(
            f"{field_name} length ({len(code_str)}) exceeds maximum allowed ({MAX_ERROR_CODE_LENGTH})"
        )
    if not _ERROR_CODE_PATTERN.match(code_str):
        raise ContinuityStateValidationError(f"{field_name} contains invalid characters: {error_code!r}")
    return code_str


def _validate_task_token_in_path(path: str, task_id: str, field_name: str) -> None:
    """
    Validates delimiter-aware task identity tokens in path (C3 / AIP-3).
    Extracts all 'TASK-<digits>' tokens and requires all extracted task numbers
    to match the numeric identifier of active task_id without ambiguity or aliasing.
    """
    target_num = int(task_id.split("-")[1])
    matches = _TASK_TOKEN_PATTERN.findall(path)
    if not matches:
        raise ContinuityStateValidationError(
            f"{field_name} path '{path}' must match active task identity {task_id}"
        )
    extracted_nums = [int(m) for m in matches]
    for num in extracted_nums:
        if num != target_num:
            raise ContinuityStateValidationError(
                f"{field_name} path '{path}' contains task token 'TASK-{num}' "
                f"which does not match active task identity {task_id}"
            )


def _validate_artifact_role_and_task(
    path: str,
    output_type: BrainOutputType,
    task_id: str,
    field_name: str,
) -> None:
    """Validates that target artifact path matches the output type and active task_id."""
    canon_path = _validate_canonical_artifact_path(path, field_name)
    task_num_str = task_id.split("-")[1]
    task_num_int = int(task_num_str)

    if output_type == BrainOutputType.TASK_ARTIFACT:
        expected = f".ai/tasks/{task_id}.md"
        if canon_path != expected:
            raise ContinuityStateValidationError(
                f"{field_name} path '{canon_path}' incompatible with TASK_ARTIFACT for {task_id} (expected '{expected}')"
            )
    elif output_type == BrainOutputType.REVIEW_ARTIFACT:
        expected_standard = f".ai/reviews/REVIEW-{str(task_num_int).zfill(3)}.md"
        expected_exact = f".ai/reviews/REVIEW-{task_num_str}.md"
        expected_short = f".ai/reviews/REVIEW-{task_num_int}.md"
        if canon_path not in (expected_standard, expected_exact, expected_short):
            raise ContinuityStateValidationError(
                f"{field_name} path '{canon_path}' incompatible with REVIEW_ARTIFACT for {task_id} (expected '{expected_standard}')"
            )
    elif output_type == BrainOutputType.PLAN_ARTIFACT:
        # PLAN must live under .ai/context/, .ai/plans/, or .ai/decisions/ and NOT under tasks/reviews/results/metrics
        if not (canon_path.startswith(".ai/context/") or canon_path.startswith(".ai/plans/") or canon_path.startswith(".ai/decisions/")):
            raise ContinuityStateValidationError(
                f"{field_name} path '{canon_path}' incompatible with PLAN_ARTIFACT (must live under .ai/context/, .ai/plans/, or .ai/decisions/)"
            )
        _validate_task_token_in_path(canon_path, task_id, field_name)
    elif output_type == BrainOutputType.DIAGNOSIS_ARTIFACT:
        # DIAGNOSIS must live under .ai/context/ or .ai/diagnosis/
        if not (canon_path.startswith(".ai/context/") or canon_path.startswith(".ai/diagnosis/")):
            raise ContinuityStateValidationError(
                f"{field_name} path '{canon_path}' incompatible with DIAGNOSIS_ARTIFACT (must live under .ai/context/ or .ai/diagnosis/)"
            )
        _validate_task_token_in_path(canon_path, task_id, field_name)
    elif output_type == BrainOutputType.PATCH_PROPOSAL_ARTIFACT:
        # PATCH_PROPOSAL must live under .ai/context/ or .ai/patches/
        if not (canon_path.startswith(".ai/context/") or canon_path.startswith(".ai/patches/")):
            raise ContinuityStateValidationError(
                f"{field_name} path '{canon_path}' incompatible with PATCH_PROPOSAL_ARTIFACT (must live under .ai/context/ or .ai/patches/)"
            )
        _validate_task_token_in_path(canon_path, task_id, field_name)
    elif output_type == BrainOutputType.BOUNDED_TEXT:
        raise ContinuityStateValidationError(
            f"{field_name} path '{canon_path}' cannot be specified for BOUNDED_TEXT output type"
        )


@dataclass(frozen=True)
class ContextRef:
    """Bounded, navigation-only context reference pointer."""
    path: str
    blob_sha: str | None = None
    description: str | None = None

    def __post_init__(self) -> None:
        canon_path = _validate_canonical_artifact_path(self.path, "ContextRef.path")
        object.__setattr__(self, "path", canon_path)

        if self.blob_sha is not None:
            _validate_exact_hex_sha(self.blob_sha, "ContextRef.blob_sha")
        if self.description is not None:
            if isinstance(self.description, bool) or not isinstance(self.description, str):
                raise ContinuityStateValidationError("ContextRef.description must be a string or None")
            if len(self.description) > MAX_DESCRIPTION_LENGTH:
                raise ContinuityStateValidationError(
                    f"ContextRef.description length ({len(self.description)}) exceeds maximum allowed ({MAX_DESCRIPTION_LENGTH})"
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "blob_sha": self.blob_sha,
            "description": self.description,
            "path": self.path,
        }

    @classmethod
    def from_dict(cls, data: Any, context_name: str = "ContextRef") -> ContextRef:
        if not isinstance(data, dict):
            raise ContinuityStateValidationError(f"{context_name} must be a dict, got: {type(data).__name__}")
        allowed_keys = {"blob_sha", "description", "path"}
        extra_keys = set(data.keys()) - allowed_keys
        if extra_keys:
            raise ContinuityStateValidationError(f"Unknown fields in {context_name}: {sorted(extra_keys)}")
        if "path" not in data:
            raise ContinuityStateValidationError(f"Missing required field 'path' in {context_name}")
        return cls(
            path=data["path"],
            blob_sha=data.get("blob_sha"),
            description=data.get("description"),
        )


@dataclass(frozen=True)
class OutputContract:
    """Specification of expected output type and target destination."""
    expected_output_type: BrainOutputType
    target_artifact_path: str | None = None
    max_output_bytes: int = MAX_SERIALIZED_BYTES

    def __post_init__(self) -> None:
        if not isinstance(self.expected_output_type, BrainOutputType):
            try:
                object.__setattr__(self, "expected_output_type", BrainOutputType(self.expected_output_type))
            except Exception as e:
                valid_types = ", ".join(t.value for t in BrainOutputType)
                raise ContinuityStateValidationError(
                    f"Invalid BrainOutputType: {self.expected_output_type!r}. Valid values: {valid_types}"
                ) from e

        if self.expected_output_type == BrainOutputType.BOUNDED_TEXT:
            if self.target_artifact_path is not None:
                raise ContinuityStateValidationError(
                    "OutputContract with expected_output_type 'BOUNDED_TEXT' must have target_artifact_path=None"
                )
        else:
            if self.target_artifact_path is not None:
                canon_target = _validate_canonical_artifact_path(
                    self.target_artifact_path, "OutputContract.target_artifact_path"
                )
                object.__setattr__(self, "target_artifact_path", canon_target)

        _validate_non_negative_int(self.max_output_bytes, "OutputContract.max_output_bytes", min_val=1)
        if self.max_output_bytes > MAX_SERIALIZED_BYTES:
            raise ContinuityStateValidationError(
                f"OutputContract.max_output_bytes ({self.max_output_bytes}) exceeds MAX_SERIALIZED_BYTES ({MAX_SERIALIZED_BYTES})"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "expected_output_type": self.expected_output_type.value,
            "max_output_bytes": self.max_output_bytes,
            "target_artifact_path": self.target_artifact_path,
        }

    @classmethod
    def from_dict(cls, data: Any, context_name: str = "OutputContract") -> OutputContract:
        if not isinstance(data, dict):
            raise ContinuityStateValidationError(f"{context_name} must be a dict, got: {type(data).__name__}")
        allowed_keys = {"expected_output_type", "max_output_bytes", "target_artifact_path"}
        extra_keys = set(data.keys()) - allowed_keys
        if extra_keys:
            raise ContinuityStateValidationError(f"Unknown fields in {context_name}: {sorted(extra_keys)}")
        if "expected_output_type" not in data:
            raise ContinuityStateValidationError(f"Missing required field 'expected_output_type' in {context_name}")
        return cls(
            expected_output_type=data["expected_output_type"],
            target_artifact_path=data.get("target_artifact_path"),
            max_output_bytes=data.get("max_output_bytes", MAX_SERIALIZED_BYTES),
        )


@dataclass(frozen=True)
class BrainCapability:
    """Declarative description of a Brain surface's supported operations."""
    brain_id: str
    supported_operations: tuple[BrainOperation, ...]
    max_context_bytes: int | None = None
    declarative_only: bool = True

    def __post_init__(self) -> None:
        canon_brain = _validate_canonical_actor_id(self.brain_id, "BrainCapability.brain_id")
        object.__setattr__(self, "brain_id", canon_brain)

        if not self.declarative_only:
            raise ContinuityStateValidationError("BrainCapability.declarative_only must be True")

        if not isinstance(self.supported_operations, tuple):
            try:
                object.__setattr__(self, "supported_operations", tuple(self.supported_operations))
            except Exception as e:
                raise ContinuityStateValidationError("BrainCapability.supported_operations must be an iterable") from e

        if not self.supported_operations:
            raise ContinuityStateValidationError("BrainCapability.supported_operations cannot be empty")

        validated_ops = []
        seen_ops: set[BrainOperation] = set()
        for idx, op in enumerate(self.supported_operations):
            if not isinstance(op, BrainOperation):
                try:
                    op = BrainOperation(op)
                except Exception as e:
                    valid_ops = ", ".join(o.value for o in BrainOperation)
                    raise ContinuityStateValidationError(
                        f"Invalid BrainOperation in supported_operations[{idx}]: {op!r}. Valid: {valid_ops}"
                    ) from e
            if op in seen_ops:
                raise ContinuityStateValidationError(
                    f"Duplicate BrainOperation in supported_operations: {op.value!r}"
                )
            seen_ops.add(op)
            validated_ops.append(op)
        object.__setattr__(self, "supported_operations", tuple(validated_ops))

        _validate_non_negative_int(self.max_context_bytes, "BrainCapability.max_context_bytes", allow_none=True)

        # Enforce 16 KiB size cap fail-closed in constructor/parser
        raw_canonical = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        utf8_bytes = raw_canonical.encode("utf-8")
        if len(utf8_bytes) > MAX_SERIALIZED_BYTES:
            raise ContinuityStateValidationError(
                f"Serialized BrainCapability size ({len(utf8_bytes)} bytes) exceeds MAX_SERIALIZED_BYTES limit ({MAX_SERIALIZED_BYTES})"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "brain_id": self.brain_id,
            "declarative_only": self.declarative_only,
            "max_context_bytes": self.max_context_bytes,
            "supported_operations": [op.value for op in self.supported_operations],
        }

    @classmethod
    def from_dict(cls, data: Any, context_name: str = "BrainCapability") -> BrainCapability:
        if not isinstance(data, dict):
            raise ContinuityStateValidationError(f"{context_name} must be a dict, got: {type(data).__name__}")
        allowed_keys = {"brain_id", "declarative_only", "max_context_bytes", "supported_operations"}
        extra_keys = set(data.keys()) - allowed_keys
        if extra_keys:
            raise ContinuityStateValidationError(f"Unknown fields in {context_name}: {sorted(extra_keys)}")
        for req in ("brain_id", "supported_operations"):
            if req not in data:
                raise ContinuityStateValidationError(f"Missing required field '{req}' in {context_name}")
        ops_raw = data["supported_operations"]
        if not isinstance(ops_raw, list):
            raise ContinuityStateValidationError(f"{context_name}.supported_operations must be a list")
        return cls(
            brain_id=data["brain_id"],
            supported_operations=tuple(ops_raw),
            max_context_bytes=data.get("max_context_bytes"),
            declarative_only=data.get("declarative_only", True),
        )


@dataclass(frozen=True)
class BrainRequest:
    """
    Vendor-neutral Brain reasoning request (ADR-010 Milestone 2).
    Carries bounded control & navigation metadata for a reasoning operation.
    """
    task_id: str
    request_id: str
    brain_id: str
    operation: BrainOperation
    objective: str
    output_contract: OutputContract
    context_refs: tuple[ContextRef, ...] = ()
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ContinuityStateValidationError(
                f"Unsupported schema_version: {self.schema_version!r} (expected {SCHEMA_VERSION!r})"
            )

        _validate_task_id(self.task_id, "BrainRequest.task_id")
        canon_req_id = _validate_canonical_request_id(self.request_id, "BrainRequest.request_id")
        canon_brain_id = _validate_canonical_actor_id(self.brain_id, "BrainRequest.brain_id")
        object.__setattr__(self, "request_id", canon_req_id)
        object.__setattr__(self, "brain_id", canon_brain_id)

        if not isinstance(self.operation, BrainOperation):
            try:
                object.__setattr__(self, "operation", BrainOperation(self.operation))
            except Exception as e:
                valid_ops = ", ".join(o.value for o in BrainOperation)
                raise ContinuityStateValidationError(
                    f"Invalid BrainOperation: {self.operation!r}. Valid values: {valid_ops}"
                ) from e

        if isinstance(self.objective, bool) or not isinstance(self.objective, str) or not self.objective.strip():
            raise ContinuityStateValidationError("BrainRequest.objective must be a non-empty string")
        if len(self.objective) > MAX_OBJECTIVE_LENGTH:
            raise ContinuityStateValidationError(
                f"BrainRequest.objective length ({len(self.objective)}) exceeds maximum allowed ({MAX_OBJECTIVE_LENGTH})"
            )

        if not isinstance(self.output_contract, OutputContract):
            raise ContinuityStateValidationError(
                f"BrainRequest.output_contract must be an OutputContract, got: {type(self.output_contract).__name__}"
            )

        # Validate operation vs expected_output_type compatibility
        allowed_types = OPERATION_OUTPUT_TYPE_COMPATIBILITY.get(self.operation, frozenset())
        if self.output_contract.expected_output_type not in allowed_types:
            raise ContinuityStateValidationError(
                f"Incompatible expected_output_type {self.output_contract.expected_output_type.value!r} "
                f"for operation {self.operation.value!r}. Allowed types: {sorted(t.value for t in allowed_types)}"
            )

        # For artifact output types, require a non-null target_artifact_path
        if self.output_contract.expected_output_type != BrainOutputType.BOUNDED_TEXT:
            if self.output_contract.target_artifact_path is None:
                raise ContinuityStateValidationError(
                    f"BrainRequest with expected_output_type '{self.output_contract.expected_output_type.value}' "
                    f"requires a non-null target_artifact_path"
                )

        # Validate output target artifact path against output type and task_id if provided
        if self.output_contract.target_artifact_path is not None:
            _validate_artifact_role_and_task(
                self.output_contract.target_artifact_path,
                self.output_contract.expected_output_type,
                self.task_id,
                "OutputContract.target_artifact_path",
            )

        if not isinstance(self.context_refs, tuple):
            try:
                object.__setattr__(self, "context_refs", tuple(self.context_refs))
            except Exception as e:
                raise ContinuityStateValidationError("BrainRequest.context_refs must be an iterable of ContextRef") from e

        if len(self.context_refs) > MAX_CONTEXT_REFS:
            raise ContinuityStateValidationError(
                f"BrainRequest.context_refs count ({len(self.context_refs)}) exceeds maximum allowed ({MAX_CONTEXT_REFS})"
            )

        seen_paths: set[str] = set()
        for idx, ref in enumerate(self.context_refs):
            if not isinstance(ref, ContextRef):
                raise ContinuityStateValidationError(
                    f"BrainRequest.context_refs[{idx}] must be a ContextRef, got: {type(ref).__name__}"
                )
            if ref.path in seen_paths:
                raise ContinuityStateValidationError(f"Duplicate context_ref path rejected: {ref.path!r}")
            seen_paths.add(ref.path)

        # Enforce 16 KiB size cap fail-closed in constructor/parser
        raw_canonical = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        utf8_bytes = raw_canonical.encode("utf-8")
        if len(utf8_bytes) > MAX_SERIALIZED_BYTES:
            raise ContinuityStateValidationError(
                f"Serialized BrainRequest size ({len(utf8_bytes)} bytes) exceeds MAX_SERIALIZED_BYTES limit ({MAX_SERIALIZED_BYTES})"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "brain_id": self.brain_id,
            "context_refs": [ref.to_dict() for ref in self.context_refs],
            "objective": self.objective,
            "operation": self.operation.value,
            "output_contract": self.output_contract.to_dict(),
            "request_id": self.request_id,
            "schema_version": self.schema_version,
            "task_id": self.task_id,
        }

    def to_canonical_json(self) -> str:
        data = self.to_dict()
        canonical_str = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        utf8_bytes = canonical_str.encode("utf-8")
        if len(utf8_bytes) > MAX_SERIALIZED_BYTES:
            raise ContinuityStateValidationError(
                f"Serialized BrainRequest size ({len(utf8_bytes)} bytes) exceeds MAX_SERIALIZED_BYTES limit ({MAX_SERIALIZED_BYTES})"
            )
        return canonical_str

    def fingerprint(self) -> str:
        canonical_str = self.to_canonical_json()
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    @classmethod
    def from_dict(cls, data: Any) -> BrainRequest:
        if not isinstance(data, dict):
            raise ContinuityStateValidationError(f"BrainRequest root must be a dict, got: {type(data).__name__}")

        allowed_root_keys = {
            "brain_id",
            "context_refs",
            "objective",
            "operation",
            "output_contract",
            "request_id",
            "schema_version",
            "task_id",
        }
        extra_keys = set(data.keys()) - allowed_root_keys
        if extra_keys:
            raise ContinuityStateValidationError(f"Unknown root fields in BrainRequest: {sorted(extra_keys)}")

        for req in ("brain_id", "objective", "operation", "output_contract", "request_id", "schema_version", "task_id"):
            if req not in data:
                raise ContinuityStateValidationError(f"Missing required field '{req}' in BrainRequest")

        if data["schema_version"] != SCHEMA_VERSION:
            raise ContinuityStateValidationError(
                f"Unsupported schema_version: {data['schema_version']!r} (expected {SCHEMA_VERSION!r})"
            )

        refs_raw = data.get("context_refs", [])
        if not isinstance(refs_raw, list):
            raise ContinuityStateValidationError("BrainRequest.context_refs must be a list")
        context_refs = [
            ContextRef.from_dict(r, f"context_refs[{i}]") for i, r in enumerate(refs_raw)
        ]

        output_contract = OutputContract.from_dict(data["output_contract"], "output_contract")

        return cls(
            task_id=data["task_id"],
            request_id=data["request_id"],
            brain_id=data["brain_id"],
            operation=data["operation"],
            objective=data["objective"],
            output_contract=output_contract,
            context_refs=tuple(context_refs),
            schema_version=data["schema_version"],
        )

    @classmethod
    def from_json(cls, text: str | bytes) -> BrainRequest:
        if isinstance(text, (bytes, bytearray)):
            raw_bytes = bytes(text)
            if len(raw_bytes) > MAX_SERIALIZED_BYTES:
                raise ContinuityStateValidationError(
                    f"Input JSON size ({len(raw_bytes)} bytes) exceeds maximum allowable size of {MAX_SERIALIZED_BYTES} bytes"
                )
            try:
                decoded_text = raw_bytes.decode("utf-8")
            except UnicodeDecodeError as e:
                raise ContinuityStateValidationError(f"Invalid UTF-8 encoding in JSON: {e}") from e
        elif isinstance(text, str):
            raw_bytes = text.encode("utf-8")
            if len(raw_bytes) > MAX_SERIALIZED_BYTES:
                raise ContinuityStateValidationError(
                    f"Input JSON size ({len(raw_bytes)} bytes) exceeds maximum allowable size of {MAX_SERIALIZED_BYTES} bytes"
                )
            decoded_text = text
        else:
            raise ContinuityStateValidationError(f"from_json expects str or bytes, got: {type(text).__name__}")

        try:
            data = json.loads(decoded_text)
        except Exception as e:
            raise ContinuityStateValidationError(f"Malformed JSON input: {e}") from e

        return cls.from_dict(data)


@dataclass(frozen=True)
class BrainResult:
    """
    Vendor-neutral advisory Brain outcome (ADR-010 Milestone 2).
    Represents an advisory result or artifact pointer without granting execution authority.
    Persists only pointers and deterministic metadata, never raw model output bodies.
    """
    task_id: str
    request_id: str
    brain_id: str
    operation: BrainOperation
    status: BrainResultStatus
    output_type: BrainOutputType
    artifact_ref: ArtifactRef | None = None
    evidence_ref: ContextRef | None = None
    error_code: str | None = None
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ContinuityStateValidationError(
                f"Unsupported schema_version: {self.schema_version!r} (expected {SCHEMA_VERSION!r})"
            )

        _validate_task_id(self.task_id, "BrainResult.task_id")
        canon_req_id = _validate_canonical_request_id(self.request_id, "BrainResult.request_id")
        canon_brain_id = _validate_canonical_actor_id(self.brain_id, "BrainResult.brain_id")
        object.__setattr__(self, "request_id", canon_req_id)
        object.__setattr__(self, "brain_id", canon_brain_id)

        if not isinstance(self.operation, BrainOperation):
            try:
                object.__setattr__(self, "operation", BrainOperation(self.operation))
            except Exception as e:
                valid_ops = ", ".join(o.value for o in BrainOperation)
                raise ContinuityStateValidationError(
                    f"Invalid BrainOperation: {self.operation!r}. Valid values: {valid_ops}"
                ) from e

        if not isinstance(self.status, BrainResultStatus):
            try:
                object.__setattr__(self, "status", BrainResultStatus(self.status))
            except Exception as e:
                valid_statuses = ", ".join(s.value for s in BrainResultStatus)
                raise ContinuityStateValidationError(
                    f"Invalid BrainResultStatus: {self.status!r}. Valid values: {valid_statuses}"
                ) from e

        if not isinstance(self.output_type, BrainOutputType):
            try:
                object.__setattr__(self, "output_type", BrainOutputType(self.output_type))
            except Exception as e:
                valid_types = ", ".join(t.value for t in BrainOutputType)
                raise ContinuityStateValidationError(
                    f"Invalid BrainOutputType: {self.output_type!r}. Valid values: {valid_types}"
                ) from e

        # Validate operation vs output_type compatibility
        allowed_types = OPERATION_OUTPUT_TYPE_COMPATIBILITY.get(self.operation, frozenset())
        if self.output_type not in allowed_types:
            raise ContinuityStateValidationError(
                f"Incompatible output_type {self.output_type.value!r} for operation {self.operation.value!r}. "
                f"Allowed types: {sorted(t.value for t in allowed_types)}"
            )

        # Check payload exclusivity first (C4 / AIP-4)
        if self.artifact_ref is not None and self.evidence_ref is not None:
            raise ContinuityStateValidationError(
                "Ambiguous result payload: both artifact_ref and evidence_ref provided"
            )

        if self.status == BrainResultStatus.SUCCESS:
            if self.error_code is not None:
                raise ContinuityStateValidationError(
                    "SUCCESS status cannot have a non-null error_code"
                )
            if self.artifact_ref is None and self.evidence_ref is None:
                raise ContinuityStateValidationError(
                    "SUCCESS status requires exactly one result payload pointer (artifact_ref or evidence_ref)"
                )
            if self.output_type == BrainOutputType.BOUNDED_TEXT and self.artifact_ref is not None:
                raise ContinuityStateValidationError(
                    "SUCCESS status with BOUNDED_TEXT output_type cannot carry artifact_ref"
                )
            if self.output_type != BrainOutputType.BOUNDED_TEXT and self.evidence_ref is not None:
                raise ContinuityStateValidationError(
                    f"SUCCESS status with {self.output_type.value} output_type cannot carry evidence_ref"
                )

        # Validate artifact_ref if present
        if self.artifact_ref is not None:
            if not isinstance(self.artifact_ref, ArtifactRef):
                raise ContinuityStateValidationError(
                    f"BrainResult.artifact_ref must be an ArtifactRef or None, got: {type(self.artifact_ref).__name__}"
                )
            _validate_canonical_artifact_path(self.artifact_ref.path, "BrainResult.artifact_ref.path")
            _validate_artifact_role_and_task(
                self.artifact_ref.path,
                self.output_type,
                self.task_id,
                "BrainResult.artifact_ref",
            )

        # Validate evidence_ref if present
        if self.evidence_ref is not None:
            if not isinstance(self.evidence_ref, ContextRef):
                raise ContinuityStateValidationError(
                    f"BrainResult.evidence_ref must be a ContextRef or None, got: {type(self.evidence_ref).__name__}"
                )
            _validate_canonical_artifact_path(self.evidence_ref.path, "BrainResult.evidence_ref.path")
            if self.output_type != BrainOutputType.BOUNDED_TEXT:
                raise ContinuityStateValidationError(
                    f"evidence_ref payload is only valid for BOUNDED_TEXT output_type, got: {self.output_type.value}"
                )

        if self.error_code is not None:
            object.__setattr__(self, "error_code", _validate_error_code(self.error_code, "BrainResult.error_code"))

        # Enforce 16 KiB size cap fail-closed in constructor/parser
        raw_canonical = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        utf8_bytes = raw_canonical.encode("utf-8")
        if len(utf8_bytes) > MAX_SERIALIZED_BYTES:
            raise ContinuityStateValidationError(
                f"Serialized BrainResult size ({len(utf8_bytes)} bytes) exceeds MAX_SERIALIZED_BYTES limit ({MAX_SERIALIZED_BYTES})"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_ref": self.artifact_ref.to_dict() if self.artifact_ref is not None else None,
            "brain_id": self.brain_id,
            "error_code": self.error_code,
            "evidence_ref": self.evidence_ref.to_dict() if self.evidence_ref is not None else None,
            "operation": self.operation.value,
            "output_type": self.output_type.value,
            "request_id": self.request_id,
            "schema_version": self.schema_version,
            "status": self.status.value,
            "task_id": self.task_id,
        }

    def to_canonical_json(self) -> str:
        data = self.to_dict()
        canonical_str = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        utf8_bytes = canonical_str.encode("utf-8")
        if len(utf8_bytes) > MAX_SERIALIZED_BYTES:
            raise ContinuityStateValidationError(
                f"Serialized BrainResult size ({len(utf8_bytes)} bytes) exceeds MAX_SERIALIZED_BYTES limit ({MAX_SERIALIZED_BYTES})"
            )
        return canonical_str

    def fingerprint(self) -> str:
        canonical_str = self.to_canonical_json()
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    @classmethod
    def from_dict(cls, data: Any) -> BrainResult:
        if not isinstance(data, dict):
            raise ContinuityStateValidationError(f"BrainResult root must be a dict, got: {type(data).__name__}")

        allowed_root_keys = {
            "artifact_ref",
            "brain_id",
            "error_code",
            "evidence_ref",
            "operation",
            "output_type",
            "request_id",
            "schema_version",
            "status",
            "task_id",
        }
        extra_keys = set(data.keys()) - allowed_root_keys
        if extra_keys:
            raise ContinuityStateValidationError(f"Unknown root fields in BrainResult: {sorted(extra_keys)}")

        for req in ("brain_id", "operation", "output_type", "request_id", "schema_version", "status", "task_id"):
            if req not in data:
                raise ContinuityStateValidationError(f"Missing required field '{req}' in BrainResult")

        if data["schema_version"] != SCHEMA_VERSION:
            raise ContinuityStateValidationError(
                f"Unsupported schema_version: {data['schema_version']!r} (expected {SCHEMA_VERSION!r})"
            )

        artifact_data = data.get("artifact_ref")
        artifact_ref = ArtifactRef.from_dict(artifact_data, "artifact_ref") if artifact_data is not None else None

        evidence_data = data.get("evidence_ref")
        evidence_ref = ContextRef.from_dict(evidence_data, "evidence_ref") if evidence_data is not None else None

        return cls(
            task_id=data["task_id"],
            request_id=data["request_id"],
            brain_id=data["brain_id"],
            operation=data["operation"],
            status=data["status"],
            output_type=data["output_type"],
            artifact_ref=artifact_ref,
            evidence_ref=evidence_ref,
            error_code=data.get("error_code"),
            schema_version=data["schema_version"],
        )

    @classmethod
    def from_json(cls, text: str | bytes) -> BrainResult:
        if isinstance(text, (bytes, bytearray)):
            raw_bytes = bytes(text)
            if len(raw_bytes) > MAX_SERIALIZED_BYTES:
                raise ContinuityStateValidationError(
                    f"Input JSON size ({len(raw_bytes)} bytes) exceeds maximum allowable size of {MAX_SERIALIZED_BYTES} bytes"
                )
            try:
                decoded_text = raw_bytes.decode("utf-8")
            except UnicodeDecodeError as e:
                raise ContinuityStateValidationError(f"Invalid UTF-8 encoding in JSON: {e}") from e
        elif isinstance(text, str):
            raw_bytes = text.encode("utf-8")
            if len(raw_bytes) > MAX_SERIALIZED_BYTES:
                raise ContinuityStateValidationError(
                    f"Input JSON size ({len(raw_bytes)} bytes) exceeds maximum allowable size of {MAX_SERIALIZED_BYTES} bytes"
                )
            decoded_text = text
        else:
            raise ContinuityStateValidationError(f"from_json expects str or bytes, got: {type(text).__name__}")

        try:
            data = json.loads(decoded_text)
        except Exception as e:
            raise ContinuityStateValidationError(f"Malformed JSON input: {e}") from e

        return cls.from_dict(data)
