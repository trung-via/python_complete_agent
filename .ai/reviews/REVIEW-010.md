# REVIEW-010 — TASK-010 (Phase 6 M1 Production Bootstrap & Autonomous Queue Closure)

## Status
CHANGES_REQUIRED

## Reviewed Head
- Branch: `ai/task-010`
- Reviewed commit: `21bd9ae96c9295a1763ceb7c8a04b9b5416913a0`
- Main baseline: `e332ee142afc04da62e8ca73ba0819047a5b139b`
- Branch relation to main: ahead 1, behind 0 (fast-forward safe)
- Exact RUN authorization in RESULT: `.ai/tasks/TASK-010.md (80850fe722)`
- Reported focused Phase 6 bootstrap suite: 13 passed, 0 failed
- Reported full repository suite: 370 passed, 0 failed

## Summary
The bootstrap wiring is substantially improved: `main.py` now calls canonical `start()` / `run_autonomous_loop()` / `stop()`, the Phase 5.6 readiness gate runs before external initialization, scraper context wiring is coherent, and the bounded file queue implements deterministic snapshot/order/dedup/completion behavior.

Two production-safety gaps remain and block approval because they violate TASK-010's explicit fail-closed contract.

## Blocking Finding 1 — Fatal system/storage corruption can be downgraded to an ordinary task failure and the queue continues

### Location
`src/agent_controller.py` — `run_autonomous_loop()` together with existing `src/agent/loop.py` failure behavior.

TASK-010 requires that ordinary task failures may continue, but system-state/readiness/storage/corruption failures must fail closed and stop autonomous processing.

Current behavior does not guarantee that:

1. `AgentLoop` catches `SystemStateError` during tool execution, writes a `RUN_HALTED` event, and returns `None` rather than propagating the exception.
2. `run_autonomous_loop()` then sees a non-completed run, logs a warning, and continues to the next queued task.
3. `ReplayEngine.load_events_for_run(...)` in the queue verification path can raise `CheckpointCorruptionError`, `CheckpointStateError`, or checkpoint I/O errors; these are currently caught by the broad `except Exception` branch and likewise treated as an ordinary task failure.

This means a persistence/idempotency/checkpoint integrity failure can permit later autonomous provider/tool work, contrary to M1.4 #9 and M1.5.

### Required Fix
Make the queue distinguish ordinary business/task failure from fatal runtime-state failure without redesigning `AgentLoop`.

At minimum:
- checkpoint corruption/state/inspection I/O errors during post-run verification must be converted to/propagated as fatal `SystemStateError` and terminate the queue;
- if the completed run inspection shows a fatal `RUN_HALTED` caused by `SYSTEM_STATE_ERROR` / storage integrity failure, terminate the queue instead of continuing;
- do not introduce a second retry loop;
- retain continuation for ordinary `RUN_FAILED` / non-system task failures.

Add focused regressions proving a fatal tool-side `SystemStateError` and checkpoint corruption stop the queue before a later task executes.

## Blocking Finding 2 — Required Google Drive initialization failure is swallowed, so startup can report success and begin autonomous work with an unusable production dependency

### Location
`src/agent_controller.py` — `start()`.

After readiness passes, `start()` calls `self.gdrive.authenticate()` inside `try/except Exception` and only logs a warning on failure. It then returns successfully.

For this repository's current production contract, Google Drive is a required dependency of the registered Shopee/TikTok ingestion tools and `docs/PHASE_6_BOOTSTRAP.md` documents `credentials.json` / `GDRIVE_FOLDER_ID` as required configuration. Swallowing authentication failure therefore weakens the previous controller behavior and allows LLM/browser/tool side effects to begin even though the output sink is not initialized.

### Required Fix
Fail startup when a required external initialization step fails:
- propagate the known auth/dependency failure, or wrap it as `SystemStateError` with actionable diagnostics;
- preserve `finally: stop()` safety after partial initialization;
- do not use a live API request as the Phase 5.6 readiness probe — this is initialization after readiness, not part of readiness itself.

Add a focused test proving failed GDrive initialization prevents queue/provider/tool execution and still permits safe shutdown.

## Verification / Evidence Notes

What is correct in the current branch:
- `main.py` no longer references undefined controller methods;
- readiness is evaluated before GDrive authentication;
- Shopee/TikTok no longer require the unused `ai_controller` dependency and accept the controller's browser context;
- queue snapshot parsing ignores blanks/comments, skips completed tasks, deduplicates in order, and appends successful items with `flush()` + `os.fsync()`;
- branch remains a clean fast-forward from current `main`;
- RESULT reports 13 focused tests and 370 full-suite tests passing.

Coverage should be expanded for the two fatal-path gaps above. Also regenerate `RESULT-010.md` after FIX with fresh counts and a complete diff stat; the current diff-stat block omits the added docs/tests/result files shown by the actual branch comparison.

## Decision
CHANGES_REQUIRED.

Publish the fix only through the exact current REVIEW-010 artifact. Do not merge automatically. After the FIX is published, the user should request `Review TASK-010` again.
