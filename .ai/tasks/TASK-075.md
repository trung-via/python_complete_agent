# TASK-075 — H3 Exact-Snapshot Artifact Role Summaries & Python Symbol Intelligence

STATUS: READY
PUBLISHER_PROFILE: CANONICAL_E4
CLASS: L2 — AIOS ENGINEERING H-SERIES
MILESTONE: H3
EXECUTOR_MODE: DUAL_EXECUTOR_ALLOWED
RECOMMENDED_EXECUTOR: antigravity

## Baseline

```text
MAIN_SHA: a5dba4d85cccc94ea4364d6a2eb52e905f3a40fe
TARGET_BRANCH: ai/task-075
H0_STATUS: COMPLETE
H1_STATUS: COMPLETE
H2_STATUS: COMPLETE
TASK_074_CODEX_E4_HARDENING: COMPLETE
H3_STATUS: AUTHORIZED_BY_ADR_048
H4_IMPLEMENTATION_AUTHORIZED: NO
LEAN_AUTO_MERGE: ENABLED
DUAL_EXECUTOR_OPERATIONAL_BASELINE: PROVEN
ADR: ADR-048
ADR_BLOB_SHA: 5f595a20e10541f6c53f8ecc2d061157d79a284c
PAID_API_CALL_ALLOWED: NO
AUTO_RETRY_ALLOWED: NO
AUTO_REROUTE_ALLOWED: NO
REAL_CODEX_REQUIRED: NO
REAL_ANTIGRAVITY_REQUIRED: NO
```

## Machine-Readable E4 Inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/decisions/ADR-038-AIOS-ENGINEERING-H-SERIES-H0-AUTHORITY-BOUNDARY-CONTRACT-LOCK.md","blob_sha":"be56f92eef5dcffdc37cebafea280399730b151f"},{"path":".ai/decisions/ADR-043-AIOS-ENGINEERING-H1-REPOSITORY-SNAPSHOT-DISCOVERY-PROVENANCE-CONTRACT-LOCK.md","blob_sha":"140e1a03593e31f6681016ae45b427f9b16ee8c9"},{"path":".ai/decisions/ADR-045-AIOS-ENGINEERING-H2-DETERMINISTIC-TASK-RELEVANCE-RANKING-BOUNDED-SELECTION-CONTRACT-LOCK.md","blob_sha":"0cbb4fc90e75bff533e1fd99397f4a1470e39c72"},{"path":".ai/decisions/ADR-048-AIOS-ENGINEERING-H3-EXACT-SNAPSHOT-ARTIFACT-ROLE-PYTHON-SYMBOL-INTELLIGENCE-CONTRACT-LOCK.md","blob_sha":"5f595a20e10541f6c53f8ecc2d061157d79a284c"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["src/aios_engineering/harness/__init__.py","src/aios_engineering/harness/roles.py","tests/aios_engineering/harness/test_roles.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

The publisher profile and the three E4 marker lines above are mandatory executable authoring inputs. They create no retry, reroute, paid-provider, merge, executor-substitution, or H4 authority.

## Objective

Implement ADR-048 as H3 repository intelligence: consume one exact H2 `RepositoryRankingResult`, preserve the exact H2 selected-evidence order, verify the exact local Git commit/tree snapshot, inspect only the selected Git blob objects under hard byte bounds, classify each selected artifact into one deterministic primary role, extract a bounded top-level Python AST symbol inventory without importing/executing repository code, and emit a fingerprint-bound `RepositoryRoleSummaryResult` plus zero-authority H0 `HarnessReceipt`.

H3 must never read selected content through mutable worktree paths. Blob bodies come only from the exact Git object database bound by H2 provenance.

## Writable Scope

Executor may modify/create only:

```text
src/aios_engineering/harness/__init__.py
src/aios_engineering/harness/roles.py
tests/aios_engineering/harness/test_roles.py
```

Bridge-generated `.ai/results/RESULT-075.md` is publication output, not executor writable scope.

Explicitly forbidden:

```text
bridge.py
src/aios_bridge/**
src/aios_engineering/harness/contracts.py
src/aios_engineering/harness/discovery.py
src/aios_engineering/harness/ranking.py
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

Implement in `src/aios_engineering/harness/roles.py` a public surface equivalent to:

```python
H3_ROLE_POLICY_VERSION = "h3-v1"

class ArtifactRole(...): ...
class ContentAnalysisStatus(...): ...
class PythonSymbolKind(...): ...

@dataclass(frozen=True)
class PythonSymbolSummary: ...

@dataclass(frozen=True)
class RepositoryRoleSummary: ...

@dataclass(frozen=True)
class RepositoryRoleSummaryResult: ...

