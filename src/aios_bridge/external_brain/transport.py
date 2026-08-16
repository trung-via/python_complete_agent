"""Transport boundary contracts and protocols for AIOS Bridge External Brain."""
from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping, Protocol

from .errors import ContractValidationError


def _deep_freeze(val: Any) -> Any:
    """Recursively converts dicts/mappings to MappingProxyType, lists to tuples, and sets to frozensets."""
    if isinstance(val, (dict, Mapping)):
        return MappingProxyType({str(k): _deep_freeze(v) for k, v in val.items()})
    elif isinstance(val, (list, tuple)):
        return tuple(_deep_freeze(v) for v in val)
    elif isinstance(val, (set, frozenset)):
        return frozenset(_deep_freeze(v) for v in val)
    return val


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
        object.__setattr__(self, "headers", _deep_freeze(self.headers))
        object.__setattr__(self, "payload", _deep_freeze(self.payload))


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

        if isinstance(self.body, (dict, list, set, Mapping)):
            object.__setattr__(self, "body", _deep_freeze(self.body))


class ModelTransport(Protocol):
    """
    Protocol for low-level HTTP transport implementations.
    Decouples model request serialization from specific HTTP networking clients.
    """

    async def send(self, request: TransportRequest) -> TransportResult:
        """Sends a TransportRequest and returns a TransportResult."""
        ...
