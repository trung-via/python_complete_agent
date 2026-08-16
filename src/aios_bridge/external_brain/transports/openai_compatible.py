"""Concrete OpenAI-compatible HTTP transport implementation for External Brain."""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Mapping

import requests

from ..errors import ContractValidationError
from ..transport import ModelTransport, TransportRequest, TransportResult


_HEADER_REQUEST_ID_KEYS = (
    "x-request-id",
    "request-id",
    "minimax-request-id",
    "trace-id",
)


class OpenAICompatibleTransport:
    """
    Standard HTTP transport for OpenAI-compatible inference endpoints.
    Performs exactly one request per send() call with no retries.
    """

    def __init__(
        self,
        default_timeout_seconds: float = 60.0,
        max_diagnostic_bytes: int = 2048,
        session: requests.Session | None = None,
    ) -> None:
        if default_timeout_seconds <= 0:
            raise ContractValidationError(f"default_timeout_seconds must be positive, got: {default_timeout_seconds}")
        self._default_timeout_seconds = float(default_timeout_seconds)
        self._max_diagnostic_bytes = int(max_diagnostic_bytes)
        self._session = session

    def _get_session(self) -> requests.Session:
        return self._session if self._session is not None else requests

    def _sync_send(
        self,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        timeout: float,
    ) -> tuple[int, Any, bool, str | None]:
        """Synchronous HTTP execution run within worker thread."""
        session = self._get_session()
        resp = session.post(url, headers=headers, json=payload, timeout=timeout)

        status_code = resp.status_code
        provider_req_id = None
        for k in _HEADER_REQUEST_ID_KEYS:
            if k in resp.headers:
                provider_req_id = resp.headers[k]
                break

        body: Any
        is_json = False
        content_type = resp.headers.get("content-type", "")
        if "application/json" in content_type or resp.text.startswith(("{", "[")):
            try:
                body = resp.json()
                is_json = True
                if provider_req_id is None and isinstance(body, dict) and "id" in body and isinstance(body["id"], str):
                    provider_req_id = body["id"]
            except Exception:
                body = resp.text[: self._max_diagnostic_bytes]
                is_json = False
        else:
            body = resp.text[: self._max_diagnostic_bytes]
            is_json = False

        return status_code, body, is_json, provider_req_id

    async def send(self, request: TransportRequest) -> TransportResult:
        """
        Sends a single HTTP POST request to the target model endpoint.
        Never retries and never leaks authorization tokens in error states.
        """
        if not isinstance(request, TransportRequest):
            raise ContractValidationError(f"request must be a TransportRequest instance, got: {type(request)}")

        url = f"{request.endpoint_url.rstrip('/')}/{request.path.lstrip('/')}"
        timeout = float(request.timeout_seconds) if request.timeout_seconds else self._default_timeout_seconds

        headers = dict(request.headers)
        if "Content-Type" not in headers and "content-type" not in headers:
            headers["Content-Type"] = "application/json"

        payload = request.to_json_payload()

        t0 = time.perf_counter()
        try:
            # Wrap synchronous requests in thread with outer safety timeout
            status_code, body, is_json, provider_req_id = await asyncio.wait_for(
                asyncio.to_thread(self._sync_send, url, headers, payload, timeout),
                timeout=timeout + 5.0,
            )
            latency_ms = max(0, int((time.perf_counter() - t0) * 1000))
            return TransportResult(
                status_code=status_code,
                body=body,
                latency_ms=latency_ms,
                provider_request_id=provider_req_id,
            )

        except (requests.Timeout, asyncio.TimeoutError):
            latency_ms = max(0, int((time.perf_counter() - t0) * 1000))
            return TransportResult(
                status_code=None,
                body={"error": "Request timed out", "type": "Timeout"},
                latency_ms=latency_ms,
                provider_request_id=None,
            )

        except requests.ConnectionError:
            latency_ms = max(0, int((time.perf_counter() - t0) * 1000))
            return TransportResult(
                status_code=None,
                body={"error": "Connection failed", "type": "ConnectionError"},
                latency_ms=latency_ms,
                provider_request_id=None,
            )

        except Exception as e:
            latency_ms = max(0, int((time.perf_counter() - t0) * 1000))
            err_type = type(e).__name__
            return TransportResult(
                status_code=None,
                body={"error": f"Transport request failed ({err_type})", "type": err_type},
                latency_ms=latency_ms,
                provider_request_id=None,
            )
