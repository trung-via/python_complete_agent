from __future__ import annotations

import asyncio
from dataclasses import replace
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
    DispatchStatus,
)
from src.aios_bridge.continuity.state import ArtifactRef, BrainOperation
from src.aios_bridge.external_brain.context import ContextBuildResult
from src.aios_bridge.external_brain.contracts import (
    BrainOperation as ExternalBrainOperation,
    BrainOutputType,
    BrainRole,
    ContextItem,
    ContextKind,
    ModelRequest,
    ModelResponse,
    ModelResponseStatus,
)
from src.aios_bridge.external_brain.gateway import ModelGateway
from src.aios_bridge.external_brain.usage import JsonlUsageLedger
from src.aios_bridge import paid_api_brain_escape as paid_escape_module
from src.aios_bridge import provider_input_budget as provider_input_budget_module
from src.aios_bridge.paid_api_brain_escape import (
    PaidApiBrainEscapeError,
    PaidApiBrainEscapeResult,
    execute_paid_api_brain_escape,
)
from src.aios_bridge.paid_api_grant import PaidApiGrant
from src.aios_bridge.paid_api_operational_proof import (
    build_paid_api_operational_proof,
)
from src.aios_bridge.provider_input_budget import (
    ProviderInputBudgetError,
    ProviderInputCountEvidence,
    ProviderInputTokenCounter,
    fingerprint_model_request,
)
from src.aios_bridge.runtime_paid_api_grant import (
    AtomicPaidApiGrantStore,
    ContinuityStateValidationError,
)


TASK_ID = "TASK-054"
WORKSPACE_ID = "1" * 64
ARTIFACT_PATH = ".ai/tasks/TASK-054.md"
ARTIFACT_CONTENT = "# TASK-054\n\nBounded paid Brain work.\n"
PROVIDER_ID = "offline-provider"
MODEL_ID = "offline-model"
PAID_BRAIN_ID = "paid-brain"


def git_blob_sha(content: str) -> str:
    payload = content.encode("utf-8")
    return hashlib.sha1(
        b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
    ).hexdigest()


ARTIFACT_BLOB_SHA = git_blob_sha(ARTIFACT_CONTENT)


OPERATION_MAP = {
    BrainOperation.PLAN: (ExternalBrainOperation.PLAN, BrainOutputType.PLAN),
    BrainOperation.DIAGNOSIS: (
        ExternalBrainOperation.DIAGNOSE_FAILURE,
        BrainOutputType.DIAGNOSIS,
    ),
    BrainOperation.PATCH_PROPOSAL: (
        ExternalBrainOperation.GENERATE_PATCH,
        BrainOutputType.PATCH_PROPOSAL,
    ),
    BrainOperation.REVIEW: (
        ExternalBrainOperation.REVIEW_PATCH,
        BrainOutputType.REVIEW,
    ),
}


_NO_EVIDENCE_OVERRIDE = object()


class OfflineProviderInputCounter:
    def __init__(
        self,
        *,
        provider_id: str = PROVIDER_ID,
        model_id: str = MODEL_ID,
        counter_id: str = "offline-full-input-counter",
        is_exact: bool = True,
        counted_input_tokens: int = 64,
        evidence_provider_id: str | None = None,
        evidence_model_id: str | None = None,
        evidence_counter_id: str | None = None,
        evidence_is_exact: bool = True,
        evidence_fingerprint: str | None = None,
        evidence_override=_NO_EVIDENCE_OVERRIDE,
        observe=None,
    ) -> None:
        self.provider_id = provider_id
        self.model_id = model_id
        self.counter_id = counter_id
        self.is_exact = is_exact
        self.counted_input_tokens = counted_input_tokens
        self.evidence_provider_id = evidence_provider_id
        self.evidence_model_id = evidence_model_id
        self.evidence_counter_id = evidence_counter_id
        self.evidence_is_exact = evidence_is_exact
        self.evidence_fingerprint = evidence_fingerprint
        self.evidence_override = evidence_override
        self.observe = observe
        self.calls = 0
        self.last_evidence = None

    def count_request(self, request: ModelRequest) -> ProviderInputCountEvidence:
        self.calls += 1
        if self.observe is not None:
            self.observe()
        if self.evidence_override is not _NO_EVIDENCE_OVERRIDE:
            evidence = self.evidence_override
        else:
            evidence = ProviderInputCountEvidence(
                provider_id=self.evidence_provider_id or self.provider_id,
                model_id=self.evidence_model_id or self.model_id,
                model_request_fingerprint=(
                    self.evidence_fingerprint or fingerprint_model_request(request)
                ),
                counted_input_tokens=self.counted_input_tokens,
                counter_id=self.evidence_counter_id or self.counter_id,
                token_count_is_exact=self.evidence_is_exact,
            )
        self.last_evidence = evidence
        return evidence


