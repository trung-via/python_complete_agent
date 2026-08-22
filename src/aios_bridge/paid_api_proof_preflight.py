"""Offline correlation and readiness proof receipt for M11.3B paid API preflight."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

from .minimax_m3_proof_lock import (
    MiniMaxM3ProofLock,
    PROVIDER_ID,
    MODEL_ID,
    CREDENTIAL_ENV_NAME,
    SOURCE_REVISION,
    JINJA2_VERSION,
    TOKENIZERS_VERSION,
    REQUESTS_VERSION,
)
from .paid_api_grant import PaidApiGrant


PREFLIGHT_SCHEMA_VERSION = "1"
MAX_PREFLIGHT_RECEIPT_BYTES = 64 * 1024

_LOWERCASE_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_LOWERCASE_SHA1_40 = re.compile(r"^[0-9a-f]{40}$")
_TASK_ID_PATTERN = re.compile(r"^TASK-[0-9]+$")

_RECEIPT_FIELDS = frozenset(
    {
        "schema_version",
        "task_id",
        "grant_id",
        "grant_fingerprint",
        "workspace_id",
        "brain_id",
        "provider_id",
        "model_id",
        "runtime_main_sha",
        "control_commit_sha",
        "authorized_artifact_path",
        "authorized_artifact_blob_sha",
        "proof_lock_path",
        "proof_lock_blob_sha",
        "proof_lock_fingerprint",
        "endpoint_url",
        "credential_env_name",
        "credential_present",
        "source_revision",
        "chat_template_sha256",
        "tokenizer_sha256",
        "counter_id",
        "jinja2_version",
        "tokenizers_version",
        "requests_version",
        "ledger_logical_path",
        "ledger_ready",
        "grant_active",
        "grant_consumed",
        "paid_dispatch_enabled",
        "provider_call_started",
    }
)


class PaidApiProofPreflightError(ValueError):
    """Raised when preflight verification or receipt construction fails."""


def _reject_duplicate_json_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise PaidApiProofPreflightError("preflight receipt contains duplicate JSON keys")
        result[key] = value
    return result


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


@dataclass(frozen=True, slots=True)
class PaidApiProofPreflightReceipt:
    """Immutable, offline readiness receipt for M11.3B paid API preflight."""

    schema_version: str
    task_id: str
    grant_id: str
    grant_fingerprint: str
    workspace_id: str
    brain_id: str
    provider_id: str
    model_id: str
    runtime_main_sha: str
    control_commit_sha: str
    authorized_artifact_path: str
    authorized_artifact_blob_sha: str
    proof_lock_path: str
    proof_lock_blob_sha: str
    proof_lock_fingerprint: str
    endpoint_url: str
    credential_env_name: str
    credential_present: bool
    source_revision: str
    chat_template_sha256: str
    tokenizer_sha256: str
    counter_id: str
    jinja2_version: str
    tokenizers_version: str
    requests_version: str
    ledger_logical_path: str
    ledger_ready: bool
    grant_active: bool
    grant_consumed: bool
    paid_dispatch_enabled: bool
    provider_call_started: bool

    def __post_init__(self) -> None:
        if type(self.schema_version) is not str or self.schema_version != PREFLIGHT_SCHEMA_VERSION:
            raise PaidApiProofPreflightError(
                f"schema_version must be exact '{PREFLIGHT_SCHEMA_VERSION}'"
            )
        if type(self.task_id) is not str or _TASK_ID_PATTERN.fullmatch(self.task_id) is None:
            raise PaidApiProofPreflightError("task_id must match TASK-N pattern")
        if type(self.grant_id) is not str or not self.grant_id:
            raise PaidApiProofPreflightError("grant_id must be a non-empty string")
        if (
            type(self.grant_fingerprint) is not str
            or _LOWERCASE_SHA256.fullmatch(self.grant_fingerprint) is None
        ):
            raise PaidApiProofPreflightError("grant_fingerprint must be a lowercase 64-hex SHA-256")
        if type(self.workspace_id) is not str or not self.workspace_id:
            raise PaidApiProofPreflightError("workspace_id must be a non-empty string")
        if type(self.brain_id) is not str or not self.brain_id:
            raise PaidApiProofPreflightError("brain_id must be a non-empty string")
        if type(self.provider_id) is not str or self.provider_id != PROVIDER_ID:
            raise PaidApiProofPreflightError(f"provider_id must be exact '{PROVIDER_ID}'")
        if type(self.model_id) is not str or self.model_id != MODEL_ID:
            raise PaidApiProofPreflightError(f"model_id must be exact '{MODEL_ID}'")
        if (
            type(self.runtime_main_sha) is not str
            or _LOWERCASE_SHA1_40.fullmatch(self.runtime_main_sha) is None
        ):
            raise PaidApiProofPreflightError("runtime_main_sha must be a lowercase 40-hex Git commit SHA")
        if (
            type(self.control_commit_sha) is not str
            or _LOWERCASE_SHA1_40.fullmatch(self.control_commit_sha) is None
        ):
            raise PaidApiProofPreflightError("control_commit_sha must be a lowercase 40-hex Git commit SHA")
        if type(self.authorized_artifact_path) is not str or not self.authorized_artifact_path:
            raise PaidApiProofPreflightError("authorized_artifact_path must be a non-empty string")
        if (
            type(self.authorized_artifact_blob_sha) is not str
            or _LOWERCASE_SHA1_40.fullmatch(self.authorized_artifact_blob_sha) is None
        ):
            raise PaidApiProofPreflightError("authorized_artifact_blob_sha must be a lowercase 40-hex Git blob SHA")
        if type(self.proof_lock_path) is not str or not self.proof_lock_path:
            raise PaidApiProofPreflightError("proof_lock_path must be a non-empty string")
        if (
            type(self.proof_lock_blob_sha) is not str
            or _LOWERCASE_SHA1_40.fullmatch(self.proof_lock_blob_sha) is None
        ):
            raise PaidApiProofPreflightError("proof_lock_blob_sha must be a lowercase 40-hex Git blob SHA")
        if (
            type(self.proof_lock_fingerprint) is not str
            or _LOWERCASE_SHA256.fullmatch(self.proof_lock_fingerprint) is None
        ):
            raise PaidApiProofPreflightError("proof_lock_fingerprint must be a lowercase 64-hex SHA-256")
        if type(self.endpoint_url) is not str or not self.endpoint_url:
            raise PaidApiProofPreflightError("endpoint_url must be a non-empty string")
        if type(self.credential_env_name) is not str or self.credential_env_name != CREDENTIAL_ENV_NAME:
            raise PaidApiProofPreflightError(f"credential_env_name must be exact '{CREDENTIAL_ENV_NAME}'")
        if type(self.credential_present) is not bool or not self.credential_present:
            raise PaidApiProofPreflightError("credential_present must be True")
        if type(self.source_revision) is not str or self.source_revision != SOURCE_REVISION:
            raise PaidApiProofPreflightError(f"source_revision must be exact '{SOURCE_REVISION}'")
        if (
            type(self.chat_template_sha256) is not str
            or _LOWERCASE_SHA256.fullmatch(self.chat_template_sha256) is None
        ):
            raise PaidApiProofPreflightError("chat_template_sha256 must be a lowercase 64-hex SHA-256")
        if (
            type(self.tokenizer_sha256) is not str
            or _LOWERCASE_SHA256.fullmatch(self.tokenizer_sha256) is None
        ):
            raise PaidApiProofPreflightError("tokenizer_sha256 must be a lowercase 64-hex SHA-256")
        if type(self.counter_id) is not str or not self.counter_id:
            raise PaidApiProofPreflightError("counter_id must be a non-empty string")
        if type(self.jinja2_version) is not str or self.jinja2_version != JINJA2_VERSION:
            raise PaidApiProofPreflightError(f"jinja2_version must be exact '{JINJA2_VERSION}'")
        if type(self.tokenizers_version) is not str or self.tokenizers_version != TOKENIZERS_VERSION:
            raise PaidApiProofPreflightError(f"tokenizers_version must be exact '{TOKENIZERS_VERSION}'")
        if type(self.requests_version) is not str or self.requests_version != REQUESTS_VERSION:
            raise PaidApiProofPreflightError(f"requests_version must be exact '{REQUESTS_VERSION}'")
        if type(self.ledger_logical_path) is not str or not self.ledger_logical_path:
            raise PaidApiProofPreflightError("ledger_logical_path must be a non-empty relative string")
        # Forbid absolute paths in ledger_logical_path
        if self.ledger_logical_path.startswith("/") or self.ledger_logical_path.startswith("\\") or os.path.isabs(self.ledger_logical_path) or ":" in self.ledger_logical_path or "\\" in self.ledger_logical_path:
            raise PaidApiProofPreflightError("ledger_logical_path must be a normalized relative path without drive letters")
        if type(self.ledger_ready) is not bool or not self.ledger_ready:
            raise PaidApiProofPreflightError("ledger_ready must be True")
        if type(self.grant_active) is not bool or not self.grant_active:
            raise PaidApiProofPreflightError("grant_active must be True")
        if type(self.grant_consumed) is not bool or self.grant_consumed:
            raise PaidApiProofPreflightError("grant_consumed must be False")
        if type(self.paid_dispatch_enabled) is not bool or self.paid_dispatch_enabled:
            raise PaidApiProofPreflightError("paid_dispatch_enabled must be False")
        if type(self.provider_call_started) is not bool or self.provider_call_started:
            raise PaidApiProofPreflightError("provider_call_started must be False")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "task_id": self.task_id,
            "grant_id": self.grant_id,
            "grant_fingerprint": self.grant_fingerprint,
            "workspace_id": self.workspace_id,
            "brain_id": self.brain_id,
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "runtime_main_sha": self.runtime_main_sha,
            "control_commit_sha": self.control_commit_sha,
            "authorized_artifact_path": self.authorized_artifact_path,
            "authorized_artifact_blob_sha": self.authorized_artifact_blob_sha,
            "proof_lock_path": self.proof_lock_path,
            "proof_lock_blob_sha": self.proof_lock_blob_sha,
            "proof_lock_fingerprint": self.proof_lock_fingerprint,
            "endpoint_url": self.endpoint_url,
            "credential_env_name": self.credential_env_name,
            "credential_present": self.credential_present,
            "source_revision": self.source_revision,
            "chat_template_sha256": self.chat_template_sha256,
            "tokenizer_sha256": self.tokenizer_sha256,
            "counter_id": self.counter_id,
            "jinja2_version": self.jinja2_version,
            "tokenizers_version": self.tokenizers_version,
            "requests_version": self.requests_version,
            "ledger_logical_path": self.ledger_logical_path,
            "ledger_ready": self.ledger_ready,
            "grant_active": self.grant_active,
            "grant_consumed": self.grant_consumed,
            "paid_dispatch_enabled": self.paid_dispatch_enabled,
            "provider_call_started": self.provider_call_started,
        }

    def to_canonical_json(self) -> str:
        return _canonical_json(self.to_dict())

    def fingerprint(self) -> str:
        return hashlib.sha256(self.to_canonical_json().encode("utf-8")).hexdigest()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PaidApiProofPreflightReceipt:
        if type(data) is not dict:
            raise PaidApiProofPreflightError("preflight receipt data must be a dict")
        if set(data) != _RECEIPT_FIELDS:
            raise PaidApiProofPreflightError(
                "preflight receipt must contain exactly the required fields"
            )
        # Check bools are exact bools not ints
        for bool_field in (
            "credential_present",
            "ledger_ready",
            "grant_active",
            "grant_consumed",
            "paid_dispatch_enabled",
            "provider_call_started",
        ):
            if type(data[bool_field]) is not bool:
                raise PaidApiProofPreflightError(
                    f"field '{bool_field}' must be an exact boolean"
                )
        for str_field in _RECEIPT_FIELDS - {
            "credential_present",
            "ledger_ready",
            "grant_active",
            "grant_consumed",
            "paid_dispatch_enabled",
            "provider_call_started",
        }:
            if type(data[str_field]) is not str:
                raise PaidApiProofPreflightError(
                    f"field '{str_field}' must be an exact string"
                )

        return cls(
            schema_version=data["schema_version"],
            task_id=data["task_id"],
            grant_id=data["grant_id"],
            grant_fingerprint=data["grant_fingerprint"],
            workspace_id=data["workspace_id"],
            brain_id=data["brain_id"],
            provider_id=data["provider_id"],
            model_id=data["model_id"],
            runtime_main_sha=data["runtime_main_sha"],
            control_commit_sha=data["control_commit_sha"],
            authorized_artifact_path=data["authorized_artifact_path"],
            authorized_artifact_blob_sha=data["authorized_artifact_blob_sha"],
            proof_lock_path=data["proof_lock_path"],
            proof_lock_blob_sha=data["proof_lock_blob_sha"],
            proof_lock_fingerprint=data["proof_lock_fingerprint"],
            endpoint_url=data["endpoint_url"],
            credential_env_name=data["credential_env_name"],
            credential_present=data["credential_present"],
            source_revision=data["source_revision"],
            chat_template_sha256=data["chat_template_sha256"],
            tokenizer_sha256=data["tokenizer_sha256"],
            counter_id=data["counter_id"],
            jinja2_version=data["jinja2_version"],
            tokenizers_version=data["tokenizers_version"],
            requests_version=data["requests_version"],
            ledger_logical_path=data["ledger_logical_path"],
            ledger_ready=data["ledger_ready"],
            grant_active=data["grant_active"],
            grant_consumed=data["grant_consumed"],
            paid_dispatch_enabled=data["paid_dispatch_enabled"],
            provider_call_started=data["provider_call_started"],
        )

    @classmethod
    def from_json(cls, raw: str | bytes) -> PaidApiProofPreflightReceipt:
        if isinstance(raw, str):
            raw_bytes = raw.encode("utf-8")
        elif isinstance(raw, (bytes, bytearray)):
            raw_bytes = bytes(raw)
        else:
            raise PaidApiProofPreflightError("raw receipt must be str or bytes")

        if len(raw_bytes) > MAX_PREFLIGHT_RECEIPT_BYTES:
            raise PaidApiProofPreflightError("receipt exceeds maximum allowed bytes")

        try:
            text = raw_bytes.decode("utf-8", errors="strict")
            data = json.loads(text, object_pairs_hook=_reject_duplicate_json_keys)
        except PaidApiProofPreflightError:
            raise
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PaidApiProofPreflightError("receipt must be valid UTF-8 JSON") from exc

        return cls.from_dict(data)


def probe_ledger_durability(ledger_path: Path) -> bool:
    """Probes durability of the ledger destination directory without appending real usage records."""
    try:
        parent = ledger_path.parent
        parent.mkdir(parents=True, exist_ok=True)
        probe_file = parent / f".probe_{os.getpid()}_{hashlib.sha256(os.urandom(16)).hexdigest()[:8]}.tmp"
        with open(probe_file, "wb") as f:
            f.write(b"AIOS_LEDGER_DURABILITY_PROBE\n")
            f.flush()
            os.fsync(f.fileno())
        try:
            probe_file.unlink(missing_ok=True)
        except OSError:
            pass
        return True
    except Exception as exc:
        raise PaidApiProofPreflightError(f"ledger directory durability probe failed: {exc}") from exc


def build_paid_api_proof_preflight_receipt(
    *,
    task_id: str,
    grant: PaidApiGrant,
    runtime_main_sha: str,
    control_commit_sha: str,
    proof_lock_path: str,
    proof_lock_blob_sha: str,
    proof_lock: MiniMaxM3ProofLock,
    counter_id: str,
    ledger_logical_path: str,
    ledger_ready: bool,
    credential_present: bool,
) -> PaidApiProofPreflightReceipt:
    """Constructs an exact PaidApiProofPreflightReceipt from verified observations."""
    if not isinstance(grant, PaidApiGrant):
        raise PaidApiProofPreflightError("grant must be a PaidApiGrant instance")
    if not isinstance(proof_lock, MiniMaxM3ProofLock):
        raise PaidApiProofPreflightError("proof_lock must be a MiniMaxM3ProofLock instance")

    return PaidApiProofPreflightReceipt(
        schema_version=PREFLIGHT_SCHEMA_VERSION,
        task_id=task_id,
        grant_id=grant.grant_id,
        grant_fingerprint=grant.fingerprint(),
        workspace_id=grant.workspace_id,
        brain_id=grant.brain_id,
        provider_id=proof_lock.provider_id,
        model_id=proof_lock.model_id,
        runtime_main_sha=runtime_main_sha,
        control_commit_sha=control_commit_sha,
        authorized_artifact_path=grant.authorized_artifact_path,
        authorized_artifact_blob_sha=grant.authorized_artifact_blob_sha,
        proof_lock_path=proof_lock_path,
        proof_lock_blob_sha=proof_lock_blob_sha,
        proof_lock_fingerprint=proof_lock.fingerprint(),
        endpoint_url=proof_lock.endpoint_url,
        credential_env_name=proof_lock.credential_env_name,
        credential_present=credential_present,
        source_revision=proof_lock.source_revision,
        chat_template_sha256=proof_lock.chat_template_sha256,
        tokenizer_sha256=proof_lock.tokenizer_sha256,
        counter_id=counter_id,
        jinja2_version=proof_lock.jinja2_version,
        tokenizers_version=proof_lock.tokenizers_version,
        requests_version=proof_lock.requests_version,
        ledger_logical_path=ledger_logical_path,
        ledger_ready=ledger_ready,
        grant_active=True,
        grant_consumed=False,
        paid_dispatch_enabled=False,
        provider_call_started=False,
    )


__all__ = [
    "PaidApiProofPreflightReceipt",
    "PaidApiProofPreflightError",
    "PREFLIGHT_SCHEMA_VERSION",
    "MAX_PREFLIGHT_RECEIPT_BYTES",
    "probe_ledger_durability",
    "build_paid_api_proof_preflight_receipt",
]