def summarize_repository_roles(
    repo_root: Path | str,
    ranking: RepositoryRankingResult,
) -> tuple[RepositoryRoleSummaryResult, HarnessReceipt]: ...
```

Exact naming may vary only if necessary, but ADR-048 semantics are locked. Export the final H3 surface through `src/aios_engineering/harness/__init__.py`.

## Exact Input / Snapshot Requirements

Before reading any selected body:

```text
RepositoryRankingResult revalidation: PASS
ranking task_id == ranking.plan.task_id
ranking snapshot exact commit/tree SHA binding: PASS
local Git exact commit resolves as commit
exact commit^{tree} == ranking.plan.snapshot.repository_tree_sha
```

For each selected evidence item:

```text
object type for exact evidence.blob_sha == blob
blob size obtained before body read
blob body read by Git object plumbing only
no path-based open/read of repository worktree content
```

Dirty/untracked/current-worktree bytes must not affect output for the same exact Git object snapshot.

## H2 Scope Preservation

H3 input candidates are exactly:

```text
ranking.plan.selected_evidence
```

Required invariants:

```text
H2 selected order preserved exactly
H2 path/blob/kind/priority preserved exactly
H2 priority not recomputed
H2 ranking not changed
H2 exclusions not changed
unselected body read forbidden
every H2 selected item produces exactly one H3 summary
```

Do not construct a second `HarnessIntelligencePlan`.

## Deterministic Artifact Role Policy v1

Use exactly one primary role with this precedence:

```text
CONTRACT       -> CONTRACT_ARTIFACT
TEST           -> TEST_ARTIFACT
DOCUMENTATION  -> DOCUMENTATION_ARTIFACT
CONFIGURATION  -> CONFIGURATION_ARTIFACT
SOURCE + basename __init__.py
               -> PACKAGE_EXPORT_SURFACE
SOURCE + Python main-entry evidence
               -> EXECUTABLE_ENTRYPOINT
SOURCE         -> SOURCE_IMPLEMENTATION
OTHER          -> OTHER_ARTIFACT
```

Python main-entry evidence may be only:

```text
canonical basename main.py or cli.py
OR
top-level AST if-guard equivalent to __name__ == "__main__"
```

No probabilistic role score, model output, current time, executor identity, or ambient state.

## Python Symbol Inventory

Only selected `.py` blobs are parsed.

Extract only top-level:

```text
ClassDef
FunctionDef
AsyncFunctionDef
```

Do not extract nested functions or class methods as top-level symbols.

Each symbol binds at minimum:

```text
kind
name
line_number
symbol_locator
```

Required limits:

```text
MAX_H3_SYMBOLS_PER_FILE = 128
MAX_H3_SYMBOL_NAME_LENGTH = 128
```

No imports of repository modules, no execution, no decorator evaluation, no dynamic introspection.

## Analysis Status Accounting

Closed status set equivalent to:

```text
PARSED
NOT_PYTHON
CONTENT_BOUND_EXCEEDED
DECODE_REJECTED
SYNTAX_REJECTED
```

Every H2 selected evidence item gets exactly one summary and one status.

Required behavior:

```text
non-.py             -> NOT_PYTHON, zero symbols
oversized Python    -> CONTENT_BOUND_EXCEEDED, zero symbols
aggregate bound hit -> CONTENT_BOUND_EXCEEDED, zero symbols, no partial parse
decode failure      -> DECODE_REJECTED, zero symbols
AST syntax failure  -> SYNTAX_REJECTED, zero symbols
valid Python        -> PARSED
```

## Hard Bounds

Implement exact limits from ADR-048:

```text
MAX_H3_SELECTED_ITEMS = 32
MAX_H3_BLOB_BYTES = 262144
MAX_H3_TOTAL_BODY_BYTES = 4194304
MAX_H3_SYMBOLS_PER_FILE = 128
MAX_H3_SYMBOL_NAME_LENGTH = 128
MAX_H3_GIT_SCALAR_BYTES = 4096
```

Check size before body read. Do not partially sample an oversized blob and treat it as parsed source.

Git subprocess output/error handling must itself remain bounded.

## Git Child Boundary

Permitted only for exact local object-database operations equivalent to:

```text
git rev-parse --verify <exact_sha>^{commit}
git rev-parse <exact_sha>^{tree}
git cat-file -t <exact_blob_sha>
git cat-file -s <exact_blob_sha>
git cat-file blob <exact_blob_sha>
```

Requirements:

```text
shell=True: FORBIDDEN
symbolic ref substitution: FORBIDDEN
worktree body reads: FORBIDDEN
arbitrary inherited GIT_* environment: FORBIDDEN
provider credential inheritance: FORBIDDEN
non-zero Git exit: FAIL_CLOSED
unexpected object type: FAIL_CLOSED
```

Reuse/match H1 closed Git child-environment semantics where practical; do not widen them.

## Summary / Result Fingerprint Contract

Each `RepositoryRoleSummary` must be immutable and self-fingerprint-verifying.

Minimum summary fields:

```text
path
blob_sha
evidence_kind
h2_priority
artifact_role
analysis_status
blob_size_bytes
symbols exact tuple
summary_fingerprint
```

`RepositoryRoleSummaryResult` binds at minimum:

```text
schema_version
policy_version = h3-v1
task_id
snapshot
ranking_fingerprint
h2_plan_fingerprint
summaries exact tuple preserving H2 order
role_summary_fingerprint
```

Construction must fail closed on any task/snapshot/ranking/plan/summary binding mismatch.

Use existing H0 canonical JSON + SHA-256 helpers. Do not create a second fingerprint serialization scheme.

## Receipt Contract

Return H0 `HarnessReceipt` with:

```text
authority_created = false
network_used = false
llm_used = false
paid_api_used = false
candidate_count = len(H2 selected evidence)
selected_count = len(H3 summaries)
excluded_count = 0
input_fingerprint = deterministic H2-ranking + H3-policy binding
output_fingerprint = role_summary_fingerprint
```

## Explicit Non-Goals

```text
free-form semantic prose summary: NO
LLM semantic interpretation: NO
repository graph construction: NO
knowledge/invariant registry: NO
skill compilation: NO
skill precedence resolution: NO
executor-specific rendering: NO
executor tendency inference: NO
Bridge context-ref injection: NO
H4 implementation: NO
```

The earlier executor-tendency direction is deferred, not dropped, until a canonical immutable execution-experience input contract exists.

## Mandatory Tests

Add `tests/aios_engineering/harness/test_roles.py` proving at minimum:

```text
H2_RANKING_INPUT_BOUND_EXACTLY: PASS
H2_SELECTED_ORDER_PRESERVED: PASS
H2_PRIORITY_MUTATED: NO
UNSELECTED_BODY_READ: NO
WORKTREE_BODY_READ: NO
DIRTY_WORKTREE_DOES_NOT_CHANGE_OUTPUT: PASS
EXACT_COMMIT_TREE_BINDING: PASS
EXACT_BLOB_TYPE_BINDING: PASS

