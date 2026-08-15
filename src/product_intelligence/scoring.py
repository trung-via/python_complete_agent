from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional, Sequence, Set, Tuple

from src.product_intelligence.models import (
    CategoryScore,
    ConfidenceBreakdown,
    DecisionBand,
    NormalizedSignal,
    ProductCandidateSnapshot,
    ScoreCategory,
    SignalEvidence,
    SignalProvenance,
    WinningProductScore,
)
from src.product_intelligence.normalizer import SnapshotNormalizer
from src.product_intelligence.policy import ScoringPolicy


class WinningProductScorer:
    """
    Pure, deterministic winning product intelligence scorer V1.
    Performs zero network, tool, LLM, or filesystem operations.
    Requires an explicit evaluated_at timestamp for 100% reproducible scoring.
    """

    @classmethod
    def score(
        cls,
        candidate_id: str,
        platform: str,
        signals: Sequence[NormalizedSignal],
        evaluated_at: datetime,
        policy: Optional[ScoringPolicy] = None,
    ) -> WinningProductScore:
        """
        Pure function: evaluates a sequence of normalized signals against ScoringPolicy.
        evaluated_at is strictly required.
        """
        if evaluated_at is None:
            raise ValueError("evaluated_at timestamp is required for deterministic scoring")

        policy = policy or ScoringPolicy()

        # 1. Compute Category Scores
        category_scores: Dict[ScoreCategory, CategoryScore] = {}
        available_category_weights: float = 0.0
        available_weighted_scores: float = 0.0

        for category, cat_weight in policy.category_weights.items():
            cat_signals = [s for s in signals if s.category == category]
            present_signals = [
                s for s in cat_signals if s.provenance != SignalProvenance.MISSING
            ]

            if cat_signals:
                total_cat_weight = sum(s.weight for s in cat_signals)
                present_cat_weight = sum(s.weight for s in present_signals)
                coverage = (
                    present_cat_weight / total_cat_weight
                    if total_cat_weight > 0
                    else 0.0
                )
            else:
                coverage = 0.0

            if present_signals:
                present_signal_weight = sum(s.weight for s in present_signals)
                raw_score = (
                    sum(s.score * s.weight for s in present_signals) / present_signal_weight
                    if present_signal_weight > 0
                    else 0.0
                )
                weighted_score = raw_score * cat_weight
                available_category_weights += cat_weight
                available_weighted_scores += weighted_score
            else:
                raw_score = 0.0
                weighted_score = 0.0

            category_scores[category] = CategoryScore(
                category=category,
                raw_score=max(0.0, min(1.0, raw_score)),
                weight=cat_weight,
                weighted_score=max(0.0, min(cat_weight, weighted_score)),
                coverage=max(0.0, min(1.0, coverage)),
                signals=tuple(cat_signals),
            )

        # 2. Base Score: Renormalized over available categories to 0-100 scale
        if available_category_weights > 0:
            base_score = (available_weighted_scores / available_category_weights) * 100.0
        else:
            base_score = 0.0
        base_score = max(0.0, min(100.0, base_score))

        # 3. Confidence Dimensions
        # Dimension A: Data completeness (weighted by canonical category weights)
        data_completeness = sum(
            cs.coverage * (policy.category_weights[cat] / 100.0)
            for cat, cs in category_scores.items()
        )
        data_completeness = max(0.0, min(1.0, data_completeness))

        present_all = [s for s in signals if s.provenance != SignalProvenance.MISSING]

        # Dimension B: Freshness
        if present_all:
            tot_w = sum(s.weight for s in present_all)
            freshness = (
                sum(s.freshness * s.weight for s in present_all) / tot_w
                if tot_w > 0
                else 0.0
            )
        else:
            freshness = 0.0
        freshness = max(0.0, min(1.0, freshness))

        # Dimension C: Source reliability
        if present_all:
            tot_w = sum(s.weight for s in present_all)
            source_reliability = (
                sum(s.source_reliability * s.weight for s in present_all) / tot_w
                if tot_w > 0
                else 0.0
            )
        else:
            source_reliability = 0.0
        source_reliability = max(0.0, min(1.0, source_reliability))

        # Dimension D: Evidence coverage (fraction of present signals with factual evidence)
        if present_all:
            factual_count = sum(
                1
                for s in present_all
                if len(s.evidence_refs) > 0
                and s.provenance in (SignalProvenance.OBSERVED, SignalProvenance.DERIVED)
            )
            evidence_coverage = factual_count / len(present_all)
        else:
            evidence_coverage = 0.0
        evidence_coverage = max(0.0, min(1.0, evidence_coverage))

        # Combined Overall Confidence
        overall_confidence = (
            (policy.completeness_weight * data_completeness)
            + (policy.freshness_weight * freshness)
            + (policy.reliability_weight * source_reliability)
            + (policy.evidence_weight * evidence_coverage)
        )
        overall_confidence = max(0.0, min(1.0, overall_confidence))

        confidence_breakdown = ConfidenceBreakdown(
            data_completeness=data_completeness,
            freshness=freshness,
            source_reliability=source_reliability,
            evidence_coverage=evidence_coverage,
            overall_confidence=overall_confidence,
        )

        # 4. Final Score (Confidence-adjusted)
        final_score = max(0.0, min(100.0, base_score * overall_confidence))

        # 5. Advisory Decision Band
        decision_band = policy.classify_decision(final_score, overall_confidence)

        # 6. Supporting / Weak Signals & Reason Codes
        key_supporting: List[str] = [
            s.name for s in present_all if s.score >= 0.70
        ]
        missing_or_weak: List[str] = []
        for s in signals:
            if s.provenance == SignalProvenance.MISSING:
                missing_or_weak.append(f"MISSING_{s.name}")
            elif s.score < 0.35:
                missing_or_weak.append(s.name)

        # Collect unique evidence references
        unique_evidences: List[SignalEvidence] = []
        seen_evidences: Set[Tuple[str, str, str]] = set()
        for s in present_all:
            for ev in s.evidence_refs:
                key = (ev.signal_name, ev.source_type, str(ev.observed_at))
                if key not in seen_evidences:
                    seen_evidences.add(key)
                    unique_evidences.append(ev)

        # Deterministic reason codes
        reason_codes: List[str] = []

        # Demand
        dem_score = category_scores[ScoreCategory.DEMAND]
        if dem_score.coverage == 0:
            reason_codes.append("DEMAND_DATA_MISSING")
        elif dem_score.raw_score >= 0.75:
            reason_codes.append("STRONG_DEMAND")
        elif dem_score.raw_score < 0.35:
            reason_codes.append("WEAK_DEMAND")

        # Momentum
        mom_score = category_scores[ScoreCategory.MOMENTUM]
        if mom_score.coverage == 0:
            reason_codes.append("INSUFFICIENT_MOMENTUM_DATA")
        elif mom_score.raw_score >= 0.75:
            reason_codes.append("HIGH_MOMENTUM")
        elif mom_score.raw_score < 0.35:
            reason_codes.append("LOW_MOMENTUM")

        # Economics
        comm_score = category_scores[ScoreCategory.COMMERCIAL_ATTRACTIVENESS]
        if comm_score.coverage == 0:
            reason_codes.append("COMMISSION_UNKNOWN")
        elif comm_score.raw_score >= 0.75:
            reason_codes.append("FAVORABLE_ECONOMICS")
        elif comm_score.raw_score < 0.35:
            reason_codes.append("LOW_COMMISSION")

        # Trust
        trust_score = category_scores[ScoreCategory.TRUST]
        if trust_score.coverage == 0:
            reason_codes.append("TRUST_DATA_MISSING")
        elif trust_score.raw_score >= 0.75:
            reason_codes.append("TRUST_SIGNAL_STRONG")
        elif trust_score.raw_score < 0.40:
            reason_codes.append("LOW_RATING")

        # Contentability
        cont_score = category_scores[ScoreCategory.CONTENTABILITY]
        if cont_score.coverage == 0:
            reason_codes.append("CONTENTABILITY_UNEVALUATED")
        elif cont_score.raw_score >= 0.75:
            reason_codes.append("CONTENTABILITY_HIGH")

        # Competition
        comp_score = category_scores[ScoreCategory.COMPETITION_OPPORTUNITY]
        if comp_score.coverage == 0:
            reason_codes.append("COMPETITION_DATA_MISSING")
        elif comp_score.raw_score >= 0.75:
            reason_codes.append("COMPETITION_FAVORABLE")
        elif comp_score.raw_score < 0.35:
            reason_codes.append("HIGH_SATURATION")

        # Confidence diagnostic codes
        if data_completeness >= 0.80:
            reason_codes.append("HIGH_DATA_COMPLETENESS")
        else:
            reason_codes.append("LOW_DATA_COMPLETENESS")

        if freshness < 0.50:
            reason_codes.append("STALE_MARKET_DATA")
        else:
            reason_codes.append("FRESH_MARKET_DATA")

        if evidence_coverage < 0.50:
            reason_codes.append("LOW_EVIDENCE_COVERAGE")
        else:
            reason_codes.append("HIGH_EVIDENCE_COVERAGE")

        if source_reliability < 0.50:
            reason_codes.append("LOW_SOURCE_RELIABILITY")
        else:
            reason_codes.append("HIGH_SOURCE_RELIABILITY")

        return WinningProductScore(
            candidate_id=candidate_id,
            platform=platform,
            base_score=base_score,
            confidence=overall_confidence,
            final_score=final_score,
            decision_band=decision_band,
            category_scores=category_scores,
            confidence_breakdown=confidence_breakdown,
            key_supporting_signals=tuple(key_supporting),
            missing_or_weak_signals=tuple(missing_or_weak),
            evidence_references=tuple(unique_evidences),
            reason_codes=tuple(reason_codes),
            evaluated_at=evaluated_at,
        )

    @classmethod
    def score_snapshot(
        cls,
        snapshot: ProductCandidateSnapshot,
        evaluated_at: datetime,
        semantic_signals: Optional[Sequence[NormalizedSignal]] = None,
        policy: Optional[ScoringPolicy] = None,
    ) -> WinningProductScore:
        """
        Convenience helper: normalizes snapshot fields and scores candidate deterministically.
        evaluated_at is strictly required.
        """
        if evaluated_at is None:
            raise ValueError("evaluated_at timestamp is required for deterministic scoring")

        policy = policy or ScoringPolicy()

        signals = SnapshotNormalizer.normalize_snapshot(
            snapshot=snapshot,
            evaluated_at=evaluated_at,
            policy=policy,
        )
        if semantic_signals:
            signals.extend(semantic_signals)

        return cls.score(
            candidate_id=snapshot.candidate_id,
            platform=snapshot.platform,
            signals=signals,
            evaluated_at=evaluated_at,
            policy=policy,
        )
