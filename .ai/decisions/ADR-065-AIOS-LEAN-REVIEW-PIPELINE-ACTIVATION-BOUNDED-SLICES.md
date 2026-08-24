# ADR-065 — AIOS Lean Review Pipeline Activation & Bounded Implementation Slices

STATUS: ACCEPTED
CHANGE_CLASS: IMPLEMENTATION_REFINEMENT
HUMAN_APPROVED_SOURCE: ADR-064
ROADMAP_ID: AIOS-BRIDGE-LEAN-EXECUTION
ROADMAP_VERSION: 1.2
ACTIVATION_PREREQUISITE_TASK: TASK-086
ACTIVATION_PREREQUISITE_STATUS: PASS_MERGED
TASK_087_REMAINS_RESERVED: YES
P2_P3_AUTHORIZED: NO
H5_H8_AUTHORIZED: NO

## Context

TASK-086 reached PASS and merged to main at `90b381d3be78b68a8e7b25c42c66e539486a44e2`. This satisfies ADR-064's activation gate. Canonical roadmap v1.2 is the controlled successor of v1.1 and adds P1 Lean Review requirements without retroactively reinterpreting TASK-086.

ADR-064 is intentionally too broad to implement safely as one executor task. AIOS therefore activates the refinement through ordered bounded slices. Each slice is separately authorized, reviewed, certified, and merged before the next slice is bound to the new exact main.

## Decision

Implementation sequence:

```text
TASK-089 — Lean Review deterministic contract foundation
  -> review/certify/merge
  -> next exact-baseline slice: Review-First Certification + Certification Job integration
  -> review/certify/merge
  -> next exact-baseline slice: FIX Proof Carry-Forward + Invalidation + Delta/Impact Review
  -> review/certify/merge
  -> next exact-baseline slice: compact evidence + supersession + bounded guardrail promotion
  -> review/certify/merge
  -> rebind reserved TASK-087
```

Future slice task numbers are not pre-authorized here. They are allocated only after the preceding slice PASS/merge so every task binds the exact current main and exact current canonical artifacts.

## Slice A — TASK-089 Foundation

TASK-089 establishes deterministic pure contracts only. It does not cut over current Bridge publication/review ordering.

Required foundation:

```text
review lifecycle states with semantic acceptance separated from final PASS
machine-readable FindingRecord + closed finding lifecycle
machine-readable ProofRecord + VALID/INVALIDATED/NEW state
bounded deterministic review-risk classes and routing evidence
provider-neutral CertificationJob state bound to exact candidate identity
SUPERSEDED terminal/non-authoritative semantics
no-model-polling invariant represented at certification-job boundary
```

This slice must be small enough that existing v1.1-compatible certification behavior can safely validate it once after implementation.

## Slice B — Review-First Certification Integration

After Slice A merge, bind a new task to the exact new main. Integrate:

```text
executor T0/T1 + candidate publication
non-authoritative semantic review state
semantic acceptance -> deterministic certification job
T2 exactly once only for semantic-accepted exact candidate
final PASS only after certification
no repeated model polling while T2 runs
```

Current merge authority, reviewed-head binding, roadmap binding, lease, scope and fail-closed behavior remain unchanged.

## Slice C — FIX Proof Reuse

After Slice B merge, bind a new task implementing:

```text
Proof Carry-Forward
subject/dependency fingerprint validation
invalidation-based targeted testing
unknown-impact conservative expansion
FIX Context Pack
Delta + Impact Review
accepted-surface protection unless impact/regression reopens it
```

Tests are never deleted because earlier proof passed. Final T2 remains canonical certification for the final candidate.

## Slice D — Evidence & Learning Optimization

After Slice C merge, bind a final Lean Review implementation task for:

```text
compact RESULT evidence
single machine-readable source of truth
review/certification supersession integration
bounded finding-to-guardrail promotion
stale candidate cancellation/ignore semantics where infrastructure permits
```

## Non-Negotiable Invariants

```text
NO_SILENT_ROADMAP_DRIFT
NO_RETROACTIVE_TASK_086_REINTERPRETATION
NO_AUTO_RETRY
NO_AUTO_REROUTE
NO_AUTHORITY_ESCALATION
SEMANTIC_ACCEPTANCE_IS_NOT_FINAL_PASS
FINAL_T2_REQUIRED_FOR_FINAL_CANDIDATE
REVIEWED_HEAD_BINDING_PRESERVED
MERGE_GATE_PRESERVED
TASK_PASS != P1_COMPLETE
TASK_087_NOT_EXECUTED_UNTIL_LEAN_REVIEW_SLICES_COMPLETE
P2_P3_NOT_OPENED
H5_H8_NOT_OPENED
```

## Rationale

The decomposition follows AIOS Lean Execution itself: reduce executor ambiguity, keep context bounded, surface failures earlier, avoid long fragile tasks, and make every change independently reviewable and recoverable.
