"""Deterministic offline coverage for the TASK-142 Gemini transport."""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from google.genai import types

from src.agent.messages import AssistantToolCall, LLMMessage, MessageRole
from src.core.errors import AgentException
import src.providers.gemini as gemini_module
from src.providers.gemini import DEFAULT_GEMINI_MODEL, GeminiProvider


OFFLINE_API_KEY = "offline-valid-value"


class FakeModels:
    def __init__(self, response: Any = None, error: BaseException | None = None) -> None:
        self.response = response
        self.error = error
        self.calls: list[dict[str, Any]] = []

    async def generate_content(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.response


class FakeClientFactory:
    def __init__(self, response: Any = None, error: BaseException | None = None) -> None:
        self.models = FakeModels(response=response, error=error)
        self.api_keys: list[str] = []

    def __call__(self, *, api_key: str) -> Any:
        self.api_keys.append(api_key)
        return SimpleNamespace(aio=SimpleNamespace(models=self.models))


def response_with_parts(*parts: types.Part) -> types.GenerateContentResponse:
    return types.GenerateContentResponse(
        response_id="offline-response",
        candidates=[
            types.Candidate(
                content=types.Content(role="model", parts=list(parts)),
                finish_reason=types.FinishReason.STOP,
            )
        ],
        usage_metadata=types.GenerateContentResponseUsageMetadata(
            prompt_token_count=2,
            candidates_token_count=3,
            total_token_count=5,
        ),
    )


def task_132_messages() -> list[LLMMessage]:
    return [
        LLMMessage(role=MessageRole.SYSTEM, content="system text"),
        LLMMessage(role=MessageRole.USER, content="user text"),
    ]


def test_dependency_and_example_configuration_are_exact() -> None:
    repository = Path(__file__).resolve().parents[2]
    requirements = (repository / "requirements.txt").read_text(encoding="utf-8")
    dependency_lines = [
        line.strip()
        for line in requirements.splitlines()
        if line.strip().casefold().startswith("google-gen")
    ]
    assert dependency_lines == ["google-genai==2.22.0"]
    assert "google-generativeai" not in requirements

    example = (repository / ".env.example").read_text(encoding="utf-8")
    assert "GEMINI_API_KEY=your_gemini_api_key_here" in example
    assert "GEMINI_MODEL_NAME=gemini-3.8-flash" in example
    assert DEFAULT_GEMINI_MODEL == "gemini-3.8-flash"


@pytest.mark.asyncio
async def test_explicit_configuration_precedes_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "ignored-environment-value")
    monkeypatch.setenv("GEMINI_MODEL_NAME", "ignored-environment-model")
    factory = FakeClientFactory(response_with_parts(types.Part(text="ok")))
    monkeypatch.setattr(gemini_module.genai, "Client", factory)

    provider = GeminiProvider(api_key=OFFLINE_API_KEY, model_name="opaque-model")
    await provider.generate(task_132_messages(), [])

    assert factory.api_keys == [OFFLINE_API_KEY]
    assert factory.models.calls[0]["model"] == "opaque-model"


@pytest.mark.asyncio
async def test_environment_fallback_and_exact_default_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", OFFLINE_API_KEY)
    monkeypatch.delenv("GEMINI_MODEL_NAME", raising=False)
    factory = FakeClientFactory(response_with_parts(types.Part(text="ok")))
    monkeypatch.setattr(gemini_module.genai, "Client", factory)

    provider = GeminiProvider()
    await provider.generate(task_132_messages(), [])

    assert factory.api_keys == [OFFLINE_API_KEY]
    assert factory.models.calls[0]["model"] == "gemini-3.8-flash"


@pytest.mark.asyncio
async def test_environment_model_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", OFFLINE_API_KEY)
    monkeypatch.setenv("GEMINI_MODEL_NAME", "environment-model")
    factory = FakeClientFactory(response_with_parts(types.Part(text="ok")))
    monkeypatch.setattr(gemini_module.genai, "Client", factory)

    await GeminiProvider().generate(task_132_messages(), [])

    assert factory.models.calls[0]["model"] == "environment-model"


