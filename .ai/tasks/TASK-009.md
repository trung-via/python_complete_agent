# TASK-009 — Phase 5.6 M6 Production Readiness Gate

## Objective
Close Phase 5.6 with a deterministic **production-readiness gate** over the reliability controls already implemented in M1–M5.

Canonical baseline when authored:
- `main`: `bfce0eb1b10061ee5ec23d549ef75f1a6f3f4e6f`
- AIOS Bridge: v0.4.0 zero-touch handoff
- Phase 5.6 status:
  - M1 Cancellation ✅
  - M2 Retry Policy Engine ✅
  - M3 Retry Timeline & Failure Classification ✅
  - M4 Run Budget Enforcement ✅
  - M5 Fault Injection & Concurrency Verification ✅
  - M6 Production Readiness Gate ⏭ CURRENT

This milestone is **closure + operational verification**, not a runtime redesign.

The goal is to answer one production question deterministically:

> “Is this agent runtime configured and internally consistent enough to begin autonomous execution safely?”

M6 should turn the reliability work from M1–M5 into a small, explicit, testable readiness contract and a durable Phase 5.6 completion report.

---

## Core Principles

Preserve all merged invariants:
- durable cancellation wins over further work;
- terminal states are immutable;
- corrupt/inconsistent checkpoint state fails closed;
- RetryPolicyEngine remains authoritative for retry/stop decisions;
- RetryPolicy.get_delay() remains authoritative for actual Retry-After/jitter delay;
- retry attempts do not inflate logical tool-call budgets;
- crash/resume does not reset iteration/tool budgets;
- stable `call_id` remains the idempotency identity;
- concurrent same-call execution cannot duplicate an external side effect when idempotency is active;
- no auto-repair of corruption;
- no AIOS/bridge modifications in this task;
- no auto-merge.

M6 must not add a second scheduler, retry layer, checkpoint system, or policy framework.

---

## M6.1 — Typed Production Readiness Contract

Add a small read-only readiness model in an appropriate core/agent module, for example:

`src/agent/production_readiness.py`

Recommended shape (exact naming may vary):

```python
from dataclasses import dataclass, field
from enum import Enum

class ReadinessStatus(str, Enum):
    READY = "READY"
    NOT_READY = "NOT_READY"

@dataclass(frozen=True)
class ReadinessCheck:
    name: str
    passed: bool
    reason: str

@dataclass(frozen=True)
class ProductionReadinessReport:
    status: ReadinessStatus
    checks: tuple[ReadinessCheck, ...]

    @property
    def ready(self) -> bool:
        return self.status == ReadinessStatus.READY
```

Add a deterministic evaluator such as:

```python
class ProductionReadinessChecker:
    @staticmethod
    def evaluate(...dependencies...) -> ProductionReadinessReport:
        ...
```

Requirements:
- read-only: no provider calls, no tool side effects, no checkpoint mutation;
- deterministic for the same inputs/files;
- every NOT_READY decision must include a machine-testable reason;
- no secret/prompt/tool-payload leakage in the report;
- one failed safety-critical check makes the overall status NOT_READY;
- no warning-only downgrade that silently permits execution when a required invariant cannot be verified.

---

## M6.2 — Required Readiness Checks

The readiness gate must verify at least the following.

### A. RunPolicy validity
Use the existing `RunPolicy` validation.

Confirm:
- `max_iterations >= 0`;
- `max_tool_calls >= 0`;
- `timeout_seconds > 0`.

Do not duplicate policy validation rules in two places if they can be delegated to the existing policy object.

### B. Retry policy sanity
Validate the configured retry policy without changing retry semantics.

At minimum:
- `max_attempts >= 1`;
- `base_delay >= 0`;
- `max_delay >= base_delay`;
- retry policy object is usable by current RetryManager.

Do not change Retry-After or jitter behavior.

### C. Checkpoint store structural health
Perform a read-only structural validation of the configured checkpoint store.

Requirements:
- missing/empty store may be valid for a fresh runtime;
- malformed JSON, invalid sequence/state transition, or integrity violation => NOT_READY;
- do not auto-repair or rewrite the file;
- do not append a probe checkpoint merely to test writability;
- leverage existing replay/integrity primitives rather than inventing a parallel parser where possible.

If multiple run IDs are present, validate all existing runs sufficiently to detect structural corruption.

### D. Idempotency store structural health
Perform a read-only parse/contract check on the configured idempotency store.

