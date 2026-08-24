# REVIEW-083 — P0 Validation Ownership + Telemetry Foundation
PUBLISHER_PROFILE: CANONICAL_E4

STATUS: CHANGES_REQUIRED
APPROVED: NO
AUTO_MERGE_ELIGIBLE: NO
MERGE_AUTHORIZED: NO
MERGED_TO_MAIN: NO

TASK_ID: TASK-083
REVIEW_ROUND: 1
REVIEW_REVISION: ADR-060_OBSERVABILITY_BOUNDARY
REVIEWED_TASK_HEAD_SHA: 0c9c5f9fe5789fd56162c0786e4f8f90ef785bb0
REVIEWED_BASE_MAIN_SHA: 962712450ce14d3629c3d1caef59c9651bba7f90
TASK_ARTIFACT_BLOB_SHA: 15eaa9985f0b522a1ad1a9325bd2674a4e593ccc
RESULT_BLOB_SHA: e24c6240541623aa95549269a64172436d5523fd
EXECUTOR_ID: codex
BLOCKERS_REMAINING: 1
CODE_AUDIT: CHANGES_REQUIRED
CANONICAL_TESTS: PASS_REPORTED
ROADMAP_AUDIT: PASS
ROADMAP_ID: AIOS-BRIDGE-LEAN-EXECUTION
ROADMAP_VERSION: 1.1
ROADMAP_BLOB_SHA: cae51de4db517dd452c260076a1daa521c1e3a4c
ROADMAP_FINGERPRINT: 4bcbb10e1e8e02169ccb5a516801abd1ce01b0b5edd348d90abcac7d0887404f
MILESTONE: P0
CAPABILITY_ID: P0_VALIDATION_OWNERSHIP_TELEMETRY
REFINEMENT_ADR: ADR-060
P0_FORMAL_COMPLETION: NO
P1_P3_AUTHORIZED: NO
H5_H8_AUTHORIZED: NO

## Reviewed Snapshot

```text
BRANCH: ai/task-083
BASE_MAIN_SHA: 962712450ce14d3629c3d1caef59c9651bba7f90
REVIEWED_TASK_HEAD_SHA: 0c9c5f9fe5789fd56162c0786e4f8f90ef785bb0
STATUS_VS_BASE: AHEAD
AHEAD_BY: 1
BEHIND_BY: 0
MERGE_BASE_SHA: 962712450ce14d3629c3d1caef59c9651bba7f90
CUMULATIVE_SCOPE: EXACT
```

Reported canonical certification evidence remains:

```text
FULL_REPOSITORY_TESTS: 2549 passed, 7 skipped, 0 failed
FULL_REPOSITORY_DURATION: 335.42s
E4_TRANSPORT_STATUS: EXITED_ZERO
E4_ALLOWED_SCOPE_VERIFIED: PASS
E4_PUBLICATION_TRUST_VERIFIED: PASS
```

## Controlled Refinement — ADR-060

Human-approved ADR-060 clarifies the P0 measurement boundary without changing Lean Execution roadmap v1.1 requirement identities, capability, authority, or sequencing.

P0 distinguishes:

```text
AIOS_MANAGED_VALIDATION
EXECUTOR_AD_HOC_VALIDATION
```

P0 must prove exact ownership/count for validation directly scheduled or invoked by AIOS. It must not claim exact global executor validation counts when the current executor transport/session cannot observe ad-hoc shell commands.

The prior requested shell-level global proof is therefore withdrawn. Shell interception, terminal proxying, persistent session command capture, and Antigravity shell mediation are not authorized in P0.

The Codex FIX attempt that ended `CLEAN_NO_WORKTREE_DELTA` created no implementation delta and no publication. It is a blocked pre-publication attempt, not a completed FIX round.

## Finding B1 — AIOS-managed T2 deduplication and honest scoped telemetry are incomplete

STATUS: BLOCKING
SEVERITY: VALIDATION_INTEGRITY

The reviewed implementation has the correct validation tier/owner model and a handoff-bound `ValidationPlan`, but RESULT/publication evidence does not yet distinguish exact AIOS-managed counts from executor ad-hoc observability.

TASK-083 must finish P0 within the ADR-060 boundary.

### Required Repair

1. Preserve the existing provider-neutral validation tier/owner model and handoff-bound `ValidationPlan`.
2. Ensure AIOS/Bridge never schedules more than one T2 for a P0 execution. The certification boundary remains the sole AIOS-managed T2 owner.
3. Apply the bound validation plan to any AIOS-controlled executor validation command list so T2 is excluded from executor-owned T0/T1 validation. Do not add shell interception or transport command capture merely to observe executor ad-hoc commands.
4. Replace ambiguous/global counting with scoped evidence. RESULT-N must persist machine-readable evidence equivalent to:

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

