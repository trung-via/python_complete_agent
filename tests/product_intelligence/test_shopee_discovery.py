from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import pytest

from src.product_intelligence.adapters.shopee import ShopeeDiscoveryAdapter
from src.product_intelligence.discovery import (
    DiscoveryBatch,
    DiscoveryBlockedError,
    DiscoveryError,
    DiscoveryInvalidRequestError,
    DiscoveryNavigationError,
    DiscoveryRequest,
)
from src.product_intelligence.models import ProductCandidateSnapshot


@pytest.fixture(autouse=True)
def no_real_readiness_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure all tests in this module execute with zero wall-clock sleep by default."""
    async def _instant_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr("src.product_intelligence.adapters.shopee._readiness_sleep", _instant_sleep)


class FakePage:
    """Test fake for browser page emulation with configurable navigation and extraction returns."""

    def __init__(
        self,
        script_results: Optional[List[Dict[str, Any]]] = None,
        fail_navigation_on_page: Optional[int] = None,
    ) -> None:
        self.script_results = script_results or []
        self.fail_navigation_on_page = fail_navigation_on_page
        self.navigated_urls: List[str] = []
        self.call_count = 0
        self.closed = False

    async def goto(self, url: str, timeout: int = 30000, wait_until: str = "domcontentloaded") -> None:
        current_page_idx = len(self.navigated_urls) + 1
        if self.fail_navigation_on_page is not None and current_page_idx == self.fail_navigation_on_page:
            raise RuntimeError(f"Network error on page {current_page_idx}")
        self.navigated_urls.append(url)

    async def evaluate(self, script: str) -> Any:
        if "scrollBy" in script:
            return None

        idx = min(self.call_count, len(self.script_results) - 1) if self.script_results else -1
        self.call_count += 1
        if idx >= 0:
            return self.script_results[idx]
        return {"is_blocked": False, "is_empty": False, "items": []}

    async def close(self) -> None:
        self.closed = True


class FakePlaywrightBrowser:
    """Test fake for Playwright Browser/BrowserContext object supporting new_page()."""

    def __init__(self, fake_page: FakePage) -> None:
        self.fake_page = fake_page

    async def new_page(self) -> FakePage:
        return self.fake_page


class FakeBrowserSession:
    """Test fake implementing the project's BrowserSession protocol."""

    def __init__(
        self,
        run_id: str = "discovery_run",
        script_results: Optional[List[Dict[str, Any]]] = None,
        fail_navigation_on_page: Optional[int] = None,
    ) -> None:
        self._run_id = run_id
        self.script_results = script_results or []
        self.fail_navigation_on_page = fail_navigation_on_page
        self.navigated_urls: List[str] = []
        self.call_count = 0
        self.closed = False

    @property
    def run_id(self) -> str:
        return self._run_id

    @property
    def state(self) -> Any:
        return "READY"

    async def start(self) -> None:
        pass

    async def close(self) -> None:
        self.closed = True

    async def navigate(self, url: str) -> None:
        current_page_idx = len(self.navigated_urls) + 1
        if self.fail_navigation_on_page is not None and current_page_idx == self.fail_navigation_on_page:
            raise RuntimeError(f"Network error on page {current_page_idx}")
        self.navigated_urls.append(url)

    async def evaluate(self, script: str) -> Any:
        if "scrollBy" in script:
            return None
        idx = min(self.call_count, len(self.script_results) - 1) if self.script_results else -1
        self.call_count += 1
        if idx >= 0:
            return self.script_results[idx]
        return {"is_blocked": False, "is_empty": False, "items": []}

    async def inspect(self) -> Dict[str, Any]:
        return {"url": self.navigated_urls[-1] if self.navigated_urls else "", "title": "Test", "elements": []}

    async def click(self, element_id: Optional[str] = None, locator: Optional[Any] = None) -> None:
        pass

    async def type_text(self, text: str, element_id: Optional[str] = None, locator: Optional[Any] = None) -> None:
        pass

    async def press(self, key: str) -> None:
        pass

    async def screenshot(self) -> bytes:
        return b""


