# REVIEW-066 — H0 Harness Foundation & Authority Boundary Lock

STATUS: CHANGES_REQUIRED
APPROVED: NO
READY_FOR_HUMAN_MERGE: NO
MERGE_AUTHORIZED: NO
H0_COMPLETE: NO
LIVE_PAID_API_AUTHORIZED: NO

## Reviewed Snapshot

```text
TASK_ID: TASK-066
BASE_MAIN_SHA: bb6e57ca6ba69b1a613430b3903d032c58cfdcd4
BRANCH: ai/task-066
BRANCH_STATUS_VS_MAIN: AHEAD
AHEAD_BY: 1
BEHIND_BY: 0
MERGE_BASE_SHA: bb6e57ca6ba69b1a613430b3903d032c58cfdcd4
TASK_BLOB_SHA: 3c751899554906f04560afb6f70b83a06ee4873e
CONTRACTS_BLOB_SHA: 8b256036b8da2bc51b77ab61308e87880e199db6
FINGERPRINT_BLOB_SHA: eedd37acbd5f7bf025a82e85b1f76c835a4e5ed7
TESTS_BLOB_SHA: 224810e4df89a85432f850aafa47758d377f9a5a
RESULT_STATUS: READY_FOR_REVIEW
```

## Scope / Authority Audit — PASS

Cumulative task delta is confined to the six authorized H0 implementation/test paths plus Bridge-generated `.ai/results/RESULT-066.md`.

No `bridge.py`, `src/aios_bridge/**`, `.agents/skills/aios-worker/**`, `.agents/workflows/aios-worker.md`, task/review/decision contract, dispatcher, lease, paid-API, or worker-identity path is changed.

The new package is physically separated under `src/aios_engineering/harness/`, and the reviewed package does not import `src.aios_bridge` runtime modules.

Bridge publication reports:

```text
TARGETED_TESTS: 57 passed, 0 skipped, 0 failed
FULL_REPOSITORY_TESTS: 2029 passed, 7 skipped, 0 failed
EXECUTOR: antigravity
```

Those green tests do not override the contract mismatches below because the current tests encode weaker semantics than TASK-066/ADR-038.

## Finding B1 — BLOCKER — candidate-set fingerprint is not a fingerprint of the evidence union

TASK-066 requires:

```text
candidate_set_fingerprint = derived from the union of selected + excluded evidence
candidate-set semantics = order-independent
```

ADR-038 further defines it as order-independent over canonical evidence identities.

Current `compute_candidate_set_fingerprint(...)` serializes selected items as:

```text
{"type":"SELECTED","evidence":...}
```

and exclusions as:

```text
{"type":"EXCLUDED","exclusion":{"evidence":...,"reason_code":...}}
```

Therefore the candidate-set fingerprint changes when the exact same `RepositoryEvidenceRef` moves from selected to excluded, or when only the exclusion reason changes, even though the underlying candidate evidence union is unchanged.

That makes the candidate-set fingerprint encode disposition rather than candidate identity and violates the locked H0 fingerprint semantics.

### Required correction B1

`compute_candidate_set_fingerprint(...)` must hash only the canonical `RepositoryEvidenceRef` identities from the union of selected evidence plus `exclusion.evidence`, canonically sorted before hashing.

Selection/exclusion disposition and exclusion reason belong in `plan_fingerprint`, not `candidate_set_fingerprint`.

Add regression tests proving all of the following:

```text
same evidence union + selected input permutation -> same candidate fingerprint
same evidence union + exclusion input permutation -> same candidate fingerprint
same evidence union + evidence moved selected <-> excluded -> same candidate fingerprint
same evidence union + exclusion reason changed -> same candidate fingerprint
```

## Finding B2 — BLOCKER — plan fingerprint gives incidental exclusion input order semantic meaning

TASK-066 locks selected evidence as ranked/order-sensitive, but exclusions as deterministic exclusions/reasons. ADR-038 only grants semantic rank meaning to selected evidence.

Current `compute_plan_fingerprint(...)` serializes `excluded_evidence` in caller-provided order without canonical sorting. Consequently, two semantically identical plans with the same selected ranking and same exclusion set/reasons can produce different `plan_fingerprint` values solely because exclusion input order differs.

### Required correction B2

Canonicalize exclusions deterministically for plan fingerprinting (for example by canonical serialized exclusion payload) while preserving caller-provided selected rank order exactly.

Add regression tests proving:

```text
excluded input permutation -> same plan fingerprint
selected rank permutation -> different plan fingerprint
```

## Finding B3 — BLOCKER — explicitly bounded strings are currently unbounded

TASK-066 explicitly requires bounded strings for:

```text
RepositorySnapshotRef.schema_version
RepositoryEvidenceRef.reason_code
RepositoryEvidenceRef.symbol_locator (when present)
HarnessEvidenceExclusion.reason_code
```

