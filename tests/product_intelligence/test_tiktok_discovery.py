from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import pytest

from src.product_intelligence.adapters.tiktok import TikTokDiscoveryAdapter
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
async def test_tiktok_discovery_successful_extraction_and_mapping() -> None:
    obs_time = datetime(2026, 8, 29, 10, 0, 0, tzinfo=timezone.utc)
    card_data = [
        {
            "title": "Tai nghe không dây chống ồn TWS Pro",
            "href": "/product/1729482910481234567",
            "price_text": "₫199.000",
            "orig_price_text": "₫350.000",
            "discount_text": "-43%",
            "sold_text": "Đã bán 3,2k",
            "rating_text": "4.8",
            "review_text": "(1.2k)",
            "shop_name": "Official Audio VN",
            "item_id": "1729482910481234567",
            "shop_id": "888999",
        },
        {
            "title": "Bình giữ nhiệt inox 304 800ml",
            "href": "https://www.tiktok.com/item/1729482910487654321",
            "price_text": "120k",
            "orig_price_text": None,
            "discount_text": None,
            "sold_text": "Đã bán 500",
            "rating_text": "4.95",
            "review_text": "250 đánh giá",
            "shop_name": "Gia Dung Thong Minh",
            "item_id": "1729482910487654321",
            "shop_id": "777666",
        },
    ]

    fake_page = FakePage(script_results=[{"is_blocked": False, "is_empty": False, "items": card_data}])
    adapter = TikTokDiscoveryAdapter(browser=fake_page)

    req = DiscoveryRequest(query="tai nghe", max_candidates=10, max_pages=1)
    batch = await adapter.discover(req, observed_at=obs_time)

    assert isinstance(batch, DiscoveryBatch)
    assert batch.platform == "tiktok"
    assert batch.query == "tai nghe"
    assert batch.observed_at == obs_time
    assert len(batch.candidates) == 2
    assert batch.pages_examined == 1
    assert batch.raw_items_seen == 2
    assert "DISCOVERY_SUCCESS" in batch.diagnostic_codes

    c1 = batch.candidates[0]
    assert c1.candidate_id == "tiktok_1729482910481234567"
    assert c1.platform == "tiktok"
    assert c1.url == "https://www.tiktok.com/product/1729482910481234567"
    assert c1.title == "Tai nghe không dây chống ồn TWS Pro"
    assert c1.price == 199000.0
    assert c1.original_price == 350000.0
    assert c1.discount_percent == 43.0
    assert c1.sold_count == 3200
    assert c1.rating == 4.8
    assert c1.review_count == 1200
    assert c1.shop_name == "Official Audio VN"
    assert c1.shop_id == "888999"

    c2 = batch.candidates[1]
    assert c2.candidate_id == "tiktok_1729482910487654321"
    assert c2.rating == 4.95
    assert c2.review_count == 250

    # Verify unobserved fields remain strictly None (no fabricated momentum or commission)
    assert c1.affiliate_commission_rate is None
    assert c1.estimated_commission_value is None
    assert c1.creator_count is None
    assert c1.video_count is None
    assert c1.sales_velocity is None
    assert c1.review_velocity is None
    assert c1.creator_velocity is None


@pytest.mark.asyncio
async def test_tiktok_discovery_explicit_none_shop_attributes() -> None:
    obs_time = datetime(2026, 8, 29, 10, 0, 0, tzinfo=timezone.utc)
    card_data = [
        {
            "title": "Sạc dự phòng 20000mAh",
            "href": "/product/111222333444",
            "price_text": "250.000₫",
            "shop_name": None,
            "shop_id": None,
            "item_id": "111222333444",
        },
        {
            "title": "Cáp sạc type-C",
            "href": "/product/555666777888",
            "price_text": "30.000₫",
            "shop_name": "   ",
            "shop_id": "",
            "item_id": "555666777888",
        },
    ]

    fake_page = FakePage(script_results=[{"is_blocked": False, "is_empty": False, "items": card_data}])
    adapter = TikTokDiscoveryAdapter(browser=fake_page)

    req = DiscoveryRequest(query="sac du phong")
    batch = await adapter.discover(req, observed_at=obs_time)

    assert len(batch.candidates) == 2
    assert batch.candidates[0].shop_name is None
    assert batch.candidates[0].shop_id is None
    assert batch.candidates[1].shop_name is None
    assert batch.candidates[1].shop_id is None


