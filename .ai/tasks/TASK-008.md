# TASK-008 — Phase 5.6 M5 Fault Injection & Concurrency Verification

## Objective
Continue Phase 5.6 after M4 Run Budget Enforcement by verifying the reliability control plane under deterministic crash, retry, cancellation, resume, and concurrency fault scenarios.

Canonical baseline when authored:
- `main`: `799aa448385e3058e73b7e905b4127f859396dd0`
- AIOS Bridge: v0.4.0 zero-touch handoff
- Phase 5.6 status:
  - M1 Cancellation ✅
  - M2 Retry Policy Engine ✅
  - M3 Retry Timeline & Failure Classification ✅
  - M4 Run Budget Enforcement ✅
  - M5 Fault Injection & Concurrency Verification ⏭ CURRENT

Existing Phase 5.5 reliability tests already cover basic crash/resume, integrity verification, interleaved runs, store maintenance, and four-process checkpoint activity. M5 must go beyond those happy-path reliability checks and stress the interactions between the Phase 5.6 control mechanisms.

This milestone is **verification-first**. Do not redesign the runtime unless a deterministic test exposes a real correctness gap.

---

## Core Invariants to Verify

The combined control plane must preserve all of these under faults and races:

1. Cancellation prevents any new autonomous work once durable cancellation wins.
2. Terminal states are immutable.
3. Corruption and checkpoint-store failures fail closed.
4. Retry precedence from M2 remains authoritative.
5. Retry delay semantics from M3 preserve `retry_after` and jitter behavior.
6. A stable `call_id` remains one logical tool call across retry/replay/resume.
7. M4 iteration/tool budgets do not reset after crash/resume.
8. Concurrent activity must not create duplicate logical tool execution where idempotency should prevent it.
9. No race may silently turn STOP into RETRY or terminal into active.
10. Fault tests must be deterministic and repeatable; no flaky timing-based assertions.

---

## M5.1 — Deterministic Fault-Injection Test Harness

Create a focused test-only fault injection utility under `tests/support/` or equivalent.

The harness should support deterministic failpoints such as:
- before/after LLM request checkpoint;
- after LLM response checkpoint but before tool execution;
- before first tool attempt;
- after tool side effect / idempotency completion but before final tool-result checkpoint;
- after failed attempt but before retry sleep;
- after `RETRY_SCHEDULED` checkpoint;
- before/after resumed pending-tool execution;
- checkpoint write failure at selected boundaries.

Requirements:
- test-only by default; do not add a production remote-debug backdoor;
- use explicit events/barriers/callbacks/fakes rather than arbitrary `sleep()` for synchronization;
- faults must be reproducible by name/index;
- failure injection must not mutate unrelated repository/runtime state.

A small injectable callback seam in production code is acceptable only if unavoidable and must default to no-op, be narrowly scoped, and have no behavior change when unused. Prefer monkeypatch/fakes around existing boundaries first.

---

## M5.2 — Crash Boundary Verification

Add integration tests for critical crash windows.

At minimum verify:

### A. Crash after LLM response, before tool execution
- resume reconstructs the pending tool;
- tool executes exactly once logically;
- budget is not double charged;
- final run can complete.

### B. Tool side effect succeeds, checkpoint/result persistence fails
Use the existing idempotency model to simulate:

```text
tool side effect succeeds
idempotency completion becomes durable
process/checkpoint path fails before TOOL_RESULT_RECEIVED
resume
```

Expected:
- no duplicate external tool side effect;
- resumed path resolves through idempotency state;
- same `call_id` remains one logical budget unit;
- timeline remains valid or fails closed if the durable state is inconsistent.

### C. Crash after failed attempt / `RETRY_SCHEDULED`, before next attempt
Expected:
- resume must not invent an extra logical tool call;
- retry policy limits still apply;
- current run state must not bypass cancellation/terminal checks.

Do not add a background retry daemon in this milestone.

---

## M5.3 — Cancellation Race Verification

