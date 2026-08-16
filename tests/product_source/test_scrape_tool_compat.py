from __future__ import annotations

from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, patch

import pytest

from src.core.types import ToolCall, ToolStatus
from src.product_source.models import (
    MediaProvenance,
    MediaRole,
    OriginalMediaRef,
)
from src.tools.shopee_scrape_tool import ShopeeScrapeTool
from src.tools.tiktok_scrape_tool import TikTokScrapeTool


class FakeBrowserSession:
    def __init__(self, evaluate_result=None):
        self.navigated_urls = []
        self.evaluated_scripts = []
        self._evaluate_result = evaluate_result or {
            "structured": {
                "title": "Sample Product",
                "product_id": "456",
                "images": ["https://cf.shopee.vn/file/img1.jpg"],
                "brand": "SampleBrand",
                "specs": [],
            },
            "gallery": ["https://cf.shopee.vn/file/gallery.jpg"],
            "gallery_images": ["https://p16-oec-va.ibyteimg.com/gallery.jpg"],
            "variants": [],
            "description_media": [],
            "seller_images": [],
            "fallback_media": [],
            "fallback_images": [],
            "blocked": False,
        }

    async def navigate(self, url: str, **kwargs: Any) -> None:
        self.navigated_urls.append(url)

    async def evaluate(self, script: str, *args: Any) -> Any:
        self.evaluated_scripts.append((script, args))
        return self._evaluate_result


class FakeBrowserManager:
    """
    Fake conforming strictly to BrowserManager protocol:
    async def get_or_create_session(self, run_id: str, config: Optional[Any] = None) -> BrowserSession
    """
    def __init__(self, session: FakeBrowserSession):
        self._session = session
        self.new_page_called = False
        self.received_run_id: Optional[str] = None

    def new_page(self):
        self.new_page_called = True
        raise NotImplementedError("Tools should not call new_page() directly")

    async def get_or_create_session(self, run_id: str, config: Optional[Any] = None):
        # Strict positional run_id argument enforcement
        if not isinstance(run_id, str) or not run_id.strip():
            raise TypeError("get_or_create_session requires a non-empty run_id string")
        self.received_run_id = run_id
        return self._session


class FakeGDrive:
    def __init__(self, should_fail: bool = False, partial_fail: bool = False):
        self.folders = {}
        self.uploaded_files = []
        self.should_fail = should_fail
        self.partial_fail = partial_fail
        self.upload_call_count = 0

    def get_or_create_folder(self, folder_name: str, parent_id: str = None) -> str:
        fid = f"folder_{folder_name}"
        self.folders[fid] = folder_name
        return fid

    def upload_file(self, file_path: str, folder_id: str = None) -> str:
        self.upload_call_count += 1
        if self.should_fail:
            return None
        if self.partial_fail and self.upload_call_count > 1:
            return None
        fid = f"file_{len(self.uploaded_files)}"
        self.uploaded_files.append((file_path, folder_id))
        return fid


@pytest.fixture
def fake_browser_session():
    return FakeBrowserSession()


@pytest.fixture
def fake_browser_manager(fake_browser_session):
    return FakeBrowserManager(fake_browser_session)


def test_shopee_scrape_tool_schema():
    """1. ShopeeScrapeTool name and schema."""
    tool = ShopeeScrapeTool()
    assert tool.name == "shopee_scrape"
    schema = tool.get_schema()
    assert "url" in schema["properties"]
    assert "url" in schema["required"]


def test_tiktok_scrape_tool_schema():
    """2. TikTokScrapeTool name and schema."""
    tool = TikTokScrapeTool()
    assert tool.name == "tiktok_scrape"
    schema = tool.get_schema()
    assert "url" in schema["properties"]
    assert "url" in schema["required"]


@pytest.mark.asyncio
async def test_shopee_scrape_tool_passes_run_id_to_browser_manager(fake_browser_manager):
    """3. ShopeeScrapeTool calls get_or_create_session(run_id) with non-empty run_id."""
    tool = ShopeeScrapeTool()
    context = {
        "browser_manager": fake_browser_manager,
        "gdrive": FakeGDrive(),
        "gdrive_folder_id": "root",
    }
    call = ToolCall(
        name="shopee_scrape",
        arguments={"url": "https://shopee.vn/product/123/456"},
        call_id="c1",
        run_id="run_shopee_123",
    )

    fake_downloaded = [
        OriginalMediaRef(
            source_url="https://cf.shopee.vn/file/img1.jpg",
            platform="shopee",
            role=MediaRole.PRIMARY,
            provenance=MediaProvenance.STRUCTURED_PRODUCT_DATA,
            ordinal=0,
            local_filename="orig_000_abc123.jpg",
        )
    ]
    with patch(
        "src.product_source.downloader.OriginalMediaDownloader.download_accepted_media",
        new=AsyncMock(return_value=(fake_downloaded, [])),
    ):
        result = await tool.execute(call, context)

    assert not fake_browser_manager.new_page_called
    assert fake_browser_manager.received_run_id == "run_shopee_123"
    assert result.status == ToolStatus.SUCCESS


