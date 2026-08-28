from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

import pytest

from src.product_intelligence.models import ProductCandidateSnapshot, SignalProvenance
from src.product_intelligence.ranking import (
    MAX_RANKING_CANDIDATES,
    CandidateRanker,
    CandidateRankingError,
    rank_candidates,
)
from src.product_intelligence.scoring import WinningProductScorer


EVALUATED_AT = datetime(2026, 8, 28, 12, 0, tzinfo=timezone.utc)


def _snapshot(candidate_id: str, **values: object) -> ProductCandidateSnapshot:
    fields = {
        "candidate_id": candidate_id,
        "platform": "shopee",
        "url": f"https://shopee.vn/{candidate_id}",
        "observed_at": EVALUATED_AT,
        "title": f"Candidate {candidate_id}",
    }
    fields.update(values)
    return ProductCandidateSnapshot(**fields)  # type: ignore[arg-type]


def test_deterministic_ties_use_candidate_id_and_ignore_input_order() -> None:
    candidates = (_snapshot("candidate-c"), _snapshot("candidate-a"), _snapshot("candidate-b"))

    forward = CandidateRanker.rank(candidates, evaluated_at=EVALUATED_AT)
    reversed_result = CandidateRanker.rank(tuple(reversed(candidates)), evaluated_at=EVALUATED_AT)

    assert tuple(entry.candidate_id for entry in forward) == (
        "candidate-a",
        "candidate-b",
        "candidate-c",
    )
    assert forward == reversed_result
    assert all(entry.score.final_score == forward[0].score.final_score for entry in forward)


def test_top_n_returns_immutable_entries_without_mutating_candidates() -> None:
    candidates = (
        _snapshot("weak"),
        _snapshot("strong", sold_count=20_000, review_count=3_000, rating=4.9),
        _snapshot("medium", sold_count=500, review_count=80, rating=4.5),
    )

    result = rank_candidates(candidates, evaluated_at=EVALUATED_AT, shortlist_size=2)

    assert len(result) == 2
    assert tuple(entry.candidate_id for entry in result) == ("strong", "medium")
    assert candidates[0].candidate_id == "weak"
    with pytest.raises(FrozenInstanceError):
        result[0].score = result[1].score  # type: ignore[misc]


def test_duplicate_ids_fail_before_any_candidate_is_scored(monkeypatch: pytest.MonkeyPatch) -> None:
    duplicate = (_snapshot("same"), _snapshot("same"))

    def unexpected_score(*args: object, **kwargs: object) -> None:
        raise AssertionError("scorer must not be called for invalid input")

    monkeypatch.setattr(WinningProductScorer, "score_snapshot", unexpected_score)
    with pytest.raises(CandidateRankingError, match="duplicate candidate_id"):
        CandidateRanker.rank(duplicate, evaluated_at=EVALUATED_AT)


@pytest.mark.parametrize("shortlist_size", [0, -1, 101, 1.5, True])
def test_invalid_shortlist_bounds_fail(shortlist_size: object) -> None:
    with pytest.raises(CandidateRankingError, match="shortlist_size"):
        CandidateRanker.rank(
            (_snapshot("only"),),
            evaluated_at=EVALUATED_AT,
            shortlist_size=shortlist_size,  # type: ignore[arg-type]
        )


def test_shortlist_cannot_exceed_candidate_count() -> None:
    with pytest.raises(CandidateRankingError, match="cannot exceed"):
        CandidateRanker.rank(
            (_snapshot("only"),), evaluated_at=EVALUATED_AT, shortlist_size=2
        )


def test_candidate_collection_bounds_and_evaluated_at_are_required() -> None:
    with pytest.raises(CandidateRankingError, match="candidate count"):
        CandidateRanker.rank((), evaluated_at=EVALUATED_AT)

    too_many = tuple(
        _snapshot(f"candidate-{index:03d}")
        for index in range(MAX_RANKING_CANDIDATES + 1)
    )
    with pytest.raises(CandidateRankingError, match="candidate count"):
        CandidateRanker.rank(too_many, evaluated_at=EVALUATED_AT)

    with pytest.raises(CandidateRankingError, match="evaluated_at"):
        CandidateRanker.rank((_snapshot("only"),), evaluated_at=None)  # type: ignore[arg-type]


def test_sparse_candidate_preserves_missing_signal_and_confidence_semantics() -> None:
    result = CandidateRanker.rank((_snapshot("sparse"),), evaluated_at=EVALUATED_AT)[0]
    score = result.score

    assert score.final_score == 0.0
    assert score.confidence_breakdown.data_completeness == 0.0
    assert score.confidence == 0.0
    assert all(
        signal.provenance == SignalProvenance.MISSING
        for category in score.category_scores.values()
        for signal in category.signals
    )


def test_ranked_entry_preserves_snapshot_identity_and_exact_scorer_result() -> None:
    candidate = _snapshot(
        "preserved",
        sold_count=2_500,
        review_count=400,
        rating=4.8,
        affiliate_commission_rate=12.0,
    )
    expected = WinningProductScorer.score_snapshot(candidate, evaluated_at=EVALUATED_AT)

    ranked = CandidateRanker.rank((candidate,), evaluated_at=EVALUATED_AT)[0]

    assert ranked.candidate is candidate
    assert ranked.candidate_id == candidate.candidate_id
    assert ranked.score == expected
