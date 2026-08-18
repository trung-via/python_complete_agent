# TASK-035 — M9.2 Human-Authorized Hot Local Handoff Bridge Lifecycle

## Work Class

`L4 — CONTROL PLANE / AUTHORITY TRANSITION / DIRTY-WORKSPACE HANDOFF`

Primary Brain has already completed architecture analysis and implementation planning.

**Executor mode for this task: THIN EXECUTOR.**

Primary Brain owns:
- ADR interpretation;
- lifecycle architecture;
- implementation blueprint;
- test design;
- independent semantic review;
- PASS / CHANGES_REQUIRED decision.

Executor owns only:
- bounded implementation of the supplied blueprint;
- focused test execution;
- truthful implementation/test report.

Human remains sole authority for:
- RUN;
- FIX;
- hot-handoff prepare confirmation;
- replacement Executor selection/activation;
- MERGE.

---

# Baseline

Canonical `main` at task authoring:

```text
6d9222523fa24ac7b456299f37655b6c544523a9
```

TASK-034 / M9.1 is PASS and merged.

Authoritative contracts:

```text
.ai/decisions/ADR-023-M9-HOT-LOCAL-HANDOFF-CONTRACT-LOCK.md
.ai/decisions/ADR-024-M9.2-HOT-HANDOFF-BRIDGE-LIFECYCLE-CONTRACT-LOCK.md
```

ADR-024 authoring commit:

```text
0152c47aab28faa994b90a33c7c7c5e0afcfed58
```

ADR-024 blob:

```text
701e5a29bce56d6eed18d24095076db4dcdfe93c
```

Primary-Brain implementation blueprint:

```text
.ai/context/TASK-035-IMPLEMENTATION-BLUEPRINT.md
```

Blueprint authoring commit:

```text
31007829c898142f0b081108d0b1c841385499e0
```

Blueprint blob:

```text
f4a18ab4ec663c80dbcba2bc4d2e7ab76a182491
```

The Executor SHALL treat ADR-024 + the exact blueprint as authoritative and SHALL NOT redesign M9.2.

---

# Objective

Integrate the already-proven M9.1 checkpoint primitive into an explicit Human-controlled Bridge lifecycle that can safely transition one unpublished dirty task workspace from a source Executor to a distinct replacement Executor without ever permitting two active leases.

M9.2 must implement:

```text
ACTIVE(source)
  -> hot-handoff-prepare --confirm-quiescent
  -> exact checkpoint capture/verify
  -> exact source lease release
  -> checkpoint re-verify
  -> HANDOFF_PREPARED / zero active leases
  -> hot-handoff-activate --executor <distinct> --checkpoint <exact fp>
  -> checkpoint verify
  -> new replacement lease acquire
  -> checkpoint re-verify
  -> ACTIVE(replacement, checkpoint-bound)
```

This task implements lifecycle safety only.

It MUST NOT perform or claim the M9.3 real two-Executor proof.

---

# Locked Implementation Contract

## C1 — Exact commands

Add exactly:

```text
bridge.py hot-handoff-prepare <task_id> --confirm-quiescent
bridge.py hot-handoff-activate <task_id> --executor <replacement> --checkpoint <fingerprint>
```

Activation MUST NOT have a default replacement Executor.

## C2 — Exact source authority

Prepare requires:
- current expected task branch;
- exact ACTIVE authorization;
- exact active source lease reconstructed from authorization;
- unchanged authoritative control artifact blob;
- exact current workspace ID.

No authorization may be invented or inferred.

## C3 — Opt-in scope marker

The currently authorized TASK/REVIEW must contain exactly one:

```text
HOT_HANDOFF_ALLOWED_PATHS_JSON: ["path/one", "path/two"]
```

Bridge uses exactly that JSON array as M9.1 `allowed_paths`.

No CLI scope widening. No Markdown heading inference. No dirty-file-derived scope.

## C4 — Protected control-plane state cannot be hot-handed-off

Prepare fails if dirty paths include any of:

```text
bridge.py
src/aios_bridge/runtime_lease.py
src/aios_bridge/continuity/hot_handoff.py
src/aios_bridge/continuity/lease.py
src/aios_bridge/continuity/executor.py
src/aios_bridge/continuity/executor_failover.py
src/aios_bridge/continuity/state.py
src/aios_bridge/continuity/errors.py
```