@pytest.mark.asyncio
async def test_tiktok_scrape_tool_passes_run_id_to_browser_manager(fake_browser_manager):
    """4. TikTokScrapeTool calls get_or_create_session(run_id) with non-empty run_id."""
    tool = TikTokScrapeTool()
    context = {
        "browser_manager": fake_browser_manager,
        "gdrive": FakeGDrive(),
        "gdrive_folder_id": "root",
    }
    call = ToolCall(
        name="tiktok_scrape",
        arguments={"url": "https://www.tiktok.com/view/product/123456"},
        call_id="c2",
        run_id="run_tiktok_456",
    )

    fake_downloaded = [
        OriginalMediaRef(
            source_url="https://p16-oec-va.ibyteimg.com/img1.jpg",
            platform="tiktok",
            role=MediaRole.PRIMARY,
            provenance=MediaProvenance.STRUCTURED_PRODUCT_DATA,
            ordinal=0,
            local_filename="orig_000_tiktok123.jpg",
        )
    ]
    with patch(
        "src.product_source.downloader.OriginalMediaDownloader.download_accepted_media",
        new=AsyncMock(return_value=(fake_downloaded, [])),
    ):
        result = await tool.execute(call, context)

    assert not fake_browser_manager.new_page_called
    assert fake_browser_manager.received_run_id == "run_tiktok_456"
    assert result.status == ToolStatus.SUCCESS


def test_tools_do_not_call_image_processor():
    """5. Scrape tools do not import or require ImageProcessor for source persistence."""
    import inspect
    from src.tools import shopee_scrape_tool, tiktok_scrape_tool

    shopee_src = inspect.getsource(shopee_scrape_tool)
    tiktok_src = inspect.getsource(tiktok_scrape_tool)

    assert "process_and_save" not in shopee_src
    assert "process_and_save" not in tiktok_src


def test_tools_do_not_invoke_llm():
    """6. Scrape tools do not invoke LLM/scoring/ranking/queue mutation."""
    import inspect
    from src.tools import shopee_scrape_tool, tiktok_scrape_tool

    shopee_src = inspect.getsource(shopee_scrape_tool)
    tiktok_src = inspect.getsource(tiktok_scrape_tool)

    assert "LLMProvider" not in shopee_src
    assert "tasks.txt" not in shopee_src
    assert "score" not in shopee_src.lower()
    assert "ranking" not in shopee_src.lower()


@pytest.mark.asyncio
async def test_partial_upload_returns_partial_success(fake_browser_manager, tmp_path):
    """7. Partial upload returns honest PARTIAL_SUCCESS semantics."""
    tool = ShopeeScrapeTool()
    partial_gdrive = FakeGDrive(partial_fail=True)
    context = {
        "browser_manager": fake_browser_manager,
        "gdrive": partial_gdrive,
        "gdrive_folder_id": "root",
        "output_dir": str(tmp_path),
    }
    call = ToolCall(
        name="shopee_scrape",
        arguments={"url": "https://shopee.vn/product/123/456"},
        call_id="c3",
        run_id="r3",
    )

    orig_dir = tmp_path / "shopee" / "shopee_456" / "original"
    orig_dir.mkdir(parents=True, exist_ok=True)
    dummy_file = orig_dir / "orig_000_abc123.jpg"
    dummy_file.write_bytes(b"\xFF\xD8\xFF\xE0" + b"\x00" * 10)

    fake_downloaded = [
        OriginalMediaRef(
            source_url="https://cf.shopee.vn/file/img1.jpg",
            platform="shopee",
            role=MediaRole.PRIMARY,
            provenance=MediaProvenance.STRUCTURED_PRODUCT_DATA,
            ordinal=0,
            local_filename="orig_000_abc123.jpg",
        )
    ]
    with patch(
        "src.product_source.downloader.OriginalMediaDownloader.download_accepted_media",
        new=AsyncMock(return_value=(fake_downloaded, [])),
    ):
        result = await tool.execute(call, context)

    assert result.status == ToolStatus.PARTIAL_SUCCESS
    assert result.data["uploaded_count"] == 1


@pytest.mark.asyncio
async def test_full_upload_failure_returns_failure(fake_browser_manager):
    """8. Full upload failure returns FAILURE with UPLOAD_FAILED error code."""
    tool = ShopeeScrapeTool()
    failing_gdrive = FakeGDrive(should_fail=True)
    context = {
        "browser_manager": fake_browser_manager,
        "gdrive": failing_gdrive,
        "gdrive_folder_id": "root",
    }
    call = ToolCall(
        name="shopee_scrape",
        arguments={"url": "https://shopee.vn/product/123/456"},
        call_id="c4",
        run_id="r4",
    )

    fake_downloaded = [
        OriginalMediaRef(
            source_url="https://cf.shopee.vn/file/img1.jpg",
            platform="shopee",
            role=MediaRole.PRIMARY,
            provenance=MediaProvenance.STRUCTURED_PRODUCT_DATA,
            ordinal=0,
            local_filename="orig_000_abc123.jpg",
        )
    ]
    with patch(
        "src.product_source.downloader.OriginalMediaDownloader.download_accepted_media",
        new=AsyncMock(return_value=(fake_downloaded, [])),
    ):
        result = await tool.execute(call, context)

    assert result.status == ToolStatus.FAILURE
    assert result.error is not None
    assert result.error.code == "UPLOAD_FAILED"
