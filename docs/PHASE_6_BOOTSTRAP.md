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

### Authenticated browser boundary

The production `AgentController` explicitly constructs its browser manager in
Chromium CDP mode with the exact endpoint `http://127.0.0.1:9222`. The operator
is responsible for starting persistent Chrome with remote debugging enabled at
that endpoint and authenticating the required marketplace session before the
agent starts. This boundary does not automate login, profile setup, CAPTCHA, or
any other authentication step.

CDP startup is deliberately fail closed. It requires the connected browser to
already contain at least one context and requires that context's page list to
contain a non-closed page. The agent borrows the first context and the first
non-closed page in their existing order. A refused or timed-out connection,
unsupported non-Chromium configuration, missing context, missing usable page,
or later browser/page disconnection fails the browser session. Production never
falls back to launching a separate browser and never creates or navigates a page
during attachment.

The persistent Chrome process, selected context, and selected page remain
operator-owned. Agent cleanup removes only its listeners and stops its own
Playwright connection; it never closes those borrowed resources. Runs are
sequential and share the selected page, so the operator must avoid concurrently
driving that page while agent work is active.

`PlaywrightBrowserManager()` with no CDP endpoint remains the isolated launch
path for tests and callers that intentionally need an agent-owned browser,
context, and page. Its cleanup continues to close those launch-owned resources.
Passing an explicit browser manager to `AgentController` preserves that exact
manager and its selected mode.

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
4. **Milestone Boundary**: M2 through M4 remain closed and unchanged. This
   post-M4 bootstrap extension establishes only the P1 live-acquisition browser
   transport boundary; source-evidence intake, governed knowledge updates, live
   provider certification, presentation, and quality/scale work remain separate
   future boundaries.
