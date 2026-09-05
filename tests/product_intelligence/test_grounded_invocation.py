"""Focused offline tests for TASK-132 grounded model invocation adapter."""

from __future__ import annotations

import ast
import asyncio
from dataclasses import FrozenInstanceError, fields
import inspect
import json
from typing import Any

import pytest

import src.product_intelligence as pi
from src.agent.messages import LLMMessage, MessageRole
from src.product_intelligence.canonical_rag_context import CanonicalRagContext
from src.product_intelligence.grounded_answer import GroundedAnswer, GroundedAnswerStatus
import src.product_intelligence.grounded_invocation as grounded_invocation_module
from src.product_intelligence.grounded_invocation import (
    GroundedInvocationError,
    GroundedModelPayload,
    invoke_grounded_model,
)
from src.product_intelligence.grounded_prompt import GroundedPromptPackage
from src.providers.base import LLMResponse, ProviderToolCall


class FakeProvider:
    """Deterministic offline provider test double."""

    def __init__(
        self,
        response: LLMResponse | None = None,
        error: Exception | None = None,
    ) -> None:
        self.response = response
        self.error = error
        self.calls: list[tuple[list[LLMMessage], list[dict[str, Any]]]] = []

    async def generate(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]],
    ) -> LLMResponse:
        self.calls.append((messages, tools))
        if self.error is not None:
            raise self.error
        assert self.response is not None
        return self.response


def make_package(
    system_instruction: str = "System instructions for grounded QA.",
    user_prompt: str = "QUESTION\nWhat is the product weight?\n\nCANONICAL_CONTEXT_JSON\n{}\n\nRESPONSE_SCHEMA_JSON\n{}",
) -> GroundedPromptPackage:
    context = CanonicalRagContext(
        question="What is the product weight?",
        retrieval_query="product weight",
        max_hits=5,
        max_context_utf8_bytes=32768,
        hits=(),
        truncated=False,
        omitted_evidence_blocks=0,
    )
    return GroundedPromptPackage(
        context=context,
        system_instruction=system_instruction,
        user_prompt=user_prompt,
        context_json="{}",
        response_schema_json="{}",
    )


def test_exact_public_exports_and_function_signature() -> None:
    expected = [
        "GroundedInvocationError",
        "GroundedModelPayload",
        "invoke_grounded_model",
    ]
    assert grounded_invocation_module.__all__ == expected
    for name in expected:
        assert getattr(pi, name) is getattr(grounded_invocation_module, name)
        assert name in pi.__all__

    sig = inspect.signature(invoke_grounded_model)
    assert list(sig.parameters) == ["package", "provider"]
    assert inspect.iscoroutinefunction(invoke_grounded_model)


def test_payload_layout_frozen_and_types() -> None:
    payload = GroundedModelPayload(
        status=GroundedAnswerStatus.ANSWERED,
        answer_text="Sample text",
        citation_ids=("H001-W001",),
        limitations=(),
    )
    assert [f.name for f in fields(GroundedModelPayload)] == [
        "status",
        "answer_text",
        "citation_ids",
        "limitations",
    ]
    assert payload.status is GroundedAnswerStatus.ANSWERED
    assert type(payload) is not GroundedAnswer
    assert not isinstance(payload, GroundedAnswer)

    with pytest.raises(FrozenInstanceError):
        payload.answer_text = "Mutated"  # type: ignore[misc]

    with pytest.raises(GroundedInvocationError, match="status must be an exact GroundedAnswerStatus"):
        GroundedModelPayload(
            status="ANSWERED",  # type: ignore[arg-type]
            answer_text="ok",
            citation_ids=(),
            limitations=(),
        )

    with pytest.raises(GroundedInvocationError, match="answer_text must be an exact str"):
        GroundedModelPayload(
            status=GroundedAnswerStatus.ANSWERED,
            answer_text=123,  # type: ignore[arg-type]
            citation_ids=(),
            limitations=(),
        )

    with pytest.raises(GroundedInvocationError, match="citation_ids must be an exact tuple of str"):
        GroundedModelPayload(
            status=GroundedAnswerStatus.ANSWERED,
            answer_text="ok",
            citation_ids=["H001"],  # type: ignore[arg-type]
            limitations=(),
        )

    with pytest.raises(GroundedInvocationError, match="limitations must be an exact tuple of str"):
        GroundedModelPayload(
            status=GroundedAnswerStatus.ANSWERED,
            answer_text="ok",
            citation_ids=(),
            limitations=["lim"],  # type: ignore[arg-type]
        )


