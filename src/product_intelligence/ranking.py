from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Sequence, Set, Tuple

from src.product_intelligence.models import ProductCandidateSnapshot, WinningProductScore
from src.product_intelligence.policy import ScoringPolicy
from src.product_intelligence.scoring import WinningProductScorer


MIN_RANKING_CANDIDATES = 1
MAX_RANKING_CANDIDATES = 100
MIN_SHORTLIST_SIZE = 1
MAX_SHORTLIST_SIZE = 100


class CandidateRankingError(ValueError):
    """Raised when a deterministic candidate ranking request is invalid."""


@dataclass(frozen=True)
class RankedCandidate:
    """Immutable association between a candidate snapshot and its canonical score."""

    candidate: ProductCandidateSnapshot
    score: WinningProductScore

    def __post_init__(self) -> None:
        if self.candidate.candidate_id != self.score.candidate_id:
            raise ValueError("candidate and score candidate_id values must match")
        if self.candidate.platform != self.score.platform:
            raise ValueError("candidate and score platform values must match")

    @property
    def candidate_id(self) -> str:
        return self.candidate.candidate_id


class CandidateRanker:
    """
    Pure, deterministic ranking over a bounded collection of candidate snapshots.

    Evaluation is delegated unchanged to ``WinningProductScorer.score_snapshot``.
    This class performs no discovery, approval, ingestion, persistence, or queue work.
    """

    @classmethod
    def rank(
        cls,
        candidates: Sequence[ProductCandidateSnapshot],
        *,
        evaluated_at: datetime,
        shortlist_size: Optional[int] = None,
        policy: Optional[ScoringPolicy] = None,
    ) -> Tuple[RankedCandidate, ...]:
        if evaluated_at is None:
            raise CandidateRankingError(
                "evaluated_at timestamp is required for deterministic ranking"
            )

        candidate_count = len(candidates)
        if not MIN_RANKING_CANDIDATES <= candidate_count <= MAX_RANKING_CANDIDATES:
            raise CandidateRankingError(
                "candidate count must be in "
                f"[{MIN_RANKING_CANDIDATES}, {MAX_RANKING_CANDIDATES}], "
                f"got {candidate_count}"
            )

        if shortlist_size is None:
            result_size = candidate_count
        else:
            if isinstance(shortlist_size, bool) or not isinstance(shortlist_size, int):
                raise CandidateRankingError("shortlist_size must be an integer")
            if not MIN_SHORTLIST_SIZE <= shortlist_size <= MAX_SHORTLIST_SIZE:
                raise CandidateRankingError(
                    "shortlist_size must be in "
                    f"[{MIN_SHORTLIST_SIZE}, {MAX_SHORTLIST_SIZE}], got {shortlist_size}"
                )
            if shortlist_size > candidate_count:
                raise CandidateRankingError(
                    "shortlist_size cannot exceed the number of candidates"
                )
            result_size = shortlist_size

        seen_candidate_ids: Set[str] = set()
        duplicate_ids: Set[str] = set()
        for candidate in candidates:
            if candidate.candidate_id in seen_candidate_ids:
                duplicate_ids.add(candidate.candidate_id)
            seen_candidate_ids.add(candidate.candidate_id)
        if duplicate_ids:
            raise CandidateRankingError(
                "duplicate candidate_id values are not allowed: "
                + ", ".join(sorted(duplicate_ids))
            )

        ranked = tuple(
            RankedCandidate(
                candidate=candidate,
                score=WinningProductScorer.score_snapshot(
                    snapshot=candidate,
                    evaluated_at=evaluated_at,
                    policy=policy,
                ),
            )
            for candidate in candidates
        )

        ordered = sorted(ranked, key=cls._sort_key)
        return tuple(ordered[:result_size])

    rank_candidates = rank

    @staticmethod
    def _sort_key(entry: RankedCandidate) -> tuple[object, ...]:
        score = entry.score
        confidence = score.confidence_breakdown
        return (
            -score.final_score,
            -score.confidence,
            -score.base_score,
            -confidence.data_completeness,
            -confidence.freshness,
            -confidence.source_reliability,
            -confidence.evidence_coverage,
            entry.candidate_id,
        )


def rank_candidates(
    candidates: Sequence[ProductCandidateSnapshot],
    *,
    evaluated_at: datetime,
    shortlist_size: Optional[int] = None,
    policy: Optional[ScoringPolicy] = None,
) -> Tuple[RankedCandidate, ...]:
    """Functional entry point for :meth:`CandidateRanker.rank`."""

    return CandidateRanker.rank(
        candidates,
        evaluated_at=evaluated_at,
        shortlist_size=shortlist_size,
        policy=policy,
    )
