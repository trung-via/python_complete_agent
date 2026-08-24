# REVIEW-086 — P1.0A Transactional RUN/FIX + Evidence Refresh
PUBLISHER_PROFILE: CANONICAL_E4

STATUS: CHANGES_REQUIRED
APPROVED: NO
AUTO_MERGE_ELIGIBLE: NO
MERGE_AUTHORIZED: NO
MERGED_TO_MAIN: NO

TASK_ID: TASK-086
REVIEW_ROUND: 2
REVIEWED_TASK_HEAD_SHA: aa251feb47abb3fe510289d2f6835c7d792c2726
REVIEWED_BASE_MAIN_SHA: 11967270857dd886e6e686a599bdd40e1d684619
TASK_ARTIFACT_BLOB_SHA: 92d184f824f7dd31d538097e93284c92fd3ad916
RESULT_BLOB_SHA: 92fe531a7a476974dc2e30608b38b1d7de688c5d
EXECUTOR_ID: antigravity
FIX_EXECUTION_MODE: IMPLEMENTATION
BLOCKERS_REMAINING: 2
CODE_AUDIT: CHANGES_REQUIRED
CANONICAL_TESTS: PASS
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
HEAD: aa251feb47abb3fe510289d2f6835c7d792c2726
MAIN: 11967270857dd886e6e686a599bdd40e1d684619
LINEAGE: AHEAD 2 / BEHIND 0
MERGE_BASE: 11967270857dd886e6e686a599bdd40e1d684619
FULL_CANONICAL: 2584 passed, 7 skipped
AIOS_MANAGED_T2_EXECUTION_COUNT: 1
AIOS_MANAGED_T2_DUPLICATION_DETECTED: NO
```

## Prior findings B1–B3

All three round-1 findings are closed and must remain preserved.

```text
B1_BOUND_MAIN_LINEAGE: PASS
BOUND_MAIN_IS_ANCESTOR_OF_TASK_HEAD: PASS
RESULT_BASE_MAIN_MATCHES_ACTUAL_LINEAGE: PASS
TASK_088_ACCEPTED_CHANGES_PRESERVED: PASS
STALE_EXISTING_RUN_BRANCH_CANNOT_SILENTLY_BYPASS_BOUND_MAIN: PASS

B2_REDUNDANT_SYNC_REMOVED: PASS
STATUS_NOT_PREREQUISITE: PASS
RUN_NO_REDUNDANT_PRE_SYNC: PASS
FIX_NO_REDUNDANT_PRE_SYNC: PASS
HANDOFF_REMAINS_SINGLE_PRE_AUTHORITY_SYNC_BOUNDARY: PASS

B3_EXACT_MODE_AUTHORITY: PASS_WITH_RESIDUAL_FAIL_CLOSED_GAP_B5
LATEST_EXACT_REVIEW_IS_SINGLE_MODE_AUTHORITY: PASS
STALE_LOCAL_REVIEW_CANNOT_ROUTE_CONTINUATION: PASS
```

TASK-088 observability is preserved because the repaired branch is descended from accepted main and does not modify the accepted Codex transport/outcome files.

## Finding B4 — EVIDENCE_REFRESH does not yet enforce clean exact reviewed head

STATUS: BLOCKING
SEVERITY: AUTHORITY_AND_PUBLICATION_SAFETY

TASK-086 explicitly requires EVIDENCE_REFRESH to operate only after a fresh FIX authorization, on the exact reviewed task head, with a clean worktree, zero executor invocations, and exactly one canonical T2 certification.

Current `WorkerFlowCoordinator` does:

```text
handoff FIX
→ load active authorization
→ if fix_execution_mode == EVIDENCE_REFRESH
→ call bridge publish directly
```

The coordinator performs no clean-worktree check and no `HEAD == REVIEWED_TASK_HEAD_SHA` check before publication. Generic Bridge `publish` is not EVIDENCE_REFRESH-aware; its normal purpose is allowed to publish implementation deltas. The governed FIX preflight validates that `REVIEWED_TASK_HEAD_SHA` exists and is a 40-hex SHA, but does not itself prove the current task branch HEAD equals that reviewed SHA.

Therefore an explicit EVIDENCE_REFRESH can currently route to canonical publication with an unreviewed dirty delta or a task-head drift unless another incidental guard happens to stop it. This violates the task's closed safety contract.

Required repair:

```text
EVIDENCE_REFRESH continuation must be Bridge-owned/fail-closed and verify BEFORE tests/publication:
  ACTIVE action == FIX
  fix_execution_mode == EVIDENCE_REFRESH
  exact frozen REVIEW authorization is still current
  current branch is the authorized task branch
  current task HEAD == exact REVIEWED_TASK_HEAD_SHA from the frozen review evidence
  non-.ai worktree is clean / no implementation delta is present

Only after all checks pass:
  executor invocation count = 0
  canonical T2 runs exactly once
  RESULT publication proceeds through canonical Bridge publication
