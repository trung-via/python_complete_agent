from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import hashlib
import inspect
import json

import pytest

from src.aios_bridge.continuity.brain import BrainCapability
from src.aios_bridge.continuity.dispatch import (
    BrainDispatchCandidate,
    BrainDispatchRequest,
    CapacityClass,
    CapacityState,
    DispatchActorKind,
    DispatchStatus,
    dispatch_brain,
)
from src.aios_bridge.continuity.state import BrainOperation
from src.aios_bridge.external_brain.contracts import (
    BrainOperation as ExternalBrainOperation,
    BrainOutputType,
    BrainRole,
    ModelRequest,
    ModelResponse,
    ModelResponseStatus,
)
from src.aios_bridge.external_brain.gateway import GatewayResult
from src.aios_bridge.external_brain.usage import UsageRecord
from src.aios_bridge.paid_api_brain_escape import PaidApiBrainEscapeResult
from src.aios_bridge import paid_api_operational_proof as proof_module
from src.aios_bridge.paid_api_operational_proof import (
    PaidApiOperationalProofError,
    PaidApiOperationalProofReceipt,
    build_paid_api_operational_proof,
)
from src.aios_bridge.paid_api_grant import PaidApiGrant
from src.aios_bridge.provider_input_budget import (
    ProviderInputCountEvidence,
    fingerprint_model_request,
)
from src.aios_bridge.runtime_paid_api_grant import AtomicPaidApiGrantStore


TASK_ID = "TASK-058"
WORKSPACE_ID = "1" * 64
GRANT_ID = "grant-task-058"
BRAIN_ID = "paid-proof-brain"
PROVIDER_ID = "offline-provider"
MODEL_ID = "offline-model"
ARTIFACT_PATH = ".ai/tasks/TASK-058.md"
ARTIFACT_BLOB_SHA = "a" * 40
REQUEST_ID = "request-task-058"
PROVIDER_REQUEST_ID = "provider-request-058"
COUNTER_ID = "offline-original-precall-counter"
RESPONSE_CONTENT = "# Plan\n\nValidated offline proposal."


def make_grant(**changes) -> PaidApiGrant:
    values = {
        "schema_version": "1",
        "grant_id": GRANT_ID,
        "task_id": TASK_ID,
        "actor_kind": DispatchActorKind.BRAIN,
        "brain_id": BRAIN_ID,
        "provider_id": PROVIDER_ID,
        "model_id": MODEL_ID,
        "brain_operation": BrainOperation.PLAN,
        "authorized_artifact_path": ARTIFACT_PATH,
        "authorized_artifact_blob_sha": ARTIFACT_BLOB_SHA,
        "max_input_tokens": 128,
        "max_output_tokens": 64,
        "max_calls": 1,
        "expires_at_epoch_seconds": 1_000,
        "workspace_id": WORKSPACE_ID,
    }
    values.update(changes)
    return PaidApiGrant(**values)


def make_model_request(**changes) -> ModelRequest:
    values = {
        "schema_version": "1",
        "request_id": REQUEST_ID,
        "task_id": TASK_ID,
        "role": BrainRole.CODER,
        "operation": ExternalBrainOperation.PLAN,
        "instruction": "Perform bounded offline proof work.",
        "context": (),
        "output_format": BrainOutputType.PLAN,
        "provider": PROVIDER_ID,
        "model": MODEL_ID,
        "max_input_tokens": 128,
        "max_output_tokens": 64,
    }
    values.update(changes)
    return ModelRequest(**values)


def make_candidate(
    brain_id: str,
    *,
    capacity_class: CapacityClass = CapacityClass.PAID_API,
    state: CapacityState = CapacityState.AVAILABLE,
    operation: BrainOperation = BrainOperation.PLAN,
) -> BrainDispatchCandidate:
    return BrainDispatchCandidate(
        brain_id=brain_id,
        capability=BrainCapability(
            brain_id=brain_id,
            supported_operations=(operation,),
        ),
        capacity_state=state,
        capacity_class=capacity_class,
    )


