# ADR-066 — AIOS P1 Capability Batch + Bounded Integration Lane Contract Lock

STATUS: ACCEPTED
CHANGE_CLASS: P1_IMPLEMENTATION_CONTRACT
HUMAN_APPROVED_SOURCE: USER_APPROVAL_2026-08-25
ROADMAP_ID: AIOS-BRIDGE-LEAN-EXECUTION
ROADMAP_VERSION: 1.2
ROADMAP_BLOB_SHA: 41bf467f3dd4fc8aea165ac65c37e0e2a5a3ef5c
ROADMAP_FINGERPRINT: 89c9372c074ecb43778705f07c6fded67e4af7833c0feb72a92a9ae2e737c612
BASE_MAIN_SHA: 12904cf867fe5c5fe5be901d94ece82e3523beca
TASK_087_STATUS: PASS_CERTIFIED_MERGED
LEAN_REVIEW_SLICES_A_D: COMPLETE
P1_FORMAL_COMPLETION: NO
P2_P3_AUTHORIZED: NO
H5_H8_AUTHORIZED: NO
DEFAULT_IMPLEMENTATION_EXECUTOR: codex
AUTO_RETRY_ALLOWED: NO
AUTO_REROUTE_ALLOWED: NO
ROADMAP_MUTATION: NO

## Context

Canonical roadmap v1.2 requires P1 to deliver five related capabilities before the Python Agent fast-lane pilot can be considered complete:

```text
P1.R1 explicit CONTROL_PLANE_STRICT and PRODUCT_DELIVERY_FAST validation profiles
P1.R2 multiple separately authorized tasks may belong to one capability batch
P1.R3 intermediate product work remains on a bounded integration lane; main receives only capability-certified state
P1.R4 deterministic impact evidence drives targeted validation and insufficient confidence falls back conservatively
P1.R5 Python Agent pilot measures Time-to-Trusted-Capability
```

TASK-087 has now passed, been certified, and merged to exact main `12904cf867fe5c5fe5be901d94ece82e3523beca`. The Lean Review A→D implementation is also on main. The remaining P1 work therefore moves from worker-failure control semantics to capability delivery semantics.

The existing Bridge currently exposes only the legacy compatibility validation profile `CONTROL_PLANE_STRICT_COMPAT`. It does not yet provide a capability-batch authority object, a bounded integration lane, or a capability-level certification/merge boundary. These semantics must be locked before executor implementation so a worker cannot invent authority rules while coding.

This ADR implements no code and does not modify canonical roadmap v1.2. It is a bounded implementation contract beneath the already-approved P1 requirements.

## Decision

P1 capability delivery is split into two distinct execution modes:

```text
CONTROL-PLANE WORK
  -> CONTROL_PLANE_STRICT
  -> task-local Review-First semantic acceptance
  -> task-local T2 certification
  -> existing reviewed-head main merge gate

PRODUCT CAPABILITY WORK
  -> PRODUCT_DELIVERY_FAST
  -> separately authorized task
  -> task-local T0/T1 + semantic review
  -> bounded integration-lane gate
  -> no main merge / no task FINAL_PASS yet
  -> next separately authorized task may build on exact lane head
  -> capability-level exact-head T2 certification
  -> capability-level main merge gate
```

The fast path reduces repeated full-repository certification only where bounded deterministic evidence makes that safe. It does not weaken Human authority, roadmap authority, task authority, scope enforcement, publication trust, review authority, lease safety, or final main-merge safety.

## 1. Closed Validation Profiles

P1 introduces these canonical authoring profiles:

```text
CONTROL_PLANE_STRICT
PRODUCT_DELIVERY_FAST
```

Existing `CONTROL_PLANE_STRICT_COMPAT` remains a frozen compatibility profile for already-authored artifacts and compatibility paths. It MUST NOT be silently rewritten, reinterpreted, or used as a generic alias that changes historical evidence.

Required compatibility behavior:

```text
legacy artifact explicitly says CONTROL_PLANE_STRICT_COMPAT
  -> preserve exact legacy evidence identity
  -> preserve existing strict T2 semantics
  -> no retroactive profile rewrite

new P1 control-plane task
  -> author CONTROL_PLANE_STRICT

new eligible product-batch task
  -> author PRODUCT_DELIVERY_FAST
```

If implementation needs an internal effective-policy mapping, the persisted/original profile identity and effective execution policy must remain distinguishable. No executor may choose or mutate its own validation profile.

