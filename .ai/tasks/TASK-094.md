# TASK-094 — P1 Capability Batch Authority + Linear Integration Lane

STATUS: READY
PUBLISHER_PROFILE: CANONICAL_E4
CLASS: L3 — AIOS BRIDGE LEAN EXECUTION / P1 CAPABILITY BATCH + LINEAR INTEGRATION LANE
MILESTONE: P1
CAPABILITY_ID: P1_UNIFIED_VALIDATION_CAPABILITY_BATCH
VALIDATION_PROFILE: CONTROL_PLANE_STRICT
EXECUTOR_MODE: DUAL_EXECUTOR_ALLOWED
RECOMMENDED_EXECUTOR: codex
PAID_API_CALL_ALLOWED: NO
AUTO_RETRY_ALLOWED: NO
AUTO_REROUTE_ALLOWED: NO
P1_CONTRACT_ADR: ADR-066
TASK_093_PREREQUISITE: PASS_CERTIFIED_MERGED
P1_FORMAL_COMPLETION: NO
TASK_095_AUTHORIZED: NO
PYTHON_AGENT_FAST_LANE_PILOT_AUTHORIZED: NO
PRODUCT_DELIVERY_FAST_FULL_ADMISSION: NOT_YET_AUTHORIZED
P2_P3_AUTHORIZED: NO
H5_H8_AUTHORIZED: NO
REVIEW_PIPELINE_MODE: REVIEW_FIRST_CERTIFICATION

ROADMAP_BINDING_JSON: {"roadmap_id":"AIOS-BRIDGE-LEAN-EXECUTION","roadmap_version":"1.2","roadmap_blob_sha":"41bf467f3dd4fc8aea165ac65c37e0e2a5a3ef5c","roadmap_fingerprint":"89c9372c074ecb43778705f07c6fded67e4af7833c0feb72a92a9ae2e737c612","roadmap_fingerprint_algorithm_version":"roadmap-sha256-v1","milestone":"P1","capability_id":"P1_UNIFIED_VALIDATION_CAPABILITY_BATCH","requirement_bindings":["P1.R2","P1.R3"],"scope_in":["bounded machine-readable capability-batch authority preserving independent task authority","versioned/fingerprinted batch manifest identity and closed lifecycle","linear integration-lane state bound to exact base main and exact current lane head","separately authorized task membership without scope collapse","deterministic exact-head lane integration preflight and fast-forward-only integration semantics","main-drift fail-closed behavior for open batches","provider-neutral batch/lane contracts reusable by later PRODUCT_DELIVERY_FAST admission","Review-First and Slice-C compatibility for future fast-lane tasks"],"scope_out":["capability-level T2 certification job","capability-level main merge gate","final PRODUCT_DELIVERY_FAST admission cutover","Python Agent fast-lane pilot","parallel batch DAG execution","automatic rebase","automatic conflict resolution","automatic retry","automatic reroute","persistent executor session","checkpoint/resume","capacity suspension","P2","P3","H5-H8","canonical roadmap mutation"]}

## Exact Baseline

```text
MAIN_SHA: 46a567bfd134fa0737ac0b93058ef1cd93d386ee
TARGET_BRANCH: ai/task-094
TASK_093: PASS_CERTIFIED_MERGED
ADR_066: ACCEPTED
ROADMAP_V1_2: LOCKED_REGISTERED
CONTROL_PLANE_STRICT: IMPLEMENTED
PRODUCT_DELIVERY_FAST: DEFINED_CLOSED_NOT_FULLY_EXECUTABLE
CAPABILITY_BATCH_RUNTIME: ABSENT
LINEAR_INTEGRATION_LANE_RUNTIME: ABSENT
CAPABILITY_CERTIFICATION_RUNTIME: ABSENT
CAPABILITY_MAIN_MERGE_RUNTIME: ABSENT
P1_FORMAL_COMPLETION: NO
P2_P3_STATUS: NOT_AUTHORIZED
H5_H8_STATUS: NOT_AUTHORIZED
```

### Baseline missing guard

