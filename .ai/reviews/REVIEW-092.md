# REVIEW-092 — Lean Review Slice D: Compact Evidence, Supersession, Guardrail Learning & Blocked Recovery
PUBLISHER_PROFILE: CANONICAL_E4
STATUS: CHANGES_REQUIRED
APPROVED: NO
AUTO_MERGE_ELIGIBLE: NO
MERGE_AUTHORIZED: NO
MERGED_TO_MAIN: NO
TASK_ID: TASK-092
REVIEW_ROUND: 4
REVIEWED_TASK_HEAD_SHA: b6c060fed441437b859c56ff37578b5c1dcfa990
REVIEWED_BASE_MAIN_SHA: 5570e64bec7522caf6b4ebda3b2f34ec45a11ebf
TASK_ARTIFACT_BLOB_SHA: 8031684cf59cc6259b8d870b0ceacd47a7d767c3
RESULT_BLOB_SHA: dee382e96ffef001fc573996a2d79393b6d84752
EXECUTOR_ID: antigravity
BLOCKERS_REMAINING: 1
CODE_AUDIT: CHANGES_REQUIRED
CANONICAL_TESTS: FAILED_CERTIFICATION
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
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","tests/test_bridge.py","tests/aios_bridge/test_lean_review_integration.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]},{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]}],"operation":"FIX","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

FIX_REVIEW_MODE: PROOF_REUSE_DELTA_IMPACT
FIX_CONTEXT_PACK_JSON: {"schema_version":"1","previous_reviewed_head_sha":"b6c060fed441437b859c56ff37578b5c1dcfa990","impact_confidence":"KNOWN","open_finding_ids":["B4"],"affected_paths":["bridge.py","tests/test_bridge.py","tests/aios_bridge/test_lean_review_integration.py"],"protected_accepted_paths":["src/aios_bridge/result_evidence.py","src/aios_bridge/certification_job.py","src/aios_bridge/blocked_recovery.py","src/aios_bridge/review_learning.py","src/aios_bridge/review_pipeline.py","tests/aios_bridge/test_result_evidence.py","tests/aios_bridge/test_blocked_recovery.py","tests/aios_bridge/test_review_learning.py","tests/aios_bridge/test_review_pipeline.py"],"required_test_paths":["tests/aios_bridge/test_roadmap_governance.py","tests/test_bridge_task_authoring.py","tests/aios_bridge/test_lean_review_integration.py","tests/test_bridge.py"],"unknown_impact_fallback_test_paths":["tests/aios_bridge/test_roadmap_governance.py","tests/test_bridge_task_authoring.py","tests/aios_bridge/test_lean_review_integration.py","tests/test_bridge_executor_automation.py","tests/test_bridge.py"],"proof_bindings":[]}

## Certification Failure Snapshot

```text
CANDIDATE_HEAD: b6c060fed441437b859c56ff37578b5c1dcfa990
BASE_MAIN: 5570e64bec7522caf6b4ebda3b2f34ec45a11ebf
SEMANTIC_ACCEPTANCE_ROUND: 3
CERTIFICATION_STATUS: CERTIFICATION_FAILED
AIOS_MANAGED_T2_EXECUTION_COUNT: 1
FULL_CANONICAL_RESULT: 7 failed, 2713 passed, 7 skipped
MERGE_AUTHORITY_CREATED: NO
AUTO_RETRY: NO
AUTO_REROUTE: NO
```

The failed certification is terminal for this exact candidate. Do not rerun `certify-reviewed 92` on `b6c060fe...`. A new implementation candidate is required before a new certification job can exist.

## Finding

### B4 — Handoff prior-state snapshot is ordered before canonical governance/task-authoring preflight

Round-2 B3 correctly added rollback coverage for normal exceptions and `SystemExit`, but it introduced this function-entry dependency:

```text
paths = get_runtime_paths()
pre_start_prior_state = load_json(paths["state"], None)
```

before RUN/FIX artifact, roadmap, and task-authoring preflight has completed.

The canonical T2 failures are concentrated in preflight-ordering tests, including:

```text
tests/aios_bridge/test_roadmap_governance.py::test_bridge_run_and_e4_paths_reject_missing_authoritative_progression
tests/aios_bridge/test_roadmap_governance.py::test_bridge_governed_fix_uses_exact_original_task_evidence[exact]
tests/aios_bridge/test_roadmap_governance.py::test_bridge_governed_fix_uses_exact_original_task_evidence[missing_task]
tests/aios_bridge/test_roadmap_governance.py::test_bridge_governed_fix_uses_exact_original_task_evidence[task_blob_drift]
tests/aios_bridge/test_roadmap_governance.py::test_bridge_governed_fix_uses_exact_original_task_evidence[roadmap_mismatch]
plus the two task-authoring preflight-before-mutation regressions reported by canonical T2.
```

These tests intentionally use minimal runtime mocks because invalid/mismatched governed artifacts must fail before activation/runtime-state dependencies. The implementation must preserve that invariant; do not weaken or rewrite those canonical tests to accommodate the regression.

Required repair:

```text
1. REMOVE eager pre_start_prior_state capture from cmd_handoff() function entry.
2. Complete all deterministic control-artifact / task-authoring / roadmap / FIX-mode / Slice-C / blocked-replacement preflight first.
3. Prepare/reconcile the task branch as currently required.
4. Capture exact prior runtime state only immediately before the first lease acquisition for that RUN/FIX activation path.
5. The captured state must still be persisted into the newly ACTIVE authorization and used by _rollback_proven_pre_start_failure().
6. RUN, ordinary FIX, stable-failover FIX, and blocked-replacement FIX must retain SystemExit + Exception rollback coverage once a lease has actually been acquired.
7. No state mutation, lease acquisition, executor invocation, retry, or reroute may occur when canonical governance/task-authoring preflight fails.
```

A small provider-neutral helper for late prior-state capture is acceptable. Do not change roadmap semantics, canonical task requirements, or failing governance tests merely to make T2 green.

Required regressions:

```text
GOVERNANCE_FAILURE_OCCURS_BEFORE_PRE_START_STATE_CAPTURE
TASK_AUTHORING_FAILURE_OCCURS_BEFORE_PRE_START_STATE_CAPTURE
VALID_HANDOFF_CAPTURES_PRIOR_STATE_BEFORE_LEASE_ACTIVATION
SYSTEMEXIT_AFTER_LEASE_STILL_ROLLS_BACK_EXACT_PRIOR_STATE
NORMAL_EXCEPTION_AFTER_LEASE_STILL_ROLLS_BACK_EXACT_PRIOR_STATE
NO_STALE_LEASE_ON_PROVEN_PRE_START_FAILURE
NO_AUTO_RETRY_OR_REROUTE
```

## Protected / Closed

B1 compact RESULT semantics remains CLOSED: schema v2 retains required candidate_head_sha as PRE_PUBLICATION_CONTENT_HEAD, exact governed base_main_sha, external published-head binding, strict fenced-marker handling, duplicate-key rejection, and one machine authority.

B2 certification supersession remains CLOSED: exact PASS idempotent, exact FAILED terminal/no retry, stale PASS/FAILED archived as non-current provenance for a different candidate, stale RUNNING fail-closed.

B3 rollback semantics remains conceptually CLOSED except for B4 ordering: once a lease is acquired, both SystemExit and normal Exception paths must invoke exact rollback while executor is provably not started.

Finding lifecycle, risk evidence, guardrail recommendation, blocked-executor replacement, roadmap v1.2, allowed-path safety, reviewed-head/merge safety, TASK-087 reservation, and P2/P3/H5-H8 closure remain protected.

## Validation

Run bounded impacted tests only during FIX publication, including the exact 7 canonical failures from this certification run plus the new late-snapshot regressions. Candidate-stage AIOS-managed T2 must remain 0.

Do not run full canonical T2 in the executor/FIX publication path. Do not rerun certification for the failed head. After a new candidate is published, ChatGPT performs Delta + Impact review again. Only a newly semantically accepted head may receive a new `certify-reviewed 92` execution.

## Decision

```text
TASK-092: CHANGES_REQUIRED
OPEN: B4
CURRENT_HEAD_CERTIFICATION: FAILED_TERMINAL
MERGE: NO
NEXT: FIX TASK-092 -> NEW HEAD -> REVIEW -> certify new head if accepted
TASK_087: DO_NOT_RUN
P1_FORMAL_COMPLETION: NO
```
