# REVIEW-070 — AIOS Engineering H1 Repository Snapshot Discovery & Provenance

STATUS: CHANGES_REQUIRED
APPROVED: NO
AUTO_MERGE_ELIGIBLE: NO
MERGED_TO_MAIN: NO

TASK_ID: TASK-070
REVIEWED_TASK_HEAD_SHA: cf5bba080ca026bf9ecd9132f6d558197d442b36
REVIEWED_BASE_MAIN_SHA: bc64de848c6ef151b4d41a31cdb9df1ebb3bb775
RESULT_BLOB_SHA: 5241c2f272407f4db451031c7cad5bc4ec590eb6
TASK_ARTIFACT_BLOB_SHA: f450d5b0c9d5da30fb61ee6d67501e40ec0461f3
EXECUTOR_ID: codex
H1_IMPLEMENTATION_PASS: NO
H2_AUTHORIZED: NO
LIVE_PAID_API_AUTHORIZED: NO

## Machine-Readable FIX Inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/tasks/TASK-070.md","blob_sha":"f450d5b0c9d5da30fb61ee6d67501e40ec0461f3"},{"path":".ai/decisions/ADR-038-AIOS-ENGINEERING-H-SERIES-H0-AUTHORITY-BOUNDARY-CONTRACT-LOCK.md","blob_sha":"be56f92eef5dcffdc37cebafea280399730b151f"},{"path":".ai/decisions/ADR-043-AIOS-ENGINEERING-H1-REPOSITORY-SNAPSHOT-DISCOVERY-PROVENANCE-CONTRACT-LOCK.md","blob_sha":"140e1a03593e31f6681016ae45b427f9b16ee8c9"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["src/aios_engineering/harness/__init__.py","src/aios_engineering/harness/discovery.py","src/aios_engineering/harness/errors.py","tests/aios_engineering/harness/test_discovery.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]},{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]}],"operation":"FIX","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

The three marker lines above are the complete E4 machine-readable marker set for this FIX artifact. They create no merge, retry, reroute, network, provider, or paid-API authority.

## Reviewed Snapshot

```text
BASE_MAIN_SHA: bc64de848c6ef151b4d41a31cdb9df1ebb3bb775
BRANCH: ai/task-070
REVIEWED_TASK_HEAD_SHA: cf5bba080ca026bf9ecd9132f6d558197d442b36
BRANCH_STATUS_VS_MAIN: AHEAD
AHEAD_BY: 2
BEHIND_BY: 0
MERGE_BASE_SHA: bc64de848c6ef151b4d41a31cdb9df1ebb3bb775
TASK_BRANCH_EQUALS_REVIEWED_SHA: YES
```

Cumulative changed paths remain exactly the four TASK-070 writable implementation/test paths plus Bridge-generated `.ai/results/RESULT-070.md`. No Bridge production path, worker surface, dependency file, H0 contract, or H0 fingerprint implementation changed.

## Runtime / Test Evidence

```text
ACTION: FIX
EXECUTOR_ID: codex
E4_AUTO_EXECUTION: YES
E4_CONTROL_COMMIT_SHA: c03d718361536ee3d030aa18ed628abc50687188
E4_PRE_EXECUTION_HEAD: b21aa97327eb84002d2eb9597fed87836126edb6
E4_TRANSPORT_STATUS: EXITED_ZERO
E4_ALLOWED_SCOPE_VERIFIED: PASS
E4_PUBLICATION_TRUST_VERIFIED: PASS
E4_DIRTY_PATH_COUNT: 2
FULL_REPOSITORY_TESTS: 2216 passed, 7 skipped, 0 failed
```

The FIX closed the two prior findings, but one H0/H1 environment-provenance blocker remains.

## Prior Finding B1 — Lazy-fetch network boundary

STATUS: RESOLVED / PASS

`_open_git_process()` now forces `GIT_NO_LAZY_FETCH=1` for every H1 Git subprocess, overriding a caller-provided `GIT_NO_LAZY_FETCH=0`. Regression coverage verifies the setting is present with explicit argv and `shell=False`.

