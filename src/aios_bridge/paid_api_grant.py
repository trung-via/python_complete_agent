from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from .continuity.dispatch import DispatchActorKind
from .continuity.state import BrainOperation, MAX_SERIALIZED_BYTES


PAID_API_GRANT_SCHEMA_VERSION = "1"
MAX_PAID_API_INPUT_TOKENS = 1_000_000
MAX_PAID_API_OUTPUT_TOKENS = 262_144
MAX_PAID_API_GRANT_ID_LENGTH = 96
MAX_PAID_API_ACTOR_ID_LENGTH = 128
MAX_PAID_API_PROVIDER_ID_LENGTH = 128
MAX_PAID_API_MODEL_ID_LENGTH = 256


_GRANT_ID_PATTERN = re.compile(r"[a-z0-9]+(?:[a-z0-9_.:-]*[a-z0-9])?")
_TASK_ID_PATTERN = re.compile(r"TASK-[0-9]+")
_ACTOR_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]*")
_GIT_BLOB_SHA_PATTERN = re.compile(r"[0-9a-f]{40}")
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _require_exact_string(value: Any, field_name: str) -> str:
    if type(value) is not str:
        raise ValueError(f"{field_name} must be an exact string")
    return value


def _require_bounded_identifier(
    value: Any,
    field_name: str,
    maximum_length: int,
    *,
    pattern: re.Pattern[str] | None = None,
) -> str:
    value = _require_exact_string(value, field_name)
    if not value or value != value.strip():
        raise ValueError(f"{field_name} must be non-empty and unpadded")
    if len(value) > maximum_length:
        raise ValueError(f"{field_name} exceeds its maximum length")
    if not all(character.isprintable() for character in value):
        raise ValueError(f"{field_name} contains a control character")
    if pattern is not None and pattern.fullmatch(value) is None:
        raise ValueError(f"{field_name} has an invalid format")
    return value


def _require_exact_int(value: Any, field_name: str) -> int:
    if type(value) is not int:
        raise ValueError(f"{field_name} must be an exact integer")
    return value


def _parse_actor_kind(value: Any) -> DispatchActorKind:
    if isinstance(value, DispatchActorKind):
        actor_kind = value
    elif type(value) is str:
        try:
            actor_kind = DispatchActorKind(value)
        except ValueError as exc:
            raise ValueError("actor_kind is invalid") from exc
    else:
        raise ValueError("actor_kind must be a DispatchActorKind value")
    if actor_kind is not DispatchActorKind.BRAIN:
        raise ValueError("paid API grants are restricted to BRAIN actors")
    return actor_kind


def _parse_brain_operation(value: Any) -> BrainOperation:
    if isinstance(value, BrainOperation):
        return value
    if type(value) is str:
        try:
            return BrainOperation(value)
        except ValueError as exc:
            raise ValueError("brain_operation is invalid") from exc
    raise ValueError("brain_operation must be a BrainOperation value")


def _validate_artifact_path(value: Any) -> str:
    value = _require_exact_string(value, "authorized_artifact_path")
    if not value or not value.startswith(".ai/"):
        raise ValueError("authorized_artifact_path must start with .ai/")
    if "\\" in value or ":" in value or value.startswith("/"):
        raise ValueError("authorized_artifact_path must be repository-relative")
    if any(character in value for character in ("\x00", "\r", "\n")):
        raise ValueError("authorized_artifact_path contains a forbidden character")
    components = value.split("/")
    if any(component in ("", ".", "..") for component in components):
        raise ValueError("authorized_artifact_path is not canonical")
    return value


