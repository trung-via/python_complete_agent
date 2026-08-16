"""
Brain Failover Contract & Proof Harness for Open Multi-Agent Continuity OS (ADR-010 / ADR-016 Milestone 3A).
Provides pure, deterministic, and state-anchored rules for neutral Brain failover.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Sequence

from .brain import (
    BrainCapability,
    BrainOperation,
    BrainRequest,
    BrainResult,
    BrainResultStatus,
    _validate_request_id,
    _validate_task_id,
)
from .errors import ContinuityStateValidationError
from .state import (
    MAX_SERIALIZED_BYTES,
    SCHEMA_VERSION,
    ContinuityState,
    _validate_actor_id,
)

_FINGERPRINT_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _validate_hex_fingerprint(fp: Any, field_name: str) -> str:
    """Validates exact lowercase 64-character SHA-256 hex string with zero whitespace tolerance."""
    if isinstance(fp, bool) or not isinstance(fp, str):
        raise ContinuityStateValidationError(f"{field_name} must be a non-empty string")
    if fp != fp.strip() or not fp:
        raise ContinuityStateValidationError(
            f"{field_name} must not contain leading or trailing whitespace: {fp!r}"
        )
    if not _FINGERPRINT_PATTERN.match(fp):
        raise ContinuityStateValidationError(
            f"{field_name} must be an exact 64-character lowercase hex SHA-256 string, got: {fp!r}"
        )
    return fp


def _validate_canonical_actor_id(actor_id: Any, field_name: str) -> str:
    """Validates exact canonical actor ID with zero whitespace padding."""
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


def _validate_canonical_request_id(request_id: Any, field_name: str) -> str:
    """Validates exact canonical request ID with zero whitespace padding."""
    if isinstance(request_id, bool) or not isinstance(request_id, str):
        raise ContinuityStateValidationError(f"{field_name} must be a non-empty string")
    if request_id != request_id.strip() or not request_id:
        raise ContinuityStateValidationError(
            f"{field_name} must not contain leading or trailing whitespace: {request_id!r}"
        )
    canonical = _validate_request_id(request_id, field_name)
    if request_id != canonical:
        raise ContinuityStateValidationError(
            f"{field_name} must be exact canonical request ID, got: {request_id!r}"
        )
    return canonical


@dataclass(frozen=True)
class BrainFailoverProof:
    """
    Deterministic audit record proving a valid, semantically equivalent Brain failover handoff.
    Bound to a specific ContinuityState snapshot fingerprint and source/replacement request fingerprints.
    """
    task_id: str
    operation: BrainOperation
    state_fingerprint: str
    source_brain_id: str
    source_request_id: str
    source_request_fingerprint: str
    replacement_brain_id: str
    replacement_request_id: str
    replacement_request_fingerprint: str
    source_result_status: BrainResultStatus | None = None
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ContinuityStateValidationError(
                f"Unsupported schema_version: {self.schema_version!r} (expected {SCHEMA_VERSION!r})"
            )

        _validate_task_id(self.task_id, "BrainFailoverProof.task_id")

        if not isinstance(self.operation, BrainOperation):
            try:
                object.__setattr__(self, "operation", BrainOperation(self.operation))
            except Exception as e:
                valid_ops = ", ".join(o.value for o in BrainOperation)
                raise ContinuityStateValidationError(
                    f"Invalid BrainOperation: {self.operation!r}. Valid values: {valid_ops}"
                ) from e

        canon_state_fp = _validate_hex_fingerprint(self.state_fingerprint, "BrainFailoverProof.state_fingerprint")
        canon_source_brain = _validate_canonical_actor_id(self.source_brain_id, "BrainFailoverProof.source_brain_id")
        canon_source_req_id = _validate_canonical_request_id(self.source_request_id, "BrainFailoverProof.source_request_id")
        canon_source_req_fp = _validate_hex_fingerprint(self.source_request_fingerprint, "BrainFailoverProof.source_request_fingerprint")

        canon_rep_brain = _validate_canonical_actor_id(self.replacement_brain_id, "BrainFailoverProof.replacement_brain_id")
        canon_rep_req_id = _validate_canonical_request_id(self.replacement_request_id, "BrainFailoverProof.replacement_request_id")
        canon_rep_req_fp = _validate_hex_fingerprint(
            self.replacement_request_fingerprint,
            "BrainFailoverProof.replacement_request_fingerprint",
        )

        object.__setattr__(self, "state_fingerprint", canon_state_fp)
        object.__setattr__(self, "source_brain_id", canon_source_brain)
        object.__setattr__(self, "source_request_id", canon_source_req_id)
        object.__setattr__(self, "source_request_fingerprint", canon_source_req_fp)
        object.__setattr__(self, "replacement_brain_id", canon_rep_brain)
        object.__setattr__(self, "replacement_request_id", canon_rep_req_id)
        object.__setattr__(self, "replacement_request_fingerprint", canon_rep_req_fp)

        if canon_source_brain == canon_rep_brain:
            raise ContinuityStateValidationError(
                f"Same-Brain pseudo-failover rejected: source and replacement brain_id are identical ('{canon_source_brain}')"
            )

        if self.source_result_status is not None:
            if not isinstance(self.source_result_status, BrainResultStatus):
                try:
                    object.__setattr__(self, "source_result_status", BrainResultStatus(self.source_result_status))
                except Exception as e:
                    valid_statuses = ", ".join(s.value for s in BrainResultStatus)
                    raise ContinuityStateValidationError(
                        f"Invalid BrainResultStatus: {self.source_result_status!r}. Valid values: {valid_statuses}"
                    ) from e

            if self.source_result_status == BrainResultStatus.SUCCESS:
                raise ContinuityStateValidationError(
                    "BrainFailoverProof cannot record a failover for a SUCCESS source result: duplicate outputs forbidden"
                )

        # Enforce 16 KiB size limit fail-closed
        raw_canonical = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        utf8_bytes = raw_canonical.encode("utf-8")
        if len(utf8_bytes) > MAX_SERIALIZED_BYTES:
            raise ContinuityStateValidationError(
                f"Serialized BrainFailoverProof size ({len(utf8_bytes)} bytes) exceeds MAX_SERIALIZED_BYTES limit ({MAX_SERIALIZED_BYTES})"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation.value,
            "replacement_brain_id": self.replacement_brain_id,
            "replacement_request_fingerprint": self.replacement_request_fingerprint,
            "replacement_request_id": self.replacement_request_id,
            "schema_version": self.schema_version,
            "source_brain_id": self.source_brain_id,
            "source_request_fingerprint": self.source_request_fingerprint,
            "source_request_id": self.source_request_id,
            "source_result_status": self.source_result_status.value if self.source_result_status is not None else None,
            "state_fingerprint": self.state_fingerprint,
            "task_id": self.task_id,
        }

    def to_canonical_json(self) -> str:
        data = self.to_dict()
        canonical_str = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        utf8_bytes = canonical_str.encode("utf-8")
        if len(utf8_bytes) > MAX_SERIALIZED_BYTES:
            raise ContinuityStateValidationError(
                f"Serialized BrainFailoverProof size ({len(utf8_bytes)} bytes) exceeds MAX_SERIALIZED_BYTES limit ({MAX_SERIALIZED_BYTES})"
            )
        return canonical_str

    def fingerprint(self) -> str:
        canonical_str = self.to_canonical_json()
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    @classmethod
    def from_dict(cls, data: Any) -> BrainFailoverProof:
        if not isinstance(data, dict):
            raise ContinuityStateValidationError(f"BrainFailoverProof root must be a dict, got: {type(data).__name__}")

        allowed_root_keys = {
            "operation",
            "replacement_brain_id",
            "replacement_request_fingerprint",
            "replacement_request_id",
            "schema_version",
            "source_brain_id",
            "source_request_fingerprint",
            "source_request_id",
            "source_result_status",
            "state_fingerprint",
            "task_id",
        }
        extra_keys = set(data.keys()) - allowed_root_keys
        if extra_keys:
            raise ContinuityStateValidationError(f"Unknown root fields in BrainFailoverProof: {sorted(extra_keys)}")

        for req in (
            "operation",
            "replacement_brain_id",
            "replacement_request_fingerprint",
            "replacement_request_id",
            "schema_version",
            "source_brain_id",
            "source_request_fingerprint",
            "source_request_id",
            "state_fingerprint",
            "task_id",
        ):
            if req not in data:
                raise ContinuityStateValidationError(f"Missing required field '{req}' in BrainFailoverProof")

        if data["schema_version"] != SCHEMA_VERSION:
            raise ContinuityStateValidationError(
                f"Unsupported schema_version: {data['schema_version']!r} (expected {SCHEMA_VERSION!r})"
            )

        return cls(
            task_id=data["task_id"],
            operation=data["operation"],
            state_fingerprint=data["state_fingerprint"],
            source_brain_id=data["source_brain_id"],
            source_request_id=data["source_request_id"],
            source_request_fingerprint=data["source_request_fingerprint"],
            replacement_brain_id=data["replacement_brain_id"],
            replacement_request_id=data["replacement_request_id"],
            replacement_request_fingerprint=data["replacement_request_fingerprint"],
            source_result_status=data.get("source_result_status"),
            schema_version=data["schema_version"],
        )

    @classmethod
    def from_json(cls, text: str | bytes) -> BrainFailoverProof:
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


def build_replacement_brain_request(
    source_request: BrainRequest,
    replacement_brain_id: str,
    replacement_request_id: str,
) -> BrainRequest:
    """
    Pure constructor helper that derives a semantically equivalent replacement BrainRequest
    for a new Brain identity, preserving all objective, context_refs, output_contract, and task identity.
    """
    if not isinstance(source_request, BrainRequest):
        raise ContinuityStateValidationError(
            f"source_request must be a BrainRequest, got: {type(source_request).__name__}"
        )

    canon_source_brain = _validate_canonical_actor_id(source_request.brain_id, "source_request.brain_id")
    canon_rep_brain = _validate_canonical_actor_id(replacement_brain_id, "replacement_brain_id")
    canon_rep_req_id = _validate_canonical_request_id(replacement_request_id, "replacement_request_id")

    if canon_source_brain == canon_rep_brain:
        raise ContinuityStateValidationError(
            f"Same-Brain pseudo-failover rejected: replacement_brain_id '{canon_rep_brain}' "
            f"must differ from source_request.brain_id '{canon_source_brain}'"
        )

    return BrainRequest(
        task_id=source_request.task_id,
        request_id=canon_rep_req_id,
        brain_id=canon_rep_brain,
        operation=source_request.operation,
        objective=source_request.objective,
        output_contract=source_request.output_contract,
        context_refs=source_request.context_refs,
        schema_version=source_request.schema_version,
    )


def validate_brain_failover_eligibility(
    source_request: BrainRequest,
    replacement_request: BrainRequest,
    state: ContinuityState,
    expected_state_fingerprint: str,
    replacement_capability: BrainCapability,
    source_result: BrainResult | None = None,
) -> BrainFailoverProof:
    """
    Validates pure mathematical and state-anchored failover eligibility between two BrainRequests.
    Returns an immutable BrainFailoverProof record on success. Fails closed on any discrepancy.
    Requires caller-supplied expected_state_fingerprint and replacement_capability.
    """
    if not isinstance(source_request, BrainRequest):
        raise ContinuityStateValidationError(
            f"source_request must be a BrainRequest, got: {type(source_request).__name__}"
        )
    if not isinstance(replacement_request, BrainRequest):
        raise ContinuityStateValidationError(
            f"replacement_request must be a BrainRequest, got: {type(replacement_request).__name__}"
        )
    if not isinstance(state, ContinuityState):
        raise ContinuityStateValidationError(
            f"state must be a ContinuityState, got: {type(state).__name__}"
        )

    # 1. State Anchor Validation (Mandatory)
    canon_expected_fp = _validate_hex_fingerprint(expected_state_fingerprint, "expected_state_fingerprint")
    if state.task_id != source_request.task_id:
        raise ContinuityStateValidationError(
            f"State task_id mismatch: state.task_id '{state.task_id}' != source_request.task_id '{source_request.task_id}'"
        )
    if state.task_id != replacement_request.task_id:
        raise ContinuityStateValidationError(
            f"State task_id mismatch: state.task_id '{state.task_id}' != replacement_request.task_id '{replacement_request.task_id}'"
        )

    actual_state_fingerprint = state.fingerprint()
    if canon_expected_fp != actual_state_fingerprint:
        raise ContinuityStateValidationError(
            f"State fingerprint mismatch: expected '{canon_expected_fp}', actual '{actual_state_fingerprint}'"
        )

    # 2. Semantic Equivalence Validation
    if source_request.task_id != replacement_request.task_id:
        raise ContinuityStateValidationError(
            f"Task ID drift in failover: source '{source_request.task_id}' != replacement '{replacement_request.task_id}'"
        )
    if source_request.operation != replacement_request.operation:
        raise ContinuityStateValidationError(
            f"Operation drift in failover: source '{source_request.operation.value}' != replacement '{replacement_request.operation.value}'"
        )
    if source_request.objective != replacement_request.objective:
        raise ContinuityStateValidationError("Objective drift in failover: source and replacement objectives differ")
    if source_request.output_contract != replacement_request.output_contract:
        raise ContinuityStateValidationError("OutputContract drift in failover: output contracts differ")
    if source_request.context_refs != replacement_request.context_refs:
        raise ContinuityStateValidationError("ContextRefs drift in failover: context references differ or reordered")
    if source_request.schema_version != replacement_request.schema_version:
        raise ContinuityStateValidationError("Schema version drift in failover")

    canon_source_brain = _validate_canonical_actor_id(source_request.brain_id, "source_request.brain_id")
    canon_rep_brain = _validate_canonical_actor_id(replacement_request.brain_id, "replacement_request.brain_id")

    if canon_source_brain == canon_rep_brain:
        raise ContinuityStateValidationError(
            f"Same-Brain pseudo-failover rejected: source and replacement brain_id are identical ('{canon_source_brain}')"
        )

    # 3. Replacement Capability Validation (Mandatory Gate)
    if not isinstance(replacement_capability, BrainCapability):
        raise ContinuityStateValidationError(
            f"replacement_capability must be a BrainCapability, got: {type(replacement_capability).__name__}"
        )
    canon_cap_brain = _validate_canonical_actor_id(replacement_capability.brain_id, "replacement_capability.brain_id")
    if canon_cap_brain != canon_rep_brain:
        raise ContinuityStateValidationError(
            f"Replacement capability brain_id mismatch: capability '{canon_cap_brain}' "
            f"!= replacement_request '{canon_rep_brain}'"
        )
    if replacement_request.operation not in replacement_capability.supported_operations:
        raise ContinuityStateValidationError(
            f"Replacement brain '{canon_cap_brain}' does not support operation '{replacement_request.operation.value}'"
        )
    if not replacement_capability.declarative_only:
        raise ContinuityStateValidationError("Replacement capability declarative_only must be True")

    # 4. Source Result Validation (if provided)
    source_status: BrainResultStatus | None = None
    if source_result is not None:
        if not isinstance(source_result, BrainResult):
            raise ContinuityStateValidationError(
                f"source_result must be a BrainResult, got: {type(source_result).__name__}"
            )
        if source_result.task_id != source_request.task_id:
            raise ContinuityStateValidationError(
                f"Source result task_id mismatch: '{source_result.task_id}' != '{source_request.task_id}'"
            )
        if source_result.request_id != source_request.request_id:
            raise ContinuityStateValidationError(
                f"Source result request_id mismatch: '{source_result.request_id}' != '{source_request.request_id}'"
            )
        if source_result.brain_id != source_request.brain_id:
            raise ContinuityStateValidationError(
                f"Source result brain_id mismatch: '{source_result.brain_id}' != '{source_request.brain_id}'"
            )
        if source_result.operation != source_request.operation:
            raise ContinuityStateValidationError(
                f"Source result operation mismatch: '{source_result.operation.value}' != '{source_request.operation.value}'"
            )

        if source_result.status == BrainResultStatus.SUCCESS:
            raise ContinuityStateValidationError(
                "Cannot fail over operation: source request already succeeded with status SUCCESS (duplicate outputs forbidden)"
            )
        source_status = source_result.status

    # 5. Construct and return verified BrainFailoverProof
    return BrainFailoverProof(
        task_id=source_request.task_id,
        operation=source_request.operation,
        state_fingerprint=actual_state_fingerprint,
        source_brain_id=canon_source_brain,
        source_request_id=source_request.request_id,
        source_request_fingerprint=source_request.fingerprint(),
        replacement_brain_id=canon_rep_brain,
        replacement_request_id=replacement_request.request_id,
        replacement_request_fingerprint=replacement_request.fingerprint(),
        source_result_status=source_status,
        schema_version=source_request.schema_version,
    )
