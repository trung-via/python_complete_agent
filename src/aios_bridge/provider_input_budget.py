"""Exact, provider-bound evidence for complete ModelRequest input budgets.

This module defines only immutable contracts and a local counting seam.  It
does not initialize providers, discover credentials, or perform I/O.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Protocol, runtime_checkable

from .external_brain.contracts import ModelRequest


_SCHEMA_VERSION = "1"
_LOWERCASE_HEX = frozenset("0123456789abcdef")


class ProviderInputBudgetError(ValueError):
    """Raised when exact full-provider-input budget evidence is invalid."""


def _require_exact_nonempty_unpadded_string(value: object, field_name: str) -> None:
    if type(value) is not str or not value or value != value.strip():
        raise ProviderInputBudgetError(
            f"{field_name} must be an exact non-empty unpadded string"
        )


def _require_lowercase_sha256(value: object, field_name: str) -> None:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in _LOWERCASE_HEX for character in value)
    ):
        raise ProviderInputBudgetError(
            f"{field_name} must be an exact lowercase SHA-256 fingerprint"
        )


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def fingerprint_model_request(request: ModelRequest) -> str:
    """Fingerprint the canonical JSON of exact ``ModelRequest.to_dict()`` semantics."""

    if type(request) is not ModelRequest:
        raise ProviderInputBudgetError("request must be an exact ModelRequest")
    payload = _canonical_json(request.to_dict()).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class ProviderInputCountEvidence:
    """Exact token-count evidence for one complete provider-bound request."""

    provider_id: str
    model_id: str
    model_request_fingerprint: str
    counted_input_tokens: int
    counter_id: str
    token_count_is_exact: bool
    schema_version: str = _SCHEMA_VERSION

    def __post_init__(self) -> None:
        if type(self.schema_version) is not str or self.schema_version != _SCHEMA_VERSION:
            raise ProviderInputBudgetError("unsupported schema_version")
        _require_exact_nonempty_unpadded_string(self.provider_id, "provider_id")
        _require_exact_nonempty_unpadded_string(self.model_id, "model_id")
        _require_exact_nonempty_unpadded_string(self.counter_id, "counter_id")
        _require_lowercase_sha256(
            self.model_request_fingerprint,
            "model_request_fingerprint",
        )
        if type(self.counted_input_tokens) is not int or self.counted_input_tokens < 0:
            raise ProviderInputBudgetError(
                "counted_input_tokens must be an exact non-negative integer"
            )
        if type(self.token_count_is_exact) is not bool:
            raise ProviderInputBudgetError("token_count_is_exact must be an exact bool")

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic JSON-serializable representation without prompt data."""

        return {
            "counted_input_tokens": self.counted_input_tokens,
            "counter_id": self.counter_id,
            "model_id": self.model_id,
            "model_request_fingerprint": self.model_request_fingerprint,
            "provider_id": self.provider_id,
            "schema_version": self.schema_version,
            "token_count_is_exact": self.token_count_is_exact,
        }

    def to_canonical_json(self) -> str:
        """Serialize the evidence deterministically for audit correlation."""

        return _canonical_json(self.to_dict())


@runtime_checkable
class ProviderInputTokenCounter(Protocol):
    """Local exact counter seam for complete provider-rendered ModelRequest input."""

    @property
    def provider_id(self) -> str: ...

    @property
    def model_id(self) -> str: ...

    @property
    def counter_id(self) -> str: ...

    @property
    def is_exact(self) -> bool: ...

    def count_request(self, request: ModelRequest) -> ProviderInputCountEvidence: ...


__all__ = [
    "ProviderInputBudgetError",
    "ProviderInputCountEvidence",
    "ProviderInputTokenCounter",
    "fingerprint_model_request",
]
