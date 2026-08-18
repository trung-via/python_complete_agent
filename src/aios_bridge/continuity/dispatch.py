"""Pure deterministic Brain/Executor recommendation policy (ADR-026 / M10.1)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from typing import Any

from .brain import BrainCapability
from .executor import ExecutionCapability, ExecutionOperation, ExecutorCapabilities
from .errors import ContinuityStateValidationError
from .state import MAX_SERIALIZED_BYTES, SCHEMA_VERSION, BrainOperation, _validate_actor_id


class DispatchActorKind(str, Enum):
    BRAIN = "BRAIN"
    EXECUTOR = "EXECUTOR"


class CapacityState(str, Enum):
    AVAILABLE = "AVAILABLE"
    LIMITED = "LIMITED"
    QUOTA_EXHAUSTED = "QUOTA_EXHAUSTED"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


class CapacityClass(str, Enum):
    SUBSCRIPTION = "SUBSCRIPTION"
    PAID_API = "PAID_API"


class DispatchStatus(str, Enum):
    SELECTED = "SELECTED"
    WAIT = "WAIT"
    NO_COMPATIBLE_CANDIDATE = "NO_COMPATIBLE_CANDIDATE"


class DispatchReason(str, Enum):
    SELECTED_COMPATIBLE_AVAILABLE = "SELECTED_COMPATIBLE_AVAILABLE"
    WAIT_CAPACITY = "WAIT_CAPACITY"
    NO_COMPATIBLE_CANDIDATE = "NO_COMPATIBLE_CANDIDATE"


class CandidateReason(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    OPERATION_UNSUPPORTED = "OPERATION_UNSUPPORTED"
    CONTEXT_TOO_LARGE = "CONTEXT_TOO_LARGE"
    REQUIRED_CAPABILITY_MISSING = "REQUIRED_CAPABILITY_MISSING"
    PAID_API_NOT_ALLOWED = "PAID_API_NOT_ALLOWED"
    CAPACITY_LIMITED = "CAPACITY_LIMITED"
    CAPACITY_QUOTA_EXHAUSTED = "CAPACITY_QUOTA_EXHAUSTED"
    CAPACITY_UNAVAILABLE = "CAPACITY_UNAVAILABLE"
    CAPACITY_UNKNOWN = "CAPACITY_UNKNOWN"


_CAPACITY_CLASS_RANK = {
    CapacityClass.SUBSCRIPTION: 0,
    CapacityClass.PAID_API: 1,
}
_CAPACITY_STATE_RUNNABLE_RANK = {
    CapacityState.AVAILABLE: 0,
    CapacityState.LIMITED: 1,
}
_CAPACITY_REASON = {
    CapacityState.LIMITED: CandidateReason.CAPACITY_LIMITED,
    CapacityState.QUOTA_EXHAUSTED: CandidateReason.CAPACITY_QUOTA_EXHAUSTED,
    CapacityState.UNAVAILABLE: CandidateReason.CAPACITY_UNAVAILABLE,
    CapacityState.UNKNOWN: CandidateReason.CAPACITY_UNKNOWN,
}


def _canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _validate_canonical_actor_id(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or value != value.strip():
        raise ContinuityStateValidationError(f"{field_name} must be an exact canonical actor ID")
    return _validate_actor_id(value, field_name)


def _validate_preference_rank(value: Any, field_name: str) -> int:
    if type(value) is not int or value < 0:
        raise ContinuityStateValidationError(f"{field_name} must be an exact non-negative integer")
    return value


def _validate_required_context_bytes(value: Any) -> int | None:
    if value is None:
        return None
    if type(value) is not int or value < 0:
        raise ContinuityStateValidationError(
            "required_context_bytes must be None or an exact non-negative integer"
        )
    return value


def _validate_serialized_size(data: Any, context_name: str) -> None:
    size = len(_canonical_json(data).encode("utf-8"))
    if size > MAX_SERIALIZED_BYTES:
        raise ContinuityStateValidationError(
            f"Serialized {context_name} exceeds size limit ({size} > {MAX_SERIALIZED_BYTES})"
        )


def _parse_enum(value: Any, enum_type: type[Enum], field_name: str):
    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(value)
    except (TypeError, ValueError) as exc:
        raise ContinuityStateValidationError(
            f"Invalid {field_name}: {value!r}; expected one of {[item.value for item in enum_type]}"
        ) from exc


def _normalize_iterable(value: Any, field_name: str) -> tuple[Any, ...]:
    if isinstance(value, (str, bytes, dict)):
        raise ContinuityStateValidationError(f"{field_name} must be an iterable of typed items")
    try:
        return tuple(value)
    except TypeError as exc:
        raise ContinuityStateValidationError(f"{field_name} must be iterable") from exc


@dataclass(frozen=True)
class BrainDispatchCandidate:
    brain_id: str
    capability: BrainCapability
    capacity_state: CapacityState
    capacity_class: CapacityClass
    preference_rank: int = 0

    def __post_init__(self) -> None:
        actor_id = _validate_canonical_actor_id(self.brain_id, "BrainDispatchCandidate.brain_id")
        if not isinstance(self.capability, BrainCapability):
            raise ContinuityStateValidationError("BrainDispatchCandidate.capability must be BrainCapability")
        if actor_id != self.capability.brain_id:
            raise ContinuityStateValidationError("Brain candidate ID must exactly match capability brain_id")
        object.__setattr__(
            self,
            "capacity_state",
            _parse_enum(self.capacity_state, CapacityState, "BrainDispatchCandidate.capacity_state"),
        )
        object.__setattr__(
            self,
            "capacity_class",
            _parse_enum(self.capacity_class, CapacityClass, "BrainDispatchCandidate.capacity_class"),
        )
        _validate_preference_rank(self.preference_rank, "BrainDispatchCandidate.preference_rank")
        _validate_serialized_size(self.to_dict(), "BrainDispatchCandidate")

    def to_dict(self) -> dict[str, Any]:
        return {
            "brain_id": self.brain_id,
            "capability": self.capability.to_dict(),
            "capacity_class": self.capacity_class.value,
            "capacity_state": self.capacity_state.value,
            "preference_rank": self.preference_rank,
        }


@dataclass(frozen=True)
class ExecutorDispatchCandidate:
    executor_id: str
    capabilities: ExecutorCapabilities
    capacity_state: CapacityState
    capacity_class: CapacityClass
    preference_rank: int = 0

    def __post_init__(self) -> None:
        actor_id = _validate_canonical_actor_id(
            self.executor_id, "ExecutorDispatchCandidate.executor_id"
        )
        if not isinstance(self.capabilities, ExecutorCapabilities):
            raise ContinuityStateValidationError(
                "ExecutorDispatchCandidate.capabilities must be ExecutorCapabilities"
            )
        if actor_id != self.capabilities.executor_id:
            raise ContinuityStateValidationError(
                "Executor candidate ID must exactly match capabilities executor_id"
            )
        object.__setattr__(
            self,
            "capacity_state",
            _parse_enum(self.capacity_state, CapacityState, "ExecutorDispatchCandidate.capacity_state"),
        )
        object.__setattr__(
            self,
            "capacity_class",
            _parse_enum(self.capacity_class, CapacityClass, "ExecutorDispatchCandidate.capacity_class"),
        )
        _validate_preference_rank(self.preference_rank, "ExecutorDispatchCandidate.preference_rank")
        _validate_serialized_size(self.to_dict(), "ExecutorDispatchCandidate")

    def to_dict(self) -> dict[str, Any]:
        return {
            "capabilities": self.capabilities.to_dict(),
            "capacity_class": self.capacity_class.value,
            "capacity_state": self.capacity_state.value,
            "executor_id": self.executor_id,
            "preference_rank": self.preference_rank,
        }


@dataclass(frozen=True)
class BrainDispatchRequest:
    operation: BrainOperation
    candidates: tuple[BrainDispatchCandidate, ...]
    required_context_bytes: int | None = None
    allow_paid_api: bool = False
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ContinuityStateValidationError("Unsupported BrainDispatchRequest schema_version")
        object.__setattr__(
            self, "operation", _parse_enum(self.operation, BrainOperation, "BrainDispatchRequest.operation")
        )
        if type(self.allow_paid_api) is not bool:
            raise ContinuityStateValidationError("allow_paid_api must be exact bool")
        _validate_required_context_bytes(self.required_context_bytes)
        candidates = _normalize_iterable(self.candidates, "BrainDispatchRequest.candidates")
        if not candidates or any(not isinstance(item, BrainDispatchCandidate) for item in candidates):
            raise ContinuityStateValidationError(
                "BrainDispatchRequest.candidates must contain BrainDispatchCandidate values"
            )
        actor_ids = [item.brain_id for item in candidates]
        if len(actor_ids) != len(set(actor_ids)):
            raise ContinuityStateValidationError("Duplicate Brain dispatch candidate actor IDs")
        object.__setattr__(self, "candidates", tuple(sorted(candidates, key=lambda item: item.brain_id)))
        _validate_serialized_size(self.to_dict(), "BrainDispatchRequest")

    def to_dict(self) -> dict[str, Any]:
        return {
            "allow_paid_api": self.allow_paid_api,
            "candidates": [item.to_dict() for item in sorted(self.candidates, key=lambda item: item.brain_id)],
            "operation": self.operation.value,
            "required_context_bytes": self.required_context_bytes,
            "schema_version": self.schema_version,
        }

    def to_canonical_json(self) -> str:
        return _canonical_json(self.to_dict())

    def fingerprint(self) -> str:
        return hashlib.sha256(self.to_canonical_json().encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ExecutorDispatchRequest:
    operation: ExecutionOperation
    candidates: tuple[ExecutorDispatchCandidate, ...]
    required_capabilities: tuple[ExecutionCapability, ...] = ()
    allow_paid_api: bool = False
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ContinuityStateValidationError("Unsupported ExecutorDispatchRequest schema_version")
        object.__setattr__(
            self,
            "operation",
            _parse_enum(self.operation, ExecutionOperation, "ExecutorDispatchRequest.operation"),
        )
        if type(self.allow_paid_api) is not bool:
            raise ContinuityStateValidationError("allow_paid_api must be exact bool")
        candidates = _normalize_iterable(self.candidates, "ExecutorDispatchRequest.candidates")
        if not candidates or any(not isinstance(item, ExecutorDispatchCandidate) for item in candidates):
            raise ContinuityStateValidationError(
                "ExecutorDispatchRequest.candidates must contain ExecutorDispatchCandidate values"
            )
        actor_ids = [item.executor_id for item in candidates]
        if len(actor_ids) != len(set(actor_ids)):
            raise ContinuityStateValidationError("Duplicate Executor dispatch candidate actor IDs")
        object.__setattr__(
            self, "candidates", tuple(sorted(candidates, key=lambda item: item.executor_id))
        )

        raw_required = _normalize_iterable(
            self.required_capabilities, "ExecutorDispatchRequest.required_capabilities"
        )
        parsed_required = tuple(
            _parse_enum(item, ExecutionCapability, "ExecutorDispatchRequest.required_capabilities")
            for item in raw_required
        )
        if len(parsed_required) != len(set(parsed_required)):
            raise ContinuityStateValidationError("Duplicate required Executor capabilities")
        object.__setattr__(
            self,
            "required_capabilities",
            tuple(sorted(parsed_required, key=lambda item: item.value)),
        )
        _validate_serialized_size(self.to_dict(), "ExecutorDispatchRequest")

    def to_dict(self) -> dict[str, Any]:
        return {
            "allow_paid_api": self.allow_paid_api,
            "candidates": [
                item.to_dict() for item in sorted(self.candidates, key=lambda item: item.executor_id)
            ],
            "operation": self.operation.value,
            "required_capabilities": [item.value for item in self.required_capabilities],
            "schema_version": self.schema_version,
        }

    def to_canonical_json(self) -> str:
        return _canonical_json(self.to_dict())

    def fingerprint(self) -> str:
        return hashlib.sha256(self.to_canonical_json().encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CandidateEvaluation:
    actor_id: str
    compatible: bool
    runnable: bool
    reasons: tuple[CandidateReason, ...]
    capacity_class: CapacityClass
    capacity_state: CapacityState
    preference_rank: int

    def __post_init__(self) -> None:
        _validate_canonical_actor_id(self.actor_id, "CandidateEvaluation.actor_id")
        if type(self.compatible) is not bool or type(self.runnable) is not bool:
            raise ContinuityStateValidationError("CandidateEvaluation flags must be exact bool")
        if self.runnable and not self.compatible:
            raise ContinuityStateValidationError("Runnable candidate evaluation must be compatible")
        object.__setattr__(
            self,
            "capacity_class",
            _parse_enum(self.capacity_class, CapacityClass, "CandidateEvaluation.capacity_class"),
        )
        object.__setattr__(
            self,
            "capacity_state",
            _parse_enum(self.capacity_state, CapacityState, "CandidateEvaluation.capacity_state"),
        )
        _validate_preference_rank(self.preference_rank, "CandidateEvaluation.preference_rank")
        raw_reasons = _normalize_iterable(self.reasons, "CandidateEvaluation.reasons")
        parsed = tuple(
            _parse_enum(reason, CandidateReason, "CandidateEvaluation.reasons")
            for reason in raw_reasons
        )
        if not parsed or len(parsed) != len(set(parsed)):
            raise ContinuityStateValidationError("CandidateEvaluation reasons must be non-empty and unique")
        if CandidateReason.ELIGIBLE in parsed and len(parsed) != 1:
            raise ContinuityStateValidationError("ELIGIBLE must be the only candidate reason")
        object.__setattr__(self, "reasons", tuple(sorted(parsed, key=lambda item: item.value)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "actor_id": self.actor_id,
            "capacity_class": self.capacity_class.value,
            "capacity_state": self.capacity_state.value,
            "compatible": self.compatible,
            "preference_rank": self.preference_rank,
            "reasons": [reason.value for reason in self.reasons],
            "runnable": self.runnable,
        }


@dataclass(frozen=True)
class DispatchResult:
    actor_kind: DispatchActorKind
    status: DispatchStatus
    selected_actor_id: str | None
    reason: DispatchReason
    request_fingerprint: str
    evaluations: tuple[CandidateEvaluation, ...]
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ContinuityStateValidationError("Unsupported DispatchResult schema_version")
        object.__setattr__(
            self, "actor_kind", _parse_enum(self.actor_kind, DispatchActorKind, "DispatchResult.actor_kind")
        )
        object.__setattr__(
            self, "status", _parse_enum(self.status, DispatchStatus, "DispatchResult.status")
        )
        object.__setattr__(
            self, "reason", _parse_enum(self.reason, DispatchReason, "DispatchResult.reason")
        )
        if (
            not isinstance(self.request_fingerprint, str)
            or len(self.request_fingerprint) != 64
            or any(char not in "0123456789abcdef" for char in self.request_fingerprint)
        ):
            raise ContinuityStateValidationError("request_fingerprint must be exact lowercase 64-hex")
        evaluations = _normalize_iterable(self.evaluations, "DispatchResult.evaluations")
        if not evaluations or any(not isinstance(item, CandidateEvaluation) for item in evaluations):
            raise ContinuityStateValidationError(
                "DispatchResult.evaluations must contain CandidateEvaluation values"
            )
        actor_ids = [item.actor_id for item in evaluations]
        if len(actor_ids) != len(set(actor_ids)):
            raise ContinuityStateValidationError("Duplicate DispatchResult evaluation actor IDs")
        object.__setattr__(
            self, "evaluations", tuple(sorted(evaluations, key=lambda item: item.actor_id))
        )
        expected_reason = {
            DispatchStatus.SELECTED: DispatchReason.SELECTED_COMPATIBLE_AVAILABLE,
            DispatchStatus.WAIT: DispatchReason.WAIT_CAPACITY,
            DispatchStatus.NO_COMPATIBLE_CANDIDATE: DispatchReason.NO_COMPATIBLE_CANDIDATE,
        }[self.status]
        if self.reason is not expected_reason:
            raise ContinuityStateValidationError("DispatchResult reason does not match status")
        if self.status is DispatchStatus.SELECTED:
            if not isinstance(self.selected_actor_id, str):
                raise ContinuityStateValidationError("SELECTED result requires selected_actor_id")
            _validate_canonical_actor_id(self.selected_actor_id, "DispatchResult.selected_actor_id")
            selected = [item for item in evaluations if item.actor_id == self.selected_actor_id]
            if len(selected) != 1 or not selected[0].compatible or not selected[0].runnable:
                raise ContinuityStateValidationError(
                    "selected_actor_id must match one compatible runnable evaluation"
                )
        elif self.selected_actor_id is not None:
            raise ContinuityStateValidationError("Non-SELECTED result must not select an actor")
        _validate_serialized_size(self.to_dict(), "DispatchResult")

    def to_dict(self) -> dict[str, Any]:
        return {
            "actor_kind": self.actor_kind.value,
            "evaluations": [item.to_dict() for item in self.evaluations],
            "reason": self.reason.value,
            "request_fingerprint": self.request_fingerprint,
            "schema_version": self.schema_version,
            "selected_actor_id": self.selected_actor_id,
            "status": self.status.value,
        }

    def to_canonical_json(self) -> str:
        return _canonical_json(self.to_dict())

    def fingerprint(self) -> str:
        return hashlib.sha256(self.to_canonical_json().encode("utf-8")).hexdigest()


def _capacity_evidence(state: CapacityState) -> tuple[bool, tuple[CandidateReason, ...]]:
    if state is CapacityState.AVAILABLE:
        return True, (CandidateReason.ELIGIBLE,)
    if state is CapacityState.LIMITED:
        return True, (CandidateReason.CAPACITY_LIMITED,)
    return False, (_CAPACITY_REASON[state],)


def _build_result(
    actor_kind: DispatchActorKind,
    request_fingerprint: str,
    evaluations: tuple[CandidateEvaluation, ...],
) -> DispatchResult:
    runnable = [item for item in evaluations if item.compatible and item.runnable]
    if runnable:
        selected = min(
            runnable,
            key=lambda item: (
                _CAPACITY_CLASS_RANK[item.capacity_class],
                _CAPACITY_STATE_RUNNABLE_RANK[item.capacity_state],
                item.preference_rank,
                item.actor_id,
            ),
        )
        status = DispatchStatus.SELECTED
        reason = DispatchReason.SELECTED_COMPATIBLE_AVAILABLE
        selected_actor_id = selected.actor_id
    elif any(item.compatible for item in evaluations):
        status = DispatchStatus.WAIT
        reason = DispatchReason.WAIT_CAPACITY
        selected_actor_id = None
    else:
        status = DispatchStatus.NO_COMPATIBLE_CANDIDATE
        reason = DispatchReason.NO_COMPATIBLE_CANDIDATE
        selected_actor_id = None
    return DispatchResult(
        actor_kind=actor_kind,
        status=status,
        selected_actor_id=selected_actor_id,
        reason=reason,
        request_fingerprint=request_fingerprint,
        evaluations=evaluations,
    )


def dispatch_brain(request: BrainDispatchRequest) -> DispatchResult:
    if not isinstance(request, BrainDispatchRequest):
        raise ContinuityStateValidationError("dispatch_brain requires BrainDispatchRequest")
    evaluations = []
    for candidate in request.candidates:
        incompatibilities = []
        if request.operation not in candidate.capability.supported_operations:
            incompatibilities.append(CandidateReason.OPERATION_UNSUPPORTED)
        if (
            request.required_context_bytes is not None
            and candidate.capability.max_context_bytes is not None
            and candidate.capability.max_context_bytes < request.required_context_bytes
        ):
            incompatibilities.append(CandidateReason.CONTEXT_TOO_LARGE)
        if candidate.capacity_class is CapacityClass.PAID_API and not request.allow_paid_api:
            incompatibilities.append(CandidateReason.PAID_API_NOT_ALLOWED)
        compatible = not incompatibilities
        runnable, capacity_reasons = _capacity_evidence(candidate.capacity_state)
        evaluations.append(
            CandidateEvaluation(
                actor_id=candidate.brain_id,
                compatible=compatible,
                runnable=compatible and runnable,
                reasons=capacity_reasons if compatible else tuple(incompatibilities),
                capacity_class=candidate.capacity_class,
                capacity_state=candidate.capacity_state,
                preference_rank=candidate.preference_rank,
            )
        )
    return _build_result(
        DispatchActorKind.BRAIN,
        request.fingerprint(),
        tuple(evaluations),
    )


def dispatch_executor(request: ExecutorDispatchRequest) -> DispatchResult:
    if not isinstance(request, ExecutorDispatchRequest):
        raise ContinuityStateValidationError("dispatch_executor requires ExecutorDispatchRequest")
    evaluations = []
    required = set(request.required_capabilities)
    for candidate in request.candidates:
        incompatibilities = []
        if request.operation not in candidate.capabilities.supported_operations:
            incompatibilities.append(CandidateReason.OPERATION_UNSUPPORTED)
        if not required.issubset(set(candidate.capabilities.supported_capabilities)):
            incompatibilities.append(CandidateReason.REQUIRED_CAPABILITY_MISSING)
        if candidate.capacity_class is CapacityClass.PAID_API and not request.allow_paid_api:
            incompatibilities.append(CandidateReason.PAID_API_NOT_ALLOWED)
        compatible = not incompatibilities
        runnable, capacity_reasons = _capacity_evidence(candidate.capacity_state)
        evaluations.append(
            CandidateEvaluation(
                actor_id=candidate.executor_id,
                compatible=compatible,
                runnable=compatible and runnable,
                reasons=capacity_reasons if compatible else tuple(incompatibilities),
                capacity_class=candidate.capacity_class,
                capacity_state=candidate.capacity_state,
                preference_rank=candidate.preference_rank,
            )
        )
    return _build_result(
        DispatchActorKind.EXECUTOR,
        request.fingerprint(),
        tuple(evaluations),
    )


__all__ = [
    "BrainDispatchCandidate",
    "BrainDispatchRequest",
    "CandidateEvaluation",
    "CandidateReason",
    "CapacityClass",
    "CapacityState",
    "DispatchActorKind",
    "DispatchReason",
    "DispatchResult",
    "DispatchStatus",
    "ExecutorDispatchCandidate",
    "ExecutorDispatchRequest",
    "dispatch_brain",
    "dispatch_executor",
]
