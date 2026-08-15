from __future__ import annotations

import asyncio
import os
import sys
from typing import Any, Dict, List, Optional
import pytest

import main
from src.agent_controller import AgentController
from src.agent.policy import RunPolicy
from src.agent.production_readiness import ReadinessStatus
from src.core.checkpoint import CheckpointManager
from src.core.errors import AgentException, DependencyError, SystemStateError
from src.core.idempotency_store_v2 import JsonlIdempotencyStore
from src.core.retry import RetryPolicy
from src.core.tool_registry import ToolRegistry
from src.core.types import ToolCall, ToolResult, ToolStatus
from src.providers.base import LLMProvider, LLMResponse, ProviderToolCall
from src.tools.shopee_scrape_tool import ShopeeScrapeTool
from src.tools.tiktok_scrape_tool import TikTokScrapeTool
from tests.support.fault_injection import FaultyLLMProvider


class FakeBrowserSession:
    async def __aenter__(self) -> FakeBrowserSession:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass

    async def goto(self, url: str, **kwargs: Any) -> None:
        pass

    async def wait_for_selector(self, selector: str, **kwargs: Any) -> None:
        pass

    async def wait_for_timeout(self, timeout_ms: int) -> None:
        pass

    async def evaluate(self, script: str, *args: Any) -> Any:
        return None

    async def query_selector(self, selector: str) -> None:
        return None


class FakeBrowserManager:
    def __init__(self) -> None:
        self.closed = False
        self.close_count = 0

    def new_page(self) -> FakeBrowserSession:
        return FakeBrowserSession()

    async def close_all(self) -> None:
        self.closed = True
        self.close_count += 1


class FakeImageProcessor:
    def process_image(self, path: str) -> str:
        return path


class FakeGDrive:
    def __init__(self, should_fail: bool = False) -> None:
        self.authenticated = False
        self.should_fail = should_fail

    def authenticate(self) -> None:
        if self.should_fail:
            raise RuntimeError("OAuth2 token expired or credentials invalid")
        self.authenticated = True


class MockCallingTool:
    def __init__(self, name: str = "mock_task_tool", fatal_on_call: bool = False) -> None:
        self.name = name
        self.description = "mock tool for testing"
        self.calls: List[str] = []
        self.fatal_on_call = fatal_on_call

    def get_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {"input": {"type": "string"}}}

    async def execute(self, call: ToolCall, context: Dict[str, Any]) -> ToolResult:
        self.calls.append(call.arguments.get("input", ""))
        if self.fatal_on_call:
            raise SystemStateError("Fatal hardware storage failure during tool execution")
        return ToolResult(
            call_id=call.call_id,
            run_id=call.run_id,
            tool_name=self.name,
            status=ToolStatus.SUCCESS,
            data={"result": f"processed {call.arguments.get('input', '')}"},
        )


def _build_test_controller(
    tmp_path: Any,
    responses: List[LLMResponse],
    tool: Optional[Any] = None,
    policy: Optional[RunPolicy] = None,
    retry_policy: Optional[RetryPolicy] = None,
    gdrive_should_fail: bool = False,
) -> tuple[AgentController, FakeBrowserManager, FakeGDrive]:
    db_path = str(tmp_path / "checkpoints.jsonl")
    idempotency_path = str(tmp_path / "idempotency.jsonl")
    
    registry = ToolRegistry()
    if tool:
        registry.register_tool(tool)

    browser = FakeBrowserManager()
    gdrive = FakeGDrive(should_fail=gdrive_should_fail)
    image_processor = FakeImageProcessor()
    llm = FaultyLLMProvider(responses)

    controller = AgentController(
        db_path=db_path,
        idempotency_path=idempotency_path,
        llm_provider=llm,
        policy=policy or RunPolicy(max_iterations=5, max_tool_calls=5, timeout_seconds=10),
        retry_policy=retry_policy or RetryPolicy(max_attempts=2, base_delay=0.01),
        browser_manager=browser,  # type: ignore[arg-type]
        image_processor=image_processor,  # type: ignore[arg-type]
        gdrive=gdrive,  # type: ignore[arg-type]
        gdrive_folder_id="test_folder",
        tool_registry=registry,
    )
    return controller, browser, gdrive