Requirements:
- missing/empty store may be valid for a fresh runtime;
- malformed/internally inconsistent persisted records => NOT_READY;
- no mutation, compaction, cleanup, or claim probe during readiness evaluation;
- preserve current store locking/persistence implementation.

### E. Cross-store consistency for active/recoverable runs
Where durable checkpoint history references logical tool calls whose idempotency state is required for safe replay/recovery, use existing integrity verification to detect mismatch.

Required behavior:
- completed/idempotent calls are consistent -> pass;
- ambiguous/corrupt cross-store state -> NOT_READY;
- do not “fix” the state automatically.

### F. No unsafe terminal continuation
Readiness evaluation must confirm existing persisted terminal runs are not classified as resumable active work.

This is a regression/invariant check over the existing recovery diagnostics, not a new state machine.

---

## M6.3 — Readiness Before Autonomous Execution

Integrate the readiness gate at the smallest appropriate production boundary.

Preferred behavior:
- provide an explicit callable preflight API that application/bootstrap code can invoke before autonomous execution;
- if there is already one clear composition/bootstrap entry point, wire the gate there;
- avoid running an expensive repository-wide scan before every single LLM/tool operation.

If integrating directly into `AgentLoop` would couple it too tightly to store/file implementation details, keep the readiness checker as an explicit production preflight service instead and document the required call order.

The architecture must remain clean:

```text
build dependencies
→ run production readiness check
→ READY: autonomous execution may begin
→ NOT_READY: fail closed before provider/tool side effects
```

No live LLM request should be used as a “health check”.

---

## M6.4 — Deterministic Soak Verification

Add a bounded deterministic reliability soak test suite. This is not a long-running chaos daemon.

The suite should repeatedly exercise already-supported behavior with temporary stores and fake providers/tools.

At minimum include:

1. repeated fresh run → tool → final response lifecycle;
2. repeated crash/resume lifecycle;
3. repeated retry-success lifecycle;
4. repeated budget halt lifecycle;
5. repeated cancellation-before-continuation lifecycle;
6. repeated idempotent replay lifecycle;
7. repeated same-call contention rounds where practical;
8. integrity verification after every run/round.

Target:
- enough rounds to expose state leakage/counter-reset bugs but keep CI practical;
- prefer ~20–50 deterministic rounds total rather than time-based soak duration;
- no arbitrary sleeps for race correctness;
- explicit events/barriers for concurrency rounds;
- fixed fake inputs; no external network dependency.

The soak suite must remain stable on Windows, since the current development/runtime environment uses Windows multiprocessing semantics.

---

## M6.5 — Phase 5.6 Safety Matrix Regression

Add one compact integration test/table-driven matrix covering the final precedence rules across M1–M5.

At minimum assert these precedence relationships:

```text
CORRUPTION / STORE INSPECTION FAILURE
    > autonomous continuation

DURABLE TERMINAL / CANCELLATION
    > scheduled retry
    > pending resume work
    > next LLM iteration

RUN BUDGET EXHAUSTION
    > new LLM/tool work

EXISTING STABLE call_id
    > duplicate logical budget charge
    > duplicate side effect

RetryPolicyEngine STOP
    > retry continuation
```

Do not encode these as a second policy engine. The matrix is verification of existing behavior.

---

## M6.6 — Production Readiness Documentation

Create:

`docs/PHASE_56_PRODUCTION_READINESS.md`

Document concisely:
- Phase 5.6 scope and completed milestones M1–M6;
- runtime safety invariants;
- production preflight/readiness API usage;
- READY vs NOT_READY meaning;
- what readiness does **not** test (provider availability, internet connectivity, external API quota, business correctness);
- crash/resume semantics;
- logical tool budget vs retry attempts;
- retry continuation cancellation/terminal guard;
- corruption behavior (fail closed, no auto-repair);
- same-call concurrency/idempotency behavior;
- timeout limitation if still session-scoped across crash/resume;
- commands to run focused Phase 5.6 tests and full suite.

Documentation must describe actual implemented behavior only.

---

## M6.7 — Durable Phase Completion Evidence

`.ai/results/RESULT-009.md` must include:
- exact task/review authorization;
- commit SHA or immutable reviewed-head reference according to current AIOS publishing contract;
- focused readiness/soak test command and pass count;
- full repository test command and pass count;
- readiness checks implemented;
- safety matrix covered;
- known limitations intentionally retained;
- no claim of external provider/network readiness unless actually tested (it should not be tested here).

---

## Required Tests

