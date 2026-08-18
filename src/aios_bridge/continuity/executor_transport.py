"""Pure vendor-neutral Executor invocation transport contract (ADR-029 / E1)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import re
from typing import Any, Protocol, runtime_checkable

from .errors import ContinuityStateValidationError
from .executor import (
    ExecutionOperation,
    ExecutionRequest,
    PreparedExecution,
    validate_prepared_execution_against_request,
)
from .lease import ExecutorLease, validate_executor_lease_binding
from .state import (
    MAX_SERIALIZED_BYTES,
    SCHEMA_VERSION,
    _validate_actor_id,
    _validate_safe_git_ref,
)


MAX_INVOCATION_ID_LENGTH = 64
MAX_TRANSPORT_ID_LENGTH = 64
MAX_ERROR_CODE_LENGTH = 64
MAX_INVOCATION_PAYLOAD_BYTES = 1_048_576
MIN_PROCESS_EXIT_CODE = -2_147_483_648
MAX_PROCESS_EXIT_CODE = 2_147_483_647

_TASK_ID_PATTERN = re.compile(r"^TASK-\d+$")
_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:[a-z0-9_.\-:]+)*$")
_ERROR_CODE_PATTERN = re.compile(r"^[A-Za-z0-9_.\-]+$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

FORBIDDEN_INVOCATION_KEYS = {
    "approved",
    "human_approved",
    "authorization_token",
    "merge_allowed",
    "api_key",
    "token",
    "cookie",
    "cookies",
    "auth",
    "auth_header",
    "session_secret",
    "payload",
    "prompt",
    "context",
    "stdout",
    "stderr",
    "environment",
    "env",
    "command",
    "cwd",
}


class InvocationStatus(str, Enum):
    EXITED_ZERO = "EXITED_ZERO"
    EXITED_NONZERO = "EXITED_NONZERO"
    FAILED_TO_START = "FAILED_TO_START"
    TIMED_OUT = "TIMED_OUT"
    INTERRUPTED = "INTERRUPTED"


def _validate_task_id(value: Any, field_name: str = "task_id") -> str:
    if type(value) is not str or not _TASK_ID_PATTERN.fullmatch(value):
        raise ContinuityStateValidationError(
            f"{field_name} must match exact case-sensitive '^TASK-\\d+$', got: {value!r}"
        )
    return value


def _validate_canonical_id(value: Any, field_name: str, maximum_length: int) -> str:
    if type(value) is not str or not value:
        raise ContinuityStateValidationError(f"{field_name} must be a non-empty string")
    if value != value.strip():
        raise ContinuityStateValidationError(
            f"{field_name} must not contain leading or trailing whitespace: {value!r}"
        )
    if len(value) > maximum_length:
        raise ContinuityStateValidationError(
            f"{field_name} length exceeds maximum allowed ({maximum_length})"
        )
    if not _ID_PATTERN.fullmatch(value):
        raise ContinuityStateValidationError(
            f"{field_name} must be a conservative lowercase identifier, got: {value!r}"
        )
    return value


def _validate_executor_id(value: Any, field_name: str = "executor_id") -> str:
    if type(value) is not str or not value or value != value.strip():
        raise ContinuityStateValidationError(
            f"{field_name} must be an exact canonical actor ID, got: {value!r}"
        )
    canonical = _validate_actor_id(value, field_name)
    if canonical != value:
        raise ContinuityStateValidationError(
            f"{field_name} must be an exact canonical actor ID, got: {value!r}"
        )
    return value


def _validate_fingerprint(value: Any, field_name: str) -> str:
    if type(value) is not str or not _SHA256_PATTERN.fullmatch(value):
        raise ContinuityStateValidationError(
            f"{field_name} must be an exact lowercase 64-hex SHA-256 string, got: {value!r}"
        )
    return value


def _validate_operation(value: Any, field_name: str = "operation") -> ExecutionOperation:
    if isinstance(value, ExecutionOperation):
        return value
    try:
        return ExecutionOperation(value)
    except (TypeError, ValueError) as exc:
        raise ContinuityStateValidationError(
            f"{field_name} must be exact RUN or FIX, got: {value!r}"
        ) from exc


def _validate_target_branch(value: Any) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise ContinuityStateValidationError(
            f"target_branch must be an exact non-empty safe Git ref, got: {value!r}"
        )
    canonical = _validate_safe_git_ref(value, "target_branch")
    if canonical != value:
        raise ContinuityStateValidationError("target_branch must be an exact safe Git ref")
    return value


def _validate_serialized_size(value: dict[str, Any], context: str) -> None:
    size = len(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
            "utf-8"
        )
    )
    if size > MAX_SERIALIZED_BYTES:
        raise ContinuityStateValidationError(
            f"Serialized {context} exceeds size limit ({size} > {MAX_SERIALIZED_BYTES})"
        )


def _decode_json_input(value: str | bytes, context: str) -> Any:
    if type(value) is bytes:
        raw = value
        if len(raw) > MAX_SERIALIZED_BYTES:
            raise ContinuityStateValidationError(
                f"Input JSON byte size ({len(raw)}) exceeds maximum allowed ({MAX_SERIALIZED_BYTES})"
            )
        try:
            decoded = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ContinuityStateValidationError(
                f"Invalid UTF-8 encoding in input bytes for {context}: {exc}"
            ) from exc
    elif type(value) is str:
        raw = value.encode("utf-8")
        if len(raw) > MAX_SERIALIZED_BYTES:
            raise ContinuityStateValidationError(
                f"Input JSON byte size ({len(raw)}) exceeds maximum allowed ({MAX_SERIALIZED_BYTES})"
            )
        decoded = value
    else:
        raise ContinuityStateValidationError(
            f"from_json expects str or bytes, got: {type(value).__name__}"
        )
    try:
        return json.loads(decoded)
    except (TypeError, ValueError) as exc:
        raise ContinuityStateValidationError(f"Malformed JSON for {context}: {exc}") from exc


@dataclass(frozen=True)
class ExecutorInvocation:
    schema_version: str
    invocation_id: str
    task_id: str
    request_id: str
    executor_id: str
    transport_id: str
    operation: ExecutionOperation
    workspace_id: str
    target_branch: str
    execution_id: str
    request_fingerprint: str
    prepared_execution_fingerprint: str
    lease_fingerprint: str
    execution_fingerprint: str
    payload_sha256: str
    payload_size_bytes: int

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ContinuityStateValidationError(
                f"Unsupported schema_version in ExecutorInvocation: {self.schema_version!r}"
            )
        _validate_canonical_id(
            self.invocation_id, "invocation_id", MAX_INVOCATION_ID_LENGTH
        )
        _validate_task_id(self.task_id)
        _validate_canonical_id(self.request_id, "request_id", MAX_INVOCATION_ID_LENGTH)
        _validate_executor_id(self.executor_id)
        _validate_canonical_id(
            self.transport_id, "transport_id", MAX_TRANSPORT_ID_LENGTH
        )
        object.__setattr__(self, "operation", _validate_operation(self.operation))
        _validate_fingerprint(self.workspace_id, "workspace_id")
        _validate_target_branch(self.target_branch)
        _validate_canonical_id(self.execution_id, "execution_id", MAX_INVOCATION_ID_LENGTH)
        _validate_fingerprint(self.request_fingerprint, "request_fingerprint")
        _validate_fingerprint(
            self.prepared_execution_fingerprint, "prepared_execution_fingerprint"
        )
        _validate_fingerprint(self.lease_fingerprint, "lease_fingerprint")
        _validate_fingerprint(self.execution_fingerprint, "execution_fingerprint")
        _validate_fingerprint(self.payload_sha256, "payload_sha256")
        if (
            type(self.payload_size_bytes) is not int
            or not 1 <= self.payload_size_bytes <= MAX_INVOCATION_PAYLOAD_BYTES
        ):
            raise ContinuityStateValidationError(
                "payload_size_bytes must be an exact positive int not exceeding "
                f"{MAX_INVOCATION_PAYLOAD_BYTES}"
            )
        _validate_serialized_size(self.to_dict(), "ExecutorInvocation")

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_fingerprint": self.execution_fingerprint,
            "execution_id": self.execution_id,
            "executor_id": self.executor_id,
            "invocation_id": self.invocation_id,
            "lease_fingerprint": self.lease_fingerprint,
            "operation": self.operation.value,
            "payload_sha256": self.payload_sha256,
            "payload_size_bytes": self.payload_size_bytes,
            "prepared_execution_fingerprint": self.prepared_execution_fingerprint,
            "request_fingerprint": self.request_fingerprint,
            "request_id": self.request_id,
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

    @classmethod
    def from_dict(cls, data: Any) -> ExecutorInvocation:
        if not isinstance(data, dict):
            raise ContinuityStateValidationError(
                f"ExecutorInvocation root must be a dict, got: {type(data).__name__}"
            )
        forbidden = set(data).intersection(FORBIDDEN_INVOCATION_KEYS)
        if forbidden:
            raise ContinuityStateValidationError(
                f"Forbidden authority/secret/raw-payload fields in ExecutorInvocation: {sorted(forbidden)}"
            )
        required = {
            "schema_version",
            "invocation_id",
            "task_id",
            "request_id",
            "executor_id",
            "transport_id",
            "operation",
            "workspace_id",
            "target_branch",
            "execution_id",
            "request_fingerprint",
            "prepared_execution_fingerprint",
            "lease_fingerprint",
            "execution_fingerprint",
            "payload_sha256",
            "payload_size_bytes",
        }
        extra = set(data) - required
        missing = required - set(data)
        if extra:
            raise ContinuityStateValidationError(
                f"Unknown fields in ExecutorInvocation: {sorted(extra)}"
            )
        if missing:
            raise ContinuityStateValidationError(
                f"Missing required fields in ExecutorInvocation: {sorted(missing)}"
            )
        return cls(**{key: data[key] for key in required})

    @classmethod
    def from_json(cls, value: str | bytes) -> ExecutorInvocation:
        return cls.from_dict(_decode_json_input(value, cls.__name__))


def validate_executor_invocation(
    invocation: ExecutorInvocation,
    execution_request: ExecutionRequest,
    prepared_execution: PreparedExecution,
    executor_lease: ExecutorLease,
) -> None:
    if not isinstance(invocation, ExecutorInvocation):
        raise ContinuityStateValidationError("invocation must be an ExecutorInvocation")
    if not isinstance(execution_request, ExecutionRequest):
        raise ContinuityStateValidationError("execution_request must be an ExecutionRequest")
    if not isinstance(prepared_execution, PreparedExecution):
        raise ContinuityStateValidationError("prepared_execution must be a PreparedExecution")
    if not isinstance(executor_lease, ExecutorLease):
        raise ContinuityStateValidationError("executor_lease must be an ExecutorLease")

    validate_prepared_execution_against_request(prepared_execution, execution_request)
    expected_request_fields = {
        "schema_version": execution_request.schema_version,
        "task_id": execution_request.task_id,
        "request_id": execution_request.request_id,
        "executor_id": execution_request.executor_id,
        "operation": execution_request.operation,
        "target_branch": execution_request.target_branch,
    }
    for field_name, expected in expected_request_fields.items():
        if getattr(invocation, field_name) != expected:
            raise ContinuityStateValidationError(
                f"ExecutorInvocation {field_name} does not match ExecutionRequest"
            )
    if invocation.request_fingerprint != execution_request.fingerprint():
        raise ContinuityStateValidationError(
            "ExecutorInvocation request_fingerprint does not match ExecutionRequest"
        )
    if invocation.execution_id != prepared_execution.execution_id:
        raise ContinuityStateValidationError(
            "ExecutorInvocation execution_id does not match PreparedExecution"
        )
    if invocation.prepared_execution_fingerprint != prepared_execution.fingerprint():
        raise ContinuityStateValidationError(
            "ExecutorInvocation prepared_execution_fingerprint does not match PreparedExecution"
        )

    validate_executor_lease_binding(
        executor_lease,
        task_id=invocation.task_id,
        workspace_id=invocation.workspace_id,
        executor_id=invocation.executor_id,
        operation=invocation.operation,
        execution_fingerprint=invocation.execution_fingerprint,
    )
    if executor_lease.schema_version != invocation.schema_version:
        raise ContinuityStateValidationError(
            "ExecutorLease schema_version does not match ExecutorInvocation"
        )
    if invocation.lease_fingerprint != executor_lease.fingerprint():
        raise ContinuityStateValidationError(
            "ExecutorInvocation lease_fingerprint does not match ExecutorLease"
        )


def validate_invocation_payload(invocation: ExecutorInvocation, payload: bytes) -> None:
    if not isinstance(invocation, ExecutorInvocation):
        raise ContinuityStateValidationError("invocation must be an ExecutorInvocation")
    if type(payload) is not bytes:
        raise ContinuityStateValidationError("payload must be exact bytes")
    if not payload:
        raise ContinuityStateValidationError("payload must not be empty")
    if len(payload) > MAX_INVOCATION_PAYLOAD_BYTES:
        raise ContinuityStateValidationError("payload exceeds MAX_INVOCATION_PAYLOAD_BYTES")
    if len(payload) != invocation.payload_size_bytes:
        raise ContinuityStateValidationError("payload length does not match payload_size_bytes")
    if hashlib.sha256(payload).hexdigest() != invocation.payload_sha256:
        raise ContinuityStateValidationError("payload SHA-256 does not match payload_sha256")


def _validate_error_code(value: Any) -> str:
    if (
        type(value) is not str
        or not value
        or value != value.strip()
        or len(value) > MAX_ERROR_CODE_LENGTH
        or not _ERROR_CODE_PATTERN.fullmatch(value)
    ):
        raise ContinuityStateValidationError(
            f"error_code must be a bounded canonical error identifier, got: {value!r}"
        )
    return value


@dataclass(frozen=True)
class InvocationReceipt:
    schema_version: str
    invocation_id: str
    task_id: str
    request_id: str
    executor_id: str
    transport_id: str
    operation: ExecutionOperation
    execution_id: str
    invocation_fingerprint: str
    status: InvocationStatus
    exit_code: int | None
    error_code: str | None

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ContinuityStateValidationError(
                f"Unsupported schema_version in InvocationReceipt: {self.schema_version!r}"
            )
        _validate_canonical_id(
            self.invocation_id, "invocation_id", MAX_INVOCATION_ID_LENGTH
        )
        _validate_task_id(self.task_id)
        _validate_canonical_id(self.request_id, "request_id", MAX_INVOCATION_ID_LENGTH)
        _validate_executor_id(self.executor_id)
        _validate_canonical_id(
            self.transport_id, "transport_id", MAX_TRANSPORT_ID_LENGTH
        )
        object.__setattr__(self, "operation", _validate_operation(self.operation))
        _validate_canonical_id(self.execution_id, "execution_id", MAX_INVOCATION_ID_LENGTH)
        _validate_fingerprint(self.invocation_fingerprint, "invocation_fingerprint")
        if not isinstance(self.status, InvocationStatus):
            try:
                object.__setattr__(self, "status", InvocationStatus(self.status))
            except (TypeError, ValueError) as exc:
                raise ContinuityStateValidationError(
                    f"Invalid InvocationStatus: {self.status!r}"
                ) from exc

        if self.status is InvocationStatus.EXITED_ZERO:
            if type(self.exit_code) is not int or self.exit_code != 0:
                raise ContinuityStateValidationError(
                    "EXITED_ZERO requires exact integer exit_code 0"
                )
            if self.error_code is not None:
                raise ContinuityStateValidationError("EXITED_ZERO requires error_code None")
        elif self.status is InvocationStatus.EXITED_NONZERO:
            if (
                type(self.exit_code) is not int
                or self.exit_code == 0
                or not MIN_PROCESS_EXIT_CODE <= self.exit_code <= MAX_PROCESS_EXIT_CODE
            ):
                raise ContinuityStateValidationError(
                    "EXITED_NONZERO requires a bounded exact non-zero integer exit_code"
                )
            _validate_error_code(self.error_code)
        else:
            if self.exit_code is not None:
                raise ContinuityStateValidationError(
                    f"{self.status.value} requires exit_code None"
                )
            _validate_error_code(self.error_code)
        _validate_serialized_size(self.to_dict(), "InvocationReceipt")

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_code": self.error_code,
            "execution_id": self.execution_id,
            "executor_id": self.executor_id,
            "exit_code": self.exit_code,
            "invocation_fingerprint": self.invocation_fingerprint,
            "invocation_id": self.invocation_id,
            "operation": self.operation.value,
            "request_id": self.request_id,
            "schema_version": self.schema_version,
            "status": self.status.value,
            "task_id": self.task_id,
            "transport_id": self.transport_id,
        }

    def to_canonical_json(self) -> str:
        return json.dumps(
            self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )

    def fingerprint(self) -> str:
        return hashlib.sha256(self.to_canonical_json().encode("utf-8")).hexdigest()

    @classmethod
    def from_dict(cls, data: Any) -> InvocationReceipt:
        if not isinstance(data, dict):
            raise ContinuityStateValidationError(
                f"InvocationReceipt root must be a dict, got: {type(data).__name__}"
            )
        forbidden = set(data).intersection(FORBIDDEN_INVOCATION_KEYS)
        if forbidden:
            raise ContinuityStateValidationError(
                f"Forbidden authority/secret/raw-payload fields in InvocationReceipt: {sorted(forbidden)}"
            )
        required = {
            "schema_version",
            "invocation_id",
            "task_id",
            "request_id",
            "executor_id",
            "transport_id",
            "operation",
            "execution_id",
            "invocation_fingerprint",
            "status",
            "exit_code",
            "error_code",
        }
        extra = set(data) - required
        missing = required - set(data)
        if extra:
            raise ContinuityStateValidationError(
                f"Unknown fields in InvocationReceipt: {sorted(extra)}"
            )
        if missing:
            raise ContinuityStateValidationError(
                f"Missing required fields in InvocationReceipt: {sorted(missing)}"
            )
        return cls(**{key: data[key] for key in required})

    @classmethod
    def from_json(cls, value: str | bytes) -> InvocationReceipt:
        return cls.from_dict(_decode_json_input(value, cls.__name__))


def validate_invocation_receipt(
    receipt: InvocationReceipt, invocation: ExecutorInvocation
) -> None:
    if not isinstance(receipt, InvocationReceipt):
        raise ContinuityStateValidationError("receipt must be an InvocationReceipt")
    if not isinstance(invocation, ExecutorInvocation):
        raise ContinuityStateValidationError("invocation must be an ExecutorInvocation")
    expected = {
        "schema_version": invocation.schema_version,
        "invocation_id": invocation.invocation_id,
        "task_id": invocation.task_id,
        "request_id": invocation.request_id,
        "executor_id": invocation.executor_id,
        "transport_id": invocation.transport_id,
        "operation": invocation.operation,
        "execution_id": invocation.execution_id,
        "invocation_fingerprint": invocation.fingerprint(),
    }
    for field_name, value in expected.items():
        if getattr(receipt, field_name) != value:
            raise ContinuityStateValidationError(
                f"InvocationReceipt {field_name} does not match ExecutorInvocation"
            )


@runtime_checkable
class ExecutionTransport(Protocol):
    @property
    def transport_id(self) -> str:
        ...

    @property
    def executor_id(self) -> str:
        ...

    def invoke(
        self, invocation: ExecutorInvocation, payload: bytes
    ) -> InvocationReceipt:
        ...


def validate_transport_binding(
    transport: ExecutionTransport, invocation: ExecutorInvocation
) -> None:
    if not isinstance(invocation, ExecutorInvocation):
        raise ContinuityStateValidationError("invocation must be an ExecutorInvocation")
    transport_id = getattr(transport, "transport_id", None)
    executor_id = getattr(transport, "executor_id", None)
    _validate_canonical_id(transport_id, "transport.transport_id", MAX_TRANSPORT_ID_LENGTH)
    _validate_executor_id(executor_id, "transport.executor_id")
    if transport_id != invocation.transport_id:
        raise ContinuityStateValidationError(
            "Transport transport_id does not match ExecutorInvocation"
        )
    if executor_id != invocation.executor_id:
        raise ContinuityStateValidationError(
            "Transport executor_id does not match ExecutorInvocation"
        )


__all__ = [
    "MAX_INVOCATION_PAYLOAD_BYTES",
    "ExecutionTransport",
    "ExecutorInvocation",
    "InvocationReceipt",
    "InvocationStatus",
    "validate_executor_invocation",
    "validate_invocation_payload",
    "validate_invocation_receipt",
    "validate_transport_binding",
]