```

Do not implement this as a second independent review parser in the coordinator. Preserve B3: exact Bridge-frozen review/authorization remains the single authority.

Required regressions:

```text
EVIDENCE_REFRESH_DIRTY_WORKTREE_FAILS_BEFORE_CERTIFICATION: PASS
EVIDENCE_REFRESH_HEAD_DRIFT_FAILS_BEFORE_CERTIFICATION: PASS
EVIDENCE_REFRESH_EXACT_CLEAN_REVIEWED_HEAD_PASSES: PASS
EVIDENCE_REFRESH_EXECUTOR_INVOCATION_COUNT_ZERO: PASS
EVIDENCE_REFRESH_T2_EXACTLY_ONCE: PASS
EVIDENCE_REFRESH_PUBLISHES_THROUGH_NORMAL_WORKER_SURFACE: PASS
```

## Finding B5 — Closed FIX mode still has two non-fail-closed cases

STATUS: BLOCKING
SEVERITY: CLOSED_AUTHORITY_VOCABULARY

Two residual gaps remain in the closed FIX mode contract.

### B5.1 Duplicate identical review markers are accepted

`extract_fix_execution_mode()` currently rejects conflicting values, but two identical markers such as:

```text
FIX_EXECUTION_MODE: IMPLEMENTATION
FIX_EXECUTION_MODE: IMPLEMENTATION
```

are accepted because the implementation collapses matches into a set and only rejects more than one distinct value. TASK-086 requires `multiple/conflicting markers → FAIL_CLOSED`, so any marker count greater than one must fail, even if values are identical.

### B5.2 Missing authoritative mode in post-handoff auth silently defaults

After successful FIX handoff, the coordinator currently uses:

```text
auth.get("fix_execution_mode", "IMPLEMENTATION")
```

At that point compatibility defaulting has already happened inside Bridge while parsing the exact REVIEW. A persisted ACTIVE FIX authorization missing `fix_execution_mode` is therefore malformed/drifted authority and must fail closed, not silently become IMPLEMENTATION.

Required repair and tests:

```text
DUPLICATE_IDENTICAL_FIX_MODE_MARKERS_FAIL_CLOSED: PASS
CONFLICTING_FIX_MODE_MARKERS_FAIL_CLOSED: PASS
UNKNOWN_FIX_MODE_FAILS_CLOSED: PASS
MISSING_AUTHORIZED_FIX_MODE_FAILS_CLOSED: PASS
VALID_MISSING_REVIEW_MARKER_NORMALIZES_TO_IMPLEMENTATION_IN_BRIDGE_AUTH: PASS
```

The compatibility rule remains unchanged: a REVIEW with no FIX_EXECUTION_MODE marker means IMPLEMENTATION, but Bridge must persist that normalized mode explicitly in authorization.

## Preserve / Out of scope

```text
AUTO_RETRY: NO
AUTO_REROUTE: NO
TASK_087_CONCERNS_NOT_IMPLEMENTED: PASS
CODEX_FAILURE_ENVELOPE_PROPAGATION: RESERVED_FOR_TASK_087
P1_CAPABILITY_BATCH_NOT_IMPLEMENTED: PASS
P2_P3_NOT_OPENED: PASS
H5_H8_NOT_OPENED: PASS
```

Do not reopen B1–B3 except where needed to preserve their accepted behavior. Do not add timeout classification, persistent sessions, capability batching, adaptive routing, or H5 work.

## Decision

```text
TASK-086: CHANGES_REQUIRED
APPROVED: NO
MERGE_AUTHORIZED: NO
BLOCKERS_REMAINING: 2
NEXT_ACTION: FIX TASK-086 WITH ANTIGRAVITY
```

## Machine-Readable E4 Inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/tasks/TASK-086.md","blob_sha":"92d184f824f7dd31d538097e93284c92fd3ad916"},{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.1.md","blob_sha":"cae51de4db517dd452c260076a1daa521c1e3a4c"},{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.1.completions.json","blob_sha":"b7256b572469ac89db8808c88b8cd880e67cd7b6"},{"path":".ai/decisions/ADR-061-AIOS-P1.0-TRANSACTIONAL-WORKER-FLOW-FIX-RECOVERY-CONTRACT.md","blob_sha":"b456d80befff7aeec0d3a0217e03a9834f71d7f8"},{"path":".ai/decisions/ADR-062-AIOS-P1.0-BOUNDED-SLICE-DECOMPOSITION-AFTER-CLEAN-NOOP.md","blob_sha":"bcdb4f148d731292c776802d858448e99469abe1"},{"path":".ai/decisions/ADR-063-AIOS-CODEX-NOOP-OUTCOME-OBSERVABILITY-GATE.md","blob_sha":"471067d090d76488ebb760266082aba745eb5a06"},{"path":".ai/results/RESULT-086.md","blob_sha":"92fe531a7a476974dc2e30608b38b1d7de688c5d"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","src/aios_bridge/worker_flow.py",".agents/skills/aios-worker/scripts/aios_worker.py",".agents/skills/aios-worker/SKILL.md",".agents/workflows/aios-worker.md","tests/aios_bridge/test_worker_flow.py","tests/aios_bridge/test_aios_worker_control_surface.py","tests/test_bridge.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]}],"operation":"FIX","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}
