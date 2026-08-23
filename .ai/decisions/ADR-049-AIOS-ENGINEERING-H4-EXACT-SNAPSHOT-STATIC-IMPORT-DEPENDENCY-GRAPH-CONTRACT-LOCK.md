# ADR-049 — AIOS Engineering H4 Exact-Snapshot Static Import Dependency Graph Contract Lock

STATUS: LOCKED
DATE: 2026-08-23
SCOPE: AIOS Engineering H-Series H4
BASELINE_MAIN_SHA: 60f18b3be650725f097305e38c1c36b6b434e62b
H0_STATUS: COMPLETE
H1_STATUS: COMPLETE
H2_STATUS: COMPLETE
H3_STATUS: COMPLETE
H4_AUTHORIZED: YES
H5_IMPLEMENTATION_AUTHORIZED: NO

## 1. Decision

H4 converts the exact, bounded H2/H3 repository intelligence into a deterministic static Python import dependency graph.

H4 consumes one exact H2 `RepositoryRankingResult` and one exact H3 `RepositoryRoleSummaryResult`, verifies their cross-bindings and exact Git snapshot, re-reads only H2-selected Python blobs that H3 marked `PARSED`, extracts static `import` / `from ... import ...` references without executing repository code, deterministically resolves internal targets only when resolution is exact and unambiguous, and emits an immutable fingerprint-bound dependency graph plus a zero-authority H0 `HarnessReceipt`.

Locked flow:

```text
H2 RepositoryRankingResult
        +
H3 RepositoryRoleSummaryResult
        ↓
exact task/snapshot/ranking/plan/H3 binding
        ↓
exact local Git commit/tree verification
        ↓
H2 selected evidence only
        ↓
H3 PARSED Python selected blobs only
        ↓
H3 exact bounded blob reader semantics
        ↓
Python AST import extraction
        ↓
deterministic internal-resolution policy
        ↓
RepositoryDependencyGraphResult
        ↓
zero-authority HarnessReceipt
```

H4 is advisory repository intelligence. It creates no Bridge, executor, retry, paid-provider, review, task-state, lease, or merge authority.

## 2. Why H4 Comes After H3

H1 answers: what exact tracked repository artifacts exist?

H2 answers: which artifacts are relevant to the current task and in what deterministic order?

H3 answers: what role does each selected artifact play and which top-level Python symbols does it define?

H4 answers: which selected Python artifacts statically depend on which module references, and which of those references can be proven to map to exact repository artifacts?

This graph is the missing structural layer needed before future knowledge/invariant registries or context-expansion/compilation. H4 must not skip directly to model-generated semantic knowledge or executor-specific rendering.

## 3. Authority Boundary

ADR-038 remains authoritative.

H4 MAY:

```text
CONSUME_H2_RANKING_RESULT: YES
CONSUME_H3_ROLE_SUMMARY_RESULT: YES
READ_LOCAL_GIT_METADATA: YES
READ_EXACT_SELECTED_GIT_BLOBS: YES, BOUNDED
PARSE_BOUNDED_PYTHON_AST: YES
EXTRACT_STATIC_IMPORT_REFERENCES: YES
RESOLVE_EXACT_INTERNAL_TARGETS: YES, DETERMINISTIC_ONLY
EMIT_STATIC_DEPENDENCY_GRAPH: YES
EMIT_ZERO_AUTHORITY_RECEIPT: YES
```

H4 MUST NOT:

```text
READ_MUTABLE_WORKTREE_FILE_BYTES: FORBIDDEN
READ_UNSELECTED_REPOSITORY_BODIES: FORBIDDEN
EXECUTE_REPOSITORY_SOURCE: FORBIDDEN
IMPORT_DISCOVERED_REPOSITORY_MODULES: FORBIDDEN
EVALUATE_DYNAMIC_IMPORTS: FORBIDDEN
NETWORK_CALL: FORBIDDEN
LLM_CALL: FORBIDDEN
PAID_API_CALL: FORBIDDEN
PROVIDER_CREDENTIAL_VALUE_READ: FORBIDDEN
TASK_STATE_AUTHORITY: FORBIDDEN
REVIEW_STATE_AUTHORITY: FORBIDDEN
EXECUTOR_SELECTION_AUTHORITY: FORBIDDEN
LEASE_AUTHORITY: FORBIDDEN
DISPATCH_AUTHORITY: FORBIDDEN
RETRY_OR_FAILOVER_AUTHORITY: FORBIDDEN
BRIDGE_STATE_MUTATION: FORBIDDEN
MERGE_AUTHORITY: FORBIDDEN
H5_IMPLEMENTATION: FORBIDDEN
```