class FakeBrowserManager:
    """Test fake implementing the project's BrowserManager protocol."""

    def __init__(self, session: FakeBrowserSession) -> None:
        self.session = session
        self.requested_run_ids: List[str] = []

    async def get_or_create_session(self, run_id: str, config: Optional[Any] = None) -> FakeBrowserSession:
        self.requested_run_ids.append(run_id)
        return self.session

    async def close_session(self, run_id: str) -> None:
        await self.session.close()

    async def close_all(self) -> None:
        await self.session.close()


@pytest.mark.asyncio
async def test_shopee_discovery_successful_extraction_and_mapping() -> None:
    obs_time = datetime(2026, 8, 16, 12, 0, 0, tzinfo=timezone.utc)
    card_data = [
        {
            "title": "Tai nghe Bluetooth Không Dây Pin Trâu",
            "href": "/Tai-nghe-Bluetooth-i.111.222",
            "price_text": "₫150.000",
            "orig_price_text": "₫200.000",
            "discount_text": "-25%",
            "sold_text": "Đã bán 1,5k",
            "rating_text": "4.85",
            "review_text": None,
            "shop_name": "Official Store Audio",
            "item_id": "222",
            "shop_id": "111",
        },
        {
            "title": "Bàn Phím Cơ Gaming RGB",
            "href": "/product/333/444",
            "price_text": "₫450.000",
            "orig_price_text": None,
            "discount_text": None,
            "sold_text": "Đã bán 850",
            "rating_text": "4.9",
            "review_text": "(350)",
            "shop_name": "GearVN Store",
            "item_id": "444",
            "shop_id": "333",
        },
    ]

    fake_page = FakePage(script_results=[{"is_blocked": False, "is_empty": False, "items": card_data}])
    adapter = ShopeeDiscoveryAdapter(browser=fake_page)

    req = DiscoveryRequest(query="tai nghe bluetooth", max_candidates=10, max_pages=1)
    batch = await adapter.discover(req, observed_at=obs_time)

    assert isinstance(batch, DiscoveryBatch)
    assert batch.platform == "shopee"
    assert batch.query == "tai nghe bluetooth"
    assert batch.observed_at == obs_time
    assert len(batch.candidates) == 2
    assert batch.pages_examined == 1
    assert batch.raw_items_seen == 2
    assert "DISCOVERY_SUCCESS" in batch.diagnostic_codes

    c1 = batch.candidates[0]
    assert c1.candidate_id == "shopee_222"
    assert c1.platform == "shopee"
    assert c1.url == "https://shopee.vn/Tai-nghe-Bluetooth-i.111.222"
    assert c1.title == "Tai nghe Bluetooth Không Dây Pin Trâu"
    assert c1.price == 150000.0
    assert c1.original_price == 200000.0
    assert c1.discount_percent == 25.0
    assert c1.sold_count == 1500
    assert c1.rating == 4.85
    assert c1.review_count is None  # Should not be fabricated from rating_text
    assert c1.shop_name == "Official Store Audio"

    c2 = batch.candidates[1]
    assert c2.rating == 4.9
    assert c2.review_count == 350  # Should be extracted from dedicated review_text

    # Verify unobserved fields remain strictly None (no fabricated momentum or commission)
    assert c1.affiliate_commission_rate is None
    assert c1.estimated_commission_value is None
    assert c1.creator_count is None
    assert c1.video_count is None
    assert c1.sales_velocity is None
    assert c1.review_velocity is None
    assert c1.creator_velocity is None


@pytest.mark.asyncio
async def test_shopee_discovery_deduplication_and_max_candidates_limit() -> None:
    obs_time = datetime(2026, 8, 16, 12, 0, 0, tzinfo=timezone.utc)
    # 4 items with duplicate item_id "222"
    card_data = [
        {"title": "Product A", "href": "/p-i.1.222", "item_id": "222", "price_text": "100k"},
        {"title": "Product A Duplicate Card", "href": "/p-i.1.222", "item_id": "222", "price_text": "100k"},
        {"title": "Product B", "href": "/p-i.1.333", "item_id": "333", "price_text": "200k"},
        {"title": "Product C", "href": "/p-i.1.444", "item_id": "444", "price_text": "300k"},
    ]

    fake_page = FakePage(script_results=[{"is_blocked": False, "is_empty": False, "items": card_data}])
    adapter = ShopeeDiscoveryAdapter(browser=fake_page)

    # Limit to max 2 candidates
    req = DiscoveryRequest(query="gear", max_candidates=2, max_pages=1)
    batch = await adapter.discover(req, observed_at=obs_time)

    # 4 raw items seen, duplicate 222 collapsed, capped at 2
    assert batch.raw_items_seen == 4
    assert len(batch.candidates) == 2
    assert batch.candidates[0].candidate_id == "shopee_222"
    assert batch.candidates[0].title == "Product A"  # First-seen title preserved
    assert batch.candidates[1].candidate_id == "shopee_333"


