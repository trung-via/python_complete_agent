"""Usage telemetry records and append-only ledger protocol for External Brain."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from .contracts import ModelResponseStatus
from .errors import ContractValidationError


@dataclass(frozen=True)
class UsageRecord:
    """
    Immutable telemetry record capturing request metadata, token counts, and latency.
    Strictly adheres to ADR-007 locked telemetry schema.
    Strictly excludes prompts, context content, model outputs, headers, and credentials.
    """

    schema_version: str
    timestamp_utc: str
    request_id: str
    task_id: str
    provider: str
    requested_model: str | None
    actual_model: str
    status: ModelResponseStatus
    provider_input_tokens: int | None = None
    provider_output_tokens: int | None = None
    provider_reasoning_tokens: int | None = None
    provider_cached_tokens: int | None = None
    latency_ms: int | None = None
    provider_request_id: str | None = None
    context_fingerprint: str | None = None
    context_counted_tokens: int | None = None
    context_counter_id: str | None = None
    context_count_is_exact: bool | None = None
    error_code: str | None = None

    def __post_init__(self) -> None:
        if self.schema_version != "1":
            raise ContractValidationError(f"Unsupported schema_version: {self.schema_version!r} (expected '1')")

        if not self.timestamp_utc or not isinstance(self.timestamp_utc, str):
            raise ContractValidationError("timestamp_utc must be a non-empty ISO 8601 string")

        if not self.request_id or not isinstance(self.request_id, str):
            raise ContractValidationError("request_id must be a non-empty string")

        if not self.task_id or not isinstance(self.task_id, str):
            raise ContractValidationError("task_id must be a non-empty string")

        if not self.provider or not isinstance(self.provider, str):
            raise ContractValidationError("provider must be a non-empty string")

        if self.requested_model is not None and not isinstance(self.requested_model, str):
            raise ContractValidationError("requested_model must be a string or None")

        if not self.actual_model or not isinstance(self.actual_model, str):
            raise ContractValidationError("actual_model must be a non-empty string")

        if not isinstance(self.status, ModelResponseStatus):
            try:
                object.__setattr__(self, "status", ModelResponseStatus(self.status))
            except Exception as e:
                raise ContractValidationError(f"Invalid ModelResponseStatus: {self.status}") from e

        # Validate non-negative integers for token metrics and latency
        integer_fields = (
            "provider_input_tokens",
            "provider_output_tokens",
            "provider_reasoning_tokens",
            "provider_cached_tokens",
            "latency_ms",
            "context_counted_tokens",
        )
        for field_name in integer_fields:
            val = getattr(self, field_name)
            if val is not None:
                if isinstance(val, bool) or not isinstance(val, int) or val < 0:
                    raise ContractValidationError(f"{field_name} must be a non-negative integer, got: {val!r}")

        if self.context_count_is_exact is not None and not isinstance(self.context_count_is_exact, bool):
            raise ContractValidationError("context_count_is_exact must be a boolean or None")

    def to_dict(self) -> dict[str, Any]:
        """Returns a deterministic JSON-serializable dictionary representation."""
        return {
            "schema_version": self.schema_version,
            "timestamp_utc": self.timestamp_utc,
            "request_id": self.request_id,
            "task_id": self.task_id,
            "provider": self.provider,
            "requested_model": self.requested_model,
            "actual_model": self.actual_model,
            "status": self.status.value,
            "provider_input_tokens": self.provider_input_tokens,
            "provider_output_tokens": self.provider_output_tokens,
            "provider_reasoning_tokens": self.provider_reasoning_tokens,
            "provider_cached_tokens": self.provider_cached_tokens,
            "latency_ms": self.latency_ms,
            "provider_request_id": self.provider_request_id,
            "context_fingerprint": self.context_fingerprint,
            "context_counted_tokens": self.context_counted_tokens,
            "context_counter_id": self.context_counter_id,
            "context_count_is_exact": self.context_count_is_exact,
            "error_code": self.error_code,
        }


@runtime_checkable
class UsageLedger(Protocol):
    """Protocol for recording usage telemetry."""

    def append(self, record: UsageRecord) -> None:
        """Appends a single UsageRecord to the underlying ledger store."""
        ...


class JsonlUsageLedger:
    """
    Concrete append-only JSONL usage ledger.
    Writes one line per UsageRecord with directory creation, flush, and fsync.
    """

    def __init__(self, file_path: str | Path) -> None:
        self._path = Path(file_path)

    @property
    def path(self) -> Path:
        return self._path

    def append(self, record: UsageRecord) -> None:
        if not isinstance(record, UsageRecord):
            raise ContractValidationError(f"record must be a UsageRecord instance, got: {type(record)}")

        self._path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record.to_dict(), sort_keys=True)
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
            f.flush()
            os.fsync(f.fileno())
