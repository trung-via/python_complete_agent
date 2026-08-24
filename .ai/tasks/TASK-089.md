# TASK-089 — Lean Review Deterministic Contract Foundation

STATUS: READY
PUBLISHER_PROFILE: CANONICAL_E4
CLASS: L2 — AIOS BRIDGE LEAN EXECUTION / P1 LEAN REVIEW FOUNDATION
MILESTONE: P1
CAPABILITY_ID: P1_UNIFIED_VALIDATION_CAPABILITY_BATCH
EXECUTOR_MODE: DUAL_EXECUTOR_ALLOWED
RECOMMENDED_EXECUTOR: antigravity
PAID_API_CALL_ALLOWED: NO
AUTO_RETRY_ALLOWED: NO
AUTO_REROUTE_ALLOWED: NO
IMPLEMENTATION_REFINEMENT_ADR: ADR-064
DECOMPOSITION_ADR: ADR-065
TASK_087_REMAINS_RESERVED: YES
P2_P3_AUTHORIZED: NO
H5_H8_AUTHORIZED: NO

ROADMAP_BINDING_JSON: {"roadmap_id":"AIOS-BRIDGE-LEAN-EXECUTION","roadmap_version":"1.2","roadmap_blob_sha":"41bf467f3dd4fc8aea165ac65c37e0e2a5a3ef5c","roadmap_fingerprint":"89c9372c074ecb43778705f07c6fded67e4af7833c0feb72a92a9ae2e737c612","roadmap_fingerprint_algorithm_version":"roadmap-sha256-v1","milestone":"P1","capability_id":"P1_UNIFIED_VALIDATION_CAPABILITY_BATCH","requirement_bindings":["P1.R6","P1.R7","P1.R8","P1.R9"],"scope_in":["pure deterministic Lean Review lifecycle contracts","machine-readable finding lifecycle foundation","machine-readable proof validity/fingerprint foundation","bounded deterministic review-risk classification foundation","provider-neutral certification-job state and exact candidate binding","superseded state prevents stale review/certification authority","no-model-polling invariant represented at the deterministic certification boundary"],"scope_out":["cutover of existing Bridge publish/review ordering","running T2 after semantic acceptance in production flow","actual background or asynchronous job runner","FIX proof carry-forward integration into Bridge","dependency impact engine","delta review orchestration","FIX context-pack integration","compact RESULT cutover","guardrail promotion integration","TASK-087 implementation","P1 capability batch container or integration lane","Python Agent fast-lane pilot","P2 persistent sessions checkpoint resume shell interception or capacity suspension","P3 Claude transport or adaptive routing","automatic retry or automatic reroute","H5-H8 implementation"]}

## Baseline

```text
MAIN_SHA: 90b381d3be78b68a8e7b25c42c66e539486a44e2
TARGET_BRANCH: ai/task-089
TASK_086: PASS_MERGED
ROADMAP_V1_2: LOCKED_REGISTERED
ADR_064_ACTIVATION_GATE: SATISFIED
TASK_087: RESERVED_NOT_EXECUTED
P1_FORMAL_COMPLETION: NO
P2_P3_STATUS: NOT_AUTHORIZED
H5_H8_STATUS: NOT_AUTHORIZED
```

## Machine-Readable E4 Inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.2.md","blob_sha":"41bf467f3dd4fc8aea165ac65c37e0e2a5a3ef5c"},{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.2.completions.json","blob_sha":"6b5fb5f99ec17cacca632e3b7a1953131b82c9b7"},{"path":".ai/roadmaps/CANONICAL-ROADMAP-REGISTRY-v1.json","blob_sha":"09180853439a383bb459094cb96fa2bd705afdd4"},{"path":".ai/decisions/ADR-064-AIOS-LEAN-REVIEW-PIPELINE-CONTROLLED-EVOLUTION.md","blob_sha":"af3581e47d010cd52014a7d7352bb10f6e8b21bb"},{"path":".ai/decisions/ADR-065-AIOS-LEAN-REVIEW-PIPELINE-ACTIVATION-BOUNDED-SLICES.md","blob_sha":"947b3ec5b63ddd628838a533822e37499a837a74"},{"path":".ai/reviews/REVIEW-086.md","blob_sha":"4e3d0258755e52536a5125d7a4eebbba88546483"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["src/aios_bridge/review_pipeline.py","src/aios_bridge/certification_job.py","tests/aios_bridge/test_review_pipeline.py","tests/aios_bridge/test_certification_job.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

## Purpose

Create the small provider-neutral deterministic contract foundation required by ADR-064 before changing the live Bridge review/certification flow.

This task is intentionally a foundation slice. It MUST NOT cut over publication, change T2 ownership, or implement TASK-087. The next Lean Review integration task will be authored only after TASK-089 PASS/merge and will bind that exact new main.

