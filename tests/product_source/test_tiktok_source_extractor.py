from __future__ import annotations

from typing import Any, Dict, Optional
import pytest

from src.product_source.models import (
    MediaProvenance,
    MediaRole,
    SourcePackBlockedError,
    SourcePackExtractionError,
)
from src.product_source.platforms.tiktok import TikTokSourceExtractor


class FakeSession:
    def __init__(self, evaluate_data: Optional[Dict[str, Any]] = None, raise_on_eval: bool = False):
        self.evaluate_data = evaluate_data
        self.raise_on_eval = raise_on_eval
        self.navigated_url = None
        self.evaluated_script = None
        self.evaluated_args = None

    async def navigate(self, url: str, **kwargs: Any) -> None:
        self.navigated_url = url

    async def evaluate(self, script: str, *args: Any) -> Any:
        self.evaluated_script = script
        self.evaluated_args = args
        if self.raise_on_eval:
            raise RuntimeError("Browser session evaluate failed")
        return self.evaluate_data


class StrictFakeBrowserManager:
    """Fake browser manager strictly enforcing get_or_create_session(run_id: str, ...)."""
    def __init__(self, session: FakeSession):
        self._session = session
        self.received_run_id = None

    async def get_or_create_session(self, run_id: str, config: Optional[Any] = None) -> FakeSession:
        if not isinstance(run_id, str) or not run_id.strip():
            raise TypeError("run_id must be a non-empty string")
        self.received_run_id = run_id
        return self._session


@pytest.mark.asyncio
async def test_tiktok_extractor_prefers_structured_data_when_identity_matches():
    """Structured product images preferred in TikTok extractor when product ID matches."""
    eval_data = {
        "structured": {
            "title": "TikTok Trend Product",
            "product_id": "17294829102938",
            "images": ["https://p16-oec-va.ibyteimg.com/tos-maliva-i-o3syd03w52-us/img1.jpg"],
            "brand": "TrendCo",
            "shop_name": "TrendShop",
            "description": "Viral item description",
            "specifications": [{"name": "Material", "value": "Cotton"}],
        },
        "gallery_images": ["https://p16-oec-va.ibyteimg.com/gallery.jpg"],
        "variants": [],
        "seller_images": ["https://p16-oec-va.ibyteimg.com/desc.jpg"],
        "fallback_images": [],
        "blocked": False,
    }
    session = FakeSession(eval_data)
    extractor = TikTokSourceExtractor(browser=session)

    pack = await extractor.extract("https://www.tiktok.com/view/product/17294829102938")

    assert pack.platform == "tiktok"
    assert pack.source_product_id == "17294829102938"
    assert pack.source_pack_id == "tiktok_17294829102938"
    assert pack.title == "TikTok Trend Product"
    assert pack.brand == "TrendCo"
    assert pack.shop_name == "TrendShop"

    assert len(pack.media) >= 1
    assert pack.media[0].source_url == "https://p16-oec-va.ibyteimg.com/tos-maliva-i-o3syd03w52-us/img1.jpg"
    assert pack.media[0].provenance == MediaProvenance.STRUCTURED_PRODUCT_DATA
    assert pack.media[0].role == MediaRole.PRIMARY


@pytest.mark.asyncio
async def test_tiktok_extractor_rejects_unrelated_structured_data_on_identity_mismatch():
    """Structured data from unrelated recommendation with mismatched ID is rejected for BOTH media and title/brand/shop."""
    eval_data = {
        "structured": {
            "title": "Unrelated TikTok Recommendation",
            "product_id": "999888777",  # Mismatched ID
            "images": ["https://p16-oec-va.ibyteimg.com/unrelated.jpg"],
            "brand": "UnrelatedBrand",
            "shop_name": "UnrelatedShop",
            "description": "Unrelated desc",
            "specifications": [{"name": "UnrelatedSpec", "value": "Bad"}],
        },
        "gallery_images": ["https://p16-oec-va.ibyteimg.com/real_gallery.jpg"],
        "variants": [],
        "seller_images": [],
        "fallback_images": [],
        "blocked": False,
        "page_title": "Fallback Page Title | TikTok",
    }
    session = FakeSession(eval_data)
    extractor = TikTokSourceExtractor(browser=session)

    pack = await extractor.extract("https://www.tiktok.com/view/product/17294829102938")

    # Mismatched structured media rejected -> falls back to real gallery images
    assert len(pack.media) == 1
    assert pack.media[0].source_url == "https://p16-oec-va.ibyteimg.com/real_gallery.jpg"
    assert pack.media[0].provenance == MediaProvenance.SEMANTIC_PRODUCT_GALLERY

    # Unrelated structured metadata is discarded
    assert pack.title == "Fallback Page Title"
    assert pack.brand is None
    assert pack.shop_name is None
    assert pack.description_text is None
    assert not any(f.key == "Brand" and f.value == "UnrelatedBrand" for f in pack.facts)


