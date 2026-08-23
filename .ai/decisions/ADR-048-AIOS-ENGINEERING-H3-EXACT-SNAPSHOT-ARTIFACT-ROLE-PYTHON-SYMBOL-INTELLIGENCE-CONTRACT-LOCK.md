# ADR-048 — AIOS Engineering H3 Exact-Snapshot Artifact Role Summaries & Python Symbol Intelligence Contract Lock

STATUS: LOCKED
DATE: 2026-08-23
SCOPE: AIOS Engineering H-Series H3
BASELINE_MAIN_SHA: a5dba4d85cccc94ea4364d6a2eb52e905f3a40fe
H0_STATUS: COMPLETE
H1_STATUS: COMPLETE
H2_STATUS: COMPLETE
TASK_074_CODEX_E4_HARDENING: COMPLETE
H3_AUTHORIZED: YES
H4_IMPLEMENTATION_AUTHORIZED: NO

## 1. Decision

H3 is the first H-Series milestone permitted to inspect bounded repository artifact bodies. It consumes one exact H2 `RepositoryRankingResult`, preserves H2 selection/rank order, reads only the selected Git blob objects from the exact H2 snapshot, and emits deterministic structured artifact-role summaries plus a bounded Python top-level symbol inventory.

H3 is advisory repository intelligence only. It does not generate execution authority, mutate Bridge state, select/reroute an executor, call a model/provider, or merge code.

Locked flow:

```text
H2 RepositoryRankingResult
        ↓
verify exact H2/H0 bindings
        ↓
verify exact local Git commit/tree snapshot
        ↓
for H2 selected evidence only
        ↓
verify exact blob object + bounded size
        ↓
read Git object body (never mutable worktree bytes)
        ↓
deterministic role classification
+ bounded Python AST top-level symbol extraction
        ↓
RepositoryRoleSummary tuple preserving H2 rank order
        ↓
RepositoryRoleSummaryResult + zero-authority HarnessReceipt
```

H3 does not re-rank, add candidates, silently substitute files, or change the H2 `HarnessIntelligencePlan`.

## 2. Authority Boundary — Unchanged

ADR-038 remains authoritative.

H3 MAY:

```text
CONSUME_H2_RANKING_RESULT: YES
READ_LOCAL_GIT_METADATA: YES
READ_EXACT_GIT_BLOB_OBJECTS: YES, BOUNDED
PARSE_BOUNDED_PYTHON_SOURCE: YES
CLASSIFY_ARTIFACT_ROLE: YES
EXTRACT_TOP_LEVEL_PYTHON_SYMBOLS: YES
EMIT_STRUCTURED_ROLE_SUMMARIES: YES
EMIT_ZERO_AUTHORITY_RECEIPT: YES
```

H3 MUST NOT:

```text
READ_MUTABLE_WORKTREE_FILE_BYTES: FORBIDDEN
READ_UNSELECTED_REPOSITORY_BODIES: FORBIDDEN
EXECUTE_REPOSITORY_SOURCE: FORBIDDEN
IMPORT_DISCOVERED_REPOSITORY_MODULES: FORBIDDEN
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
```

No H3 summary, role code, symbol, fingerprint, or receipt grants execution or merge authority.

## 3. Exact Input / Snapshot Binding

H3 consumes exactly one H2 `RepositoryRankingResult` plus one explicit local repository root.

Before reading any selected blob body, H3 must verify:

```text
ranking result self-validation: PASS
ranking task_id == ranking.plan.task_id
repository commit SHA is exact lowercase 40-hex
repository tree SHA is exact lowercase 40-hex
local Git object database resolves the exact commit as a commit
exact commit^{tree} == ranking.plan.snapshot.repository_tree_sha
```

Symbolic refs, current branch, HEAD substitution, remote refs, or worktree state must not replace the exact snapshot identity.

For every H2 selected evidence item:

```text
Git object type for evidence.blob_sha == blob
blob identity == exact H2 evidence blob_sha
body read uses Git object database only
```