# ============================================================================
# M1.1 & M1.2 — Lifecycle & Production Readiness Gate
# ============================================================================

def test_main_entry_point_references_valid_canonical_methods() -> None:
    """Verifies that main.py and AgentController expose valid start/stop/run/run_autonomous_loop methods."""
    assert hasattr(AgentController, "start")
    assert hasattr(AgentController, "stop")
    assert hasattr(AgentController, "initialize")
    assert hasattr(AgentController, "shutdown")
    assert hasattr(AgentController, "run")
    assert hasattr(AgentController, "run_autonomous_loop")


@pytest.mark.asyncio
async def test_ready_startup_proceeds_to_initialization(tmp_path: Any) -> None:
    """A valid/ready runtime starts successfully and authenticates GDrive."""
    controller, browser, gdrive = _build_test_controller(tmp_path, [LLMResponse("mock", "1", "OK", [])])
    
    await controller.start()
    assert gdrive.authenticated is True

    await controller.stop()
    assert browser.closed is True


@pytest.mark.asyncio
async def test_not_ready_startup_fails_closed_and_blocks_execution(tmp_path: Any) -> None:
    """
    When ProductionReadinessChecker fails (e.g. corrupted checkpoint store),
    controller.start() raises SystemStateError and does not call LLM or tool.
    """
    db_path = str(tmp_path / "checkpoints.jsonl")
    with open(db_path, "w", encoding="utf-8") as f:
        f.write("CORRUPTED_CHECKPOINT_STORE_DATA\n")

    tool = MockCallingTool()
    controller, browser, gdrive = _build_test_controller(
        tmp_path,
        [LLMResponse("mock", "1", "SHOULD_NOT_EXECUTE", [])],
        tool=tool,
    )

    with pytest.raises(SystemStateError) as exc_info:
        await controller.start()

    assert "Production readiness check failed" in str(exc_info.value)
    assert "checkpoint_store_health" in str(exc_info.value)
    # Proves 0 tool calls executed
    assert len(tool.calls) == 0


@pytest.mark.asyncio
async def test_failed_gdrive_initialization_fails_closed_and_permits_safe_shutdown(tmp_path: Any) -> None:
    """
    If required Google Drive authentication fails during start(),
    controller raises SystemStateError and blocks work, while stop() in finally cleans up safely.
    """
    tool = MockCallingTool()
    controller, browser, gdrive = _build_test_controller(
        tmp_path,
        [LLMResponse("mock", "1", "SHOULD_NOT_EXECUTE", [])],
        tool=tool,
        gdrive_should_fail=True,
    )

    try:
        with pytest.raises(SystemStateError) as exc_info:
            await controller.start()
        assert "Google Drive initialization failed" in str(exc_info.value)
        assert len(tool.calls) == 0
    finally:
        await controller.stop()
        assert browser.closed is True


@pytest.mark.asyncio
async def test_shutdown_runs_safely_in_finally_and_is_idempotent(tmp_path: Any) -> None:
    """controller.stop() (and shutdown()) can be called repeatedly without errors."""
    controller, browser, _ = _build_test_controller(tmp_path, [])
    
    await controller.start()
    await controller.stop()
    assert browser.close_count == 1

    # Repeated shutdown
    await controller.shutdown()
    assert browser.close_count == 2


@pytest.mark.asyncio
async def test_shutdown_after_partial_initialization(tmp_path: Any) -> None:
    """Shutdown runs safely even if start() was not called or failed."""
    controller, browser, _ = _build_test_controller(tmp_path, [])
    
    # Direct stop without start
    await controller.stop()
    assert browser.closed is True


# ============================================================================
# M1.3 — Tool Context Contract
# ============================================================================

