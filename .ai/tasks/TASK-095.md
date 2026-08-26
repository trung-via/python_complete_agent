# TASK-095 — P1 Impact Admission + Capability Certification + Capability Main Merge

STATUS: BLOCKED
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
BLOCKED_BY_TASK: TASK-096
BLOCK_REASON: CODEX_INTERACTIVE_EXECUTOR_PARITY_RECOVERY_REQUIRED
TASK_095_RESUME_AUTHORIZED: NO
P1_FORMAL_COMPLETION: NO
PYTHON_AGENT_FAST_LANE_PILOT_AUTHORIZED: NO
P2_P3_AUTHORIZED: NO
H5_H8_AUTHORIZED: NO
REVIEW_PIPELINE_MODE: REVIEW_FIRST_CERTIFICATION

ROADMAP_BINDING_JSON: {"roadmap_id":"AIOS-BRIDGE-LEAN-EXECUTION","roadmap_version":"1.2","roadmap_blob_sha":"41bf467f3dd4fc8aea165ac65c37e0e2a5a3ef5c","roadmap_fingerprint":"89c9372c074ecb43778705f07c6fded67e4af7833c0feb72a92a9ae2e737c612","roadmap_fingerprint_algorithm_version":"roadmap-sha256-v1","milestone":"P1","capability_id":"P1_UNIFIED_VALIDATION_CAPABILITY_BATCH","requirement_bindings":["P1.R3","P1.R4","P1.R6","P1.R9"],"scope_in":["deterministic PRODUCT_DELIVERY_FAST admission from exact batch/lane/task authority and KNOWN impact","task-level fast validation with zero task-level T2","operational exact-head linear lane integration","capability-level exact-head T2 certification with supersession","capability-certified fast-forward-only main merge","strict/compat regression preservation"],"scope_out":["Python Agent pilot","P1 completion","parallel DAG","automatic rebase/conflict resolution/retry/reroute","persistent executor session","P2","P3","H5-H8","roadmap mutation","Slim R2 cleanup"]}

## Blocking recovery gate

TASK-095 MUST NOT execute while `TASK_095_RESUME_AUTHORIZED: NO`.

Observed Codex execution reliability on the exact baseline produced two consecutive zero-product attempts, including one orphaned ACTIVE lease/authorization recovery and one structured `CLEAN_NO_WORKTREE_DELTA`. Human authority therefore requires TASK-096 (ADR-067) to restore Codex interactive executor parity before this task resumes.

After TASK-096 PASS/certification/merge, TASK-095 must be rebound to the new exact main and explicitly returned to READY. No automatic resume, retry, reroute, or baseline rewrite is authorized.

## Exact baseline

```text
MAIN_SHA: 558e666cc5808f5574862feaa8562a7d8c70e86f
TARGET_BRANCH: ai/task-095
TASK_094: PASS_CERTIFIED_MERGED
TASK_096: REQUIRED_BEFORE_RESUME
ROADMAP_V1_2: LOCKED_REGISTERED
ADR_066: ACCEPTED
CONTROL_PLANE_STRICT: IMPLEMENTED
PRODUCT_DELIVERY_FAST: RECOGNIZED_BUT_END_TO_END_BLOCKED
CAPABILITY_BATCH_LANE_CONTRACTS: IMPLEMENTED
CAPABILITY_CERTIFICATION_MAIN_MERGE: ABSENT
P1_FORMAL_COMPLETION: NO
PYTHON_AGENT_FAST_LANE_PILOT_AUTHORIZED: NO
```