@pytest.mark.asyncio
async def test_tiktok_discovery_deduplication_and_max_candidates_limit() -> None:
    obs_time = datetime(2026, 8, 29, 10, 0, 0, tzinfo=timezone.utc)
    card_data = [
        {"title": "Product A", "href": "/product/101", "item_id": "101", "price_text": "100k"},
        {"title": "Product A Duplicate Card", "href": "/product/101", "item_id": "101", "price_text": "100k"},
        {"title": "Product B", "href": "/product/102", "item_id": "102", "price_text": "200k"},
        {"title": "Product C", "href": "/product/103", "item_id": "103", "price_text": "300k"},
    ]

    fake_page = FakePage(script_results=[{"is_blocked": False, "is_empty": False, "items": card_data}])
    adapter = TikTokDiscoveryAdapter(browser=fake_page)

    req = DiscoveryRequest(query="gear", max_candidates=2, max_pages=1)
    batch = await adapter.discover(req, observed_at=obs_time)

    assert batch.raw_items_seen == 4
    assert len(batch.candidates) == 2
    assert batch.candidates[0].candidate_id == "tiktok_101"
    assert batch.candidates[0].title == "Product A"  # First-seen title preserved
    assert batch.candidates[1].candidate_id == "tiktok_102"


@pytest.mark.asyncio
async def test_tiktok_discovery_pagination_and_max_pages_enforcement() -> None:
    obs_time = datetime(2026, 8, 29, 10, 0, 0, tzinfo=timezone.utc)
    page1_items = [{"title": "Item 1", "href": "/product/1", "item_id": "1"}]
    page2_items = [{"title": "Item 2", "href": "/product/2", "item_id": "2"}]
    page3_items = [{"title": "Item 3", "href": "/product/3", "item_id": "3"}]

    fake_page = FakePage(script_results=[
        {"is_blocked": False, "is_empty": False, "items": page1_items},
        {"is_blocked": False, "is_empty": False, "items": page2_items},
        {"is_blocked": False, "is_empty": False, "items": page3_items},
    ])
    adapter = TikTokDiscoveryAdapter(browser=fake_page)

    req = DiscoveryRequest(query="gadgets", max_candidates=50, max_pages=2)
    batch = await adapter.discover(req, observed_at=obs_time)

    assert batch.pages_examined == 2
    assert len(batch.candidates) == 2
    assert len(fake_page.navigated_urls) == 2
    assert "page=2" in fake_page.navigated_urls[1]


@pytest.mark.asyncio
async def test_tiktok_discovery_malformed_cards_skipped_without_batch_failure() -> None:
    obs_time = datetime(2026, 8, 29, 10, 0, 0, tzinfo=timezone.utc)
    card_data = [
        {"title": "", "href": ""},  # Malformed empty card
        {"title": "Valid Item", "href": "/product/555", "item_id": "555", "price_text": "150k"},
        {"title": "Invalid Price Card", "href": "/product/666", "item_id": "666", "price_text": "Unparseable Price"},
    ]

    fake_page = FakePage(script_results=[{"is_blocked": False, "is_empty": False, "items": card_data}])
    adapter = TikTokDiscoveryAdapter(browser=fake_page)

    req = DiscoveryRequest(query="camera", max_candidates=10)
    batch = await adapter.discover(req, observed_at=obs_time)

    assert len(batch.candidates) == 2
    assert batch.candidates[0].candidate_id == "tiktok_555"
    assert batch.candidates[0].price == 150000.0
    assert batch.candidates[1].candidate_id == "tiktok_666"
    assert batch.candidates[1].price is None  # Unparseable price gracefully set to None


@pytest.mark.asyncio
async def test_tiktok_discovery_true_empty_search_returns_empty_batch() -> None:
    obs_time = datetime(2026, 8, 29, 10, 0, 0, tzinfo=timezone.utc)
    fake_page = FakePage(script_results=[{"is_blocked": False, "is_empty": True, "items": []}])
    adapter = TikTokDiscoveryAdapter(browser=fake_page)

    req = DiscoveryRequest(query="xyznonexistentkeyword123")
    batch = await adapter.discover(req, observed_at=obs_time)

    assert len(batch.candidates) == 0
    assert "TRUE_EMPTY_SEARCH" in batch.diagnostic_codes


@pytest.mark.asyncio
async def test_tiktok_discovery_empty_items_without_empty_marker_raises_error() -> None:
    fake_page = FakePage(script_results=[{"is_blocked": False, "is_empty": False, "items": []}])
    adapter = TikTokDiscoveryAdapter(browser=fake_page)

    req = DiscoveryRequest(query="xyz")
    with pytest.raises(DiscoveryNavigationError, match="No cards extracted"):
        await adapter.discover(req)


