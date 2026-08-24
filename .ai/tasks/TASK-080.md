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

The marker set above is the complete execution authority. It grants no H2 formal-completion mutation, H3/H4-H8 work, Bridge authority, network/model/provider call, paid API, retry, reroute, or merge authority.

## Objective

Implement the final canonical H2 graph capability required by ADR-053 by composing current reviewed evidence rather than duplicating earlier stages.

The final H2 data flow must be equivalent to:

```text
H1 RepositoryDiscoveryResult
        │
        ├── H2 ranking/selection
        │       │
        │       └── supporting role/symbol summaries
        │               │
        │               └── TASK-079 static import graph
        │
H1 RepositoryExperienceManifest
 repository snapshot + control-plane snapshot
        │
        ▼
H2 Canonical Structural + Experience Graph
        │
        ├── file → symbol → structural component
        ├── static import dependencies (bound upstream evidence)
        └── evidence-only task/review/executor/invariant relationships
        │
        ▼
combined deterministic graph fingerprint + zero-authority receipt
```

Do not rewrite `roles.py`, `experience.py`, `ranking.py`, `discovery.py`, or `graph.py` to make the composition easier. Treat their merged contracts as upstream evidence.

## 1. New Canonical H2 Composition Module

Create:

```text
src/aios_engineering/harness/structural_experience_graph.py
```

Use a distinct policy identity equivalent to:

```python
H2_STRUCTURAL_EXPERIENCE_GRAPH_POLICY_VERSION = "h2-structural-experience-v1"
STRUCTURAL_EXPERIENCE_GRAPH_SCHEMA_VERSION = "1"
```

Required stable public concepts should be equivalent to:

```python
class StructuralComponentKind(...):
    PYTHON_PACKAGE = "PYTHON_PACKAGE"
    STANDALONE_PYTHON_MODULE = "STANDALONE_PYTHON_MODULE"

class H2GraphNodeKind(...): ...
class H2GraphRelation(...): ...
class H2ExperienceParseStatus(...): ...

@dataclass(frozen=True)
class StructuralComponent: ...
@dataclass(frozen=True)
class StructuralSymbolRef: ...
@dataclass(frozen=True)
class H2GraphNode: ...
@dataclass(frozen=True)
class H2GraphEdge: ...
@dataclass(frozen=True)
class H2UnresolvedExperienceRecord: ...
@dataclass(frozen=True)
class RepositoryStructuralExperienceGraphResult: ...

def build_repository_structural_experience_graph(...): ...
```

Exact class names may be refined for clarity, but there must be one immutable combined result and one deterministic builder authority for canonical H2 composition.

## 2. Required Upstream Inputs and Exact Cross-Binding

The builder must consume already-frozen upstream values equivalent to:

```text
RepositoryDiscoveryResult
RepositoryRankingResult
RepositoryRoleSummaryResult
RepositoryDependencyGraphResult
RepositoryExperienceManifest
```

Before any experience artifact body read or graph emission, fail closed unless at minimum:

```text
all repository snapshots are identical
ranking task_id is compatible with the graph build task identity
role summaries are exactly bound to the supplied ranking identity
import graph is exactly bound to supplied ranking + role summary identities
experience manifest repository snapshot equals structural repository snapshot
experience manifest discovery/candidate fingerprints equal supplied discovery identity
all upstream fingerprints validate under their own immutable dataclass contracts
control-plane snapshot is exact and present
```

Do not repair contradictory upstream evidence by choosing one source.

## 3. H2.R1 — File → Symbol → Structural Component

Reuse `RepositoryRoleSummaryResult` top-level Python symbol summaries. Do not independently AST-parse files again for symbols.

For each eligible selected Python file:

```text
FILE node
  ↓ CONTAINS_SYMBOL
SYMBOL node
  ↓ BELONGS_TO_COMPONENT
STRUCTURAL COMPONENT node
```