## 1. Closed Review Lifecycle

Create `src/aios_bridge/review_pipeline.py` with a closed review lifecycle sufficient to distinguish semantic judgment from final certification authority.

Required minimum states, exact names may be used directly:

```text
READY_FOR_SEMANTIC_REVIEW
CHANGES_REQUIRED
SEMANTICALLY_ACCEPTED_PENDING_T2
CERTIFICATION_RUNNING
CERTIFIED
FINAL_PASS
SUPERSEDED
```

Required invariants:

```text
SEMANTICALLY_ACCEPTED_PENDING_T2 != FINAL_PASS
SEMANTIC_ACCEPTANCE_CREATES_MERGE_AUTHORITY: NO
FINAL_PASS_REQUIRES_CERTIFIED_STATE: YES
SUPERSEDED_CAN_REACH_FINAL_PASS: NO
INVALID_TRANSITION: FAIL_CLOSED
STATE_TRANSITION_FUNCTIONS: PURE_DETERMINISTIC
```

Do not call Git, filesystem, network, model, executor, tests, or Bridge commands from these state transition functions.

## 2. Finding Lifecycle Registry Contract

Define immutable machine-readable finding objects and a closed status vocabulary.

Minimum states:

```text
NEW
OPEN
FIX_SUBMITTED
VERIFYING
CLOSED
REOPENED
```

Each finding must bind at minimum:

```text
finding_id
introduced_review_round
severity
affected_surfaces
status
fixed_by_sha optional
required_proof_ids
closure_review_round optional
```

Rules:

```text
CLOSED_REOPEN_REQUIRES_EXPLICIT_EVIDENCE_SIGNAL: YES
CLOSED_DOES_NOT_REOPEN_BY_DEFAULT: YES
INVALID_STATUS_TRANSITION: FAIL_CLOSED
DUPLICATE_AFFECTED_SURFACE: REJECT
DUPLICATE_REQUIRED_PROOF_ID: REJECT
```

This task defines registry/state contracts only; persistence/orchestration is out of scope.

## 3. Proof Carry-Forward Contract Foundation

Define immutable proof records sufficient for later FIX invalidation integration.

Minimum fields:

```text
proof_id
subject
subject_fingerprint
dependency_fingerprint
evidence_fingerprint
source_review_round
status = VALID | INVALIDATED | NEW
```

Required pure decision semantics:

```text
same subject fingerprint + same dependency fingerprint + VALID
    -> CARRY_FORWARD_ALLOWED
subject changed
    -> INVALIDATE
dependency changed
    -> INVALIDATE
status NEW or INVALIDATED
    -> CARRY_FORWARD_FORBIDDEN
unknown/malformed fingerprint
    -> FAIL_CLOSED
```

Do not implement a dependency graph in this task.

## 4. Risk-Adaptive Review Contract Foundation

Define a bounded deterministic risk evidence object and closed review effort classes:

```text
FAST
STANDARD
DEEP
CRITICAL_SECOND_REVIEW
```

Risk evidence must be finite/bounded and may represent:

```text
task class
changed path classes / bounded path facts
dependency blast-radius class
public API or contract impact
authority/security impact
schema/storage impact
test infrastructure impact
roadmap/control-plane criticality
impact confidence known/unknown
```

Required rules:

```text
AUTHORITY_OR_SECURITY_CRITICAL -> CRITICAL_SECOND_REVIEW
UNKNOWN_HIGH_IMPACT -> DEEP or stronger
LOW_BOUNDED_NON_CRITICAL -> FAST allowed
ROUTER_IS_PURE_DETERMINISTIC: YES
MODEL_SELF_SELECTS_REVIEW_EFFORT: NO
```

Do not build a full dependency-impact engine in this task.

## 5. Provider-Neutral Certification Job Contract

Create `src/aios_bridge/certification_job.py` with immutable deterministic certification-job state.

Minimum lifecycle:

```text
CERTIFICATION_PENDING
CERTIFICATION_RUNNING
CERTIFICATION_PASS
CERTIFICATION_FAILED
SUPERSEDED
```

Minimum binding:

```text
job_id
task_id
candidate_head_sha
candidate_fingerprint
validation_profile
certification_command_identity
status
started_at optional
terminal_result_digest optional
```

Required invariants:

```text
EXACT_CANDIDATE_HEAD_BINDING: YES
EXACT_CANDIDATE_FINGERPRINT_BINDING: YES
PROVIDER_SPECIFIC_EXECUTOR_FIELD_REQUIRED: NO
SUPERSEDED_JOB_CREATES_AUTHORITY: NO
SUPERSEDED_JOB_CAN_PASS: NO
TERMINAL_STATE_REENTRY: FAIL_CLOSED
MACHINE_WAIT_OWNER: CERTIFICATION_BOUNDARY
MODEL_POLL_REQUIRED: NO
```