@pytest.mark.asyncio
async def test_tiktok_discovery_blocked_or_captcha_raises_error() -> None:
    fake_page = FakePage(script_results=[{"is_blocked": True, "is_empty": False, "items": []}])
    adapter = TikTokDiscoveryAdapter(browser=fake_page)

    req = DiscoveryRequest(query="shoes")
    with pytest.raises(DiscoveryBlockedError, match="challenge or captcha"):
        await adapter.discover(req)


@pytest.mark.asyncio
async def test_tiktok_discovery_first_page_navigation_failure_raises() -> None:
    fake_page = FakePage(fail_navigation_on_page=1)
    adapter = TikTokDiscoveryAdapter(browser=fake_page)

    req = DiscoveryRequest(query="watch")
    with pytest.raises(DiscoveryNavigationError, match="Failed to navigate"):
        await adapter.discover(req)


@pytest.mark.asyncio
async def test_tiktok_discovery_later_page_failure_returns_partial_batch() -> None:
    obs_time = datetime(2026, 8, 29, 10, 0, 0, tzinfo=timezone.utc)
    page1_items = [{"title": "Item 1", "href": "/product/1", "item_id": "1"}]

    fake_page = FakePage(
        script_results=[{"is_blocked": False, "is_empty": False, "items": page1_items}],
        fail_navigation_on_page=2,
    )
    adapter = TikTokDiscoveryAdapter(browser=fake_page)

    req = DiscoveryRequest(query="speaker", max_pages=3)
    batch = await adapter.discover(req, observed_at=obs_time)

    assert len(batch.candidates) == 1
    assert batch.pages_examined == 1
    assert "PARTIAL_EXTRACTION_PAGE_FAILED" in batch.diagnostic_codes


@pytest.mark.asyncio
async def test_tiktok_discovery_missing_browser_dependency_fails() -> None:
    adapter = TikTokDiscoveryAdapter(browser=None)
    req = DiscoveryRequest(query="lamp")
    with pytest.raises(DiscoveryError, match="Browser dependency is required"):
        await adapter.discover(req)


@pytest.mark.asyncio
async def test_tiktok_discovery_with_browser_manager_dependency() -> None:
    obs_time = datetime(2026, 8, 29, 10, 0, 0, tzinfo=timezone.utc)
    card_data = [
        {"title": "USB Cable Fast Charge", "href": "/product/99", "item_id": "99", "price_text": "50.000₫"},
        {"title": "USB Cable Fast Charge Dup", "href": "/product/99", "item_id": "99", "price_text": "50.000₫"},
        {"title": "USB-C Adapter", "href": "/product/100", "item_id": "100", "price_text": "80.000₫"},
    ]
    session = FakeBrowserSession(
        run_id="discovery_run",
        script_results=[{"is_blocked": False, "is_empty": False, "items": card_data}],
    )
    manager = FakeBrowserManager(session=session)
    adapter = TikTokDiscoveryAdapter(browser=manager)

    req = DiscoveryRequest(query="usb cable", max_candidates=2, max_pages=1)
    batch = await adapter.discover(req, observed_at=obs_time)

    assert "discovery_run" in manager.requested_run_ids
    assert len(session.navigated_urls) == 1
    assert "q=usb+cable" in session.navigated_urls[0]
    assert len(batch.candidates) == 2
    assert batch.candidates[0].candidate_id == "tiktok_99"
    assert batch.candidates[0].price == 50000.0
    assert batch.candidates[1].candidate_id == "tiktok_100"
    assert batch.candidates[1].price == 80000.0


@pytest.mark.asyncio
async def test_tiktok_discovery_with_playwright_browser_context() -> None:
    obs_time = datetime(2026, 8, 29, 10, 0, 0, tzinfo=timezone.utc)
    page = FakePage(script_results=[{
        "is_blocked": False,
        "is_empty": False,
        "items": [{"title": "USB Cable", "href": "/product/99", "item_id": "99"}],
    }])
    browser = FakePlaywrightBrowser(fake_page=page)
    adapter = TikTokDiscoveryAdapter(browser=browser)

    req = DiscoveryRequest(query="usb cable")
    batch = await adapter.discover(req, observed_at=obs_time)

    assert len(batch.candidates) == 1
    assert batch.candidates[0].candidate_id == "tiktok_99"
    assert page.closed is True  # Verify cleanup called on page created via new_page()