@pytest.mark.asyncio
async def test_shopee_discovery_pagination_and_max_pages_enforcement() -> None:
    obs_time = datetime(2026, 8, 16, 12, 0, 0, tzinfo=timezone.utc)
    page1_items = [{"title": "Item 1", "href": "/item-i.1.1", "item_id": "1"}]
    page2_items = [{"title": "Item 2", "href": "/item-i.1.2", "item_id": "2"}]
    page3_items = [{"title": "Item 3", "href": "/item-i.1.3", "item_id": "3"}]

    fake_page = FakePage(script_results=[
        {"is_blocked": False, "is_empty": False, "items": page1_items},
        {"is_blocked": False, "is_empty": False, "items": page2_items},
        {"is_blocked": False, "is_empty": False, "items": page3_items},
    ])
    adapter = ShopeeDiscoveryAdapter(browser=fake_page)

    req = DiscoveryRequest(query="gadgets", max_candidates=50, max_pages=2)
    batch = await adapter.discover(req, observed_at=obs_time)

    assert batch.pages_examined == 2
    assert len(batch.candidates) == 2
    assert len(fake_page.navigated_urls) == 2
    assert "page=1" in fake_page.navigated_urls[1]


@pytest.mark.asyncio
async def test_shopee_discovery_malformed_cards_skipped_without_batch_failure() -> None:
    obs_time = datetime(2026, 8, 16, 12, 0, 0, tzinfo=timezone.utc)
    card_data = [
        {"title": "", "href": ""},  # Malformed empty card
        {"title": "Valid Item", "href": "/valid-i.1.555", "item_id": "555", "price_text": "150k"},
        {"title": "Invalid Price Card", "href": "/bad-price-i.1.666", "item_id": "666", "price_text": "Unparseable Price"},
    ]

    fake_page = FakePage(script_results=[{"is_blocked": False, "is_empty": False, "items": card_data}])
    adapter = ShopeeDiscoveryAdapter(browser=fake_page)

    req = DiscoveryRequest(query="camera", max_candidates=10)
    batch = await adapter.discover(req, observed_at=obs_time)

    assert len(batch.candidates) == 2
    assert batch.candidates[0].candidate_id == "shopee_555"
    assert batch.candidates[0].price == 150000.0
    assert batch.candidates[1].candidate_id == "shopee_666"
    assert batch.candidates[1].price is None  # Unparseable price gracefully set to None


@pytest.mark.asyncio
async def test_shopee_discovery_explicit_none_optional_shop_fields_remain_none() -> None:
    obs_time = datetime(2026, 8, 16, 12, 0, 0, tzinfo=timezone.utc)
    card_data = [
        {
            "title": "Valid Item With Explicit Null Shop",
            "href": "/item-i.1.777",
            "price_text": "120.000₫",
            "orig_price_text": None,
            "discount_text": None,
            "sold_text": "Đã bán 50",
            "rating_text": "4.7",
            "review_text": None,
            "shop_name": None,  # Explicit None
            "shop_id": None,    # Explicit None
            "item_id": None,    # Explicit None (falls back to URL parsing)
        },
        {
            "title": "Valid Item With Whitespace Shop",
            "href": "/product/222/888",
            "price_text": "220.000₫",
            "orig_price_text": None,
            "discount_text": None,
            "sold_text": None,
            "rating_text": None,
            "review_text": None,
            "shop_name": "   ",  # Whitespace-only string
            "shop_id": "   ",    # Whitespace-only string
            "item_id": "888",
        },
    ]

    fake_page = FakePage(script_results=[{"is_blocked": False, "is_empty": False, "items": card_data}])
    adapter = ShopeeDiscoveryAdapter(browser=fake_page)

    req = DiscoveryRequest(query="null shop test", max_candidates=10)
    batch = await adapter.discover(req, observed_at=obs_time)

    assert len(batch.candidates) == 2
    assert "DISCOVERY_SUCCESS" in batch.diagnostic_codes

    c1 = batch.candidates[0]
    assert c1.candidate_id == "shopee_777"
    assert c1.title == "Valid Item With Explicit Null Shop"
    assert c1.shop_name is None
    assert c1.shop_id is None
    assert c1.price == 120000.0

    c2 = batch.candidates[1]
    assert c2.candidate_id == "shopee_888"
    assert c2.title == "Valid Item With Whitespace Shop"
    assert c2.shop_name is None
    assert c2.shop_id is None
    assert c2.price == 220000.0


