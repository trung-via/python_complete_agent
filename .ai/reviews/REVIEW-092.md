# REVIEW-092 — Lean Review Slice D: Compact Evidence, Supersession, Guardrail Learning & Blocked Recovery
PUBLISHER_PROFILE: CANONICAL_E4
STATUS: CHANGES_REQUIRED
APPROVED: NO
AUTO_MERGE_ELIGIBLE: NO
MERGE_AUTHORIZED: NO
MERGED_TO_MAIN: NO
TASK_ID: TASK-092
REVIEW_ROUND: 1
REVIEWED_TASK_HEAD_SHA: 65abd6f6f39c6103a29d925f618927f22de42aa0
REVIEWED_BASE_MAIN_SHA: 5570e64bec7522caf6b4ebda3b2f34ec45a11ebf
TASK_ARTIFACT_BLOB_SHA: 8031684cf59cc6259b8d870b0ceacd47a7d767c3
RESULT_BLOB_SHA: d93eeadd41b39e98af1b55f3cab414ee4d8c33b2
EXECUTOR_ID: codex
BLOCKERS_REMAINING: 3
CODE_AUDIT: CHANGES_REQUIRED
CANONICAL_TESTS: DEFERRED_PENDING_SEMANTIC_ACCEPTANCE
ROADMAP_AUDIT: PASS
ROADMAP_ID: AIOS-BRIDGE-LEAN-EXECUTION
ROADMAP_VERSION: 1.2
ROADMAP_BLOB_SHA: 41bf467f3dd4fc8aea165ac65c37e0e2a5a3ef5c
ROADMAP_FINGERPRINT: 89c9372c074ecb43778705f07c6fded67e4af7833c0feb72a92a9ae2e737c612
MILESTONE: P1
CAPABILITY_ID: P1_UNIFIED_VALIDATION_CAPABILITY_BATCH
REQUIREMENT_BINDINGS_FINGERPRINT: 82ada616254ac56f89c78c05c9c01f4707b923aa4db8804ed5a18067a3e05ec3
FIX_EXECUTION_MODE: IMPLEMENTATION
TASK_087_PREREQUISITE_ELIGIBLE: NO
P1_FORMAL_COMPLETION: NO
P2_P3_AUTHORIZED: NO
H5_H8_AUTHORIZED: NO
EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/tasks/TASK-092.md","blob_sha":"8031684cf59cc6259b8d870b0ceacd47a7d767c3"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","src/aios_bridge/result_evidence.py","tests/aios_bridge/test_result_evidence.py","tests/aios_bridge/test_lean_review_integration.py","tests/test_bridge_executor_automation.py","tests/test_bridge.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]},{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]}],"operation":"FIX","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

FIX_REVIEW_MODE: PROOF_REUSE_DELTA_IMPACT
FIX_CONTEXT_PACK_JSON: {"schema_version":"1","previous_reviewed_head_sha":"65abd6f6f39c6103a29d925f618927f22de42aa0","impact_confidence":"KNOWN","open_finding_ids":["B1","B2","B3"],"affected_paths":["bridge.py","src/aios_bridge/result_evidence.py","tests/aios_bridge/test_result_evidence.py","tests/aios_bridge/test_lean_review_integration.py","tests/test_bridge_executor_automation.py","tests/test_bridge.py"],"protected_accepted_paths":["src/aios_bridge/blocked_recovery.py","src/aios_bridge/review_learning.py","src/aios_bridge/review_pipeline.py","tests/aios_bridge/test_blocked_recovery.py","tests/aios_bridge/test_review_learning.py","tests/aios_bridge/test_review_pipeline.py"],"required_test_paths":["tests/aios_bridge/test_result_evidence.py","tests/aios_bridge/test_lean_review_integration.py","tests/test_bridge_executor_automation.py","tests/test_bridge.py"],"unknown_impact_fallback_test_paths":["tests/aios_bridge/test_result_evidence.py","tests/aios_bridge/test_lean_review_integration.py","tests/aios_bridge/test_certification_job.py","tests/test_bridge_executor_automation.py","tests/test_bridge.py"],"proof_bindings":[]}

## Authoring Correction After Clean No-Op