@pytest.fixture(autouse=True)
def trust_offline_provider_input_counter(monkeypatch):
    monkeypatch.setattr(
        provider_input_budget_module,
        "_TRUSTED_LOCAL_COUNTER_TYPES",
        (OfflineProviderInputCounter,),
    )


class OfflineProvider:
    def __init__(
        self,
        *,
        provider_id: str = PROVIDER_ID,
        model_name: str = MODEL_ID,
        observe=None,
        raises: Exception | None = None,
        status: ModelResponseStatus = ModelResponseStatus.FAILED,
        input_tokens: int = 7,
        output_tokens: int = 3,
    ) -> None:
        self.provider_id = provider_id
        self.model_name = model_name
        self.observe = observe
        self.raises = raises
        self.status = status
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.calls = 0

    async def invoke(self, request: ModelRequest) -> ModelResponse:
        self.calls += 1
        if self.observe is not None:
            self.observe()
        if self.raises is not None:
            raise self.raises
        success = self.status is ModelResponseStatus.SUCCESS
        return ModelResponse(
            schema_version="1",
            request_id=request.request_id,
            task_id=request.task_id,
            provider=self.provider_id,
            model=self.model_name,
            status=self.status,
            output_type=BrainOutputType.PLAN if success else None,
            content=(
                "# SUMMARY\nOffline proof.\n\n"
                "## STEPS\n1. Correlate evidence.\n\n"
                "## FILES\n- No worktree mutation.\n\n"
                "## TESTS\nRun targeted tests.\n\n"
                "## RISKS\nNo provider call.\n"
                if success
                else None
            ),
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            latency_ms=1,
            provider_request_id="offline-provider-request-054",
            error_code=None if success else "OFFLINE_TEST_FAILURE",
            error_message=None if success else "deterministic offline response",
        )


class FailingLedger:
    def append(self, _record) -> None:
        raise OSError("deterministic ledger failure")


def make_grant(
    *,
    operation: BrainOperation = BrainOperation.PLAN,
    task_id: str = TASK_ID,
    workspace_id: str = WORKSPACE_ID,
    brain_id: str = PAID_BRAIN_ID,
    provider_id: str = PROVIDER_ID,
    model_id: str = MODEL_ID,
    artifact_path: str = ARTIFACT_PATH,
    artifact_blob_sha: str = ARTIFACT_BLOB_SHA,
    max_input_tokens: int = 128,
    max_output_tokens: int = 64,
    expires_at: int = 1_000,
) -> PaidApiGrant:
    return PaidApiGrant(
        schema_version="1",
        grant_id="grant-task-054",
        task_id=task_id,
        actor_kind="BRAIN",
        brain_id=brain_id,
        provider_id=provider_id,
        model_id=model_id,
        brain_operation=operation,
        authorized_artifact_path=artifact_path,
        authorized_artifact_blob_sha=artifact_blob_sha,
        max_input_tokens=max_input_tokens,
        max_output_tokens=max_output_tokens,
        max_calls=1,
        expires_at_epoch_seconds=expires_at,
        workspace_id=workspace_id,
    )


def make_candidate(
    brain_id: str,
    *,
    capacity_class: CapacityClass,
    state: CapacityState = CapacityState.AVAILABLE,
    operation: BrainOperation = BrainOperation.PLAN,
    preference_rank: int = 0,
    supports_operation: bool = True,
) -> BrainDispatchCandidate:
    supported = operation if supports_operation else BrainOperation.REVIEW
    if not supports_operation and operation is BrainOperation.REVIEW:
        supported = BrainOperation.PLAN
    return BrainDispatchCandidate(
        brain_id=brain_id,
        capability=BrainCapability(
            brain_id=brain_id,
            supported_operations=(supported,),
        ),
        capacity_state=state,
        capacity_class=capacity_class,
        preference_rank=preference_rank,
    )


def make_base_request(
    *,
    operation: BrainOperation = BrainOperation.PLAN,
    paid_state: CapacityState = CapacityState.AVAILABLE,
    subscriptions: tuple[BrainDispatchCandidate, ...] = (),
    allow_paid_api: bool = False,
    paid_supports_operation: bool = True,
) -> BrainDispatchRequest:
    paid = make_candidate(
        PAID_BRAIN_ID,
        capacity_class=CapacityClass.PAID_API,
        state=paid_state,
        operation=operation,
        preference_rank=99,
        supports_operation=paid_supports_operation,
    )
    return BrainDispatchRequest(
        operation=operation,
        candidates=(*subscriptions, paid),
        required_context_bytes=12,
        allow_paid_api=allow_paid_api,
    )