def make_effective_request(
    *,
    brain_id: str = BRAIN_ID,
    state: CapacityState = CapacityState.AVAILABLE,
    operation: BrainOperation = BrainOperation.PLAN,
    allow_paid_api: bool = True,
    extra_candidates: tuple[BrainDispatchCandidate, ...] = (),
) -> BrainDispatchRequest:
    return BrainDispatchRequest(
        operation=operation,
        candidates=(
            *extra_candidates,
            make_candidate(brain_id, state=state, operation=operation),
        ),
        allow_paid_api=allow_paid_api,
    )


def make_response(request: ModelRequest, **changes) -> ModelResponse:
    values = {
        "schema_version": "1",
        "request_id": request.request_id,
        "task_id": request.task_id,
        "provider": PROVIDER_ID,
        "model": MODEL_ID,
        "status": ModelResponseStatus.SUCCESS,
        "output_type": BrainOutputType.PLAN,
        "content": RESPONSE_CONTENT,
        "input_tokens": 64,
        "output_tokens": 12,
        "latency_ms": 5,
        "provider_request_id": PROVIDER_REQUEST_ID,
    }
    values.update(changes)
    return ModelResponse(**values)


def make_usage(request: ModelRequest, response: ModelResponse, **changes) -> UsageRecord:
    values = {
        "schema_version": "1",
        "timestamp_utc": "2026-08-20T00:00:00+00:00",
        "request_id": request.request_id,
        "task_id": request.task_id,
        "provider": PROVIDER_ID,
        "requested_model": request.model,
        "actual_model": MODEL_ID,
        "status": response.status,
        "provider_input_tokens": response.input_tokens,
        "provider_output_tokens": response.output_tokens,
        "latency_ms": response.latency_ms,
        "provider_request_id": response.provider_request_id,
        "error_code": response.error_code,
    }
    values.update(changes)
    return UsageRecord(**values)


def make_proof_inputs(
    tmp_path,
    *,
    grant: PaidApiGrant | None = None,
    model_request: ModelRequest | None = None,
    evidence: ProviderInputCountEvidence | None = None,
    response: ModelResponse | None = None,
    usage_record: UsageRecord | None = None,
    ledger_persisted: bool | None = True,
    ledger_error_code: str | None = None,
    durable_state: str = "consumed",
    stored_grant: PaidApiGrant | None = None,
):
    actual_grant = grant or make_grant()
    request = model_request or make_model_request()
    effective_request = make_effective_request(
        brain_id=actual_grant.brain_id,
        operation=actual_grant.brain_operation,
    )
    dispatch_result = dispatch_brain(effective_request)
    actual_evidence = evidence or ProviderInputCountEvidence(
        provider_id=PROVIDER_ID,
        model_id=MODEL_ID,
        model_request_fingerprint=fingerprint_model_request(request),
        counted_input_tokens=64,
        counter_id=COUNTER_ID,
        token_count_is_exact=True,
    )
    actual_response = response or make_response(request)
    actual_usage = usage_record or make_usage(request, actual_response)
    gateway_result = GatewayResult(
        response=actual_response,
        usage_record=actual_usage,
        ledger_persisted=ledger_persisted,
        ledger_error_code=ledger_error_code,
    )
    escape_result = PaidApiBrainEscapeResult(
        effective_dispatch_request=effective_request,
        dispatch_result=dispatch_result,
        provider_input_evidence=actual_evidence,
        paid_candidate_selected=True,
        grant_consumed=True,
        gateway_result=gateway_result,
    )

    state_grant = stored_grant or actual_grant
    grant_store = AtomicPaidApiGrantStore(
        tmp_path / "paid-api-proof-grants",
        actual_grant.workspace_id,
    )
    if durable_state in ("active", "consumed"):
        grant_store.activate(state_grant, now_epoch_seconds=10)
    if durable_state == "consumed":
        grant_store.consume(state_grant, now_epoch_seconds=20)
    if durable_state not in ("missing", "active", "consumed"):
        raise AssertionError(f"unknown test durable state: {durable_state}")

    return {
        "escape_result": escape_result,
        "grant": actual_grant,
        "grant_store": grant_store,
        "model_request": request,
    }


def build(arguments):
    return build_paid_api_operational_proof(**arguments)


