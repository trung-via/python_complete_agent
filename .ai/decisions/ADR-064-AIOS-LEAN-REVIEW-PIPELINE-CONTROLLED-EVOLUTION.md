# ADR-064 — AIOS Lean Review Pipeline Controlled Evolution

STATUS: APPROVED_PENDING_ACTIVATION
AUTHORITY: HUMAN_APPROVED_ARCHITECTURAL_REFINEMENT
ACTIVATION_GATE: TASK-086_PASS_AND_MERGED_TO_MAIN
CURRENT_CANONICAL_ROADMAP_REMAINS: AIOS-BRIDGE-LEAN-EXECUTION-v1.1
CURRENT_TASK_086_AUTHORITY_UNCHANGED: YES
RETROACTIVE_APPLICATION_TO_TASK_086: NO
SILENT_ROADMAP_DRIFT_ALLOWED: NO

## Decision

AIOS Engineering adopts a bounded Lean Review Pipeline refinement under the existing AIOS Bridge Lean Execution direction. The refinement is approved now but MUST NOT alter TASK-086 execution, review, certification, roadmap binding, or merge semantics while TASK-086 is active.

TASK-088 is already PASS and merged. TASK-086 is the final pre-activation bounded P1.0A task and remains governed by the current locked roadmap v1.1 contract. Activation occurs only after TASK-086 reaches PASS and is merged to main. At activation, the canonical roadmap must evolve through the existing Controlled Evolution mechanism; the locked roadmap/registry must not be silently edited in place.

## North-Star Alignment

The refinement optimizes:

```text
TIME_TO_TRUSTED_CAPABILITY
HUMAN_ATTENTION
MODEL_TOKEN_AND_QUOTA_COST
REWORK_COST
RECOVERY_COST
```

subject to unchanged authority safety, provenance, bounded risk, certified delivery, and deterministic merge safety.

## Approved Lean Review Pipeline

```text
EXECUTOR
  -> T0 / impacted T1 / diff check
  -> deterministic review preflight
  -> risk-sized semantic review
      -> CHANGES_REQUIRED -> FIX loop
      -> semantic acceptance -> deterministic T2 certification job exactly once
  -> final certification
  -> deterministic merge gate
  -> main
```

T2 remains mandatory before merge. Semantic acceptance alone never creates merge authority.

## Approved Core Refinements

### R1 — Review-First Certification

Run semantic review before final T2 certification. Do not spend a full canonical certification on a candidate that semantic review has already rejected.

Invariant:

```text
SEMANTIC_ACCEPTANCE != FINAL_PASS
FINAL_PASS_REQUIRES_T2_CERTIFICATION: YES
```

### R2 — Proof Carry-Forward

A previously accepted proof remains reusable only while its subject and dependency evidence remain unchanged.

Proof reuse must be machine-bound, not inferred from prose memory.

Minimum proof state:

```text
proof_id
subject_fingerprint
dependency_fingerprint
evidence_fingerprint
source_review_round
status = VALID | INVALIDATED | NEW
```

### R3 — Invalidation-Based Testing

FIX execution reruns only proofs/tests invalidated by the FIX delta plus a bounded impact perimeter.

```text
UNCHANGED_PROOF -> REUSE
KNOWN_IMPACT -> RETEST_AFFECTED
UNKNOWN_IMPACT -> FAIL_CONSERVATIVE_AND_EXPAND
```

Tests are not deleted merely because they passed previously. Final T2 still runs the full canonical suite exactly once before merge.

### R4 — Delta + Impact Review

Initial review performs a full semantic audit with a bounded one-pass blocker sweep. Later FIX rounds review:

```text
open finding closure
+ new FIX delta
+ impacted semantic envelope
+ regressions into previously accepted surfaces only when impact evidence requires reopening
```

Pure line-diff review is insufficient. Previously accepted surfaces remain closed unless affected or regressed.

## Approved Additional Refinements

### R5 — Finding Lifecycle Registry

Review findings become machine-readable lifecycle objects rather than prose-only history.

Minimum lifecycle:

```text
NEW -> OPEN -> FIX_SUBMITTED -> VERIFYING -> CLOSED
                              -> OPEN on failed verification
CLOSED -> REOPENED only on evidence-backed regression/impact
```

Each finding binds at minimum:

```text
finding_id
introduced_review_round
severity
affected_surfaces
status
fixed_by_sha
required_proofs
closure_review_round
```