The current implementation validates non-empty/shape/control safety but defines no finite maximum length for these fields. Arbitrarily large values are accepted.

For H0 foundation contracts this is a fail-closed boundary requirement, not a style preference.

### Required correction B3

Introduce named finite upper-bound constants in the H0 package, apply them consistently, and add oversized-value rejection tests. Keep the bounds local/deterministic; do not add dependencies or Bridge coupling.

The FIX may choose reasonable documented finite values as long as they are explicit, stable, and tested. Do not broaden the task into repository I/O or runtime policy.

## Finding B4 — BLOCKER — required minimum tests are incomplete

TASK-066 requires at minimum:

```text
candidate/exclusion input permutation coverage
plan fingerprint changes when snapshot commit/tree changes
```

The current test suite permutes selected candidates but does not permute exclusions, and the snapshot-change test changes the commit SHA only, not the tree SHA.

### Required correction B4

Add focused tests for:

```text
candidate-set exclusion permutation invariance
plan exclusion permutation invariance
candidate disposition invariance required by B1
snapshot tree SHA change -> plan fingerprint changes
oversized bounded strings -> rejected
```

## Evidence Already Passing

The following parts of TASK-066 are accepted and must not be redesigned during FIX:

```text
H0 namespace boundary: PASS
RepositorySnapshotRef frozen shape: PASS
RepositoryEvidenceRef path safety: PASS
lowercase 40-hex SHA shape: PASS
EvidenceKind exact identities: PASS
HarnessExtensionPoint exact identities: PASS
duplicate exact evidence rejection: PASS
same path/symbol conflicting blob rejection: PASS
forged fingerprint rejection: PASS
HarnessReceipt zero-authority flags: PASS
HarnessReceipt count invariant: PASS
no Bridge runtime import: PASS
no executor/lease/dispatch authority fields: PASS
no production Bridge change: PASS
no worker surface change: PASS
network/LLM/paid authority created: NO
```

## Exact FIX Writable Scope

EXECUTOR_ALLOWED_PATHS_JSON: ["src/aios_engineering/harness/contracts.py","src/aios_engineering/harness/fingerprint.py","tests/aios_engineering/harness/test_contracts.py"]

Bridge-generated `.ai/results/RESULT-066.md` remains publication output only.

Do not modify `bridge.py`, `src/aios_bridge/**`, worker surfaces, ADR-038, TASK-066, dependencies, configuration, or unrelated tests.

## FIX Executor Dispatch Policy

DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]},{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]}],"operation":"FIX","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

Human selects exactly one subscription executor. No automatic failover, silent reroute, paid executor, or second executor.

Given the separately observed Codex local transport no-delta/nonzero reliability issue, Antigravity is the recommended executor for this FIX. Codex transport hardening remains a separate post-H0 refinement and must not be mixed into TASK-066.

## Required FIX Validation

Run:

```text
venv/Scripts/python.exe -m pytest tests/aios_engineering/harness/test_contracts.py -q
venv/Scripts/python.exe -m pytest tests/ -q
git diff --check
exact writable-scope check
```

Required evidence:

```text
CANDIDATE_SET_EVIDENCE_UNION_SEMANTICS: PASS
CANDIDATE_SET_SELECTED_PERMUTATION_INVARIANT: YES
CANDIDATE_SET_EXCLUSION_PERMUTATION_INVARIANT: YES
CANDIDATE_SET_DISPOSITION_INVARIANT: YES
CANDIDATE_SET_EXCLUSION_REASON_INVARIANT: YES
PLAN_EXCLUSION_ORDER_INVARIANT: YES
SELECTED_RANK_ORDER_FINGERPRINT_SENSITIVE: YES
SNAPSHOT_COMMIT_CHANGE_SENSITIVE: YES
SNAPSHOT_TREE_CHANGE_SENSITIVE: YES
BOUNDED_SCHEMA_VERSION: YES
BOUNDED_REASON_CODE: YES
BOUNDED_SYMBOL_LOCATOR: YES
H_SERIES_AUTHORITY_CREATED: NO
NO_PRODUCTION_BRIDGE_CHANGE: YES
NO_WORKER_SURFACE_CHANGE: YES
NETWORK_REQUIRED: NO
LLM_REQUIRED: NO
PAID_API_REQUIRED: NO
SCOPE_EXACT: YES
```

## Review Decision

```text
TASK-066: CHANGES_REQUIRED
BLOCKERS: 4
B1: CANDIDATE-SET UNION SEMANTICS
B2: DETERMINISTIC EXCLUSION ORDER
B3: FINITE STRING BOUNDS
B4: REQUIRED REGRESSION COVERAGE
MERGE: FORBIDDEN
H0_COMPLETE: NO
PAID PROVIDER CALL: FORBIDDEN
```

After a clean bounded FIX publication, ChatGPT must review the new blobs before any Human merge.