This task MUST NOT implement an asynchronous/background service. It defines the job/state contract that the next integration slice will use. No hidden background work is authorized.

## 6. No Model Polling Contract

Represent the invariant so later integration cannot require repeated LLM/executor completion-check turns as a normal wait mechanism.

Required proof:

```text
LONG_RUNNING_DETERMINISTIC_WAIT_OWNER: CERTIFICATION_BOUNDARY
MODEL_COMPLETION_POLLING: NOT_REQUIRED
EXECUTOR_COMPLETION_POLLING: NOT_REQUIRED
ANTIGRAVITY_SPECIFIC_SEMANTICS: NO
CODEX_SPECIFIC_SEMANTICS: NO
FUTURE_EXECUTOR_COMPATIBLE: YES
```

The implementation may express this through a closed owner enum/property/validation contract rather than adding runtime polling code.

## 7. Required Targeted Tests

Add focused tests only for the new pure contracts.

Required proofs:

```text
REVIEW_STATE_MACHINE_CLOSED: PASS
SEMANTIC_ACCEPTANCE_NON_AUTHORITATIVE: PASS
FINAL_PASS_REQUIRES_CERTIFICATION: PASS
SUPERSEDED_REVIEW_FAILS_CLOSED: PASS
FINDING_LIFECYCLE_CLOSED: PASS
CLOSED_FINDING_STAYS_CLOSED_WITHOUT_REOPEN_EVIDENCE: PASS
PROOF_RECORD_FINGERPRINT_BOUND: PASS
UNCHANGED_VALID_PROOF_CARRY_FORWARD_ALLOWED: PASS
CHANGED_SUBJECT_INVALIDATES_PROOF: PASS
CHANGED_DEPENDENCY_INVALIDATES_PROOF: PASS
MALFORMED_PROOF_FAILS_CLOSED: PASS
RISK_REVIEW_CLASSES_CLOSED: PASS
RISK_ROUTER_DETERMINISTIC: PASS
CRITICAL_AUTHORITY_SECURITY_ESCALATES: PASS
UNKNOWN_HIGH_IMPACT_FAILS_CONSERVATIVE: PASS
CERTIFICATION_JOB_STATE_MACHINE_CLOSED: PASS
CERTIFICATION_JOB_EXACT_CANDIDATE_BOUND: PASS
SUPERSEDED_CERTIFICATION_JOB_NON_AUTHORITATIVE: PASS
NO_MODEL_POLLING_CONTRACT_PROVIDER_NEUTRAL: PASS
NO_FILESYSTEM_GIT_NETWORK_MODEL_SIDE_EFFECTS: PASS
CURRENT_BRIDGE_PUBLICATION_FLOW_UNCHANGED: PASS
TASK_087_NOT_IMPLEMENTED: PASS
P2_P3_NOT_OPENED: PASS
H5_H8_NOT_OPENED: PASS
```

Executor runs targeted/impact tests for changed modules and a diff check. Existing certification boundary remains owner of the full canonical T2 exactly once for TASK-089 under the current live flow.

## 8. Explicit Out of Scope

```text
bridge.py behavior changes
worker_flow.py behavior changes
validation.py ownership changes
review_merge.py merge-authority changes
actual semantic-review orchestration
actual delayed T2 cutover
background daemon/service/thread for certification
polling loop implementation
GitHub Actions changes
FIX dependency impact graph
FIX proof persistence
finding persistence
compact RESULT migration
guardrail generation
TASK-087
P2/P3
H5-H8
```

## Certification

```text
VALIDATION_PROFILE: CONTROL_PLANE_STRICT_COMPAT
T2_OWNER: CERTIFICATION_BOUNDARY
FULL_REPOSITORY: .\venv\Scripts\python.exe -m pytest tests/ -q
AIOS_MANAGED_T2_EXPECTED: 1
```

## Acceptance

TASK-089 passes only if:

```text
LEAN_REVIEW_FOUNDATION: PASS
PURE_DETERMINISTIC_CONTRACTS: PASS
SEMANTIC_ACCEPTANCE_SEPARATED_FROM_FINAL_PASS: PASS
FINDING_REGISTRY_CONTRACT: PASS
PROOF_CARRY_FORWARD_CONTRACT: PASS
RISK_ADAPTIVE_REVIEW_CONTRACT: PASS
CERTIFICATION_JOB_CONTRACT: PASS
NO_MODEL_POLLING_PROVIDER_NEUTRAL_CONTRACT: PASS
LIVE_FLOW_CUTOVER: NO
CONTROL_PLANE_AUTHORITY_UNCHANGED: PASS
TASK_087_REMAINS_RESERVED: PASS
P1_COMPLETE: NO
P2_P3_NOT_OPENED: PASS
H5_H8_NOT_OPENED: PASS
```
