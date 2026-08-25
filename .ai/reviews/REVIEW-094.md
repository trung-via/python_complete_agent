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

Candidate scope is bounded and useful. It adds only pure capability-batch/lane contracts and their tests; it does not alter Bridge execution, certification job, reviewed-head merge gate, or PRODUCT_DELIVERY_FAST end-to-end admission. The implementation is therefore preserved and reviewed rather than discarded.

The post-TASK-093 P0–P3 / Lean Review reconciliation audit found two semantic defects that prevent this candidate from satisfying P1.R2/P1.R3 as an operational foundation. Both defects are already inside TASK-094 authority and can be repaired without implementing TASK-095.

## B1 — OPEN — Fabricated Fast-Lane Review State Is Not Authoritative

### Finding

`integration_lane.py` requires the free-form string:

```text
SEMANTICALLY_ACCEPTED_PENDING_INTEGRATION
```

and tests manufacture the same string as successful review evidence.

The current authoritative Lean Review `ReviewState` does not contain that state; its semantic-acceptance state is `SEMANTICALLY_ACCEPTED_PENDING_T2`. Therefore TASK-094 currently treats a future, non-authoritative token as if it were a machine review-state authority.

This violates the task requirement that lane integration consume deterministic semantic-review evidence and the Lean invariant that machine-derived authority must have one authoritative source.

### Required repair

TASK-094 MUST NOT modify the canonical Lean Review state machine or implement TASK-095 profile-aware review routing. Instead, within current allowed scope, make the lane foundation consume bounded semantic-acceptance evidence supplied by a deterministic caller without inventing a new ReviewState token.

Equivalent acceptable contract:

```text
semantic_acceptance_valid: exact bool
reviewed_task_head_sha: exact SHA
reviewed head == current task branch head
semantic acceptance creates FINAL_PASS: NO
semantic acceptance creates main merge authority: NO
```

Exact field/class naming may differ.

Required properties:

```text
free-form review status cannot create lane authority
false/unknown/malformed semantic acceptance fails closed
reviewed head mismatch fails closed
lane advancement still creates no FINAL_PASS
lane advancement still creates no main merge authority
TASK-095 remains owner of future profile-aware ReviewState integration
```

Do not add `SEMANTICALLY_ACCEPTED_PENDING_INTEGRATION` to `review_pipeline.py` in this FIX; that file is outside TASK-094 allowed implementation scope and end-to-end state integration belongs to TASK-095.

### Required proofs

```text
NO_FABRICATED_FAST_REVIEW_STATE_AUTHORITY: PASS
SEMANTIC_ACCEPTANCE_FALSE_FAILS_CLOSED: PASS
SEMANTIC_ACCEPTANCE_MALFORMED_FAILS_CLOSED: PASS
REVIEWED_HEAD_MISMATCH_REJECTED: PASS
LANE_ADVANCE_FINAL_PASS_AUTHORITY: NO
LANE_ADVANCE_MAIN_MERGE_AUTHORITY: NO
```

## B2 — OPEN — Multi-Task Batch Membership Is Not Realizable Across Unknown Future Lane Heads

### Finding

`TaskMembershipBinding` currently requires every member to carry an exact `bound_lane_base_sha` at manifest construction, and the manifest requires every member's `membership_version` to equal the whole `manifest_version`.

This works for a one-task batch and for tests that pre-supply a synthetic second-task base SHA, but it does not implement the real P1.R2/P1.R3 sequence:

```text
TASK-A base = current lane head   -> known
TASK-A reviewed/integrated head   -> created later
TASK-B base = TASK-A integrated head -> not knowable when initial batch opens
```

The code has `require_valid_membership_revision()`, but a manifest revision changes the manifest fingerprint while the lane remains bound to the previous fingerprint. There is no deterministic lane-to-revised-manifest rebind contract. In addition, forcing all unchanged members to acquire the new manifest version would rewrite the identity of an already integrated prefix merely because a later task is added.

