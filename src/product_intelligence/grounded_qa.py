"""Canonical application composition for grounded product-intelligence QA.

TASK-133 owns only the one-pass call order across the existing context, prompt,
invocation, and final-answer authorities. It adds no validation or policy.
"""

import src.product_intelligence.canonical_rag_context as _canonical_rag_context
import src.product_intelligence.grounded_answer as _grounded_answer
import src.product_intelligence.grounded_invocation as _grounded_invocation
import src.product_intelligence.grounded_prompt as _grounded_prompt
from src.providers.base import LLMProvider as _LLMProvider


async def answer_grounded_context(
    context: _canonical_rag_context.CanonicalRagContext,
    provider: _LLMProvider,
) -> _grounded_answer.GroundedAnswer:
    """Return the validated grounded answer for one exact canonical context."""

    package = _grounded_prompt.build_grounded_prompt_package(context)
    payload = await _grounded_invocation.invoke_grounded_model(package, provider)
    answer = _grounded_answer.create_grounded_answer(
        context,
        status=payload.status,
        answer_text=payload.answer_text,
        citation_ids=payload.citation_ids,
        limitations=payload.limitations,
    )
    return answer


__all__ = ["answer_grounded_context"]
