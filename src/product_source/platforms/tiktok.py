from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from src.product_source.models import (
    MediaProvenance,
    MediaRole,
    OriginalMediaRef,
    ProductFact,
    ProductSourcePack,
    SourcePackBlockedError,
    SourcePackError,
    SourcePackExtractionError,
    build_source_pack_id,
)

logger = logging.getLogger(__name__)

_TIKTOK_EXTRACTOR_JS = r"""
(targetProductId) => {
    const extractUrl = (str) => {
        if (!str) return null;
        try {
            const url = new URL(str, window.location.origin);
            if (url.protocol === 'http:' || url.protocol === 'https:') {
                return url.href;
            }
        } catch (e) {}
        return null;
    };

    const isExcluded = (node) => {
        if (!node) return false;
        while (node && node !== document.body) {
            const className = (node.className || '').toString().toLowerCase();
            const id = (node.id || '').toString().toLowerCase();
            if (
                className.includes('review') ||
                className.includes('rating') ||
                className.includes('comment') ||
                className.includes('recommend') ||
                className.includes('similar') ||
                className.includes('ugc') ||
                className.includes('you-may-like') ||
                className.includes('suggestion') ||
                id.includes('review') ||
                id.includes('comment') ||
                id.includes('recommend')
            ) {
                return true;
            }
            node = node.parentNode;
        }
        return false;
    };

    const result = {
        structured: {
            title: null,
            product_id: null,
            brand: null,
            shop_name: null,
            images: [],
            description: null,
            specifications: []
        },
        gallery_images: [],
        variants: [],
        seller_images: [],
        fallback_images: [],
        blocked: false,
        page_title: document.title || ''
    };

    if (document.title.toLowerCase().includes('captcha') ||
        document.title.toLowerCase().includes('robot') ||
        document.querySelector('script[src*="captcha"]')) {
        result.blocked = true;
        return result;
    }

    // PRIORITY 1: Structured Data (Identity strictly matched to targetProductId from the object itself)
    // Try JSON-LD first
    const jsonLdScripts = document.querySelectorAll('script[type="application/ld+json"]');
    for (const script of jsonLdScripts) {
        try {
            const data = JSON.parse(script.textContent);
            if (data['@type'] === 'Product' || data['@type'] === 'ProductGroup') {
                const itemUrl = data.offers && data.offers.url ? data.offers.url : (data.url || '');
                const productId = data.productID || data.sku || '';
                const matches = targetProductId && (
                    itemUrl.includes(targetProductId) || 
                    productId.toString().includes(targetProductId) ||
                    (data.sku && data.sku.toString().includes(targetProductId))
                );

                if (matches) {
                    if (data.name && !result.structured.title) result.structured.title = data.name;
                    if (data.description && !result.structured.description) result.structured.description = data.description;
                    if (data.brand) {
                        const bName = typeof data.brand === 'string' ? data.brand : (data.brand.name || null);
                        if (bName && !result.structured.brand) result.structured.brand = bName;
                    }
                    if (data.image) {
                        const imgArr = Array.isArray(data.image) ? data.image : [data.image];
                        for (const img of imgArr) {
                            const u = extractUrl(typeof img === 'string' ? img : (img && img.url ? img.url : null));
                            if (u && !result.structured.images.includes(u)) {
                                result.structured.images.push(u);
                            }
                        }
                    }
                    result.structured.product_id = targetProductId;
                }
            }
        } catch (e) {}
    }

    // Try SIGI_STATE or __NEXT_DATA__ (scoped to productDetail / itemInfo)
    let stateObj = null;
    try {
        if (window.SIGI_STATE) stateObj = window.SIGI_STATE;
        else if (window.__NEXT_DATA__) stateObj = window.__NEXT_DATA__;
        else {
            const sEl = document.getElementById('SIGI_STATE') || document.getElementById('__NEXT_DATA__');
            if (sEl) stateObj = JSON.parse(sEl.textContent);
        }
    } catch (e) {}

    if (stateObj && typeof stateObj === 'object') {
        const productCandidates = [];
        if (stateObj.productInfo) productCandidates.push(stateObj.productInfo);
        if (stateObj.productDetail) productCandidates.push(stateObj.productDetail);
        if (stateObj.itemInfo && stateObj.itemInfo.itemStruct) productCandidates.push(stateObj.itemInfo.itemStruct);
        if (stateObj.props && stateObj.props.pageProps && stateObj.props.pageProps.productInfo) {
            productCandidates.push(stateObj.props.pageProps.productInfo);
        }

        for (const prod of productCandidates) {
            const pId = prod.productId || prod.id || prod.itemId || '';
            const matches = targetProductId && pId.toString().includes(targetProductId);
            if (matches) {
                if (prod.title && !result.structured.title) result.structured.title = prod.title;
                if (prod.description && !result.structured.description) result.structured.description = prod.description;
                if (prod.brand && prod.brand.name && !result.structured.brand) result.structured.brand = prod.brand.name;
                if (prod.seller && prod.seller.name && !result.structured.shop_name) result.structured.shop_name = prod.seller.name;
                if (prod.images && Array.isArray(prod.images)) {
                    for (const img of prod.images) {
                        const u = extractUrl(typeof img === 'string' ? img : (img.urlList ? img.urlList[0] : img.url));
                        if (u && !result.structured.images.includes(u)) result.structured.images.push(u);
                    }
                }
                if (prod.specifications && Array.isArray(prod.specifications)) {
                    for (const spec of prod.specifications) {
                        if (spec.name && spec.value) {
                            result.structured.specifications.push({ name: spec.name, value: spec.value });
                        }
                    }
                }
                result.structured.product_id = targetProductId;
                break;
            }
        }
    }

    const getImagesFromNodes = (nodes) => {
        const urls = [];
        const seen = new Set();
        for (const node of nodes) {
            if (isExcluded(node)) continue;
            const imgs = node.querySelectorAll ? node.querySelectorAll('img') : [];
            for (const img of imgs) {
                if (!isExcluded(img) && img.src) {
                    const u = extractUrl(img.src);
                    if (u && !seen.has(u)) {
                        seen.add(u);
                        urls.push(u);
                    }
                }
            }
        }
        return urls;
    };

    // PRIORITY 2: Semantic Product Gallery
    const gallerySelectors = [
        '.product-image', '.pdp-image',
        '[data-testid*="gallery"]',
        '[class*="gallery-container"]', '[class*="pdp-carousel"]', '[class*="product-slider"]'
    ];
    let galleryNodes = [];
    for (const sel of gallerySelectors) {
        galleryNodes = [...galleryNodes, ...document.querySelectorAll(sel)];
    }
    result.gallery_images = getImagesFromNodes(galleryNodes);

    // PRIORITY 2.5: Semantic Variant Media
    const variantSelectors = [
        '[class*="sku-item"]', '[class*="spec-item"]', '[class*="variation-item"]', '[data-testid*="sku"]'
    ];
    for (const sel of variantSelectors) {
        const nodes = document.querySelectorAll(sel);
        for (const n of nodes) {
            if (isExcluded(n)) continue;
            const imgs = n.querySelectorAll('img');
            const labelEl = n.querySelector('span, div, p') || n;
            const label = labelEl ? labelEl.innerText.trim() : null;
            for (const img of imgs) {
                if (!isExcluded(img) && img.src) {
                    const u = extractUrl(img.src);
                    if (u) {
                        result.variants.push({ url: u, label: label || null });
                    }
                }
            }
        }
    }

    // PRIORITY 3: Seller Description Media
    const sellerSelectors = [
        '[class*="seller-description"]',
        '[class*="product-description"]',
        '[data-testid*="description"]'
    ];
    let sellerNodes = [];
    for (const sel of sellerSelectors) {
        sellerNodes = [...sellerNodes, ...document.querySelectorAll(sel)];
    }
    result.seller_images = getImagesFromNodes(sellerNodes);

    // PRIORITY 4: Bounded Platform-Scoped Fallback
    // Confined to specific product detail container ONLY
    if (result.structured.images.length === 0 && result.gallery_images.length === 0) {
        const productContainers = document.querySelectorAll(
            '[data-testid="pdp-container"], .pdp-container, .product-container, [class*="product-detail-container"], [class*="product-info-container"]'
        );
        let count = 0;
        const urls = new Set();
        for (const container of productContainers) {
            if (isExcluded(container)) continue;
            const imgs = container.querySelectorAll('img');
            for (const img of imgs) {
                if (count >= 10) break;
                if (!isExcluded(img) && img.src) {
                    const u = extractUrl(img.src);
                    if (u && !urls.has(u)) {
                        urls.add(u);
                        count++;
                    }
                }
            }
            if (count >= 10) break;
        }
        result.fallback_images = Array.from(urls);
    }

    return result;
}
"""