@pytest.mark.asyncio
async def test_explicit_empty_credential_does_not_fall_back_to_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "ignored-environment-value")
    calls = 0

    def forbidden_client(**kwargs: Any) -> Any:
        nonlocal calls
        calls += 1
        raise AssertionError("client construction is forbidden")

    monkeypatch.setattr(gemini_module.genai, "Client", forbidden_client)

    with pytest.raises(AgentException) as exc_info:
        await GeminiProvider(api_key="").generate(task_132_messages(), [])

    assert exc_info.value.code == "LLM_PROVIDER_ERROR"
    assert calls == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid_value",
    [None, "", "   ", "your_gemini_api_key_here", "PLACEHOLDER"],
)
async def test_missing_or_placeholder_credentials_fail_before_client(
    monkeypatch: pytest.MonkeyPatch,
    invalid_value: str | None,
) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    calls = 0

    def forbidden_client(**kwargs: Any) -> Any:
        nonlocal calls
        calls += 1
        raise AssertionError("client construction is forbidden")

    monkeypatch.setattr(gemini_module.genai, "Client", forbidden_client)
    provider = GeminiProvider(api_key=invalid_value)

    with pytest.raises(AgentException) as exc_info:
        await provider.generate(task_132_messages(), [])

    assert exc_info.value.code == "LLM_PROVIDER_ERROR"
    assert exc_info.value.retryable is False
    assert calls == 0
    if invalid_value:
        assert invalid_value not in str(exc_info.value)


@pytest.mark.asyncio
async def test_task_132_transport_uses_one_async_request_and_no_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory = FakeClientFactory(response_with_parts(types.Part(text="first")))
    monkeypatch.setattr(gemini_module.genai, "Client", factory)
    monkeypatch.delenv("GEMINI_MODEL_NAME", raising=False)

    result = await GeminiProvider(api_key=OFFLINE_API_KEY).generate(
        task_132_messages(), []
    )

    assert len(factory.models.calls) == 1
    request = factory.models.calls[0]
    assert request["model"] == "gemini-3.8-flash"
    assert len(request["contents"]) == 1
    assert request["contents"][0].role == "user"
    assert request["contents"][0].parts[0].text == "user text"
    assert request["config"].system_instruction.parts[0].text == "system text"
    assert request["config"].tools is None
    assert request["config"].automatic_function_calling is None
    assert result.content == "first"


@pytest.mark.asyncio
async def test_assistant_tool_history_and_manual_declarations_are_preserved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory = FakeClientFactory(response_with_parts(types.Part(text="done")))
    monkeypatch.setattr(gemini_module.genai, "Client", factory)
    messages = [
        LLMMessage(role=MessageRole.USER, content="question"),
        LLMMessage(
            role=MessageRole.ASSISTANT,
            content="calling",
            tool_calls=[
                AssistantToolCall(
                    call_id="call-1",
                    name="lookup",
                    arguments={"query": "raw value"},
                )
            ],
        ),
        LLMMessage(
            role=MessageRole.TOOL,
            content='{"unchanged": true}',
            tool_call_id="call-1",
            tool_name="lookup",
        ),
    ]
    schema = {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    }

    await GeminiProvider(api_key=OFFLINE_API_KEY).generate(
        messages,
        [{"name": "lookup", "description": "Lookup data", "parameters": schema}],
    )

    request = factory.models.calls[0]
    assistant_call = request["contents"][1].parts[1].function_call
    assert request["contents"][1].role == "model"
    assert assistant_call.id == "call-1"
    assert assistant_call.name == "lookup"
    assert assistant_call.args == {"query": "raw value"}

    tool_response = request["contents"][2].parts[0].function_response
    assert request["contents"][2].role == "user"
    assert tool_response.id == "call-1"
    assert tool_response.name == "lookup"
    assert tool_response.response == {"result": '{"unchanged": true}'}

    config = request["config"]
    assert config.automatic_function_calling.disable is True
    assert len(config.tools) == 1
    declarations = config.tools[0].function_declarations
    assert len(declarations) == 1
    assert declarations[0].name == "lookup"
    assert declarations[0].description == "Lookup data"
    assert declarations[0].parameters_json_schema == schema


