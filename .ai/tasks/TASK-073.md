# TASK-073 — Codex E4 Implementation Intent & Clean No-Op Recovery Hardening

STATUS: READY
PUBLISHER_PROFILE: CANONICAL_E4
CLASS: L1 — AIOS BRIDGE CONTROL-PLANE REFINEMENT
MILESTONE: PRE-H2 RECOVERY HARDENING
EXECUTOR_MODE: ANTIGRAVITY_ONLY
RECOMMENDED_EXECUTOR: antigravity

## Baseline

```text
MAIN_SHA: 0f803c2d66244147734c5b8f5ea3670c6f57c6cc
TARGET_BRANCH: ai/task-073
ADR: ADR-046
ADR_BLOB_SHA: de5b63eb0c23681ec3feb427f44b91d8f44151c0
TASK_072_STATUS: CLEAN_CODEX_NOOP / NOT_PUBLISHED
TASK_072_RERUN_AUTHORIZED_BY_THIS_TASK: NO
AUTO_RETRY_ALLOWED: NO
AUTO_REROUTE_ALLOWED: NO
PAID_API_CALL_ALLOWED: NO
LEAN_AUTO_MERGE: ENABLED
```

## Machine-Readable E4 Inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/decisions/ADR-044-EXECUTABLE-TASK-AUTHORING-PREFLIGHT-ZERO-TOUCH-START-CONTRACT-LOCK.md","blob_sha":"24b212d96d5fa650241a71049ce114f7a3a85489"},{"path":".ai/decisions/ADR-046-CODEX-E4-IMPLEMENTATION-INTENT-CLEAN-NOOP-RECOVERY-CONTRACT-LOCK.md","blob_sha":"de5b63eb0c23681ec3feb427f44b91d8f44151c0"},{"path":".ai/tasks/TASK-072.md","blob_sha":"4ecbd102388e34c1e328cb152d53aebfde3aa6c2"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","src/aios_bridge/executor_context.py","tests/aios_bridge/test_executor_context_pack.py","tests/test_bridge_executor_automation.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

The publisher profile and the three E4 markers above are the complete executable authoring inputs. They create no Codex rerun, executor failover, paid-provider, merge, or TASK-072 execution authority.

## Objective

Implement ADR-046 narrowly. Align the Codex executor-facing context pack with the already-existing E4 machine invariant that a successful automatic RUN/FIX implementation must create a non-empty authorized worktree delta, and add deterministic automatic cleanup for the exact clean-no-op case so it becomes `EXECUTION_BLOCKED` without leaving a stale active lease/authorization requiring routine Human repair.

Do not add a new task authoring marker. Do not change TASK-071 preflight semantics.

## Root Cause Being Fixed

Current E4 already rejects an empty worktree delta through `validate_executor_worktree_delta()`, but the thin executor context does not explicitly tell Codex that no-op success violates the implementation protocol.

Current exact clean-no-op behavior is also operationally expensive:

```text
Codex exits zero
branch unchanged
head unchanged
dirty_paths = empty
        ↓
post-executor scope gate rejects no delta
        ↓
RECOVERY_REQUIRED
ACTIVE lease/auth may remain
        ↓
Human cleanup required
```

Target behavior:

```text
Codex exits zero
branch/head exact + no dirty paths
        ↓
classify CLEAN_NO_WORKTREE_DELTA
        ↓
release exact active lease
mark authorization non-ACTIVE/non-reusable
state = EXECUTION_BLOCKED
no publish / no retry / no reroute
```

Any drift, dirty-path ambiguity, process failure, or cleanup uncertainty remains fail-closed as `RECOVERY_REQUIRED`.

## Writable Scope

Executor may modify only:

```text
bridge.py
src/aios_bridge/executor_context.py
tests/aios_bridge/test_executor_context_pack.py
tests/test_bridge_executor_automation.py
```

Bridge-generated `.ai/results/RESULT-073.md` is publication output, not executor writable scope.

Explicitly forbidden:

```text
src/aios_bridge/task_authoring.py
src/aios_bridge/executor_automation.py
src/aios_bridge/runtime_lease.py
src/aios_bridge/continuity/**
src/aios_engineering/**
.agents/**
.ai/decisions/**
.ai/reviews/**
.ai/tasks/**
requirements.txt
```

No dependency changes.

## Requirement A — Executor Context Must State Existing Delta Obligation

Update the canonical thin executor instruction block in `src/aios_bridge/executor_context.py` so bounded Codex receives an explicit deterministic instruction equivalent to:

```text
IMPLEMENTATION_EXECUTION: YES
AUTHORIZED_WORKTREE_DELTA_REQUIRED: YES
NO_OP_SUCCESS_IS_PROTOCOL_FAILURE: YES
```

The wording may be natural prose but semantics must be unambiguous:

- RUN/FIX is implementation execution, not advisory review;
- Codex must make substantive edits only inside authorized allowed paths when implementation is possible;
- a successful turn that makes no worktree change is not completion;
- if blocked, Codex must report the blocker rather than claim implementation success;
- commit/push/publish/merge remain forbidden to the worker.

This instruction grants no new authority. Existing TASK/REVIEW + lease/auth + allowed paths remain the only execution boundaries.

Do not include raw secrets, environment values, or new provider instructions.

## Requirement B — Exact Clean No-Op Predicate

In `bridge.py`, introduce a small deterministic helper or equivalent closed logic for exact clean no-op classification.

It may classify a no-op only if all are true:

```text
receipt.status == EXITED_ZERO
publication trust verification already passed
post_branch == pre_branch == authorized task branch
post_head_sha == pre_head_sha
dirty_paths == ()
```

The helper must not infer from Codex prose or diagnostic event text.

It must NOT classify as clean no-op when:

```text
transport failed/timed out/interrupted
branch changed
head changed
any dirty path exists
publication trust drifted
post-state observation failed
```

Those cases preserve existing fail-closed behavior.

## Requirement C — Deterministic Clean No-Op Cleanup

For the exact clean-no-op case only:

1. Use the exact lease already reconstructed and verified during E4 pre-invocation.
2. Release that exact active lease through the existing lease store.
3. Persist authorization in a non-ACTIVE, non-reusable blocked terminal form. Preferred status: `EXECUTION_BLOCKED` unless an existing closed authorization status vocabulary requires an equivalent explicit blocked value.
4. Preserve original task/artifact/executor/lease fingerprints as audit metadata; do not fabricate a published SHA.
5. Persist operational task state as `EXECUTION_BLOCKED` with a bounded reason identifying `CLEAN_NO_WORKTREE_DELTA` and the closed transport diagnostic code.
6. Exit non-zero / fail the command after cleanup.
7. Do not publish RESULT, commit, push, merge, retry, reroute, or acquire another lease.

The cleanup sequence must be fail-closed. If release or persistence cannot be proven, update state to `RECOVERY_REQUIRED` where possible and do not report successful cleanup.

No destructive Git reset/checkout is needed because the exact predicate requires zero worktree delta and unchanged head/branch.

## Requirement D — Preserve Existing E4 Success and Failure Semantics

Do not weaken:

```text
validate_executor_worktree_delta
out-of-scope dirty-path rejection
branch/head mutation rejection
publication trust snapshot verification
transport failure handling
full-suite publication path
single-invocation rule
no-auto-retry rule
no-auto-reroute rule
```

Authorized non-empty delta continues through the existing E4 full-suite + canonical publisher path unchanged.

A dirty/out-of-scope or drifted execution must never be auto-cleaned using the clean-no-op path.

## Requirement E — Tests

Update/add focused tests proving:

```text
CONTEXT_PACK_EXPLICIT_DELTA_OBLIGATION: PASS
CONTEXT_PACK_STILL_DENIES_COMMIT_PUSH_PUBLISH_MERGE: PASS
CONTEXT_PACK_NEW_AUTHORITY_CREATED: NO

CLEAN_NOOP_EXITED_ZERO: EXECUTION_BLOCKED
CLEAN_NOOP_PUBLISH_CALLED: NO
CLEAN_NOOP_LEASE_RELEASE_CALLED_EXACTLY_ONCE: YES
CLEAN_NOOP_AUTH_STATUS_ACTIVE_AFTERWARD: NO
CLEAN_NOOP_STATE_REASON_CONTAINS_CLEAN_NO_WORKTREE_DELTA: YES
CLEAN_NOOP_SECOND_EXECUTOR_INVOKED: NO

NOOP_WITH_BRANCH_DRIFT_AUTO_CLEANED: NO
NOOP_WITH_HEAD_DRIFT_AUTO_CLEANED: NO
DIRTY_OUT_OF_SCOPE_AUTO_CLEANED: NO
TRANSPORT_FAILURE_AUTO_CLEANED: NO
CLEANUP_RELEASE_FAILURE: RECOVERY_REQUIRED
CLEANUP_AUTH_PERSISTENCE_FAILURE: RECOVERY_REQUIRED

AUTHORIZED_DELTA_HAPPY_PATH_PRESERVED: YES
FULL_SUITE_PUBLICATION_PATH_PRESERVED: YES
AUTO_RETRY: NO
AUTO_REROUTE: NO
```

Tests must use fake/local deterministic executor outcomes only. Do not invoke real Codex, Antigravity, network, provider, or paid API.

## Validation Commands

Run exactly:

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_bridge/test_executor_context_pack.py tests/test_bridge_executor_automation.py -q
.\venv\Scripts\python.exe -m pytest tests/ -q
git diff --check
```

Use the existing canonical Bridge E4 publisher only. Do not expand RESULT schema.

## Acceptance Boundary

TASK-073 passes only if:

- executor-facing instructions explicitly communicate the already-existing non-empty-delta postcondition;
- exact clean no-op is separated from ambiguous recovery;
- the exact stale lease/auth is automatically and provably deactivated only for that clean no-op;
- all other E4 safety gates remain fail-closed;
- no retry/reroute/paid/provider/merge authority is introduced.

After TASK-073 is reviewed and merged, TASK-072 remains a separate H2 task and requires a fresh explicit Human RUN. This task does not itself rerun TASK-072.
