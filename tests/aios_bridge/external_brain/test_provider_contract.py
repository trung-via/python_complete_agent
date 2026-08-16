"""Tests for External Brain ProviderAdapter protocol and decoupling."""
from __future__ import annotations

import pytest

from src.aios_bridge.external_brain import (
    BrainOperation,
    BrainOutputType,
    BrainRole,
    ModelRequest,
    ModelResponse,
    ModelResponseStatus,
    ProviderAdapter,
)
from src.providers.base import LLMProvider, LLMResponse


class FakeExternalBrainProvider:
    """Fake provider implementing ProviderAdapter without inheriting LLMProvider."""

    def __init__(self, provider_id: str = "fake_brain") -> None:
        self._provider_id = provider_id
        self.invoked_requests: list[ModelRequest] = []

    @property
    def provider_id(self) -> str:
        return self._provider_id

    async def invoke(self, request: ModelRequest) -> ModelResponse:
        self.invoked_requests.append(request)
        return ModelResponse(
            schema_version="1",
            request_id=request.request_id,
            task_id=request.task_id,
            provider=self.provider_id,
            model="fake-model-01",
            status=ModelResponseStatus.SUCCESS,
            output_type=request.output_format,
            content="# SUMMARY\nFake plan\n## STEPS\n1. Run\n## FILES\na.py\n## TESTS\ntest\n## RISKS\nnone",
            input_tokens=50,
            output_tokens=100,
            latency_ms=150,
        )


@pytest.mark.asyncio
async def test_provider_adapter_protocol_conformance():
    """ProviderAdapter protocol is satisfied by a pure async adapter without runtime LLMProvider coupling."""
    provider: ProviderAdapter = FakeExternalBrainProvider()
    assert provider.provider_id == "fake_brain"

    req = ModelRequest(
        schema_version="1",
        request_id="req-test-01",
        task_id="TASK-014",
        role=BrainRole.ARCHITECT,
        operation=BrainOperation.PLAN,
        instruction="Create plan",
        context=(),
        output_format=BrainOutputType.PLAN,
    )

    resp = await provider.invoke(req)
    assert resp.status == ModelResponseStatus.SUCCESS
    assert resp.request_id == "req-test-01"
    assert resp.task_id == "TASK-014"
    assert resp.output_type == BrainOutputType.PLAN
    assert not hasattr(provider, "generate")


def test_runtime_llm_provider_remains_untouched():
    """Verify src.providers.base.LLMProvider remains decoupled and untouched."""
    # Ensure LLMProvider methods and LLMResponse fields remain as expected for Python Agent runtime
    assert hasattr(LLMProvider, "generate")
    assert "content" in LLMResponse.__dataclass_fields__
    assert "tool_calls" in LLMResponse.__dataclass_fields__
    assert "finish_reason" in LLMResponse.__dataclass_fields__
    assert "usage" in LLMResponse.__dataclass_fields__


