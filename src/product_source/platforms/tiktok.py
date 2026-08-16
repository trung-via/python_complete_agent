from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, List, Optional, Set

from src.product_source.models import (
    MediaRole,
    MediaProvenance,
    OriginalMediaRef,
    ProductFact,
    ProductSourcePack,
    SourcePackBlockedError,
    SourcePackExtractionError,
    build_source_pack_id,
)

logger = logging.getLogger(__name__)

_TIKTOK_EXTRACTOR_JS = """
(() => {
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
        structured: null,
        gallery_images: [],
        seller_images: [],
        fallback_images: [],
        blocked: false,
        page_title: document.title || ''
    };

    if (document.title.toLowerCase().includes('captcha') ||
        document.querySelector('script[src*="captcha"]')) {
        result.blocked = true;
        return result;
    }

    // PRIORITY 1: Structured Data
    let structuredData = null;

    try {
        if (window.SIGI_STATE) {
            structuredData = window.SIGI_STATE;
        } else {
            const sigiScript = document.getElementById('SIGI_STATE');
            if (sigiScript) {
                structuredData = JSON.parse(sigiScript.textContent);
            }
        }
    } catch (e) {}

    if (!structuredData) {
        try {
            if (window.__NEXT_DATA__) {
                structuredData = window.__NEXT_DATA__;
            } else {
                const nextScript = document.getElementById('__NEXT_DATA__');
                if (nextScript) {
                    structuredData = JSON.parse(nextScript.textContent);
                }
            }
        } catch (e) {}
    }

    let jsonLdData = null;
    const jsonLdScripts = document.querySelectorAll('script[type="application/ld+json"]');
    for (const script of jsonLdScripts) {
        try {
            const data = JSON.parse(script.textContent);
            if (data['@type'] === 'Product' || data['@type'] === 'ProductGroup') {
                jsonLdData = data;
                break;
            }
        } catch (e) {}
    }

    const findValues = (obj, key, depth) => {
        if (depth > 6) return [];
        let results = [];
        if (!obj || typeof obj !== 'object') return results;
        if (obj[key] !== undefined) results.push(obj[key]);
        for (const k in obj) {
            if (typeof obj[k] === 'object') {
                results = results.concat(findValues(obj[k], key, depth + 1));
            }
        }
        return results;
    };

    const parseStructured = () => {
        let title = '';
        let images = [];
        let brand = '';
        let shop_name = '';
        let description = '';
        let specifications = [];

        if (jsonLdData) {
            title = jsonLdData.name || '';
            description = jsonLdData.description || '';
            if (jsonLdData.brand) {
                brand = typeof jsonLdData.brand === 'string' ? jsonLdData.brand : jsonLdData.brand.name || '';
            }
            if (jsonLdData.image) {
                if (Array.isArray(jsonLdData.image)) {
                    images = jsonLdData.image.map(img => typeof img === 'string' ? img : img.url).filter(Boolean);
                } else if (typeof jsonLdData.image === 'string') {
                    images.push(jsonLdData.image);
                }
            }
        }

        if (structuredData) {
            if (!title) {
                const titles = findValues(structuredData, 'title', 0);
                if (titles.length > 0 && typeof titles[0] === 'string') title = titles[0];
            }
            if (images.length === 0) {
                const imgArrays = findValues(structuredData, 'images', 0);
                if (imgArrays.length > 0 && Array.isArray(imgArrays[0])) {
                    images = imgArrays[0].map(img => {
                        if (typeof img === 'string') return img;
                        if (img && img.urlList && img.urlList[0]) return img.urlList[0];
                        return null;
                    }).filter(Boolean);
                }
            }
            if (!description) {
                const descs = findValues(structuredData, 'description', 0);
                if (descs.length > 0 && typeof descs[0] === 'string') description = descs[0];
            }
            if (!brand) {
                const brands = findValues(structuredData, 'brand', 0);
                if (brands.length > 0 && brands[0] && brands[0].name) brand = brands[0].name;
            }
            const sellerInfo = findValues(structuredData, 'sellerInfo', 0);
            if (sellerInfo.length > 0 && sellerInfo[0] && sellerInfo[0].name) {
                shop_name = sellerInfo[0].name;
            }
            const specs = findValues(structuredData, 'specifications', 0);
            if (specs.length > 0 && Array.isArray(specs[0])) {
                specifications = specs[0];
            }
        }

        return {
            title,
            images: images.map(extractUrl).filter(Boolean),
            brand,
            shop_name,
            description: typeof description === 'string' ? description.slice(0, 10000) : '',
            specifications
        };
    };

    result.structured = parseStructured();

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
        '[class*="gallery"]', '[class*="carousel"]', '[class*="slider"]'
    ];
    let galleryNodes = [];
    for (const sel of gallerySelectors) {
        galleryNodes = [...galleryNodes, ...document.querySelectorAll(sel)];
    }
    result.gallery_images = getImagesFromNodes(galleryNodes);

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

    // PRIORITY 4: Platform Scoped Fallback (bounded, max 10)
    if (result.structured.images.length === 0 && result.gallery_images.length === 0) {
        const productContainers = document.querySelectorAll(
            '[class*="product-detail"], [class*="product-info"], main, article'
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
})();
"""


