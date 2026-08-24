# REVIEW-079 — H2 Static Import Graph Salvage + Canonical Rebinding

STATUS: CHANGES_REQUIRED
PUBLISHER_PROFILE: CANONICAL_E4
APPROVED: NO
AUTO_MERGE_ELIGIBLE: NO

TASK_ID: TASK-079
REVIEWED_TASK_HEAD_SHA: 91eedffe08501e0819a369bc829d081b47b850f2
REVIEWED_BASE_MAIN_SHA: a51e9c33cd66dc262f13063747295609d7b7df97
TASK_ARTIFACT_BLOB_SHA: 0e783f3e1e32c37e93dd2d52f607c9d81e01cf95
RESULT_BLOB_SHA: fa461ed5cead09f33d17d70e7b812fa94c468812
EXECUTOR_ID: codex
BLOCKERS_REMAINING: 1
CODE_AUDIT: PASS_WITH_TEST_PORTABILITY_BLOCKER
ROADMAP_AUDIT: PASS
ROADMAP_ID: AIOS-ENGINEERING-H-SERIES
ROADMAP_VERSION: 1.0
ROADMAP_BLOB_SHA: 41775383879c86dc68a7d87c0d705cfc8512f62d
ROADMAP_FINGERPRINT: 449dd8bfa4867e74723a1e4a3f619779aebc0c77845a702491bef178a8bc4ce6
MILESTONE: H2
CAPABILITY_ID: H2_STRUCTURAL_EXPERIENCE_GRAPH
REQUIREMENT_BINDINGS_FINGERPRINT: 6b99a9e7e047d29994e9abe3a5e35dbec5505c88687e9f30794324a133eb5d9e
H1_FORMAL_COMPLETION_GATE: PASS
H2_R1_PARTIAL_STRUCTURAL_EVIDENCE: PASS
H2_R2_IMPLEMENTED: NO
H2_FORMAL_COMPLETION: NO
H3_H8_NEW_CAPABILITY: NONE
TASK_076_BRANCH_PRESERVED_AT_REVIEW: YES
TASK_076_PRESERVED_HEAD_SHA: fea85a8bc7f696c50fd5457b0cea3b5d8032b24f
LIVE_PAID_API_AUTHORIZED: NO

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/tasks/TASK-079.md","blob_sha":"0e783f3e1e32c37e93dd2d52f607c9d81e01cf95"},{"path":".ai/roadmaps/H-SERIES-v1.0.md","blob_sha":"41775383879c86dc68a7d87c0d705cfc8512f62d"},{"path":".ai/roadmaps/H-SERIES-v1.0.completions.json","blob_sha":"864072a7444dd8d0ffdb234f0d03a323d898bf11"},{"path":".ai/decisions/ADR-052-AIOS-ENGINEERING-H2-STATIC-IMPORT-GRAPH-REBIND-SALVAGE-CONTRACT-LOCK.md","blob_sha":"57343ac3238c4052ee0f59dafe639d9a5f6f10d5"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["tests/aios_engineering/harness/test_graph.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]},{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]}],"operation":"FIX","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

## Reviewed Snapshot

```text
BASE_MAIN_SHA: a51e9c33cd66dc262f13063747295609d7b7df97
BRANCH: ai/task-079
REVIEWED_TASK_HEAD_SHA: 91eedffe08501e0819a369bc829d081b47b850f2
STATUS_VS_MAIN: AHEAD
AHEAD_BY: 1
BEHIND_BY: 0
MERGE_BASE_SHA: a51e9c33cd66dc262f13063747295609d7b7df97
CUMULATIVE_SCOPE: EXACT
```

Changed implementation scope is exactly the three TASK-079 writable paths plus Bridge-generated RESULT-079.

The preserved historical branch was independently rechecked during review and still points to:

```text
ai/task-076 = fea85a8bc7f696c50fd5457b0cea3b5d8032b24f
```

No mutation/rebase/merge of TASK-076 occurred.

## Validation

```text
FULL_REPOSITORY_TESTS: 2455 passed, 7 skipped, 0 failed
E4_AUTO_EXECUTION: YES
E4_CONTROL_COMMIT_SHA: 52a7baf0551bdba7cf7902c137822a982a95067b
E4_PRE_EXECUTION_HEAD: a51e9c33cd66dc262f13063747295609d7b7df97
E4_TRANSPORT_STATUS: EXITED_ZERO
E4_ALLOWED_SCOPE_VERIFIED: PASS
E4_PUBLICATION_TRUST_VERIFIED: PASS
E4_DIRTY_PATH_COUNT: 3
NETWORK_LLM_PAID_API: NONE
```

