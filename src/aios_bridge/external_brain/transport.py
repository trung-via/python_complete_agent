"""Transport boundary contracts and protocols for AIOS Bridge External Brain."""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from types import MappingProxyType
from typing import Any, Mapping, Protocol

from .errors import ContractValidationError


def _validate_and_freeze_payload(val: Any) -> Any:
    """Recursively validates strict JSON compatibility and freezes payload into immutable structures."""
    if val is None or isinstance(val, (str, bool)):
        return val
    elif isinstance(val, int):
        return val
    elif isinstance(val, float):
        if not math.isfinite(val):
            raise ContractValidationError(f"Float payload values must be finite (no NaN/Inf), got: {val}")
        return val
    elif isinstance(val, (dict, Mapping)):
        frozen_dict = {}
        for k, v in val.items():
            if not isinstance(k, str):
                raise ContractValidationError(f"Payload dictionary keys must be strings, got: {type(k)}")
            frozen_dict[k] = _validate_and_freeze_payload(v)
        return MappingProxyType(frozen_dict)
    elif isinstance(val, (list, tuple)):
        return tuple(_validate_and_freeze_payload(v) for v in val)
    elif isinstance(val, (set, frozenset)):
        raise ContractValidationError(
            f"Unordered sets are not JSON-compatible payload values: {type(val).__name__} ({val!r})"
        )
    else:
        raise ContractValidationError(f"Non-JSON-compatible payload value: {type(val)} ({val!r})")


def _freeze_headers(headers: Mapping[str, Any]) -> MappingProxyType[str, str]:
    """Validates and freezes request headers into an immutable MappingProxyType."""
    frozen = {}
    for k, v in headers.items():
        if not isinstance(k, str) or not isinstance(v, str):
            raise ContractValidationError(f"Header keys and values must be strings, got key={type(k)}, value={type(v)}")
        frozen[k] = v
    return MappingProxyType(frozen)


def _to_json_compatible(val: Any) -> Any:
    """Recursively converts internal MappingProxyType and tuples into standard JSON dict/list primitives."""
    if isinstance(val, (MappingProxyType, dict, Mapping)):
        return {str(k): _to_json_compatible(v) for k, v in val.items()}
    elif isinstance(val, (tuple, list)):
        return [_to_json_compatible(v) for v in val]
    return val


_SENSITIVE_HEADER_KEYS = frozenset({
    "authorization",
    "proxy-authorization",
    "api-key",
    "x-api-key",
    "token",
    "x-auth-token",
})


def _sanitize_headers_for_repr(headers: Mapping[str, str]) -> dict[str, str]:
    """Returns a dict of headers with sensitive credential values redacted."""
    return {
        k: ("[REDACTED]" if k.lower() in _SENSITIVE_HEADER_KEYS else v)
        for k, v in headers.items()
    }


@dataclass(frozen=True)
class TransportRequest:
    """Immutable low-level HTTP transport request contract."""
    endpoint_url: str
    path: str
    headers: Mapping[str, str] = field(default_factory=dict)
    payload: Mapping[str, Any] = field(default_factory=dict)
    timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        if not self.endpoint_url or not isinstance(self.endpoint_url, str):
            raise ContractValidationError("endpoint_url must be a non-empty string")

        if not (self.endpoint_url.startswith("http://") or self.endpoint_url.startswith("https://")):
            raise ContractValidationError(f"endpoint_url must start with http:// or https://, got: {self.endpoint_url!r}")

        if not isinstance(self.path, str):
            raise ContractValidationError("path must be a string")

        if isinstance(self.timeout_seconds, bool) or not isinstance(self.timeout_seconds, (int, float)) or self.timeout_seconds <= 0:
            raise ContractValidationError(
                f"timeout_seconds must be a positive number, got: {self.timeout_seconds!r}"
            )

        if not isinstance(self.headers, Mapping):
            raise ContractValidationError("headers must be a mapping")

        if not isinstance(self.payload, Mapping):
            raise ContractValidationError("payload must be a mapping")

        # Defensive deep-copy & deep-freeze
        object.__setattr__(self, "headers", _freeze_headers(self.headers))
        object.__setattr__(self, "payload", _validate_and_freeze_payload(self.payload))

    def __repr__(self) -> str:
        safe_headers = _sanitize_headers_for_repr(self.headers)
        return (
            f"TransportRequest(endpoint_url={self.endpoint_url!r}, "
            f"path={self.path!r}, headers={safe_headers!r}, "
            f"payload={self.payload!r}, timeout_seconds={self.timeout_seconds!r})"
        )

    def __str__(self) -> str:
        return repr(self)

    def to_json_payload(self) -> dict[str, Any]:
        """Returns a fresh JSON-compatible dictionary representation of the request payload."""
        return _to_json_compatible(self.payload)

    def to_wire_dict(self) -> dict[str, Any]:
        """Returns a fresh JSON-compatible wire representation of the entire transport request."""
        return {
            "endpoint_url": self.endpoint_url,
            "path": self.path,
            "headers": dict(self.headers),
            "payload": self.to_json_payload(),
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass(frozen=True)
class TransportResult:
    """Immutable low-level HTTP transport result contract."""
    status_code: int | None
    body: Any
    latency_ms: int
    provider_request_id: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.latency_ms, bool) or not isinstance(self.latency_ms, int) or self.latency_ms < 0:
            raise ContractValidationError(f"latency_ms must be a non-negative integer, got: {self.latency_ms!r}")

        if self.status_code is not None:
            if isinstance(self.status_code, bool) or not isinstance(self.status_code, int):
                raise ContractValidationError(f"status_code must be an integer if specified, got: {self.status_code!r}")

        if isinstance(self.body, (dict, list, Mapping)):
            object.__setattr__(self, "body", _validate_and_freeze_payload(self.body))

    def to_dict(self) -> dict[str, Any]:
        """Returns a fresh JSON-compatible dictionary representation of the transport result."""
        return {
            "status_code": self.status_code,
            "body": _to_json_compatible(self.body),
            "latency_ms": self.latency_ms,
            "provider_request_id": self.provider_request_id,
        }


class ModelTransport(Protocol):
    """
    Protocol for low-level HTTP transport implementations.
    Decouples model request serialization from specific HTTP networking clients.
    """

    async def send(self, request: TransportRequest) -> TransportResult:
        """Sends a TransportRequest and returns a TransportResult."""
        ...
