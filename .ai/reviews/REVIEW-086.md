# REVIEW-086 — P1.0A Transactional RUN/FIX + Evidence Refresh
PUBLISHER_PROFILE: CANONICAL_E4

STATUS: CHANGES_REQUIRED
APPROVED: NO
AUTO_MERGE_ELIGIBLE: NO
MERGE_AUTHORIZED: NO
MERGED_TO_MAIN: NO

TASK_ID: TASK-086
REVIEW_ROUND: 1
REVIEWED_TASK_HEAD_SHA: 0ae356cf5bdf3c1d92ab0d8d11ed4dc7056dcf02
TASK_ARTIFACT_BLOB_SHA: 92d184f824f7dd31d538097e93284c92fd3ad916
RESULT_BLOB_SHA: 99b992cbec7ad88693029cb6ca8f25e2ddf4af24
EXECUTOR_ID: antigravity
FIX_EXECUTION_MODE: IMPLEMENTATION
BLOCKERS_REMAINING: 3
CODE_AUDIT: CHANGES_REQUIRED
CANONICAL_TESTS: INVALID_BASELINE_LINEAGE
ROADMAP_AUDIT: PASS
ROADMAP_ID: AIOS-BRIDGE-LEAN-EXECUTION
ROADMAP_VERSION: 1.1
ROADMAP_BLOB_SHA: cae51de4db517dd452c260076a1daa521c1e3a4c
ROADMAP_FINGERPRINT: 4bcbb10e1e8e02169ccb5a516801abd1ce01b0b5edd348d90abcac7d0887404f
MILESTONE: P1
CAPABILITY_ID: P1_UNIFIED_VALIDATION_CAPABILITY_BATCH
TASK_087_REMAINS_RESERVED: YES
P2_P3_AUTHORIZED: NO
H5_H8_AUTHORIZED: NO

## Finding B1 — Bound-main lineage integrity

STATUS: BLOCKING

TASK-086 was rebound to canonical main `11967270857dd886e6e686a599bdd40e1d684619`, but the published RUN head above was built from stale merge-base `d55a5b168f6833558c3f9db63f46dd1817392283` and is behind canonical main by the three accepted TASK-088 commits.

Required repair:

```text
preserve TASK-086 implementation delta
forward-port/rebase it onto exact main 11967270857dd886e6e686a599bdd40e1d684619
preserve all accepted TASK-088 observability behavior
make bound main an ancestor of repaired TASK-086 head
add a fail-closed/deterministic guard so a rebound RUN cannot silently reuse an older branch baseline
rerun targeted tests and exactly one canonical T2
republish RESULT-086 from repaired lineage
```

Acceptance:

```text
BOUND_MAIN_IS_ANCESTOR_OF_TASK_HEAD: PASS
RESULT_BASE_MAIN_MATCHES_ACTUAL_LINEAGE: PASS
TASK_088_ACCEPTED_CHANGES_PRESERVED: PASS
STALE_EXISTING_RUN_BRANCH_CANNOT_SILENTLY_BYPASS_BOUND_MAIN: PASS
```

## Finding B2 — Remove redundant RUN/FIX pre-sync

STATUS: BLOCKING

`WorkerFlowCoordinator` currently performs `bridge sync` before `bridge handoff`, while handoff already fetches/freezes control evidence, reconciles canonical main and performs pre-authority validation.

Required repair:

```text
STATUS: sync -> pending
RUN/FIX: handoff directly as the single pre-authority synchronization boundary
```

Acceptance:

```text
STATUS_NOT_PREREQUISITE: PASS
RUN_NO_REDUNDANT_PRE_SYNC: PASS
FIX_NO_REDUNDANT_PRE_SYNC: PASS
HANDOFF_REMAINS_SINGLE_PRE_AUTHORITY_SYNC_BOUNDARY: PASS
```

## Finding B3 — Exact Bridge authorization is the single FIX-mode authority