@pytest.mark.asyncio
async def test_text_and_manual_function_calls_map_without_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = response_with_parts(
        types.Part(text="first"),
        types.Part(
            function_call=types.FunctionCall(
                id="provider-call",
                name="lookup",
                args={"query": "value"},
            )
        ),
        types.Part(text="second"),
    )
    factory = FakeClientFactory(response)
    monkeypatch.setattr(gemini_module.genai, "Client", factory)

    result = await GeminiProvider(api_key=OFFLINE_API_KEY).generate(
        task_132_messages(), []
    )

    assert len(factory.models.calls) == 1
    assert result.provider == "gemini"
    assert result.provider_response_id == "offline-response"
    assert result.content == "firstsecond"
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].provider_call_id == "provider-call"
    assert result.tool_calls[0].name == "lookup"
    assert result.tool_calls[0].arguments == {"query": "value"}
    assert result.usage == {
        "candidates_token_count": 3,
        "prompt_token_count": 2,
        "total_token_count": 5,
    }


@pytest.mark.asyncio
async def test_missing_function_call_identity_uses_compatibility_uuid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = response_with_parts(
        types.Part(function_call=types.FunctionCall(name="lookup", args={}))
    )
    factory = FakeClientFactory(response)
    monkeypatch.setattr(gemini_module.genai, "Client", factory)
    monkeypatch.setattr(gemini_module.uuid, "uuid4", lambda: "compatibility-id")

    result = await GeminiProvider(api_key=OFFLINE_API_KEY).generate(
        task_132_messages(), []
    )

    assert result.tool_calls[0].provider_call_id == "compatibility-id"


@pytest.mark.asyncio
async def test_provider_error_preserves_cause_without_adapter_retry_or_key_leak(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    cause = RuntimeError("offline transport failed")
    factory = FakeClientFactory(error=cause)
    monkeypatch.setattr(gemini_module.genai, "Client", factory)

    with pytest.raises(AgentException) as exc_info:
        await GeminiProvider(api_key=OFFLINE_API_KEY).generate(task_132_messages(), [])

    assert exc_info.value.code == "LLM_PROVIDER_ERROR"
    assert exc_info.value.retryable is True
    assert exc_info.value.__cause__ is cause
    assert len(factory.models.calls) == 1
    assert OFFLINE_API_KEY not in str(exc_info.value)
    assert OFFLINE_API_KEY not in caplog.text


@pytest.mark.asyncio
async def test_cancellation_propagates_without_conversion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cancellation = asyncio.CancelledError("offline cancellation")
    factory = FakeClientFactory(error=cancellation)
    monkeypatch.setattr(gemini_module.genai, "Client", factory)

    with pytest.raises(asyncio.CancelledError) as exc_info:
        await GeminiProvider(api_key=OFFLINE_API_KEY).generate(task_132_messages(), [])

    assert exc_info.value is cancellation
    assert len(factory.models.calls) == 1


@pytest.mark.asyncio
async def test_unsupported_message_shape_fails_before_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory = FakeClientFactory(response_with_parts(types.Part(text="unused")))
    monkeypatch.setattr(gemini_module.genai, "Client", factory)
    invalid = [LLMMessage(role=MessageRole.USER, content=None)]

    with pytest.raises(AgentException) as exc_info:
        await GeminiProvider(api_key=OFFLINE_API_KEY).generate(invalid, [])

    assert exc_info.value.code == "LLM_PROVIDER_ERROR"
    assert factory.api_keys == []
    assert factory.models.calls == []
