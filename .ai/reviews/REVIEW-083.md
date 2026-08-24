# REVIEW-083 — P0 Validation Ownership + Telemetry Foundation
PUBLISHER_PROFILE: CANONICAL_E4

STATUS: CHANGES_REQUIRED
APPROVED: NO
AUTO_MERGE_ELIGIBLE: NO
MERGE_AUTHORIZED: NO
MERGED_TO_MAIN: NO

TASK_ID: TASK-083
REVIEW_ROUND: 2
REVIEW_REVISION: ADR-060_RESULT_EVIDENCE_REFRESH
REVIEWED_TASK_HEAD_SHA: 4f47ddfb2ae241a4d7efa0a3c6c2ae3c1536b2e1
REVIEWED_BASE_MAIN_SHA: 962712450ce14d3629c3d1caef59c9651bba7f90
TASK_ARTIFACT_BLOB_SHA: 15eaa9985f0b522a1ad1a9325bd2674a4e593ccc
RESULT_BLOB_SHA: 847bbc2629f4d2d9896032234e44764547c7f9b7
EXECUTOR_ID: codex
BLOCKERS_REMAINING: 1
CODE_AUDIT: PASS_WITH_EVIDENCE_BLOCKER
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
PRIOR_REVIEWED_HEAD_SHA: 0c9c5f9fe5789fd56162c0786e4f8f90ef785bb0
REVIEWED_TASK_HEAD_SHA: 4f47ddfb2ae241a4d7efa0a3c6c2ae3c1536b2e1
STATUS_VS_PRIOR_REVIEWED_HEAD: AHEAD
AHEAD_BY: 1
STATUS_VS_MAIN: AHEAD
AHEAD_BY_MAIN: 2
BEHIND_BY_MAIN: 0
MERGE_BASE_SHA: 962712450ce14d3629c3d1caef59c9651bba7f90
FIX_SCOPE: EXACT
```

Round-2 FIX delta is limited to authorized paths plus Bridge-generated RESULT:

```text
bridge.py
src/aios_bridge/validation.py
tests/aios_bridge/test_validation.py
tests/test_bridge_executor_automation.py
.ai/results/RESULT-083.md
```

Reported canonical certification:

```text
FULL_REPOSITORY_TESTS: 2553 passed, 7 skipped, 0 failed
FULL_REPOSITORY_DURATION: 316.38s
E4_TRANSPORT_STATUS: EXITED_ZERO
E4_ALLOWED_SCOPE_VERIFIED: PASS
E4_PUBLICATION_TRUST_VERIFIED: PASS
```

## Round-2 Code Audit — ADR-060 Logic

The reviewed source now implements the intended ADR-060 boundary:

```text
AIOS_MANAGED_VALIDATION: scoped exact evidence
EXECUTOR_AD_HOC_VALIDATION: OBSERVED | UNAVAILABLE
UNAVAILABLE_AD_HOC_COUNT: UNKNOWN
UNAVAILABLE_GLOBAL_COUNT: UNKNOWN
CERTIFICATION_T2_OWNER: CERTIFICATION_BOUNDARY
AIOS_MANAGED_T2_EXPECTED: 1
SECOND_AIOS_MANAGED_T2: REJECTED
OBSERVED_AD_HOC_T2_WHILE_CERTIFICATION_OWNS_T2: POLICY_VIOLATION
TARGETED_COUNT_OUTSIDE_CERTIFICATION_STREAM: UNKNOWN
```

`certification_commands_for_plan()` now rejects duplicate AIOS-managed T2 scheduling. `ValidationEvidence` no longer fabricates unavailable ad-hoc/global counts, and `_validation_result_manifest()` renders the ADR-060 scoped fields. These logic changes are accepted for this reviewed head and must remain preserved.

## Finding B2 — Published RESULT still uses the pre-ADR-060 evidence schema

STATUS: BLOCKING
SEVERITY: EVIDENCE_INTEGRITY

The source at reviewed head `4f47ddfb...` contains the new ADR-060 scoped renderer, but the RESULT committed by the same FIX still contains the prior schema:

```text
EXPECTED_FULL_SUITE_EXECUTION_COUNT: 1
FULL_SUITE_EXECUTION_COUNT: 1
TARGETED_TEST_EXECUTION_COUNT: 0
VALIDATION_DUPLICATION_DETECTED: NO
```

and its `Validation Evidence` JSON still uses the old ambiguous fields and records targeted count `0` instead of `UNKNOWN`.

It does NOT persist the required ADR-060 evidence:

```text
EXPECTED_AIOS_MANAGED_T2_EXECUTION_COUNT
AIOS_MANAGED_T2_EXECUTION_COUNT
AIOS_MANAGED_T2_DUPLICATION_DETECTED
EXECUTOR_AD_HOC_T2_OBSERVABILITY
EXECUTOR_AD_HOC_T2_EXECUTION_COUNT
GLOBAL_T2_EXECUTION_COUNT
```

This mismatch is consistent with the self-hosted execution path: `bridge.py execute` starts the Bridge process before the bounded executor mutates `bridge.py`, then the same already-loaded process performs E4 publication after the executor returns. Therefore the code fix can be correct on disk while that same run's RESULT is rendered by the pre-fix in-memory implementation.

P0 cannot PASS until the canonical RESULT itself proves the new evidence contract.

## Required Repair — bounded evidence refresh only

Do not redesign P0 and do not add shell/session interception.

1. Preserve the accepted round-2 implementation logic.
2. Add or strengthen one bounded integration regression in an already authorized test path proving that `cmd_publish`/RESULT persistence, not merely the pure `_validation_result_manifest()` helper, emits the ADR-060 scoped evidence schema.
3. The regression should prove at minimum:

```text
FULL_CANONICAL_OWNER: CERTIFICATION_BOUNDARY
EXPECTED_AIOS_MANAGED_T2_EXECUTION_COUNT: 1
AIOS_MANAGED_T2_EXECUTION_COUNT: 1
AIOS_MANAGED_T2_DUPLICATION_DETECTED: NO
EXECUTOR_AD_HOC_T2_OBSERVABILITY: UNAVAILABLE
EXECUTOR_AD_HOC_T2_EXECUTION_COUNT: UNKNOWN
GLOBAL_T2_EXECUTION_COUNT: UNKNOWN
TARGETED_TEST_EXECUTION_COUNT: UNKNOWN
```

4. Re-run the FIX through a newly started Bridge process. Because the reviewed branch already contains the new renderer before this next invocation starts, the next canonical publication must regenerate RESULT-083 with the ADR-060 scoped evidence.
5. The `Validation Evidence` JSON in RESULT must also use the scoped schema and must not present unavailable targeted/ad-hoc/global counts as exact zeroes.
6. Legacy ambiguous field names may only remain if explicitly marked as AIOS-managed compatibility aliases. Preferred outcome for this task is the already-implemented scoped renderer with no ambiguous top-level legacy claims.
7. Keep canonical T2 certification exactly once for this new execution. This new certification is for the new FIX candidate and is not a duplicate within the prior execution.
8. No P1, P2, P3, H5-H8, shell interception, persistent session work, auto-retry, or auto-reroute.

## Acceptance for B2

```text
ROUND2_LOGIC_PRESERVED: PASS
CMD_PUBLISH_RESULT_PERSISTENCE_REGRESSION: PASS
VALIDATION_PROFILE: CONTROL_PLANE_STRICT_COMPAT
FULL_CANONICAL_OWNER: CERTIFICATION_BOUNDARY
EXPECTED_AIOS_MANAGED_T2_EXECUTION_COUNT: 1
AIOS_MANAGED_T2_EXECUTION_COUNT: 1
AIOS_MANAGED_T2_DUPLICATION_DETECTED: NO
EXECUTOR_AD_HOC_T2_OBSERVABILITY: UNAVAILABLE
EXECUTOR_AD_HOC_T2_EXECUTION_COUNT: UNKNOWN
GLOBAL_T2_EXECUTION_COUNT: UNKNOWN
TARGETED_TEST_EXECUTION_COUNT: UNKNOWN
RESULT_SCOPED_EVIDENCE_PERSISTED: PASS
GLOBAL_COUNT_NOT_FABRICATED: PASS
CANONICAL_T2: PASS
```

## Accepted / Do Not Reopen Without Regression

```text
BASELINE_AND_LINEAGE: PASS
FIX_SCOPE: EXACT
LEAN_ROADMAP_V1_1_NORMAL_PREFLIGHT: PASS
VALIDATION_PLAN_BOUND_TO_AUTHORIZATION: PASS
VALIDATION_TIER_OWNER_MODEL: PASS
AIOS_MANAGED_T2_SCHEDULER: PASS
AIOS_MANAGED_DUPLICATE_REJECTION: PASS
AD_HOC_OBSERVABILITY_MODEL: PASS
GLOBAL_COUNT_NOT_FABRICATED_IN_SOURCE: PASS
FAILED_T2_CANNOT_PUBLISH: PASS
RUN_FIX_SYNC_BEFORE_HANDOFF: PASS
CODEX_ANTIGRAVITY_POLICY_MODEL: PASS
CANONICAL_FULL_SUITE: PASS_REPORTED
AUTO_RETRY: NO
AUTO_REROUTE: NO
P1_P3_OPENED: NO
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
