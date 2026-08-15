from __future__ import annotations

import math
from datetime import datetime, timezone
import pytest

from src.product_intelligence.models import (
    CANONICAL_FACTUAL_SIGNALS,
    CANONICAL_SEMANTIC_SIGNALS,
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


def test_product_candidate_snapshot_commission_rate_boundaries() -> None:
    now = datetime.now(timezone.utc)

    # Valid commission rates in [0.0, 100.0] percentage points
    for valid_rate in [0.0, 1.0, 10.0, 15.0, 20.0, 100.0]:
        s = ProductCandidateSnapshot(
            candidate_id="c1", platform="shopee", url="u", observed_at=now, title="t",
            affiliate_commission_rate=valid_rate,
        )
        assert s.affiliate_commission_rate == valid_rate

    # Invalid commission rates
    with pytest.raises(ValueError, match="affiliate_commission_rate"):
        ProductCandidateSnapshot(
            candidate_id="c1", platform="shopee", url="u", observed_at=now, title="t",
            affiliate_commission_rate=-0.5,
        )

    with pytest.raises(ValueError, match="affiliate_commission_rate"):
        ProductCandidateSnapshot(
            candidate_id="c1", platform="shopee", url="u", observed_at=now, title="t",
            affiliate_commission_rate=105.0,
        )


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


def test_signal_evidence_safety_and_serialization() -> None:
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
    assert "token" not in d
    assert "cookie" not in d
    assert "secret" not in d

    # Helper test
    assert SignalEvidence.format_scalar(15.0, "%") == "15%"
    assert SignalEvidence.format_scalar(15.25, "%") == "15.25%"


def test_signal_evidence_rejects_credential_cookie_and_structured_payloads() -> None:
    now = datetime(2026, 8, 16, 0, 0, 0, tzinfo=timezone.utc)

    # Oversized raw_value_repr (> 120 chars)
    with pytest.raises(ValueError, match="exceeds maximum safe scalar length"):
        SignalEvidence(signal_name="s", source_type="shopee", observed_at=now, raw_value_repr="A" * 121)

    # Multiline raw payload
    with pytest.raises(ValueError, match="single-line scalar diagnostic"):
        SignalEvidence(signal_name="s", source_type="shopee", observed_at=now, raw_value_repr="line1\nline2")

    # Generic cookie assignments
    with pytest.raises(ValueError, match="forbidden"):
        SignalEvidence(signal_name="s", source_type="shopee", observed_at=now, raw_value_repr="cookie=session=abc")

    # Generic authorization headers
    with pytest.raises(ValueError, match="forbidden"):
        SignalEvidence(signal_name="s", source_type="shopee", observed_at=now, raw_value_repr="authorization: Basic abc")

    # Token assignment
    with pytest.raises(ValueError, match="forbidden"):
        SignalEvidence(signal_name="s", source_type="shopee", observed_at=now, raw_value_repr="token=abc")

    # Secret assignment
    with pytest.raises(ValueError, match="forbidden"):
        SignalEvidence(signal_name="s", source_type="shopee", observed_at=now, raw_value_repr="secret=abc")

    # JSON with whitespace
    with pytest.raises(ValueError, match="forbidden"):
        SignalEvidence(signal_name="s", source_type="shopee", observed_at=now, raw_value_repr="{ \"x\": 1 }")

    # HTML fragment
    with pytest.raises(ValueError, match="forbidden"):
        SignalEvidence(signal_name="s", source_type="shopee", observed_at=now, raw_value_repr="<html><body>dump</body></html>")


def test_normalized_signal_canonical_registry_and_provenance_validations() -> None:
    now = datetime.now(timezone.utc)
    ev = SignalEvidence(signal_name="s", source_type="t", observed_at=now)

    # Valid factual observed signal matching canonical registry
    sig = NormalizedSignal(
        name="sold_volume",
        category=ScoreCategory.DEMAND,
        score=0.85,
        provenance=SignalProvenance.OBSERVED,
        evidence_refs=(ev,),
        freshness=0.9,
        source_reliability=1.0,
    )
    assert sig.score == 0.85

    # Valid semantic inferred signal matching canonical semantic registry
    sem_sig = NormalizedSignal(
        name="visual_demo_potential",
        category=ScoreCategory.CONTENTABILITY,
        score=0.75,
        provenance=SignalProvenance.INFERRED,
    )
    assert sem_sig.score == 0.75

    # Valid extensible custom semantic signal in CONTENTABILITY with INFERRED
    custom_sem_sig = NormalizedSignal(
        name="custom_unregistered_hook",
        category=ScoreCategory.CONTENTABILITY,
        score=0.70,
        provenance=SignalProvenance.INFERRED,
    )
    assert custom_sem_sig.score == 0.70

    # Known semantic signal in factual DEMAND category with OBSERVED provenance (MUST BE REJECTED)
    with pytest.raises(ValueError, match="Canonical semantic signal 'visual_demo_potential' must belong to category CONTENTABILITY"):
        NormalizedSignal(
            name="visual_demo_potential",
            category=ScoreCategory.DEMAND,
            score=0.85,
            provenance=SignalProvenance.OBSERVED,
            evidence_refs=(ev,),
        )

    # Known semantic signal in factual DEMAND category with INFERRED provenance (MUST BE REJECTED)
    with pytest.raises(ValueError, match="Canonical semantic signal 'visual_demo_potential' must belong to category CONTENTABILITY"):
        NormalizedSignal(
            name="visual_demo_potential",
            category=ScoreCategory.DEMAND,
            score=0.85,
            provenance=SignalProvenance.INFERRED,
        )

    # Canonical factual signal placed in wrong category (sold_volume in CONTENTABILITY)
    with pytest.raises(ValueError, match="must belong to category DEMAND"):
        NormalizedSignal(
            name="sold_volume",
            category=ScoreCategory.CONTENTABILITY,
            score=0.80,
            provenance=SignalProvenance.INFERRED,
        )

    # Canonical factual signal placed in wrong category (commission_rate in MOMENTUM)
    with pytest.raises(ValueError, match="must belong to category COMMERCIAL_ATTRACTIVENESS"):
        NormalizedSignal(
            name="commission_rate",
            category=ScoreCategory.MOMENTUM,
            score=0.80,
            provenance=SignalProvenance.OBSERVED,
            evidence_refs=(ev,),
        )

    # Canonical factual signal with INFERRED provenance
    with pytest.raises(ValueError, match="cannot have INFERRED provenance"):
        NormalizedSignal(
            name="sold_volume",
            category=ScoreCategory.DEMAND,
            score=0.90,
            provenance=SignalProvenance.INFERRED,
        )

    # Semantic signal with OBSERVED provenance in CONTENTABILITY
    with pytest.raises(ValueError, match="Semantic signal 'visual_demo_potential' cannot have OBSERVED provenance"):
        NormalizedSignal(
            name="visual_demo_potential",
            category=ScoreCategory.CONTENTABILITY,
            score=0.85,
            provenance=SignalProvenance.OBSERVED,
            evidence_refs=(ev,),
        )

    # Custom semantic signal with OBSERVED provenance in CONTENTABILITY
    with pytest.raises(ValueError, match="Semantic signal in category CONTENTABILITY cannot have OBSERVED provenance"):
        NormalizedSignal(
            name="custom_unregistered_hook",
            category=ScoreCategory.CONTENTABILITY,
            score=0.85,
            provenance=SignalProvenance.OBSERVED,
            evidence_refs=(ev,),
        )

    # MISSING signal with non-zero score rejected
    with pytest.raises(ValueError, match="MISSING signals must have score=0.0"):
        NormalizedSignal(
            name="sales_velocity",
            category=ScoreCategory.MOMENTUM,
            score=0.50,
            provenance=SignalProvenance.MISSING,
        )

    # MISSING signal with evidence references rejected
    with pytest.raises(ValueError, match="MISSING signals cannot have evidence references"):
        NormalizedSignal(
            name="sales_velocity",
            category=ScoreCategory.MOMENTUM,
            score=0.0,
            provenance=SignalProvenance.MISSING,
            evidence_refs=(ev,),
        )


def test_scoring_policy_strict_validation() -> None:
    # Valid default policy sums to 100 and 1.0
    policy = ScoringPolicy()
    assert sum(policy.category_weights.values()) == 100.0
    assert (
        policy.completeness_weight
        + policy.freshness_weight
        + policy.reliability_weight
        + policy.evidence_weight
    ) == 1.0

    # Negative category weight that still sums to 100.0 must be rejected
    with pytest.raises(ValueError, match="Category weight must be finite and > 0.0"):
        ScoringPolicy(demand_weight=-20.0, momentum_weight=65.0)

    # Negative confidence weight that still sums to 1.0 must be rejected
    with pytest.raises(ValueError, match="Confidence weight must be finite"):
        ScoringPolicy(completeness_weight=-0.20, freshness_weight=0.85)

    # Non-finite values
    with pytest.raises(ValueError):
        ScoringPolicy(demand_weight=float("nan"))

    with pytest.raises(ValueError):
        ScoringPolicy(completeness_weight=float("inf"))

    # Out of range decision thresholds
    with pytest.raises(ValueError, match="Score threshold"):
        ScoringPolicy(recommended_min_final_score=120.0)

    with pytest.raises(ValueError, match="Confidence threshold"):
        ScoringPolicy(recommended_min_confidence=1.5)

    # Inverted thresholds
    with pytest.raises(ValueError, match="recommended_min_final_score must be >="):
        ScoringPolicy(recommended_min_final_score=60.0, needs_review_min_final_score=70.0)

    with pytest.raises(ValueError, match="recommended_min_confidence must be >="):
        ScoringPolicy(recommended_min_confidence=0.50, needs_review_min_confidence=0.70)

    with pytest.raises(ValueError, match="needs_review_min_confidence must be >="):
        ScoringPolicy(needs_review_min_confidence=0.40, insufficient_data_confidence_threshold=0.50)

    # Non-positive half-life
    with pytest.raises(ValueError, match="freshness_half_life_hours"):
        ScoringPolicy(freshness_half_life_hours=0.0)
