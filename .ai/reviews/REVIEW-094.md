# REVIEW-094 — P1 Capability Batch Authority + Linear Integration Lane
PUBLISHER_PROFILE: CANONICAL_E4
STATUS: CHANGES_REQUIRED
APPROVED: NO
AUTO_MERGE_ELIGIBLE: NO
MERGE_AUTHORIZED: NO
MERGED_TO_MAIN: NO
TASK_ID: TASK-094
REVIEW_ROUND: 1
REVIEWED_TASK_HEAD_SHA: 5a4a57fde7d9244799bde67d4f29eb91acd6eb2d
REVIEWED_BASE_MAIN_SHA: 46a567bfd134fa0737ac0b93058ef1cd93d386ee
TASK_ARTIFACT_BLOB_SHA: b7e47372bdf576327f427cf584aa5389ed7905df
RESULT_BLOB_SHA: 7e55e98569f7424ad26199323dec822b346f0986
EXECUTOR_ID: codex
RECOMMENDED_FIX_EXECUTOR: codex
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
REQUIREMENT_BINDINGS_FINGERPRINT: b8438b5d18d993585c694b64908c61334b46649a81690589b283d758471fe979
RECONCILIATION_ADR: ADR-067
RECONCILIATION_ADR_BLOB_SHA: fcd2f4ebb7b50c237dc357d0a68aa98d89bc132b
CANONICAL_REQUIREMENT_IDENTITY_CHANGED: NO
ROADMAP_V1_3_REQUIRED: NO
P1_FORMAL_COMPLETION: NO
TASK_095_AUTHORIZED: NO
PYTHON_AGENT_FAST_LANE_PILOT_AUTHORIZED: NO
P2_P3_AUTHORIZED: NO
H5_H8_AUTHORIZED: NO
FIX_REVIEW_MODE: PROOF_REUSE_DELTA_IMPACT
FIX_CONTEXT_PACK_JSON: {"schema_version":"1","previous_reviewed_head_sha":"5a4a57fde7d9244799bde67d4f29eb91acd6eb2d","impact_confidence":"KNOWN","open_finding_ids":["B1_REVIEW_STATE_AUTHORITY","B2_PROGRESSIVE_MEMBERSHIP_REBIND"],"affected_paths":["src/aios_bridge/capability_batch.py","src/aios_bridge/integration_lane.py","tests/aios_bridge/test_capability_batch.py","tests/aios_bridge/test_integration_lane.py"],"protected_accepted_paths":[],"required_test_paths":["tests/aios_bridge/test_capability_batch.py","tests/aios_bridge/test_integration_lane.py"],"unknown_impact_fallback_test_paths":["tests/aios_bridge/test_validation.py","tests/aios_bridge/test_lean_review_integration.py","tests/aios_bridge/test_capability_batch.py","tests/aios_bridge/test_integration_lane.py"],"proof_bindings":[]}
EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/tasks/TASK-094.md","blob_sha":"b7e47372bdf576327f427cf584aa5389ed7905df"},{"path":".ai/decisions/ADR-066-AIOS-P1-CAPABILITY-BATCH-INTEGRATION-LANE-CONTRACT-LOCK.md","blob_sha":"e69abac52a773f13b251e27807fd08aac7715a84"},{"path":".ai/decisions/ADR-067-AIOS-P0-P3-LEAN-REVIEW-RECONCILIATION.md","blob_sha":"fcd2f4ebb7b50c237dc357d0a68aa98d89bc132b"},{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.2.md","blob_sha":"41bf467f3dd4fc8aea165ac65c37e0e2a5a3ef5c"},{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.2.completions.json","blob_sha":"6b5fb5f99ec17cacca632e3b7a1953131b82c9b7"},{"path":".ai/roadmaps/CANONICAL-ROADMAP-REGISTRY-v1.json","blob_sha":"09180853439a383bb459094cb96fa2bd705afdd4"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["src/aios_bridge/capability_batch.py","src/aios_bridge/integration_lane.py","tests/aios_bridge/test_capability_batch.py","tests/aios_bridge/test_integration_lane.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]},{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]}],"operation":"FIX","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

## Snapshot

```text
HEAD: 5a4a57fde7d9244799bde67d4f29eb91acd6eb2d
BASE_MAIN: 46a567bfd134fa0737ac0b93058ef1cd93d386ee
MERGE_BASE: 46a567bfd134fa0737ac0b93058ef1cd93d386ee
AHEAD_FROM_MAIN: 1
BEHIND_MAIN: 0
MAIN_DRIFT: NO
CANDIDATE_STAGE_AIOS_MANAGED_T2_EXECUTION_COUNT: 0
CERTIFICATION_DEFERRED: YES
TARGETED_TEST_STATUS: NOT_REQUIRED
VALIDATION_PROFILE: CONTROL_PLANE_STRICT
```

Candidate is preserved. It adds bounded pure capability-batch/lane contracts and tests only; it has not opened PRODUCT_DELIVERY_FAST end-to-end execution, certification, or main-merge authority.

## B1 — OPEN — Fast-Lane Review Authority Must Not Be Fabricated

`integration_lane.py` currently treats the free-form token `SEMANTICALLY_ACCEPTED_PENDING_INTEGRATION` as semantic-review authority even though that state is not part of the authoritative Lean Review `ReviewState`.