The registry is the authoritative finding-state source; review prose is a derived view.

### R6 — Risk-Adaptive Review Effort

Semantic review effort is selected deterministically from bounded task/diff risk evidence, not by ad-hoc model preference.

Closed review classes:

```text
FAST
STANDARD
DEEP
CRITICAL_SECOND_REVIEW
```

Risk evidence may include:

```text
task class
changed paths
dependency blast radius
public API / contract impact
authority/security impact
schema/storage impact
test infrastructure impact
roadmap/control-plane criticality
```

Unknown or ambiguous high-impact risk fails conservatively toward the stronger review class.

### R7 — Review / Certification Supersession

Review and certification bind an exact candidate head/fingerprint.

If a newer candidate head supersedes the bound subject:

```text
old review/certification -> STALE/SUPERSEDED
old work must not gain authority
cancel/ignore obsolete work when infrastructure permits
```

Reviewed-head and merge-gate protections remain unchanged.

### R8 — Finding-to-Guardrail Promotion

Repeated or systemic findings may be promoted into durable engineering guardrails:

```text
regression test
static/lint rule
architecture invariant
task template rule
ADR/knowledge artifact
```

Promotion is bounded and evidence-driven. A single low-value/style finding must not automatically create permanent policy.

## Supporting Execution Optimizations

### FIX Context Pack

FIX executors should receive the minimum bounded authority-preserving context required to close current findings:

```text
task authority reference
previous reviewed head
open findings
allowed paths
accepted/protected surfaces
required impacted tests
roadmap binding identity/fingerprint
```

Do not reload unrelated historical context by default.

### Deterministic Review Preflight

Move deterministic facts out of semantic reviewer reasoning when machine-verifiable, including where applicable:

```text
scope/path checks
candidate/head identity
base/main identity
roadmap binding identity
branch lineage / merge-base facts
validation evidence presence
finding/proof state consistency
```

Principle:

```text
MACHINE_PROVES_FACTS
REVIEWER_EVALUATES_MEANING
```

### Compact Result Evidence

Primary RESULT artifacts should carry bounded structured evidence rather than large raw pytest/stdout dumps.

Retain at minimum:

```text
command identity/hash
exit code
passed/failed/skipped/warnings summary
duration
log/evidence digest
failure excerpt only when needed
```

Raw logs may remain separately available for forensics but are not the canonical review context by default.

### Single Source of Truth

Machine-derived facts such as test counts, durations, fingerprints, finding status, and candidate identity must have one authoritative structured source. Derived prose must not independently restate stale values as authority.

### Deterministic Certification Job / No Model Polling

Long-running deterministic certification/publication work MUST NOT require repeated LLM or executor reasoning turns to ask whether the work has completed.

Principle:

```text
MACHINE_WAITS_FOR_MACHINE
MODEL_DOES_NOT_POLL_DETERMINISTIC_WORK
```

After semantic acceptance, final certification is represented as a bounded machine-readable job bound to the exact candidate subject. Minimum job evidence:

```text
job_id
task_id
candidate_head_sha
candidate_fingerprint
validation_profile
certification_command_identity
status
started_at
terminal_result_digest
```

Closed minimum lifecycle:

```text
CERTIFICATION_PENDING
  -> CERTIFICATION_RUNNING
      -> CERTIFICATION_PASS
      -> CERTIFICATION_FAILED
      -> SUPERSEDED
```

Requirements:

```text
REPEATED_MODEL_COMPLETION_CHECKS: FORBIDDEN_AS_NORMAL_FLOW
T2_EXECUTION_OWNER: CERTIFICATION_BOUNDARY
T2_EXECUTION_COUNT: EXACTLY_ONCE_FOR_FINAL_CANDIDATE
JOB_SUBJECT_BINDING: EXACT_CANDIDATE_HEAD_OR_AUTHORIZED_FINGERPRINT
NEW_CANDIDATE_INVALIDATES_OLD_JOB_AUTHORITY: YES
OBSOLETE_JOB_CANCEL_OR_IGNORE_WHEN_POSSIBLE: YES
MODEL_TOKEN_SPEND_WHILE_WAITING_FOR_T2: NOT_REQUIRED
```

A deterministic runner may block internally on the process, receive completion from the process, or use bounded non-model event/status mechanics. The normal workflow must not consume repeated model turns for `check completion again` behavior.

