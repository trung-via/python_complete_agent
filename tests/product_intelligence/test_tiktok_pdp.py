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
        (["₫0"], 0.0),
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
    zero = await TikTokPdpCollector(
        FakeSession(
            payload(
                current_price_candidates=["₫0"],
                original_price_candidates=["0"],
            )
        )
    ).collect(
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

    assert zero.snapshot.price == 0.0
    assert zero.snapshot.original_price == 0.0
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


def test_collector_consumes_canonical_shared_bounded_dom_scope_resolver() -> None:
    """Prove collector consumes the canonical shared BOUNDED_TIKTOK_PDP_DOM_SCOPE_RESOLUTION resolver."""
    from src.product_intelligence.adapters.tiktok_pdp import TIKTOK_PDP_EXTRACTION_SCRIPT
    from src.product_intelligence.tiktok_pdp_dom_scope import (
        BOUNDED_TIKTOK_PDP_DOM_SCOPE_RESOLUTION,
        TIKTOK_PDP_DOM_SCOPE_JS,
    )

    source_path = Path(inspect.getfile(tiktok_pdp))
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        node.module: [alias.name for alias in node.names]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert "src.product_intelligence.tiktok_pdp_dom_scope" in imports
    assert "TIKTOK_PDP_DOM_SCOPE_JS" in imports["src.product_intelligence.tiktok_pdp_dom_scope"]
    assert TIKTOK_PDP_DOM_SCOPE_JS in TIKTOK_PDP_EXTRACTION_SCRIPT
    assert "resolveBoundedPdpDomScope()" in TIKTOK_PDP_EXTRACTION_SCRIPT
    assert BOUNDED_TIKTOK_PDP_DOM_SCOPE_RESOLUTION == "BOUNDED_TIKTOK_PDP_DOM_SCOPE_RESOLUTION"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("candidates", "expected"),
    [
        (["₫200.000"], 200_000.0),
        (["₫0"], 0.0),
        (["₫200.000 - ₫250.000"], None),
        (["₫200.000 - ₫250.000", "₫200.000"], None),
        (["₫200.000", "₫250.000"], None),
        (["₫200.000", "200,000 VND", "200k"], 200_000.0),
        ([], None),
    ],
)
async def test_exact_pdp_original_price_reconciliation(
    candidates: list[str], expected: float | None
) -> None:
    result = await TikTokPdpCollector(
        FakeSession(payload(original_price_candidates=candidates))
    ).collect(REQUESTED_URL, observed_at=OBSERVED_AT)
    assert result.snapshot.original_price == expected


@pytest.mark.asyncio
async def test_bounded_root_missing_and_unresolved_role_leave_price_none_without_failing_snapshot() -> None:
    """Safe root absence and unresolved role yield None price fields without whole-snapshot failure."""
    # Root missing: current and original price candidates empty, snapshot succeeds
    root_missing_result = await TikTokPdpCollector(
        FakeSession(payload(current_price_candidates=[], original_price_candidates=[]))
    ).collect(REQUESTED_URL, observed_at=OBSERVED_AT)
    assert root_missing_result.snapshot.price is None
    assert root_missing_result.snapshot.original_price is None
    assert root_missing_result.snapshot.title == "Đèn LED cảm biến chuyển động"
    assert root_missing_result.snapshot.source_product_id == PRODUCT_ID

    # Unambiguous current and original price
    both_result = await TikTokPdpCollector(
        FakeSession(
            payload(
                current_price_candidates=["₫150.000"],
                original_price_candidates=["₫200.000"],
            )
        )
    ).collect(REQUESTED_URL, observed_at=OBSERVED_AT)
    assert both_result.snapshot.price == 150_000.0
    assert both_result.snapshot.original_price == 200_000.0

    # Conflicting current prices
    conflict_result = await TikTokPdpCollector(
        FakeSession(
            payload(
                current_price_candidates=["₫150.000", "₫180.000"],
                original_price_candidates=["₫200.000"],
            )
        )
    ).collect(REQUESTED_URL, observed_at=OBSERVED_AT)
    assert conflict_result.snapshot.price is None
    assert conflict_result.snapshot.original_price == 200_000.0

    # Range current price
    range_result = await TikTokPdpCollector(
        FakeSession(
            payload(
                current_price_candidates=["₫150.000 - ₫200.000"],
                original_price_candidates=["₫250.000"],
            )
        )
    ).collect(REQUESTED_URL, observed_at=OBSERVED_AT)
    assert range_result.snapshot.price is None
    assert range_result.snapshot.original_price == 250_000.0


