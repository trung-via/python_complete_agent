"""Deterministic retrieval-quality evaluation over lexical retrieval and grounded answers.

TASK-164 establishes the P6.1a evaluation-contract authority. It measures lexical
retrieval precision and recall against explicit Human-authored benchmark labels, and
evaluates grounded-answer citation fidelity against those same benchmark labels.

Evaluation performs pure deterministic in-memory computation and delegates retrieval
only to TASK-122. It performs no model invocation, query planning, vector search,
re-ranking, persistence, network I/O, product-truth reconciliation, or semantic
entailment grading.
"""

from collections.abc import Iterable as _Iterable
from dataclasses import dataclass as _dataclass
from fractions import Fraction as _Fraction

from src.product_intelligence.canonical_profile import (
    CanonicalVariantProfile as _CanonicalVariantProfile,
)
from src.product_intelligence.canonical_rag_context import (
    CanonicalRagContext as _CanonicalRagContext,
    CanonicalRagHitContext as _CanonicalRagHitContext,
)
from src.product_intelligence.canonical_retrieval import (
    CanonicalProfileRetrievalError as _CanonicalProfileRetrievalError,
    CanonicalVariantRetrievalHit as _CanonicalVariantRetrievalHit,
    retrieve_canonical_variant_profiles as _retrieve_canonical_variant_profiles,
)
from src.product_intelligence.grounded_answer import (
    GroundedAnswer as _GroundedAnswer,
)

_MAX_CASE_ID_BYTES = 128
_MAX_QUESTION_BYTES = 4096
_MIN_LIMIT = 1
_MAX_LIMIT = 100


class RetrievalQualityEvaluationError(ValueError):
    """Raised when retrieval-quality evaluation input or state is outside contract."""


@_dataclass(frozen=True)
class RetrievalBenchmarkCase:
    """Frozen Human-authored benchmark test case for lexical retrieval evaluation.

    Contains exactly four fields:
    - case_id: Non-blank single-line identifier <= 128 UTF-8 bytes.
    - question: Non-blank natural-language question <= 4096 UTF-8 bytes.
    - retrieval_query: Exact query string passed unchanged to TASK-122 retrieval.
    - relevant_variant_ids: Non-empty tuple of unique non-blank variant IDs in caller order.
    """

    case_id: str
    question: str
    retrieval_query: str
    relevant_variant_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _validate_benchmark_case(self)


def _validate_benchmark_case(case: RetrievalBenchmarkCase) -> None:
    if type(case.case_id) is not str:
        raise RetrievalQualityEvaluationError("case_id must be an exact str")
    if not case.case_id.strip():
        raise RetrievalQualityEvaluationError("case_id must be non-blank")
    if case.case_id.splitlines() != [case.case_id] or "\n" in case.case_id or "\r" in case.case_id:
        raise RetrievalQualityEvaluationError("case_id must be a single-line string")
    case_id_bytes = case.case_id.encode("utf-8")
    if len(case_id_bytes) > _MAX_CASE_ID_BYTES:
        raise RetrievalQualityEvaluationError(
            f"case_id size ({len(case_id_bytes)} bytes) exceeds UTF-8 bound of {_MAX_CASE_ID_BYTES} bytes"
        )

    if type(case.question) is not str:
        raise RetrievalQualityEvaluationError("question must be an exact str")
    if not case.question.strip():
        raise RetrievalQualityEvaluationError("question must be non-blank")
    question_bytes = case.question.encode("utf-8")
    if len(question_bytes) > _MAX_QUESTION_BYTES:
        raise RetrievalQualityEvaluationError(
            f"question size ({len(question_bytes)} bytes) exceeds UTF-8 bound of {_MAX_QUESTION_BYTES} bytes"
        )

    if type(case.retrieval_query) is not str:
        raise RetrievalQualityEvaluationError("retrieval_query must be an exact str")

    if type(case.relevant_variant_ids) is not tuple:
        raise RetrievalQualityEvaluationError("relevant_variant_ids must be an exact tuple")
    if len(case.relevant_variant_ids) == 0:
        raise RetrievalQualityEvaluationError("relevant_variant_ids must be non-empty")

    seen_ids: set[str] = set()
    for idx, vid in enumerate(case.relevant_variant_ids):
        if type(vid) is not str:
            raise RetrievalQualityEvaluationError(
                f"relevant_variant_ids item at index {idx} must be an exact str"
            )
        if not vid.strip():
            raise RetrievalQualityEvaluationError(
                f"relevant_variant_ids item at index {idx} must be non-blank"
            )
        if vid in seen_ids:
            raise RetrievalQualityEvaluationError(
                f"relevant_variant_ids contains duplicate variant_id '{vid}'"
            )
        seen_ids.add(vid)


