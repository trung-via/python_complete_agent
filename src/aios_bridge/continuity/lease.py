"""
Executor Lease Contract for Open Multi-Agent Continuity OS (ADR-010 Milestone 5 / ADR-019 / TASK-029).
Provides immutable vendor-neutral lease models and pure relational lease binding validation.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any

from .errors import ContinuityStateValidationError
from .executor import ExecutionOperation
from .state import (
    MAX_SERIALIZED_BYTES,
    SCHEMA_VERSION,
    _validate_actor_id,
)

# Invariant (C2 / ADR-019): Parallel Executor mutation is strictly prohibited.
MAX_ACTIVE_EXECUTORS_PER_TASK = 1

_TASK_ID_PATTERN = re.compile(r"^TASK-\d+$")
_LEASE_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:[a-z0-9_.\-:]+)*$")
MAX_LEASE_ID_LENGTH = 64

FORBIDDEN_LEASE_KEYS = {
    "approved",
    "human_approved",
    "merge_allowed",
    "authorization_token",
    "api_key",
    "cookie",
    "cookies",
    "auth_header",
    "session_secret",
    "expires_at",
    "ttl",
    "heartbeat",
    "failover_target",
    "token",
    "auth",
}


def _validate_task_id(task_id: Any, field_name: str = "task_id") -> str:
    if isinstance(task_id, bool) or not isinstance(task_id, str):
        raise ContinuityStateValidationError(f"{field_name} must be a non-empty string")
    if not _TASK_ID_PATTERN.match(task_id):
        raise ContinuityStateValidationError(
            f"{field_name} must match exact case-sensitive '^TASK-\\d+$', got: {task_id!r}"
        )
    return task_id


def _validate_canonical_actor_id(actor_id: Any, field_name: str = "executor_id") -> str:
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


def _validate_canonical_lease_id(lease_id: Any, field_name: str = "lease_id") -> str:
    """Validates exact canonical lease ID with zero whitespace padding."""
    if isinstance(lease_id, bool) or not isinstance(lease_id, str) or not lease_id:
        raise ContinuityStateValidationError(f"{field_name} must be a non-empty string")
    if lease_id != lease_id.strip():
        raise ContinuityStateValidationError(
            f"{field_name} must not contain leading or trailing whitespace: {lease_id!r}"
        )
    if len(lease_id) > MAX_LEASE_ID_LENGTH:
        raise ContinuityStateValidationError(
            f"{field_name} length ({len(lease_id)}) exceeds maximum allowed ({MAX_LEASE_ID_LENGTH})"
        )
    if not _LEASE_ID_PATTERN.match(lease_id):
        raise ContinuityStateValidationError(
            f"{field_name} must be a conservative lowercase identifier (e.g. 'lease-task-029-abc'), got: {lease_id!r}"
        )
    return lease_id


def _validate_exact_hex_sha_64(fp: Any, field_name: str) -> str:
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


@dataclass(frozen=True)
class ExecutorLease:
    """
    Canonical representation of single-active-executor lease ownership (C3 / C4 / ADR-019).
    This record represents active task execution ownership, NOT authorization.
    """
    schema_version: str
    lease_id: str
    task_id: str
    workspace_id: str
    executor_id: str
    operation: ExecutionOperation
    execution_fingerprint: str

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ContinuityStateValidationError(
                f"Unsupported schema_version in ExecutorLease: {self.schema_version!r} (expected {SCHEMA_VERSION!r})"
            )
        _validate_canonical_lease_id(self.lease_id, "lease_id")
        _validate_task_id(self.task_id, "task_id")
        _validate_exact_hex_sha_64(self.workspace_id, "workspace_id")
        _validate_canonical_actor_id(self.executor_id, "executor_id")

        if not isinstance(self.operation, ExecutionOperation):
            try:
                object.__setattr__(self, "operation", ExecutionOperation(self.operation))
            except Exception as e:
                valid_ops = ", ".join(o.value for o in ExecutionOperation)
                raise ContinuityStateValidationError(
                    f"Invalid ExecutionOperation in ExecutorLease: {self.operation!r}. Valid values: {valid_ops}"
                ) from e

        _validate_exact_hex_sha_64(self.execution_fingerprint, "execution_fingerprint")

        raw_canonical = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        utf8_bytes = raw_canonical.encode("utf-8")
        if len(utf8_bytes) > MAX_SERIALIZED_BYTES:
            raise ContinuityStateValidationError(
                f"Serialized ExecutorLease exceeds size limit ({len(utf8_bytes)} > {MAX_SERIALIZED_BYTES})"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_fingerprint": self.execution_fingerprint,
            "executor_id": self.executor_id,
            "lease_id": self.lease_id,
            "operation": self.operation.value,
            "schema_version": self.schema_version,
            "task_id": self.task_id,
            "workspace_id": self.workspace_id,
        }

    def to_canonical_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    def fingerprint(self) -> str:
        return hashlib.sha256(self.to_canonical_json().encode("utf-8")).hexdigest()

    @classmethod
    def from_dict(cls, data: Any) -> ExecutorLease:
        if not isinstance(data, dict):
            raise ContinuityStateValidationError(
                f"ExecutorLease root must be a dict, got: {type(data).__name__}"
            )

        forbidden_present = set(data.keys()) & FORBIDDEN_LEASE_KEYS
        if forbidden_present:
            raise ContinuityStateValidationError(
                f"Forbidden authority/secret/timing fields in ExecutorLease: {sorted(forbidden_present)}"
            )

        allowed_keys = {
            "execution_fingerprint",
            "executor_id",
            "lease_id",
            "operation",
            "schema_version",
            "task_id",
            "workspace_id",
        }
        extra_keys = set(data.keys()) - allowed_keys
        if extra_keys:
            raise ContinuityStateValidationError(
                f"Unknown fields in ExecutorLease: {sorted(extra_keys)}"
            )

        for req in allowed_keys:
            if req not in data:
                raise ContinuityStateValidationError(f"Missing required field '{req}' in ExecutorLease")

        return cls(
            schema_version=data["schema_version"],
            lease_id=data["lease_id"],
            task_id=data["task_id"],
            workspace_id=data["workspace_id"],
            executor_id=data["executor_id"],
            operation=data["operation"],
            execution_fingerprint=data["execution_fingerprint"],
        )

    @classmethod
    def from_json(cls, json_str: str | bytes) -> ExecutorLease:
        if isinstance(json_str, bytes):
            if len(json_str) > MAX_SERIALIZED_BYTES:
                raise ContinuityStateValidationError(
                    f"Input JSON byte size ({len(json_str)}) exceeds maximum allowed ({MAX_SERIALIZED_BYTES})"
                )
            try:
                decoded = json_str.decode("utf-8")
            except UnicodeDecodeError as e:
                raise ContinuityStateValidationError(
                    f"Invalid UTF-8 encoding in input bytes for {cls.__name__}: {e}"
                ) from e
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
            raise ContinuityStateValidationError(f"Malformed JSON for ExecutorLease: {e}") from e

        return cls.from_dict(data)


def validate_executor_lease_binding(
    lease: ExecutorLease,
    *,
    task_id: str,
    workspace_id: str,
    executor_id: str,
    operation: ExecutionOperation,
    execution_fingerprint: str,
) -> None:
    """
    Pure validation of an ExecutorLease against its expected execution activation parameters (C7 / ADR-019).
    Fails closed on any task_id, workspace_id, executor_id, operation, or execution_fingerprint mismatch.
    """
    if not isinstance(lease, ExecutorLease):
        raise ContinuityStateValidationError(
            f"lease must be an ExecutorLease instance, got: {type(lease).__name__}"
        )

    if not isinstance(operation, ExecutionOperation):
        try:
            operation = ExecutionOperation(operation)
        except Exception as e:
            valid_ops = ", ".join(o.value for o in ExecutionOperation)
            raise ContinuityStateValidationError(
                f"Invalid expected ExecutionOperation in validate_executor_lease_binding: {operation!r}. Valid values: {valid_ops}"
            ) from e

    if lease.task_id != task_id:
        raise ContinuityStateValidationError(
            f"ExecutorLease task_id '{lease.task_id}' != expected task_id '{task_id}'"
        )

    if lease.workspace_id != workspace_id:
        raise ContinuityStateValidationError(
            f"ExecutorLease workspace_id '{lease.workspace_id}' != expected workspace_id '{workspace_id}'"
        )

    if lease.executor_id != executor_id:
        raise ContinuityStateValidationError(
            f"ExecutorLease executor_id '{lease.executor_id}' != expected executor_id '{executor_id}'"
        )

    if lease.operation != operation:
        raise ContinuityStateValidationError(
            f"ExecutorLease operation '{lease.operation.value}' != expected operation '{operation.value}'"
        )

    if lease.execution_fingerprint != execution_fingerprint:
        raise ContinuityStateValidationError(
            f"ExecutorLease execution_fingerprint '{lease.execution_fingerprint}' != expected execution_fingerprint '{execution_fingerprint}'"
        )
