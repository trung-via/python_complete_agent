# ADR-067 — AIOS P0–P3 / Lean Review Reconciliation Contract

STATUS: ACCEPTED
AUTHORITY: HUMAN_APPROVED_IMPLEMENTATION_REFINEMENT
CHANGE_CLASS: IMPLEMENTATION_REFINEMENT
CANONICAL_REQUIREMENT_IDENTITY_CHANGED: NO
ROADMAP_MUTATION: NO
ROADMAP_ID: AIOS-BRIDGE-LEAN-EXECUTION
ROADMAP_VERSION: 1.2
ROADMAP_BLOB_SHA: 41bf467f3dd4fc8aea165ac65c37e0e2a5a3ef5c
ROADMAP_FINGERPRINT: 89c9372c074ecb43778705f07c6fded67e4af7833c0feb72a92a9ae2e737c612
BASE_MAIN_SHA: 46a567bfd134fa0737ac0b93058ef1cd93d386ee
TASK_093_STATUS: PASS_CERTIFIED_MERGED
TASK_094_CANDIDATE_HEAD: 5a4a57fde7d9244799bde67d4f29eb91acd6eb2d
TASK_094_CANDIDATE_DISPOSITION: PRESERVE_FOR_REVIEW_AND_RECONCILIATION_FIX
P1_FORMAL_COMPLETION: NO
P2_P3_AUTHORIZED: NO
H5_H8_AUTHORIZED: NO
AUTO_RETRY_ALLOWED: NO
AUTO_REROUTE_ALLOWED: NO

## Context

The canonical v1.1 roadmap already defined P1 capability batches, bounded integration lanes, capability-certified main state, deterministic impact validation, and the Python Agent pilot before Lean Review was introduced. Roadmap v1.2 then added Lean Review requirements P1.R6–P1.R10 as additive refinements and explicitly preserved P0, P2, and P3 semantics.

A post-TASK-093 reconciliation audit found that the roadmap direction remains coherent, but two implementation seams must be made explicit before PRODUCT_DELIVERY_FAST can become operational:

1. the existing Lean Review state machine is task-T2-oriented while fast-lane tasks require semantic acceptance followed by lane integration without task-level FINAL_PASS; and
2. a multi-task batch cannot safely pre-bind future task lane bases whose exact predecessor heads do not exist yet.

These are implementation-contract gaps, not new canonical capabilities. Therefore this ADR is an IMPLEMENTATION_REFINEMENT beneath locked roadmap v1.2. It does not change roadmap requirement identity, roadmap blob/fingerprint, milestone ordering, or P0–P3 goals.

## Decision Summary

```text
ROADMAP v1.2: KEEP LOCKED UNCHANGED
P0 SEMANTICS: PRESERVED
P1 INTENT: PRESERVED AND RECONCILED
P2 SEMANTICS: PRESERVED WITH IMPLEMENTATION BOUNDARIES
P3 SEMANTICS: PRESERVED WITH IMPLEMENTATION BOUNDARIES
TASK-094 CANDIDATE: KEEP; DO NOT CERTIFY/MERGE UNTIL REVIEW BLOCKERS CLOSE
```

## 1. Certification Subject Semantics

P0 requires exactly one owner for each validation tier. It does not require every task to be an independent T2 subject.

The reconciled subject rules are:

```text
CONTROL_PLANE_STRICT / CONTROL_PLANE_STRICT_COMPAT
  -> task candidate is the final certification subject
  -> semantic acceptance
  -> exact task-head T2 exactly once
  -> TASK FINAL_PASS
  -> existing reviewed-head main merge gate

PRODUCT_DELIVERY_FAST
  -> individual task candidate is NOT a final T2 subject
  -> task-local T0/T1 + semantic review
  -> bounded lane integration
  -> task remains NON-FINAL with respect to main
  -> exact final capability lane head becomes the T2 subject
  -> capability T2 exactly once
  -> capability-certified main merge authority
```

Invariant:

```text
FINAL_PASS_REQUIRES_EXACT_SUBJECT_T2: YES
FAST_TASK_LANE_INTEGRATION_IS_FINAL_PASS: NO
CAPABILITY_CERTIFICATION_SUBJECT: EXACT_FINAL_LANE_HEAD
```

This satisfies P1.R2/P1.R3 and P1.R6 simultaneously: an intermediate fast task never claims FINAL_PASS, while the final capability subject still requires exact-head T2.

## 2. Lean Review State / Fast-Lane Handoff Boundary

The current authoritative Lean Review `ReviewState` is task-T2-oriented. TASK-094 MUST NOT invent a future review state token and treat that free string as authority.

Until TASK-095 installs the end-to-end profile-aware review/lane integration surface, TASK-094 may only define a pure bounded lane-preflight evidence boundary equivalent to:

```text
semantic_acceptance_valid: exact bool supplied by deterministic caller
reviewed_task_head_sha: exact reviewed head
review_subject_matches_task: proven by exact binding/head evidence
review_creates_final_pass_authority: NO
review_creates_main_merge_authority: NO
```

Requirements:

```text
NO FABRICATED REVIEWSTATE TOKEN
NO FREE-FORM STRING AS SEMANTIC AUTHORITY
FALSE / UNKNOWN / MALFORMED ACCEPTANCE EVIDENCE -> FAIL CLOSED
REVIEWED HEAD MUST EXACTLY MATCH TASK BRANCH HEAD
LANE INTEGRATION MUST NOT DERIVE FINAL_PASS
```

TASK-095 owns the later deterministic mapping from the canonical Lean Review lifecycle plus `PRODUCT_DELIVERY_FAST` profile identity into lane-integration eligibility. If the canonical ReviewState enum requires a new profile-specific state, TASK-095 must add it with explicit profile-aware transition rules and regression tests; TASK-094 does not pre-authorize that code change.

## 3. Progressive Capability Membership

A real multi-task batch cannot require all future tasks to know their exact `bound_lane_base_sha` when the batch first opens, because each later base is the reviewed/integrated head of the previous task and does not yet exist.

Therefore initial P1 uses progressive, Human/Architect-authorized manifest revision.

Canonical shape:

```text
manifest v1
  -> admits TASK-A bound to current lane head
  -> TASK-A integrates

manifest v2
  -> preserves integrated TASK-A authority exactly
  -> admits TASK-B bound to the now-known current lane head
  -> deterministic lane-manifest rebind
  -> TASK-B integrates

manifest v3 ...
```

This is not executor self-expansion. Every membership revision remains an explicit authority artifact/version and no executor may add, remove, reorder, or widen membership on its own.

## 4. Integrated Prefix Immutability

Manifest evolution after lane work begins MUST preserve the already integrated prefix.

```text
INTEGRATED PREFIX
  -> task_id unchanged
  -> exact task artifact blob unchanged
  -> task scope fingerprint unchanged
  -> expected task branch unchanged
  -> bound lane base unchanged
  -> membership position unchanged
  -> per-member authority identity unchanged unless separately re-authorized
```

Forbidden:

```text
reorder integrated tasks
remove integrated tasks
silently rewrite integrated membership version
widen integrated task scope
change integrated task artifact identity
change prior lane-base binding
```

Only the unintegrated suffix may be added/revised under a new manifest version.

## 5. Manifest Version vs Membership Version

Whole-manifest version and per-member authority version are distinct concepts.

```text
manifest_version
  = version of the batch authority envelope

membership_version
  = version of that member's own authority binding
```

A manifest revision MUST NOT force every unchanged integrated member to acquire the new manifest version. An unchanged member preserves its own membership version. A newly added or explicitly revised unintegrated member receives an appropriate new member authority version bound to the current manifest revision.

This preserves Lean Review's proof-carry-forward principle: unchanged accepted authority is not invalidated merely because later batch authority is appended.

## 6. Deterministic Lane ↔ Manifest Rebind

TASK-094 must provide a pure fail-closed rebind contract for an authorized manifest revision.

A lane may rebind from previous manifest fingerprint to candidate manifest fingerprint only if all are true:

```text
same batch_id
same roadmap identity/fingerprint
same capability identity
same base_main_sha
same integration_lane_ref
candidate manifest_version == previous + 1
lane currently binds previous manifest fingerprint
integrated_task_ids exactly equal the immutable preserved prefix
candidate preserves that prefix exactly
candidate next admitted task, if any, binds exact current lane head
main/base drift policy remains satisfied
no lane head mutation during rebind
no certification/main-merge authority created
```

Rebind result may change only the manifest-fingerprint authority binding and any bounded lane metadata explicitly required by the new manifest. It MUST NOT synthesize commits, rebase, merge, cherry-pick, squash, reset, or alter integrated history.

## 7. Batch Closure / Capability Candidate

Before capability certification, batch membership must be explicitly frozen/closed by deterministic authority. The exact final manifest fingerprint and exact lane head together define the capability candidate subject.

```text
FROZEN MANIFEST FINGERPRINT
+ EXACT FINAL LANE HEAD
+ EXACT ROADMAP / BASE MAIN
= CAPABILITY CANDIDATE IDENTITY
```

TASK-094 may represent readiness only. TASK-095 owns capability T2 execution, CERTIFIED state creation, and capability main merge gate.

## 8. Impact / Lean Proof Reconciliation

P1.R4 and Lean Review P1.R7 are complementary:

```text
KNOWN impact
  -> invalidate/retest only affected task proofs/T1 perimeter

UNKNOWN / ESCAPED / authority-sensitive impact
  -> fast admission/integration fails closed
  -> no automatic profile switch
  -> Human/Architect may separately re-authorize CONTROL_PLANE_STRICT
```

