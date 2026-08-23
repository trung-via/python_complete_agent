# TASK-076 — H4 Exact-Snapshot Static Import Dependency Graph

STATUS: READY
PUBLISHER_PROFILE: CANONICAL_E4
CLASS: L2 — AIOS ENGINEERING H-SERIES
MILESTONE: H4
EXECUTOR_MODE: DUAL_EXECUTOR_ALLOWED
RECOMMENDED_EXECUTOR: antigravity

## Baseline

```text
MAIN_SHA: 60f18b3be650725f097305e38c1c36b6b434e62b
TARGET_BRANCH: ai/task-076
H0_STATUS: COMPLETE
H1_STATUS: COMPLETE
H2_STATUS: COMPLETE
H3_STATUS: COMPLETE
H4_STATUS: AUTHORIZED_BY_ADR_049
H5_IMPLEMENTATION_AUTHORIZED: NO
LEAN_AUTO_MERGE: ENABLED
DUAL_EXECUTOR_OPERATIONAL_BASELINE: PROVEN
ADR: ADR-049
ADR_BLOB_SHA: 8ce0dfd0058ca7f9d2bcf54fcc08fb125bdf6c07
PAID_API_CALL_ALLOWED: NO
AUTO_RETRY_ALLOWED: NO
AUTO_REROUTE_ALLOWED: NO
REAL_CODEX_REQUIRED: NO
REAL_ANTIGRAVITY_REQUIRED: NO
```

## Machine-Readable E4 Inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/decisions/ADR-038-AIOS-ENGINEERING-H-SERIES-H0-AUTHORITY-BOUNDARY-CONTRACT-LOCK.md","blob_sha":"be56f92eef5dcffdc37cebafea280399730b151f"},{"path":".ai/decisions/ADR-043-AIOS-ENGINEERING-H1-REPOSITORY-SNAPSHOT-DISCOVERY-PROVENANCE-CONTRACT-LOCK.md","blob_sha":"140e1a03593e31f6681016ae45b427f9b16ee8c9"},{"path":".ai/decisions/ADR-045-AIOS-ENGINEERING-H2-DETERMINISTIC-TASK-RELEVANCE-RANKING-BOUNDED-SELECTION-CONTRACT-LOCK.md","blob_sha":"0cbb4fc90e75bff533e1fd99397f4a1470e39c72"},{"path":".ai/decisions/ADR-048-AIOS-ENGINEERING-H3-EXACT-SNAPSHOT-ARTIFACT-ROLE-PYTHON-SYMBOL-INTELLIGENCE-CONTRACT-LOCK.md","blob_sha":"5f595a20e10541f6c53f8ecc2d061157d79a284c"},{"path":".ai/decisions/ADR-049-AIOS-ENGINEERING-H4-EXACT-SNAPSHOT-STATIC-IMPORT-DEPENDENCY-GRAPH-CONTRACT-LOCK.md","blob_sha":"8ce0dfd0058ca7f9d2bcf54fcc08fb125bdf6c07"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["src/aios_engineering/harness/__init__.py","src/aios_engineering/harness/graph.py","tests/aios_engineering/harness/test_graph.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

The publisher profile and three E4 markers above are mandatory executable authoring inputs. They create no retry, reroute, paid-provider, merge, executor-substitution, or H5 authority.

## Objective

Implement ADR-049 as H4 repository intelligence: consume one exact H2 `RepositoryRankingResult` and one exact H3 `RepositoryRoleSummaryResult`, revalidate all H2/H3 cross-bindings before body reads, verify the exact local Git commit/tree snapshot, read only H2-selected `.py` blobs whose corresponding H3 status is `PARSED`, reuse the H3 exact bounded Git-blob identity boundary, extract static Python import references, deterministically resolve exact internal repository targets from complete H2 candidate metadata, and emit a fingerprint-bound `RepositoryDependencyGraphResult` plus a zero-authority H0 `HarnessReceipt`.

## Writable Scope

Executor may modify/create only:

```text
src/aios_engineering/harness/__init__.py
src/aios_engineering/harness/graph.py
tests/aios_engineering/harness/test_graph.py
```

Bridge-generated `.ai/results/RESULT-076.md` is publication output, not executor writable scope.

