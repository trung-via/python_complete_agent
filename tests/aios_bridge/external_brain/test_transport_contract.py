"""Tests for External Brain ModelTransport protocol and Transport contracts."""
from __future__ import annotations

import pytest

from src.aios_bridge.external_brain import (
    ContractValidationError,
    ModelTransport,
    TransportRequest,
    TransportResult,
)


class FakeTransport:
    """Fake transport implementing ModelTransport protocol."""

    async def send(self, request: TransportRequest) -> TransportResult:
        return TransportResult(
            status_code=200,
            body={"id": "resp-001", "choices": [{"message": {"content": "ok"}}]},
            latency_ms=250,
            provider_request_id="prov-req-123",
        )


@pytest.mark.asyncio
async def test_transport_protocol_conformance():
    """ModelTransport protocol is satisfied by an async send implementation."""
    transport: ModelTransport = FakeTransport()
    req = TransportRequest(
        endpoint_url="https://api.minimax.chat/v1",
        path="/text/chatcompletion_v2",
        headers={"Authorization": "Bearer fake_token"},
        payload={"model": "MiniMax-Text-01"},
        timeout_seconds=15.0,
    )
    result = await transport.send(req)
    assert result.status_code == 200
    assert result.latency_ms == 250
    assert result.provider_request_id == "prov-req-123"
    assert isinstance(result.body, dict)


def test_transport_request_validation():
    """TransportRequest validates URL scheme and positive timeout."""
    # Valid
    req = TransportRequest(
        endpoint_url="https://api.deepseek.com",
        path="/chat/completions",
        timeout_seconds=30.0,
    )
    assert req.endpoint_url == "https://api.deepseek.com"

    # Invalid URL scheme
    with pytest.raises(ContractValidationError, match="endpoint_url must start with http:// or https://"):
        TransportRequest(endpoint_url="ftp://api.example.com", path="/")

    # Non-positive timeout
    with pytest.raises(ContractValidationError, match="timeout_seconds must be a positive number"):
        TransportRequest(endpoint_url="https://api.example.com", path="/", timeout_seconds=0)

    with pytest.raises(ContractValidationError, match="timeout_seconds must be a positive number"):
        TransportRequest(endpoint_url="https://api.example.com", path="/", timeout_seconds=-5.0)


def test_transport_result_validation():
    """TransportResult validates non-negative latency."""
    res = TransportResult(status_code=200, body="ok", latency_ms=0)
    assert res.latency_ms == 0

    with pytest.raises(ContractValidationError, match="latency_ms must be a non-negative integer"):
        TransportResult(status_code=200, body="ok", latency_ms=-10)