## Prior Finding B2 — Exact tuple factory boundary

STATUS: RESOLVED / PASS

`RepositoryDiscoveryResult.create()` now requires exact tuple inputs for both `evidence` and `exclusions`. List, generator, reversed iterator, and string substitutes are rejected. Deterministic sorting/fingerprinting remains applied only after exact tuple validation.

## Finding B3 — Child environment violates zero-credential-read and exact repository provenance

STATUS: FAIL / BLOCKER

The B1 fix builds the Git child environment with:

```python
child_environment = os.environ.copy()
child_environment["GIT_NO_LAZY_FETCH"] = "1"
```

This is not compatible with ADR-038 / ADR-043. H-Series explicitly forbids `PROVIDER_CREDENTIAL_VALUE_READ`, while `os.environ.copy()` reads and copies every environment value, including provider/API credentials when present. It also forwards arbitrary Git control variables such as `GIT_DIR`, `GIT_WORK_TREE`, `GIT_OBJECT_DIRECTORY`, `GIT_ALTERNATE_OBJECT_DIRECTORIES`, `GIT_CONFIG_COUNT`, and related `GIT_*` variables. Those variables can redirect or alter the Git object/config source independently of the supplied `repository_root`, weakening H1's exact repository provenance contract.

Required fix:

```text
- do not copy the full caller environment;
- construct a closed, minimal child-environment allowlist needed only to launch local Git on the current platform;
- do not read/copy provider credential values;
- reject/omit all caller-controlled GIT_* variables;
- set exactly GIT_NO_LAZY_FETCH=1 after constructing the closed environment;
- preserve explicit argv + shell=False;
- add tests proving representative provider-secret variables are absent from child env;
- add tests proving caller GIT_DIR / GIT_WORK_TREE / GIT_OBJECT_DIRECTORY / GIT_CONFIG_* cannot survive into the child env;
- add tests proving GIT_NO_LAZY_FETCH is always exactly 1;
- no network fallback, retry, or Bridge changes.
```

A platform-specific allowlist is acceptable. The implementation may preserve only non-secret process-launch variables actually required for Git execution (for example PATH and necessary OS/locale/temp variables), but must not enumerate/copy environment values generically.

## What Passes

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
EXACT_TUPLE_FACTORY_INPUT: PASS
NON_TUPLE_FACTORY_INPUT_REJECTED: PASS
GIT_NO_LAZY_FETCH_FORCED: PASS
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

Tests must additionally prove:

```text
FULL_CALLER_ENV_COPIED: NO
PROVIDER_CREDENTIAL_VALUE_PROPAGATED: NO
CALLER_GIT_DIR_PROPAGATED: NO
CALLER_GIT_WORK_TREE_PROPAGATED: NO
CALLER_GIT_OBJECT_DIRECTORY_PROPAGATED: NO
CALLER_GIT_CONFIG_OVERRIDE_PROPAGATED: NO
GIT_NO_LAZY_FETCH: EXACTLY_1
EXPLICIT_ARGV: YES
SHELL_FALSE: YES
NETWORK_FALLBACK: NO
```

## Publication Evidence Note

The prior TASK-070 authoring mismatch around task-specific RESULT fields remains an authoring concern, not permission to alter Bridge. Keep Bridge forbidden and do not fabricate RESULT fields manually. Final review may verify H1 invariants from exact source/tests plus canonical E4 publication evidence.

## Decision

```text
TASK-070: CHANGES_REQUIRED
PRIOR_B1_B2: RESOLVED
B3_CLOSED_CHILD_ENVIRONMENT: FAIL
BLOCKERS_REMAINING: 1
AUTO_MERGE: NO
H1_COMPLETE: NO
H2_AUTHORIZED: NO
```

Apply only B3 inside the existing writable scope. Do not change Bridge, TASK/ADR artifacts, worker surfaces, dependencies, ranking semantics, or authority boundaries.
