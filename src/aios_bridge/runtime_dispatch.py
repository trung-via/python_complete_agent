"""External runtime capacity evidence for read-only M10.2 recommendations."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
from typing import Any, Iterable

from src.aios_bridge.continuity.dispatch import (
    CapacityClass,
    CapacityState,
    DispatchActorKind,
    ExecutorDispatchCandidate,
    ExecutorDispatchRequest,
)
from src.aios_bridge.continuity.executor import (
    ExecutionCapability,
    ExecutionOperation,
    ExecutorCapabilities,
)
from src.aios_bridge.continuity.errors import ContinuityStateValidationError
from src.aios_bridge.continuity.state import (
    MAX_SERIALIZED_BYTES,
    SCHEMA_VERSION,
    _validate_actor_id,
)


MAX_CAPACITY_TTL_SECONDS = 86400
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ObservationSource(str, Enum):
    HUMAN_DECLARED = "HUMAN_DECLARED"
    ADAPTER_REPORTED = "ADAPTER_REPORTED"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _parse_enum(value: Any, enum_type: type[Enum], field_name: str):
    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(value)
    except (TypeError, ValueError) as exc:
        raise ContinuityStateValidationError(
            f"Invalid {field_name}: {value!r}; expected {[item.value for item in enum_type]}"
        ) from exc


def _validate_actor_path_component(value: Any, field_name: str = "actor_id") -> str:
    if not isinstance(value, str) or value != value.strip():
        raise ContinuityStateValidationError(f"{field_name} must be an exact canonical actor ID")
    if value in {".", ".."} or "/" in value or "\\" in value:
        raise ContinuityStateValidationError(f"{field_name} must be a path-safe single component")
    return _validate_actor_id(value, field_name)


def _validate_exact_non_negative_int(value: Any, field_name: str) -> int:
    if type(value) is not int or value < 0:
        raise ContinuityStateValidationError(f"{field_name} must be an exact non-negative integer")
    return value


def _validate_ttl(value: Any) -> int:
    if type(value) is not int or not 1 <= value <= MAX_CAPACITY_TTL_SECONDS:
        raise ContinuityStateValidationError(
            f"ttl_seconds must be an exact integer in [1, {MAX_CAPACITY_TTL_SECONDS}]"
        )
    return value


def _validate_preference_rank(value: Any) -> int:
    if type(value) is not int or value < 0:
        raise ContinuityStateValidationError("preference_rank must be an exact non-negative integer")
    return value


def _validate_serialized_size(value: Any, context_name: str) -> None:
    size = len(_canonical_json(value).encode("utf-8"))
    if size > MAX_SERIALIZED_BYTES:
        raise ContinuityStateValidationError(
            f"Serialized {context_name} exceeds size limit ({size} > {MAX_SERIALIZED_BYTES})"
        )


def _normalize_enum_sequence(
    value: Any,
    enum_type: type[Enum],
    field_name: str,
    *,
    require_nonempty: bool,
) -> tuple[Any, ...]:
    if isinstance(value, (str, bytes, dict)):
        raise ContinuityStateValidationError(f"{field_name} must be an ordered enum sequence")
    try:
        raw = tuple(value)
    except TypeError as exc:
        raise ContinuityStateValidationError(f"{field_name} must be iterable") from exc
    if require_nonempty and not raw:
        raise ContinuityStateValidationError(f"{field_name} must not be empty")
    parsed = tuple(_parse_enum(item, enum_type, field_name) for item in raw)
    if len(parsed) != len(set(parsed)):
        raise ContinuityStateValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(parsed, key=lambda item: item.value))


@dataclass(frozen=True)
class RuntimeCapacityRecord:
    actor_kind: DispatchActorKind
    actor_id: str
    capacity_state: CapacityState
    observed_at_epoch_seconds: int
    ttl_seconds: int
    observation_source: ObservationSource = ObservationSource.HUMAN_DECLARED
    schema_version: str = SCHEMA_VERSION
    record_fingerprint: str | None = None

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ContinuityStateValidationError("Unsupported RuntimeCapacityRecord schema_version")
        object.__setattr__(
            self,
            "actor_kind",
            _parse_enum(self.actor_kind, DispatchActorKind, "RuntimeCapacityRecord.actor_kind"),
        )
        _validate_actor_path_component(self.actor_id)
        object.__setattr__(
            self,
            "capacity_state",
            _parse_enum(self.capacity_state, CapacityState, "RuntimeCapacityRecord.capacity_state"),
        )
        _validate_exact_non_negative_int(
            self.observed_at_epoch_seconds, "observed_at_epoch_seconds"
        )
        _validate_ttl(self.ttl_seconds)
        object.__setattr__(
            self,
            "observation_source",
            _parse_enum(
                self.observation_source,
                ObservationSource,
                "RuntimeCapacityRecord.observation_source",
            ),
        )
        computed = self.fingerprint()
        if self.record_fingerprint is None:
            object.__setattr__(self, "record_fingerprint", computed)
        elif not _SHA256_RE.fullmatch(self.record_fingerprint) or self.record_fingerprint != computed:
            raise ContinuityStateValidationError(
                "RuntimeCapacityRecord record_fingerprint does not match canonical semantics"
            )
        _validate_serialized_size(self.to_dict(), "RuntimeCapacityRecord")

    def semantic_dict(self) -> dict[str, Any]:
        return {
            "actor_id": self.actor_id,
            "actor_kind": self.actor_kind.value,
            "capacity_state": self.capacity_state.value,
            "observation_source": self.observation_source.value,
            "observed_at_epoch_seconds": self.observed_at_epoch_seconds,
            "schema_version": self.schema_version,
            "ttl_seconds": self.ttl_seconds,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.semantic_dict(), "record_fingerprint": self.record_fingerprint}

    def to_canonical_json(self) -> str:
        return _canonical_json(self.to_dict())

    def fingerprint(self) -> str:
        return hashlib.sha256(_canonical_json(self.semantic_dict()).encode("utf-8")).hexdigest()

    @classmethod
    def from_dict(cls, data: Any) -> RuntimeCapacityRecord:
        if not isinstance(data, dict):
            raise ContinuityStateValidationError("RuntimeCapacityRecord root must be a JSON object")
        expected = {
            "actor_id",
            "actor_kind",
            "capacity_state",
            "observation_source",
            "observed_at_epoch_seconds",
            "record_fingerprint",
            "schema_version",
            "ttl_seconds",
        }
        if set(data) != expected:
            raise ContinuityStateValidationError(
                f"RuntimeCapacityRecord fields must be exact; missing={sorted(expected - set(data))}, "
                f"extra={sorted(set(data) - expected)}"
            )
        return cls(
            actor_kind=data["actor_kind"],
            actor_id=data["actor_id"],
            capacity_state=data["capacity_state"],
            observed_at_epoch_seconds=data["observed_at_epoch_seconds"],
            ttl_seconds=data["ttl_seconds"],
            observation_source=data["observation_source"],
            schema_version=data["schema_version"],
            record_fingerprint=data["record_fingerprint"],
        )

    @classmethod
    def from_json(cls, value: str | bytes) -> RuntimeCapacityRecord:
        if isinstance(value, bytes):
            if len(value) > MAX_SERIALIZED_BYTES:
                raise ContinuityStateValidationError("RuntimeCapacityRecord JSON exceeds size limit")
            try:
                value = value.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ContinuityStateValidationError(
                    "RuntimeCapacityRecord JSON must be valid UTF-8"
                ) from exc
        if not isinstance(value, str):
            raise ContinuityStateValidationError("RuntimeCapacityRecord JSON must be str or bytes")
        if len(value.encode("utf-8")) > MAX_SERIALIZED_BYTES:
            raise ContinuityStateValidationError("RuntimeCapacityRecord JSON exceeds size limit")
        try:
            data = json.loads(value)
        except (TypeError, ValueError) as exc:
            raise ContinuityStateValidationError(
                f"Malformed RuntimeCapacityRecord JSON: {exc}"
            ) from exc
        return cls.from_dict(data)


def classify_capacity_freshness(
    record: RuntimeCapacityRecord, now_epoch_seconds: int
) -> str:
    if not isinstance(record, RuntimeCapacityRecord):
        raise ContinuityStateValidationError("record must be RuntimeCapacityRecord")
    _validate_exact_non_negative_int(now_epoch_seconds, "now_epoch_seconds")
    if now_epoch_seconds < record.observed_at_epoch_seconds:
        raise ContinuityStateValidationError("Capacity observation is from the future")
    if now_epoch_seconds <= record.observed_at_epoch_seconds + record.ttl_seconds:
        return "FRESH"
    return "EXPIRED"


def effective_capacity_state(
    record_or_none: RuntimeCapacityRecord | None, now_epoch_seconds: int
) -> CapacityState:
    _validate_exact_non_negative_int(now_epoch_seconds, "now_epoch_seconds")
    if record_or_none is None:
        return CapacityState.UNKNOWN
    return (
        record_or_none.capacity_state
        if classify_capacity_freshness(record_or_none, now_epoch_seconds) == "FRESH"
        else CapacityState.UNKNOWN
    )


class AtomicRuntimeCapacityStore:
    def __init__(self, root: Path | str):
        self.root = Path(root).resolve()

    def record_path(self, actor_kind: DispatchActorKind, actor_id: str) -> Path:
        kind = _parse_enum(actor_kind, DispatchActorKind, "actor_kind")
        actor = _validate_actor_path_component(actor_id)
        return self.root / kind.value / f"{actor}.json"

    def write(self, record: RuntimeCapacityRecord) -> None:
        if not isinstance(record, RuntimeCapacityRecord):
            raise ContinuityStateValidationError("record must be RuntimeCapacityRecord")
        final_path = self.record_path(record.actor_kind, record.actor_id)
        final_path.parent.mkdir(parents=True, exist_ok=True)
        payload = record.to_canonical_json().encode("utf-8") + b"\n"
        temp_path = final_path.with_name(f".{final_path.name}.tmp-{secrets.token_hex(8)}")
        try:
            with temp_path.open("xb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, final_path)
            try:
                directory_fd = os.open(str(final_path.parent), os.O_RDONLY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
            except OSError:
                pass
        except Exception as exc:
            try:
                temp_path.unlink()
            except OSError:
                pass
            raise ContinuityStateValidationError(
                f"Atomic runtime capacity write failed for {record.actor_id}: {exc}"
            ) from exc
        loaded = self.load(record.actor_kind, record.actor_id)
        if loaded != record or loaded is None or loaded.record_fingerprint != record.record_fingerprint:
            raise ContinuityStateValidationError("Runtime capacity atomic write read-back mismatch")

    def load(
        self, actor_kind: DispatchActorKind, actor_id: str
    ) -> RuntimeCapacityRecord | None:
        kind = _parse_enum(actor_kind, DispatchActorKind, "actor_kind")
        actor = _validate_actor_path_component(actor_id)
        path = self.record_path(kind, actor)
        if not path.exists():
            return None
        if not path.is_file():
            raise ContinuityStateValidationError(f"Runtime capacity path is not a file: {path}")
        try:
            with path.open("rb") as handle:
                raw = handle.read(MAX_SERIALIZED_BYTES + 1)
        except OSError as exc:
            raise ContinuityStateValidationError(
                f"Runtime capacity record is unreadable: {path}"
            ) from exc
        if not raw or len(raw) > MAX_SERIALIZED_BYTES:
            raise ContinuityStateValidationError("Runtime capacity record is empty or oversized")
        record = RuntimeCapacityRecord.from_json(raw)
        if record.actor_kind is not kind or record.actor_id != actor:
            raise ContinuityStateValidationError("Runtime capacity record namespace mismatch")
        return record

    def list_records(
        self,
        actor_kind: DispatchActorKind | None = None,
        actor_id: str | None = None,
    ) -> tuple[RuntimeCapacityRecord, ...]:
        if actor_id is not None and actor_kind is None:
            raise ContinuityStateValidationError("actor_id filter requires actor_kind")
        if actor_kind is not None:
            kinds = (_parse_enum(actor_kind, DispatchActorKind, "actor_kind"),)
        else:
            kinds = tuple(sorted(DispatchActorKind, key=lambda item: item.value))
        if actor_id is not None:
            actor = _validate_actor_path_component(actor_id)
            record = self.load(kinds[0], actor)
            return () if record is None else (record,)
        records = []
        for kind in kinds:
            directory = self.root / kind.value
            if not directory.exists():
                continue
            if not directory.is_dir():
                raise ContinuityStateValidationError(
                    f"Runtime capacity actor-kind namespace is not a directory: {directory}"
                )
            for path in sorted(directory.glob("*.json"), key=lambda item: item.name):
                if not path.is_file():
                    raise ContinuityStateValidationError(
                        f"Runtime capacity discovered path is not a file: {path}"
                    )
                actor = _validate_actor_path_component(path.stem)
                record = self.load(kind, actor)
                if record is None:
                    raise ContinuityStateValidationError("Discovered runtime record disappeared")
                records.append(record)
        return tuple(records)


@dataclass(frozen=True)
class ExecutorPolicyCandidateSpec:
    executor_id: str
    supported_operations: tuple[ExecutionOperation, ...]
    supported_capabilities: tuple[ExecutionCapability, ...]
    capacity_class: CapacityClass
    preference_rank: int

    def __post_init__(self) -> None:
        _validate_actor_path_component(self.executor_id, "executor_id")
        object.__setattr__(
            self,
            "supported_operations",
            _normalize_enum_sequence(
                self.supported_operations,
                ExecutionOperation,
                "supported_operations",
                require_nonempty=True,
            ),
        )
        object.__setattr__(
            self,
            "supported_capabilities",
            _normalize_enum_sequence(
                self.supported_capabilities,
                ExecutionCapability,
                "supported_capabilities",
                require_nonempty=False,
            ),
        )
        object.__setattr__(
            self,
            "capacity_class",
            _parse_enum(self.capacity_class, CapacityClass, "capacity_class"),
        )
        _validate_preference_rank(self.preference_rank)
        _validate_serialized_size(self.to_dict(), "ExecutorPolicyCandidateSpec")

    def to_dict(self) -> dict[str, Any]:
        return {
            "capacity_class": self.capacity_class.value,
            "executor_id": self.executor_id,
            "preference_rank": self.preference_rank,
            "supported_capabilities": [item.value for item in self.supported_capabilities],
            "supported_operations": [item.value for item in self.supported_operations],
        }

    @classmethod
    def from_dict(cls, data: Any) -> ExecutorPolicyCandidateSpec:
        if not isinstance(data, dict):
            raise ContinuityStateValidationError("Policy candidate must be a JSON object")
        expected = {
            "capacity_class",
            "executor_id",
            "preference_rank",
            "supported_capabilities",
            "supported_operations",
        }
        if set(data) != expected:
            raise ContinuityStateValidationError("Policy candidate fields must be exact")
        return cls(
            executor_id=data["executor_id"],
            supported_operations=data["supported_operations"],
            supported_capabilities=data["supported_capabilities"],
            capacity_class=data["capacity_class"],
            preference_rank=data["preference_rank"],
        )


@dataclass(frozen=True)
class ExecutorDispatchPolicySpec:
    operation: ExecutionOperation
    required_capabilities: tuple[ExecutionCapability, ...]
    candidates: tuple[ExecutorPolicyCandidateSpec, ...]
    allow_paid_api: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "operation", _parse_enum(self.operation, ExecutionOperation, "operation")
        )
        object.__setattr__(
            self,
            "required_capabilities",
            _normalize_enum_sequence(
                self.required_capabilities,
                ExecutionCapability,
                "required_capabilities",
                require_nonempty=False,
            ),
        )
        if isinstance(self.candidates, (str, bytes, dict)):
            raise ContinuityStateValidationError("candidates must be an iterable of policy candidates")
        try:
            candidates = tuple(self.candidates)
        except TypeError as exc:
            raise ContinuityStateValidationError("candidates must be iterable") from exc
        if not candidates or any(not isinstance(item, ExecutorPolicyCandidateSpec) for item in candidates):
            raise ContinuityStateValidationError(
                "candidates must be non-empty ExecutorPolicyCandidateSpec values"
            )
        actor_ids = [item.executor_id for item in candidates]
        if len(actor_ids) != len(set(actor_ids)):
            raise ContinuityStateValidationError("Duplicate executor IDs in dispatch policy")
        object.__setattr__(
            self, "candidates", tuple(sorted(candidates, key=lambda item: item.executor_id))
        )
        if type(self.allow_paid_api) is not bool:
            raise ContinuityStateValidationError("allow_paid_api must be exact bool")
        _validate_serialized_size(self.to_dict(), "ExecutorDispatchPolicySpec")

    def to_dict(self) -> dict[str, Any]:
        return {
            "allow_paid_api": self.allow_paid_api,
            "candidates": [item.to_dict() for item in self.candidates],
            "operation": self.operation.value,
            "required_capabilities": [item.value for item in self.required_capabilities],
        }

    def to_canonical_json(self) -> str:
        return _canonical_json(self.to_dict())

    def fingerprint(self) -> str:
        return hashlib.sha256(self.to_canonical_json().encode("utf-8")).hexdigest()

    @classmethod
    def from_dict(cls, data: Any) -> ExecutorDispatchPolicySpec:
        if not isinstance(data, dict):
            raise ContinuityStateValidationError("Executor dispatch policy must be a JSON object")
        expected = {"allow_paid_api", "candidates", "operation", "required_capabilities"}
        if set(data) != expected:
            raise ContinuityStateValidationError(
                f"Executor dispatch policy fields must be exact; missing={sorted(expected - set(data))}, "
                f"extra={sorted(set(data) - expected)}"
            )
        if not isinstance(data["candidates"], list):
            raise ContinuityStateValidationError("Policy candidates must be a JSON list")
        if not isinstance(data["required_capabilities"], list):
            raise ContinuityStateValidationError("required_capabilities must be a JSON list")
        return cls(
            operation=data["operation"],
            required_capabilities=data["required_capabilities"],
            candidates=tuple(ExecutorPolicyCandidateSpec.from_dict(item) for item in data["candidates"]),
            allow_paid_api=data["allow_paid_api"],
        )


def parse_executor_dispatch_policy_marker(content: str) -> ExecutorDispatchPolicySpec:
    if not isinstance(content, str):
        raise ContinuityStateValidationError("Dispatch policy artifact content must be text")
    prefix = "DISPATCH_EXECUTOR_POLICY_JSON:"
    occurrences = [line[len(prefix):].strip() for line in content.splitlines() if line.startswith(prefix)]
    if len(occurrences) != 1:
        raise ContinuityStateValidationError(
            f"Artifact must contain exactly one {prefix} marker; found {len(occurrences)}"
        )
    try:
        data = json.loads(occurrences[0])
    except (TypeError, ValueError) as exc:
        raise ContinuityStateValidationError(f"Malformed dispatch policy JSON: {exc}") from exc
    return ExecutorDispatchPolicySpec.from_dict(data)


@dataclass(frozen=True)
class CapacityEvidence:
    actor_id: str
    stored_state: CapacityState | None
    effective_state: CapacityState
    freshness: str
    record_fingerprint: str | None

    def __post_init__(self) -> None:
        _validate_actor_path_component(self.actor_id)
        if self.stored_state is not None:
            object.__setattr__(
                self,
                "stored_state",
                _parse_enum(self.stored_state, CapacityState, "stored_state"),
            )
        object.__setattr__(
            self,
            "effective_state",
            _parse_enum(self.effective_state, CapacityState, "effective_state"),
        )
        if self.freshness not in {"FRESH", "EXPIRED", "MISSING"}:
            raise ContinuityStateValidationError("Invalid capacity evidence freshness")
        if self.record_fingerprint is not None and not _SHA256_RE.fullmatch(
            self.record_fingerprint
        ):
            raise ContinuityStateValidationError("Invalid capacity evidence record fingerprint")

    def to_dict(self) -> dict[str, Any]:
        return {
            "actor_id": self.actor_id,
            "effective_state": self.effective_state.value,
            "freshness": self.freshness,
            "record_fingerprint": self.record_fingerprint,
            "stored_state": self.stored_state.value if self.stored_state is not None else None,
        }


def build_executor_dispatch_request_from_runtime(
    policy: ExecutorDispatchPolicySpec,
    store: AtomicRuntimeCapacityStore,
    now_epoch_seconds: int,
) -> tuple[ExecutorDispatchRequest, tuple[CapacityEvidence, ...]]:
    if not isinstance(policy, ExecutorDispatchPolicySpec):
        raise ContinuityStateValidationError("policy must be ExecutorDispatchPolicySpec")
    if not isinstance(store, AtomicRuntimeCapacityStore):
        raise ContinuityStateValidationError("store must be AtomicRuntimeCapacityStore")
    _validate_exact_non_negative_int(now_epoch_seconds, "now_epoch_seconds")
    candidates = []
    evidence = []
    for spec in policy.candidates:
        record = store.load(DispatchActorKind.EXECUTOR, spec.executor_id)
        if record is None:
            freshness = "MISSING"
            effective_state = CapacityState.UNKNOWN
            stored_state = None
            record_fingerprint = None
        else:
            if record.actor_kind is not DispatchActorKind.EXECUTOR or record.actor_id != spec.executor_id:
                raise ContinuityStateValidationError("Runtime capacity record does not match policy actor")
            freshness = classify_capacity_freshness(record, now_epoch_seconds)
            effective_state = effective_capacity_state(record, now_epoch_seconds)
            stored_state = record.capacity_state
            record_fingerprint = record.record_fingerprint
        capabilities = ExecutorCapabilities(
            executor_id=spec.executor_id,
            supported_operations=spec.supported_operations,
            supported_capabilities=spec.supported_capabilities,
        )
        candidates.append(
            ExecutorDispatchCandidate(
                executor_id=spec.executor_id,
                capabilities=capabilities,
                capacity_state=effective_state,
                capacity_class=spec.capacity_class,
                preference_rank=spec.preference_rank,
            )
        )
        evidence.append(
            CapacityEvidence(
                actor_id=spec.executor_id,
                stored_state=stored_state,
                effective_state=effective_state,
                freshness=freshness,
                record_fingerprint=record_fingerprint,
            )
        )
    request = ExecutorDispatchRequest(
        operation=policy.operation,
        candidates=tuple(candidates),
        required_capabilities=policy.required_capabilities,
        allow_paid_api=policy.allow_paid_api,
    )
    return request, tuple(sorted(evidence, key=lambda item: item.actor_id))


__all__ = [
    "AtomicRuntimeCapacityStore",
    "CapacityEvidence",
    "ExecutorDispatchPolicySpec",
    "ExecutorPolicyCandidateSpec",
    "MAX_CAPACITY_TTL_SECONDS",
    "ObservationSource",
    "RuntimeCapacityRecord",
    "build_executor_dispatch_request_from_runtime",
    "classify_capacity_freshness",
    "effective_capacity_state",
    "parse_executor_dispatch_policy_marker",
]