@dataclass(frozen=True)
class PaidApiGrant:
    schema_version: str
    grant_id: str
    task_id: str
    actor_kind: DispatchActorKind
    brain_id: str
    provider_id: str
    model_id: str
    brain_operation: BrainOperation
    authorized_artifact_path: str
    authorized_artifact_blob_sha: str
    max_input_tokens: int
    max_output_tokens: int
    max_calls: int
    expires_at_epoch_seconds: int
    workspace_id: str
    grant_fingerprint: str | None = None

    def __post_init__(self) -> None:
        if type(self.schema_version) is not str or self.schema_version != PAID_API_GRANT_SCHEMA_VERSION:
            raise ValueError("schema_version is invalid")

        _require_bounded_identifier(
            self.grant_id,
            "grant_id",
            MAX_PAID_API_GRANT_ID_LENGTH,
            pattern=_GRANT_ID_PATTERN,
        )

        task_id = _require_exact_string(self.task_id, "task_id")
        if _TASK_ID_PATTERN.fullmatch(task_id) is None:
            raise ValueError("task_id is invalid")

        actor_kind = _parse_actor_kind(self.actor_kind)
        object.__setattr__(self, "actor_kind", actor_kind)

        _require_bounded_identifier(
            self.brain_id,
            "brain_id",
            MAX_PAID_API_ACTOR_ID_LENGTH,
            pattern=_ACTOR_ID_PATTERN,
        )
        _require_bounded_identifier(
            self.provider_id,
            "provider_id",
            MAX_PAID_API_PROVIDER_ID_LENGTH,
            pattern=_ACTOR_ID_PATTERN,
        )
        _require_bounded_identifier(
            self.model_id,
            "model_id",
            MAX_PAID_API_MODEL_ID_LENGTH,
        )

        brain_operation = _parse_brain_operation(self.brain_operation)
        object.__setattr__(self, "brain_operation", brain_operation)

        _validate_artifact_path(self.authorized_artifact_path)
        artifact_blob_sha = _require_exact_string(
            self.authorized_artifact_blob_sha,
            "authorized_artifact_blob_sha",
        )
        if _GIT_BLOB_SHA_PATTERN.fullmatch(artifact_blob_sha) is None:
            raise ValueError("authorized_artifact_blob_sha is invalid")

        max_input_tokens = _require_exact_int(self.max_input_tokens, "max_input_tokens")
        if not 1 <= max_input_tokens <= MAX_PAID_API_INPUT_TOKENS:
            raise ValueError("max_input_tokens is outside the permitted range")

        max_output_tokens = _require_exact_int(self.max_output_tokens, "max_output_tokens")
        if not 1 <= max_output_tokens <= MAX_PAID_API_OUTPUT_TOKENS:
            raise ValueError("max_output_tokens is outside the permitted range")

        max_calls = _require_exact_int(self.max_calls, "max_calls")
        if max_calls != 1:
            raise ValueError("max_calls must equal 1")

        expires_at = _require_exact_int(
            self.expires_at_epoch_seconds,
            "expires_at_epoch_seconds",
        )
        if expires_at <= 0:
            raise ValueError("expires_at_epoch_seconds must be positive")

        workspace_id = _require_exact_string(self.workspace_id, "workspace_id")
        if _SHA256_PATTERN.fullmatch(workspace_id) is None:
            raise ValueError("workspace_id is invalid")

        computed_fingerprint = self.fingerprint()
        if self.grant_fingerprint is None:
            object.__setattr__(self, "grant_fingerprint", computed_fingerprint)
        else:
            stored_fingerprint = _require_exact_string(
                self.grant_fingerprint,
                "grant_fingerprint",
            )
            if _SHA256_PATTERN.fullmatch(stored_fingerprint) is None:
                raise ValueError("grant_fingerprint is invalid")
            if stored_fingerprint != computed_fingerprint:
                raise ValueError("grant_fingerprint does not match grant semantics")

        serialized_bytes = self.to_canonical_json().encode("utf-8")
        if len(serialized_bytes) > MAX_SERIALIZED_BYTES:
            raise ValueError("serialized paid API grant exceeds MAX_SERIALIZED_BYTES")

    def semantic_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "grant_id": self.grant_id,
            "task_id": self.task_id,
            "actor_kind": self.actor_kind.value,
            "brain_id": self.brain_id,
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "brain_operation": self.brain_operation.value,
            "authorized_artifact_path": self.authorized_artifact_path,
            "authorized_artifact_blob_sha": self.authorized_artifact_blob_sha,
            "max_input_tokens": self.max_input_tokens,
            "max_output_tokens": self.max_output_tokens,
            "max_calls": self.max_calls,
            "expires_at_epoch_seconds": self.expires_at_epoch_seconds,
            "workspace_id": self.workspace_id,
        }

    def to_dict(self) -> dict[str, Any]:
        value = self.semantic_dict()
        value["grant_fingerprint"] = self.grant_fingerprint
        return value

    def to_canonical_json(self) -> str:
        return _canonical_json(self.to_dict())

    def fingerprint(self) -> str:
        canonical_semantics = _canonical_json(self.semantic_dict()).encode("utf-8")
        return hashlib.sha256(canonical_semantics).hexdigest()

    @classmethod
    def from_dict(cls, data: Any) -> PaidApiGrant:
        if type(data) is not dict:
            raise ValueError("paid API grant must be an exact object")
        expected_fields = {
            "schema_version",
            "grant_id",
            "task_id",
            "actor_kind",
            "brain_id",
            "provider_id",
            "model_id",
            "brain_operation",
            "authorized_artifact_path",
            "authorized_artifact_blob_sha",
            "max_input_tokens",
            "max_output_tokens",
            "max_calls",
            "expires_at_epoch_seconds",
            "workspace_id",
            "grant_fingerprint",
        }
        if set(data) != expected_fields:
            raise ValueError("paid API grant object has an inexact field set")
        return cls(**data)

    @classmethod
    def from_json(cls, value: str | bytes) -> PaidApiGrant:
        if type(value) is bytes:
            try:
                decoded = value.decode("utf-8", errors="strict")
            except UnicodeDecodeError as exc:
                raise ValueError("paid API grant bytes must be strict UTF-8") from exc
        elif type(value) is str:
            decoded = value
        else:
            raise ValueError("paid API grant JSON must be an exact string or bytes")

        def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            result: dict[str, Any] = {}
            for key, item in pairs:
                if key in result:
                    raise ValueError("paid API grant JSON contains duplicate keys")
                result[key] = item
            return result

        try:
            data = json.loads(decoded, object_pairs_hook=reject_duplicate_keys)
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError("paid API grant JSON is malformed") from exc
        if type(data) is not dict:
            raise ValueError("paid API grant JSON root must be an object")
        return cls.from_dict(data)