Explicitly forbidden:

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
.ai/decisions/**
.ai/reviews/**
.ai/tasks/**
requirements.txt
```

No dependency changes.

## Required Public Surface

Implement in `src/aios_engineering/harness/graph.py` a public surface equivalent to:

```python
H4_GRAPH_POLICY_VERSION = "h4-v1"

class ImportDependencyKind(...): ...
class ImportResolutionStatus(...): ...

@dataclass(frozen=True)
class RepositoryImportDependency: ...

@dataclass(frozen=True)
class RepositoryDependencyGraphResult: ...

def build_repository_dependency_graph(
    repo_root: Path | str,
    ranking: RepositoryRankingResult,
    roles: RepositoryRoleSummaryResult,
) -> tuple[RepositoryDependencyGraphResult, HarnessReceipt]: ...
```

Export the final H4 public surface through `src/aios_engineering/harness/__init__.py`.

H4 graph-domain error classes may live in `graph.py`; do not modify shared `errors.py`.

## Exact H2/H3 Binding Gate

Before any Git body read, reconstruct/revalidate exact H2 and H3 objects and enforce:

```text
ranking.task_id == roles.task_id
ranking.plan.snapshot == roles.snapshot
ranking.ranking_fingerprint == roles.ranking_fingerprint
ranking.plan.plan_fingerprint == roles.h2_plan_fingerprint
len(ranking.plan.selected_evidence) == len(roles.summaries)
```

For every positional selected item/summary pair enforce exact equality of:

```text
path
blob_sha
evidence_kind
h2 priority
```

Any mismatch must fail before selected source bytes are read.

## Exact Git Boundary

H4 must reuse the existing H3 exact-snapshot and exact-blob read semantics rather than implementing a weaker duplicate.

Preferred internal integration in H4 v1:

```python
from src.aios_engineering.harness import roles as roles_module
```

and reuse the H3 internal repository-root/snapshot/blob helpers as needed.

Do not promote those H3 helpers as new public API and do not modify `roles.py`.

Every body actually analyzed must retain:

```text
exact object type == blob
size before read
bounded body read
exact body length check
canonical Git blob SHA-1 recomputation from actual bytes
actual blob SHA == expected H2/H3 blob SHA
```

No repository worktree path-based source read is allowed.

## Candidate Metadata / Body Read Scope

Internal resolution metadata universe is exactly:

```text
ranking.plan.selected_evidence
+
tuple(exclusion.evidence for exclusion in ranking.plan.excluded_evidence)
```

Body reads are allowed only when all are true:

```text
candidate is H2 selected
candidate.path endswith .py
corresponding H3 summary.analysis_status == PARSED
```

Unselected candidates may be internal dependency targets using metadata only; their bodies must never be read.

Selected non-Python or non-PARSED H3 summaries produce no import edges and no source-body read.

## Static Import Extraction

Extract AST `Import` and `ImportFrom` nodes anywhere in the parsed source tree, including nested scopes.

Emit:

```text
import a, b.c as x
    -> one IMPORT_MODULE edge for a
    -> one IMPORT_MODULE edge for b.c

from pkg.mod import A, B
    -> one IMPORT_FROM edge for A
    -> one IMPORT_FROM edge for B
```

Do not infer:

```text
__import__()
importlib.import_module()
exec/eval-generated imports
runtime plugin discovery
```

Sort discovered AST import records explicitly; do not rely on incidental container/set traversal ordering.

## Edge Contract

Each immutable `RepositoryImportDependency` binds at minimum:

```text
source_path
source_blob_sha
kind
module_expression
imported_name | None
relative_level
line_number
column_offset
resolution_status
target_path | None
target_blob_sha | None
target_selected | None
edge_fingerprint
```

Closed kind set:

```text
IMPORT_MODULE
IMPORT_FROM
```

Closed resolution set:

```text
INTERNAL_SELECTED
INTERNAL_UNSELECTED
EXTERNAL_OR_UNRESOLVED
AMBIGUOUS_INTERNAL
```

Resolved internal status requires exact target path/blob and exact selected boolean. Unresolved/ambiguous status requires all target fields null.

## Module Alias / Internal Resolution Policy

Build aliases only from H2 Python candidate paths.

Canonical alias:

```text
remove .py
replace / with .
remove trailing .__init__ for package __init__.py
```

For exact path prefix `src/`, add one additional alias with leading `src.` removed.

Examples:

```text
pkg/mod.py           -> pkg.mod
pkg/__init__.py      -> pkg
src/pkg/mod.py       -> src.pkg.mod + pkg.mod
src/pkg/__init__.py  -> src.pkg + pkg
```

No other source-root heuristic is allowed.

For absolute imports, resolve the exact module expression against this alias index.

For relative `ImportFrom`, derive source package aliases and apply exact AST `level`; append explicit module part when present. Resolve only if all exact candidates collapse to one unique H2 candidate path/blob.

`from . import name` must not guess symbol-vs-submodule semantics. Without an exact unambiguous module target under the locked policy, leave it `EXTERNAL_OR_UNRESOLVED`.

Alias collision across distinct candidate paths -> `AMBIGUOUS_INTERNAL`, never heuristic tie-break.

## Ordering

Primary source order is H2 selected evidence order.

Within one source, sort edges by:

```text
line_number
column_offset
kind
module_expression
imported_name (None first)
target_path (None first)
```

Duplicate exact edge identity must fail closed rather than silently deduplicate.

## Hard Bounds

Implement exactly:

```text
MAX_H4_SELECTED_ITEMS = 32
MAX_H4_IMPORT_EDGES_PER_FILE = 128
MAX_H4_TOTAL_IMPORT_EDGES = 1024
MAX_H4_MODULE_EXPRESSION_LENGTH = 256
MAX_H4_IMPORTED_NAME_LENGTH = 128
MAX_H4_RELATIVE_LEVEL = 64
MAX_H4_TOTAL_BODY_BYTES = 4194304
```

All integer contracts reject bool.

If per-file/total edge bound would be exceeded, fail closed with a bounded graph-domain error. Do not truncate and return a graph presented as complete.

Only H3 `PARSED` Python may be re-read, preserving H3's effective 256 KiB per-blob bound. Recompute aggregate bytes read in H2 selected order and enforce the H4 total-body ceiling independently.

## Upstream Consistency

If H3 says `PARSED` but re-reading the exact blob now produces identity mismatch, UTF-8 decode failure, syntax failure, or another contradictory content outcome, H4 fails closed. Do not mutate/downgrade H3 status.

Operational AST/runtime/resource failures propagate or become H4 fail-closed errors; they must not become dependency edges.

## Result / Fingerprint Contract

`RepositoryDependencyGraphResult` must bind at minimum:

```text
schema_version
policy_version = h4-v1
task_id
snapshot
ranking_fingerprint
h2_plan_fingerprint
h3_role_summary_fingerprint
source_summary_fingerprints exact tuple in H2 selected order
edges exact deterministic tuple
graph_fingerprint
```

Construction must revalidate upstream bindings and every edge fingerprint.

Use existing H0 canonical JSON + SHA-256 helpers. No alternate serialization scheme.

## Receipt Contract

Return H0 `HarnessReceipt`:

```text
authority_created = false
network_used = false
llm_used = false
paid_api_used = false
candidate_count = len(roles.summaries)
selected_count = len(roles.summaries)
excluded_count = 0
input_fingerprint binds H2 ranking + H3 role result + h4-v1
output_fingerprint = graph_fingerprint
```

## Explicit Non-Goals

```text
call graph: NO
runtime dependency graph: NO
data-flow graph: NO
inheritance graph: NO
symbol-use graph: NO
dynamic import inference: NO
package-manager/runtime dependency resolution: NO
knowledge/invariant registry: NO
context expansion/compilation: NO
skill compilation: NO
skill precedence: NO
executor-specific rendering: NO
executor tendency inference: NO
Bridge context injection: NO
H5 implementation: NO
```

## Mandatory Tests

Add `tests/aios_engineering/harness/test_graph.py` proving at minimum:

```text
H2_H3_CROSS_BINDING_EXACT: PASS
MISMATCH_FAILS_BEFORE_BODY_READ: PASS
EXACT_COMMIT_TREE_BINDING: PASS
ONLY_SELECTED_PARSED_PYTHON_BODY_READ: PASS
UNSELECTED_BODY_READ: NO
WORKTREE_BODY_READ: NO
DIRTY_WORKTREE_INDEPENDENCE: PASS
H3_EXACT_BLOB_SHA_REPROOF_REUSED: PASS

IMPORT_MODULE: EXTRACTED
IMPORT_FROM: EXTRACTED
NESTED_IMPORT: EXTRACTED
DYNAMIC_IMPORT: NOT_INFERRED
EDGE_ORDER: DETERMINISTIC

PATH_ALIAS_RESOLUTION: PASS
SRC_ALIAS_RESOLUTION: PASS
INTERNAL_SELECTED: PASS
INTERNAL_UNSELECTED: PASS
EXTERNAL_OR_UNRESOLVED: PASS
AMBIGUOUS_INTERNAL: PASS
RELATIVE_IMPORT: DETERMINISTIC
RUNTIME_SYSPATH_GUESSING: NO

PER_FILE_EDGE_BOUND: ENFORCED
TOTAL_EDGE_BOUND: ENFORCED
SILENT_TRUNCATION: NO
TOTAL_BODY_BOUND: ENFORCED
UPSTREAM_PARSED_CONTRADICTION: FAIL_CLOSED
OPERATIONAL_AST_FAILURE: FAIL_CLOSED

EDGE_FINGERPRINT: DETERMINISTIC
GRAPH_FINGERPRINT_BINDS_H2_H3: PASS
SNAPSHOT_CHANGE_INVALIDATES_BINDING: PASS
RECEIPT_ZERO_AUTHORITY: PASS
NETWORK_USED: NO
LLM_USED: NO
PAID_API_USED: NO
H5_STARTED: NO
```

Tests may create bounded temporary Git repositories and synthetic H2/H3 inputs. Unit behavior must not invoke network, a model/provider, Codex, or Antigravity.

## Validation Commands

Run exactly:

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_engineering/harness/test_contracts.py tests/aios_engineering/harness/test_discovery.py tests/aios_engineering/harness/test_ranking.py tests/aios_engineering/harness/test_roles.py tests/aios_engineering/harness/test_graph.py -q
.\venv\Scripts\python.exe -m pytest tests/ -q
git diff --check
```

Use canonical Bridge E4 publication only.

## Acceptance Boundary

TASK-076 passes only if H4 is exact-H2/H3-bound, exact-snapshot/blob-bound, selected-body-only, deterministic, statically import-aware, conservatively internally resolved, bounded without silent truncation, fingerprint-bound, and zero-authority/zero-network/zero-LLM/zero-paid-API.

H4 completion does not authorize H5 implementation.