## Passing Areas

The salvage itself is technically sound and remains accepted pending the single test-only blocker:

```text
CANONICAL_H2_BINDING: PASS
H1_COMPLETION_GATE: PASS
CURRENT_MAIN_BASELINE: PASS
TASK_076_HISTORY_PRESERVED: PASS (review evidence)
GRAPH_H4_PUBLIC_IDENTITY_REMAINING: NO
H2_IMPORT_GRAPH_POLICY_VERSION: h2-import-graph-v1
H2_H3_CROSS_BINDING_BEFORE_BODY_READ: PASS
EXACT_REPOSITORY_SNAPSHOT_BOUND: PASS
EXACT_BLOB_IDENTITY_BOUND: PASS
WORKTREE_SOURCE_BYTES_USED: NO
STATIC_AST_ONLY: PASS
DETERMINISTIC_INTERNAL_RESOLUTION: PASS
AMBIGUOUS/UNRESOLVED_RESOLUTION: CONSERVATIVE
EDGE_ORDER_AND_FINGERPRINTS: PASS
BODY/EDGE/REFERENCE_BOUNDS: PASS
ZERO_AUTHORITY_RECEIPT: PASS
H2_R2_IMPLEMENTED: NO
H2_COMPLETE_CLAIMED: NO
H3_H8_NEW_CAPABILITY: NONE
```

The recovered graph now uses only canonical H2-specific policy identity (`H2_IMPORT_GRAPH_POLICY_VERSION`, `MAX_H2_IMPORT_GRAPH_*`, and `h2_repository_import_dependency_graph`) while preserving neutral domain types such as `RepositoryImportDependency` and `RepositoryDependencyGraphResult`.

## Blocking Finding

### B1 — Permanent unit test depends on an unmerged local historical branch/object

`test_salvage_history_baseline_and_h2_public_identity_are_locked()` currently executes repository-local Git assertions equivalent to:

```text
git cat-file -t fea85a8bc7f696c50fd5457b0cea3b5d8032b24f
git rev-parse refs/heads/ai/task-076
git merge-base --is-ancestor a51e9c33... HEAD
```

This passes in the current developer workspace because the old task branch and its unmerged commit object are locally present. It is not a durable repository test contract.

A normal fresh clone or CI checkout of `main` is not required to create the local ref `refs/heads/ai/task-076`; a single-branch/shallow checkout may also not contain the unmerged historical commit object or the pre-task baseline object. Therefore, after merging TASK-079, the canonical full suite could fail solely because unrelated local Git history/ref topology differs even though the H2 graph implementation is correct.

This violates the portability expectation of the permanent canonical test suite and incorrectly turns one-time salvage/review provenance into a runtime unit-test dependency.

### Required Fix

Modify only:

```text
tests/aios_engineering/harness/test_graph.py
```

Remove permanent test dependence on:

```text
refs/heads/ai/task-076
availability of unmerged historical commit fea85a8...
availability of baseline commit a51e9c33... for merge-base checks
```

Preserve deterministic regression coverage for the actual product contract:

```text
H2 public/policy identity is exact
forbidden graph-specific H4 identity tokens are absent
graph implementation does not claim H2 completion/H2.R2/H3-H8 capability
salvaged behavioral semantics remain covered by the existing static-import/provenance/bounds tests
```

It is acceptable to retain the exact historical SHA as a non-operational constant/assertion documenting the audited source, but the test must not require that Git object/ref/history to exist locally.

`TASK_076_BRANCH_MUTATED: NO`, exact historical-source provenance, and current-main branch ancestry are one-time execution/review evidence. They are already independently verified by the Bridge/GitHub review transaction and must not become permanent runtime dependencies of `pytest tests/`.

Do not modify production graph code for B1.

## Revalidation Required

Run exactly:

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_engineering/harness/test_graph.py tests/aios_engineering/harness/test_ranking.py tests/aios_engineering/harness/test_roles.py tests/aios_engineering/harness/test_experience.py -q
.\venv\Scripts\python.exe -m pytest tests/ -q
git diff --check
```

Then publish through canonical E4 FIX.

## Decision

```text
TASK-079: CHANGES_REQUIRED
APPROVED: NO
AUTO_MERGE_ELIGIBLE: NO
BLOCKERS_REMAINING: 1
B1_TEST_PORTABILITY: OPEN
PRODUCTION_GRAPH_CHANGE_REQUIRED: NO
H2_FORMAL_COMPLETION: NO
H3_H8_NEW_CAPABILITY: NONE
LIVE_PAID_API_AUTHORIZED: NO
```
