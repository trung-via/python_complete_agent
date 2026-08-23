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
            provider_request_id="minimax-header-123",
        )


def _make_plan_request(model: str | None = "MiniMax-M3") -> ModelRequest:
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
        model=model,
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
    # Body id takes precedence over header id
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
async def test_minimax_provider_model_validation():
    """Provider validates request.model: None or matching succeeds; mismatch fails before transport."""
    mock_transport = MockTransport()
    provider = MiniMaxOpenAIProvider(api_key="key", transport=mock_transport)

    # 1. request.model is None -> succeeds using configured model
    req_none = _make_plan_request(model=None)
    res_none = await provider.invoke(req_none)
    assert res_none.status == ModelResponseStatus.SUCCESS
    assert len(mock_transport.sent_requests) == 1

    # 2. request.model matches configured model -> succeeds
    req_match = _make_plan_request(model="MiniMax-M3")
    res_match = await provider.invoke(req_match)
    assert res_match.status == ModelResponseStatus.SUCCESS
    assert len(mock_transport.sent_requests) == 2

    # 3. request.model mismatch -> fails before any transport call
    req_mismatch = _make_plan_request(model="OtherModel-7B")
    with pytest.raises(ContractValidationError, match="Model mismatch"):
        await provider.invoke(req_mismatch)

    assert len(mock_transport.sent_requests) == 2  # No new transport calls


@pytest.mark.asyncio
async def test_minimax_provider_request_id_precedence():
    """Provider prefers JSON body 'id' when present, falling back to transport header ID."""
    # Case A: Both body id and header id present -> body id wins
    mock_transport_both = MockTransport(
        result=TransportResult(
            status_code=200,
            body={
                "id": "body-id-preferred",
                "choices": [{"finish_reason": "stop", "message": {"content": "# PLAN\n## SUMMARY\nS\n## STEPS\nSt\n## FILES\nF\n## TESTS\nT\n## RISKS\nR"}}],
            },
            latency_ms=100,
            provider_request_id="header-id-fallback",
        )
    )
    provider_both = MiniMaxOpenAIProvider(api_key="key", transport=mock_transport_both)
    res_both = await provider_both.invoke(_make_plan_request())
    assert res_both.provider_request_id == "body-id-preferred"

    # Case B: Body id absent -> header id used
    mock_transport_hdr = MockTransport(
        result=TransportResult(
            status_code=200,
            body={
                "choices": [{"finish_reason": "stop", "message": {"content": "# PLAN\n## SUMMARY\nS\n## STEPS\nSt\n## FILES\nF\n## TESTS\nT\n## RISKS\nR"}}],
            },
            latency_ms=100,
            provider_request_id="header-id-fallback",
        )
    )
    provider_hdr = MiniMaxOpenAIProvider(api_key="key", transport=mock_transport_hdr)
    res_hdr = await provider_hdr.invoke(_make_plan_request())
    assert res_hdr.provider_request_id == "header-id-fallback"


@pytest.mark.asyncio
async def test_minimax_provider_embedded_reasoning_fails_closed():
    """Embedded <think>...</think> in message.content fails closed to INVALID_RESPONSE with content=None."""
    think_contents = [
        "<think>Let me ponder this internally</think>\n# PLAN\n## SUMMARY\nPlan summary",
        "<THINK>Uppercase think envelope</THINK>\n## SUMMARY\nPlan",
        "<think>Unclosed thinking block",
    ]

    for think_text in think_contents:
        mock_transport = MockTransport(
            result=TransportResult(
                status_code=200,
                body={
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "message": {"content": think_text},
                        }
                    ],
                    "usage": {"prompt_tokens": 100, "completion_tokens": 50},
                },
                latency_ms=200,
            )
        )
        provider = MiniMaxOpenAIProvider(api_key="key", transport=mock_transport)
        res = await provider.invoke(_make_plan_request())

        assert res.status == ModelResponseStatus.INVALID_RESPONSE
        assert res.error_code == "REASONING_CONTENT_LEAK"
        assert res.content is None
        # Thinking text must not leak into error_message
        assert "ponder" not in (res.error_message or "")
        assert "thinking" not in (res.error_message or "").lower() or "embedded reasoning markers" in (res.error_message or "")


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
async def test_minimax_provider_error_mappings_and_bounded_metadata():
    """MiniMax provider maps codes and never surfaces unbounded or sensitive status_msg."""
    secret_status_msg = "Bearer token=sk-super-secret-123 failed for user root at /secret/path"

    cases = [
        # (status_code, body, expected_status, expected_error_code)
        (401, {"error": "Unauthorized"}, ModelResponseStatus.AUTH_ERROR, "AUTH_ERROR"),
        (403, {"error": "Forbidden"}, ModelResponseStatus.AUTH_ERROR, "AUTH_ERROR"),
        (429, {"error": "Rate limit"}, ModelResponseStatus.RATE_LIMITED, "RATE_LIMITED"),
        (504, {"error": "Gateway Timeout"}, ModelResponseStatus.TIMEOUT, "TIMEOUT"),
        (500, {"error": "Server Error"}, ModelResponseStatus.UNAVAILABLE, "UNAVAILABLE"),
        (200, {"base_resp": {"status_code": 1004, "status_msg": secret_status_msg}}, ModelResponseStatus.AUTH_ERROR, "AUTH_ERROR"),
        (200, {"base_resp": {"status_code": 2049, "status_msg": secret_status_msg}}, ModelResponseStatus.AUTH_ERROR, "AUTH_ERROR"),
        (200, {"base_resp": {"status_code": 1002, "status_msg": "Rate limited"}}, ModelResponseStatus.RATE_LIMITED, "RATE_LIMITED"),
        (200, {"base_resp": {"status_code": 1001, "status_msg": "Timeout"}}, ModelResponseStatus.TIMEOUT, "TIMEOUT"),
        (200, {"base_resp": {"status_code": 1024, "status_msg": "Unavailable"}}, ModelResponseStatus.UNAVAILABLE, "UNAVAILABLE"),
        (200, {"base_resp": {"status_code": 9999, "status_msg": secret_status_msg}}, ModelResponseStatus.FAILED, "MINIMAX_9999"),
        (None, {"type": "Timeout"}, ModelResponseStatus.TIMEOUT, "TIMEOUT"),
        (None, {"type": "ConnectionError"}, ModelResponseStatus.UNAVAILABLE, "UNAVAILABLE"),
    ]

    for status_code, body, expected_status, expected_error_code in cases:
        mock_transport = MockTransport(result=TransportResult(status_code=status_code, body=body, latency_ms=50))
        provider = MiniMaxOpenAIProvider(api_key="key", transport=mock_transport)
        res = await provider.invoke(_make_plan_request())

        assert res.status == expected_status, f"Failed for status_code={status_code}, body={body}"
        assert res.error_code == expected_error_code
        # Ensure secret_status_msg was never reflected into error_message
        assert secret_status_msg not in (res.error_message or "")
        assert "sk-super-secret" not in (res.error_message or "")


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


