from __future__ import annotations

from typing import Any, Dict, List, Optional
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
import pytest

from src.product_source.models import (
    MediaProvenance,
    MediaRole,
    ProductFact,
    SourcePackBlockedError,
    SourcePackExtractionError,
)
from src.product_intelligence.entity_resolution import (
    ProductRelationship,
    resolve_product_entities,
)
from src.product_source.platforms.shopee import ShopeeSourceExtractor
from src.product_source.platforms.shopee import _SHOPEE_EXTRACTION_SCRIPT
from src.integrations.playwright.manager import PlaywrightBrowserManager
import src.integrations.playwright.session as playwright_session_module


class FakeSession:
    def __init__(
        self,
        evaluate_data: Optional[Dict[str, Any]] = None,
        raise_on_eval: bool = False,
        *,
        evaluate_results: Optional[List[Any]] = None,
    ):
        self.evaluate_data = evaluate_data
        self.evaluate_results = list(evaluate_results) if evaluate_results is not None else None
        self.raise_on_eval = raise_on_eval
        self.navigated_url = None
        self.navigation_count = 0
        self.evaluate_count = 0
        self.evaluated_script = None
        self.evaluated_args = None

    async def navigate(self, url: str, **kwargs: Any) -> None:
        self.navigated_url = url
        self.navigation_count += 1

    async def evaluate(self, script: str, *args: Any) -> Any:
        self.evaluated_script = script
        self.evaluated_args = args
        result_index = self.evaluate_count
        self.evaluate_count += 1
        if self.raise_on_eval:
            raise RuntimeError("Browser session evaluate failed")
        if self.evaluate_results is not None:
            return self.evaluate_results[min(result_index, len(self.evaluate_results) - 1)]
        return self.evaluate_data


class StrictFakeBrowserManager:
    """Fake browser manager strictly enforcing get_or_create_session(run_id: str, ...)."""
    def __init__(self, session: FakeSession):
        self._session = session
        self.received_run_id = None
        self.acquisition_count = 0

    async def get_or_create_session(self, run_id: str, config: Optional[Any] = None) -> FakeSession:
        if not isinstance(run_id, str) or not run_id.strip():
            raise TypeError("run_id must be a non-empty string")
        self.received_run_id = run_id
        self.acquisition_count += 1
        return self._session


@pytest.fixture(autouse=True)
def no_real_readiness_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _instant_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr("src.product_source.platforms.shopee._readiness_sleep", _instant_sleep)


def _media_empty_sample() -> Dict[str, Any]:
    return {
        "structured": {"title": "Hydrating Product", "product_id": "456789", "images": []},
        "gallery": [],
        "variants": [],
        "description_media": [],
        "fallback_media": [],
        "blocked": False,
    }


def _ready_sample() -> Dict[str, Any]:
    return {
        "structured": {
            "title": "Hydrated Product",
            "product_id": "456789",
            "images": ["https://cf.shopee.vn/file/hydrated.jpg"],
            "specs": [],
        },
        "gallery": [],
        "variants": [],
        "description_media": [],
        "fallback_media": [],
        "blocked": False,
    }


@pytest.mark.asyncio
async def test_shopee_extractor_delayed_hydration_uses_one_acquisition_and_navigation(
    monkeypatch: pytest.MonkeyPatch,
):
    sleep_calls: List[float] = []

    async def _record_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr("src.product_source.platforms.shopee._readiness_sleep", _record_sleep)
    session = FakeSession(evaluate_results=[_media_empty_sample(), _media_empty_sample(), _ready_sample()])
    manager = StrictFakeBrowserManager(session)
    extractor = ShopeeSourceExtractor(browser=manager)

    pack = await extractor.extract("https://shopee.vn/product/123/456789", run_id="hydration-run")

    assert [item.source_url for item in pack.media] == ["https://cf.shopee.vn/file/hydrated.jpg"]
    assert manager.acquisition_count == 1
    assert session.navigation_count == 1
    assert session.evaluate_count == 3
    assert sleep_calls == [0.5, 0.5]
    assert session.evaluated_script == _SHOPEE_EXTRACTION_SCRIPT
    assert session.evaluated_args == ("456789",)


