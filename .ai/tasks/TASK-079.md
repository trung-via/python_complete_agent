# TASK-079 — H2 Static Import Graph Salvage + Canonical Rebinding

STATUS: READY
PUBLISHER_PROFILE: CANONICAL_E4
CLASS: L2 — AIOS ENGINEERING H-SERIES / H2 RECOVERY
MILESTONE: H2
EXECUTOR_MODE: DUAL_EXECUTOR_ALLOWED
RECOMMENDED_EXECUTOR: codex

## Baseline

```text
MAIN_SHA: a51e9c33cd66dc262f13063747295609d7b7df97
TARGET_BRANCH: ai/task-079
CANONICAL_ROADMAP: .ai/roadmaps/H-SERIES-v1.0.md
CANONICAL_ROADMAP_BLOB_SHA: 41775383879c86dc68a7d87c0d705cfc8512f62d
CANONICAL_ROADMAP_FINGERPRINT: 449dd8bfa4867e74723a1e4a3f619779aebc0c77845a702491bef178a8bc4ce6
MILESTONE_COMPLETION_ARTIFACT: .ai/roadmaps/H-SERIES-v1.0.completions.json
MILESTONE_COMPLETION_ARTIFACT_BLOB_SHA: 864072a7444dd8d0ffdb234f0d03a323d898bf11
H1_COMPLETION_RECORD_FINGERPRINT: 6a93ae900dc9d1702d829cd378414291ffba3eaec572a7eac42118424165d8f1
H0_STATUS: FORMALLY_COMPLETE
H1_STATUS: FORMALLY_COMPLETE
H2_STATUS: OPEN_PARTIAL
PRESERVED_TASK_076_HEAD: fea85a8bc7f696c50fd5457b0cea3b5d8032b24f
PRESERVED_TASK_076_BRANCH: ai/task-076
PRESERVED_TASK_076_DISPOSITION: READ_ONLY_AUDIT_EVIDENCE
H3_NEW_WORK_AUTHORIZED: NO
H4_H8_AUTHORIZED: NO
NETWORK_CALL_ALLOWED: NO
LLM_CALL_ALLOWED: NO
PAID_API_CALL_ALLOWED: NO
AUTO_RETRY_ALLOWED: NO
AUTO_REROUTE_ALLOWED: NO
```

ROADMAP_BINDING_JSON: {"roadmap_id":"AIOS-ENGINEERING-H-SERIES","roadmap_version":"1.0","roadmap_blob_sha":"41775383879c86dc68a7d87c0d705cfc8512f62d","roadmap_fingerprint":"449dd8bfa4867e74723a1e4a3f619779aebc0c77845a702491bef178a8bc4ce6","roadmap_fingerprint_algorithm_version":"roadmap-sha256-v1","milestone":"H2","capability_id":"H2_STRUCTURAL_EXPERIENCE_GRAPH","requirement_bindings":["H2.R1","H2.R3","H2.R4"],"scope_in":["salvage exact-snapshot static Python import graph from preserved TASK-076 implementation","rebind all graph-specific H4 policy identity to canonical H2 supporting-capability identity","preserve deterministic provenance boundedness and unresolved/ambiguous resolution semantics","consume existing ranking/role evidence only as bounded supporting inputs"],"scope_out":["H2.R2 experience relationship graph","H2 milestone completion","new H3 work","H4 Knowledge Registry","H5-H8 capabilities","merging rebasing resetting or mutating ai/task-076"]}

## Machine-Readable E4 Inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/roadmaps/H-SERIES-v1.0.md","blob_sha":"41775383879c86dc68a7d87c0d705cfc8512f62d"},{"path":".ai/roadmaps/H-SERIES-v1.0.completions.json","blob_sha":"864072a7444dd8d0ffdb234f0d03a323d898bf11"},{"path":".ai/decisions/ADR-050-AIOS-ENGINEERING-CANONICAL-ROADMAP-LOCK-CONTROLLED-EVOLUTION-CONTRACT-LOCK.md","blob_sha":"334b610b2c221ac20b2b9946142a0baed8952690"},{"path":".ai/decisions/ADR-052-AIOS-ENGINEERING-H2-STATIC-IMPORT-GRAPH-REBIND-SALVAGE-CONTRACT-LOCK.md","blob_sha":"57343ac3238c4052ee0f59dafe639d9a5f6f10d5"},{"path":".ai/decisions/ADR-049-AIOS-ENGINEERING-H4-EXACT-SNAPSHOT-STATIC-IMPORT-DEPENDENCY-GRAPH-CONTRACT-LOCK.md","blob_sha":"8ce0dfd0058ca7f9d2bcf54fcc08fb125bdf6c07"},{"path":".ai/tasks/TASK-076.md","blob_sha":"21010f368b08116808ec8b30f241089526fa9e86"},{"path":".ai/reviews/REVIEW-076.md","blob_sha":"cf4dfc7253bc252746a6bfee1dd275784add416e"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["src/aios_engineering/harness/__init__.py","src/aios_engineering/harness/graph.py","tests/aios_engineering/harness/test_graph.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

