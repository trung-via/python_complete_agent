from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from src.product_intelligence.adapters.shopee_parsing import extract_shopee_product_id
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

_SHOPEE_EXTRACTION_SCRIPT = r"""
(targetProductId) => {
    const result = {
        structured: {
            title: null,
            product_id: null,
            brand: null,
            shop_name: null,
            images: [],
            description: null,
            specs: []
        },
        gallery: [],
        variants: [],
        description_media: [],
        fallback_media: [],
        blocked: false
    };

    const isExcluded = (element) => {
        if (!element) return false;
        const excludedSelectors = [
            '.product-ratings', '.product-reviews', '[data-sqe="rating"]',
            '.shop-review', '.comment', '.review-images',
            '.similar-products', '.recommend', '.you-may-like',
            '.shopee-header-section', 'header', 'nav', 'footer'
        ];
        if (element.closest && element.closest(excludedSelectors.join(', '))) {
            return true;
        }
        let curr = element;
        while (curr && curr !== document.body) {
            const className = (curr.className || '').toString().toLowerCase();
            const id = (curr.id || '').toString().toLowerCase();
            if (
                className.includes('review') ||
                className.includes('rating') ||
                className.includes('comment') ||
                className.includes('recommend') ||
                className.includes('similar') ||
                id.includes('review') ||
                id.includes('comment')
            ) {
                return true;
            }
            curr = curr.parentElement;
        }
        return false;
    };

    // Check anti-bot block / captcha
    if (document.querySelector('.shopee-captcha') || 
        document.body.innerHTML.includes('verify.shopee') ||
        document.title.toLowerCase().includes('robot') ||
        document.title.toLowerCase().includes('captcha')) {
        result.blocked = true;
        return result;
    }

    // PRIORITY 1: Structured Data (Must match target product ID)
    const ldJsonScripts = document.querySelectorAll('script[type="application/ld+json"]');
    for (const script of ldJsonScripts) {
        try {
            const data = JSON.parse(script.textContent);
            if (data['@type'] === 'Product' || data['@type'] === 'ProductGroup') {
                const itemUrl = data.offers && data.offers.url ? data.offers.url : (data.url || '');
                const productId = data.productID || data.sku || data.mpn || '';
                
                // Match current product identity
                const matchesCurrentProduct = !targetProductId || 
                    itemUrl.includes(targetProductId) || 
                    productId.toString().includes(targetProductId) ||
                    (window.location.href.includes(targetProductId));

                if (matchesCurrentProduct) {
                    if (data.name && !result.structured.title) result.structured.title = data.name;
                    if (data.image) {
                        const imgArr = Array.isArray(data.image) ? data.image : [data.image];
                        for (const img of imgArr) {
                            const u = typeof img === 'string' ? img : (img && img.url ? img.url : null);
                            if (u && !result.structured.images.includes(u)) {
                                result.structured.images.push(u);
                            }
                        }
                    }
                    if (data.description && !result.structured.description) {
                        result.structured.description = data.description;
                    }
                    if (data.brand && data.brand.name && !result.structured.brand) {
                        result.structured.brand = data.brand.name;
                    }
                    result.structured.product_id = targetProductId;
                }
            }
        } catch (e) {}
    }

    // Specifications / Attributes table
    const specRows = document.querySelectorAll('.product-detail .kIo6pj, .product-detail .rY0UiC, .product-detail .flex.items-center');
    for (const row of specRows) {
        if (isExcluded(row)) continue;
        const label = row.querySelector('label, .h-c-a-u, ._826p0R, .G27FPf');
        const val = row.querySelector('div, a, .O99_S8, .wb9p0C');
        if (label && val) {
            const labelText = label.innerText.trim();
            const valText = val.innerText.trim();
            if (labelText && valText) {
                result.structured.specs.push({ name: labelText, value: valText });
            }
        }
    }

    if (result.structured.specs.length === 0) {
        const attrLabels = document.querySelectorAll('div.G27FPf');
        const attrValues = document.querySelectorAll('div.wb9p0C, a.wb9p0C');
        if (attrLabels.length === attrValues.length && attrLabels.length > 0) {
            for (let i = 0; i < attrLabels.length; i++) {
                const l = attrLabels[i].innerText.trim();
                const v = attrValues[i].innerText.trim();
                if (l && v) {
                    result.structured.specs.push({ name: l, value: v });
                }
            }
        }
    }

    // PRIORITY 2: Semantic Product Gallery
    const galleryContainers = document.querySelectorAll('.product-image-carousel, .product-image__content, .V9sV-Q, .xNIlvG');
    for (const container of galleryContainers) {
        if (isExcluded(container)) continue;
        const imgs = container.querySelectorAll('img');
        for (const img of imgs) {
            if (img.src && !isExcluded(img) && !result.gallery.includes(img.src)) {
                result.gallery.push(img.src);
            }
        }
    }

    // PRIORITY 2.5: Semantic Variant Media
    const variantContainers = document.querySelectorAll(
        '.product-variation, [class*="variation-item"], [class*="product-variation"], .items-center .product-variation-item'
    );
    for (const container of variantContainers) {
        if (isExcluded(container)) continue;
        const imgs = container.querySelectorAll('img');
        const labelEl = container.querySelector('span, div, p') || container;
        const label = labelEl ? labelEl.innerText.trim() : null;
        for (const img of imgs) {
            if (img.src && !isExcluded(img)) {
                result.variants.push({ url: img.src, label: label || null });
            }
        }
    }

    // PRIORITY 3: Seller Description Media
    const descriptionContainers = document.querySelectorAll('.product-detail, .product-description, .page-product__description');
    for (const container of descriptionContainers) {
        if (isExcluded(container)) continue;
        const imgs = container.querySelectorAll('img');
        for (const img of imgs) {
            if (img.src && !isExcluded(img) && !result.description_media.includes(img.src)) {
                result.description_media.push(img.src);
            }
        }
        if (!result.structured.description) {
            const descText = container.innerText.trim();
            if (descText) {
                result.structured.description = descText;
            }
        }
    }

    // PRIORITY 4: Bounded Platform-Scoped Fallback (within product summary briefing only)
    if (result.structured.images.length === 0 && result.gallery.length === 0) {
        const briefingContainers = document.querySelectorAll('.page-product__briefing, .product-briefing');
        for (const container of briefingContainers) {
            if (isExcluded(container)) continue;
            const imgs = container.querySelectorAll('img');
            let count = 0;
            for (const img of imgs) {
                if (count >= 10) break;
                if (img.src && !isExcluded(img) && !result.fallback_media.includes(img.src)) {
                    result.fallback_media.push(img.src);
                    count++;
                }
            }
        }
    }

    return result;
}
"""


