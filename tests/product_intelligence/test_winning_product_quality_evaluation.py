from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

import src.product_intelligence.winning_product_quality_evaluation as evaluation_module
from src.product_intelligence import (
    CandidateWinningProductCoverage,
    WinningProductCoverageReport,
    WinningProductQualityEvaluationError,
    evaluate_winning_product_coverage,
)
from src.product_intelligence.models import (
    CategoryScore,
    ConfidenceBreakdown,
    DecisionBand,
    NormalizedSignal,
    ProductCandidateSnapshot,
    ScoreCategory,
    SignalProvenance,
    WinningProductScore,
)
from src.product_intelligence.policy import ScoringPolicy


EVALUATED_AT = datetime(2026, 9, 11, 12, 0, tzinfo=timezone.utc)


def _candidate(candidate_id: str) -> ProductCandidateSnapshot:
    return ProductCandidateSnapshot(
        candidate_id=candidate_id,
        platform="shopee",
        url=f"https://example.test/{candidate_id}",
        observed_at=EVALUATED_AT,
        title=candidate_id,
    )


def _signal(
    name: str,
    category: ScoreCategory,
    provenance: SignalProvenance,
) -> NormalizedSignal:
    return NormalizedSignal(
        name=name,
        category=category,
        score=0.0 if provenance is SignalProvenance.MISSING else 0.5,
        provenance=provenance,
    )


def _score(
    candidate: ProductCandidateSnapshot,
    coverages: dict[ScoreCategory, float],
    *,
    decision_band: DecisionBand,
    signals: dict[ScoreCategory, tuple[NormalizedSignal, ...]] | None = None,
) -> WinningProductScore:
    category_scores = {
        category: CategoryScore(
            category=category,
            raw_score=0.0,
            weight=1.0,
            weighted_score=0.0,
            coverage=coverages[category],
            signals=() if signals is None else signals.get(category, ()),
        )
        for category in ScoreCategory
    }
    return WinningProductScore(
        candidate_id=candidate.candidate_id,
        platform=candidate.platform,
        base_score=0.0,
        confidence=0.0,
        final_score=0.0,
        decision_band=decision_band,
        category_scores=category_scores,
        confidence_breakdown=ConfidenceBreakdown(0.0, 0.0, 0.0, 0.0, 0.0),
        key_supporting_signals=(),
        missing_or_weak_signals=(),
        evidence_references=(),
        reason_codes=(),
        evaluated_at=EVALUATED_AT,
    )


def test_exact_public_api_and_frozen_field_shapes() -> None:
    public_names = {name for name in vars(evaluation_module) if not name.startswith("_")}
    assert public_names == {
        "WinningProductQualityEvaluationError",
        "CandidateWinningProductCoverage",
        "WinningProductCoverageReport",
        "evaluate_winning_product_coverage",
    }
    assert [field.name for field in fields(CandidateWinningProductCoverage)] == [
        "candidate",
        "score",
        "zero_coverage_categories",
        "partial_coverage_categories",
        "full_coverage_categories",
        "missing_factual_signal_names",
    ]
    assert [field.name for field in fields(WinningProductCoverageReport)] == [
        "evaluated_at",
        "candidate_evaluations",
        "zero_coverage_counts_by_category",
        "partial_coverage_counts_by_category",
        "full_coverage_counts_by_category",
        "decision_band_counts",
    ]

    candidate = _candidate("frozen")
    score = _score(
        candidate,
        {category: 0.0 for category in ScoreCategory},
        decision_band=DecisionBand.INSUFFICIENT_DATA,
    )
    result = CandidateWinningProductCoverage(candidate, score, (), (), (), ())
    with pytest.raises(FrozenInstanceError):
        result.score = score  # type: ignore[misc]


class _OneShotCandidates:
    def __init__(self, values: tuple[ProductCandidateSnapshot, ...]) -> None:
        self.values = values
        self.iterations = 0

    def __iter__(self):
        self.iterations += 1
        if self.iterations > 1:
            raise AssertionError("candidate iterable was materialized more than once")
        yield from self.values


def test_materializes_once_scores_once_in_order_and_preserves_exact_objects() -> None:
    candidates = (_candidate("first"), _candidate("second"))
    iterable = _OneShotCandidates(candidates)
    scores = [
        _score(
            candidate,
            {category: 1.0 for category in ScoreCategory},
            decision_band=DecisionBand.HOLD,
        )
        for candidate in candidates
    ]
    policy = ScoringPolicy()

    with patch.object(
        evaluation_module._WinningProductScorer,
        "score_snapshot",
        side_effect=scores,
    ) as scorer:
        report = evaluate_winning_product_coverage(
            iterable,
            evaluated_at=EVALUATED_AT,
            policy=policy,
        )

    assert iterable.iterations == 1
    assert [entry.candidate for entry in report.candidate_evaluations] == list(candidates)
    assert report.candidate_evaluations[0].candidate is candidates[0]
    assert report.candidate_evaluations[1].candidate is candidates[1]
    assert report.candidate_evaluations[0].score is scores[0]
    assert report.candidate_evaluations[1].score is scores[1]
    assert scorer.call_count == 2
    for index, call in enumerate(scorer.call_args_list):
        assert call.args == ()
        assert call.kwargs == {
            "snapshot": candidates[index],
            "evaluated_at": EVALUATED_AT,
            "policy": policy,
        }
        assert call.kwargs["snapshot"] is candidates[index]
        assert call.kwargs["evaluated_at"] is EVALUATED_AT
        assert call.kwargs["policy"] is policy


@pytest.mark.parametrize(
    "candidates",
    [
        (),
        tuple(_candidate(f"candidate-{index}") for index in range(101)),
        (_candidate("valid"), {"candidate_id": "mapping"}),
        (True,),
        (_candidate("duplicate"), _candidate("duplicate")),
    ],
)
def test_invalid_cohorts_fail_before_scoring(candidates: object) -> None:
    with patch.object(evaluation_module._WinningProductScorer, "score_snapshot") as scorer:
        with pytest.raises(WinningProductQualityEvaluationError):
            evaluate_winning_product_coverage(candidates, evaluated_at=EVALUATED_AT)  # type: ignore[arg-type]
    scorer.assert_not_called()


def test_non_iterable_explicit_time_and_policy_boundaries_fail_closed() -> None:
    candidate = _candidate("boundary")

    class PolicySubclass(ScoringPolicy):
        pass

    invalid_calls = (
        lambda: evaluate_winning_product_coverage(42, evaluated_at=EVALUATED_AT),  # type: ignore[arg-type]
        lambda: evaluate_winning_product_coverage((candidate,), evaluated_at=None),  # type: ignore[arg-type]
        lambda: evaluate_winning_product_coverage((candidate,), evaluated_at="2026-09-11"),  # type: ignore[arg-type]
        lambda: evaluate_winning_product_coverage(
            (candidate,), evaluated_at=EVALUATED_AT, policy=PolicySubclass()
        ),
    )
    with patch.object(evaluation_module._WinningProductScorer, "score_snapshot") as scorer:
        for call in invalid_calls:
            with pytest.raises(WinningProductQualityEvaluationError):
                call()
    scorer.assert_not_called()

    with pytest.raises(TypeError):
        evaluate_winning_product_coverage((candidate,))  # type: ignore[call-arg]


def test_classification_missing_names_and_aggregate_order_come_only_from_scores() -> None:
    first = _candidate("first")
    second = _candidate("second")
    first_coverages = {
        ScoreCategory.DEMAND: 0.0,
        ScoreCategory.MOMENTUM: 0.25,
        ScoreCategory.COMMERCIAL_ATTRACTIVENESS: 1.0,
        ScoreCategory.TRUST: 0.999,
        ScoreCategory.CONTENTABILITY: 0.0,
        ScoreCategory.COMPETITION_OPPORTUNITY: 1.0,
    }
    second_coverages = {
        ScoreCategory.DEMAND: 1.0,
        ScoreCategory.MOMENTUM: 0.0,
        ScoreCategory.COMMERCIAL_ATTRACTIVENESS: 0.5,
        ScoreCategory.TRUST: 1.0,
        ScoreCategory.CONTENTABILITY: 0.0,
        ScoreCategory.COMPETITION_OPPORTUNITY: 0.5,
    }
    first_signals = {
        ScoreCategory.DEMAND: (
            _signal("sold_volume", ScoreCategory.DEMAND, SignalProvenance.MISSING),
            _signal("review_depth", ScoreCategory.DEMAND, SignalProvenance.MISSING),
        ),
        ScoreCategory.MOMENTUM: (
            _signal("sales_velocity", ScoreCategory.MOMENTUM, SignalProvenance.MISSING),
        ),
        ScoreCategory.TRUST: (
            _signal("rating_quality", ScoreCategory.TRUST, SignalProvenance.OBSERVED),
        ),
    }
    scores = (
        _score(
            first,
            first_coverages,
            decision_band=DecisionBand.RECOMMENDED,
            signals=first_signals,
        ),
        _score(
            second,
            second_coverages,
            decision_band=DecisionBand.HOLD,
        ),
    )

    with patch.object(
        evaluation_module._WinningProductScorer,
        "score_snapshot",
        side_effect=scores,
    ):
        report = evaluate_winning_product_coverage(
            (first, second), evaluated_at=EVALUATED_AT
        )

    first_result = report.candidate_evaluations[0]
    assert first_result.zero_coverage_categories == (
        ScoreCategory.DEMAND,
        ScoreCategory.CONTENTABILITY,
    )
    assert first_result.partial_coverage_categories == (
        ScoreCategory.MOMENTUM,
        ScoreCategory.TRUST,
    )
    assert first_result.full_coverage_categories == (
        ScoreCategory.COMMERCIAL_ATTRACTIVENESS,
        ScoreCategory.COMPETITION_OPPORTUNITY,
    )
    assert first_result.missing_factual_signal_names == (
        "sold_volume",
        "review_depth",
        "sales_velocity",
    )
    assert not any("content" in name for name in first_result.missing_factual_signal_names)

    assert tuple(category for category, _ in report.zero_coverage_counts_by_category) == tuple(ScoreCategory)
    assert tuple(category for category, _ in report.partial_coverage_counts_by_category) == tuple(ScoreCategory)
    assert tuple(category for category, _ in report.full_coverage_counts_by_category) == tuple(ScoreCategory)
    assert report.zero_coverage_counts_by_category == (
        (ScoreCategory.DEMAND, 1),
        (ScoreCategory.MOMENTUM, 1),
        (ScoreCategory.COMMERCIAL_ATTRACTIVENESS, 0),
        (ScoreCategory.TRUST, 0),
        (ScoreCategory.CONTENTABILITY, 2),
        (ScoreCategory.COMPETITION_OPPORTUNITY, 0),
    )
    assert report.partial_coverage_counts_by_category == (
        (ScoreCategory.DEMAND, 0),
        (ScoreCategory.MOMENTUM, 1),
        (ScoreCategory.COMMERCIAL_ATTRACTIVENESS, 1),
        (ScoreCategory.TRUST, 1),
        (ScoreCategory.CONTENTABILITY, 0),
        (ScoreCategory.COMPETITION_OPPORTUNITY, 1),
    )
    assert report.full_coverage_counts_by_category == (
        (ScoreCategory.DEMAND, 1),
        (ScoreCategory.MOMENTUM, 0),
        (ScoreCategory.COMMERCIAL_ATTRACTIVENESS, 1),
        (ScoreCategory.TRUST, 1),
        (ScoreCategory.CONTENTABILITY, 0),
        (ScoreCategory.COMPETITION_OPPORTUNITY, 1),
    )
    assert report.decision_band_counts == (
        (DecisionBand.RECOMMENDED, 1),
        (DecisionBand.NEEDS_REVIEW, 0),
        (DecisionBand.INSUFFICIENT_DATA, 0),
        (DecisionBand.HOLD, 1),
    )
    with pytest.raises(FrozenInstanceError):
        report.decision_band_counts = ()  # type: ignore[misc]


