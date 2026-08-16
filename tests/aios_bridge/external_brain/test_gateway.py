"""Unit tests for ModelGateway orchestration, validation, and ledger recording."""
from __future__ import annotations

from typing import Any
import pytest

from src.aios_bridge.external_brain import (
    BrainOperation,
    BrainOutputType,
    BrainRole,
    ContextBudget,
    ContextBuilder,
    ContextItem,
    ContextKind,
    ContractValidationError,
    GatewayResult,
    ModelGateway,
    ModelRequest,
    ModelResponse,
    ModelResponseStatus,
    ProviderAdapter,
    UsageLedger,
    UsageRecord,
)


class FakeProvider:
    """Fake provider adapter tracking invoke() call counts."""

    def __init__(self, provider_id: str = "minimax", response: ModelResponse | None = None) -> None:
        self.provider_id = provider_id
        self.call_count = 0
        self.response = response

    async def invoke(self, request: ModelRequest) -> ModelResponse:
        self.call_count += 1
        if self.response is not None:
            return self.response
        return ModelResponse(
            schema_version="1",
            request_id=request.request_id,
            task_id=request.task_id,
            provider=self.provider_id,
            model="test-model",
            status=ModelResponseStatus.SUCCESS,
            output_type=BrainOutputType.PLAN,
            content="# PLAN\n\n## SUMMARY\nPlan valid summary\n\n## STEPS\nSteps\n\n## FILES\nFiles\n\n## TESTS\nTests\n\n## RISKS\nRisks",
            input_tokens=100,
            output_tokens=50,
            latency_ms=120,
            provider_request_id="prov-req-1",
        )


class FakeLedger:
    """Fake synchronous UsageLedger tracking appended records."""

    def __init__(self, should_fail: bool = False, fail_message: str = "Disk full / sensitive/path/key=SECRET123") -> None:
        self.records: list[UsageRecord] = []
        self.should_fail = should_fail
        self.fail_message = fail_message

    def append(self, record: UsageRecord) -> None:
        if self.should_fail:
            raise IOError(self.fail_message)
        self.records.append(record)


def _make_req(provider: str | None = "minimax") -> tuple[ModelRequest, Any]:
    task = ContextItem(kind=ContextKind.TASK, content="Plan something")
    budget = ContextBudget(max_context_tokens=1000)
    builder = ContextBuilder()
    context_build = builder.build([task], budget)

    req = ModelRequest(
        schema_version="1",
        request_id="req-gw-1",
        task_id="TASK-016",
        role=BrainRole.ARCHITECT,
        operation=BrainOperation.PLAN,
        instruction="Instruction",
        output_format=BrainOutputType.PLAN,
        context=context_build.selected,
        provider=provider,
        model="MiniMax-M3",
    )
    return req, context_build


@pytest.mark.asyncio
async def test_gateway_successful_invocation_and_ledger_persistence():
    """Gateway orchestrates pre-check, single provider call, validation, and ledger recording."""
    provider = FakeProvider(provider_id="minimax")
    ledger = FakeLedger()
    gateway = ModelGateway(provider=provider, ledger=ledger)

    req, context_build = _make_req()
    result = await gateway.invoke(req, context_build=context_build)

    assert isinstance(result, GatewayResult)
    assert result.response.status == ModelResponseStatus.SUCCESS
    assert result.ledger_persisted is True
    assert result.ledger_error_code is None
    assert provider.call_count == 1

    assert len(ledger.records) == 1
    rec = ledger.records[0]
    assert rec.request_id == "req-gw-1"
    assert rec.task_id == "TASK-016"
    assert rec.provider == "minimax"
    assert rec.requested_model == "MiniMax-M3"
    assert rec.actual_model == "test-model"
    assert rec.provider_input_tokens == 100
    assert rec.provider_output_tokens == 50
    assert rec.context_fingerprint == context_build.context_fingerprint


@pytest.mark.asyncio
async def test_gateway_allows_none_provider_and_invokes_configured_provider():
    """request.provider=None is accepted and uses the gateway's configured provider."""
    provider = FakeProvider(provider_id="minimax")
    gateway = ModelGateway(provider=provider)

    req, context_build = _make_req(provider=None)
    assert req.provider is None

    result = await gateway.invoke(req, context_build=context_build)
    assert result.response.status == ModelResponseStatus.SUCCESS
    assert result.ledger_persisted is None
    assert result.ledger_error_code is None
    assert provider.call_count == 1


