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
    # Category weights (must sum to exactly 100.0, each must be strictly positive and finite)
    demand_weight: float = 25.0
    momentum_weight: float = 20.0
    commercial_attractiveness_weight: float = 15.0
    trust_weight: float = 10.0
    contentability_weight: float = 15.0
    competition_opportunity_weight: float = 15.0

    # Confidence weights (must sum to exactly 1.0, each in [0.0, 1.0] and finite)
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
        # 1. Validate Category Weights
        cat_weights = [
            self.demand_weight,
            self.momentum_weight,
            self.commercial_attractiveness_weight,
            self.trust_weight,
            self.contentability_weight,
            self.competition_opportunity_weight,
        ]
        for w in cat_weights:
            if not math.isfinite(w) or w <= 0.0:
                raise ValueError(f"Category weight must be finite and > 0.0, got {w}")

        total_category_weight = sum(cat_weights)
        if not math.isclose(total_category_weight, 100.0, rel_tol=1e-5):
            raise ValueError(
                f"Category weights must sum to exactly 100.0, got {total_category_weight}"
            )

        # 2. Validate Confidence Weights
        conf_weights = [
            self.completeness_weight,
            self.freshness_weight,
            self.reliability_weight,
            self.evidence_weight,
        ]
        for w in conf_weights:
            if not math.isfinite(w) or not (0.0 <= w <= 1.0):
                raise ValueError(f"Confidence weight must be finite and in [0.0, 1.0], got {w}")

        total_confidence_weight = sum(conf_weights)
        if not math.isclose(total_confidence_weight, 1.0, rel_tol=1e-5):
            raise ValueError(
                f"Confidence weights must sum to exactly 1.0, got {total_confidence_weight}"
            )

        # 3. Validate Decision Thresholds
        for s_thresh in (self.recommended_min_final_score, self.needs_review_min_final_score):
            if not math.isfinite(s_thresh) or not (0.0 <= s_thresh <= 100.0):
                raise ValueError(f"Score threshold must be in [0.0, 100.0], got {s_thresh}")

        for c_thresh in (
            self.recommended_min_confidence,
            self.needs_review_min_confidence,
            self.insufficient_data_confidence_threshold,
        ):
            if not math.isfinite(c_thresh) or not (0.0 <= c_thresh <= 1.0):
                raise ValueError(f"Confidence threshold must be in [0.0, 1.0], got {c_thresh}")

        if self.recommended_min_final_score < self.needs_review_min_final_score:
            raise ValueError("recommended_min_final_score must be >= needs_review_min_final_score")

        if self.recommended_min_confidence < self.needs_review_min_confidence:
            raise ValueError("recommended_min_confidence must be >= needs_review_min_confidence")

        if self.needs_review_min_confidence < self.insufficient_data_confidence_threshold:
            raise ValueError("needs_review_min_confidence must be >= insufficient_data_confidence_threshold")

        if not math.isfinite(self.freshness_half_life_hours) or self.freshness_half_life_hours <= 0:
            raise ValueError("freshness_half_life_hours must be finite and strictly positive")

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