Also emit direct `FILE_BELONGS_TO_COMPONENT` when useful for task-scope linking.

### Package component rule

Determine structural package identity from the exact repository discovery evidence only:

1. take the Python file's parent path;
2. enumerate enclosing directories evidenced to contain exact `__init__.py` files in the same frozen repository snapshot;
3. choose the nearest/deepest enclosing package directory;
4. component kind = `PYTHON_PACKAGE`;
5. component id must be deterministic from kind + canonical path.

If no enclosing package directory is evidenced:

```text
component kind = STANDALONE_PYTHON_MODULE
component path = exact file path
```

Do not infer component ownership/responsibility from names or prose.

Non-Python selected evidence may remain outside this structural component slice unless an exact structural rule is explicitly locked by ADR-053; do not invent generic components merely for coverage.

## 4. Import Graph Integration

The canonical combined H2 graph must bind the existing TASK-079 static import graph fingerprint and may expose/import its exact dependencies as canonical structural edges or a bound subgraph reference.

Do not duplicate static-import parsing.

At minimum prove:

```text
combined graph changes if import-graph fingerprint changes
resolved import target component can be linked only when target path maps deterministically
ambiguous/unresolved import targets remain conservative
TASK-079 H2_IMPORT_GRAPH_POLICY_VERSION remains unchanged
no H4 graph identity returns
```

## 5. H2.R2 — Experience Entity Types

Support bounded canonical node identities for at least:

```text
TASK
REVIEW_FINDING
EXECUTOR
INVARIANT
COMPONENT
```

A node identity must include enough stable evidence to prevent collision across task IDs / finding IDs / executors / invariant IDs / components.

Do not create H4 knowledge objects or lifecycle state. H2 invariant nodes are relationship identities only.

## 6. Closed Experience Evidence Grammar

Parse experience artifact bodies only when their `ExperienceArtifactRef` already exists in the supplied `RepositoryExperienceManifest`.

Use exact bounded body reads from local Git objects. Recompute/verify exact Git blob identity before parsing.

### TASK evidence

Canonical task ID comes from artifact path:

```text
.ai/tasks/TASK-NNN.md
```

The only task → component scope source authorized here is exact top-level machine marker:

```text
EXECUTOR_ALLOWED_PATHS_JSON: [...]
```

Reuse the marker grammar semantically but do not import Bridge authority modules into H-Series. Implement a local pure bounded parser for the exact JSON array syntax needed by H2.

Each allowed path may create `TASK_TOUCHES_COMPONENT` only when the path maps deterministically to a structural component. Otherwise create bounded unresolved accounting.

Paths under Bridge/runtime control namespaces that do not map to the selected H2 structural graph must not fabricate a component.

### RESULT evidence

Parse only a closed `## Review Manifest` fenced YAML-like block with exact scalar lines needed by H2, at minimum:

```text
TASK_ID: TASK-NNN
EXECUTOR_ID: <bounded executor token>
```

Require task ID to match RESULT artifact path identity before emitting:

```text
TASK_EXECUTED_BY_EXECUTOR
```

Do not infer executor from recommended executor, branch name, commit author, or prose.

### REVIEW finding evidence

Canonical review task identity comes from:

```text
.ai/reviews/REVIEW-NNN.md
```

Recognize bounded closed finding headings equivalent to:

```text
### B1 — <bounded title>
### B2 - <bounded title>
```

Emit:

```text
TASK_HAS_REVIEW_FINDING
```

A finding may emit `REVIEW_FINDING_RELATES_TO_COMPONENT` only from an exact path reference captured under a locked closed rule in the finding section/body. Do not use finding-title keyword similarity.

### INVARIANT evidence

Support one explicit local H2 marker grammar equivalent to:

```text
H2_INVARIANT_REFS_JSON: [{"invariant_id":"...","component_path":"..."}, ...]
```

The marker is relationship evidence only. It must be strict JSON, bounded, duplicate-free, canonical-path validated, and may appear only in experience artifacts whose kind is TASK, REVIEW, DECISION, or LEARNING.