def make_context(
    *,
    content: str = ARTIFACT_CONTENT,
    path: str = ARTIFACT_PATH,
    extra: tuple[ContextItem, ...] = (),
    exact: bool = True,
    counted_tokens: int = 20,
    max_context_tokens: int = 128,
    reserve_tokens: int = 8,
) -> ContextBuildResult:
    item = ContextItem(kind=ContextKind.TASK, content=content, path=path, priority=10)
    return ContextBuildResult(
        selected=(item, *extra),
        excluded=(),
        counted_tokens=counted_tokens,
        max_context_tokens=max_context_tokens,
        protocol_reserve_tokens=reserve_tokens,
        counter_id="offline-exact-counter",
        token_count_is_exact=exact,
        context_fingerprint="2" * 64,
    )


def make_model_request(
    context: ContextBuildResult,
    *,
    operation: BrainOperation = BrainOperation.PLAN,
    task_id: str = TASK_ID,
    provider: str | None = PROVIDER_ID,
    model: str | None = MODEL_ID,
    max_input_tokens: int | None = 128,
    max_output_tokens: int | None = 64,
    external_operation: ExternalBrainOperation | None = None,
) -> ModelRequest:
    mapped_operation, output_type = OPERATION_MAP.get(
        operation,
        (ExternalBrainOperation.PLAN, BrainOutputType.PLAN),
    )
    selected_operation = external_operation or mapped_operation
    output_by_external = {
        ExternalBrainOperation.PLAN: BrainOutputType.PLAN,
        ExternalBrainOperation.DIAGNOSE_FAILURE: BrainOutputType.DIAGNOSIS,
        ExternalBrainOperation.GENERATE_PATCH: BrainOutputType.PATCH_PROPOSAL,
        ExternalBrainOperation.REVIEW_PATCH: BrainOutputType.REVIEW,
    }
    return ModelRequest(
        schema_version="1",
        request_id="request-task-054",
        task_id=task_id,
        role=BrainRole.CODER,
        operation=selected_operation,
        instruction="Perform only bounded offline reasoning.",
        context=context.selected,
        output_format=output_by_external.get(selected_operation, output_type),
        provider=provider,
        model=model,
        max_input_tokens=max_input_tokens,
        max_output_tokens=max_output_tokens,
    )


def make_artifact(*, path: str = ARTIFACT_PATH, blob_sha: str = ARTIFACT_BLOB_SHA):
    return ArtifactRef(path=path, ref="main", blob_sha=blob_sha)


def setup_execution(
    tmp_path,
    *,
    operation: BrainOperation = BrainOperation.PLAN,
    base: BrainDispatchRequest | None = None,
    grant: PaidApiGrant | None = None,
    context: ContextBuildResult | None = None,
    model_request: ModelRequest | None = None,
    artifact: ArtifactRef | None = None,
    provider: OfflineProvider | None = None,
    provider_input_counter: OfflineProviderInputCounter | None = None,
    ledger=None,
    activate: bool = True,
    activation_now: int = 10,
):
    actual_grant = grant or make_grant(operation=operation)
    store = AtomicPaidApiGrantStore(tmp_path / "paid-grants", actual_grant.workspace_id)
    if activate:
        store.activate(actual_grant, now_epoch_seconds=activation_now)
    actual_context = context or make_context()
    actual_model_request = model_request or make_model_request(
        actual_context, operation=operation
    )
    actual_provider = provider or OfflineProvider()
    return {
        "base_dispatch_request": base or make_base_request(operation=operation),
        "grant": actual_grant,
        "grant_store": store,
        "authorized_artifact": artifact or make_artifact(),
        "model_request": actual_model_request,
        "context_build": actual_context,
        "provider_input_counter": provider_input_counter or OfflineProviderInputCounter(),
        "gateway": ModelGateway(actual_provider, ledger=ledger),
        "now_epoch_seconds": 20,
    }, actual_provider, store


def run(arguments):
    return asyncio.run(execute_paid_api_brain_escape(**arguments))


def assert_fails_closed(arguments, provider, match: str | None = None):
    with pytest.raises(
        (PaidApiBrainEscapeError, ValueError, ContinuityStateValidationError),
        match=match,
    ):
        run(arguments)
    assert provider.calls == 0


def test_base_allow_paid_true_is_rejected_before_dispatch(tmp_path):
    arguments, provider, _ = setup_execution(
        tmp_path, base=make_base_request(allow_paid_api=True)
    )
    assert_fails_closed(arguments, provider, "must be exactly False")


def test_exactly_one_paid_candidate_is_required(tmp_path):
    subscription = make_candidate(
        "subscription-brain", capacity_class=CapacityClass.SUBSCRIPTION
    )
    no_paid = BrainDispatchRequest(
        operation=BrainOperation.PLAN,
        candidates=(subscription,),
    )
    arguments, provider, _ = setup_execution(tmp_path, base=no_paid)
    assert_fails_closed(arguments, provider, "exactly one")


