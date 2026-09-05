"""Deterministic lexical query planning over canonical variant profile evidence.

TASK-134 derives one explicit TASK-122 retrieval query from a caller's
natural-language question and canonical profile corpus using only bounded
contiguous lexical spans and TASK-122 retrieval probes.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from src.product_intelligence.canonical_retrieval import (
    CanonicalRetrievalField,
    retrieve_canonical_variant_profiles,
)

if TYPE_CHECKING:
    from src.product_intelligence.canonical_profile import CanonicalVariantProfile


class GroundedQueryPlanningError(ValueError):
    """Raised when query planning input is invalid or planning fails closed."""


_IDENTITY_WITNESS_FIELDS = frozenset(
    {
        CanonicalRetrievalField.TITLE,
        CanonicalRetrievalField.BRAND,
        CanonicalRetrievalField.MODEL_SKU,
        CanonicalRetrievalField.MEDIA_VARIANT_LABEL,
    }
)

_MAX_QUESTION_BYTES = 4096
_MAX_QUESTION_TOKENS = 24
_MAX_SPAN_TOKENS = 12
_PROBE_LIMIT = 2


def plan_grounded_retrieval_query(
    profiles: Iterable[CanonicalVariantProfile],
    *,
    question: str,
) -> str:
    """Derive one deterministic TASK-122 retrieval query from question spans."""
    if type(question) is not str:
        raise GroundedQueryPlanningError("question must be an exact str")
    if not question.strip():
        raise GroundedQueryPlanningError(
            "question must contain at least one non-whitespace character"
        )
    if len(question.encode("utf-8")) > _MAX_QUESTION_BYTES:
        raise GroundedQueryPlanningError(
            "question must not exceed 4096 UTF-8 bytes"
        )

    tokens = _segment_question(question)
    if not tokens:
        raise GroundedQueryPlanningError(
            "question must contain at least one alphanumeric token"
        )
    if len(tokens) > _MAX_QUESTION_TOKENS:
        raise GroundedQueryPlanningError(
            "question must contain at most 24 alphanumeric tokens"
        )

    try:
        corpus = tuple(profiles)
    except TypeError:
        first_candidate = " ".join(tokens[: min(len(tokens), _MAX_SPAN_TOKENS)])
        retrieve_canonical_variant_profiles(
            profiles, query=first_candidate, limit=_PROBE_LIMIT
        )
        raise

    best_single: str | None = None
    best_multiple: str | None = None

    max_span_len = min(len(tokens), _MAX_SPAN_TOKENS)
    for span_len in range(max_span_len, 0, -1):
        for start in range(len(tokens) - span_len + 1):
            candidate = " ".join(tokens[start : start + span_len])
            hits = retrieve_canonical_variant_profiles(
                corpus, query=candidate, limit=_PROBE_LIMIT
            )
            hit_count = len(hits)
            if hit_count == 1:
                is_identity_bearing = any(
                    witness.field in _IDENTITY_WITNESS_FIELDS
                    for witness in hits[0].witnesses
                )
                if is_identity_bearing:
                    return candidate
                if best_single is None:
                    best_single = candidate
            elif hit_count == 2:
                if best_multiple is None:
                    best_multiple = candidate

    if best_single is not None:
        return best_single
    if best_multiple is not None:
        return best_multiple
    if len(tokens) <= _MAX_SPAN_TOKENS:
        return " ".join(tokens)
    raise GroundedQueryPlanningError(
        "no candidate produced retrieval hits and question exceeds 12 tokens"
    )


def _segment_question(question: str) -> tuple[str, ...]:
    tokens: list[str] = []
    current_run: list[str] = []
    for char in question:
        if char.isalnum():
            current_run.append(char)
        elif current_run:
            tokens.append("".join(current_run))
            current_run = []
    if current_run:
        tokens.append("".join(current_run))
    return tuple(tokens)


__all__ = [
    "GroundedQueryPlanningError",
    "plan_grounded_retrieval_query",
]
