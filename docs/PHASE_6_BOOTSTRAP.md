# Phase 6 M1 — Production Bootstrap & Autonomous Queue

This document specifies the canonical startup lifecycle, production readiness gate enforcement, and bounded autonomous file-queue processing implemented in Phase 6 M1.

---

## 1. Canonical Startup Lifecycle

The production application entry point (`main.py`) and `AgentController` adhere to one canonical lifecycle:

```text
construct AgentController
  → evaluate ProductionReadinessChecker
  → NOT_READY: fail closed (SystemStateError), zero tool / provider side effects
  → READY: initialize external resources (e.g. GDrive authentication)
  → run single prompt OR run bounded autonomous queue
  → stop() / shutdown() in finally block (idempotent resource cleanup)
```

### Public API Methods on `AgentController`

1. **`async def start(self) -> None`**:
   - Canonical initialization method.
   - Evaluates `ProductionReadinessChecker.evaluate_agent(self.agent_loop)`.
   - If `report.ready is False`: Logs all check failures and raises `SystemStateError`.
   - If `report.ready is True`: Authenticates Google Drive and prepares runtime dependencies.
   - Backward-compatible alias: `async def initialize(self) -> None`.

2. **`async def stop(self) -> None`**:
   - Canonical shutdown method.
   - Idempotently terminates browser sessions and cleans up resources.
   - Safe to call multiple times and safe within `finally` blocks (even after partial initialization).
   - Backward-compatible alias: `async def shutdown(self) -> None`.

3. **`async def run(self, user_prompt: str, run_id: Optional[str] = None) -> Optional[str]`**:
   - Runs a single task / prompt through `AgentLoop`.
   - Preserves all Phase 5.6 safety guarantees (cancellation, retry budget, tool idempotency, checkpointing).

4. **`async def run_autonomous_loop(self, tasks_file: str = "tasks.txt", completed_file: str = "completed.txt") -> List[str]`**:
   - Minimal bounded autonomous file-queue loop.

---

## 2. Required Environment & Configuration

Environment variables (stored in `.env` or system environment):
- `GEMINI_API_KEY`: API key for Gemini LLM provider.
- `GDRIVE_FOLDER_ID`: Target Google Drive folder ID for scraped/watermarked media.
- `credentials.json`: OAuth2 credentials for Google Drive integrator.

### Production browser attachment (TASK-126)

The default `AgentController` explicitly constructs
`PlaywrightBrowserManager(cdp_endpoint="http://127.0.0.1:9222")`. Attachment is
lazy: the first `get_or_create_session(run_id)` calls
`chromium.connect_over_cdp` with that endpoint and a finite **30,000 ms connection
timeout**. Controller construction/start does not attach or certify browser
availability, login, or marketplace access.

The operator must start the dedicated persistent Chrome profile, retain any
required login, and leave an open tab. A session borrows exactly
`browser.contexts[0]` and the first non-closed page in that context's existing
page order. Startup neither navigates nor launches a browser or creates a
context/page. A page in a later context cannot replace a missing page in the
first context. Subsequent explicit browser operations may navigate the borrowed
tab. Per-session `BrowserConfig` cannot switch this manager back to launch mode;
CDP rejects non-Chromium types and does not apply headless, executable, viewport,
or user-agent launch settings to borrowed resources. Operation timeouts still
use `BrowserConfig.timeout_seconds`.

Each run retains its cached session; repeated/concurrent acquisition for the
same healthy run attaches once. **Different CDP sessions can share the same
context and page, so browser work must be sequential across runs/consumers.**
The per-run lock only serializes acquisition/close for that run. There is no
context isolation, page allocation, cross-run scheduling, or automatic
reconnection in this mode.

Shutdown (`close_session`, `close_all`, or controller `stop`) removes only that
session's listeners and stops its owned Playwright connection. It leaves the
operator's Chrome process, borrowed context/page, and persistent profile open
and unchanged by cleanup. Partial attachment failure uses the same ownership
boundary. Closing one session does not close another session's borrowed page.

Connection refusal/timeout, missing context/open page, and disconnection fail
closed through the existing browser errors, without a fallback launch. Failed
startup is not cached. Disconnected sessions become `CRASHED`; cached
`CLOSED`/`CRASHED` sessions are rejected rather than silently replaced. The
operator must restore the endpoint and an open tab (and login if needed), then
explicitly close/remove any failed cached session or restart the controller
before requesting another session. Chrome startup/restart, profile management,
login, and manual marketplace checks remain operator responsibilities.

