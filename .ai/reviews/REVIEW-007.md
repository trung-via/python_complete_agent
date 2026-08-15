# REVIEW-007 — TASK-007 (Phase 5.6 M4 — Run Budget Enforcement)

## Status
CHANGES_REQUIRED

## Summary
The implementation is strong overall: the branch is a clean one-commit fast-forward from current `main`, `RunBudgetEngine` is side-effect free, policy validation is in place, canonical halt reasons are preserved, timeout/cancellation behavior remains intact, and RESULT-007 reports 298/298 tests passing.

One blocking resume-accounting gap remains in `AgentLoop._resume_internal()`.

## Blocking Finding 1 — Resume reconstructs durable tool usage, then discards it

### Location
`src/agent/loop.py` — `_resume_internal()` immediately after `RunBudgetEngine.reconstruct_usage(events)`.

Current code:

```python
prior_usage = RunBudgetEngine.reconstruct_usage(events)
iterations_used = prior_usage.iterations_used
tool_calls_used = len(session.completed_tool_calls)
```

The implementation correctly reconstructs durable logical tool usage in `prior_usage.tool_calls_used`, but then does not use that value. Instead it rebuilds the live counter from only `session.completed_tool_calls` and charges every pending call again before execution.

That is not the M4 contract. TASK-007 requires resume to initialize remaining budget from **durable usage**, and repeated/idempotent durable events with the same stable `call_id` must not be charged twice.

### Why this is a real correctness issue

`RunBudgetEngine.reconstruct_usage()` deduplicates by `call_id` across `LLM_RESPONDED`, `TOOL_ATTEMPT_STARTED`, `TOOL_ATTEMPT_ENDED`, and `TOOL_RESULT_RECEIVED`, which is correct.

But `_resume_internal()` throws away that deduplicated tool count. This creates inconsistent accounting between the core budget model and the execution path.

A concrete valid idempotency/replay case:

```text
iteration 1: LLM emits call_id=A
A completes
later durable replay/repeated provider event contains call_id=A again
process stops before the repeated pending A is resolved
```

Durable budget usage is still exactly 1 logical call because `call_id=A` is stable.

Replay state may now contain A in completed history and A pending again. The current resume path starts with:

```text
tool_calls_used = len(completed_tool_calls) = 1
```

then treats pending A as a brand-new requested call and asks for `+1`. With `max_tool_calls=1`, it incorrectly halts even though the durable logical-call budget is still 1/1.

The opposite class of problem is also possible: durable attempt/history events can establish logical tool usage that is not represented by `completed_tool_calls`, causing the live counter to start smaller than the durable reconstructed usage.

This violates the core M4 requirement that crash/resume cannot reset or distort already-consumed logical tool budget.

### Required Fix
Make durable reconstructed usage authoritative during resume.

Recommended shape:

1. Initialize both dimensions from `prior_usage`:

```python
iterations_used = prior_usage.iterations_used
tool_calls_used = prior_usage.tool_calls_used
```

2. Do **not** charge a pending tool call again when its stable `call_id` is already part of the durable reconstructed logical-call set.

Because `BudgetUsage` currently exposes only counts, use one of these focused approaches:
- extend the reconstruction helper with a small internal/result structure that also exposes the set of already-seen logical `call_id`s; or
- add a deterministic helper that reconstructs logical call IDs alongside `BudgetUsage`.

Avoid redesigning ReplayEngine.

3. Before executing resumed pending work, fail closed if durable reconstructed usage is already beyond policy.

4. Only newly emitted tool calls from **new post-resume LLM responses** should consume a new tool-call budget unit.

Preserve all existing retry semantics: multiple attempts for one stable `call_id` remain one logical budget unit.

## Required Regression Tests

Add focused tests proving:

1. Resume uses `prior_usage.tool_calls_used` as the authoritative starting tool budget.
2. Completed `call_id=A` + replayed/pending `call_id=A` counts as exactly one logical tool call and does not halt at `max_tool_calls=1` merely because A is pending again.
3. Distinct pending `call_id=B` after completed A consumes the second unit and is blocked when only one unit is allowed.
4. Multiple retry-attempt events for A across crash/resume still count as one logical call.
5. Durable usage already above the configured tool limit halts before further pending tool execution.
6. Existing 298-test suite plus new regressions pass.

## What Is Already Correct

- `RunBudgetEngine.decide()` has clear exact-limit semantics.
- `RunPolicy` rejects negative iteration/tool limits and non-positive timeout.
- Iteration usage on resume is sourced from durable reconstructed usage.
- Retry attempts are deduplicated by `call_id` inside `RunBudgetEngine.reconstruct_usage()`.
- Fresh-run budget gates stop tool execution before N+1.
- Canonical halt reasons remain `MAX_ITERATIONS_REACHED`, `MAX_TOOL_CALLS_REACHED`, and `TIMEOUT_REACHED`.
- No bridge/AIOS or unrelated application changes were introduced.
- RESULT-007 carries exact RUN authorization and reports the full repository suite passing.

## Re-review Requirements

Publish a new commit on `ai/task-007` through the exact current FIX authorization and update `.ai/results/RESULT-007.md` with fresh full-suite evidence.

Then the user should only need to say `Review TASK-007` again. Do not merge automatically.
