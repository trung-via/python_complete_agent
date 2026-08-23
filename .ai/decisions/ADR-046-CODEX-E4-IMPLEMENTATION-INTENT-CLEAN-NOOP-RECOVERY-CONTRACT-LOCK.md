# ADR-046 — Codex E4 Implementation Intent & Clean No-Op Recovery Contract Lock

STATUS: LOCKED
DATE: 2026-08-23
SCOPE: AIOS Bridge Codex E4 refinement before H2 retry
BASELINE_MAIN_SHA: 0f803c2d66244147734c5b8f5ea3670c6f57c6cc
TASK_AUTHORING_PREFLIGHT_STATUS: COMPLETE
H2_TASK_072_STATUS: BLOCKED_BY_CLEAN_CODEX_NOOP
AUTO_RETRY: FORBIDDEN
AUTO_REROUTE: FORBIDDEN
PAID_API_AUTHORITY: NONE

## 1. Decision

Codex E4 already has a fail-closed post-executor invariant: a successful bounded Codex invocation must produce a non-empty worktree delta entirely inside the authorized writable scope. The existing `validate_executor_worktree_delta()` rejects an empty dirty-path set.

TASK-072 exposed a mismatch between that machine invariant and the executor-facing context pack: the thin executor instruction block does not explicitly state that a RUN/FIX implementation execution is required to create an authorized worktree delta. Codex may therefore exit successfully without editing anything, after which E4 detects the no-op only at the post-executor gate.

This ADR fixes the mismatch without introducing a new task marker or widening authority.

Locked flow:

```text
Human-authorized Codex RUN/FIX
        ↓
existing exact TASK/REVIEW + E4 markers
        ↓
context pack explicitly states implementation/delta obligation
        ↓
bounded Codex process
        ↓
post-executor exact Git observation
        ├─ authorized delta present → existing E4 validation/publication path
        └─ clean exact no-op → deterministic blocked cleanup; no publication
```

## 2. No New Authoring Marker

No new executable task marker is introduced.

Reason: E4 already unconditionally requires a non-empty worktree delta for automatic Codex RUN/FIX. A second marker would duplicate an existing runtime invariant and create unnecessary authoring/versioning burden.

The existing executable authoring contract remains:

```text
PUBLISHER_PROFILE: CANONICAL_E4
EXECUTOR_CONTEXT_REFS_JSON
EXECUTOR_ALLOWED_PATHS_JSON
DISPATCH_EXECUTOR_POLICY_JSON
```

TASK-071 authoring preflight remains unchanged.

## 3. Executor-Facing Implementation Intent

The canonical executor context pack instruction profile must state, in bounded deterministic prose, that for Codex E4 RUN/FIX:

```text
IMPLEMENTATION_EXECUTION: YES
AUTHORIZED_WORKTREE_DELTA_REQUIRED: YES
NO_OP_SUCCESS_IS_PROTOCOL_FAILURE: YES
EDIT_SCOPE: ONLY authorized allowed paths
COMMIT_PUSH_PUBLISH_MERGE_BY_EXECUTOR: FORBIDDEN
```

The instruction must not grant authority. It merely communicates an already-existing E4 postcondition.

If Codex cannot implement the requested change, it must not claim successful implementation. E4 remains the final machine verifier and still rejects empty/out-of-scope deltas.

No raw model prose is trusted as proof of completion.

## 4. Exact Clean No-Op Classification

A clean Codex no-op is recognized only when ALL of the following are true after invocation:

```text
invocation receipt status == EXITED_ZERO
publication-trust snapshot == unchanged
post_branch == pre_branch == authorized task branch
post_head_sha == pre_head_sha
dirty_paths == empty
```

This classification is not a success and is not publication-eligible.

It is an exact, bounded `EXECUTION_BLOCKED` condition rather than a generic recovery condition because there is no worktree mutation to preserve and the bounded executor process has already terminated successfully.

Any ambiguity or mismatch remains `RECOVERY_REQUIRED` fail-closed.

