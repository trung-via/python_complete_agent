"""Certification-only integration test for live product source acquisition.

Proves that one explicit current marketplace route can discover a real candidate
and persist a typed V1 ProductSourcePack locally beneath pytest tmp_path.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any, Optional

import pytest

from src.browser.errors import BrowserError, BrowserSessionUnavailableError
from src.core.types import ToolCall, ToolResult, ToolStatus
from src.integrations.playwright.manager import PlaywrightBrowserManager
from src.product_intelligence.adapters.shopee import ShopeeDiscoveryAdapter
from src.product_intelligence.adapters.tiktok import TikTokDiscoveryAdapter
from src.product_intelligence.discovery import (
    DiscoveryBatch,
    DiscoveryBlockedError,
    DiscoveryError,
    DiscoveryNavigationError,
    DiscoveryRequest,
)
from src.product_intelligence.orchestration import (
    OrchestrationError,
    PlatformDiscoveryPlan,
    orchestrate_discovery,
)
from src.product_source.models import ProductSourcePack
from src.product_source.serialization import deserialize_product_source_pack
from src.tools.shopee_scrape_tool import ShopeeScrapeTool
from src.tools.tiktok_scrape_tool import TikTokScrapeTool


DEFAULT_LIVE_CERT_PLATFORM = "shopee"
DEFAULT_LIVE_CERT_QUERY = "bình giữ nhiệt inox"
DEFAULT_LIVE_CERT_CDP_ENDPOINT = "http://127.0.0.1:9222"


@dataclass(frozen=True)
class LiveAcquisitionConfig:
    platform: str
    query: str
    cdp_endpoint: str


def resolve_live_acquisition_config() -> LiveAcquisitionConfig:
    """Resolve and validate live acquisition certification configuration."""
    # 1. Platform: defaults to "shopee", accepts only exact "shopee" or "tiktok"
    platform_env = os.environ.get("PI_LIVE_CERT_PLATFORM")
    if platform_env is None:
        platform = DEFAULT_LIVE_CERT_PLATFORM
    else:
        if platform_env not in ("shopee", "tiktok"):
            raise ValueError(
                f"Invalid PI_LIVE_CERT_PLATFORM: {platform_env!r}. "
                "Must be exact 'shopee' or 'tiktok'."
            )
        platform = platform_env

    # 2. Query: defaults to exact "bình giữ nhiệt inox", must be single-line and non-whitespace
    query_env = os.environ.get("PI_LIVE_CERT_QUERY")
    if query_env is None:
        query = DEFAULT_LIVE_CERT_QUERY
    else:
        if "\n" in query_env or "\r" in query_env:
            raise ValueError(
                "Invalid PI_LIVE_CERT_QUERY: query must be a single-line string."
            )
        if not query_env.strip():
            raise ValueError(
                "Invalid PI_LIVE_CERT_QUERY: query cannot be empty or whitespace-only."
            )
        query = query_env

    # 3. CDP Endpoint: defaults to exact "http://127.0.0.1:9222", forwarded unchanged
    cdp_env = os.environ.get("PI_LIVE_CERT_CDP_ENDPOINT")
    if cdp_env is None:
        cdp_endpoint = DEFAULT_LIVE_CERT_CDP_ENDPOINT
    else:
        if not cdp_env.strip() or ("\n" in cdp_env or "\r" in cdp_env):
            raise ValueError(
                "Invalid PI_LIVE_CERT_CDP_ENDPOINT: endpoint cannot be empty or multiline."
            )
        cdp_endpoint = cdp_env

    return LiveAcquisitionConfig(
        platform=platform,
        query=query,
        cdp_endpoint=cdp_endpoint,
    )


class InMemoryCertificationDriveSink:
    """Certification-only zero-network in-memory Drive sink.

    Implements the minimal synchronous GDrive protocol required by existing
    platform scrape tools without performing any filesystem writes, network
    requests, or external authentication.
    """

    def __init__(self) -> None:
        self.folders: dict[str, str] = {}
        self.uploaded_files: list[tuple[str, Optional[str]]] = []
        self.folder_call_count: int = 0
        self.upload_call_count: int = 0

    def get_or_create_folder(self, name: str, parent_id: Optional[str] = None) -> str:
        self.folder_call_count += 1
        folder_id = f"cert_folder_{name}"
        self.folders[folder_id] = name
        return folder_id

    def upload_file(self, file_path: str, folder_id: Optional[str] = None) -> str:
        self.upload_call_count += 1
        file_id = f"cert_file_{len(self.uploaded_files)}"
        self.uploaded_files.append((file_path, folder_id))
        return file_id


def _is_browser_or_cdp_error(exc: BaseException) -> bool:
    curr: Optional[BaseException] = exc
    while curr is not None:
        if isinstance(curr, (BrowserError, BrowserSessionUnavailableError)):
            return True
        msg = str(curr).lower()
        if "connect" in msg or "cdp" in msg or "connection refused" in msg or "target closed" in msg:
            return True
        curr = curr.__cause__ or curr.__context__
    return False


@pytest.mark.asyncio
async def test_live_product_source_acquisition(tmp_path: Path) -> None:
    """Certify live marketplace discovery to persisted typed ProductSourcePack."""
    try:
        config = resolve_live_acquisition_config()
    except Exception:
        pytest.fail("LIVE_CONFIG_INVALID", pytrace=False)

    manager = PlaywrightBrowserManager(cdp_endpoint=config.cdp_endpoint)

    try:
        # Discovery phase: exactly one adapter, one request, one plan, one orchestrate call
        try:
            if config.platform == "shopee":
                adapter = ShopeeDiscoveryAdapter(browser=manager)
            elif config.platform == "tiktok":
                adapter = TikTokDiscoveryAdapter(browser=manager)
            else:
                pytest.fail("LIVE_CONFIG_INVALID", pytrace=False)

            request = DiscoveryRequest(
                query=config.query,
                max_pages=1,
                max_candidates=20,
            )
            plan = PlatformDiscoveryPlan(
                platform=config.platform,
                adapter=adapter,
                request=request,
            )
            now = datetime.now(timezone.utc)
            orchestration_result = await orchestrate_discovery(
                (plan,),
                observed_at=now,
                evaluated_at=now,
                shortlist_size=5,
            )
        except Exception as exc:
            if _is_browser_or_cdp_error(exc):
                pytest.fail("LIVE_CDP_UNAVAILABLE", pytrace=False)
            pytest.fail("LIVE_DISCOVERY_UNAVAILABLE", pytrace=False)

        # Shortlist requirement
        if not orchestration_result.shortlist:
            pytest.fail("LIVE_DISCOVERY_EMPTY", pytrace=False)

        candidate = orchestration_result.shortlist[0].candidate

        # Acquisition / scrape phase: exactly one scrape tool execution
        try:
            if config.platform == "shopee":
                tool = ShopeeScrapeTool()
            else:
                tool = TikTokScrapeTool()

            drive_sink = InMemoryCertificationDriveSink()
            call = ToolCall(
                name=tool.name,
                arguments={"url": candidate.url},
                call_id="cert_call_001",
                run_id="cert_run_001",
            )
            context = {
                "browser": manager,
                "browser_manager": manager,
                "gdrive": drive_sink,
                "gdrive_folder_id": "cert_dummy_folder",
                "output_dir": str(tmp_path),
            }
            tool_result = await tool.execute(call, context)
        except Exception as exc:
            if _is_browser_or_cdp_error(exc):
                pytest.fail("LIVE_CDP_UNAVAILABLE", pytrace=False)
            pytest.fail("LIVE_ACQUISITION_UNAVAILABLE", pytrace=False)

        if tool_result.status != ToolStatus.SUCCESS or tool_result.error is not None:
            pytest.fail("LIVE_ACQUISITION_UNAVAILABLE", pytrace=False)

        # Persistence & typed rehydration verification
        try:
            if not tool_result.data or not isinstance(tool_result.data, dict):
                pytest.fail("LIVE_SOURCE_PACK_INVALID", pytrace=False)

            manifest_path_raw = tool_result.data.get("manifest_path")
            if not manifest_path_raw or not isinstance(manifest_path_raw, str):
                pytest.fail("LIVE_SOURCE_PACK_INVALID", pytrace=False)

            manifest_path = Path(manifest_path_raw).resolve()
            tmp_resolved = tmp_path.resolve()

            try:
                manifest_path.relative_to(tmp_resolved)
            except ValueError:
                pytest.fail("LIVE_SOURCE_PACK_INVALID", pytrace=False)

            if manifest_path.name != "source_pack.json":
                pytest.fail("LIVE_SOURCE_PACK_INVALID", pytrace=False)

            if not manifest_path.is_file() or manifest_path.is_symlink():
                pytest.fail("LIVE_SOURCE_PACK_INVALID", pytrace=False)

            pack = deserialize_product_source_pack(str(manifest_path))

            if not isinstance(pack, ProductSourcePack):
                pytest.fail("LIVE_SOURCE_PACK_INVALID", pytrace=False)

            if pack.platform != config.platform:
                pytest.fail("LIVE_SOURCE_PACK_INVALID", pytrace=False)

            for field_val in (
                pack.source_pack_id,
                pack.source_product_id,
                pack.collector,
                pack.product_url,
            ):
                if not isinstance(field_val, str) or not field_val.strip():
                    pytest.fail("LIVE_SOURCE_PACK_INVALID", pytrace=False)

            if (
                not isinstance(pack.observed_at, datetime)
                or pack.observed_at.tzinfo is None
                or pack.observed_at.utcoffset() is None
            ):
                pytest.fail("LIVE_SOURCE_PACK_INVALID", pytrace=False)

            has_substantive = any(
                (
                    isinstance(pack.title, str) and bool(pack.title.strip()),
                    isinstance(pack.shop_name, str) and bool(pack.shop_name.strip()),
                    isinstance(pack.brand, str) and bool(pack.brand.strip()),
                    isinstance(pack.model_sku, str) and bool(pack.model_sku.strip()),
                    isinstance(pack.description_text, str)
                    and bool(pack.description_text.strip()),
                    bool(pack.facts),
                    bool(pack.media),
                )
            )
            if not has_substantive:
                pytest.fail("LIVE_SOURCE_PACK_INVALID", pytrace=False)

            # Assert returned tool data aligns with deserialized source pack
            if tool_result.data.get("source_pack_id") != pack.source_pack_id:
                pytest.fail("LIVE_SOURCE_PACK_INVALID", pytrace=False)

            if Path(str(tool_result.data.get("manifest_path"))).resolve() != manifest_path:
                pytest.fail("LIVE_SOURCE_PACK_INVALID", pytrace=False)

        except Exception:
            pytest.fail("LIVE_SOURCE_PACK_INVALID", pytrace=False)

    finally:
        try:
            await manager.close_all()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Offline deterministic tests for configuration and Drive sink
# ---------------------------------------------------------------------------


def test_resolve_live_acquisition_config_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PI_LIVE_CERT_PLATFORM", raising=False)
    monkeypatch.delenv("PI_LIVE_CERT_QUERY", raising=False)
    monkeypatch.delenv("PI_LIVE_CERT_CDP_ENDPOINT", raising=False)

    config = resolve_live_acquisition_config()
    assert config.platform == "shopee"
    assert config.query == "bình giữ nhiệt inox"
    assert config.cdp_endpoint == "http://127.0.0.1:9222"


def test_resolve_live_acquisition_config_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PI_LIVE_CERT_PLATFORM", "tiktok")
    monkeypatch.setenv("PI_LIVE_CERT_QUERY", "nồi chiên không dầu")
    monkeypatch.setenv("PI_LIVE_CERT_CDP_ENDPOINT", "http://127.0.0.1:9333")

    config = resolve_live_acquisition_config()
    assert config.platform == "tiktok"
    assert config.query == "nồi chiên không dầu"
    assert config.cdp_endpoint == "http://127.0.0.1:9333"


@pytest.mark.parametrize("invalid_platform", ["Shopee", "SHOPEE", "tik_tok", "amazon", "lazada", ""])
def test_resolve_live_acquisition_config_invalid_platform(
    monkeypatch: pytest.MonkeyPatch,
    invalid_platform: str,
) -> None:
    monkeypatch.setenv("PI_LIVE_CERT_PLATFORM", invalid_platform)
    with pytest.raises(ValueError, match="PI_LIVE_CERT_PLATFORM"):
        resolve_live_acquisition_config()


@pytest.mark.parametrize("invalid_query", ["", "   ", "\t", "line1\nline2", "line1\rline2"])
def test_resolve_live_acquisition_config_invalid_query(
    monkeypatch: pytest.MonkeyPatch,
    invalid_query: str,
) -> None:
    monkeypatch.setenv("PI_LIVE_CERT_QUERY", invalid_query)
    with pytest.raises(ValueError, match="PI_LIVE_CERT_QUERY"):
        resolve_live_acquisition_config()


@pytest.mark.parametrize("invalid_cdp", ["", "   ", "http://127.0.0.1:9222\n"])
def test_resolve_live_acquisition_config_invalid_cdp(
    monkeypatch: pytest.MonkeyPatch,
    invalid_cdp: str,
) -> None:
    monkeypatch.setenv("PI_LIVE_CERT_CDP_ENDPOINT", invalid_cdp)
    with pytest.raises(ValueError, match="PI_LIVE_CERT_CDP_ENDPOINT"):
        resolve_live_acquisition_config()


def test_certification_drive_sink() -> None:
    sink = InMemoryCertificationDriveSink()
    fid = sink.get_or_create_folder("Shopee", parent_id="root_id")
    assert fid == "cert_folder_Shopee"
    assert sink.folder_call_count == 1
    assert sink.folders[fid] == "Shopee"

    file_id = sink.upload_file("manifest.json", folder_id=fid)
    assert file_id == "cert_file_0"
    assert sink.upload_call_count == 1
    assert sink.uploaded_files == [("manifest.json", fid)]

    public_methods = {
        m for m in dir(sink)
        if not m.startswith("_") and callable(getattr(sink, m))
    }
    assert public_methods == {"get_or_create_folder", "upload_file"}
