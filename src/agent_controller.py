import os
import re
import asyncio
import logging
from src.ai_controller import AIController
from src.modules.browser_automation import BrowserAutomation
from src.modules.image_processor import ImageProcessor
from src.modules.gdrive_integrator import GDriveIntegrator
from src.core.tool_registry import ToolRegistry
from src.tools.shopee_scrape_tool import ShopeeScrapeTool
from src.tools.tiktok_scrape_tool import TikTokScrapeTool

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

    async def initialize(self):
        """Initializes async components like the browser."""
        await self.browser.start()

    async def shutdown(self):
        """Cleans up resources."""
        await self.browser.stop()

    async def execute_task(self, user_prompt: str) -> bool:
        """
        The main workflow:
        1. Ask AI Controller to parse the prompt.
        2. Execute the corresponding sub-module action.
        3. Process results (e.g., download images).
        4. Upload to Google Drive.
        Returns True if successful, False otherwise.
        """
        logger.info(f"Received user prompt: {user_prompt}")
        
        # 0. We will rely entirely on Gemini Function Calling now (Phase 2)
        plan = None
        
        # 1. AI Planning (only if fast-path fails)
        if not plan:
            tools_schema = self.registry.get_tools_schema()
            plan = self.ai.plan_action(user_prompt, tools_schema)
            
        if "error" in plan:
            logger.error(f"Could not create plan: {plan['error']}")
            return False

        action = plan.get("action")
        url = plan.get("url")

        if action == "unknown" or not url:
            logger.warning(f"AI determined the request is unknown or missing URL. Plan: {plan}")
            return False

        # 2. Look up tool in registry
        tool = self.registry.get_tool(action)
        if not tool:
            logger.warning(f"No tool registered for action: {action}")
            return False
            
        # 3. Execution
        context = {
            'browser': self.browser,
            'image_processor': self.image_processor,
            'gdrive': self.gdrive,
            'ai_controller': self.ai,
            'gdrive_folder_id': self.gdrive_folder_id
        }
        
        try:
            result = await tool.execute(url=url, context=context)
            if result and result.get("status") == "success":
                return True
            else:
                logger.error(f"Tool execution reported failure: {result}")
                return False
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return False

    async def run_autonomous_loop(self, tasks_file: str = "tasks.txt", completed_file: str = "completed.txt"):
        """Runs the agent autonomously, reading tasks from a file and saving progress."""
        if not os.path.exists(tasks_file):
            logger.info(f"No {tasks_file} found. Creating an empty one.")
            with open(tasks_file, "w", encoding="utf-8") as f:
                f.write("# Paste URLs here, one per line\n")
            return

        # Load completed tasks
        completed_urls = set()
        if os.path.exists(completed_file):
            with open(completed_file, "r", encoding="utf-8") as f:
                for line in f:
                    completed_urls.add(line.strip())

        # Read tasks
        with open(tasks_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        pending_tasks = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line not in completed_urls:
                pending_tasks.append(line)

        if not pending_tasks:
            logger.info("No new tasks found in tasks.txt.")
            return

        logger.info(f"Starting autonomous loop with {len(pending_tasks)} pending tasks.")

        for url in pending_tasks:
            success = False
            retries = 3
            
            for attempt in range(1, retries + 1):
                logger.info(f"--- Task: {url} (Attempt {attempt}/{retries}) ---")
                
                # Make sure browser context is clean or re-created if necessary.
                # In our case, Playwright handles new pages fine.
                
                success = await self.execute_task(url)
                if success:
                    break
                else:
                    if attempt < retries:
                        logger.info("Task failed. Retrying in 5 seconds...")
                        await asyncio.sleep(5)
            
            if success:
                logger.info(f"Successfully processed {url}. Marking as completed.")
                with open(completed_file, "a", encoding="utf-8") as f:
                    f.write(f"{url}\n")
            else:
                logger.error(f"Failed to process {url} after {retries} attempts. Skipping.")
                
        logger.info("Autonomous loop finished.")