## 5. Clean No-Op Authority Cleanup

For the exact clean-no-op condition only, Bridge must perform deterministic cleanup so routine Human lease surgery is unnecessary.

Required transaction:

```text
1. exact active lease/auth binding already verified by E4 pre-invocation
2. invocation receipt proves process exited
3. exact post-state proves branch/head unchanged and no dirty paths
4. release exact active executor lease
5. persist authorization as non-ACTIVE blocked/consumed state that cannot be reused
6. persist task operational state = EXECUTION_BLOCKED
7. return non-zero / fail command with bounded diagnostic
```

No fresh authorization is created.

If lease release or authorization/state persistence cannot be proven, status becomes `RECOVERY_REQUIRED` and Bridge must not pretend cleanup succeeded.

## 6. No Retry / Reroute

Clean no-op handling MUST NOT:

```text
retry Codex
rerun the same invocation
select another executor
activate Antigravity
create failover authority
create a new lease
publish RESULT
commit/push/merge
```

A subsequent attempt requires a new explicit Human RUN/FIX command after the blocked state is clean.

## 7. Diagnostic Contract

The already-persisted bounded E4 invocation receipt remains authoritative evidence for the attempt.

The user-facing failure should distinguish a clean no-op from generic recovery, for example:

```text
E4_EXECUTION_BLOCKED: CLEAN_NO_WORKTREE_DELTA
TRANSPORT: EXITED_ZERO
DIAGNOSTIC: <closed diagnostic code>
LEASE_ACTIVE_AFTER_BLOCK: NO
AUTO_RETRY: NO
AUTO_REROUTE: NO
```

Do not persist or print raw Codex reasoning/prose as trusted diagnostic evidence.

## 8. Authority Boundary

This refinement changes no executor identity or authority boundary.

```text
$aios-worker -> codex
/aios-worker -> antigravity
```

Worker merge authority remains forbidden. Lean Auto-Merge remains review-bound. Paid-provider authority remains unchanged/absent.

## 9. Writable Implementation Scope

Preferred implementation may modify only:

```text
bridge.py
src/aios_bridge/executor_context.py
tests/aios_bridge/test_executor_context_pack.py
tests/test_bridge_executor_automation.py
```

If exact bridge integration tests require an existing adjacent Bridge test file, that path must be explicitly authorized by the executable task before modification.

Do not change worker surface files, H-Series code, lease schema, dispatch policy, RESULT publisher schema, retry/failover semantics, or dependencies.

## 10. Acceptance Invariants

Tests must prove at minimum:

```text
CONTEXT_PACK_STATES_DELTA_REQUIRED: YES
CONTEXT_PACK_GRANTS_NEW_AUTHORITY: NO

EMPTY_DELTA_STILL_REJECTED: YES
OUT_OF_SCOPE_DELTA_STILL_REJECTED: YES
AUTHORIZED_DELTA_EXISTING_PATH_PRESERVED: YES

CLEAN_NOOP_EXITED_ZERO_CLASSIFIED_BLOCKED: YES
CLEAN_NOOP_LEASE_RELEASED: YES
CLEAN_NOOP_AUTH_REUSABLE: NO
CLEAN_NOOP_STATE: EXECUTION_BLOCKED
CLEAN_NOOP_PUBLICATION: NO

DIRTY_OR_DRIFT_FAILURE_AUTO_CLEANED_AS_NOOP: NO
CLEANUP_FAILURE_STATUS: RECOVERY_REQUIRED
AUTO_RETRY: NO
AUTO_REROUTE: NO
PAID_API_CALL: NO
```

## 11. TASK-072 Recovery Boundary

TASK-072 itself does not need a new task-authoring marker. After this refinement is implemented and merged, TASK-072 may receive a fresh Human RUN authorization using its existing canonical task artifact, provided the stale TASK-072 lease/authorization from the pre-refinement clean no-op has first been explicitly cleared under the existing recovery contract.

The failed attempt is not silently retried and does not count as a published TASK-072 implementation.
