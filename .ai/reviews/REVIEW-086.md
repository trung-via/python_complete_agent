# REVIEW-086 — P1.0A Transactional RUN/FIX + Evidence Refresh
PUBLISHER_PROFILE: CANONICAL_E4

STATUS: CHANGES_REQUIRED
APPROVED: NO
AUTO_MERGE_ELIGIBLE: NO
MERGE_AUTHORIZED: NO
MERGED_TO_MAIN: NO

TASK_ID: TASK-086
REVIEW_ROUND: 1
REVIEWED_TASK_REF: ai/task-086
REVIEWED_BASE_MAIN_SHA: 11967270857dd886e6e686a599bdd40e1d684619
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

## Reviewed Snapshot

```text
BRANCH: ai/task-086
BOUND_MAIN_SHA: 11967270857dd886e6e686a599bdd40e1d684619
COMPARE_VS_MAIN: DIVERGED
AHEAD_BY_MAIN: 1
BEHIND_BY_MAIN: 3
ACTUAL_MERGE_BASE_SHA: d55a5b168f6833558c3f9db63f46dd1817392283
RESULT_CLAIMED_BASE_MAIN_SHA: 11967270857dd886e6e686a599bdd40e1d684619
RESULT_CANONICAL_T2: 2564 passed, 7 skipped
CURRENT_MAIN_T2_FROM_TASK_088: 2573 passed, 7 skipped
```

The implementation files are within the TASK-086 allowed path set, and the task intent remains P1.0A only. However the published branch is not descended from the rebound canonical baseline, so the current RESULT cannot certify a mergeable state.

## Finding B1 — Bound-main lineage was not actually present on the task branch

STATUS: BLOCKING
SEVERITY: BASELINE_AUTHORITY_INTEGRITY

TASK-086 was rebound to exact main `11967270857dd886e6e686a599bdd40e1d684619` after TASK-088 merged. RESULT-086 also claims that SHA as `Base Main SHA`. Git comparison proves the task branch instead has merge-base `d55a5b168f6833558c3f9db63f46dd1817392283`, is behind main by 3 commits, and ahead by 1.

This is not metadata-only drift. The task branch still contains the pre-TASK-088 Codex transport implementation; for example `src/aios_bridge/executor_transports/codex_local.py` lacks the TASK-088 executor-outcome imports and strict observability implementation. The branch full suite reports 2564 passed, while the accepted TASK-088 main baseline reports 2573 passed.

Required repair:

```text
preserve the authorized TASK-086 implementation delta
forward-port/rebase that delta onto exact main 11967270857dd886e6e686a599bdd40e1d684619
resolve any bridge/adapter conflicts by preserving BOTH:
  - all accepted TASK-088 observability behavior
  - TASK-086 P1.0A behavior
verify main is an ancestor of the repaired TASK-086 head
rerun targeted tests and one canonical T2
republish RESULT-086 from the repaired lineage
```

Also add a bounded regression/guard in the existing authorized Bridge/test paths so a RUN artifact bound to a newer exact `base_main_sha` cannot silently reuse an older task branch and then claim the newer main as its baseline. Fail closed or deterministically realign before authorization; do not silently certify a diverged task branch.

Acceptance:

```text
BOUND_MAIN_IS_ANCESTOR_OF_TASK_HEAD: PASS
RESULT_BASE_MAIN_MATCHES_ACTUAL_LINEAGE: PASS
TASK_088_ACCEPTED_CHANGES_PRESERVED: PASS
STALE_EXISTING_RUN_BRANCH_CANNOT_SILENTLY_BYPASS_BOUND_MAIN: PASS
```

## Finding B2 — RUN/FIX performs redundant synchronization before handoff

STATUS: BLOCKING
SEVERITY: LEAN_EXECUTION_CONTRACT

`WorkerFlowCoordinator.execute_transaction()` currently performs:

```text
RUN/FIX
→ bridge sync
→ bridge handoff
```

but `bridge handoff` already fetches/freeze-resolves control evidence, reconciles canonical main, prepares the task branch, and performs pre-authority validation. TASK-086 explicitly required preserving handoff as the synchronization/authority boundary rather than creating another preparation requirement.

The current design removes the Human-typed STATUS step but introduces an extra automatic sync/network round before every RUN/FIX. That fixes UX while retaining unnecessary wall-time overhead.

Required repair:

```text
STATUS:
  sync → pending remains valid

RUN/FIX:
  call handoff directly as the one pre-authority synchronization boundary
  do not call a separate bridge sync first
```

Tests must prove one RUN/FIX operator command invokes exactly one handoff synchronization path and STATUS remains non-authorizing.

Acceptance:

```text
STATUS_NOT_PREREQUISITE: PASS
RUN_NO_REDUNDANT_PRE_SYNC: PASS
FIX_NO_REDUNDANT_PRE_SYNC: PASS
HANDOFF_REMAINS_SINGLE_PRE_AUTHORITY_SYNC_BOUNDARY: PASS
```

## Finding B3 — FIX continuation is not bound to the exact mode authorized by Bridge

