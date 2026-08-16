from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set

from src.product_source.models import (
    MediaRole,
    MediaProvenance,
    ProductFact,
    OriginalMediaRef,
    build_source_pack_id,
    ProductSourcePack,
    SourcePackExtractionError,
    SourcePackBlockedError,
)
from src.product_intelligence.adapters.shopee_parsing import extract_shopee_product_id

class ShopeeSourceExtractor:
    """Extracts product source pack from Shopee product pages."""

    def __init__(self, browser: Optional[Any] = None, *, collector_name: str = 'shopee_source_v1') -> None:
        self.browser = browser
        self.collector_name = collector_name

    async def _acquire_page(self, url: str) -> Any:
        page = None
        if hasattr(self.browser, "get_or_create_session"):
            page = await self.browser.get_or_create_session()
        elif hasattr(self.browser, "new_page"):
            page = await self.browser.new_page()
        elif callable(self.browser):
            page = await self.browser()
        elif hasattr(self.browser, "navigate") and hasattr(self.browser, "evaluate"):
            page = self.browser
        else:
            page = self.browser
        
        await page.navigate(url)
        return page

    async def extract(self, product_url: str, *, observed_at: Optional[datetime] = None) -> ProductSourcePack:
        product_id = extract_shopee_product_id(product_url)
        if not product_id:
            raise SourcePackExtractionError(f"Failed to extract product ID from {product_url}")

        if observed_at is None:
            observed_at = datetime.now()

        try:
            page = await self._acquire_page(product_url)
        except Exception as e:
            raise SourcePackExtractionError(f"Failed to acquire page: {e}") from e

        js_script = """
        () => {
            const result = {
                structured: { title: null, price: null, brand: null, shop_name: null, images: [], description: null, specs: [] },
                gallery: [],
                description_media: [],
                fallback_media: [],
                blocked: false
            };

            if (document.querySelector('.shopee-captcha') || document.body.innerHTML.includes('verify.shopee')) {
                result.blocked = true;
                return result;
            }

            // Priority 1: Structured Data
            const ldJsonScripts = document.querySelectorAll('script[type="application/ld+json"]');
            for (const script of ldJsonScripts) {
                try {
                    const data = JSON.parse(script.textContent);
                    if (data['@type'] === 'Product') {
                        if (data.name) result.structured.title = data.name;
                        if (data.image) {
                            if (Array.isArray(data.image)) {
                                result.structured.images = data.image;
                            } else if (typeof data.image === 'string') {
                                result.structured.images = [data.image];
                            }
                        }
                        if (data.description) result.structured.description = data.description;
                        if (data.brand && data.brand.name) result.structured.brand = data.brand.name;
                        if (data.offers && data.offers.price) result.structured.price = data.offers.price;
                    }
                } catch (e) {}
            }

            const nextDataScript = document.querySelector('#__NEXT_DATA__');
            if (nextDataScript) {
                try {
                    const data = JSON.parse(nextDataScript.textContent);
                    // Add __NEXT_DATA__ parsing if needed
                } catch (e) {}
            }

            // Product specs from the page
            const specRows = document.querySelectorAll('.product-detail .kIo6pj, .product-detail .rY0UiC, .product-detail .flex.items-center');
            for (const row of specRows) {
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
                if (attrLabels.length === attrValues.length) {
                    for(let i=0; i<attrLabels.length; i++) {
                        result.structured.specs.push({ name: attrLabels[i].innerText.trim(), value: attrValues[i].innerText.trim()});
                    }
                }
            }

            const isExcluded = (element) => {
                const excludedSelectors = [
                    '.product-ratings', '.product-reviews', '[data-sqe="rating"]',
                    '.shop-review', '.comment', '.review-images',
                    '.similar-products', '.recommend', '.you-may-like'
                ];
                if (element.closest(excludedSelectors.join(', '))) {
                    return true;
                }
                let curr = element;
                while (curr) {
                    if (curr.className && typeof curr.className === 'string') {
                        const c = curr.className.toLowerCase();
                        if (c.includes('review') || c.includes('rating') || c.includes('comment')) {
                            return true;
                        }
                    }
                    curr = curr.parentElement;
                }
                return false;
            };

            // Priority 2: Semantic Product Gallery
            const galleryContainers = document.querySelectorAll('.product-image-carousel, .product-image__content, .V9sV-Q, .xNIlvG');
            for (const container of galleryContainers) {
                if (isExcluded(container)) continue;
                const imgs = container.querySelectorAll('img');
                for (const img of imgs) {
                    if (img.src && !isExcluded(img)) {
                        result.gallery.push(img.src);
                    }
                }
            }

            // Priority 3: Seller Description Media
            const descriptionContainers = document.querySelectorAll('.product-detail, .product-description, .page-product__description');
            for (const container of descriptionContainers) {
                if (isExcluded(container)) continue;
                const imgs = container.querySelectorAll('img');
                for (const img of imgs) {
                    if (img.src && !isExcluded(img)) {
                        result.description_media.push(img.src);
                    }
                }
                if (!result.structured.description) {
                    const descText = container.innerText;
                    if (descText) {
                        result.structured.description = descText;
                    }
                }
            }

            // Priority 4: Platform Scoped Fallback
            const briefingContainers = document.querySelectorAll('.page-product__briefing, .product-briefing');
            for (const container of briefingContainers) {
                if (isExcluded(container)) continue;
                const imgs = container.querySelectorAll('img');
                let count = 0;
                for (const img of imgs) {
                    if (count >= 10) break;
                    if (img.src && !isExcluded(img)) {
                        result.fallback_media.push(img.src);
                        count++;
                    }
                }
            }

            return result;
        }
        """

        try:
            data = await page.evaluate(js_script)
        except Exception as e:
            raise SourcePackExtractionError(f"Failed to evaluate extraction script: {e}") from e

        if not data:
            raise SourcePackExtractionError("Extraction returned no data")

        if data.get('blocked'):
            raise SourcePackBlockedError("Shopee anti-bot verification or captcha detected")

        source_pack_id = build_source_pack_id("shopee", product_id, product_url)
        
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
                    platform="shopee",
                    role=role,
                    provenance=provenance,
                    ordinal=ordinal
                )
            )
            ordinal += 1

        structured = data.get('structured', {})

        # Priority 1: Structured
        for url in structured.get('images', []):
            add_media(url, MediaRole.PRIMARY, MediaProvenance.STRUCTURED_PRODUCT_DATA)

        # Priority 2: Gallery
        for url in data.get('gallery', []):
            role = MediaRole.PRIMARY if not media_items else MediaRole.GALLERY
            add_media(url, role, MediaProvenance.SEMANTIC_PRODUCT_GALLERY)

        # Priority 3: Seller Description
        for url in data.get('description_media', []):
            add_media(url, MediaRole.SELLER_DESCRIPTION, MediaProvenance.SEMANTIC_SELLER_DESCRIPTION)

        # Priority 4: Fallback
        for url in data.get('fallback_media', []):
            add_media(url, MediaRole.GALLERY, MediaProvenance.PLATFORM_SCOPED_FALLBACK)

        facts: List[ProductFact] = []
        for spec in structured.get('specs', []):
            facts.append(
                ProductFact(
                    key=spec.get('name', ''),
                    value=spec.get('value', ''),
                    source_section="specification_table",
                    provenance="specification_table"
                )
            )

        if structured.get('brand'):
            facts.append(
                ProductFact(
                    key="Brand",
                    value=structured['brand'],
                    source_section="structured_data",
                    provenance="structured_data"
                )
            )

        description = structured.get('description')

        return ProductSourcePack(
            source_pack_id=source_pack_id,
            platform="shopee",
            product_url=product_url,
            observed_at=observed_at,
            collector=self.collector_name,
            title=structured.get('title'),
            source_product_id=product_id,
            shop_name=structured.get('shop_name'),
            brand=structured.get('brand'),
            description_text=description,
            facts=tuple(facts),
            media=tuple(media_items)
        )
