# REVIEW-008 — TASK-008 (Phase 5.6 M5 — Fault Injection & Concurrency Verification)

## Status
CHANGES_REQUIRED

## Summary
TASK-008 is directionally good and the branch is a clean one-commit fast-forward from `main` (`799aa448...` -> `e49fc989...`). It adds a useful test-only fault harness, same-run/same-call coverage, four-process independent-run coverage, corruption tests, and a focused production fix so raw application/tool `OSError` is no longer automatically promoted to checkpoint-store failure. The reported full suite is 317/317 passing.

However, M5 is verification-first and several mandatory race/fault invariants are not actually exercised yet. One of those omissions leaves a real control-plane gap visible in the current production code: once `RetryManager` has scheduled a retry, there is no cancellation/terminal continuation guard before the next attempt. In addition, the current same-run concurrency tests are not forced into a real contention boundary, and the required process-level same-run/same-call contention case is absent.

## Blocking Finding 1 — Cancellation/terminal state cannot stop an already-scheduled retry

### Location
- `src/core/retry.py` — `RetryManager.execute_with_retry()`
- `src/core/tool_executor.py` — retry callback wiring

Current retry flow is:

```text
attempt fails
RetryPolicyEngine decides RETRY
on_retry_scheduled(...)
await asyncio.sleep(delay)
attempt = next_attempt
loop continues
```

There is no durable run-state/cancellation check between `RETRY_SCHEDULED` and the next attempt.

AgentLoop cancellation checks happen before entering a tool batch, but once `ToolExecutor.execute()` is inside `RetryManager.execute_with_retry()`, a durable cancellation or terminal transition can occur and the next retry attempt still proceeds.

That violates TASK-008 required cases:
- cancel after retryable failure but before retry continuation -> zero next attempt;
- cancellation wins while retryable failure is waiting -> no next attempt;
- terminal state appears before scheduled retry continuation -> no retry execution;
- no race may silently turn STOP/terminal into active work.

### Required Fix
Add the smallest possible retry-continuation guard at the existing retry boundary. Do not redesign RetryManager.

Acceptable shape:
- add an optional callback/predicate invoked immediately before a retry attempt continues (or immediately after retry wait, before next operation execution);
- ToolExecutor supplies a guard based on the durable run/checkpoint state for `call.run_id`;
- if the run is `HALTED`, `FAILED`, or `COMPLETED`, do not execute another tool attempt;
- durable cancellation is represented by terminal/halted checkpoint state, so durable state is authoritative;
- preserve existing `retry_after` and jitter delay calculation exactly;
- do not add a second retry engine.

The guard must not weaken checkpoint-store/corruption fail-closed behavior.

### Required Regression Tests
Add deterministic barrier/event-driven tests proving:
1. retryable attempt fails;
2. `RETRY_SCHEDULED` is durably written;
3. test pauses before next attempt;
4. cancellation becomes durable;
5. release the retry continuation;
6. attempt N+1 never executes.

Also add the terminal-state variant (`FAILED`/`HALTED`/`COMPLETED` as appropriate) proving no retry continuation after terminal state wins.

Do not implement this test with arbitrary sleeps.

## Blocking Finding 2 — Same-run/same-call “concurrency” tests are not forced into a contention boundary

### Location
`tests/integration/test_phase56_concurrency.py`

The two key tests use plain `asyncio.gather(...)`:
- `test_same_run_two_concurrent_resume_contenders`
- `test_concurrent_same_run_and_call_id_execution`

But the tool/store path is mostly synchronous and the test tool itself has no blocking await/barrier at the side-effect boundary. Therefore one coroutine can claim/execute/complete before the other actually contends. The test can pass as effectively sequential idempotent replay rather than a deterministic race.

TASK-008 explicitly requires deterministic race control using events/barriers rather than timing luck.

### Required Fix
Use the existing fault-injection/barrier utility (or a similarly small test-only barrier) to force both contenders to reach a known contention boundary before either is released.

At minimum verify under forced contention:
- exactly one external side effect for one stable `(run_id, call_id)`;
- the losing contender converges through idempotency or fails closed cleanly;
- checkpoint/idempotency durable state remains valid.

## Blocking Finding 3 — Required real multiprocessing same-run/same-call contention case is missing

The current real multiprocessing test covers four **independent** runs. That is useful and should remain, but TASK-008 also explicitly requires at least one real process-level same-store **same-run or same-call** contention scenario.

Add one multiprocessing test where two OS processes contend for the same durable idempotency key / stable `(run_id, call_id)` against the shared Jsonl idempotency store.

Acceptance:
- at most one external side effect is committed;
- store remains parseable/valid;
- no duplicate successful claim/complete path for the same logical call;
- losing process may fail closed or replay completed result according to current architecture.

Avoid fragile sleeps; use a multiprocessing barrier/event if synchronization is required.

## Finding 4 — Production refactor leaves unreachable stale code

### Location
`src/core/tool_executor.py` after:

```python
except (SystemStateError, CheckpointCorruptionError, CheckpointStateError):
    raise
```

There is unreachable leftover code referencing `failure_result` after the `raise`.

It does not currently execute, but this is production core code and indicates an incomplete exception-path refactor. Remove the dead block and keep exception classification explicit and minimal.

Also preserve the intended M5 fix:
- raw application/tool `OSError` -> ordinary tool failure classification;
- idempotency/checkpoint persistence `OSError` -> `SystemStateError` at the persistence boundary.

## Finding 5 — RESULT-008 does not satisfy the required operational evidence contract

`RESULT-008.md` reports the full suite (`317 passed`) and exact RUN authorization, but TASK-008 M5.7 requires additional durable evidence that is currently absent:
- focused M5 test command(s);
- focused M5 pass count;
- published commit SHA;
- short list of verified fault classes;
- known intentionally untested limitation(s), if any.

The current Diff Stat also lists only `src/core/tool_executor.py` even though the branch adds the M5 test files/harness. Regenerate RESULT-008 from the final FIX publish so the evidence accurately describes the complete branch.

## Additional Missing Mandatory Matrix Coverage

Add or clearly demonstrate existing tests for these TASK-008 required cases if not already covered by the final suite:
- invalid checkpoint sequence/state-transition corruption fails closed;
- explicit persistence-boundary failure is classified as infrastructure/checkpoint-store failure;
- cancel-after-failure-before-retry continuation;
- terminal-before-retry continuation.

Existing TASK-003/TASK-005/TASK-007 regressions must remain green, including RateLimit `retry_after`, jitter, retry timeline, and budget resume behavior.

## What Is Already Good

- Branch is based exactly on current main and contains no AIOS/bridge changes.
- Full reported suite is 317/317 passing.
- Raw tool/application `OSError` classification is being corrected in the right direction.
- Fault harness is test-only and does not introduce a production chaos/debug backdoor.
- Crash-after-LLM-response, idempotent replay after missing tool-result checkpoint, malformed JSON, repeated cancellation, independent multiprocessing, and budget/retry reconstruction coverage are useful.
- No auto-merge behavior was introduced.

## Re-review Requirements

Publish a new commit on `ai/task-008` through the exact current FIX authorization.

Before publishing:
1. close Findings 1-4;
2. add the mandatory deterministic/process-level regressions above;
3. run focused M5 tests separately and record their pass count;
4. run the full repository suite;
5. regenerate `.ai/results/RESULT-008.md` with complete M5.7 evidence.

Then the user should only need to say `Review TASK-008` again. Do not merge automatically.
