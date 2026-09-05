"""Pure, deterministic grounded answer boundary over canonical RAG context.

TASK-129 establishes the first Phase 6 M4 domain contract: binding an
application-level answer to an exact, immutable CanonicalRagContext. It validates
only structural invariants (exact types, text bounds, context-local citation
addresses, leaf-citation minimums, and limitation bounds).

It does not invoke models, parse prompts, call providers, access storage,
mutate canonical knowledge, or claim semantic-entailment guarantees.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.product_intelligence.canonical_rag_context import CanonicalRagContext

_MAX_ANSWER_UTF8_BYTES = 32768
_MAX_LIMITATIONS = 16
_MAX_LIMITATION_UTF8_BYTES = 2048


class GroundedAnswerError(ValueError):
    """Raised when grounded answer construction or validation fails."""


class GroundedAnswerStatus(Enum):
    """Application-answer states over canonical grounded RAG context.

    These are application-answer states only. They must not alter canonical evidence,
    constitute product-truth resolution, or imply an M2 business recommendation/approval
    decision.
    """

    ANSWERED = "ANSWERED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"


def _validate_context(context: object) -> None:
    if type(context) is not CanonicalRagContext:
        raise GroundedAnswerError("context must be an exact CanonicalRagContext")


def _validate_status(status: object) -> None:
    if type(status) is not GroundedAnswerStatus:
        raise GroundedAnswerError("status must be an exact GroundedAnswerStatus")


def _validate_answer_text(answer_text: object) -> None:
    if type(answer_text) is not str:
        raise GroundedAnswerError("answer_text must be an exact str")
    if not answer_text.strip():
        raise GroundedAnswerError("answer_text must contain at least one non-whitespace character")
    answer_bytes = answer_text.encode("utf-8")
    if len(answer_bytes) > _MAX_ANSWER_UTF8_BYTES:
        raise GroundedAnswerError(
            f"answer_text size ({len(answer_bytes)} bytes) exceeds UTF-8 bound of {_MAX_ANSWER_UTF8_BYTES} bytes"
        )


def _resolve_citation_addresses(context: CanonicalRagContext) -> tuple[set[str], set[str]]:
    valid_hit_ids: set[str] = set()
    valid_leaf_ids: set[str] = set()

    for hit_context in context.hits:
        valid_hit_ids.add(hit_context.citation_id)
        for w_idx in range(1, len(hit_context.hit.witnesses) + 1):
            valid_leaf_ids.add(f"{hit_context.citation_id}-W{w_idx:03d}")
        for block in hit_context.supplemental_evidence:
            valid_leaf_ids.add(block.citation_id)

    return valid_hit_ids, valid_leaf_ids


def _validate_citation_ids(
    citation_ids: object,
    status: GroundedAnswerStatus,
    valid_hit_ids: set[str],
    valid_leaf_ids: set[str],
) -> None:
    if type(citation_ids) is not tuple:
        raise GroundedAnswerError("citation_ids must be an exact tuple of exact str")

    valid_citations = valid_hit_ids | valid_leaf_ids
    seen_citations: set[str] = set()
    leaf_count = 0

    for idx, c in enumerate(citation_ids):
        if type(c) is not str:
            raise GroundedAnswerError(
                f"citation_id at index {idx} must be an exact str, got {type(c).__name__}"
            )
        if not c:
            raise GroundedAnswerError(
                f"citation_id at index {idx} must be a non-empty string"
            )
        if c in seen_citations:
            raise GroundedAnswerError(f"duplicate citation_id: {c}")
        seen_citations.add(c)
        if c not in valid_citations:
            raise GroundedAnswerError(
                f"citation_id '{c}' does not resolve in supplied context"
            )
        if c in valid_leaf_ids:
            leaf_count += 1

    if status is GroundedAnswerStatus.ANSWERED:
        if leaf_count < 1:
            raise GroundedAnswerError(
                "ANSWERED status requires at least one valid witness or supplemental evidence leaf citation"
            )
    elif status is GroundedAnswerStatus.CONFLICTING_EVIDENCE:
        if leaf_count < 2:
            raise GroundedAnswerError(
                "CONFLICTING_EVIDENCE status requires at least two distinct valid witness or supplemental evidence leaf citations"
            )
    elif status is GroundedAnswerStatus.INSUFFICIENT_EVIDENCE:
        pass


def _validate_limitations(limitations: object, status: GroundedAnswerStatus) -> None:
    if type(limitations) is not tuple:
        raise GroundedAnswerError("limitations must be an exact tuple of exact str")

    if len(limitations) > _MAX_LIMITATIONS:
        raise GroundedAnswerError(
            f"limitations cannot contain more than {_MAX_LIMITATIONS} items, got {len(limitations)}"
        )

    for idx, lim in enumerate(limitations):
        if type(lim) is not str:
            raise GroundedAnswerError(
                f"limitation item at index {idx} must be an exact str, got {type(lim).__name__}"
            )
        if not lim.strip():
            raise GroundedAnswerError(
                f"limitation item at index {idx} must contain at least one non-whitespace character"
            )
        lim_bytes = lim.encode("utf-8")
        if len(lim_bytes) > _MAX_LIMITATION_UTF8_BYTES:
            raise GroundedAnswerError(
                f"limitation item at index {idx} size ({len(lim_bytes)} bytes) exceeds UTF-8 bound of {_MAX_LIMITATION_UTF8_BYTES} bytes"
            )

    if status in (
        GroundedAnswerStatus.INSUFFICIENT_EVIDENCE,
        GroundedAnswerStatus.CONFLICTING_EVIDENCE,
    ):
        if len(limitations) < 1:
            raise GroundedAnswerError(
                f"{status.name} status requires at least one limitation"
            )


@dataclass(frozen=True)
class GroundedAnswer:
    """Immutable grounded answer value bound to canonical context.

    Contains exactly five required fields:
    - context: Exact CanonicalRagContext object supplied at construction.
    - status: Exact GroundedAnswerStatus application state.
    - answer_text: Exact accepted answer text.
    - citation_ids: Exact tuple of context-local citation addresses.
    - limitations: Exact tuple of bounded limitation strings.
    """

    context: CanonicalRagContext
    status: GroundedAnswerStatus
    answer_text: str
    citation_ids: tuple[str, ...]
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        _validate_context(self.context)
        _validate_status(self.status)
        _validate_answer_text(self.answer_text)
        valid_hit_ids, valid_leaf_ids = _resolve_citation_addresses(self.context)
        _validate_citation_ids(self.citation_ids, self.status, valid_hit_ids, valid_leaf_ids)
        _validate_limitations(self.limitations, self.status)


def create_grounded_answer(
    context: CanonicalRagContext,
    *,
    status: GroundedAnswerStatus,
    answer_text: str,
    citation_ids: tuple[str, ...] = (),
    limitations: tuple[str, ...] = (),
) -> GroundedAnswer:
    """Construct an immutable GroundedAnswer over canonical RAG context.

    Validates exact types, text bounds, context-local citation addresses,
    leaf-citation minimums, and limitation invariants. Retains the exact
    supplied context object without rebuilding or copying.
    """
    return GroundedAnswer(
        context=context,
        status=status,
        answer_text=answer_text,
        citation_ids=citation_ids,
        limitations=limitations,
    )


__all__ = [
    "GroundedAnswerError",
    "GroundedAnswerStatus",
    "GroundedAnswer",
    "create_grounded_answer",
]
