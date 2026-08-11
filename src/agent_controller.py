import os
import re
import asyncio
import logging
import uuid
from typing import Optional
from src.ai_controller import AIController
from src.modules.browser_automation import BrowserAutomation
from src.modules.image_processor import ImageProcessor
from src.modules.gdrive_integrator import GDriveIntegrator
from src.core.tool_registry import ToolRegistry
from src.core.types import ToolCall, ToolResult, ToolStatus
from src.core.errors import AgentException, RateLimitError
from src.tools.shopee_scrape_tool import ShopeeScrapeTool
from src.tools.tiktok_scrape_tool import TikTokScrapeTool
from src.core.checkpoint import CheckpointManager
from src.core.retry import RetryManager
from src.core.idempotency import IdempotencyStore

logger = logging.getLogger(__name__)

class AgentController:
    def __init__(self):
        self.ai = AIController()
        
        # Determine headless mode from env
        headless = os.environ.get("HEADLESS_BROWSER", "true").lower() == "true"
        self.browser = BrowserAutomation(headless=headless)
        
        self.image_processor = ImageProcessor(output_dir="data/images")
        
        gdrive_creds = os.environ.get("GDRIVE_CREDENTIALS_FILE", "credentials.json")
        self.gdrive = GDriveIntegrator(credentials_file=gdrive_creds)
        
        self.gdrive_folder_id = os.environ.get("GDRIVE_TARGET_FOLDER_ID")
        
        # Initialize Tool Registry and register tools
        self.registry = ToolRegistry()
        self.registry.register_tool(ShopeeScrapeTool())
        self.registry.register_tool(TikTokScrapeTool())
        
        # Initialize Checkpoint Manager, Retry Manager, and Idempotency Store
        self.checkpoints = CheckpointManager()
        self.retry_manager = RetryManager(max_retries=3)
        self.idempotency_store = IdempotencyStore()

    async def initialize(self):
        """Initializes async components like the browser and GDrive."""
        await self.browser.start()
        # Move GDrive auth to initialization
        await asyncio.to_thread(self.gdrive.authenticate)

    async def shutdown(self):
        """Cleans up resources."""
        await self.browser.stop()

    async def execute_task(self, task_context: str, run_id: str) -> bool:
        """
        Executes a single task with proper schema validation and tool contract.
        """
        logger.info(f"Processing task context: {task_context}")
        
        tools_schema = self.registry.get_tools_schema()
        try:
            # AIController now boundary-creates the ToolCall
            call: ToolCall = self.ai.plan_action(task_context, tools_schema, run_id)
        except AgentException as e:
            logger.error(f"AI Planning failed: {e.code} - {e.message}")
            return False
            
        self.checkpoints.log_tool_call(run_id, call.call_id, call.name, call.arguments)
        
        # Strict JSON Schema validation
        try:
            self.registry.validate_call(call)
        except ValueError as e:
            logger.error(f"ToolCall validation failed: {e}")
            return False
            
        # Look up tool in registry
        tool = self.registry.get_tool(call.name)
        if not tool:
            logger.warning(f"No tool registered for action: {call.name}")
            return False
            
        context = {
            'browser': self.browser,
            'image_processor': self.image_processor,
            'gdrive': self.gdrive,
            'ai_controller': self.ai,
            'gdrive_folder_id': self.gdrive_folder_id
        }
        
        # Check idempotency store before executing
        cached_result = self.idempotency_store.get(call.idempotency_key)
        if cached_result:
            logger.info(f"Idempotency hit! Returning cached result for {call.name} (Key: {call.idempotency_key})")
            result = cached_result
        else:
            # Execute tool via RetryManager
            try:
                # Pass call and context to tool.execute
                result: ToolResult = await self.retry_manager.execute_with_retry(
                    tool.execute, call=call, context=context
                )
                
                # Save successful result to idempotency store
                if result.status in (ToolStatus.SUCCESS, ToolStatus.PARTIAL_SUCCESS):
                    self.idempotency_store.save(call.idempotency_key, result)
                    
            except AgentException as e:
                logger.error(f"Tool failed after retries: {e.code} - {e.message}")
                return False
            except Exception as e:
                logger.error(f"Unexpected tool execution failure: {e}", exc_info=True)
                return False

        from src.core.types import ToolStatus
        
        if result.status == ToolStatus.PARTIAL_SUCCESS:
            logger.warning(f"Tool executed with partial success: {result.error.message if result.error else 'Unknown'}")
            return True # Treat partial success as completed
        elif result.status == ToolStatus.SUCCESS:
            logger.info(f"Tool executed successfully. Data: {result.data}")
            return True
        else:
            logger.error(f"Tool execution failed: {result.error.message if result.error else 'Unknown'}")
            return False

    async def run_autonomous_loop(self, tasks_file: str = "tasks.txt"):
        """Runs the agent autonomously using CheckpointManager for state."""
        if not os.path.exists(tasks_file):
            logger.info(f"No {tasks_file} found. Creating an empty one.")
            with open(tasks_file, "w", encoding="utf-8") as f:
                f.write("# Paste task contexts here, one per line\n")
            return

        completed_tasks = self.checkpoints.get_completed_tasks()

        with open(tasks_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        pending_tasks = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line not in completed_tasks:
                pending_tasks.append(line)

        if not pending_tasks:
            logger.info("No new tasks found in tasks.txt.")
            return

        logger.info(f"Starting autonomous loop with {len(pending_tasks)} pending tasks.")

        for task_context in pending_tasks:
            run_id = self.checkpoints.log_task_start(task_context)
            logger.info(f"--- Task: {task_context} (Run ID: {run_id}) ---")
            
            # The execution logic (including ToolCall retries) is now handled natively
            success = await self.execute_task(task_context, run_id)
            
            # 0 retries here since RetryManager handles it internally at the Tool level
            self.checkpoints.log_task_end(run_id, success, 0)
            
            if success:
                logger.info(f"Successfully processed {task_context}. Marked as SUCCESS in checkpoint.")
            else:
                logger.error(f"Failed to process {task_context}. Marked as FAILED.")
                
        logger.info("Autonomous loop finished.")