def test_repeated_evaluation_is_deterministic_with_existing_scorer() -> None:
    candidates = (_candidate("stable-one"), _candidate("stable-two"))
    first = evaluate_winning_product_coverage(candidates, evaluated_at=EVALUATED_AT)
    second = evaluate_winning_product_coverage(candidates, evaluated_at=EVALUATED_AT)
    assert first == second


def test_delegation_surface_has_no_forbidden_authority_or_io_side_effects() -> None:
    candidate = _candidate("pure")
    score = _score(
        candidate,
        {category: 0.0 for category in ScoreCategory},
        decision_band=DecisionBand.INSUFFICIENT_DATA,
    )
    implementation_names = evaluation_module.evaluate_winning_product_coverage.__code__.co_names
    forbidden_fragments = (
        "Normalizer",
        "Ranker",
        "Discovery",
        "Provider",
        "LLM",
        "open",
        "sqlite",
        "subprocess",
        "random",
        "uuid",
        "getenv",
        "environ",
    )
    assert not any(
        fragment.lower() in name.lower()
        for fragment in forbidden_fragments
        for name in implementation_names
    )
    assert not {"now", "utcnow", "time"}.intersection(implementation_names)

    with (
        patch.object(
            evaluation_module._WinningProductScorer,
            "score_snapshot",
            return_value=score,
        ) as scorer,
        patch("os.getenv", side_effect=AssertionError("environment access")),
        patch("subprocess.run", side_effect=AssertionError("subprocess access")),
        patch("socket.socket", side_effect=AssertionError("network access")),
        patch("random.random", side_effect=AssertionError("random access")),
        patch("uuid.uuid4", side_effect=AssertionError("UUID access")),
        patch("builtins.open", side_effect=AssertionError("filesystem access")),
    ):
        report = evaluate_winning_product_coverage(
            (candidate,), evaluated_at=EVALUATED_AT
        )

    assert report.candidate_evaluations[0].score is score
    scorer.assert_called_once_with(
        snapshot=candidate,
        evaluated_at=EVALUATED_AT,
        policy=None,
    )


def test_existing_scorer_exception_propagates_unchanged_and_stops_iteration() -> None:
    candidates = (_candidate("first"), _candidate("second"))
    failure = RuntimeError("scorer failure")
    with patch.object(
        evaluation_module._WinningProductScorer,
        "score_snapshot",
        side_effect=failure,
    ) as scorer:
        with pytest.raises(RuntimeError) as exc_info:
            evaluate_winning_product_coverage(candidates, evaluated_at=EVALUATED_AT)
    assert exc_info.value is failure
    assert scorer.call_count == 1