### CONTROL_PLANE_STRICT admission

This profile is mandatory for changes touching or materially affecting control-plane authority, including at least:

```text
roadmap governance
task/review authoring authority
authorization or lease semantics
scope enforcement
publication trust
review lifecycle / review preflight
certification jobs
merge gates
capability-batch authority itself
integration-lane authority itself
provider/executor authority semantics
```

Lifecycle remains the existing Review-First flow:

```text
T0/T1 executor
-> semantic review
-> exact-candidate T2 at certification boundary
-> FINAL_PASS
-> existing main merge gate
```

### PRODUCT_DELIVERY_FAST admission

This profile is allowed only when all of the following are true:

```text
active Human-approved capability batch exists
exact task is separately authorized
exact task binds current integration-lane head
changed surfaces are product-capability surfaces allowed by the task/batch
no protected control-plane surface is touched
impact confidence is deterministically KNOWN and bounded
no authority-sensitive uncertainty is present
```

If eligibility cannot be proven, fail closed. The system MUST NOT automatically upgrade, downgrade, retry, reroute, or reinterpret the profile. A Human/Architect may separately re-authorize the work under `CONTROL_PLANE_STRICT` if full per-task certification is required.

## 2. Capability Batch Authority

A capability batch is a bounded machine-readable authority container. It groups tasks for one capability outcome but never collapses task authority.

Minimum immutable/versioned batch identity must include equivalent fields:

```text
batch_id
schema_version
roadmap_id / roadmap_version / roadmap_fingerprint
milestone
capability_id
base_main_sha
integration_lane_ref
current_integration_head_sha
batch_manifest_version / fingerprint
ordered task membership or approved membership set
status
```

Recommended closed lifecycle:

```text
OPEN
-> INTEGRATING
-> READY_FOR_CAPABILITY_CERTIFICATION
-> CERTIFICATION_PENDING
-> CERTIFIED
-> MERGED

failure / stale identity paths:
CERTIFICATION_FAILED
SUPERSEDED
RECOVERY_REQUIRED
```

Exact enum naming may differ in implementation, but semantics must remain closed and fail-conservative.

### Task authority remains independent

For every task in a batch:

```text
TASK artifact remains the implementation authority
TASK has its own exact blob SHA
TASK has its own allowed paths
TASK has its own executor lease
TASK has its own review findings and semantic review
TASK has its own exact candidate head
TASK cannot inherit implementation scope merely from batch membership
```

Batch authority may constrain a task further; it may never widen task authority silently.

Adding, removing, reordering, or replacing batch membership is a controlled authority change. No executor may mutate membership. The batch manifest must be versioned/fingerprinted so stale membership cannot gain certification authority.

## 3. Bounded Linear Integration Lane

Initial P1 implementation uses a deliberately linear integration lane rather than parallel merge topology.

Canonical shape:

```text
main @ base_main_sha
        |
        +-> ai/capability/<batch-id> @ lane_head_0
                |
                +-> TASK-A branch from exact lane_head_0
                      -> semantic acceptance
                      -> deterministic lane integration gate
                |
                +-> lane_head_1
                      |
                      +-> TASK-B branch from exact lane_head_1
                            -> semantic acceptance
                            -> deterministic lane integration gate
                |
                +-> lane_head_2 ...
```

The lane starts from exact `base_main_sha`. Each new fast-lane task MUST bind the exact current lane head before execution begins.

### Why linear first

```text
no hidden merge conflict resolution
no ambiguous ancestry
no automatic rebase
no cross-task scope collapse
simple exact-head provenance
fast-forward integration can be deterministic
```

Parallel capability branches, automatic conflict resolution, or DAG batch scheduling are outside P1 and require separate authority if ever desired.

## 4. Task-Level Fast-Lane Lifecycle

A `PRODUCT_DELIVERY_FAST` task follows:

```text
exact batch/lane binding
-> executor T0/T1 + diff/scope checks
-> Review-First candidate publication with candidate-stage T2 = 0
-> semantic review
-> CHANGES_REQUIRED -> Slice-C Delta+Impact FIX as today
-> SEMANTICALLY_ACCEPTED_PENDING_INTEGRATION
-> deterministic lane integration gate
-> INTEGRATED_PENDING_CAPABILITY_CERTIFICATION
```

Exact state names may differ, but these authority distinctions are mandatory.

