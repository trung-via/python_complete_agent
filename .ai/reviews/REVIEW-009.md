# REVIEW-009 — TASK-009 (Phase 5.6 M6 — Production Readiness Gate)

## Status
CHANGES_REQUIRED

## Re-review Head
- Branch: `ai/task-009`
- Reviewed commit: `76ab9e48656e34c0538a3a70849e2ef82b53be6e`
- Previous reviewed commit: `3e41fd5b41f04acd8056742c937613a55a777390`
- Main baseline: `bfce0eb1b10061ee5ec23d549ef75f1a6f3f4e6f`
- Branch relation to main: ahead 2, behind 0 (fast-forward safe)
- Exact FIX authorization in RESULT: `.ai/reviews/REVIEW-009.md (acefab4a10)`
- Reported focused M6 suite: 21 passed, 0 failed
- Reported full Phase 5.6 integration suite: 43 passed, 0 failed
- Reported full repository suite: 344 passed, 0 failed

## Summary
The first-round blockers were substantially addressed: readiness no longer constructs a persistent idempotency store during inspection, the missing-store path is non-mutating, exact RecordKey matching replaced the previous same-tool heuristic, and the M6 safety matrix now exercises real retry/terminal and budget-dedup boundaries. The branch remains fast-forward safe and all reported suites are green.

Two correctness blockers remain in the readiness contract.

## Blocking Finding 1 — The new read-only idempotency parser does not validate the actual persisted store contract

### Location
`src/agent/production_readiness.py` — `parse_idempotency_store_read_only()`.

The parser currently validates only a subset of the production JSONL record schema: key, status, and `updated_at`. It reads `owner_id` and `attempt` but does not validate them, defaults a missing `attempt` to 1, and does not require/validate `created_at` or `data`.

That is weaker than `JsonlIdempotencyStore._record_from_dict()` / `_validate_record()`, which require and validate the persisted contract including:
- `created_at` and `updated_at` numeric values;
- non-empty `owner_id`;
- integer `attempt >= 1` (bool is not accepted);
- `data` being object or null;
- `updated_at >= created_at`.

As a result, syntactically valid but structurally impossible store records can currently pass `idempotency_store_health` and contribute to an overall READY report.

The new lifecycle regression demonstrates the gap itself: its supposedly valid persisted records omit `created_at`, which the real store loader would reject, but the readiness parser accepts them far enough to test terminal reopening.

The lifecycle transition check is also too permissive relative to the actual mutation contract. For example it permits terminal → same-terminal and `RECOVERABLE → RECOVERABLE`, while production transitions only originate from `IN_PROGRESS` for complete/fail, and a recoverable record must be reclaimed to `IN_PROGRESS` before another failure transition. Re-claim transitions should also preserve the real attempt/ownership progression instead of ignoring those fields.

### Required Fix
Keep inspection strictly read-only, but validate the same persisted record contract as production.

Preferred direction: reuse/extract a pure record-deserialization/validation helper from the existing idempotency implementation rather than maintaining a weaker second schema. Then validate per-key lifecycle history against the actual allowed persisted transitions, including attempt progression where the existing contract makes it deterministic.

Add regressions proving NOT_READY, file unchanged, for at least:
1. missing/invalid `created_at`;
2. empty/missing `owner_id`;
3. invalid `attempt` (0, negative, bool/non-int);
4. invalid `data` shape;
5. `updated_at < created_at`;
6. impossible lifecycle history such as terminal reopening and an invalid recoverable progression.

## Blocking Finding 2 — Cross-store readiness now rejects a known-safe crash boundary before idempotency is required

### Location
`ProductionReadinessChecker._check_cross_store_consistency()` and `test_cross_store_pending_recoverable_call_missing_record_fails_closed`.

The implementation requires **every** non-terminal `session.pending_tool_calls` entry to already have an idempotency record. But a pending call can exist durably immediately after `LLM_RESPONDED` and before `ToolExecutor` has claimed the idempotency key.

That exact boundary is a supported Phase 5.6 recovery case: crash after the LLM response, before tool execution/claim. On resume, the call can safely create a fresh idempotency claim; the absence of a record is not a cross-store mismatch yet.

The new test named `pending_recoverable_call_missing_record` creates exactly that pre-execution state — `RUN_STARTED → LLM_REQUESTED → LLM_RESPONDED` only — and then expects NOT_READY. It therefore turns a previously verified safe crash/resume state into a production-readiness false negative.

M6.2 C requires a record only where durable history shows idempotency state is **required for safe replay/recovery**. The checker must distinguish:
- pending but never-started tool work: missing idempotency record can be valid;
- a call with durable evidence that execution/attempt/retry began: exact idempotency state is required, and missing/ambiguous state must be NOT_READY;
- completed checkpoint calls: exact COMPLETED idempotency state remains required.

### Required Fix
Use existing durable events to decide when idempotency state becomes mandatory. Do not blanket-require a record for every LLM-produced pending call.

Add focused regressions for:
1. crash after `LLM_RESPONDED` before tool claim, no idempotency record → readiness remains safe/consistent;
2. pending call with durable `TOOL_ATTEMPT_STARTED` / retry evidence but missing exact idempotency record → NOT_READY;
3. exact pending/recoverable idempotency state → READY;
4. completed call with unrelated same-tool record still → NOT_READY.

This preserves both the M5 crash-before-tool recovery invariant and the M6 fail-closed cross-store requirement.

## What Is Fixed Correctly

- Missing-store readiness inspection no longer creates parent directories or `.lock` files.
- The readiness path parses the idempotency data file directly instead of constructing `JsonlIdempotencyStore`.
- Exact RecordKey matching is used for completed calls, so an unrelated same-tool record cannot mask a missing exact record.
- The M6 matrix now creates a real `RETRY_SCHEDULED` boundary before durable terminal/cancellation wins.
- A dedicated STOP-over-retry regression is present.
- Stable-call resume budget dedup is exercised through AgentLoop/resume rather than only direct ToolExecutor replay.
- Windows lock-file growth/contention fix is small and the full reported suite remains green.
- RESULT-009 now includes populated diff stats and correct FIX authorization.

## Durable Evidence Note

`RESULT-009.md` still cannot embed the SHA of the commit that contains itself without a self-reference cycle. As with earlier AIOS tasks, the immutable reviewed head is recorded by this REVIEW artifact after publication. This re-review therefore treats the reviewed commit recorded above as the canonical immutable head reference rather than requiring another self-referential RESULT-only publication cycle.

## Re-review Requirements

Publish one more FIX commit through the exact current REVIEW-009 artifact. Before publish:
1. make read-only idempotency validation contract-equivalent to the production persisted schema/lifecycle;
2. distinguish safe pre-claim pending calls from pending calls whose durable history requires idempotency state;
3. add focused regressions for both cases;
4. keep the readiness path strictly non-mutating;
5. run focused M6, full Phase 5.6 integration, and full repository suites;
6. regenerate RESULT-009 with fresh evidence.

Then the user should only need to say `Review TASK-009` again. Do not merge automatically.