## Machine-readable E4 inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.2.md","blob_sha":"41bf467f3dd4fc8aea165ac65c37e0e2a5a3ef5c"},{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.2.completions.json","blob_sha":"6b5fb5f99ec17cacca632e3b7a1953131b82c9b7"},{"path":".ai/roadmaps/CANONICAL-ROADMAP-REGISTRY-v1.json","blob_sha":"09180853439a383bb459094cb96fa2bd705afdd4"},{"path":".ai/decisions/ADR-066-AIOS-P1-CAPABILITY-BATCH-INTEGRATION-LANE-CONTRACT-LOCK.md","blob_sha":"e69abac52a773f13b251e27807fd08aac7715a84"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","src/aios_bridge/validation.py","src/aios_bridge/capability_batch.py","src/aios_bridge/integration_lane.py","src/aios_bridge/certification_job.py","src/aios_bridge/review_pipeline.py","src/aios_bridge/review_merge.py","src/aios_bridge/capability_delivery.py","src/aios_bridge/runtime_capability.py","tests/aios_bridge/test_validation.py","tests/aios_bridge/test_capability_batch.py","tests/aios_bridge/test_integration_lane.py","tests/aios_bridge/test_certification_job.py","tests/aios_bridge/test_review_pipeline.py","tests/aios_bridge/test_review_merge.py","tests/aios_bridge/test_capability_delivery.py","tests/aios_bridge/test_runtime_capability.py","tests/aios_bridge/test_lean_review_integration.py","tests/test_bridge.py","tests/test_bridge_review_merge.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

## Authority

ADR-066 Sections 4–9 are the detailed implementation contract. This TASK narrows them to the exact current baseline and allowed paths. Do not duplicate or reinterpret batch/lane authority already implemented by TASK-094.

`legacy_bridge.py` is NOT authorized for mutation. Extend the Slim root `bridge.py` surface and bounded modules above. If the requirement cannot be implemented without changing `legacy_bridge.py`, report a specific blocker instead of widening scope.

## Required implementation

### A. PRODUCT_DELIVERY_FAST admission

Open the fast profile only from exact machine evidence proving:

```text
current Human-approved batch manifest/fingerprint
current linear lane/head
separately-authorized task binding == current lane head
exact task artifact + scope binding
main == batch base main
impact confidence == KNOWN
no protected control-plane surface / authority uncertainty
```

Missing/stale/UNKNOWN evidence fails closed. No inference from prose/model/executor. No automatic profile switch.

Validation ownership must become:

```text
CONTROL_PLANE_STRICT_COMPAT -> task T2 exactly 1 (unchanged)
CONTROL_PLANE_STRICT        -> task T2 exactly 1 (unchanged)
PRODUCT_DELIVERY_FAST       -> executor T0/T1; task T2 = 0; capability T2 required
```

### B. Real linear-lane integration

Use TASK-094 pure gates. After semantic acceptance, advance the capability lane only when exact review head, publication trust, scope, KNOWN impact, lease absence, manifest identity, base-main identity and fast-forward ancestry all pass.

Mutation is `fast-forward lane -> exact reviewed task head` only. Refetch and post-verify remote lane identity. Integration is NON-FINAL: no TASK FINAL_PASS, capability certification, main merge authority or P1 completion.

### C. Capability certification

At `READY_FOR_CAPABILITY_CERTIFICATION`, freeze manifest fingerprint + base main + lane ref/head + roadmap identity + full-suite command identity. Run full canonical T2 exactly once on that exact lane head.

Preserve existing certification principles:

```text
FULL_CANONICAL_OWNER: CAPABILITY_CERTIFICATION_BOUNDARY
T2_EXPECTED: 1
MODEL_POLLING: NO
NEW_LANE_HEAD: SUPERSEDE_OLD_JOB
FAILED_EXACT_HEAD: TERMINAL
AUTO_RETRY: NO
REPAIR: NEW_AUTHORIZED_TASK / NEW_LANE_HEAD
```

Reuse/generalize `certification_job.py` where safe; do not create a duplicate authority model unnecessarily.

### D. Capability main merge

Allow fast-forward `main -> certified lane head` only when certification PASS binds the exact current head/manifest, roadmap is current, `main == batch.base_main_sha`, ancestry is fast-forwardable, and no stale certification/recovery/lease uncertainty exists.

Post-push refetch must prove:

```text
remote main == certified lane head
remote capability lane == certified lane head
certification subject still exact
```

Individual PRODUCT_DELIVERY_FAST tasks must never use task-level direct-main merge authority.

### E. Minimal persistence

