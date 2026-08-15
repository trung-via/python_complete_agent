from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict

from src.product_intelligence.models import DecisionBand, ScoreCategory


@dataclass(frozen=True)
class ScoringPolicy:
    """
    Configuration policy for Winning Product Intelligence scoring V1.
    All weights and thresholds are strictly validated in __post_init__.
    """
    # Category weights (must sum to exactly 100.0)
    demand_weight: float = 25.0
    momentum_weight: float = 20.0
    commercial_attractiveness_weight: float = 15.0
    trust_weight: float = 10.0
    contentability_weight: float = 15.0
    competition_opportunity_weight: float = 15.0

    # Confidence weights (must sum to exactly 1.0)
    completeness_weight: float = 0.40
    freshness_weight: float = 0.25
    reliability_weight: float = 0.20
    evidence_weight: float = 0.15

    # Decision band thresholds
    recommended_min_final_score: float = 80.0
    recommended_min_confidence: float = 0.75
    needs_review_min_final_score: float = 65.0
    needs_review_min_confidence: float = 0.65
    insufficient_data_confidence_threshold: float = 0.50

    # Freshness configuration: decay half-life in hours (default 72 hours = 3 days)
    freshness_half_life_hours: float = 72.0

    def __post_init__(self) -> None:
        total_category_weight = (
            self.demand_weight
            + self.momentum_weight
            + self.commercial_attractiveness_weight
            + self.trust_weight
            + self.contentability_weight
            + self.competition_opportunity_weight
        )
        if not math.isclose(total_category_weight, 100.0, rel_tol=1e-5):
            raise ValueError(
                f"Category weights must sum to exactly 100.0, got {total_category_weight}"
            )

        total_confidence_weight = (
            self.completeness_weight
            + self.freshness_weight
            + self.reliability_weight
            + self.evidence_weight
        )
        if not math.isclose(total_confidence_weight, 1.0, rel_tol=1e-5):
            raise ValueError(
                f"Confidence weights must sum to exactly 1.0, got {total_confidence_weight}"
            )

        if self.recommended_min_final_score < self.needs_review_min_final_score:
            raise ValueError("recommended_min_final_score must be >= needs_review_min_final_score")

        if self.recommended_min_confidence < self.needs_review_min_confidence:
            raise ValueError("recommended_min_confidence must be >= needs_review_min_confidence")

        if self.freshness_half_life_hours <= 0:
            raise ValueError("freshness_half_life_hours must be strictly positive")

    @property
    def category_weights(self) -> Dict[ScoreCategory, float]:
        return {
            ScoreCategory.DEMAND: self.demand_weight,
            ScoreCategory.MOMENTUM: self.momentum_weight,
            ScoreCategory.COMMERCIAL_ATTRACTIVENESS: self.commercial_attractiveness_weight,
            ScoreCategory.TRUST: self.trust_weight,
            ScoreCategory.CONTENTABILITY: self.contentability_weight,
            ScoreCategory.COMPETITION_OPPORTUNITY: self.competition_opportunity_weight,
        }

    def classify_decision(self, final_score: float, confidence: float) -> DecisionBand:
        """Deterministically classifies candidate into an advisory decision band."""
        if confidence < self.insufficient_data_confidence_threshold:
            return DecisionBand.INSUFFICIENT_DATA

        if (
            final_score >= self.recommended_min_final_score
            and confidence >= self.recommended_min_confidence
        ):
            return DecisionBand.RECOMMENDED

        if (
            final_score >= self.needs_review_min_final_score
            and confidence >= self.needs_review_min_confidence
        ):
            return DecisionBand.NEEDS_REVIEW

        return DecisionBand.HOLD
