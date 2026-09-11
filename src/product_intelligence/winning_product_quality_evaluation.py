"""Bounded Winning Product evidence-coverage evaluation.

TASK-181 observes only the public outputs of the existing V1 scorer. It does not
discover, normalize, score, rank, approve, persist, retrieve, or infer product
facts, and it makes no business-quality or roadmap decision.
"""

from collections.abc import Iterable as _Iterable
from dataclasses import dataclass as _dataclass
from datetime import datetime as _datetime

from src.product_intelligence.models import (
    DecisionBand as _DecisionBand,
    ProductCandidateSnapshot as _ProductCandidateSnapshot,
    ScoreCategory as _ScoreCategory,
    SignalProvenance as _SignalProvenance,
    WinningProductScore as _WinningProductScore,
)
from src.product_intelligence.policy import ScoringPolicy as _ScoringPolicy
from src.product_intelligence.scoring import WinningProductScorer as _WinningProductScorer

_MIN_CANDIDATES = 1
_MAX_CANDIDATES = 100
_CATEGORIES = tuple(_ScoreCategory)
_DECISION_BANDS = tuple(_DecisionBand)


class WinningProductQualityEvaluationError(ValueError):
    """Raised when Winning Product coverage-evaluation input is outside contract."""


@_dataclass(frozen=True)
class CandidateWinningProductCoverage:
    """Immutable scorer-owned coverage observations for one exact candidate."""

    candidate: _ProductCandidateSnapshot
    score: _WinningProductScore
    zero_coverage_categories: tuple[_ScoreCategory, ...]
    partial_coverage_categories: tuple[_ScoreCategory, ...]
    full_coverage_categories: tuple[_ScoreCategory, ...]
    missing_factual_signal_names: tuple[str, ...]


@_dataclass(frozen=True)
class WinningProductCoverageReport:
    """Immutable aggregate coverage observations for one bounded cohort."""

    evaluated_at: _datetime
    candidate_evaluations: tuple[CandidateWinningProductCoverage, ...]
    zero_coverage_counts_by_category: tuple[tuple[_ScoreCategory, int], ...]
    partial_coverage_counts_by_category: tuple[tuple[_ScoreCategory, int], ...]
    full_coverage_counts_by_category: tuple[tuple[_ScoreCategory, int], ...]
    decision_band_counts: tuple[tuple[_DecisionBand, int], ...]


def evaluate_winning_product_coverage(
    candidates: _Iterable[_ProductCandidateSnapshot],
    *,
    evaluated_at: _datetime,
    policy: _ScoringPolicy | None = None,
) -> WinningProductCoverageReport:
    """Evaluate scorer-emitted evidence coverage without adding scoring authority."""

    if not isinstance(evaluated_at, _datetime):
        raise WinningProductQualityEvaluationError(
            "evaluated_at must be a datetime value"
        )
    if policy is not None and type(policy) is not _ScoringPolicy:
        raise WinningProductQualityEvaluationError(
            "policy must be None or an exact ScoringPolicy value"
        )

    try:
        materialized_candidates = tuple(candidates)
    except TypeError as exc:
        raise WinningProductQualityEvaluationError(
            "candidates must be an iterable of exact ProductCandidateSnapshot values"
        ) from exc

    candidate_count = len(materialized_candidates)
    if not _MIN_CANDIDATES <= candidate_count <= _MAX_CANDIDATES:
        raise WinningProductQualityEvaluationError(
            "candidate count must be in "
            f"[{_MIN_CANDIDATES}, {_MAX_CANDIDATES}], got {candidate_count}"
        )

    seen_candidate_ids: set[str] = set()
    for index, candidate in enumerate(materialized_candidates):
        if type(candidate) is not _ProductCandidateSnapshot:
            raise WinningProductQualityEvaluationError(
                "candidates item at index "
                f"{index} must be an exact ProductCandidateSnapshot, "
                f"got {type(candidate).__name__}"
            )
        if candidate.candidate_id in seen_candidate_ids:
            raise WinningProductQualityEvaluationError(
                f"duplicate candidate_id '{candidate.candidate_id}' is not allowed"
            )
        seen_candidate_ids.add(candidate.candidate_id)

    candidate_evaluations: list[CandidateWinningProductCoverage] = []
    zero_counts = {category: 0 for category in _CATEGORIES}
    partial_counts = {category: 0 for category in _CATEGORIES}
    full_counts = {category: 0 for category in _CATEGORIES}
    decision_counts = {band: 0 for band in _DECISION_BANDS}

    for candidate in materialized_candidates:
        score = _WinningProductScorer.score_snapshot(
            snapshot=candidate,
            evaluated_at=evaluated_at,
            policy=policy,
        )

        zero_categories: list[_ScoreCategory] = []
        partial_categories: list[_ScoreCategory] = []
        full_categories: list[_ScoreCategory] = []
        missing_names: list[str] = []

        for category in _CATEGORIES:
            category_score = score.category_scores[category]
            if category_score.coverage == 0.0:
                zero_categories.append(category)
                zero_counts[category] += 1
            elif category_score.coverage == 1.0:
                full_categories.append(category)
                full_counts[category] += 1
            else:
                partial_categories.append(category)
                partial_counts[category] += 1

            missing_names.extend(
                signal.name
                for signal in category_score.signals
                if signal.provenance is _SignalProvenance.MISSING
            )

        decision_counts[score.decision_band] += 1
        candidate_evaluations.append(
            CandidateWinningProductCoverage(
                candidate=candidate,
                score=score,
                zero_coverage_categories=tuple(zero_categories),
                partial_coverage_categories=tuple(partial_categories),
                full_coverage_categories=tuple(full_categories),
                missing_factual_signal_names=tuple(missing_names),
            )
        )

    return WinningProductCoverageReport(
        evaluated_at=evaluated_at,
        candidate_evaluations=tuple(candidate_evaluations),
        zero_coverage_counts_by_category=tuple(
            (category, zero_counts[category]) for category in _CATEGORIES
        ),
        partial_coverage_counts_by_category=tuple(
            (category, partial_counts[category]) for category in _CATEGORIES
        ),
        full_coverage_counts_by_category=tuple(
            (category, full_counts[category]) for category in _CATEGORIES
        ),
        decision_band_counts=tuple(
            (band, decision_counts[band]) for band in _DECISION_BANDS
        ),
    )
