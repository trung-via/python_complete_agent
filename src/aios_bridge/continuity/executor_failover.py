"""
Stable-Boundary Executor Failover Contract for Open Multi-Agent Continuity OS (ADR-010 / ADR-020 Milestone 6 / TASK-030).
Provides immutable vendor-neutral failover proof models and pure relational failover validation.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any

from .errors import ContinuityStateValidationError
from .executor import ExecutionOperation
from .lease import (
    ExecutorLease,
    _validate_canonical_actor_id,
    _validate_exact_hex_sha_64,
    _validate_task_id,
)
from .state import (
    MAX_SERIALIZED_BYTES,
    SCHEMA_VERSION,
    ArtifactRef,
    _validate_exact_hex_sha,
    _validate_safe_git_ref,
)

FORBIDDEN_FAILOVER_PROOF_KEYS = {
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
    "token",
    "auth",
    "pid",
    "quota",
    "command",
    "prompt",
    "transcript",
    "next_executor",
}


def _validate_task_specific_artifact_path(path: str, task_id: str, artifact_type: str) -> None:
    """Validates that artifact path matches the exact numeric task identity without alias tolerance (R1-4)."""
    match = re.match(r"^TASK-(\d+)$", task_id)
    if not match:
        raise ContinuityStateValidationError(f"Invalid task_id format: {task_id!r}")
    task_suffix = match.group(1)

    if artifact_type == "RESULT":
        expected_path = f".ai/results/RESULT-{task_suffix}.md"
        if path != expected_path:
            raise ContinuityStateValidationError(
                f"Source RESULT artifact path '{path}' does not match task_id '{task_id}' (expected '{expected_path}')"
            )
    elif artifact_type == "REVIEW":
        expected_path = f".ai/reviews/REVIEW-{task_suffix}.md"
        if path != expected_path:
            raise ContinuityStateValidationError(
                f"REVIEW artifact path '{path}' does not match task_id '{task_id}' (expected '{expected_path}')"
            )
    else:
        raise ContinuityStateValidationError(f"Unknown artifact type: {artifact_type}")


@dataclass(frozen=True)
class StableExecutorFailoverProof:
    """
    Immutable, content-addressed proof of a valid stable-boundary Executor failover (ADR-020 / C2).
    Captures exact source execution/lease/RESULT identities and replacement execution/lease/REVIEW bindings.
    """
    schema_version: str
    task_id: str
    target_branch: str
    source_executor_id: str
    source_operation: ExecutionOperation
    source_execution_fingerprint: str
    source_lease_fingerprint: str
    source_published_sha: str
    source_result_ref: ArtifactRef
    replacement_executor_id: str
    replacement_operation: ExecutionOperation
    replacement_execution_fingerprint: str
    replacement_lease_fingerprint: str
    review_ref: ArtifactRef

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ContinuityStateValidationError(
                f"Unsupported schema_version in StableExecutorFailoverProof: {self.schema_version!r} (expected {SCHEMA_VERSION!r})"
            )
        _validate_task_id(self.task_id, "task_id")
        _validate_safe_git_ref(self.target_branch, "target_branch")

        _validate_canonical_actor_id(self.source_executor_id, "source_executor_id")
        _validate_canonical_actor_id(self.replacement_executor_id, "replacement_executor_id")

        if self.source_executor_id == self.replacement_executor_id:
            raise ContinuityStateValidationError(
                f"source_executor_id '{self.source_executor_id}' and replacement_executor_id "
                f"'{self.replacement_executor_id}' must differ for failover (C4)"
            )

        if not isinstance(self.source_operation, ExecutionOperation) or self.source_operation not in (
            ExecutionOperation.RUN,
            ExecutionOperation.FIX,
        ):
            raise ContinuityStateValidationError(
                f"source_operation must be ExecutionOperation.RUN or ExecutionOperation.FIX, got: {self.source_operation!r}"
            )

        if not isinstance(self.replacement_operation, ExecutionOperation) or self.replacement_operation != ExecutionOperation.FIX:
            raise ContinuityStateValidationError(
                f"replacement_operation must be ExecutionOperation.FIX, got: {self.replacement_operation!r} (C5)"
            )

        _validate_exact_hex_sha_64(self.source_execution_fingerprint, "source_execution_fingerprint")
        _validate_exact_hex_sha_64(self.source_lease_fingerprint, "source_lease_fingerprint")
        _validate_exact_hex_sha(self.source_published_sha, "source_published_sha")

        _validate_exact_hex_sha_64(self.replacement_execution_fingerprint, "replacement_execution_fingerprint")
        _validate_exact_hex_sha_64(self.replacement_lease_fingerprint, "replacement_lease_fingerprint")

        if not isinstance(self.source_result_ref, ArtifactRef):
            raise ContinuityStateValidationError(
                f"source_result_ref must be ArtifactRef, got: {type(self.source_result_ref).__name__}"
            )

        if not isinstance(self.review_ref, ArtifactRef):
            raise ContinuityStateValidationError(
                f"review_ref must be ArtifactRef, got: {type(self.review_ref).__name__}"
            )

        # Exact task and role identity checks (C3)
        _validate_task_specific_artifact_path(self.source_result_ref.path, self.task_id, "RESULT")
        _validate_task_specific_artifact_path(self.review_ref.path, self.task_id, "REVIEW")

        # Immutable Git anchors (C6)
        if self.source_result_ref.ref != self.source_published_sha:
            raise ContinuityStateValidationError(
                f"source_result_ref.ref '{self.source_result_ref.ref}' must equal source_published_sha '{self.source_published_sha}'"
            )

        _validate_exact_hex_sha(self.review_ref.ref, "review_ref.ref")

        # Enforce canonical serialized size limit on every construction path (R1-4)
        canonical_bytes = self.to_canonical_json().encode("utf-8")
        if len(canonical_bytes) > MAX_SERIALIZED_BYTES:
            raise ContinuityStateValidationError(
                f"StableExecutorFailoverProof serialized size ({len(canonical_bytes)} bytes) exceeds maximum allowed ({MAX_SERIALIZED_BYTES} bytes)"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "replacement_execution_fingerprint": self.replacement_execution_fingerprint,
            "replacement_executor_id": self.replacement_executor_id,
            "replacement_lease_fingerprint": self.replacement_lease_fingerprint,
            "replacement_operation": self.replacement_operation.value,
            "review_ref": self.review_ref.to_dict(),
            "schema_version": self.schema_version,
            "source_execution_fingerprint": self.source_execution_fingerprint,
            "source_executor_id": self.source_executor_id,
            "source_lease_fingerprint": self.source_lease_fingerprint,
            "source_operation": self.source_operation.value,
            "source_published_sha": self.source_published_sha,
            "source_result_ref": self.source_result_ref.to_dict(),
            "target_branch": self.target_branch,
            "task_id": self.task_id,
        }

    def to_canonical_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    def fingerprint(self) -> str:
        return hashlib.sha256(self.to_canonical_json().encode("utf-8")).hexdigest()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StableExecutorFailoverProof:
        if not isinstance(data, dict):
            raise ContinuityStateValidationError(
                f"from_dict expects a dict, got: {type(data).__name__}"
            )

        # Check forbidden keys (C9)
        forbidden = set(data.keys()) & FORBIDDEN_FAILOVER_PROOF_KEYS
        if forbidden:
            raise ContinuityStateValidationError(
                f"Forbidden authority/secret/transport keys present in failover proof: {sorted(forbidden)}"
            )

        allowed_keys = {
            "schema_version",
            "task_id",
            "target_branch",
            "source_executor_id",
            "source_operation",
            "source_execution_fingerprint",
            "source_lease_fingerprint",
            "source_published_sha",
            "source_result_ref",
            "replacement_executor_id",
            "replacement_operation",
            "replacement_execution_fingerprint",
            "replacement_lease_fingerprint",
            "review_ref",
        }
        unknown = set(data.keys()) - allowed_keys
        if unknown:
            raise ContinuityStateValidationError(
                f"Unknown fields rejected in StableExecutorFailoverProof: {sorted(unknown)}"
            )

        required_keys = {
            "schema_version",
            "task_id",
            "target_branch",
            "source_executor_id",
            "source_operation",
            "source_execution_fingerprint",
            "source_lease_fingerprint",
            "source_published_sha",
            "source_result_ref",
            "replacement_executor_id",
            "replacement_operation",
            "replacement_execution_fingerprint",
            "replacement_lease_fingerprint",
            "review_ref",
        }
        missing = required_keys - set(data.keys())
        if missing:
            raise ContinuityStateValidationError(
                f"Missing required fields in StableExecutorFailoverProof: {sorted(missing)}"
            )

        try:
            source_op = ExecutionOperation(data["source_operation"])
        except Exception as e:
            raise ContinuityStateValidationError(
                f"Invalid source_operation in failover proof: {data.get('source_operation')!r}"
            ) from e

        try:
            replacement_op = ExecutionOperation(data["replacement_operation"])
        except Exception as e:
            raise ContinuityStateValidationError(
                f"Invalid replacement_operation in failover proof: {data.get('replacement_operation')!r}"
            ) from e

        source_result = ArtifactRef.from_dict(data["source_result_ref"], "source_result_ref")
        review = ArtifactRef.from_dict(data["review_ref"], "review_ref")

        return cls(
            schema_version=data["schema_version"],
            task_id=data["task_id"],
            target_branch=data["target_branch"],
            source_executor_id=data["source_executor_id"],
            source_operation=source_op,
            source_execution_fingerprint=data["source_execution_fingerprint"],
            source_lease_fingerprint=data["source_lease_fingerprint"],
            source_published_sha=data["source_published_sha"],
            source_result_ref=source_result,
            replacement_executor_id=data["replacement_executor_id"],
            replacement_operation=replacement_op,
            replacement_execution_fingerprint=data["replacement_execution_fingerprint"],
            replacement_lease_fingerprint=data["replacement_lease_fingerprint"],
            review_ref=review,
        )

    @classmethod
    def from_json(cls, data: bytes | str | dict[str, Any]) -> StableExecutorFailoverProof:
        if isinstance(data, (bytes, bytearray)):
            if len(data) > MAX_SERIALIZED_BYTES:
                raise ContinuityStateValidationError(
                    f"Payload size ({len(data)} bytes) exceeds limit ({MAX_SERIALIZED_BYTES} bytes)"
                )
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError as e:
                raise ContinuityStateValidationError(f"Invalid UTF-8 payload: {e}") from e
            try:
                parsed = json.loads(text)
            except Exception as e:
                raise ContinuityStateValidationError(f"Malformed JSON payload: {e}") from e
        elif isinstance(data, str):
            raw_bytes = data.encode("utf-8")
            if len(raw_bytes) > MAX_SERIALIZED_BYTES:
                raise ContinuityStateValidationError(
                    f"Payload size ({len(raw_bytes)} bytes) exceeds limit ({MAX_SERIALIZED_BYTES} bytes)"
                )
            try:
                parsed = json.loads(data)
            except Exception as e:
                raise ContinuityStateValidationError(f"Malformed JSON payload: {e}") from e
        elif isinstance(data, dict):
            parsed = data
        else:
            raise ContinuityStateValidationError(
                f"Data must be bytes, str, or dict, got: {type(data).__name__}"
            )

        return cls.from_dict(parsed)


def validate_stable_executor_failover(
    proof: StableExecutorFailoverProof,
    *,
    source_lease: ExecutorLease,
    replacement_lease: ExecutorLease,
) -> None:
    """
    Pure relational validator for stable-boundary Executor failover (ADR-020 / C8).
    Binds exact relational equality across proof, source lease, and replacement lease without any I/O.
    """
    if not isinstance(proof, StableExecutorFailoverProof):
        raise ContinuityStateValidationError(
            f"proof must be StableExecutorFailoverProof, got: {type(proof).__name__}"
        )
    if not isinstance(source_lease, ExecutorLease):
        raise ContinuityStateValidationError(
            f"source_lease must be ExecutorLease, got: {type(source_lease).__name__}"
        )
    if not isinstance(replacement_lease, ExecutorLease):
        raise ContinuityStateValidationError(
            f"replacement_lease must be ExecutorLease, got: {type(replacement_lease).__name__}"
        )

    # 1. Task ID binding
    if source_lease.task_id != proof.task_id:
        raise ContinuityStateValidationError(
            f"Source lease task_id '{source_lease.task_id}' does not match proof task_id '{proof.task_id}'"
        )
    if replacement_lease.task_id != proof.task_id:
        raise ContinuityStateValidationError(
            f"Replacement lease task_id '{replacement_lease.task_id}' does not match proof task_id '{proof.task_id}'"
        )

    # 2. Source Executor & Operation binding
    if source_lease.executor_id != proof.source_executor_id:
        raise ContinuityStateValidationError(
            f"Source lease executor_id '{source_lease.executor_id}' does not match proof source_executor_id '{proof.source_executor_id}'"
        )
    if source_lease.operation != proof.source_operation:
        raise ContinuityStateValidationError(
            f"Source lease operation '{source_lease.operation.value}' does not match proof source_operation '{proof.source_operation.value}'"
        )
    if source_lease.execution_fingerprint != proof.source_execution_fingerprint:
        raise ContinuityStateValidationError(
            f"Source lease execution_fingerprint '{source_lease.execution_fingerprint}' does not match proof '{proof.source_execution_fingerprint}'"
        )
    if source_lease.fingerprint() != proof.source_lease_fingerprint:
        raise ContinuityStateValidationError(
            f"Source lease fingerprint '{source_lease.fingerprint()}' does not match proof source_lease_fingerprint '{proof.source_lease_fingerprint}'"
        )

    # 3. Replacement Executor & Operation binding
    if replacement_lease.executor_id != proof.replacement_executor_id:
        raise ContinuityStateValidationError(
            f"Replacement lease executor_id '{replacement_lease.executor_id}' does not match proof replacement_executor_id '{proof.replacement_executor_id}'"
        )
    if replacement_lease.operation != proof.replacement_operation or replacement_lease.operation != ExecutionOperation.FIX:
        raise ContinuityStateValidationError(
            f"Replacement lease operation '{replacement_lease.operation.value}' must be FIX and match proof '{proof.replacement_operation.value}'"
        )
    if replacement_lease.execution_fingerprint != proof.replacement_execution_fingerprint:
        raise ContinuityStateValidationError(
            f"Replacement lease execution_fingerprint '{replacement_lease.execution_fingerprint}' does not match proof '{proof.replacement_execution_fingerprint}'"
        )
    if replacement_lease.fingerprint() != proof.replacement_lease_fingerprint:
        raise ContinuityStateValidationError(
            f"Replacement lease fingerprint '{replacement_lease.fingerprint()}' does not match proof replacement_lease_fingerprint '{proof.replacement_lease_fingerprint}'"
        )

    # 4. Same-workspace invariant (C8)
    if source_lease.workspace_id != replacement_lease.workspace_id:
        raise ContinuityStateValidationError(
            f"Source workspace '{source_lease.workspace_id}' and replacement workspace '{replacement_lease.workspace_id}' must match (same-workspace failover)"
        )

    # 5. Distinct executor invariant (C4)
    if proof.source_executor_id == proof.replacement_executor_id:
        raise ContinuityStateValidationError(
            f"source_executor_id and replacement_executor_id cannot be identical for failover: {proof.source_executor_id!r}"
        )