STATUS: BLOCKING

The coordinator must not independently route using a separately read local/stale REVIEW. The exact REVIEW frozen by Bridge handoff and its persisted authorization must be the single authority for `IMPLEMENTATION` versus `EVIDENCE_REFRESH`.

Required repair:

```text
remove independent authoritative local REVIEW mode decision
continuation consumes Bridge-owned exact authorized mode/result
stale working-tree REVIEW cannot override control evidence
mode drift/mismatch fails closed
EVIDENCE_REFRESH skips executor only when exact Bridge authorization says EVIDENCE_REFRESH
```

Acceptance:

```text
LATEST_EXACT_REVIEW_IS_SINGLE_MODE_AUTHORITY: PASS
COORDINATOR_MODE_EQUALS_AUTHORIZED_MODE: PASS
STALE_LOCAL_REVIEW_CANNOT_ROUTE_CONTINUATION: PASS
MODE_DRIFT_FAILS_CLOSED: PASS
EVIDENCE_REFRESH_SKIPS_EXECUTOR_ONLY_WHEN_EXACT_AUTH_SAYS_EVIDENCE_REFRESH: PASS
```

## Preserve

```text
FIX_MODE_CLOSED_VOCABULARY: ACCEPTED
UNKNOWN_FIX_MODE_FAILS_CLOSED: ACCEPTED
CONFLICTING_FIX_MODE_FAILS_CLOSED: ACCEPTED
ANTIGRAVITY_INTERACTIVE_IMPLEMENTATION_CONTINUATION: ACCEPTED
CODEX_BOUNDED_IMPLEMENTATION_CONTINUATION_INTENT: ACCEPTED
P0_T2_OWNER: CERTIFICATION_BOUNDARY
AUTO_RETRY: NO
AUTO_REROUTE: NO
TASK_087_NOT_IMPLEMENTED: PASS
P2_P3_NOT_OPENED: PASS
H5_H8_NOT_OPENED: PASS
```

The Codex failure-envelope propagation issue remains reserved for TASK-087.

## Decision

```text
TASK-086: CHANGES_REQUIRED
APPROVED: NO
MERGE_AUTHORIZED: NO
BLOCKERS_REMAINING: 3
NEXT_ACTION: FIX TASK-086 WITH ANTIGRAVITY
```

## Machine-Readable E4 Inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/tasks/TASK-086.md","blob_sha":"92d184f824f7dd31d538097e93284c92fd3ad916"},{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.1.md","blob_sha":"cae51de4db517dd452c260076a1daa521c1e3a4c"},{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.1.completions.json","blob_sha":"b7256b572469ac89db8808c88b8cd880e67cd7b6"},{"path":".ai/decisions/ADR-061-AIOS-P1.0-TRANSACTIONAL-WORKER-FLOW-FIX-RECOVERY-CONTRACT.md","blob_sha":"b456d80befff7aeec0d3a0217e03a9834f71d7f8"},{"path":".ai/decisions/ADR-062-AIOS-P1.0-BOUNDED-SLICE-DECOMPOSITION-AFTER-CLEAN-NOOP.md","blob_sha":"bcdb4f148d731292c776802d858448e99469abe1"},{"path":".ai/decisions/ADR-063-AIOS-CODEX-NOOP-OUTCOME-OBSERVABILITY-GATE.md","blob_sha":"471067d090d76488ebb760266082aba745eb5a06"},{"path":".ai/results/RESULT-086.md","blob_sha":"99b992cbec7ad88693029cb6ca8f25e2ddf4af24"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","src/aios_bridge/worker_flow.py",".agents/skills/aios-worker/scripts/aios_worker.py",".agents/skills/aios-worker/SKILL.md",".agents/workflows/aios-worker.md","tests/aios_bridge/test_worker_flow.py","tests/aios_bridge/test_aios_worker_control_surface.py","tests/test_bridge.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]}],"operation":"FIX","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}
