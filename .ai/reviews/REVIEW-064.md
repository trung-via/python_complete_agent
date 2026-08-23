# REVIEW-064 — M11.3D Paid Brain Completion Envelope & Post-Consume Diagnostics Hardening

STATUS: CHANGES_REQUIRED
APPROVED: NO
READY_FOR_HUMAN_MERGE: NO
MERGE_AUTHORIZED: NO
LIVE_MINIMAX_PROOF_AUTHORIZED: NO

## Reviewed Snapshot

```text
TASK_ID: TASK-064
BASE_MAIN_SHA: 67aa98132ca0413fda320929375887b8efed1fa6
REVIEWED_TASK_HEAD_SHA: a8a4d65435879f00092285eca25b7516d18ec9da
BRANCH: ai/task-064
AHEAD_BY: 1
BEHIND_BY: 0
MERGE_BASE_SHA: 67aa98132ca0413fda320929375887b8efed1fa6
TASK_BLOB_SHA: 863a2372c1d7c4d95cf2751e706701e89488187c
RESULT_BLOB_SHA: 0349e5634b66c07b6f3b17ffff5cd3822c394746
```

## Exact Reviewed Blobs

```text
bridge.py: 6ff0d5f0465923c3c5879825f7a6170386f2b064
src/aios_bridge/paid_api_real_escape.py: c9cc3bcc98cea93507ac9954e4b8a482de360aaf
tests/test_bridge_paid_api_real_escape.py: 582f149bedff80c75dc1f6eee070d148291c758f
tests/aios_bridge/test_paid_api_real_escape.py: 5ec71597ac7e26dfa59e562b3d8147507b70a409
tests/aios_bridge/external_brain/test_minimax_provider.py: ea243a9f36aeeda074d729bbb2ae75762844e625
.ai/results/RESULT-064.md: 0349e5634b66c07b6f3b17ffff5cd3822c394746
```

## Scope Audit

The published implementation delta is otherwise scope-clean: the five TASK-064 authorized production/test paths plus Bridge-generated `RESULT-064.md` only.

The core completion-envelope authority, direct real-escape gate, `paid-proof-execute` gate, bounded post-consume diagnostics, secret-safe error-code allowlist, R9 strictness, one-call/no-retry semantics, and MiniMax `max_completion_tokens=8192` test coverage are directionally correct.

## Finding B1 — BLOCKER — TASK-specific bypass violates the canonical preflight policy

`bridge.py` adds:

```python
if active_grant.task_id != "TASK-059" and active_grant.max_output_tokens != M11_REAL_PROOF_MAX_OUTPUT_TOKENS:
    fail(...)
```

This is not permitted by TASK-064. The locked contract requires `paid-proof-preflight` to reject an ACTIVE grant whenever `max_output_tokens != 8192`; there is no TASK-ID exemption. The direct real-escape and `paid-proof-execute` paths correctly enforce the exact 8192 authority, so this special case also creates an inconsistent state where a legacy TASK-059 grant can PASS preflight and then fail at execute.

The current legacy `tests/test_bridge_paid_api_proof_preflight.py` fixture still creates TASK-059 with `max_output_tokens=4000` and expects successful preflight. That legacy test is outside the original TASK-064 writable scope. This exposed an architecture/scope omission in TASK-064; it does **not** justify a production bypass.

Required correction:

1. Remove every TASK-ID-specific exception from the production completion-envelope check. The rule must be exactly `grant.max_output_tokens == M11_REAL_PROOF_MAX_OUTPUT_TOKENS` for every `paid-proof-preflight` invocation.
2. Update the legacy TASK-059 preflight test fixture to the canonical 8192 value for its success-path tests.
3. Add/adjust a regression in that legacy test file proving a TASK-059 grant with 4000 (or another non-8192 value) is rejected before any credential-value access, provider construction/invocation, or grant consumption.
4. Preserve generic `PaidApiGrant` schema/ranges and `paid-grant-create` semantics; do not make 8192 a generic grant-schema restriction.
5. Do not change the already-correct direct real-escape, diagnostics, R9, endpoint, tokenizer/proof-lock, timeout, retry, or consume-before-call contracts unless needed solely to keep the existing tests green without semantic weakening.