@_dataclass(frozen=True)
class RetrievalCaseEvaluation:
    """Frozen per-case evaluation result containing exact hits and Fraction metrics.

    Contains exactly eight fields:
    - case: Exact supplied RetrievalBenchmarkCase.
    - limit: Exact evaluator limit used for retrieval.
    - hits: Exact tuple of CanonicalVariantRetrievalHit returned by TASK-122.
    - true_positive_variant_ids: Tuple of variant IDs in exact hit order.
    - false_positive_variant_ids: Tuple of variant IDs in exact hit order.
    - false_negative_variant_ids: Tuple of variant IDs in exact benchmark case order.
    - precision: Exact Fraction precision (TP / retrieved_count, or Fraction(0, 1) if 0 hits).
    - recall: Exact Fraction recall (TP / relevant_count).
    """

    case: RetrievalBenchmarkCase
    limit: int
    hits: tuple[_CanonicalVariantRetrievalHit, ...]
    true_positive_variant_ids: tuple[str, ...]
    false_positive_variant_ids: tuple[str, ...]
    false_negative_variant_ids: tuple[str, ...]
    precision: _Fraction
    recall: _Fraction

    def __post_init__(self) -> None:
        _validate_case_evaluation(self)


def _validate_case_evaluation(obj: RetrievalCaseEvaluation) -> None:
    if type(obj.case) is not RetrievalBenchmarkCase:
        raise RetrievalQualityEvaluationError("case must be an exact RetrievalBenchmarkCase")
    if type(obj.limit) is not int or obj.limit is True or obj.limit is False or not (_MIN_LIMIT <= obj.limit <= _MAX_LIMIT):
        raise RetrievalQualityEvaluationError(
            f"limit must be an exact integer in the inclusive range {_MIN_LIMIT}..{_MAX_LIMIT}"
        )
    if type(obj.hits) is not tuple or any(type(h) is not _CanonicalVariantRetrievalHit for h in obj.hits):
        raise RetrievalQualityEvaluationError("hits must be an exact tuple of CanonicalVariantRetrievalHit")
    if type(obj.true_positive_variant_ids) is not tuple or any(type(v) is not str for v in obj.true_positive_variant_ids):
        raise RetrievalQualityEvaluationError("true_positive_variant_ids must be an exact tuple of str")
    if type(obj.false_positive_variant_ids) is not tuple or any(type(v) is not str for v in obj.false_positive_variant_ids):
        raise RetrievalQualityEvaluationError("false_positive_variant_ids must be an exact tuple of str")
    if type(obj.false_negative_variant_ids) is not tuple or any(type(v) is not str for v in obj.false_negative_variant_ids):
        raise RetrievalQualityEvaluationError("false_negative_variant_ids must be an exact tuple of str")
    if type(obj.precision) is not _Fraction:
        raise RetrievalQualityEvaluationError("precision must be an exact fractions.Fraction")
    if type(obj.recall) is not _Fraction:
        raise RetrievalQualityEvaluationError("recall must be an exact fractions.Fraction")


@_dataclass(frozen=True)
class RetrievalQualityReport:
    """Frozen aggregated quality report across multiple benchmark cases.

    Contains exactly seven fields:
    - limit: Exact evaluator limit used for retrieval.
    - case_evaluations: Tuple of RetrievalCaseEvaluation in caller case order.
    - true_positive_count: Sum of true positives across cases.
    - false_positive_count: Sum of false positives across cases.
    - false_negative_count: Sum of false negatives across cases.
    - micro_precision: Total TP / (TP + FP), or Fraction(0, 1) when no hits retrieved.
    - micro_recall: Total TP / (TP + FN).
    """

    limit: int
    case_evaluations: tuple[RetrievalCaseEvaluation, ...]
    true_positive_count: int
    false_positive_count: int
    false_negative_count: int
    micro_precision: _Fraction
    micro_recall: _Fraction

    def __post_init__(self) -> None:
        _validate_quality_report(self)


