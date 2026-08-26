# TASK-095 — P1 Impact Admission + Capability Certification + Capability Main Merge

STATUS: READY
PUBLISHER_PROFILE: CANONICAL_E4
CLASS: L3 — AIOS BRIDGE LEAN EXECUTION / P1 FAST DELIVERY FINALIZATION
MILESTONE: P1
CAPABILITY_ID: P1_UNIFIED_VALIDATION_CAPABILITY_BATCH
VALIDATION_PROFILE: CONTROL_PLANE_STRICT
EXECUTOR_MODE: DUAL_EXECUTOR_ALLOWED
RECOMMENDED_EXECUTOR: codex
PAID_API_CALL_ALLOWED: NO
AUTO_RETRY_ALLOWED: NO
AUTO_REROUTE_ALLOWED: NO
P1_CONTRACT_ADR: ADR-066
TASK_094_PREREQUISITE: PASS_CERTIFIED_MERGED
P1_FORMAL_COMPLETION: NO
PYTHON_AGENT_FAST_LANE_PILOT_AUTHORIZED: NO
P2_P3_AUTHORIZED: NO
H5_H8_AUTHORIZED: NO
REVIEW_PIPELINE_MODE: REVIEW_FIRST_CERTIFICATION

ROADMAP_BINDING_JSON: {"roadmap_id":"AIOS-BRIDGE-LEAN-EXECUTION","roadmap_version":"1.2","roadmap_blob_sha":"41bf467f3dd4fc8aea165ac65c37e0e2a5a3ef5c","roadmap_fingerprint":"89c9372c074ecb43778705f07c6fded67e4af7833c0feb72a92a9ae2e737c612","roadmap_fingerprint_algorithm_version":"roadmap-sha256-v1","milestone":"P1","capability_id":"P1_UNIFIED_VALIDATION_CAPABILITY_BATCH","requirement_bindings":["P1.R3","P1.R4","P1.R6","P1.R9"],"scope_in":["deterministic PRODUCT_DELIVERY_FAST admission from exact batch/lane/task authority and KNOWN impact","task-level fast validation plan with T0/T1 executor ownership and zero task-level T2","operational exact-head lane integration using TASK-094 pure gates","capability-level exact-head T2 certification job with supersession and no model polling","capability-certified fast-forward-only main merge gate","preservation of strict/compat task-local certification semantics"],"scope_out":["Python Agent fast-lane pilot","P1 completion declaration","parallel batch DAG execution","automatic rebase","automatic conflict resolution","automatic retry","automatic reroute","persistent executor session","checkpoint/resume","capacity suspension","P2","P3","H5-H8","canonical roadmap mutation","Slim R2 cleanup"]}

## Exact baseline

```text
MAIN_SHA: 558e666cc5808f5574862feaa8562a7d8c70e86f
TARGET_BRANCH: ai/task-095
TASK_094: PASS_CERTIFIED_MERGED
ROADMAP_V1_2: LOCKED_REGISTERED
ADR_066: ACCEPTED
CONTROL_PLANE_STRICT: IMPLEMENTED
PRODUCT_DELIVERY_FAST_IDENTITY: IMPLEMENTED_BUT_END_TO_END_BLOCKED
CAPABILITY_BATCH_AND_LINEAR_LANE_PURE_CONTRACTS: IMPLEMENTED
CAPABILITY_LEVEL_CERTIFICATION: ABSENT
CAPABILITY_MAIN_MERGE: ABSENT
P1_FORMAL_COMPLETION: NO
PYTHON_AGENT_FAST_LANE_PILOT_AUTHORIZED: NO
P2_P3_STATUS: NOT_AUTHORIZED
H5_H8_STATUS: NOT_AUTHORIZED
```

## Machine-readable E4 inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.2.md","blob_sha":"41bf467f3dd4fc8aea165ac65c37e0e2a5a3ef5c"},{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.2.completions.json","blob_sha":"6b5fb5f99ec17cacca632e3b7a1953131b82c9b7"},{"path":".ai/roadmaps/CANONICAL-ROADMAP-REGISTRY-v1.json","blob_sha":"09180853439a383bb459094cb96fa2bd705afdd4"},{"path":".ai/decisions/ADR-066-AIOS-P1-CAPABILITY-BATCH-INTEGRATION-LANE-CONTRACT-LOCK.md","blob_sha":"e69abac52a773f13b251e27807fd08aac7715a84"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","src/aios_bridge/validation.py","src/aios_bridge/capability_batch.py","src/aios_bridge/integration_lane.py","src/aios_bridge/certification_job.py","src/aios_bridge/review_pipeline.py","src/aios_bridge/review_merge.py","src/aios_bridge/capability_delivery.py","src/aios_bridge/runtime_capability.py","tests/aios_bridge/test_validation.py","tests/aios_bridge/test_capability_batch.py","tests/aios_bridge/test_integration_lane.py","tests/aios_bridge/test_certification_job.py","tests/aios_bridge/test_review_pipeline.py","tests/aios_bridge/test_review_merge.py","tests/aios_bridge/test_capability_delivery.py","tests/aios_bridge/test_runtime_capability.py","tests/aios_bridge/test_lean_review_integration.py","tests/test_bridge.py","tests/test_bridge_review_merge.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