Required repair within TASK-094 scope:

```text
semantic_acceptance_valid: exact bool supplied by deterministic caller
reviewed_task_head_sha: exact SHA
reviewed head == current task branch head
false/unknown/malformed semantic acceptance -> fail closed
lane advancement -> no FINAL_PASS authority
lane advancement -> no main merge authority
```

Do not modify `src/aios_bridge/review_pipeline.py` in this FIX. Profile-aware ReviewState integration remains TASK-095 work.

Required proofs:

```text
NO_FABRICATED_FAST_REVIEW_STATE_AUTHORITY: PASS
SEMANTIC_ACCEPTANCE_FALSE_FAILS_CLOSED: PASS
SEMANTIC_ACCEPTANCE_MALFORMED_FAILS_CLOSED: PASS
REVIEWED_HEAD_MISMATCH_REJECTED: PASS
LANE_ADVANCE_FINAL_PASS_AUTHORITY: NO
LANE_ADVANCE_MAIN_MERGE_AUTHORITY: NO
```

## B2 — OPEN — Progressive Multi-Task Membership + Lane Rebind

The current manifest requires future members to know exact `bound_lane_base_sha` before predecessor reviewed heads exist, and collapses every member version into the whole manifest version. A manifest revision changes its fingerprint while the lane remains bound to the prior fingerprint, so the multi-task sequence is not yet realizable.

Required repair:

```text
manifest v1 admits TASK-A bound to current lane head
TASK-A integrates
manifest v2 preserves integrated TASK-A exactly
manifest v2 admits TASK-B bound to the now-known current lane head
pure deterministic lane-manifest rebind changes only manifest authority binding
TASK-B becomes the next admissible member
```

Integrated prefix must remain immutable across manifest revisions:

```text
task_id unchanged
task artifact blob unchanged
scope fingerprint unchanged
expected branch unchanged
bound lane base unchanged
membership position unchanged
unchanged member authority version unchanged
```

`manifest_version` and `membership_version` are distinct. A lane-manifest rebind must require exact batch/roadmap/capability/base/lane identity, previous fingerprint binding, next manifest version, immutable integrated prefix, and next member base equal to current lane head. It must not move lane head or create FINAL_PASS, certification, or main-merge authority.

Required proofs:

```text
MULTI_TASK_PROGRESSIVE_MEMBERSHIP_REALIZABLE: PASS
INTEGRATED_PREFIX_IMMUTABLE: PASS
UNCHANGED_MEMBER_VERSION_PRESERVED: PASS
MANIFEST_REVISION_CHANGES_MANIFEST_FINGERPRINT: PASS
LANE_MANIFEST_REBIND_EXACT: PASS
STALE_PREVIOUS_MANIFEST_REJECTED: PASS
REORDERED_OR_MUTATED_INTEGRATED_PREFIX_REJECTED: PASS
NEXT_MEMBER_BINDS_CURRENT_LANE_HEAD: PASS
LANE_HEAD_UNCHANGED_BY_REBIND: PASS
REBINDS_CREATE_NO_FINAL_PASS: PASS
REBINDS_CREATE_NO_MAIN_MERGE_AUTHORITY: PASS
```

## Accepted / Protected Surfaces

```text
A1 batch/lane modules remain pure: no filesystem, Git, certification, or main-merge side effects
A2 closed schemas/enums remain strict and fail-closed
A3 exact SHA/fingerprint validation remains intact
A4 batch membership never replaces independent TASK artifact/scope authority
A5 candidate-stage T2 remains 0
A6 UNKNOWN impact remains rejected for fast-lane integration
A7 publication trust, scope, lease absence, main-base identity, and fast-forwardability remain required
A8 lane advancement creates neither FINAL_PASS nor main merge authority
A9 PRODUCT_DELIVERY_FAST end-to-end admission remains blocked until TASK-095
A10 CONTROL_PLANE_STRICT behavior is not modified
A11 P1 remains incomplete; P2/P3 and H5-H8 remain unopened
```

## Delta + Impact FIX Boundary

FIX write scope is deliberately narrowed to the four paths in `EXECUTOR_ALLOWED_PATHS_JSON`. Required targeted floor:

```text
pytest tests/aios_bridge/test_capability_batch.py -q
pytest tests/aios_bridge/test_integration_lane.py -q
```

If deterministic impact becomes UNKNOWN, use the fallback test set from `FIX_CONTEXT_PACK_JSON`; do not widen write authority. Candidate-stage AIOS-managed T2 must remain 0.

## Semantic Decision

```text
TASK-094: CHANGES_REQUIRED
REVIEW_ROUND: 1
SEMANTIC_BLOCKERS: 2
B1: OPEN
B2: OPEN
FINAL_PASS: NO
CERTIFICATION_AUTHORIZED: NO
MERGE_AUTHORIZED: NO
ROADMAP_V1_2: UNCHANGED
ROADMAP_V1_3_REQUIRED: NO
TASK_095_AUTHORIZED: NO
NEXT: $aios-worker FIX TASK-094
```

This is an executable-authoring repair of the same Round-1 semantic review, not a new semantic review round. The review remains bound to exact candidate `5a4a57fde7d9244799bde67d4f29eb91acd6eb2d` and base main `46a567bfd134fa0737ac0b93058ef1cd93d386ee`. Full canonical T2 remains forbidden until both blockers close.