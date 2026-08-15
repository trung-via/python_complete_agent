# TASK-007 — Phase 5.6 M4 Run Budget Enforcement

## Objective
Continue Phase 5.6 after M3 Retry Timeline & Failure Classification by hardening the agent's production execution limits into deterministic, resume-safe run budgets.

Canonical baseline when this task is authored:
- `main`: `e0da2da6db37e8939dd1cc3ce730182504eb73b6`
- AIOS Bridge: v0.4.0 zero-touch handoff
- Phase 5.6 status:
  - M1 Cancellation ✅
  - M2 Retry Policy Engine ✅
  - M3 Retry/Failure Observability ✅
  - M4 Run Budget Enforcement ⏭ CURRENT

Existing `RunPolicy` already exposes:
- `max_iterations`
- `max_tool_calls`
- `timeout_seconds`

But the current enforcement is local-loop counter based, so iteration/tool budgets can be reset by `resume()`, and limit decisions are scattered inside `AgentLoop` rather than represented as a deterministic production-control contract.

The goal of M4 is **not** to redesign the agent loop. The goal is to make existing production limits explicit, deterministic, testable, and safe across crash/resume.

---

## Core Safety Principles

Preserve all Phase 5.6 invariants already merged:
- cancellation always wins over further work;
- terminal runs never resume into active execution;
- corruption/checkpoint-store failures remain fail-closed;
- retry-policy precedence and actual retry delay semantics from M2/M3 remain unchanged;
- retry attempts must not silently inflate logical tool-call accounting;
- `call_id` / idempotency behavior remains unchanged;
- no auto-repair of corrupt state;
- no unrelated bridge/AIOS changes in this task.

Budget enforcement must never create a second retry framework or duplicate the existing retry policy.

---

## M4.1 — Deterministic Budget Model

Introduce a small production budget model in an appropriate core module, for example `src/core/run_budget.py`.

Recommended public contract (exact naming may vary):

```python
from dataclasses import dataclass
from enum import Enum

class BudgetDimension(str, Enum):
    ITERATIONS = "ITERATIONS"
    TOOL_CALLS = "TOOL_CALLS"
    TIME = "TIME"

@dataclass(frozen=True)
class BudgetUsage:
    iterations_used: int
    tool_calls_used: int
    elapsed_seconds: float

@dataclass(frozen=True)
class BudgetDecision:
    allowed: bool
    exhausted_dimension: BudgetDimension | None
    reason: str | None

class RunBudgetEngine:
    @staticmethod
    def decide(policy, usage, requested_iterations=0, requested_tool_calls=0) -> BudgetDecision:
        ...
```

Requirements:
- decision layer is deterministic and side-effect free;
- no sleeping, checkpoint mutation, Git/runtime interaction, or provider calls;
- no off-by-one ambiguity;
- `max_iterations=N` permits exactly N LLM iterations, never N+1;
- `max_tool_calls=N` permits exactly N logical tool calls, never N+1;
- invalid negative limits fail closed at policy validation/construction boundary;
- zero limits are valid and mean no work of that dimension may begin;
- preserve current defaults and backward-compatible `RunPolicy` construction unless a compelling safety issue requires explicit migration.

Do not add token/cost-provider billing logic in this milestone. M4 is execution-budget enforcement, not external pricing accounting.

---

## M4.2 — Resume-Safe Usage Reconstruction

The critical M4 requirement is that crash/resume must **not reset already-consumed budgets**.

Add a deterministic read-only helper that reconstructs budget usage for a `run_id` from durable checkpoint history.

Requirements:
- derive prior LLM iteration usage from durable checkpoint events, not local variables;
- derive prior **logical tool-call usage**, not retry-attempt count;
- M3 `TOOL_ATTEMPT_STARTED` / `RETRY_SCHEDULED` events must not cause one logical tool invocation to be counted multiple times;
- repeated/idempotent checkpoint events must not double-count the same logical tool call when a stable `call_id` identifies it;
- reconstruction is read-only and deterministic;
- malformed/corrupt checkpoint history must not silently produce a smaller budget usage; use existing checkpoint/integrity failure behavior and fail closed.

Prefer existing canonical checkpoint events and replay data. Do not introduce duplicate shadow persistence if the event log already contains sufficient information.

### Logical tool-call accounting

Budget semantics are based on provider-requested logical tool calls:

```text
LLM emits call_id=A
  attempt 1 fails
  RETRY_SCHEDULED
  attempt 2 succeeds
```

This consumes:
- 1 logical tool call budget
- 2 retry attempts governed separately by RetryPolicyEngine

It must **not** consume 2 tool-call budget units.

---

## M4.3 — AgentLoop Integration

Replace scattered raw counter limit decisions in `AgentLoop` with the budget model while keeping the execution flow small and readable.

### Fresh run

At the beginning of a fresh run:
- usage starts at zero;
- enforce iteration budget **before** issuing the next LLM request;
- enforce tool-call budget **before** executing each newly requested logical tool call;
- preserve current terminal halt behavior when exhausted.

### Resume

Before resumed execution:
- reconstruct durable usage already consumed by the run;
- initialize remaining budget from durable usage, not from zero;
- continuing after resume must never allow more total iterations/tool calls than the configured `RunPolicy` permits;
- already-completed/idempotently replayed work must not be charged again.

### Exhaustion behavior

Preserve compatible terminal semantics:
- iteration exhaustion -> halt with canonical reason `MAX_ITERATIONS_REACHED`;
- tool-call exhaustion -> halt with canonical reason `MAX_TOOL_CALLS_REACHED`;
- timeout -> halt with canonical reason `TIMEOUT_REACHED`.

Do not change terminal-state immutability.

If a structured internal `BudgetDecision` is added, the externally persisted halt reason should remain backward compatible unless tests show a safe reason to extend it.