def _extract_tiktok_product_id(url: str) -> Optional[str]:
    """Extracts TikTok Shop product ID from URL patterns."""
    # Pattern: /product/{product_id}
    m = re.search(r"/product/(\d+)", url)
    if m:
        return m.group(1)
    # Pattern: /item/{product_id}
    m = re.search(r"/item/(\d+)", url)
    if m:
        return m.group(1)
    return None


class TikTokSourceExtractor:
    """Extracts product source pack from TikTok Shop product pages."""

    def __init__(self, browser: Optional[Any] = None, *, collector_name: str = 'tiktok_source_v1') -> None:
        self.browser = browser
        self.collector_name = collector_name

    async def _acquire_page(self) -> Any:
        """Acquire a page/session using the injected browser dependency."""
        # Pattern 1: BrowserManager
        if hasattr(self.browser, "get_or_create_session"):
            return await self.browser.get_or_create_session()
        # Pattern 2: Playwright Browser/Context
        if hasattr(self.browser, "new_page"):
            return await self.browser.new_page()
        # Pattern 3: Direct session with navigate() + evaluate()
        if hasattr(self.browser, "navigate") and hasattr(self.browser, "evaluate"):
            return self.browser
        # Pattern 4: Callable
        if callable(self.browser):
            import asyncio
            session = self.browser()
            if asyncio.iscoroutine(session):
                session = await session
            return session

        raise ValueError("Unsupported browser interface")

    async def extract(self, product_url: str, *, observed_at: Optional[datetime] = None) -> ProductSourcePack:
        if observed_at is None:
            observed_at = datetime.now(timezone.utc)

        product_id = _extract_tiktok_product_id(product_url)

        page = await self._acquire_page()

        try:
            if hasattr(page, "navigate") and hasattr(page, "evaluate"):
                await page.navigate(product_url)
                result = await page.evaluate(_TIKTOK_EXTRACTOR_JS)
            else:
                await page.goto(product_url, wait_until="domcontentloaded")
                result = await page.evaluate(_TIKTOK_EXTRACTOR_JS)
        except Exception as e:
            raise SourcePackExtractionError(f"Failed to navigate/evaluate TikTok product page: {e}") from e

        if not result:
            raise SourcePackExtractionError("TikTok extractor script returned null")

        if result.get("blocked"):
            raise SourcePackBlockedError("TikTok platform blocking detected (Captcha)")

        structured = result.get("structured") or {}

        title = structured.get("title", "")
        if not title:
            # Fallback to page title
            page_title = result.get("page_title", "")
            if page_title:
                title = page_title.split("|")[0].strip() or None
            else:
                title = None

        # Build media refs with proper deduplication
        seen_urls: Set[str] = set()
        media_items: List[OriginalMediaRef] = []
        ordinal = 0

        def add_media(url: str, role: MediaRole, provenance: MediaProvenance) -> None:
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
                )
            )
            ordinal += 1

        # Priority 1: Structured images
        for img_url in structured.get("images", []):
            add_media(img_url, MediaRole.PRIMARY, MediaProvenance.STRUCTURED_PRODUCT_DATA)

        # Priority 2: Gallery images
        for img_url in result.get("gallery_images", []):
            role = MediaRole.PRIMARY if not media_items else MediaRole.GALLERY
            add_media(img_url, role, MediaProvenance.SEMANTIC_PRODUCT_GALLERY)

        # Priority 3: Seller description images
        for img_url in result.get("seller_images", []):
            add_media(img_url, MediaRole.SELLER_DESCRIPTION, MediaProvenance.SEMANTIC_SELLER_DESCRIPTION)

        # Priority 4: Fallback images
        for img_url in result.get("fallback_images", []):
            add_media(img_url, MediaRole.GALLERY, MediaProvenance.PLATFORM_SCOPED_FALLBACK)

        # Build facts
        facts: List[ProductFact] = []
        if structured.get("brand"):
            facts.append(ProductFact(
                key="Brand", value=str(structured["brand"]),
                source_section="structured_data", provenance="structured_data",
            ))

        for spec in structured.get("specifications", []):
            if isinstance(spec, dict) and spec.get("name") and spec.get("value"):
                facts.append(ProductFact(
                    key=str(spec["name"]), value=str(spec["value"]),
                    source_section="specification_table", provenance="structured_data",
                ))

        source_pack_id = build_source_pack_id("tiktok", product_id, product_url)

        description = structured.get("description")
        shop_name = structured.get("shop_name") or None
        brand = structured.get("brand") or None

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
