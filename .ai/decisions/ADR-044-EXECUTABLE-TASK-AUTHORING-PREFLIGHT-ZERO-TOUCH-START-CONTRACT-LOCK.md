# ADR-044 — Executable Task Authoring Preflight & Zero-Touch Start Contract Lock

STATUS: LOCKED
DATE: 2026-08-23
SCOPE: AIOS Bridge executable TASK/REVIEW handoff preflight
BASELINE_MAIN_SHA: 2eb9822bfcd923bd937598def9fcf1f2c93b6c9b
H1_STATUS: COMPLETE
LEAN_AUTO_MERGE: ENABLED
DUAL_EXECUTOR_OPERATIONAL_BASELINE: PROVEN

## 1. Decision

AIOS Bridge must reject malformed executable TASK/REVIEW artifacts at handoff time, before any executor lease, authorization, task-state mutation, task-branch creation/switch, or bounded executor invocation.

The intent is to eliminate the TASK-070 failure class where missing E4 markers were discovered only after authorization/lease creation.

Locked flow:

```text
Human RUN/FIX
    ↓
fetch exact control artifact + blob
    ↓
EXECUTABLE ARTIFACT PREFLIGHT
    ↓
PASS only
    ↓
safe local-main reconciliation for RUN
    ↓
prepare task branch
    ↓
lease + authorization
    ↓
executor / E4
```

If preflight fails, the workflow stops before authority-bearing or worktree/branch mutations.

## 2. Existing Zero-Touch Start Is Preserved

Bridge v0.4.0 already owns safe local-main reconciliation for RUN. A Human does not need to manually run `git switch main`, `git pull`, `git status`, or `git rev-parse` after every remote auto-merge merely to start the next AIOS task.

The existing reconciliation behavior remains authoritative:

```text
clean local main strictly behind remote main -> fast-forward automatically
local main identical to remote main          -> continue
local main ahead/diverged                    -> fail closed
non-AI dirty worktree                        -> fail closed
reset --hard / force / destructive rebase    -> forbidden
```

TASK-071 must preserve this behavior; it must not introduce a second synchronization mechanism.

## 3. Preflight Position Is Security-Critical

Executable-artifact preflight must occur after the exact control artifact and blob are fetched/read, but before all of the following:

```text
TASK_BRANCH_CREATE_OR_SWITCH
LOCAL_MAIN_RECONCILIATION_MUTATION
EXECUTOR_LEASE_ACQUIRE
AUTHORIZATION_WRITE
TASK_STATE_AUTHORITY_MUTATION
EXECUTOR_PROCESS_START
```

External non-authority caching of the exact fetched control artifact is permitted.

A malformed task must not leave a lease that requires manual release.

## 4. Required Machine-Readable Markers

For executable RUN/FIX artifacts, preflight must validate the complete existing E4 marker set:

```text
EXECUTOR_CONTEXT_REFS_JSON:
EXECUTOR_ALLOWED_PATHS_JSON:
DISPATCH_EXECUTOR_POLICY_JSON:
```

Each marker must occur exactly once and must parse through the existing canonical Bridge parsers. No alternate parser or permissive fallback is allowed.

Preflight must reuse existing contracts rather than duplicate/reinterpret them.

## 5. Cross-Marker / Operation Validation

Preflight must bind marker semantics to the requested handoff:

```text
artifact operation == requested RUN/FIX
selected executor is an exact declared candidate
selected executor supports the requested operation
required capabilities are satisfiable by the selected candidate
paid-API policy is not inferred or broadened
context refs remain within existing E4 bounds
allowed paths remain canonical existing E4 scope semantics
```

No preflight outcome may select a different executor, retry, reroute, or create authority.

## 6. Strict Failure Semantics

Preflight is deterministic and fail-closed.

At minimum reject:

```text
missing marker
multiple same marker
malformed JSON
invalid context ref
invalid/empty/duplicate allowed path
malformed dispatch policy
operation mismatch
selected executor absent from policy
selected executor unsupported for operation/capabilities
```

