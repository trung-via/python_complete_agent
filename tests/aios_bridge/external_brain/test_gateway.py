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
    """Fake provider adapter tracking complete() call counts."""

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
    """Fake UsageLedger tracking appended records."""

    def __init__(self, should_fail: bool = False) -> None:
        self.records: list[UsageRecord] = []
        self.should_fail = should_fail

    async def append(self, record: UsageRecord) -> None:
        if self.should_fail:
            raise IOError("Disk full / write failure")
        self.records.append(record)


def _make_req(provider: str = "minimax") -> tuple[ModelRequest, Any]:
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
    assert result.ledger_error is None
    assert provider.call_count == 1

    assert len(ledger.records) == 1
    rec = ledger.records[0]
    assert rec.request_id == "req-gw-1"
    assert rec.task_id == "TASK-016"
    assert rec.provider == "minimax"
    assert rec.input_tokens == 100
    assert rec.output_tokens == 50
    assert rec.total_tokens == 150
    assert rec.context_fingerprint == context_build.context_fingerprint


@pytest.mark.asyncio
async def test_gateway_provider_mismatch_fails_closed_before_call():
    """Provider mismatch raises ContractValidationError before invoking provider."""
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

    # Different context_build
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
async def test_gateway_ledger_failure_does_not_repeat_provider_call():
    """Ledger persistence failure records ledger_persisted=False without re-invoking provider."""
    provider = FakeProvider(provider_id="minimax")
    failing_ledger = FakeLedger(should_fail=True)
    gateway = ModelGateway(provider=provider, ledger=failing_ledger)

    req, context_build = _make_req()
    result = await gateway.invoke(req, context_build=context_build)

    # Provider was called only once
    assert provider.call_count == 1
    # Response was still returned successfully
    assert result.response.status == ModelResponseStatus.SUCCESS
    # Ledger failure is honestly reported
    assert result.ledger_persisted is False
    assert "Disk full" in (result.ledger_error or "")
