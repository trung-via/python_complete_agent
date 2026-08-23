# TASK-066 — H0 Harness Foundation & Authority Boundary Lock

STATUS: READY
CLASS: L2 — AIOS ENGINEERING FOUNDATION / LOCAL-DETERMINISTIC
MILESTONE: H-SERIES H0
EXECUTOR_MODE: UNIFIED_AIOS_WORKER_DUAL_EXECUTOR
RECOMMENDED_EXECUTOR: antigravity

## Baseline

```text
MAIN_SHA: bb6e57ca6ba69b1a613430b3903d032c58cfdcd4
TARGET_BRANCH: ai/task-066
M11_STATUS: OPERATIONALLY_PROVEN / CLOSED
M12_CREATED: NO
BRIDGE_RUNTIME_CHANGE_ALLOWED: NO
NETWORK_CALL_ALLOWED: NO
LLM_CALL_ALLOWED: NO
PAID_API_CALL_ALLOWED: NO
```

TASK-066 begins the approved AIOS Engineering H-Series after M11 closure. It implements **H0 only**. It does not implement H1-H8 and does not reopen M11.

## Purpose

Create the minimal immutable local contract layer for H-Series repository intelligence while proving that H-Series creates **zero authority** and remains physically/semantically outside the AIOS Bridge control plane.

H0 must establish:

1. exact Git snapshot binding;
2. provenance-bearing repository evidence references;
3. deterministic advisory intelligence-plan fingerprints;
4. local audit receipts proving no network/model/paid authority;
5. explicit extension-point identities for future Skill Compiler, Skill Precedence, and executor-specific rendering;
6. a hard package boundary under `src/aios_engineering/harness/`.

## Authoritative Context

```text
ADR_038_PATH: .ai/decisions/ADR-038-AIOS-ENGINEERING-H-SERIES-H0-AUTHORITY-BOUNDARY-CONTRACT-LOCK.md
ADR_038_BLOB_SHA: be56f92eef5dcffdc37cebafea280399730b151f
M11_FINAL_REVIEW_PATH: .ai/reviews/REVIEW-065.md
M11_FINAL_REVIEW_BLOB_SHA: cd4182ead2eb3ccdde50e4ba33dda73fafe1deb9
```

## Machine-Readable Executor Context

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/decisions/ADR-038-AIOS-ENGINEERING-H-SERIES-H0-AUTHORITY-BOUNDARY-CONTRACT-LOCK.md","blob_sha":"be56f92eef5dcffdc37cebafea280399730b151f"},{"path":".ai/reviews/REVIEW-065.md","blob_sha":"cd4182ead2eb3ccdde50e4ba33dda73fafe1deb9"}]

## Exact Writable Scope

EXECUTOR_ALLOWED_PATHS_JSON: ["src/aios_engineering/__init__.py","src/aios_engineering/harness/__init__.py","src/aios_engineering/harness/contracts.py","src/aios_engineering/harness/errors.py","src/aios_engineering/harness/fingerprint.py","tests/aios_engineering/harness/test_contracts.py"]

Bridge-generated `.ai/results/RESULT-066.md` is publication output only.

No other file may be modified. If implementation appears to require a Bridge, worker-surface, config, dependency, schema, or unrelated test change, STOP rather than broadening scope.

## Explicitly Forbidden Writable Paths

```text
bridge.py
src/aios_bridge/**
.agents/skills/aios-worker/**
.agents/workflows/aios-worker.md
.ai/decisions/**
.ai/reviews/**
.ai/tasks/**
```

The ADR/task/control artifacts are read-only inputs to the executor.

## Executor Dispatch Policy

DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN","FIX"]},{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN","FIX"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

Human selects exactly one subscription Executor. No silent reroute, automatic failover, paid Executor, or second executor.

## H0 Package Contract

Create exactly the following new implementation package:

```text
src/aios_engineering/
├── __init__.py
└── harness/
    ├── __init__.py
    ├── contracts.py
    ├── errors.py
    └── fingerprint.py
```

H0 must not import or depend on `src.aios_bridge` runtime modules. Standard-library-only implementation is preferred and required unless a pre-existing repository dependency is strictly necessary; adding a new dependency is forbidden.

## Required Contracts

### 1. RepositorySnapshotRef

Implement an immutable/frozen contract with exact semantic fields:

```text
schema_version
repository_commit_sha
repository_tree_sha
```

Validation:

```text
schema_version: exact non-empty bounded string
repository_commit_sha: exact lowercase 40-hex
repository_tree_sha: exact lowercase 40-hex
```

No repository I/O is performed by the contract itself.

### 2. EvidenceKind

Implement an explicit string enum sufficient for H0/future repository evidence. It must include at least:

```text
SOURCE
TEST
DOCUMENTATION
CONFIGURATION
CONTRACT
OTHER
```

Do not infer an evidence kind from file contents or extension inside H0.

### 3. RepositoryEvidenceRef

Implement an immutable/frozen contract with exact semantic fields:

```text
path
blob_sha
evidence_kind
reason_code
priority
symbol_locator  # optional
```

Validation must fail closed:

```text
path:
  canonical repository-relative POSIX path
  non-empty
  no leading '/'
  no backslash
  no empty segments
  no '.' segment
  no '..' segment
  no control characters
  no '.git' or '.git/**'

blob_sha:
  exact lowercase 40-hex

reason_code:
  bounded non-empty machine-readable token
  uppercase ASCII convention such as [A-Z0-9_:-]
  no whitespace/control characters

priority:
  exact int, bool forbidden
  bounded 0..1000

symbol_locator:
  None or bounded non-empty control-free string
  no absolute local filesystem path semantics
```

### 4. HarnessEvidenceExclusion

Implement an immutable/frozen exclusion record containing:

```text
evidence: RepositoryEvidenceRef
reason_code: bounded machine-readable token
```

It is advisory provenance only.

### 5. HarnessExtensionPoint

Implement an explicit string enum with exactly these H0 extension-point identities:

```text
SKILL_COMPILER
SKILL_PRECEDENCE
EXECUTOR_SPECIFIC_RENDERING
```

H0 must not implement the compiler, precedence engine, or renderer.

### 6. HarnessIntelligencePlan

Implement an immutable/frozen plan bound to:

```text
schema_version
task_id
snapshot: RepositorySnapshotRef
selected_evidence: tuple[RepositoryEvidenceRef, ...]
excluded_evidence: tuple[HarnessEvidenceExclusion, ...]
candidate_set_fingerprint
plan_fingerprint
```

Required semantics:

- canonical task id `TASK-<positive digits>`;
- selected and excluded collections must be exact immutable tuples after normalization;
- duplicate exact evidence identities across selected/excluded are rejected;
- conflicting evidence for the same canonical `(path, symbol_locator)` with different blob SHA is rejected;
- `candidate_set_fingerprint` is derived from the union of selected + excluded evidence and is **order-independent**;
- `plan_fingerprint` binds task id + snapshot + ranked selected order + deterministic exclusions + candidate-set fingerprint and is **order-sensitive for selected rank order**;
- identical semantic input must produce identical fingerprints;
- no field may represent approval, executor choice, lease, dispatch, retry, merge, or paid-provider authorization.

A pure factory/helper is permitted to construct the plan and compute verified fingerprints. If callers may supply fingerprints directly, stale/forged fingerprints must be rejected.

### 7. HarnessReceipt

Implement an immutable/frozen local receipt with exact semantic fields:

```text
schema_version
task_id
repository_commit_sha
input_fingerprint
output_fingerprint
generator_version
candidate_count
selected_count
excluded_count
authority_created
network_used
llm_used
paid_api_used
```

Validation must lock:

```text
authority_created == False
network_used == False
llm_used == False
paid_api_used == False
candidate_count == selected_count + excluded_count
all counts are exact non-negative ints; bool forbidden
input_fingerprint/output_fingerprint are exact lowercase 64-hex
task_id is canonical
repository_commit_sha is exact lowercase 40-hex
```

### 8. Canonical Fingerprinting Helpers

`fingerprint.py` must provide pure deterministic helpers using:

```text
UTF-8
canonical JSON
sort_keys=True
separators=(",", ":")
SHA-256
```

Required properties:

```text
candidate evidence set fingerprint: order-independent
selected plan ranking fingerprint: order-sensitive
same semantic input: same fingerprint
no Python object repr / hash() / process-randomized identity
```

## Authority / Side-Effect Boundary

The H0 package must contain no code path that:

```text
opens a network connection
calls an LLM/provider
reads provider credential values
creates/consumes/reactivates a paid grant
mutates Bridge state
creates an executor lease
selects an executor
invokes Bridge dispatch
implements retry/failover
mutates TASK/REVIEW artifacts
merges branches
```

Do not add convenience wrappers that call `bridge.py` from `src/aios_engineering/harness/`.

## Tests

Create `tests/aios_engineering/harness/test_contracts.py` with focused deterministic coverage.

At minimum test:

1. valid snapshot round-trip / immutability;
2. uppercase/short/non-hex commit/tree SHA rejection;
3. valid evidence construction for each EvidenceKind;
4. absolute path rejection;
5. backslash, `.`/`..`, empty-segment and `.git` rejection;
6. invalid reason code / bool priority / out-of-range priority rejection;
7. invalid symbol locator rejection;
8. exact duplicate evidence ambiguity rejection;
9. same path/symbol with conflicting blob SHA rejection;
10. candidate-set fingerprint invariant under candidate/exclusion input permutation;
11. plan fingerprint stable for identical semantic input;
12. plan fingerprint changes when selected ranking changes;
13. plan fingerprint changes when snapshot commit/tree changes;
14. receipt rejects any authority/network/LLM/paid flag set `True`;
15. receipt count invariant;
16. extension-point enum is exactly the three locked identities;
17. package source does not import `src.aios_bridge`/`aios_bridge` runtime modules;
18. no executor/lease/dispatch/paid authority fields exist in `HarnessIntelligencePlan` or `HarnessReceipt`.

Tests must not use network or provider credentials.

## Validation Commands

Executor must run:

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_engineering/harness/test_contracts.py -q
.\venv\Scripts\python.exe -m pytest tests/ -q
```

Also run:

```text
git diff --check
exact writable-scope check
```

The full-suite baseline before TASK-066 is `1972 passed, 7 skipped, 0 failed`; TASK-066 may increase passed-test count but must introduce zero failures/regressions.

## Required RESULT-066 Evidence

`RESULT-066.md` must report at minimum:

```text
H_SERIES_MILESTONE: H0
H_SERIES_AUTHORITY_CREATED: NO
BRIDGE_RUNTIME_CHANGED: NO
BRIDGE_STATE_CHANGED: NO
DISPATCH_CHANGED: NO
WORKER_IDENTITY_CHANGED: NO

REPOSITORY_SNAPSHOT_BINDING: EXACT
EVIDENCE_BLOB_BINDING_SHAPE: EXACT
ABSOLUTE_PATH_ACCEPTED: NO
PATH_TRAVERSAL_ACCEPTED: NO
DUPLICATE_EVIDENCE_AMBIGUITY: REJECTED

CANONICAL_SERIALIZATION: YES
ORDER_INDEPENDENT_FINGERPRINT: YES  # candidate-set semantics
CANDIDATE_SET_FINGERPRINT_ORDER_INDEPENDENT: YES
SELECTED_RANK_ORDER_FINGERPRINT_SENSITIVE: YES
DETERMINISTIC_PLAN_FINGERPRINT: YES

NETWORK_REQUIRED: NO
LLM_REQUIRED: NO
PAID_API_REQUIRED: NO
PROVIDER_CREDENTIAL_VALUE_READ: NO

SKILL_COMPILER_EXTENSION_POINT: PRESENT
SKILL_PRECEDENCE_EXTENSION_POINT: PRESENT
EXECUTOR_RENDERING_EXTENSION_POINT: PRESENT

NO_PRODUCTION_BRIDGE_CHANGE: YES
NO_WORKER_SURFACE_CHANGE: YES
SCOPE_EXACT: YES
```

Include exact targeted and full-suite test commands, exit codes, pass/skip/fail counts, branch, and implementation SHA.

## Acceptance Criteria

TASK-066 may publish READY_FOR_REVIEW only if:

```text
H0_PACKAGE_EXISTS: YES
H0_CONTRACTS_IMMUTABLE: YES
H_SERIES_AUTHORITY_CREATED: NO
BRIDGE_RUNTIME_CHANGED: NO
DISPATCH_CHANGED: NO
WORKER_IDENTITY_CHANGED: NO
REPOSITORY_SNAPSHOT_BINDING: EXACT
PATH_SAFETY_FAIL_CLOSED: YES
DUPLICATE_EVIDENCE_AMBIGUITY: REJECTED
CANONICAL_SERIALIZATION: YES
CANDIDATE_SET_FINGERPRINT_ORDER_INDEPENDENT: YES
SELECTED_RANK_ORDER_FINGERPRINT_SENSITIVE: YES
DETERMINISTIC_PLAN_FINGERPRINT: YES
NETWORK_REQUIRED: NO
LLM_REQUIRED: NO
PAID_API_REQUIRED: NO
TARGETED_TESTS: PASS
FULL_REPOSITORY_TESTS: PASS
SCOPE_EXACT: YES
```

## Non-Goals / Deferred

TASK-066 does **not** implement:

```text
repository crawling/discovery
repo map generation
symbol graph
retrieval/ranking algorithm
context compression
skill compilation
skill precedence resolution
Codex skill rendering
Antigravity skill rendering
Bridge integration changes
ContextBuilder changes
executor-context limit changes
H1-H8
```

Those capabilities remain future H-Series milestones and require separate explicit contract/task/review/merge cycles.

## Completion Boundary

TASK-066 PASS + Human merge means **H0 complete**, not H-Series complete. It authorizes no paid provider call and no automatic start of H1.