@pytest.mark.asyncio
async def test_package_exact_type_required() -> None:
    provider = FakeProvider(
        response=LLMResponse(provider="fake", provider_response_id="1", content="{}")
    )

    class PackageSubclass(GroundedPromptPackage):
        pass

    pkg = make_package()
    subclass_pkg = PackageSubclass(
        context=pkg.context,
        system_instruction=pkg.system_instruction,
        user_prompt=pkg.user_prompt,
        context_json=pkg.context_json,
        response_schema_json=pkg.response_schema_json,
    )

    with pytest.raises(GroundedInvocationError, match="exact GroundedPromptPackage"):
        await invoke_grounded_model(subclass_pkg, provider)

    with pytest.raises(GroundedInvocationError, match="exact GroundedPromptPackage"):
        await invoke_grounded_model(object(), provider)  # type: ignore[arg-type]

    assert len(provider.calls) == 0


@pytest.mark.asyncio
async def test_exact_two_message_mapping_and_tools_empty_list() -> None:
    valid_content = json.dumps(
        {
            "status": "ANSWERED",
            "answer_text": "The weight is 500g.",
            "citation_ids": ["H001-W001"],
            "limitations": [],
        }
    )
    provider = FakeProvider(
        response=LLMResponse(provider="test", provider_response_id="1", content=valid_content)
    )
    package = make_package(
        system_instruction="Fixed system instructions",
        user_prompt="Framed user prompt",
    )

    payload = await invoke_grounded_model(package, provider)

    assert len(provider.calls) == 1
    messages, tools = provider.calls[0]
    assert tools == []
    assert len(messages) == 2

    assert messages[0].role == MessageRole.SYSTEM
    assert messages[0].content == "Fixed system instructions"
    assert messages[0].tool_calls == []

    assert messages[1].role == MessageRole.USER
    assert messages[1].content == "Framed user prompt"
    assert messages[1].tool_calls == []

    assert payload.status == GroundedAnswerStatus.ANSWERED
    assert payload.answer_text == "The weight is 500g."
    assert payload.citation_ids == ("H001-W001",)
    assert payload.limitations == ()


@pytest.mark.asyncio
async def test_provider_exception_fails_closed_and_preserves_cause() -> None:
    root_cause = ConnectionResetError("Connection reset by peer")
    provider = FakeProvider(error=root_cause)
    package = make_package()

    with pytest.raises(GroundedInvocationError) as exc_info:
        await invoke_grounded_model(package, provider)

    assert exc_info.value.__cause__ is root_cause
    assert len(provider.calls) == 1  # exactly one attempt, no retry


@pytest.mark.asyncio
async def test_asyncio_cancellation_propagates_directly() -> None:
    provider = FakeProvider(error=asyncio.CancelledError("task cancelled"))
    package = make_package()

    with pytest.raises(asyncio.CancelledError):
        await invoke_grounded_model(package, provider)

    assert len(provider.calls) == 1  # no retry on cancellation