def _validate_quality_report(obj: RetrievalQualityReport) -> None:
    if type(obj.limit) is not int or obj.limit is True or obj.limit is False or not (_MIN_LIMIT <= obj.limit <= _MAX_LIMIT):
        raise RetrievalQualityEvaluationError(
            f"limit must be an exact integer in the inclusive range {_MIN_LIMIT}..{_MAX_LIMIT}"
        )
    if type(obj.case_evaluations) is not tuple or any(type(ce) is not RetrievalCaseEvaluation for ce in obj.case_evaluations):
        raise RetrievalQualityEvaluationError("case_evaluations must be an exact tuple of RetrievalCaseEvaluation")
    if type(obj.true_positive_count) is not int or obj.true_positive_count is True or obj.true_positive_count is False or obj.true_positive_count < 0:
        raise RetrievalQualityEvaluationError("true_positive_count must be a non-negative int")
    if type(obj.false_positive_count) is not int or obj.false_positive_count is True or obj.false_positive_count is False or obj.false_positive_count < 0:
        raise RetrievalQualityEvaluationError("false_positive_count must be a non-negative int")
    if type(obj.false_negative_count) is not int or obj.false_negative_count is True or obj.false_negative_count is False or obj.false_negative_count < 0:
        raise RetrievalQualityEvaluationError("false_negative_count must be a non-negative int")
    if type(obj.micro_precision) is not _Fraction:
        raise RetrievalQualityEvaluationError("micro_precision must be an exact fractions.Fraction")
    if type(obj.micro_recall) is not _Fraction:
        raise RetrievalQualityEvaluationError("micro_recall must be an exact fractions.Fraction")


@_dataclass(frozen=True)
class GroundedCitationFidelity:
    """Frozen fidelity evaluation linking GroundedAnswer citations to benchmark relevance.

    Contains exactly six fields:
    - case_evaluation: Exact supplied RetrievalCaseEvaluation.
    - answer: Exact supplied GroundedAnswer.
    - leaf_citation_ids: Tuple of leaf citations preserving answer.citation_ids order.
    - relevant_leaf_citation_ids: Tuple of benchmark-relevant leaf citations.
    - irrelevant_leaf_citation_ids: Tuple of benchmark-irrelevant leaf citations.
    - fidelity: Fraction(relevant_leaf_count, leaf_count) when leaf_count >= 1, else None.
    """

    case_evaluation: RetrievalCaseEvaluation
    answer: _GroundedAnswer
    leaf_citation_ids: tuple[str, ...]
    relevant_leaf_citation_ids: tuple[str, ...]
    irrelevant_leaf_citation_ids: tuple[str, ...]
    fidelity: _Fraction | None

    def __post_init__(self) -> None:
        _validate_citation_fidelity(self)


def _validate_citation_fidelity(obj: GroundedCitationFidelity) -> None:
    if type(obj.case_evaluation) is not RetrievalCaseEvaluation:
        raise RetrievalQualityEvaluationError("case_evaluation must be an exact RetrievalCaseEvaluation")
    if type(obj.answer) is not _GroundedAnswer:
        raise RetrievalQualityEvaluationError("answer must be an exact GroundedAnswer")
    if type(obj.leaf_citation_ids) is not tuple or any(type(c) is not str for c in obj.leaf_citation_ids):
        raise RetrievalQualityEvaluationError("leaf_citation_ids must be an exact tuple of str")
    if type(obj.relevant_leaf_citation_ids) is not tuple or any(type(c) is not str for c in obj.relevant_leaf_citation_ids):
        raise RetrievalQualityEvaluationError("relevant_leaf_citation_ids must be an exact tuple of str")
    if type(obj.irrelevant_leaf_citation_ids) is not tuple or any(type(c) is not str for c in obj.irrelevant_leaf_citation_ids):
        raise RetrievalQualityEvaluationError("irrelevant_leaf_citation_ids must be an exact tuple of str")
    if obj.fidelity is not None and type(obj.fidelity) is not _Fraction:
        raise RetrievalQualityEvaluationError("fidelity must be an exact fractions.Fraction or None")


