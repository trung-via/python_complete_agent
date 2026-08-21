# TASK-061 Blueprint — Cancelled Executor Reselection Recovery

STATUS: LOCKED_FOR_IMPLEMENTATION
CLASS: L3 — EXECUTOR AUTHORITY / RECOVERY / FAIL-CLOSED CONTROL
OWNER_CONTRACT: ADR-039
PARALLEL_LANE: YES
MERGE_BLOCKED_UNTIL_TASK_060: YES
POST_TASK_060_RECONCILE_AND_FRESH_REVIEW_REQUIRED: YES

## 1. Baseline / Branch

```text
BASELINE_MAIN_SHA: 0d7bddac2066ad508bf68fbb4d3bd8b69b18d1b3
TARGET_BRANCH: ai/task-061
PARALLEL_WORKTREE_RECOMMENDED: YES
```

TASK-061 may be implemented from this baseline while TASK-060 remains unresolved, but it MUST NOT be merged before TASK-060.

After TASK-060 PASS + Human merge, this branch must be reconciled/rebased onto the new `main` without force-push, all tests rerun, and a fresh independent review performed on the exact rebased head.

## 2. Purpose

Implement ADR-039's missing recovery transition:

```text
CANCELLED FIX by executor A
    + Human recovery release already completed
    + no active lease
    + clean worktree/index
    + exact stable predecessor branch restored
    + exact same CHANGES_REQUIRED review
    + Human explicitly selects eligible executor B
        -> fresh FIX authorization for executor B
```

This is **not** M6 stable failover and must never mutate or reinterpret the cancelled source authorization as `CONSUMED`.

## 3. Existing Contract That Must Remain True

ADR-020 remains authoritative:

```text
CONSUMED A -> B = StableExecutorFailoverProof
ACTIVE A   -> B = reject
```

TASK-061 adds only:

```text
CANCELLED A -> B = CancelledExecutorReselectionProof
```

when every ADR-039 recovery gate passes.

## 4. Canonical Pure Contract

Add:

```text
src/aios_bridge/continuity/cancelled_reselection.py
```

Expected public semantics:

```python
@dataclass(frozen=True)
class CancelledExecutorReselectionProof:
    schema_version: str
    task_id: str
    target_branch: str
    cancelled_executor_id: str
    cancelled_operation: ExecutionOperation
    cancelled_execution_fingerprint: str
    cancelled_lease_fingerprint: str
    cancelled_lease_id: str
    stable_predecessor_sha: str
    review_ref: ArtifactRef
    replacement_executor_id: str
    replacement_operation: ExecutionOperation
    replacement_execution_fingerprint: str
    replacement_lease_fingerprint: str

    def to_dict(self) -> dict: ...
    def to_json(self) -> str: ...
    def fingerprint(self) -> str: ...
    @classmethod
    def from_dict(cls, value: dict) -> "CancelledExecutorReselectionProof": ...
    @classmethod
    def from_json(cls, value: str | bytes) -> "CancelledExecutorReselectionProof": ...


def validate_cancelled_executor_reselection(
    proof: CancelledExecutorReselectionProof,
    *,
    cancelled_lease: ExecutorLease,
    replacement_lease: ExecutorLease,
) -> None: ...
```

Exact naming may vary only if semantics remain obviously equivalent.

## 5. Pure Proof Rules

The proof MUST be immutable, deterministic and strict-schema.

Required relations:

```text
task_id exact TASK-<digits>
target_branch exact ai/task-N for same N
cancelled_executor_id != replacement_executor_id
cancelled_operation == FIX
replacement_operation == FIX
cancelled execution/lease fingerprints == exact supplied cancelled lease
replacement execution/lease fingerprints == exact supplied replacement lease
stable_predecessor_sha == lowercase 40-hex
review_ref.path == .ai/reviews/REVIEW-N.md for same task
review_ref is immutable/content-addressed under existing ArtifactRef rules
```

Unknown fields, malformed enums, padded IDs, bool-as-string/integer confusion, cross-task aliases, oversized input and invalid UTF-8 fail closed under existing Continuity conventions.

No filesystem/Git/network/process/model/provider I/O in the pure module.

## 6. Bridge Classification

Current different-executor FIX classification must become three-way without weakening M6:

```text
same executor
    -> ordinary existing FIX

different executor + prior status CONSUMED
    -> existing ADR-020 stable failover path unchanged

different executor + prior status CANCELLED
    -> ADR-039 cancelled-reselection path

ACTIVE/other status + different executor
    -> reject
```

Do not alter `StableExecutorFailoverProof` semantics.

Do not change existing CONSUMED failover tests except additive regression coverage proving they still pass unchanged.

## 7. CANCELLED Source Authorization Validation

The recovery path must require prior authorization exact fields/bindings sufficient to reconstruct the cancelled M5 lease and prove it was the same cancelled FIX activation.

Required:

```text
status == CANCELLED
action == FIX
task_id exact
workspace_id exact current workspace
executor_id valid and != replacement
lease_id exact
lease_fingerprint exact
execution_fingerprint exact
authorized artifact path == .ai/reviews/REVIEW-N.md
authorized artifact blob == current authoritative review blob
cancelled_at present/bounded
cancellation_reason proves existing Human recovery release
prior_published_sha exact lowercase 40-hex
```

The implementation MUST NOT set `status = CONSUMED` on this record.

## 8. Stable Predecessor Gate

Before replacement lease acquisition, require mechanically:

```text
current branch == ai/task-N
worktree clean
index clean
local HEAD == prior_published_sha
remote ai/task-N HEAD == prior_published_sha
lease_store.load_active(TASK-N) is None
```

If remote branch is absent, moved, ambiguous or inaccessible, fail closed.

No reset/rebase/merge/stash/cherry-pick/cleanup is performed by this recovery path.

## 9. Exact Review Gate

Current canonical review must still be `CHANGES_REQUIRED` under existing parsing rules and must match exactly:

```text
path == cancelled auth authorized review path
blob_sha == cancelled auth authorized review blob SHA
```

A changed review blob fails closed for ADR-039 v1.

## 10. Human Replacement Selection / Eligibility

The new executor is provided only by the Human-selected adapter/Bridge handoff path.

It must be eligible exactly once in the canonical review's FIX dispatch policy and satisfy all existing operation/capability checks.

No quota detection, recommendation auto-selection, model choice, fallback, retry or reroute.

## 11. Replacement Activation Transaction

Locked order:

```text
validate review/control
prepare/reconcile branch using existing safe rules
load/classify prior auth
validate CANCELLED recovery evidence
validate stable predecessor
validate clean worktree/index
validate no active lease
validate explicit replacement eligibility
build new replacement lease
atomic acquire replacement lease
build + pure-validate CancelledExecutorReselectionProof
persist new ACTIVE authorization with recovery metadata
expose/execute according to existing executor adapter
```

Post-acquire failure may release only the newly acquired replacement lease.

Never recreate, reacquire, delete or rewrite the cancelled source lease.

## 12. Required ACTIVE Authorization Metadata

A replacement authorization produced by ADR-039 must include bounded non-secret metadata sufficient for publish revalidation, equivalent to:

```text
cancelled_reselection_proof
cancelled_reselection_proof_fingerprint
reselection_from_executor_id
reselection_stable_predecessor_sha
```

It may additionally retain a bounded exact source-lease representation if required for deterministic publish-time proof validation.

No secrets, transcripts, raw filesystem paths, process IDs, quota values or shell history.

## 13. Publish Revalidation

Before any test command, RESULT mutation, commit or push under a recovery authorization:

```text
require exact replacement ACTIVE lease
strictly parse recovery proof
verify proof fingerprint
reconstruct/bind cancelled source lease evidence
validate pure proof relation
revalidate exact current review blob/status
verify branch lineage still anchored correctly
```

Malformed recovery evidence MUST NOT fall back to ordinary FIX or stable failover.

## 14. RESULT Manifest

Successful recovery publication must distinguish the path explicitly:

```text
EXECUTOR_FAILOVER: NO
CANCELLED_RESELECTION: YES
RESELECTION_FROM_EXECUTOR: <source>
RESELECTION_TO_EXECUTOR: <replacement>
RESELECTION_STABLE_PREDECESSOR_SHA: <40hex>
RESELECTION_PROOF_FINGERPRINT: <64hex>
RESELECTION_REVIEW_BLOB_SHA: <40hex>
```

Ordinary FIX remains `CANCELLED_RESELECTION: NO` or omission only if existing RESULT compatibility requires omission. M6 failover remains `EXECUTOR_FAILOVER: YES` and must never be conflated with reselection.

## 15. Exact Writable Scope

Executor may modify only:

```text
bridge.py
src/aios_bridge/continuity/cancelled_reselection.py
tests/aios_bridge/continuity/test_cancelled_reselection.py
tests/test_bridge.py
```

Bridge-generated publication output:

```text
.ai/results/RESULT-061.md
```

No other file is authorized.

Specifically forbidden:

```text
.agents/workflows/**
.agents/skills/**
docs/AIOS_UNIFIED_WORKER_WORKFLOW.md
TASK-059 files
TASK-060 files
src/aios_bridge/minimax_m3_*
src/aios_bridge/paid_api_*
requirements.txt
```

## 16. Required Test Concepts

At minimum:

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
CORRUPT_ACTIVE_LEASE_FAILS_CLOSED
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

## 17. Targeted Test Command

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_bridge/continuity/test_cancelled_reselection.py tests/test_bridge.py -q
```

Bridge publication must run the full repository suite under its existing test gate.

## 18. Executor Policy

TASK-061 is compatible with both subscription executors under ADR-038, but this parallel lane is intended to use Codex while Antigravity is occupied by TASK-060.

Human selection remains explicit.

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
    },
    {
      "executor_id": "antigravity",
      "capacity_class": "SUBSCRIPTION",
      "preference_rank": 1,
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

Preference does not authorize selection. For this parallel run the Human is expected to invoke the Codex `$aios-worker` surface in the separate TASK-061 worktree.

## 19. Parallel Worktree Boundary

Recommended second worktree concept:

```text
primary worktree   -> TASK-060 / Antigravity
secondary worktree -> TASK-061 / Codex
```

Each task has a different task ID and branch. No files or partial deltas are copied between worktrees.

Do not use the TASK-061 worktree to touch TASK-060 or vice versa.

## 20. Merge Hold

Even if TASK-061 receives PASS before TASK-060 is complete:

```text
MERGE TASK-061: FORBIDDEN
```

until:

```text
TASK-060 PASS
TASK-060 Human merge
TASK-061 reconciled/rebased onto new main
focused tests rerun
full repo tests rerun
fresh Review TASK-061 on exact reconciled head
```

No force-push is authorized by this blueprint.

## 21. Out of Scope

```text
CANCELLED RUN RESELECTION: NO
DIRTY HOT HANDOFF: NO
AUTO STASH/RESET/CHERRY-PICK: NO
PROCESS PID TRACKING: NO
PROCESS TERMINATION: NO
QUOTA DETECTION: NO
AUTOMATIC EXECUTOR CHOICE: NO
AUTOMATIC RETRY/REROUTE: NO
M6 SEMANTIC RELAXATION: NO
M11 PAID API: NO
TASK-059 IMPLEMENTATION: NO
TASK-060 IMPLEMENTATION: NO
AUTO MERGE: NO
```

## 22. Completion

After first Bridge publication:

```text
STOP
NEXT: Review TASK-061
```

A first PASS proves the implementation on the pre-TASK-060 baseline only. Final merge eligibility requires the post-TASK-060 reconcile + fresh review gate defined above.
