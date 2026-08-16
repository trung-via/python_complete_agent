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
    from typing import Mapping
    assert isinstance(result.body, Mapping)


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

    with pytest.raises(ContractValidationError, match="latency_ms must be a non-negative integer"):
        TransportResult(status_code=200, body="ok", latency_ms=True)  # bool rejected


def test_transport_request_deep_immutability_and_defensive_copy():
    """TransportRequest is deeply immutable and defensively copies caller-owned structures."""
    headers = {"Authorization": "Bearer initial_token"}
    payload = {"messages": [{"role": "user", "content": "hello"}], "params": {"temperature": 0.7}}

    req = TransportRequest(
        endpoint_url="https://api.minimax.chat/v1",
        path="/chat",
        headers=headers,
        payload=payload,
    )

    # 1. Mutating original caller dict does not mutate req
    headers["Authorization"] = "Bearer modified_token"
    payload["messages"][0]["content"] = "tampered"
    payload["params"]["temperature"] = 0.0

    assert req.headers["Authorization"] == "Bearer initial_token"
    assert req.payload["messages"][0]["content"] == "hello"
    assert req.payload["params"]["temperature"] == 0.7

    # 2. Mutating headers directly on req is rejected (MappingProxyType)
    with pytest.raises(TypeError):
        req.headers["New-Header"] = "value"  # type: ignore

    # 3. Mutating payload directly on req is rejected
    with pytest.raises(TypeError):
        req.payload["new_param"] = 123  # type: ignore

    # 4. Mutating nested structures directly is rejected
    with pytest.raises(TypeError):
        req.payload["params"]["temperature"] = 1.0  # type: ignore

    with pytest.raises(TypeError):
        req.payload["messages"][0]["content"] = "tampered"  # type: ignore

    # 5. Boolean timeout rejected
    with pytest.raises(ContractValidationError, match="timeout_seconds must be a positive number"):
        TransportRequest(endpoint_url="https://api.example.com", path="/", timeout_seconds=True)