STATUS: BLOCKING
SEVERITY: AUTHORITY_TOCTOU

The coordinator currently resolves review text itself after `sync`, chooses `fix_mode`, then calls `bridge handoff`. Bridge independently resolves/freeze-binds the exact REVIEW and independently computes/persists `fix_execution_mode` in authorization.

The coordinator then routes continuation using its own earlier `fix_mode`, not the exact mode persisted by Bridge. Its default resolver also prefers a working-tree `.ai/reviews/REVIEW-N.md` if one exists before reading `origin/ai-control`.

Therefore this unsafe sequence is possible:

```text
coordinator observes stale/local review A → EVIDENCE_REFRESH
Bridge handoff freezes current review B → IMPLEMENTATION
Bridge authorization correctly binds IMPLEMENTATION
coordinator still follows A → publish without executor
```

That violates the TASK-086 requirement that FIX mode be bound to exact REVIEW authority and that drift fail closed.

Required repair:

```text
one authority for FIX mode = exact REVIEW frozen by Bridge handoff
coordinator must not independently decide an authoritative mode from working-tree review text
continuation must consume a machine-readable mode/result returned from the exact handoff authorization, or use another deterministic Bridge-owned continuation command that reads the persisted authorization
working-tree stale REVIEW must never override the synchronized/frozen control artifact
mode mismatch/drift → fail closed
```

Do not infer EVIDENCE_REFRESH from clean executor output.

Acceptance:

```text
LATEST_EXACT_REVIEW_IS_SINGLE_MODE_AUTHORITY: PASS
COORDINATOR_MODE_EQUALS_AUTHORIZED_MODE: PASS
STALE_LOCAL_REVIEW_CANNOT_ROUTE_CONTINUATION: PASS
MODE_DRIFT_FAILS_CLOSED: PASS
EVIDENCE_REFRESH_SKIPS_EXECUTOR_ONLY_WHEN_EXACT_AUTH_SAYS_EVIDENCE_REFRESH: PASS
```

## Accepted / Preserve

```text
FIX_MODE_CLOSED_VOCABULARY: ACCEPTED
UNKNOWN_FIX_MODE_FAILS_CLOSED: ACCEPTED
CONFLICTING_FIX_MODE_FAILS_CLOSED: ACCEPTED
ANTIGRAVITY_INTERACTIVE_IMPLEMENTATION_CONTINUATION: ACCEPTED
CODEX_BOUNDED_IMPLEMENTATION_CONTINUATION_INTENT: ACCEPTED
EVIDENCE_REFRESH_EXECUTOR_COUNT_TARGET: 0
P0_T2_OWNER: CERTIFICATION_BOUNDARY
AUTO_RETRY: NO
AUTO_REROUTE: NO
TASK_087_NOT_IMPLEMENTED: PASS
P2_P3_NOT_OPENED: PASS
H5_H8_NOT_OPENED: PASS
```

The prior Codex failure-envelope propagation issue remains reserved for TASK-087 and is not a TASK-086 blocker unless the repair regresses existing behavior.

## Decision

```text
TASK-086: CHANGES_REQUIRED
APPROVED: NO
MERGE_AUTHORIZED: NO
BLOCKERS_REMAINING: 3
NEXT_ACTION: FIX TASK-086 WITH ANTIGRAVITY
TASK_087_REMAINS_RESERVED: YES
P2_P3_AUTHORIZED: NO
H5_H8_AUTHORIZED: NO
```

## Machine-Readable E4 Inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/tasks/TASK-086.md","blob_sha":"92d184f824f7dd31d538097e93284c92fd3ad916"},{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.1.md","blob_sha":"cae51de4db517dd452c260076a1daa521c1e3a4c"},{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.1.completions.json","blob_sha":"b7256b572469ac89db8808c88b8cd880e67cd7b6"},{"path":".ai/decisions/ADR-061-AIOS-P1.0-TRANSACTIONAL-WORKER-FLOW-FIX-RECOVERY-CONTRACT.md","blob_sha":"b456d80befff7aeec0d3a0217e03a9834f71d7f8"},{"path":".ai/decisions/ADR-062-AIOS-P1.0-BOUNDED-SLICE-DECOMPOSITION-AFTER-CLEAN-NOOP.md","blob_sha":"bcdb4f148d731292c776802d858448e99469abe1"},{"path":".ai/decisions/ADR-063-AIOS-CODEX-NOOP-OUTCOME-OBSERVABILITY-GATE.md","blob_sha":"471067d090d76488ebb760266082aba745eb5a06"},{"path":".ai/results/RESULT-086.md","blob_sha":"99b992cbec7ad88693029cb6ca8f25e2ddf4af24"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","src/aios_bridge/worker_flow.py",".agents/skills/aios-worker/scripts/aios_worker.py",".agents/skills/aios-worker/SKILL.md",".agents/workflows/aios-worker.md","tests/aios_bridge/test_worker_flow.py","tests/aios_bridge/test_aios_worker_control_surface.py","tests/test_bridge.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]}],"operation":"FIX","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}