Add deterministic race tests for cancellation against active/recovering work.

Required cases:

1. cancel vs next LLM iteration;
2. cancel vs pending tool execution on resume;
3. cancel after a failed attempt but before retry continuation;
4. repeated concurrent cancel requests remain idempotent;
5. cancellation checkpoint write failure does not falsely mark memory cancelled;
6. once cancellation has become durable, no new LLM/tool operation occurs.

Use barriers/events so the race boundary is controlled, not probabilistic.

Preserve existing cancellation reason/event contract.

---

## M5.4 — Concurrent Resume / Duplicate Execution Safety

Stress same-run concurrency, not only independent runs.

Required scenarios:

### Same run, two resume contenders
Start two workers/threads/processes attempting recovery of the same interrupted run.

Expected safety property:
- at most one external side effect for one stable `call_id` when idempotency is active;
- both contenders must not independently execute the same logical tool side effect;
- resulting durable state must remain valid or one contender must fail closed cleanly;
- no corrupt checkpoint sequence.

Do not assert both resumes must return success if the architecture intentionally permits one to fail closed. The invariant is no duplicate effect and no silent corruption.

### Independent runs sharing stores
Retain/extend the existing four-process reliability scenario with:
- distinct `run_id`s;
- distinct logical calls;
- shared checkpoint/idempotency stores where supported;
- integrity verification for every completed run.

### Concurrent same `call_id`
Two execution contenders for the same `(run_id, call_id)` must converge through idempotency behavior rather than perform duplicate side effects.

---

## M5.5 — Budget × Retry × Resume Interaction Matrix

Add focused cross-feature tests instead of testing each component in isolation.

Required cases:

1. `max_tool_calls=1`, tool A retries multiple attempts, crash/resume in between -> still exactly one logical tool budget unit.
2. run consumes iteration budget before crash; resume cannot get extra iterations.
3. durable usage already at tool limit + pending previously-seen call A -> replay A is not charged again.
4. durable usage at tool limit + genuinely new call B -> halt before B executes.
5. cancellation arrives while retryable failure is waiting to continue -> no next attempt after cancellation wins.
6. terminal state appears before scheduled retry continuation -> no retry execution.

Preserve TASK-003/TASK-005 actual delay semantics; do not replace actual delay with `RetryDecision.delay_seconds` if legacy delay carries `retry_after`/jitter.

---

## M5.6 — Corruption / Persistence Fail-Closed Matrix

Verify production safety under storage failures.

At minimum:
- malformed checkpoint JSON -> no resume mutation, deterministic corruption failure;
- invalid sequence/timestamp/state transition -> fail closed;
- checkpoint write failure during cancellation -> cancellation memory state is not falsely advanced;
- checkpoint/infrastructure persistence failure during tool/retry path remains `SystemStateError` / checkpoint-store domain as appropriate;
- raw application/tool `OSError` must not automatically be reclassified as checkpoint-store failure unless it comes from the persistence boundary;
- terminal checkpoint immutability remains enforced after any recovery attempt.

Do not auto-repair checkpoint corruption.

---

## M5.7 — Operational Verification Report

Create a durable test/verification summary for this milestone through normal AIOS publishing.

`.ai/results/RESULT-008.md` must include:
- exact test command(s);
- exit code(s);
- total pass count;
- focused M5 test count if separately run;
- commit SHA;
- short note listing which fault classes were verified;
- any known limitation that remains intentionally untested.

No need to create a new production observability subsystem in this milestone.

---

## Required Tests

Add deterministic coverage for at least these scenarios:

1. crash after LLM response before tool execution -> one logical execution after resume;
2. side effect durable/idempotent but tool-result checkpoint missing -> no duplicate side effect after resume;
3. crash after `RETRY_SCHEDULED` before retry continuation;
4. cancel before resumed pending tool -> zero new tool execution;
5. cancel after retryable failure before next attempt -> zero next attempt;
6. concurrent repeated cancel is idempotent;
7. same-run concurrent resumes do not duplicate one stable `call_id` side effect;
8. concurrent same `(run_id, call_id)` execution converges through idempotency;
9. 4+ independent concurrent runs preserve checkpoint integrity;
10. retry attempts across crash/resume count as one logical tool budget unit;
11. consumed iteration budget persists through crash/resume;
12. new call beyond durable tool budget is blocked before execution;
13. previously-seen pending call at limit may replay without extra charge;
14. malformed checkpoint JSON fails closed and remains unmodified;
15. invalid checkpoint transition/sequence fails closed;
16. persistence failure is classified as infrastructure/checkpoint-store failure;
17. application/tool raw `OSError` is not falsely promoted to checkpoint-store failure;
18. terminal state prevents retry/resume continuation;
19. existing rate-limit `retry_after` regression remains green;
20. existing jitter regression remains green;
21. full repository suite passes.

Where process-level concurrency is too expensive for every case, combine:
- threads/async tasks for deterministic barrier races;
- at least one real multiprocessing same-store/same-run or same-call scenario;
- existing process-safe stores/checkpoint primitives.

---

## Review Expectations

ChatGPT review will check especially for:
- flaky tests based on timing sleeps;
- assertions that only inspect call counts without checking durable state;
- duplicate tool side effects under same-run/same-call races;
- hidden retries after cancellation/terminal state;
- budget drift across resume;
- accidental changes to retry delay semantics;
- source changes made only to satisfy tests but weakening fail-closed behavior.

If a test exposes a real production bug, fix the minimum source surface necessary and add a regression tied to that bug.

---

## Protected / Non-Goals

Do NOT in TASK-008:
- modify `bridge.py` or AIOS workflow;
- add provider pricing/token-cost accounting;
- add distributed queues/workers;
- implement an always-on chaos daemon;
- redesign RetryManager/ReplayEngine/CheckpointManager wholesale;
- auto-repair corrupt checkpoint files;
- weaken terminal-state validation;
- weaken cancellation durability ordering;
- change stable `call_id` semantics;
- auto-merge.

---

## Expected File Scope

Likely files:
- `tests/integration/test_phase56_fault_injection.py` (new)
- `tests/integration/test_phase56_concurrency.py` (new, or equivalent)
- `tests/support/fault_injection.py` (new, if useful)
- existing cancellation/retry/budget/checkpoint integration tests if extending them is cleaner
- minimal production source files only if deterministic tests expose a correctness gap

Avoid broad refactors.

---

## Acceptance Criteria

- [ ] Deterministic fault-injection coverage exists for critical crash boundaries.
- [ ] Same-run concurrency is tested, not only independent runs.
- [ ] Same stable `call_id` cannot cause duplicate side effects through retry/replay/concurrent resume when idempotency is active.
- [ ] Cancellation blocks future work across retry/resume races.
- [ ] Terminal state blocks future retry/resume work.
- [ ] M4 budgets remain correct across retry/crash/resume.
- [ ] Corruption/persistence failures remain fail-closed.
- [ ] RateLimit `retry_after` and jitter semantics remain unchanged.
- [ ] Existing Phase 5.5 reliability suite remains green.
- [ ] Existing TASK-003/TASK-005/TASK-007 regressions remain green.
- [ ] Full repository test suite passes.
- [ ] `.ai/results/RESULT-008.md` contains durable evidence.
- [ ] Branch `ai/task-008` is pushed for ChatGPT review.
- [ ] No merge occurs without explicit `Merge TASK-008` from the user.

---

## Delivery

Use AIOS v0.4.0 normal workflow:

```text
/aios-worker RUN TASK-008
```

Worker must:
1. handoff exact current TASK-008 artifact;
2. safely reconcile local `main` with `origin/main`;
3. work only on `ai/task-008`;
4. implement M5 verification/hardening;
5. run focused M5 tests + full repository suite;
6. publish `.ai/results/RESULT-008.md` through ACTIVE exact RUN authorization;
7. push branch;
8. do not merge.