This optimization does not weaken final T2, publication verification, reviewed-head binding, or merge safety. It only removes model participation from deterministic waiting.

## Non-Negotiable Invariants

The refinement MUST NOT weaken or bypass:

```text
canonical roadmap lock + controlled evolution
roadmap ID/version/blob/fingerprint binding
requirement binding
allowed-path/scope enforcement
executor authorization and lease safety
no silent authority escalation
no automatic retry/reroute unless separately authorized
reviewed-head binding
task-head drift detection
main/base/merge-base/fast-forward safety
final T2 full canonical certification exactly once before merge
fail-closed deterministic merge gate
TASK PASS != MILESTONE COMPLETE
Human authority over material roadmap/executor changes
```

## Activation / Sequencing

Current sequence is locked as:

```text
TASK-088 PASS + merged
  -> TASK-086 executes/reviews/FIXes under existing v1.1 contract
  -> TASK-086 PASS + merge to main
  -> activate ADR-064 through Controlled Evolution of AIOS-BRIDGE-LEAN-EXECUTION roadmap
  -> author next available bounded implementation task for Lean Review Pipeline
  -> implement/test/review/certify/merge refinement
  -> rebind TASK-087 to the post-refinement canonical main
  -> continue P1
```

ADR-064 MUST NOT retroactively reinterpret TASK-086 evidence or modify its currently active authority.

## Implementation Acceptance

The implementation phase is complete only when machine tests prove at minimum:

```text
REVIEW_FIRST_CERTIFICATION_ENFORCED: PASS
SEMANTIC_ACCEPTANCE_HAS_NO_MERGE_AUTHORITY: PASS
FINAL_T2_STILL_REQUIRED_EXACTLY_ONCE: PASS
PROOF_CARRY_FORWARD_FINGERPRINT_BOUND: PASS
AFFECTED_PROOF_INVALIDATION: PASS
UNKNOWN_IMPACT_FAILS_CONSERVATIVE: PASS
DELTA_IMPACT_REVIEW_STATE_MACHINE: PASS
FINDING_LIFECYCLE_MACHINE_READABLE: PASS
RISK_REVIEW_CLASS_DETERMINISTIC: PASS
CRITICAL_REVIEW_ESCALATION_BOUNDED: PASS
STALE_REVIEW_SUPERSEDED: PASS
STALE_CERTIFICATION_SUPERSEDED: PASS
GUARDRAIL_PROMOTION_BOUNDED: PASS
FIX_CONTEXT_PACK_BOUNDED: PASS
DETERMINISTIC_REVIEW_PREFLIGHT: PASS
COMPACT_RESULT_EVIDENCE: PASS
SINGLE_SOURCE_OF_TRUTH: PASS
DETERMINISTIC_CERTIFICATION_JOB_STATE: PASS
CERTIFICATION_JOB_BOUND_TO_EXACT_CANDIDATE: PASS
NO_MODEL_POLLING_FOR_LONG_RUNNING_T2: PASS
SUPERSEDED_CERTIFICATION_JOB_FAILS_CLOSED: PASS
ROADMAP_GOVERNANCE_PRESERVED: PASS
AUTHORITY_AND_LEASE_SEMANTICS_PRESERVED: PASS
REVIEWED_HEAD_AND_MERGE_GATE_PRESERVED: PASS
TASK_PASS_NOT_MILESTONE_COMPLETE: PASS
```

## Decision Summary

```text
LEAN_REVIEW_PIPELINE: APPROVED
PROOF_CARRY_FORWARD: APPROVED
INVALIDATION_BASED_TESTING: APPROVED
DELTA_IMPACT_REVIEW: APPROVED
FINDING_LIFECYCLE_REGISTRY: APPROVED
RISK_ADAPTIVE_REVIEW: APPROVED
REVIEW_SUPERSESSION: APPROVED
FINDING_TO_GUARDRAIL_PROMOTION: APPROVED
DETERMINISTIC_CERTIFICATION_JOB: APPROVED
NO_MODEL_POLLING_FOR_LONG_RUNNING_T2: APPROVED
ACTIVATE_BEFORE_TASK_086_MERGE: NO
ACTIVATE_AFTER_TASK_086_MERGE: YES
ROADMAP_CHANGE_PROTOCOL: CONTROLLED_EVOLUTION_REQUIRED
```