@pytest.mark.asyncio
async def test_shopee_extractor_first_ready_sample_terminates_immediately(
    monkeypatch: pytest.MonkeyPatch,
):
    sleep_calls: List[float] = []

    async def _record_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr("src.product_source.platforms.shopee._readiness_sleep", _record_sleep)
    session = FakeSession(evaluate_results=[_ready_sample(), _media_empty_sample()])

    pack = await ShopeeSourceExtractor(browser=session).extract("https://shopee.vn/product/123/456789")

    assert pack.title == "Hydrated Product"
    assert session.evaluate_count == 1
    assert session.navigation_count == 1
    assert sleep_calls == []


@pytest.mark.asyncio
async def test_shopee_extractor_delayed_blocked_state_terminates_immediately(
    monkeypatch: pytest.MonkeyPatch,
):
    sleep_calls: List[float] = []

    async def _record_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr("src.product_source.platforms.shopee._readiness_sleep", _record_sleep)
    session = FakeSession(
        evaluate_results=[_media_empty_sample(), {"blocked": True}, _ready_sample()]
    )

    with pytest.raises(SourcePackBlockedError):
        await ShopeeSourceExtractor(browser=session).extract("https://shopee.vn/product/123/456789")

    assert session.evaluate_count == 2
    assert session.navigation_count == 1
    assert sleep_calls == [0.5]


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
async def test_shopee_extractor_fails_closed_when_no_media_found(
    monkeypatch: pytest.MonkeyPatch,
):
    """Exhausting all extraction paths without media raises SourcePackExtractionError."""
    sleep_calls: List[float] = []

    async def _record_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr("src.product_source.platforms.shopee._readiness_sleep", _record_sleep)
    session = FakeSession(_media_empty_sample())
    extractor = ShopeeSourceExtractor(browser=session)

    with pytest.raises(SourcePackExtractionError, match="No trusted seller-product media"):
        await extractor.extract("https://shopee.vn/product/123/456789")

    assert session.evaluate_count == 10
    assert session.navigation_count == 1
    assert sleep_calls == [0.5] * 9


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_payload", [None, [], {}])
async def test_shopee_extractor_invalid_payload_fails_without_retry(
    invalid_payload: Any,
    monkeypatch: pytest.MonkeyPatch,
):
    sleep_calls: List[float] = []

    async def _record_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr("src.product_source.platforms.shopee._readiness_sleep", _record_sleep)
    session = FakeSession(evaluate_results=[invalid_payload, _ready_sample()])

    with pytest.raises(SourcePackExtractionError, match="invalid/empty data"):
        await ShopeeSourceExtractor(browser=session).extract("https://shopee.vn/product/123/456789")

    assert session.evaluate_count == 1
    assert session.navigation_count == 1
    assert sleep_calls == []


@pytest.mark.asyncio
async def test_shopee_extractor_evaluate_error_fails_without_retry(
    monkeypatch: pytest.MonkeyPatch,
):
    sleep_calls: List[float] = []

    async def _record_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr("src.product_source.platforms.shopee._readiness_sleep", _record_sleep)
    session = FakeSession(_ready_sample(), raise_on_eval=True)

    with pytest.raises(SourcePackExtractionError, match="Failed to evaluate Shopee extraction script"):
        await ShopeeSourceExtractor(browser=session).extract("https://shopee.vn/product/123/456789")

    assert session.evaluate_count == 1
    assert session.navigation_count == 1
    assert sleep_calls == []


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
            "model_sku": "SKU-200",
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
    assert pack.model_sku == "SKU-200"
    assert manager.received_run_id == "custom_run_shopee"
    assert session.navigated_url == "https://shopee.vn/product/100/200"


@pytest.mark.asyncio
async def test_shopee_extractor_forwards_product_id_through_real_playwright_wrapper(
    monkeypatch: pytest.MonkeyPatch,
):
    """The current manager/session wrapper preserves extractor script and arg semantics."""
    eval_data = {
        "structured": {
            "title": "Wrapped Product",
            "product_id": "200",
            "images": ["https://cf.shopee.vn/file/wrapped.jpg"],
            "specs": [],
        },
        "gallery": [],
        "variants": [],
        "description_media": [],
        "fallback_media": [],
        "blocked": False,
    }
    page = MagicMock()
    page.is_closed.return_value = False
    page.goto = AsyncMock()
    page.evaluate = AsyncMock(return_value=eval_data)
    context = MagicMock()
    context.pages = [page]
    browser = MagicMock()
    browser.contexts = [context]
    browser.is_connected.return_value = True
    chromium = MagicMock()
    chromium.connect_over_cdp = AsyncMock(return_value=browser)
    playwright = SimpleNamespace(chromium=chromium, stop=AsyncMock())
    starter = SimpleNamespace(start=AsyncMock(return_value=playwright))
    monkeypatch.setattr(
        playwright_session_module,
        "async_playwright",
        lambda: starter,
    )
    manager = PlaywrightBrowserManager(cdp_endpoint="http://127.0.0.1:9222")
    extractor = ShopeeSourceExtractor(browser=manager)

    pack = await extractor.extract(
        "https://shopee.vn/product/100/200",
        run_id="wrapped-shopee",
    )

    page.goto.assert_awaited_once_with(
        "https://shopee.vn/product/100/200",
        timeout=30000,
    )
    page.evaluate.assert_awaited_once_with(_SHOPEE_EXTRACTION_SCRIPT, "200")
    assert pack.source_product_id == "200"
    assert pack.title == "Wrapped Product"
    assert [item.source_url for item in pack.media] == [
        "https://cf.shopee.vn/file/wrapped.jpg"
    ]


