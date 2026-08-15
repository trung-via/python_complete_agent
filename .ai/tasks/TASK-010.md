# TASK-010 — Phase 6 M1 Production Bootstrap & Autonomous Queue Closure

## Objective
Close the gap between the now-hardened Phase 5.6 runtime and the actual application entry point so the repository has one coherent, tested, production-safe way to start autonomous product-ingestion work.

This is a **bootstrap/wiring closure task**, not a new orchestration framework and not the Product Intelligence milestone yet.

Canonical baseline when authored:
- `main`: `e332ee142afc04da62e8ca73ba0819047a5b139b`
- Phase 5.6 M1–M6: merged and complete
- AIOS Bridge: v0.4.0 zero-touch handoff

After this task, the next planned direction is:
1. Phase 6 M2 — Product Intelligence / Winning Product Discovery
2. Phase 6 M3 — Canonical Product Knowledge Base

Do not implement M2/M3 in TASK-010.

---

## Current Wiring Gaps To Close

### A. Entry-point/controller lifecycle mismatch
`main.py` currently calls:
- `agent.initialize()`
- `agent.run_autonomous_loop()`
- `agent.shutdown()`

But the current `AgentController` exposes:
- `start()`
- `stop()`
- `run()`

The production entry point therefore references lifecycle methods that are not present on the current controller.

### B. Production readiness is implemented but not wired into startup
Phase 5.6 M6 added `ProductionReadinessChecker`, but `main.py` does not currently enforce READY before autonomous execution begins.

### C. Scraper tool context does not match controller wiring
`AgentController.tool_context` currently provides `browser_manager`, while Shopee/TikTok scraper tools read `context['browser']`. The scraper tools also require `ai_controller` even though that dependency is not part of the current controller context.

This mismatch must be resolved minimally and coherently so the registered production scraper tools can actually execute under the current controller.

### D. Existing file queue has no canonical tested autonomous-loop contract
The repository already has `tasks.txt` and `completed.txt`, but the current controller does not expose a working autonomous queue loop matching `main.py`.

TASK-010 must define the minimal V1 queue semantics without inventing a scheduler/database/worker framework.

---

## M1.1 — Canonical Controller Lifecycle

Choose and implement one canonical public lifecycle for production startup.

Preferred minimal direction:
- retain `start()`, `stop()`, and `run()` as core controller methods;
- either update `main.py` to use those methods directly, or add small compatibility wrappers only if they materially improve clarity/backward compatibility;
- no duplicate lifecycle implementations with divergent behavior.

Required behavior:
- heavy/external initialization happens once;
- shutdown is safe in `finally` and can be called after partial initialization;
- no undefined method calls remain in the production entry point;
- repeated shutdown should not create unsafe side effects or crash due to already-closed browser resources.

Do not redesign `AgentLoop`.

---

## M1.2 — Enforce Production Readiness Before Autonomous Side Effects

Wire the existing Phase 5.6 readiness gate into the smallest appropriate startup boundary.

Required order:

```text
construct dependencies
→ evaluate ProductionReadinessChecker
→ NOT_READY: fail closed, no autonomous provider/tool work
→ READY: initialize external resources
→ process autonomous queue
→ shutdown
```

Requirements:
- use the existing `ProductionReadinessChecker`; do not duplicate its policy/store validation;
- readiness failure must be visible and actionable;
- NOT_READY must prevent LLM requests and scraper/tool side effects;
- no live LLM/network request may be used as a readiness probe;
- preserve all Phase 5.6 cancellation/retry/budget/idempotency semantics.

Tests must prove a NOT_READY startup does not invoke the LLM provider or execute a tool.

---

## M1.3 — Fix Production Tool Context Contract

Make the controller and registered Shopee/TikTok scraper tools agree on one context contract.

Current mismatch to resolve:
- controller provides `browser_manager`;
- scrapers request `browser`;
- scrapers currently require `ai_controller`.

Preferred direction:
- use the actual dependency name/type already owned by the controller;
- remove accidental/unused dependency requirements rather than injecting unnecessary self-references;
- if compatibility aliases are retained, keep them explicit and documented;
- both Shopee and TikTok tools must receive the same coherent context shape.

Acceptance:
- a tool wiring smoke test can construct the real `AgentController` dependencies with fakes/stubs and pass scraper dependency validation without external network access;
- missing genuinely required dependencies still fail clearly.

Do not rewrite scraper extraction logic in this task.

---

## M1.4 — Minimal Autonomous File-Queue Contract

Implement a bounded V1 autonomous queue using the existing repository concepts:
- `tasks.txt`
- `completed.txt`

This is a simple file-backed work list, not a distributed scheduler.

Required semantics:
1. Read a snapshot of `tasks.txt` at invocation start.
2. Ignore blank lines and comment lines beginning with `#`.
3. Treat exact task strings/URLs as identities for this V1; do not invent aggressive URL canonicalization that could change meaning.
4. Load `completed.txt` if it exists; missing file is valid.
5. Skip tasks already present in `completed.txt`.
6. Process each remaining task at most once in that invocation, in deterministic file order.
7. Mark a task completed only after its agent run finishes successfully according to the existing run/terminal contract.
8. Failed, halted, cancelled, or exception paths must not mark the task completed.
9. One task failure must be handled deterministically; choose and document whether the current V1 continues to later tasks or stops. Prefer continuing unless a system-state/readiness/storage failure requires fail-closed shutdown.
10. The loop is bounded to the startup snapshot; it must not poll forever waiting for new lines.

