# REVIEW-008 — TASK-008 (Phase 5.6 M5 — Fault Injection & Concurrency Verification)

## Status
APPROVED

## Reviewed Head
- Branch: `ai/task-008`
- Reviewed commit: `bfce0eb1b10061ee5ec23d549ef75f1a6f3f4e6f`
- Main baseline: `799aa448385e3058e73b7e905b4127f859396dd0`
- Branch relation to main at review: ahead 3, behind 0 (fast-forward safe)
- Exact FIX authorization in RESULT: `.ai/reviews/REVIEW-008.md (ef416b6655)`

## Test Evidence
- Focused M5 suite: 22 passed, 0 failed
- Full repository suite: 323 passed, 0 failed
- RESULT status: `READY_FOR_REVIEW`

## Approval Summary
All blocking findings from the previous review are closed.

### 1. Retry continuation now fails closed
`ToolExecutor.before_retry_attempt()` no longer returns `True` when durable run-state inspection fails. `RecoveryPotential.CORRUPT` and inspection exceptions are converted to `SystemStateError`, preventing attempt N+1. A regression corrupts checkpoint history between `RETRY_SCHEDULED` and retry continuation and proves the next tool attempt never executes.

Existing retry delay behavior remains unchanged: the retry continuation guard is applied after the existing delay calculation/wait and does not replace `RetryPolicy.get_delay()`, preserving Retry-After/jitter semantics.

### 2. Async same-run/same-call contention is deterministic
The concurrency tests now use a test-only `ContentionAwareIdempotencyStore` plus explicit events. Contender 1 is held inside tool execution while contender 2 is required to complete its competing `claim()` attempt before contender 1 is released.

The tests verify:
- contender 2 actually reaches the claim boundary while the key is in progress;
- contender 2 receives `IDEMPOTENCY_IN_PROGRESS` / yields cleanly;
- exactly one underlying side effect occurs;
- same-run resume checkpoint/idempotency integrity remains valid.

### 3. Real multiprocessing duplicate-side-effect safety is measured
The same-call multiprocessing regression now uses a `multiprocessing.Value` protected by a process-shared lock as an observable external-side-effect counter. Two OS processes contend for the same durable `(run_id, call_id)` and the test asserts the shared side-effect count is exactly 1. The final idempotency record must be `COMPLETED` and the store remains readable.

### 4. Persistence-boundary classification is correct
The persistence regression now injects `OSError` from the real idempotency completion boundary and asserts that `ToolExecutor._complete_v2()` surfaces `SystemStateError` with the established persistence-domain message. The separate raw application/tool `OSError` regression remains in place and verifies it is treated as an ordinary tool failure rather than checkpoint/store infrastructure failure.

### 5. Previous cleanup and safety fixes remain intact
- unreachable stale exception code remains removed;
- `AgentLoop` yields competing resume contenders on `IDEMPOTENCY_IN_PROGRESS` instead of persisting a false tool result;
- cancellation/terminal-before-retry regressions remain present;
- corruption and invalid-transition checks remain fail closed;
- no AIOS/bridge changes are included in TASK-008;
- no auto-merge behavior is introduced.

## Operational Evidence Note
`RESULT-008.md` records exact FIX authorization, focused/full test commands and counts, verified fault classes, and limitations. The immutable reviewed Git commit for this result is recorded above as `bfce0eb1b10061ee5ec23d549ef75f1a6f3f4e6f`; embedding a commit's own final SHA inside the file committed by that same commit would require an additional self-referential/amend publication cycle and is not treated as a blocking safety issue.

## Decision
TASK-008 is approved for the human merge gate.

Do not merge automatically. Merge only after the user explicitly says `Merge TASK-008`.
