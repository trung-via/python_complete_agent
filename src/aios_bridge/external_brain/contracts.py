"""Data contracts and value objects for AIOS Bridge External Brain."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Sequence

from .errors import ContractValidationError, CorrelationError

_HEX_64_PATTERN = re.compile(r"^[a-fA-F0-9]{64}$")
_TASK_ID_PATTERN = re.compile(r"^TASK-\d+$")


class ContextKind(str, Enum):
    """Kinds of context items that can be attached to an External Brain request."""
    TASK = "TASK"
    CONTRACT = "CONTRACT"
    SOURCE = "SOURCE"
    TEST = "TEST"
    DIFF = "DIFF"
    ERROR = "ERROR"
    ARCHITECTURE = "ARCHITECTURE"


class BrainRole(str, Enum):
    """The persona / role assumed by the External Brain."""
    ARCHITECT = "ARCHITECT"
    CODER = "CODER"
    DEBUGGER = "DEBUGGER"
    REVIEWER = "REVIEWER"


class BrainOperation(str, Enum):
    """The analytical / generation operation to perform."""
    PLAN = "PLAN"
    GENERATE_PATCH = "GENERATE_PATCH"
    DIAGNOSE_FAILURE = "DIAGNOSE_FAILURE"
    REVIEW_PATCH = "REVIEW_PATCH"


class BrainOutputType(str, Enum):
    """Expected output artifact format for the response."""
    PLAN = "PLAN"
    PATCH_PROPOSAL = "PATCH_PROPOSAL"
    DIAGNOSIS = "DIAGNOSIS"
    REVIEW = "REVIEW"


class ModelResponseStatus(str, Enum):
    """Normalized status of the model response."""
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    RATE_LIMITED = "RATE_LIMITED"
    UNAVAILABLE = "UNAVAILABLE"
    TIMEOUT = "TIMEOUT"
    AUTH_ERROR = "AUTH_ERROR"
    INVALID_RESPONSE = "INVALID_RESPONSE"


OPERATION_OUTPUT_MAP: dict[BrainOperation, BrainOutputType] = {
    BrainOperation.PLAN: BrainOutputType.PLAN,
    BrainOperation.GENERATE_PATCH: BrainOutputType.PATCH_PROPOSAL,
    BrainOperation.DIAGNOSE_FAILURE: BrainOutputType.DIAGNOSIS,
    BrainOperation.REVIEW_PATCH: BrainOutputType.REVIEW,
}


def get_expected_output_type(operation: BrainOperation) -> BrainOutputType:
    """Returns the locked expected BrainOutputType for a given BrainOperation."""
    if not isinstance(operation, BrainOperation):
        raise ContractValidationError(f"Invalid operation type: {operation}")
    return OPERATION_OUTPUT_MAP[operation]


@dataclass(frozen=True)
class ContextItem:
    """Immutable context piece supplied to the External Brain."""
    kind: ContextKind
    content: str
    path: str | None = None
    priority: int = 0
    content_sha256: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ContextKind):
            try:
                object.__setattr__(self, "kind", ContextKind(self.kind))
            except Exception as e:
                raise ContractValidationError(f"Invalid ContextKind: {self.kind}") from e

        if not isinstance(self.content, str):
            raise ContractValidationError("ContextItem content must be a non-null string")

        if isinstance(self.priority, bool) or not isinstance(self.priority, int):
            raise ContractValidationError(f"priority must be an integer, got: {type(self.priority)}")

        if self.content_sha256 is not None:
            if not isinstance(self.content_sha256, str) or not _HEX_64_PATTERN.match(self.content_sha256):
                raise ContractValidationError(
                    f"content_sha256 must be a 64-character hexadecimal string, got: {self.content_sha256!r}"
                )

        if self.path is not None and not isinstance(self.path, str):
            raise ContractValidationError(f"path must be a string if provided, got: {type(self.path)}")

    def to_dict(self) -> dict[str, Any]:
        """Deterministic JSON-serializable dictionary representation."""
        return {
            "kind": self.kind.value,
            "content": self.content,
            "path": self.path,
            "priority": self.priority,
            "content_sha256": self.content_sha256,
        }


@dataclass(frozen=True)
class ModelRequest:
    """Immutable request contract for External Brain operations."""
    schema_version: str
    request_id: str
    task_id: str
    role: BrainRole
    operation: BrainOperation
    instruction: str
    context: tuple[ContextItem, ...]
    output_format: BrainOutputType
    provider: str | None = None
    model: str | None = None
    max_input_tokens: int | None = None
    max_output_tokens: int | None = None

    def __post_init__(self) -> None:
        if self.schema_version != "1":
            raise ContractValidationError(f"Unsupported schema_version: {self.schema_version!r} (expected '1')")

        if not self.request_id or not isinstance(self.request_id, str) or not self.request_id.strip():
            raise ContractValidationError("request_id must be a non-empty string")

        if not self.task_id or not isinstance(self.task_id, str) or not _TASK_ID_PATTERN.match(self.task_id):
            raise ContractValidationError(
                f"task_id must follow the 'TASK-<digits>' pattern (e.g. TASK-014), got: {self.task_id!r}"
            )

        if not isinstance(self.role, BrainRole):
            try:
                object.__setattr__(self, "role", BrainRole(self.role))
            except Exception as e:
                raise ContractValidationError(f"Invalid BrainRole: {self.role}") from e

        if not isinstance(self.operation, BrainOperation):
            try:
                object.__setattr__(self, "operation", BrainOperation(self.operation))
            except Exception as e:
                raise ContractValidationError(f"Invalid BrainOperation: {self.operation}") from e

        if not isinstance(self.instruction, str) or not self.instruction.strip():
            raise ContractValidationError("instruction must be a non-empty string")

        if not isinstance(self.output_format, BrainOutputType):
            try:
                object.__setattr__(self, "output_format", BrainOutputType(self.output_format))
            except Exception as e:
                raise ContractValidationError(f"Invalid BrainOutputType: {self.output_format}") from e

        expected_output = get_expected_output_type(self.operation)
        if self.output_format != expected_output:
            raise ContractValidationError(
                f"output_format mismatch for operation {self.operation.value}: "
                f"expected {expected_output.value}, got {self.output_format.value}"
            )

        if not isinstance(self.context, tuple):
            if isinstance(self.context, Sequence):
                object.__setattr__(self, "context", tuple(self.context))
            else:
                raise ContractValidationError("context must be a sequence/tuple of ContextItem")

        for item in self.context:
            if not isinstance(item, ContextItem):
                raise ContractValidationError(f"All context items must be ContextItem instances, got: {type(item)}")

        if self.max_input_tokens is not None:
            if isinstance(self.max_input_tokens, bool) or not isinstance(self.max_input_tokens, int) or self.max_input_tokens <= 0:
                raise ContractValidationError("max_input_tokens must be a positive integer if specified")

        if self.max_output_tokens is not None:
            if isinstance(self.max_output_tokens, bool) or not isinstance(self.max_output_tokens, int) or self.max_output_tokens <= 0:
                raise ContractValidationError("max_output_tokens must be a positive integer if specified")

    def to_dict(self) -> dict[str, Any]:
        """Deterministic JSON-serializable dictionary representation."""
        return {
            "schema_version": self.schema_version,
            "request_id": self.request_id,
            "task_id": self.task_id,
            "role": self.role.value,
            "operation": self.operation.value,
            "instruction": self.instruction,
            "context": [item.to_dict() for item in self.context],
            "output_format": self.output_format.value,
            "provider": self.provider,
            "model": self.model,
            "max_input_tokens": self.max_input_tokens,
            "max_output_tokens": self.max_output_tokens,
        }


@dataclass(frozen=True)
class ModelResponse:
    """Immutable response contract for External Brain operations."""
    schema_version: str
    request_id: str
    task_id: str
    provider: str
    model: str
    status: ModelResponseStatus
    output_type: BrainOutputType | None
    content: str | None
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: int | None = None
    provider_request_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        if self.schema_version != "1":
            raise ContractValidationError(f"Unsupported schema_version: {self.schema_version!r} (expected '1')")

        if not self.request_id or not isinstance(self.request_id, str) or not self.request_id.strip():
            raise ContractValidationError("request_id must be a non-empty string")

        if not self.task_id or not isinstance(self.task_id, str) or not self.task_id.strip():
            raise ContractValidationError("task_id must be a non-empty string")

        if not self.provider or not isinstance(self.provider, str) or not self.provider.strip():
            raise ContractValidationError("provider must be a non-empty string")

        if not self.model or not isinstance(self.model, str) or not self.model.strip():
            raise ContractValidationError("model must be a non-empty string")

        if not isinstance(self.status, ModelResponseStatus):
            try:
                object.__setattr__(self, "status", ModelResponseStatus(self.status))
            except Exception as e:
                raise ContractValidationError(f"Invalid ModelResponseStatus: {self.status}") from e

        if self.status == ModelResponseStatus.SUCCESS:
            if self.output_type is None:
                raise ContractValidationError("SUCCESS status requires non-null output_type")
            if not isinstance(self.output_type, BrainOutputType):
                try:
                    object.__setattr__(self, "output_type", BrainOutputType(self.output_type))
                except Exception as e:
                    raise ContractValidationError(f"Invalid BrainOutputType: {self.output_type}") from e
            if not isinstance(self.content, str) or not self.content.strip():
                raise ContractValidationError("SUCCESS status requires non-empty content string")
            if self.error_code is not None:
                raise ContractValidationError(f"SUCCESS status cannot have error_code (got {self.error_code!r})")
            if self.error_message is not None:
                raise ContractValidationError(f"SUCCESS status cannot have error_message (got {self.error_message!r})")
        else:
            if self.output_type is not None and not isinstance(self.output_type, BrainOutputType):
                try:
                    object.__setattr__(self, "output_type", BrainOutputType(self.output_type))
                except Exception as e:
                    raise ContractValidationError(f"Invalid BrainOutputType: {self.output_type}") from e

        if self.input_tokens is not None:
            if isinstance(self.input_tokens, bool) or not isinstance(self.input_tokens, int) or self.input_tokens < 0:
                raise ContractValidationError("input_tokens must be a non-negative integer if specified")

        if self.output_tokens is not None:
            if isinstance(self.output_tokens, bool) or not isinstance(self.output_tokens, int) or self.output_tokens < 0:
                raise ContractValidationError("output_tokens must be a non-negative integer if specified")

        if self.latency_ms is not None:
            if isinstance(self.latency_ms, bool) or not isinstance(self.latency_ms, int) or self.latency_ms < 0:
                raise ContractValidationError("latency_ms must be a non-negative integer if specified")

    def to_dict(self) -> dict[str, Any]:
        """Deterministic JSON-serializable dictionary representation."""
        return {
            "schema_version": self.schema_version,
            "request_id": self.request_id,
            "task_id": self.task_id,
            "provider": self.provider,
            "model": self.model,
            "status": self.status.value,
            "output_type": self.output_type.value if self.output_type is not None else None,
            "content": self.content,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "latency_ms": self.latency_ms,
            "provider_request_id": self.provider_request_id,
            "error_code": self.error_code,
            "error_message": self.error_message,
        }


def validate_request_response_correlation(request: ModelRequest, response: ModelResponse) -> None:
    """
    Validates that a ModelResponse belongs to and correlates with a specific ModelRequest.
    Raises CorrelationError if any invariant fails.
    """
    if request.request_id != response.request_id:
        raise CorrelationError(
            f"Request ID mismatch: request.request_id={request.request_id!r}, "
            f"response.request_id={response.request_id!r}"
        )

    if request.task_id != response.task_id:
        raise CorrelationError(
            f"Task ID mismatch: request.task_id={request.task_id!r}, "
            f"response.task_id={response.task_id!r}"
        )

    if response.status == ModelResponseStatus.SUCCESS:
        expected_output = get_expected_output_type(request.operation)
        if response.output_type != expected_output:
            raise CorrelationError(
                f"Output type mismatch for operation {request.operation.value}: "
                f"expected {expected_output.value}, response returned {response.output_type.value if response.output_type else None}"
            )