The following required P1 implementation is absent on the exact baseline and therefore a clean no-op is not a valid successful implementation:

```text
src/aios_bridge/capability_batch.py: ABSENT
src/aios_bridge/integration_lane.py: ABSENT
machine-readable batch manifest contract: ABSENT
versioned batch fingerprint: ABSENT
linear lane state contract: ABSENT
exact-head deterministic lane integration preflight: ABSENT
NO_WORK_REQUIRED_ALLOWED: NO
CLEAN_NO_WORKTREE_DELTA_AS_TASK_SUCCESS: NO
```

The executor MUST create a real implementation delta or report a specific blocker.

## Executor Authority Clarification

ADR-066 is the architecture contract for this task. The exact TASK-094 artifact is the bounded implementation authority.

Authority order:

```text
canonical roadmap v1.2
  -> ADR-066 locked P1 contract
  -> exact TASK-094 artifact
  -> current main implementation contracts
```

TASK-094 MUST NOT reinterpret ADR-066 as permission to implement TASK-095 capability certification/main-merge authority.

## Machine-Readable E4 Inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.2.md","blob_sha":"41bf467f3dd4fc8aea165ac65c37e0e2a5a3ef5c"},{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.2.completions.json","blob_sha":"6b5fb5f99ec17cacca632e3b7a1953131b82c9b7"},{"path":".ai/roadmaps/CANONICAL-ROADMAP-REGISTRY-v1.json","blob_sha":"09180853439a383bb459094cb96fa2bd705afdd4"},{"path":".ai/decisions/ADR-066-AIOS-P1-CAPABILITY-BATCH-INTEGRATION-LANE-CONTRACT-LOCK.md","blob_sha":"e69abac52a773f13b251e27807fd08aac7715a84"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","src/aios_bridge/capability_batch.py","src/aios_bridge/integration_lane.py","src/aios_bridge/validation.py","src/aios_bridge/executor_automation.py","tests/aios_bridge/test_capability_batch.py","tests/aios_bridge/test_integration_lane.py","tests/aios_bridge/test_validation.py","tests/aios_bridge/test_lean_review_integration.py","tests/test_bridge_executor_automation.py","tests/test_bridge.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

## Purpose

Implement only P1.R2 and P1.R3 from ADR-066:

```text
P1.R2 — capability batches may contain multiple separately authorized tasks without collapsing task authority
P1.R3 — intermediate product work remains on a bounded linear integration lane and main receives no un-certified intermediate state
```

TASK-094 creates the authority and lane foundation that TASK-095 will later connect to impact admission, capability-level T2 certification, and capability main merge.

This task itself is control-plane work and therefore executes under `CONTROL_PLANE_STRICT` with normal task-local Review-First certification.

## 1. Capability Batch Manifest Contract

Create `src/aios_bridge/capability_batch.py` unless an equivalent bounded pure module is strictly necessary.

Define an immutable, machine-readable batch manifest with equivalent required identity fields:

```text
schema_version
batch_id
roadmap_id
roadmap_version
roadmap_fingerprint
milestone
capability_id
base_main_sha
integration_lane_ref
manifest_version
ordered_task_membership
status
```

The exact schema may include additional bounded identity fields required for safe operation, but MUST remain closed and machine-validated.

Required validation:

```text
batch_id canonical and bounded
all SHAs exact lowercase 40-hex
roadmap fingerprint exact lowercase 64-hex
manifest version positive and bounded
membership non-empty when integration begins
membership duplicate-free
membership task IDs canonical TASK-<digits>
unknown/extra serialized fields fail closed
malformed scalar coercion forbidden
```

### Manifest fingerprint

Provide deterministic canonical serialization and fingerprinting.

Required invariant:

```text
same exact manifest identity -> same fingerprint
membership/order/status/authority identity change -> fingerprint changes
```

Do not use timestamps, filesystem state, model output, or unordered serialization as fingerprint authority.

## 2. Closed Batch Lifecycle

Implement a closed lifecycle equivalent to:

```text
OPEN
INTEGRATING
READY_FOR_CAPABILITY_CERTIFICATION
CERTIFICATION_PENDING
CERTIFIED
MERGED
CERTIFICATION_FAILED
SUPERSEDED
RECOVERY_REQUIRED
```

TASK-094 owns only the transitions required through `READY_FOR_CAPABILITY_CERTIFICATION` plus fail-closed recovery/supersession representation where necessary for consistency.

It MUST NOT implement capability T2 execution, capability certification PASS creation, or capability main merge authority. Those remain TASK-095.

A deterministic transition helper must reject impossible/authority-skipping transitions such as:

```text
OPEN -> CERTIFIED
INTEGRATING -> MERGED
READY_FOR_CAPABILITY_CERTIFICATION -> MERGED
CERTIFICATION_FAILED -> CERTIFIED without new authority/head
```

## 3. Independent Task Authority Inside a Batch

Batch membership MUST NOT replace task authority.

Represent task membership/binding sufficiently to prove at least:

```text
task_id
exact task artifact blob SHA
bound lane base SHA
expected task branch
allowed-path/scope fingerprint or equivalent exact authority binding
membership position/version
```

A task may be admitted only if it is explicitly present in the current manifest and its exact binding matches current batch/lane identity.

Required invariant:

```text
BATCH AUTHORITY MAY NARROW TASK AUTHORITY
BATCH AUTHORITY MUST NEVER WIDEN TASK AUTHORITY
```

Adding/removing/reordering/replacing membership requires a new manifest version/fingerprint. No executor may mutate membership as part of implementation execution.

## 4. Linear Integration Lane State

Create `src/aios_bridge/integration_lane.py` unless an equivalent bounded pure module is strictly necessary.

Define immutable/machine-readable lane state equivalent to:

```text
batch_id
batch_manifest_fingerprint
base_main_sha
integration_lane_ref
current_lane_head_sha
integrated_task_ids
status
```

Initial lane state:

```text
base_main_sha == current_lane_head_sha
integrated_task_ids == empty
```

After each successful task integration:

```text
current_lane_head_sha -> exact reviewed task head
integrated_task_ids -> append exactly one expected task
```

The initial implementation is strictly linear. No DAG/parallel parent sets.

## 5. Deterministic Task-to-Lane Binding

Provide a bounded task/lane binding contract sufficient for future fast-lane authoring.

A task binding must prove:

```text
batch_id
batch_manifest_fingerprint
integration_lane_ref
bound_lane_base_sha
expected_task_branch
exact task artifact blob SHA
membership identity/position
```

The next task must bind the exact current lane head. If the lane advances, a stale task binding is invalid.

No automatic rebase or rebinding is permitted.

## 6. Deterministic Lane Integration Preflight

Implement a pure/deterministic preflight evidence contract equivalent to ADR-066 requirements.

Integration may be authorized only when all required facts are proven, including:

```text
batch status permits integration
manifest fingerprint is current
roadmap identity/fingerprint exact
current task is exact expected membership item
review state is semantic acceptance for exact task head
reviewed task head == task branch head
candidate-stage AIOS-managed T2 count == 0
required targeted/impact validation passed or exact machine policy permits NOT_REQUIRED
impact confidence == KNOWN for future fast profile
publication trust valid
scope / allowed paths valid
no active or uncertain executor lease
current lane head == task bound lane base SHA
main current SHA == batch base_main_sha for initial P1 implementation
reviewed task head is a descendant suitable for exact fast-forward lane advancement
```

Because TASK-094 does not own Git itself as pure authority evidence, it may accept bounded booleans/SHAs such as `fast_forwardable` supplied by the Bridge caller. It MUST NOT infer ancestry from prose.

Any missing/unknown/contradictory fact fails closed.

## 7. Lane Advancement Contract

Provide a pure transition that, after a successful preflight, produces the next exact lane state.

Required:

```text
old lane head == task bound lane base
new lane head == exact reviewed task head
one expected membership item appended
batch/lane identity unchanged
no hidden commit synthesis
no scope expansion
```

No lane transition may directly create:

```text
TASK FINAL_PASS
capability CERTIFIED
main merge authority
release authority
```

If the executor adds a minimal Bridge integration surface, it must remain deterministic and fast-forward-only. No command may auto-merge main, auto-rebase, cherry-pick, squash, or conflict-resolve.

## 8. Main Drift Fail-Closed

The batch is bound to exact `base_main_sha`.

Required initial P1 behavior:

```text
main current SHA != batch.base_main_sha
-> lane integration / readiness transition FAIL CLOSED
-> no silent base update
-> no merge-main-into-lane
-> no auto rebase
```

The Human may later authorize a dedicated rebind/rebase procedure, but TASK-094 does not implement one.

## 9. Readiness for Capability Certification

When all manifest tasks have been integrated in exact order, deterministic state may advance to:

```text
READY_FOR_CAPABILITY_CERTIFICATION
```

Required readiness evidence includes at least:

```text
all membership items integrated exactly once
current lane head exact
manifest fingerprint current
main still equals base_main_sha
no unresolved recovery state
```

This state is NON-FINAL and creates no certification or main merge authority.

TASK-095 will own the exact capability T2 job and main merge gate.

## 10. PRODUCT_DELIVERY_FAST Boundary

TASK-094 installs batch/lane authority primitives but MUST NOT silently make `PRODUCT_DELIVERY_FAST` fully executable through the normal worker path yet.

Until TASK-095 installs capability-level certification/main-merge authority:

```text
PRODUCT_DELIVERY_FAST explicit task
-> profile identity remains recognized
-> batch/lane primitives may validate independently in tests/pure contracts
-> normal end-to-end executable admission remains fail-closed
```

Do not change the TASK-093 fail-closed resolver into a permissive fast execution path in this task.

This prevents product work from entering a lane that has no implemented final certification/main-merge boundary.

## 11. Minimal Bridge / Executor Integration

Only add integration necessary to expose or validate the new authority contracts without opening TASK-095 semantics.

Allowed outcomes include deterministic helpers/CLI preflight surfaces for:

```text
batch manifest validation
lane state validation
lane integration preflight evaluation
readiness evaluation
```

If no CLI is necessary to satisfy P1.R2/P1.R3 foundation safely, keep the implementation pure and defer operational commands to TASK-095.

Do not redesign:

```text
roadmap governance
lease semantics
review lifecycle
certification jobs
existing task main merge gate
WorkerFailureEvidence
executor replacement
publication trust
```

## 12. Required Targeted / Impact Proofs

At minimum prove:

```text
CAPABILITY_BATCH_SCHEMA_CLOSED: PASS
CAPABILITY_BATCH_FINGERPRINT_DETERMINISTIC: PASS
CAPABILITY_BATCH_MEMBERSHIP_VERSIONED: PASS
TASK_AUTHORITY_REMAINS_INDEPENDENT: PASS
BATCH_CANNOT_WIDEN_TASK_SCOPE: PASS
BATCH_LIFECYCLE_CLOSED: PASS
AUTHORITY_SKIPPING_TRANSITIONS_REJECTED: PASS
LINEAR_LANE_INITIAL_STATE_EXACT: PASS
LINEAR_LANE_ADVANCES_ONE_TASK_AT_A_TIME: PASS
STALE_LANE_BASE_REJECTED: PASS
STALE_MANIFEST_FINGERPRINT_REJECTED: PASS
WRONG_MEMBERSHIP_ORDER_REJECTED: PASS
REVIEWED_HEAD_MISMATCH_REJECTED: PASS
CANDIDATE_T2_NONZERO_REJECTED: PASS
UNKNOWN_IMPACT_REJECTED: PASS
INVALID_PUBLICATION_TRUST_REJECTED: PASS
ACTIVE_OR_UNCERTAIN_LEASE_REJECTED: PASS
MAIN_DRIFT_REJECTED: PASS
NON_FAST_FORWARD_LANE_ADVANCEMENT_REJECTED: PASS
NO_AUTO_REBASE: PASS
NO_AUTO_CONFLICT_RESOLUTION: PASS
LANE_INTEGRATION_DOES_NOT_CREATE_MAIN_MERGE_AUTHORITY: PASS
ALL_TASKS_INTEGRATED_CAN_REACH_READY_FOR_CAPABILITY_CERTIFICATION: PASS
READY_FOR_CAPABILITY_CERTIFICATION_IS_NON_FINAL: PASS
PRODUCT_DELIVERY_FAST_END_TO_END_REMAINS_BLOCKED_UNTIL_TASK_095: PASS
CONTROL_PLANE_STRICT_TASK_094_REVIEW_FIRST_CANDIDATE_T2_ZERO: PASS
TASK_093_VALIDATION_PROFILE_BEHAVIOR_NOT_REGRESSED: PASS
TASK_087_WORKER_FAILURE_BEHAVIOR_NOT_REGRESSED: PASS
AUTO_RETRY: NO
AUTO_REROUTE: NO
TASK_095_NOT_IMPLEMENTED: PASS
P1_FORMAL_COMPLETION: NO
P2_P3_NOT_OPENED: PASS
H5_H8_NOT_OPENED: PASS
```

