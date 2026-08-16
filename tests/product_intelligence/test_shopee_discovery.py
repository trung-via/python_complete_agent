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
