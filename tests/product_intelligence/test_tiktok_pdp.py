from __future__ import annotations

import ast
import inspect
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from src.product_intelligence.adapters import tiktok_pdp
from src.product_intelligence.adapters.tiktok_pdp import (
    TikTokPdpBlockedOrLoginError,
    TikTokPdpCollector,
    TikTokPdpExtractionError,
    TikTokPdpIdentityError,
)


PRODUCT_ID = "1731381331718341815"
OTHER_ID = "1731381331718341816"
REQUESTED_URL = (
    "https://shop.tiktok.com/vn/pdp/"
    "den-led-cam-bien-chuyen-dong-3-che-do-sang-sac-usb-c/"
    f"{PRODUCT_ID}"
)
OBSERVED_AT = datetime(2026, 9, 21, 9, 30, tzinfo=timezone.utc)


class FakeSession:
    def __init__(self, extraction: dict[str, Any], *, failure: Exception | None = None) -> None:
        self.extraction = extraction
        self.failure = failure
        self.navigations: list[str] = []
        self.evaluations: list[str] = []
        self.variant_interactions: list[str] = []

    async def navigate(self, url: str) -> None:
        self.navigations.append(url)
        if self.failure:
            raise self.failure

    async def evaluate(self, script: str) -> dict[str, Any]:
        self.evaluations.append(script)
        return deepcopy(self.extraction)


def payload(**updates: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "observed_url": REQUESTED_URL + "?lang=vi-VN",
        "access_state": "PUBLIC",
        "identity_candidates": [PRODUCT_ID],
        "title_candidates": ["Đèn LED cảm biến chuyển động"],
        "shop_name_candidates": ["Lighting Store"],
        "current_price_candidates": ["₫150.000"],
        "original_price_candidates": ["₫200.000"],
        "discount_candidates": ["25% OFF"],
        "sold_count_candidates": ["Đã bán 0"],
        "rating_candidates": ["4.8 / 5"],
        "review_count_candidates": ["0 reviews"],
    }
    base.update(updates)
    return base


@pytest.mark.asyncio
async def test_valid_exact_pdp_produces_only_canonical_snapshot_and_binding_receipt() -> None:
    session = FakeSession(payload())
    result = await TikTokPdpCollector(session).collect(REQUESTED_URL, observed_at=OBSERVED_AT)

    snapshot = result.snapshot
    assert snapshot.candidate_id == f"tiktok_{PRODUCT_ID}"
    assert snapshot.platform == "tiktok"
    assert snapshot.source_product_id == PRODUCT_ID
    assert snapshot.url == REQUESTED_URL + "?lang=vi-VN"
    assert snapshot.observed_at is OBSERVED_AT
    assert snapshot.collector == "tiktok_public_pdp_v1"
    assert snapshot.title == "Đèn LED cảm biến chuyển động"
    assert snapshot.shop_name == "Lighting Store"
    assert snapshot.price == 150_000.0
    assert snapshot.original_price == 200_000.0
    assert snapshot.discount_percent == 25.0
    assert snapshot.sold_count == 0
    assert snapshot.rating == 4.8
    assert snapshot.review_count == 0

    assert result.binding.requested_url == REQUESTED_URL
    assert result.binding.observed_url == snapshot.url
    assert {basis.source_product_id for basis in result.binding.identity_bases} == {PRODUCT_ID}
    assert session.navigations == [REQUESTED_URL]
    assert len(session.evaluations) == 1
    assert session.variant_interactions == []

    for field in (
        "shop_id",
        "category",
        "brand",
        "model",
        "affiliate_commission_rate",
        "estimated_commission_value",
        "creator_count",
        "video_count",
        "similar_listing_count",
        "sales_velocity",
        "review_velocity",
        "creator_velocity",
        "video_velocity",
    ):
        assert getattr(snapshot, field) is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "extraction",
    [
        payload(observed_url=REQUESTED_URL.replace(PRODUCT_ID, OTHER_ID)),
        payload(identity_candidates=[OTHER_ID]),
        payload(identity_candidates=[PRODUCT_ID, OTHER_ID]),
        payload(observed_url="https://shop.tiktok.com/vn/shop", identity_candidates=[]),
        payload(observed_url="https://example.com/product", identity_candidates=[PRODUCT_ID]),
    ],
)
async def test_identity_mismatch_conflict_absence_and_unrelated_pages_fail_closed(
    extraction: dict[str, Any],
) -> None:
    with pytest.raises(TikTokPdpIdentityError):
        await TikTokPdpCollector(FakeSession(extraction)).collect(
            REQUESTED_URL, observed_at=OBSERVED_AT
        )


