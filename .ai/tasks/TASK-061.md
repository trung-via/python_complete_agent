# TASK-061 — Cancelled Executor Reselection Recovery

STATUS: READY
CLASS: L3 — EXECUTOR AUTHORITY / RECOVERY / FAIL-CLOSED CONTROL
MILESTONE: SUPPORTING EXECUTOR-CONTROL HARDENING
EXECUTOR_MODE: CODEX_PARALLEL_LANE
PARALLEL_LANE: YES
MERGE_BLOCKED_UNTIL_TASK_060: YES
POST_TASK_060_RECONCILE_AND_FRESH_REVIEW_REQUIRED: YES

## Baseline

```text
MAIN_SHA: 0d7bddac2066ad508bf68fbb4d3bd8b69b18d1b3
TARGET_BRANCH: ai/task-061
```

## Purpose

Implement ADR-039: allow a Human to select a different eligible Executor for a fresh FIX activation after a prior FIX attempt was explicitly cancelled by the existing Human recovery release path, but only after the repository has returned to a clean, lease-free, exact stable predecessor boundary.

This task MUST NOT weaken ADR-020 stable-boundary failover and MUST NOT reinterpret `CANCELLED` as `CONSUMED`.

## Authoritative References

```text
ADR-019:
.ai/decisions/ADR-019-AIOS-CONTINUITY-M5-EXECUTOR-LEASE-AND-SINGLE-ACTIVE-EXECUTOR-LOCK.md
BLOB_SHA: fb2be56d87bb8b7c556270bd9e6e1ff21e74a570

ADR-020:
.ai/decisions/ADR-020-AIOS-CONTINUITY-M6-STABLE-BOUNDARY-EXECUTOR-FAILOVER-CONTRACT-LOCK.md
BLOB_SHA: fbaf062a4d2938ea16b0f70b2dba76401e9396ff

ADR-038:
.ai/decisions/ADR-038-DEFAULT-DUAL-EXECUTOR-TASK-AUTHORING-POLICY-LOCK.md
BLOB_SHA: 72d38bf2f2ff5a07e7b63322116ad87622349df1

ADR-039:
.ai/decisions/ADR-039-CANCELLED-EXECUTOR-RESELECTION-RECOVERY-CONTRACT-LOCK.md
BLOB_SHA: d317711732cf141f3714d95c74e40b1e979e1b99

BLUEPRINT:
.ai/context/TASK-061-CANCELLED-EXECUTOR-RESELECTION-RECOVERY-BLUEPRINT.md
BLOB_SHA: e2cb781a8b689d793af345ff6a74c6221edc28c7
```

Machine-readable context refs:

```json
[
  {"path":".ai/decisions/ADR-019-AIOS-CONTINUITY-M5-EXECUTOR-LEASE-AND-SINGLE-ACTIVE-EXECUTOR-LOCK.md","blob_sha":"fb2be56d87bb8b7c556270bd9e6e1ff21e74a570"},
  {"path":".ai/decisions/ADR-020-AIOS-CONTINUITY-M6-STABLE-BOUNDARY-EXECUTOR-FAILOVER-CONTRACT-LOCK.md","blob_sha":"fbaf062a4d2938ea16b0f70b2dba76401e9396ff"},
  {"path":".ai/decisions/ADR-038-DEFAULT-DUAL-EXECUTOR-TASK-AUTHORING-POLICY-LOCK.md","blob_sha":"72d38bf2f2ff5a07e7b63322116ad87622349df1"},
  {"path":".ai/decisions/ADR-039-CANCELLED-EXECUTOR-RESELECTION-RECOVERY-CONTRACT-LOCK.md","blob_sha":"d317711732cf141f3714d95c74e40b1e979e1b99"},
  {"path":".ai/context/TASK-061-CANCELLED-EXECUTOR-RESELECTION-RECOVERY-BLUEPRINT.md","blob_sha":"e2cb781a8b689d793af345ff6a74c6221edc28c7"}
]
```

## Locked Transition Semantics

```text
same executor + existing valid FIX rules
    -> ordinary FIX

different executor + prior auth CONSUMED
    -> existing ADR-020 M6 stable failover, unchanged

different executor + prior auth CANCELLED
    -> ADR-039 cancelled-reselection recovery path

different executor + prior auth ACTIVE/other
    -> fail closed
```

The ADR-039 path is valid only for source operation FIX and replacement operation FIX.

Cancelled RUN reselection is forbidden in TASK-061.

## Required Recovery Gates

Before a replacement lease may be acquired, mechanically require all of:

```text
prior auth status == CANCELLED
prior auth action == FIX
cancellation came from existing Human lease-release --confirm-stopped evidence
prior auth retains exact M5 source lease binding
prior_published_sha is exact lowercase 40-hex
current canonical review == CHANGES_REQUIRED
current review path/blob == cancelled FIX authorization path/blob
current branch == ai/task-N
worktree clean
index clean
local HEAD == prior_published_sha
remote ai/task-N HEAD == prior_published_sha
no ACTIVE lease for TASK-N
replacement executor != cancelled executor
replacement executor explicitly Human-selected
replacement executor eligible for FIX in exact current review policy
```

Any unknown/corrupt/stale/missing evidence fails closed.

## Required Canonical Proof

Implement a strict immutable vendor-neutral `CancelledExecutorReselectionProof` in:

```text
src/aios_bridge/continuity/cancelled_reselection.py
```

and a pure relational validator binding it to the cancelled source lease identity and the newly acquired replacement lease identity.

The proof MUST NOT contain secrets, raw local paths, process IDs, quota values, prompts/transcripts, hidden reasoning, merge authority or transport credentials.

## Bridge Integration

Bridge FIX classification must preserve M6 and add the ADR-039 branch only for different-executor + prior `CANCELLED`.

The source cancelled authorization remains `CANCELLED` forever as historical evidence. Never mutate it to `CONSUMED`.

Replacement activation must acquire a completely new lease and persist a new ACTIVE authorization containing bounded recovery proof metadata.

Publish must revalidate the exact recovery proof before tests/RESULT mutation/commit/push and must not allow malformed recovery metadata to fall back to ordinary FIX or M6 failover.

## RESULT Evidence

A successful ADR-039 publication must carry bounded evidence equivalent to:

```text
EXECUTOR_FAILOVER: NO
CANCELLED_RESELECTION: YES
RESELECTION_FROM_EXECUTOR: <source>
RESELECTION_TO_EXECUTOR: <replacement>
RESELECTION_STABLE_PREDECESSOR_SHA: <40hex>
RESELECTION_PROOF_FINGERPRINT: <64hex>
RESELECTION_REVIEW_BLOB_SHA: <40hex>
```

It must never claim `EXECUTOR_FAILOVER: YES` for this path.

## Exact Writable Scope

EXECUTOR_ALLOWED_PATHS_JSON:

```json
[
  "bridge.py",
  "src/aios_bridge/continuity/cancelled_reselection.py",
  "tests/aios_bridge/continuity/test_cancelled_reselection.py",
  "tests/test_bridge.py"
]
```

Bridge-generated publication output only:

```text
.ai/results/RESULT-061.md
```

No other path is authorized.

## Explicit Forbidden Scope

```text
TASK-060 operator UI files: NO
.agents/workflows/**: NO
.agents/skills/**: NO
docs/AIOS_UNIFIED_WORKER_WORKFLOW.md: NO
TASK-059 implementation/artifacts: NO
MiniMax / paid API / M11.3B/C: NO
requirements.txt: NO
process PID tracking: NO
process termination: NO
quota detection: NO
dirty hot handoff: NO
auto stash/reset/cherry-pick: NO
automatic retry/reroute: NO
auto merge: NO
```

## Required Tests

At minimum implement and pass the blueprint test matrix, including:

```text
CANONICAL_RESELECTION_PROOF_ROUNDTRIP
CANONICAL_RESELECTION_PROOF_FINGERPRINT_DETERMINISTIC
CANCELLED_AND_REPLACEMENT_EXECUTORS_MUST_DIFFER
CANCELLED_OPERATION_MUST_BE_FIX
REPLACEMENT_OPERATION_MUST_BE_FIX
CROSS_TASK_REVIEW_REF_REJECTED
RANDOM_SOURCE_LEASE_FINGERPRINT_REJECTED
RANDOM_REPLACEMENT_LEASE_FINGERPRINT_REJECTED
UNKNOWN_FIELDS_REJECTED

CONSUMED_DIFFERENT_EXECUTOR_STILL_USES_M6_FAILOVER
CANCELLED_DIFFERENT_EXECUTOR_USES_RESELECTION
ACTIVE_DIFFERENT_EXECUTOR_REJECTED
CANCELLED_RUN_RESELECTION_REJECTED
CANCELLED_SAME_EXECUTOR_PRESERVES_EXISTING_SAME_EXECUTOR_RULE

CANCELLED_REQUIRES_HUMAN_RECOVERY_CANCELLATION_EVIDENCE
CANCELLED_REQUIRES_PRIOR_PUBLISHED_SHA
CANCELLED_NEVER_MUTATED_TO_CONSUMED
NO_ACTIVE_LEASE_REQUIRED
WORKTREE_MUST_BE_CLEAN
INDEX_MUST_BE_CLEAN
LOCAL_HEAD_MUST_EQUAL_STABLE_PREDECESSOR
REMOTE_HEAD_MUST_EQUAL_STABLE_PREDECESSOR
CURRENT_REVIEW_MUST_BE_CHANGES_REQUIRED
CURRENT_REVIEW_PATH_MUST_MATCH_CANCELLED_AUTH
CURRENT_REVIEW_BLOB_MUST_MATCH_CANCELLED_AUTH
REPLACEMENT_EXECUTOR_MUST_BE_REVIEW_ELIGIBLE
NEW_REPLACEMENT_LEASE_ID_REQUIRED
SOURCE_LEASE_NEVER_REACQUIRED

PUBLISH_REVALIDATES_RESELECTION_BEFORE_TESTS
TAMPERED_RESELECTION_PROOF_REJECTED_BEFORE_TESTS
MISSING_RESELECTION_PROOF_DOES_NOT_FALL_BACK
RESULT_MARKS_CANCELLED_RESELECTION_NOT_FAILOVER
NO_AUTO_RETRY
NO_AUTO_REROUTE
NO_PROCESS_PROBING
NO_DIRTY_WORK_TRANSFER
FULL_REPO_TESTS_PASS
```

Targeted command:

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_bridge/continuity/test_cancelled_reselection.py tests/test_bridge.py -q
```

Bridge publication owns the full repository test gate.

## Executor Selection

This specific RUN is intentionally assigned to Codex as a parallel lane while the primary worktree is reserved for TASK-060 / Antigravity.

SINGLE_EXECUTOR_REASON:

```text
Separate parallel implementation lane chosen explicitly by the Human to avoid contaminating the suspended TASK-060 Antigravity workspace.
```

DISPATCH_EXECUTOR_POLICY_JSON:

```json
{
  "allow_paid_api": false,
  "operation": "RUN",
  "required_capabilities": [
    "FILESYSTEM_WRITE",
    "LOCAL_GIT",
    "REPOSITORY_READ",
    "SHELL",
    "TEST_EXECUTION"
  ],
  "candidates": [
    {
      "executor_id": "codex",
      "capacity_class": "SUBSCRIPTION",
      "preference_rank": 0,
      "supported_operations": ["RUN"],
      "supported_capabilities": [
        "FILESYSTEM_WRITE",
        "LOCAL_GIT",
        "REPOSITORY_READ",
        "SHELL",
        "TEST_EXECUTION"
      ]
    }
  ]
}
```

No fallback or reroute to Antigravity is authorized for this RUN.

## Child Executor Role Lock

```text
visible Codex + $aios-worker skill = operator UI
Bridge E4 spawned Codex process      = bounded implementation Executor
```

The child Executor must implement TASK-061 directly. It must not invoke `$aios-worker`, `/aios-worker`, raw nested Codex orchestration, Bridge approve/publish manually, or create another Executor.

## Parallel Worktree / Merge Hold

TASK-061 is designed for a second Git worktree so TASK-060 can remain untouched in the primary worktree.

Even if TASK-061 first review is PASS:

```text
MERGE TASK-061: FORBIDDEN
```

until all of the following occur:

```text
1. TASK-060 receives PASS.
2. Human merges TASK-060 first.
3. TASK-061 is reconciled/rebased onto the new main without force-push.
4. Targeted tests rerun.
5. Full repository tests rerun.
6. ChatGPT performs a fresh Review TASK-061 on the exact reconciled head.
7. Only a fresh post-reconcile PASS may become READY_FOR_HUMAN_MERGE.
```

A PASS from the current pre-TASK-060 baseline is implementation evidence only.

## TASK-059 Boundary

TASK-059 remains blocked until TASK-060 PASS + merge.

Do not run or modify TASK-059 as part of TASK-061.

After TASK-060 and TASK-061 are merged, TASK-059 must be reconciled/reissued against the then-current `main` before execution because its original baseline predates these supporting hardening changes.

## Completion

After first Bridge publication:

```text
STOP
NEXT: Review TASK-061
MERGE: BLOCKED UNTIL POST-TASK-060 RECONCILE + FRESH PASS
```