The previous wording of B1 was too broad: it could be read as authorizing removal or replacement of TASK-092's required `candidate_head_sha` field. That conflicts with the canonical TASK artifact. This revision is an authoring correction only; the reviewed candidate head, blocker set, scope, roadmap binding, and review round remain unchanged.

Normative precedence for this FIX:

```text
TASK-092 authority is unchanged.
REVIEW-092 may narrow/clarify implementation but MUST NOT remove a TASK-required evidence field.
The executor MUST preserve candidate_head_sha in the compact RESULT schema.
```

## Snapshot

```text
HEAD: 65abd6f6f39c6103a29d925f618927f22de42aa0
BASE_MAIN: 5570e64bec7522caf6b4ebda3b2f34ec45a11ebf
MERGE_BASE: 5570e64bec7522caf6b4ebda3b2f34ec45a11ebf
AHEAD: 1
BEHIND: 0
CANDIDATE_STAGE_AIOS_MANAGED_T2_EXECUTION_COUNT: 0
CERTIFICATION_DEFERRED: YES
```

## Blocking Findings

### B1 — Compact RESULT candidate-head semantics are ambiguous and parser strictness is incomplete

`cmd_publish()` creates RESULT evidence before the publication commit exists. Therefore a normal Git commit cannot embed its own final commit SHA. TASK-092 nevertheless requires the machine schema to retain the `candidate_head_sha` field.

Required repair — preserve TASK authority exactly:

```text
KEEP candidate_head_sha as a required exact lowercase 40-hex field.
For review-first embedded RESULT schema v2, define candidate_head_sha as the exact PRE_PUBLICATION_CONTENT_HEAD known before RESULT generation.
ADD a closed role/binding discriminator, for example:
  candidate_head_role = PRE_PUBLICATION_CONTENT_HEAD
  published_head_binding = EXTERNAL_GIT_COMMIT
The embedded RESULT MUST NOT claim candidate_head_sha is the final published/reviewed branch head.
Exact final reviewed-head authority remains externally bound by Git/ref + REVIEWED_TASK_HEAD_SHA + certification/merge checks.
Any parser/caller needing final-head validation must accept/use the externally observed published head rather than equating it to the embedded pre-publication content head.
```

Equivalent bounded names are acceptable, but `candidate_head_sha` MUST remain present. Do not rename/remove it. Do not predict/iterate a self-referential Git SHA. Do not weaken exact-head review, certification, or merge authority.

Also harden `parse_result_evidence()`:

```text
RESULT_EVIDENCE_JSON inside fenced examples is not authority.
Exactly one unfenced top-level RESULT_EVIDENCE_JSON marker is required.
Duplicate JSON object keys fail closed.
Unknown schema fields fail closed according to the selected version.
```

Required regressions:

```text
COMPACT_RESULT_PRESERVES_TASK_REQUIRED_CANDIDATE_HEAD_SHA
COMPACT_RESULT_EXPLICITLY_CLASSIFIES_CANDIDATE_HEAD_AS_PREPUBLICATION_CONTENT_HEAD
EXTERNAL_PUBLISHED_HEAD_REMAINS_EXACT_REVIEW_AUTHORITY
FENCED_RESULT_EVIDENCE_MARKER_IS_NOT_AUTHORITY
DUPLICATE_JSON_KEY_FAILS_CLOSED
REVIEW_FIRST_RESULT_HAS_ONE_MACHINE_AUTHORITY
```

### B2 — Stale terminal certification must become non-current provenance, not a permanent dead-end

Current `cmd_certify_reviewed()` archives a stale terminal PASS/FAILED for a different candidate but leaves it in the current `job.json` slot and fails. Repeating the command reloads the same stale terminal job forever.

Required repair:

```text
exact current PASS -> idempotent return; T2 rerun = 0
exact current FAILED -> fail; no automatic retry
stale PENDING -> SUPERSEDED + archive/non-current -> new candidate may create PENDING
stale PASS/FAILED -> archive immutable terminal evidence -> remove/replace only the CURRENT pointer -> new candidate may create its own PENDING
stale RUNNING -> no invented cancellation; fail closed / recovery until safe handling
```

Do not mutate terminal PASS/FAILED into an invalid lifecycle transition. Preserve immutable history. Old PASS creates zero authority for a new head; old FAILED does not permanently prohibit a different candidate from certification.

Required regressions:

```text
OLD_CERT_PASS_CANNOT_AUTHORIZE_NEW_HEAD
STALE_TERMINAL_PASS_ARCHIVED_THEN_NEW_CANDIDATE_CAN_CERTIFY
STALE_TERMINAL_FAILED_ARCHIVED_THEN_NEW_CANDIDATE_CAN_CERTIFY
EXACT_FAILED_CANDIDATE_STILL_CANNOT_AUTO_RETRY
EXACT_PASS_REMAINS_IDEMPOTENT_WITH_ZERO_SECOND_T2
STALE_RUNNING_REMAINS_FAIL_CLOSED_WITHOUT_FAKE_CANCELLATION
```

### B3 — Provider-neutral handoff pre-start failures must roll back the newly acquired lease

`_rollback_proven_pre_start_failure()` currently protects Codex `cmd_execute()` pre-invocation validation. `cmd_handoff()` can still acquire a lease, persist ACTIVE authorization/state, then fail during final context construction/rendering while no executor has started.

Required repair:

```text
validate everything possible before lease acquisition
then acquire/persist lease
then perform unavoidable post-acquire pre-start work
if that work fails AND executor is provably not started:
    release exact newly acquired lease
    restore exact prior authorization/state
    read-back verify restoration
    no stale lease
if start state is uncertain:
    RECOVERY_REQUIRED; no unsafe auto-release
```

At minimum cover the final `cmd_context(args)` handoff boundary for both Codex and Antigravity. Prefer one shared provider-neutral transaction wrapper. This mechanism creates no retry/reroute authority.

Required regressions must exercise real `cmd_handoff()` behavior:

```text
HANDOFF_CONTEXT_FAILURE_BEFORE_START_RELEASES_NEW_LEASE
HANDOFF_CONTEXT_FAILURE_RESTORES_PRIOR_AUTH_AND_STATE
ANTIGRAVITY_PRE_START_FAILURE_HAS_NO_STALE_LEASE
CODEX_PRE_START_FAILURE_HAS_NO_STALE_LEASE
UNCERTAIN_EXECUTOR_START_STATE_STILL_REQUIRES_RECOVERY
NO_AUTO_RETRY_OR_REROUTE
```

## Accepted / Protected Unless Impact Evidence Reopens

```text
A1 Review-first publication remains T2=0 before semantic acceptance.
A2 FindingRegistry reuses the closed FindingRecord lifecycle and binds exact review round/head.
A3 Risk evidence remains deterministic; CRITICAL_SECOND_REVIEW evidence does not auto-invoke a model.
A4 Guardrail promotion remains recommendation-only with zero repository mutation/authority expansion.
A5 Structured CLEAN_NO_WORKTREE_DELTA evidence remains bounded and contains no raw final-agent reasoning.
A6 Blocked-executor replacement remains explicit-Human-only, different-executor-only, zero-delta, exact-head, clean-worktree and no-active-lease.
A7 Existing allowed-path, roadmap v1.2, lease, publication-trust and exact-head merge gates remain fail-closed.
A8 TASK-087, P2/P3 and H5-H8 remain unopened.
```

## FIX Execution Guidance

This REVIEW is complete normative FIX guidance for B1-B3. The executor does not need to infer any alternate authority from historical reviews. TASK-092 remains the sole task/scope authority.

The failed Codex attempt produced zero worktree delta and no new candidate. Therefore REVIEW_ROUND and REVIEWED_TASK_HEAD_SHA remain unchanged.

Because the prior Codex attempt is now an `EXECUTION_BLOCKED` clean no-op, do NOT silently retry/reroute. Any replacement executor must be selected explicitly by Human and must pass TASK-092's BLOCKED_EXECUTOR_REPLACEMENT preflight.

## Validation

Run only bounded impacted T1 selected by Slice-C. Do not run full canonical T2 during FIX publication. `certify-reviewed 92` remains forbidden until B1-B3 close and semantic acceptance is issued.

## Decision

```text
TASK-092: CHANGES_REQUIRED
OPEN: B1 B2 B3
FINAL_T2_NOW: NO
CERTIFICATION_NOW: NO
MERGE: NO
NEXT: explicit Human replacement executor after clean-no-op blocker, then FIX TASK-092
TASK_087: DO_NOT_RUN
P1_FORMAL_COMPLETION: NO
```