### Explicit isolation path

`PlaywrightBrowserManager()` and direct
`PlaywrightBrowserSession(run_id, BrowserConfig())` retain launch mode. Each
session launches its configured browser and creates a fresh context/page;
browser type, headless mode, executable path, viewport, user agent, and operation
timeout settings retain their prior behavior. Closing releases the owned
context, browser, and Playwright resources.

To use this mode with a controller, inject it explicitly:

```python
isolated_manager = PlaywrightBrowserManager()
agent = AgentController(browser_manager=isolated_manager)
```

An injected manager retains its identity and selected behavior. There is no
environment-based or test-based mode detection. Both session contracts support
`evaluate(script)`, `evaluate(script, arg)`, and `evaluate(script, arg=value)`;
the argument is forwarded unchanged via Playwright's `arg` keyword.

TASK-126's regressions use a mocked Playwright attachment boundary and isolated
headless Chromium with local/in-memory DOM fixtures and blocked incidental
requests. They do not establish live Shopee success, TASK-125 M3 completion, or
M4 capability.

---

## 3. Autonomous File Queue Semantics (`tasks.txt` / `completed.txt`)

The V1 file queue provides simple, crash-conscious, file-backed work list processing without requiring external databases or messaging brokers:

1. **Snapshot Read**: Takes a snapshot of `tasks_file` at start. Missing file returns empty list `[]`.
2. **Comment / Blank Filtering**: Ignores empty lines and lines starting with `#`.
3. **Completion Filtering**: Loads `completed_file` (if present) and skips any task already marked completed.
4. **Order-Preserving Deduplication**: Deduplicates task lines within the same snapshot while strictly preserving file order.
5. **Deterministic Sequential Execution**: Executes remaining tasks one-by-one via `agent.run()`.
6. **Crash-Conscious Completion Marking**:
   - Only tasks whose run ends in terminal `RUN_COMPLETED` with non-None response are appended to `completed_file`.
   - Appending is immediately flushed and synced to disk via `flush()` and `os.fsync()`.
7. **Failure Isolation**:
   - A failed, halted, or cancelled task is **never** appended to `completed_file`.
   - Ordinary task failures are logged and the queue deterministically proceeds to the next task.
   - Fatal system errors (`SystemStateError`, storage corruption) fail closed immediately.
8. **Strictly Bounded**: The loop finishes when all tasks in the startup snapshot have been attempted; it does not poll indefinitely.

---

## 4. Usage Examples

### Running the Autonomous Queue (Production Entry Point)
```bash
python main.py
```

### Running One Manual Task Programmatically
```python
import asyncio
from src.agent_controller import AgentController

async def run_manual_task():
    agent = AgentController()
    try:
        await agent.start()
        result = await agent.run("Scrape product images from https://shopee.vn/example-item")
        print(f"Result: {result}")
    finally:
        await agent.stop()

if __name__ == "__main__":
    asyncio.run(run_manual_task())
```

---

## 5. Tool Context Contract

`AgentController` exposes a unified, coherent `tool_context` dictionary:
- `"browser_manager"`: `PlaywrightBrowserManager` instance.
- `"browser"`: Alias to `browser_manager` for scraper tool compatibility.
- `"image_processor"`: `ImageProcessor` instance.
- `"gdrive"`: `GDriveIntegrator` instance.
- `"gdrive_folder_id"`: String Google Drive folder identifier.

Scraper tools (`ShopeeScrapeTool`, `TikTokScrapeTool`) validate only genuinely required dependencies (`browser`, `image_processor`, `gdrive`) and no longer require an unused `ai_controller` reference.

---

## 6. Known V1 Limitations & Milestone Boundaries

1. **Timeout Scope**: `RunPolicy.timeout_seconds` applies per individual task execution run, not across the entire multi-task queue invocation.
2. **Preflight Scope**: `ProductionReadinessChecker` evaluates local configuration, policy, and storage health; it does not make live network requests to Google Drive or Gemini APIs during preflight.
3. **Queue Scope**: The V1 queue is file-backed and bounded to a single process; it is not a distributed multi-worker scheduler.
4. **Milestone Boundary**: **Product Intelligence (winning product discovery, scoring, knowledge base) is the next milestone (Phase 6 M2/M3)** and is intentionally not included in TASK-010.
