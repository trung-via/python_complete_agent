from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from src.product_intelligence.adapters.tiktok_parsing import (
    build_tiktok_candidate_id,
    build_tiktok_search_url,
    extract_tiktok_product_id,
    parse_tiktok_discount_percent,
    parse_tiktok_price,
    parse_tiktok_rating,
    parse_tiktok_review_count,
    parse_tiktok_sold_count,
)
from src.product_intelligence.discovery import (
    DiscoveryBatch,
    DiscoveryBlockedError,
    DiscoveryError,
    DiscoveryInvalidRequestError,
    DiscoveryNavigationError,
    DiscoveryRequest,
    ProductDiscoveryAdapter,
)
from src.product_intelligence.models import ProductCandidateSnapshot

logger = logging.getLogger(__name__)


# Client-side extraction script for TikTok Shop search/listing pages
TIKTOK_CARD_EXTRACTION_SCRIPT = r"""() => {
    // 1. Check for Challenge / Captcha / Block Page Indicators
    const title = document.title ? document.title.toLowerCase() : '';
    const bodyText = document.body ? document.body.innerText.toLowerCase() : '';
    const isBlocked = (
        title.includes('robot') ||
        title.includes('captcha') ||
        title.includes('security verification') ||
        title.includes('verify you are human') ||
        document.querySelector('.tiktok-captcha, #challenge-running, .captcha_container, [data-testid="captcha"], .sec-captcha') !== null ||
        bodyText.includes('please verify you are human') ||
        bodyText.includes('xác minh bảo mật') ||
        bodyText.includes('verification challenge')
    );

    if (isBlocked) {
        return { is_blocked: true, is_empty: false, items: [] };
    }

    // 2. Check for True Empty Search Results
    const isEmpty = (
        document.querySelector('.tiktok-search-empty-result, .no-result, [data-testid="empty-result"], .search-empty') !== null ||
        bodyText.includes('không tìm thấy kết quả') ||
        bodyText.includes('no results found') ||
        bodyText.includes('no results matching')
    );

    // 3. Extract Listing Cards
    const cardElements = document.querySelectorAll(
        '[data-testid="product-card"], .product-card, .search-product-item, div[class*="ProductCard"], div[class*="product-item"], div[class*="SearchCard"]'
    );

    const items = [];
    cardElements.forEach(card => {
        // Link and Title
        const linkEl = card.querySelector('a[href*="/product/"], a[href*="/item/"], a[href*="itemId="], a[href*="shop"]');
        const href = linkEl ? linkEl.getAttribute('href') : (card.tagName.toLowerCase() === 'a' ? card.getAttribute('href') : null);

        // Title element
        const titleEl = card.querySelector('[data-testid="product-title"], .product-title, .title, h3, img[alt]');
        let title = titleEl ? (titleEl.innerText || titleEl.getAttribute('alt') || '') : '';
        title = title.trim();

        // Price elements
        const priceEl = card.querySelector('[data-testid="product-price"], .price, .product-price, .current-price');
        const priceText = priceEl ? priceEl.innerText : null;

        const origPriceEl = card.querySelector('[data-testid="original-price"], .orig-price, .original-price, .line-through');
        const origPriceText = origPriceEl ? origPriceEl.innerText : null;

        const discountEl = card.querySelector('[data-testid="discount-tag"], .discount, .discount-badge, .percent');
        const discountText = discountEl ? discountEl.innerText : null;

        // Sold count
        const soldEl = card.querySelector('[data-testid="sold-count"], .sold-count, .sales-volume, .sold');
        const soldText = soldEl ? soldEl.innerText : null;

        // Rating
        const ratingEl = card.querySelector('[data-testid="rating-score"], .rating-score, .rating, .star-rating');
        const ratingText = ratingEl ? ratingEl.innerText : null;

        // Review count
        const reviewEl = card.querySelector('[data-testid="review-count"], .review-count, .reviews');
        const reviewText = reviewEl ? reviewEl.innerText : null;

        // Shop / seller
        const shopEl = card.querySelector('[data-testid="shop-name"], .shop-name, .seller-name, .store-name');
        const shopText = shopEl ? shopEl.innerText : null;

        // Item ID / Shop ID attributes
        const itemIdAttr = card.getAttribute('data-item-id') || card.getAttribute('data-product-id') || (linkEl ? (linkEl.getAttribute('data-item-id') || linkEl.getAttribute('data-product-id')) : null);
        const shopIdAttr = card.getAttribute('data-shop-id') || card.getAttribute('data-seller-id') || (linkEl ? (linkEl.getAttribute('data-shop-id') || linkEl.getAttribute('data-seller-id')) : null);

        if (title || href) {
            items.push({
                title: title,
                href: href,
                price_text: priceText,
                orig_price_text: origPriceText,
                discount_text: discountText,
                sold_text: soldText,
                rating_text: ratingText,
                review_text: reviewText,
                shop_name: shopText,
                item_id: itemIdAttr,
                shop_id: shopIdAttr,
            });
        }
    });

    return {
        is_blocked: false,
        is_empty: isEmpty && items.length === 0,
        items: items,
    };
}"""


