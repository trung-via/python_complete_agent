from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

from src.agent.loop import AgentLoop
from src.agent.policy import RunPolicy
from src.agent.production_readiness import ProductionReadinessChecker
from src.agent.replay_engine import ReplayEngine
from src.core.checkpoint import CheckpointManager
from src.core.checkpoint_contract import (
    CheckpointCorruptionError,
    CheckpointEventType,
    CheckpointStateError,
)
from src.core.errors import SystemStateError
from src.core.idempotency_store_v2 import JsonlIdempotencyStore
from src.core.retry import RetryManager, RetryPolicy
from src.core.tool_executor import ToolExecutor
from src.core.tool_registry import ToolRegistry
from src.integrations.playwright.manager import PlaywrightBrowserManager
from src.modules.gdrive_integrator import GDriveIntegrator
from src.modules.image_processor import ImageProcessor
from src.providers.base import LLMProvider
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
    Main orchestration class for the autonomous e-commerce product agent.

    Provides canonical lifecycle methods:
    - start() / initialize(): verifies ProductionReadinessChecker, then initializes external resources (fails closed on failure).
    - stop() / shutdown(): idempotent resource cleanup (safe in finally).
    - run(): single-prompt execution through AgentLoop.
    - run_autonomous_loop(): snapshot-bounded file-queue processing (tasks.txt -> completed.txt) with fatal-state fail-closed semantics.
    """

    def __init__(
        self,
        db_path: str = "data/checkpoints.jsonl",
        idempotency_path: str = "data/idempotency_store_v2.jsonl",
        llm_provider: Optional[LLMProvider] = None,
        policy: Optional[RunPolicy] = None,
        retry_policy: Optional[RetryPolicy] = None,
        browser_manager: Optional[PlaywrightBrowserManager] = None,
        image_processor: Optional[ImageProcessor] = None,
        gdrive: Optional[GDriveIntegrator] = None,
        gdrive_folder_id: Optional[str] = None,
        tool_registry: Optional[ToolRegistry] = None,
        checkpoint_manager: Optional[CheckpointManager] = None,
        idempotency_store: Optional[JsonlIdempotencyStore] = None,
    ) -> None:
        self.registry = tool_registry or ToolRegistry()
        self.checkpoints = checkpoint_manager or CheckpointManager(db_path=db_path)
        self.retry_policy = retry_policy or RetryPolicy()
        self.retry_manager = RetryManager(default_policy=self.retry_policy)
        self.idempotency_store = idempotency_store or JsonlIdempotencyStore(
            db_path=idempotency_path,
        )

        self.browser_manager = (
            browser_manager if browser_manager is not None
            else PlaywrightBrowserManager(cdp_endpoint="http://127.0.0.1:9222")
        )
        self.image_processor = image_processor or ImageProcessor()
        self.gdrive = gdrive or GDriveIntegrator("credentials.json")
        self.gdrive_folder_id = gdrive_folder_id or os.environ.get(
            "GDRIVE_FOLDER_ID",
            "dummy_folder_id",
        )

        # Only register default tools if using a fresh registry
        if tool_registry is None:
            self._register_tools()

        self.llm_provider = llm_provider or GeminiProvider()

        # Coherent context dictionary supporting both 'browser' and 'browser_manager'
        self.tool_context: Dict[str, Any] = {
            "browser_manager": self.browser_manager,
            "browser": self.browser_manager,
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

        self.policy = policy or RunPolicy()
        self.agent_loop = AgentLoop(
            llm_provider=self.llm_provider,
            tool_executor=self.tool_executor,
            tool_registry=self.registry,
            checkpoints=self.checkpoints,
            policy=self.policy,
        )

    def _register_tools(self) -> None:
        self.registry.register_tool(NavigateTool(self.browser_manager))
        self.registry.register_tool(ClickTool(self.browser_manager))
        self.registry.register_tool(TypeTextTool(self.browser_manager))
        self.registry.register_tool(PressTool(self.browser_manager))
        self.registry.register_tool(ScreenshotTool(self.browser_manager))
        self.registry.register_tool(InspectTool(self.browser_manager))
        self.registry.register_tool(ShopeeScrapeTool())
        self.registry.register_tool(TikTokScrapeTool())

    async def start(self) -> None:
        """
        Canonical startup method:
        1. Evaluates ProductionReadinessChecker preflight gate.
        2. Fails closed (raises SystemStateError) if NOT_READY.
        3. Initializes required external dependencies (GDrive authentication). Fails closed if auth fails.
        """
        logger.info("Evaluating production readiness gate...")
        report = ProductionReadinessChecker.evaluate_agent(self.agent_loop)
        if not report.ready:
            failed_checks = [f"{c.name}: {c.reason}" for c in report.checks if not c.passed]
            error_msg = f"Production readiness check failed: {'; '.join(failed_checks)}"
            logger.error(error_msg)
            raise SystemStateError(error_msg)

        logger.info("Production readiness check passed. Initializing external resources...")
        if self.gdrive:
            try:
                self.gdrive.authenticate()
            except Exception as exc:
                error_msg = f"Google Drive initialization failed: {exc}"
                logger.error(error_msg)
                raise SystemStateError(error_msg) from exc

    async def initialize(self) -> None:
        """Compatibility alias for start()."""
        await self.start()

    async def stop(self) -> None:
        """
        Canonical shutdown method:
        Idempotently cleans up resources (browser sessions, etc.).
        Safe to call multiple times and from finally blocks.
        """
        logger.info("Shutting down AgentController resources...")
        if self.browser_manager:
            try:
                await self.browser_manager.close_all()
            except Exception as exc:
                logger.warning(f"Error during browser cleanup: {exc}")

    async def shutdown(self) -> None:
        """Compatibility alias for stop()."""
        await self.stop()

    async def run(
        self,
        user_prompt: str,
        run_id: Optional[str] = None,
    ) -> Optional[str]:
        """Execute a single agent run for user_prompt."""
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

    async def run_autonomous_loop(
        self,
        tasks_file: str = "tasks.txt",
        completed_file: str = "completed.txt",
    ) -> List[str]:
        """
        Minimal bounded autonomous file-queue loop.
        
        Semantics:
        1. Reads a snapshot of tasks_file. Missing file returns [].
        2. Ignores blank lines and comments (#).
        3. Loads completed_file if present to skip already completed tasks.
        4. Deduplicates tasks within the snapshot preserving file order.
        5. Processes each remaining task sequentially via self.run().
        6. Appends to completed_file with immediate flush/fsync only after successful completion.
        7. Failed/halted/cancelled tasks are NOT marked completed.
        8. Fatal system state / storage corruption failures immediately fail closed and stop the queue.
        9. Continues to next task on ordinary task failure.
        10. Strictly bounded to snapshot (does not poll indefinitely).
        """
        if not os.path.exists(tasks_file):
            logger.warning(f"Tasks file not found: {tasks_file}")
            return []

        # 1. Read tasks snapshot
        raw_tasks: List[str] = []
        try:
            with open(tasks_file, "r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped and not stripped.startswith("#"):
                        raw_tasks.append(stripped)
        except OSError as exc:
            logger.error(f"Error reading tasks file {tasks_file}: {exc}")
            raise

        # 2. Read completed set
        completed_set: set[str] = set()
        if os.path.exists(completed_file):
            try:
                with open(completed_file, "r", encoding="utf-8") as f:
                    for line in f:
                        stripped = line.strip()
                        if stripped and not stripped.startswith("#"):
                            completed_set.add(stripped)
            except OSError as exc:
                logger.error(f"Error reading completed file {completed_file}: {exc}")
                raise

        # 3. Filter and deduplicate preserving order
        tasks_to_process: List[str] = []
        seen_in_snapshot: set[str] = set()
        for t in raw_tasks:
            if t not in completed_set and t not in seen_in_snapshot:
                seen_in_snapshot.add(t)
                tasks_to_process.append(t)

        logger.info(
            f"Loaded {len(raw_tasks)} tasks from {tasks_file}, "
            f"{len(completed_set)} already completed, "
            f"{len(tasks_to_process)} remaining to process."
        )

        completed_in_this_run: List[str] = []

        # 4. Process each task
        for task in tasks_to_process:
            logger.info(f"Processing queued task: {task}")
            try:
                run_id = self.checkpoints.log_task_start(task)
            except (CheckpointCorruptionError, CheckpointStateError, OSError) as exc:
                error_msg = f"Fatal checkpoint store integrity error starting task '{task}': {exc}"
                logger.error(error_msg)
                raise SystemStateError(error_msg) from exc

            try:
                result = await self.run(user_prompt=task, run_id=run_id)
            except (KeyboardInterrupt, asyncio.CancelledError):
                logger.warning("Autonomous loop interrupted by user/cancellation.")
                raise
            except (SystemStateError, CheckpointCorruptionError, CheckpointStateError) as exc:
                logger.error(f"Fatal system state error during task '{task}', failing closed: {exc}")
                raise
            except Exception as exc:
                logger.error(f"Ordinary error processing task '{task}': {exc}", exc_info=True)
                continue

            # Post-run checkpoint verification
            try:
                events = ReplayEngine.load_events_for_run(self.checkpoints.db_path, run_id)
            except (CheckpointCorruptionError, CheckpointStateError, OSError) as exc:
                error_msg = f"Fatal checkpoint store integrity error while verifying run '{run_id}': {exc}"
                logger.error(error_msg)
                raise SystemStateError(error_msg) from exc
            except Exception as exc:
                error_msg = f"Unexpected failure loading checkpoint events for run '{run_id}': {exc}"
                logger.error(error_msg)
                raise SystemStateError(error_msg) from exc

            # Check if run ended in fatal RUN_HALTED due to SYSTEM_STATE_ERROR or corruption
            for e in events:
                if e.event_type == CheckpointEventType.RUN_HALTED:
                    reason = str(e.payload.get("reason", ""))
                    if "SYSTEM_STATE_ERROR" in reason or "CORRUPT" in reason or "STORAGE" in reason:
                        error_msg = f"Fatal system state error halted run '{run_id}': {reason}"
                        logger.error(error_msg)
                        raise SystemStateError(error_msg)

            # Check if run completed successfully
            is_completed = any(e.event_type == CheckpointEventType.RUN_COMPLETED for e in events)

            if is_completed and result is not None:
                self._mark_task_completed(completed_file, task)
                completed_set.add(task)
                completed_in_this_run.append(task)
                logger.info(f"Successfully completed task: {task}")
            else:
                logger.warning(f"Task did not complete successfully (is_completed={is_completed}): {task}")

        return completed_in_this_run

    @staticmethod
    def _mark_task_completed(completed_file: str, task: str) -> None:
        """Append completed task to completed_file and flush."""
        parent_dir = os.path.dirname(completed_file)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)

        with open(completed_file, "a", encoding="utf-8") as f:
            f.write(f"{task}\n")
            f.flush()
            os.fsync(f.fileno())
