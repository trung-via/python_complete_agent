"""Transport boundary contracts and protocols for AIOS Bridge External Brain."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol

from .errors import ContractValidationError


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

        if not isinstance(self.timeout_seconds, (int, float)) or self.timeout_seconds <= 0:
            raise ContractValidationError(
                f"timeout_seconds must be a positive number, got: {self.timeout_seconds!r}"
            )


@dataclass(frozen=True)
class TransportResult:
    """Immutable low-level HTTP transport result contract."""
    status_code: int | None
    body: Any
    latency_ms: int
    provider_request_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.latency_ms, int) or self.latency_ms < 0:
            raise ContractValidationError(f"latency_ms must be a non-negative integer, got: {self.latency_ms!r}")

        if self.status_code is not None and not isinstance(self.status_code, int):
            raise ContractValidationError(f"status_code must be an integer if specified, got: {self.status_code!r}")


class ModelTransport(Protocol):
    """
    Protocol for low-level HTTP transport implementations.
    Decouples model request serialization from specific HTTP networking clients.
    """

    async def send(self, request: TransportRequest) -> TransportResult:
        """Sends a TransportRequest and returns a TransportResult."""
        ...