def validate_paid_api_grant_binding(
    grant: PaidApiGrant,
    *,
    task_id: str,
    workspace_id: str,
    brain_id: str,
    provider_id: str,
    model_id: str,
    brain_operation: BrainOperation,
    authorized_artifact_path: str,
    authorized_artifact_blob_sha: str,
) -> None:
    if type(grant) is not PaidApiGrant:
        raise ValueError("grant must be a PaidApiGrant")
    if grant.actor_kind is not DispatchActorKind.BRAIN:
        raise ValueError("grant actor_kind must be BRAIN")
    if grant.max_calls != 1 or type(grant.max_calls) is not int:
        raise ValueError("grant max_calls must be the exact integer 1")
    if grant.grant_fingerprint != grant.fingerprint():
        raise ValueError("stored grant fingerprint is stale or forged")

    bindings = {
        "task_id": (task_id, grant.task_id),
        "workspace_id": (workspace_id, grant.workspace_id),
        "brain_id": (brain_id, grant.brain_id),
        "provider_id": (provider_id, grant.provider_id),
        "model_id": (model_id, grant.model_id),
        "authorized_artifact_path": (
            authorized_artifact_path,
            grant.authorized_artifact_path,
        ),
        "authorized_artifact_blob_sha": (
            authorized_artifact_blob_sha,
            grant.authorized_artifact_blob_sha,
        ),
    }
    for field_name, (supplied, expected) in bindings.items():
        if type(supplied) is not str or supplied != expected:
            raise ValueError(f"{field_name} does not exactly match the grant")

    if not isinstance(brain_operation, BrainOperation) or brain_operation != grant.brain_operation:
        raise ValueError("brain_operation does not exactly match the grant")


def validate_paid_api_grant_budget(
    grant: PaidApiGrant,
    *,
    input_tokens: int,
    output_tokens: int,
) -> None:
    if type(grant) is not PaidApiGrant:
        raise ValueError("grant must be a PaidApiGrant")
    input_tokens = _require_exact_int(input_tokens, "input_tokens")
    output_tokens = _require_exact_int(output_tokens, "output_tokens")
    if input_tokens < 0 or output_tokens < 0:
        raise ValueError("requested token amounts must be non-negative")
    if input_tokens > grant.max_input_tokens:
        raise ValueError("input token amount exceeds the grant")
    if output_tokens > grant.max_output_tokens:
        raise ValueError("output token amount exceeds the grant")
