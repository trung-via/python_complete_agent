"""Offline correlation proof for one completed paid API Brain escape.

The verifier in this module consumes only already-produced immutable evidence
and read-only durable grant state.  It performs no counting, dispatch,
provider invocation, ledger write, credential lookup, or wall-clock lookup.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any

from .continuity.dispatch import (
    BrainDispatchRequest,
    CapacityClass,
    DispatchActorKind,
    DispatchStatus,
)
from .continuity.errors import ContinuityStateValidationError
from .continuity.state import BrainOperation as ContinuityBrainOperation
from .external_brain.contracts import (
    BrainOperation as ExternalBrainOperation,
    BrainOutputType,
    ModelRequest,
    ModelResponse,
    ModelResponseStatus,
    get_expected_output_type,
)
from .external_brain.gateway import GatewayResult
from .external_brain.usage import UsageRecord
from .paid_api_brain_escape import PaidApiBrainEscapeResult
from .paid_api_grant import PaidApiGrant
from .provider_input_budget import (
    ProviderInputCountEvidence,
    fingerprint_model_request,
)
from .runtime_paid_api_grant import AtomicPaidApiGrantStore


_SCHEMA_VERSION = "1"
_TASK_ID_PATTERN = re.compile(r"TASK-[0-9]+")
_LOWERCASE_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_GIT_BLOB_SHA_PATTERN = re.compile(r"[0-9a-f]{40}")
_MAX_IDENTIFIER_LENGTH = 512
_MAX_ARTIFACT_PATH_LENGTH = 4096

_OPERATION_MAP: dict[ContinuityBrainOperation, ExternalBrainOperation] = {
    ContinuityBrainOperation.PLAN: ExternalBrainOperation.PLAN,
    ContinuityBrainOperation.DIAGNOSIS: ExternalBrainOperation.DIAGNOSE_FAILURE,
    ContinuityBrainOperation.PATCH_PROPOSAL: ExternalBrainOperation.GENERATE_PATCH,
    ContinuityBrainOperation.REVIEW: ExternalBrainOperation.REVIEW_PATCH,
}


class PaidApiOperationalProofError(ValueError):
    """Raised when completed paid API evidence cannot be proven exactly."""


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise PaidApiOperationalProofError(message)


def _require_exact_string(
    value: object,
    field_name: str,
    *,
    maximum_length: int = _MAX_IDENTIFIER_LENGTH,
) -> str:
    if (
        type(value) is not str
        or not value
        or value != value.strip()
        or len(value) > maximum_length
        or not all(character.isprintable() for character in value)
    ):
        raise PaidApiOperationalProofError(
            f"{field_name} must be an exact bounded non-empty unpadded string"
        )
    return value


def _require_exact_non_negative_int(value: object, field_name: str) -> int:
    if type(value) is not int or value < 0:
        raise PaidApiOperationalProofError(
            f"{field_name} must be an exact non-negative integer"
        )
    return value


def _require_response_content(value: object) -> str:
    if (
        type(value) is not str
        or not value.strip()
        or len(value) > 16 * 1024 * 1024
    ):
        raise PaidApiOperationalProofError(
            "response.content must be an exact bounded non-empty string"
        )
    return value


def _require_lowercase_sha256(value: object, field_name: str) -> str:
    if type(value) is not str or _LOWERCASE_SHA256_PATTERN.fullmatch(value) is None:
        raise PaidApiOperationalProofError(
            f"{field_name} must be an exact lowercase SHA-256"
        )
    return value


def _require_artifact_path(value: object) -> str:
    path = _require_exact_string(
        value,
        "authorized_artifact_path",
        maximum_length=_MAX_ARTIFACT_PATH_LENGTH,
    )
    components = path.split("/")
    if (
        not path.startswith(".ai/")
        or "\\" in path
        or ":" in path
        or path.startswith("/")
        or any(component in ("", ".", "..") for component in components)
    ):
        raise PaidApiOperationalProofError(
            "authorized_artifact_path must be a canonical .ai/ repository path"
        )
    return path


@dataclass(frozen=True)
class PaidApiOperationalProofReceipt:
    """Bounded immutable receipt for an exactly correlated paid Brain call."""

    schema_version: str
    task_id: str
    grant_id: str
    grant_fingerprint: str
    brain_id: str
    provider_id: str
    model_id: str
    request_id: str
    model_request_fingerprint: str
    authorized_artifact_path: str
    authorized_artifact_blob_sha: str
    counter_id: str
    local_pre_call_input_tokens: int
    provider_reported_input_tokens: int
    provider_reported_output_tokens: int
    provider_request_id: str
    response_status: ModelResponseStatus
    ledger_persisted: bool
    grant_consumed: bool
    input_token_match: bool
    response_content_sha256: str

    def __post_init__(self) -> None:
        if type(self.schema_version) is not str or self.schema_version != _SCHEMA_VERSION:
            raise PaidApiOperationalProofError("unsupported receipt schema_version")
        task_id = _require_exact_string(self.task_id, "task_id")
        if _TASK_ID_PATTERN.fullmatch(task_id) is None:
            raise PaidApiOperationalProofError("task_id is invalid")
        _require_exact_string(self.grant_id, "grant_id")
        _require_lowercase_sha256(self.grant_fingerprint, "grant_fingerprint")
        _require_exact_string(self.brain_id, "brain_id")
        _require_exact_string(self.provider_id, "provider_id")
        _require_exact_string(self.model_id, "model_id")
        _require_exact_string(self.request_id, "request_id")
        _require_lowercase_sha256(
            self.model_request_fingerprint,
            "model_request_fingerprint",
        )
        _require_artifact_path(self.authorized_artifact_path)
        if (
            type(self.authorized_artifact_blob_sha) is not str
            or _GIT_BLOB_SHA_PATTERN.fullmatch(
                self.authorized_artifact_blob_sha
            )
            is None
        ):
            raise PaidApiOperationalProofError(
                "authorized_artifact_blob_sha must be an exact lowercase Git blob SHA"
            )
        _require_exact_string(self.counter_id, "counter_id")
        local_input = _require_exact_non_negative_int(
            self.local_pre_call_input_tokens,
            "local_pre_call_input_tokens",
        )
        provider_input = _require_exact_non_negative_int(
            self.provider_reported_input_tokens,
            "provider_reported_input_tokens",
        )
        _require_exact_non_negative_int(
            self.provider_reported_output_tokens,
            "provider_reported_output_tokens",
        )
        _require_exact_string(self.provider_request_id, "provider_request_id")
        if type(self.response_status) is not ModelResponseStatus:
            raise PaidApiOperationalProofError(
                "response_status must be an exact ModelResponseStatus"
            )
        if self.response_status is not ModelResponseStatus.SUCCESS:
            raise PaidApiOperationalProofError("response_status must be SUCCESS")
        for field_name in (
            "ledger_persisted",
            "grant_consumed",
            "input_token_match",
        ):
            if type(getattr(self, field_name)) is not bool:
                raise PaidApiOperationalProofError(f"{field_name} must be an exact bool")
            if getattr(self, field_name) is not True:
                raise PaidApiOperationalProofError(f"{field_name} must be exactly True")
        if local_input != provider_input:
            raise PaidApiOperationalProofError(
                "receipt local and provider input token counts must exactly match"
            )
        _require_lowercase_sha256(
            self.response_content_sha256,
            "response_content_sha256",
        )

    def to_dict(self) -> dict[str, Any]:
        """Return only the bounded receipt semantic fields."""

        return {
            "authorized_artifact_blob_sha": self.authorized_artifact_blob_sha,
            "authorized_artifact_path": self.authorized_artifact_path,
            "brain_id": self.brain_id,
            "counter_id": self.counter_id,
            "grant_consumed": self.grant_consumed,
            "grant_fingerprint": self.grant_fingerprint,
            "grant_id": self.grant_id,
            "input_token_match": self.input_token_match,
            "ledger_persisted": self.ledger_persisted,
            "local_pre_call_input_tokens": self.local_pre_call_input_tokens,
            "model_id": self.model_id,
            "model_request_fingerprint": self.model_request_fingerprint,
            "provider_id": self.provider_id,
            "provider_reported_input_tokens": self.provider_reported_input_tokens,
            "provider_reported_output_tokens": self.provider_reported_output_tokens,
            "provider_request_id": self.provider_request_id,
            "request_id": self.request_id,
            "response_content_sha256": self.response_content_sha256,
            "response_status": self.response_status.value,
            "schema_version": self.schema_version,
            "task_id": self.task_id,
        }

    def to_canonical_json(self) -> str:
        """Serialize receipt semantics deterministically using UTF-8 JSON rules."""

        return _canonical_json(self.to_dict())

    def fingerprint(self) -> str:
        """Return the deterministic SHA-256 of canonical receipt semantics."""

        return hashlib.sha256(self.to_canonical_json().encode("utf-8")).hexdigest()


def _require_exact_inputs(
    *,
    escape_result: object,
    grant: object,
    grant_store: object,
    model_request: object,
) -> tuple[
    PaidApiBrainEscapeResult,
    PaidApiGrant,
    AtomicPaidApiGrantStore,
    ModelRequest,
]:
    exact_types = (
        (escape_result, PaidApiBrainEscapeResult, "escape_result"),
        (grant, PaidApiGrant, "grant"),
        (grant_store, AtomicPaidApiGrantStore, "grant_store"),
        (model_request, ModelRequest, "model_request"),
    )
    for value, expected_type, field_name in exact_types:
        if type(value) is not expected_type:
            raise PaidApiOperationalProofError(
                f"{field_name} must be an exact {expected_type.__name__}"
            )
    return escape_result, grant, grant_store, model_request


def build_paid_api_operational_proof(
    *,
    escape_result: PaidApiBrainEscapeResult,
    grant: PaidApiGrant,
    grant_store: AtomicPaidApiGrantStore,
    model_request: ModelRequest,
) -> PaidApiOperationalProofReceipt:
    """Verify completed paid-call evidence and return a bounded receipt.

    The two grant-store calls are read-only terminal-state observations.  This
    function deliberately has no counter, gateway, provider, ledger, clock,
    environment, credential, or retry parameter.
    """

    escape_result, grant, grant_store, model_request = _require_exact_inputs(
        escape_result=escape_result,
        grant=grant,
        grant_store=grant_store,
        model_request=model_request,
    )

    grant_fingerprint = _require_lowercase_sha256(
        grant.grant_fingerprint,
        "grant.grant_fingerprint",
    )
    _require(
        grant_fingerprint == grant.fingerprint(),
        "grant fingerprint does not exactly match grant semantics",
    )
    _require(
        grant_store.workspace_id == grant.workspace_id,
        "grant store workspace does not exactly match the grant",
    )

    effective_request = escape_result.effective_dispatch_request
    dispatch_result = escape_result.dispatch_result
    _require(
        type(effective_request) is BrainDispatchRequest,
        "effective dispatch request must be an exact BrainDispatchRequest",
    )
    _require(
        escape_result.paid_candidate_selected is True,
        "paid candidate selection is required",
    )
    _require(
        escape_result.grant_consumed is True,
        "grant_consumed must be exactly True",
    )
    _require(
        effective_request.allow_paid_api is True,
        "effective allow_paid_api must be exactly True",
    )
    _require(
        dispatch_result.status is DispatchStatus.SELECTED,
        "dispatch status must be SELECTED",
    )
    _require(
        dispatch_result.actor_kind is DispatchActorKind.BRAIN,
        "dispatch actor_kind must be BRAIN",
    )
    _require(
        dispatch_result.selected_actor_id == grant.brain_id,
        "selected Brain does not exactly match the grant",
    )
    selected_candidates = tuple(
        candidate
        for candidate in effective_request.candidates
        if candidate.brain_id == grant.brain_id
    )
    _require(
        len(selected_candidates) == 1
        and selected_candidates[0].capacity_class is CapacityClass.PAID_API,
        "selected granted Brain must be exactly one PAID_API candidate",
    )
    _require(
        dispatch_result.request_fingerprint == effective_request.fingerprint(),
        "dispatch result does not bind the effective dispatch request",
    )
    _require(
        effective_request.operation is grant.brain_operation,
        "effective Brain operation does not exactly match the grant",
    )
    expected_external_operation = _OPERATION_MAP.get(grant.brain_operation)
    _require(
        expected_external_operation is not None
        and model_request.operation is expected_external_operation,
        "ModelRequest operation does not exactly match the granted Brain operation",
    )

    try:
        active_grant = grant_store.load_active(grant.task_id, grant.grant_id)
        consumed_grant = grant_store.load_consumed(grant.task_id, grant.grant_id)
    except ContinuityStateValidationError as exc:
        raise PaidApiOperationalProofError(
            "durable grant terminal state could not be proven"
        ) from exc
    _require(active_grant is None, "paid API grant must not remain ACTIVE")
    _require(
        type(consumed_grant) is PaidApiGrant and consumed_grant == grant,
        "CONSUMED paid API grant must exactly match the supplied grant",
    )
    _require(
        consumed_grant.grant_fingerprint == grant_fingerprint
        and consumed_grant.fingerprint() == grant_fingerprint,
        "CONSUMED paid API grant fingerprint must exactly match",
    )

    request_id = _require_exact_string(model_request.request_id, "model_request.request_id")
    _require(
        type(model_request.task_id) is str and model_request.task_id == grant.task_id,
        "ModelRequest task_id does not exactly match the grant",
    )
    _require(
        type(model_request.provider) is str
        and model_request.provider == grant.provider_id,
        "ModelRequest provider does not exactly match the grant",
    )
    _require(
        type(model_request.model) is str and model_request.model == grant.model_id,
        "ModelRequest model does not exactly match the grant",
    )
    _require(
        type(model_request.max_input_tokens) is int
        and model_request.max_input_tokens > 0,
        "ModelRequest max_input_tokens must be an exact positive integer",
    )
    _require(
        type(model_request.max_output_tokens) is int
        and model_request.max_output_tokens > 0,
        "ModelRequest max_output_tokens must be an exact positive integer",
    )

    evidence = escape_result.provider_input_evidence
    _require(
        type(evidence) is ProviderInputCountEvidence,
        "provider_input_evidence must be exact original evidence",
    )
    model_request_fingerprint = fingerprint_model_request(model_request)
    _require(
        evidence.provider_id == grant.provider_id,
        "provider input evidence provider does not exactly match the grant",
    )
    _require(
        evidence.model_id == grant.model_id,
        "provider input evidence model does not exactly match the grant",
    )
    _require(
        evidence.model_request_fingerprint == model_request_fingerprint,
        "provider input evidence does not bind the exact ModelRequest",
    )
    _require(
        evidence.token_count_is_exact is True,
        "provider input evidence must be exactly counted",
    )
    counter_id = _require_exact_string(evidence.counter_id, "evidence.counter_id")
    local_input_tokens = _require_exact_non_negative_int(
        evidence.counted_input_tokens,
        "evidence.counted_input_tokens",
    )
    _require(
        local_input_tokens
        <= model_request.max_input_tokens
        <= grant.max_input_tokens,
        "local/request/grant input-token bounds are not satisfied",
    )
    _require(
        model_request.max_output_tokens <= grant.max_output_tokens,
        "request output-token bound exceeds the grant",
    )

    gateway_result = escape_result.gateway_result
    _require(
        type(gateway_result) is GatewayResult,
        "a successful exact GatewayResult is required",
    )
    response = gateway_result.response
    usage_record = gateway_result.usage_record
    _require(type(response) is ModelResponse, "response must be an exact ModelResponse")
    _require(type(usage_record) is UsageRecord, "usage_record must be an exact UsageRecord")
    _require(
        response.status is ModelResponseStatus.SUCCESS,
        "response status must be SUCCESS",
    )
    _require(
        type(response.request_id) is str and response.request_id == request_id,
        "response request_id does not exactly match ModelRequest",
    )
    _require(
        type(response.task_id) is str
        and response.task_id == model_request.task_id == grant.task_id,
        "response task_id correlation failed",
    )
    _require(
        type(response.provider) is str and response.provider == grant.provider_id,
        "response provider does not exactly match the grant",
    )
    _require(
        type(response.model) is str and response.model == grant.model_id,
        "response model does not exactly match the grant",
    )
    expected_output_type = get_expected_output_type(model_request.operation)
    _require(
        type(response.output_type) is BrainOutputType
        and response.output_type is expected_output_type,
        "response output_type does not exactly match ModelRequest.operation",
    )
    response_content = _require_response_content(response.content)
    provider_request_id = _require_exact_string(
        response.provider_request_id,
        "response.provider_request_id",
    )
    response_input_tokens = _require_exact_non_negative_int(
        response.input_tokens,
        "response.input_tokens",
    )
    response_output_tokens = _require_exact_non_negative_int(
        response.output_tokens,
        "response.output_tokens",
    )
    _require(
        response_output_tokens
        <= model_request.max_output_tokens
        <= grant.max_output_tokens,
        "response/request/grant output-token bounds are not satisfied",
    )

    _require(
        gateway_result.ledger_persisted is True,
        "usage ledger must be durably persisted",
    )
    _require(
        gateway_result.ledger_error_code is None,
        "usage ledger error code must be absent",
    )
    _require(
        type(usage_record.request_id) is str and usage_record.request_id == request_id,
        "usage request_id correlation failed",
    )
    _require(
        type(usage_record.task_id) is str and usage_record.task_id == grant.task_id,
        "usage task_id correlation failed",
    )
    _require(
        type(usage_record.provider) is str
        and usage_record.provider == grant.provider_id,
        "usage provider correlation failed",
    )
    _require(
        type(usage_record.requested_model) is str
        and usage_record.requested_model == model_request.model == grant.model_id,
        "usage requested_model correlation failed",
    )
    _require(
        type(usage_record.actual_model) is str
        and usage_record.actual_model == grant.model_id,
        "usage actual_model correlation failed",
    )
    _require(
        usage_record.status is ModelResponseStatus.SUCCESS
        and usage_record.status is response.status,
        "usage status correlation failed",
    )
    usage_input_tokens = _require_exact_non_negative_int(
        usage_record.provider_input_tokens,
        "usage.provider_input_tokens",
    )
    usage_output_tokens = _require_exact_non_negative_int(
        usage_record.provider_output_tokens,
        "usage.provider_output_tokens",
    )
    _require(
        type(usage_record.provider_request_id) is str
        and usage_record.provider_request_id == provider_request_id,
        "usage provider_request_id correlation failed",
    )
    _require(usage_record.error_code is None, "successful usage record cannot contain an error")
    _require(
        local_input_tokens == response_input_tokens == usage_input_tokens,
        "local, response, and usage input-token counts must exactly match",
    )
    _require(
        response_output_tokens == usage_output_tokens,
        "response and usage output-token counts must exactly match",
    )

    return PaidApiOperationalProofReceipt(
        schema_version=_SCHEMA_VERSION,
        task_id=grant.task_id,
        grant_id=grant.grant_id,
        grant_fingerprint=grant_fingerprint,
        brain_id=grant.brain_id,
        provider_id=grant.provider_id,
        model_id=grant.model_id,
        request_id=request_id,
        model_request_fingerprint=model_request_fingerprint,
        authorized_artifact_path=grant.authorized_artifact_path,
        authorized_artifact_blob_sha=grant.authorized_artifact_blob_sha,
        counter_id=counter_id,
        local_pre_call_input_tokens=local_input_tokens,
        provider_reported_input_tokens=response_input_tokens,
        provider_reported_output_tokens=response_output_tokens,
        provider_request_id=provider_request_id,
        response_status=response.status,
        ledger_persisted=True,
        grant_consumed=True,
        input_token_match=True,
        response_content_sha256=hashlib.sha256(
            response_content.encode("utf-8")
        ).hexdigest(),
    )


__all__ = [
    "PaidApiOperationalProofError",
    "PaidApiOperationalProofReceipt",
    "build_paid_api_operational_proof",
]