## C5 — M9.1 primitive is reused unchanged

Use existing:

```text
HotHandoffCheckpoint
capture_hot_handoff_checkpoint
verify_hot_handoff_checkpoint
```

Do not copy/reimplement checkpoint hashing, Git-status parsing, path safety, or payload verification inside Bridge.

## C6 — Prepare order and rollback

Implement the exact prepare algorithm and rollback rules in the blueprint.

Successful prepare MUST end with:

```text
authorization.status = HANDOFF_PREPARED
active lease = NONE
checkpoint persisted outside worktree
workspace still exactly equals checkpoint
```

If failure happens after source release, attempt exact source-lease/auth restoration; if restoration cannot be proven, transition to `RECOVERY_REQUIRED` and stop.

## C7 — Activation order and rollback

Implement the exact activation algorithm and rollback rules in the blueprint.

Successful activation MUST end with:

```text
authorization.status = ACTIVE
authorization.executor_id = replacement
active lease executor = replacement
replacement lease != source lease
hot_handoff provenance retained
workspace still equals checkpoint at activation boundary
```

If post-acquire verification/persistence fails, release the replacement lease and preserve `HANDOFF_PREPARED` when rollback is provable.

## C8 — Single active Executor invariant

At no tested point may both source and replacement leases be active.

Existing M5 lease contract/store remains unchanged.

## C9 — Stable failover remains separate

Hot handoff MUST NOT create or reuse:

```text
StableExecutorFailoverProof
M6 failover proof
M8 composite proof
```

Existing `EXECUTOR_FAILOVER` semantics remain unchanged.

## C10 — Context visibility

`bridge.py context <id>` exposes the nested `hot_handoff` metadata without changing other context semantics.

## C11 — Publish provenance

For activated hot-handoff authorization, publish validates complete persisted hot-handoff provenance before tests/RESULT creation but does NOT require workspace equality with the checkpoint after replacement work has continued.

Hot-handoff RESULT manifest adds:

```text
HOT_HANDOFF: YES
HOT_HANDOFF_CHECKPOINT_FINGERPRINT: <fp>
HOT_HANDOFF_FROM_EXECUTOR: <source>
HOT_HANDOFF_TO_EXECUTOR: <replacement>
```

Ordinary publication emits:

```text
HOT_HANDOFF: NO
```

`EXECUTOR_FAILOVER` behavior MUST remain untouched.

## C12 — No M5/M6/M8 redesign

Forbidden semantic changes:

```text
src/aios_bridge/runtime_lease.py
src/aios_bridge/continuity/lease.py
src/aios_bridge/continuity/hot_handoff.py
src/aios_bridge/continuity/executor_failover.py
```

If existing primitives prove insufficient, STOP and report the exact blocker.

---

# Implementation Blueprint

The exact implementation plan is already authored at:

```text
.ai/context/TASK-035-IMPLEMENTATION-BLUEPRINT.md
```

Executor MUST follow it rather than performing broad repository discovery.

If actual code conflicts materially with the blueprint, Executor must stop and report:

```text
BLOCKER
EXACT_FILE
EXACT_SYMBOL
EXPECTED_BY_BLUEPRINT
ACTUAL_CODE
WHY_SAFE_IMPLEMENTATION_CANNOT_CONTINUE
```

Do not silently redesign.

---

# Allowed Files

Implementation:

```text
bridge.py
```

Focused tests:

```text
tests/test_bridge_hot_handoff.py
```

Bridge-generated publication artifact:

```text
.ai/results/RESULT-035.md
```

No other repository changes are authorized.

---

# Forbidden Scope

```text
src/aios_bridge/runtime_lease.py
src/aios_bridge/continuity/lease.py
src/aios_bridge/continuity/hot_handoff.py
src/aios_bridge/continuity/executor.py
src/aios_bridge/continuity/executor_failover.py
src/aios_bridge/continuity/state.py
product/scraper code
browser automation
provider integration
quota detection
smart routing
M9.3 real-proof work
M10 deterministic dispatch
M11 API escape hatch
unrelated RESULT diff-stat cleanup
```

---

# Required Adversarial Tests