class TikTokDiscoveryAdapter(ProductDiscoveryAdapter):
    """
    Bounded TikTok candidate discovery collector.
    Discovers marketplace listings from keyword search surfaces and outputs canonical M2.1 ProductCandidateSnapshot objects.
    """

    def __init__(
        self,
        browser: Optional[Any] = None,
        *,
        collector_name: str = "tiktok_discovery_v1",
    ) -> None:
        self._browser = browser
        self.collector_name = collector_name

    async def discover(
        self,
        request: DiscoveryRequest,
        *,
        observed_at: Optional[datetime] = None,
    ) -> DiscoveryBatch:
        """
        Executes bounded discovery for a TikTok search query.
        """
        if not isinstance(request, DiscoveryRequest):
            raise DiscoveryInvalidRequestError(f"Expected DiscoveryRequest, got {type(request)}")

        if self._browser is None:
            raise DiscoveryError("Browser dependency is required for TikTokDiscoveryAdapter")

        eval_observed_at = observed_at or datetime.now(timezone.utc)
        candidates: List[ProductCandidateSnapshot] = []
        seen_candidate_ids: set[str] = set()
        diagnostic_codes: List[str] = []
        pages_examined = 0
        raw_items_seen = 0

        # Acquire page/session from injected dependency
        page, cleanup_fn = await self._acquire_page()

        try:
            for page_idx in range(1, request.max_pages + 1):
                if len(candidates) >= request.max_candidates:
                    break

                search_url = build_tiktok_search_url(request.query, page=page_idx, locale=request.locale)
                logger.info(f"Navigating to TikTok discovery page {page_idx}: {search_url}")

                try:
                    await self._navigate_page(page, search_url)
                except Exception as nav_exc:
                    if page_idx == 1:
                        diagnostic_codes.append("FIRST_PAGE_NAVIGATION_FAILED")
                        raise DiscoveryNavigationError(
                            f"Failed to navigate to first TikTok search page: {nav_exc}"
                        ) from nav_exc
                    else:
                        logger.warning(f"Failed to navigate to TikTok page {page_idx}: {nav_exc}")
                        diagnostic_codes.append("PARTIAL_EXTRACTION_PAGE_FAILED")
                        break

                pages_examined += 1

                # Light deterministic scrolling to trigger lazy-loaded cards
                try:
                    await self._light_scroll(page)
                except Exception:
                    pass

                # Extract listing cards via script evaluation
                try:
                    extraction_data = await self._evaluate_script(
                        page, TIKTOK_CARD_EXTRACTION_SCRIPT
                    )
                except Exception as eval_exc:
                    if page_idx == 1:
                        diagnostic_codes.append("PAGE_EVALUATION_FAILED")
                        raise DiscoveryNavigationError(
                            f"Failed to extract cards from TikTok page 1: {eval_exc}"
                        ) from eval_exc
                    else:
                        diagnostic_codes.append("PARTIAL_EXTRACTION_EVAL_FAILED")
                        break

                # Handle challenge / captcha block detection
                if extraction_data.get("is_blocked", False):
                    diagnostic_codes.append("BLOCKED_PAGE_DETECTED")
                    raise DiscoveryBlockedError(
                        f"TikTok anti-bot challenge or captcha detected for query {request.query!r}"
                    )

                # Handle true empty search results
                if extraction_data.get("is_empty", False) and len(candidates) == 0:
                    diagnostic_codes.append("TRUE_EMPTY_SEARCH")
                    break

                raw_cards = extraction_data.get("items", [])
                raw_items_seen += len(raw_cards)

                if not raw_cards:
                    if page_idx == 1:
                        diagnostic_codes.append("EXTRACTION_FAILED")
                        raise DiscoveryNavigationError(
                            f"No cards extracted on page 1 and no empty-result marker found for query {request.query!r}"
                        )
                    else:
                        diagnostic_codes.append("PARTIAL_EXTRACTION_PAGE_FAILED")
                        break

                # Map extracted cards to canonical snapshots
                for card_dict in raw_cards:
                    if len(candidates) >= request.max_candidates:
                        break

                    snapshot = self._map_card_to_snapshot(
                        card_dict=card_dict,
                        observed_at=eval_observed_at,
                    )
                    if snapshot is None:
                        # Malformed or missing title/URL card skipped deterministically
                        continue

                    if snapshot.candidate_id in seen_candidate_ids:
                        # Deduplicate while preserving first-seen order
                        continue

                    seen_candidate_ids.add(snapshot.candidate_id)
                    candidates.append(snapshot)

        finally:
            if cleanup_fn:
                try:
                    await cleanup_fn()
                except Exception as exc:
                    logger.warning(f"Error during discovery page cleanup: {exc}")

        if not diagnostic_codes:
            diagnostic_codes.append("DISCOVERY_SUCCESS")

        return DiscoveryBatch(
            platform="tiktok",
            query=request.query,
            observed_at=eval_observed_at,
            candidates=tuple(candidates),
            pages_examined=pages_examined,
            raw_items_seen=raw_items_seen,
            diagnostic_codes=tuple(diagnostic_codes),
        )

    def _map_card_to_snapshot(
        self,
        card_dict: Dict[str, Any],
        observed_at: datetime,
    ) -> Optional[ProductCandidateSnapshot]:
        """
        Pure deterministic mapping from extracted card fields to canonical ProductCandidateSnapshot.
        Returns None if required fields (title, url) cannot be resolved.
        """
        title_val = card_dict.get("title")
        title = str(title_val).strip() if title_val is not None else ""

        href_val = card_dict.get("href")
        href = str(href_val).strip() if href_val is not None else ""

        if not title or not href:
            return None

        # Resolve full URL
        if href.startswith("/"):
            url = f"https://www.tiktok.com{href}"
        elif not href.startswith("http"):
            url = f"https://www.tiktok.com/{href}"
        else:
            url = href

        # Extract stable product/item ID
        raw_item_id = card_dict.get("item_id")
        item_id_str = str(raw_item_id).strip() if raw_item_id is not None else None
        source_product_id = extract_tiktok_product_id(
            url_or_href=url,
            item_id_attr=item_id_str,
        )
        candidate_id = build_tiktok_candidate_id(source_product_id, url)

        # Parse observed market scalars
        price = parse_tiktok_price(card_dict.get("price_text"))
        original_price = parse_tiktok_price(card_dict.get("orig_price_text"))
        discount_percent = parse_tiktok_discount_percent(card_dict.get("discount_text"))
        sold_count = parse_tiktok_sold_count(card_dict.get("sold_text"))
        rating = parse_tiktok_rating(card_dict.get("rating_text"))
        review_count = parse_tiktok_review_count(card_dict.get("review_text"))

        raw_shop_name = card_dict.get("shop_name")
        shop_name = str(raw_shop_name).strip() if raw_shop_name is not None else ""
        shop_name = shop_name or None

        raw_shop_id = card_dict.get("shop_id")
        shop_id = str(raw_shop_id).strip() if raw_shop_id is not None else ""
        shop_id = shop_id or None

        try:
            return ProductCandidateSnapshot(
                candidate_id=candidate_id,
                platform="tiktok",
                url=url,
                observed_at=observed_at,
                title=title,
                source_product_id=source_product_id,
                collector=self.collector_name,
                shop_id=shop_id,
                shop_name=shop_name,
                price=price,
                original_price=original_price,
                discount_percent=discount_percent,
                sold_count=sold_count,
                rating=rating,
                review_count=review_count,
                # Unavailable metrics remain strictly None
                affiliate_commission_rate=None,
                estimated_commission_value=None,
                creator_count=None,
                video_count=None,
                similar_listing_count=None,
                sales_velocity=None,
                review_velocity=None,
                creator_velocity=None,
                video_velocity=None,
            )
        except ValueError as val_err:
            logger.warning(f"Validation error mapping card to snapshot: {val_err}")
            return None

    async def _acquire_page(self) -> Tuple[Any, Optional[Any]]:
        """
        Acquires a page object and optional cleanup coroutine from the injected browser dependency.
        Supports BrowserManager, Playwright Browser/Context, BrowserSession, or callable.
        """
        b = self._browser

        # Pattern 1: Object with new_page() (Playwright Browser or BrowserContext)
        if hasattr(b, "new_page") and callable(b.new_page):
            page = await b.new_page()
            async def cleanup():
                if hasattr(page, "close") and callable(page.close):
                    await page.close()
            return page, cleanup

        # Pattern 2: BrowserManager with get_or_create_session()
        if hasattr(b, "get_or_create_session") and callable(b.get_or_create_session):
            session = await b.get_or_create_session("discovery_run")
            return session, None

        # Pattern 3: Direct BrowserSession or Page object
        if hasattr(b, "navigate") or hasattr(b, "goto"):
            return b, None

        # Pattern 4: Async Callable
        if callable(b):
            page = await b()
            return page, None

        return b, None

    async def _navigate_page(self, page: Any, url: str) -> None:
        if hasattr(page, "goto") and callable(page.goto):
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
        elif hasattr(page, "navigate") and callable(page.navigate):
            await page.navigate(url)
        else:
            raise DiscoveryNavigationError(f"Page object {type(page)} lacks navigation capability")

    async def _light_scroll(self, page: Any) -> None:
        if hasattr(page, "evaluate") and callable(page.evaluate):
            await page.evaluate("window.scrollBy(0, 800)")

    async def _evaluate_script(self, page: Any, script: str) -> Dict[str, Any]:
        if hasattr(page, "evaluate") and callable(page.evaluate):
            res = await page.evaluate(script)
            if isinstance(res, dict):
                return res
        return {"is_blocked": False, "is_empty": False, "items": []}
