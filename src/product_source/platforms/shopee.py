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
            model_sku: null,
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
            '.shopee-header-section', 'header', 'nav', 'footer',
            '[class*="footer"]', '[class*="header"]', '[class*="nav"]',
            '[class*="voucher"]', '[class*="bundle"]', '[class*="badge"]'
        ];
        if (element.closest && element.closest(excludedSelectors.join(', '))) {
            return true;
        }
        let curr = element;
        while (curr && curr !== document.body) {
            const tagName = (curr.tagName || '').toLowerCase();
            if (tagName === 'footer' || tagName === 'header' || tagName === 'nav') {
                return true;
            }
            const className = (curr.className || '').toString().toLowerCase();
            const id = (curr.id || '').toString().toLowerCase();
            if (
                className.includes('review') ||
                className.includes('rating') ||
                className.includes('comment') ||
                className.includes('recommend') ||
                className.includes('similar') ||
                className.includes('footer') ||
                className.includes('header') ||
                className.includes('nav') ||
                id.includes('review') ||
                id.includes('rating') ||
                id.includes('comment') ||
                id.includes('footer')
            ) {
                return true;
            }
            curr = curr.parentElement;
        }
        return false;
    };

    const extractMediaUrl = (raw) => {
        if (!raw || typeof raw !== 'string') return null;
        let clean = raw.trim();
        const bgMatch = clean.match(/url\(['"]?(https?:\/\/[^'")\s]+)['"]?\)/i);
        if (bgMatch) clean = bgMatch[1];
        if (clean.startsWith('//')) clean = 'https:' + clean;
        if (clean.includes('http://') || clean.includes('https://')) {
            const httpIdx = clean.indexOf('http');
            if (httpIdx > 0) clean = clean.substring(httpIdx);
        }
        if (!clean.startsWith('http')) return null;

        // Filter out UI SVG icons, static asset icons, or badges
        if (clean.endsWith('.svg') || clean.includes('.svg?') || clean.includes('.svg#') || clean.includes('icon_')) {
            return null;
        }

        // Canonicalize Shopee image URLs by stripping thumbnail resize query/suffix if present
        if (clean.includes('@resize_')) {
            clean = clean.split('@resize_')[0];
        }
        if (clean.endsWith('_tn')) {
            clean = clean.substring(0, clean.length - 3);
        }

        return clean;
    };

    const getMediaUrls = (rootEl) => {
        const urls = [];
        const seen = new Set();

        const addUrl = (raw) => {
            const u = extractMediaUrl(raw);
            if (u && !seen.has(u)) {
                seen.add(u);
                urls.push(u);
            }
        };

        if (!rootEl || isExcluded(rootEl)) return urls;

        // 1. Inspect rootEl itself if it is an img or has background-image
        if (rootEl.tagName === 'IMG') {
            addUrl(rootEl.getAttribute('src'));
            addUrl(rootEl.src);
            addUrl(rootEl.getAttribute('data-src'));
            const srcset = rootEl.getAttribute('srcset');
            if (srcset) {
                const firstSrc = srcset.split(',')[0].trim().split(' ')[0];
                addUrl(firstSrc);
            }
        }
        if (rootEl.style && (rootEl.style.backgroundImage || rootEl.getAttribute('style'))) {
            addUrl(rootEl.style.backgroundImage || rootEl.getAttribute('style'));
        }

        // 2. Inspect descendant img elements
        const imgs = rootEl.querySelectorAll ? rootEl.querySelectorAll('img') : [];
        for (const img of imgs) {
            if (isExcluded(img)) continue;
            addUrl(img.getAttribute('src'));
            addUrl(img.src);
            addUrl(img.getAttribute('data-src'));
            const srcset = img.getAttribute('srcset');
            if (srcset) {
                const firstSrc = srcset.split(',')[0].trim().split(' ')[0];
                addUrl(firstSrc);
            }
        }

        // 3. Inspect descendant background-image elements
        const bgEls = rootEl.querySelectorAll ? rootEl.querySelectorAll('[style*="background-image"], [style*="url("]') : [];
        for (const el of bgEls) {
            if (isExcluded(el)) continue;
            addUrl(el.style.backgroundImage || el.getAttribute('style'));
        }

        return urls;
    };

    // Check anti-bot block / captcha
    if (document.querySelector('.shopee-captcha, iframe[src*="/verify/captcha"], [class*="captcha-container"]') || 
        window.location.pathname.startsWith('/verify') ||
        window.location.href.includes('/verify/') ||
        document.title.toLowerCase().includes('robot') ||
        document.title.toLowerCase().includes('captcha')) {
        result.blocked = true;
        return result;
    }

    // PRIORITY 1: Structured Data (Identity strictly matched to targetProductId from the object itself)
    const ldJsonScripts = document.querySelectorAll('script[type="application/ld+json"]');
    for (const script of ldJsonScripts) {
        try {
            const data = JSON.parse(script.textContent);
            if (data['@type'] === 'Product' || data['@type'] === 'ProductGroup') {
                const itemUrl = data.offers && data.offers.url ? data.offers.url : (data.url || '');
                const productId = (data.productID || data.sku || data.mpn || '').toString();
                const dataSku = (data.sku || '').toString();
                
                let urlMatch = false;
                if (itemUrl && targetProductId) {
                    const match = itemUrl.match(/-i\.\d+\.(\d+)/);
                    if (match && match[1] === targetProductId.toString()) {
                        urlMatch = true;
                    }
                }

                const matchesCurrentProduct = targetProductId && (
                    urlMatch || 
                    productId === targetProductId.toString() ||
                    dataSku === targetProductId.toString()
                );

                if (matchesCurrentProduct) {
                    if (dataSku && !result.structured.model_sku) result.structured.model_sku = dataSku;
                    if (data.name && !result.structured.title) result.structured.title = data.name;
                    if (data.image) {
                        const imgArr = Array.isArray(data.image) ? data.image : [data.image];
                        for (const img of imgArr) {
                            const rawUrl = typeof img === 'string' ? img : (img && (img.url || img.contentUrl) ? (img.url || img.contentUrl) : null);
                            const u = extractMediaUrl(rawUrl);
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

    // PRIORITY 2: Semantic & Anchored Product Gallery
    // Strategy 2A: Semantic gallery selectors
    const gallerySelectors = [
        '.product-image-carousel', '.product-image__content', '.V9sV-Q', '.xNIlvG',
        '[class*="gallery-container"]', '[class*="image-carousel"]', '[class*="product-slider"]',
        '[class*="product-gallery"]', '[class*="product-image"]'
    ];
    for (const sel of gallerySelectors) {
        const containers = document.querySelectorAll(sel);
        for (const container of containers) {
            const urls = getMediaUrls(container);
            for (const u of urls) {
                if (!result.gallery.includes(u)) {
                    result.gallery.push(u);
                }
            }
        }
    }

    // Strategy 2B: Positive Anchor Expansion (anchored by verified identity/structured image or title)
    // Avoids scanning arbitrary whole-page sections or unverified promo/recommendation blocks
    if (result.gallery.length === 0) {
        let seedNode = null;

        // Anchor 1: Match verified structured seed image in the DOM
        if (result.structured.images.length > 0) {
            const seedUrls = result.structured.images;
            const allDomImgs = document.querySelectorAll('img, [style*="background-image"]');
            for (const el of allDomImgs) {
                if (isExcluded(el)) continue;
                const elUrls = getMediaUrls(el);
                for (const u of elUrls) {
                    const uParts = u.split('/');
                    const uFile = uParts[uParts.length - 1].split('?')[0].split('@')[0].split('_tn')[0];
                    for (const s of seedUrls) {
                        const sParts = s.split('/');
                        const sFile = sParts[sParts.length - 1].split('?')[0].split('@')[0].split('_tn')[0];
                        if (u === s || (uFile && sFile && uFile === sFile && uFile.length > 8)) {
                            seedNode = el;
                            break;
                        }
                    }
                    if (seedNode) break;
                }
                if (seedNode) break;
            }
        }

        // Anchor 2: If seed image node not found, match verified product title in the DOM
        if (!seedNode && result.structured.title) {
            const h1s = document.querySelectorAll('h1, [class*="title"], [class*="name"]');
            for (const h of h1s) {
                if (isExcluded(h)) continue;
                if (h.innerText && h.innerText.trim().includes(result.structured.title.trim().substring(0, 30))) {
                    seedNode = h;
                    break;
                }
            }
        }

        // If a verified positive anchor is found, locate its enclosing product media column / thumbnail cluster
        if (seedNode) {
            let curr = seedNode;
            let galleryFound = false;
            let fallbackUrls = [];
            for (let level = 0; level < 6 && curr && curr !== document.body; level++) {
                if (isExcluded(curr)) break;

                const candidateUrls = getMediaUrls(curr);
                if (candidateUrls.length > fallbackUrls.length) {
                    fallbackUrls = candidateUrls;
                }
                if (candidateUrls.length >= 2) {
                    for (const u of candidateUrls) {
                        if (!result.gallery.includes(u)) {
                            result.gallery.push(u);
                        }
                    }
                    galleryFound = true;
                    break;
                }
                curr = curr.parentElement;
            }

            if (!galleryFound && fallbackUrls.length > 0) {
                for (const u of fallbackUrls) {
                    if (!result.gallery.includes(u)) {
                        result.gallery.push(u);
                    }
                }
                galleryFound = true;
            }

            if (!galleryFound && curr) {
                const parentSection = curr.closest('.page-product__briefing, .product-briefing, [class*="briefing"]');
                if (parentSection && !isExcluded(parentSection)) {
                    const divs = parentSection.querySelectorAll('div');
                    for (const d of divs) {
                        if (isExcluded(d)) continue;
                        const candidateUrls = getMediaUrls(d);
                        if (candidateUrls.length >= 2) {
                            for (const u of candidateUrls) {
                                if (!result.gallery.includes(u)) {
                                    result.gallery.push(u);
                                }
                            }
                            if (result.gallery.length >= 2) break;
                        }
                    }
                }
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
            if (isExcluded(img)) continue;
            const u = extractMediaUrl(img.src) || extractMediaUrl(img.getAttribute('data-src'));
            if (u) {
                result.variants.push({ url: u, label: label || null });
            }
        }
    }

    // PRIORITY 3: Seller Description Media
    const descContainers = document.querySelectorAll(
        '.product-detail, .product-description, [class*="product-detail"], [class*="product-description"]'
    );
    for (const container of descContainers) {
        if (isExcluded(container)) continue;
        const urls = getMediaUrls(container);
        for (const u of urls) {
            if (!result.description_media.includes(u)) {
                result.description_media.push(u);
            }
        }
        if (!result.structured.description) {
            const descText = container.innerText.trim();
            if (descText) {
                result.structured.description = descText;
            }
        }
    }

    // PRIORITY 4: Bounded Platform-Scoped Fallback (within known product briefing container only)
    // NEVER scans generic 'section' or unanchored page elements
    if (result.structured.images.length === 0 && result.gallery.length === 0) {
        const briefingContainers = document.querySelectorAll(
            '.page-product__briefing, .product-briefing, [class*="product-briefing"], [class*="page-product__briefing"]'
        );
        for (const container of briefingContainers) {
            if (isExcluded(container)) continue;
            const urls = getMediaUrls(container);
            let count = 0;
            for (const u of urls) {
                if (count >= 10) break;
                if (!result.fallback_media.includes(u)) {
                    result.fallback_media.push(u);
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
        structured_matches = (structured.get("product_id") == product_id)

        # Priority 1: Structured Product Data (ONLY when identity matches target product)
        if structured_matches:
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

        # Fail closed when no trusted media could be accepted
        if not media_items:
            raise SourcePackExtractionError(
                f"No trusted seller-product media could be extracted for Shopee product {product_id} ({product_url})"
            )

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

        # Gate structured-derived title, brand, description behind verified identity
        title = structured.get("title") if structured_matches else None
        brand = structured.get("brand") if structured_matches else None
        description = structured.get("description") if structured_matches else None
        model_sku = structured.get("model_sku") if structured_matches else None

        if structured_matches and brand:
            facts.append(
                ProductFact(
                    key="Brand",
                    value=brand,
                    source_section="structured_data",
                    provenance="structured_data",
                )
            )

        return ProductSourcePack(
            source_pack_id=source_pack_id,
            platform="shopee",
            product_url=product_url,
            observed_at=observed_at,
            collector=self.collector_name,
            title=title,
            source_product_id=product_id,
            shop_name=structured.get("shop_name") if structured_matches else None,
            brand=brand,
            model_sku=model_sku,
            description_text=description,
            facts=tuple(facts),
            media=tuple(media_items),
        )