@pytest.mark.asyncio
async def test_tool_calls_in_response_fails_closed() -> None:
    content = json.dumps(
        {
            "status": "ANSWERED",
            "answer_text": "Answer text",
            "citation_ids": [],
            "limitations": [],
        }
    )
    tool_call = ProviderToolCall(
        provider_call_id="call-123",
        name="web_search",
        arguments={"q": "product"},
    )
    provider = FakeProvider(
        response=LLMResponse(
            provider="test",
            provider_response_id="1",
            content=content,
            tool_calls=[tool_call],
        )
    )
    package = make_package()

    with pytest.raises(GroundedInvocationError, match="tool calls"):
        await invoke_grounded_model(package, provider)

    assert len(provider.calls) == 1


@pytest.mark.asyncio
async def test_missing_or_non_string_content_fails_closed() -> None:
    package = make_package()

    # None content
    p1 = FakeProvider(
        response=LLMResponse(provider="test", provider_response_id="1", content=None)
    )
    with pytest.raises(GroundedInvocationError, match="non-null str"):
        await invoke_grounded_model(package, p1)

    # Int content (non-string)
    p2 = FakeProvider(
        response=LLMResponse(provider="test", provider_response_id="1", content=12345)  # type: ignore[arg-type]
    )
    with pytest.raises(GroundedInvocationError, match="non-null str"):
        await invoke_grounded_model(package, p2)


@pytest.mark.asyncio
async def test_malformed_json_fails_closed() -> None:
    package = make_package()
    provider = FakeProvider(
        response=LLMResponse(provider="test", provider_response_id="1", content='{status: "broken"')
    )
    with pytest.raises(GroundedInvocationError, match="not valid JSON") as exc_info:
        await invoke_grounded_model(package, provider)

    assert isinstance(exc_info.value.__cause__, json.JSONDecodeError)


@pytest.mark.asyncio
async def test_extra_json_data_fails_closed() -> None:
    package = make_package()
    content = (
        '{"status": "ANSWERED", "answer_text": "ok", "citation_ids": [], "limitations": []}'
        ' {"status": "ANSWERED", "answer_text": "ok", "citation_ids": [], "limitations": []}'
    )
    provider = FakeProvider(
        response=LLMResponse(provider="test", provider_response_id="1", content=content)
    )
    with pytest.raises(GroundedInvocationError, match="not valid JSON") as exc_info:
        await invoke_grounded_model(package, provider)

    assert isinstance(exc_info.value.__cause__, json.JSONDecodeError)


@pytest.mark.asyncio
async def test_non_object_root_fails_closed() -> None:
    package = make_package()
    invalid_roots = [
        '["status", "ANSWERED"]',
        '"ANSWERED"',
        "42",
        "true",
        "null",
    ]
    for raw in invalid_roots:
        provider = FakeProvider(
            response=LLMResponse(provider="test", provider_response_id="1", content=raw)
        )
        with pytest.raises(GroundedInvocationError, match="root must be a JSON object"):
            await invoke_grounded_model(package, provider)


@pytest.mark.asyncio
async def test_missing_and_extra_keys_fail_closed() -> None:
    package = make_package()
    base = {
        "status": "ANSWERED",
        "answer_text": "ok",
        "citation_ids": [],
        "limitations": [],
    }

    # Missing each required key
    for key in base:
        incomplete = dict(base)
        del incomplete[key]
        provider = FakeProvider(
            response=LLMResponse(
                provider="test", provider_response_id="1", content=json.dumps(incomplete)
            )
        )
        with pytest.raises(GroundedInvocationError, match="Response object keys must be exactly"):
            await invoke_grounded_model(package, provider)

    # Extra key
    with_extra = dict(base)
    with_extra["extra_key"] = "forbidden"
    p_extra = FakeProvider(
        response=LLMResponse(
            provider="test", provider_response_id="1", content=json.dumps(with_extra)
        )
    )
    with pytest.raises(GroundedInvocationError, match="Response object keys must be exactly"):
        await invoke_grounded_model(package, p_extra)

    # Duplicate keys in JSON
    duplicate_json = (
        '{"status": "ANSWERED", "status": "INSUFFICIENT_EVIDENCE", "answer_text": "ok", '
        '"citation_ids": [], "limitations": []}'
    )
    p_dup = FakeProvider(
        response=LLMResponse(
            provider="test", provider_response_id="1", content=duplicate_json
        )
    )
    with pytest.raises(GroundedInvocationError, match="Duplicate key in JSON"):
        await invoke_grounded_model(package, p_dup)