After this correction the RESULT statement `NON_8192_REAL_PROOF_GRANT_FAILS_PRE_SPEND: YES` will become true without hidden exceptions.

## FIX Machine-Readable Executor Context

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/tasks/TASK-064.md","blob_sha":"863a2372c1d7c4d95cf2751e706701e89488187c"},{"path":".ai/context/TASK-064-M11.3D-COMPLETION-DIAGNOSTICS-BLUEPRINT.md","blob_sha":"ae49e6c898c1bd1bc61a267d444989392d711dbc"},{"path":".ai/context/TASK-064-M11.3D-LIVE-ATTEMPT-2-FORENSIC.md","blob_sha":"78291ca0eddc41cf1958fb947ef35b9a9220cf75"}]

## Exact FIX Writable Scope

EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","tests/test_bridge_paid_api_proof_preflight.py","tests/test_bridge_paid_api_real_escape.py"]

This review explicitly authorizes `tests/test_bridge_paid_api_proof_preflight.py` for the FIX because the legacy 4000-token success fixture is the reason the original exact scope was insufficient. No other production/test path is authorized.

## FIX Executor Dispatch Policy

DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]},{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]}],"operation":"FIX","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

Human selects exactly one subscription Executor. No silent reroute, paid Executor, automatic executor failover, or second executor.

## Mandatory FIX Tests

Use fake/local dependencies only. At minimum run:

```text
venv/Scripts/python.exe -m pytest tests/test_bridge_paid_api_proof_preflight.py tests/test_bridge_paid_api_real_escape.py tests/aios_bridge/test_paid_api_real_escape.py tests/aios_bridge/external_brain/test_minimax_provider.py -q
venv/Scripts/python.exe -m pytest tests/ -q
```

Required evidence:

```text
TASK_059_BYPASS_REMOVED: YES
NON_8192_PREFLIGHT_REJECTED_FOR_TASK_059: YES
NON_8192_PREFLIGHT_REJECTED_FOR_CURRENT_TASKS: YES
8192_PREFLIGHT_SUCCESS_PATH: YES
PAID_PROOF_EXECUTE_8192_GATE_UNCHANGED: YES
DIRECT_REAL_ESCAPE_8192_GATE_UNCHANGED: YES
POST_CONSUME_DIAGNOSTICS_UNCHANGED: YES
R9_STRICTNESS_UNCHANGED: YES
MAX_CALLS_ONE: YES
AUTO_RETRY_ZERO: YES
REAL_PAID_API_CALL_DURING_FIX: NO
REAL_MINIMAX_NETWORK_DURING_FIX: NO
REAL_API_KEY_VALUE_USE_DURING_FIX: NO
REAL_GRANT_CREATION_DURING_FIX: NO
REAL_GRANT_CONSUME_DURING_FIX: NO
TARGETED_TESTS_PASS: YES
FULL_REPO_TESTS_PASS: YES
```

## Evidence Already Passing in RUN Snapshot

Reported by `RESULT-064.md`:

```text
TARGETED: 94 passed, 0 skipped, 0 failed
FULL REPOSITORY: 1966 passed, 7 skipped, 0 failed
REAL_PAID_API_CALL_DURING_TASK: NO
REAL_MINIMAX_NETWORK_DURING_TASK: NO
REAL_API_KEY_VALUE_USE_DURING_TASK: NO
REAL_GRANT_CREATION_DURING_TASK: NO
REAL_GRANT_CONSUME_DURING_TASK: NO
```

These green suites do not override B1 because the full suite remained green specifically by retaining the TASK-059 production exemption rather than migrating the stale legacy fixture.

## Review Decision

```text
TASK-064: CHANGES_REQUIRED
BLOCKERS: 1
B1: REMOVE TASK-059 PREFLIGHT BYPASS AND MIGRATE LEGACY TEST
MERGE: FORBIDDEN
LIVE PAID PROOF: FORBIDDEN
```

Do not create another MiniMax paid grant or run another live provider call during this FIX. After a clean FIX publication, ChatGPT must review the new exact task head before any merge or live-proof authorization.