def _extract_tiktok_product_id(url: str) -> Optional[str]:
    """Extracts TikTok Shop product ID from URL patterns."""
    m = re.search(r"/product/(\d+)", url)
    if m:
        return m.group(1)
    m = re.search(r"/item/(\d+)", url)
    if m:
        return m.group(1)
    m = re.search(r"itemId=(\d+)", url)
    if m:
        return m.group(1)
    return None


class TikTokSourceExtractor:
    """Extracts canonical product source pack from TikTok Shop product pages."""

    def __init__(self, browser: Optional[Any] = None, *, collector_name: str = "tiktok_source_v1") -> None:
        self.browser = browser
        self.collector_name = collector_name

    async def _acquire_page(self, url: str, run_id: str) -> Any:
        b = self.browser

        # Pattern 1: BrowserManager with get_or_create_session(run_id)
        if hasattr(b, "get_or_create_session") and callable(b.get_or_create_session):
            page = await b.get_or_create_session(run_id)
        # Pattern 2: Playwright Browser or BrowserContext with new_page()
        elif hasattr(b, "new_page") and callable(b.new_page):
            res = b.new_page()
            import inspect
            page = await res if inspect.isawaitable(res) else res
            if hasattr(page, "__aenter__"):
                page = await page.__aenter__()
        # Pattern 3: Async or sync callable
        elif callable(b):
            import inspect
            res = b()
            page = await res if inspect.isawaitable(res) else res
        # Pattern 4: Direct session
        elif hasattr(b, "navigate") or hasattr(b, "goto"):
            page = b
        else:
            page = b

        if hasattr(page, "navigate") and callable(page.navigate):
            await page.navigate(url)
        elif hasattr(page, "goto") and callable(page.goto):
            await page.goto(url, wait_until="domcontentloaded")

        return page

    async def extract(
        self,
        product_url: str,
        *,
        run_id: Optional[str] = None,
        observed_at: Optional[datetime] = None,
    ) -> ProductSourcePack:
        if observed_at is None:
            observed_at = datetime.now(timezone.utc)

        product_id = _extract_tiktok_product_id(product_url)
        eff_run_id = run_id or (f"tiktok_source_{product_id}" if product_id else "tiktok_source_run")

        try:
            page = await self._acquire_page(product_url, eff_run_id)
        except Exception as e:
            raise SourcePackExtractionError(f"Failed to acquire browser session for {product_url}: {e}") from e

        try:
            if hasattr(page, "evaluate") and callable(page.evaluate):
                result = await page.evaluate(_TIKTOK_EXTRACTOR_JS, product_id)
            else:
                raise SourcePackExtractionError("Page object lacks evaluate capability")
        except Exception as e:
            raise SourcePackExtractionError(f"Failed to evaluate TikTok extraction script: {e}") from e

        if not result or not isinstance(result, dict):
            raise SourcePackExtractionError("TikTok extractor script returned invalid/null data")

        if result.get("blocked"):
            raise SourcePackBlockedError("TikTok platform blocking detected (Captcha)")

        structured = result.get("structured") or {}
        structured_matches = (structured.get("product_id") == product_id and product_id is not None)

        seen_urls: Set[str] = set()
        media_items: List[OriginalMediaRef] = []
        ordinal = 0

        def add_media(
            url: str,
            role: MediaRole,
            provenance: MediaProvenance,
            variant_label: Optional[str] = None,
        ) -> None:
            nonlocal ordinal
            if not url or url in seen_urls:
                return
            if not (url.startswith("http://") or url.startswith("https://")):
                return
            seen_urls.add(url)
            media_items.append(
                OriginalMediaRef(
                    source_url=url,
                    platform="tiktok",
                    role=role,
                    provenance=provenance,
                    ordinal=ordinal,
                    variant_label=variant_label,
                )
            )
            ordinal += 1

        # Priority 1: Structured images (identity checked)
        if structured_matches:
            for img_url in structured.get("images", []):
                add_media(img_url, MediaRole.PRIMARY, MediaProvenance.STRUCTURED_PRODUCT_DATA)

        # Priority 2: Gallery images
        for img_url in result.get("gallery_images", []):
            role = MediaRole.PRIMARY if not media_items else MediaRole.GALLERY
            add_media(img_url, role, MediaProvenance.SEMANTIC_PRODUCT_GALLERY)

        # Priority 2.5: Variant images
        for var_item in result.get("variants", []):
            if isinstance(var_item, dict) and var_item.get("url"):
                add_media(
                    var_item["url"],
                    MediaRole.VARIANT,
                    MediaProvenance.SEMANTIC_VARIANT_MEDIA,
                    variant_label=var_item.get("label"),
                )

        # Priority 3: Seller description images
        for img_url in result.get("seller_images", []):
            add_media(img_url, MediaRole.SELLER_DESCRIPTION, MediaProvenance.SEMANTIC_SELLER_DESCRIPTION)

        # Priority 4: Bounded Scoped Fallback
        for img_url in result.get("fallback_images", []):
            add_media(img_url, MediaRole.GALLERY, MediaProvenance.PLATFORM_SCOPED_FALLBACK)

        # Fail closed when no trusted media could be extracted
        if not media_items:
            raise SourcePackExtractionError(
                f"No trusted seller-product media could be extracted for TikTok product {product_id} ({product_url})"
            )

        title = structured.get("title") if structured_matches else None
        if not title:
            page_title = result.get("page_title", "")
            if page_title:
                title = page_title.split("|")[0].strip() or None

        # Build facts
        facts: List[ProductFact] = []
        if structured_matches and structured.get("brand"):
            facts.append(
                ProductFact(
                    key="Brand",
                    value=str(structured["brand"]),
                    source_section="structured_data",
                    provenance="structured_data",
                )
            )

        if structured_matches:
            for spec in structured.get("specifications", []):
                if isinstance(spec, dict) and spec.get("name") and spec.get("value"):
                    facts.append(
                        ProductFact(
                            key=str(spec["name"]),
                            value=str(spec["value"]),
                            source_section="specification_table",
                            provenance="structured_data",
                        )
                    )

        source_pack_id = build_source_pack_id("tiktok", product_id, product_url)
        description = structured.get("description") if structured_matches else None
        shop_name = structured.get("shop_name") if structured_matches else None
        brand = structured.get("brand") if structured_matches else None

        return ProductSourcePack(
            source_pack_id=source_pack_id,
            platform="tiktok",
            product_url=product_url,
            observed_at=observed_at,
            collector=self.collector_name,
            title=title,
            source_product_id=product_id,
            shop_name=shop_name,
            brand=brand,
            description_text=description if description else None,
            facts=tuple(facts),
            media=tuple(media_items),
        )