## 4. Exact H2/H3 Binding

Before any H4 body read:

```text
H2 RepositoryRankingResult self-validation: PASS
H3 RepositoryRoleSummaryResult self-validation: PASS
H2 task_id == H3 task_id
H2 plan snapshot == H3 snapshot
H2 ranking_fingerprint == H3 ranking_fingerprint
H2 plan.plan_fingerprint == H3 h2_plan_fingerprint
len(H2 selected evidence) == len(H3 summaries)
for every position:
    H2 path/blob/kind/priority == H3 path/blob/kind/priority
```

Any mismatch fails closed before Git body reads.

## 5. Exact Snapshot / Blob Read Boundary

H4 must verify the exact H2/H3 commit and tree in the local Git object database before reading selected bodies.

H4 may reuse H3 internal exact-snapshot/blob-reader semantics rather than creating a wider child-process surface. For H4 v1, internal reuse of H3's bounded Git plumbing is explicitly permitted even though those helpers are not promoted as general public API.

Every body actually analyzed must retain H3 guarantees:

```text
object type == blob
size checked before read
bounded body read
actual body length == preflight size
canonical Git blob SHA-1 recomputed over:
    b"blob " + decimal_size + b"\0" + body
actual blob SHA == expected H2/H3 blob_sha
```

H4 must never open a repository worktree path to obtain source content.

## 6. H4 Candidate / Body Scope

H4 metadata universe is the complete H2 candidate accounting:

```text
H2 selected evidence
+
H2 excluded evidence.evidence
```

This metadata may be used to build an internal module-resolution index.

Body reads are much narrower:

```text
ONLY H2 selected evidence
AND path ends with .py
AND corresponding H3 analysis_status == PARSED
```

No unselected body may be read merely to resolve an import target.

Selected non-Python, H3 `NOT_PYTHON`, `CONTENT_BOUND_EXCEEDED`, `DECODE_REJECTED`, or `SYNTAX_REJECTED` artifacts contribute no import-body reads and no import edges.

## 7. Static Import Extraction v1

Policy identity:

```text
H4_GRAPH_POLICY_VERSION = h4-v1
```

Extract only AST `Import` and `ImportFrom` nodes from the exact bounded source.

Imports may occur at module scope or nested scope; H4 captures both as static source references.

For:

```python
import a
import b.c as x
```

emit one edge per imported module.

For:

```python
from pkg.mod import A, B
```

emit one edge per imported name while sharing the same module expression.

Dynamic forms are out of scope:

```text
__import__(...)
importlib.import_module(...)
exec/eval-generated imports
plugin discovery by runtime strings
```

H4 must not infer those as dependencies.

## 8. Deterministic Edge Model

Introduce immutable structured types equivalent to:

```python
class ImportDependencyKind(...): ...
class ImportResolutionStatus(...): ...

@dataclass(frozen=True)
class RepositoryImportDependency: ...

@dataclass(frozen=True)
class RepositoryDependencyGraphResult: ...
```

Closed dependency kinds equivalent to:

```text
IMPORT_MODULE
IMPORT_FROM
```

Closed resolution statuses equivalent to:

```text
INTERNAL_SELECTED
INTERNAL_UNSELECTED
EXTERNAL_OR_UNRESOLVED
AMBIGUOUS_INTERNAL
```

Each dependency edge binds at minimum:

```text
source_path
source_blob_sha
kind
module_expression
imported_name | null
relative_level
line_number
column_offset
resolution_status
target_path | null
target_blob_sha | null
target_selected | null
edge_fingerprint
```

Resolved internal edges MUST bind exact target path and blob SHA from H2 candidate metadata. Unresolved/ambiguous edges MUST NOT invent a target path/blob.

## 9. Deterministic Repository Module Alias Policy v1