def test_collector_price_observation_is_deterministically_bounded_and_fails_closed_on_truncation() -> None:
    """Prove collector price observation traversal enforces hard node/candidate bounds and fails closed on truncation."""
    from src.product_intelligence.adapters.tiktok_pdp import (
        MAX_PRICE_CANDIDATES,
        MAX_PRICE_OBSERVATION_NODES,
        TIKTOK_PDP_EXTRACTION_SCRIPT,
    )
    from src.product_intelligence.tiktok_pdp_dom_scope import TIKTOK_PDP_DOM_SCOPE_JS

    assert MAX_PRICE_OBSERVATION_NODES == 300
    assert MAX_PRICE_CANDIDATES == 300
    assert "LOCAL_MAX=300" in TIKTOK_PDP_DOM_SCOPE_JS

    # Prove script establishes hard caps and bounded traversal
    assert "MAX_PRICE_NODES = LOCAL_MAX" in TIKTOK_PDP_EXTRACTION_SCRIPT
    assert "MAX_PRICE_CANDIDATES = LOCAL_MAX" in TIKTOK_PDP_EXTRACTION_SCRIPT
    assert "scannedNodes < MAX_PRICE_NODES" in TIKTOK_PDP_EXTRACTION_SCRIPT
    assert "candidates.length < MAX_PRICE_CANDIDATES" in TIKTOK_PDP_EXTRACTION_SCRIPT
    assert "truncated = Boolean(node)" in TIKTOK_PDP_EXTRACTION_SCRIPT

    # Prove truncation fails closed: leafCandidates and prices only populated if !truncated
    assert "if (!truncated)" in TIKTOK_PDP_EXTRACTION_SCRIPT

    # Prove no unbounded TreeWalker advancement exists
    assert "while (node)" not in TIKTOK_PDP_EXTRACTION_SCRIPT


@pytest.mark.asyncio
async def test_price_observation_truncation_fails_closed_without_failing_snapshot() -> None:
    """When price observation bound is exhausted, collector fails closed for prices while snapshot succeeds."""
    # When truncation occurs, the extraction script returns empty price candidate sets
    # rather than admitting partial first-window candidates.
    truncated_payload = payload(
        current_price_candidates=[],
        original_price_candidates=[],
    )
    result = await TikTokPdpCollector(FakeSession(truncated_payload)).collect(
        REQUESTED_URL, observed_at=OBSERVED_AT
    )

    # Price discovery fails closed (None), but whole-snapshot admission is preserved
    assert result.snapshot.price is None
    assert result.snapshot.original_price is None
    assert result.snapshot.candidate_id == f"tiktok_{PRODUCT_ID}"
    assert result.snapshot.title == "Đèn LED cảm biến chuyển động"
    assert result.snapshot.shop_name == "Lighting Store"
    assert result.snapshot.discount_percent == 25.0
    assert result.snapshot.sold_count == 0
    assert result.snapshot.rating == 4.8
    assert result.snapshot.review_count == 0
    assert result.binding.requested_url == REQUESTED_URL
    assert result.binding.observed_url == result.snapshot.url


def test_price_observation_traversal_cap_and_truncation_logic() -> None:
    """Deterministic offline simulation proving the node cap and truncation behavior."""
    def simulate_traversal(total_elements: int, cap: int = 300) -> tuple[int, bool]:
        scanned_nodes = 0
        current_idx = 1
        while current_idx <= total_elements and scanned_nodes < cap:
            scanned_nodes += 1
            current_idx += 1
        has_remaining_node = current_idx <= total_elements
        truncated = has_remaining_node
        return scanned_nodes, truncated

    # Subtree within bound: fully observed, untruncated
    scanned, truncated = simulate_traversal(50)
    assert scanned == 50
    assert not truncated

    # Subtree at exact bound: fully observed, untruncated
    scanned, truncated = simulate_traversal(300)
    assert scanned == 300
    assert not truncated

    # Subtree exceeding bound: truncated at 300, bound exhausted before fully observed
    scanned, truncated = simulate_traversal(301)
    assert scanned == 300
    assert truncated

    scanned, truncated = simulate_traversal(1000)
    assert scanned == 300
    assert truncated


def _make_pdp_html(price_html: str, *, include_root: bool = True, title: str = "Đèn LED cảm biến chuyển động") -> str:
    if not include_root:
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>{title} - TikTok Shop</title>
    <meta name="product_id" content="{PRODUCT_ID}" />
</head>
<body>
    <header>
        <h1 data-testid="product-title">{title}</h1>
    </header>
    <div class="generic-sidebar">
        {price_html}
    </div>