def replace_gateway(arguments, *, response=None, usage_record=None, **changes):
    gateway_result = arguments["escape_result"].gateway_result
    assert gateway_result is not None
    replacement = replace(
        gateway_result,
        response=response or gateway_result.response,
        usage_record=usage_record or gateway_result.usage_record,
        **changes,
    )
    updated = dict(arguments)
    updated["escape_result"] = replace(
        arguments["escape_result"],
        gateway_result=replacement,
    )
    return updated


def test_valid_receipt_is_bounded_immutable_and_deterministic(tmp_path):
    arguments = make_proof_inputs(tmp_path)
    receipt = build(arguments)

    assert receipt.schema_version == "1"
    assert receipt.task_id == TASK_ID
    assert receipt.grant_fingerprint == arguments["grant"].fingerprint()
    assert receipt.model_request_fingerprint == fingerprint_model_request(
        arguments["model_request"]
    )
    assert receipt.local_pre_call_input_tokens == 64
    assert receipt.provider_reported_input_tokens == 64
    assert receipt.provider_reported_output_tokens == 12
    assert receipt.response_status is ModelResponseStatus.SUCCESS
    assert receipt.ledger_persisted is True
    assert receipt.grant_consumed is True
    assert receipt.input_token_match is True
    assert receipt.response_content_sha256 == hashlib.sha256(
        RESPONSE_CONTENT.encode("utf-8")
    ).hexdigest()

    canonical = receipt.to_canonical_json()
    assert canonical == json.dumps(
        receipt.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    assert receipt.fingerprint() == hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    assert build(arguments).to_canonical_json() == canonical
    assert build(arguments).fingerprint() == receipt.fingerprint()
    with pytest.raises(FrozenInstanceError):
        receipt.task_id = "TASK-999"
    with pytest.raises(PaidApiOperationalProofError, match="exact non-negative"):
        replace(receipt, provider_reported_output_tokens=True)


def test_receipt_hash_binds_content_but_excludes_content_and_secrets(tmp_path):
    request = make_model_request(instruction="PROMPT_SECRET_058")
    response = make_response(request, content="# Plan\n\nOUTPUT_SECRET_058")
    arguments = make_proof_inputs(
        tmp_path,
        model_request=request,
        response=response,
        usage_record=make_usage(request, response),
    )
    receipt = build(arguments)
    serialized = receipt.to_canonical_json()
    fields = set(receipt.to_dict())

    assert receipt.response_content_sha256 == hashlib.sha256(
        response.content.encode("utf-8")
    ).hexdigest()
    assert "PROMPT_SECRET_058" not in serialized
    assert "OUTPUT_SECRET_058" not in serialized
    assert fields.isdisjoint(
        {
            "instruction",
            "context",
            "content",
            "api_key",
            "headers",
            "cookies",
            "raw_response_body",
            "timestamp_utc",
        }
    )

    changed_response = replace(response, content="# Plan\n\nDifferent validated output.")
    changed = replace_gateway(arguments, response=changed_response)
    changed_receipt = build(changed)
    assert changed_receipt.response_content_sha256 != receipt.response_content_sha256
    assert changed_receipt.fingerprint() != receipt.fingerprint()


@pytest.mark.parametrize(
    "field_name",
    ["escape_result", "grant", "grant_store", "model_request"],
)
def test_verifier_requires_exact_authority_input_types(tmp_path, field_name):
    arguments = make_proof_inputs(tmp_path)
    arguments[field_name] = object()
    with pytest.raises(PaidApiOperationalProofError, match=field_name):
        build(arguments)


def test_paid_selection_and_grant_consumed_are_required(tmp_path):
    arguments = make_proof_inputs(tmp_path)
    arguments["escape_result"] = replace(
        arguments["escape_result"],
        paid_candidate_selected=False,
        grant_consumed=False,
        gateway_result=None,
    )
    with pytest.raises(PaidApiOperationalProofError, match="paid candidate selection"):
        build(arguments)


def test_effective_allow_paid_api_is_required(tmp_path):
    arguments = make_proof_inputs(tmp_path)
    effective = replace(
        arguments["escape_result"].effective_dispatch_request,
        allow_paid_api=False,
    )
    arguments["escape_result"] = replace(
        arguments["escape_result"],
        effective_dispatch_request=effective,
    )
    with pytest.raises(PaidApiOperationalProofError, match="allow_paid_api"):
        build(arguments)


def test_selected_dispatch_status_and_brain_actor_are_required(tmp_path):
    arguments = make_proof_inputs(tmp_path)
    waiting_request = make_effective_request(state=CapacityState.UNAVAILABLE)
    waiting_result = dispatch_brain(waiting_request)
    assert waiting_result.status is DispatchStatus.WAIT
    waiting = dict(arguments)
    waiting["escape_result"] = replace(
        arguments["escape_result"],
        effective_dispatch_request=waiting_request,
        dispatch_result=waiting_result,
    )
    with pytest.raises(PaidApiOperationalProofError, match="SELECTED"):
        build(waiting)

    executor_actor = dict(arguments)
    executor_actor["escape_result"] = replace(
        arguments["escape_result"],
        dispatch_result=replace(
            arguments["escape_result"].dispatch_result,
            actor_kind=DispatchActorKind.EXECUTOR,
        ),
    )
    with pytest.raises(PaidApiOperationalProofError, match="BRAIN"):
        build(executor_actor)


def test_selected_brain_and_dispatch_request_fingerprint_must_match(tmp_path):
    arguments = make_proof_inputs(tmp_path)
    subscription = make_candidate(
        "other-brain",
        capacity_class=CapacityClass.SUBSCRIPTION,
    )
    other_request = make_effective_request(extra_candidates=(subscription,))
    other_result = dispatch_brain(other_request)
    assert other_result.selected_actor_id == "other-brain"
    arguments["escape_result"] = replace(
        arguments["escape_result"],
        effective_dispatch_request=other_request,
        dispatch_result=other_result,
    )
    with pytest.raises(PaidApiOperationalProofError, match="selected Brain"):
        build(arguments)

    subscription_arguments = make_proof_inputs(tmp_path / "subscription")
    subscription_request = BrainDispatchRequest(
        operation=BrainOperation.PLAN,
        candidates=(
            make_candidate(
                BRAIN_ID,
                capacity_class=CapacityClass.SUBSCRIPTION,
            ),
        ),
        allow_paid_api=True,
    )
    subscription_arguments["escape_result"] = replace(
        subscription_arguments["escape_result"],
        effective_dispatch_request=subscription_request,
        dispatch_result=dispatch_brain(subscription_request),
    )
    with pytest.raises(PaidApiOperationalProofError, match="PAID_API candidate"):
        build(subscription_arguments)

    fingerprint_arguments = make_proof_inputs(tmp_path / "fingerprint")
    fingerprint_arguments["escape_result"] = replace(
        fingerprint_arguments["escape_result"],
        dispatch_result=replace(
            fingerprint_arguments["escape_result"].dispatch_result,
            request_fingerprint="0" * 64,
        ),
    )
    with pytest.raises(PaidApiOperationalProofError, match="effective dispatch"):
        build(fingerprint_arguments)


@pytest.mark.parametrize("durable_state", ["missing", "active"])
def test_grant_must_be_durably_consumed_and_not_active(tmp_path, durable_state):
    arguments = make_proof_inputs(tmp_path, durable_state=durable_state)
    with pytest.raises(PaidApiOperationalProofError):
        build(arguments)


def test_consumed_grant_and_fingerprint_must_match_exactly(tmp_path):
    expected = make_grant()
    stored = make_grant(model_id="different-offline-model")
    arguments = make_proof_inputs(
        tmp_path,
        grant=expected,
        stored_grant=stored,
    )
    with pytest.raises(PaidApiOperationalProofError, match="CONSUMED"):
        build(arguments)

    fingerprint_arguments = make_proof_inputs(tmp_path / "fingerprint")
    object.__setattr__(fingerprint_arguments["grant"], "grant_fingerprint", "0" * 64)
    with pytest.raises(PaidApiOperationalProofError, match="fingerprint"):
        build(fingerprint_arguments)


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("provider_id", "different-provider", "evidence provider"),
        ("model_id", "different-model", "evidence model"),
        ("model_request_fingerprint", "0" * 64, "exact ModelRequest"),
        ("token_count_is_exact", False, "exactly counted"),
        ("counted_input_tokens", 129, "input-token bounds"),
    ],
)
def test_original_provider_input_evidence_is_exact_and_bounded(
    tmp_path, field_name, value, message
):
    arguments = make_proof_inputs(tmp_path)
    evidence = replace(
        arguments["escape_result"].provider_input_evidence,
        **{field_name: value},
    )
    arguments["escape_result"] = replace(
        arguments["escape_result"],
        provider_input_evidence=evidence,
    )
    with pytest.raises(PaidApiOperationalProofError, match=message):
        build(arguments)


