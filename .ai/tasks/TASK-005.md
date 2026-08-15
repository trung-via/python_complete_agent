# TASK-005 — Phase 5.6 M3 Retry Timeline & Failure Classification

## Objective
Complete Phase 5.6 M3 on top of the current canonical `main` by adding durable retry observability, per-attempt checkpoint persistence, and normalized failure classification **without regressing the M1/M2 behavior already merged by TASK-003**.

Current canonical baseline when this task is authored:
- `main`: `205dddbda7b7ceda31c854700c23953a68232f55`
- TASK-003 already merged Phase 5.6 M1/M2 and intentionally preserved legacy runtime delay semantics (`RetryPolicy.get_delay()`), including rate-limit `retry_after` and jitter.
- TASK-004 only stabilizes AIOS Bridge behavior and must not be modified by this task.

## Historical Reference Commits — REFERENCE ONLY
The old `p0-agent-control` branch contains partial M3 work in these commits:

1. `e70900b09ba0413ba087b703d255c7c6fc624ac6`
   - `RETRY_SCHEDULED` checkpoint event
   - retry audit metadata/callback
2. `fb5891a1c8ea098f0798c274718954ea4654dc72`
   - `FailureClassifier`
3. `4e0b3d6b42a8b59b53d5ac13c1004eb6e6fb1209`
   - per-attempt `TOOL_ATTEMPT_STARTED` logging

**Do not blindly cherry-pick these commits.** Re-implement/adapt their intent against current `main`, because TASK-003 changed retry-delay semantics and the historical classifier contains assumptions that are too broad for the current architecture.

## Scope
Primary files expected to change:
- `src/core/checkpoint_contract.py`
- `src/core/checkpoint.py`
- `src/core/retry_policy.py`
- `src/agent/retry_policy.py`
- `src/core/retry.py`
- `src/core/tool_executor.py`
- focused retry/checkpoint tests

Avoid unrelated refactors. Do not modify `bridge.py` or AIOS Bridge tests.

---

## M3.1 — Durable `RETRY_SCHEDULED` Event

Add `CheckpointEventType.RETRY_SCHEDULED` and a checkpoint logging API for retry scheduling.

Minimum payload contract:

```json
{
  "operation": "TOOL",
  "attempt": 1,
  "next_attempt": 2,
  "delay_seconds": 5.0,
  "reason": "RETRYABLE_RATE_LIMIT",
  "failure_domain": "TOOL_EXECUTION",
  "call_id": "..."
}
```

Requirements:
1. `RETRY_SCHEDULED` is a non-terminal event and must not change the run state.
2. State-transition validation must accept it in the appropriate active retry states and reject illegal terminal-state mutation.
3. It must be persisted **after the failed attempt is recorded and before sleeping / starting the next attempt**.
4. Do not emit `RETRY_SCHEDULED` when policy decides STOP, cancellation/terminal/corruption blocks retry, or max attempts are exhausted.

### Critical delay contract
`delay_seconds` must represent the **actual delay the runtime is about to sleep**, not merely `RetryDecision.delay_seconds`.

Current M2/TASK-003 behavior intentionally calculates the real delay using:

```python
self.policy.get_delay(attempt, target_err)
```

This preserves:
- `RateLimitError.details["retry_after"]`
- `RATE_LIMIT` / `RATE_LIMIT_ERROR` behavior
- jitter semantics

Therefore M3 observability must log/callback the exact same final `delay` value passed to `asyncio.sleep(delay)`.

Do not regress back to using deterministic `RetryDecision.delay_seconds` as the actual sleep duration.

If useful, a separate policy/backoff value may be recorded under a differently named optional field, but `delay_seconds` must always equal the actual scheduled sleep.

---

## M3.2 — Per-Attempt Start Persistence

Today `ToolExecutor` logs `TOOL_ATTEMPT_STARTED` once before entering the retry manager while `TOOL_ATTEMPT_ENDED` is emitted per attempt. Fix this asymmetry.

Requirements:
1. `log_tool_attempt_started()` must persist the 1-indexed `attempt` number.
2. Every actual execution attempt emits exactly one `TOOL_ATTEMPT_STARTED` before invoking the operation.
3. Every completed/failed attempt continues to emit its corresponding `TOOL_ATTEMPT_ENDED`.
4. Remove the old one-time pre-retry start logging from both legacy and v2 execution paths so attempt 1 is not double-counted.
5. Preserve exact `call_id` and idempotency key across retries.

Expected retry timeline for a 3-attempt tool call:

```text
TOOL_CALL_CREATED
TOOL_ATTEMPT_STARTED  attempt=1
TOOL_ATTEMPT_ENDED    attempt=1
RETRY_SCHEDULED       attempt=1 next_attempt=2
TOOL_ATTEMPT_STARTED  attempt=2
TOOL_ATTEMPT_ENDED    attempt=2
RETRY_SCHEDULED       attempt=2 next_attempt=3
TOOL_ATTEMPT_STARTED  attempt=3
TOOL_ATTEMPT_ENDED    attempt=3
... final result handling ...
```

No duplicate attempt-start event is allowed.

---

## M3.3 — Failure Classification

Add a deterministic `FailureClassifier` that normalizes failures used by `RetryPolicyEngine` into:

```text
(FailureDomain, transient: bool, error_code: str)
```

Export it through `src/agent/retry_policy.py` for API consistency.

### Required classification behavior
At minimum:

1. `CheckpointCorruptionError` / `CheckpointStateError`
   - domain: `CORRUPTION_INTEGRITY`
   - transient: `False`
   - must never retry

2. `SystemStateError`
   - domain: `CHECKPOINT_STORE`
   - transient: `False`
   - must never retry
   - this type already represents critical checkpoint/idempotency/system-state persistence failures

3. `AgentException`
   - domain according to retry operation (`TOOL_EXECUTION` for tool flow, `LLM_PROVIDER` for LLM flow)
   - transient from `retryable`
   - preserve its exact `code`

4. Timeout exceptions
   - operation-specific domain
   - transient: `True`
   - code: stable timeout code such as `TIMEOUT`

5. Unknown/generic exceptions
   - operation-specific domain
   - safe default: non-transient unless there is explicit retryability metadata
   - stable error code

### Important anti-regression rule
Do **not** classify every raw `OSError` / `PermissionError` / `FileNotFoundError` as `CHECKPOINT_STORE` merely because it is an OS error.

A raw OS error may originate inside a user/tool operation. Infrastructure persistence failures are already wrapped as `SystemStateError` by the current architecture. The classifier must not falsely convert arbitrary tool I/O failures into checkpoint-store failures.

The classifier is for retry decision metadata only. It must not discard or replace the original error object used by `RetryPolicy.get_delay()`; rate-limit `retry_after` details must remain available.

---

## M3.4 — RetryManager Integration

Adapt `RetryManager.execute_with_retry()` so that:

1. It classifies the current failure via `FailureClassifier` before calling `RetryPolicyEngine.decide()`.
2. It preserves all M2 precedence rules already implemented in `RetryPolicyEngine`.
3. It keeps the original failure object available for final propagation and actual-delay calculation.
4. It supports callbacks/hooks for:
   - attempt start
   - attempt complete
   - retry scheduled
5. Callback metadata must match the actual retry decision and actual sleep delay.
6. A callback failure must not silently cause a retry decision to diverge from the operation state. Keep implementation simple and deterministic; do not add background execution.

Do not broaden this task into a new retry framework or add automatic LLM retry execution unless already required by current code paths.

---

## Acceptance Criteria

- [ ] Current `main` M1/M2 behavior remains intact.
- [ ] `RETRY_SCHEDULED` exists in checkpoint contract and is state-machine valid only in non-terminal active contexts.
- [ ] Every retryable tool attempt has a durable ordered timeline with start/end/retry-scheduled metadata.
- [ ] A 3-attempt execution persists attempt starts exactly `[1, 2, 3]`.
- [ ] Retry scheduled events for that run are exactly `1 -> 2` and `2 -> 3`; no retry event after attempt 3.
- [ ] `RETRY_SCHEDULED.delay_seconds` equals the exact value passed to `asyncio.sleep()`.
- [ ] Rate-limit `retry_after` remains honored and is reflected in `RETRY_SCHEDULED.delay_seconds`.
- [ ] Existing jitter behavior is not removed or silently bypassed.
- [ ] Failure classification drives `RetryPolicyEngine` with correct `FailureDomain`, transient flag, and error code.
- [ ] Corruption/integrity and system-state persistence failures never retry.
- [ ] Raw generic tool `OSError` is not automatically mislabeled as checkpoint-store failure.
- [ ] Existing legacy and v2 ToolExecutor paths remain functional.
- [ ] Existing idempotency semantics remain unchanged.
- [ ] Full repository test suite passes with no regressions.

---

## Required Tests

Add focused tests covering at least:

1. **Retry event contract**
   - transient retry creates `RETRY_SCHEDULED`
   - payload contains attempt, next attempt, reason, failure domain, call id, actual delay

2. **Actual delay / rate limit**
   - `RateLimitError` or equivalent with `details={"retry_after": X}`
   - capture/patch sleep
   - assert checkpoint `delay_seconds == X`
   - assert actual sleep receives the same `X`

3. **Per-attempt persistence**
   - three executions produce `TOOL_ATTEMPT_STARTED` attempts `[1, 2, 3]`
   - matching `TOOL_ATTEMPT_ENDED` attempts `[1, 2, 3]`
   - exactly two `RETRY_SCHEDULED` events (`1->2`, `2->3`)

4. **No retry event on stop**
   - max-attempt, non-retryable, corruption, or system-state stop produces no subsequent `RETRY_SCHEDULED`

5. **FailureClassifier**
   - checkpoint corruption
   - checkpoint/state-system failure
   - retryable `AgentException`
   - timeout
   - generic exception
   - raw tool `OSError` is not classified as `CHECKPOINT_STORE` unless represented/wrapped as infrastructure `SystemStateError`

6. **State machine**
   - `RETRY_SCHEDULED` preserves active state
   - terminal state remains immutable

7. Existing retry-after regression tests from TASK-003 must continue passing.

---

## Delivery

- Work on branch `ai/task-005`.
- Start from current `origin/main`; do not base implementation on stale `p0-agent-control` history.
- Historical M3 commits are references only; adaptation is expected.
- Run focused M3/retry/checkpoint tests.
- Run full repository test suite.
- Report:
  1. changed files;
  2. focused test totals;
  3. full suite total;
  4. final commit SHA;
  5. brief note confirming actual scheduled delay remains compatible with TASK-003 rate-limit/jitter semantics.
- Push `ai/task-005` for ChatGPT review.
- **Do not auto-merge.** Human approval remains mandatory.
