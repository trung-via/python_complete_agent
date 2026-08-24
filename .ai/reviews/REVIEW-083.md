# REVIEW-083 — P0 Validation Ownership + Telemetry Foundation
PUBLISHER_PROFILE: CANONICAL_E4

STATUS: CHANGES_REQUIRED
APPROVED: NO
AUTO_MERGE_ELIGIBLE: NO
MERGE_AUTHORIZED: NO
MERGED_TO_MAIN: NO

TASK_ID: TASK-083
REVIEW_ROUND: 1
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

Observed cumulative TASK-083 delta is limited to the TASK-authorized implementation/test paths plus Bridge-generated RESULT:

```text
bridge.py
src/aios_bridge/executor_automation.py
src/aios_bridge/validation.py
tests/aios_bridge/test_validation.py
tests/test_bridge.py
.ai/results/RESULT-083.md
```

Reported canonical certification evidence:

```text
FULL_REPOSITORY_TESTS: 2549 passed, 7 skipped, 0 failed
FULL_REPOSITORY_DURATION: 335.42s
E4_TRANSPORT_STATUS: EXITED_ZERO
E4_ALLOWED_SCOPE_VERIFIED: PASS
E4_PUBLICATION_TRUST_VERIFIED: PASS
```

The current TASK-083 artifact is correctly rebound after TASK-084 bootstrap; TASK-084 is not part of the TASK-083 delta when reviewed against the authoritative baseline above.

## Finding B1 — T2 deduplication and full-suite count are modeled but not actually observed across the executor boundary

STATUS: BLOCKING
SEVERITY: VALIDATION_INTEGRITY

TASK-083 requires one shared validation ownership mechanism to both eliminate duplicate T2 execution and machine-observe actual versus expected full-suite execution count. The implementation creates sound contract objects (`ValidationPlan`, `ValidationEvidence`, T0-T3 tiers, canonical ownership, duplication rejection), but the executor-side enforcement/observation path is incomplete.

### A. Executor-side T2 filtering is not wired into execution

`executor_commands_for_plan()` correctly removes commands classified as T2 when the certification boundary owns T2, and unit tests prove that pure helper behavior. However the reviewed execution path does not consume that helper when launching Codex or Antigravity. `ExecutorAutomationLaunchPlan` carries a `validation_plan`, but this plan is only bound/passed onward; the actual executor validation command path is not derived through `executor_commands_for_plan()`.

Consequently correctness still depends on the executor/model obeying task prose such as "do not independently run T2" rather than AIOS enforcing the shared validation plan.

### B. Publication telemetry counts only the certification command, not executor-side full-suite executions

In `cmd_publish`, `ValidationEvidence.full_suite_execution_count` is currently derived from the single publication `args.test` command:

```text
1 if args.test classifies as T2, else 0
```

This proves that the certification boundary ran T2 once. It does not prove that Codex/Antigravity did not already run a full suite during implementation.

Therefore this sequence can remain invisible to the current telemetry:

```text
executor runs full pytest tests/ -q      -> unobserved by ValidationEvidence
certification runs full pytest tests/ -q -> counted as 1
reported full_suite_execution_count      -> 1
actual full-suite executions             -> 2
```

That violates the core P0 requirement that duplicate full-suite work be machine-observable rather than inferred from executor compliance or RESULT prose.

### C. RESULT-083 does not persist the required final validation evidence

RESULT-083 records the canonical full-suite command/result and E4 transport/publication facts, but does not persist the required P0 evidence fields:

```text
FULL_CANONICAL_OWNER
EXPECTED_FULL_SUITE_EXECUTION_COUNT
FULL_SUITE_EXECUTION_COUNT
VALIDATION_DUPLICATION_DETECTED
TARGETED_TEST_EXECUTION_COUNT / observed targeted timing when available
```

So an independent reviewer cannot reconstruct the P0 invariant from the RESULT artifact itself.

## Required Repair

Keep the FIX within TASK-083 authorized paths and preserve the current good contract model.

1. Wire the handoff-bound `ValidationPlan` into the real executor-facing validation path for both Codex and Antigravity semantics. T2 owned by certification must be removed/blocked from executor validation execution, not merely represented by a helper that is unused by the execution path.
2. Build validation evidence from observed executor-validation events plus certification events. Do not manufacture `full_suite_execution_count=1` solely because the publication command is T2.
3. If a runtime cannot observe whether an executor performed T2, represent that state explicitly and fail conservatively; do not claim deduplication is proven.
4. Persist machine-readable validation evidence in RESULT-N (or an exact RESULT-bound evidence field) including owner, expected/actual T2 count, duplication flag, targeted count, and observed durations where available.
5. Add integration regressions proving an attempted executor-side T2 plus certification T2 is either prevented before execution or yields `VALIDATION_DUPLICATION_DETECTED`; a fabricated `ValidationEvidence(full_suite_execution_count=2)` unit test alone is insufficient.
6. Prove the same shared mechanism for Codex and Antigravity surfaces. Future Claude remains contract-compatible only; no Claude transport is authorized.
7. Keep canonical T2 certification itself intact. No auto-retry, auto-reroute, P1 batching, P2 sessions, P3 routing, H5-H8, or authority redesign.

## Non-blocking Audit Results

The following reviewed boundaries are acceptable at this snapshot and must remain preserved by the FIX:

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
DUPLICATION_REJECTION_MODEL: PASS
PROVIDER_NEUTRAL_EVIDENCE_SCHEMA: PASS
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

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/tasks/TASK-083.md","blob_sha":"15eaa9985f0b522a1ad1a9325bd2674a4e593ccc"},{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.1.md","blob_sha":"cae51de4db517dd452c260076a1daa521c1e3a4c"},{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.1.completions.json","blob_sha":"ad2ed229adcd7e0db4909a8e1f330b7836544870"},{"path":".ai/roadmaps/CANONICAL-ROADMAP-REGISTRY-v1.json","blob_sha":"52f4f24a6b0af719886c6524ade8e19f8cc8984c"},{"path":".ai/decisions/ADR-056-AIOS-BRIDGE-LEAN-EXECUTION-CONTROLLED-EVOLUTION-CONTRACT-LOCK.md","blob_sha":"7ae9b7d518d5130d193ceb9cf981f29290014288"},{"path":".ai/decisions/ADR-057-AIOS-BRIDGE-LEAN-EXECUTION-V1.1-CANONICAL-ROADMAP-NORMALIZATION.md","blob_sha":"3270fca0fb723c49a67eba5586d6a6714bcb2bfa"},{"path":".ai/reviews/REVIEW-084.md","blob_sha":"46ea510b872d52047b030786bb6f91b57b2c00db"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","src/aios_bridge/validation.py","src/aios_bridge/executor_automation.py",".agents/skills/aios-worker/scripts/aios_worker.py","tests/aios_bridge/test_validation.py","tests/test_bridge.py","tests/test_bridge_executor_automation.py","tests/aios_bridge/test_aios_worker_control_surface.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]},{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]}],"operation":"FIX","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}