On any failure:

```text
LEASE_CREATED: NO
AUTHORIZATION_CREATED: NO
TASK_BRANCH_CREATED_OR_SWITCHED: NO
EXECUTOR_CALLED: NO
AUTO_RETRY: NO
AUTO_REROUTE: NO
```

The Human receives one concise preflight reason and may correct the control artifact before a fresh explicit RUN/FIX.

## 7. RESULT / Publisher Authoring Boundary

Bridge E4 owns canonical RESULT publication. Executable task authoring must not make arbitrary custom RESULT keys a hard acceptance dependency unless the active Bridge publisher contract can actually emit them.

For current E4:

```text
canonical Bridge-generated E4/full-suite publication evidence = authoritative
implementation-specific invariants = prove through source/tests and ChatGPT review
```

TASK-071 must not broaden Bridge publication schema merely to satisfy free-form task prose. The authoring/preflight layer should expose a deterministic publisher-profile check or equivalent closed rule preventing unsupported custom publication requirements from becoming executable-task blockers.

## 8. Authority Boundary

Preflight is validation only.

It MUST NOT:

```text
create approval
acquire lease
mutate review/task state
select/reroute executor
invoke provider/model
use paid API
merge branches
retry execution
```

Worker merge prohibition and ADR-042 Lean Auto-Merge remain unchanged.

## 9. Implementation Direction

Preferred shape:

```text
src/aios_bridge/task_authoring.py
    ExecutableArtifactPreflight
    ExecutableArtifactPreflightError
    preflight_executable_artifact(...)

bridge.py
    cmd_handoff(...)
       fetch/read exact artifact
       preflight_executable_artifact(...)
       only then reconcile/prepare/acquire/authorize
```

Equivalent repository-owned factoring is acceptable if the same authority ordering is mechanically proven.

## 10. Acceptance Tests

Tests must prove at minimum:

```text
MISSING_CONTEXT_MARKER_FAILS_BEFORE_LEASE: YES
MISSING_ALLOWED_PATHS_MARKER_FAILS_BEFORE_LEASE: YES
MISSING_DISPATCH_MARKER_FAILS_BEFORE_LEASE: YES
DUPLICATE_MARKER_FAILS_BEFORE_LEASE: YES
MALFORMED_MARKER_FAILS_BEFORE_LEASE: YES
OPERATION_MISMATCH_FAILS_BEFORE_LEASE: YES
EXECUTOR_NOT_DECLARED_FAILS_BEFORE_LEASE: YES

PREFLIGHT_FAILURE_TASK_BRANCH_MUTATION: NO
PREFLIGHT_FAILURE_AUTHORIZATION_CREATED: NO
PREFLIGHT_FAILURE_STATE_AUTHORITY_MUTATED: NO
PREFLIGHT_FAILURE_EXECUTOR_CALLED: NO

VALID_RUN_PREFLIGHT: PASS
VALID_FIX_PREFLIGHT: PASS
EXISTING_E4_PARSERS_REUSED: YES

LOCAL_MAIN_BEHIND_REMOTE_AUTO_FAST_FORWARD: PASS
MANUAL_POST_MERGE_PULL_REQUIRED_FOR_NEXT_TASK: NO
LOCAL_MAIN_DIVERGED_FAIL_CLOSED: YES
DIRTY_WORKTREE_FAIL_CLOSED: YES
FORCE_OR_RESET_USED: NO
```

No real Codex/Antigravity process is required for TASK-071 automated tests.

## 11. Non-Changes

TASK-071 must not change:

```text
E4 marker schemas
MAX_AUTOMATION_CONTEXT_REFS
executor identity semantics
lease schema
paid API grant semantics
retry/failover semantics
Lean Auto-Merge semantics
H-Series H0/H1 implementation
```

No dependency changes.

## 12. Sequence

```text
H0 ✅
H1 ✅
TASK-071 authoring/handoff preflight hardening
    ↓
review + auto-merge
    ↓
H2 contract/task cycle
```

TASK-071 does not itself authorize H2 implementation.