The current worktree may be dirty or contain different bytes without changing H3 output for the same exact Git snapshot.

## 4. Scope Preservation

H3 operates only on:

```text
ranking.plan.selected_evidence
```

It must preserve that tuple's exact order in the H3 summary result.

H3 MUST NOT:

```text
re-rank H2 evidence
change H2 priority
add an unselected H1/H2 candidate
silently drop a selected candidate
change H2 exclusion accounting
construct a competing HarnessIntelligencePlan
```

Every H2 selected evidence item must produce exactly one H3 `RepositoryRoleSummary`, including bounded/unsupported/parse-rejected cases.

## 5. H3 Role Summary Model

H3 introduces immutable structured types equivalent to:

```python
class ArtifactRole(...): ...
class ContentAnalysisStatus(...): ...
class PythonSymbolKind(...): ...

@dataclass(frozen=True)
class PythonSymbolSummary: ...

@dataclass(frozen=True)
class RepositoryRoleSummary: ...

@dataclass(frozen=True)
class RepositoryRoleSummaryResult: ...
```

Exact naming may vary only where necessary; semantics below are locked.

### RepositoryRoleSummary minimum semantic fields

```text
path
blob_sha
evidence_kind
h2_priority
artifact_role
analysis_status
blob_size_bytes
symbols: exact tuple[PythonSymbolSummary, ...]
summary_fingerprint
```

The summary must preserve H2 path/blob/kind/priority exactly.

No free-form model-generated prose is required or permitted in H3 v1.

## 6. Deterministic Artifact Role Policy v1

Policy identity:

```text
H3_ROLE_POLICY_VERSION = h3-v1
```

Exactly one primary role is assigned using deterministic precedence:

```text
EvidenceKind.CONTRACT       -> CONTRACT_ARTIFACT
EvidenceKind.TEST           -> TEST_ARTIFACT
EvidenceKind.DOCUMENTATION  -> DOCUMENTATION_ARTIFACT
EvidenceKind.CONFIGURATION  -> CONFIGURATION_ARTIFACT
EvidenceKind.SOURCE + path basename == __init__.py
                            -> PACKAGE_EXPORT_SURFACE
EvidenceKind.SOURCE + Python main-entry evidence
                            -> EXECUTABLE_ENTRYPOINT
EvidenceKind.SOURCE         -> SOURCE_IMPLEMENTATION
otherwise                   -> OTHER_ARTIFACT
```

For Python source, `EXECUTABLE_ENTRYPOINT` may be detected only from deterministic AST shape of a top-level `if __name__ == "__main__"` guard or canonical basename `main.py` / `cli.py`.

No model, heuristic confidence score, timestamp, executor identity, or ambient environment may affect role assignment.

## 7. Python Symbol Inventory v1

Only selected `.py` Git blobs are eligible for Python AST symbol extraction.

H3 parses source without importing or executing it.

Extract only top-level:

```text
class definitions
function definitions
async function definitions
```

Each `PythonSymbolSummary` must bind at minimum:

```text
kind
name
line_number
symbol_locator
```

`symbol_locator` must be deterministic, repository-safe, bounded, and contain no absolute filesystem semantics.

Nested functions, methods, runtime values, decorators' evaluated results, type-checker execution, imports, module execution, and dynamic introspection are out of scope for H3 v1.

Symbol order is deterministic source order with a deterministic secondary key if needed.

## 8. Analysis Status / Exact Accounting

Every selected item receives exactly one status from a closed enum equivalent to:

```text
PARSED
NOT_PYTHON
CONTENT_BOUND_EXCEEDED
DECODE_REJECTED
SYNTAX_REJECTED
```

Rules:

- non-Python selected artifacts receive their deterministic role with `NOT_PYTHON` and zero symbols;
- oversized Python blobs receive `CONTENT_BOUND_EXCEEDED` and zero symbols;
- decode failure receives `DECODE_REJECTED` and zero symbols;
- Python AST syntax failure receives `SYNTAX_REJECTED` and zero symbols;
- valid bounded Python receives `PARSED`.

