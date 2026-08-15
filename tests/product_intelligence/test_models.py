from __future__ import annotations

from datetime import datetime, timezone
import pytest

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
from src.product_intelligence.policy import ScoringPolicy


def test_product_candidate_snapshot_immutable_and_serialization() -> None:
    now = datetime(2026, 8, 16, 0, 0, 0, tzinfo=timezone.utc)
    snapshot = ProductCandidateSnapshot(
        candidate_id="c_123",
        platform="shopee",
        url="https://shopee.vn/product/123/456",
        observed_at=now,
        title="Ergonomic Mechanical Keyboard",
        price=150000.0,
        original_price=200000.0,
        discount_percent=25.0,
        sold_count=1200,
        rating=4.8,
        review_count=350,
        affiliate_commission_rate=12.5,
    )

    # Immutability
    with pytest.raises(Exception):
        snapshot.price = 100000.0  # type: ignore

    # Serialization
    d = snapshot.to_dict()
    assert d["candidate_id"] == "c_123"
    assert d["platform"] == "shopee"
    assert d["title"] == "Ergonomic Mechanical Keyboard"
    assert d["sold_count"] == 1200
    assert d["rating"] == 4.8
    assert d["discount_percent"] == 25.0
    assert d["affiliate_commission_rate"] == 12.5
    assert d["sales_velocity"] is None  # Remains None, never converted to 0
    assert d["video_count"] is None


def test_product_candidate_snapshot_rejects_invalid_values() -> None:
    now = datetime.now(timezone.utc)

    # Negative price
    with pytest.raises(ValueError, match="price cannot be negative"):
        ProductCandidateSnapshot(candidate_id="c1", platform="shopee", url="u", observed_at=now, title="t", price=-10.0)

    # Negative sold count
    with pytest.raises(ValueError, match="sold_count cannot be negative"):
        ProductCandidateSnapshot(candidate_id="c1", platform="shopee", url="u", observed_at=now, title="t", sold_count=-5)

    # Invalid rating (> 5.0)
    with pytest.raises(ValueError, match="rating must be in"):
        ProductCandidateSnapshot(candidate_id="c1", platform="shopee", url="u", observed_at=now, title="t", rating=5.5)

    # Invalid rating (< 0.0)
    with pytest.raises(ValueError, match="rating must be in"):
        ProductCandidateSnapshot(candidate_id="c1", platform="shopee", url="u", observed_at=now, title="t", rating=-0.1)

    # Invalid discount (> 100.0)
    with pytest.raises(ValueError, match="discount_percent must be in"):
        ProductCandidateSnapshot(candidate_id="c1", platform="shopee", url="u", observed_at=now, title="t", discount_percent=120.0)

    # Missing candidate_id
    with pytest.raises(ValueError, match="candidate_id cannot be empty"):
        ProductCandidateSnapshot(candidate_id="", platform="shopee", url="u", observed_at=now, title="t")


def test_signal_evidence_validation_and_serialization() -> None:
    now = datetime(2026, 8, 16, 0, 0, 0, tzinfo=timezone.utc)
    ev = SignalEvidence(
        signal_name="sold_count",
        source_type="shopee",
        source_url="https://shopee.vn/p/1",
        observed_at=now,
        collector="shopee_adapter",
        raw_value_repr="1200",
        source_reliability=0.95,
    )
    assert ev.source_reliability == 0.95

    # Invalid reliability > 1.0
    with pytest.raises(ValueError, match="source_reliability"):
        SignalEvidence(
            signal_name="s",
            source_type="shopee",
            observed_at=now,
            source_reliability=1.5,
        )

    d = ev.to_dict()
    assert d["signal_name"] == "sold_count"
    assert d["source_reliability"] == 0.95
    # Asserts no sensitive keys in dictionary
    assert "token" not in d
    assert "cookie" not in d
    assert "secret" not in d


def test_normalized_signal_range_validations() -> None:
    now = datetime.now(timezone.utc)
    ev = SignalEvidence(signal_name="s", source_type="t", observed_at=now)

    # Valid signal
    sig = NormalizedSignal(
        name="test_demand",
        category=ScoreCategory.DEMAND,
        score=0.85,
        provenance=SignalProvenance.OBSERVED,
        evidence_refs=(ev,),
        freshness=0.9,
        source_reliability=1.0,
    )
    assert sig.score == 0.85

    # Score > 1.0
    with pytest.raises(ValueError, match="score must be in"):
        NormalizedSignal(
            name="invalid_sig",
            category=ScoreCategory.DEMAND,
            score=1.2,
            provenance=SignalProvenance.OBSERVED,
        )

    # Freshness < 0.0
    with pytest.raises(ValueError, match="freshness must be in"):
        NormalizedSignal(
            name="invalid_sig",
            category=ScoreCategory.DEMAND,
            score=0.5,
            provenance=SignalProvenance.OBSERVED,
            freshness=-0.1,
        )


def test_scoring_policy_weights_validation() -> None:
    # Valid default policy sums to 100 and 1.0
    policy = ScoringPolicy()
    assert sum(policy.category_weights.values()) == 100.0
    assert (
        policy.completeness_weight
        + policy.freshness_weight
        + policy.reliability_weight
        + policy.evidence_weight
    ) == 1.0

    # Invalid category weights sum
    with pytest.raises(ValueError, match="Category weights must sum to exactly 100.0"):
        ScoringPolicy(demand_weight=30.0)  # Total 105.0

    # Invalid confidence weights sum
    with pytest.raises(ValueError, match="Confidence weights must sum to exactly 1.0"):
        ScoringPolicy(completeness_weight=0.50)  # Total 1.10
