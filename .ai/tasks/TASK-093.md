# TASK-093 — P1 Validation Profiles Foundation

STATUS: READY
PUBLISHER_PROFILE: CANONICAL_E4
CLASS: L2 — AIOS BRIDGE LEAN EXECUTION / P1 VALIDATION PROFILE FOUNDATION
MILESTONE: P1
CAPABILITY_ID: P1_UNIFIED_VALIDATION_CAPABILITY_BATCH
EXECUTOR_MODE: DUAL_EXECUTOR_ALLOWED
RECOMMENDED_EXECUTOR: codex
PAID_API_CALL_ALLOWED: NO
AUTO_RETRY_ALLOWED: NO
AUTO_REROUTE_ALLOWED: NO
P1_CONTRACT_ADR: ADR-066
TASK_087_PREREQUISITE: PASS_CERTIFIED_MERGED
P1_FORMAL_COMPLETION: NO
TASK_094_AUTHORIZED: NO
TASK_095_AUTHORIZED: NO
PYTHON_AGENT_FAST_LANE_PILOT_AUTHORIZED: NO
P2_P3_AUTHORIZED: NO
H5_H8_AUTHORIZED: NO
REVIEW_PIPELINE_MODE: REVIEW_FIRST_CERTIFICATION
TARGET_PROFILE_FOUNDATION: CONTROL_PLANE_STRICT,PRODUCT_DELIVERY_FAST
BOOTSTRAP_EXECUTION_PROFILE: CONTROL_PLANE_STRICT_COMPAT

ROADMAP_BINDING_JSON: {"roadmap_id":"AIOS-BRIDGE-LEAN-EXECUTION","roadmap_version":"1.2","roadmap_blob_sha":"41bf467f3dd4fc8aea165ac65c37e0e2a5a3ef5c","roadmap_fingerprint":"89c9372c074ecb43778705f07c6fded67e4af7833c0feb72a92a9ae2e737c612","roadmap_fingerprint_algorithm_version":"roadmap-sha256-v1","milestone":"P1","capability_id":"P1_UNIFIED_VALIDATION_CAPABILITY_BATCH","requirement_bindings":["P1.R1"],"scope_in":["closed validation profile identities CONTROL_PLANE_STRICT and PRODUCT_DELIVERY_FAST","frozen compatibility identity and behavior for CONTROL_PLANE_STRICT_COMPAT","deterministic explicit profile parsing/resolution for future P1 task artifacts","strict control-plane execution policy equivalent in safety to current compatibility policy while preserving distinct evidence identity","fail-closed PRODUCT_DELIVERY_FAST admission until capability-batch/integration-lane authority exists","machine-readable profile policy metadata sufficient for later TASK-094/TASK-095 integration","Review-First candidate T2=0 and strict final certification T2=1 preservation"],"scope_out":["capability batch manifest implementation","integration lane implementation","lane integration gate","capability certification job","capability main merge gate","Python Agent fast-lane pilot","automatic strict/fast profile switching","automatic retry","automatic reroute","persistent executor session","checkpoint/resume","capacity suspension","P2","P3","H5-H8","canonical roadmap mutation"]}

## Exact Baseline

```text
MAIN_SHA: 12904cf867fe5c5fe5be901d94ece82e3523beca
TARGET_BRANCH: ai/task-093
TASK_087: PASS_CERTIFIED_MERGED
ADR_066: ACCEPTED
LEAN_REVIEW_SLICES_A_D: COMPLETE
ROADMAP_V1_2: LOCKED_REGISTERED
CURRENT_VALIDATION_PROFILE_ENUM: CONTROL_PLANE_STRICT_COMPAT_ONLY
CURRENT_STRICT_PLAN: CONTROL_PLANE_STRICT_COMPAT_PLAN
CONTROL_PLANE_STRICT: ABSENT
PRODUCT_DELIVERY_FAST: ABSENT
CAPABILITY_BATCH_AUTHORITY: ABSENT
INTEGRATION_LANE_AUTHORITY: ABSENT
P1_FORMAL_COMPLETION: NO
P2_P3_STATUS: NOT_AUTHORIZED
H5_H8_STATUS: NOT_AUTHORIZED
```

### Bootstrap clarification

TASK-093 creates the new profile foundation, so the exact baseline cannot yet execute this task under a parser-recognized `CONTROL_PLANE_STRICT` profile. This one task therefore executes under the already-certified `CONTROL_PLANE_STRICT_COMPAT` bootstrap policy.

