from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any
import pytest

from src.product_intelligence.models import (
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
from src.product_intelligence.scoring import WinningProductScorer


def test_identical_input_produces_identical_deterministic_score() -> None:
    eval_time = datetime(2026, 8, 16, 12, 0, 0, tzinfo=timezone.utc)
    obs_time = datetime(2026, 8, 16, 0, 0, 0, tzinfo=timezone.utc)

    snapshot = ProductCandidateSnapshot(
        candidate_id="c_det_1",
        platform="shopee",
        url="https://shopee.vn/product/1",
        observed_at=obs_time,
        title="Wireless Charging Stand",
        sold_count=5000,
        rating=4.9,
        review_count=1200,
        affiliate_commission_rate=15.0,
        sales_velocity=45.0,
        similar_listing_count=5,
    )

    policy = ScoringPolicy()

    score1 = WinningProductScorer.score_snapshot(snapshot, evaluated_at=eval_time, policy=policy)
    score2 = WinningProductScorer.score_snapshot(snapshot, evaluated_at=eval_time, policy=policy)

    assert score1.final_score == score2.final_score
    assert score1.base_score == score2.base_score
    assert score1.confidence == score2.confidence
    assert score1.decision_band == score2.decision_band
    assert score1.to_dict() == score2.to_dict()


def test_evaluated_at_is_strictly_required_for_determinism() -> None:
    """Verifies that scorer and normalizer fail closed if evaluated_at is omitted."""
    snapshot = ProductCandidateSnapshot(
        candidate_id="c_det", platform="shopee", url="u",
        observed_at=datetime(2026, 8, 16, 0, 0, tzinfo=timezone.utc),
        title="Item", sold_count=100,
    )

    with pytest.raises((TypeError, ValueError)):
        WinningProductScorer.score_snapshot(snapshot, evaluated_at=None)  # type: ignore

    with pytest.raises((TypeError, ValueError)):
        WinningProductScorer.score("c_det", "shopee", [], evaluated_at=None)  # type: ignore

    with pytest.raises((TypeError, ValueError)):
        SnapshotNormalizer.normalize_snapshot(snapshot, evaluated_at=None)  # type: ignore


def test_score_and_confidence_bounds() -> None:
    eval_time = datetime(2026, 8, 16, 12, 0, 0, tzinfo=timezone.utc)

    # Empty candidate signals
    empty_score = WinningProductScorer.score("c_empty", "shopee", [], evaluated_at=eval_time)
    assert empty_score.base_score == 0.0
    assert empty_score.confidence == 0.0
    assert empty_score.final_score == 0.0
    assert empty_score.decision_band == DecisionBand.INSUFFICIENT_DATA

    # Maxed out signals for all 6 categories (with proper provenance)
    obs_time = eval_time
    ev = SignalEvidence("test", "shopee", obs_time)
    max_signals = [
        NormalizedSignal("s_demand", ScoreCategory.DEMAND, score=1.0, provenance=SignalProvenance.OBSERVED, evidence_refs=(ev,)),
        NormalizedSignal("s_momentum", ScoreCategory.MOMENTUM, score=1.0, provenance=SignalProvenance.DERIVED, evidence_refs=(ev,)),
        NormalizedSignal("s_commercial", ScoreCategory.COMMERCIAL_ATTRACTIVENESS, score=1.0, provenance=SignalProvenance.OBSERVED, evidence_refs=(ev,)),
        NormalizedSignal("s_trust", ScoreCategory.TRUST, score=1.0, provenance=SignalProvenance.OBSERVED, evidence_refs=(ev,)),
        NormalizedSignal("s_content", ScoreCategory.CONTENTABILITY, score=1.0, provenance=SignalProvenance.INFERRED),
        NormalizedSignal("s_comp", ScoreCategory.COMPETITION_OPPORTUNITY, score=1.0, provenance=SignalProvenance.OBSERVED, evidence_refs=(ev,)),
    ]

    max_score = WinningProductScorer.score("c_max", "shopee", max_signals, evaluated_at=eval_time)
    assert 0.0 <= max_score.base_score <= 100.0
    assert 0.0 <= max_score.confidence <= 1.0
    assert 0.0 <= max_score.final_score <= 100.0
    assert max_score.final_score == pytest.approx(max_score.base_score * max_score.confidence, rel=1e-4)


def test_base_score_renormalization_and_sparse_confidence_damping() -> None:
    """
    When only Demand category is observed and has perfect signals (1.0),
    base_score is 100.0 (100% of available observed strength).
    Completeness is 0.25, so confidence is ~0.70, and final_score is 70.0.
    Missing signals are explicitly reported in missing_or_weak_signals.
    """
    eval_time = datetime(2026, 8, 16, 12, 0, 0, tzinfo=timezone.utc)
    ev = SignalEvidence("sold_count", "shopee", eval_time)

    # Only DEMAND category has observed signals; all other categories are MISSING
    signals = [
        NormalizedSignal("sold_volume", ScoreCategory.DEMAND, score=1.0, provenance=SignalProvenance.OBSERVED, evidence_refs=(ev,)),
        NormalizedSignal("review_depth", ScoreCategory.DEMAND, score=1.0, provenance=SignalProvenance.OBSERVED, evidence_refs=(ev,)),
        NormalizedSignal("sales_velocity", ScoreCategory.MOMENTUM, score=0.0, provenance=SignalProvenance.MISSING),
        NormalizedSignal("commission_rate", ScoreCategory.COMMERCIAL_ATTRACTIVENESS, score=0.0, provenance=SignalProvenance.MISSING),
        NormalizedSignal("rating_quality", ScoreCategory.TRUST, score=0.0, provenance=SignalProvenance.MISSING),
        NormalizedSignal("visual_demo_potential", ScoreCategory.CONTENTABILITY, score=0.0, provenance=SignalProvenance.MISSING),
        NormalizedSignal("market_whitespace", ScoreCategory.COMPETITION_OPPORTUNITY, score=0.0, provenance=SignalProvenance.MISSING),
    ]

    score = WinningProductScorer.score("c_sparse", "shopee", signals, evaluated_at=eval_time)
    assert score.base_score == pytest.approx(100.0, rel=1e-4)
    assert score.confidence_breakdown.data_completeness == pytest.approx(0.25, rel=1e-4)
    assert score.confidence == pytest.approx(0.70, rel=1e-4)
    assert score.final_score == pytest.approx(70.0, rel=1e-4)
    assert "MISSING_sales_velocity" in score.missing_or_weak_signals
    assert "MISSING_commission_rate" in score.missing_or_weak_signals


def test_partial_category_completeness() -> None:
    """If Demand has sold_volume (weight 1.5) but lacks review_depth (weight 1.0), coverage is 0.60."""
    eval_time = datetime(2026, 8, 16, 12, 0, 0, tzinfo=timezone.utc)
    ev = SignalEvidence("sold_count", "shopee", eval_time)

    signals = [
        NormalizedSignal("sold_volume", ScoreCategory.DEMAND, score=1.0, provenance=SignalProvenance.OBSERVED, evidence_refs=(ev,), weight=1.5),
        NormalizedSignal("review_depth", ScoreCategory.DEMAND, score=0.0, provenance=SignalProvenance.MISSING, weight=1.0),
    ]

    score = WinningProductScorer.score("c_partial", "shopee", signals, evaluated_at=eval_time)
    dem_cat = score.category_scores[ScoreCategory.DEMAND]
    assert dem_cat.coverage == pytest.approx(0.60, rel=1e-4)
    assert dem_cat.raw_score == pytest.approx(1.0, rel=1e-4)
    assert score.confidence_breakdown.data_completeness == pytest.approx(0.15, rel=1e-4)


def test_commission_normalization_percentage_points_continuity() -> None:
    """Verifies no discontinuity around 1.0% commission."""
    eval_time = datetime(2026, 8, 16, 12, 0, 0, tzinfo=timezone.utc)

    # 0.0% -> 0.0
    s0 = ProductCandidateSnapshot(candidate_id="c0", platform="shopee", url="u", observed_at=eval_time, title="T", affiliate_commission_rate=0.0)
    sig0 = [s for s in SnapshotNormalizer.normalize_snapshot(s0, evaluated_at=eval_time) if s.name == "commission_rate"][0]
    assert sig0.score == pytest.approx(0.0, rel=1e-4)

    # 1.0% -> 1.0 / 20.0 = 0.05
    s1 = ProductCandidateSnapshot(candidate_id="c1", platform="shopee", url="u", observed_at=eval_time, title="T", affiliate_commission_rate=1.0)
    sig1 = [s for s in SnapshotNormalizer.normalize_snapshot(s1, evaluated_at=eval_time) if s.name == "commission_rate"][0]
    assert sig1.score == pytest.approx(0.05, rel=1e-4)

    # 1.01% -> 1.01 / 20.0 = 0.0505 (continuous, monotonically increasing)
    s1_01 = ProductCandidateSnapshot(candidate_id="c1_01", platform="shopee", url="u", observed_at=eval_time, title="T", affiliate_commission_rate=1.01)
    sig1_01 = [s for s in SnapshotNormalizer.normalize_snapshot(s1_01, evaluated_at=eval_time) if s.name == "commission_rate"][0]
    assert sig1_01.score > sig1.score
    assert sig1_01.score == pytest.approx(0.0505, rel=1e-4)

    # 10.0% -> 0.50
    s10 = ProductCandidateSnapshot(candidate_id="c10", platform="shopee", url="u", observed_at=eval_time, title="T", affiliate_commission_rate=10.0)
    sig10 = [s for s in SnapshotNormalizer.normalize_snapshot(s10, evaluated_at=eval_time) if s.name == "commission_rate"][0]
    assert sig10.score == pytest.approx(0.50, rel=1e-4)

    # 20.0% -> 1.0
    s20 = ProductCandidateSnapshot(candidate_id="c20", platform="shopee", url="u", observed_at=eval_time, title="T", affiliate_commission_rate=20.0)
    sig20 = [s for s in SnapshotNormalizer.normalize_snapshot(s20, evaluated_at=eval_time) if s.name == "commission_rate"][0]
    assert sig20.score == pytest.approx(1.0, rel=1e-4)


def test_stale_data_lowers_freshness_and_confidence() -> None:
    eval_time = datetime(2026, 8, 16, 12, 0, 0, tzinfo=timezone.utc)
    fresh_obs_time = eval_time - timedelta(hours=2)
    stale_obs_time = eval_time - timedelta(days=14)

    policy = ScoringPolicy(freshness_half_life_hours=72.0)

    fresh_snap = ProductCandidateSnapshot(
        candidate_id="c_fresh", platform="shopee", url="u", observed_at=fresh_obs_time, title="Item",
        sold_count=1000, rating=4.8, affiliate_commission_rate=10.0,
    )
    stale_snap = ProductCandidateSnapshot(
        candidate_id="c_stale", platform="shopee", url="u", observed_at=stale_obs_time, title="Item",
        sold_count=1000, rating=4.8, affiliate_commission_rate=10.0,
    )

    fresh_score = WinningProductScorer.score_snapshot(fresh_snap, evaluated_at=eval_time, policy=policy)
    stale_score = WinningProductScorer.score_snapshot(stale_snap, evaluated_at=eval_time, policy=policy)

    assert fresh_score.base_score == pytest.approx(stale_score.base_score, rel=1e-4)
    assert fresh_score.confidence_breakdown.freshness > stale_score.confidence_breakdown.freshness
    assert fresh_score.confidence > stale_score.confidence
    assert fresh_score.final_score > stale_score.final_score
    assert "STALE_MARKET_DATA" in stale_score.reason_codes


def test_missing_evidence_lowers_evidence_coverage_confidence() -> None:
    eval_time = datetime(2026, 8, 16, 12, 0, 0, tzinfo=timezone.utc)
    ev = SignalEvidence("s", "shopee", eval_time)

    with_evidence = [
        NormalizedSignal("s1", ScoreCategory.DEMAND, 1.0, SignalProvenance.OBSERVED, evidence_refs=(ev,)),
        NormalizedSignal("s2", ScoreCategory.TRUST, 1.0, SignalProvenance.OBSERVED, evidence_refs=(ev,)),
    ]
    without_evidence = [
        NormalizedSignal("s1", ScoreCategory.DEMAND, 1.0, SignalProvenance.DERIVED, evidence_refs=()),
        NormalizedSignal("s2", ScoreCategory.TRUST, 1.0, SignalProvenance.DERIVED, evidence_refs=()),
    ]

    score_ev = WinningProductScorer.score("c1", "shopee", with_evidence, evaluated_at=eval_time)
    score_no_ev = WinningProductScorer.score("c2", "shopee", without_evidence, evaluated_at=eval_time)

    assert score_ev.confidence_breakdown.evidence_coverage == 1.0
    assert score_no_ev.confidence_breakdown.evidence_coverage == 0.0
    assert score_ev.confidence > score_no_ev.confidence
    assert "LOW_EVIDENCE_COVERAGE" in score_no_ev.reason_codes


def test_one_snapshot_absolute_sold_count_cannot_masquerade_as_momentum() -> None:
    eval_time = datetime(2026, 8, 16, 12, 0, 0, tzinfo=timezone.utc)
    snapshot = ProductCandidateSnapshot(
        candidate_id="c_nomom",
        platform="shopee",
        url="u",
        observed_at=eval_time,
        title="High Sales Static Item",
        sold_count=50000,
        rating=4.9,
    )

    score = WinningProductScorer.score_snapshot(snapshot, evaluated_at=eval_time)
    mom_cat = score.category_scores[ScoreCategory.MOMENTUM]
    assert mom_cat.coverage == 0.0
    assert mom_cat.raw_score == 0.0
    assert mom_cat.weighted_score == 0.0
    assert "INSUFFICIENT_MOMENTUM_DATA" in score.reason_codes


def test_competition_category_higher_is_better() -> None:
    eval_time = datetime(2026, 8, 16, 12, 0, 0, tzinfo=timezone.utc)

    low_comp_snap = ProductCandidateSnapshot(
        candidate_id="c_low", platform="shopee", url="u", observed_at=eval_time, title="T",
        similar_listing_count=2, creator_count=1,
    )
    high_comp_snap = ProductCandidateSnapshot(
        candidate_id="c_high", platform="shopee", url="u", observed_at=eval_time, title="T",
        similar_listing_count=250, creator_count=150,
    )

    score_low = WinningProductScorer.score_snapshot(low_comp_snap, evaluated_at=eval_time)
    score_high = WinningProductScorer.score_snapshot(high_comp_snap, evaluated_at=eval_time)

    cat_low = score_low.category_scores[ScoreCategory.COMPETITION_OPPORTUNITY]
    cat_high = score_high.category_scores[ScoreCategory.COMPETITION_OPPORTUNITY]

    assert cat_low.raw_score > cat_high.raw_score
    assert cat_low.weighted_score > cat_high.weighted_score
    assert "COMPETITION_FAVORABLE" in score_low.reason_codes
    assert "HIGH_SATURATION" in score_high.reason_codes


def test_decision_band_exact_threshold_boundaries() -> None:
    policy = ScoringPolicy(
        recommended_min_final_score=80.0,
        recommended_min_confidence=0.75,
        needs_review_min_final_score=65.0,
        needs_review_min_confidence=0.65,
        insufficient_data_confidence_threshold=0.50,
    )

    # 1. INSUFFICIENT_DATA (confidence < 0.50 regardless of score)
    assert policy.classify_decision(final_score=95.0, confidence=0.49) == DecisionBand.INSUFFICIENT_DATA

    # 2. RECOMMENDED (final_score >= 80.0 and confidence >= 0.75)
    assert policy.classify_decision(final_score=80.0, confidence=0.75) == DecisionBand.RECOMMENDED
    assert policy.classify_decision(final_score=85.0, confidence=0.80) == DecisionBand.RECOMMENDED

    # 3. NEEDS_REVIEW (final_score >= 65.0 and confidence >= 0.65, but not recommended)
    assert policy.classify_decision(final_score=65.0, confidence=0.65) == DecisionBand.NEEDS_REVIEW
    assert policy.classify_decision(final_score=82.0, confidence=0.70) == DecisionBand.NEEDS_REVIEW

    # 4. HOLD (everything else with confidence >= 0.50)
    assert policy.classify_decision(final_score=60.0, confidence=0.65) == DecisionBand.HOLD
    assert policy.classify_decision(final_score=70.0, confidence=0.55) == DecisionBand.HOLD


def test_reason_codes_and_breakdown_explainability() -> None:
    eval_time = datetime(2026, 8, 16, 12, 0, 0, tzinfo=timezone.utc)
    snapshot = ProductCandidateSnapshot(
        candidate_id="c_explain",
        platform="shopee",
        url="https://shopee.vn/item",
        observed_at=eval_time,
        title="Winning Wireless Earbuds",
        sold_count=15000,
        rating=4.95,
        review_count=3500,
        affiliate_commission_rate=20.0,
        discount_percent=30.0,
        sales_velocity=80.0,
        creator_velocity=5.0,
        similar_listing_count=3,
        creator_count=2,
    )

    content_signal = NormalizedSignal(
        name="visual_demo_potential",
        category=ScoreCategory.CONTENTABILITY,
        score=0.90,
        provenance=SignalProvenance.INFERRED,
        freshness=1.0,
        source_reliability=0.9,
    )

    score = WinningProductScorer.score_snapshot(
        snapshot,
        evaluated_at=eval_time,
        semantic_signals=[content_signal],
    )

    assert "STRONG_DEMAND" in score.reason_codes
    assert "HIGH_MOMENTUM" in score.reason_codes
    assert "FAVORABLE_ECONOMICS" in score.reason_codes
    assert "TRUST_SIGNAL_STRONG" in score.reason_codes
    assert "CONTENTABILITY_HIGH" in score.reason_codes
    assert "COMPETITION_FAVORABLE" in score.reason_codes
    assert "FRESH_MARKET_DATA" in score.reason_codes
    assert len(score.key_supporting_signals) > 0
    assert len(score.evidence_references) > 0
    assert score.decision_band == DecisionBand.RECOMMENDED


def test_scorer_purity_no_filesystem_mutation_and_no_side_effects(tmp_path: Any) -> None:
    eval_time = datetime(2026, 8, 16, 12, 0, 0, tzinfo=timezone.utc)
    snapshot = ProductCandidateSnapshot(
        candidate_id="c_pure", platform="shopee", url="u", observed_at=eval_time, title="T",
        sold_count=100, rating=4.5,
    )

    initial_files = list(tmp_path.iterdir())
    score = WinningProductScorer.score_snapshot(snapshot, evaluated_at=eval_time)
    after_files = list(tmp_path.iterdir())

    assert initial_files == after_files
    assert isinstance(score, WinningProductScore)