@pytest.mark.asyncio
async def test_wrong_value_types_fail_closed() -> None:
    package = make_package()
    bad_payloads = [
        ({"status": 123, "answer_text": "ok", "citation_ids": [], "limitations": []}, "status must be an exact str"),
        ({"status": "ANSWERED", "answer_text": ["not string"], "citation_ids": [], "limitations": []}, "answer_text must be an exact str"),
        ({"status": "ANSWERED", "answer_text": "ok", "citation_ids": "H001", "limitations": []}, "citation_ids must be a JSON array"),
        ({"status": "ANSWERED", "answer_text": "ok", "citation_ids": [], "limitations": "None"}, "limitations must be a JSON array"),
        ({"status": "ANSWERED", "answer_text": "ok", "citation_ids": ["H001", 99], "limitations": []}, "citation_ids item at index 1 must be an exact str"),
        ({"status": "ANSWERED", "answer_text": "ok", "citation_ids": [], "limitations": [None]}, "limitations item at index 0 must be an exact str"),
    ]

    for data, match_str in bad_payloads:
        provider = FakeProvider(
            response=LLMResponse(
                provider="test", provider_response_id="1", content=json.dumps(data)
            )
        )
        with pytest.raises(GroundedInvocationError, match=match_str):
            await invoke_grounded_model(package, provider)


@pytest.mark.asyncio
async def test_unknown_status_value_fails_closed() -> None:
    package = make_package()
    unknown_statuses = ["PARTIAL", "UNKNOWN", "answered", "Answered", "INSUFFICIENT"]
    for bad_status in unknown_statuses:
        content = json.dumps(
            {
                "status": bad_status,
                "answer_text": "ok",
                "citation_ids": [],
                "limitations": [],
            }
        )
        provider = FakeProvider(
            response=LLMResponse(provider="test", provider_response_id="1", content=content)
        )
        with pytest.raises(GroundedInvocationError, match="status must be a valid GroundedAnswerStatus"):
            await invoke_grounded_model(package, provider)


@pytest.mark.asyncio
async def test_preserves_exact_strings_order_and_converts_to_tuples() -> None:
    package = make_package()
    raw_answer = "  Preserve leading/trailing whitespace \r\n\t and Unicode: Cân nặng 500g "
    raw_citations = ["H001-W002", "H001-W001", "H001-W001"]  # preserves order and duplicate
    raw_limitations = ["Limitation Bravo", "Limitation Alpha"]  # preserves order

    content = json.dumps(
        {
            "status": "CONFLICTING_EVIDENCE",
            "answer_text": raw_answer,
            "citation_ids": raw_citations,
            "limitations": raw_limitations,
        },
        ensure_ascii=False,
    )
    provider = FakeProvider(
        response=LLMResponse(provider="test", provider_response_id="1", content=content)
    )

    payload = await invoke_grounded_model(package, provider)

    assert payload.status is GroundedAnswerStatus.CONFLICTING_EVIDENCE
    assert payload.answer_text == raw_answer
    assert payload.citation_ids == tuple(raw_citations)
    assert payload.limitations == tuple(raw_limitations)
    assert isinstance(payload.citation_ids, tuple)
    assert isinstance(payload.limitations, tuple)


