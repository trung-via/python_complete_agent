# REVIEW-009 — TASK-009 (Phase 5.6 M6 — Production Readiness Gate)

## Status
CHANGES_REQUIRED

## Reviewed Head
- Branch: `ai/task-009`
- Reviewed commit: `3e41fd5b41f04acd8056742c937613a55a777390`
- Main baseline: `bfce0eb1b10061ee5ec23d549ef75f1a6f3f4e6f`
- Branch relation to main: ahead 1, behind 0 (fast-forward safe)
- Exact RUN authorization in RESULT: `.ai/tasks/TASK-009.md (14086def0a)`
- Reported focused M6 suite: 20 passed, 0 failed
- Reported full Phase 5.6 integration suite: 42 passed, 0 failed
- Reported full repository suite: 343 passed, 0 failed

## Summary
The M6 shape is good: a typed READY/NOT_READY contract, six explicit checks, bounded soak tests, and Phase 5.6 documentation are present, with the full repository suite green. However, the current implementation does not yet satisfy several mandatory production-readiness invariants. Most importantly, the supposedly read-only gate mutates filesystem state when inspecting the idempotency store, and cross-store verification can return READY for semantic mismatches that M6 explicitly requires to fail closed.

## Blocking Finding 1 — Readiness is not strictly read-only for the idempotency store

### Location
`src/agent/production_readiness.py` — `_check_idempotency_store()`.

For both an existing store and especially a missing store, the checker constructs `JsonlIdempotencyStore(db_path=...)` and then calls `get_all_records()`.

The current `JsonlIdempotencyStore` constructor is not a read-only parser. It:
- calls `_ensure_parent_directory()` (creates directories),
- enters `_store_lock()`,
- `_store_lock()` opens `<db_path>.lock` with `a+b`, which creates/modifies the lock file,
- on Windows `_acquire_os_lock()` writes a byte to an empty lock file.

So a readiness evaluation can create directories and lock files even when the data store itself does not exist. That violates M6.1/M6.2 D and the acceptance criteria requiring zero store mutation.

The current regression `test_readiness_evaluation_is_strictly_read_only` only compares the JSONL data-file sizes after the store has already been constructed; it does not detect creation/modification of the lock file or parent directory.

### Required Fix
Use a genuinely read-only idempotency inspection path. Keep production mutation/locking semantics unchanged.

Acceptable direction:
- add a small read-only snapshot/validation helper that parses the JSONL without constructing a mutating `JsonlIdempotencyStore`; or
- add an explicitly read-only store inspection API that does not create directories, lock files, temp files, or data files.

For a missing store path, return a fresh-runtime result without constructing the persistent store.

Add regressions that assert readiness does not create or modify:
- the JSONL data file,
- the `.lock` file,
- the parent directory when it did not exist,
- existing file mtimes/content.

## Blocking Finding 2 — Idempotency structural health does not detect persisted lifecycle inconsistency

M6 requires malformed **or internally inconsistent persisted records** to be NOT_READY.

The current health check delegates to `JsonlIdempotencyStore` loading. That loader validates record shape and timestamp monotonicity, but it does not validate the persisted lifecycle history for a canonical key. For example, a later record can move a key from terminal `COMPLETED`/`FAILED` back to `IN_PROGRESS` with a newer timestamp and still be accepted by the loader, even though the idempotency contract says terminal transitions cannot reopen that way.

### Required Fix
During the read-only structural scan, validate per-key persisted lifecycle invariants without mutating the store. At minimum fail closed on impossible transitions, attempt/ownership progression that contradicts the current idempotency contract, or terminal reopening.

Add a deterministic regression with a syntactically valid JSONL file containing an impossible lifecycle transition and prove:
- readiness is NOT_READY,
- the file is unchanged.

Do not add a second idempotency engine; this is validation of the existing contract only.

## Blocking Finding 3 — Cross-store consistency can miss the exact mismatch M6 requires

### Location
`ProductionReadinessChecker._check_cross_store_consistency()` delegates to `RunIntegrityVerifier.verify()`.

The existing verifier only cross-checks `session.completed_tool_calls`; it does not verify pending/recoverable logical calls. M6 explicitly requires a recoverable/pending logical-call mismatch to be NOT_READY.

Also, for completed calls the verifier searches for **any** COMPLETED idempotency record with the same tool operation scope. It does not require the exact expected `RecordKey`/idempotency identity for that logical operation. Therefore an unrelated completed record for the same tool can mask a missing record and produce a false READY.

### Required Fix
Make M6 cross-store verification exact enough to prove safe replay/recovery:
- derive the exact current idempotency identity/`RecordKey` using the existing `ToolCall`/store semantics; do not invent new identity rules;
- verify pending/recoverable calls whose durable replay requires idempotency state;
- ensure an unrelated record for the same tool cannot satisfy the check;
- ambiguous/missing state must be NOT_READY.

Add regressions for:
1. pending/recoverable checkpoint call with missing required idempotency state => NOT_READY;
2. missing exact record plus an unrelated COMPLETED record for the same tool => still NOT_READY;
3. exact consistent state => READY.

## Blocking Finding 4 — The M6 safety matrix does not actually cover all required precedence rules

The new matrix has useful tests, but two required relationships are not demonstrated by the M6 tests themselves:

1. `test_safety_matrix_cancellation_precedence_over_scheduled_retry` pre-cancels the run before `AgentLoop.run()` starts. It does not create a retryable failure, durably write `RETRY_SCHEDULED`, then prove cancellation wins before attempt N+1. The test name claims a scheduled-retry race that it never exercises.

2. The task explicitly requires `RetryPolicyEngine STOP > retry continuation`; there is no compact M6 matrix regression for this rule.

3. The stable-call test executes `ToolExecutor` twice and proves no duplicate side effect, but it does not exercise AgentLoop/resume budget accounting, so it does not prove `stable call_id > duplicate logical budget charge` inside the M6 matrix.

Existing M1–M5 regressions should remain green, but M6.5 explicitly asks for a compact final precedence verification matrix. Add focused M6 regressions that exercise the real boundaries rather than only relying on older suites.

## Finding 5 — RESULT-009 durable evidence is incomplete

`RESULT-009.md` has good test counts and authorization, but:
- the Diff Stat block is empty;
- it does not record the published task-head SHA / immutable reviewed-head reference required by M6.7.

Regenerate the final FIX result with complete evidence. As in earlier tasks, the immutable reviewed head can be recorded through the publish/review contract without attempting an impossible self-referential SHA inside the same commit; the final evidence should make the reviewed head unambiguous.

## What Is Already Good

- Branch is exactly one commit ahead of current main and not behind.
- Full reported suite is 343/343 passing.
- Focused M6 suite reports 20/20 passing.
- The production-readiness model is typed and fail-closed at the report level.
- No AIOS/bridge changes are included.
- No live provider/network health checks or auto-repair were introduced.
- Documentation correctly frames provider/network availability as outside preflight scope.

## Re-review Requirements

Publish a FIX commit through the exact current REVIEW-009 artifact. Before publishing:
1. make idempotency readiness inspection truly read-only, including lock/directory behavior;
2. validate persisted idempotency lifecycle consistency;
3. make cross-store checks exact and cover pending/recoverable calls;
4. complete the M6 precedence matrix with real scheduled-retry/STOP/budget-dedupe boundaries;
5. run focused M6 tests, the full Phase 5.6 integration suite, and the full repository suite;
6. regenerate RESULT-009 with complete durable evidence.

Then the user should only need to say `Review TASK-009` again. Do not merge automatically.
