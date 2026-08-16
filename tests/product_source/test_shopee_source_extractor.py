from __future__ import annotations

from typing import Any, Dict, Optional
import pytest

from src.product_source.models import (
    MediaProvenance,
    MediaRole,
    SourcePackBlockedError,
    SourcePackExtractionError,
)
from src.product_source.platforms.shopee import ShopeeSourceExtractor


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
async def test_shopee_extractor_prefers_structured_data_when_identity_matches():
    """Structured product images and metadata preferred when product identity matches target product."""
    eval_data = {
        "structured": {
            "title": "Shopee Official Product",
            "product_id": "456789",
            "images": ["https://cf.shopee.vn/file/struct1.jpg", "https://cf.shopee.vn/file/struct2.jpg"],
            "brand": "Anker",
            "description": "Detailed product description",
            "specs": [{"name": "Weight", "value": "200g"}],
        },
        "gallery": ["https://cf.shopee.vn/file/gallery1.jpg"],
        "variants": [],
        "description_media": ["https://cf.shopee.vn/file/desc1.jpg"],
        "fallback_media": [],
        "blocked": False,
    }
    session = FakeSession(eval_data)
    extractor = ShopeeSourceExtractor(browser=session)

    pack = await extractor.extract("https://shopee.vn/product/123/456789")

    assert pack.platform == "shopee"
    assert pack.source_product_id == "456789"
    assert pack.source_pack_id == "shopee_456789"
    assert pack.title == "Shopee Official Product"
    assert pack.brand == "Anker"
    assert pack.description_text == "Detailed product description"

    assert len(pack.media) >= 2
    assert pack.media[0].source_url == "https://cf.shopee.vn/file/struct1.jpg"
    assert pack.media[0].provenance == MediaProvenance.STRUCTURED_PRODUCT_DATA
    assert pack.media[0].role == MediaRole.PRIMARY


@pytest.mark.asyncio
async def test_shopee_extractor_rejects_unrelated_structured_data_on_identity_mismatch():
    """Structured data from unrelated recommendation with different ID is rejected for BOTH media and title/brand."""
    eval_data = {
        "structured": {
            "title": "Unrelated Recommended Product",
            "product_id": "999999",  # Mismatched ID
            "images": ["https://cf.shopee.vn/file/unrelated_recommendation.jpg"],
            "brand": "UnrelatedBrand",
            "description": "Unrelated desc",
            "specs": [],
        },
        "gallery": ["https://cf.shopee.vn/file/actual_gallery.jpg"],
        "variants": [],
        "description_media": [],
        "fallback_media": [],
        "blocked": False,
    }
    session = FakeSession(eval_data)
    extractor = ShopeeSourceExtractor(browser=session)

    pack = await extractor.extract("https://shopee.vn/product/123/456789")

    # Mismatched structured images rejected -> falls back to actual gallery images
    assert len(pack.media) == 1
    assert pack.media[0].source_url == "https://cf.shopee.vn/file/actual_gallery.jpg"
    assert pack.media[0].provenance == MediaProvenance.SEMANTIC_PRODUCT_GALLERY

    # Unrelated structured title, brand, description are discarded
    assert pack.title is None
    assert pack.brand is None
    assert pack.description_text is None
    assert not any(f.key == "Brand" and f.value == "UnrelatedBrand" for f in pack.facts)


@pytest.mark.asyncio
async def test_shopee_extractor_fails_closed_when_no_media_found():
    """Exhausting all extraction paths without media raises SourcePackExtractionError."""
    eval_data = {
        "structured": {"title": "No Media Product", "product_id": "456789", "images": []},
        "gallery": [],
        "variants": [],
        "description_media": [],
        "fallback_media": [],
        "blocked": False,
    }
    session = FakeSession(eval_data)
    extractor = ShopeeSourceExtractor(browser=session)

    with pytest.raises(SourcePackExtractionError, match="No trusted seller-product media"):
        await extractor.extract("https://shopee.vn/product/123/456789")


@pytest.mark.asyncio
async def test_shopee_extractor_collects_explicit_variants():
    """Variant images are collected with MediaRole.VARIANT and SEMANTIC_VARIANT_MEDIA."""
    eval_data = {
        "structured": {
            "title": "Shopee Variant Product",
            "product_id": "456789",
            "images": ["https://cf.shopee.vn/file/main.jpg"],
            "specs": [],
        },
        "gallery": [],
        "variants": [
            {"url": "https://cf.shopee.vn/file/variant_black.jpg", "label": "Black / 128GB"},
            {"url": "https://cf.shopee.vn/file/variant_white.jpg", "label": "White / 256GB"},
        ],
        "description_media": [],
        "fallback_media": [],
        "blocked": False,
    }
    session = FakeSession(eval_data)
    extractor = ShopeeSourceExtractor(browser=session)

    pack = await extractor.extract("https://shopee.vn/product/123/456789")

    variant_media = [m for m in pack.media if m.role == MediaRole.VARIANT]
    assert len(variant_media) == 2
    assert variant_media[0].provenance == MediaProvenance.SEMANTIC_VARIANT_MEDIA
    assert variant_media[0].variant_label == "Black / 128GB"
    assert variant_media[1].variant_label == "White / 256GB"