@pytest.mark.asyncio
async def test_minimax_provider_timeout_configurability_and_validation():
    """Provider supports configurable positive finite timeout_seconds forwarded to TransportRequest."""
    # 1. Default timeout is 30.0
    mock_transport_default = MockTransport()
    provider_default = MiniMaxOpenAIProvider(api_key="key", transport=mock_transport_default)
    assert provider_default.timeout_seconds == 30.0
    await provider_default.invoke(_make_plan_request())
    assert len(mock_transport_default.sent_requests) == 1
    assert mock_transport_default.sent_requests[0].timeout_seconds == 30.0

    # 2. Explicit custom timeout (e.g. 90.0 for real-task proof)
    mock_transport_custom = MockTransport()
    provider_custom = MiniMaxOpenAIProvider(
        api_key="key",
        transport=mock_transport_custom,
        timeout_seconds=90.0,
    )
    assert provider_custom.timeout_seconds == 90.0
    await provider_custom.invoke(_make_plan_request())
    assert len(mock_transport_custom.sent_requests) == 1
    assert mock_transport_custom.sent_requests[0].timeout_seconds == 90.0

    # 2b. Integer timeout (e.g. 90) normalizes to float 90.0
    mock_transport_int = MockTransport()
    provider_int = MiniMaxOpenAIProvider(
        api_key="key",
        transport=mock_transport_int,
        timeout_seconds=90,
    )
    assert isinstance(provider_int.timeout_seconds, float)
    assert provider_int.timeout_seconds == 90.0
    await provider_int.invoke(_make_plan_request())
    assert len(mock_transport_int.sent_requests) == 1
    assert mock_transport_int.sent_requests[0].timeout_seconds == 90.0

    # 3. Invalid timeout values fail during __init__ with ContractValidationError
    invalid_timeouts = [
        0,
        0.0,
        -1,
        -10.5,
        True,
        False,
        float("nan"),
        float("inf"),
        float("-inf"),
        "90.0",
        None,
    ]
    for invalid_val in invalid_timeouts:
        with pytest.raises(ContractValidationError, match="timeout_seconds must be a positive finite number"):
            MiniMaxOpenAIProvider(api_key="key", timeout_seconds=invalid_val)  # type: ignore

    # 4. Extreme large/negative integers fail during __init__ with ContractValidationError (C1 / AIP-2 / P18-1)
    for extreme_int in [10**10000, -(10**10000)]:
        with pytest.raises(ContractValidationError, match="timeout_seconds cannot be converted to a valid finite float"):
            MiniMaxOpenAIProvider(api_key="key", timeout_seconds=extreme_int)


def test_minimax_provider_api_key_isolation_in_repr():
    """API key is private and not exposed in __repr__ or __str__, while timeout is visible."""
    key = "super-secret-production-token-9999"
    provider = MiniMaxOpenAIProvider(api_key=key, model_name="MiniMax-M3", timeout_seconds=45.0)

    repr_str = repr(provider)
    str_str = str(provider)

    assert key not in repr_str
    assert key not in str_str
    assert "MiniMax-M3" in repr_str
    assert "45" in repr_str
    assert "45" in str_str
@pytest.mark.asyncio
async def test_minimax_provider_passes_max_completion_tokens_8192():
    """Prove ModelRequest with max_output_tokens=8192 sets payload max_completion_tokens=8192 unchanged."""
    transport = MockTransport()
    provider = MiniMaxOpenAIProvider(
        api_key="test-key",
        model_name="MiniMax-M3",
        transport=transport,
    )
    request = ModelRequest(
        schema_version="1",
        request_id="req-tokens-8192",
        task_id="TASK-064",
        role=BrainRole.ARCHITECT,
        operation=BrainOperation.PLAN,
        instruction="Plan the task",
        context=[ContextItem(kind=ContextKind.TASK, content="Task context")],
        output_format=BrainOutputType.PLAN,
        provider="minimax",
        model="MiniMax-M3",
        max_input_tokens=256,
        max_output_tokens=8192,
    )
    response = await provider.invoke(request)
    assert response.status == ModelResponseStatus.SUCCESS
    assert len(transport.sent_requests) == 1
    sent_payload = transport.sent_requests[0].payload
    assert sent_payload.get("max_completion_tokens") == 8192
