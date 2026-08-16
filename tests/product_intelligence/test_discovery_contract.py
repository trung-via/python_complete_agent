from __future__ import annotations

from datetime import datetime, timezone
import pytest

from src.product_intelligence.discovery import (
    DiscoveryBatch,
    DiscoveryError,
    DiscoveryInvalidRequestError,
    DiscoveryNavigationError,
    DiscoveryBlockedError,
    DiscoveryRequest,
    ProductDiscoveryAdapter,
    MIN_CANDIDATES,
    MAX_CANDIDATES,
    MIN_PAGES,
    MAX_PAGES,
)
from src.product_intelligence.models import ProductCandidateSnapshot


def test_discovery_request_valid_construction() -> None:
    req = DiscoveryRequest(query="tai nghe bluetooth", max_candidates=30, max_pages=2)
    assert req.query == "tai nghe bluetooth"
    assert req.max_candidates == 30
    assert req.max_pages == 2
    assert req.locale == "vi-VN"


def test_discovery_request_rejects_empty_or_whitespace_query() -> None:
    with pytest.raises(DiscoveryInvalidRequestError, match="empty"):
        DiscoveryRequest(query="")

    with pytest.raises(DiscoveryInvalidRequestError, match="empty"):
        DiscoveryRequest(query="   \t\n  ")


def test_discovery_request_rejects_out_of_bounds_candidates() -> None:
    with pytest.raises(DiscoveryInvalidRequestError, match="max_candidates"):
        DiscoveryRequest(query="laptop", max_candidates=0)

    with pytest.raises(DiscoveryInvalidRequestError, match="max_candidates"):
        DiscoveryRequest(query="laptop", max_candidates=-10)

    with pytest.raises(DiscoveryInvalidRequestError, match="max_candidates"):
        DiscoveryRequest(query="laptop", max_candidates=101)


def test_discovery_request_rejects_out_of_bounds_pages() -> None:
    with pytest.raises(DiscoveryInvalidRequestError, match="max_pages"):
        DiscoveryRequest(query="ban phim", max_pages=0)

    with pytest.raises(DiscoveryInvalidRequestError, match="max_pages"):
        DiscoveryRequest(query="ban phim", max_pages=6)


def test_discovery_batch_immutability_and_serialization() -> None:
    obs_time = datetime(2026, 8, 16, 12, 0, 0, tzinfo=timezone.utc)
    snap = ProductCandidateSnapshot(
        candidate_id="shopee_123",
        platform="shopee",
        url="https://shopee.vn/product/123/456",
        observed_at=obs_time,
        title="Wireless Mouse",
        price=120000.0,
        sold_count=500,
    )

    batch = DiscoveryBatch(
        platform="shopee",
        query="chuot khong day",
        observed_at=obs_time,
        candidates=(snap,),
        pages_examined=1,
        raw_items_seen=1,
        diagnostic_codes=("DISCOVERY_SUCCESS",),
    )

    # Immutability
    with pytest.raises(Exception):
        batch.platform = "tiktok"  # type: ignore

    # Serialization
    d = batch.to_dict()
    assert d["platform"] == "shopee"
    assert d["query"] == "chuot khong day"
    assert d["candidate_count"] == 1
    assert len(d["candidates"]) == 1
    assert d["candidates"][0]["candidate_id"] == "shopee_123"
    assert d["pages_examined"] == 1
    assert d["raw_items_seen"] == 1
    assert d["diagnostic_codes"] == ["DISCOVERY_SUCCESS"]

    # Verify no raw sensitive keys leaked
    assert "token" not in d
    assert "cookie" not in d
    assert "html" not in d