@pytest.mark.asyncio
async def test_shopee_discovery_explicit_none_required_fields_skipped_without_attribute_error() -> None:
    obs_time = datetime(2026, 8, 16, 12, 0, 0, tzinfo=timezone.utc)
    card_data = [
        # Explicit None title with valid href
        {"title": None, "href": "/product-i.1.101", "item_id": "101"},
        # Explicit None href with valid title
        {"title": "Valid Title Missing Href", "href": None, "item_id": "102"},
        # Both explicit None
        {"title": None, "href": None, "item_id": "103"},
        # Whitespace-only title
        {"title": "   ", "href": "/product-i.1.104", "item_id": "104"},
        # Whitespace-only href
        {"title": "Valid Title Whitespace Href", "href": "   ", "item_id": "105"},
        # Sibling valid card must be extracted normally
        {
            "title": "Completely Valid Sibling Product",
            "href": "/sibling-i.1.999",
            "item_id": "999",
            "price_text": "99.000₫",
            "shop_name": "Sibling Store",
            "shop_id": "1",
        },
    ]

    fake_page = FakePage(script_results=[{"is_blocked": False, "is_empty": False, "items": card_data}])
    adapter = ShopeeDiscoveryAdapter(browser=fake_page)

    req = DiscoveryRequest(query="null required fields test", max_candidates=10)
    # Must execute cleanly without raising AttributeError: 'NoneType' object has no attribute 'strip'
    batch = await adapter.discover(req, observed_at=obs_time)

    # Exactly the one valid sibling card should be in the batch
    assert len(batch.candidates) == 1
    assert batch.raw_items_seen == 6
    assert batch.candidates[0].candidate_id == "shopee_999"
    assert batch.candidates[0].title == "Completely Valid Sibling Product"
    assert batch.candidates[0].url == "https://shopee.vn/sibling-i.1.999"
    assert batch.candidates[0].shop_name == "Sibling Store"
    assert batch.candidates[0].shop_id == "1"
    assert "DISCOVERY_SUCCESS" in batch.diagnostic_codes


def test_shopee_map_card_to_snapshot_null_safety_matrix() -> None:
    obs_time = datetime(2026, 8, 16, 12, 0, 0, tzinfo=timezone.utc)
    adapter = ShopeeDiscoveryAdapter()

    # Required field None / empty / whitespace checks -> return None
    assert adapter._map_card_to_snapshot({"title": None, "href": "/p"}, obs_time) is None
    assert adapter._map_card_to_snapshot({"title": "T", "href": None}, obs_time) is None
    assert adapter._map_card_to_snapshot({"title": None, "href": None}, obs_time) is None
    assert adapter._map_card_to_snapshot({"title": "", "href": "/p"}, obs_time) is None
    assert adapter._map_card_to_snapshot({"title": "T", "href": ""}, obs_time) is None
    assert adapter._map_card_to_snapshot({"title": "   ", "href": "/p"}, obs_time) is None
    assert adapter._map_card_to_snapshot({"title": "T", "href": "   "}, obs_time) is None
    assert adapter._map_card_to_snapshot({}, obs_time) is None

    # Optional field None / empty / whitespace checks -> remain None on snapshot
    s1 = adapter._map_card_to_snapshot({
        "title": "Title",
        "href": "/item-i.1.123",
        "shop_name": None,
        "shop_id": None,
    }, obs_time)
    assert s1 is not None
    assert s1.title == "Title"
    assert s1.url == "https://shopee.vn/item-i.1.123"
    assert s1.shop_name is None
    assert s1.shop_id is None
    assert s1.source_product_id == "123"
    assert s1.candidate_id == "shopee_123"

    s2 = adapter._map_card_to_snapshot({
        "title": "Title 2",
        "href": "/item-i.1.456",
        "shop_name": "   ",
        "shop_id": "   ",
    }, obs_time)
    assert s2 is not None
    assert s2.shop_name is None
    assert s2.shop_id is None

    # Trimming check for string values
    s3 = adapter._map_card_to_snapshot({
        "title": "  Trimmed Title  ",
        "href": "  /item-i.1.789  ",
        "shop_name": "  Trimmed Shop  ",
        "shop_id": "  77  ",
    }, obs_time)
    assert s3 is not None
    assert s3.title == "Trimmed Title"
    assert s3.url == "https://shopee.vn/item-i.1.789"
    assert s3.shop_name == "Trimmed Shop"
    assert s3.shop_id == "77"


