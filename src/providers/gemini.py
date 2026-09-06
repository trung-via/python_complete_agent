"""Google GenAI transport adapter for the repository LLMProvider contract."""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from typing import Any, List

from google import genai
from google.genai import types

from src.agent.messages import LLMMessage, MessageRole
from src.core.errors import AgentException
from src.providers.base import LLMProvider, LLMResponse, ProviderToolCall

logger = logging.getLogger(__name__)

DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"
DEFAULT_VERTEX_LOCATION = "global"
_DEVELOPER_API_BACKEND = "developer_api"
_VERTEX_AI_BACKEND = "vertex_ai"
_SUPPORTED_BACKENDS = frozenset({_DEVELOPER_API_BACKEND, _VERTEX_AI_BACKEND})
_PLACEHOLDER_API_KEYS = frozenset(
    {
        "placeholder",
        "replace_with_your_gemini_api_key",
        "your-api-key-here",
        "your_gemini_api_key_here",
    }
)


def _configuration_error(message: str) -> AgentException:
    return AgentException(message, code="LLM_PROVIDER_ERROR", retryable=False)


class GeminiProvider(LLMProvider):
    """Single concrete Gemini adapter over the generic provider transport."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model_name: str | None = None,
        backend: str = _DEVELOPER_API_BACKEND,
        project: str | None = None,
        location: str | None = None,
    ) -> None:
        self._backend = backend
        self._explicit_api_key = api_key
        self._api_key = (
            (
                api_key
                if api_key is not None
                else os.environ.get("GEMINI_API_KEY")
            )
            if backend == _DEVELOPER_API_BACKEND
            else None
        )
        self._project = project
        self._location = location

        if model_name is not None:
            self.model_name = model_name
        else:
            environment_model = os.environ.get("GEMINI_MODEL_NAME")
            self.model_name = (
                environment_model
                if environment_model is not None and environment_model.strip()
                else DEFAULT_GEMINI_MODEL
            )

    async def generate(
        self,
        messages: List[LLMMessage],
        tools: List[dict],
    ) -> LLMResponse:
        """Make one async request and map only generic provider transport values."""
        client_kwargs = self._validated_client_kwargs()
        if not isinstance(self.model_name, str) or not self.model_name.strip():
            raise _configuration_error("Gemini model configuration is missing or invalid.")

        try:
            system_instruction, contents = self._translate_messages(messages)
            config = self._build_config(system_instruction, tools)
            client = genai.Client(**client_kwargs)
            response = await client.aio.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config,
            )
            return self._map_response(response)
        except asyncio.CancelledError:
            raise
        except AgentException:
            raise
        except Exception as exc:
            logger.error("Gemini provider request failed.")
            raise AgentException(
                "LLM Provider failure.",
                code="LLM_PROVIDER_ERROR",
                retryable=True,
            ) from exc

    def _validated_client_kwargs(self) -> dict[str, Any]:
        if type(self._backend) is not str or self._backend not in _SUPPORTED_BACKENDS:
            raise _configuration_error("Gemini backend configuration is invalid.")

        if self._backend == _DEVELOPER_API_BACKEND:
            return {"api_key": self._validated_api_key(), "vertexai": False}

        if self._explicit_api_key is not None:
            raise _configuration_error(
                "Gemini API credentials are invalid for the Vertex AI backend."
            )

        project = (
            self._project
            if self._project is not None
            else os.environ.get("GOOGLE_CLOUD_PROJECT")
        )
        if type(project) is not str or not project.strip():
            raise _configuration_error(
                "Google Cloud project configuration is missing or invalid."
            )

        if self._location is not None:
            location = self._location
        else:
            environment_location = os.environ.get("GOOGLE_CLOUD_LOCATION")
            location = (
                environment_location
                if environment_location is not None and environment_location.strip()
                else DEFAULT_VERTEX_LOCATION
            )
        if type(location) is not str or not location.strip():
            raise _configuration_error(
                "Google Cloud location configuration is missing or invalid."
            )

        return {"vertexai": True, "project": project, "location": location}

    def _validated_api_key(self) -> str:
        if not isinstance(self._api_key, str):
            raise _configuration_error("Gemini API credential is missing or invalid.")

        normalized = self._api_key.strip()
        if not normalized or normalized.casefold() in _PLACEHOLDER_API_KEYS:
            raise _configuration_error("Gemini API credential is missing or invalid.")
        return self._api_key

    @staticmethod
    def _translate_messages(
        messages: List[LLMMessage],
    ) -> tuple[types.Content | None, list[types.Content]]:
        if not isinstance(messages, list):
            raise _configuration_error("Gemini messages must be supplied as a list.")

        system_parts: list[types.Part] = []
        contents: list[types.Content] = []
        conversation_started = False

        for message in messages:
            if not isinstance(message, LLMMessage) or not isinstance(
                message.role, MessageRole
            ):
                raise _configuration_error("Gemini received an unsupported message shape.")

            if message.role is MessageRole.SYSTEM:
                if (
                    conversation_started
                    or message.tool_calls
                    or message.tool_call_id is not None
                    or message.tool_name is not None
                ):
                    raise _configuration_error(
                        "Gemini system messages must precede conversation history."
                    )
                if not isinstance(message.content, str):
                    raise _configuration_error("Gemini system message content must be text.")
                system_parts.append(types.Part.from_text(text=message.content))
                continue

            conversation_started = True

            if message.role is MessageRole.USER:
                if (
                    not isinstance(message.content, str)
                    or message.tool_calls
                    or message.tool_call_id is not None
                    or message.tool_name is not None
                ):
                    raise _configuration_error("Gemini received an invalid user message.")
                contents.append(
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=message.content)],
                    )
                )
                continue

            if message.role is MessageRole.ASSISTANT:
                if (
                    (message.content is not None and not isinstance(message.content, str))
                    or message.tool_call_id is not None
                    or message.tool_name is not None
                ):
                    raise _configuration_error(
                        "Gemini assistant message content must be text or null."
                    )
                parts: list[types.Part] = []
                if message.content is not None:
                    parts.append(types.Part.from_text(text=message.content))
                for tool_call in message.tool_calls:
                    if (
                        not isinstance(tool_call.call_id, str)
                        or not tool_call.call_id
                        or not isinstance(tool_call.name, str)
                        or not tool_call.name
                        or not isinstance(tool_call.arguments, dict)
                    ):
                        raise _configuration_error(
                            "Gemini received an invalid assistant tool call."
                        )
                    parts.append(
                        types.Part(
                            function_call=types.FunctionCall(
                                id=tool_call.call_id,
                                name=tool_call.name,
                                args=tool_call.arguments,
                            )
                        )
                    )
                if not parts:
                    raise _configuration_error("Gemini received an empty assistant message.")
                contents.append(types.Content(role="model", parts=parts))
                continue

            if message.role is MessageRole.TOOL:
                if (
                    not isinstance(message.content, str)
                    or not isinstance(message.tool_call_id, str)
                    or not message.tool_call_id
                    or not isinstance(message.tool_name, str)
                    or not message.tool_name
                    or message.tool_calls
                ):
                    raise _configuration_error("Gemini received an invalid tool response.")
                contents.append(
                    types.Content(
                        role="user",
                        parts=[
                            types.Part(
                                function_response=types.FunctionResponse(
                                    id=message.tool_call_id,
                                    name=message.tool_name,
                                    response={"result": message.content},
                                )
                            )
                        ],
                    )
                )
                continue

            raise _configuration_error("Gemini received an unsupported message role.")

        system_instruction = (
            types.Content(parts=system_parts) if system_parts else None
        )
        return system_instruction, contents

    @staticmethod
    def _build_config(
        system_instruction: types.Content | None,
        tools: List[dict],
    ) -> types.GenerateContentConfig:
        if not isinstance(tools, list):
            raise _configuration_error("Gemini tools must be supplied as a list.")

        if not tools:
            return types.GenerateContentConfig(system_instruction=system_instruction)

        declarations: list[types.FunctionDeclaration] = []
        for tool in tools:
            if not isinstance(tool, dict):
                raise _configuration_error("Gemini received an invalid tool declaration.")
            name = tool.get("name")
            description = tool.get("description")
            parameters = tool.get(
                "parameters", {"type": "object", "properties": {}}
            )
            if (
                not isinstance(name, str)
                or not name
                or not isinstance(description, str)
                or not isinstance(parameters, dict)
            ):
                raise _configuration_error("Gemini received an invalid tool declaration.")
            declarations.append(
                types.FunctionDeclaration(
                    name=name,
                    description=description,
                    parameters_json_schema=parameters,
                )
            )

        return types.GenerateContentConfig(
            system_instruction=system_instruction,
            tools=[types.Tool(function_declarations=declarations)],
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                disable=True
            ),
        )

    @staticmethod
    def _map_response(response: Any) -> LLMResponse:
        text_parts: list[str] = []
        provider_tool_calls: list[ProviderToolCall] = []
        candidates = getattr(response, "candidates", None) or []

        if candidates:
            content = getattr(candidates[0], "content", None)
            for part in getattr(content, "parts", None) or []:
                text = getattr(part, "text", None)
                if text is not None:
                    text_parts.append(text)

                function_call = getattr(part, "function_call", None)
                if function_call is not None:
                    provider_call_id = getattr(function_call, "id", None)
                    if not provider_call_id:
                        provider_call_id = str(uuid.uuid4())
                    provider_tool_calls.append(
                        ProviderToolCall(
                            provider_call_id=provider_call_id,
                            name=function_call.name,
                            arguments=dict(function_call.args or {}),
                        )
                    )

        usage_metadata = getattr(response, "usage_metadata", None)
        usage = (
            usage_metadata.model_dump(exclude_none=True)
            if usage_metadata is not None
            else {}
        )
        finish_reason = (
            str(candidates[0].finish_reason)
            if candidates and getattr(candidates[0], "finish_reason", None) is not None
            else None
        )

        return LLMResponse(
            provider="gemini",
            provider_response_id=getattr(response, "response_id", None),
            content="".join(text_parts) if text_parts else None,
            tool_calls=provider_tool_calls,
            finish_reason=finish_reason,
            usage=usage,
        )