def evaluate_lexical_retrieval_quality(
    profiles: _Iterable[_CanonicalVariantProfile],
    cases: _Iterable[RetrievalBenchmarkCase],
    *,
    limit: int = 10,
) -> RetrievalQualityReport:
    """Evaluate lexical retrieval quality against Human-authored benchmark cases."""
    if type(limit) is not int or limit is True or limit is False or not (_MIN_LIMIT <= limit <= _MAX_LIMIT):
        raise RetrievalQualityEvaluationError(
            f"limit must be an exact integer in the inclusive range {_MIN_LIMIT}..{_MAX_LIMIT}"
        )

    try:
        materialized_cases = tuple(cases)
    except TypeError as exc:
        raise RetrievalQualityEvaluationError(
            "cases must be an iterable of RetrievalBenchmarkCase values"
        ) from exc

    if len(materialized_cases) == 0:
        raise RetrievalQualityEvaluationError("cases must be a non-empty collection")

    seen_case_ids: set[str] = set()
    for idx, case in enumerate(materialized_cases):
        if type(case) is not RetrievalBenchmarkCase:
            raise RetrievalQualityEvaluationError(
                f"cases item at index {idx} must be an exact RetrievalBenchmarkCase, got {type(case).__name__}"
            )
        if case.case_id in seen_case_ids:
            raise RetrievalQualityEvaluationError(
                f"duplicate case_id '{case.case_id}' in benchmark cases"
            )
        seen_case_ids.add(case.case_id)

    try:
        materialized_profiles = tuple(profiles)
    except TypeError as exc:
        raise _CanonicalProfileRetrievalError(
            "profiles must be an iterable of exact CanonicalVariantProfile values"
        ) from exc

    case_evaluations: list[RetrievalCaseEvaluation] = []
    corpus_variant_ids: set[str] | None = None

    for case in materialized_cases:
        hits = _retrieve_canonical_variant_profiles(
            materialized_profiles,
            query=case.retrieval_query,
            limit=limit,
        )

        if corpus_variant_ids is None:
            corpus_variant_ids = {p.variant_id for p in materialized_profiles}
            for c in materialized_cases:
                for vid in c.relevant_variant_ids:
                    if vid not in corpus_variant_ids:
                        raise RetrievalQualityEvaluationError(
                            f"relevant_variant_id '{vid}' in case '{c.case_id}' does not exist in validated corpus"
                        )

        relevant_set = set(case.relevant_variant_ids)
        true_positive_ids = tuple(
            hit.profile.variant_id
            for hit in hits
            if hit.profile.variant_id in relevant_set
        )
        false_positive_ids = tuple(
            hit.profile.variant_id
            for hit in hits
            if hit.profile.variant_id not in relevant_set
        )
        retrieved_set = {hit.profile.variant_id for hit in hits}
        false_negative_ids = tuple(
            vid
            for vid in case.relevant_variant_ids
            if vid not in retrieved_set
        )

        retrieved_count = len(hits)
        tp_count = len(true_positive_ids)
        precision = _Fraction(0, 1) if retrieved_count == 0 else _Fraction(tp_count, retrieved_count)
        recall = _Fraction(tp_count, len(case.relevant_variant_ids))

        case_evaluations.append(
            RetrievalCaseEvaluation(
                case=case,
                limit=limit,
                hits=hits,
                true_positive_variant_ids=true_positive_ids,
                false_positive_variant_ids=false_positive_ids,
                false_negative_variant_ids=false_negative_ids,
                precision=precision,
                recall=recall,
            )
        )

    total_tp = sum(len(ce.true_positive_variant_ids) for ce in case_evaluations)
    total_fp = sum(len(ce.false_positive_variant_ids) for ce in case_evaluations)
    total_fn = sum(len(ce.false_negative_variant_ids) for ce in case_evaluations)

    retrieved_total = total_tp + total_fp
    micro_precision = _Fraction(0, 1) if retrieved_total == 0 else _Fraction(total_tp, retrieved_total)
    relevant_total = total_tp + total_fn
    micro_recall = _Fraction(total_tp, relevant_total)

    return RetrievalQualityReport(
        limit=limit,
        case_evaluations=tuple(case_evaluations),
        true_positive_count=total_tp,
        false_positive_count=total_fp,
        false_negative_count=total_fn,
        micro_precision=micro_precision,
        micro_recall=micro_recall,
    )