@pytest.mark.asyncio
async def test_shopee_discovery_true_empty_search_returns_empty_batch() -> None:
    obs_time = datetime(2026, 8, 16, 12, 0, 0, tzinfo=timezone.utc)
    fake_page = FakePage(script_results=[{"is_blocked": False, "is_empty": True, "items": []}])
    adapter = ShopeeDiscoveryAdapter(browser=fake_page)

    req = DiscoveryRequest(query="xyznonexistentkeyword123")
    batch = await adapter.discover(req, observed_at=obs_time)

    assert len(batch.candidates) == 0
    assert "TRUE_EMPTY_SEARCH" in batch.diagnostic_codes


@pytest.mark.asyncio
async def test_shopee_discovery_empty_items_without_empty_marker_raises_error() -> None:
    # A successful JS evaluation that returns zero items but NO explicit empty marker
    # Should not be silently treated as TRUE_EMPTY_SEARCH
    fake_page = FakePage(script_results=[{"is_blocked": False, "is_empty": False, "items": []}])
    adapter = ShopeeDiscoveryAdapter(browser=fake_page)

    req = DiscoveryRequest(query="xyz")
    with pytest.raises(DiscoveryNavigationError, match="No cards extracted"):
        await adapter.discover(req)


@pytest.mark.asyncio
async def test_shopee_discovery_blocked_or_captcha_raises_error() -> None:
    fake_page = FakePage(script_results=[{"is_blocked": True, "is_empty": False, "items": []}])
    adapter = ShopeeDiscoveryAdapter(browser=fake_page)

    req = DiscoveryRequest(query="shoes")
    with pytest.raises(DiscoveryBlockedError, match="challenge or captcha"):
        await adapter.discover(req)


@pytest.mark.asyncio
async def test_shopee_discovery_first_page_navigation_failure_raises() -> None:
    fake_page = FakePage(fail_navigation_on_page=1)
    adapter = ShopeeDiscoveryAdapter(browser=fake_page)

    req = DiscoveryRequest(query="watch")
    with pytest.raises(DiscoveryNavigationError, match="Failed to navigate"):
        await adapter.discover(req)


@pytest.mark.asyncio
async def test_shopee_discovery_later_page_failure_returns_partial_batch() -> None:
    obs_time = datetime(2026, 8, 16, 12, 0, 0, tzinfo=timezone.utc)
    page1_items = [{"title": "Item 1", "href": "/item-i.1.1", "item_id": "1"}]

    fake_page = FakePage(
        script_results=[{"is_blocked": False, "is_empty": False, "items": page1_items}],
        fail_navigation_on_page=2,
    )
    adapter = ShopeeDiscoveryAdapter(browser=fake_page)

    req = DiscoveryRequest(query="speaker", max_pages=3)
    batch = await adapter.discover(req, observed_at=obs_time)

    assert len(batch.candidates) == 1
    assert batch.pages_examined == 1
    assert "PARTIAL_EXTRACTION_PAGE_FAILED" in batch.diagnostic_codes


@pytest.mark.asyncio
async def test_shopee_discovery_missing_browser_dependency_fails() -> None:
    adapter = ShopeeDiscoveryAdapter(browser=None)
    req = DiscoveryRequest(query="lamp")
    with pytest.raises(DiscoveryError, match="Browser dependency is required"):
        await adapter.discover(req)