Completion persistence should be simple but crash-conscious:
- append only after successful completion;
- flush the completed record before moving on;
- avoid duplicate completion entries within one invocation.

Do not add SQLite/Redis/Celery/queue services in TASK-010.

---

## M1.5 — Preserve Reliable Run Semantics

Autonomous queue execution must delegate actual work through the existing controller/AgentLoop path rather than bypassing Phase 5.6 controls.

Required invariants:
- each queued task becomes a normal Agent run;
- cancellation remains authoritative;
- terminal states remain immutable;
- run budgets remain enforced;
- tool retries remain governed by the existing RetryPolicyEngine/RetryManager;
- stable tool-call idempotency behavior is untouched;
- storage corruption/system-state failures still fail closed.

Do not introduce a second retry loop around failed tasks that could multiply tool side effects or bypass run budgets.

---

## M1.6 — Bootstrap / Queue Integration Tests

Add focused deterministic tests, suggested location:

`tests/integration/test_phase6_bootstrap.py`

Cover at least:

1. `main`/bootstrap uses only existing canonical controller methods.
2. READY startup proceeds to initialization and queue processing.
3. NOT_READY startup blocks provider/tool execution.
4. shutdown runs from `finally` after success.
5. shutdown runs after a processing exception/partial initialization.
6. `tasks.txt` parsing ignores blanks/comments.
7. tasks already in `completed.txt` are skipped.
8. duplicate task lines in the same input snapshot execute at most once.
9. successful task is appended to `completed.txt` only after success.
10. failed/halted task is not appended to `completed.txt`.
11. deterministic file order is preserved.
12. one ordinary task failure does not corrupt queue bookkeeping.
13. production scraper context wiring passes with fake browser/image/GDrive dependencies.
14. missing required scraper dependency still produces a clear failure.
15. no external network, real Gemini, browser website, or Google Drive dependency is required by the focused test suite.

If practical, add a small entry-point smoke test proving `main.py` no longer references nonexistent controller methods.

---

## M1.7 — Documentation

Add/update a short production bootstrap document, suggested:

`docs/PHASE_6_BOOTSTRAP.md`

Document:
- canonical startup lifecycle;
- readiness-before-execution order;
- required environment/configuration;
- `tasks.txt` / `completed.txt` queue semantics;
- success/failure behavior;
- how to run one manual task vs autonomous queue;
- known V1 limitations;
- explicit statement that Product Intelligence discovery is the next milestone, not part of this queue.

Keep documentation aligned with actual code; do not describe APIs that do not exist.

---

## Acceptance Criteria

TASK-010 is ready for review only if all are true:

- `main.py` has no stale calls to undefined controller lifecycle methods;
- one canonical startup/shutdown path exists;
- `ProductionReadinessChecker` is enforced before autonomous provider/tool execution;
- NOT_READY fails closed;
- Shopee/TikTok production tool context mismatch is resolved;
- the existing file queue can process pending tasks deterministically;
- completed bookkeeping only advances on successful runs;
- no new scheduler/retry/checkpoint/idempotency framework is introduced;
- Phase 5.6 behavior remains backward compatible;
- focused Phase 6 bootstrap tests pass;
- full repository test suite passes;
- documentation reflects the implementation.

---

## Required Verification

Run at minimum:

```powershell
.\venv\Scripts\python -m pytest tests/integration/test_phase6_bootstrap.py -v
.\venv\Scripts\python -m pytest tests/ -q -W ignore
```

Also run any directly affected scraper/controller tests if they exist.

No live production credentials should be required for test execution.

---

## RESULT-010 Requirements

Publish `.ai/results/RESULT-010.md` containing:
- `STATUS: READY_FOR_REVIEW` only when acceptance criteria are met;
- Task: `TASK-010`;
- action (`RUN` or `FIX`);
- exact authorized task/review artifact reference required by AIOS Bridge v0.4.0;
- branch name;
- files changed;
- concise diff stat;
- exact focused test command + exit code + pass count;
- exact full-suite command + exit code + total pass count;
- current task branch commit SHA where workflow permits durable reporting;
- short summary of lifecycle/readiness/queue/context fixes;
- known limitations retained intentionally.

---

## Non-Goals

Do **not** in TASK-010:
- implement winning-product discovery/scoring;
- build a canonical Product Knowledge Base;
- add content generation/video generation;
- add affiliate publishing/distribution;
- add analytics/optimization loops;
- redesign AgentLoop, checkpointing, retry, idempotency, or cancellation;
- add a distributed queue, task broker, daemon, scheduler, or database solely for the file queue;
- rewrite Shopee/TikTok scraping algorithms unless necessary to fix the dependency-context contract;
- change AIOS Bridge semantics;
- auto-merge.

---

## Human Gate

Implementation begins only after explicit:

`/aios-worker RUN TASK-010`

After publication, review is performed from GitHub with:

`Review TASK-010`

Merge remains an explicit separate human gate:

`Merge TASK-010`
