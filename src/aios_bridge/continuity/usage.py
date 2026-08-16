"""
Usage & Efficiency Telemetry Contract for Open Multi-Agent Continuity OS (ADR-013 / ADR-014 / TASK-024).
Provides deterministic measurement models, validation, estimation, and canonical serialization.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import math
import re
from typing import Any, Mapping, Sequence

from .errors import ContinuityStateValidationError
from .state import (
    MAX_SERIALIZED_BYTES,
    SCHEMA_VERSION,
    BrainOperation,
    _validate_actor_id,
)

_TASK_ID_PATTERN = re.compile(r"^TASK-\d+$")
_METHOD_PATTERN = re.compile(r"^[a-z0-9]+(?:[a-z0-9_.\-]+)*$")
MAX_METHOD_LENGTH = 64
MAX_USAGE_INT = (1 << 63) - 1  # 9,223,372,036,854,775,807 (signed 64-bit int max)

SUPPORTED_ESTIMATION_METHODS = {
    "utf8-bytes-div4-v1",
}


class UsageSource(str, Enum):
    """Provenance category for token/usage measurements."""
    REPORTED = "REPORTED"
    ESTIMATED = "ESTIMATED"
    UNKNOWN = "UNKNOWN"


class ExecutorAction(str, Enum):
    """Action category executed by an executor."""
    RUN = "RUN"
    FIX = "FIX"


def _validate_usage_int(
    val: Any,
    field_name: str,
    allow_none: bool = False,
    min_val: int = 0,
    max_val: int = MAX_USAGE_INT,
) -> int | None:
    """Validates non-negative integer within deterministic [min_val, max_val] boundaries (C2 / AIP-2)."""
    if val is None:
        if allow_none:
            return None
        raise ContinuityStateValidationError(f"{field_name} cannot be null/None")
    if isinstance(val, bool) or not isinstance(val, int):
        raise ContinuityStateValidationError(f"{field_name} must be an integer, got: {type(val).__name__}")
    if val < min_val:
        raise ContinuityStateValidationError(f"{field_name} must be >= {min_val}, got: {val}")
    if val > max_val:
        raise ContinuityStateValidationError(
            f"{field_name} ({val}) exceeds maximum allowed ({max_val})"
        )
    return val


def _validate_non_negative_int(val: Any, field_name: str, allow_none: bool = False, min_val: int = 0) -> int | None:
    return _validate_usage_int(val, field_name, allow_none=allow_none, min_val=min_val, max_val=MAX_USAGE_INT)


def _validate_canonical_actor_id(actor_id: Any, field_name: str) -> str:
    """Validates exact canonical actor ID with zero whitespace padding (C1 / AIP-3)."""
    if isinstance(actor_id, bool) or not isinstance(actor_id, str):
        raise ContinuityStateValidationError(f"{field_name} must be a non-empty string")
    if actor_id != actor_id.strip() or not actor_id:
        raise ContinuityStateValidationError(
            f"{field_name} must not contain leading or trailing whitespace: {actor_id!r}"
        )
    canonical = _validate_actor_id(actor_id, field_name)
    if actor_id != canonical:
        raise ContinuityStateValidationError(
            f"{field_name} must be exact canonical actor ID, got: {actor_id!r}"
        )
    return canonical


def _validate_canonical_ratio(val: Any, field_name: str, allow_none: bool = False) -> float | None:
    """Validates and normalizes numeric ratio to a canonical float in [0.0, 1.0] (C4 / AIP-4)."""
    if val is None:
        if allow_none:
            return None
        raise ContinuityStateValidationError(f"{field_name} cannot be null/None")
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        raise ContinuityStateValidationError(f"{field_name} must be a float or None, got: {type(val).__name__}")
    if math.isnan(val) or math.isinf(val):
        raise ContinuityStateValidationError(f"{field_name} must be a finite number, got: {val}")
    fval = float(val)
    if fval == 0.0:
        fval = 0.0  # normalize -0.0 to +0.0
    if not (0.0 <= fval <= 1.0):
        raise ContinuityStateValidationError(f"{field_name} must be in [0.0, 1.0], got: {val}")
    return fval


def _validate_task_id(task_id: Any, field_name: str = "task_id") -> str:
    if isinstance(task_id, bool) or not isinstance(task_id, str):
        raise ContinuityStateValidationError(f"{field_name} must be a non-empty string")
    if not _TASK_ID_PATTERN.match(task_id):
        raise ContinuityStateValidationError(
            f"{field_name} must match exact case-sensitive '^TASK-\\d+$', got: {task_id!r}"
        )
    return task_id


def _validate_method_identifier(method: Any, field_name: str = "method") -> str:
    if isinstance(method, bool) or not isinstance(method, str) or not method.strip():
        raise ContinuityStateValidationError(f"{field_name} must be a non-empty string")
    method_str = method.strip()
    if len(method_str) > MAX_METHOD_LENGTH:
        raise ContinuityStateValidationError(
            f"{field_name} length ({len(method_str)}) exceeds maximum allowed ({MAX_METHOD_LENGTH})"
        )
    if not _METHOD_PATTERN.match(method_str):
        raise ContinuityStateValidationError(
            f"{field_name} must be a conservative lowercase identifier (e.g. 'utf8-bytes-div4-v1'), got: {method!r}"
        )
    return method_str


@dataclass(frozen=True)
class TokenMeasurement:
    """Bounded, provenance-explicit token measurement."""
    source: UsageSource
    min_tokens: int | None = None
    max_tokens: int | None = None
    method: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source, UsageSource):
            try:
                object.__setattr__(self, "source", UsageSource(self.source))
            except Exception as e:
                valid_sources = ", ".join(s.value for s in UsageSource)
                raise ContinuityStateValidationError(
                    f"Invalid UsageSource: {self.source!r}. Valid values: {valid_sources}"
                ) from e

        if self.source == UsageSource.REPORTED:
            if self.min_tokens is None or self.max_tokens is None:
                raise ContinuityStateValidationError("REPORTED token measurement requires exact min_tokens and max_tokens")
            _validate_usage_int(self.min_tokens, "TokenMeasurement.min_tokens")
            _validate_usage_int(self.max_tokens, "TokenMeasurement.max_tokens")
            if self.min_tokens != self.max_tokens:
                raise ContinuityStateValidationError(
                    f"REPORTED token measurement must be exact (min_tokens == max_tokens), got: min={self.min_tokens}, max={self.max_tokens}"
                )
            if self.method is not None:
                object.__setattr__(self, "method", _validate_method_identifier(self.method, "TokenMeasurement.method"))

        elif self.source == UsageSource.ESTIMATED:
            if self.min_tokens is None or self.max_tokens is None:
                raise ContinuityStateValidationError("ESTIMATED token measurement requires bounded min_tokens and max_tokens")
            _validate_usage_int(self.min_tokens, "TokenMeasurement.min_tokens")
            _validate_usage_int(self.max_tokens, "TokenMeasurement.max_tokens")
            if self.min_tokens > self.max_tokens:
                raise ContinuityStateValidationError(
                    f"Token measurement min_tokens ({self.min_tokens}) cannot exceed max_tokens ({self.max_tokens})"
                )
            if self.method is None:
                raise ContinuityStateValidationError("ESTIMATED token measurement requires a method identifier")
            object.__setattr__(self, "method", _validate_method_identifier(self.method, "TokenMeasurement.method"))

        elif self.source == UsageSource.UNKNOWN:
            if self.min_tokens is not None or self.max_tokens is not None:
                raise ContinuityStateValidationError("UNKNOWN token measurement must have min_tokens=None and max_tokens=None")
            if self.method is not None:
                raise ContinuityStateValidationError("UNKNOWN token measurement must have method=None")

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_tokens": self.max_tokens,
            "method": self.method,
            "min_tokens": self.min_tokens,
            "source": self.source.value,
        }

    @classmethod
    def from_dict(cls, data: Any, context_name: str = "TokenMeasurement") -> TokenMeasurement:
        if not isinstance(data, dict):
            raise ContinuityStateValidationError(f"{context_name} must be a dict, got: {type(data).__name__}")
        allowed_keys = {"max_tokens", "method", "min_tokens", "source"}
        extra_keys = set(data.keys()) - allowed_keys
        if extra_keys:
            raise ContinuityStateValidationError(f"Unknown fields in {context_name}: {sorted(extra_keys)}")
        if "source" not in data:
            raise ContinuityStateValidationError(f"Missing required field 'source' in {context_name}")
        return cls(
            source=data["source"],
            min_tokens=data.get("min_tokens"),
            max_tokens=data.get("max_tokens"),
            method=data.get("method"),
        )


@dataclass(frozen=True)
class BrainUsageRecord:
    """Audit record of Brain reasoning/planning/review usage."""
    brain_id: str
    operation: BrainOperation
    tokens: TokenMeasurement
    round: int = 1
    turns: int = 1
    input_bytes: int | None = None
    output_bytes: int | None = None
    patch_bytes: int | None = None
    full_file_reads: int | None = None
    artifact_reads: int | None = None
    external_api_calls: int | None = None

    def __post_init__(self) -> None:
        canon_brain = _validate_canonical_actor_id(self.brain_id, "BrainUsageRecord.brain_id")
        object.__setattr__(self, "brain_id", canon_brain)

        if not isinstance(self.operation, BrainOperation):
            try:
                object.__setattr__(self, "operation", BrainOperation(self.operation))
            except Exception as e:
                valid_ops = ", ".join(o.value for o in BrainOperation)
                raise ContinuityStateValidationError(
                    f"Invalid BrainOperation: {self.operation!r}. Valid values: {valid_ops}"
                ) from e

        if not isinstance(self.tokens, TokenMeasurement):
            raise ContinuityStateValidationError(
                f"BrainUsageRecord.tokens must be a TokenMeasurement, got: {type(self.tokens).__name__}"
            )

        _validate_usage_int(self.round, "BrainUsageRecord.round", min_val=1)
        _validate_usage_int(self.turns, "BrainUsageRecord.turns", min_val=1)
        _validate_usage_int(self.input_bytes, "BrainUsageRecord.input_bytes", allow_none=True)
        _validate_usage_int(self.output_bytes, "BrainUsageRecord.output_bytes", allow_none=True)
        _validate_usage_int(self.patch_bytes, "BrainUsageRecord.patch_bytes", allow_none=True)
        _validate_usage_int(self.full_file_reads, "BrainUsageRecord.full_file_reads", allow_none=True)
        _validate_usage_int(self.artifact_reads, "BrainUsageRecord.artifact_reads", allow_none=True)
        _validate_usage_int(self.external_api_calls, "BrainUsageRecord.external_api_calls", allow_none=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_reads": self.artifact_reads,
            "brain_id": self.brain_id,
            "external_api_calls": self.external_api_calls,
            "full_file_reads": self.full_file_reads,
            "input_bytes": self.input_bytes,
            "operation": self.operation.value,
            "output_bytes": self.output_bytes,
            "patch_bytes": self.patch_bytes,
            "round": self.round,
            "tokens": self.tokens.to_dict(),
            "turns": self.turns,
        }

    @classmethod
    def from_dict(cls, data: Any, context_name: str = "BrainUsageRecord") -> BrainUsageRecord:
        if not isinstance(data, dict):
            raise ContinuityStateValidationError(f"{context_name} must be a dict, got: {type(data).__name__}")
        allowed_keys = {
            "artifact_reads",
            "brain_id",
            "external_api_calls",
            "full_file_reads",
            "input_bytes",
            "operation",
            "output_bytes",
            "patch_bytes",
            "round",
            "tokens",
            "turns",
        }
        extra_keys = set(data.keys()) - allowed_keys
        if extra_keys:
            raise ContinuityStateValidationError(f"Unknown fields in {context_name}: {sorted(extra_keys)}")
        for req in ("brain_id", "operation", "tokens"):
            if req not in data:
                raise ContinuityStateValidationError(f"Missing required field '{req}' in {context_name}")

        tokens = TokenMeasurement.from_dict(data["tokens"], f"{context_name}.tokens")
        return cls(
            brain_id=data["brain_id"],
            operation=data["operation"],
            tokens=tokens,
            round=data.get("round", 1),
            turns=data.get("turns", 1),
            input_bytes=data.get("input_bytes"),
            output_bytes=data.get("output_bytes"),
            patch_bytes=data.get("patch_bytes"),
            full_file_reads=data.get("full_file_reads"),
            artifact_reads=data.get("artifact_reads"),
            external_api_calls=data.get("external_api_calls"),
        )


@dataclass(frozen=True)
class ExecutorUsageRecord:
    """Audit record of Executor implementation/fixing usage."""
    executor_id: str
    action: ExecutorAction
    tokens: TokenMeasurement
    runs: int = 1
    input_bytes: int | None = None
    output_bytes: int | None = None
    test_runs: int | None = None
    external_api_calls: int | None = None

    def __post_init__(self) -> None:
        canon_exec = _validate_canonical_actor_id(self.executor_id, "ExecutorUsageRecord.executor_id")
        object.__setattr__(self, "executor_id", canon_exec)

        if not isinstance(self.action, ExecutorAction):
            try:
                object.__setattr__(self, "action", ExecutorAction(self.action))
            except Exception as e:
                valid_actions = ", ".join(a.value for a in ExecutorAction)
                raise ContinuityStateValidationError(
                    f"Invalid ExecutorAction: {self.action!r}. Valid values: {valid_actions}"
                ) from e

        if not isinstance(self.tokens, TokenMeasurement):
            raise ContinuityStateValidationError(
                f"ExecutorUsageRecord.tokens must be a TokenMeasurement, got: {type(self.tokens).__name__}"
            )

        _validate_usage_int(self.runs, "ExecutorUsageRecord.runs", min_val=1)
        _validate_usage_int(self.input_bytes, "ExecutorUsageRecord.input_bytes", allow_none=True)
        _validate_usage_int(self.output_bytes, "ExecutorUsageRecord.output_bytes", allow_none=True)
        _validate_usage_int(self.test_runs, "ExecutorUsageRecord.test_runs", allow_none=True)
        _validate_usage_int(self.external_api_calls, "ExecutorUsageRecord.external_api_calls", allow_none=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action.value,
            "executor_id": self.executor_id,
            "external_api_calls": self.external_api_calls,
            "input_bytes": self.input_bytes,
            "output_bytes": self.output_bytes,
            "runs": self.runs,
            "test_runs": self.test_runs,
            "tokens": self.tokens.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Any, context_name: str = "ExecutorUsageRecord") -> ExecutorUsageRecord:
        if not isinstance(data, dict):
            raise ContinuityStateValidationError(f"{context_name} must be a dict, got: {type(data).__name__}")
        allowed_keys = {
            "action",
            "executor_id",
            "external_api_calls",
            "input_bytes",
            "output_bytes",
            "runs",
            "test_runs",
            "tokens",
        }
        extra_keys = set(data.keys()) - allowed_keys
        if extra_keys:
            raise ContinuityStateValidationError(f"Unknown fields in {context_name}: {sorted(extra_keys)}")
        for req in ("executor_id", "action", "tokens"):
            if req not in data:
                raise ContinuityStateValidationError(f"Missing required field '{req}' in {context_name}")

        tokens = TokenMeasurement.from_dict(data["tokens"], f"{context_name}.tokens")
        return cls(
            executor_id=data["executor_id"],
            action=data["action"],
            tokens=tokens,
            runs=data.get("runs", 1),
            input_bytes=data.get("input_bytes"),
            output_bytes=data.get("output_bytes"),
            test_runs=data.get("test_runs"),
            external_api_calls=data.get("external_api_calls"),
        )


@dataclass(frozen=True)
class HumanUsage:
    """Measurement of operator/human workflow interactions."""
    approvals: int = 0
    manual_sync: int = 0
    manual_pending: int = 0
    manual_watch: int = 0
    human_copy_paste_bytes: int | None = None

    def __post_init__(self) -> None:
        _validate_usage_int(self.approvals, "HumanUsage.approvals")
        _validate_usage_int(self.manual_sync, "HumanUsage.manual_sync")
        _validate_usage_int(self.manual_pending, "HumanUsage.manual_pending")
        _validate_usage_int(self.manual_watch, "HumanUsage.manual_watch")
        _validate_usage_int(self.human_copy_paste_bytes, "HumanUsage.human_copy_paste_bytes", allow_none=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "approvals": self.approvals,
            "human_copy_paste_bytes": self.human_copy_paste_bytes,
            "manual_pending": self.manual_pending,
            "manual_sync": self.manual_sync,
            "manual_watch": self.manual_watch,
        }

    @classmethod
    def from_dict(cls, data: Any, context_name: str = "HumanUsage") -> HumanUsage:
        if not isinstance(data, dict):
            raise ContinuityStateValidationError(f"{context_name} must be a dict, got: {type(data).__name__}")
        allowed_keys = {
            "approvals",
            "human_copy_paste_bytes",
            "manual_pending",
            "manual_sync",
            "manual_watch",
        }
        extra_keys = set(data.keys()) - allowed_keys
        if extra_keys:
            raise ContinuityStateValidationError(f"Unknown fields in {context_name}: {sorted(extra_keys)}")
        return cls(
            approvals=data.get("approvals", 0),
            manual_sync=data.get("manual_sync", 0),
            manual_pending=data.get("manual_pending", 0),
            manual_watch=data.get("manual_watch", 0),
            human_copy_paste_bytes=data.get("human_copy_paste_bytes"),
        )


@dataclass(frozen=True)
class EfficiencyMetrics:
    """Efficiency and context-utilization measurements."""
    brain_context_bytes: int | None = None
    useful_context_bytes: int | None = None
    redundant_context_bytes: int | None = None
    escalated_context_bytes: int | None = None
    context_efficiency_ratio: float | None = None
    full_file_read_rate: float | None = None

    def __post_init__(self) -> None:
        _validate_usage_int(self.brain_context_bytes, "EfficiencyMetrics.brain_context_bytes", allow_none=True)
        _validate_usage_int(self.useful_context_bytes, "EfficiencyMetrics.useful_context_bytes", allow_none=True)
        _validate_usage_int(self.redundant_context_bytes, "EfficiencyMetrics.redundant_context_bytes", allow_none=True)
        _validate_usage_int(self.escalated_context_bytes, "EfficiencyMetrics.escalated_context_bytes", allow_none=True)

        norm_eff_ratio = _validate_canonical_ratio(
            self.context_efficiency_ratio, "EfficiencyMetrics.context_efficiency_ratio", allow_none=True
        )
        object.__setattr__(self, "context_efficiency_ratio", norm_eff_ratio)

        norm_read_rate = _validate_canonical_ratio(
            self.full_file_read_rate, "EfficiencyMetrics.full_file_read_rate", allow_none=True
        )
        object.__setattr__(self, "full_file_read_rate", norm_read_rate)

        # Enforce exact partition equality when all components and total are known
        if (
            self.brain_context_bytes is not None
            and self.useful_context_bytes is not None
            and self.redundant_context_bytes is not None
            and self.escalated_context_bytes is not None
        ):
            sum_all = self.useful_context_bytes + self.redundant_context_bytes + self.escalated_context_bytes
            if sum_all != self.brain_context_bytes:
                raise ContinuityStateValidationError(
                    f"Inconsistent efficiency partition: sum of components ({sum_all}) != total brain_context_bytes ({self.brain_context_bytes})"
                )
        elif self.brain_context_bytes is not None:
            sum_known = sum(
                x for x in (self.useful_context_bytes, self.redundant_context_bytes, self.escalated_context_bytes) if x is not None
            )
            if sum_known > self.brain_context_bytes:
                raise ContinuityStateValidationError(
                    f"Impossible efficiency partition: partial sum of components ({sum_known}) exceeds total brain_context_bytes ({self.brain_context_bytes})"
                )

        # C3: UNKNOWN efficiency inputs require context_efficiency_ratio to be None
        if self.useful_context_bytes is None or self.brain_context_bytes is None or self.brain_context_bytes == 0:
            if self.context_efficiency_ratio is not None:
                raise ContinuityStateValidationError(
                    "context_efficiency_ratio must be None when useful_context_bytes or brain_context_bytes is unknown or brain_context_bytes is 0"
                )
        else:
            expected_ratio = calculate_context_efficiency_ratio(self.useful_context_bytes, self.brain_context_bytes)
            if self.context_efficiency_ratio is not None and float(self.context_efficiency_ratio) != float(expected_ratio):
                raise ContinuityStateValidationError(
                    f"Inconsistent context_efficiency_ratio: supplied {self.context_efficiency_ratio} != expected {expected_ratio} (useful_bytes / brain_context_bytes)"
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "brain_context_bytes": self.brain_context_bytes,
            "context_efficiency_ratio": self.context_efficiency_ratio,
            "escalated_context_bytes": self.escalated_context_bytes,
            "full_file_read_rate": self.full_file_read_rate,
            "redundant_context_bytes": self.redundant_context_bytes,
            "useful_context_bytes": self.useful_context_bytes,
        }

    @classmethod
    def from_dict(cls, data: Any, context_name: str = "EfficiencyMetrics") -> EfficiencyMetrics:
        if not isinstance(data, dict):
            raise ContinuityStateValidationError(f"{context_name} must be a dict, got: {type(data).__name__}")
        allowed_keys = {
            "brain_context_bytes",
            "context_efficiency_ratio",
            "escalated_context_bytes",
            "full_file_read_rate",
            "redundant_context_bytes",
            "useful_context_bytes",
        }
        extra_keys = set(data.keys()) - allowed_keys
        if extra_keys:
            raise ContinuityStateValidationError(f"Unknown fields in {context_name}: {sorted(extra_keys)}")
        return cls(
            brain_context_bytes=data.get("brain_context_bytes"),
            useful_context_bytes=data.get("useful_context_bytes"),
            redundant_context_bytes=data.get("redundant_context_bytes"),
            escalated_context_bytes=data.get("escalated_context_bytes"),
            context_efficiency_ratio=data.get("context_efficiency_ratio"),
            full_file_read_rate=data.get("full_file_read_rate"),
        )


@dataclass(frozen=True)
class TaskUsageRecord:
    """
    Immutable, deterministic task-level usage and efficiency record (ADR-014 Schema Version 1).
    """
    task_id: str
    brain_usage: tuple[BrainUsageRecord, ...] = ()
    executor_usage: tuple[ExecutorUsageRecord, ...] = ()
    human_usage: HumanUsage = HumanUsage()
    efficiency: EfficiencyMetrics = EfficiencyMetrics()
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ContinuityStateValidationError(
                f"Unsupported schema_version: {self.schema_version!r} (expected {SCHEMA_VERSION!r})"
            )

        _validate_task_id(self.task_id, "TaskUsageRecord.task_id")

        if not isinstance(self.brain_usage, tuple):
            try:
                object.__setattr__(self, "brain_usage", tuple(self.brain_usage))
            except Exception as e:
                raise ContinuityStateValidationError("TaskUsageRecord.brain_usage must be an iterable of BrainUsageRecord") from e

        for idx, b in enumerate(self.brain_usage):
            if not isinstance(b, BrainUsageRecord):
                raise ContinuityStateValidationError(
                    f"brain_usage[{idx}] must be a BrainUsageRecord, got: {type(b).__name__}"
                )

        if not isinstance(self.executor_usage, tuple):
            try:
                object.__setattr__(self, "executor_usage", tuple(self.executor_usage))
            except Exception as e:
                raise ContinuityStateValidationError("TaskUsageRecord.executor_usage must be an iterable of ExecutorUsageRecord") from e

        for idx, ex in enumerate(self.executor_usage):
            if not isinstance(ex, ExecutorUsageRecord):
                raise ContinuityStateValidationError(
                    f"executor_usage[{idx}] must be an ExecutorUsageRecord, got: {type(ex).__name__}"
                )

        if not isinstance(self.human_usage, HumanUsage):
            raise ContinuityStateValidationError(
                f"TaskUsageRecord.human_usage must be a HumanUsage, got: {type(self.human_usage).__name__}"
            )

        if not isinstance(self.efficiency, EfficiencyMetrics):
            raise ContinuityStateValidationError(
                f"TaskUsageRecord.efficiency must be an EfficiencyMetrics, got: {type(self.efficiency).__name__}"
            )

        # Enforce 16 KiB size cap fail-closed in constructor/parser
        raw_canonical = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        utf8_bytes = raw_canonical.encode("utf-8")
        if len(utf8_bytes) > MAX_SERIALIZED_BYTES:
            raise ContinuityStateValidationError(
                f"Serialized TaskUsageRecord size ({len(utf8_bytes)} bytes) exceeds MAX_SERIALIZED_BYTES limit ({MAX_SERIALIZED_BYTES})"
            )

    def to_dict(self) -> dict[str, Any]:
        """Deterministic JSON-serializable dictionary representation."""
        return {
            "brain_usage": [b.to_dict() for b in self.brain_usage],
            "efficiency": self.efficiency.to_dict(),
            "executor_usage": [e.to_dict() for e in self.executor_usage],
            "human_usage": self.human_usage.to_dict(),
            "schema_version": self.schema_version,
            "task_id": self.task_id,
        }

    def to_canonical_json(self) -> str:
        """
        Produces deterministic canonical JSON string.
        Enforces maximum 16 KiB size cap fail-closed with no truncation.
        """
        data = self.to_dict()
        canonical_str = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        utf8_bytes = canonical_str.encode("utf-8")
        if len(utf8_bytes) > MAX_SERIALIZED_BYTES:
            raise ContinuityStateValidationError(
                f"Serialized TaskUsageRecord size ({len(utf8_bytes)} bytes) exceeds MAX_SERIALIZED_BYTES limit ({MAX_SERIALIZED_BYTES})"
            )
        return canonical_str

    def fingerprint(self) -> str:
        """Computes deterministic SHA-256 fingerprint from canonical serialized bytes."""
        canonical_str = self.to_canonical_json()
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    @classmethod
    def from_dict(cls, data: Any) -> TaskUsageRecord:
        """Constructs and strictly validates TaskUsageRecord from dictionary."""
        if not isinstance(data, dict):
            raise ContinuityStateValidationError(f"TaskUsageRecord root must be a dict, got: {type(data).__name__}")

        allowed_root_keys = {
            "brain_usage",
            "efficiency",
            "executor_usage",
            "human_usage",
            "schema_version",
            "task_id",
        }
        extra_keys = set(data.keys()) - allowed_root_keys
        if extra_keys:
            raise ContinuityStateValidationError(f"Unknown root fields in TaskUsageRecord: {sorted(extra_keys)}")

        for req in ("task_id", "schema_version"):
            if req not in data:
                raise ContinuityStateValidationError(f"Missing required field '{req}' in TaskUsageRecord")

        if data["schema_version"] != SCHEMA_VERSION:
            raise ContinuityStateValidationError(
                f"Unsupported schema_version: {data['schema_version']!r} (expected {SCHEMA_VERSION!r})"
            )

        task_id = data["task_id"]

        brain_raw = data.get("brain_usage", [])
        if not isinstance(brain_raw, list):
            raise ContinuityStateValidationError("TaskUsageRecord.brain_usage must be a list")
        brain_records = [
            BrainUsageRecord.from_dict(b, f"brain_usage[{i}]") for i, b in enumerate(brain_raw)
        ]

        exec_raw = data.get("executor_usage", [])
        if not isinstance(exec_raw, list):
            raise ContinuityStateValidationError("TaskUsageRecord.executor_usage must be a list")
        exec_records = [
            ExecutorUsageRecord.from_dict(e, f"executor_usage[{i}]") for i, e in enumerate(exec_raw)
        ]

        human_data = data.get("human_usage", {})
        human_usage = HumanUsage.from_dict(human_data, "human_usage")

        eff_data = data.get("efficiency", {})
        efficiency = EfficiencyMetrics.from_dict(eff_data, "efficiency")

        return cls(
            task_id=task_id,
            brain_usage=tuple(brain_records),
            executor_usage=tuple(exec_records),
            human_usage=human_usage,
            efficiency=efficiency,
            schema_version=data["schema_version"],
        )

    @classmethod
    def from_json(cls, text: str | bytes) -> TaskUsageRecord:
        """Parses and strictly validates TaskUsageRecord from JSON string or bytes."""
        if isinstance(text, (bytes, bytearray)):
            raw_bytes = bytes(text)
            if len(raw_bytes) > MAX_SERIALIZED_BYTES:
                raise ContinuityStateValidationError(
                    f"Input JSON size ({len(raw_bytes)} bytes) exceeds maximum allowable size of {MAX_SERIALIZED_BYTES} bytes"
                )
            try:
                decoded_text = raw_bytes.decode("utf-8")
            except UnicodeDecodeError as e:
                raise ContinuityStateValidationError(f"Invalid UTF-8 encoding in JSON: {e}") from e
        elif isinstance(text, str):
            raw_bytes = text.encode("utf-8")
            if len(raw_bytes) > MAX_SERIALIZED_BYTES:
                raise ContinuityStateValidationError(
                    f"Input JSON size ({len(raw_bytes)} bytes) exceeds maximum allowable size of {MAX_SERIALIZED_BYTES} bytes"
                )
            decoded_text = text
        else:
            raise ContinuityStateValidationError(f"from_json expects str or bytes, got: {type(text).__name__}")

        try:
            data = json.loads(decoded_text)
        except Exception as e:
            raise ContinuityStateValidationError(f"Malformed JSON input: {e}") from e

        return cls.from_dict(data)


# ---------------------------------------------------------------------------
# Pure Helpers
# ---------------------------------------------------------------------------

def estimate_tokens_from_bytes(
    byte_count: int,
    method: str = "utf8-bytes-div4-v1",
) -> TokenMeasurement:
    """
    Computes a deterministic token-equivalent estimate from byte count.
    ALWAYS returns source=ESTIMATED, never REPORTED.
    Fails closed if the requested method label is unsupported or byte_count exceeds MAX_USAGE_INT.
    """
    _validate_usage_int(byte_count, "byte_count")
    _validate_method_identifier(method, "method")

    if method not in SUPPORTED_ESTIMATION_METHODS:
        raise ContinuityStateValidationError(
            f"Unsupported estimation method: {method!r}. Supported methods: {sorted(SUPPORTED_ESTIMATION_METHODS)}"
        )

    if byte_count == 0:
        return TokenMeasurement(
            source=UsageSource.ESTIMATED,
            min_tokens=0,
            max_tokens=0,
            method=method,
        )

    min_tok = max(1, byte_count // 5)
    max_tok = max(1, (byte_count + 2) // 3)

    return TokenMeasurement(
        source=UsageSource.ESTIMATED,
        min_tokens=min_tok,
        max_tokens=max_tok,
        method=method,
    )


def aggregate_token_ranges(
    measurements: Sequence[TokenMeasurement],
) -> tuple[int | None, int | None]:
    """
    Deterministically aggregates min and max token ranges across a sequence of TokenMeasurements.
    Returns (total_min, total_max).
    If any measurement is UNKNOWN or missing min/max, returns (None, None) to preserve incompleteness.
    If measurements is empty, returns (0, 0).
    Fails closed if cumulative total_min or total_max exceeds MAX_USAGE_INT (R1-1).
    """
    if not measurements:
        return (0, 0)

    total_min = 0
    total_max = 0

    for m in measurements:
        if not isinstance(m, TokenMeasurement):
            raise ContinuityStateValidationError(f"Expected TokenMeasurement, got: {type(m).__name__}")
        if m.source == UsageSource.UNKNOWN or m.min_tokens is None or m.max_tokens is None:
            return (None, None)
        total_min += m.min_tokens
        total_max += m.max_tokens

    _validate_usage_int(total_min, "aggregate_token_ranges.total_min")
    _validate_usage_int(total_max, "aggregate_token_ranges.total_max")

    return (total_min, total_max)


def aggregate_token_ranges_by_actor_class(
    record: TaskUsageRecord,
) -> dict[str, tuple[int | None, int | None]]:
    """
    Deterministically aggregates token ranges separately for BRAIN and EXECUTOR actor classes (C5).
    Returns {'BRAIN': (brain_min, brain_max), 'EXECUTOR': (exec_min, exec_max)}.
    UNKNOWN in one class does not contaminate the other class's known aggregate.
    Empty actor class deterministically returns (0, 0).
    """
    if not isinstance(record, TaskUsageRecord):
        raise ContinuityStateValidationError(
            f"Expected TaskUsageRecord, got: {type(record).__name__}"
        )

    brain_tokens = [b.tokens for b in record.brain_usage]
    exec_tokens = [e.tokens for e in record.executor_usage]

    return {
        "BRAIN": aggregate_token_ranges(brain_tokens),
        "EXECUTOR": aggregate_token_ranges(exec_tokens),
    }


def calculate_context_efficiency_ratio(
    useful_bytes: int | None,
    total_bytes: int | None,
) -> float | None:
    """
    Calculates context efficiency ratio (useful_bytes / total_bytes).
    Returns None if either parameter is None or if total_bytes == 0.
    """
    if useful_bytes is None or total_bytes is None:
        return None
    _validate_usage_int(useful_bytes, "useful_bytes")
    _validate_usage_int(total_bytes, "total_bytes")

    if total_bytes == 0:
        return None
    if useful_bytes > total_bytes:
        raise ContinuityStateValidationError(
            f"useful_bytes ({useful_bytes}) cannot exceed total_bytes ({total_bytes})"
        )

    return round(useful_bytes / total_bytes, 4)