When valid and component path resolves:

```text
TASK REFERENCES_INVARIANT INVARIANT      (when TASK evidence supplies marker)
INVARIANT RELATES_TO_COMPONENT COMPONENT
```

For non-TASK evidence, record provenance linkage without inventing a task relation.

Existing legacy prose that merely says "invariant" must not generate nodes.

## 7. Conservative Parse / Unresolved Accounting

Define closed parse states/reasons for cases such as:

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

Malformed explicit machine evidence must fail closed when ambiguity could corrupt graph identity. Absence of optional machine evidence should be represented as deterministic no-edge/accounting, not treated as an error.

Do not silently drop parsed-but-unresolved evidence.

## 8. Exact Body Read Contract

Before parsing each experience blob:

```text
verify local Git object type == blob
obtain bounded exact byte size
read with hard per-artifact bound
recompute canonical Git blob SHA-1 over exact bytes
require SHA == ExperienceArtifactRef.blob_sha
only then decode/parse
```

Use the same closed Git child-environment discipline already established in H1/H3. No lazy network fetch or remote fallback.

Operational Git/decoder/parser errors must fail closed and must not be converted into repository evidence.

## 9. Hard Bounds

Lock finite constants for at least:

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

Use conservative values compatible with current repository size. Validate bounds before returning a complete result.

No unbounded regex over entire arbitrarily large bodies; body bytes are bounded first.

## 10. Canonical Graph Node / Edge Ordering

Define one stable ordering independent of Python set/dict iteration.

Suggested identities:

```text
component: component kind + canonical path
symbol: file path + blob SHA + symbol locator
TASK: canonical task id
review finding: task id + B-number + bounded title fingerprint
executor: exact bounded executor token
invariant: exact bounded invariant id
```

Every node and edge must have a deterministic fingerprint.

Duplicate exact nodes/edges are deduplicated only when their complete identity/evidence agrees. Contradictory duplicate identities fail closed.

## 11. Combined Result Fingerprint

`RepositoryStructuralExperienceGraphResult` must bind at minimum:

```text
schema version
policy version
repository snapshot
control-plane snapshot
repository discovery fingerprint
repository candidate-set fingerprint
H1 experience manifest fingerprint
H2 ranking result fingerprint / relevance-plan identity
role summary result fingerprint
TASK-079 import graph fingerprint
component nodes
symbol nodes
experience nodes
all structural/experience edges
unresolved/accounting records
zero-authority state
```

Changing any upstream fingerprint, exact snapshot, component mapping, symbol identity, task/finding/executor/invariant identity, edge, or unresolved record must change/reject the combined fingerprint.

Canonical serialization must use existing Harness fingerprint helpers.

## 12. Zero-Authority Receipt

Return a `HarnessReceipt` operation name equivalent to:

```text
h2_repository_structural_experience_graph
```

Receipt must prove local-only advisory construction and exact candidate/result fingerprint binding.

Forbidden:

```text
network calls
LLM/model calls
provider calls
paid API use
runtime import/execution of repository Python modules
Bridge task/review/state/lease/dispatch mutation
executor routing/substitution
retry/failover
merge authority
H3 ownership inference
H3 executor tendency inference
H4 knowledge lifecycle
```

## 13. Public API

Update `src/aios_engineering/harness/__init__.py` only with stable H2 structural-experience graph contracts/constants/build function.

Do not export private Git readers/parsers/regex helpers.

Do not rename existing H1/H2/H3 supporting APIs.

No compatibility aliases for historically incorrect milestone identities are allowed.

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

Build synthetic exact Git fixtures for closed experience grammar. Permanent tests must not depend on unmerged local task branches or historical local refs.

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

A PASS for TASK-080 may provide the remaining implementation evidence needed to mint a separate formal H2 completion record. TASK-080 PASS alone must not open H3.