5. If executor ad-hoc T2 observability is `UNAVAILABLE`, its count and global count must be `UNKNOWN`; never fabricate zero or one.
6. If ad-hoc T2 is actually observable and observed while certification owns T2, report a validation policy violation and fail conservatively.
7. Add integration regressions proving AIOS-managed T2 is scheduled exactly once, a second AIOS-managed T2 is rejected/detected, unavailable ad-hoc observability remains explicit `UNKNOWN`, and RESULT persistence preserves the evidence scope.
8. Prove the same validation policy semantics for Codex and Antigravity surfaces. No Claude transport implementation is authorized.
9. Preserve canonical T2 certification, roadmap authority, task authority, leases, scope enforcement, publication trust, reviewed-head merge safety, no auto-retry, and no auto-reroute.

## Acceptance for B1

```text
VALIDATION_PLAN_BOUND_TO_AUTHORIZATION: PASS
AIOS_CONTROLLED_EXECUTOR_T2_FILTERING: PASS
FULL_CANONICAL_OWNER: CERTIFICATION_BOUNDARY
EXPECTED_AIOS_MANAGED_T2_EXECUTION_COUNT: 1
AIOS_MANAGED_T2_EXECUTION_COUNT: 1
AIOS_MANAGED_T2_DUPLICATION_DETECTED: NO
EXECUTOR_AD_HOC_T2_OBSERVABILITY: EXPLICIT
GLOBAL_COUNT_NOT_FABRICATED: PASS
RESULT_EVIDENCE_PERSISTED: PASS
CODEX_ANTIGRAVITY_VALIDATION_POLICY_PARITY: PASS
SHELL_INTERCEPTION_ADDED: NO
P2_SESSION_CAPTURE_ADDED: NO
```

## Non-blocking Audit Results

The following reviewed boundaries already PASS and must remain preserved:

```text
BASELINE_AND_LINEAGE: PASS
CUMULATIVE_SCOPE: EXACT
LEAN_ROADMAP_V1_1_NORMAL_PREFLIGHT: PASS
TASK_084_BOOTSTRAP_REUSE: PASS
RUN_FIX_SYNC_BEFORE_HANDOFF: PASS
SYNC_FAILURE_BLOCKS_HANDOFF: PASS
VALIDATION_TIER_CLOSED: PASS
VALIDATION_OWNER_CLOSED: PASS
VALIDATION_PLAN_IMMUTABLE: PASS
EXACTLY_ONE_T2_OWNER_MODEL: PASS
FAILED_T2_CANNOT_PUBLISH: PASS
PROVIDER_NEUTRAL_EVIDENCE_SCHEMA_FOUNDATION: PASS
CANONICAL_FULL_SUITE: PASS_REPORTED
AUTO_RETRY: NO
AUTO_REROUTE: NO
H5_H8_OPENED: NO
```

## Decision

```text
TASK-083: CHANGES_REQUIRED
APPROVED: NO
MERGE_AUTHORIZED: NO
BLOCKERS_REMAINING: 1
NEXT_ACTION: FIX TASK-083
P0_FORMAL_COMPLETION: NO
P1_P3_AUTHORIZED: NO
H5_H8_AUTHORIZED: NO
```

## Machine-Readable E4 Inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/tasks/TASK-083.md","blob_sha":"15eaa9985f0b522a1ad1a9325bd2674a4e593ccc"},{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.1.md","blob_sha":"cae51de4db517dd452c260076a1daa521c1e3a4c"},{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.1.completions.json","blob_sha":"ad2ed229adcd7e0db4909a8e1f330b7836544870"},{"path":".ai/roadmaps/CANONICAL-ROADMAP-REGISTRY-v1.json","blob_sha":"52f4f24a6b0af719886c6524ade8e19f8cc8984c"},{"path":".ai/decisions/ADR-057-AIOS-BRIDGE-LEAN-EXECUTION-V1.1-CANONICAL-ROADMAP-NORMALIZATION.md","blob_sha":"3270fca0fb723c49a67eba5586d6a6714bcb2bfa"},{"path":".ai/decisions/ADR-060-AIOS-P0-MANAGED-VALIDATION-OBSERVABILITY-BOUNDARY-CONTRACT.md","blob_sha":"3a0b9bca86b0cf1aad4ec066e3e9a4089450f6ae"},{"path":".ai/reviews/REVIEW-084.md","blob_sha":"46ea510b872d52047b030786bb6f91b57b2c00db"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","src/aios_bridge/validation.py","src/aios_bridge/executor_automation.py",".agents/skills/aios-worker/scripts/aios_worker.py","tests/aios_bridge/test_validation.py","tests/test_bridge.py","tests/test_bridge_executor_automation.py","tests/aios_bridge/test_aios_worker_control_surface.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]},{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]}],"operation":"FIX","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}