---

## M4.4 — Time Budget Semantics

Keep timeout semantics conservative and explicitly documented.

For this milestone:
- continue to use `asyncio.wait_for` or equivalent for the active execution session;
- do not invent provider billing-time accounting;
- do not count machine downtime between process crash and manual resume as active execution time unless existing durable data already supports that semantics unambiguously;
- if accurate active elapsed time across crash/resume cannot be reconstructed safely from current events, keep timeout enforcement per active run/resume session and document that limitation rather than fabricating precision.

The main M4 persistence requirement is iteration/tool-call continuity across resume.

Add tests confirming timeout still halts correctly and does not regress while refactoring limit enforcement.

---

## M4.5 — Policy Validation

Harden `RunPolicy` input validation without breaking normal callers.

At minimum:
- `max_iterations >= 0`
- `max_tool_calls >= 0`
- `timeout_seconds > 0`

Invalid policies must fail deterministically before autonomous execution begins.

Do not silently clamp invalid values.

If `RunPolicy` remains a dataclass, `__post_init__` is acceptable.

---

## M4.6 — Observability / Diagnostics

Budget decisions should be easy to inspect in logs/tests without adding noisy new checkpoint events unless necessary.

At minimum:
- log the exhausted dimension and current usage/limit when halting;
- budget reconstruction should expose a typed `BudgetUsage` object usable by tests and later M5 operational verification;
- do not log secrets, prompts, or tool payloads merely for budget accounting.

A new checkpoint event is **not required** for M4 if existing `RUN_HALTED` reason + durable source events are sufficient.

---

## Required Tests

Add focused unit/integration coverage for at least:

1. `RunBudgetEngine` allows exactly `max_iterations` and rejects iteration N+1.
2. `RunBudgetEngine` allows exactly `max_tool_calls` and rejects logical tool call N+1.
3. zero iteration/tool budgets fail before work begins.
4. negative iteration/tool budgets are rejected deterministically.
5. non-positive timeout is rejected deterministically.
6. fresh run at limit halts with existing canonical reason.
7. resume reconstructs prior LLM iterations and does not reset iteration budget.
8. resume reconstructs prior logical tool calls and does not reset tool-call budget.
9. a retried tool with the same `call_id` counts as exactly one logical tool call.
10. multiple `TOOL_ATTEMPT_STARTED` events for one call do not inflate logical tool usage.
11. multiple distinct tool `call_id`s each consume one budget unit.
12. idempotent/replayed durable events do not double-count the same logical call.
13. budget exhaustion performs no further LLM/tool operation after the decision is STOP.
14. cancellation still prevents work and is not overridden by budget handling.
15. terminal/corrupt recovery behavior remains unchanged.
16. timeout path still logs/halt-reasons `TIMEOUT_REACHED` correctly.
17. existing TASK-003/TASK-005 retry-after/jitter/retry-timeline tests remain green.
18. full repository test suite passes.

Where possible, include one integration scenario such as:

```text
policy: max_iterations=3, max_tool_calls=2
run consumes iteration 1 + tool A
process interruption
resume consumes iteration 2 + tool B
next requested tool C -> HALT MAX_TOOL_CALLS_REACHED
no tool C execution occurs
```

And one retry scenario:

```text
policy max_tool_calls=1
LLM requests tool A
A fails once, retries, then succeeds
run must not halt merely because A used 2 attempts
logical tool budget used == 1
```

---

## Protected / Non-Goals

Do NOT in TASK-007:
- modify `bridge.py` or AIOS workflow;
- implement M5 operational verification/fault injection/concurrency stress yet;
- add external provider pricing or token-dollar accounting;
- redesign ReplayEngine;
- change retry backoff/retry-after/jitter semantics;
- change FailureClassifier precedence;
- change cancellation semantics;
- change call-id/idempotency semantics;
- rebase/reset unrelated history;
- auto-merge.

---

## Expected File Scope

Likely files (exact set may vary after inspection):
- `src/agent/policy.py`
- `src/agent/loop.py`
- `src/core/run_budget.py` (new, or equivalent focused module)
- checkpoint/replay helper only if genuinely needed for read-only usage reconstruction
- focused unit/integration tests

Avoid unrelated application or AIOS refactors.

---

## Acceptance Criteria

- [ ] Phase 5.6 M4 has a deterministic typed budget decision model.
- [ ] Existing RunPolicy defaults remain compatible.
- [ ] Invalid production limits fail before autonomous execution.
- [ ] Fresh run cannot exceed max iterations or logical tool calls.
- [ ] Resume cannot reset iteration budget.
- [ ] Resume cannot reset logical tool-call budget.
- [ ] Retry attempts with the same `call_id` do not consume extra logical tool-call budget.
- [ ] Existing retry/cancellation/terminal/corruption precedence is preserved.
- [ ] Existing canonical halt reasons remain compatible.
- [ ] No extra LLM/tool operation occurs after budget exhaustion.
- [ ] Timeout behavior remains correct and explicitly documented.
- [ ] Full repository tests pass.
- [ ] `.ai/results/RESULT-007.md` contains durable test evidence.
- [ ] Branch `ai/task-007` is pushed for ChatGPT review.
- [ ] No merge occurs without explicit `Merge TASK-007` from the user.

---

## Delivery

Use AIOS v0.4.0 normal workflow:

```text
/aios-worker RUN TASK-007
```

Worker must:
1. handoff exact current TASK-007 artifact;
2. safely reconcile local `main` with `origin/main`;
3. work only on `ai/task-007`;
4. implement M4;
5. run focused tests + full repository suite;
6. publish `.ai/results/RESULT-007.md` through ACTIVE exact RUN authorization;
7. push branch;
8. do not merge.