This does NOT alias or reinterpret the two identities. Required post-TASK-093 behavior is:

```text
TASK-093 execution evidence
  -> retains CONTROL_PLANE_STRICT_COMPAT because that is the exact baseline policy

future newly-authored control-plane tasks
  -> may explicitly bind CONTROL_PLANE_STRICT

historical artifacts
  -> retain CONTROL_PLANE_STRICT_COMPAT identity and semantics forever
```

The executor MUST NOT rewrite historical RESULT/TASK evidence to the new profile name.

## Machine-Readable E4 Inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.2.md","blob_sha":"41bf467f3dd4fc8aea165ac65c37e0e2a5a3ef5c"},{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.2.completions.json","blob_sha":"6b5fb5f99ec17cacca632e3b7a1953131b82c9b7"},{"path":".ai/roadmaps/CANONICAL-ROADMAP-REGISTRY-v1.json","blob_sha":"09180853439a383bb459094cb96fa2bd705afdd4"},{"path":".ai/decisions/ADR-066-AIOS-P1-CAPABILITY-BATCH-INTEGRATION-LANE-CONTRACT-LOCK.md","blob_sha":"e69abac52a773f13b251e27807fd08aac7715a84"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","src/aios_bridge/validation.py","src/aios_bridge/executor_automation.py","tests/aios_bridge/test_validation.py","tests/aios_bridge/test_lean_review_integration.py","tests/aios_bridge/test_result_evidence.py","tests/test_bridge_executor_automation.py","tests/test_bridge.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

## Purpose

Implement only the P1.R1 validation-profile foundation locked by ADR-066.

The existing Bridge has one frozen compatibility profile:

```text
CONTROL_PLANE_STRICT_COMPAT
```

TASK-093 must add two explicit new identities:

```text
CONTROL_PLANE_STRICT
PRODUCT_DELIVERY_FAST
```

without implementing the capability batch or integration lane that will make the fast profile operational later.

The core design rule is:

```text
PROFILE IDENTITY != SILENT ALIAS
```

Historical compatibility evidence remains historically true. New profile identity must be explicit, machine-readable, deterministic, and fail-closed.

## 1. Closed Validation Profile Vocabulary

Extend the provider-neutral validation profile model so the exact closed vocabulary is:

```text
CONTROL_PLANE_STRICT_COMPAT
CONTROL_PLANE_STRICT
PRODUCT_DELIVERY_FAST
```

Unknown values MUST fail closed.

No free-form executor-selected profile is permitted.

Required identity invariants:

```text
CONTROL_PLANE_STRICT_COMPAT != CONTROL_PLANE_STRICT
CONTROL_PLANE_STRICT != PRODUCT_DELIVERY_FAST
CONTROL_PLANE_STRICT_COMPAT != PRODUCT_DELIVERY_FAST
```

Do not rename or remove the existing compatibility member.

## 2. Frozen Compatibility Behavior

`CONTROL_PLANE_STRICT_COMPAT` remains exactly the existing certified behavior for historical/compatibility artifacts:

```text
T0/T1 -> EXECUTOR
candidate-stage T2 -> 0 under Review-First
final T2 -> CERTIFICATION_BOUNDARY exactly once
expected full-suite count -> 1
full-canonical publication safety unchanged
```

Existing constant/API compatibility should remain available unless an equivalent backwards-compatible export is strictly required.

Historical tasks with a Lean roadmap binding but no explicit new profile marker MUST continue to resolve to `CONTROL_PLANE_STRICT_COMPAT` rather than being silently rewritten to `CONTROL_PLANE_STRICT`.

## 3. CONTROL_PLANE_STRICT Policy

Introduce an explicit strict plan/policy with persisted identity:

```text
profile_id = CONTROL_PLANE_STRICT
T0/T1 -> EXECUTOR
candidate-stage T2 -> 0 under Review-First
final T2 -> CERTIFICATION_BOUNDARY exactly once
expected full-suite count -> 1
diff check -> required
```

Its safety/ownership semantics are intentionally equivalent to the current strict compatibility behavior, but its profile identity is distinct for new P1 authoring.

Required:

```text
CONTROL_PLANE_STRICT_PLAN.profile_id == CONTROL_PLANE_STRICT
CONTROL_PLANE_STRICT_COMPAT_PLAN.profile_id == CONTROL_PLANE_STRICT_COMPAT
plans may share effective safety policy
plans MUST NOT collapse persisted identity
```

Review-First and certification helpers must operate correctly with both strict identities.