@pytest.mark.asyncio
async def test_shopee_discovery_with_browser_manager_dependency() -> None:
    obs_time = datetime(2026, 8, 16, 12, 0, 0, tzinfo=timezone.utc)
    card_data = [
        {"title": "USB Cable Fast Charge", "href": "/usb-i.1.99", "item_id": "99", "price_text": "50.000₫"},
        {"title": "USB Cable Fast Charge Dup", "href": "/usb-i.1.99", "item_id": "99", "price_text": "50.000₫"},
        {"title": "USB-C Adapter", "href": "/adapter-i.1.100", "item_id": "100", "price_text": "80.000₫"},
    ]
    session = FakeBrowserSession(
        run_id="discovery_run",
        script_results=[{"is_blocked": False, "is_empty": False, "items": card_data}],
    )
    manager = FakeBrowserManager(session=session)
    adapter = ShopeeDiscoveryAdapter(browser=manager)

    req = DiscoveryRequest(query="usb cable", max_candidates=2, max_pages=1)
    batch = await adapter.discover(req, observed_at=obs_time)

    # Verify BrowserManager.get_or_create_session was called
    assert "discovery_run" in manager.requested_run_ids
    # Verify session navigation and evaluation occurred
    assert len(session.navigated_urls) == 1
    assert "keyword=usb+cable" in session.navigated_urls[0]
    # Verify candidates extracted, deduplicated, and bounded
    assert len(batch.candidates) == 2
    assert batch.candidates[0].candidate_id == "shopee_99"
    assert batch.candidates[0].price == 50000.0
    assert batch.candidates[1].candidate_id == "shopee_100"
    assert batch.candidates[1].price == 80000.0


@pytest.mark.asyncio
async def test_shopee_discovery_with_playwright_browser_context() -> None:
    obs_time = datetime(2026, 8, 16, 12, 0, 0, tzinfo=timezone.utc)
    page = FakePage(script_results=[{
        "is_blocked": False,
        "is_empty": False,
        "items": [{"title": "USB Cable", "href": "/usb-i.1.99", "item_id": "99"}],
    }])
    browser = FakePlaywrightBrowser(fake_page=page)
    adapter = ShopeeDiscoveryAdapter(browser=browser)

    req = DiscoveryRequest(query="usb cable")
    batch = await adapter.discover(req, observed_at=obs_time)

    assert len(batch.candidates) == 1
    assert batch.candidates[0].candidate_id == "shopee_99"
    assert page.closed is True  # Verify cleanup called on page created via new_page()


@pytest.mark.asyncio
async def test_shopee_discovery_delayed_hydration_success(monkeypatch: pytest.MonkeyPatch) -> None:
    obs_time = datetime(2026, 8, 16, 12, 0, 0, tzinfo=timezone.utc)
    sleep_calls: List[float] = []

    async def _record_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr("src.product_intelligence.adapters.shopee._readiness_sleep", _record_sleep)

    card_data = [{
        "title": "Hydrated Keyboard",
        "href": "/hydrated-i.1.888",
        "price_text": "250k",
        "item_id": "888",
    }]
    # First 2 attempts return empty items (hydrating), 3rd returns items
    fake_page = FakePage(script_results=[
        {"is_blocked": False, "is_empty": False, "items": []},
        {"is_blocked": False, "is_empty": False, "items": []},
        {"is_blocked": False, "is_empty": False, "items": card_data},
    ])
    adapter = ShopeeDiscoveryAdapter(browser=fake_page)

    req = DiscoveryRequest(query="keyboard", max_candidates=5)
    batch = await adapter.discover(req, observed_at=obs_time)

    assert len(batch.candidates) == 1
    assert batch.candidates[0].candidate_id == "shopee_888"
    assert batch.candidates[0].title == "Hydrated Keyboard"
    assert fake_page.call_count == 3
    assert len(sleep_calls) == 2
    assert sleep_calls == [0.5, 0.5]
    assert len(fake_page.navigated_urls) == 1  # Exactly one navigation


