# REVIEW-005 — TASK-005

## Status
CHANGES_REQUIRED

## Summary
TASK-005 gets the main M3 observability pieces largely right: `RETRY_SCHEDULED` is durable, per-attempt start logging is moved into the retry loop, the scheduled delay uses the same final value passed to `asyncio.sleep()`, rate-limit `retry_after` remains available through the original `AgentException`, and raw tool `OSError` is not blindly classified as checkpoint-store failure.

However, there are two related blocking issues in `RetryManager.execute_with_retry()` around final failure selection and policy-engine authority.

## Blocking Finding 1 — A stale prior `ToolResult` can mask a later critical failure

### Location
`src/core/retry.py` — retry loop state and the `if not decision.should_retry` branch.

### Problem
`last_result` and `last_exception` persist across attempts. When policy decides STOP, the code currently prefers `last_result` before `last_exception`:

```python
if last_result:
    return last_result
if last_exception:
    raise last_exception
```

This is incorrect when the failure type changes between attempts.

Concrete sequence:
1. attempt 1 returns a retryable failed `ToolResult` -> `last_result` is set;
2. retry is scheduled;
3. attempt 2 raises `SystemStateError` (or another current non-retryable/critical exception) -> classifier correctly returns `CHECKPOINT_STORE`, transient `False`;
4. policy correctly decides STOP;
5. the manager returns the stale failed result from attempt 1 instead of propagating the current `SystemStateError` from attempt 2.

That hides the actual critical failure and can cause the caller/idempotency layer to treat the operation according to the stale retryable result instead of the current infrastructure failure.

### Required Fix
Make final STOP handling use the **current attempt's failure**, never stale state from a prior attempt. A simple acceptable approach is to clear/supersede prior result/exception state at the start of every attempt or use explicit `current_result` / `current_exception` variables.

The current attempt must win:
- current failed `ToolResult` -> return that result when policy stops;
- current exception -> re-raise that exact exception when policy stops.

Preserve the original error object for `RetryPolicy.get_delay()` and final propagation.

## Blocking Finding 2 — Some failures still bypass `FailureClassifier` / `RetryPolicyEngine`

### Location
`src/core/retry.py` — non-retryable `ToolResult` and non-retryable `AgentException` branches.

### Problem
TASK-005 requires the current failure to be classified before `RetryPolicyEngine.decide()` and for classification metadata to drive the retry decision. The implementation still exits early for:

- failed `ToolResult` whose error is non-retryable -> immediate `return result`;
- non-retryable `AgentException` -> immediate `raise`.

Those paths never reach `FailureClassifier.classify()` or `RetryPolicyEngine.decide()`.

Semantically they still stop, but M3's normalized policy path is not actually authoritative for all failures, and the required failure-domain/error-code decision metadata is bypassed.

### Required Fix
After recording the attempt end, funnel failure cases through the same deterministic classification + policy-decision path. Preserve existing external behavior:
- non-retryable result still returns the current result;
- non-retryable exception still re-raises the same exception;
- no `RETRY_SCHEDULED` is emitted when policy says STOP.

Do not change TASK-003 actual-delay semantics.

## Required Regression Tests
Add focused tests covering at least:

1. **Current critical failure beats stale prior result**
   - attempt 1 returns retryable failed `ToolResult`;
   - attempt 2 raises `SystemStateError`;
   - assert no retry is scheduled after attempt 2;
   - assert the current `SystemStateError` is propagated, not the stale attempt-1 result.

2. **Current generic/corruption stop cannot be masked by prior result**
   - equivalent mixed-attempt case for a current non-retryable exception (preferably `CheckpointCorruptionError` or a safe generic non-transient exception);
   - assert current failure wins and no extra retry event is emitted.

3. **Non-retryable paths pass through normalized policy decision**
   - verify non-retryable `AgentException` and/or non-retryable failed `ToolResult` reaches `FailureClassifier` / `RetryPolicyEngine` while preserving existing return/raise behavior and emitting no retry event.

Run the focused M3/retry/checkpoint tests and the full repository suite again.

## What Already Looks Correct
- Branch is exactly one commit ahead of current `main` and not based on stale history.
- Scope is limited to retry/checkpoint implementation and tests; `bridge.py` is untouched.
- `RETRY_SCHEDULED.delay_seconds` is sourced from `RetryPolicy.get_delay(...)` and the same value is passed to the scheduling callback before `asyncio.sleep(delay)`.
- Rate-limit `retry_after` is preserved.
- Per-attempt start logging avoids the old one-time pre-loop duplicate.
- Raw tool `OSError` remains in the operation-specific domain rather than being mislabeled as `CHECKPOINT_STORE`.

## Re-review Requirements
After fixing, report:
1. new commit SHA on `ai/task-005`;
2. focused regression test result for the stale-result/current-critical-failure case;
3. focused M3/retry/checkpoint test total;
4. full repository test total.

Do not merge automatically.
