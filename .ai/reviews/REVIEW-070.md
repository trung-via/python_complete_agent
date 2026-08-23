# REVIEW-070 — AIOS Engineering H1 Repository Snapshot Discovery & Provenance

STATUS: CHANGES_REQUIRED
APPROVED: NO
AUTO_MERGE_ELIGIBLE: NO
MERGED_TO_MAIN: NO

TASK_ID: TASK-070
REVIEWED_TASK_HEAD_SHA: b21aa97327eb84002d2eb9597fed87836126edb6
REVIEWED_BASE_MAIN_SHA: bc64de848c6ef151b4d41a31cdb9df1ebb3bb775
RESULT_BLOB_SHA: 1ad09f2d03191a40cbf4f1eac571392e3a92ee20
TASK_ARTIFACT_BLOB_SHA: f450d5b0c9d5da30fb61ee6d67501e40ec0461f3
EXECUTOR_ID: codex
H1_IMPLEMENTATION_PASS: NO
H2_AUTHORIZED: NO
LIVE_PAID_API_AUTHORIZED: NO

## Machine-Readable FIX Inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/tasks/TASK-070.md","blob_sha":"f450d5b0c9d5da30fb61ee6d67501e40ec0461f3"},{"path":".ai/decisions/ADR-038-AIOS-ENGINEERING-H-SERIES-H0-AUTHORITY-BOUNDARY-CONTRACT-LOCK.md","blob_sha":"be56f92eef5dcffdc37cebafea280399730b151f"},{"path":".ai/decisions/ADR-043-AIOS-ENGINEERING-H1-REPOSITORY-SNAPSHOT-DISCOVERY-PROVENANCE-CONTRACT-LOCK.md","blob_sha":"140e1a03593e31f6681016ae45b427f9b16ee8c9"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["src/aios_engineering/harness/__init__.py","src/aios_engineering/harness/discovery.py","src/aios_engineering/harness/errors.py","tests/aios_engineering/harness/test_discovery.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]},{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]}],"operation":"FIX","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

The three marker lines above are the complete E4 machine-readable marker set for this FIX artifact. They grant no merge, retry, reroute, network, provider, or paid-API authority.

## Reviewed Snapshot

```text
BASE_MAIN_SHA: bc64de848c6ef151b4d41a31cdb9df1ebb3bb775
BRANCH: ai/task-070
REVIEWED_TASK_HEAD_SHA: b21aa97327eb84002d2eb9597fed87836126edb6
BRANCH_STATUS_VS_MAIN: AHEAD
AHEAD_BY: 1
BEHIND_BY: 0
MERGE_BASE_SHA: bc64de848c6ef151b4d41a31cdb9df1ebb3bb775
TASK_BRANCH_EQUALS_REVIEWED_SHA: YES
```

Cumulative changed paths are exactly the four TASK-070 writable implementation/test paths plus Bridge-generated `.ai/results/RESULT-070.md`. No Bridge production path, worker surface, dependency file, or H0 contract/fingerprint file changed.

## Runtime / Test Evidence

```text
E4_AUTO_EXECUTION: YES
E4_TRANSPORT_STATUS: EXITED_ZERO
E4_PRE_EXECUTION_HEAD: bc64de848c6ef151b4d41a31cdb9df1ebb3bb775
E4_ALLOWED_SCOPE_VERIFIED: PASS
E4_PUBLICATION_TRUST_VERIFIED: PASS
E4_DIRTY_PATH_COUNT: 4
FULL_REPOSITORY_TESTS: 2207 passed, 7 skipped, 0 failed
```

The green full suite is necessary but not sufficient for PASS because two H1 contract violations remain.

## Finding B1 — Network boundary is not mechanically closed

STATUS: FAIL / BLOCKER

`_open_git_process()` launches local Git plumbing with `subprocess.Popen(...)` but does not pass a child environment that forces lazy promisor-object fetching off. Git can lazily fetch missing objects from a promisor remote in partial-clone repositories. H1 explicitly requires that discovery never contact a remote; merely avoiding explicit `git fetch/pull/clone` argv is insufficient.

Required fix:

```text
- build a child environment for every H1 Git subprocess;
- force GIT_NO_LAZY_FETCH=1 (or an equivalent mechanically enforced no-lazy-fetch primitive);
- caller/user environment must not be able to override this back to 0;
- keep explicit argv + shell=False;
- add regression coverage proving the no-lazy-fetch setting is present on every H1 Git process path;
- no network fallback and no retry.
```