H4 may resolve only against Python candidate paths present in complete H2 candidate metadata.

For candidate path `X.py`, canonical path-derived module alias is:

```text
strip trailing .py
replace / with .
```

For `.../__init__.py`, the `.__init__` suffix is removed so the path represents its package module.

For paths under exact prefix `src/`, H4 also adds one deterministic source-layout alias with `src.` removed.

Examples:

```text
pkg/mod.py           -> pkg.mod
pkg/__init__.py      -> pkg
src/pkg/mod.py       -> src.pkg.mod AND pkg.mod
src/pkg/__init__.py  -> src.pkg AND pkg
```

No other source roots, packaging metadata, `sys.path`, editable installs, environment variables, or runtime import hooks may be guessed in H4 v1.

Alias collisions are not resolved heuristically. If one import expression maps to multiple distinct H2 candidate paths, resolution is `AMBIGUOUS_INTERNAL` with no target path/blob.

## 10. Relative Import Resolution

Relative `ImportFrom` resolution must be deterministic and path-derived only.

For a selected source, derive package aliases from its candidate aliases. Apply the AST `level` by removing exactly `level - 1` package segments, then append the explicit module part when present.

Resolution succeeds only if all generated exact candidates collapse to one unique H2 candidate path/blob.

`from . import name` without an explicit module part must not guess whether `name` is a symbol or submodule. Unless an exact unambiguous module target can be proven under the locked alias policy without semantic guessing, mark it `EXTERNAL_OR_UNRESOLVED`.

## 11. Deterministic Ordering

H4 preserves H2 selected source order as the primary source order.

Within each source file, dependency edges are ordered by:

```text
line_number ascending
column_offset ascending
dependency kind
module_expression
imported_name (null first)
target_path (null first)
```

The final graph edge tuple is exact and deterministic.

Duplicate exact edge identities are rejected rather than silently deduplicated.

## 12. Hard Bounds

Locked H4 v1 bounds:

```text
MAX_H4_SELECTED_ITEMS = 32
MAX_H4_IMPORT_EDGES_PER_FILE = 128
MAX_H4_TOTAL_IMPORT_EDGES = 1024
MAX_H4_MODULE_EXPRESSION_LENGTH = 256
MAX_H4_IMPORTED_NAME_LENGTH = 128
MAX_H4_RELATIVE_LEVEL = 64
MAX_H4_TOTAL_BODY_BYTES = 4194304
```

H4 reuses H3's per-blob 256 KiB body bound implicitly because only H3 `PARSED` blobs may be read.

If per-file or aggregate edge bounds would be exceeded, H4 fails closed with a bounded H4 graph-domain error. It must not silently truncate a dependency graph and present it as complete.

Integer bounds reject bool.

## 13. Upstream Consistency

An H3 summary marked `PARSED` is a provenance assertion over exact bytes. If H4 re-reading the same exact blob produces decode/syntax failure, body identity mismatch, or other contradiction, H4 fails closed. It must not silently downgrade or invent a new H3 analysis status.

Operational AST failures propagate/fail closed; they are not converted into dependency evidence.

## 14. RepositoryDependencyGraphResult

The immutable result binds at minimum:

```text
schema_version
policy_version = h4-v1
task_id
snapshot
ranking_fingerprint
h2_plan_fingerprint
h3_role_summary_fingerprint
source_summary_fingerprints in H2 selected order
edges exact deterministic tuple
graph_fingerprint
```

Construction revalidates every upstream binding and every edge fingerprint.

The graph fingerprint uses existing H0 canonical UTF-8 JSON + SHA-256 helpers. No alternate serialization scheme is allowed.

## 15. HarnessReceipt

H4 emits H0 `HarnessReceipt` with:

```text
authority_created = false
network_used = false
llm_used = false
paid_api_used = false
candidate_count = len(H3 summaries)
selected_count = len(H3 summaries)
excluded_count = 0
input_fingerprint binds H2 + H3 + h4-v1
output_fingerprint = graph_fingerprint
```

Edge counts live in the graph result, not overloaded into receipt authority semantics.

## 16. Explicit Non-Goals

