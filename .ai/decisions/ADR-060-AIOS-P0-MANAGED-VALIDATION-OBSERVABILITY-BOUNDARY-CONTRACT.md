# ADR-060 — AIOS P0 Managed Validation Observability Boundary Contract

STATUS: ACCEPTED
DECISION_TYPE: IMPLEMENTATION_REFINEMENT
HUMAN_APPROVED: YES
ROADMAP_ID: AIOS-BRIDGE-LEAN-EXECUTION
ROADMAP_VERSION: 1.1
MILESTONE: P0
CAPABILITY_ID: P0_VALIDATION_OWNERSHIP_TELEMETRY
CANONICAL_REQUIREMENT_IDENTITY_CHANGE: NO
SEMANTIC_CAPABILITY_CHANGE: NO
AUTHORITY_CHANGE: NO
SEQUENCING_CHANGE: NO
ROADMAP_VERSION_BUMP_REQUIRED: NO
P1_P3_AUTHORIZED: NO
H5_H8_AUTHORIZED: NO
AUTO_RETRY_CHANGE: NO
AUTO_REROUTE_CHANGE: NO
SHELL_INTERCEPTION_AUTHORIZED: NO
EXECUTOR_SESSION_CAPTURE_AUTHORIZED: NO

## Context

TASK-083 P0 introduced provider-neutral validation tiers, ownership, a `ValidationPlan`, and validation evidence. Review round 1 correctly identified that the first implementation could count the certification-boundary T2 execution but could not prove whether an executor independently ran an ad-hoc `pytest tests/ -q` inside its own runtime.

A subsequent Codex FIX was correctly authorized but produced `CLEAN_NO_WORKTREE_DELTA` because the requested repair implicitly required command-level observability across executor runtimes. The current Codex transport exposes bounded process/JSON-event diagnostics rather than a complete shell-command event stream, and Antigravity interactive execution is not mediated by Bridge shell interception.

Requiring P0 to intercept every executor shell command would expand the work into executor-session/command mediation that belongs to the later provider-neutral session architecture. That would violate the Lean Execution sequencing rule to remove measured validation overhead before building P2 infrastructure.

## Decision

P0 validation observability is explicitly split into two evidence domains:

```text
AIOS_MANAGED_VALIDATION
EXECUTOR_AD_HOC_VALIDATION
```

### 1. AIOS-managed validation

AIOS-managed validation is any validation command/event directly scheduled, owned, or invoked by Bridge/AIOS certification logic.

P0 MUST guarantee:

```text
T0/T1_OWNER: EXECUTOR
T2_OWNER: CERTIFICATION_BOUNDARY
T3_OWNER: RELEASE_BOUNDARY
EXPECTED_AIOS_MANAGED_T2_EXECUTION_COUNT: 1
AIOS_MANAGED_T2_EXECUTION_COUNT: 1
AIOS_MANAGED_T2_DUPLICATION_DETECTED: NO
```

Bridge/AIOS MUST NOT schedule a second T2 when the certification boundary already owns T2. Any AIOS-controlled executor validation command list must apply the bound `ValidationPlan` and exclude T2 from the executor-owned validation set.

### 2. Executor ad-hoc validation

Executor ad-hoc validation means shell/test commands independently initiated inside an executor runtime outside an AIOS-observed validation event stream.

P0 MUST report observability honestly:

```text
EXECUTOR_AD_HOC_T2_OBSERVABILITY: OBSERVED | UNAVAILABLE
EXECUTOR_AD_HOC_T2_EXECUTION_COUNT: <non-negative integer> | UNKNOWN
GLOBAL_T2_EXECUTION_COUNT: <non-negative integer> | UNKNOWN
```

Rules:

```text
UNAVAILABLE -> count MUST be UNKNOWN, never fabricated as 0 or 1
OBSERVED -> observed count MUST be persisted
OBSERVED executor-side T2 while certification owns T2 -> validation policy violation
UNKNOWN global count MUST NOT be presented as exact actual count
```

Lack of ad-hoc command observability alone does not fail P0 publication when AIOS-managed ownership/count is proven and the unavailable boundary is explicitly recorded. P0 must never convert unavailable observability into a false deduplication claim.