@pytest.mark.asyncio
async def test_tiktok_extractor_fails_closed_when_no_media_found():
    """Exhausting all extraction paths without media raises SourcePackExtractionError."""
    eval_data = {
        "structured": {"title": "No Media Product", "product_id": "17294829102938", "images": []},
        "gallery_images": [],
        "variants": [],
        "seller_images": [],
        "fallback_images": [],
        "blocked": False,
    }
    session = FakeSession(eval_data)
    extractor = TikTokSourceExtractor(browser=session)

    with pytest.raises(SourcePackExtractionError, match="No trusted seller-product media"):
        await extractor.extract("https://www.tiktok.com/view/product/17294829102938")


@pytest.mark.asyncio
async def test_tiktok_extractor_collects_explicit_variants():
    """Variant images are collected with MediaRole.VARIANT and SEMANTIC_VARIANT_MEDIA."""
    eval_data = {
        "structured": {
            "title": "TikTok Variant Product",
            "product_id": "1234567",
            "images": ["https://p16-oec-va.ibyteimg.com/main.jpg"],
            "specifications": [],
        },
        "gallery_images": [],
        "variants": [
            {"url": "https://p16-oec-va.ibyteimg.com/var_blue.jpg", "label": "Blue / L"},
            {"url": "https://p16-oec-va.ibyteimg.com/var_red.jpg", "label": "Red / M"},
        ],
        "seller_images": [],
        "fallback_images": [],
        "blocked": False,
    }
    session = FakeSession(eval_data)
    extractor = TikTokSourceExtractor(browser=session)

    pack = await extractor.extract("https://www.tiktok.com/view/product/1234567")

    variants = [m for m in pack.media if m.role == MediaRole.VARIANT]
    assert len(variants) == 2
    assert variants[0].provenance == MediaProvenance.SEMANTIC_VARIANT_MEDIA
    assert variants[0].variant_label == "Blue / L"
    assert variants[1].variant_label == "Red / M"


@pytest.mark.asyncio
async def test_tiktok_extractor_gallery_fallback():
    """Semantic gallery images extracted when structured images empty."""
    eval_data = {
        "structured": {
            "title": "TikTok Gallery Product",
            "product_id": "1234567",
            "images": [],
            "brand": None,
            "shop_name": None,
            "specifications": [],
        },
        "gallery_images": ["https://p16-oec-va.ibyteimg.com/gal1.jpg", "https://p16-oec-va.ibyteimg.com/gal2.jpg"],
        "variants": [],
        "seller_images": [],
        "fallback_images": [],
        "blocked": False,
    }
    session = FakeSession(eval_data)
    extractor = TikTokSourceExtractor(browser=session)

    pack = await extractor.extract("https://www.tiktok.com/view/product/1234567")
    assert len(pack.media) == 2
    assert pack.media[0].provenance == MediaProvenance.SEMANTIC_PRODUCT_GALLERY


@pytest.mark.asyncio
async def test_tiktok_extractor_with_strict_browser_manager():
    """Extractor works with real BrowserManager interface get_or_create_session(run_id)."""
    eval_data = {
        "structured": {
            "title": "TikTok Manager Product",
            "product_id": "888999",
            "model_sku": "SKU-888",
            "images": ["https://p16-oec-va.ibyteimg.com/img.jpg"],
            "specifications": [],
        },
        "gallery_images": [],
        "variants": [],
        "seller_images": [],
        "fallback_images": [],
        "blocked": False,
    }
    session = FakeSession(eval_data)
    manager = StrictFakeBrowserManager(session)
    extractor = TikTokSourceExtractor(browser=manager)

    pack = await extractor.extract("https://www.tiktok.com/view/product/888999", run_id="tiktok_run_abc")
    assert pack.title == "TikTok Manager Product"
    assert pack.model_sku == "SKU-888"
    assert manager.received_run_id == "tiktok_run_abc"
    assert session.navigated_url == "https://www.tiktok.com/view/product/888999"


