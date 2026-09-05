import ast
import asyncio
import inspect
import json

import pytest

import src.product_intelligence as product_intelligence
import src.product_intelligence.grounded_qa as grounded_qa
from src.product_intelligence.canonical_rag_context import CanonicalRagContext
from src.product_intelligence.grounded_answer import (
    GroundedAnswerError,
    GroundedAnswerStatus,
    create_grounded_answer,
)
from src.product_intelligence.grounded_invocation import GroundedModelPayload
from src.providers.base import LLMResponse


def _context() -> CanonicalRagContext:
    return CanonicalRagContext(
        question="What evidence is available?",
        retrieval_query="evidence",
        max_hits=1,
        max_context_utf8_bytes=4096,
        hits=(),
        truncated=False,
        omitted_evidence_blocks=0,
    )


def test_public_api_adds_only_answer_grounded_context() -> None:
    assert grounded_qa.__all__ == ["answer_grounded_context"]
    assert {
        name for name in vars(grounded_qa) if not name.startswith("_")
    } == {"answer_grounded_context"}
    assert product_intelligence.answer_grounded_context is grounded_qa.answer_grounded_context
    assert product_intelligence.__all__.count("answer_grounded_context") == 1
    assert inspect.iscoroutinefunction(grounded_qa.answer_grounded_context)


def test_exact_one_pass_order_identity_and_value_forwarding(monkeypatch) -> None:
    context = _context()
    provider = object()
    package = object()
    citation_ids = ()
    limitations = ("  exact limitation  ",)
    payload = GroundedModelPayload(
        status=GroundedAnswerStatus.INSUFFICIENT_EVIDENCE,
        answer_text="  exact answer text  ",
        citation_ids=citation_ids,
        limitations=limitations,
    )
    expected = create_grounded_answer(
        context,
        status=payload.status,
        answer_text=payload.answer_text,
        citation_ids=payload.citation_ids,
        limitations=payload.limitations,
    )
    calls = []

    def build(received_context):
        calls.append(("build", received_context))
        assert received_context is context
        return package

    async def invoke(received_package, received_provider):
        calls.append(("invoke", received_package, received_provider))
        assert received_package is package
        assert received_provider is provider
        return payload

    def create(received_context, **fields):
        calls.append(("create", received_context, fields))
        assert received_context is context
        assert fields["status"] is payload.status
        assert fields["answer_text"] is payload.answer_text
        assert fields["citation_ids"] is payload.citation_ids
        assert fields["limitations"] is payload.limitations
        return expected

    monkeypatch.setattr(grounded_qa._grounded_prompt, "build_grounded_prompt_package", build)
    monkeypatch.setattr(grounded_qa._grounded_invocation, "invoke_grounded_model", invoke)
    monkeypatch.setattr(grounded_qa._grounded_answer, "create_grounded_answer", create)

    actual = asyncio.run(grounded_qa.answer_grounded_context(context, provider))

    assert actual is expected
    assert actual.context is context
    assert [call[0] for call in calls] == ["build", "invoke", "create"]


@pytest.mark.parametrize("failing_stage", ["build", "invoke", "create"])
def test_predecessor_failure_propagates_unchanged_and_short_circuits(
    monkeypatch, failing_stage
) -> None:
    context = _context()
    package = object()
    payload = GroundedModelPayload(
        status=GroundedAnswerStatus.INSUFFICIENT_EVIDENCE,
        answer_text="No answer.",
        citation_ids=(),
        limitations=("No evidence.",),
    )
    failure = RuntimeError(failing_stage)
    calls = []

    def build(received_context):
        calls.append("build")
        if failing_stage == "build":
            raise failure
        return package

    async def invoke(received_package, received_provider):
        calls.append("invoke")
        if failing_stage == "invoke":
            raise failure
        return payload

    def create(received_context, **fields):
        calls.append("create")
        if failing_stage == "create":
            raise failure
        raise AssertionError("create must be the selected failing stage")

    monkeypatch.setattr(grounded_qa._grounded_prompt, "build_grounded_prompt_package", build)
    monkeypatch.setattr(grounded_qa._grounded_invocation, "invoke_grounded_model", invoke)
    monkeypatch.setattr(grounded_qa._grounded_answer, "create_grounded_answer", create)

    with pytest.raises(RuntimeError) as caught:
        asyncio.run(grounded_qa.answer_grounded_context(context, object()))

    assert caught.value is failure
    expected_calls = {
        "build": ["build"],
        "invoke": ["build", "invoke"],
        "create": ["build", "invoke", "create"],
    }
    assert calls == expected_calls[failing_stage]


def test_cancellation_propagates_without_final_answer_stage(monkeypatch) -> None:
    context = _context()
    package = object()
    calls = []

    def build(received_context):
        calls.append("build")
        return package

    async def invoke(received_package, received_provider):
        calls.append("invoke")
        raise asyncio.CancelledError

    def create(received_context, **fields):
        calls.append("create")
        raise AssertionError("create must not run after cancellation")

    monkeypatch.setattr(grounded_qa._grounded_prompt, "build_grounded_prompt_package", build)
    monkeypatch.setattr(grounded_qa._grounded_invocation, "invoke_grounded_model", invoke)
    monkeypatch.setattr(grounded_qa._grounded_answer, "create_grounded_answer", create)

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(grounded_qa.answer_grounded_context(context, object()))

    assert calls == ["build", "invoke"]


def test_task_129_rejects_syntax_valid_structurally_invalid_payload(monkeypatch) -> None:
    context = _context()
    package = object()
    payload = GroundedModelPayload(
        status=GroundedAnswerStatus.ANSWERED,
        answer_text="Syntactically valid but uncited.",
        citation_ids=(),
        limitations=(),
    )

    monkeypatch.setattr(
        grounded_qa._grounded_prompt,
        "build_grounded_prompt_package",
        lambda received_context: package,
    )

    async def invoke(received_package, received_provider):
        return payload

    monkeypatch.setattr(grounded_qa._grounded_invocation, "invoke_grounded_model", invoke)

    with pytest.raises(GroundedAnswerError):
        asyncio.run(grounded_qa.answer_grounded_context(context, object()))


def test_offline_composition_preserves_model_payload_values_and_context_identity() -> None:
    context = _context()
    answer_text = "  Evidence is insufficient.  "
    limitation = "  No matching canonical evidence.  "

    class Provider:
        def __init__(self):
            self.calls = 0

        async def generate(self, messages, tools):
            self.calls += 1
            return LLMResponse(
                provider="deterministic-fake",
                provider_response_id="offline-1",
                content=json.dumps(
                    {
                        "status": "INSUFFICIENT_EVIDENCE",
                        "answer_text": answer_text,
                        "citation_ids": [],
                        "limitations": [limitation],
                    }
                ),
            )

    provider = Provider()
    answer = asyncio.run(grounded_qa.answer_grounded_context(context, provider))

    assert provider.calls == 1
    assert answer.context is context
    assert answer.status is GroundedAnswerStatus.INSUFFICIENT_EVIDENCE
    assert answer.answer_text == answer_text
    assert answer.citation_ids == ()
    assert answer.limitations == (limitation,)


def test_composition_source_contains_only_three_predecessor_calls() -> None:
    source = inspect.getsource(grounded_qa.answer_grounded_context)
    tree = ast.parse(source)
    call_names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                call_names.append(node.func.attr)
            elif isinstance(node.func, ast.Name):
                call_names.append(node.func.id)

    assert sorted(call_names) == sorted(
        [
            "build_grounded_prompt_package",
            "invoke_grounded_model",
            "create_grounded_answer",
        ]
    )