def test_second_paid_candidate_is_rejected_before_enablement(tmp_path):
    second_paid = make_candidate(
        "second-paid-brain", capacity_class=CapacityClass.PAID_API
    )
    base = BrainDispatchRequest(
        operation=BrainOperation.PLAN,
        candidates=(*make_base_request().candidates, second_paid),
    )
    arguments, provider, _ = setup_execution(tmp_path, base=base)
    assert_fails_closed(arguments, provider, "exactly one")


def test_paid_candidate_must_exactly_match_grant(tmp_path):
    other_paid = make_candidate("other-paid", capacity_class=CapacityClass.PAID_API)
    base = BrainDispatchRequest(operation=BrainOperation.PLAN, candidates=(other_paid,))
    arguments, provider, _ = setup_execution(tmp_path, base=base)
    assert_fails_closed(arguments, provider, "match grant.brain_id")


def test_missing_expired_and_consumed_grants_all_fail_before_gateway(tmp_path):
    missing, missing_provider, _ = setup_execution(tmp_path / "missing", activate=False)
    assert_fails_closed(missing, missing_provider, "not ACTIVE")

    expired_grant = make_grant(expires_at=30)
    expired, expired_provider, _ = setup_execution(
        tmp_path / "expired", grant=expired_grant
    )
    expired["now_epoch_seconds"] = 30
    assert_fails_closed(expired, expired_provider, "expired")

    consumed, consumed_provider, consumed_store = setup_execution(tmp_path / "consumed")
    consumed_store.consume(consumed["grant"], now_epoch_seconds=20)
    assert_fails_closed(consumed, consumed_provider, "not ACTIVE")


@pytest.mark.parametrize(
    ("operation", "expected_external"),
    [
        (BrainOperation.PLAN, ExternalBrainOperation.PLAN),
        (BrainOperation.DIAGNOSIS, ExternalBrainOperation.DIAGNOSE_FAILURE),
        (BrainOperation.PATCH_PROPOSAL, ExternalBrainOperation.GENERATE_PATCH),
        (BrainOperation.REVIEW, ExternalBrainOperation.REVIEW_PATCH),
    ],
)
def test_exact_operation_mapping_for_all_four_supported_operations(
    tmp_path, operation, expected_external
):
    arguments, provider, _ = setup_execution(tmp_path / operation.value, operation=operation)
    assert arguments["model_request"].operation is expected_external
    result = run(arguments)
    assert result.paid_candidate_selected is True
    assert result.grant_consumed is True
    assert provider.calls == 1


@pytest.mark.parametrize("operation", [BrainOperation.TASK, BrainOperation.TASK_AND_PLAN])
def test_task_operations_fail_closed(tmp_path, operation):
    arguments, provider, _ = setup_execution(tmp_path / operation.value, operation=operation)
    assert_fails_closed(arguments, provider, "no authorized External Brain mapping")


@pytest.mark.parametrize(
    "mutation",
    [
        "request_task",
        "request_provider",
        "request_model",
        "request_operation",
        "gateway_provider",
        "gateway_model",
        "grant_operation",
    ],
)
def test_task_workspace_provider_model_and_operation_bindings_fail_closed(
    tmp_path, mutation
):
    context = make_context()
    operation = BrainOperation.PLAN
    grant = make_grant(
        operation=BrainOperation.REVIEW if mutation == "grant_operation" else operation
    )
    request = make_model_request(
        context,
        operation=operation,
        task_id="TASK-999" if mutation == "request_task" else TASK_ID,
        provider="wrong-provider" if mutation == "request_provider" else PROVIDER_ID,
        model="wrong-model" if mutation == "request_model" else MODEL_ID,
        external_operation=(
            ExternalBrainOperation.REVIEW_PATCH
            if mutation == "request_operation"
            else None
        ),
    )
    provider = OfflineProvider(
        provider_id="wrong-provider" if mutation == "gateway_provider" else PROVIDER_ID,
        model_name="wrong-model" if mutation == "gateway_model" else MODEL_ID,
    )
    arguments, provider, _ = setup_execution(
        tmp_path,
        grant=grant,
        context=context,
        model_request=request,
        provider=provider,
    )
    assert_fails_closed(arguments, provider)


def test_artifact_pointer_and_exact_selected_content_blob_are_required(tmp_path):
    wrong_pointer = make_artifact(blob_sha="a" * 40)
    arguments, provider, _ = setup_execution(tmp_path / "pointer", artifact=wrong_pointer)
    assert_fails_closed(arguments, provider)

    wrong_content = make_context(content=ARTIFACT_CONTENT + "changed")
    arguments, provider, _ = setup_execution(tmp_path / "bytes", context=wrong_content)
    arguments["model_request"] = make_model_request(wrong_content)
    assert_fails_closed(arguments, provider, "bytes do not match")

    duplicate = ContextItem(
        kind=ContextKind.CONTRACT,
        content=ARTIFACT_CONTENT,
        path=ARTIFACT_PATH,
    )
    duplicate_context = make_context(extra=(duplicate,))
    arguments, provider, _ = setup_execution(
        tmp_path / "duplicate", context=duplicate_context
    )
    arguments["model_request"] = make_model_request(duplicate_context)
    assert_fails_closed(arguments, provider, "exactly one selected")


