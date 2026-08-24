# TASK-080 — H2 Canonical Structural + Experience Graph Completion Implementation

STATUS: READY
PUBLISHER_PROFILE: CANONICAL_E4
CLASS: L3 — AIOS ENGINEERING H-SERIES / H2 CANONICAL COMPLETION IMPLEMENTATION
MILESTONE: H2
EXECUTOR_MODE: DUAL_EXECUTOR_ALLOWED
RECOMMENDED_EXECUTOR: codex

## Baseline

```text
MAIN_SHA: a2fe1e7273503d6dc1863ae00ac3c026192bb2a2
TARGET_BRANCH: ai/task-080
CANONICAL_ROADMAP: .ai/roadmaps/H-SERIES-v1.0.md
CANONICAL_ROADMAP_BLOB_SHA: 41775383879c86dc68a7d87c0d705cfc8512f62d
CANONICAL_ROADMAP_FINGERPRINT: 449dd8bfa4867e74723a1e4a3f619779aebc0c77845a702491bef178a8bc4ce6
MILESTONE_COMPLETION_ARTIFACT: .ai/roadmaps/H-SERIES-v1.0.completions.json
MILESTONE_COMPLETION_ARTIFACT_BLOB_SHA: 864072a7444dd8d0ffdb234f0d03a323d898bf11
H0_STATUS: FORMALLY_COMPLETE
H1_STATUS: FORMALLY_COMPLETE
H2_STATUS: OPEN_PARTIAL
TASK_079_STATUS: PASS_MERGED
TASK_079_MAIN_SHA: a2fe1e7273503d6dc1863ae00ac3c026192bb2a2
H3_NEW_WORK_AUTHORIZED: NO
H4_H8_AUTHORIZED: NO
NETWORK_CALL_ALLOWED: NO
LLM_CALL_ALLOWED: NO
PAID_API_CALL_ALLOWED: NO
AUTO_RETRY_ALLOWED: NO
AUTO_REROUTE_ALLOWED: NO
```

ROADMAP_BINDING_JSON: {"roadmap_id":"AIOS-ENGINEERING-H-SERIES","roadmap_version":"1.0","roadmap_blob_sha":"41775383879c86dc68a7d87c0d705cfc8512f62d","roadmap_fingerprint":"449dd8bfa4867e74723a1e4a3f619779aebc0c77845a702491bef178a8bc4ce6","roadmap_fingerprint_algorithm_version":"roadmap-sha256-v1","milestone":"H2","capability_id":"H2_STRUCTURAL_EXPERIENCE_GRAPH","requirement_bindings":["H2.R1","H2.R2","H2.R3","H2.R4"],"scope_in":["compose canonical file-symbol-component structural graph from exact H1/H2/supporting symbol evidence","build bounded evidence-only component/invariant/task/review-finding/executor experience relationships","bind one canonical combined graph identity to exact repository and control-plane provenance","preserve deterministic H2 ranking as supporting input only"],"scope_out":["formal H2 milestone completion record","H3 semantic ownership or must-own/must-not-own summaries","H3 executor tendencies","H4 knowledge registry or invariant lifecycle","H5-H8 capabilities","Bridge authority mutation","network LLM provider or paid API calls"]}

## Machine-Readable E4 Inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/roadmaps/H-SERIES-v1.0.md","blob_sha":"41775383879c86dc68a7d87c0d705cfc8512f62d"},{"path":".ai/roadmaps/H-SERIES-v1.0.completions.json","blob_sha":"864072a7444dd8d0ffdb234f0d03a323d898bf11"},{"path":".ai/decisions/ADR-050-AIOS-ENGINEERING-CANONICAL-ROADMAP-LOCK-CONTROLLED-EVOLUTION-CONTRACT-LOCK.md","blob_sha":"334b610b2c221ac20b2b9946142a0baed8952690"},{"path":".ai/decisions/ADR-053-AIOS-ENGINEERING-H2-CANONICAL-STRUCTURAL-EXPERIENCE-GRAPH-COMPLETION-CONTRACT-LOCK.md","blob_sha":"5f484356baf69aaf0f5426c0dbb150c04a9d22f9"},{"path":".ai/reviews/REVIEW-079.md","blob_sha":"37e7611bc0c80415eedd597bb3c6cab4d1b0fa58"},{"path":".ai/reviews/REVIEW-078.md","blob_sha":"c3b352169e92f028089faba269bcb2da09c7740e"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["src/aios_engineering/harness/__init__.py","src/aios_engineering/harness/structural_experience_graph.py","tests/aios_engineering/harness/test_structural_experience_graph.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

