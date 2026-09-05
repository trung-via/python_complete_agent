"""Model invocation and syntactic response parsing boundary for grounded QA.

TASK-132 maps an exact TASK-131 GroundedPromptPackage to the existing generic
LLMProvider boundary, invokes the provider exactly once without tools or AgentLoop,
and parses the model output against the syntactic response schema into an immutable
GroundedModelPayload.

It does not invoke AgentLoop, retry, fallback, reroute, or execute tool calls.
It does not validate context-local citations, leaf-citation minima, limitation bounds,
or construct GroundedAnswer. That remains the sole authority of TASK-129.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
from typing import Any

from src.agent.messages import LLMMessage, MessageRole
from src.product_intelligence.grounded_answer import GroundedAnswerStatus
from src.product_intelligence.grounded_prompt import GroundedPromptPackage
from src.providers.base import LLMProvider


class GroundedInvocationError(Exception):
    """Raised when grounded model invocation or response parsing fails closed."""


@dataclass(frozen=True)
class GroundedModelPayload:
    """Syntax-validated model transport payload for grounded QA.

    Contains exactly four fields:
    - status: Syntactically valid GroundedAnswerStatus mapped from model response.
    - answer_text: Decoded answer string preserved without normalization.
    - citation_ids: Decoded citation strings in model-supplied order.
    - limitations: Decoded limitation strings in model-supplied order.

    This payload represents transport-level syntax validation only. It does not
    prove context-local citation validity, satisfy leaf minima, or constitute
    a GroundedAnswer.
    """

    status: GroundedAnswerStatus
    answer_text: str
    citation_ids: tuple[str, ...]
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        if type(self.status) is not GroundedAnswerStatus:
            raise GroundedInvocationError("status must be an exact GroundedAnswerStatus")
        if type(self.answer_text) is not str:
            raise GroundedInvocationError("answer_text must be an exact str")
        if type(self.citation_ids) is not tuple or any(
            type(c) is not str for c in self.citation_ids
        ):
            raise GroundedInvocationError("citation_ids must be an exact tuple of str")
        if type(self.limitations) is not tuple or any(
            type(lim) is not str for lim in self.limitations
        ):
            raise GroundedInvocationError("limitations must be an exact tuple of str")


_REQUIRED_RESPONSE_KEYS = frozenset(
    {"status", "answer_text", "citation_ids", "limitations"}
)


def _parse_and_validate_payload(content: str) -> GroundedModelPayload:
    def _reject_duplicate_keys(pairs: list[tuple[Any, Any]]) -> dict[str, Any]:
        obj: dict[str, Any] = {}
        for key, value in pairs:
            if type(key) is not str:
                raise GroundedInvocationError("JSON object keys must be strings")
            if key in obj:
                raise GroundedInvocationError(f"Duplicate key in JSON response: {key}")
            obj[key] = value
        return obj

    try:
        data = json.loads(content, object_pairs_hook=_reject_duplicate_keys)
    except GroundedInvocationError:
        raise
    except Exception as exc:
        raise GroundedInvocationError("Response content is not valid JSON") from exc

    if type(data) is not dict:
        raise GroundedInvocationError("Response root must be a JSON object")

    if set(data.keys()) != _REQUIRED_RESPONSE_KEYS:
        raise GroundedInvocationError(
            f"Response object keys must be exactly {_REQUIRED_RESPONSE_KEYS}, got {set(data.keys())}"
        )

    status_raw = data["status"]
    if type(status_raw) is not str:
        raise GroundedInvocationError("status must be an exact str")

    try:
        status = GroundedAnswerStatus(status_raw)
    except ValueError as exc:
        raise GroundedInvocationError(
            f"status must be a valid GroundedAnswerStatus value, got {status_raw!r}"
        ) from exc

    answer_text_raw = data["answer_text"]
    if type(answer_text_raw) is not str:
        raise GroundedInvocationError("answer_text must be an exact str")

    citation_ids_raw = data["citation_ids"]
    if type(citation_ids_raw) is not list:
        raise GroundedInvocationError("citation_ids must be a JSON array")

    for idx, cid in enumerate(citation_ids_raw):
        if type(cid) is not str:
            raise GroundedInvocationError(
                f"citation_ids item at index {idx} must be an exact str, got {type(cid).__name__}"
            )

    limitations_raw = data["limitations"]
    if type(limitations_raw) is not list:
        raise GroundedInvocationError("limitations must be a JSON array")

    for idx, lim in enumerate(limitations_raw):
        if type(lim) is not str:
            raise GroundedInvocationError(
                f"limitations item at index {idx} must be an exact str, got {type(lim).__name__}"
            )

    return GroundedModelPayload(
        status=status,
        answer_text=answer_text_raw,
        citation_ids=tuple(citation_ids_raw),
        limitations=tuple(limitations_raw),
    )


async def invoke_grounded_model(
    package: GroundedPromptPackage,
    provider: LLMProvider,
) -> GroundedModelPayload:
    """Invoke LLMProvider with an exact GroundedPromptPackage and return validated payload.

    Translates package into SYSTEM and USER LLMMessage instances, calls provider.generate
    once with tools=[], and syntax-validates the response JSON object into GroundedModelPayload.
    """
    if type(package) is not GroundedPromptPackage:
        raise GroundedInvocationError("package must be an exact GroundedPromptPackage")

    if (
        provider is None
        or not hasattr(provider, "generate")
        or not callable(getattr(provider, "generate"))
    ):
        raise GroundedInvocationError("provider must provide a callable generate method")

    messages = [
        LLMMessage(role=MessageRole.SYSTEM, content=package.system_instruction),
        LLMMessage(role=MessageRole.USER, content=package.user_prompt),
    ]

    try:
        response = await provider.generate(messages, [])
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        raise GroundedInvocationError("LLM provider generation failed") from exc

    if response is None:
        raise GroundedInvocationError("Provider returned null response")

    if not hasattr(response, "tool_calls") or response.tool_calls:
        if not hasattr(response, "tool_calls"):
            raise GroundedInvocationError("Provider response missing tool_calls attribute")
        raise GroundedInvocationError("Provider returned tool calls which are not permitted")

    if not hasattr(response, "content") or response.content is None or type(response.content) is not str:
        raise GroundedInvocationError("Provider response content must be a non-null str")

    return _parse_and_validate_payload(response.content)


__all__ = [
    "GroundedInvocationError",
    "GroundedModelPayload",
    "invoke_grounded_model",
]