@pytest.mark.asyncio
async def test_shopee_discovery_readiness_stops_immediately_on_first_item_state(monkeypatch: pytest.MonkeyPatch) -> None:
    obs_time = datetime(2026, 8, 16, 12, 0, 0, tzinfo=timezone.utc)
    sleep_calls: List[float] = []

    async def _record_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr("src.product_intelligence.adapters.shopee._readiness_sleep", _record_sleep)

    card_data = [{"title": "Instant Item", "href": "/instant-i.1.10", "item_id": "10"}]
    # Multiple script results supplied, but only 1 should be evaluated
    fake_page = FakePage(script_results=[
        {"is_blocked": False, "is_empty": False, "items": card_data},
        {"is_blocked": False, "is_empty": False, "items": []},
    ])
    adapter = ShopeeDiscoveryAdapter(browser=fake_page)

    req = DiscoveryRequest(query="instant")
    batch = await adapter.discover(req, observed_at=obs_time)

    assert len(batch.candidates) == 1
    assert fake_page.call_count == 1
    assert len(sleep_calls) == 0  # Zero delays needed


@pytest.mark.asyncio
async def test_shopee_discovery_delayed_blocked_state_raises_error(monkeypatch: pytest.MonkeyPatch) -> None:
    sleep_calls: List[float] = []

    async def _record_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr("src.product_intelligence.adapters.shopee._readiness_sleep", _record_sleep)

    fake_page = FakePage(script_results=[
        {"is_blocked": False, "is_empty": False, "items": []},
        {"is_blocked": True, "is_empty": False, "items": []},
    ])
    adapter = ShopeeDiscoveryAdapter(browser=fake_page)

    req = DiscoveryRequest(query="shoes")
    with pytest.raises(DiscoveryBlockedError, match="challenge or captcha"):
        await adapter.discover(req)

    assert fake_page.call_count == 2
    assert len(sleep_calls) == 1
    assert len(fake_page.navigated_urls) == 1


@pytest.mark.asyncio
async def test_shopee_discovery_delayed_true_empty_state_returns_empty_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    obs_time = datetime(2026, 8, 16, 12, 0, 0, tzinfo=timezone.utc)
    sleep_calls: List[float] = []

    async def _record_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr("src.product_intelligence.adapters.shopee._readiness_sleep", _record_sleep)

    fake_page = FakePage(script_results=[
        {"is_blocked": False, "is_empty": False, "items": []},
        {"is_blocked": False, "is_empty": True, "items": []},
    ])
    adapter = ShopeeDiscoveryAdapter(browser=fake_page)

    req = DiscoveryRequest(query="nonexistent")
    batch = await adapter.discover(req, observed_at=obs_time)

    assert len(batch.candidates) == 0
    assert "TRUE_EMPTY_SEARCH" in batch.diagnostic_codes
    assert fake_page.call_count == 2
    assert len(sleep_calls) == 1
    assert len(fake_page.navigated_urls) == 1


@pytest.mark.asyncio
async def test_shopee_discovery_bounded_exhaustion_raises_navigation_error(monkeypatch: pytest.MonkeyPatch) -> None:
    sleep_calls: List[float] = []

    async def _record_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr("src.product_intelligence.adapters.shopee._readiness_sleep", _record_sleep)

    fake_page = FakePage(script_results=[
        {"is_blocked": False, "is_empty": False, "items": []}
    ])
    adapter = ShopeeDiscoveryAdapter(browser=fake_page)

    req = DiscoveryRequest(query="exhaustion_test")
    with pytest.raises(DiscoveryNavigationError, match="No cards extracted on page 1 and no empty-result marker found"):
        await adapter.discover(req)

    # Evaluates up to _READINESS_MAX_ATTEMPTS (10) and sleeps 9 times
    assert fake_page.call_count == 10
    assert len(sleep_calls) == 9
    assert len(fake_page.navigated_urls) == 1  # Exactly one navigation despite 10 samples