@pytest.mark.asyncio
async def test_scraper_context_wiring_passes_with_fakes(tmp_path: Any) -> None:
    """
    ShopeeScrapeTool and TikTokScrapeTool accept controller context with
    'browser'/'browser_manager', 'image_processor', and 'gdrive' without requiring ai_controller.
    """
    browser = FakeBrowserManager()
    image_processor = FakeImageProcessor()
    gdrive = FakeGDrive()

    context = {
        "browser_manager": browser,
        "browser": browser,
        "image_processor": image_processor,
        "gdrive": gdrive,
        "gdrive_folder_id": "test_folder",
    }

    shopee_tool = ShopeeScrapeTool()
    tiktok_tool = TikTokScrapeTool()

    # Shopee tool execution with fake browser
    call_shopee = ToolCall(name="shopee_scrape", arguments={"url": "https://shopee.vn/product/1/2"}, call_id="c_s1", run_id="r1")
    result_shopee = await shopee_tool.execute(call_shopee, context)
    assert result_shopee.status in (ToolStatus.SUCCESS, ToolStatus.FAILURE)

    # TikTok tool execution with fake browser
    call_tiktok = ToolCall(name="tiktok_scrape", arguments={"url": "https://tiktok.com/@shop/video/123"}, call_id="c_t1", run_id="r2")
    result_tiktok = await tiktok_tool.execute(call_tiktok, context)
    assert result_tiktok.status in (ToolStatus.SUCCESS, ToolStatus.FAILURE)


@pytest.mark.asyncio
async def test_scraper_missing_required_dependency_fails_clearly() -> None:
    """Missing genuinely required dependencies (e.g. gdrive or browser) raises DependencyError."""
    shopee_tool = ShopeeScrapeTool()
    call = ToolCall(name="shopee_scrape", arguments={"url": "https://shopee.vn/test"}, call_id="c1", run_id="r1")

    # Incomplete context (missing gdrive)
    context = {
        "browser": FakeBrowserManager(),
        "image_processor": FakeImageProcessor(),
    }

    with pytest.raises(DependencyError) as exc_info:
        await shopee_tool.execute(call, context)

    assert "Missing required context components" in str(exc_info.value)
    assert "gdrive" in str(exc_info.value)


# ============================================================================
# M1.4 & M1.5 — Autonomous File-Queue Contract & Fail-Closed Safety
# ============================================================================

