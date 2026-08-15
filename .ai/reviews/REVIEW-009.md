# REVIEW-009 — TASK-009 (Phase 5.6 M6 — Production Readiness Gate)

## Status
CHANGES_REQUIRED

## Re-review Head
- Branch: `ai/task-009`
- Reviewed commit: `1bbc20b04dd7e418b901df2a7dd4c3a79dc14d46`
- Previous reviewed commit: `76ab9e48656e34c0538a3a70849e2ef82b53be6e`
- Main baseline: `bfce0eb1b10061ee5ec23d549ef75f1a6f3f4e6f`
- Branch relation to main: ahead 3, behind 0 (fast-forward safe)
- Exact FIX authorization in RESULT: `.ai/reviews/REVIEW-009.md (61aa2d703e)`
- Reported focused M6 suite: 30 passed, 0 failed
- Reported full Phase 5.6 integration suite: 52 passed, 0 failed
- Reported full repository suite: 353 passed, 0 failed

## Summary
The two prior blockers are mostly addressed correctly. The readiness path now reuses the production record deserializer, validates required persisted fields, preserves strict read-only behavior, and distinguishes the safe `LLM_RESPONDED` pre-claim crash boundary from calls whose durable history shows execution began. The reported focused/full suites are green and the branch remains fast-forward safe.

Two remaining correctness gaps prevent final M6 approval.

## Blocking Finding 1 — Persisted lifecycle validation is still weaker than the actual idempotency mutation contract

### Location
`src/agent/production_readiness.py` — `parse_idempotency_store_read_only()`.

The parser now correctly reuses `JsonlIdempotencyStore._record_from_dict()` and checks `updated_at >= created_at`, immutable `created_at`, timestamp monotonicity, terminal reopening, and `RECOVERABLE -> IN_PROGRESS` attempt increment.

However, transitions originating from `IN_PROGRESS` are still validated only by target status. The parser currently accepts impossible histories such as:

```text
IN_PROGRESS owner=A attempt=1
→ COMPLETED owner=B attempt=9
```

or:

```text
IN_PROGRESS owner=A attempt=1
→ RECOVERABLE owner=A attempt=7
```

or a duplicate/reclaim-like:

```text
IN_PROGRESS attempt=1
→ IN_PROGRESS attempt=1
```

The production store cannot persist those histories. `complete()` / `fail()` require the current owner and `_transition_locked()` preserves both `owner_id` and `attempt`; an `IN_PROGRESS -> IN_PROGRESS` append only comes from stale re-claim and increments `attempt` by exactly 1. Existing `NEW` records are also reclaimed to `IN_PROGRESS` with `attempt + 1`, but the readiness lifecycle validator currently has no explicit `NEW` transition rule.

This matters because M6 requires internally inconsistent persisted records to produce `NOT_READY`, not merely schema-valid records.

### Required Fix
Make the read-only lifecycle validator match the transitions the persistent store can actually append:

- `IN_PROGRESS -> COMPLETED|FAILED|RECOVERABLE`: preserve `owner_id`, preserve `attempt`;
- `IN_PROGRESS -> IN_PROGRESS` (stale reclaim): `attempt == prev.attempt + 1`; owner may transfer according to claim semantics;
- `RECOVERABLE -> IN_PROGRESS`: `attempt == prev.attempt + 1`;
- `NEW -> IN_PROGRESS`: `attempt == prev.attempt + 1`;
- terminal records: no later record for that canonical key;
- reject all other persisted transitions.

Add focused regressions for owner change on completion/failure, attempt jumps on completion/failure, same-attempt `IN_PROGRESS -> IN_PROGRESS`, and invalid `NEW` progression.

## Blocking Finding 2 — Completed pre-claim/rejected tool results are still incorrectly required to have idempotency state

### Location
`ProductionReadinessChecker._check_cross_store_consistency()`.

The safe pre-claim pending boundary is fixed: pending calls only require an exact idempotency record after durable execution evidence exists.

But the completed-call branch still requires an exact `COMPLETED` idempotency record for **every** `session.completed_tool_calls` entry.

That is too broad. `ToolExecutor.execute()` logs `TOOL_CALL_CREATED` and can reject a call during validation / missing-tool handling **before any idempotency claim occurs**. `AgentLoop` then durably records the returned failure as `TOOL_RESULT_RECEIVED`. Such a call is legitimately completed in checkpoint history but never needed, and must not have, a persistent idempotency record.

A historical run that safely handled an invalid/rejected provider tool call can therefore make the global production-readiness gate return `NOT_READY` forever due to a nonexistent idempotency record that was never required for replay safety.

### Required Fix
Use durable execution evidence for completed calls too:

- if the call reached `TOOL_ATTEMPT_STARTED` / retry execution evidence, require the exact idempotency record and correct replay-safe status;
- if the call was rejected before claim/execution and then recorded as a completed failure result, absence of an idempotency record is valid;
- preserve exact RecordKey matching for calls that did enter idempotent execution.

Add regressions for:
1. validation-rejected/pre-claim tool call + durable failure result + no idempotency record => readiness remains consistent;
2. actually executed completed call + missing exact record => `NOT_READY`;
3. actually executed completed call + unrelated same-tool record => `NOT_READY`;
4. actually executed completed call + exact `COMPLETED` record => READY.

## What Is Fixed Correctly

- Required persisted fields now reuse the production record parser: `created_at`, `updated_at`, `owner_id`, `attempt`, and `data` are validated.
- `updated_at < created_at` is rejected.
- Terminal reopening and invalid `RECOVERABLE -> COMPLETED` progression are rejected.
- Missing-store/readiness inspection remains strictly non-mutating.
- Safe crash after `LLM_RESPONDED` but before tool claim no longer falsely requires idempotency state.
- Started pending/recoverable calls with missing exact idempotency state fail closed.
- Exact RecordKey matching remains in place.
- M6 safety-matrix regressions for scheduled-retry cancellation, STOP-over-retry, and stable-call budget dedup remain present.
- RESULT-009 reports 30 focused M6, 52 Phase 5.6 integration, and 353 full-suite tests passing.

## Durable Evidence Note

`RESULT-009.md` uses the exact current REVIEW authorization and reports fresh test evidence. The immutable reviewed task head is recorded here as `1bbc20b04dd7e418b901df2a7dd4c3a79dc14d46`.

## Re-review Requirements

Publish one more FIX commit through this exact REVIEW-009 artifact. Before publish:
1. make persisted idempotency lifecycle validation contract-equivalent for owner/attempt/state progression;
2. distinguish pre-claim completed/rejected calls from calls that actually entered idempotent execution;
3. add focused regressions for both gaps;
4. keep readiness strictly read-only;
5. run focused M6, full Phase 5.6 integration, and full repository suites;
6. regenerate RESULT-009 with fresh evidence.

Then the user should only need to say `Review TASK-009` again. Do not merge automatically.