@pytest.mark.asyncio
async def test_shopee_discovery_exact_one_navigation_and_acquisition_despite_multiple_samples() -> None:
    obs_time = datetime(2026, 8, 16, 12, 0, 0, tzinfo=timezone.utc)
    card_data = [{"title": "Widget", "href": "/widget-i.1.999", "item_id": "999"}]
    session = FakeBrowserSession(
        run_id="discovery_run",
        script_results=[
            {"is_blocked": False, "is_empty": False, "items": []},
            {"is_blocked": False, "is_empty": False, "items": []},
            {"is_blocked": False, "is_empty": False, "items": card_data},
        ],
    )
    manager = FakeBrowserManager(session=session)
    adapter = ShopeeDiscoveryAdapter(browser=manager)

    req = DiscoveryRequest(query="widget", max_pages=1)
    batch = await adapter.discover(req, observed_at=obs_time)

    # Exactly one session acquisition
    assert manager.requested_run_ids == ["discovery_run"]
    # Exactly one navigation
    assert len(session.navigated_urls) == 1
    # 3 evaluate calls on that same page
    assert session.call_count == 3
    assert len(batch.candidates) == 1
    assert batch.candidates[0].candidate_id == "shopee_999"


def test_shopee_card_extraction_script_has_product_anchor_fallback() -> None:
    from src.product_intelligence.adapters.shopee import SHOPEE_CARD_EXTRACTION_SCRIPT

    # Script must support canonical product URL forms as fallback discovery roots
    assert 'a[href*="-i."]' in SHOPEE_CARD_EXTRACTION_SCRIPT
    assert 'a[href*="/product/"]' in SHOPEE_CARD_EXTRACTION_SCRIPT
    assert "seenHrefs" in SHOPEE_CARD_EXTRACTION_SCRIPT
    # Script must check bounded title sources
    assert "aria-label" in SHOPEE_CARD_EXTRACTION_SCRIPT
    assert "img[alt]" in SHOPEE_CARD_EXTRACTION_SCRIPT
    # Script must retain primary container selectors
    assert ".shopee-search-item-result__item" in SHOPEE_CARD_EXTRACTION_SCRIPT
    assert "candidateAnchors" in SHOPEE_CARD_EXTRACTION_SCRIPT


@pytest.mark.asyncio
async def test_shopee_card_extraction_script_fallback_dom_execution() -> None:
    from playwright.async_api import async_playwright
    from src.product_intelligence.adapters.shopee import SHOPEE_CARD_EXTRACTION_SCRIPT

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page()

            # HTML without legacy presentation card classes; products are modern anchors
            html_content = """
            <!DOCTYPE html>
            <html><body>
            <div class="main-content">
                <div class="grid-item">
                    <a href="/ao-thun-nam-cotton-i.12345.67890" aria-label="Ao Thun Nam Cotton">
                        <img alt="Ao Thun Nam Cotton" src="thumb.jpg" />
                        <span class="vioxXd">150.000</span>
                        <span class="truncate">Da ban 1,2k</span>
                        <span class="rating-stars">4.8</span>
                    </a>
                </div>
                <!-- Duplicate anchor with same product URL (e.g. image link + text link) -->
                <div class="grid-item">
                    <a href="/ao-thun-nam-cotton-i.12345.67890">Ao Thun Nam Cotton Dup</a>
                </div>
                <div class="grid-item">
                    <a href="/product/55555/99999" title="Quan Jean Slimfit">
                        <span class="vioxXd">350.000</span>
                    </a>
                </div>
                <!-- Non-product anchor should be ignored -->
                <div class="footer">
                    <a href="/help-center">Help Center</a>
                </div>
            </div>
            </body></html>
            """
            await page.set_content(html_content)
            result = await page.evaluate(SHOPEE_CARD_EXTRACTION_SCRIPT)

            assert result["is_blocked"] is False
            assert result["is_empty"] is False
            items = result["items"]
            assert len(items) == 2  # Duplicate ao-thun collapsed, help-center ignored
            assert items[0]["title"] == "Ao Thun Nam Cotton"
            assert items[0]["href"] == "/ao-thun-nam-cotton-i.12345.67890"
            assert items[0]["price_text"] == "150.000"
            assert items[0]["sold_text"] == "Da ban 1,2k"
            assert items[0]["rating_text"] == "4.8"
            assert items[0]["review_text"] is None

            assert items[1]["title"] == "Quan Jean Slimfit"
            assert items[1]["href"] == "/product/55555/99999"
            assert items[1]["price_text"] == "350.000"
            assert items[1]["sold_text"] is None
        finally:
            await browser.close()
