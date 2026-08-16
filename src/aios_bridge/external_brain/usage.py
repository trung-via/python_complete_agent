"""Usage telemetry records and append-only ledger protocol for External Brain."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from .errors import ContractValidationError


@dataclass(frozen=True)
class UsageRecord:
    """
    Immutable telemetry record capturing request metadata, token counts, and latency.
    Strictly excludes prompts, context content, model outputs, headers, and credentials.
    """

    request_id: str
    task_id: str
    provider: str
    model: str
    operation: str
    status: str
    recorded_at: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    latency_ms: int | None = None
    provider_request_id: str | None = None
    context_fingerprint: str | None = None
    context_token_count: int | None = None
    context_counter_id: str | None = None
    context_token_count_is_exact: bool | None = None
    error_code: str | None = None
    schema_version: str = "1.0"

    def __post_init__(self) -> None:
        if not self.request_id or not isinstance(self.request_id, str):
            raise ContractValidationError("request_id must be a non-empty string")
        if not self.task_id or not isinstance(self.task_id, str):
            raise ContractValidationError("task_id must be a non-empty string")
        if not self.provider or not isinstance(self.provider, str):
            raise ContractValidationError("provider must be a non-empty string")
        if not self.model or not isinstance(self.model, str):
            raise ContractValidationError("model must be a non-empty string")
        if not self.operation or not isinstance(self.operation, str):
            raise ContractValidationError("operation must be a non-empty string")
        if not self.status or not isinstance(self.status, str):
            raise ContractValidationError("status must be a non-empty string")

        if self.recorded_at is None:
            now_iso = datetime.now(timezone.utc).isoformat()
            object.__setattr__(self, "recorded_at", now_iso)
        elif not isinstance(self.recorded_at, str):
            raise ContractValidationError("recorded_at must be an ISO 8601 string")

        # Validate token count non-negativity
        for field_name in ("input_tokens", "output_tokens", "total_tokens", "latency_ms", "context_token_count"):
            val = getattr(self, field_name)
            if val is not None:
                if isinstance(val, bool) or not isinstance(val, int) or val < 0:
                    raise ContractValidationError(f"{field_name} must be a non-negative integer, got: {val!r}")

        if self.context_token_count_is_exact is not None and not isinstance(self.context_token_count_is_exact, bool):
            raise ContractValidationError("context_token_count_is_exact must be a boolean or None")

        # Calculate total_tokens if missing and components present
        if self.total_tokens is None and self.input_tokens is not None and self.output_tokens is not None:
            object.__setattr__(self, "total_tokens", self.input_tokens + self.output_tokens)

    def to_dict(self) -> dict[str, Any]:
        """Returns a deterministic JSON-serializable dictionary representation."""
        return {
            "schema_version": self.schema_version,
            "recorded_at": self.recorded_at,
            "request_id": self.request_id,
            "task_id": self.task_id,
            "provider": self.provider,
            "model": self.model,
            "operation": self.operation,
            "status": self.status,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "latency_ms": self.latency_ms,
            "provider_request_id": self.provider_request_id,
            "context_fingerprint": self.context_fingerprint,
            "context_token_count": self.context_token_count,
            "context_counter_id": self.context_counter_id,
            "context_token_count_is_exact": self.context_token_count_is_exact,
            "error_code": self.error_code,
        }


@runtime_checkable
class UsageLedger(Protocol):
    """Protocol for recording usage telemetry."""

    async def append(self, record: UsageRecord) -> None:
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

    def _sync_append(self, line: str) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
            f.flush()
            os.fsync(f.fileno())

    async def append(self, record: UsageRecord) -> None:
        if not isinstance(record, UsageRecord):
            raise ContractValidationError(f"record must be a UsageRecord instance, got: {type(record)}")

        line = json.dumps(record.to_dict(), sort_keys=True)
        await asyncio.to_thread(self._sync_append, line)