def test_request_fingerprint_and_request_grant_bounds_are_exact(tmp_path):
    request = make_model_request(max_input_tokens=129)
    evidence = ProviderInputCountEvidence(
        provider_id=PROVIDER_ID,
        model_id=MODEL_ID,
        model_request_fingerprint=fingerprint_model_request(request),
        counted_input_tokens=64,
        counter_id=COUNTER_ID,
        token_count_is_exact=True,
    )
    arguments = make_proof_inputs(tmp_path, model_request=request, evidence=evidence)
    with pytest.raises(PaidApiOperationalProofError, match="input-token bounds"):
        build(arguments)

    output_request = make_model_request(max_output_tokens=65)
    output_evidence = replace(
        evidence,
        model_request_fingerprint=fingerprint_model_request(output_request),
    )
    output_arguments = make_proof_inputs(
        tmp_path / "output",
        model_request=output_request,
        evidence=output_evidence,
    )
    with pytest.raises(PaidApiOperationalProofError, match="output-token bound"):
        build(output_arguments)


@pytest.mark.parametrize(
    "status",
    [
        ModelResponseStatus.FAILED,
        ModelResponseStatus.RATE_LIMITED,
        ModelResponseStatus.UNAVAILABLE,
        ModelResponseStatus.TIMEOUT,
        ModelResponseStatus.AUTH_ERROR,
        ModelResponseStatus.INVALID_RESPONSE,
    ],
)
def test_every_non_success_response_status_is_rejected(tmp_path, status):
    request = make_model_request()
    response = make_response(request, status=status)
    arguments = make_proof_inputs(
        tmp_path,
        model_request=request,
        response=response,
        usage_record=make_usage(request, response),
    )
    with pytest.raises(PaidApiOperationalProofError, match="SUCCESS"):
        build(arguments)


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("request_id", "different-request", "request_id"),
        ("task_id", "TASK-999", "task_id"),
        ("provider", "different-provider", "provider"),
        ("model", "different-model", "model"),
        ("output_type", BrainOutputType.REVIEW, "output_type"),
        ("provider_request_id", None, "provider_request_id"),
        ("input_tokens", None, "input_tokens"),
        ("output_tokens", None, "output_tokens"),
        ("output_tokens", 65, "output-token bounds"),
    ],
)
def test_success_response_correlations_usage_presence_and_bounds_are_exact(
    tmp_path, field_name, value, message
):
    arguments = make_proof_inputs(tmp_path)
    gateway = arguments["escape_result"].gateway_result
    assert gateway is not None
    response = replace(gateway.response, **{field_name: value})
    arguments = replace_gateway(arguments, response=response)
    with pytest.raises(PaidApiOperationalProofError, match=message):
        build(arguments)


