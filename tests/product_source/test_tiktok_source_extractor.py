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
async def test_tiktok_extractor_prefers_structured_data():
    """Structured product images preferred in TikTok extractor."""
    eval_data = {
        "structured": {
            "title": "TikTok Trend Product",
            "images": ["https://p16-oec-va.ibyteimg.com/tos-maliva-i-o3syd03w52-us/img1.jpg"],
            "brand": "TrendCo",
            "shop_name": "TrendShop",
            "description": "Viral item description",
            "specifications": [{"name": "Material", "value": "Cotton"}],
        },
        "gallery_images": ["https://p16-oec-va.ibyteimg.com/gallery.jpg"],
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

    # Verify structured media
    assert len(pack.media) >= 1
    assert pack.media[0].source_url == "https://p16-oec-va.ibyteimg.com/tos-maliva-i-o3syd03w52-us/img1.jpg"
    assert pack.media[0].provenance == MediaProvenance.STRUCTURED_PRODUCT_DATA
    assert pack.media[0].role == MediaRole.PRIMARY

    # Verify facts
    assert len(pack.facts) >= 2
    mat_fact = next((f for f in pack.facts if f.key == "Material"), None)
    assert mat_fact is not None
    assert mat_fact.value == "Cotton"


@pytest.mark.asyncio
async def test_tiktok_extractor_gallery_fallback():
    """Semantic gallery images extracted when structured images empty."""
    eval_data = {
        "structured": {
            "title": "TikTok Gallery Product",
            "images": [],
            "brand": None,
            "shop_name": None,
            "specifications": [],
        },
        "gallery_images": ["https://p16-oec-va.ibyteimg.com/gal1.jpg", "https://p16-oec-va.ibyteimg.com/gal2.jpg"],
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
async def test_tiktok_extractor_seller_description_media():
    """Seller description images labeled with SELLER_DESCRIPTION role."""
    eval_data = {
        "structured": {
            "title": "TikTok Desc Product",
            "images": ["https://p16-oec-va.ibyteimg.com/main.jpg"],
            "specifications": [],
        },
        "gallery_images": [],
        "seller_images": ["https://p16-oec-va.ibyteimg.com/seller_img.jpg"],
        "fallback_images": [],
        "blocked": False,
    }
    session = FakeSession(eval_data)
    extractor = TikTokSourceExtractor(browser=session)

    pack = await extractor.extract("https://www.tiktok.com/view/product/1234567")
    desc_media = next((m for m in pack.media if m.role == MediaRole.SELLER_DESCRIPTION), None)
    assert desc_media is not None
    assert desc_media.provenance == MediaProvenance.SEMANTIC_SELLER_DESCRIPTION


@pytest.mark.asyncio
async def test_tiktok_extractor_raises_blocked_on_captcha():
    """Captcha detection triggers SourcePackBlockedError."""
    eval_data = {
        "blocked": True,
    }
    session = FakeSession(eval_data)
    extractor = TikTokSourceExtractor(browser=session)

    with pytest.raises(SourcePackBlockedError):
        await extractor.extract("https://www.tiktok.com/view/product/1234567")


@pytest.mark.asyncio
async def test_tiktok_extractor_with_browser_manager():
    """Works with BrowserManager interface."""
    eval_data = {
        "structured": {
            "title": "TikTok Manager Product",
            "images": ["https://p16-oec-va.ibyteimg.com/img.jpg"],
            "specifications": [],
        },
        "gallery_images": [],
        "seller_images": [],
        "fallback_images": [],
        "blocked": False,
    }
    session = FakeSession(eval_data)
    manager = FakeBrowserManager(session)
    extractor = TikTokSourceExtractor(browser=manager)

    pack = await extractor.extract("https://www.tiktok.com/view/product/888999")
    assert pack.title == "TikTok Manager Product"
    assert session.navigated_url == "https://www.tiktok.com/view/product/888999"


@pytest.mark.asyncio
async def test_tiktok_js_script_excludes_reviews():
    """JS script contains review/UGC exclusions."""
    session = FakeSession({
        "structured": {"title": "Test", "images": []},
        "gallery_images": [],
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
    assert "ugc" in script
