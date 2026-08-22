"""Canonical MiniMax-M3 proof lock specification for M11.3B runtime preflight."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any
from urllib.parse import urlparse


SCHEMA_VERSION = "1"
PROVIDER_ID = "minimax"
MODEL_ID = "MiniMax-M3"
CREDENTIAL_ENV_NAME = "MINIMAX_API_KEY"
SOURCE_REPOSITORY = "MiniMaxAI/MiniMax-M3"
SOURCE_REVISION = "3a41b311ffa5719cef48fed3974ccf2cc03733ea"
CHAT_TEMPLATE_PATH = "chat_template.jinja"
TOKENIZER_PATH = "tokenizer.json"
JINJA2_VERSION = "3.1.6"
TOKENIZERS_VERSION = "0.23.1"
REQUESTS_VERSION = "2.32.3"

ALLOWED_MINIMAX_HOST = "api.minimax.io"
ALLOWED_MINIMAX_ENDPOINTS = frozenset(
    {
        "https://api.minimax.io/v1/text/chatcompletion_v2",
        "https://api.minimax.io/v1/chat/completions",
    }
)

MAX_PROOF_LOCK_BYTES = 64 * 1024
_LOWERCASE_SHA256 = re.compile(r"^[0-9a-f]{64}$")

_PROOF_LOCK_FIELDS = frozenset(
    {
        "schema_version",
        "provider_id",
        "model_id",
        "endpoint_url",
        "credential_env_name",
        "source_repository",
        "source_revision",
        "chat_template_path",
        "chat_template_sha256",
        "tokenizer_path",
        "tokenizer_sha256",
        "jinja2_version",
        "tokenizers_version",
        "requests_version",
    }
)


class MiniMaxM3ProofLockError(ValueError):
    """Raised when canonical proof-lock parsing or validation fails."""


def _reject_duplicate_json_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise MiniMaxM3ProofLockError("proof lock contains duplicate JSON keys")
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
class MiniMaxM3ProofLock:
    """Immutable, deterministic proof lock for MiniMax-M3 provenance."""

    schema_version: str
    provider_id: str
    model_id: str
    endpoint_url: str
    credential_env_name: str
    source_repository: str
    source_revision: str
    chat_template_path: str
    chat_template_sha256: str
    tokenizer_path: str
    tokenizer_sha256: str
    jinja2_version: str
    tokenizers_version: str
    requests_version: str

    def __post_init__(self) -> None:
        if type(self.schema_version) is not str or self.schema_version != SCHEMA_VERSION:
            raise MiniMaxM3ProofLockError(
                f"schema_version must be exact '{SCHEMA_VERSION}'"
            )
        if type(self.provider_id) is not str or self.provider_id != PROVIDER_ID:
            raise MiniMaxM3ProofLockError(
                f"provider_id must be exact '{PROVIDER_ID}'"
            )
        if type(self.model_id) is not str or self.model_id != MODEL_ID:
            raise MiniMaxM3ProofLockError(
                f"model_id must be exact '{MODEL_ID}'"
            )
        if type(self.credential_env_name) is not str or self.credential_env_name != CREDENTIAL_ENV_NAME:
            raise MiniMaxM3ProofLockError(
                f"credential_env_name must be exact '{CREDENTIAL_ENV_NAME}'"
            )
        if type(self.source_repository) is not str or self.source_repository != SOURCE_REPOSITORY:
            raise MiniMaxM3ProofLockError(
                f"source_repository must be exact '{SOURCE_REPOSITORY}'"
            )
        if type(self.source_revision) is not str or self.source_revision != SOURCE_REVISION:
            raise MiniMaxM3ProofLockError(
                f"source_revision must be exact '{SOURCE_REVISION}'"
            )
        if type(self.chat_template_path) is not str or self.chat_template_path != CHAT_TEMPLATE_PATH:
            raise MiniMaxM3ProofLockError(
                f"chat_template_path must be exact '{CHAT_TEMPLATE_PATH}'"
            )
        if type(self.tokenizer_path) is not str or self.tokenizer_path != TOKENIZER_PATH:
            raise MiniMaxM3ProofLockError(
                f"tokenizer_path must be exact '{TOKENIZER_PATH}'"
            )
        if type(self.jinja2_version) is not str or self.jinja2_version != JINJA2_VERSION:
            raise MiniMaxM3ProofLockError(
                f"jinja2_version must be exact '{JINJA2_VERSION}'"
            )
        if type(self.tokenizers_version) is not str or self.tokenizers_version != TOKENIZERS_VERSION:
            raise MiniMaxM3ProofLockError(
                f"tokenizers_version must be exact '{TOKENIZERS_VERSION}'"
            )
        if type(self.requests_version) is not str or self.requests_version != REQUESTS_VERSION:
            raise MiniMaxM3ProofLockError(
                f"requests_version must be exact '{REQUESTS_VERSION}'"
            )

        # Validate endpoint URL
        if type(self.endpoint_url) is not str:
            raise MiniMaxM3ProofLockError("endpoint_url must be an exact string")
        parsed = urlparse(self.endpoint_url)
        if (
            parsed.scheme != "https"
            or parsed.netloc != ALLOWED_MINIMAX_HOST
            or parsed.query
            or parsed.fragment
            or parsed.username
            or parsed.password
            or parsed.port
            or self.endpoint_url not in ALLOWED_MINIMAX_ENDPOINTS
        ):
            raise MiniMaxM3ProofLockError(
                f"endpoint_url must be a canonical HTTPS URL in allowlist: {ALLOWED_MINIMAX_ENDPOINTS}"
            )

        # Validate SHA-256 digests
        if (
            type(self.chat_template_sha256) is not str
            or _LOWERCASE_SHA256.fullmatch(self.chat_template_sha256) is None
        ):
            raise MiniMaxM3ProofLockError(
                "chat_template_sha256 must be a lowercase 64-hex SHA-256 digest"
            )
        if (
            type(self.tokenizer_sha256) is not str
            or _LOWERCASE_SHA256.fullmatch(self.tokenizer_sha256) is None
        ):
            raise MiniMaxM3ProofLockError(
                "tokenizer_sha256 must be a lowercase 64-hex SHA-256 digest"
            )

    def to_dict(self) -> dict[str, str]:
        return {
            "schema_version": self.schema_version,
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "endpoint_url": self.endpoint_url,
            "credential_env_name": self.credential_env_name,
            "source_repository": self.source_repository,
            "source_revision": self.source_revision,
            "chat_template_path": self.chat_template_path,
            "chat_template_sha256": self.chat_template_sha256,
            "tokenizer_path": self.tokenizer_path,
            "tokenizer_sha256": self.tokenizer_sha256,
            "jinja2_version": self.jinja2_version,
            "tokenizers_version": self.tokenizers_version,
            "requests_version": self.requests_version,
        }

    def to_canonical_json(self) -> str:
        return _canonical_json(self.to_dict())

    def fingerprint(self) -> str:
        return hashlib.sha256(self.to_canonical_json().encode("utf-8")).hexdigest()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MiniMaxM3ProofLock:
        if type(data) is not dict:
            raise MiniMaxM3ProofLockError("proof lock data must be a dict")
        if set(data) != _PROOF_LOCK_FIELDS:
            raise MiniMaxM3ProofLockError(
                "proof lock must contain exactly the required fields"
            )
        for key, value in data.items():
            if type(value) is not str:
                raise MiniMaxM3ProofLockError(
                    f"proof lock field '{key}' must be an exact string"
                )
        return cls(
            schema_version=data["schema_version"],
            provider_id=data["provider_id"],
            model_id=data["model_id"],
            endpoint_url=data["endpoint_url"],
            credential_env_name=data["credential_env_name"],
            source_repository=data["source_repository"],
            source_revision=data["source_revision"],
            chat_template_path=data["chat_template_path"],
            chat_template_sha256=data["chat_template_sha256"],
            tokenizer_path=data["tokenizer_path"],
            tokenizer_sha256=data["tokenizer_sha256"],
            jinja2_version=data["jinja2_version"],
            tokenizers_version=data["tokenizers_version"],
            requests_version=data["requests_version"],
        )

    @classmethod
    def from_json(cls, raw: str | bytes) -> MiniMaxM3ProofLock:
        if isinstance(raw, str):
            raw_bytes = raw.encode("utf-8")
        elif isinstance(raw, (bytes, bytearray)):
            raw_bytes = bytes(raw)
        else:
            raise MiniMaxM3ProofLockError("raw proof lock must be str or bytes")

        if len(raw_bytes) > MAX_PROOF_LOCK_BYTES:
            raise MiniMaxM3ProofLockError("proof lock exceeds maximum allowed bytes")

        try:
            text = raw_bytes.decode("utf-8", errors="strict")
            data = json.loads(text, object_pairs_hook=_reject_duplicate_json_keys)
        except MiniMaxM3ProofLockError:
            raise
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise MiniMaxM3ProofLockError("proof lock must be valid UTF-8 JSON") from exc

        return cls.from_dict(data)


__all__ = [
    "MiniMaxM3ProofLock",
    "MiniMaxM3ProofLockError",
    "SCHEMA_VERSION",
    "PROVIDER_ID",
    "MODEL_ID",
    "CREDENTIAL_ENV_NAME",
    "SOURCE_REPOSITORY",
    "SOURCE_REVISION",
    "CHAT_TEMPLATE_PATH",
    "TOKENIZER_PATH",
    "JINJA2_VERSION",
    "TOKENIZERS_VERSION",
    "REQUESTS_VERSION",
    "ALLOWED_MINIMAX_HOST",
    "ALLOWED_MINIMAX_ENDPOINTS",
    "MAX_PROOF_LOCK_BYTES",
]
