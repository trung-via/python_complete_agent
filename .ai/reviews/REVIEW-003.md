# REVIEW-003 — TASK-003

## Status
APPROVED

## Re-review Summary
Re-reviewed `ai/task-003` at commit `8ebab4f5a85ba842e76cbd3c26bf0b73080890a8` against the previous reviewed head `4c47669a38518689a2fccd8bd9cb087aec7566f1` and current `main`.

Both blocking findings from the first review are resolved.

## Finding 1 — Concurrent cancellation durable idempotency
RESOLVED.

`RunCancellationController` now uses a controller-level `threading.RLock` and performs the full same-run cancellation sequence under that lock:
- get token;
- check already-cancelled state;
- write durable `RUN_HALTED`;
- only after successful durable write, mark the in-memory token cancelled.

This preserves fail-closed ordering and prevents concurrent callers for the same run from persisting duplicate cancellation transitions.

The concurrency test was strengthened to assert exactly one durable `RUN_HALTED` entry.

## Finding 2 — RetryPolicy runtime delay semantics
RESOLVED.

`RetryPolicyEngine` remains the pure decision authority for whether retry is allowed and for the next attempt/reason. Runtime sleeping now obtains the actual delay from `RetryPolicy.get_delay(...)`, restoring the existing contract for:
- provider/tool `retry_after` values;
- configured jitter;
- existing exponential/capped delay fallback.

`RATE_LIMIT_ERROR` is also accepted alongside `RATE_LIMIT` for retry-after handling.

Integration tests were added for both raised rate-limit errors and failure `ToolResult` rate-limit errors, with `asyncio.sleep` patched so no real delay is incurred.

## Scope Verification
`main..ai/task-003` remains limited to the intended M1/M2 functional areas and their tests. The excluded M3 work is not present in the branch diff:
- no RETRY_SCHEDULED checkpoint/event work;
- no FailureClassifier;
- no per-attempt start persistence changes.

The branch is 3 commits ahead of `main`: two M1/M2 integration commits plus the review-fix commit.

## Test Report
Worker reported:
- concurrent cancellation durable-idempotency focused test: PASS;
- both RATE_LIMIT retry-after focused tests: PASS;
- M1/M2 focused suite: 29/29 PASS;
- full repository suite: 251/251 PASS.

No GitHub status checks are configured for this commit, so the test totals above are the worker's published local verification rather than independently observed CI results.

## Decision
APPROVED for HUMAN GATE.

Do not auto-merge. Final merge requires explicit human approval.