def test_context_correlation_and_exact_counter_are_required(tmp_path):
    context = make_context()
    other_context = make_context(extra=(ContextItem(ContextKind.SOURCE, "x", "src/x.py"),))
    arguments, provider, _ = setup_execution(
        tmp_path / "correlation",
        context=context,
        model_request=make_model_request(other_context),
    )
    assert_fails_closed(arguments, provider, "must exactly equal")

    conservative = make_context(exact=False)
    arguments, provider, _ = setup_execution(
        tmp_path / "counter", context=conservative
    )
    arguments["model_request"] = make_model_request(conservative)
    assert_fails_closed(arguments, provider, "exact token counter")


@pytest.mark.parametrize("case", ["missing_input", "missing_output", "mismatch", "overflow", "grant"])
def test_exact_token_bounds_and_budget_are_required(tmp_path, case):
    max_context = 256 if case == "mismatch" else 128
    counted = 125 if case == "overflow" else 20
    reserve = 8
    context = make_context(
        max_context_tokens=max_context,
        counted_tokens=counted,
        reserve_tokens=reserve,
    )
    grant = make_grant(max_input_tokens=64 if case == "grant" else 128)
    request = make_model_request(
        context,
        max_input_tokens=None if case == "missing_input" else 128,
        max_output_tokens=None if case == "missing_output" else 64,
    )
    arguments, provider, _ = setup_execution(
        tmp_path, grant=grant, context=context, model_request=request
    )
    assert_fails_closed(arguments, provider)


def test_provider_input_evidence_contract_is_exact_immutable_and_prompt_free():
    request = make_model_request(make_context())
    evidence = ProviderInputCountEvidence(
        provider_id=PROVIDER_ID,
        model_id=MODEL_ID,
        model_request_fingerprint=fingerprint_model_request(request),
        counted_input_tokens=0,
        counter_id="offline-full-input-counter",
        token_count_is_exact=False,
    )
    assert evidence.schema_version == "1"
    assert evidence.to_canonical_json() == json.dumps(
        evidence.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    assert "instruction" not in evidence.to_dict()
    assert request.instruction not in evidence.to_canonical_json()
    with pytest.raises((AttributeError, TypeError)):
        evidence.counted_input_tokens = 1


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", "2"),
        ("provider_id", " padded"),
        ("model_id", ""),
        ("counter_id", 7),
        ("model_request_fingerprint", "A" * 64),
        ("counted_input_tokens", True),
        ("counted_input_tokens", -1),
        ("token_count_is_exact", 1),
    ],
)
def test_provider_input_evidence_rejects_non_exact_fields(field, value):
    values = {
        "schema_version": "1",
        "provider_id": PROVIDER_ID,
        "model_id": MODEL_ID,
        "model_request_fingerprint": "a" * 64,
        "counted_input_tokens": 1,
        "counter_id": "offline-full-input-counter",
        "token_count_is_exact": True,
    }
    values[field] = value
    with pytest.raises(ProviderInputBudgetError):
        ProviderInputCountEvidence(**values)


