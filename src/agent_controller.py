import os
import logging
from typing import Optional, List, Dict, Any

from src.core.tool_registry import ToolRegistry
from src.core.checkpoint import CheckpointManager
from src.core.retry import RetryManager
from src.core.idempotency import IdempotencyStore
from src.core.errors import AgentException, SystemStateError
from src.core.types import ToolCall, ToolResult, ToolStatus

# Phase 2 Components
from src.core.tool_executor import ToolExecutor
from src.agent.policy import RunPolicy
from src.agent.loop import AgentLoop
from src.providers.gemini import GeminiProvider

# We keep standard tools initialization here for now
from src.modules.browser_automation import BrowserAutomation
from src.modules.image_processor import ImageProcessor
from src.modules.gdrive_integrator import GDriveIntegrator

from src.tools.shopee_scrape_tool import ShopeeScrapeTool
from src.tools.tiktok_scrape_tool import TikTokScrapeTool

logger = logging.getLogger(__name__)

class AgentController:
    """
    Main orchestration class.
    Phase 2: Wiring the LLM Provider, ToolExecutor, and AgentLoop.
    """
    def __init__(self, db_path: str = "data/checkpoints.jsonl", idempotency_path: str = "data/idempotency_store.jsonl"):
        # Base infrastructure
        self.registry = ToolRegistry()
        self.checkpoints = CheckpointManager(db_path=db_path)
        self.retry_manager = RetryManager()
        self.idempotency_store = IdempotencyStore(db_path=idempotency_path)
        
        # Modules
        self.browser = BrowserAutomation(headless=True)
        self.image_processor = ImageProcessor()
        self.gdrive = GDriveIntegrator("credentials.json")
        self.gdrive_folder_id = os.environ.get("GDRIVE_FOLDER_ID", "dummy_folder_id")
        
        # Register standard tools
        self._register_tools()
        
        # Phase 2 Abstractions
        self.llm_provider = GeminiProvider()
        
        self.tool_context = {
            'browser': self.browser,
            'image_processor': self.image_processor,
            'gdrive': self.gdrive,
            'gdrive_folder_id': self.gdrive_folder_id
        }
        
        self.tool_executor = ToolExecutor(
            registry=self.registry,
            idempotency_store=self.idempotency_store,
            retry_manager=self.retry_manager,
            checkpoints=self.checkpoints,
            context=self.tool_context
        )
        
        self.agent_loop = AgentLoop(
            llm_provider=self.llm_provider,
            tool_executor=self.tool_executor,
            tool_registry=self.registry,
            checkpoints=self.checkpoints,
            policy=RunPolicy()
        )

    def _register_tools(self):
        self.registry.register_tool(ShopeeScrapeTool())
        self.registry.register_tool(TikTokScrapeTool())

    async def start(self):
        """Initializes heavy resources."""
        await self.browser.start()
        self.gdrive.authenticate()

    async def stop(self):
        """Cleans up resources."""
        await self.browser.stop()

    async def run(self, user_prompt: str, run_id: Optional[str] = None) -> Optional[str]:
        """
        Executes the full agent loop.
        """
        if not run_id:
            run_id = self.checkpoints.log_task_start(user_prompt)
            
        system_prompt = (
            "You are an autonomous agent designed to scrape products from Shopee and TikTok, "
            "download their images, watermark them, and upload them to Google Drive. "
            "You have access to a set of tools to accomplish this. "
            "Think step-by-step and call tools as needed."
        )
        
        return await self.agent_loop.run(
            run_id=run_id,
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )
