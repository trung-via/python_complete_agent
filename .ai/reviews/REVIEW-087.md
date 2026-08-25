# REVIEW-087 — P1.0B Failure Classification + Deterministic Next Action
PUBLISHER_PROFILE: CANONICAL_E4
STATUS: CHANGES_REQUIRED
APPROVED: NO
AUTO_MERGE_ELIGIBLE: NO
MERGE_AUTHORIZED: NO
MERGED_TO_MAIN: NO
TASK_ID: TASK-087
REVIEW_ROUND: 2
REVIEWED_TASK_HEAD_SHA: a600fbab0eb2a1619b99c6e859f520954d9642b7
REVIEWED_BASE_MAIN_SHA: ac0ae79e85e30a80410380188578db1993720b5b
TASK_ARTIFACT_BLOB_SHA: eb0d2455f6b98e6fa44a8db336dd78625e66820a
RESULT_BLOB_SHA: aa48dbfaeeda4c084c2515a538f2862e0c961494
EXECUTOR_ID: antigravity
BLOCKERS_REMAINING: 2
CODE_AUDIT: CHANGES_REQUIRED
CANONICAL_TESTS: NOT_RUN_REVIEW_FIRST
ROADMAP_AUDIT: PASS
ROADMAP_ID: AIOS-BRIDGE-LEAN-EXECUTION
ROADMAP_VERSION: 1.2
ROADMAP_BLOB_SHA: 41bf467f3dd4fc8aea165ac65c37e0e2a5a3ef5c
ROADMAP_FINGERPRINT: 89c9372c074ecb43778705f07c6fded67e4af7833c0feb72a92a9ae2e737c612
MILESTONE: P1
CAPABILITY_ID: P1_UNIFIED_VALIDATION_CAPABILITY_BATCH
REQUIREMENT_BINDINGS_FINGERPRINT: d0c2a52e727d6042b2bf5aa22c0c4c5a94ab2229203ccfc44fb4578055523eba
P1_FORMAL_COMPLETION: NO
P2_P3_AUTHORIZED: NO
H5_H8_AUTHORIZED: NO
FIX_EXECUTION_MODE: IMPLEMENTATION
FIX_REVIEW_MODE: PROOF_REUSE_DELTA_IMPACT
FIX_CONTEXT_PACK_JSON: {"schema_version":"1","previous_reviewed_head_sha":"a600fbab0eb2a1619b99c6e859f520954d9642b7","impact_confidence":"KNOWN","open_finding_ids":["B2","B3"],"affected_paths":["bridge.py","src/aios_bridge/worker_failure.py","src/aios_bridge/worker_flow.py","tests/aios_bridge/test_worker_failure.py","tests/aios_bridge/test_worker_flow.py","tests/test_bridge_executor_automation.py","tests/test_bridge.py"],"protected_accepted_paths":[".agents/skills/aios-worker/scripts/aios_worker.py"],"required_test_paths":["tests/aios_bridge/test_worker_failure.py","tests/aios_bridge/test_worker_flow.py","tests/aios_bridge/test_aios_worker_control_surface.py","tests/test_bridge_executor_automation.py","tests/test_bridge.py"],"unknown_impact_fallback_test_paths":["tests/aios_bridge/test_worker_failure.py","tests/aios_bridge/test_worker_flow.py","tests/aios_bridge/test_aios_worker_control_surface.py","tests/test_bridge_executor_automation.py","tests/test_bridge.py"],"proof_bindings":[]}
EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/tasks/TASK-087.md","blob_sha":"eb0d2455f6b98e6fa44a8db336dd78625e66820a"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","src/aios_bridge/worker_failure.py","src/aios_bridge/worker_flow.py","tests/aios_bridge/test_worker_failure.py","tests/aios_bridge/test_worker_flow.py","tests/test_bridge_executor_automation.py","tests/test_bridge.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]},{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]}],"operation":"FIX","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

## Snapshot

```text
HEAD: a600fbab0eb2a1619b99c6e859f520954d9642b7
PREVIOUS_REVIEWED_HEAD: dfbca7fc9c56f9d71c4591301f32b9a49bec47ba
BASE_MAIN: ac0ae79e85e30a80410380188578db1993720b5b
MERGE_BASE: ac0ae79e85e30a80410380188578db1993720b5b
AHEAD_FROM_PREVIOUS_REVIEW: 1
AHEAD_FROM_MAIN: 2
BEHIND_MAIN: 0
MAIN_DRIFT: NO
CANDIDATE_STAGE_AIOS_MANAGED_T2_EXECUTION_COUNT: 0
CERTIFICATION_DEFERRED: YES
TARGETED_TEST_STATUS: PASS
SLICE_C_IMPACT_CONFIDENCE: KNOWN
```

Round 2 is a Delta + Impact review of the B1-B4 FIX. The new candidate is exactly one commit on the Round-1 reviewed head. Slice-C selected the bounded impact suites and reports PASS. Review-First publication remains correct: no canonical T2 has run for this candidate.

## Finding Closure

### B1 — CLOSED

The pure classifier now fails closed on the important uncertainty cases raised in Round 1:

- timeout classification requires exact `TIMED_OUT` and `is_known_stopped is True`;
- unsupported terminal-status tokens are rejected;
- `EXITED_ZERO` with an implementation delta is rejected rather than mislabeled as timeout;
- productive nonzero classification requires exact `EXITED_NONZERO`, non-zero preserved delta, known stopped status, and explicit allowed-path evidence;
- missing scope evidence cannot create productive-recovery authority.

Negative tests cover unknown terminal status, unknown/stopped-false evidence, missing scope, and invalid zero/non-zero combinations.

### B4 — CLOSED EXCEPT THE PRODUCTIVE-NONZERO INTEGRATION PROOF OWNED BY B2

The FIX adds integration coverage for clean timeout and dirty timeout through the Bridge boundary, structured WorkerFlow output, malformed-evidence fail-closed behavior, and the Review-First impacted test lane. Clean timeout proves no publication; dirty timeout proves preserved worktree plus `RECOVERY_REQUIRED` semantics. The only remaining integration gap is the valid productive-nonzero path described under B2 below.

## Remaining Blockers

### B2 — PRODUCTIVE_NONZERO_RECOVERY_CANDIDATE is classified in the pure model but is not integrated as a blocked recovery boundary

The Round-2 FIX correctly persists structured worker-failure evidence for clean and dirty timeout paths. However the existing Bridge branch for `EXITED_NONZERO` with an authorized dirty delta still follows the old productive-recovery path:

```text
EXITED_NONZERO + dirty delta
  -> strict validate_executor_worktree_delta
  -> is_productive_nonzero_recovery_candidate == TRUE
  -> fall through to targeted test / publication continuation
```

That conflicts with TASK-087's newly locked machine contract:

```text
PRODUCTIVE_NONZERO_RECOVERY_CANDIDATE
  -> next_action = RECOVERY_REQUIRED_PRESERVED_DELTA
```

A classified blocked execution cannot both require preserved-delta recovery and silently continue toward publication in the same transaction.

Required repair:

- preserve the existing strict branch/head/allowed-path/publication-trust/authorization-binding gate as the authority for deciding whether the nonzero delta is a valid productive recovery candidate;
- when that strict gate returns TRUE, construct/validate `WorkerFailureEvidence` for exact `EXITED_NONZERO` using the already verified dirty paths and allowed paths;
- persist that exact structured evidence through the same bounded operational-failure mechanism used for owned timeout classes;
- set the operational state to `RECOVERY_REQUIRED` with next action `RECOVERY_REQUIRED_PRESERVED_DELTA`;
- preserve the lease/worktree/delta for Human recovery; do not reset, clean, stash, commit, retry, reroute, test, publish, or fabricate a consumed boundary;
- invalid/out-of-scope/non-proven nonzero evidence must remain fail-closed and must not create PRODUCTIVE_NONZERO authority.

Required regression proof:

```text
VALID_PRODUCTIVE_NONZERO
  -> structured failure_class PRODUCTIVE_NONZERO_RECOVERY_CANDIDATE
  -> exactly one next_action RECOVERY_REQUIRED_PRESERVED_DELTA
  -> state RECOVERY_REQUIRED
  -> preserved delta
  -> no publication
  -> no automatic retry/reroute
```

Also retain a negative proof that out-of-scope/non-proven nonzero evidence cannot create productive-recovery authority.

### B3 — persisted WorkerFailureEvidence still allows semantic class/status mismatch for CLEAN_NO_WORKTREE_DELTA

Round 2 correctly removed coercive deserialization, requires the exact field set and exact primitive types, validates deterministic human guidance, and WorkerFlow now parses the record through `WorkerFailureEvidence.from_dict()` before exposing it. Those parts are accepted.

One machine-authority hole remains: the persisted evidence contract does not yet enforce the same closed terminal-status semantics as the pure classifier for `CLEAN_NO_WORKTREE_DELTA`.

A tampered record can currently satisfy the structural checks with, for example:

```text
failure_class = CLEAN_NO_WORKTREE_DELTA
next_action = HUMAN_SELECT_REPLACEMENT_EXECUTOR_IF_PROVEN_SAFE
zero_worktree_delta = true
terminal_status = TIMED_OUT
```

or with another uppercase but unsupported terminal token. That can reinterpret timeout evidence into a different recovery next action when WorkerFlow loads the persisted record.

Required repair:

- persisted/direct `WorkerFailureEvidence` must reject any terminal status outside the same closed terminal vocabulary used by the classifier;
- `CLEAN_NO_WORKTREE_DELTA` must require zero delta AND a terminal status compatible with the classifier's clean-noop branch; it must reject `TIMED_OUT` because timeout has its own class;
- retain the existing class/status/delta invariants for CLEAN_TIMEOUT, DIRTY_TIMEOUT_RECOVERY_REQUIRED, and PRODUCTIVE_NONZERO_RECOVERY_CANDIDATE;
- do not duplicate a second divergent status vocabulary: use one shared closed validation source inside `worker_failure.py`;
- WorkerFlow continues to fail closed on malformed/tampered evidence.

Required negative tests:

```text
CLEAN_NO_WORKTREE_DELTA + TIMED_OUT -> REJECT
CLEAN_NO_WORKTREE_DELTA + unsupported terminal token -> REJECT
```

## Protected Accepted Surfaces

Do not reopen unless this narrow FIX touches or regresses them:

- B1 fail-closed classifier predicates are accepted.
- strict no-coercion `WorkerFailureEvidence.from_dict()` field/type validation is accepted.
- deterministic `human_guidance` derivation and WorkerFlow validation are accepted.
- clean timeout structured evidence, no publication and Human-decision next action are accepted.
- dirty timeout structured evidence, preserved worktree and `RECOVERY_REQUIRED` behavior are accepted.
- TASK-092 clean-noop blocked-replacement compatibility remains protected.
- `.agents/skills/aios-worker/scripts/aios_worker.py` output wiring is accepted and protected from modification in this FIX.
- Review-First candidate publication remains T2=0.
- compact RESULT / Slice-C impact evidence remain authoritative.
- no automatic retry or automatic reroute.
- roadmap v1.2, lease, scope, publication trust, reviewed-head and merge safety remain unchanged.
- capability batch, integration lane, Python Agent pilot, P2/P3 and H5-H8 remain out of scope.

## Decision

```text
TASK-087: CHANGES_REQUIRED
OPEN_BLOCKERS: B2 B3
CLOSED_THIS_ROUND: B1; B4 except B2-owned productive-nonzero proof
FINAL_T2_NOW: NO
MERGE_NOW: NO
P1_FORMAL_COMPLETION: NO
```

The next FIX is narrow. It must publish a new Review-First candidate with AIOS-managed T2 count still equal to zero. If B2 and B3 close without regression, the next semantic state may become `SEMANTICALLY_ACCEPTED_PENDING_T2`.