## Interpretation of P0.R3 / P0.R4

The existing Lean Execution v1.1 requirement identities remain unchanged.

`P0.R3` is interpreted as requiring elimination and machine observability of duplicate **AIOS-managed** full-canonical scheduling, plus explicit observability status for executor ad-hoc T2.

`P0.R4` requires telemetry to preserve the measurement scope so reviewers can distinguish exact AIOS-managed counts from unavailable executor-ad-hoc/global counts.

This is an implementation/measurement-boundary clarification, not a roadmap capability change, authority change, milestone reorder, or requirement identity change. Therefore Lean Execution roadmap v1.1 remains canonical and no roadmap version bump is required.

## Required RESULT Evidence

For P0-governed publication, RESULT-N must persist machine-readable evidence equivalent to:

```text
VALIDATION_PROFILE: CONTROL_PLANE_STRICT_COMPAT
FULL_CANONICAL_OWNER: CERTIFICATION_BOUNDARY
EXPECTED_AIOS_MANAGED_T2_EXECUTION_COUNT: 1
AIOS_MANAGED_T2_EXECUTION_COUNT: 1
AIOS_MANAGED_T2_DUPLICATION_DETECTED: NO
EXECUTOR_AD_HOC_T2_OBSERVABILITY: OBSERVED | UNAVAILABLE
EXECUTOR_AD_HOC_T2_EXECUTION_COUNT: <n> | UNKNOWN
GLOBAL_T2_EXECUTION_COUNT: <n> | UNKNOWN
TARGETED_TEST_EXECUTION_COUNT: <n> | UNKNOWN
FULL_SUITE_DURATION_SECONDS: <observed> | UNKNOWN
TARGETED_TEST_DURATION_SECONDS: <observed> | UNKNOWN
```

Legacy field names may be retained for compatibility only if their evidence scope is explicit and cannot be mistaken for global executor-observed counts.

## P0 Acceptance Boundary

TASK-083 may PASS without shell interception if all of the following are proven:

```text
VALIDATION_PLAN_BOUND_TO_AUTHORIZATION: PASS
AIOS_CONTROLLED_EXECUTOR_T2_FILTERING: PASS
CERTIFICATION_T2_PRESERVED: PASS
EXPECTED_AIOS_MANAGED_T2_EXECUTION_COUNT: 1
AIOS_MANAGED_T2_EXECUTION_COUNT: 1
AIOS_MANAGED_T2_DUPLICATION_DETECTED: NO
EXECUTOR_AD_HOC_T2_OBSERVABILITY: EXPLICIT
GLOBAL_COUNT_NOT_FABRICATED: PASS
RESULT_EVIDENCE_PERSISTED: PASS
CODEX_ANTIGRAVITY_VALIDATION_POLICY_PARITY: PASS
```

If command-level observability later becomes available, observed executor-side T2 can be incorporated without changing the validation ownership model.

## Explicitly Deferred

The following are NOT authorized by P0 or this ADR:

```text
shell-command interception
terminal proxying
full command event capture
persistent Codex/Claude sessions
Antigravity shell mediation
checkpoint/resume
capacity suspension/resume
adaptive routing
Claude transport implementation
P1 capability batching
H5-H8 work
```

If P1 telemetry later proves executor ad-hoc validation is a material TTTC/overhead problem, P2 may propose bounded command/session observability under a separate Human-approved task/ADR.

## Failed FIX Attempt Classification

The Codex FIX attempt following REVIEW-083 round 1 that ended with `CLEAN_NO_WORKTREE_DELTA` created no implementation delta and no publication. It is classified as a blocked pre-publication execution attempt, not a completed FIX round and not evidence of executor failure.

## Invariants Preserved

```text
TASK_AUTHORITY: UNCHANGED
ROADMAP_AUTHORITY: UNCHANGED
REVIEW_AUTHORITY: UNCHANGED
LEASE_SEMANTICS: UNCHANGED
SCOPE_ENFORCEMENT: UNCHANGED
PUBLICATION_TRUST: UNCHANGED
REVIEWED_HEAD_MERGE_SAFETY: UNCHANGED
AUTO_RETRY: NO
AUTO_REROUTE: NO
H5_H8_OPENED: NO
```
