from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict

from src.core.base_tool import BaseTool
from src.core.errors import (
    AgentException,
    DependencyError,
)
from src.core.types import ToolCall, ToolResult, ToolStatus
from src.product_source.downloader import OriginalMediaDownloader
from src.product_source.models import (
    SourcePackBlockedError,
    SourcePackError,
    SourcePackExtractionError,
)
from src.product_source.platforms.shopee import ShopeeSourceExtractor
from src.product_source.serialization import serialize_source_pack

logger = logging.getLogger(__name__)


class ShopeeScrapeTool(BaseTool):
    @property
    def name(self) -> str:
        return "shopee_scrape"

    @property
    def description(self) -> str:
        return "Scrapes canonical product source pack (facts and original media) from a Shopee URL, persists source_pack.json, and uploads to Google Drive."

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The Shopee product URL to scrape",
                }
            },
            "required": ["url"],
        }

    async def execute(self, call: ToolCall, context: Dict[str, Any]) -> ToolResult:
        url = call.arguments.get("url")
        if not url:
            return ToolResult(
                call_id=call.call_id,
                run_id=call.run_id,
                tool_name=self.name,
                status=ToolStatus.FAILURE,
                error=AgentException("Missing 'url' in arguments", code="MISSING_ARG_URL"),
            )

        logger.info(f"Executing ShopeeScrapeTool for URL: {url}")

        browser = context.get("browser") or context.get("browser_manager")
        gdrive = context.get("gdrive")
        gdrive_folder_id = context.get("gdrive_folder_id")

        if not all([browser, gdrive]):
            missing = []
            if not browser:
                missing.append("browser/browser_manager")
            if not gdrive:
                missing.append("gdrive")
            raise DependencyError(
                f"Missing required context components for ShopeeScrapeTool: {', '.join(missing)}"
            )

        output_base_dir = context.get("output_dir") or "data/source_packs"

        # 1. Extract canonical product source pack
        extractor = ShopeeSourceExtractor(browser=browser)
        try:
            source_pack = await extractor.extract(url, run_id=call.run_id)
        except SourcePackBlockedError as e:
            return ToolResult(
                call_id=call.call_id,
                run_id=call.run_id,
                tool_name=self.name,
                status=ToolStatus.FAILURE,
                error=AgentException(
                    f"Shopee extraction blocked: {e}",
                    code="EXTRACTION_BLOCKED",
                    retryable=False,
                ),
            )
        except (SourcePackExtractionError, SourcePackError, Exception) as e:
            return ToolResult(
                call_id=call.call_id,
                run_id=call.run_id,
                tool_name=self.name,
                status=ToolStatus.FAILURE,
                error=AgentException(
                    f"Shopee source extraction failed: {e}",
                    code="EXTRACTION_EMPTY",
                    retryable=True,
                ),
            )

        product_output_dir = os.path.join(output_base_dir, "shopee", source_pack.source_pack_id)
        os.makedirs(product_output_dir, exist_ok=True)

        # 2. Download original media bytes (byte-preserving, no re-encoding)
        downloader = OriginalMediaDownloader(output_dir=product_output_dir)
        downloaded_refs, download_diagnostics = await downloader.download_accepted_media(source_pack.media)

        # Update pack with downloaded refs and diagnostics
        all_diagnostics = list(source_pack.diagnostic_codes) + download_diagnostics
        updated_pack = type(source_pack)(
            source_pack_id=source_pack.source_pack_id,
            platform=source_pack.platform,
            product_url=source_pack.product_url,
            observed_at=source_pack.observed_at,
            collector=source_pack.collector,
            title=source_pack.title,
            source_product_id=source_pack.source_product_id,
            shop_name=source_pack.shop_name,
            brand=source_pack.brand,
            model_sku=source_pack.model_sku,
            description_text=source_pack.description_text,
            facts=source_pack.facts,
            media=tuple(downloaded_refs),
            diagnostic_codes=tuple(all_diagnostics),
        )

        manifest_path = serialize_source_pack(updated_pack, product_output_dir)

        if not downloaded_refs and len(source_pack.media) > 0:
            return ToolResult(
                call_id=call.call_id,
                run_id=call.run_id,
                tool_name=self.name,
                status=ToolStatus.FAILURE,
                error=AgentException(
                    "Failed to download any accepted original media locally",
                    code="DOWNLOAD_FAILED",
                    retryable=True,
                ),
            )

        # 3. Google Drive Publication (source_pack.json + original files)
        upload_success_count = 0
        total_files_to_upload = 0

        try:
            logger.info("Setting up GDrive folders...")
            platform_folder_id = gdrive.get_or_create_folder("Shopee", parent_id=gdrive_folder_id)
            if not platform_folder_id:
                platform_folder_id = gdrive_folder_id

            safe_product_name = (
                re.sub(r'[\\/*?:"<>|]', "", source_pack.title or "Unknown Product")[:80].strip()
                or source_pack.source_pack_id
            )
            product_folder_id = gdrive.get_or_create_folder(safe_product_name, parent_id=platform_folder_id)
            if not product_folder_id:
                product_folder_id = platform_folder_id

            # Upload source_pack.json
            total_files_to_upload += 1
            if gdrive.upload_file(manifest_path, folder_id=product_folder_id):
                upload_success_count += 1

            # Upload original files
            orig_folder_id = gdrive.get_or_create_folder("original", parent_id=product_folder_id)
            if not orig_folder_id:
                orig_folder_id = product_folder_id

            for ref in downloaded_refs:
                if ref.local_filename:
                    file_path = os.path.join(downloader.original_dir, ref.local_filename)
                    if os.path.exists(file_path):
                        total_files_to_upload += 1
                        if gdrive.upload_file(file_path, folder_id=orig_folder_id):
                            upload_success_count += 1
        except Exception as e:
            logger.warning(f"GDrive upload encountered error: {e}")

        is_partial = upload_success_count < total_files_to_upload

        if total_files_to_upload > 0 and upload_success_count == 0:
            return ToolResult(
                call_id=call.call_id,
                run_id=call.run_id,
                tool_name=self.name,
                status=ToolStatus.FAILURE,
                error=AgentException(
                    "Failed to upload source pack to GDrive",
                    code="UPLOAD_FAILED",
                    retryable=True,
                ),
            )

        logger.info("Shopee Source Pack task completed successfully.")
        return ToolResult(
            call_id=call.call_id,
            run_id=call.run_id,
            tool_name=self.name,
            status=ToolStatus.PARTIAL_SUCCESS if is_partial else ToolStatus.SUCCESS,
            data={
                "source_pack_id": source_pack.source_pack_id,
                "title": source_pack.title,
                "shop_name": source_pack.shop_name,
                "brand": source_pack.brand,
                "facts_count": len(source_pack.facts),
                "total_found": len(source_pack.media),
                "downloaded_count": len(downloaded_refs),
                "uploaded_count": upload_success_count,
                "manifest_path": manifest_path,
            },
        )