Canonical membership/binding authority must remain exact control/Git evidence, never a local cache. If operational state requires persistence, use the smallest external-runtime record bound to manifest fingerprint + lane ref/head + base main, following existing atomic-runtime patterns. Do not build a workflow database, scheduler or new generalized control plane.

## Required proofs

```text
FAST_TASK_T2_ZERO: PASS
STRICT_COMPAT_T2_UNCHANGED: PASS
FAST_ADMISSION_EXACT_BATCH_LANE_TASK: PASS
KNOWN_IMPACT_REQUIRED: PASS
UNKNOWN_IMPACT_FAIL_CLOSED: PASS
PROTECTED_CONTROL_PLANE_REJECTED: PASS
STALE_BINDING_REJECTED: PASS
DIRECT_FAST_TASK_MAIN_MERGE_REJECTED: PASS
LANE_FAST_FORWARD_ONLY: PASS
LANE_POST_PUSH_IDENTITY: PASS
LANE_INTEGRATION_FINAL_PASS: NO
CAPABILITY_CERTIFICATION_EXACT_HEAD: PASS
CAPABILITY_T2_EXACTLY_ONE: PASS
CAPABILITY_CERTIFICATION_SUPERSESSION: PASS
FAILED_CERTIFICATION_AUTO_RETRY: NO
CAPABILITY_MERGE_CERTIFIED_ONLY: PASS
MAIN_DRIFT_REJECTED: PASS
STALE_MANIFEST_CERTIFICATION_REJECTED: PASS
CAPABILITY_MAIN_FAST_FORWARD_ONLY: PASS
POST_MERGE_IDENTITY: PASS
AUTO_RETRY: NO
AUTO_REROUTE: NO
AUTO_REBASE: NO
AUTO_CONFLICT_RESOLUTION: NO
PYTHON_AGENT_PILOT_IMPLEMENTED: NO
P1_FORMAL_COMPLETION: NO
P2_P3_NOT_OPENED: PASS
H5_H8_NOT_OPENED: PASS
```

Executor runs T0 / bounded targeted T1 / diff check only. TASK-095 itself is CONTROL_PLANE_STRICT, so its full canonical T2 remains exclusively `bridge.py certify-reviewed 95` after semantic acceptance.

## Protected / out of scope

Preserve Roadmap Lock, Human executor authority, lease safety, publication trust, allowed-path enforcement, Review-First/Slice-C semantics, task certification, strict merge gate, worker recovery, and Slim context reduction.

Do not implement the Python Agent pilot, P1 completion, roadmap v1.3, H5-H8, P2/P3, sessions/checkpoint/resume, parallel capability DAG, adaptive selection, automatic retry/reroute/rebase/conflict resolution, or Slim R2 cleanup.

## Acceptance

```text
P1_R4_IMPACT_ADMISSION: PASS
PRODUCT_DELIVERY_FAST_END_TO_END_AUTHORITY: IMPLEMENTED_FAIL_CLOSED
TASK_LEVEL_FAST_T2: ZERO
CAPABILITY_LEVEL_FINAL_T2: EXACTLY_ONE
CAPABILITY_CERTIFICATION_SUPERSESSION: PASS
CAPABILITY_MAIN_MERGE_CERTIFIED_ONLY: PASS
DIRECT_FAST_TASK_MAIN_MERGE: FORBIDDEN
STRICT_COMPAT_REGRESSION: NONE
TASK PASS != P1 COMPLETE
PYTHON_AGENT_FAST_LANE_PILOT_AUTHORIZED_AFTER_095_PASS_MERGE: YES
P1_FORMAL_COMPLETION: NO
P2_P3_NOT_OPENED: PASS
H5_H8_NOT_OPENED: PASS
```

## Delivery lifecycle

```text
BLOCKED until TASK-096 PASS/certified/merged
-> rebind TASK-095 to new exact main
-> explicit Human resume
-> Codex direct-interactive RUN -> T0/T1 -> publish(T2=0) -> ChatGPT review
-> certify-reviewed 95 (TASK-095 T2 exactly once)
-> merge-reviewed 95
-> only then Python Agent fast-lane pilot
```
