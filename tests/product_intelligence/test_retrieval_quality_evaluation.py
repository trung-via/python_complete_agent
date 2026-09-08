"""Focused regressions for TASK-164 Retrieval-Quality Evaluation contract."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timezone
from fractions import Fraction
import inspect
import pytest

import src.product_intelligence as pi
from src.product_intelligence import (
    CanonicalProfileFactEvidence,
    CanonicalProfileMediaEvidence,
    CanonicalProfileObservation,
    CanonicalProfileRetrievalError,
    CanonicalRagContext,
    CanonicalRagEvidenceBlock,
    CanonicalRagEvidenceKind,
    CanonicalRagHitContext,
    CanonicalVariantProfile,
    CanonicalVariantRetrievalHit,
    GroundedAnswer,
    GroundedAnswerStatus,
    GroundedCitationFidelity,
    RetrievalBenchmarkCase,
    RetrievalCaseEvaluation,
    RetrievalQualityEvaluationError,
    RetrievalQualityReport,
    SourceObservationIdentity,
    build_canonical_rag_context,
    create_grounded_answer,
    evaluate_grounded_answer_citation_fidelity,
    evaluate_lexical_retrieval_quality,
    retrieve_canonical_variant_profiles,
)
import src.product_intelligence.retrieval_quality_evaluation as rqe

OBSERVED_AT = datetime(2026, 9, 8, tzinfo=timezone.utc)

EXPECTED_PUBLIC_NAMES = {
    "RetrievalQualityEvaluationError",
    "RetrievalBenchmarkCase",
    "RetrievalCaseEvaluation",
    "RetrievalQualityReport",
    "GroundedCitationFidelity",
    "evaluate_lexical_retrieval_quality",
    "evaluate_grounded_answer_citation_fidelity",
}


def make_member(name: str, platform: str = "Shopee") -> SourceObservationIdentity:
    return SourceObservationIdentity(
        source_pack_id=f"pack-{name}",
        platform=platform,
        source_product_id=f"prod-{name}",
        product_url=f"https://example.com/p/{name}",
        observed_at=OBSERVED_AT,
    )


def make_profile(
    variant_id: str,
    family_id: str = "fam-1",
    title: str = "Ergonomic Mechanical Keyboard",
    brand: str = "KeyChron",
    model_sku: str = "K2-V2",
    description_text: str | None = None,
) -> CanonicalVariantProfile:
    if description_text is None:
        description_text = f"Description for {variant_id}"
    m = make_member(f"m-{variant_id}")
    obs = CanonicalProfileObservation(
        member=m,
        collector="collector",
        title=title,
        shop_name="Official Tech Store",
        brand=brand,
        model_sku=model_sku,
        description_text=description_text,
    )
    return CanonicalVariantProfile(
        variant_id=variant_id,
        family_id=family_id,
        members=(m,),
        observations=(obs,),
        fact_evidence=(),
        media_evidence=(),
    )


# ---------------------------------------------------------------------------
# 1. Exact module and package public API
# ---------------------------------------------------------------------------


def test_retrieval_quality_evaluation_module_exports():
    actual_dir = {name for name in dir(rqe) if not name.startswith("_")}
    assert actual_dir == EXPECTED_PUBLIC_NAMES
    assert set(rqe.__all__) == EXPECTED_PUBLIC_NAMES


def test_product_intelligence_package_exports():
    for name in EXPECTED_PUBLIC_NAMES:
        assert hasattr(pi, name), f"Missing export in src.product_intelligence: {name}"
        assert getattr(pi, name) is getattr(rqe, name)
        assert name in pi.__all__


# ---------------------------------------------------------------------------
# 2. RetrievalBenchmarkCase immutability and validation
# ---------------------------------------------------------------------------


def test_benchmark_case_fields_and_immutability():
    case = RetrievalBenchmarkCase(
        case_id="case-001",
        question="Which keyboard has RGB backlighting?",
        retrieval_query="keyboard rgb",
        relevant_variant_ids=("v-001", "v-002"),
    )
    case_fields = [f.name for f in fields(case)]
    assert case_fields == ["case_id", "question", "retrieval_query", "relevant_variant_ids"]

    with pytest.raises(FrozenInstanceError):
        case.case_id = "new-id"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        case.question = "new question"  # type: ignore[misc]


def test_benchmark_case_preserves_strings_and_order():
    case = RetrievalBenchmarkCase(
        case_id="  case-padded  ",
        question="  padded question?  ",
        retrieval_query="  raw query  ",
        relevant_variant_ids=("v-002", "v-001"),
    )
    assert case.case_id == "  case-padded  "
    assert case.question == "  padded question?  "
    assert case.retrieval_query == "  raw query  "
    assert case.relevant_variant_ids == ("v-002", "v-001")


def test_benchmark_case_case_id_validation():
    # Non-str
    with pytest.raises(RetrievalQualityEvaluationError, match="case_id must be an exact str"):
        RetrievalBenchmarkCase(123, "q", "query", ("v-1",))  # type: ignore[arg-type]

    # Blank / whitespace
    with pytest.raises(RetrievalQualityEvaluationError, match="case_id must be non-blank"):
        RetrievalBenchmarkCase("   ", "q", "query", ("v-1",))

    # Multi-line
    with pytest.raises(RetrievalQualityEvaluationError, match="single-line"):
        RetrievalBenchmarkCase("case-1\ncase-2", "q", "query", ("v-1",))
    with pytest.raises(RetrievalQualityEvaluationError, match="single-line"):
        RetrievalBenchmarkCase("case-1\r", "q", "query", ("v-1",))

    # > 128 UTF-8 bytes
    long_id = "a" * 129
    with pytest.raises(RetrievalQualityEvaluationError, match="exceeds UTF-8 bound of 128"):
        RetrievalBenchmarkCase(long_id, "q", "query", ("v-1",))


def test_benchmark_case_question_validation():
    # Non-str
    with pytest.raises(RetrievalQualityEvaluationError, match="question must be an exact str"):
        RetrievalBenchmarkCase("c1", 999, "query", ("v-1",))  # type: ignore[arg-type]

    # Blank
    with pytest.raises(RetrievalQualityEvaluationError, match="question must be non-blank"):
        RetrievalBenchmarkCase("c1", "   \t\n  ", "query", ("v-1",))

    # > 4096 UTF-8 bytes
    long_q = "x" * 4097
    with pytest.raises(RetrievalQualityEvaluationError, match="exceeds UTF-8 bound of 4096"):
        RetrievalBenchmarkCase("c1", long_q, "query", ("v-1",))


def test_benchmark_case_retrieval_query_validation():
    # Non-str
    with pytest.raises(RetrievalQualityEvaluationError, match="retrieval_query must be an exact str"):
        RetrievalBenchmarkCase("c1", "q", None, ("v-1",))  # type: ignore[arg-type]


def test_benchmark_case_relevant_variant_ids_validation():
    # Non-tuple
    with pytest.raises(RetrievalQualityEvaluationError, match="relevant_variant_ids must be an exact tuple"):
        RetrievalBenchmarkCase("c1", "q", "query", ["v-1"])  # type: ignore[arg-type]

    # Empty
    with pytest.raises(RetrievalQualityEvaluationError, match="relevant_variant_ids must be non-empty"):
        RetrievalBenchmarkCase("c1", "q", "query", ())

    # Non-str item
    with pytest.raises(RetrievalQualityEvaluationError, match="must be an exact str"):
        RetrievalBenchmarkCase("c1", "q", "query", (123,))  # type: ignore[arg-type]

    # Blank item
    with pytest.raises(RetrievalQualityEvaluationError, match="must be non-blank"):
        RetrievalBenchmarkCase("c1", "q", "query", ("v-1", "  "))

    # Duplicates
    with pytest.raises(RetrievalQualityEvaluationError, match="duplicate variant_id"):
        RetrievalBenchmarkCase("c1", "q", "query", ("v-1", "v-2", "v-1"))


# ---------------------------------------------------------------------------
# 3. Value objects immutability and shapes
# ---------------------------------------------------------------------------


def test_case_evaluation_immutability_and_fields():
    case = RetrievalBenchmarkCase("c1", "q", "query", ("v-1",))
    ce = RetrievalCaseEvaluation(
        case=case,
        limit=10,
        hits=(),
        true_positive_variant_ids=(),
        false_positive_variant_ids=(),
        false_negative_variant_ids=("v-1",),
        precision=Fraction(0, 1),
        recall=Fraction(0, 1),
    )
    assert [f.name for f in fields(ce)] == [
        "case",
        "limit",
        "hits",
        "true_positive_variant_ids",
        "false_positive_variant_ids",
        "false_negative_variant_ids",
        "precision",
        "recall",
    ]
    with pytest.raises(FrozenInstanceError):
        ce.limit = 5  # type: ignore[misc]


def test_quality_report_immutability_and_fields():
    report = RetrievalQualityReport(
        limit=10,
        case_evaluations=(),
        true_positive_count=0,
        false_positive_count=0,
        false_negative_count=0,
        micro_precision=Fraction(0, 1),
        micro_recall=Fraction(0, 1),
    )
    assert [f.name for f in fields(report)] == [
        "limit",
        "case_evaluations",
        "true_positive_count",
        "false_positive_count",
        "false_negative_count",
        "micro_precision",
        "micro_recall",
    ]
    with pytest.raises(FrozenInstanceError):
        report.limit = 20  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 4. evaluate_lexical_retrieval_quality validation & delegation
# ---------------------------------------------------------------------------


def test_evaluate_lexical_limit_validation():
    p = make_profile("v-1", title="Wireless Mouse")
    case = RetrievalBenchmarkCase("c1", "q", "mouse", ("v-1",))

    # Reject non-int
    with pytest.raises(RetrievalQualityEvaluationError, match="limit must be an exact integer"):
        evaluate_lexical_retrieval_quality([p], [case], limit="10")  # type: ignore[arg-type]

    # Reject bool
    with pytest.raises(RetrievalQualityEvaluationError, match="limit must be an exact integer"):
        evaluate_lexical_retrieval_quality([p], [case], limit=True)  # type: ignore[arg-type]

    # Reject out of bounds
    with pytest.raises(RetrievalQualityEvaluationError, match="inclusive range 1..100"):
        evaluate_lexical_retrieval_quality([p], [case], limit=0)
    with pytest.raises(RetrievalQualityEvaluationError, match="inclusive range 1..100"):
        evaluate_lexical_retrieval_quality([p], [case], limit=101)


def test_evaluate_lexical_cases_validation():
    p = make_profile("v-1", title="Wireless Mouse")

    # Non-iterable cases
    with pytest.raises(RetrievalQualityEvaluationError, match="cases must be an iterable"):
        evaluate_lexical_retrieval_quality([p], 123)  # type: ignore[arg-type]

    # Empty cases
    with pytest.raises(RetrievalQualityEvaluationError, match="cases must be a non-empty"):
        evaluate_lexical_retrieval_quality([p], [])

    # Non-RetrievalBenchmarkCase item
    with pytest.raises(RetrievalQualityEvaluationError, match="must be an exact RetrievalBenchmarkCase"):
        evaluate_lexical_retrieval_quality([p], ["not-a-case"])  # type: ignore[list-item]

    # Duplicate case IDs
    case1 = RetrievalBenchmarkCase("dup-id", "q1", "mouse", ("v-1",))
    case2 = RetrievalBenchmarkCase("dup-id", "q2", "mouse", ("v-1",))
    with pytest.raises(RetrievalQualityEvaluationError, match="duplicate case_id 'dup-id'"):
        evaluate_lexical_retrieval_quality([p], [case1, case2])


def test_evaluate_lexical_materializes_iterables_once():
    p = make_profile("v-1", title="Wireless Mouse")
    case = RetrievalBenchmarkCase("c1", "q", "mouse", ("v-1",))

    def profile_gen():
        yield p

    def case_gen():
        yield case

    p_iter = profile_gen()
    c_iter = case_gen()

    report = evaluate_lexical_retrieval_quality(p_iter, c_iter)
    assert report.limit == 10
    assert len(report.case_evaluations) == 1
    assert report.case_evaluations[0].case.case_id == "c1"

    # Both generators should be exhausted because they were consumed
    assert list(p_iter) == []
    assert list(c_iter) == []


def test_evaluate_lexical_delegates_to_task_122_once_per_case(monkeypatch):
    p1 = make_profile("v-1", title="Mechanical Keyboard")
    p2 = make_profile("v-2", title="Wireless Mouse")
    corpus = (p1, p2)

    case1 = RetrievalBenchmarkCase("c1", "q1", "keyboard", ("v-1",))
    case2 = RetrievalBenchmarkCase("c2", "q2", "mouse", ("v-2",))

    calls = []
    real_retrieve = retrieve_canonical_variant_profiles

    def spy_retrieve(profiles, *, query, limit):
        calls.append((profiles, query, limit))
        return real_retrieve(profiles, query=query, limit=limit)

    monkeypatch.setattr(rqe, "_retrieve_canonical_variant_profiles", spy_retrieve)

    report = evaluate_lexical_retrieval_quality(corpus, [case1, case2], limit=5)

    assert len(calls) == 2
    # Verify exact materialized corpus passed unchanged
    assert calls[0][0] == corpus
    assert calls[0][1] == "keyboard"
    assert calls[0][2] == 5

    assert calls[1][0] == corpus
    assert calls[1][1] == "mouse"
    assert calls[1][2] == 5

    assert len(report.case_evaluations) == 2


def test_evaluate_lexical_propagates_task_122_corpus_errors_unchanged():
    case = RetrievalBenchmarkCase("c1", "q", "keyboard", ("v-1",))

    # Invalid profile in corpus (not a CanonicalVariantProfile)
    with pytest.raises(CanonicalProfileRetrievalError, match="profiles must contain exact CanonicalVariantProfile"):
        evaluate_lexical_retrieval_quality(["not-a-profile"], [case])  # type: ignore[list-item]

    # Duplicate variant_ids in corpus
    p1 = make_profile("v-dup", title="Keyboard One")
    p2 = make_profile("v-dup", title="Keyboard Two")
    with pytest.raises(CanonicalProfileRetrievalError, match="duplicate variant_id"):
        evaluate_lexical_retrieval_quality([p1, p2], [case])


def test_evaluate_lexical_propagates_task_122_query_errors_unchanged():
    p = make_profile("v-1", title="Mechanical Keyboard")

    # Invalid query: >12 tokens
    long_query = "one two three four five six seven eight nine ten eleven twelve thirteen"
    case = RetrievalBenchmarkCase("c1", "q", long_query, ("v-1",))

    with pytest.raises(CanonicalProfileRetrievalError, match="query must contain at most 12 normalized tokens"):
        evaluate_lexical_retrieval_quality([p], [case])

    # Invalid query: whitespace / no tokens
    blank_query_case = RetrievalBenchmarkCase("c2", "q", "   ", ("v-1",))
    with pytest.raises(CanonicalProfileRetrievalError, match="query must contain at least one Unicode-alphanumeric token"):
        evaluate_lexical_retrieval_quality([p], [blank_query_case])


def test_evaluate_lexical_absent_gold_id_rejection():
    p = make_profile("v-1", title="Mechanical Keyboard")
    # 'v-nonexistent' is not in validated corpus
    case = RetrievalBenchmarkCase("c1", "q", "keyboard", ("v-1", "v-nonexistent"))

    with pytest.raises(RetrievalQualityEvaluationError, match="relevant_variant_id 'v-nonexistent' .* does not exist in validated corpus"):
        evaluate_lexical_retrieval_quality([p], [case])


# ---------------------------------------------------------------------------
# 5. Exact metrics, order preservation, zero-hit behavior, micro aggregation
# ---------------------------------------------------------------------------


def test_evaluate_lexical_tp_fp_fn_ordering_and_fraction_metrics():
    # v-1 matches "mechanical keyboard"
    # v-2 matches "mechanical switch"
    # v-3 matches "rubber dome keyboard"
    p1 = make_profile("v-1", title="Mechanical Keyboard")
    p2 = make_profile("v-2", title="Mechanical Switch")
    p3 = make_profile("v-3", title="Rubber Dome Keyboard")
    p4 = make_profile("v-4", title="Wireless Mouse")
    corpus = (p1, p2, p3, p4)

    # Relevant are v-1 and v-4 (v-4 will not match "mechanical")
    # Caller relevant order is (v-4, v-1)
    case = RetrievalBenchmarkCase(
        case_id="c1",
        question="Which items are mechanical?",
        retrieval_query="mechanical",
        relevant_variant_ids=("v-4", "v-1"),
    )

    report = evaluate_lexical_retrieval_quality(corpus, [case], limit=10)
    assert len(report.case_evaluations) == 1
    ce = report.case_evaluations[0]

    # hits for query "mechanical":
    # v-1 matches PHRASE or EXACT_VALUE
    # v-2 matches PHRASE or EXACT_VALUE
    # hits order from TASK-122 will be (v-1, v-2) based on match class and variant_id tie-breaker
    assert tuple(h.profile.variant_id for h in ce.hits) == ("v-1", "v-2")

    # True positive: v-1 in hits order
    assert ce.true_positive_variant_ids == ("v-1",)
    # False positive: v-2 in hits order
    assert ce.false_positive_variant_ids == ("v-2",)
    # False negative: v-4 in benchmark case order
    assert ce.false_negative_variant_ids == ("v-4",)

    # Precision: TP / retrieved_count = 1 / 2
    assert ce.precision == Fraction(1, 2)
    assert type(ce.precision) is Fraction

    # Recall: TP / relevant_count = 1 / 2
    assert ce.recall == Fraction(1, 2)
    assert type(ce.recall) is Fraction


def test_evaluate_lexical_zero_hit_behavior():
    p1 = make_profile("v-1", title="Mechanical Keyboard")
    case = RetrievalBenchmarkCase(
        case_id="c1",
        question="Find headphones",
        retrieval_query="headphones",
        relevant_variant_ids=("v-1",),
    )

    report = evaluate_lexical_retrieval_quality([p1], [case], limit=10)
    ce = report.case_evaluations[0]

    assert ce.hits == ()
    assert ce.true_positive_variant_ids == ()
    assert ce.false_positive_variant_ids == ()
    assert ce.false_negative_variant_ids == ("v-1",)
    assert ce.precision == Fraction(0, 1)
    assert ce.recall == Fraction(0, 1)

    assert report.true_positive_count == 0
    assert report.false_positive_count == 0
    assert report.false_negative_count == 1
    assert report.micro_precision == Fraction(0, 1)
    assert report.micro_recall == Fraction(0, 1)


def test_evaluate_lexical_micro_aggregation_multi_case():
    p1 = make_profile("v-1", title="Gaming Keyboard RGB")
    p2 = make_profile("v-2", title="Office Keyboard Silent")
    p3 = make_profile("v-3", title="Ergonomic Mouse Wireless")
    p4 = make_profile("v-4", title="Trackball Mouse Bluetooth")
    corpus = (p1, p2, p3, p4)

    # Case 1: query="keyboard" -> retrieves v-1, v-2. Relevant=("v-1",)
    # TP: v-1 (1), FP: v-2 (1), FN: () (0)
    # precision: 1/2, recall: 1/1 = 1
    case1 = RetrievalBenchmarkCase(
        case_id="c-keyboard",
        question="Best gaming keyboard?",
        retrieval_query="keyboard",
        relevant_variant_ids=("v-1",),
    )

    # Case 2: query="mouse" -> retrieves v-3, v-4. Relevant=("v-3", "v-4", "v-2")
    # TP: v-3, v-4 (2), FP: () (0), FN: ("v-2",) (1)
    # precision: 2/2 = 1, recall: 2/3
    case2 = RetrievalBenchmarkCase(
        case_id="c-mouse",
        question="Best mice?",
        retrieval_query="mouse",
        relevant_variant_ids=("v-3", "v-4", "v-2"),
    )

    # Case 3: query="monitor" -> retrieves nothing. Relevant=("v-1",)
    # TP: 0, FP: 0, FN: ("v-1",) (1)
    # precision: 0/1, recall: 0/1
    case3 = RetrievalBenchmarkCase(
        case_id="c-monitor",
        question="Find 4K monitor",
        retrieval_query="monitor",
        relevant_variant_ids=("v-1",),
    )

    report = evaluate_lexical_retrieval_quality(corpus, [case1, case2, case3], limit=10)

    # Preserves caller case order
    assert [ce.case.case_id for ce in report.case_evaluations] == [
        "c-keyboard",
        "c-mouse",
        "c-monitor",
    ]

    # Aggregate counts:
    # TP: 1 + 2 + 0 = 3
    # FP: 1 + 0 + 0 = 1
    # FN: 0 + 1 + 1 = 2
    assert report.true_positive_count == 3
    assert report.false_positive_count == 1
    assert report.false_negative_count == 2

    # Micro precision: total TP / (total TP + total FP) = 3 / (3 + 1) = 3/4
    assert report.micro_precision == Fraction(3, 4)

    # Micro recall: total TP / (total TP + total FN) = 3 / (3 + 2) = 3/5
    assert report.micro_recall == Fraction(3, 5)


def test_evaluate_lexical_corpus_permutation_determinism():
    p1 = make_profile("v-alpha", title="Smart Watch Fitness")
    p2 = make_profile("v-beta", title="Smart Watch Steel")
    p3 = make_profile("v-gamma", title="Smart Ring Titanium")

    case = RetrievalBenchmarkCase(
        case_id="c1",
        question="Find smart watches",
        retrieval_query="smart watch",
        relevant_variant_ids=("v-alpha", "v-beta"),
    )

    report1 = evaluate_lexical_retrieval_quality([p1, p2, p3], [case], limit=5)
    report2 = evaluate_lexical_retrieval_quality([p3, p1, p2], [case], limit=5)
    report3 = evaluate_lexical_retrieval_quality([p2, p3, p1], [case], limit=5)

    assert report1.case_evaluations[0].hits == report2.case_evaluations[0].hits
    assert report2.case_evaluations[0].hits == report3.case_evaluations[0].hits
    assert report1.case_evaluations[0].precision == report2.case_evaluations[0].precision
    assert report1.case_evaluations[0].recall == report2.case_evaluations[0].recall


# ---------------------------------------------------------------------------
# 6. evaluate_grounded_answer_citation_fidelity & continuity
# ---------------------------------------------------------------------------


def test_fidelity_continuity_validation():
    p1 = make_profile("v-1", title="Gaming Keyboard RGB")
    corpus = (p1,)
    case = RetrievalBenchmarkCase(
        case_id="c1",
        question="Which keyboard has RGB backlighting?",
        retrieval_query="keyboard rgb",
        relevant_variant_ids=("v-1",),
    )

    report = evaluate_lexical_retrieval_quality(corpus, [case], limit=5)
    ce = report.case_evaluations[0]

    ctx = build_canonical_rag_context(
        corpus,
        question="Which keyboard has RGB backlighting?",
        retrieval_query="keyboard rgb",
        max_hits=5,
    )
    answer = create_grounded_answer(
        context=ctx,
        status=GroundedAnswerStatus.ANSWERED,
        answer_text="The keyboard features RGB backlighting.",
        citation_ids=("H001-W001",),
    )

    # Valid evaluation
    fid = evaluate_grounded_answer_citation_fidelity(ce, answer)
    assert fid.fidelity == Fraction(1, 1)

    # Type mismatch: case_evaluation
    with pytest.raises(RetrievalQualityEvaluationError, match="case_evaluation must be an exact RetrievalCaseEvaluation"):
        evaluate_grounded_answer_citation_fidelity("not-ce", answer)  # type: ignore[arg-type]

    # Type mismatch: answer
    with pytest.raises(RetrievalQualityEvaluationError, match="answer must be an exact GroundedAnswer"):
        evaluate_grounded_answer_citation_fidelity(ce, "not-answer")  # type: ignore[arg-type]

    # Question mismatch
    ctx_diff_q = build_canonical_rag_context(
        corpus,
        question="Different question?",
        retrieval_query="keyboard rgb",
        max_hits=5,
    )
    ans_diff_q = create_grounded_answer(
        context=ctx_diff_q,
        status=GroundedAnswerStatus.ANSWERED,
        answer_text="Diff answer",
        citation_ids=("H001-W001",),
    )
    with pytest.raises(RetrievalQualityEvaluationError, match="answer.context.question does not match"):
        evaluate_grounded_answer_citation_fidelity(ce, ans_diff_q)

    # Query mismatch
    ctx_diff_query = build_canonical_rag_context(
        corpus,
        question="Which keyboard has RGB backlighting?",
        retrieval_query="keyboard",
        max_hits=5,
    )
    ans_diff_query = create_grounded_answer(
        context=ctx_diff_query,
        status=GroundedAnswerStatus.ANSWERED,
        answer_text="Diff query answer",
        citation_ids=("H001-W001",),
    )
    with pytest.raises(RetrievalQualityEvaluationError, match="answer.context.retrieval_query does not match"):
        evaluate_grounded_answer_citation_fidelity(ce, ans_diff_query)

    # Limit / max_hits mismatch
    ctx_diff_limit = build_canonical_rag_context(
        corpus,
        question="Which keyboard has RGB backlighting?",
        retrieval_query="keyboard rgb",
        max_hits=10,
    )
    ans_diff_limit = create_grounded_answer(
        context=ctx_diff_limit,
        status=GroundedAnswerStatus.ANSWERED,
        answer_text="Diff limit answer",
        citation_ids=("H001-W001",),
    )
    with pytest.raises(RetrievalQualityEvaluationError, match="answer.context.max_hits does not match"):
        evaluate_grounded_answer_citation_fidelity(ce, ans_diff_limit)

    # Hits mismatch (different corpus hits)
    p2 = make_profile("v-2", title="Keyboard RGB Alternate")
    ctx_diff_hits = build_canonical_rag_context(
        (p1, p2),
        question="Which keyboard has RGB backlighting?",
        retrieval_query="keyboard rgb",
        max_hits=5,
    )
    ans_diff_hits = create_grounded_answer(
        context=ctx_diff_hits,
        status=GroundedAnswerStatus.ANSWERED,
        answer_text="Diff hits answer",
        citation_ids=("H001-W001",),
    )
    with pytest.raises(RetrievalQualityEvaluationError, match="answer.context hits do not match"):
        evaluate_grounded_answer_citation_fidelity(ce, ans_diff_hits)


def test_fidelity_witness_supplemental_and_hit_header_handling():
    p1 = make_profile("v-1", title="Wireless Mechanical Keyboard", brand="BrandA")
    p2 = make_profile("v-2", title="Wireless Membrane Keyboard", brand="BrandB")
    corpus = (p1, p2)

    case = RetrievalBenchmarkCase(
        case_id="c1",
        question="Which wireless keyboard is available?",
        retrieval_query="wireless keyboard",
        relevant_variant_ids=("v-1",),  # only v-1 is relevant
    )

    report = evaluate_lexical_retrieval_quality(corpus, [case], limit=5)
    ce = report.case_evaluations[0]

    ctx = build_canonical_rag_context(
        corpus,
        question="Which wireless keyboard is available?",
        retrieval_query="wireless keyboard",
        max_hits=5,
    )

    # In ctx:
    # H001: v-1 (relevant). Has witnesses H001-W001... and supplemental H001-E001...
    # H002: v-2 (irrelevant). Has witnesses H002-W001... and supplemental H002-E001...
    h1 = ctx.hits[0]
    h2 = ctx.hits[1]
    assert h1.hit.profile.variant_id == "v-1"
    assert h2.hit.profile.variant_id == "v-2"

    w1 = f"{h1.citation_id}-W001"
    e1 = h1.supplemental_evidence[0].citation_id
    w2 = f"{h2.citation_id}-W001"
    header1 = h1.citation_id

    # Answer citing: header1 (excluded), w2 (irrelevant), w1 (relevant), e1 (relevant)
    answer = create_grounded_answer(
        context=ctx,
        status=GroundedAnswerStatus.ANSWERED,
        answer_text="Both models are wireless keyboards.",
        citation_ids=(header1, w2, w1, e1),
    )

    fid = evaluate_grounded_answer_citation_fidelity(ce, answer)

    # Hit header 'H001' must be excluded from leaf citations
    assert fid.leaf_citation_ids == (w2, w1, e1)
    # Preserves answer order: w2 was first, then w1, e1
    assert fid.relevant_leaf_citation_ids == (w1, e1)
    assert fid.irrelevant_leaf_citation_ids == (w2,)

    # 2 relevant out of 3 leaves
    assert fid.fidelity == Fraction(2, 3)
    assert type(fid.fidelity) is Fraction


def test_fidelity_zero_leaf_returns_none():
    p1 = make_profile("v-1", title="Wireless Mechanical Keyboard")
    case = RetrievalBenchmarkCase(
        case_id="c1",
        question="Are any monitors available?",
        retrieval_query="monitor",
        relevant_variant_ids=("v-1",),
    )

    report = evaluate_lexical_retrieval_quality([p1], [case], limit=5)
    ce = report.case_evaluations[0]

    ctx = build_canonical_rag_context(
        [p1],
        question="Are any monitors available?",
        retrieval_query="monitor",
        max_hits=5,
    )

    # Insufficient evidence allows 0 citations
    answer_zero = create_grounded_answer(
        context=ctx,
        status=GroundedAnswerStatus.INSUFFICIENT_EVIDENCE,
        answer_text="No monitors were found in the context.",
        citation_ids=(),
        limitations=("No matching monitors retrieved",),
    )

    fid_zero = evaluate_grounded_answer_citation_fidelity(ce, answer_zero)
    assert fid_zero.leaf_citation_ids == ()
    assert fid_zero.relevant_leaf_citation_ids == ()
    assert fid_zero.irrelevant_leaf_citation_ids == ()
    assert fid_zero.fidelity is None


def test_fidelity_hit_header_only_returns_none():
    p1 = make_profile("v-1", title="Wireless Mechanical Keyboard")
    case = RetrievalBenchmarkCase(
        case_id="c1",
        question="Which keyboard is available?",
        retrieval_query="keyboard",
        relevant_variant_ids=("v-1",),
    )

    report = evaluate_lexical_retrieval_quality([p1], [case], limit=5)
    ce = report.case_evaluations[0]

    ctx = build_canonical_rag_context(
        [p1],
        question="Which keyboard is available?",
        retrieval_query="keyboard",
        max_hits=5,
    )

    # Answer citing only hit header H001 in INSUFFICIENT_EVIDENCE (valid under TASK-129)
    answer_header_only = create_grounded_answer(
        context=ctx,
        status=GroundedAnswerStatus.INSUFFICIENT_EVIDENCE,
        answer_text="Keyboard was found but lacked required detail.",
        citation_ids=("H001",),
        limitations=("Detail missing",),
    )

    fid = evaluate_grounded_answer_citation_fidelity(ce, answer_header_only)
    assert fid.leaf_citation_ids == ()
    assert fid.fidelity is None


def test_fidelity_does_not_interpret_answer_text_or_grade_entailment():
    p1 = make_profile("v-1", title="Mechanical Keyboard Blue")
    case = RetrievalBenchmarkCase(
        case_id="c1",
        question="Which keyboard is blue?",
        retrieval_query="keyboard blue",
        relevant_variant_ids=("v-1",),
    )

    report = evaluate_lexical_retrieval_quality([p1], [case], limit=5)
    ce = report.case_evaluations[0]

    ctx = build_canonical_rag_context(
        [p1],
        question="Which keyboard is blue?",
        retrieval_query="keyboard blue",
        max_hits=5,
    )

    # Completely false / contradictory answer text citing valid relevant leaf
    answer = create_grounded_answer(
        context=ctx,
        status=GroundedAnswerStatus.ANSWERED,
        answer_text="The moon is made of green cheese and no keyboards exist.",
        citation_ids=("H001-W001",),
    )

    fid = evaluate_grounded_answer_citation_fidelity(ce, answer)
    # Fidelity is purely structural: does cited leaf trace to benchmark-relevant profile?
    assert fid.fidelity == Fraction(1, 1)


# ---------------------------------------------------------------------------
# 7. Repeated determinism & no forbidden operations
# ---------------------------------------------------------------------------


def test_repeated_determinism():
    p1 = make_profile("v-1", title="Ergonomic Keyboard A")
    p2 = make_profile("v-2", title="Ergonomic Keyboard B")
    corpus = (p1, p2)

    case = RetrievalBenchmarkCase(
        case_id="c1",
        question="Find ergonomic keyboards",
        retrieval_query="ergonomic keyboard",
        relevant_variant_ids=("v-1", "v-2"),
    )

    ctx = build_canonical_rag_context(
        corpus,
        question="Find ergonomic keyboards",
        retrieval_query="ergonomic keyboard",
        max_hits=5,
    )
    answer = create_grounded_answer(
        context=ctx,
        status=GroundedAnswerStatus.ANSWERED,
        answer_text="Both keyboards are ergonomic.",
        citation_ids=("H001-W001", "H002-W001"),
    )

    baseline_report = evaluate_lexical_retrieval_quality(corpus, [case], limit=5)
    baseline_fidelity = evaluate_grounded_answer_citation_fidelity(
        baseline_report.case_evaluations[0], answer
    )

    for _ in range(10):
        rep = evaluate_lexical_retrieval_quality(corpus, [case], limit=5)
        fid = evaluate_grounded_answer_citation_fidelity(rep.case_evaluations[0], answer)
        assert rep == baseline_report
        assert fid == baseline_fidelity


def test_no_forbidden_dependencies_or_apis():
    # Module must not import sqlite3, subprocess, socket, urllib, httpx, requests,
    # random, uuid, os, sys, etc.
    forbidden_modules = {
        "sqlite3",
        "subprocess",
        "socket",
        "urllib",
        "httpx",
        "requests",
        "random",
        "uuid",
        "os",
        "sys",
    }
    loaded_module_names = {name for name, _ in inspect.getmembers(rqe)}
    for mod in forbidden_modules:
        assert mod not in loaded_module_names
        assert not hasattr(rqe, mod)