Executor runs T0 / bounded targeted T1 / diff check only. Do not run full canonical T2 during RUN/FIX candidate publication.

## 13. Protected Existing Surfaces

Unless deterministic integration proves otherwise, do not change:

```text
CONTROL_PLANE_STRICT_COMPAT historical behavior
CONTROL_PLANE_STRICT strict T2 semantics
PRODUCT_DELIVERY_FAST fail-closed end-to-end admission from TASK-093
roadmap registry/completion semantics
Review-First lifecycle
Slice-C proof carry-forward
certification-job supersession
TASK-087 failure classification
reviewed-head task merge gate
```

Any required widening beyond this list must be reported as a blocker, not silently implemented.

## 14. Explicit Out of Scope

```text
TASK-095 implementation
capability-level full canonical T2 execution
capability certification PASS authority
capability main merge command/gate
Python Agent fast-lane pilot
P1 completion declaration
main rebind/rebase workflow for open batch
parallel/DAG batch execution
automatic merge conflict resolution
automatic cherry-pick/squash/rebase
automatic executor retry/reroute
persistent session/checkpoint/resume/suspension
Claude Code integration
P2
P3
H5-H8
roadmap v1.3
```

## Required Delivery Lifecycle

```text
Codex RUN
  -> T0 / bounded targeted T1 / diff check
  -> publish Review-First candidate with AIOS-managed T2 count = 0
  -> ChatGPT semantic review
      -> CHANGES_REQUIRED: Slice-C FIX / Delta+Impact / next candidate T2=0
      -> SEMANTICALLY_ACCEPTED_PENDING_T2
  -> bridge.py certify-reviewed 94
      -> full canonical T2 exactly once for exact accepted candidate
  -> bridge.py merge-reviewed 94
```

No model polls deterministic certification.

## Acceptance

TASK-094 passes only if:

```text
P1_R2_CAPABILITY_BATCH_AUTHORITY: PASS
P1_R3_LINEAR_INTEGRATION_LANE: PASS
TASK_AUTHORITY_COLLAPSED: NO
LINEAR_EXACT_HEAD_PROVENANCE: PASS
MAIN_DRIFT_FAIL_CLOSED: PASS
LANE_INTEGRATION_FINAL_PASS: NO
LANE_INTEGRATION_MAIN_MERGE_AUTHORITY: NO
READY_FOR_CAPABILITY_CERTIFICATION_NON_FINAL: PASS
PRODUCT_DELIVERY_FAST_FULL_ADMISSION: STILL_BLOCKED_PENDING_TASK_095
CONTROL_PLANE_STRICT_TASK_CERTIFICATION: PRESERVED
TASK PASS != P1 COMPLETE
TASK_095_AUTHORIZED: NO
PYTHON_AGENT_FAST_LANE_PILOT_AUTHORIZED: NO
P2_P3_NOT_OPENED: PASS
H5_H8_NOT_OPENED: PASS
```