@pytest.mark.asyncio
async def test_tiktok_extractor_rejects_overlapping_substring_id():
    """Exact identity match rejects a product whose ID only overlaps as a substring."""
    eval_data = {
        "structured": {
            "title": "Overlapping ID Product",
            "product_id": "9123456",  # Target is 123456
            "images": ["https://p16-oec-va.ibyteimg.com/overlap.jpg"],
            "brand": "OverlapBrand",
            "model_sku": "SKU-OVERLAP",
            "specifications": [],
        },
        "gallery_images": ["https://p16-oec-va.ibyteimg.com/real_gallery.jpg"],
        "variants": [],
        "seller_images": [],
        "fallback_images": [],
        "blocked": False,
        "page_title": "Fallback Page Title | TikTok",
    }
    session = FakeSession(eval_data)
    extractor = TikTokSourceExtractor(browser=session)

    pack = await extractor.extract("https://www.tiktok.com/view/product/123456")

    # Mismatched overlapping ID rejected -> falls back to actual gallery images
    assert len(pack.media) == 1
    assert pack.media[0].source_url == "https://p16-oec-va.ibyteimg.com/real_gallery.jpg"
    assert pack.media[0].provenance == MediaProvenance.SEMANTIC_PRODUCT_GALLERY
    assert pack.title == "Fallback Page Title"
    assert pack.model_sku is None


@pytest.mark.asyncio
async def test_tiktok_js_script_excludes_reviews_and_no_main_article_fallback():
    """JS script contains review/UGC exclusions and does NOT use broad 'main' or 'article' selector."""
    session = FakeSession({
        "structured": {"title": "Test", "product_id": "123", "images": []},
        "gallery_images": ["https://p16-oec-va.ibyteimg.com/gal.jpg"],
        "variants": [],
        "seller_images": [],
        "fallback_images": [],
    })
    extractor = TikTokSourceExtractor(browser=session)
    await extractor.extract("https://www.tiktok.com/view/product/123")

    script = session.evaluated_script
    assert script is not None
    assert "review" in script
    assert "rating" in script
    assert "comment" in script
    assert "recommend" in script
    assert "main, article" not in script
    assert "main" not in script
    assert "article" not in script


@pytest.mark.asyncio
async def test_tiktok_extractor_does_not_block_on_globally_loaded_captcha_scripts():
    """Normal TikTok product page with globally loaded captcha scripts extracts successfully (blocked == False)."""
    eval_data = {
        "structured": {
            "title": "UVGREEN KA600",
            "product_id": "1729981094029264939",
            "images": ["https://p16-oec-sg.ibyteimg.com/main.webp"],
            "brand": "UVGREEN",
        },
        "gallery_images": ["https://p16-oec-sg.ibyteimg.com/gal1.webp"],
        "variants": [],
        "seller_images": [],
        "fallback_images": [],
        "blocked": False,
    }
    session = FakeSession(eval_data)
    extractor = TikTokSourceExtractor(browser=session)

    pack = await extractor.extract("https://www.tiktok.com/view/product/1729981094029264939")
    assert pack.title == "UVGREEN KA600"
    assert pack.source_product_id == "1729981094029264939"
    assert len(pack.media) >= 1


@pytest.mark.asyncio
async def test_tiktok_extractor_raises_blocked_on_active_challenge():
    """Extractor raises SourcePackBlockedError when active captcha/challenge is encountered."""
    eval_data = {
        "structured": {"title": None, "product_id": None, "images": []},
        "gallery_images": [],
        "variants": [],
        "seller_images": [],
        "fallback_images": [],
        "blocked": True,
    }
    session = FakeSession(eval_data)
    extractor = TikTokSourceExtractor(browser=session)

    with pytest.raises(SourcePackBlockedError, match="TikTok platform blocking detected"):
        await extractor.extract("https://www.tiktok.com/view/product/1729981094029264939")