Do not broaden this into Bridge networking changes.

## Finding B2 — RepositoryDiscoveryResult factory silently coerces iterable shapes

STATUS: FAIL / BLOCKER

TASK-070 locked `RepositoryDiscoveryResult` to exact tuple boundaries with no silent iterable coercion. The current `RepositoryDiscoveryResult.create()` accepts `Sequence`/arbitrary iterables and performs `tuple(evidence)` / `tuple(exclusions)`. Tests even pass lists and `reversed(...)` and expect acceptance. This weakens the fail-closed immutable boundary.

Required fix:

```text
- `create()` must require exact tuple inputs for evidence and exclusions before canonical ordering/fingerprinting;
- list, generator, reversed iterator, string-like or other iterable substitutes must be rejected, not repaired;
- deterministic ordering may still be produced from valid tuple input;
- add positive tuple tests and negative list/generator/reversed tests;
- preserve duplicate/path/fingerprint checks.
```

## Publication Evidence Note — Authoring defect, not executor scope expansion

TASK-070 originally required RESULT-070 to contain task-specific evidence keys such as `TARGETED_TESTS`, `GIT_DIFF_CHECK`, `EXACT_SNAPSHOT_BINDING`, `GIT_OBJECT_PROVENANCE_ONLY`, `BOUNDED_STREAM_DISCOVERY`, and `HARNESS_RECEIPT_ZERO_AUTHORITY`. The generic Codex E4 publisher currently emits the canonical full-suite + E4 notes block instead, so those custom keys are absent from RESULT-070.

This mismatch originated in TASK-070 authoring and must not be "fixed" by letting the H1 worker edit Bridge or manually fabricate RESULT. For this FIX, keep Bridge forbidden. Run the locked targeted command and `git diff --check` during implementation; final ChatGPT review will verify the required H1 invariants from exact source/tests plus Bridge-generated publication evidence. The separate task-authoring preflight refinement must prevent future executable tasks from declaring publication evidence the active publisher cannot emit.

## What Already Passes

```text
EXACT_LOWERCASE_COMMIT_INPUT: PASS
COMMIT_OBJECT_CHECK: PASS
TREE_SHA_BINDING: PASS
TREE_BOUND_BLOB_PROVENANCE: PASS
WORKTREE_RECURSIVE_SCAN: NO
UNTRACKED_PROMOTION: NO
DIRTY_WORKTREE_SUBSTITUTION: NO
NUL_DELIMITED_STREAM: PASS
ENTRY_BOUND: PASS
STREAM_BYTE_BOUND: PASS
RECORD_BYTE_BOUND: PASS
WHOLE_STREAM_CAPTURE: NO
CLASSIFIER_PRECEDENCE: PASS
PRIORITY_RANKING_INTRODUCED: NO
SYMBOL_LOCATOR_ALWAYS_NULL: PASS
CANDIDATE_SET_FINGERPRINT: PASS
DISCOVERY_FINGERPRINT: PASS
HARNESS_RECEIPT_ZERO_AUTHORITY: PASS
BRIDGE_CHANGED: NO
SCOPE_EXACT: YES
```

## Required Validation Before Re-review

Run exactly:

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_engineering/harness/test_contracts.py tests/aios_engineering/harness/test_discovery.py -q
.\venv\Scripts\python.exe -m pytest tests/ -q
git diff --check
```

Also ensure tests explicitly prove:

```text
GIT_NO_LAZY_FETCH_FORCED: YES
CALLER_CANNOT_REENABLE_LAZY_FETCH: YES
NETWORK_FALLBACK: NO
EXACT_TUPLE_FACTORY_INPUT: YES
LIST_FACTORY_INPUT_REJECTED: YES
GENERATOR_FACTORY_INPUT_REJECTED: YES
REVERSED_ITERATOR_FACTORY_INPUT_REJECTED: YES
```

## Decision

```text
TASK-070: CHANGES_REQUIRED
BLOCKERS_REMAINING: 2
AUTO_MERGE: NO
H1_COMPLETE: NO
H2_AUTHORIZED: NO
```

Apply only B1 and B2 inside the existing writable scope. Do not change Bridge, TASK/ADR artifacts, worker surfaces, dependencies, ranking semantics, or authority boundaries.
