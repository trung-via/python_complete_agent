"""Unit tests for MiniMaxOpenAIProvider adapter."""
from __future__ import annotations

from typing import Any
import pytest

from src.aios_bridge.external_brain import (
    BrainOperation,
    BrainOutputType,
    BrainRole,
    ContextItem,
    ContextKind,
    ContractValidationError,
    MiniMaxOpenAIProvider,
    ModelRequest,
    ModelResponseStatus,
    ModelTransport,
    ProviderAdapter,
    TransportRequest,
    TransportResult,
)


class MockTransport:
    """Configurable mock transport for provider testing."""

    def __init__(self, result: TransportResult | None = None) -> None:
        self.result = result
        self.sent_requests: list[TransportRequest] = []

    async def send(self, request: TransportRequest) -> TransportResult:
        self.sent_requests.append(request)
        if self.result is not None:
            return self.result
        return TransportResult(
            status_code=200,
            body={
                "id": "minimax-req-123",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": "# PLAN\n\n## SUMMARY\nPlan summary\n\n## STEPS\nSteps\n\n## FILES\nFiles\n\n## TESTS\nTests\n\n## RISKS\nRisks",
                            "reasoning_content": "Secret hidden thoughts that must be discarded",
                        },
                    }
                ],
                "usage": {"prompt_tokens": 150, "completion_tokens": 80, "total_tokens": 230},
            },
            latency_ms=320,
            provider_request_id="minimax-req-123",
        )


def _make_plan_request() -> ModelRequest:
    task = ContextItem(kind=ContextKind.TASK, content="Task description")
    return ModelRequest(
        schema_version="1",
        request_id="req-m3-01",
        task_id="TASK-016",
        role=BrainRole.ARCHITECT,
        operation=BrainOperation.PLAN,
        instruction="Generate execution plan.",
        output_format=BrainOutputType.PLAN,
        context=(task,),
        provider="minimax",
        model="MiniMax-M3",
        max_output_tokens=2048,
    )


@pytest.mark.asyncio
async def test_minimax_provider_protocol_and_success_parse():
    """Provider satisfies ProviderAdapter and parses successful completions with usage and latency."""
    mock_transport = MockTransport()
    provider = MiniMaxOpenAIProvider(api_key="secret-key-12345", transport=mock_transport)

    assert provider.provider_id == "minimax"
    assert provider.model_name == "MiniMax-M3"
    assert hasattr(provider, "invoke")

    req = _make_plan_request()
    res = await provider.invoke(req)

    assert res.status == ModelResponseStatus.SUCCESS
    assert res.request_id == "req-m3-01"
    assert res.task_id == "TASK-016"
    assert res.provider == "minimax"
    assert res.model == "MiniMax-M3"
    assert res.input_tokens == 150
    assert res.output_tokens == 80
    assert res.latency_ms == 320
    assert res.provider_request_id == "minimax-req-123"

    # Verify reasoning_content was discarded and not leaked into res.content
    assert "Secret hidden thoughts" not in (res.content or "")
    assert "# PLAN" in (res.content or "")

    # Verify wire payload
    assert len(mock_transport.sent_requests) == 1
    sent = mock_transport.sent_requests[0]
    assert sent.endpoint_url == "https://api.minimax.io/v1"
    assert sent.path == "/chat/completions"
    assert sent.headers["Authorization"] == "Bearer secret-key-12345"
    assert sent.payload["model"] == "MiniMax-M3"
    assert sent.payload["stream"] is False
    assert sent.payload["reasoning_split"] is True
    assert sent.payload["max_completion_tokens"] == 2048
    assert "tools" not in sent.payload
    assert "max_tokens" not in sent.payload


@pytest.mark.asyncio
async def test_minimax_provider_finish_reason_length_truncated():
    """finish_reason=length maps to INVALID_RESPONSE with TRUNCATED_OUTPUT."""
    mock_transport = MockTransport(
        result=TransportResult(
            status_code=200,
            body={
                "choices": [
                    {
                        "finish_reason": "length",
                        "message": {"content": "# Incomplete plan..."},
                    }
                ],
                "usage": {"prompt_tokens": 100, "completion_tokens": 500},
            },
            latency_ms=200,
        )
    )
    provider = MiniMaxOpenAIProvider(api_key="key", transport=mock_transport)
    res = await provider.invoke(_make_plan_request())

    assert res.status == ModelResponseStatus.INVALID_RESPONSE
    assert res.error_code == "TRUNCATED_OUTPUT"
    assert res.content is None
    assert res.input_tokens == 100
    assert res.output_tokens == 500