The three E4 machine markers above are the complete execution authority. They grant no H2 formal-completion mutation, H3/H4-H8 work, Bridge authority, network/model/provider call, paid API, retry, reroute, or merge authority.

## Objective

Implement the final canonical H2 graph composition required by ADR-053 by composing current reviewed evidence instead of duplicating earlier stages.

Required data flow:

```text
H1 RepositoryDiscoveryResult
        +
H2 RepositoryRankingResult
        +
RepositoryRoleSummaryResult (supporting symbol evidence)
        +
RepositoryDependencyGraphResult (TASK-079 import graph)
        +
H1 RepositoryExperienceManifest
        ↓
RepositoryStructuralExperienceGraphResult
        ├── file → symbol → structural component
        ├── bound static import evidence
        └── evidence-only task/review/executor/invariant relationships
        ↓
combined deterministic fingerprint + zero-authority receipt
```

Do not modify `roles.py`, `experience.py`, `ranking.py`, `discovery.py`, or `graph.py`. Treat those merged contracts as immutable upstream evidence.

## 1. Canonical H2 Composition Module

Create:

```text
src/aios_engineering/harness/structural_experience_graph.py
```

Use distinct policy identity:

```python
H2_STRUCTURAL_EXPERIENCE_GRAPH_POLICY_VERSION = "h2-structural-experience-v1"
STRUCTURAL_EXPERIENCE_GRAPH_SCHEMA_VERSION = "1"
```

Provide immutable public concepts equivalent to:

```python
StructuralComponentKind
H2GraphNodeKind
H2GraphRelation
H2ExperienceParseStatus
StructuralComponent
StructuralSymbolRef
H2GraphNode
H2GraphEdge
H2UnresolvedExperienceRecord
RepositoryStructuralExperienceGraphResult
build_repository_structural_experience_graph(...)
```

Exact names may be refined, but there must be one deterministic builder authority and one immutable combined result.

## 2. Exact Upstream Cross-Binding

Before any experience-body read or graph emission, fail closed unless:

```text
repository snapshots are identical across discovery/ranking/roles/import graph/experience manifest
ranking task identity is compatible with graph-build task identity
role summaries are exactly bound to supplied ranking identity
import graph is exactly bound to supplied ranking + role summary identities
experience manifest repository snapshot equals structural repository snapshot
experience manifest discovery/candidate fingerprints equal supplied discovery identity
upstream immutable fingerprints validate
control-plane snapshot is exact and present
```

Contradictory upstream evidence must be rejected, never repaired by preference.

## 3. H2.R1 — File → Symbol → Structural Component

Reuse top-level Python symbol summaries from `RepositoryRoleSummaryResult`. Do not AST-parse source files again for symbols.

For eligible selected Python files emit deterministic relations equivalent to:

```text
FILE --CONTAINS_SYMBOL--> SYMBOL
SYMBOL --BELONGS_TO_COMPONENT--> COMPONENT
FILE --FILE_BELONGS_TO_COMPONENT--> COMPONENT
```

Structural component rule:

1. derive from exact repository discovery evidence only;
2. inspect enclosing directories evidenced to contain exact `__init__.py` files;
3. choose the nearest/deepest enclosing package directory;
4. classify as `PYTHON_PACKAGE`;
5. if no package directory is evidenced, use exact file path as `STANDALONE_PYTHON_MODULE`;
6. component ID is deterministic from kind + canonical path.

Do not infer ownership, responsibility, must-own, or must-not-own semantics in H2.

## 4. Existing Import Graph Integration

Bind the TASK-079 static-import graph fingerprint into the combined H2 result. Do not reparse imports.

At minimum:

```text
combined fingerprint changes/rejects if import-graph fingerprint changes
resolved import targets link to structural components only when mapping is deterministic
ambiguous/unresolved import targets remain conservative
H2_IMPORT_GRAPH_POLICY_VERSION remains unchanged
no H4 graph identity returns
```