Proof carry-forward is permitted only when subject and dependency fingerprints remain unchanged. Manifest revision alone must not invalidate an unchanged integrated prefix.

## 9. P2 Boundary With Lean Review

P2 remains future work and is not opened by this ADR. When implemented:

```text
SESSION CHECKPOINT != REVIEW PROOF
SESSION COMPLETE != TASK FINAL_PASS
SESSION RESUME != REVIEW REUSE AUTHORITY
SESSION / EXECUTOR NEVER OWNS T2
```

Capacity semantics precedence:

```text
recoverable CAPACITY_EXHAUSTED + safe checkpoint
  -> SESSION_SUSPENDED
  -> not CLEAN_TIMEOUT
  -> not DIRTY_TIMEOUT_RECOVERY_REQUIRED
```

Resume or cross-executor continuation still requires exact authority/provenance and creates no automatic retry/reroute.

## 10. P3 Boundary With Lean Review

P3 remains future work and is not opened by this ADR.

```text
REVIEW RISK CLASS
  -> controls semantic review effort only

EXECUTOR QUALITY / CAPACITY TELEMETRY
  -> advisory executor preference only

HUMAN
  -> retains executor replacement authority
```

Forbidden:

```text
HIGH_RISK -> automatic executor switch
LOW_QUOTA -> automatic reroute
review model preference -> executor authority
```

## 11. TASK-094 Candidate Disposition

Candidate `5a4a57fde7d9244799bde67d4f29eb91acd6eb2d` was produced under a valid TASK-094 artifact and remains useful provenance. It is not discarded and is not retroactively reinterpreted as PASS.

Required handling:

```text
candidate remains on ai/task-094
candidate T2 remains 0
semantic review may issue CHANGES_REQUIRED for reconciliation defects already within TASK-094's P1.R2/P1.R3 authority
FIX uses Delta + Impact
no certification before blocker closure
no merge before exact-candidate certification
```

Review repairs may narrow/clarify implementation but may not expand TASK-094 into TASK-095 capability certification/main-merge work.

## 12. Acceptance For Reconciliation

Before TASK-094 may become semantically accepted, tests must prove at minimum:

```text
NO_FABRICATED_FAST_REVIEW_STATE_AUTHORITY: PASS
SEMANTIC_ACCEPTANCE_EVIDENCE_FAILS_CLOSED: PASS
MULTI_TASK_PROGRESSIVE_MEMBERSHIP_REALIZABLE: PASS
INTEGRATED_PREFIX_IMMUTABLE: PASS
UNCHANGED_MEMBER_VERSION_PRESERVED: PASS
MANIFEST_REVISION_CHANGES_MANIFEST_FINGERPRINT: PASS
LANE_MANIFEST_REBIND_EXACT_AND_FAIL_CLOSED: PASS
NEXT_MEMBER_BINDS_CURRENT_LANE_HEAD: PASS
STALE_MANIFEST_CANNOT_ADVANCE_LANE: PASS
REBINDS_CREATE_NO_FINAL_PASS: PASS
REBINDS_CREATE_NO_MAIN_MERGE_AUTHORITY: PASS
PRODUCT_DELIVERY_FAST_END_TO_END_STILL_BLOCKED_UNTIL_TASK_095: PASS
P0_VALIDATION_OWNERSHIP_NOT_REGRESSED: PASS
LEAN_REVIEW_STRICT_TASK_FLOW_NOT_REGRESSED: PASS
TASK_087_FAILURE_CLASSIFICATION_NOT_REGRESSED: PASS
```

## Non-Negotiable Invariants

```text
ROADMAP_V1_2_UNCHANGED
CANONICAL_REQUIREMENT_IDENTITY_CHANGED: NO
NO_TASK_AUTHORITY_COLLAPSE
NO_EXECUTOR_MEMBERSHIP_MUTATION
NO_FREE_STRING_REVIEW_AUTHORITY
NO_INTERMEDIATE_FAST_TASK_FINAL_PASS
NO_DIRECT_FAST_TASK_MAIN_MERGE
NO_AUTO_RETRY
NO_AUTO_REROUTE
NO_AUTO_REBASE
NO_AUTO_CONFLICT_RESOLUTION
EXACT_HEAD / EXACT_FINGERPRINT BINDING
PUBLICATION_TRUST PRESERVED
LEASE SAFETY PRESERVED
HUMAN AUTHORITY PRESERVED
TASK PASS != P1 COMPLETE
P2_P3_NOT_OPENED
H5_H8_NOT_OPENED
```

## Decision

```text
P0_P3_LEAN_REVIEW_RECONCILIATION: ACCEPTED
ROADMAP_V1_3_REQUIRED_NOW: NO
TASK_094_CANDIDATE_REUSE: YES
TASK_094_CERTIFY_BEFORE_RECONCILIATION: NO
TASK_094_MERGE_BEFORE_RECONCILIATION: NO
TASK_095_PREAUTHORIZED: NO
```