## Purpose

Complete the remaining implementation boundary required before the Python Agent fast-lane pilot. Reuse TASK-094 batch/lane contracts and existing Lean Review certification primitives; do not create a second authority model merely for fast delivery.

TASK-095 must make `PRODUCT_DELIVERY_FAST` executable only when exact machine evidence proves eligibility. It must also provide the capability-level T2 and main-merge boundary required by ADR-066. The fast path removes repeated per-task full-suite certification; it does not remove final exact-head capability certification.

## 1. Fast admission and validation ownership

Implement deterministic `PRODUCT_DELIVERY_FAST` admission. Missing, stale, unknown, or contradictory evidence fails closed.

Admission must prove at minimum:

```text
Human-approved/current capability batch identity
exact current batch manifest fingerprint
exact current linear lane identity/head
exact separately-authorized task binding to current lane head
exact task artifact/scope binding
main still equals batch base main
impact confidence == KNOWN
no protected control-plane surface is admitted as product work
no authority-sensitive uncertainty
```

Do not infer eligibility from task prose, executor identity, filenames alone, or model judgment.

Generalize validation planning only as required so:

```text
CONTROL_PLANE_STRICT_COMPAT -> task-local T2 exactly once, unchanged
CONTROL_PLANE_STRICT        -> task-local T2 exactly once, unchanged
PRODUCT_DELIVERY_FAST       -> executor T0/T1 + diff/scope; task-level T2 = 0; capability-level T2 required
```

No automatic profile upgrade/downgrade is allowed. UNKNOWN/escaped impact fails fast admission/integration; Human/Architect may separately re-authorize a future task under CONTROL_PLANE_STRICT.

## 2. Operational lane integration

Expose the minimum Bridge surface necessary to apply TASK-094's pure deterministic lane integration gate to real Git refs.

Required behavior:

```text
semantic acceptance binds exact task head
candidate-stage AIOS-managed T2 count == 0
publication trust valid
scope valid
impact KNOWN
lease state NONE
current lane head == bound lane base
main == batch base main
reviewed task head fast-forwardable from lane head
-> fast-forward capability lane to exact reviewed task head
```

After mutation, refetch and verify the remote lane head equals the exact reviewed head. Any mismatch fails closed/recovery-required and creates no final authority.

Forbidden: merge commit, cherry-pick, squash, implicit conflict resolution, automatic rebase, task direct-main merge.

Successful integration is NON-FINAL and must not create TASK FINAL_PASS, capability CERTIFIED, main merge authority, or P1 completion.

Prefer extending the Slim root `bridge.py` surface rather than adding new routine dependency to `legacy_bridge.py`. Do not modify `legacy_bridge.py` unless a concrete compatibility blocker makes it strictly necessary and the change is bounded/tested.

## 3. Capability certification job

When the current manifest/lane reaches `READY_FOR_CAPABILITY_CERTIFICATION`, freeze exact:

```text
batch identity + manifest fingerprint
base main SHA
lane ref
lane head SHA
roadmap identity/fingerprint
full canonical command identity
```

Run full canonical T2 exactly once for that exact capability candidate.

Required semantics:

```text
FULL_CANONICAL_OWNER: CAPABILITY_CERTIFICATION_BOUNDARY
EXPECTED_AIOS_MANAGED_T2_COUNT: 1
MODEL_POLLING: NO
AUTO_RETRY: NO
NEW_LANE_HEAD_AFTER_JOB_CREATION: SUPERSEDE_OLD_JOB
FAILED_EXACT_HEAD: TERMINAL_FOR_THAT_HEAD
REPAIR: NEW_SEPARATELY_AUTHORIZED_TASK / NEW_LANE_HEAD
```

Reuse/generalize existing `certification_job.py` semantics where safe. If a capability-specific wrapper is required, keep it bounded and do not duplicate task certification logic unnecessarily.

A failed T2 preserves lane provenance and grants no merge authority.

## 4. Capability main merge gate

Implement a deterministic fast-forward-only capability merge gate.

Merge may proceed only if all are exact/current:

```text
batch status == CERTIFIED
certification PASS binds current lane head
certified manifest fingerprint == current manifest fingerprint
roadmap identity/fingerprint current
main == batch.base_main_sha
lane ancestry from base to certified head is exact/fast-forwardable
no stale/superseded certification
no active/uncertain executor lease or recovery state
```

Then and only then fast-forward `main` to the certified lane head and post-verify:

```text
remote main == certified lane head
remote capability lane == certified lane head
certification subject remains exact
```

No individual `PRODUCT_DELIVERY_FAST` task may use the existing task `merge-reviewed` path to reach main.

## 5. Batch/lane authority persistence boundary

Do not make a local cache the source of Human authority. Canonical membership/binding must remain tied to exact machine-readable control evidence and Git identity.