def test_model_request_fingerprint_is_canonical_deterministic_and_mutation_sensitive():
    request = replace(
        make_model_request(make_context()),
        instruction="Phân tích bounded request exactly.",
    )
    expected = hashlib.sha256(
        json.dumps(
            request.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()
    assert fingerprint_model_request(request) == expected
    assert fingerprint_model_request(request) == fingerprint_model_request(request)
    assert fingerprint_model_request(
        replace(request, instruction=request.instruction + " changed")
    ) != fingerprint_model_request(request)


def test_provider_input_counter_is_required_and_context_only_exact_is_insufficient(
    tmp_path,
):
    arguments, provider, store = setup_execution(tmp_path)
    assert arguments["context_build"].token_count_is_exact is True
    arguments.pop("provider_input_counter")
    with pytest.raises(TypeError, match="provider_input_counter"):
        run(arguments)
    assert provider.calls == 0
    store.require_active(arguments["grant"], now_epoch_seconds=20)


def test_arbitrary_protocol_counter_is_rejected_before_count_and_paid_side_effects(
    tmp_path, monkeypatch
):
    class ArbitraryProtocolCounter(OfflineProviderInputCounter):
        pass

    counter = ArbitraryProtocolCounter(is_exact=True)
    assert isinstance(counter, ProviderInputTokenCounter)
    arguments, provider, store = setup_execution(
        tmp_path, provider_input_counter=counter
    )

    def forbidden_dispatch(_request):
        raise AssertionError("untrusted counter reached paid dispatch")

    def forbidden_consume(*_args, **_kwargs):
        raise AssertionError("untrusted counter reached grant consume")

    monkeypatch.setattr(paid_escape_module, "dispatch_brain", forbidden_dispatch)
    monkeypatch.setattr(store, "consume", forbidden_consume)
    with pytest.raises(ProviderInputBudgetError, match="trusted-local"):
        run(arguments)
    assert counter.calls == 0
    assert provider.calls == 0
    store.require_active(arguments["grant"], now_epoch_seconds=20)


def test_untrusted_counter_rejected_without_property_or_count_side_effects(tmp_path):
    events = []

    class SideEffectingUntrustedCounter:
        @property
        def provider_id(self):
            events.append("provider_id")
            return PROVIDER_ID

        @property
        def model_id(self):
            events.append("model_id")
            return MODEL_ID

        @property
        def counter_id(self):
            events.append("counter_id")
            return "untrusted-counter"

        @property
        def is_exact(self):
            events.append("is_exact")
            return True

        def count_request(self, request):
            events.append("network-or-side-effect-callback")
            raise AssertionError("untrusted callback must not run")

    counter = SideEffectingUntrustedCounter()
    arguments, provider, store = setup_execution(
        tmp_path, provider_input_counter=counter
    )
    with pytest.raises(ProviderInputBudgetError, match="trusted-local"):
        run(arguments)
    assert events == []
    assert provider.calls == 0
    store.require_active(arguments["grant"], now_epoch_seconds=20)


def test_trust_decision_precedes_exactly_one_count_request(tmp_path, monkeypatch):
    events = []
    original_require_trusted = (
        paid_escape_module.require_trusted_local_provider_input_counter
    )

    def observe_trust(counter):
        events.append("trust")
        return original_require_trusted(counter)

    counter = OfflineProviderInputCounter(
        observe=lambda: events.append("count_request")
    )
    arguments, provider, _ = setup_execution(
        tmp_path, provider_input_counter=counter
    )
    monkeypatch.setattr(
        paid_escape_module,
        "require_trusted_local_provider_input_counter",
        observe_trust,
    )
    result = run(arguments)
    assert result.paid_candidate_selected is True
    assert events == ["trust", "count_request"]
    assert counter.calls == 1
    assert provider.calls == 1


@pytest.mark.parametrize("mutation", ["provider", "model", "not_exact", "counter_id"])
def test_provider_input_counter_identity_must_match_exactly_before_count(
    tmp_path, mutation
):
    counter = OfflineProviderInputCounter(
        provider_id="wrong-provider" if mutation == "provider" else PROVIDER_ID,
        model_id="wrong-model" if mutation == "model" else MODEL_ID,
        is_exact=False if mutation == "not_exact" else True,
        counter_id=" padded" if mutation == "counter_id" else "offline-full-input-counter",
    )
    arguments, provider, store = setup_execution(
        tmp_path, provider_input_counter=counter
    )
    assert_fails_closed(arguments, provider)
    assert counter.calls == 0
    store.require_active(arguments["grant"], now_epoch_seconds=20)


@pytest.mark.parametrize(
    "mutation",
    ["type", "provider", "model", "counter_id", "not_exact", "fingerprint"],
)
def test_provider_input_evidence_requires_exact_type_and_complete_binding(
    tmp_path, mutation
):
    counter = OfflineProviderInputCounter(
        evidence_override=object() if mutation == "type" else _NO_EVIDENCE_OVERRIDE,
        evidence_provider_id="wrong-provider" if mutation == "provider" else None,
        evidence_model_id="wrong-model" if mutation == "model" else None,
        evidence_counter_id="wrong-counter" if mutation == "counter_id" else None,
        evidence_is_exact=False if mutation == "not_exact" else True,
        evidence_fingerprint="0" * 64 if mutation == "fingerprint" else None,
    )
    arguments, provider, store = setup_execution(
        tmp_path, provider_input_counter=counter
    )
    assert_fails_closed(arguments, provider)
    assert counter.calls == 1
    store.require_active(arguments["grant"], now_epoch_seconds=20)


def test_provider_input_counter_is_called_exactly_once_for_a_valid_attempt(tmp_path):
    counter = OfflineProviderInputCounter(counted_input_tokens=128)
    arguments, provider, _ = setup_execution(
        tmp_path, provider_input_counter=counter
    )
    result = run(arguments)
    assert result.paid_candidate_selected is True
    assert result.provider_input_evidence is counter.last_evidence
    assert counter.calls == 1
    assert provider.calls == 1


def test_escape_result_requires_exact_original_provider_input_evidence(tmp_path):
    counter = OfflineProviderInputCounter()
    arguments, _, _ = setup_execution(tmp_path, provider_input_counter=counter)
    result = run(arguments)

    parameter = inspect.signature(PaidApiBrainEscapeResult).parameters[
        "provider_input_evidence"
    ]
    assert parameter.default is inspect.Parameter.empty
    assert result.provider_input_evidence is counter.last_evidence
    with pytest.raises(PaidApiBrainEscapeError, match="provider_input_evidence"):
        replace(result, provider_input_evidence=object())


def test_operational_proof_reuses_original_evidence_without_second_count(tmp_path):
    counter = OfflineProviderInputCounter(counted_input_tokens=64)
    provider = OfflineProvider(
        status=ModelResponseStatus.SUCCESS,
        input_tokens=64,
        output_tokens=12,
    )
    arguments, _, store = setup_execution(
        tmp_path,
        provider=provider,
        provider_input_counter=counter,
        ledger=JsonlUsageLedger(tmp_path / "usage" / "paid-api.jsonl"),
    )

    result = run(arguments)
    assert counter.calls == 1
    assert result.provider_input_evidence is counter.last_evidence
    receipt = build_paid_api_operational_proof(
        escape_result=result,
        grant=arguments["grant"],
        grant_store=store,
        model_request=arguments["model_request"],
    )
    assert receipt.input_token_match is True
    assert counter.calls == 1


def test_full_provider_input_over_request_limit_fails_before_enablement_consume_gateway(
    tmp_path, monkeypatch
):
    counter = OfflineProviderInputCounter(counted_input_tokens=129)
    arguments, provider, store = setup_execution(
        tmp_path, provider_input_counter=counter
    )

    def forbidden_dispatch(_request):
        raise AssertionError("paid dispatch was enabled before full-input proof")

    def forbidden_consume(*_args, **_kwargs):
        raise AssertionError("grant was consumed before full-input proof")

    monkeypatch.setattr(paid_escape_module, "dispatch_brain", forbidden_dispatch)
    monkeypatch.setattr(store, "consume", forbidden_consume)
    with pytest.raises(PaidApiBrainEscapeError, match="full provider input count"):
        run(arguments)
    assert counter.calls == 1
    assert provider.calls == 0
    store.require_active(arguments["grant"], now_epoch_seconds=20)


def test_full_provider_input_at_request_limit_and_within_human_grant_is_accepted(
    tmp_path,
):
    grant = make_grant(max_input_tokens=128)
    counter = OfflineProviderInputCounter(counted_input_tokens=128)
    arguments, provider, _ = setup_execution(
        tmp_path,
        grant=grant,
        provider_input_counter=counter,
    )
    result = run(arguments)
    assert result.paid_candidate_selected is True
    assert result.grant_consumed is True
    assert counter.calls == 1
    assert provider.calls == 1


def test_exact_context_does_not_compensate_for_inexact_full_input_evidence(tmp_path):
    counter = OfflineProviderInputCounter(evidence_is_exact=False)
    arguments, provider, store = setup_execution(
        tmp_path, provider_input_counter=counter
    )
    assert arguments["context_build"].token_count_is_exact is True
    assert_fails_closed(arguments, provider, "token_count_is_exact")
    assert counter.calls == 1
    store.require_active(arguments["grant"], now_epoch_seconds=20)


def test_subscription_is_still_preferred_and_leaves_grant_active(tmp_path):
    subscription = make_candidate(
        "subscription-brain",
        capacity_class=CapacityClass.SUBSCRIPTION,
        preference_rank=500,
    )
    arguments, provider, store = setup_execution(
        tmp_path,
        base=make_base_request(subscriptions=(subscription,)),
    )
    result = run(arguments)
    assert result.dispatch_result.status is DispatchStatus.SELECTED
    assert result.dispatch_result.selected_actor_id == "subscription-brain"
    assert result.paid_candidate_selected is False
    assert result.grant_consumed is False
    assert result.gateway_result is None
    assert result.provider_input_evidence is arguments["provider_input_counter"].last_evidence
    assert provider.calls == 0
    assert arguments["provider_input_counter"].calls == 1
    assert store.require_active(arguments["grant"], now_epoch_seconds=20) == arguments["grant"]


@pytest.mark.parametrize("paid_supports", [True, False])
def test_wait_or_no_compatible_does_not_consume_or_call_gateway(tmp_path, paid_supports):
    base = make_base_request(
        paid_state=CapacityState.UNAVAILABLE,
        paid_supports_operation=paid_supports,
    )
    arguments, provider, store = setup_execution(tmp_path, base=base)
    result = run(arguments)
    expected = DispatchStatus.WAIT if paid_supports else DispatchStatus.NO_COMPATIBLE_CANDIDATE
    assert result.dispatch_result.status is expected
    assert result.grant_consumed is False
    assert result.gateway_result is None
    assert provider.calls == 0
    store.require_active(arguments["grant"], now_epoch_seconds=20)


def test_paid_win_consumes_before_exactly_one_gateway_call(tmp_path):
    observed = []
    provider = OfflineProvider(observe=lambda: observed.append("gateway"))
    arguments, provider, store = setup_execution(tmp_path, provider=provider)

    def observe_consumed():
        with pytest.raises(ContinuityStateValidationError, match="not ACTIVE"):
            store.require_active(arguments["grant"], now_epoch_seconds=20)
        observed.append("consumed-before-gateway")

    provider.observe = observe_consumed
    result = run(arguments)
    assert result.paid_candidate_selected is True
    assert result.grant_consumed is True
    assert result.gateway_result is not None
    assert observed == ["consumed-before-gateway"]
    assert provider.calls == 1


def test_consume_failure_means_zero_gateway_calls(tmp_path, monkeypatch):
    arguments, provider, store = setup_execution(tmp_path)

    def fail_consume(*_args, **_kwargs):
        raise OSError("deterministic consume failure")

    monkeypatch.setattr(store, "consume", fail_consume)
    with pytest.raises(OSError, match="consume failure"):
        run(arguments)
    assert provider.calls == 0
    store.require_active(arguments["grant"], now_epoch_seconds=20)


def test_gateway_exception_never_restores_consumed_grant_or_retries(tmp_path):
    provider = OfflineProvider(raises=RuntimeError("gateway exploded"))
    arguments, provider, store = setup_execution(tmp_path, provider=provider)
    with pytest.raises(RuntimeError, match="gateway exploded"):
        run(arguments)
    assert provider.calls == 1
    with pytest.raises(ContinuityStateValidationError, match="not ACTIVE"):
        store.require_active(arguments["grant"], now_epoch_seconds=20)


def test_provider_failure_and_ledger_failure_leave_grant_consumed(tmp_path):
    arguments, provider, store = setup_execution(
        tmp_path,
        provider=OfflineProvider(status=ModelResponseStatus.FAILED),
        ledger=FailingLedger(),
    )
    result = run(arguments)
    assert provider.calls == 1
    assert result.gateway_result is not None
    assert result.gateway_result.response.status is ModelResponseStatus.FAILED
    assert result.gateway_result.ledger_persisted is False
    assert result.gateway_result.ledger_error_code == "LEDGER_WRITE_FAILED"
    with pytest.raises(ContinuityStateValidationError, match="not ACTIVE"):
        store.require_active(arguments["grant"], now_epoch_seconds=20)


def test_sequential_replay_is_rejected_without_another_gateway_call(tmp_path):
    arguments, provider, _ = setup_execution(tmp_path)
    first = run(arguments)
    assert first.grant_consumed is True
    with pytest.raises(ContinuityStateValidationError, match="not ACTIVE"):
        run(arguments)
    assert provider.calls == 1


def test_concurrent_same_grant_has_one_consume_winner_and_at_most_one_gateway(tmp_path):
    arguments, provider, _ = setup_execution(tmp_path)

    async def race():
        results = await asyncio.gather(
            execute_paid_api_brain_escape(**arguments),
            execute_paid_api_brain_escape(**arguments),
            return_exceptions=True,
        )
        return results

    results = asyncio.run(race())
    successes = [item for item in results if not isinstance(item, Exception)]
    failures = [item for item in results if isinstance(item, Exception)]
    assert len(successes) == 1
    assert successes[0].grant_consumed is True
    assert len(failures) == 1
    assert provider.calls == 1


def test_no_second_provider_executor_authority_git_or_network_surface(tmp_path):
    second_provider = OfflineProvider(provider_id="second-provider", model_name="second-model")
    arguments, first_provider, _ = setup_execution(tmp_path)
    result = run(arguments)
    assert result.grant_consumed is True
    assert first_provider.calls == 1
    assert second_provider.calls == 0

    signature = inspect.signature(execute_paid_api_brain_escape)
    counter_parameter = signature.parameters["provider_input_counter"]
    assert counter_parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert counter_parameter.default is inspect.Parameter.empty
    assert not any("executor" in name.lower() for name in signature.parameters)
    module = inspect.getmodule(execute_paid_api_brain_escape)
    assert module is not None
    assert not {"subprocess", "socket", "requests", "urllib"}.intersection(module.__dict__)
    counter_module = inspect.getmodule(ProviderInputCountEvidence)
    assert counter_module is not None
    assert not {"subprocess", "socket", "requests", "urllib"}.intersection(
        counter_module.__dict__
    )
    assert isinstance(arguments["provider_input_counter"], ProviderInputTokenCounter)
