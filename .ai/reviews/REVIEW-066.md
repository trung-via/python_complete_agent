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
AHEAD_BY: 2
BEHIND_BY: 0
MERGE_BASE_SHA: bb6e57ca6ba69b1a613430b3903d032c58cfdcd4
ACTION_REVIEWED: FIX
EXECUTOR: antigravity
RESULT_STATUS: READY_FOR_REVIEW
FINGERPRINT_BLOB_SHA: aea04e1b8a38cde0c2825eac6f89f623960bdc3d
TESTS_BLOB_SHA: 45bb31d3331f658b72863a7fe5bb662cedcc2724
RESULT_BLOB_SHA: 209405fdd318feceb88ba1eb1bb8116c01acc680
```

## Scope / Authority Audit — PASS

Cumulative delta remains confined to the six TASK-066 H0 implementation/test paths plus Bridge-generated `.ai/results/RESULT-066.md`.

The FIX itself reports changes only to:

```text
src/aios_engineering/harness/contracts.py
src/aios_engineering/harness/fingerprint.py
tests/aios_engineering/harness/test_contracts.py
```

No `bridge.py`, `src/aios_bridge/**`, worker surface, lease/dispatch, paid API, ADR-038, or TASK-066 mutation is present in the reviewed task branch.

Bridge publication evidence:

```text
TARGETED_TESTS: 67 passed, 0 skipped, 0 failed
FULL_REPOSITORY_TESTS: 2039 passed, 7 skipped, 0 failed
H_SERIES_AUTHORITY_CREATED: NO
NO_PRODUCTION_BRIDGE_CHANGE: YES
NO_WORKER_SURFACE_CHANGE: YES
NETWORK_REQUIRED: NO
LLM_REQUIRED: NO
PAID_API_REQUIRED: NO
SCOPE_EXACT: YES
```

## Previous Findings B1-B4 — RESOLVED

### B1 — Candidate-set evidence-union semantics — PASS

`compute_candidate_set_fingerprint(...)` now hashes only canonical `RepositoryEvidenceRef` identities from selected evidence plus `exclusion.evidence`, sorted canonically. Selection/exclusion disposition and exclusion reason no longer contaminate candidate-set identity.

Regression coverage now proves:

```text
selected permutation invariant: YES
exclusion permutation invariant: YES
selected <-> excluded disposition invariant: YES
exclusion reason invariant: YES
```

### B2 — Deterministic exclusion ordering — PASS

`compute_plan_fingerprint(...)` preserves selected evidence rank order but canonically sorts exclusion payloads before hashing. Incidental exclusion input order no longer changes plan fingerprint.

### B3 — Finite bounded strings — PASS WITH ONE VALIDATION EDGE CASE BELOW

Named finite bounds now exist and are applied for schema version, reason code, symbol locator, and additional local strings.

### B4 — Required regression coverage — PASS

Tests now cover exclusion permutation, candidate disposition, exclusion reason invariance, snapshot commit change, snapshot tree change, and oversized strings.

## Finding B5 — BLOCKER — trailing-newline reason code is still accepted

TASK-066 locks `reason_code` as a bounded machine-readable uppercase ASCII token with **no whitespace/control characters**.

Current implementation uses:

```python
_REASON_CODE_RE = re.compile(r"^[A-Z0-9_:-]+$")
...
_REASON_CODE_RE.match(val)
```

In Python regular-expression semantics, `$` may match immediately before a final newline. Therefore a value such as:

```text
"VALID_REASON\n"
```

can satisfy the current `match(...)` check even though it contains a forbidden control/whitespace character.

This affects both `RepositoryEvidenceRef.reason_code` and `HarnessEvidenceExclusion.reason_code` because both use `_validate_reason_code(...)`.

### Required correction B5

Make reason-code validation exact over the entire string. Acceptable bounded approaches include:

```text
_REASON_CODE_RE.fullmatch(val)
```

or an equivalent `\Z`-anchored exact validation, while retaining the existing finite length bound.

Add focused regression tests proving at minimum:

```text
"VALID_REASON\n" -> REJECT
"VALID_REASON\r" -> REJECT
"VALID_REASON\t" -> REJECT
```

Cover both evidence reason code and exclusion reason code, directly or through a parameterized validator-facing contract test.

Do not redesign fingerprinting or broaden the H0 scope.

## Exact FIX Writable Scope

EXECUTOR_ALLOWED_PATHS_JSON: ["src/aios_engineering/harness/contracts.py","tests/aios_engineering/harness/test_contracts.py"]

Bridge-generated `.ai/results/RESULT-066.md` remains publication output only.

`fingerprint.py` is accepted for B1/B2 and must not be changed unless an unavoidable test-only integration issue is discovered; otherwise STOP and request review rather than broaden scope.

Do not modify Bridge, worker surfaces, ADR-038, TASK-066, dependencies, configuration, or unrelated tests.

## FIX Executor Dispatch Policy

DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]},{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]}],"operation":"FIX","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

Antigravity remains the recommended executor for this final bounded H0 FIX. Codex transport hardening is a separate post-H0 task and must not be mixed into TASK-066.

## Required Validation

```text
venv/Scripts/python.exe -m pytest tests/aios_engineering/harness/test_contracts.py -q
venv/Scripts/python.exe -m pytest tests/ -q
git diff --check
exact writable-scope check
```

Required evidence:

```text
B1_B4_REMAIN_PASS: YES
REASON_CODE_FULL_STRING_MATCH: YES
REASON_CODE_TRAILING_NEWLINE_REJECTED: YES
REASON_CODE_TRAILING_CR_REJECTED: YES
REASON_CODE_TRAILING_TAB_REJECTED: YES
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
PREVIOUS_BLOCKERS_B1_B4: RESOLVED
NEW_BLOCKERS: 1
B5: STRICT REASON-CODE FULL-STRING VALIDATION
MERGE: FORBIDDEN
H0_COMPLETE: NO
PAID PROVIDER CALL: FORBIDDEN
```

After the bounded B5 FIX publication, ChatGPT must review the new blobs before Human merge.
