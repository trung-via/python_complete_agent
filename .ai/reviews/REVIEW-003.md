# REVIEW-003 — TASK-003

## Status
CHANGES_REQUIRED

## Summary
TASK-003 correctly integrates only the two requested Phase 5.6 M1/M2 commits onto current `main`, excludes the three M3 commits, and keeps the task branch exactly two commits ahead of `main`. However, two blocking correctness/regression issues remain in the integrated M1/M2 behavior.

## Blocking Finding 1 — Concurrent cancellation is not durably idempotent

### Location
`src/core/cancellation.py` — `RunCancellationController.cancel()`

### Problem
`cancel()` does:
1. `token = get_token(run_id)`
2. checks `token.is_cancelled`
3. writes `RUN_HALTED`
4. calls `token._mark_cancelled(...)`

The check/write/mark sequence is not protected by one controller-level critical section. Two or more concurrent callers can all observe `token.is_cancelled == False` before any caller marks the token, then each writes its own durable `RUN_HALTED` event.

This violates the stated M1 guarantee that multiple cancel calls are idempotent, especially under concurrency. The current concurrent test only checks that all returned tokens end cancelled; it does not assert that exactly one durable halt event is written.

### Required Fix
Make cancellation atomic per run (or otherwise serialize the check -> durable write -> mark sequence) while preserving the required ordering:
- durable checkpoint write FIRST;
- only after durable write succeeds, mark in-memory token cancelled;
- checkpoint failure must leave token uncancelled;
- repeated/concurrent cancellation must produce exactly one durable cancellation transition.

Add/strengthen a concurrency test that launches multiple simultaneous cancel calls for the same run and asserts exactly one `RUN_HALTED` checkpoint entry is persisted.

## Blocking Finding 2 — RetryManager regresses existing RetryPolicy delay semantics

### Location
`src/core/retry.py` — `RetryManager.execute_with_retry()`

### Problem
Before M2, RetryManager used `self.policy.get_delay(attempt, error_to_eval)`. That path supports:
- `RATE_LIMIT` errors with `details["retry_after"]`;
- configured jitter.

After the M2 integration, RetryManager bypasses `RetryPolicy.get_delay()` and sleeps only for `RetryPolicyEngine.decide(...).delay_seconds`, which is deterministic exponential backoff. As a result, the previously supported `Retry-After` delay and configured jitter are silently ignored by actual retry execution, even though `RetryPolicy.get_delay()` and its existing unit test remain in the codebase.

This is a behavior regression against current `main`, conflicting with TASK-003's no-regression acceptance criterion.

### Required Fix
Preserve RetryPolicyEngine as the pure authority for whether/when to retry, but keep the established runtime delay contract. A minimal acceptable design is:
- policy engine decides `should_retry`, `next_attempt`, reason, etc.;
- actual sleep delay preserves `Retry-After` when supplied and existing jitter semantics where configured, without adding M3-only FailureClassifier/event-persistence work.

Add integration coverage proving that `RetryManager.execute_with_retry()` actually respects a `RATE_LIMIT` `retry_after` value (mock/patch sleep; do not make the test wait in real time). If jitter behavior is intentionally changed, document that decision explicitly and adjust the old contract/tests rather than leaving dead/contradictory behavior.

## Scope Guard
Do NOT import the excluded M3 commits wholesale. In particular, keep excluded unless strictly required and explicitly justified:
- `e70900b` — RETRY_SCHEDULED event/audit metadata
- `fb5891a` — FailureClassifier
- `4e0b3d6` — per-attempt start logging/persistence

## Re-review Requirements
After fixing, report:
1. new commit SHA on `ai/task-003`;
2. focused tests for concurrent cancellation durable idempotency;
3. focused test proving RetryManager respects RATE_LIMIT `retry_after`;
4. M1/M2 focused total;
5. full repository test total;
6. confirmation that the three M3 commits/features remain excluded.

Do not merge automatically.
