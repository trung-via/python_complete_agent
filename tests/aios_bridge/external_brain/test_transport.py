"""Unit tests for OpenAICompatibleTransport."""
from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest
import requests

from src.aios_bridge.external_brain import (
    ContractValidationError,
    ModelTransport,
    OpenAICompatibleTransport,
    TransportRequest,
    TransportResult,
)


@pytest.mark.asyncio
async def test_openai_transport_success():
    """Successful JSON response parsed into TransportResult."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"content-type": "application/json", "x-request-id": "req-xyz-123"}
    mock_resp.json.return_value = {"id": "resp-001", "choices": [{"message": {"content": "Hello"}}]}

    mock_session = MagicMock()
    mock_session.post.return_value = mock_resp

    transport = OpenAICompatibleTransport(session=mock_session)
    assert hasattr(transport, "send") and callable(transport.send)

    req = TransportRequest(
        endpoint_url="https://api.example.com",
        path="/v1/chat/completions",
        headers={"Authorization": "Bearer test-key"},
        payload={"model": "test-model", "messages": [{"role": "user", "content": "hi"}]},
    )

    res = await transport.send(req)

    assert res.status_code == 200
    assert res.body["id"] == "resp-001"
    assert res.body["choices"][0]["message"]["content"] == "Hello"
    assert res.provider_request_id == "req-xyz-123"
    assert res.latency_ms >= 0

    # Exactly 1 call (no retries)
    assert mock_session.post.call_count == 1
    call_args, call_kwargs = mock_session.post.call_args
    assert call_args[0] == "https://api.example.com/v1/chat/completions"
    assert call_kwargs["headers"]["Authorization"] == "Bearer test-key"
    assert call_kwargs["json"]["model"] == "test-model"


@pytest.mark.asyncio
async def test_openai_transport_non_json_bounded_diagnostic():
    """Non-JSON response text is bounded by max_diagnostic_bytes."""
    mock_resp = MagicMock()
    mock_resp.status_code = 502
    mock_resp.headers = {"content-type": "text/html"}
    mock_resp.text = "Bad Gateway " * 500  # Long HTML error

    mock_session = MagicMock()
    mock_session.post.return_value = mock_resp

    transport = OpenAICompatibleTransport(max_diagnostic_bytes=50, session=mock_session)

    req = TransportRequest(
        endpoint_url="https://api.example.com",
        path="/chat",
    )

    res = await transport.send(req)

    assert res.status_code == 502
    assert isinstance(res.body, str)
    assert len(res.body) <= 50
    assert "Bad Gateway" in res.body


@pytest.mark.asyncio
async def test_openai_transport_timeout_handling():
    """Timeout during HTTP execution returns normalized timeout TransportResult with single call."""
    mock_session = MagicMock()
    mock_session.post.side_effect = requests.Timeout("Connection timed out")

    transport = OpenAICompatibleTransport(session=mock_session)

    req = TransportRequest(
        endpoint_url="https://api.example.com",
        path="/chat",
        timeout_seconds=5.0,
    )

    res = await transport.send(req)

    assert res.status_code is None
    assert res.body["type"] == "Timeout"
    assert "timed out" in res.body["error"].lower()
    assert res.latency_ms >= 0
    assert mock_session.post.call_count == 1


@pytest.mark.asyncio
async def test_openai_transport_connection_error_handling():
    """Connection failure returns normalized ConnectionError TransportResult."""
    mock_session = MagicMock()
    mock_session.post.side_effect = requests.ConnectionError("Failed to establish connection")

    transport = OpenAICompatibleTransport(session=mock_session)

    req = TransportRequest(
        endpoint_url="https://api.example.com",
        path="/chat",
    )

    res = await transport.send(req)

    assert res.status_code is None
    assert res.body["type"] == "ConnectionError"
    assert res.latency_ms >= 0
    assert mock_session.post.call_count == 1


@pytest.mark.asyncio
async def test_openai_transport_validation():
    """Invalid arguments raise ContractValidationError."""
    with pytest.raises(ContractValidationError):
        OpenAICompatibleTransport(default_timeout_seconds=0)

    transport = OpenAICompatibleTransport()
    with pytest.raises(ContractValidationError):
        await transport.send({"invalid": "req"})  # type: ignore
