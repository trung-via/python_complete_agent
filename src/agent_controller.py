from __future__ import annotations

import logging
import os
from typing import Optional

from src.agent.loop import AgentLoop
from src.agent.policy import RunPolicy
from src.core.checkpoint import CheckpointManager
from src.core.idempotency_store_v2 import JsonlIdempotencyStore
from src.core.retry import RetryManager
from src.core.tool_executor import ToolExecutor
from src.core.tool_registry import ToolRegistry
from src.integrations.playwright.manager import PlaywrightBrowserManager
from src.modules.gdrive_integrator import GDriveIntegrator
from src.modules.image_processor import ImageProcessor
from src.providers.gemini import GeminiProvider
from src.tools.browser.click import ClickTool
from src.tools.browser.inspect import InspectTool
from src.tools.browser.navigate import NavigateTool
from src.tools.browser.press import PressTool
from src.tools.browser.screenshot import ScreenshotTool
from src.tools.browser.type_text import TypeTextTool
from src.tools.shopee_scrape_tool import ShopeeScrapeTool
from src.tools.tiktok_scrape_tool import TikTokScrapeTool

logger = logging.getLogger(__name__)


class AgentController:
    """
    Main orchestration class.

    Uses the v2 JSONL idempotency store while keeping the executor API
    compatible with the existing agent loop.
    """

    def __init__(
        self,
        db_path: str = "data/checkpoints.jsonl",
        idempotency_path: str = "data/idempotency_store_v2.jsonl",
    ) -> None:
        self.registry = ToolRegistry()
        self.checkpoints = CheckpointManager(db_path=db_path)
        self.retry_manager = RetryManager()
        self.idempotency_store = JsonlIdempotencyStore(
            db_path=idempotency_path,
        )

        self.browser_manager = PlaywrightBrowserManager()
        self.image_processor = ImageProcessor()
        self.gdrive = GDriveIntegrator("credentials.json")
        self.gdrive_folder_id = os.environ.get(
            "GDRIVE_FOLDER_ID",
            "dummy_folder_id",
        )

        self._register_tools()

        self.llm_provider = GeminiProvider()

        self.tool_context = {
            "browser_manager": self.browser_manager,
            "image_processor": self.image_processor,
            "gdrive": self.gdrive,
            "gdrive_folder_id": self.gdrive_folder_id,
        }

        self.tool_executor = ToolExecutor(
            registry=self.registry,
            idempotency_store=self.idempotency_store,
            retry_manager=self.retry_manager,
            checkpoints=self.checkpoints,
            context=self.tool_context,
        )

        self.agent_loop = AgentLoop(
            llm_provider=self.llm_provider,
            tool_executor=self.tool_executor,
            tool_registry=self.registry,
            checkpoints=self.checkpoints,
            policy=RunPolicy(),
        )

    def _register_tools(self) -> None:
        self.registry.register_tool(
            NavigateTool(self.browser_manager)
        )
        self.registry.register_tool(
            ClickTool(self.browser_manager)
        )
        self.registry.register_tool(
            TypeTextTool(self.browser_manager)
        )
        self.registry.register_tool(
            PressTool(self.browser_manager)
        )
        self.registry.register_tool(
            ScreenshotTool(self.browser_manager)
        )
        self.registry.register_tool(
            InspectTool(self.browser_manager)
        )
        self.registry.register_tool(ShopeeScrapeTool())
        self.registry.register_tool(TikTokScrapeTool())

    async def start(self) -> None:
        """Initialize heavy resources."""
        self.gdrive.authenticate()

    async def stop(self) -> None:
        """Clean up resources."""
        await self.browser_manager.close_all()

    async def run(
        self,
        user_prompt: str,
        run_id: Optional[str] = None,
    ) -> Optional[str]:
        """Execute the full agent loop."""
        if not run_id:
            run_id = self.checkpoints.log_task_start(user_prompt)

        system_prompt = (
            "You are an autonomous agent designed to scrape products from "
            "Shopee and TikTok, download their images, watermark them, and "
            "upload them to Google Drive. "
            "You have access to a set of tools to accomplish this. "
            "Think step-by-step and call tools as needed."
        )

        return await self.agent_loop.run(
            run_id=run_id,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