@pytest.mark.asyncio
async def test_minimax_provider_error_mappings():
    """MiniMax provider accurately maps HTTP status and MiniMax base_resp codes."""
    cases = [
        # (status_code, body, expected_status, expected_error_code)
        (401, {"error": "Unauthorized"}, ModelResponseStatus.AUTH_ERROR, "AUTH_ERROR"),
        (403, {"error": "Forbidden"}, ModelResponseStatus.AUTH_ERROR, "AUTH_ERROR"),
        (429, {"error": "Rate limit"}, ModelResponseStatus.RATE_LIMITED, "RATE_LIMITED"),
        (504, {"error": "Gateway Timeout"}, ModelResponseStatus.TIMEOUT, "TIMEOUT"),
        (500, {"error": "Server Error"}, ModelResponseStatus.UNAVAILABLE, "UNAVAILABLE"),
        (200, {"base_resp": {"status_code": 1004, "status_msg": "Invalid token"}}, ModelResponseStatus.AUTH_ERROR, "AUTH_ERROR"),
        (200, {"base_resp": {"status_code": 2049, "status_msg": "Auth failed"}}, ModelResponseStatus.AUTH_ERROR, "AUTH_ERROR"),
        (200, {"base_resp": {"status_code": 1002, "status_msg": "Rate limited"}}, ModelResponseStatus.RATE_LIMITED, "RATE_LIMITED"),
        (200, {"base_resp": {"status_code": 1001, "status_msg": "Timeout"}}, ModelResponseStatus.TIMEOUT, "TIMEOUT"),
        (200, {"base_resp": {"status_code": 1024, "status_msg": "Unavailable"}}, ModelResponseStatus.UNAVAILABLE, "UNAVAILABLE"),
        (200, {"base_resp": {"status_code": 9999, "status_msg": "Other failure"}}, ModelResponseStatus.FAILED, "MINIMAX_9999"),
        (None, {"type": "Timeout"}, ModelResponseStatus.TIMEOUT, "TIMEOUT"),
        (None, {"type": "ConnectionError"}, ModelResponseStatus.UNAVAILABLE, "UNAVAILABLE"),
    ]

    for status_code, body, expected_status, expected_error_code in cases:
        mock_transport = MockTransport(result=TransportResult(status_code=status_code, body=body, latency_ms=50))
        provider = MiniMaxOpenAIProvider(api_key="key", transport=mock_transport)
        res = await provider.invoke(_make_plan_request())

        assert res.status == expected_status, f"Failed for status_code={status_code}, body={body}"
        assert res.error_code == expected_error_code


@pytest.mark.asyncio
async def test_minimax_provider_malformed_response_handling():
    """Malformed choices list or missing content maps to INVALID_RESPONSE."""
    malformed_bodies = [
        {"choices": []},
        {"choices": [{"message": None}]},
        {"choices": [{"message": {"content": ""}}]},
        {"choices": [{"message": {"content": "   "}}]},
        "Not a dictionary",
    ]

    for body in malformed_bodies:
        mock_transport = MockTransport(result=TransportResult(status_code=200, body=body, latency_ms=50))
        provider = MiniMaxOpenAIProvider(api_key="key", transport=mock_transport)
        res = await provider.invoke(_make_plan_request())

        assert res.status == ModelResponseStatus.INVALID_RESPONSE


def test_minimax_provider_api_key_isolation_in_repr():
    """API key is private and not exposed in __repr__ or __str__."""
    key = "super-secret-production-token-9999"
    provider = MiniMaxOpenAIProvider(api_key=key, model_name="MiniMax-M3")

    repr_str = repr(provider)
    str_str = str(provider)

    assert key not in repr_str
    assert key not in str_str
    assert "MiniMax-M3" in repr_str