A fast-lane task's semantic acceptance and lane integration are NON-FINAL with respect to main.

Forbidden before capability certification:

```text
TASK FINAL_PASS derived solely from lane integration
main merge authority
release authority
claim that P1 is complete
```

`TASK PASS != MILESTONE COMPLETE` remains true, and for fast-lane work the stronger rule applies:

```text
TASK SEMANTIC ACCEPTANCE != CAPABILITY CERTIFICATION
TASK LANE INTEGRATION != MAIN MERGE AUTHORITY
```

## 5. Deterministic Lane Integration Gate

A task may advance the lane only if deterministic preconditions all pass:

```text
batch status permits integration
batch manifest identity is current
roadmap identity/fingerprint is exact
review status is semantic acceptance for exact task head
reviewed task head == current task branch head
candidate publication T2 count == 0
required targeted/impact validation passed
impact confidence == KNOWN
publication trust is valid
scope / allowed paths are valid
no active/uncertain executor lease remains
current lane head == task's bound lane base SHA
main/base identity has not been silently rebound
```

Initial integration mechanism should prefer exact fast-forward lane advancement from the bound lane head to the reviewed task head. If ancestry is not exact, fail closed; do not auto merge, auto rebase, cherry-pick, squash, or conflict-resolve.

Successful lane integration creates only lane authority for the next task. It does not create main merge authority.

## 6. Main Drift During an Open Batch

A capability batch is bound to exact `base_main_sha`.

If `main` changes while a batch is open:

```text
NO SILENT REBASE
NO SILENT BASE UPDATE
NO AUTO MERGE OF MAIN INTO LANE
NO CERTIFICATION AGAINST AN UNDECLARED BASE
```

Capability certification/main merge must fail closed until a Human-approved rebind/rebase procedure is separately authorized. P1 implementation may initially require `main == base_main_sha` at final certification and merge time.

This conservative rule is acceptable for the initial single-operator workflow and avoids hidden provenance changes.

## 7. Capability-Level Certification Boundary

When the Human/Architect closes the batch membership and all required tasks are integrated, the exact lane head becomes the capability candidate.

Required lifecycle:

```text
freeze exact batch manifest/fingerprint
freeze exact lane head SHA
-> READY_FOR_CAPABILITY_CERTIFICATION
-> deterministic certification job
-> full canonical T2 on exact capability candidate
-> CERTIFIED only if T2 passes
```

Core invariant:

```text
FULL_CANONICAL_OWNER: CAPABILITY_CERTIFICATION_BOUNDARY
FINAL_CAPABILITY_CANDIDATE_T2_EXPECTED: 1
MODEL_POLLING: NO
```

The capability certification job must use the same exact-head supersession principles already implemented by Lean Review:

```text
new lane head after certification job creation -> old job SUPERSEDED
failed certification on exact head -> terminal for that exact head
no automatic retry of failed exact head
repair requires new separately authorized task / new lane head
new lane head may create a new certification job
```

A failed T2 preserves the lane and provenance. It creates no main merge authority.

## 8. Capability Main Merge Gate

Main receives only capability-certified state.

A capability merge is permitted only if all deterministic conditions pass, including:

```text
batch status == CERTIFIED
certification PASS binds exact current lane head
batch manifest/fingerprint matches certified identity
roadmap identity remains exact
main == batch.base_main_sha for initial P1 implementation
lane ancestry from base is exact and fast-forwardable
no stale/superseded certification
no active recovery/lease uncertainty
```

Then the capability merge gate may fast-forward `main` to the certified lane head.

Forbidden:

```text
individual PRODUCT_DELIVERY_FAST task merges directly to main
merge based only on semantic acceptance
merge based only on targeted T1
merge from stale lane head
merge that requires implicit conflict resolution
```

## 9. Deterministic Impact Evidence and Conservative Fallback

`PRODUCT_DELIVERY_FAST` depends on deterministic impact confidence.

Minimum semantics:

```text
KNOWN bounded impact
  -> task-level targeted T1 may support lane integration

UNKNOWN / ESCAPED / authority-sensitive impact
  -> fast-lane admission or integration fails closed
  -> no lane advancement based only on targeted evidence
  -> Human/Architect may explicitly re-authorize under CONTROL_PLANE_STRICT
  -> full exact-candidate certification occurs through the strict path
```

This explicit strict fallback satisfies the roadmap requirement that insufficient impact confidence cannot silently skip full certification. No automatic profile switching is permitted.