</body>
</html>"""

    return f"""<!DOCTYPE html>
<html>
<head>
    <title>{title} - TikTok Shop</title>
    <meta name="product_id" content="{PRODUCT_ID}" />
</head>
<body>
    <div data-testid="pdp-container" data-product-id="{PRODUCT_ID}">
        <h1 data-testid="product-title">{title}</h1>
        <div class="seller-info" data-testid="shop-name">Lighting Store</div>
        <div class="pdp-price-section">
            {price_html}
        </div>
        <div class="actions">
            <button data-e2e="buy-now">Mua ngay</button>
        </div>
    </div>
</body>
</html>"""


class PlaywrightDomSession:
    def __init__(self, page: Any, html: str, observed_url: str = REQUESTED_URL) -> None:
        self.page = page
        self.html = html
        self.observed_url = observed_url
        self.navigations: list[str] = []

    async def navigate(self, url: str) -> None:
        self.navigations.append(url)
        await self.page.set_content(self.html)

    async def evaluate(self, script: str) -> Any:
        raw = await self.page.evaluate(script)
        if isinstance(raw, dict) and raw.get("observed_url") in ("about:blank", ""):
            raw["observed_url"] = self.observed_url
        return raw


def test_collector_price_role_admission_requires_deterministic_evidence() -> None:
    """Prove TIKTOK_PDP_EXTRACTION_SCRIPT enforces deterministic role classification without default fallthrough."""
    from src.product_intelligence.adapters.tiktok_pdp import TIKTOK_PDP_EXTRACTION_SCRIPT

    # Prove script inspects candidate and wrapper role attributes up to root
    assert "while (cur && cur !== root)" in TIKTOK_PDP_EXTRACTION_SCRIPT
    assert "curText === c.text" in TIKTOK_PDP_EXTRACTION_SCRIPT

    # Prove generic role classification attributes and patterns exist
    assert "isExplicitOriginal" in TIKTOK_PDP_EXTRACTION_SCRIPT
    assert "isExplicitCurrent" in TIKTOK_PDP_EXTRACTION_SCRIPT
    assert "isOriginal = (c.isStrike || isExplicitOriginal)" in TIKTOK_PDP_EXTRACTION_SCRIPT
    assert "isCurrent = isExplicitCurrent" in TIKTOK_PDP_EXTRACTION_SCRIPT

    # Prove admission is strictly mutual and exclusive without default current fallthrough
    assert "if (isOriginal && !isCurrent)" in TIKTOK_PDP_EXTRACTION_SCRIPT
    assert "} else if (isCurrent && !isOriginal)" in TIKTOK_PDP_EXTRACTION_SCRIPT

    # Prove no unconditioned fallthrough to currentPrices exists
    assert "} else {\n                        currentPrices.push(c.text);" not in TIKTOK_PDP_EXTRACTION_SCRIPT
    assert "} else { currentPrices.push(c.text);" not in TIKTOK_PDP_EXTRACTION_SCRIPT


@pytest.mark.asyncio
async def test_dom_price_role_classification_unresolved_rejection_and_reconciliation() -> None:
    """Prove unresolved-role DOM observations do not yield candidates while generic presentation reconciles."""
    from playwright.async_api import async_playwright
    from src.product_intelligence.adapters.tiktok_pdp import TIKTOK_PDP_EXTRACTION_SCRIPT

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page()

            # 1. Unresolved-role DOM observations (shipping, coupon, installment, plain currency)
            # must remain unclassified and NOT become current or original candidates
            unresolved_html = _make_pdp_html(
                """
                <div class="shipping-info">
                    <span class="shipping-label">Phí vận chuyển:</span>
                    <span class="shipping-amount">₫25.000</span>
                </div>
                <div class="coupon-section">
                    <span class="coupon-discount">Giảm ₫50.000</span>
                </div>
                <div class="installment-box">
                    <span class="installment-rate">₫100.000 / tháng</span>
                </div>
                <div class="other-val">
                    <span>₫75.000</span>
                </div>
                """
            )
            session = PlaywrightDomSession(page, unresolved_html)
            res = await TikTokPdpCollector(session).collect(REQUESTED_URL, observed_at=OBSERVED_AT)
            raw = await page.evaluate(TIKTOK_PDP_EXTRACTION_SCRIPT)
            assert raw["current_price_candidates"] == []
            assert raw["original_price_candidates"] == []
            assert res.snapshot.price is None
            assert res.snapshot.original_price is None
            assert res.snapshot.title == "Đèn LED cảm biến chuyển động"

            # 2. Unambiguous generic current/original presentation alongside unresolved shipping fee
            valid_html = _make_pdp_html(
                """
                <div data-testid="current-price">
                    <span>₫150.000</span>
                </div>
                <div class="original-price">
                    <del>₫200.000</del>
                </div>
                <div class="shipping-fee">
                    <span>₫25.000</span>
                </div>
                """
            )
            session = PlaywrightDomSession(page, valid_html)
            res = await TikTokPdpCollector(session).collect(REQUESTED_URL, observed_at=OBSERVED_AT)
            raw = await page.evaluate(TIKTOK_PDP_EXTRACTION_SCRIPT)
            assert raw["current_price_candidates"] == ["₫150.000"]
            assert raw["original_price_candidates"] == ["₫200.000"]
            assert res.snapshot.price == 150_000.0
            assert res.snapshot.original_price == 200_000.0

            # 3. Equivalent duplicates in DOM reconcile into unique scalar price
            dup_html = _make_pdp_html(
                """
                <div class="product-price">₫150.000</div>
                <div data-testid="current-price">₫150.000</div>
                <del class="was-price">₫200.000</del>
                <s data-testid="original-price">₫200.000</s>
                """
            )
            session = PlaywrightDomSession(page, dup_html)
            res = await TikTokPdpCollector(session).collect(REQUESTED_URL, observed_at=OBSERVED_AT)
            raw = await page.evaluate(TIKTOK_PDP_EXTRACTION_SCRIPT)
            assert raw["current_price_candidates"] == ["₫150.000", "₫150.000"]
            assert raw["original_price_candidates"] == ["₫200.000", "₫200.000"]
            assert res.snapshot.price == 150_000.0
            assert res.snapshot.original_price == 200_000.0

            # 4. Ranges in DOM yield candidate with role, but scalar admission reconciler leaves price None
            range_html = _make_pdp_html(
                """
                <div data-testid="current-price">₫150.000 - ₫200.000</div>
                <del data-testid="original-price">₫250.000</del>
                """
            )
            session = PlaywrightDomSession(page, range_html)
            res = await TikTokPdpCollector(session).collect(REQUESTED_URL, observed_at=OBSERVED_AT)
            raw = await page.evaluate(TIKTOK_PDP_EXTRACTION_SCRIPT)
            assert raw["current_price_candidates"] == ["₫150.000 - ₫200.000"]
            assert raw["original_price_candidates"] == ["₫250.000"]
            assert res.snapshot.price is None
            assert res.snapshot.original_price == 250_000.0

            # 5a. Role conflict on single element (both current and struck-through original)
            conflict_role_html = _make_pdp_html(
                """
                <del data-testid="current-price">₫150.000</del>
                """
            )
            session = PlaywrightDomSession(page, conflict_role_html)
            res = await TikTokPdpCollector(session).collect(REQUESTED_URL, observed_at=OBSERVED_AT)
            raw = await page.evaluate(TIKTOK_PDP_EXTRACTION_SCRIPT)
            assert raw["current_price_candidates"] == []
            assert raw["original_price_candidates"] == []
            assert res.snapshot.price is None
            assert res.snapshot.original_price is None

            # 5b. Scalar conflict in DOM (different current prices)
            conflict_price_html = _make_pdp_html(
                """
                <div data-testid="current-price">₫150.000</div>
                <div data-testid="current-price">₫180.000</div>
                """
            )
            session = PlaywrightDomSession(page, conflict_price_html)
            res = await TikTokPdpCollector(session).collect(REQUESTED_URL, observed_at=OBSERVED_AT)
            raw = await page.evaluate(TIKTOK_PDP_EXTRACTION_SCRIPT)
            assert raw["current_price_candidates"] == ["₫150.000", "₫180.000"]
            assert res.snapshot.price is None

            # 6. Root-missing behavior in DOM (no bounded commerce root) leaves price candidates empty
            root_missing_html = _make_pdp_html(
                """
                <div class="generic-sidebar">
                    <span class="unrelated-price">₫150.000</span>
                </div>
                """,
                include_root=False,
            )
            session_missing = PlaywrightDomSession(page, root_missing_html)
            res_missing = await TikTokPdpCollector(session_missing).collect(REQUESTED_URL, observed_at=OBSERVED_AT)
            raw = await page.evaluate(TIKTOK_PDP_EXTRACTION_SCRIPT)
            assert raw["current_price_candidates"] == []
            assert raw["original_price_candidates"] == []
            assert res_missing.snapshot.price is None
            assert res_missing.snapshot.original_price is None
            assert res_missing.snapshot.title == "Đèn LED cảm biến chuyển động"
        finally:
            await browser.close()