These statuses are evidence-accounting outcomes, not execution/retry authority.

## 9. Hard Resource Bounds

Locked H3 v1 bounds:

```text
MAX_H3_SELECTED_ITEMS = 32
MAX_H3_BLOB_BYTES = 262144          # 256 KiB per selected Python blob
MAX_H3_TOTAL_BODY_BYTES = 4194304   # 4 MiB aggregate body-read ceiling
MAX_H3_SYMBOLS_PER_FILE = 128
MAX_H3_SYMBOL_NAME_LENGTH = 128
MAX_H3_GIT_SCALAR_BYTES = 4096
```

Bounds are exact integers; bool is forbidden where an integer is expected.

H3 must check blob size before reading a body. Aggregate body accounting is deterministic in H2 selected order. Once the aggregate body-read ceiling would be exceeded, the affected Python item is accounted as `CONTENT_BOUND_EXCEEDED`; body bytes must not be partially sampled and treated as complete source.

No unbounded subprocess capture is permitted.

## 10. Git Subprocess Boundary

H3 may invoke local Git only for exact object-database verification/read operations.

Permitted conceptual operations:

```text
git rev-parse --verify <exact_sha>^{commit}
git rev-parse <exact_sha>^{tree}
git cat-file -t <exact_blob_sha>
git cat-file -s <exact_blob_sha>
git cat-file blob <exact_blob_sha>
```

Equivalent bounded plumbing is allowed.

Requirements:

```text
NO shell=True
NO symbolic ref substitution
NO mutable worktree file reads
NO inherited arbitrary GIT_* variables
NO provider credential inheritance
bounded stdout/stderr capture
non-zero Git exit -> fail closed
unexpected object type -> fail closed
```

The child environment should reuse or match the H1 closed Git environment semantics rather than inventing a wider environment surface.

## 11. RepositoryRoleSummaryResult

The result must immutably bind at minimum:

```text
schema_version
policy_version = h3-v1
task_id
repository snapshot
ranking_fingerprint
h2_plan_fingerprint
summaries: tuple preserving H2 selected order
role_summary_fingerprint
```

Construction must revalidate:

```text
result task_id == H2 task_id == H2 plan task_id
result snapshot == H2 plan snapshot
summary count == len(H2 selected evidence)
each summary path/blob/kind/priority == corresponding H2 selected evidence item
summary order == H2 selected order
all summary fingerprints valid
role_summary_fingerprint valid
```

Fingerprinting uses existing H0 canonical UTF-8 JSON + SHA-256 helpers.

## 12. HarnessReceipt

H3 emits the existing H0 `HarnessReceipt`.

Locked values:

```text
authority_created: FALSE
network_used: FALSE
llm_used: FALSE
paid_api_used: FALSE
```

Receipt semantics:

```text
candidate_count = len(H2 selected evidence)
selected_count = len(H3 summaries)
excluded_count = 0
input_fingerprint binds H2 ranking + H3 policy
output_fingerprint = role_summary_fingerprint
```

Because every H2 selected evidence item must receive exactly one H3 summary, `candidate_count == selected_count`.

## 13. Purity / Determinism Boundary

For the same exact local Git object database + identical H2 ranking input + identical H3 policy:

```text
artifact roles: identical
analysis statuses: identical
symbol inventories: identical
summary order: identical
summary fingerprints: identical
result fingerprint: identical
receipt: identical
```

H3 must not depend on wall-clock time, random state, current branch, mutable worktree bytes, executor identity, network state, or model output.

## 14. Executor Tendencies Are Explicitly Deferred

The earlier H-Series blueprint included future executor-tendency intelligence. H0-H2 do not yet define a canonical immutable execution-experience input contract. H3 therefore MUST NOT infer executor tendencies from ad-hoc logs, ambient runtime state, raw conversations, or unbound Bridge state.

Locked:

```text
EXECUTOR_TENDENCY_ANALYSIS_IN_H3: NO
EXECUTOR_TENDENCY_FEATURE_DROPPED: NO
DEFER_UNTIL_CANONICAL_EXPERIENCE_INPUT_EXISTS: YES
```

A later H milestone may add this under its own explicit provenance/precedence contract.

## 15. Namespace / Implementation Boundary

Preferred implementation:

```text
src/aios_engineering/harness/roles.py
```

Exports may be added only to:

```text
src/aios_engineering/harness/__init__.py
```

Tests:

```text
tests/aios_engineering/harness/test_roles.py
```

H3 must not modify:

```text
bridge.py
src/aios_bridge/**
src/aios_engineering/harness/contracts.py
src/aios_engineering/harness/discovery.py
src/aios_engineering/harness/ranking.py
src/aios_engineering/harness/fingerprint.py
.agents/**
requirements.txt
```

No dependency changes.

## 16. Acceptance Tests

Tests must prove at minimum:

```text
H2_RANKING_INPUT_BOUND_EXACTLY: YES
H2_SELECTED_ORDER_PRESERVED: YES
H2_PRIORITY_MUTATED: NO
UNSELECTED_BODY_READ: NO
WORKTREE_BODY_READ: NO
EXACT_COMMIT_TREE_BINDING: YES
EXACT_BLOB_TYPE_AND_SHA_BINDING: YES

ROLE_PRECEDENCE_DETERMINISTIC: YES
PACKAGE_EXPORT_ROLE: YES
ENTRYPOINT_ROLE: YES
SOURCE_IMPLEMENTATION_ROLE: YES
NON_SOURCE_ROLES_PRESERVED: YES

PYTHON_TOP_LEVEL_CLASS_EXTRACTED: YES
PYTHON_TOP_LEVEL_FUNCTION_EXTRACTED: YES
PYTHON_TOP_LEVEL_ASYNC_FUNCTION_EXTRACTED: YES
NESTED_SYMBOL_EXTRACTED: NO
MODULE_IMPORTED_OR_EXECUTED: NO
SYMBOL_ORDER_DETERMINISTIC: YES
SYMBOL_BOUND_ENFORCED: YES

PER_BLOB_BYTE_BOUND_ENFORCED: YES
AGGREGATE_BODY_BYTE_BOUND_ENFORCED: YES
OVERSIZED_BODY_PARTIALLY_PARSED: NO
MALFORMED_UTF8_ACCOUNTED: YES
PYTHON_SYNTAX_FAILURE_ACCOUNTED: YES

SUMMARY_FINGERPRINT_DETERMINISTIC: YES
RESULT_FINGERPRINT_BINDS_H2_RANKING: YES
SNAPSHOT_CHANGE_INVALIDATES_BINDING: YES

AUTHORITY_CREATED: NO
NETWORK_USED: NO
LLM_USED: NO
PAID_API_USED: NO
BRIDGE_RUNTIME_CHANGED: NO
EXECUTOR_TENDENCY_INFERRED: NO
```

Tests may use a bounded temporary local Git repository and synthetic H2 results. They must not use network, a model/provider, a paid API, Codex, or Antigravity as part of H3 unit behavior.

## 17. Sequence

```text
H0 Foundation ✅
H1 Repository Snapshot Discovery & Provenance ✅
H2 Deterministic Task Relevance Ranking & Bounded Selection ✅
TASK-074 Codex/E4 hardening ✅
        ↓
H3 Exact-Snapshot Artifact Role Summaries & Python Symbol Intelligence
        ↓
H4+ under separate contracts
```

H3 completion does not silently authorize H4 implementation.

## 18. Reopen Conditions

This contract may be reopened only by explicit Human direction and a new architecture decision. Later H milestones may add graph intelligence, knowledge/invariant registries, hybrid retrieval, context-budget compilation, task working memory, skill promotion, or executor-specific rendering only while preserving ADR-038 authority separation and exact provenance binding.