If operational lane state needs persistence, use the smallest external-runtime representation necessary and bind every record to exact batch manifest fingerprint + lane ref/head + base main. Prefer existing atomic/runtime patterns; do not create a generalized workflow database, scheduler, registry, or new control plane.

Loss/staleness of runtime state must fail closed and must not silently reconstruct authority from prose.

## 6. Required proofs

At minimum targeted tests must prove:

```text
FAST_PROFILE_TASK_LEVEL_T2_ZERO: PASS
STRICT_AND_COMPAT_T2_SEMANTICS_UNCHANGED: PASS
FAST_ADMISSION_REQUIRES_EXACT_BATCH_AND_LANE: PASS
FAST_ADMISSION_REQUIRES_KNOWN_IMPACT: PASS
UNKNOWN_IMPACT_FAILS_CLOSED: PASS
PROTECTED_CONTROL_PLANE_SURFACE_REJECTED: PASS
STALE_TASK_LANE_BINDING_REJECTED: PASS
DIRECT_FAST_TASK_MAIN_MERGE_REJECTED: PASS
LANE_INTEGRATION_FAST_FORWARD_ONLY: PASS
LANE_POST_PUSH_IDENTITY_VERIFIED: PASS
LANE_INTEGRATION_FINAL_PASS: NO
CAPABILITY_CERTIFICATION_EXACT_HEAD: PASS
CAPABILITY_T2_EXECUTION_COUNT_EXACTLY_ONE: PASS
CAPABILITY_CERTIFICATION_SUPERSESSION: PASS
FAILED_CERTIFICATION_NO_AUTO_RETRY: PASS
CAPABILITY_MERGE_REQUIRES_CERTIFIED_EXACT_HEAD: PASS
MAIN_DRIFT_REJECTED: PASS
STALE_MANIFEST_REJECTED: PASS
STALE_CERTIFICATION_REJECTED: PASS
CAPABILITY_MAIN_MERGE_FAST_FORWARD_ONLY: PASS
POST_MERGE_IDENTITY_VERIFIED: PASS
AUTO_RETRY: NO
AUTO_REROUTE: NO
AUTO_REBASE: NO
AUTO_CONFLICT_RESOLUTION: NO
PYTHON_AGENT_PILOT_NOT_IMPLEMENTED: PASS
P1_FORMAL_COMPLETION: NO
P2_P3_NOT_OPENED: PASS
H5_H8_NOT_OPENED: PASS
```

Executor runs T0 / bounded targeted T1 / diff check only. TASK-095 itself is `CONTROL_PLANE_STRICT`; do not run full canonical T2 during RUN/FIX publication. Final TASK-095 T2 remains owned by `bridge.py certify-reviewed 95` after semantic acceptance.

## 7. Protected surfaces

Preserve unless the task's exact requirement cannot be met without a bounded compatibility change:

```text
Canonical Roadmap Lock / registry semantics
Human executor authority
lease safety
publication trust
allowed-path enforcement
Review-First task semantics
Slice-C proof reuse
existing task certification exact-head semantics
existing strict reviewed-head main merge semantics
WorkerFailureEvidence / blocked recovery
Slim context reduction
```

The implementation must not restore removed model-visible machine bookkeeping or duplicate semantic preflight on the happy path.

## Explicit out of scope

```text
Python Agent pilot task or product implementation
P1 formal completion declaration
roadmap v1.3
H5-H8
P2/P3
persistent executor sessions/checkpoints/resume
parallel capability DAG
automatic retry/reroute
automatic rebase/conflict resolution
adaptive executor selection
Slim R2 / legacy_bridge physical deletion
```

## Acceptance

TASK-095 passes only if:

```text
P1_R4_IMPACT_ADMISSION: PASS
PRODUCT_DELIVERY_FAST_END_TO_END_AUTHORITY: IMPLEMENTED_FAIL_CLOSED
TASK_LEVEL_FAST_T2: ZERO
CAPABILITY_LEVEL_FINAL_T2: EXACTLY_ONE
CAPABILITY_CERTIFICATION_EXACT_HEAD_SUPERSESSION: PASS
CAPABILITY_MAIN_MERGE_CERTIFIED_ONLY: PASS
DIRECT_FAST_TASK_MAIN_MERGE: FORBIDDEN
STRICT_COMPAT_REGRESSION: NONE
TASK PASS != P1 COMPLETE
PYTHON_AGENT_FAST_LANE_PILOT_AUTHORIZED_AFTER_095_PASS_MERGE: YES
P1_FORMAL_COMPLETION: NO
P2_P3_NOT_OPENED: PASS
H5_H8_NOT_OPENED: PASS
```

## Required delivery lifecycle

```text
Codex RUN
  -> T0 / bounded targeted T1 / diff check
  -> publish Review-First candidate with AIOS-managed task T2 count = 0
  -> ChatGPT semantic review
      -> CHANGES_REQUIRED: bounded FIX / Delta+Impact
      -> SEMANTICALLY_ACCEPTED_PENDING_T2
  -> bridge.py certify-reviewed 95
      -> full canonical TASK-095 T2 exactly once
  -> bridge.py merge-reviewed 95
  -> only then authorize Python Agent fast-lane pilot
```