@pytest.mark.asyncio
async def test_autonomous_queue_processes_tasks_and_appends_completed(tmp_path: Any) -> None:
    """
    Queue processes tasks.txt, ignores comments and blank lines,
    and appends completed tasks to completed.txt in order.
    """
    tasks_file = str(tmp_path / "tasks.txt")
    completed_file = str(tmp_path / "completed.txt")

    with open(tasks_file, "w", encoding="utf-8") as f:
        f.write("# Product Tasks list\n\nTask 1: Shopee item A\n# Comment line\nTask 2: TikTok item B\n\n")

    responses = [
        LLMResponse("mock", "1", "Completed Task 1", []),
        LLMResponse("mock", "2", "Completed Task 2", []),
    ]
    controller, _, _ = _build_test_controller(tmp_path, responses)
    await controller.start()

    completed = await controller.run_autonomous_loop(tasks_file=tasks_file, completed_file=completed_file)
    assert completed == ["Task 1: Shopee item A", "Task 2: TikTok item B"]

    # Verify completed.txt contents
    with open(completed_file, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
    assert lines == ["Task 1: Shopee item A", "Task 2: TikTok item B"]

    await controller.stop()


@pytest.mark.asyncio
async def test_autonomous_queue_skips_already_completed_tasks(tmp_path: Any) -> None:
    """Tasks already present in completed.txt are skipped."""
    tasks_file = str(tmp_path / "tasks.txt")
    completed_file = str(tmp_path / "completed.txt")

    with open(tasks_file, "w", encoding="utf-8") as f:
        f.write("Task 1: Already Done\nTask 2: New Item\n")

    with open(completed_file, "w", encoding="utf-8") as f:
        f.write("Task 1: Already Done\n")

    responses = [
        LLMResponse("mock", "1", "Completed Task 2", []),
    ]
    controller, _, _ = _build_test_controller(tmp_path, responses)
    await controller.start()

    completed = await controller.run_autonomous_loop(tasks_file=tasks_file, completed_file=completed_file)
    assert completed == ["Task 2: New Item"]

    # Verify completed.txt now has both tasks
    with open(completed_file, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
    assert lines == ["Task 1: Already Done", "Task 2: New Item"]

    await controller.stop()


@pytest.mark.asyncio
async def test_autonomous_queue_deduplicates_duplicate_lines_in_snapshot(tmp_path: Any) -> None:
    """Duplicate task lines in the same input snapshot are processed at most once."""
    tasks_file = str(tmp_path / "tasks.txt")
    completed_file = str(tmp_path / "completed.txt")

    with open(tasks_file, "w", encoding="utf-8") as f:
        f.write("Task Duplicate\nTask Duplicate\nTask Duplicate\n")

    responses = [
        LLMResponse("mock", "1", "Completed Duplicate Task", []),
    ]
    controller, _, _ = _build_test_controller(tmp_path, responses)
    await controller.start()

    completed = await controller.run_autonomous_loop(tasks_file=tasks_file, completed_file=completed_file)
    assert completed == ["Task Duplicate"]

    with open(completed_file, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
    assert lines == ["Task Duplicate"]

    await controller.stop()


@pytest.mark.asyncio
async def test_autonomous_queue_ordinary_task_failure_continues_to_next_task(tmp_path: Any) -> None:
    """
    If a task experiences an ordinary non-fatal failure (e.g. LLM error / AgentException),
    it is NOT appended to completed.txt, and the queue continues to process subsequent tasks.
    """
    tasks_file = str(tmp_path / "tasks.txt")
    completed_file = str(tmp_path / "completed.txt")

    with open(tasks_file, "w", encoding="utf-8") as f:
        f.write("Task 1: Ordinary Failure\nTask 2: Successful Task\n")

    class FlakyProvider(LLMProvider):
        def __init__(self) -> None:
            self.count = 0

        async def generate(self, *args: Any, **kwargs: Any) -> LLMResponse:
            self.count += 1
            if self.count == 1:
                raise AgentException("Transient LLM error", code="PROVIDER_ERR")
            return LLMResponse("mock", "2", "Task 2 Done", [])

    db_path = str(tmp_path / "checkpoints.jsonl")
    idempotency_path = str(tmp_path / "idempotency.jsonl")
    controller = AgentController(
        db_path=db_path,
        idempotency_path=idempotency_path,
        llm_provider=FlakyProvider(),
        browser_manager=FakeBrowserManager(),  # type: ignore[arg-type]
        gdrive=FakeGDrive(),  # type: ignore[arg-type]
        image_processor=FakeImageProcessor(),  # type: ignore[arg-type]
    )
    await controller.start()

    completed = await controller.run_autonomous_loop(tasks_file=tasks_file, completed_file=completed_file)
    assert completed == ["Task 2: Successful Task"]

    # Only Task 2 is in completed.txt
    with open(completed_file, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
    assert lines == ["Task 2: Successful Task"]

    await controller.stop()


@pytest.mark.asyncio
async def test_fatal_system_state_error_in_tool_stops_autonomous_queue(tmp_path: Any) -> None:
    """
    If a fatal SystemStateError occurs during tool execution (e.g. storage integrity failure),
    the run halts with SYSTEM_STATE_ERROR and run_autonomous_loop raises SystemStateError immediately,
    terminating the queue and preventing subsequent tasks from executing.
    """
    tasks_file = str(tmp_path / "tasks.txt")
    completed_file = str(tmp_path / "completed.txt")

    with open(tasks_file, "w", encoding="utf-8") as f:
        f.write("Task 1: Fatal Tool Failure\nTask 2: Should Never Execute\n")

    fatal_tool = MockCallingTool(fatal_on_call=True)
    responses = [
        # LLM calls the fatal tool for Task 1
        LLMResponse(
            provider="mock",
            provider_response_id="1",
            content=None,
            tool_calls=[ProviderToolCall(name="mock_task_tool", arguments={"input": "test_payload"}, provider_call_id="c_fatal_1")],
        ),
        # Task 2 response if it were ever reached
        LLMResponse(provider="mock", provider_response_id="2", content="Task 2 completed", tool_calls=[]),
    ]

    controller, browser, gdrive = _build_test_controller(
        tmp_path,
        responses,
        tool=fatal_tool,
    )
    await controller.start()

    with pytest.raises(SystemStateError) as exc_info:
        await controller.run_autonomous_loop(tasks_file=tasks_file, completed_file=completed_file)

    assert "Fatal system state error" in str(exc_info.value)
    # Proves Task 1 was called, but Task 2 never executed (only 1 tool call made)
    assert len(fatal_tool.calls) == 1

    # Neither task is marked completed
    if os.path.exists(completed_file):
        with open(completed_file, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
        assert len(lines) == 0

    await controller.stop()


@pytest.mark.asyncio
async def test_checkpoint_corruption_during_queue_run_fails_closed_and_stops_queue(tmp_path: Any) -> None:
    """
    If checkpoint store is corrupted during/after task execution,
    post-run verification fails closed (raises SystemStateError) and stops the queue.
    """
    tasks_file = str(tmp_path / "tasks.txt")
    completed_file = str(tmp_path / "completed.txt")

    with open(tasks_file, "w", encoding="utf-8") as f:
        f.write("Task 1: Corrupted Store Task\nTask 2: Subsequent Task\n")

    db_path = str(tmp_path / "checkpoints.jsonl")
    idempotency_path = str(tmp_path / "idempotency.jsonl")

    # Custom LLM provider that corrupts the checkpoint file right after generating response
    class CorruptingLLMProvider(LLMProvider):
        async def generate(self, *args: Any, **kwargs: Any) -> LLMResponse:
            # Corrupt the checkpoint file by appending garbage line
            with open(db_path, "a", encoding="utf-8") as f:
                f.write("MALFORMED_CORRUPTED_CHECKPOINT_LINE\n")
            return LLMResponse("mock", "1", "Completed Task 1", [])

    controller = AgentController(
        db_path=db_path,
        idempotency_path=idempotency_path,
        llm_provider=CorruptingLLMProvider(),
        browser_manager=FakeBrowserManager(),  # type: ignore[arg-type]
        gdrive=FakeGDrive(),  # type: ignore[arg-type]
        image_processor=FakeImageProcessor(),  # type: ignore[arg-type]
    )
    await controller.start()

    with pytest.raises(SystemStateError) as exc_info:
        await controller.run_autonomous_loop(tasks_file=tasks_file, completed_file=completed_file)

    assert "Fatal checkpoint store integrity error" in str(exc_info.value)

    # Task 1 was not marked completed
    if os.path.exists(completed_file):
        with open(completed_file, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
        assert len(lines) == 0

    await controller.stop()


@pytest.mark.asyncio
async def test_autonomous_queue_missing_tasks_file_returns_empty_safely(tmp_path: Any) -> None:
    """Missing tasks.txt returns empty list without error."""
    non_existent = str(tmp_path / "non_existent_tasks.txt")
    controller, _, _ = _build_test_controller(tmp_path, [])
    await controller.start()

    completed = await controller.run_autonomous_loop(tasks_file=non_existent)
    assert completed == []

    await controller.stop()


@pytest.mark.asyncio
async def test_autonomous_queue_preserves_deterministic_order(tmp_path: Any) -> None:
    """Tasks are executed and recorded in strict input file order."""
    tasks_file = str(tmp_path / "tasks.txt")
    completed_file = str(tmp_path / "completed.txt")

    items = [f"Item_{i}" for i in range(5)]
    with open(tasks_file, "w", encoding="utf-8") as f:
        for it in items:
            f.write(f"{it}\n")

    responses = [LLMResponse("mock", str(i), f"Done {it}", []) for i, it in enumerate(items)]
    controller, _, _ = _build_test_controller(tmp_path, responses)
    await controller.start()

    completed = await controller.run_autonomous_loop(tasks_file=tasks_file, completed_file=completed_file)
    assert completed == items

    with open(completed_file, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
    assert lines == items

    await controller.stop()