def evaluate_grounded_answer_citation_fidelity(
    case_evaluation: RetrievalCaseEvaluation,
    answer: _GroundedAnswer,
) -> GroundedCitationFidelity:
    """Evaluate whether an already-valid GroundedAnswer cites benchmark-relevant variants."""
    if type(case_evaluation) is not RetrievalCaseEvaluation:
        raise RetrievalQualityEvaluationError(
            f"case_evaluation must be an exact RetrievalCaseEvaluation, got {type(case_evaluation).__name__}"
        )
    if type(answer) is not _GroundedAnswer:
        raise RetrievalQualityEvaluationError(
            f"answer must be an exact GroundedAnswer, got {type(answer).__name__}"
        )

    context = answer.context
    case = case_evaluation.case

    if context.question != case.question:
        raise RetrievalQualityEvaluationError(
            "answer.context.question does not match case_evaluation.case.question"
        )
    if context.retrieval_query != case.retrieval_query:
        raise RetrievalQualityEvaluationError(
            "answer.context.retrieval_query does not match case_evaluation.case.retrieval_query"
        )
    if context.max_hits != case_evaluation.limit:
        raise RetrievalQualityEvaluationError(
            "answer.context.max_hits does not match case_evaluation.limit"
        )

    context_hits = tuple(hit_context.hit for hit_context in context.hits)
    if context_hits != case_evaluation.hits:
        raise RetrievalQualityEvaluationError(
            "answer.context hits do not match case_evaluation.hits"
        )

    valid_hit_ids: set[str] = set()
    leaf_to_variant_id: dict[str, str] = {}

    for hit_context in context.hits:
        valid_hit_ids.add(hit_context.citation_id)
        parent_vid = hit_context.hit.profile.variant_id
        for w_idx in range(1, len(hit_context.hit.witnesses) + 1):
            leaf_id = f"{hit_context.citation_id}-W{w_idx:03d}"
            leaf_to_variant_id[leaf_id] = parent_vid
        for block in hit_context.supplemental_evidence:
            leaf_to_variant_id[block.citation_id] = parent_vid

    relevant_set = set(case.relevant_variant_ids)
    leaf_citation_ids: list[str] = []
    relevant_leaf_citation_ids: list[str] = []
    irrelevant_leaf_citation_ids: list[str] = []

    for citation_id in answer.citation_ids:
        if citation_id in valid_hit_ids:
            # Hit headers are excluded from fidelity denominator
            continue
        if citation_id not in leaf_to_variant_id:
            raise RetrievalQualityEvaluationError(
                f"citation_id '{citation_id}' does not resolve as a valid leaf address in answer context"
            )
        leaf_citation_ids.append(citation_id)
        parent_vid = leaf_to_variant_id[citation_id]
        if parent_vid in relevant_set:
            relevant_leaf_citation_ids.append(citation_id)
        else:
            irrelevant_leaf_citation_ids.append(citation_id)

    leaf_count = len(leaf_citation_ids)
    if leaf_count == 0:
        fidelity = None
    else:
        fidelity = _Fraction(len(relevant_leaf_citation_ids), leaf_count)

    return GroundedCitationFidelity(
        case_evaluation=case_evaluation,
        answer=answer,
        leaf_citation_ids=tuple(leaf_citation_ids),
        relevant_leaf_citation_ids=tuple(relevant_leaf_citation_ids),
        irrelevant_leaf_citation_ids=tuple(irrelevant_leaf_citation_ids),
        fidelity=fidelity,
    )


__all__ = [
    "RetrievalQualityEvaluationError",
    "RetrievalBenchmarkCase",
    "RetrievalCaseEvaluation",
    "RetrievalQualityReport",
    "GroundedCitationFidelity",
    "evaluate_lexical_retrieval_quality",
    "evaluate_grounded_answer_citation_fidelity",
]