Therefore the candidate has not yet proven a realizable multi-task progressive batch.

### Required repair

Implement progressive authorized manifest revision and exact lane-manifest rebind within the existing pure modules.

Required semantics:

```text
manifest v1 admits TASK-A bound to exact current lane head
TASK-A integrates
manifest v2 preserves integrated TASK-A exactly and admits TASK-B bound to new current lane head
lane rebinds from manifest-v1 fingerprint to manifest-v2 fingerprint only through a pure fail-closed transition
TASK-B can then become the next task
```

Integrated prefix must be immutable across revisions:

```text
task_id unchanged
task artifact blob unchanged
scope fingerprint unchanged
expected branch unchanged
bound lane base unchanged
membership position unchanged
per-member authority version unchanged unless that member is separately re-authorized
```

Whole `manifest_version` and per-member `membership_version` MUST no longer be collapsed into the same meaning. An unchanged integrated member must not be rewritten solely because the manifest envelope advances.

A pure lane-manifest rebind must require at minimum:

```text
same batch/roadmap/capability/base-main/lane-ref identity
candidate manifest version == previous + 1
lane currently binds previous manifest fingerprint
integrated_task_ids exactly equal preserved immutable prefix
candidate preserves that prefix
next newly admitted member, when present, binds exact current lane head
lane head unchanged by rebind
integrated history unchanged by rebind
no FINAL_PASS / certification / main merge authority created
```

No Git command, rebase, merge, cherry-pick, squash, reset, automatic conflict resolution, executor membership mutation, or TASK-095 certification behavior may be added.

### Required proofs

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

The following Round-1 surfaces are accepted and should remain protected unless the FIX necessarily touches their exact subject/dependencies:

```text
A1 Capability batch and lane modules remain pure: no filesystem, Git, certification, or main-merge side effects.
A2 Closed batch/lane enums fail closed on malformed or authority-skipping transitions.
A3 Exact lowercase SHA/fingerprint validation and closed serialization remain intact.
A4 Batch membership never replaces independent TASK artifact/scope authority.
A5 Candidate task T2 remains 0 under Review-First.
A6 Impact confidence UNKNOWN is rejected for fast-lane integration evidence.
A7 Publication trust, scope validity, lease absence, main-base identity and fast-forwardability remain required deterministic facts.
A8 Lane advancement creates neither task FINAL_PASS nor main merge authority.
A9 PRODUCT_DELIVERY_FAST end-to-end admission remains blocked until TASK-095.
A10 CONTROL_PLANE_STRICT behavior from TASK-093 is not modified.
A11 P1 is not declared complete; P2/P3 and H5-H8 remain unopened.
```

## Delta + Impact Requirements For FIX

FIX should remain bounded primarily to:

```text
src/aios_bridge/capability_batch.py
src/aios_bridge/integration_lane.py
tests/aios_bridge/test_capability_batch.py
tests/aios_bridge/test_integration_lane.py
```

If deterministic impact analysis proves a required change in another TASK-094-allowed path, it may be touched only within the original task authority. Do not touch `src/aios_bridge/review_pipeline.py`; doing so would widen this FIX into TASK-095 semantics.

Required targeted test floor:

```text
pytest tests/aios_bridge/test_capability_batch.py -q
pytest tests/aios_bridge/test_integration_lane.py -q
```

If impact becomes UNKNOWN or escapes the bounded surfaces, expand to the fallback tests in `FIX_CONTEXT_PACK_JSON` and report the impact expansion. Candidate-stage AIOS-managed T2 must remain 0.

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

The review is bound to exact candidate `5a4a57fde7d9244799bde67d4f29eb91acd6eb2d` and base main `46a567bfd134fa0737ac0b93058ef1cd93d386ee`. Any candidate-head or base-main drift supersedes this review subject. Full canonical T2 is forbidden until both blockers are closed by semantic review.
