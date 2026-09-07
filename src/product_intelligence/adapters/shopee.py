from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from src.product_intelligence.adapters.shopee_parsing import (
    build_shopee_candidate_id,
    build_shopee_search_url,
    extract_shopee_product_id,
    parse_shopee_discount_percent,
    parse_shopee_price,
    parse_shopee_rating,
    parse_shopee_review_count,
    parse_shopee_sold_count,
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

_READINESS_POLL_INTERVAL_SECONDS: float = 0.5
_READINESS_MAX_ATTEMPTS: int = 10


async def _readiness_sleep(seconds: float) -> None:
    await asyncio.sleep(seconds)


# Client-side extraction script for Shopee search/listing pages
SHOPEE_CARD_EXTRACTION_SCRIPT = r"""() => {
    // 1. Check for Challenge / Captcha / Block Page Indicators
    const docTitle = document.title ? document.title.toLowerCase() : '';
    const bodyText = document.body ? document.body.innerText.toLowerCase() : '';
    const isBlocked = (
        docTitle.includes('robot') ||
        docTitle.includes('captcha') ||
        docTitle.includes('security verification') ||
        document.querySelector('.shopee-captcha, #challenge-running, .captcha_container, [data-sqe="captcha"]') !== null ||
        bodyText.includes('please verify you are human') ||
        bodyText.includes('xác minh bảo mật')
    );

    if (isBlocked) {
        return { is_blocked: true, is_empty: false, items: [] };
    }

    // 2. Check for True Empty Search Results
    const isEmpty = (
        document.querySelector('.shopee-search-empty-result-section, .no-result, [data-sqe="empty"]') !== null ||
        bodyText.includes('không tìm thấy kết quả') ||
        bodyText.includes('no results found')
    );

    function extractCardData(card, fallbackAnchor) {
        const linkEl = fallbackAnchor || (
            (card.tagName && card.tagName.toLowerCase() === 'a')
                ? card
                : card.querySelector('a[data-sqe="link"], a[href*="/product/"], a[href*="-i."]')
        );
        const rawHref = linkEl ? linkEl.getAttribute('href') : (card.getAttribute ? card.getAttribute('href') : null);
        const href = rawHref ? rawHref.trim() : null;

        let title = '';
        const titleEl = card.querySelector('.CboxLq, [data-sqe="name"], .whitespace-normal, .line-clamp-2');
        if (titleEl && titleEl.innerText) {
            title = titleEl.innerText;
        }
        if (!title.trim()) {
            const imgEl = card.querySelector('img[alt]');
            if (imgEl && imgEl.getAttribute('alt')) {
                title = imgEl.getAttribute('alt');
            }
        }
        if (!title.trim()) {
            const ariaLabel = (card.getAttribute ? card.getAttribute('aria-label') : null)
                || (linkEl && linkEl.getAttribute ? linkEl.getAttribute('aria-label') : null)
                || (card.querySelector && card.querySelector('[aria-label]') ? card.querySelector('[aria-label]').getAttribute('aria-label') : null);
            if (ariaLabel) {
                title = ariaLabel;
            }
        }
        if (!title.trim()) {
            const titleAttr = (card.getAttribute ? card.getAttribute('title') : null)
                || (linkEl && linkEl.getAttribute ? linkEl.getAttribute('title') : null)
                || (card.querySelector && card.querySelector('[title]') ? card.querySelector('[title]').getAttribute('title') : null);
            if (titleAttr) {
                title = titleAttr;
            }
        }
        if (!title.trim() && linkEl) {
            const anchorText = (linkEl.innerText || '').trim();
            if (anchorText) {
                title = anchorText.slice(0, 300);
            }
        }
        title = title.trim();

        // Price elements
        const priceEl = card.querySelector('.vioxXd, .k9JZlv, ._1d0D8S, [data-sqe="price"], .font-medium');
        const priceText = priceEl ? priceEl.innerText : null;

        const origPriceEl = card.querySelector('.reG54x, ._1fkKk1, .line-through');
        const origPriceText = origPriceEl ? origPriceEl.innerText : null;

        const discountEl = card.querySelector('.percent, ._1pZzF0, .discount-badge');
        const discountText = discountEl ? discountEl.innerText : null;

        // Sold count
        const soldEl = card.querySelector('.r6wKnM, ._2VI87d, [data-sqe="sold"], .truncate');
        const soldText = soldEl ? soldEl.innerText : null;

        // Rating
        const ratingEl = card.querySelector('.rating-stars, [data-sqe="rating"], .shopee-rating-stars');
        const ratingText = ratingEl ? ratingEl.innerText : null;

        // Shop / location
        const shopEl = card.querySelector('.shop-name, ._2b7X6I, .location');
        const shopText = shopEl ? shopEl.innerText : null;

        // Item ID attribute if exposed
        const itemIdAttr = (card.getAttribute ? card.getAttribute('data-item-id') : null)
            || (linkEl && linkEl.getAttribute ? linkEl.getAttribute('data-item-id') : null);
        const shopIdAttr = (card.getAttribute ? card.getAttribute('data-shop-id') : null)
            || (linkEl && linkEl.getAttribute ? linkEl.getAttribute('data-shop-id') : null);

        // Review count (often adjacent to rating or in parentheses)
        const reviewEl = card.querySelector('.shopee-rating-stars__reviews, .rating-reviews, [data-sqe="review"]');
        const reviewText = reviewEl ? reviewEl.innerText : null;

        return {
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
        };
    }

    // 3. Extract Listing Cards using primary container selectors
    const cardElements = document.querySelectorAll(
        '.shopee-search-item-result__item, [data-sqe="item"], div.col-xs-2-4, .shopee-search-item-result'
    );

    const items = [];
    cardElements.forEach(card => {
        const item = extractCardData(card, null);
        if (item && (item.title || item.href)) {
            items.push(item);
        }
    });

    // 4. Fallback: If legacy presentation-only card container selectors are absent,
    // discover via exact product anchors using canonical Shopee product URL forms (-i. and /product/)
    if (items.length === 0) {
        const candidateAnchors = document.querySelectorAll('a[href*="-i."], a[href*="/product/"]');
        const seenHrefs = new Set();

        candidateAnchors.forEach(anchor => {
            const rawHref = anchor.getAttribute('href');
            if (!rawHref) return;
            const cleanHref = rawHref.trim();
            if (!cleanHref) return;
            if (!cleanHref.includes('-i.') && !cleanHref.includes('/product/')) return;
            if (seenHrefs.has(cleanHref)) return;
            seenHrefs.add(cleanHref);

            // Locate nearest product-card context bounded to this single product
            let cardContext = anchor;
            let parent = anchor.parentElement;
            let depth = 0;
            while (parent && parent !== document.body && parent !== document.documentElement && depth < 4) {
                const productLinks = parent.querySelectorAll('a[href*="-i."], a[href*="/product/"]');
                if (productLinks.length === 1) {
                    cardContext = parent;
                    parent = parent.parentElement;
                    depth++;
                } else {
                    break;
                }
            }

            const item = extractCardData(cardContext, anchor);
            if (item && item.href && item.title) {
                items.push(item);
            }
        });
    }

    return {
        is_blocked: false,
        is_empty: isEmpty && items.length === 0,
        items: items,
    };
}"""


class ShopeeDiscoveryAdapter(ProductDiscoveryAdapter):
    """
    Bounded Shopee candidate discovery collector.
    Discovers marketplace listings from keyword search surfaces and outputs canonical M2.1 ProductCandidateSnapshot objects.
    """

    def __init__(
        self,
        browser: Optional[Any] = None,
        *,
        collector_name: str = "shopee_discovery_v1",
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
        Executes bounded discovery for a Shopee search query.
        """
        if not isinstance(request, DiscoveryRequest):
            raise DiscoveryInvalidRequestError(f"Expected DiscoveryRequest, got {type(request)}")

        if self._browser is None:
            raise DiscoveryError("Browser dependency is required for ShopeeDiscoveryAdapter")

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

                search_url = build_shopee_search_url(request.query, page=page_idx)
                logger.info(f"Navigating to Shopee discovery page {page_idx}: {search_url}")

                try:
                    await self._navigate_page(page, search_url)
                except Exception as nav_exc:
                    if page_idx == 1:
                        diagnostic_codes.append("FIRST_PAGE_NAVIGATION_FAILED")
                        raise DiscoveryNavigationError(
                            f"Failed to navigate to first Shopee search page: {nav_exc}"
                        ) from nav_exc
                    else:
                        logger.warning(f"Failed to navigate to Shopee page {page_idx}: {nav_exc}")
                        diagnostic_codes.append("PARTIAL_EXTRACTION_PAGE_FAILED")
                        break

                pages_examined += 1

                # Light deterministic scrolling to trigger lazy-loaded cards
                try:
                    await self._light_scroll(page)
                except Exception:
                    pass

                # Fixed bounded same-page readiness sampling boundary
                extraction_data: Optional[Dict[str, Any]] = None
                for attempt in range(1, _READINESS_MAX_ATTEMPTS + 1):
                    try:
                        extraction_data = await self._evaluate_script(
                            page, SHOPEE_CARD_EXTRACTION_SCRIPT
                        )
                    except Exception as eval_exc:
                        if attempt < _READINESS_MAX_ATTEMPTS:
                            await _readiness_sleep(_READINESS_POLL_INTERVAL_SECONDS)
                            continue
                        if page_idx == 1:
                            diagnostic_codes.append("PAGE_EVALUATION_FAILED")
                            raise DiscoveryNavigationError(
                                f"Failed to extract cards from Shopee page 1: {eval_exc}"
                            ) from eval_exc
                        else:
                            diagnostic_codes.append("PARTIAL_EXTRACTION_EVAL_FAILED")
                            break

                    # Terminal state 1: Explicit blocked / challenge / captcha
                    if extraction_data.get("is_blocked", False):
                        diagnostic_codes.append("BLOCKED_PAGE_DETECTED")
                        raise DiscoveryBlockedError(
                            f"Shopee anti-bot challenge or captcha detected for query {request.query!r}"
                        )

                    # Terminal state 2: Explicit true empty search results
                    if extraction_data.get("is_empty", False):
                        break

                    # Terminal state 3: At least one item extracted
                    raw_cards = extraction_data.get("items", [])
                    if raw_cards:
                        break

                    # Unready state: delay before next attempt if within bounds
                    if attempt < _READINESS_MAX_ATTEMPTS:
                        await _readiness_sleep(_READINESS_POLL_INTERVAL_SECONDS)

                if extraction_data is None:
                    # Occurs if evaluation failed on later page (page_idx > 1)
                    break

                # Handle true empty search results
                if extraction_data.get("is_empty", False):
                    if len(candidates) == 0:
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
            platform="shopee",
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
        title = card_dict.get("title", "").strip()
        href = card_dict.get("href", "").strip()

        if not title or not href:
            return None

        # Resolve full URL
        if href.startswith("/"):
            url = f"https://shopee.vn{href}"
        elif not href.startswith("http"):
            url = f"https://shopee.vn/{href}"
        else:
            url = href

        # Extract stable product/item ID
        source_product_id = extract_shopee_product_id(
            url_or_href=url,
            item_id_attr=card_dict.get("item_id"),
        )
        candidate_id = build_shopee_candidate_id(source_product_id, url)

        # Parse observed market scalars
        price = parse_shopee_price(card_dict.get("price_text"))
        original_price = parse_shopee_price(card_dict.get("orig_price_text"))
        discount_percent = parse_shopee_discount_percent(card_dict.get("discount_text"))
        sold_count = parse_shopee_sold_count(card_dict.get("sold_text"))
        rating = parse_shopee_rating(card_dict.get("rating_text"))
        review_count = parse_shopee_review_count(card_dict.get("review_text"))

        shop_name = card_dict.get("shop_name", "").strip() or None
        shop_id = card_dict.get("shop_id", "").strip() or None

        try:
            return ProductCandidateSnapshot(
                candidate_id=candidate_id,
                platform="shopee",
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