def test_local_response_and_usage_token_equalities_are_critical(tmp_path):
    response_arguments = make_proof_inputs(tmp_path / "response")
    response_gateway = response_arguments["escape_result"].gateway_result
    assert response_gateway is not None
    response_arguments = replace_gateway(
        response_arguments,
        response=replace(response_gateway.response, input_tokens=63),
    )
    with pytest.raises(PaidApiOperationalProofError, match="input-token counts"):
        build(response_arguments)

    usage_input_arguments = make_proof_inputs(tmp_path / "usage-input")
    usage_input_gateway = usage_input_arguments["escape_result"].gateway_result
    assert usage_input_gateway is not None
    usage_input_arguments = replace_gateway(
        usage_input_arguments,
        usage_record=replace(
            usage_input_gateway.usage_record,
            provider_input_tokens=63,
        ),
    )
    with pytest.raises(PaidApiOperationalProofError, match="input-token counts"):
        build(usage_input_arguments)

    usage_output_arguments = make_proof_inputs(tmp_path / "usage-output")
    usage_output_gateway = usage_output_arguments["escape_result"].gateway_result
    assert usage_output_gateway is not None
    usage_output_arguments = replace_gateway(
        usage_output_arguments,
        usage_record=replace(
            usage_output_gateway.usage_record,
            provider_output_tokens=11,
        ),
    )
    with pytest.raises(PaidApiOperationalProofError, match="output-token counts"):
        build(usage_output_arguments)