@pytest.mark.asyncio
async def test_shopee_extractor_rejects_overlapping_substring_id():
    """Exact identity match rejects a product whose ID only overlaps as a substring."""
    eval_data = {
        "structured": {
            "title": "Overlapping ID Product",
            "product_id": "9123456",  # Target is 123456
            "images": ["https://cf.shopee.vn/file/overlap.jpg"],
            "brand": "OverlapBrand",
            "model_sku": "SKU-OVERLAP",
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

    pack = await extractor.extract("https://shopee.vn/product/100/123456")

    # Mismatched overlapping ID rejected -> falls back to actual gallery images
    assert len(pack.media) == 1
    assert pack.media[0].source_url == "https://cf.shopee.vn/file/actual_gallery.jpg"
    assert pack.media[0].provenance == MediaProvenance.SEMANTIC_PRODUCT_GALLERY
    assert pack.title is None
    assert pack.model_sku is None


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


@pytest.mark.asyncio
async def test_shopee_extractor_appends_selected_variant_facts_when_complete_and_identity_matched():
    """Complete identity-matched selected-variant state appends ordered ProductFact values."""
    eval_data = {
        "structured": {
            "title": "Shopee Multi-Variant Product",
            "product_id": "456789",
            "images": ["https://cf.shopee.vn/file/main.jpg"],
            "brand": "BrandX",
            "specs": [{"name": "Material", "value": "Cotton"}],
        },
        "gallery": [],
        "variants": [],
        "description_media": [],
        "fallback_media": [],
        "selected_variants": [
            {"group_label": "Màu sắc", "option_label": "Đen"},
            {"group_label": "Kích thước", "option_label": "XL"},
        ],
        "selected_variants_complete": True,
        "blocked": False,
    }
    session = FakeSession(eval_data)
    extractor = ShopeeSourceExtractor(browser=session)

    pack = await extractor.extract("https://shopee.vn/product/123/456789")

    # Facts prefix remains existing specification and brand facts in order
    assert pack.facts[0] == ProductFact(
        key="Material",
        value="Cotton",
        source_section="specification_table",
        provenance="specification_table",
    )
    assert pack.facts[1] == ProductFact(
        key="Brand",
        value="BrandX",
        source_section="structured_data",
        provenance="structured_data",
    )

    # Selected-variant facts appended strictly in group DOM order
    assert len(pack.facts) == 4
    v1, v2 = pack.facts[2], pack.facts[3]
    assert v1.key == "variant"
    assert v1.value == "Màu sắc: Đen"
    assert v1.source_section == "selected_variant_controls"
    assert v1.provenance == "selected_variant_controls"
    assert v1.unit is None

    assert v2.key == "variant"
    assert v2.value == "Kích thước: XL"
    assert v2.source_section == "selected_variant_controls"
    assert v2.provenance == "selected_variant_controls"
    assert v2.unit is None


@pytest.mark.asyncio
async def test_shopee_extractor_zero_variant_facts_on_identity_mismatch():
    """Structured identity mismatch produces zero selected-variant facts while pack extraction succeeds."""
    eval_data = {
        "structured": {
            "title": "Mismatched Product",
            "product_id": "999999",  # Does not match target 456789
            "images": ["https://cf.shopee.vn/file/unrelated.jpg"],
            "brand": "OtherBrand",
            "specs": [{"name": "Material", "value": "Silk"}],
        },
        "gallery": ["https://cf.shopee.vn/file/actual_gallery.jpg"],
        "variants": [],
        "description_media": [],
        "fallback_media": [],
        "selected_variants": [
            {"group_label": "Color", "option_label": "Blue"},
        ],
        "selected_variants_complete": True,
        "blocked": False,
    }
    session = FakeSession(eval_data)
    extractor = ShopeeSourceExtractor(browser=session)

    pack = await extractor.extract("https://shopee.vn/product/123/456789")

    # Gallery media extracted via fallback
    assert len(pack.media) == 1
    assert pack.media[0].source_url == "https://cf.shopee.vn/file/actual_gallery.jpg"

    # Zero selected-variant facts emitted because structured identity does not match
    variant_facts = [f for f in pack.facts if f.key == "variant"]
    assert len(variant_facts) == 0


@pytest.mark.asyncio
async def test_shopee_extractor_zero_variant_facts_on_incomplete_or_ambiguous_state():
    """Incomplete or ambiguous selected-variant state emits zero selected-variant facts."""
    eval_data = {
        "structured": {
            "title": "Product with Incomplete Variants",
            "product_id": "456789",
            "images": ["https://cf.shopee.vn/file/main.jpg"],
            "specs": [],
        },
        "gallery": [],
        "variants": [],
        "description_media": [],
        "fallback_media": [],
        "selected_variants": [],
        "selected_variants_complete": False,
        "blocked": False,
    }
    session = FakeSession(eval_data)
    extractor = ShopeeSourceExtractor(browser=session)

    pack = await extractor.extract("https://shopee.vn/product/123/456789")
    variant_facts = [f for f in pack.facts if f.key == "variant"]
    assert len(variant_facts) == 0


@pytest.mark.asyncio
async def test_shopee_extractor_url_model_query_params_produce_zero_variant_facts():
    """URL model query parameters without complete DOM proof produce zero selected-variant facts."""
    eval_data = {
        "structured": {
            "title": "URL Model Product",
            "product_id": "456789",
            "images": ["https://cf.shopee.vn/file/main.jpg"],
            "specs": [],
        },
        "gallery": [],
        "variants": [],
        "description_media": [],
        "fallback_media": [],
        "selected_variants": [],
        "selected_variants_complete": False,
        "blocked": False,
    }
    session = FakeSession(eval_data)
    extractor = ShopeeSourceExtractor(browser=session)

    url_with_model_params = (
        "https://shopee.vn/product/123/456789?rModelId=11111&vModelId=22222&display_model_id=33333"
    )
    pack = await extractor.extract(url_with_model_params)

    variant_facts = [f for f in pack.facts if f.key == "variant"]
    assert len(variant_facts) == 0
    assert pack.model_sku is None


@pytest.mark.asyncio
async def test_shopee_extractor_preserves_equal_option_labels_across_distinct_groups():
    """Distinct variation groups with identical option labels are preserved deterministically without deduplication."""
    eval_data = {
        "structured": {
            "title": "Shopee Multi-Tone Product",
            "product_id": "456789",
            "images": ["https://cf.shopee.vn/file/main.jpg"],
            "specs": [],
        },
        "gallery": [],
        "variants": [],
        "description_media": [],
        "fallback_media": [],
        "selected_variants": [
            {"group_label": "Primary Color", "option_label": "Red"},
            {"group_label": "Trim Color", "option_label": "Red"},
        ],
        "selected_variants_complete": True,
        "blocked": False,
    }
    session = FakeSession(eval_data)
    extractor = ShopeeSourceExtractor(browser=session)

    pack = await extractor.extract("https://shopee.vn/product/123/456789")
    variant_facts = [f for f in pack.facts if f.key == "variant"]
    assert len(variant_facts) == 2
    assert variant_facts[0].value == "Primary Color: Red"
    assert variant_facts[1].value == "Trim Color: Red"


@pytest.mark.asyncio
async def test_task_108_compatibility_same_listing_with_complete_variant_evidence():
    """Unchanged TASK-108 resolves EXACT_VARIANT_MATCH for same-listing observations carrying equal complete selected-variant evidence."""
    eval_data = {
        "structured": {
            "title": "Shopee Phone Listing",
            "product_id": "456789",
            "images": ["https://cf.shopee.vn/file/main.jpg"],
            "brand": "Acme",
            "specs": [],
        },
        "gallery": [],
        "variants": [],
        "description_media": [],
        "fallback_media": [],
        "selected_variants": [
            {"group_label": "Color", "option_label": "Black"},
        ],
        "selected_variants_complete": True,
        "blocked": False,
    }
    session = FakeSession(eval_data)
    extractor = ShopeeSourceExtractor(browser=session)

    pack1 = await extractor.extract("https://shopee.vn/product/123/456789")
    pack2 = await extractor.extract("https://shopee.vn/product/123/456789")

    result = resolve_product_entities(pack1, pack2)
    assert result.relationship is ProductRelationship.EXACT_VARIANT_MATCH
    assert result.confidence >= 0.95
    assert any(e.code == "VARIANT_MATCH" for e in result.evidence)


@pytest.mark.asyncio
async def test_task_108_compatibility_same_listing_differing_selected_option():
    """Unchanged TASK-108 resolves SAME_PRODUCT_FAMILY with VARIANT_CONFLICT when one selected option differs."""
    eval_data_black = {
        "structured": {
            "title": "Shopee Phone Listing",
            "product_id": "456789",
            "images": ["https://cf.shopee.vn/file/main.jpg"],
            "brand": "Acme",
            "specs": [],
        },
        "gallery": [],
        "variants": [],
        "description_media": [],
        "fallback_media": [],
        "selected_variants": [
            {"group_label": "Color", "option_label": "Black"},
        ],
        "selected_variants_complete": True,
        "blocked": False,
    }
    eval_data_white = {
        "structured": {
            "title": "Shopee Phone Listing",
            "product_id": "456789",
            "images": ["https://cf.shopee.vn/file/main.jpg"],
            "brand": "Acme",
            "specs": [],
        },
        "gallery": [],
        "variants": [],
        "description_media": [],
        "fallback_media": [],
        "selected_variants": [
            {"group_label": "Color", "option_label": "White"},
        ],
        "selected_variants_complete": True,
        "blocked": False,
    }

    pack_black = await ShopeeSourceExtractor(browser=FakeSession(eval_data_black)).extract(
        "https://shopee.vn/product/123/456789"
    )
    pack_white = await ShopeeSourceExtractor(browser=FakeSession(eval_data_white)).extract(
        "https://shopee.vn/product/123/456789"
    )

    result = resolve_product_entities(pack_black, pack_white)
    assert result.relationship is ProductRelationship.SAME_PRODUCT_FAMILY
    assert any(e.code == "VARIANT_CONFLICT" for e in result.evidence)
    assert "different sellable variant" in result.reasons


@pytest.mark.asyncio
async def test_task_108_compatibility_same_listing_insufficient_variant_evidence_when_absent_or_incomplete():
    """Unchanged TASK-108 resolves SAME_PRODUCT_FAMILY with insufficient variant evidence when selected evidence is absent or incomplete."""
    eval_data_no_variants = {
        "structured": {
            "title": "Shopee Phone Listing",
            "product_id": "456789",
            "images": ["https://cf.shopee.vn/file/main.jpg"],
            "brand": "Acme",
            "specs": [],
        },
        "gallery": [],
        "variants": [],
        "description_media": [],
        "fallback_media": [],
        "selected_variants": [],
        "selected_variants_complete": False,
        "blocked": False,
    }
    eval_data_with_variant = {
        "structured": {
            "title": "Shopee Phone Listing",
            "product_id": "456789",
            "images": ["https://cf.shopee.vn/file/main.jpg"],
            "brand": "Acme",
            "specs": [],
        },
        "gallery": [],
        "variants": [],
        "description_media": [],
        "fallback_media": [],
        "selected_variants": [
            {"group_label": "Color", "option_label": "Black"},
        ],
        "selected_variants_complete": True,
        "blocked": False,
    }

    pack_none1 = await ShopeeSourceExtractor(browser=FakeSession(eval_data_no_variants)).extract(
        "https://shopee.vn/product/123/456789"
    )
    pack_none2 = await ShopeeSourceExtractor(browser=FakeSession(eval_data_no_variants)).extract(
        "https://shopee.vn/product/123/456789"
    )
    pack_with = await ShopeeSourceExtractor(browser=FakeSession(eval_data_with_variant)).extract(
        "https://shopee.vn/product/123/456789"
    )

    # Both absent
    result_both_absent = resolve_product_entities(pack_none1, pack_none2)
    assert result_both_absent.relationship is ProductRelationship.SAME_PRODUCT_FAMILY
    assert "insufficient variant evidence for exact match" in result_both_absent.reasons

    # One present, one absent (incomplete pair)
    result_incomplete = resolve_product_entities(pack_with, pack_none1)
    assert result_incomplete.relationship is ProductRelationship.SAME_PRODUCT_FAMILY
    assert "insufficient variant evidence for exact match" in result_incomplete.reasons