CONTRACT_ROLE: PASS
TEST_ROLE: PASS
DOCUMENTATION_ROLE: PASS
CONFIGURATION_ROLE: PASS
PACKAGE_EXPORT_ROLE: PASS
ENTRYPOINT_BASENAME_ROLE: PASS
ENTRYPOINT_MAIN_GUARD_ROLE: PASS
SOURCE_IMPLEMENTATION_ROLE: PASS
OTHER_ROLE: PASS

TOP_LEVEL_CLASS: EXTRACTED
TOP_LEVEL_FUNCTION: EXTRACTED
TOP_LEVEL_ASYNC_FUNCTION: EXTRACTED
NESTED_FUNCTION: NOT_EXTRACTED
CLASS_METHOD: NOT_TOP_LEVEL
MODULE_EXECUTED: NO
MODULE_IMPORTED: NO
SYMBOL_ORDER: DETERMINISTIC
SYMBOL_BOUND: ENFORCED

PER_BLOB_BOUND: ENFORCED
AGGREGATE_BODY_BOUND: ENFORCED
PARTIAL_OVERSIZE_PARSE: NO
MALFORMED_UTF8: ACCOUNTED
INVALID_PYTHON_SYNTAX: ACCOUNTED

SUMMARY_FINGERPRINT: DETERMINISTIC
ROLE_RESULT_FINGERPRINT_BINDS_H2: PASS
SNAPSHOT_CHANGE_INVALIDATES_BINDING: PASS
RECEIPT_COUNTS_EXACT: PASS
AUTHORITY_CREATED: NO
NETWORK_USED: NO
LLM_USED: NO
PAID_API_USED: NO
EXECUTOR_TENDENCY_INFERRED: NO
```

Tests may create a bounded temporary local Git repository and synthetic H2 ranking objects. Unit behavior must not invoke a model/provider, network, Codex, or Antigravity.

## Validation Commands

Run exactly:

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_engineering/harness/test_contracts.py tests/aios_engineering/harness/test_discovery.py tests/aios_engineering/harness/test_ranking.py tests/aios_engineering/harness/test_roles.py -q
.\venv\Scripts\python.exe -m pytest tests/ -q
git diff --check
```

Use canonical Bridge E4 publication only.

## Acceptance Boundary

TASK-075 passes only if H3 is exact-H2-bound, exact-Git-snapshot-bound, selected-evidence-only, body-read-bounded, worktree-independent, deterministic, Python-AST-safe, fully summary-accounting, fingerprint-bound, and zero-authority/zero-network/zero-LLM/zero-paid-API.

H3 completion does not authorize H4 implementation.