The marker set above is the complete task authority. It grants no H2 completion, H3/H4-H8, network/model/provider, retry/reroute, merge, or mutation authority over `ai/task-076`.

## Objective

Recover the useful static Python import dependency graph implementation from exact historical commit:

```text
fea85a8bc7f696c50fd5457b0cea3b5d8032b24f
```

and port it onto current `main` as an explicitly bounded **canonical H2 supporting structural-graph capability**.

This task corrects authority/classification without discarding good implementation. It must not merge or rewrite history and must not claim that static imports alone complete canonical H2.

## 1. Recovery Source Is Exact SHA, Read-Only

The only authorized historical source is exact commit:

```text
fea85a8bc7f696c50fd5457b0cea3b5d8032b24f
```

Inspect only these historical paths as needed:

```text
src/aios_engineering/harness/graph.py
src/aios_engineering/harness/__init__.py
tests/aios_engineering/harness/test_graph.py
```

Preferred read pattern is exact Git-object inspection such as `git show <sha>:<path>`.

Forbidden:

```text
git checkout ai/task-076
git merge ai/task-076
git rebase ai/task-076
git reset ai/task-076
git cherry-pick fea85a8... as a whole commit
force-update ai/task-076
modify/delete ai/task-076
copy RESULT-076 into TASK-079 output
network fetch fallback if exact historical Git object is missing
```

If the exact historical object is unavailable locally, fail closed before productive porting.

## 2. Current Main Is the Only Implementation Baseline

All new code must be based on:

```text
MAIN_SHA: a51e9c33cd66dc262f13063747295609d7b7df97
```

Current-main H1 experience APIs, H2 ranking APIs, H3 role-summary APIs, and governance behavior are authoritative dependencies. Do not weaken or roll them back to make historical graph code fit.

The executor may adapt the salvaged graph implementation only within the three writable paths.

## 3. Canonical H2 Identity

The recovered graph is not H4.

At minimum the final public/policy surface must use an H2 import-graph identity equivalent to:

```python
H2_IMPORT_GRAPH_POLICY_VERSION = "h2-import-graph-v1"
MAX_H2_IMPORT_GRAPH_...
```

Final changed source/tests/exports must contain no graph-specific public/policy claim equivalent to:

```text
H4_GRAPH_POLICY_VERSION
h4-v1
MAX_H4_*
"H4 static Python import dependency graph"
"H4 dependency graph"
H4 graph receipt/operation labels
```

Neutral semantic domain names may remain when correct:

```python
RepositoryImportDependency
RepositoryDependencyGraphResult
```

Do not rename unrelated historical H3/H2 public APIs merely for cosmetic consistency.

## 4. H2.R1 Structural Slice

Preserve/port the static structural relationships:

```text
selected Python source file
    -> static import reference
    -> exact internal target when deterministically resolvable
```

The graph must distinguish conservatively among at least the historical resolution outcomes already implemented by TASK-076, including exact resolved internal targets and unresolved/ambiguous/non-internal references as applicable.

This is partial H2.R1 evidence only. Do not introduce a fake `component` identity merely to claim full file → symbol → component coverage.

## 5. H2.R3 Provenance / Determinism / Bounds

Before any body read, preserve exact upstream cross-binding/revalidation between the H2 ranking result and H3 role-summary result as implemented safely in the historical graph.

Preserve at minimum:

```text
exact task identity agreement
exact repository commit/tree agreement
exact H2 ranking/plan fingerprint agreement
exact H3 upstream fingerprint agreement
selected evidence positional/path/blob identity agreement
exact local Git snapshot/blob verification before parse
bounded Python body reads
bounded import/reference/edge counts
canonical stable ordering
graph/result fingerprint verification
conservative ambiguity/unresolved representation
zero-authority receipt
```

No mutable worktree source bytes may become graph provenance.

## 6. H2.R4 Supporting Ranking Boundary

The graph may consume current-main deterministic H2 ranking/selection as an input boundary.

It must preserve this invariant:

```text
ranking/selection supports graph construction
ranking/selection != structural graph
```

Do not rename current ranking implementation as the canonical graph and do not infer H2 completion from its historical PASS status.

## 7. Explicitly Out of Scope

Do NOT implement:

```text
H2.R2 component/invariant/task/review-finding/executor-experience graph
new component graph model
new experience graph model
H3 executor tendencies
H3 ownership expansion
H4 Invariant/Finding/Lesson/Skill registry
H5 retrieval
H6 context/learning compiler
H7 working memory/preflight
H8 evaluation/gardening/promotion
Bridge authority changes
roadmap changes
completion-record mutation
```

TASK-079 is a salvage/rebinding step, not the final canonical H2 task.

## 8. Local-Only / Zero-Authority Boundary