## 4. Explicit Profile Marker / Resolver

Add a deterministic top-level task profile marker for future tasks, equivalent to:

```text
VALIDATION_PROFILE: CONTROL_PLANE_STRICT
VALIDATION_PROFILE: PRODUCT_DELIVERY_FAST
```

Requirements:

```text
zero marker on Lean historical task -> CONTROL_PLANE_STRICT_COMPAT
exactly one CONTROL_PLANE_STRICT marker -> CONTROL_PLANE_STRICT plan
exactly one PRODUCT_DELIVERY_FAST marker -> recognized identity but fast execution admission remains blocked as described below
duplicate authoritative marker -> FAIL CLOSED
unknown profile value -> FAIL CLOSED
malformed/empty profile marker -> FAIL CLOSED
marker-like text inside fenced Markdown example -> MUST NOT create authority
```

Use deterministic parsing. Do not infer profile from title, changed paths, executor identity, prose, or model output.

If an existing shared top-level marker parser can be reused safely, reuse it rather than creating divergent Markdown-fence semantics.

## 5. PRODUCT_DELIVERY_FAST Foundation — Defined but Not Yet Executable

TASK-093 must make `PRODUCT_DELIVERY_FAST` a closed explicit profile identity and expose bounded policy metadata sufficient for later TASK-094/TASK-095 integration.

At minimum the policy must machine-represent these facts:

```text
TASK_LEVEL_T0_T1_REQUIRED: YES
TASK_LEVEL_REVIEW_FIRST_SEMANTIC_REVIEW_REQUIRED: YES
TASK_LEVEL_FINAL_T2: NO
CAPABILITY_LEVEL_FINAL_T2_REQUIRED: YES
DIFF_CHECK_REQUIRED: YES
KNOWN_IMPACT_REQUIRED: YES
DIRECT_TASK_MAIN_MERGE_ALLOWED: NO
CAPABILITY_BATCH_AUTHORITY_REQUIRED: YES
INTEGRATION_LANE_AUTHORITY_REQUIRED: YES
```

Exact field names may differ, but semantics must be closed and testable.

Crucially, TASK-093 MUST NOT make fast execution operational yet.

Until TASK-094/TASK-095 install exact batch/lane/capability certification authority:

```text
future task explicitly selects PRODUCT_DELIVERY_FAST
        ↓
profile identity is recognized
        ↓
normal executable ValidationPlan/admission resolution FAILS CLOSED
        ↓
reason identifies missing capability-batch/integration-lane authority
```

Do not silently fall back to compatibility or strict mode. Do not automatically switch profile.

A Human/Architect may later re-author a task under `CONTROL_PLANE_STRICT`; the executor cannot do that itself.

## 6. Conservative Impact Semantics

The fast profile policy must encode that deterministic `KNOWN` impact is required.

TASK-093 does not implement capability-task impact admission; TASK-095 will integrate that authority. This task only establishes the invariant so later code cannot interpret unknown impact as fast-lane eligible.

Required foundation behavior:

```text
PRODUCT_DELIVERY_FAST + impact UNKNOWN/ESCAPED/UNPROVEN
-> NOT FAST-ELIGIBLE
-> no silent strict fallback
-> no main authority
```

Do not duplicate Slice-C proof/impact machinery unless a small provider-neutral adapter is strictly necessary. Prefer reuse/compatibility with the existing bounded impact-confidence vocabulary.

## 7. Bridge / Executor Integration Boundary

Update only the minimum integration necessary so:

```text
future CONTROL_PLANE_STRICT task
-> launch plan carries CONTROL_PLANE_STRICT identity
-> Review-First candidate publication records CONTROL_PLANE_STRICT
-> candidate-stage AIOS-managed T2 remains 0
-> certify-reviewed still owns final T2 exactly once
```

For this TASK-093 bootstrap run, the launch/result profile remains `CONTROL_PLANE_STRICT_COMPAT` because the baseline parser/plan existed before TASK-093 implementation.

Do not change merge authority, certification-job identity, review lifecycle, roadmap validation, lease semantics, executor replacement semantics, or publication trust.

## 8. Required Targeted / Impact Proofs

At minimum add/adjust bounded tests proving:

```text
VALIDATION_PROFILE_VOCABULARY_CLOSED: PASS
COMPAT_PROFILE_IDENTITY_FROZEN: PASS
COMPAT_HISTORICAL_TASK_RESOLUTION_UNCHANGED: PASS
CONTROL_PLANE_STRICT_DISTINCT_IDENTITY: PASS
CONTROL_PLANE_STRICT_SINGLE_T2_POLICY: PASS
CONTROL_PLANE_STRICT_REVIEW_FIRST_CANDIDATE_T2_ZERO: PASS
CONTROL_PLANE_STRICT_FINAL_CERTIFICATION_T2_ONE: PASS
PROFILE_MARKER_EXACTLY_ONE: PASS
PROFILE_MARKER_UNKNOWN_FAILS_CLOSED: PASS
PROFILE_MARKER_DUPLICATE_FAILS_CLOSED: PASS
FENCED_PROFILE_MARKER_NON_AUTHORITATIVE: PASS
PRODUCT_DELIVERY_FAST_IDENTITY_CLOSED: PASS
PRODUCT_DELIVERY_FAST_POLICY_METADATA: PASS
PRODUCT_DELIVERY_FAST_NOT_EXECUTABLE_WITHOUT_BATCH_AUTHORITY: PASS
PRODUCT_DELIVERY_FAST_DOES_NOT_SILENTLY_FALLBACK_TO_STRICT: PASS
FAST_PROFILE_REQUIRES_KNOWN_IMPACT: PASS
FAST_PROFILE_DIRECT_MAIN_MERGE_ALLOWED: NO
RESULT_EVIDENCE_ACCEPTS_CONTROL_PLANE_STRICT_TOKEN: PASS
CODEX_ANTIGRAVITY_PROFILE_POLICY_PARITY: PASS
REVIEW_FIRST_PIPELINE_NOT_REGRESSED: PASS
TASK_087_WORKER_FAILURE_CLASSIFICATION_NOT_REGRESSED: PASS
AUTO_RETRY: NO
AUTO_REROUTE: NO
TASK_094_NOT_IMPLEMENTED: PASS
TASK_095_NOT_IMPLEMENTED: PASS
P1_FORMAL_COMPLETION: NO
P2_P3_NOT_OPENED: PASS
H5_H8_NOT_OPENED: PASS
```

Executor runs T0 / bounded targeted T1 / diff check only. Do not run full canonical T2 during RUN/FIX candidate publication.

## 9. Protected Existing Surfaces

Unless a deterministic integration requirement proves otherwise, do not redesign:

```text
roadmap governance
review lifecycle / Finding Registry
Slice-C FIX Context Pack / proof carry-forward
certification-job supersession
TASK-087 WorkerFailureEvidence and failure classification
blocked replacement semantics
lease acquisition/release
reviewed-head merge gate
capability batch/lane authority (not implemented yet)
```

If implementation discovers that P1.R1 cannot be safely completed without changing these authorities, stop and report the blocker rather than widening scope.

## 10. Explicit Out of Scope

```text
TASK-094 implementation
TASK-095 implementation
batch_id or batch manifest runtime
ai/capability/<batch-id> branch creation
integration lane state or gate
capability-level certification job
capability-level main merge gate
Python Agent fast-lane pilot
P1 completion declaration
persistent session / checkpoint / resume / suspension
parallel batch execution
automatic profile switching
automatic retry
automatic reroute
automatic rebase
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
  -> bridge.py certify-reviewed 93
      -> full canonical T2 exactly once for exact accepted candidate
  -> bridge.py merge-reviewed 93
```

No model polls deterministic certification.

## Acceptance

TASK-093 passes only if:

```text
P1_R1_VALIDATION_PROFILE_FOUNDATION: PASS
CONTROL_PLANE_STRICT: IMPLEMENTED
PRODUCT_DELIVERY_FAST: DEFINED_CLOSED_NOT_YET_EXECUTABLE
CONTROL_PLANE_STRICT_COMPAT: FROZEN_COMPATIBLE
HISTORICAL_PROFILE_IDENTITY_REWRITTEN: NO
FAST_PROFILE_AUTO_FALLBACK: NO
FAST_PROFILE_DIRECT_MAIN_MERGE: NO
REVIEW_FIRST_CERTIFICATION_PRESERVED: PASS
SLICE_C_FIX_PRESERVED: PASS
FINAL_T2_FOR_TASK_093: CERTIFICATION_BOUNDARY_EXACTLY_ONCE
TASK PASS != P1 COMPLETE
TASK_094_AUTHORIZED: NO
TASK_095_AUTHORIZED: NO
P2_P3_NOT_OPENED: PASS
H5_H8_NOT_OPENED: PASS
```