Focused tests in `tests/test_bridge_hot_handoff.py` MUST prove at minimum:

```text
[ ] prepare requires --confirm-quiescent
[ ] prepare requires exact ACTIVE authorization
[ ] source lease must exactly match authorization
[ ] control artifact blob drift blocks prepare
[ ] missing hot-handoff scope marker blocks prepare
[ ] duplicate/malformed/empty/duplicate-item scope marker blocks prepare
[ ] protected dirty control-plane path blocks prepare
[ ] capture or pre-release verify failure leaves source lease/auth active
[ ] successful prepare releases source lease
[ ] successful prepare sets HANDOFF_PREPARED
[ ] post-release verify failure rolls source lease/auth back when possible
[ ] activation requires explicit supported replacement
[ ] same source/replacement executor rejected
[ ] wrong checkpoint fingerprint rejected
[ ] workspace drift before activation rejected
[ ] control artifact drift before activation rejected
[ ] any active lease before activation blocks replacement
[ ] successful activation creates new replacement lease
[ ] successful activation creates ACTIVE replacement authorization
[ ] source checkpoint provenance survives activation
[ ] post-acquire verify failure releases replacement lease
[ ] post-acquire failure preserves HANDOFF_PREPARED when rollback succeeds
[ ] context surfaces hot_handoff metadata
[ ] partial/malformed activated metadata blocks publish
[ ] hot handoff does not manufacture stable failover proof
[ ] ordinary RUN/FIX/non-hot-handoff behavior regresses zero
```

No real external Executor provider calls are permitted in automated tests.

---

# Thin Executor Read Budget

Codex SHOULD read only:

```text
.ai/tasks/TASK-035.md
.ai/decisions/ADR-024-M9.2-HOT-HANDOFF-BRIDGE-LIFECYCLE-CONTRACT-LOCK.md
.ai/context/TASK-035-IMPLEMENTATION-BLUEPRINT.md
bridge.py relevant named functions/sections
tests/test_bridge.py only for fixture/style patterns
src/aios_bridge/continuity/hot_handoff.py public API only if needed
```

Forbidden by default:

```text
broad rg across repository
recursive src/ inspection
recursive tests/ inspection
architecture redesign
alternative-solution exploration
full repository tests inside Codex session
```

A narrow lookup is allowed only if a concrete blocker cannot be resolved from the supplied blueprint.

---

# Executor Test Gate

Codex runs only focused/Bridge regression tests:

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_bridge_hot_handoff.py -q
.\venv\Scripts\python.exe -m pytest tests/test_bridge.py -q
```

Then STOP and report.

Codex MUST NOT run full `tests/` unless the Human explicitly asks after a blocker.

---

# Publication Gate

Human/Bridge runs the full repository suite exactly once:

```powershell
.\venv\Scripts\python.exe .\bridge.py publish 35 --action RUN --test ".\venv\Scripts\python.exe -m pytest tests/ -q"
```

Bridge remains sole RESULT/commit/push authority.

---

# Completion Contract

TASK-035 is complete only when:

```text
[ ] only allowed implementation/test files changed before RESULT
[ ] two Human-controlled hot-handoff commands exist
[ ] exact scope marker parsing is fail-closed
[ ] protected dirty control-plane paths are blocked
[ ] source auth/lease/checkpoint bindings are exact
[ ] prepare release ordering is exact
[ ] prepare rollback is fail-closed
[ ] successful prepare has zero active Executors
[ ] activation requires distinct explicit replacement
[ ] checkpoint is verified before and after replacement acquire
[ ] activation rollback is fail-closed
[ ] replacement authorization is a new exact execution binding
[ ] no two active leases are observed
[ ] context exposes safe hot-handoff provenance
[ ] publish validates hot-handoff provenance
[ ] RESULT distinguishes HOT_HANDOFF from EXECUTOR_FAILOVER
[ ] M5 lease contract unchanged
[ ] M6/M8 failover contracts unchanged
[ ] targeted M9.2 tests pass
[ ] existing Bridge tests pass
[ ] full repository suite passes through Bridge publication gate
[ ] RESULT-035 is Bridge-generated
[ ] Primary Brain independent review PASS
```

M9.2 PASS does not authorize or prove M9.3 automatically.