Graph implementation must remain local-only and advisory.

Forbidden:

```text
network access
LLM/model calls
provider API calls
paid API use
executor selection/substitution
retry/failover authority
Bridge task/review/state/lease/dispatch mutation
merge authority
runtime import/execution of discovered repository Python modules
```

Use static AST analysis only.

## 9. Public API and Compatibility

Update `src/aios_engineering/harness/__init__.py` with only the stable graph contracts/constants/functions that survive the H2 rebinding.

Do not expose private Git/body/AST helpers.

Existing current-main H0/H1/H2/H3 public exports must remain backward compatible except that no already-merged H4 graph public API exists on current main and therefore no H4 graph compatibility alias is required.

Do NOT add H4 aliases for the salvaged graph; that would preserve the drift as public API.

## Mandatory Tests

Create/port/update `tests/aios_engineering/harness/test_graph.py` to prove at minimum:

```text
HISTORICAL_SOURCE_SHA_EXACT: fea85a8bc7f696c50fd5457b0cea3b5d8032b24f
CURRENT_MAIN_BASELINE_PRESERVED: PASS
TASK_076_BRANCH_MUTATED: NO
H4_GRAPH_PUBLIC_IDENTITY_REMAINING: NO
H2_IMPORT_GRAPH_POLICY_IDENTITY: PASS

H2_H3_CROSS_BINDING_BEFORE_BODY_READ: PASS
EXACT_REPOSITORY_SNAPSHOT_BOUND: PASS
EXACT_BLOB_IDENTITY_BOUND: PASS
WORKTREE_SOURCE_BYTES_USED: NO
STATIC_AST_ONLY: PASS
RUNTIME_IMPORT_EXECUTION: NO

STATIC_IMPORT_EXTRACTION: PASS
FROM_IMPORT_EXTRACTION: PASS
RELATIVE_IMPORT_HANDLING: PASS
EXACT_INTERNAL_TARGET_RESOLUTION: PASS
AMBIGUOUS_INTERNAL_TARGET: CONSERVATIVE
UNRESOLVED_REFERENCE: CONSERVATIVE
NON_INTERNAL_REFERENCE: CONSERVATIVE
CANONICAL_EDGE_ORDER: PASS
GRAPH_FINGERPRINT_TAMPER_EVIDENT: PASS
SNAPSHOT_CHANGE_FINGERPRINT_SENSITIVE: PASS
UPSTREAM_RANKING_CHANGE_FINGERPRINT_SENSITIVE: PASS
UPSTREAM_H3_CHANGE_FINGERPRINT_SENSITIVE: PASS

BODY_READ_BOUND: ENFORCED
REFERENCE_COUNT_BOUND: ENFORCED
EDGE_COUNT_BOUND: ENFORCED
MALFORMED_OR_UNSAFE_GIT_EVIDENCE: FAIL_CLOSED
ZERO_AUTHORITY_RECEIPT: PASS
NETWORK_USED: NO
LLM_USED: NO
PAID_API_USED: NO

H2_R2_IMPLEMENTED: NO
H2_COMPLETE_CLAIMED: NO
H3_NEW_CAPABILITY: NO
H4_H8_IMPLEMENTED: NO
```

Also add a regression assertion that the final changed graph source/export/test text contains none of the forbidden graph-specific H4 identity tokens listed in section 3.

## Validation Commands

Run exactly:

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_engineering/harness/test_graph.py tests/aios_engineering/harness/test_ranking.py tests/aios_engineering/harness/test_roles.py tests/aios_engineering/harness/test_experience.py -q
.\venv\Scripts\python.exe -m pytest tests/ -q
git diff --check
```

Use canonical Bridge E4 publication only.

## Acceptance Boundary

TASK-079 is reviewable only when:

```text
ROADMAP_BINDING: H2 / H2.R1 + H2.R3 + H2.R4 EXACT
H1_FORMAL_COMPLETION_GATE: SATISFIED
TASK_076_HISTORY: PRESERVED
TASK_076_IMPLEMENTATION: SAFELY_PORTED_TO_CURRENT_MAIN
GRAPH_H4_IDENTITY: REMOVED
H2_STATIC_IMPORT_GRAPH_IDENTITY: LOCKED
H2_R1_PARTIAL_STRUCTURAL_EVIDENCE: PASS
H2_R3_PROVENANCE_DETERMINISM_BOUNDS: PASS
H2_R4_SUPPORTING_RANKING_BOUNDARY: PASS
H2_R2: NOT_IMPLEMENTED
H2_FORMAL_COMPLETION: NO
H3_H8_NEW_CAPABILITY: NONE
FULL_REPOSITORY_TESTS: PASS
NETWORK_LLM_PAID_API: NONE
```

A PASS for TASK-079 will make the import-graph slice canonical H2 evidence. It will **not** complete H2. The next H2 work must address the remaining file → symbol → component coverage and H2.R2 experience relationships before any H2 completion record can be minted.
