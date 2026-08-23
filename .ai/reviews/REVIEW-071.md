# REVIEW-071 — Executable Task Authoring Preflight & Zero-Touch Start Hardening

STATUS: CHANGES_REQUIRED
APPROVED: NO
AUTO_MERGE_ELIGIBLE: NO
MERGED_TO_MAIN: NO

TASK_ID: TASK-071
REVIEWED_TASK_HEAD_SHA: a66ba4fd68b2694164d74c62b9d626ccf21bd40e
REVIEWED_BASE_MAIN_SHA: 2eb9822bfcd923bd937598def9fcf1f2c93b6c9b
RESULT_BLOB_SHA: d85cb27340e3c583efa63660c1ea041edab40b5c
TASK_ARTIFACT_BLOB_SHA: c830eeb40aad0498391fee19d20133ca38ed891c
EXECUTOR_ID: antigravity
TASK_071_IMPLEMENTATION_PASS: NO
H2_IMPLEMENTATION_AUTHORIZED: NO
LIVE_PAID_API_AUTHORIZED: NO

## Machine-Readable FIX Inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/tasks/TASK-071.md","blob_sha":"c830eeb40aad0498391fee19d20133ca38ed891c"},{"path":".ai/decisions/ADR-044-EXECUTABLE-TASK-AUTHORING-PREFLIGHT-ZERO-TOUCH-START-CONTRACT-LOCK.md","blob_sha":"24b212d96d5fa650241a71049ce114f7a3a85489"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","src/aios_bridge/task_authoring.py","tests/test_bridge.py","tests/test_bridge_task_authoring.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]},{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]}],"operation":"FIX","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

The three marker lines above are the complete E4 FIX marker set. They create no retry, reroute, paid-provider, merge, or cross-executor authority.

## Reviewed Snapshot

```text
BASE_MAIN_SHA: 2eb9822bfcd923bd937598def9fcf1f2c93b6c9b
BRANCH: ai/task-071
REVIEWED_TASK_HEAD_SHA: a66ba4fd68b2694164d74c62b9d626ccf21bd40e
BRANCH_STATUS_VS_MAIN: AHEAD
AHEAD_BY: 1
BEHIND_BY: 0
MERGE_BASE_SHA: 2eb9822bfcd923bd937598def9fcf1f2c93b6c9b
```

Cumulative scope is exact: the four executor-writable paths plus Bridge-generated `.ai/results/RESULT-071.md`. No H-Series implementation, worker surface, dependency, lease schema, paid-API grant, review-merge, or continuity contract path changed.

## Runtime / Test Evidence

```text
ACTION: RUN
EXECUTOR_ID: antigravity
TARGETED_TESTS: 77 passed, 0 skipped, 0 failed
FULL_REPOSITORY_TESTS: 2235 passed, 7 skipped, 0 failed
```

The green suite is necessary but one authoring-contract blocker remains.

## What Passes

```text
RUN_PREFLIGHT_BEFORE_RECONCILE: PASS
RUN_PREFLIGHT_BEFORE_BRANCH: PASS
RUN_PREFLIGHT_BEFORE_LEASE: PASS
RUN_PREFLIGHT_BEFORE_AUTHORIZATION: PASS
RUN_PREFLIGHT_BEFORE_STATE_MUTATION: PASS
FIX_PREFLIGHT_BEFORE_BRANCH: PASS (source ordering)
EXISTING_AUTOMATION_MARKER_PARSER_REUSED: PASS
EXISTING_DISPATCH_POLICY_PARSER_REUSED: PASS
MISSING_E4_MARKERS_FAIL_CLOSED: PASS
DUPLICATE_E4_MARKER_FAIL_CLOSED: PASS
MALFORMED_MARKER_FAIL_CLOSED: PASS
OPERATION_MISMATCH_FAIL_CLOSED: PASS
EXECUTOR/CAPABILITY_MISMATCH_FAIL_CLOSED: PASS
ZERO_TOUCH_LOCAL_MAIN_RECONCILIATION_PRESERVED: PASS
MANUAL_POST_MERGE_PULL_REQUIRED: NO
```

## Finding B1 — Publisher profile guard does not close the TASK-070 failure class

STATUS: FAIL / BLOCKER

`validate_publisher_profile()` currently rejects only four literal custom marker prefixes:

```text
REQUIRED_RESULT_KEYS_JSON:
CUSTOM_RESULT_SCHEMA_JSON:
PUBLISHER_REQUIRED_KEYS_JSON:
RESULT_SCHEMA_OVERRIDE_JSON:
```

and optionally checks the first regex match of `PUBLISHER_PROFILE:`. This does not satisfy ADR-044/TASK-071's requirement to prevent unsupported arbitrary custom RESULT requirements from becoming executable-task acceptance requirements.

The exact historical TASK-070 failure shape would still pass this validator: an executable artifact can contain a prose/Markdown section such as:

```text
## RESULT Evidence
RESULT-XYZ.md must report at minimum:
TARGETED_TESTS
GIT_DIFF_CHECK
CUSTOM_IMPLEMENTATION_KEY
```

with no forbidden custom marker and no `PUBLISHER_PROFILE:` at all. `validate_publisher_profile()` returns successfully, so the authoring mismatch is not actually prevented.

There is a second fail-open edge: `re.search()` accepts the first `PUBLISHER_PROFILE:` occurrence only. An artifact containing both `PUBLISHER_PROFILE: CANONICAL_E4` and a later conflicting/unsupported profile is not guaranteed to fail closed.

### Required fix

Implement a genuinely closed publisher-authoring contract. A preferred minimal shape is:

```text
- executable TASK/REVIEW artifacts must declare exactly one machine-readable publisher profile;
- current supported executable profile is CANONICAL_E4 (DEFAULT may be retained only if its semantics are exactly defined and non-ambiguous);
- zero profile occurrences -> reject;
- duplicate/conflicting profile occurrences -> reject;
- unsupported profile -> reject;
- under CANONICAL_E4, unsupported task-authored hard RESULT requirements must be rejected rather than silently treated as publisher obligations;
- specifically add a regression fixture matching the TASK-070-style `## RESULT Evidence` / uppercase custom-key list and prove it fails preflight;
- canonical E4 publication prose/profile must pass;
- do not expand the Bridge RESULT publisher schema.
```

Use a deterministic line/section parser or another closed grammar. Do not solve this with an ever-growing list of guessed forbidden key names.

## Required Validation Before Re-review

Run:

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_bridge_task_authoring.py tests/test_bridge.py -q
.\venv\Scripts\python.exe -m pytest tests/ -q
git diff --check
```

Tests must additionally prove:

```text
PUBLISHER_PROFILE_MISSING: REJECT
PUBLISHER_PROFILE_DUPLICATE: REJECT
PUBLISHER_PROFILE_CONFLICT: REJECT
PUBLISHER_PROFILE_UNSUPPORTED: REJECT
TASK_070_STYLE_CUSTOM_RESULT_SECTION: REJECT
CANONICAL_E4_PROFILE: PASS
CUSTOM_RESULT_SCHEMA_NOT_EXPANDED: YES
```

## Decision

```text
TASK-071: CHANGES_REQUIRED
BLOCKERS_REMAINING: 1
AUTO_MERGE: NO
TASK_AUTHORING_PREFLIGHT_COMPLETE: NO
H2_IMPLEMENTATION_AUTHORIZED: NO
```

Apply only B1 inside the existing writable scope. Preserve the already-correct handoff ordering and zero-touch reconciliation behavior. Do not change executor identity, lease, paid-API, retry/failover, Lean Auto-Merge, H-Series, or publisher schema semantics.