Future refinements may introduce additional capability-certification barriers inside a batch, but P1 initial implementation does not require them.

## 10. Python Agent Pilot Boundary

The Python Agent fast-lane pilot starts only after the profile, batch, lane, impact, capability-certification, and capability-merge contracts are implemented and certified on main.

Pilot must measure at least bounded comparable evidence for:

```text
Time-to-Trusted-Capability
number of executor T0/T1 runs
number and duration of full canonical T2 runs
semantic review rounds
FIX rounds
Human intervention count when observable
blocked/recovery events
executor identity
batch task count
```

The pilot measures whether P1 actually reduces delivery time/cost. It does not automatically authorize P2. P2 opens only if measured session/context/capacity cost remains material and Human explicitly authorizes it.

## 11. Executor Preference

For implementation tasks created under this ADR, default dispatch preference is:

```text
codex preference_rank = 0
antigravity preference_rank = 1
```

This is an operational preference, not automatic rerouting authority. If Codex becomes blocked, Bridge still follows the existing fail-closed classification and explicit-Human replacement rules. No quota state may silently change executor authority.

## 12. Planned Bounded Implementation Sequence

The approved implementation plan is:

```text
TASK-093 — Validation Profiles Foundation
  P1.R1
  CONTROL_PLANE_STRICT + PRODUCT_DELIVERY_FAST
  frozen compatibility behavior for CONTROL_PLANE_STRICT_COMPAT

TASK-094 — Capability Batch Authority + Linear Integration Lane
  P1.R2 + P1.R3
  batch manifest / exact lane binding / deterministic integration gate

TASK-095 — Impact Admission + Capability Certification + Capability Main Merge
  P1.R4 plus final batch certification/merge semantics

then
Python Agent fast-lane pilot
  P1.R5

then
P1 formal completion audit
```

The numbers identify the planned sequence but do NOT pre-authorize execution. Each task is authored only after the preceding task is certified/merged and must bind the then-current exact main and current canonical artifacts.

## 13. Non-Negotiable Invariants

```text
NO_ROADMAP_MUTATION
NO_SILENT_ROADMAP_DRIFT
NO_TASK_AUTHORITY_COLLAPSE_IN_BATCH
NO_EXECUTOR_SELF_SELECTION_OF_PROFILE
NO_AUTO_RETRY
NO_AUTO_REROUTE
NO_AUTO_REBASE
NO_AUTO_CONFLICT_RESOLUTION
NO_DIRECT_FAST_TASK_MAIN_MERGE
SEMANTIC_ACCEPTANCE_IS_NON_FINAL
LANE_INTEGRATION_IS_NON_FINAL
FINAL_MAIN_STATE_REQUIRES_CAPABILITY_CERTIFICATION
EXACT_HEAD_CERTIFICATION_BINDING
SUPERSESSION_PRESERVED
PUBLICATION_TRUST_PRESERVED
LEASE_SAFETY_PRESERVED
SCOPE_ENFORCEMENT_PRESERVED
HUMAN_EXECUTOR_REPLACEMENT_AUTHORITY_PRESERVED
TASK_PASS != P1_COMPLETE
P2_P3_NOT_OPENED
H5_H8_NOT_OPENED
```

## 14. Explicit Out of Scope

```text
persistent executor sessions
checkpoint/resume
capacity suspension
shell interception
parallel batch DAG execution
automatic rebase or conflict resolution
automatic cross-executor continuation
Claude Code integration
adaptive executor selection
P2
P3
H5-H8
canonical roadmap v1.3 mutation
Python Agent pilot implementation before TASK-093/094/095 complete
```

## Consequences

Positive:

- repeated full-suite certification can be removed from safe intermediate product tasks;
- task authority remains independent and auditable;
- final main state still receives full exact-head certification;
- linear integration keeps provenance simple and makes recovery bounded;
- Lean Review/Slice-C proof reuse can operate inside each task without weakening final capability trust;
- the Python Agent pilot can measure a real fast lane rather than a simulated optimization.

Trade-offs:

- initial batches are sequential rather than parallel;
- main drift during an open batch fails closed and may require explicit rebind work;
- uncertain impact cannot use the fast lane without explicit strict re-authorization;
- capability-level merge requires new deterministic authority surfaces rather than reusing task main-merge semantics incorrectly.

These trade-offs are intentional for P1. They minimize Time-to-Trusted-Capability while preserving bounded authority and provenance.