class ShopeeSourceExtractor:
    """Extracts canonical product source pack from Shopee product pages."""

    def __init__(self, browser: Optional[Any] = None, *, collector_name: str = "shopee_source_v1") -> None:
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
        # Pattern 4: Direct session with navigate/evaluate
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
        product_id = extract_shopee_product_id(product_url)
        if not product_id:
            raise SourcePackExtractionError(f"Failed to extract Shopee product ID from URL: {product_url}")

        if observed_at is None:
            observed_at = datetime.now(timezone.utc)

        eff_run_id = run_id or f"shopee_source_{product_id}"

        try:
            page = await self._acquire_page(product_url, eff_run_id)
        except Exception as e:
            raise SourcePackExtractionError(f"Failed to acquire browser session for {product_url}: {e}") from e

        try:
            if hasattr(page, "evaluate") and callable(page.evaluate):
                data = await page.evaluate(_SHOPEE_EXTRACTION_SCRIPT, product_id)
            else:
                raise SourcePackExtractionError("Page object lacks evaluate capability")
        except Exception as e:
            raise SourcePackExtractionError(f"Failed to evaluate Shopee extraction script: {e}") from e

        if not data or not isinstance(data, dict):
            raise SourcePackExtractionError("Extraction script returned invalid/empty data")

        if data.get("blocked"):
            raise SourcePackBlockedError("Shopee anti-bot verification or captcha detected")

        source_pack_id = build_source_pack_id("shopee", product_id, product_url)
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
                    platform="shopee",
                    role=role,
                    provenance=provenance,
                    ordinal=ordinal,
                    variant_label=variant_label,
                )
            )
            ordinal += 1

        structured = data.get("structured", {})

        # Priority 1: Structured Product Data (if tied to product identity)
        if structured.get("product_id") == product_id:
            for url in structured.get("images", []):
                add_media(url, MediaRole.PRIMARY, MediaProvenance.STRUCTURED_PRODUCT_DATA)

        # Priority 2: Semantic Gallery
        for url in data.get("gallery", []):
            role = MediaRole.PRIMARY if not media_items else MediaRole.GALLERY
            add_media(url, role, MediaProvenance.SEMANTIC_PRODUCT_GALLERY)

        # Priority 2.5: Semantic Variants
        for var_item in data.get("variants", []):
            if isinstance(var_item, dict) and var_item.get("url"):
                add_media(
                    var_item["url"],
                    MediaRole.VARIANT,
                    MediaProvenance.SEMANTIC_VARIANT_MEDIA,
                    variant_label=var_item.get("label"),
                )

        # Priority 3: Seller Description
        for url in data.get("description_media", []):
            add_media(url, MediaRole.SELLER_DESCRIPTION, MediaProvenance.SEMANTIC_SELLER_DESCRIPTION)

        # Priority 4: Bounded Scoped Fallback
        for url in data.get("fallback_media", []):
            add_media(url, MediaRole.GALLERY, MediaProvenance.PLATFORM_SCOPED_FALLBACK)

        # Build facts
        facts: List[ProductFact] = []
        for spec in structured.get("specs", []):
            if isinstance(spec, dict) and spec.get("name") and spec.get("value"):
                facts.append(
                    ProductFact(
                        key=spec["name"],
                        value=spec["value"],
                        source_section="specification_table",
                        provenance="specification_table",
                    )
                )

        if structured.get("brand"):
            facts.append(
                ProductFact(
                    key="Brand",
                    value=structured["brand"],
                    source_section="structured_data",
                    provenance="structured_data",
                )
            )

        description = structured.get("description")

        return ProductSourcePack(
            source_pack_id=source_pack_id,
            platform="shopee",
            product_url=product_url,
            observed_at=observed_at,
            collector=self.collector_name,
            title=structured.get("title"),
            source_product_id=product_id,
            shop_name=structured.get("shop_name"),
            brand=structured.get("brand"),
            description_text=description,
            facts=tuple(facts),
            media=tuple(media_items),
        )