@pytest.mark.asyncio
async def test_requested_target_must_be_a_canonical_tiktok_listing_url() -> None:
    non_tiktok = f"https://example.com/product/{PRODUCT_ID}"
    session = FakeSession(payload())
    with pytest.raises(TikTokPdpIdentityError):
        await TikTokPdpCollector(session).collect(non_tiktok, observed_at=OBSERVED_AT)
    assert session.navigations == []


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["BLOCKED", "LOGIN", "CHALLENGE", "CAPTCHA", "UNAVAILABLE"])
async def test_blocked_challenge_and_login_emit_no_snapshot(state: str) -> None:
    with pytest.raises(TikTokPdpBlockedOrLoginError):
        await TikTokPdpCollector(FakeSession(payload(access_state=state))).collect(
            REQUESTED_URL, observed_at=OBSERVED_AT
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "titles",
    [[], ["   "], ["TikTok Shop"], ["Product A", "Product B"]],
)
async def test_title_is_required_explicit_and_unconflicted(titles: list[str]) -> None:
    with pytest.raises(TikTokPdpExtractionError):
        await TikTokPdpCollector(
            FakeSession(payload(title_candidates=titles))
        ).collect(REQUESTED_URL, observed_at=OBSERVED_AT)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("candidates", "expected"),
    [
        (["₫150.000"], 150_000.0),
        (["₫150.000 - ₫200.000"], None),
        (["₫150.000 - ₫200.000", "₫150.000"], None),
        (["₫150.000", "₫200.000"], None),
        (["₫150.000", "150,000 VND", "150k"], 150_000.0),
        ([], None),
    ],
)
async def test_exact_pdp_price_reconciliation(
    candidates: list[str], expected: float | None
) -> None:
    result = await TikTokPdpCollector(
        FakeSession(payload(current_price_candidates=candidates))
    ).collect(REQUESTED_URL, observed_at=OBSERVED_AT)
    assert result.snapshot.price == expected


@pytest.mark.asyncio
async def test_explicit_zero_is_distinct_from_missing_optional_fields() -> None:
    zero = await TikTokPdpCollector(FakeSession(payload())).collect(
        REQUESTED_URL, observed_at=OBSERVED_AT
    )
    missing = await TikTokPdpCollector(
        FakeSession(
            payload(
                shop_name_candidates=[],
                current_price_candidates=[],
                original_price_candidates=[],
                discount_candidates=[],
                sold_count_candidates=[],
                rating_candidates=[],
                review_count_candidates=[],
            )
        )
    ).collect(REQUESTED_URL, observed_at=OBSERVED_AT)

    assert zero.snapshot.sold_count == 0
    assert zero.snapshot.review_count == 0
    assert missing.snapshot.shop_name is None
    assert missing.snapshot.price is None
    assert missing.snapshot.original_price is None
    assert missing.snapshot.discount_percent is None
    assert missing.snapshot.sold_count is None
    assert missing.snapshot.rating is None
    assert missing.snapshot.review_count is None


@pytest.mark.asyncio
async def test_navigation_or_evaluation_failure_is_bounded_extraction_failure() -> None:
    with pytest.raises(TikTokPdpExtractionError):
        await TikTokPdpCollector(
            FakeSession(payload(), failure=RuntimeError("offline fixture failure"))
        ).collect(REQUESTED_URL, observed_at=OBSERVED_AT)


def test_adapter_has_only_bounded_session_and_product_intelligence_dependencies() -> None:
    source_path = Path(inspect.getfile(tiktok_pdp))
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    } | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }

    forbidden = (
        "playwright",
        "product_source",
        "tiktok_scrape_tool",
        "drive",
        "scoring",
        "ranking",
        "approval",
        "persistence",
    )
    assert not any(term in imported.lower() for imported in imports for term in forbidden)
    assert ".start(" not in source
    assert ".close(" not in source
    assert ".click(" not in source
    assert ".new_page(" not in source
    assert "get_or_create_session" not in source
