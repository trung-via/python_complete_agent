import os
import re
import asyncio
import logging
import uuid
from src.ai_controller import AIController
from src.modules.browser_automation import BrowserAutomation
from src.modules.image_processor import ImageProcessor
from src.modules.gdrive_integrator import GDriveIntegrator
from src.core.tool_registry import ToolRegistry
from src.core.types import ToolCall, ToolResult
from src.core.errors import AgentException, RateLimitError
from src.tools.shopee_scrape_tool import ShopeeScrapeTool
from src.tools.tiktok_scrape_tool import TikTokScrapeTool
from src.core.checkpoint import CheckpointManager

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
        
        self.checkpoints = CheckpointManager()

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
        plan = self.ai.plan_action(task_context, tools_schema)
            
        if "error" in plan:
            logger.error(f"Could not create plan: {plan['error']}")
            return False

        action = plan.get("action")
        arguments = plan.get("arguments", {})

        if action == "unknown":
            logger.warning(f"AI determined the request is unknown. Plan: {plan}")
            return False

        # Look up tool in registry
        tool = self.registry.get_tool(action)
        if not tool:
            logger.warning(f"No tool registered for action: {action}")
            return False
            
        call = ToolCall(
            name=action,
            arguments=arguments,
            call_id=str(uuid.uuid4())
        )
        
        self.checkpoints.log_tool_call(run_id, call.call_id, call.name, call.arguments)
        
        # Strict schema validation
        try:
            self.registry.validate_call(call)
        except ValueError as e:
            logger.error(f"ToolCall validation failed: {e}")
            return False
            
        context = {
            'browser': self.browser,
            'image_processor': self.image_processor,
            'gdrive': self.gdrive,
            'ai_controller': self.ai,
            'gdrive_folder_id': self.gdrive_folder_id
        }
        
        try:
            result: ToolResult = await tool.execute(call=call, context=context)
            if result.is_success:
                logger.info(f"Tool executed successfully: {result.data}")
                return True
            elif result.is_partial_success:
                logger.warning(f"Tool executed with partial success: {result.error_message}")
                return True # Treat partial success as completed so we don't retry endlessly
            else:
                logger.error(f"Tool execution failed: {result.error_message}")
                return False
        except RateLimitError as e:
            logger.error(f"Rate limited by target: {e}")
            raise # Re-raise to trigger retry
        except AgentException as e:
            logger.error(f"Agent error during execution: {e}")
            if getattr(e, 'retryable', False):
                raise
            return False
        except Exception as e:
            logger.error(f"Unexpected tool execution failure: {e}", exc_info=True)
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
            success = False
            max_retries = 3
            
            for attempt in range(1, max_retries + 1):
                logger.info(f"--- Task: {task_context} (Attempt {attempt}/{max_retries}) ---")
                
                try:
                    success = await self.execute_task(task_context, run_id)
                    if success:
                        break
                except Exception as e:
                    logger.warning(f"Task threw a retryable exception: {e}")
                    
                if not success and attempt < max_retries:
                    logger.info("Task failed. Retrying in 5 seconds...")
                    await asyncio.sleep(5)
            
            self.checkpoints.log_task_end(run_id, success, attempt - 1)
            
            if success:
                logger.info(f"Successfully processed {task_context}. Marked as SUCCESS in checkpoint.")
            else:
                logger.error(f"Failed to process {task_context} after {max_retries} attempts. Marked as FAILED.")
                
        logger.info("Autonomous loop finished.")
