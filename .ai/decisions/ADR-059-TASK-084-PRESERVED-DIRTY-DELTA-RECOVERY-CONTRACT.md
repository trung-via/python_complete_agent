# ADR-059 — TASK-084 Preserved Dirty-Delta Recovery Contract

STATUS: ACCEPTED
DECISION_TYPE: ONE_TIME_RECOVERY_REFINEMENT
HUMAN_APPROVED: YES
AUTHORIZED_TASK: TASK-084
AUTHORIZED_EXECUTOR: codex
ONE_TIME_EXCEPTION: YES
AUTO_RETRY_ALLOWED: NO
AUTO_REROUTE_ALLOWED: NO
TASK_ARTIFACT_MUTATION_ALLOWED: NO
H5_OPENED: NO

## Context

TASK-084 passed authorization/preflight and Codex produced a productive in-scope implementation delta, but Bridge certification stopped publication because the full repository suite reported 3 failures while 2521 tests passed and 7 were skipped.

The failure class is bounded: governed-roadmap merge/preflight tests attempted to resolve `.ai/roadmaps/CANONICAL-ROADMAP-REGISTRY-v1.json` from the task worktree instead of the exact synchronized control-plane artifact/cache. Bridge correctly performed no commit, no push, no automatic retry, and no reroute.

After the failed certification, the productive worktree delta remains present and the exact TASK-084 Codex lease remains ACTIVE. However, the current `bridge.py execute 84` path requires a clean worktree before launching Codex, creating a recovery gap: Bridge preserves productive dirty delta but cannot re-enter its bounded Codex launcher while that delta exists.

## Decision

Authorize one recovery action for TASK-084 only: the already-selected Codex operator session may edit the existing preserved dirty delta under the still-active TASK-084 authority, solely to close the observed registry-resolution failures.

This is not a new RUN, not an automatic retry, not executor rerouting, and not a new authorization. It is a Human-approved continuation of the already-authorized TASK-084 work using the same task branch and existing active Codex lease.

TASK-084 itself MUST NOT be edited or rebound during this recovery, because its exact artifact blob is already bound to the active authorization.

## Allowed Recovery Work

The Codex operator may:

```text
inspect the existing TASK-084 dirty delta
inspect the exact 3 failing tests / tracebacks
edit only paths already authorized by TASK-084
correct canonical registry resolution so Bridge consumes exact synchronized ai-control evidence rather than assuming the manifest is present in the task worktree
run TASK-084 targeted tests
run git diff --check
```

The Codex operator MUST NOT:

```text
reset or discard the preserved delta
stash the preserved delta
checkout another branch
create a new RUN authorization
release or replace the current executor lease
commit or push directly
run the full repository suite inside the interactive recovery session
change TASK-084, ADR-058, roadmap semantics, P0 validation logic, H5-H8, retry/reroute, lease authority, review authority, or merge authority
```

## Resolver Contract

The corrected implementation must preserve the TASK-084 contract:

```text
canonical registry source = synchronized exact ai-control control-plane evidence
registry identity/provenance remains exact and bounded
missing registry fails closed
malformed registry fails closed
unknown roadmap identity fails closed
registered roadmap exact blob is still required
canonical roadmap parser still validates exact roadmap bytes
TASK-083 Lean v1.1 binding resolves through normal generic preflight
no TASK-083-specific bypass
```

A local task-worktree copy of `.ai/roadmaps/CANONICAL-ROADMAP-REGISTRY-v1.json` must not be required for normal governed-roadmap merge/preflight behavior.

## Recovery Validation Ownership

The interactive Codex recovery runs only:

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_bridge/test_roadmap_governance.py tests/test_bridge_task_authoring.py tests/test_bridge.py -q
git diff --check
```

After those targeted checks are green, canonical publication remains owned by Bridge. The Human/operator must invoke `bridge.py publish 84` with the full repository suite as the publication test. Bridge remains responsible for fail-closed certification, RESULT creation, commit, push, and lease consumption/release.

## Publication Boundary

Publication is authorized only if:

```text
same TASK-084 branch
same preserved authority lineage
same authorized Codex executor
all dirty paths remain within TASK-084 allowed paths
targeted recovery validation is green
git diff --check is green
Bridge full canonical repository suite is green
Bridge publication trust and lease checks remain green
```

If publication fails again, no manual commit/push is authorized.

## Exhaustion

ADR-059 is exhausted when TASK-084 publishes successfully or the Human explicitly abandons this preserved delta. It creates no precedent for future tasks.

The missing generic dirty-delta resume capability is recorded as execution-layer debt to be addressed under the already-approved Lean Execution roadmap rather than expanded inside TASK-084.