@pytest.mark.asyncio
async def test_gateway_provider_mismatch_fails_closed_before_call():
    """Explicit provider mismatch raises ContractValidationError before invoking provider."""
    provider = FakeProvider(provider_id="minimax")
    gateway = ModelGateway(provider=provider)

    req, context_build = _make_req(provider="deepseek")  # mismatch

    with pytest.raises(ContractValidationError, match="Provider mismatch"):
        await gateway.invoke(req, context_build=context_build)

    assert provider.call_count == 0


@pytest.mark.asyncio
async def test_gateway_context_build_mismatch_fails_closed_before_call():
    """Supplied context_build that does not match request.context raises ContractValidationError."""
    provider = FakeProvider(provider_id="minimax")
    gateway = ModelGateway(provider=provider)

    req, _ = _make_req()

    other_task = ContextItem(kind=ContextKind.TASK, content="Different task")
    other_build = ContextBuilder().build([other_task], ContextBudget(max_context_tokens=1000))

    with pytest.raises(ContractValidationError, match="request.context does not match"):
        await gateway.invoke(req, context_build=other_build)

    assert provider.call_count == 0


@pytest.mark.asyncio
async def test_gateway_invalid_artifact_structure_normalizes_to_invalid_response():
    """Malformed output artifact structure on SUCCESS converts to INVALID_RESPONSE."""
    malformed_response = ModelResponse(
        schema_version="1",
        request_id="req-gw-1",
        task_id="TASK-016",
        provider="minimax",
        model="MiniMax-M3",
        status=ModelResponseStatus.SUCCESS,
        output_type=BrainOutputType.PLAN,
        content="# Just random text with no required sections",
        input_tokens=100,
        output_tokens=50,
        latency_ms=150,
    )
    provider = FakeProvider(provider_id="minimax", response=malformed_response)
    gateway = ModelGateway(provider=provider)

    req, context_build = _make_req()
    result = await gateway.invoke(req, context_build=context_build)

    assert result.response.status == ModelResponseStatus.INVALID_RESPONSE
    assert result.response.error_code == "INVALID_ARTIFACT_STRUCTURE"
    assert result.response.input_tokens == 100
    assert result.response.output_tokens == 50
    assert provider.call_count == 1


@pytest.mark.asyncio
async def test_gateway_correlation_mismatch_normalizes_to_invalid_response():
    """Corrupted response request_id converts to INVALID_RESPONSE."""
    corrupted_response = ModelResponse(
        schema_version="1",
        request_id="wrong-request-id",
        task_id="TASK-016",
        provider="minimax",
        model="MiniMax-M3",
        status=ModelResponseStatus.SUCCESS,
        output_type=BrainOutputType.PLAN,
        content="# PLAN\n\n## SUMMARY\nS\n\n## STEPS\nSt\n\n## FILES\nF\n\n## TESTS\nT\n\n## RISKS\nR",
    )
    provider = FakeProvider(provider_id="minimax", response=corrupted_response)
    gateway = ModelGateway(provider=provider)

    req, context_build = _make_req()
    result = await gateway.invoke(req, context_build=context_build)

    assert result.response.status == ModelResponseStatus.INVALID_RESPONSE
    assert result.response.error_code == "CORRELATION_ERROR"
    assert provider.call_count == 1


@pytest.mark.asyncio
async def test_gateway_ledger_failure_does_not_repeat_call_and_bounds_error_code():
    """Ledger persistence failure sets ledger_persisted=False and bounded code without leaking secrets."""
    secret_fail_msg = "Disk write failed at /private/var/keys/token=sk-999999"
    failing_ledger = FakeLedger(should_fail=True, fail_message=secret_fail_msg)
    provider = FakeProvider(provider_id="minimax")
    gateway = ModelGateway(provider=provider, ledger=failing_ledger)

    req, context_build = _make_req()
    result = await gateway.invoke(req, context_build=context_build)

    # Provider was called only once
    assert provider.call_count == 1
    # Response was still returned successfully
    assert result.response.status == ModelResponseStatus.SUCCESS
    # Ledger failure is tri-state False + bounded error code
    assert result.ledger_persisted is False
    assert result.ledger_error_code == "LEDGER_WRITE_FAILED"

    # Verify secret string was never leaked into GatewayResult
    result_dict = result.to_dict()
    assert secret_fail_msg not in str(result_dict)
    assert "sk-999999" not in str(result_dict)
    assert "/private/var" not in str(result_dict)
