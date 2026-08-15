# REVIEW-008 — TASK-008 (Phase 5.6 M5 — Fault Injection & Concurrency Verification)

## Status
CHANGES_REQUIRED

## Re-review Head
- Branch: `ai/task-008`
- Reviewed commit: `0b1c6c2e88fa11bb05e686cf92479c0340be3d9f`
- Previous reviewed commit: `e49fc9895efc67e96eff733aee3c91f20ed0cb61`
- Exact FIX authorization in RESULT: `.ai/reviews/REVIEW-008.md (179ac3ff49)`
- Reported focused M5 suite: 21 passed
- Reported full suite: 322 passed

## Summary
The first-round blockers were addressed in the right direction: a retry continuation hook was added, the dead `ToolExecutor` block was removed, barrier-based async tests were introduced, a multiprocessing same-call test was added, and RESULT-008 now records focused/full test counts plus verified fault classes.

The task is not yet approvable because several fail-closed/concurrency verification requirements are still weaker than the production invariant they claim to prove.

## Blocking Finding 1 — Retry continuation state-check fails OPEN on inspection errors

### Location
`src/core/tool_executor.py` — `before_retry_attempt()`.

Current behavior:

```python
try:
    diag = RecoveryAnalyzer.analyze(call.run_id, self.checkpoints.db_path)
    if diag.current_state in (RunState.HALTED, RunState.FAILED, RunState.COMPLETED):
        return False
    return True
except Exception as e:
    logger.warning(...)
    return True
```

If durable-state inspection fails because of checkpoint corruption, I/O failure, malformed state, or another recovery-analysis error, the guard explicitly returns `True` and permits attempt N+1.

That violates TASK-008's fail-closed invariant and the previous review requirement that the continuation guard must not weaken checkpoint-store/corruption safety.

### Required Fix
Fail closed on inspection errors.

Acceptable approaches:
- let checkpoint/recovery exceptions propagate; or
- convert them to the existing `SystemStateError` / corruption domain and stop continuation.

Do not return `True` from the exception path.

Add a regression proving that a checkpoint/recovery inspection failure between `RETRY_SCHEDULED` and attempt N+1 results in zero further tool attempts.

Preserve `retry_after` and jitter calculation exactly.

## Blocking Finding 2 — Async contention tests still do not prove contender 2 reached the claim boundary before release

### Location
`tests/integration/test_phase56_concurrency.py`

The new tests correctly hold contender 1 inside tool execution, but then do:

```python
task2 = asyncio.create_task(...)
release_event.set()
```

There is no acknowledgment/barrier proving contender 2 actually attempted the idempotency claim while contender 1 still owns it. The scheduler can release contender 1 before contender 2 reaches `claim()`, turning the case back into sequential completed-result replay.

### Required Fix
Instrument a deterministic second-contender boundary.

For example, use a test-only store wrapper/callback/event around `claim()` so the test waits until contender 2 has entered/returned from the competing claim attempt before releasing contender 1.

Required assertions under forced contention:
- contender 1 holds the key;
- contender 2 actually reaches the competing claim while key is in progress;
- exactly one external side effect occurs;
- losing contender returns `IDEMPOTENCY_IN_PROGRESS`, replay, or another documented fail-closed result;
- durable state remains valid.

No arbitrary sleep/yield-based synchronization.

## Blocking Finding 3 — Multiprocessing same-call test does not measure duplicate external side effects

### Location
`tests/integration/test_phase56_concurrency.py` — `test_multiprocessing_concurrent_same_call_contention`.

Each process constructs its own `BarrierSideEffectTool`, so `tool.side_effects` is process-local and invisible to the parent. The parent currently asserts:
- at least one successful result;
- the idempotency record is parseable/has a valid status.

It does **not** assert that the two processes produced at most one external side effect. In fact, `len(success_results) >= 1` would still pass if both processes successfully executed the side effect.

### Required Fix
Use a process-shared observable side-effect sink (for example `multiprocessing.Value`, Manager-backed counter/list, or locked test file) and assert exactly one side effect for the shared `(run_id, call_id)`.

Also assert the result/store relationship tightly enough that two successful underlying executions cannot pass unnoticed.

## Blocking Finding 4 — Persistence-boundary regression does not test the claimed `SystemStateError` classification

### Location
`tests/integration/test_phase56_fault_injection.py` — `test_explicit_persistence_boundary_failure_is_classified_as_system_state_error`.

The test injects `OSError` directly from `FaultyCheckpointManager.log_event()` and then expects that raw `OSError`:

```python
with pytest.raises(OSError, match="Simulated checkpoint write failure"):
    await executor.execute(call)
```

So the test name/RESULT claim says `SystemStateError`, but the assertion verifies the opposite. This bypasses the actual production persistence wrapper that turns checkpoint/idempotency persistence failures into infrastructure/system-state failures.

### Required Fix
Exercise a real production persistence boundary and assert the production classification (`SystemStateError` or the exact established checkpoint-store exception domain).

Keep the separate raw application/tool `OSError` regression proving ordinary tool OSError is *not* promoted.

## What Is Fixed Correctly

- Retry continuation now has a dedicated minimal hook rather than a second retry engine.
- `RetryPolicy.get_delay()` remains authoritative for `retry_after` and jitter.
- Cancellation/terminal-before-retry tests now exist and report passing.
- Dead unreachable `failure_result` code in `ToolExecutor` was removed.
- `AgentLoop` yields a competing resume contender on `IDEMPOTENCY_IN_PROGRESS` rather than writing a false tool result.
- RESULT-008 now reports the focused M5 command/count, full suite count, and fault classes.
- Branch remains scoped to Phase 5.6 M5; no bridge/AIOS changes are present.

## Re-review Requirements

Publish one more FIX commit through the exact current REVIEW-008 artifact.

Before publish:
1. make retry-continuation inspection fail closed;
2. make async contention boundary deterministic for contender 2;
3. measure real multiprocessing side effects with a shared sink and assert exactly one;
4. correct the persistence-boundary classification regression;
5. run focused M5 tests and the full repository suite;
6. regenerate RESULT-008 with fresh evidence.

Then the user should only need to say `Review TASK-008` again. Do not merge automatically.
