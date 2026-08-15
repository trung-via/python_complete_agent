from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from src.product_intelligence.models import (
    NormalizedSignal,
    ProductCandidateSnapshot,
    ScoreCategory,
    SignalEvidence,
    SignalProvenance,
)
from src.product_intelligence.policy import ScoringPolicy


class SnapshotNormalizer:
    """
    Deterministic, platform-agnostic converter from a raw ProductCandidateSnapshot
    to a sequence of NormalizedSignal instances.
    """

    @staticmethod
    def calculate_freshness(
        observed_at: datetime,
        evaluated_at: datetime,
        half_life_hours: float = 72.0,
    ) -> float:
        """
        Calculates freshness decay in [0.0, 1.0] using exponential half-life.
        If evaluated_at <= observed_at, freshness is 1.0.
        """
        obs_utc = observed_at if observed_at.tzinfo else observed_at.replace(tzinfo=timezone.utc)
        eval_utc = evaluated_at if evaluated_at.tzinfo else evaluated_at.replace(tzinfo=timezone.utc)

        delta_seconds = (eval_utc - obs_utc).total_seconds()
        if delta_seconds <= 0:
            return 1.0

        age_hours = delta_seconds / 3600.0
        freshness = math.pow(0.5, age_hours / half_life_hours)
        return max(0.0, min(1.0, freshness))

    @classmethod
    def normalize_snapshot(
        cls,
        snapshot: ProductCandidateSnapshot,
        evaluated_at: Optional[datetime] = None,
        policy: Optional[ScoringPolicy] = None,
    ) -> List[NormalizedSignal]:
        """Converts observed snapshot fields into normalized signals with evidence."""
        policy = policy or ScoringPolicy()
        eval_time = evaluated_at or datetime.now(timezone.utc)
        freshness = cls.calculate_freshness(
            snapshot.observed_at,
            eval_time,
            policy.freshness_half_life_hours,
        )

        signals: List[NormalizedSignal] = []

        # 1. Demand signals
        if snapshot.sold_count is not None:
            score = min(1.0, math.log10(max(1, snapshot.sold_count)) / 4.0) if snapshot.sold_count > 0 else 0.0
            evidence = SignalEvidence(
                signal_name="sold_count",
                source_type=snapshot.platform,
                source_url=snapshot.url,
                observed_at=snapshot.observed_at,
                collector=snapshot.collector,
                raw_value_repr=str(snapshot.sold_count),
                source_reliability=1.0,
            )
            signals.append(
                NormalizedSignal(
                    name="sold_volume",
                    category=ScoreCategory.DEMAND,
                    score=score,
                    provenance=SignalProvenance.OBSERVED,
                    evidence_refs=(evidence,),
                    freshness=freshness,
                    source_reliability=1.0,
                    weight=1.5,
                )
            )

        if snapshot.review_count is not None:
            score = min(1.0, math.log10(max(1, snapshot.review_count)) / 3.7) if snapshot.review_count > 0 else 0.0
            evidence = SignalEvidence(
                signal_name="review_count",
                source_type=snapshot.platform,
                source_url=snapshot.url,
                observed_at=snapshot.observed_at,
                collector=snapshot.collector,
                raw_value_repr=str(snapshot.review_count),
                source_reliability=1.0,
            )
            signals.append(
                NormalizedSignal(
                    name="review_depth",
                    category=ScoreCategory.DEMAND,
                    score=score,
                    provenance=SignalProvenance.OBSERVED,
                    evidence_refs=(evidence,),
                    freshness=freshness,
                    source_reliability=1.0,
                    weight=1.0,
                )
            )

        # 2. Momentum signals (ONLY from explicit velocity/deltas)
        if snapshot.sales_velocity is not None:
            score = min(1.0, math.log10(max(1.0, snapshot.sales_velocity + 1.0)) / 1.7)
            evidence = SignalEvidence(
                signal_name="sales_velocity",
                source_type=snapshot.platform,
                source_url=snapshot.url,
                observed_at=snapshot.observed_at,
                collector=snapshot.collector,
                raw_value_repr=f"{snapshot.sales_velocity:.2f}/day",
                source_reliability=1.0,
            )
            signals.append(
                NormalizedSignal(
                    name="sales_velocity",
                    category=ScoreCategory.MOMENTUM,
                    score=score,
                    provenance=SignalProvenance.DERIVED,
                    evidence_refs=(evidence,),
                    freshness=freshness,
                    source_reliability=1.0,
                    weight=1.5,
                )
            )

        if snapshot.creator_velocity is not None:
            score = min(1.0, math.log10(max(1.0, snapshot.creator_velocity + 1.0)) / 1.5)
            evidence = SignalEvidence(
                signal_name="creator_velocity",
                source_type=snapshot.platform,
                source_url=snapshot.url,
                observed_at=snapshot.observed_at,
                collector=snapshot.collector,
                raw_value_repr=f"{snapshot.creator_velocity:.2f}/day",
                source_reliability=1.0,
            )
            signals.append(
                NormalizedSignal(
                    name="creator_growth",
                    category=ScoreCategory.MOMENTUM,
                    score=score,
                    provenance=SignalProvenance.DERIVED,
                    evidence_refs=(evidence,),
                    freshness=freshness,
                    source_reliability=1.0,
                    weight=1.0,
                )
            )

        # 3. Commercial Attractiveness
        if snapshot.affiliate_commission_rate is not None:
            rate = snapshot.affiliate_commission_rate
            rate_pct = rate if rate > 1.0 else rate * 100.0
            score = min(1.0, rate_pct / 20.0)
            evidence = SignalEvidence(
                signal_name="affiliate_commission_rate",
                source_type=snapshot.platform,
                source_url=snapshot.url,
                observed_at=snapshot.observed_at,
                collector=snapshot.collector,
                raw_value_repr=f"{rate_pct:.1f}%",
                source_reliability=1.0,
            )
            signals.append(
                NormalizedSignal(
                    name="commission_rate",
                    category=ScoreCategory.COMMERCIAL_ATTRACTIVENESS,
                    score=score,
                    provenance=SignalProvenance.OBSERVED,
                    evidence_refs=(evidence,),
                    freshness=freshness,
                    source_reliability=1.0,
                    weight=1.5,
                )
            )

        if snapshot.discount_percent is not None:
            score = min(1.0, snapshot.discount_percent / 50.0)
            evidence = SignalEvidence(
                signal_name="discount_percent",
                source_type=snapshot.platform,
                source_url=snapshot.url,
                observed_at=snapshot.observed_at,
                collector=snapshot.collector,
                raw_value_repr=f"{snapshot.discount_percent:.1f}%",
                source_reliability=1.0,
            )
            signals.append(
                NormalizedSignal(
                    name="discount_appeal",
                    category=ScoreCategory.COMMERCIAL_ATTRACTIVENESS,
                    score=score,
                    provenance=SignalProvenance.OBSERVED,
                    evidence_refs=(evidence,),
                    freshness=freshness,
                    source_reliability=1.0,
                    weight=1.0,
                )
            )

        # 4. Trust
        if snapshot.rating is not None:
            base_rating_score = max(0.0, (snapshot.rating - 3.0) / 2.0)
            reviews = snapshot.review_count or 0
            damping = min(1.0, reviews / 10.0) if reviews < 10 else 1.0
            trust_score = min(1.0, base_rating_score * (0.5 + 0.5 * damping))

            evidence = SignalEvidence(
                signal_name="rating",
                source_type=snapshot.platform,
                source_url=snapshot.url,
                observed_at=snapshot.observed_at,
                collector=snapshot.collector,
                raw_value_repr=f"{snapshot.rating:.2f} ({reviews} reviews)",
                source_reliability=1.0,
            )
            signals.append(
                NormalizedSignal(
                    name="rating_quality",
                    category=ScoreCategory.TRUST,
                    score=trust_score,
                    provenance=SignalProvenance.OBSERVED,
                    evidence_refs=(evidence,),
                    freshness=freshness,
                    source_reliability=1.0,
                    weight=1.0,
                )
            )

        # 5. Competition Opportunity (Higher is Better: fewer competitors -> higher opportunity score)
        if snapshot.similar_listing_count is not None:
            count = snapshot.similar_listing_count
            score = max(0.0, 1.0 - (math.log10(max(1, count + 1)) / 3.0))
            evidence = SignalEvidence(
                signal_name="similar_listing_count",
                source_type=snapshot.platform,
                source_url=snapshot.url,
                observed_at=snapshot.observed_at,
                collector=snapshot.collector,
                raw_value_repr=str(count),
                source_reliability=1.0,
            )
            signals.append(
                NormalizedSignal(
                    name="market_whitespace",
                    category=ScoreCategory.COMPETITION_OPPORTUNITY,
                    score=score,
                    provenance=SignalProvenance.OBSERVED,
                    evidence_refs=(evidence,),
                    freshness=freshness,
                    source_reliability=1.0,
                    weight=1.0,
                )
            )

        if snapshot.creator_count is not None:
            count = snapshot.creator_count
            score = max(0.0, 1.0 - (math.log10(max(1, count + 1)) / 2.5))
            evidence = SignalEvidence(
                signal_name="creator_count",
                source_type=snapshot.platform,
                source_url=snapshot.url,
                observed_at=snapshot.observed_at,
                collector=snapshot.collector,
                raw_value_repr=str(count),
                source_reliability=1.0,
            )
            signals.append(
                NormalizedSignal(
                    name="creator_whitespace",
                    category=ScoreCategory.COMPETITION_OPPORTUNITY,
                    score=score,
                    provenance=SignalProvenance.OBSERVED,
                    evidence_refs=(evidence,),
                    freshness=freshness,
                    source_reliability=1.0,
                    weight=1.0,
                )
            )

        return signals
