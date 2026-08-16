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

    async def navigate(self, url: str, **kwargs: Any) -> None:
        self.navigated_url = url

    async def evaluate(self, script: str, *args: Any) -> Any:
        self.evaluated_script = script
        if self.raise_on_eval:
            raise RuntimeError("Browser session evaluate failed")
        return self.evaluate_data


class FakeBrowserManager:
    def __init__(self, session: FakeSession):
        self._session = session

    async def get_or_create_session(self, **kwargs: Any) -> FakeSession:
        return self._session


@pytest.mark.asyncio
async def test_shopee_extractor_prefers_structured_data():
    """Structured product images preferred with STRUCTURED_PRODUCT_DATA provenance."""
    eval_data = {
        "structured": {
            "title": "Shopee Official Product",
            "images": ["https://cf.shopee.vn/file/struct1.jpg", "https://cf.shopee.vn/file/struct2.jpg"],
            "brand": "Anker",
            "description": "Detailed product description",
            "specs": [{"name": "Weight", "value": "200g"}],
        },
        "gallery": ["https://cf.shopee.vn/file/gallery1.jpg"],
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

    # Verify structured media
    assert len(pack.media) >= 2
    assert pack.media[0].source_url == "https://cf.shopee.vn/file/struct1.jpg"
    assert pack.media[0].provenance == MediaProvenance.STRUCTURED_PRODUCT_DATA
    assert pack.media[0].role == MediaRole.PRIMARY

    # Verify facts
    assert len(pack.facts) >= 2
    spec_fact = next((f for f in pack.facts if f.key == "Weight"), None)
    assert spec_fact is not None
    assert spec_fact.value == "200g"
    assert spec_fact.source_section == "specification_table"


@pytest.mark.asyncio
async def test_shopee_extractor_gallery_fallback_when_no_structured_images():
    """Gallery fallback collects gallery images when structured images missing."""
    eval_data = {
        "structured": {
            "title": "Shopee Gallery Product",
            "images": [],
            "brand": None,
            "specs": [],
        },
        "gallery": ["https://cf.shopee.vn/file/gal1.jpg", "https://cf.shopee.vn/file/gal2.jpg"],
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
            "images": ["https://cf.shopee.vn/file/main.jpg"],
            "specs": [],
        },
        "gallery": [],
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
async def test_shopee_extractor_invalid_url_raises_extraction_error():
    """URL without product ID raises SourcePackExtractionError."""
    session = FakeSession({})
    extractor = ShopeeSourceExtractor(browser=session)

    with pytest.raises(SourcePackExtractionError):
        await extractor.extract("https://shopee.vn/invalid-url-pattern")


@pytest.mark.asyncio
async def test_shopee_extractor_with_browser_manager():
    """Extractor works with BrowserManager interface (get_or_create_session)."""
    eval_data = {
        "structured": {
            "title": "Product with Manager",
            "images": ["https://cf.shopee.vn/file/img.jpg"],
            "specs": [],
        },
        "gallery": [],
        "description_media": [],
        "fallback_media": [],
        "blocked": False,
    }
    session = FakeSession(eval_data)
    manager = FakeBrowserManager(session)
    extractor = ShopeeSourceExtractor(browser=manager)

    pack = await extractor.extract("https://shopee.vn/product/100/200")
    assert pack.title == "Product with Manager"
    assert session.navigated_url == "https://shopee.vn/product/100/200"


@pytest.mark.asyncio
async def test_shopee_js_script_excludes_reviews_by_container_provenance():
    """The JS extraction script must contain explicit review/UGC exclusions."""
    session = FakeSession({
        "structured": {"title": "Test", "images": []},
        "gallery": [],
        "description_media": [],
        "fallback_media": [],
    })
    extractor = ShopeeSourceExtractor(browser=session)
    await extractor.extract("https://shopee.vn/product/1/2")

    script = session.evaluated_script
    assert script is not None
    # Verify exclusions in JS script
    assert "product-ratings" in script
    assert "product-reviews" in script
    assert "shop-review" in script
    assert "similar-products" in script
    assert "recommend" in script