@pytest.mark.parametrize(
    ("ledger_persisted", "ledger_error_code", "message"),
    [
        (False, None, "durably persisted"),
        (None, None, "durably persisted"),
        (True, "LEDGER_WRITE_FAILED", "error code"),
    ],
)
def test_durable_ledger_success_is_required(
    tmp_path, ledger_persisted, ledger_error_code, message
):
    arguments = make_proof_inputs(
        tmp_path,
        ledger_persisted=ledger_persisted,
        ledger_error_code=ledger_error_code,
    )
    with pytest.raises(PaidApiOperationalProofError, match=message):
        build(arguments)


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("request_id", "different-request", "request_id"),
        ("task_id", "TASK-999", "task_id"),
        ("provider", "different-provider", "provider"),
        ("requested_model", "different-model", "requested_model"),
        ("actual_model", "different-model", "actual_model"),
        ("status", ModelResponseStatus.FAILED, "status"),
        ("provider_request_id", "different-provider-request", "provider_request_id"),
        ("error_code", "UNEXPECTED_ERROR", "cannot contain an error"),
    ],
)
def test_usage_record_correlation_is_exact(tmp_path, field_name, value, message):
    arguments = make_proof_inputs(tmp_path)
    gateway = arguments["escape_result"].gateway_result
    assert gateway is not None
    usage = replace(gateway.usage_record, **{field_name: value})
    arguments = replace_gateway(arguments, usage_record=usage)
    with pytest.raises(PaidApiOperationalProofError, match=message):
        build(arguments)


def test_proof_is_read_only_and_has_no_count_dispatch_provider_or_secret_surface(
    tmp_path, monkeypatch
):
    arguments = make_proof_inputs(tmp_path)
    store = arguments["grant_store"]
    grant = arguments["grant"]
    before_active = store.load_active(grant.task_id, grant.grant_id)
    before_consumed = store.load_consumed(grant.task_id, grant.grant_id)
    calls = []
    original_load_active = store.load_active
    original_load_consumed = store.load_consumed

    monkeypatch.setattr(
        store,
        "load_active",
        lambda *args, **kwargs: (
            calls.append("load_active") or original_load_active(*args, **kwargs)
        ),
    )
    monkeypatch.setattr(
        store,
        "load_consumed",
        lambda *args, **kwargs: (
            calls.append("load_consumed") or original_load_consumed(*args, **kwargs)
        ),
    )
    for method_name in ("activate", "require_active", "consume"):
        monkeypatch.setattr(
            store,
            method_name,
            lambda *_args, _name=method_name, **_kwargs: (_ for _ in ()).throw(
                AssertionError(f"proof attempted forbidden grant mutation: {_name}")
            ),
        )

    receipt = build(arguments)
    assert isinstance(receipt, PaidApiOperationalProofReceipt)
    assert calls == ["load_active", "load_consumed"]
    assert store.load_active(grant.task_id, grant.grant_id) == before_active
    assert store.load_consumed(grant.task_id, grant.grant_id) == before_consumed

    signature = inspect.signature(build_paid_api_operational_proof)
    assert set(signature.parameters) == {
        "escape_result",
        "grant",
        "grant_store",
        "model_request",
    }
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        and parameter.default is inspect.Parameter.empty
        for parameter in signature.parameters.values()
    )
    assert not {
        "socket",
        "requests",
        "urllib",
        "subprocess",
        "os",
        "datetime",
    }.intersection(proof_module.__dict__)
    source = inspect.getsource(build_paid_api_operational_proof)
    assert "count_request" not in source
    assert "dispatch_brain" not in source
    assert "gateway.invoke" not in source
    assert "ledger.append" not in source
    assert "api_key" not in source.lower()
