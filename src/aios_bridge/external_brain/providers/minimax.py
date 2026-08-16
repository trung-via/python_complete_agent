"""MiniMax OpenAI-compatible ProviderAdapter implementation for External Brain."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from ..contracts import (
    BrainOutputType,
    ModelRequest,
    ModelResponse,
    ModelResponseStatus,
    get_expected_output_type,
)
from ..errors import ContractValidationError
from ..prompt import render_messages
from ..provider import ProviderAdapter
from ..transport import ModelTransport, TransportRequest, TransportResult
from ..transports.openai_compatible import OpenAICompatibleTransport


_MINIMAX_AUTH_ERROR_CODES = {1004, 2049}
_MINIMAX_RATE_LIMIT_ERROR_CODES = {1002, 2056}
_MINIMAX_TIMEOUT_ERROR_CODES = {1001}
_MINIMAX_UNAVAILABLE_ERROR_CODES = {1000, 1024, 1033}


class MiniMaxOpenAIProvider:
    """
    MiniMax inference provider adapter using the OpenAI-compatible chat completions interface.
    Implements ProviderAdapter protocol.
    """

    provider_id: str = "minimax"

    def __init__(
        self,
        api_key: str,
        model_name: str = "MiniMax-M3",
        base_url: str = "https://api.minimax.io/v1",
        path: str = "/chat/completions",
        transport: ModelTransport | None = None,
    ) -> None:
        if not api_key or not isinstance(api_key, str) or not api_key.strip():
            raise ContractValidationError("api_key must be a non-empty string")
        if not model_name or not isinstance(model_name, str):
            raise ContractValidationError("model_name must be a non-empty string")
        if not base_url or not isinstance(base_url, str):
            raise ContractValidationError("base_url must be a non-empty string")

        self._api_key = api_key.strip()
        self._model_name = model_name.strip()
        self._base_url = base_url.strip()
        self._path = path.strip()
        self._transport = transport if transport is not None else OpenAICompatibleTransport()

    @property
    def model_name(self) -> str:
        return self._model_name

    def __repr__(self) -> str:
        return (
            f"MiniMaxOpenAIProvider(provider_id={self.provider_id!r}, "
            f"model_name={self._model_name!r}, base_url={self._base_url!r})"
        )

    def _extract_usage(self, body: Any) -> tuple[int | None, int | None]:
        """Safely extracts input_tokens and output_tokens from response payload."""
        if not isinstance(body, Mapping):
            return None, None
        usage_data = body.get("usage")
        if not isinstance(usage_data, Mapping):
            return None, None

        prompt_tokens = usage_data.get("prompt_tokens")
        completion_tokens = usage_data.get("completion_tokens")

        input_tok = prompt_tokens if isinstance(prompt_tokens, int) and not isinstance(prompt_tokens, bool) and prompt_tokens >= 0 else None
        output_tok = completion_tokens if isinstance(completion_tokens, int) and not isinstance(completion_tokens, bool) and completion_tokens >= 0 else None

        return input_tok, output_tok

    async def invoke(self, request: ModelRequest) -> ModelResponse:
        """
        Submits a ModelRequest to MiniMax via the underlying transport.
        Returns a normalized, contract-compliant ModelResponse.
        """
        if not isinstance(request, ModelRequest):
            raise ContractValidationError(f"request must be a ModelRequest instance, got: {type(request)}")

        # Build messages and payload
        messages = render_messages(request)
        payload: dict[str, Any] = {
            "model": self._model_name,
            "messages": messages,
            "stream": False,
            "reasoning_split": True,
        }
        if request.max_output_tokens is not None:
            payload["max_completion_tokens"] = request.max_output_tokens

        transport_req = TransportRequest(
            endpoint_url=self._base_url,
            path=self._path,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            payload=payload,
        )

        transport_res: TransportResult = await self._transport.send(transport_req)

        status_code = transport_res.status_code
        body = transport_res.body
        latency_ms = transport_res.latency_ms
        provider_req_id = transport_res.provider_request_id
        input_tokens, output_tokens = self._extract_usage(body)

        # 1. Transport-level connection / timeout failures
        if status_code is None:
            err_type = body.get("type", "") if isinstance(body, Mapping) else ""
            if err_type == "Timeout":
                return ModelResponse(
                    schema_version="1",
                    request_id=request.request_id,
                    task_id=request.task_id,
                    provider=self.provider_id,
                    model=self._model_name,
                    status=ModelResponseStatus.TIMEOUT,
                    output_type=None,
                    content=None,
                    latency_ms=latency_ms,
                    error_code="TIMEOUT",
                    error_message="Request to MiniMax timed out",
                )
            return ModelResponse(
                schema_version="1",
                request_id=request.request_id,
                task_id=request.task_id,
                provider=self.provider_id,
                model=self._model_name,
                status=ModelResponseStatus.UNAVAILABLE,
                output_type=None,
                content=None,
                latency_ms=latency_ms,
                error_code="UNAVAILABLE",
                error_message=f"Transport connection failed: {body.get('error', 'Network error') if isinstance(body, Mapping) else 'Network error'}",
            )

        # 2. Inspect MiniMax base_resp if present in JSON body
        base_resp_code = None
        base_resp_msg = None
        if isinstance(body, Mapping) and "base_resp" in body and isinstance(body["base_resp"], Mapping):
            base_resp_code = body["base_resp"].get("status_code")
            base_resp_msg = body["base_resp"].get("status_msg")

        if base_resp_code is not None and base_resp_code != 0:
            if base_resp_code in _MINIMAX_AUTH_ERROR_CODES:
                return ModelResponse(
                    schema_version="1",
                    request_id=request.request_id,
                    task_id=request.task_id,
                    provider=self.provider_id,
                    model=self._model_name,
                    status=ModelResponseStatus.AUTH_ERROR,
                    output_type=None,
                    content=None,
                    latency_ms=latency_ms,
                    provider_request_id=provider_req_id,
                    error_code="AUTH_ERROR",
                    error_message=f"MiniMax auth error (code {base_resp_code}): {base_resp_msg or 'Authentication failed'}",
                )
            if base_resp_code in _MINIMAX_RATE_LIMIT_ERROR_CODES:
                return ModelResponse(
                    schema_version="1",
                    request_id=request.request_id,
                    task_id=request.task_id,
                    provider=self.provider_id,
                    model=self._model_name,
                    status=ModelResponseStatus.RATE_LIMITED,
                    output_type=None,
                    content=None,
                    latency_ms=latency_ms,
                    provider_request_id=provider_req_id,
                    error_code="RATE_LIMITED",
                    error_message=f"MiniMax rate limit exceeded (code {base_resp_code}): {base_resp_msg or 'Rate limit exceeded'}",
                )
            if base_resp_code in _MINIMAX_TIMEOUT_ERROR_CODES:
                return ModelResponse(
                    schema_version="1",
                    request_id=request.request_id,
                    task_id=request.task_id,
                    provider=self.provider_id,
                    model=self._model_name,
                    status=ModelResponseStatus.TIMEOUT,
                    output_type=None,
                    content=None,
                    latency_ms=latency_ms,
                    provider_request_id=provider_req_id,
                    error_code="TIMEOUT",
                    error_message=f"MiniMax timeout (code {base_resp_code}): {base_resp_msg or 'Timed out'}",
                )
            if base_resp_code in _MINIMAX_UNAVAILABLE_ERROR_CODES:
                return ModelResponse(
                    schema_version="1",
                    request_id=request.request_id,
                    task_id=request.task_id,
                    provider=self.provider_id,
                    model=self._model_name,
                    status=ModelResponseStatus.UNAVAILABLE,
                    output_type=None,
                    content=None,
                    latency_ms=latency_ms,
                    provider_request_id=provider_req_id,
                    error_code="UNAVAILABLE",
                    error_message=f"MiniMax service unavailable (code {base_resp_code}): {base_resp_msg or 'Unavailable'}",
                )
            return ModelResponse(
                schema_version="1",
                request_id=request.request_id,
                task_id=request.task_id,
                provider=self.provider_id,
                model=self._model_name,
                status=ModelResponseStatus.FAILED,
                output_type=None,
                content=None,
                latency_ms=latency_ms,
                provider_request_id=provider_req_id,
                error_code=f"MINIMAX_{base_resp_code}",
                error_message=f"MiniMax error (code {base_resp_code}): {base_resp_msg or 'Unknown error'}",
            )

        # 3. HTTP status error mappings
        if status_code in (401, 403):
            return ModelResponse(
                schema_version="1",
                request_id=request.request_id,
                task_id=request.task_id,
                provider=self.provider_id,
                model=self._model_name,
                status=ModelResponseStatus.AUTH_ERROR,
                output_type=None,
                content=None,
                latency_ms=latency_ms,
                provider_request_id=provider_req_id,
                error_code="AUTH_ERROR",
                error_message=f"HTTP {status_code} Authentication failed",
            )

        if status_code == 429:
            return ModelResponse(
                schema_version="1",
                request_id=request.request_id,
                task_id=request.task_id,
                provider=self.provider_id,
                model=self._model_name,
                status=ModelResponseStatus.RATE_LIMITED,
                output_type=None,
                content=None,
                latency_ms=latency_ms,
                provider_request_id=provider_req_id,
                error_code="RATE_LIMITED",
                error_message="HTTP 429 Rate limit exceeded",
            )

        if status_code in (408, 504):
            return ModelResponse(
                schema_version="1",
                request_id=request.request_id,
                task_id=request.task_id,
                provider=self.provider_id,
                model=self._model_name,
                status=ModelResponseStatus.TIMEOUT,
                output_type=None,
                content=None,
                latency_ms=latency_ms,
                provider_request_id=provider_req_id,
                error_code="TIMEOUT",
                error_message=f"HTTP {status_code} Gateway timeout",
            )

        if status_code >= 500:
            return ModelResponse(
                schema_version="1",
                request_id=request.request_id,
                task_id=request.task_id,
                provider=self.provider_id,
                model=self._model_name,
                status=ModelResponseStatus.UNAVAILABLE,
                output_type=None,
                content=None,
                latency_ms=latency_ms,
                provider_request_id=provider_req_id,
                error_code="UNAVAILABLE",
                error_message=f"HTTP {status_code} Server error",
            )

        if status_code != 200:
            return ModelResponse(
                schema_version="1",
                request_id=request.request_id,
                task_id=request.task_id,
                provider=self.provider_id,
                model=self._model_name,
                status=ModelResponseStatus.FAILED,
                output_type=None,
                content=None,
                latency_ms=latency_ms,
                provider_request_id=provider_req_id,
                error_code=f"HTTP_{status_code}",
                error_message=f"HTTP request returned status {status_code}",
            )

        # 4. Parse successful HTTP 200 payload
        if not isinstance(body, Mapping):
            return ModelResponse(
                schema_version="1",
                request_id=request.request_id,
                task_id=request.task_id,
                provider=self.provider_id,
                model=self._model_name,
                status=ModelResponseStatus.INVALID_RESPONSE,
                output_type=None,
                content=None,
                latency_ms=latency_ms,
                provider_request_id=provider_req_id,
                error_code="MALFORMED_RESPONSE",
                error_message="Expected JSON dictionary in response body",
            )

        choices = body.get("choices")
        if not isinstance(choices, (Sequence, list, tuple)) or isinstance(choices, (str, bytes)) or len(choices) == 0:
            return ModelResponse(
                schema_version="1",
                request_id=request.request_id,
                task_id=request.task_id,
                provider=self.provider_id,
                model=self._model_name,
                status=ModelResponseStatus.INVALID_RESPONSE,
                output_type=None,
                content=None,
                latency_ms=latency_ms,
                provider_request_id=provider_req_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                error_code="MALFORMED_RESPONSE",
                error_message="Missing or empty choices list in response",
            )

        first_choice = choices[0]
        if not isinstance(first_choice, Mapping):
            return ModelResponse(
                schema_version="1",
                request_id=request.request_id,
                task_id=request.task_id,
                provider=self.provider_id,
                model=self._model_name,
                status=ModelResponseStatus.INVALID_RESPONSE,
                output_type=None,
                content=None,
                latency_ms=latency_ms,
                provider_request_id=provider_req_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                error_code="MALFORMED_RESPONSE",
                error_message="First choice is not a dictionary",
            )

        finish_reason = first_choice.get("finish_reason")
        if finish_reason == "length":
            return ModelResponse(
                schema_version="1",
                request_id=request.request_id,
                task_id=request.task_id,
                provider=self.provider_id,
                model=self._model_name,
                status=ModelResponseStatus.INVALID_RESPONSE,
                output_type=None,
                content=None,
                latency_ms=latency_ms,
                provider_request_id=provider_req_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                error_code="TRUNCATED_OUTPUT",
                error_message="Model response was truncated due to max_completion_tokens limit",
            )

        message = first_choice.get("message")
        if not isinstance(message, Mapping):
            return ModelResponse(
                schema_version="1",
                request_id=request.request_id,
                task_id=request.task_id,
                provider=self.provider_id,
                model=self._model_name,
                status=ModelResponseStatus.INVALID_RESPONSE,
                output_type=None,
                content=None,
                latency_ms=latency_ms,
                provider_request_id=provider_req_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                error_code="MALFORMED_RESPONSE",
                error_message="Choice missing message object",
            )

        content = message.get("content")
        if content is None or not isinstance(content, str) or not content.strip():
            return ModelResponse(
                schema_version="1",
                request_id=request.request_id,
                task_id=request.task_id,
                provider=self.provider_id,
                model=self._model_name,
                status=ModelResponseStatus.INVALID_RESPONSE,
                output_type=None,
                content=None,
                latency_ms=latency_ms,
                provider_request_id=provider_req_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                error_code="EMPTY_CONTENT",
                error_message="Choice returned empty or non-string message content",
            )

        # 5. Success
        expected_output = get_expected_output_type(request.operation)
        return ModelResponse(
            schema_version="1",
            request_id=request.request_id,
            task_id=request.task_id,
            provider=self.provider_id,
            model=self._model_name,
            status=ModelResponseStatus.SUCCESS,
            output_type=expected_output,
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            provider_request_id=provider_req_id,
        )