Add deterministic coverage for at least:

1. valid fresh configuration returns READY;
2. zero iteration/tool budgets remain valid policy and can still be READY;
3. invalid RunPolicy returns/fails NOT_READY deterministically before autonomous work;
4. invalid RetryPolicy configuration returns NOT_READY;
5. missing checkpoint/idempotency stores are acceptable for a fresh runtime where current construction allows it;
6. empty stores are READY;
7. malformed checkpoint JSON => NOT_READY, file unchanged;
8. invalid checkpoint transition/sequence => NOT_READY;
9. malformed idempotency store => NOT_READY, file unchanged;
10. completed healthy run + consistent idempotency state => READY;
11. cross-store mismatch for a recoverable/pending logical call => NOT_READY;
12. terminal run is never reported as active/recoverable continuation;
13. readiness evaluation performs zero LLM calls;
14. readiness evaluation performs zero tool side effects;
15. readiness evaluation does not append/modify checkpoint store;
16. readiness evaluation does not modify idempotency store;
17. safety matrix: cancellation/terminal blocks scheduled retry;
18. safety matrix: budget exhaustion blocks new work;
19. safety matrix: stable call_id avoids duplicate side effect/budget charge;
20. safety matrix: corruption blocks continuation;
21. bounded repeated lifecycle soak completes with valid integrity every round;
22. bounded crash/resume soak preserves budget and idempotency every round;
23. bounded retry soak preserves logical tool-call accounting;
24. existing M1–M5 regressions remain green, including Retry-After/jitter;
25. full repository suite passes.

---

## Protected / Non-Goals

Do NOT in TASK-009:
- modify `bridge.py` or AIOS workflow;
- redesign AgentLoop;
- create a new retry engine;
- create a new checkpoint/state machine;
- add external provider/network/API health checks;
- add provider billing/token-dollar accounting;
- add queues/distributed workers;
- add automatic corruption repair;
- add background chaos/soak daemons;
- change stable call-id semantics;
- weaken cancellation/terminal precedence;
- change Retry-After/jitter delay semantics;
- perform unrelated product scraping/content/affiliate feature work;
- auto-merge.

If deterministic readiness/soak tests expose a real correctness bug, make the minimum production fix needed and add a regression for that exact bug.

---

## Expected File Scope

Likely files (exact set may vary after inspection):
- `src/agent/production_readiness.py` (new, or equivalent focused module)
- minimal bootstrap/composition integration only if there is a clean existing boundary
- `tests/integration/test_phase56_production_readiness.py` (new)
- `tests/integration/test_phase56_soak.py` (new or equivalent)
- `docs/PHASE_56_PRODUCTION_READINESS.md` (new)
- existing integrity/idempotency helpers only if a small read-only helper is genuinely missing

Avoid broad source refactors.

---

## Acceptance Criteria

- [ ] Typed deterministic production-readiness report exists.
- [ ] Readiness evaluation is read-only and has no LLM/tool side effects.
- [ ] Invalid policy/retry configuration is NOT_READY/fail-closed.
- [ ] Fresh missing/empty stores are handled safely.
- [ ] Checkpoint corruption is NOT_READY and never auto-repaired.
- [ ] Idempotency-store corruption/inconsistency is NOT_READY and never auto-repaired.
- [ ] Cross-store recovery mismatch is NOT_READY.
- [ ] Existing terminal/cancellation/retry/budget/idempotency precedence remains intact.
- [ ] Bounded deterministic soak verifies repeated lifecycle/recovery behavior.
- [ ] Phase 5.6 production-readiness documentation exists and matches implementation.
- [ ] Focused readiness/soak suite passes.
- [ ] Full repository suite passes.
- [ ] `.ai/results/RESULT-009.md` contains durable completion evidence.
- [ ] Branch `ai/task-009` is pushed for ChatGPT review.
- [ ] No merge occurs without explicit `Merge TASK-009` from the user.

---

## Delivery

Use AIOS v0.4.0 zero-touch workflow:

```text
/aios-worker RUN TASK-009
```

Worker must:
1. handoff exact current TASK-009 artifact;
2. safely reconcile local `main` with `origin/main`;
3. work only on `ai/task-009`;
4. implement M6 production-readiness gate and bounded deterministic soak verification;
5. run focused Phase 5.6 readiness/soak tests;
6. run the full repository suite;
7. publish `.ai/results/RESULT-009.md` through ACTIVE exact RUN authorization;
8. push branch;
9. do not merge.