@pytest.mark.asyncio
async def test_syntax_boundary_does_not_enforce_task_129_invariants() -> None:
    """TASK-132 must stop strictly at syntax validation without duplicating TASK-129 rules."""
    package = make_package()

    # 1. Blank answer_text (fails TASK-129, but valid syntax for TASK-132)
    blank_content = json.dumps(
        {
            "status": "ANSWERED",
            "answer_text": "   ",
            "citation_ids": [],
            "limitations": [],
        }
    )
    p_blank = FakeProvider(
        response=LLMResponse(provider="test", provider_response_id="1", content=blank_content)
    )
    payload_blank = await invoke_grounded_model(package, p_blank)
    assert payload_blank.answer_text == "   "

    # 2. Oversized answer_text (>32KB fails TASK-129, but valid syntax for TASK-132)
    oversized = "a" * 40000
    p_over = FakeProvider(
        response=LLMResponse(
            provider="test",
            provider_response_id="1",
            content=json.dumps(
                {"status": "ANSWERED", "answer_text": oversized, "citation_ids": [], "limitations": []}
            ),
        )
    )
    payload_over = await invoke_grounded_model(package, p_over)
    assert payload_over.answer_text == oversized

    # 3. ANSWERED with 0 leaf citations (fails TASK-129, but valid syntax for TASK-132)
    no_citations = json.dumps(
        {
            "status": "ANSWERED",
            "answer_text": "Answer text",
            "citation_ids": [],
            "limitations": [],
        }
    )
    p_no_cit = FakeProvider(
        response=LLMResponse(provider="test", provider_response_id="1", content=no_citations)
    )
    payload_no_cit = await invoke_grounded_model(package, p_no_cit)
    assert payload_no_cit.citation_ids == ()

    # 4. Fabricated citations not in context (fails TASK-129, but valid syntax for TASK-132)
    fabricated = json.dumps(
        {
            "status": "ANSWERED",
            "answer_text": "Answer text",
            "citation_ids": ["FABRICATED-CITATION-999"],
            "limitations": [],
        }
    )
    p_fab = FakeProvider(
        response=LLMResponse(provider="test", provider_response_id="1", content=fabricated)
    )
    payload_fab = await invoke_grounded_model(package, p_fab)
    assert payload_fab.citation_ids == ("FABRICATED-CITATION-999",)

    # 5. INSUFFICIENT_EVIDENCE with 0 limitations (fails TASK-129, but valid syntax for TASK-132)
    no_lim = json.dumps(
        {
            "status": "INSUFFICIENT_EVIDENCE",
            "answer_text": "Cannot answer",
            "citation_ids": [],
            "limitations": [],
        }
    )
    p_no_lim = FakeProvider(
        response=LLMResponse(provider="test", provider_response_id="1", content=no_lim)
    )
    payload_no_lim = await invoke_grounded_model(package, p_no_lim)
    assert payload_no_lim.limitations == ()

    # 6. More than 16 limitations (fails TASK-129, but valid syntax for TASK-132)
    many_lims = [f"Limitation {i}" for i in range(25)]
    p_many_lims = FakeProvider(
        response=LLMResponse(
            provider="test",
            provider_response_id="1",
            content=json.dumps(
                {
                    "status": "INSUFFICIENT_EVIDENCE",
                    "answer_text": "Cannot answer",
                    "citation_ids": [],
                    "limitations": many_lims,
                }
            ),
        )
    )
    payload_many = await invoke_grounded_model(package, p_many_lims)
    assert len(payload_many.limitations) == 25


def test_no_agent_loop_or_forbidden_imports() -> None:
    source_path = inspect.getfile(grounded_invocation_module)
    with open(source_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())

    imported_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_names.add(node.module)
            for alias in node.names:
                imported_names.add(alias.name)

    forbidden = {
        "AgentLoop",
        "AgentController",
        "ToolExecutor",
        "ToolRegistry",
        "src.agent.loop",
        "openai",
        "anthropic",
        "google.genai",
        "requests",
        "urllib.request",
        "httpx",
        "GroundedAnswer",
        "create_grounded_answer",
    }
    intersect = imported_names & forbidden
    assert not intersect, f"Forbidden imports detected: {intersect}"