```text
call graph: NO
runtime dependency graph: NO
data-flow graph: NO
inheritance graph: NO
symbol-use graph: NO
dynamic import inference: NO
package-manager dependency resolution: NO
third-party package installation inspection: NO
knowledge/invariant registry: NO
context expansion/compilation: NO
skill compilation: NO
skill precedence: NO
executor-specific rendering: NO
executor tendency inference: NO
Bridge context injection: NO
H5 implementation: NO
```

## 17. Namespace / Implementation Boundary

Preferred implementation:

```text
src/aios_engineering/harness/graph.py
```

Exports may be added only to:

```text
src/aios_engineering/harness/__init__.py
```

Tests:

```text
tests/aios_engineering/harness/test_graph.py
```

H4 must not modify:

```text
bridge.py
src/aios_bridge/**
src/aios_engineering/harness/contracts.py
src/aios_engineering/harness/discovery.py
src/aios_engineering/harness/ranking.py
src/aios_engineering/harness/roles.py
src/aios_engineering/harness/fingerprint.py
src/aios_engineering/harness/errors.py
.agents/**
requirements.txt
```

No dependency changes.

## 18. Acceptance Tests

Tests must prove at minimum:

```text
H2_H3_CROSS_BINDING_EXACT: YES
MISMATCH_FAILS_BEFORE_BODY_READ: YES
EXACT_COMMIT_TREE_BINDING: YES
ONLY_SELECTED_H3_PARSED_PYTHON_BODIES_READ: YES
UNSELECTED_BODY_READ: NO
WORKTREE_BODY_READ: NO
DIRTY_WORKTREE_INDEPENDENCE: YES
H3_EXACT_BLOB_IDENTITY_SEMANTICS_REUSED: YES

IMPORT_MODULE_EXTRACTED: YES
IMPORT_FROM_EXTRACTED: YES
NESTED_IMPORT_EXTRACTED: YES
DYNAMIC_IMPORT_INFERRED: NO
EDGE_SOURCE_ORDER_DETERMINISTIC: YES

PATH_MODULE_ALIAS_RESOLUTION: YES
SRC_LAYOUT_ALIAS_RESOLUTION: YES
INTERNAL_SELECTED_RESOLUTION: YES
INTERNAL_UNSELECTED_RESOLUTION: YES
EXTERNAL_OR_UNRESOLVED_ACCOUNTING: YES
AMBIGUOUS_INTERNAL_ACCOUNTING: YES
RELATIVE_IMPORT_DETERMINISTIC: YES
NO_RUNTIME_SYSPATH_GUESSING: YES

PER_FILE_EDGE_BOUND_ENFORCED: YES
TOTAL_EDGE_BOUND_ENFORCED: YES
SILENT_EDGE_TRUNCATION: NO
TOTAL_BODY_BOUND_ENFORCED: YES
UPSTREAM_PARSED_CONTRADICTION_FAILS_CLOSED: YES
OPERATIONAL_AST_FAILURE_FAILS_CLOSED: YES

EDGE_FINGERPRINT_DETERMINISTIC: YES
GRAPH_FINGERPRINT_BINDS_H2_H3: YES
SNAPSHOT_CHANGE_INVALIDATES_BINDING: YES

AUTHORITY_CREATED: NO
NETWORK_USED: NO
LLM_USED: NO
PAID_API_USED: NO
BRIDGE_RUNTIME_CHANGED: NO
H5_STARTED: NO
```

Tests may create bounded temporary local Git repositories and synthetic H2/H3 objects. No model/provider/network/Codex/Antigravity invocation is part of H4 unit behavior.

## 19. Sequence

```text
H0 Harness Foundation ✅
H1 Repository Snapshot Discovery & Provenance ✅
H2 Deterministic Task Relevance Ranking & Bounded Selection ✅
H3 Exact-Snapshot Artifact Role Summaries & Python Symbol Intelligence ✅
        ↓
H4 Exact-Snapshot Static Import Dependency Graph
        ↓
H5+ under separate contracts
```

H4 completion does not silently authorize H5.

## 20. Reopen Conditions

Only explicit Human direction plus a new architecture decision may widen H4 into dynamic dependency analysis, call/data-flow analysis, package-manager/runtime resolution, knowledge registries, context compilation, skills, executor-specific rendering, or any Bridge authority surface.