## 5. H2.R2 Experience Node Types

Support bounded canonical node identities for at least:

```text
TASK
REVIEW_FINDING
EXECUTOR
INVARIANT
COMPONENT
```

H2 invariant nodes are relationship identities only. Do not create H4 knowledge entities, confidence state, lifecycle, promotion, or precedence semantics.

## 6. Closed Experience Evidence Grammar

Only parse bodies whose `ExperienceArtifactRef` already exists in the supplied `RepositoryExperienceManifest`.

Use exact bounded local Git blob reads and verify exact blob identity before parsing.

### TASK evidence

Canonical task identity comes only from `.ai/tasks/TASK-NNN.md` path identity.

For task-to-component scope, use only the single top-level allowed-path machine marker declared in the Machine-Readable E4 Inputs grammar. In prose and tests refer to that marker by the name `EXECUTOR_ALLOWED_PATHS_JSON` without introducing a second marker line.

Implement a local pure bounded parser for its strict JSON-array payload. Do not import Bridge authority modules.

Each allowed path may emit `TASK_TOUCHES_COMPONENT` only when it maps deterministically to an H2 structural component. Otherwise emit bounded unresolved accounting.

### RESULT evidence

Parse only a closed `## Review Manifest` fenced block with exact scalar fields needed by H2, at minimum:

```text
TASK_ID = canonical TASK-NNN
EXECUTOR_ID = bounded executor token
```

Require task identity to match RESULT artifact path before emitting `TASK_EXECUTED_BY_EXECUTOR`.

Do not infer executor from recommended executor, branch name, commit author, or prose.

### REVIEW finding evidence

Canonical review task identity comes from `.ai/reviews/REVIEW-NNN.md`.

Recognize bounded closed headings equivalent to `B1`, `B2`, etc. Emit `TASK_HAS_REVIEW_FINDING`.

A finding may emit `REVIEW_FINDING_RELATES_TO_COMPONENT` only from an exact path reference captured by a locked closed rule in the finding body. Finding-title keyword similarity is forbidden.

### INVARIANT evidence

Support one explicit H2 marker grammar named `H2_INVARIANT_REFS_JSON` whose payload is a bounded strict JSON array of objects containing:

```text
invariant_id
component_path
```

This is relationship evidence only. It may appear only in TASK, REVIEW, DECISION, or LEARNING experience artifacts. Valid task evidence may emit task→invariant plus invariant→component relations. Non-task evidence may bind invariant provenance without inventing task relations.

Legacy prose mentioning "invariant" must not create invariant nodes.

## 7. Conservative Parse / Unresolved Accounting

Use closed statuses/reasons including equivalents of:

```text
NOT_APPLICABLE
NO_MACHINE_EVIDENCE
PATH_NOT_IN_STRUCTURAL_GRAPH
MALFORMED_MACHINE_EVIDENCE
TASK_ID_MISMATCH
AMBIGUOUS_COMPONENT
BODY_BOUND_EXCEEDED
UNSUPPORTED_ARTIFACT_KIND
```

Malformed explicit machine evidence fails closed when it could corrupt graph identity. Missing optional evidence produces deterministic no-edge/accounting rather than fabricated relations.

Parsed-but-unresolved evidence must never be silently dropped.

## 8. Exact Body Read Contract

Before parsing an experience blob:

```text
verify local Git object type == blob
obtain bounded exact byte size
read exact bytes under per-artifact and total-body bounds
recompute canonical Git blob SHA-1
require SHA == ExperienceArtifactRef.blob_sha
decode/parse only after identity verification
```

Use the existing closed Git child-environment discipline. No lazy fetch, remote fallback, network, runtime Python import, or repository code execution.

Operational Git/decoder/parser errors fail closed.

## 9. Hard Bounds

Define finite constants for at least:

```text
MAX_H2_GRAPH_COMPONENTS
MAX_H2_GRAPH_SYMBOLS
MAX_H2_GRAPH_STRUCTURAL_EDGES
MAX_H2_GRAPH_EXPERIENCE_ARTIFACTS
MAX_H2_GRAPH_EXPERIENCE_BLOB_BYTES
MAX_H2_GRAPH_TOTAL_EXPERIENCE_BYTES
MAX_H2_GRAPH_TASKS
MAX_H2_GRAPH_REVIEW_FINDINGS
MAX_H2_GRAPH_EXECUTORS
MAX_H2_GRAPH_INVARIANTS
MAX_H2_GRAPH_EXPERIENCE_EDGES
MAX_H2_GRAPH_UNRESOLVED_RECORDS
MAX_H2_GRAPH_MACHINE_MARKER_BYTES
MAX_H2_GRAPH_FINGERPRINT_PAYLOAD_BYTES
```

Validate bounds before returning a complete result. Body bytes must be bounded before regex/text parsing.

## 10. Deterministic Identity and Ordering

Define stable canonical ordering independent of set/dict iteration.

Suggested identities:

```text
component = kind + canonical path
symbol = file path + blob SHA + symbol locator
task = canonical task id
review finding = task id + finding number + bounded title fingerprint
executor = exact bounded executor token
invariant = exact bounded invariant id
```

Every node and edge must carry a deterministic fingerprint. Exact duplicates may deduplicate only when complete identity/evidence agrees; contradictory duplicates fail closed.

## 11. Combined Graph Fingerprint

`RepositoryStructuralExperienceGraphResult` must bind at minimum:

```text
schema version
policy version
repository snapshot
control-plane snapshot
repository discovery fingerprint
repository candidate-set fingerprint
H1 experience manifest fingerprint
H2 ranking/relevance identity
role summary result fingerprint
TASK-079 import graph fingerprint
component nodes
symbol nodes
experience nodes
structural + experience edges
unresolved/accounting records
zero-authority state
```

Changing any upstream fingerprint, exact snapshot, component mapping, symbol identity, experience identity, edge, or unresolved record must change or invalidate the combined fingerprint.

Use existing Harness canonical serialization/fingerprint helpers.

## 12. Zero-Authority Receipt

Return a `HarnessReceipt` operation equivalent to:

```text
h2_repository_structural_experience_graph
```

Receipt must bind exact candidate/result fingerprints and local-only advisory construction.

Forbidden:

```text
network / LLM / provider / paid API calls
runtime import/execution of repository Python modules
Bridge task/review/state/lease/dispatch mutation
executor routing/substitution
retry/failover
merge authority
H3 ownership inference
H3 executor tendency inference
H4 knowledge lifecycle
H5-H8 capability work
```

## 13. Public API

Update `src/aios_engineering/harness/__init__.py` only with stable H2 structural-experience contracts/constants/builder.

Do not export private Git readers/parsers/regex helpers and do not rename existing H1/H2/H3 supporting APIs.

## 14. Mandatory Tests

Create `tests/aios_engineering/harness/test_structural_experience_graph.py` proving at minimum:

```text
H1_FORMAL_COMPLETION_GATE_INPUT: PRESERVED
H2_CANONICAL_POLICY_IDENTITY: PASS
UPSTREAM_SNAPSHOT_CROSS_BINDING: PASS
UPSTREAM_RANKING_MISMATCH: FAIL_CLOSED
UPSTREAM_ROLE_SUMMARY_MISMATCH: FAIL_CLOSED
UPSTREAM_IMPORT_GRAPH_MISMATCH: FAIL_CLOSED
UPSTREAM_EXPERIENCE_MANIFEST_MISMATCH: FAIL_CLOSED
PYTHON_PACKAGE_COMPONENT_DEEPEST_EXACT: PASS
STANDALONE_MODULE_COMPONENT: PASS
FILE_TO_SYMBOL_EDGE: PASS
SYMBOL_TO_COMPONENT_EDGE: PASS
FILE_TO_COMPONENT_EDGE: PASS
NO_OWNERSHIP_SEMANTICS_IN_H2: PASS
NO_SECOND_SYMBOL_AST_PARSER: PASS
IMPORT_GRAPH_FINGERPRINT_BOUND: PASS
RESOLVED_IMPORT_COMPONENT_LINK: PASS
AMBIGUOUS_IMPORT_COMPONENT_LINK: CONSERVATIVE
UNRESOLVED_IMPORT_COMPONENT_LINK: CONSERVATIVE
TASK_PATH_IDENTITY: PASS
TASK_ALLOWED_PATH_TO_COMPONENT: PASS
TASK_UNMATCHED_PATH: UNRESOLVED_ACCOUNTED
RESULT_REVIEW_MANIFEST_TASK_EXECUTOR: PASS
RESULT_TASK_ID_MISMATCH: FAIL_CLOSED
REVIEW_FINDING_CLOSED_HEADING: PASS
REVIEW_FINDING_PATH_TO_COMPONENT: PASS
REVIEW_FINDING_TITLE_ONLY_DOES_NOT_INFER_COMPONENT: PASS
INVARIANT_EXPLICIT_MARKER: PASS
LEGACY_INVARIANT_PROSE_INFERRED: NO
NO_INVARIANT_EVIDENCE_ZERO_NODES_ALLOWED: PASS
EXACT_CONTROL_BLOB_IDENTITY: PASS
EXACT_REPOSITORY_EXPERIENCE_BLOB_IDENTITY: PASS
WORKTREE_EXPERIENCE_BYTES_USED: NO
MISSING_LOCAL_GIT_OBJECT: FAIL_CLOSED
NETWORK_FALLBACK: NO
BODY_BOUND: ENFORCED
TOTAL_BODY_BOUND: ENFORCED
NODE_EDGE_BOUNDS: ENFORCED
UNRESOLVED_BOUND: ENFORCED
CANONICAL_NODE_ORDER: PASS
CANONICAL_EDGE_ORDER: PASS
NODE_FINGERPRINT_TAMPER_EVIDENT: PASS
EDGE_FINGERPRINT_TAMPER_EVIDENT: PASS
UPSTREAM_FINGERPRINT_CHANGE_SENSITIVE: PASS
UNRESOLVED_CHANGE_SENSITIVE: PASS
COMBINED_GRAPH_FINGERPRINT_TAMPER_EVIDENT: PASS
ZERO_AUTHORITY_RECEIPT: PASS
H2_R1_IMPLEMENTATION_EVIDENCE: PASS
H2_R2_IMPLEMENTATION_EVIDENCE: PASS
H2_R3_COMBINED_GRAPH_EVIDENCE: PASS
H2_R4_RANKING_REMAINS_SUPPORTING_ONLY: PASS
H2_COMPLETE_CLAIMED_BY_CODE: NO
H3_NEW_CAPABILITY: NO
H4_H8_IMPLEMENTED: NO
NETWORK_USED: NO
LLM_USED: NO
PAID_API_USED: NO
```

Use synthetic exact Git fixtures. Permanent tests must not depend on unmerged local task branches or historical local refs.

## 15. Validation Commands

Run exactly:

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_engineering/harness/test_structural_experience_graph.py tests/aios_engineering/harness/test_graph.py tests/aios_engineering/harness/test_roles.py tests/aios_engineering/harness/test_ranking.py tests/aios_engineering/harness/test_experience.py -q
.\venv\Scripts\python.exe -m pytest tests/ -q
git diff --check
```

Publish only through canonical Bridge E4.

## 16. Acceptance Boundary

TASK-080 is reviewable only when:

```text
ROADMAP_BINDING: H2 / H2.R1 + H2.R2 + H2.R3 + H2.R4 EXACT
H0_H1_FORMAL_COMPLETION_GATE: SATISFIED
H2_STRUCTURAL_COMPONENT_SEMANTICS: EXACT_AND_STRUCTURAL_ONLY
H2_FILE_SYMBOL_COMPONENT_GRAPH: PASS
H2_EXPERIENCE_RELATION_GRAPH: PASS
H2_COMBINED_GRAPH_IDENTITY: PASS
EXACT_REPOSITORY_CONTROL_PROVENANCE: PASS
BOUNDS_AND_CONSERVATIVE_UNRESOLVED: PASS
H2_RANKING: SUPPORTING_ONLY
H3_OWNERSHIP_TENDENCIES: NOT_IMPLEMENTED
H4_KNOWLEDGE_REGISTRY: NOT_IMPLEMENTED
H5_H8: NOT_IMPLEMENTED
H2_FORMAL_COMPLETION_RECORD_MUTATED: NO
FULL_REPOSITORY_TESTS: PASS
NETWORK_LLM_PAID_API: NONE
```

A PASS for TASK-080 may provide the remaining implementation evidence required for a separate formal H2 completion record. TASK-080 PASS alone must not open H3.