@pytest.mark.asyncio
async def test_shopee_extractor_gallery_fallback_when_no_structured_images():
    """Gallery fallback collects gallery images when structured images missing."""
    eval_data = {
        "structured": {
            "title": "Shopee Gallery Product",
            "product_id": "456789",
            "images": [],
            "brand": None,
            "specs": [],
        },
        "gallery": ["https://cf.shopee.vn/file/gal1.jpg", "https://cf.shopee.vn/file/gal2.jpg"],
        "variants": [],
        "description_media": [],
        "fallback_media": [],
        "blocked": False,
    }
    session = FakeSession(eval_data)
    extractor = ShopeeSourceExtractor(browser=session)

    pack = await extractor.extract("https://shopee.vn/product/123/456789")
    assert len(pack.media) == 2
    assert pack.media[0].source_url == "https://cf.shopee.vn/file/gal1.jpg"
    assert pack.media[0].provenance == MediaProvenance.SEMANTIC_PRODUCT_GALLERY


@pytest.mark.asyncio
async def test_shopee_extractor_seller_description_media_labeled():
    """Seller description media is separately labeled SELLER_DESCRIPTION."""
    eval_data = {
        "structured": {
            "title": "Shopee Desc Product",
            "product_id": "456789",
            "images": ["https://cf.shopee.vn/file/main.jpg"],
            "specs": [],
        },
        "gallery": [],
        "variants": [],
        "description_media": ["https://cf.shopee.vn/file/seller_desc.jpg"],
        "fallback_media": [],
        "blocked": False,
    }
    session = FakeSession(eval_data)
    extractor = ShopeeSourceExtractor(browser=session)

    pack = await extractor.extract("https://shopee.vn/product/123/456789")
    desc_media = next((m for m in pack.media if m.role == MediaRole.SELLER_DESCRIPTION), None)
    assert desc_media is not None
    assert desc_media.source_url == "https://cf.shopee.vn/file/seller_desc.jpg"
    assert desc_media.provenance == MediaProvenance.SEMANTIC_SELLER_DESCRIPTION


@pytest.mark.asyncio
async def test_shopee_extractor_raises_blocked_on_captcha():
    """Anti-bot verification triggers SourcePackBlockedError."""
    eval_data = {
        "blocked": True,
    }
    session = FakeSession(eval_data)
    extractor = ShopeeSourceExtractor(browser=session)

    with pytest.raises(SourcePackBlockedError):
        await extractor.extract("https://shopee.vn/product/123/456789")


@pytest.mark.asyncio
async def test_shopee_extractor_with_strict_browser_manager():
    """Extractor works with real BrowserManager interface get_or_create_session(run_id)."""
    eval_data = {
        "structured": {
            "title": "Product with Manager",
            "product_id": "200",
            "images": ["https://cf.shopee.vn/file/img.jpg"],
            "specs": [],
        },
        "gallery": [],
        "variants": [],
        "description_media": [],
        "fallback_media": [],
        "blocked": False,
    }
    session = FakeSession(eval_data)
    manager = StrictFakeBrowserManager(session)
    extractor = ShopeeSourceExtractor(browser=manager)

    pack = await extractor.extract("https://shopee.vn/product/100/200", run_id="custom_run_shopee")
    assert pack.title == "Product with Manager"
    assert manager.received_run_id == "custom_run_shopee"
    assert session.navigated_url == "https://shopee.vn/product/100/200"


@pytest.mark.asyncio
async def test_shopee_js_script_excludes_reviews_by_container_provenance():
    """The JS extraction script must contain explicit review/UGC exclusions."""
    session = FakeSession({
        "structured": {"title": "Test", "product_id": "2", "images": []},
        "gallery": ["https://cf.shopee.vn/file/gal.jpg"],
        "variants": [],
        "description_media": [],
        "fallback_media": [],
    })
    extractor = ShopeeSourceExtractor(browser=session)
    await extractor.extract("https://shopee.vn/product/1/2")

    script = session.evaluated_script
    assert script is not None
    assert "product-ratings" in script
    assert "product-reviews" in script
    assert "shop-review" in script
    assert "similar-products" in script
    assert "recommend" in script
