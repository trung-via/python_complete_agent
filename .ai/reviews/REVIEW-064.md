# REVIEW-064 — M11.3D Paid Brain Completion Envelope & Post-Consume Diagnostics Hardening

STATUS: PASS
APPROVED: YES
READY_FOR_HUMAN_MERGE: YES
MERGE_AUTHORIZED: NO
MERGED_TO_MAIN: NO
LIVE_MINIMAX_PROOF_AUTHORIZED: NO

## Reviewed Snapshot

```text
TASK_ID: TASK-064
BASE_MAIN_SHA: 67aa98132ca0413fda320929375887b8efed1fa6
PRIOR_REVIEWED_HEAD_SHA: a8a4d65435879f00092285eca25b7516d18ec9da
REVIEWED_TASK_HEAD_SHA: 5a714a410d4a4d5fc0b76cea62e7fd164f0cdd54
BRANCH: ai/task-064
AHEAD_BY: 2
BEHIND_BY: 0
MERGE_BASE_SHA: 67aa98132ca0413fda320929375887b8efed1fa6
TASK_BLOB_SHA: 863a2372c1d7c4d95cf2751e706701e89488187c
PRIOR_REVIEW_BLOB_SHA: 96a093dd1a51b0045f7b0e5b1a314c00bce1796d
RESULT_BLOB_SHA: 67342890c09d3e125612dcf94a63dacbd72d4212
```

## Exact Reviewed Blobs

```text
bridge.py: d52a0a2188ca4bc96b9c1300a5f4cd1c75577fca
src/aios_bridge/paid_api_real_escape.py: c9cc3bcc98cea93507ac9954e4b8a482de360aaf
tests/test_bridge_paid_api_real_escape.py: 582f149bedff80c75dc1f6eee070d148291c758f
tests/aios_bridge/test_paid_api_real_escape.py: 5ec71597ac7e26dfa59e562b3d8147507b70a409
tests/aios_bridge/external_brain/test_minimax_provider.py: ea243a9f36aeeda074d729bbb2ae75762844e625
tests/test_bridge_paid_api_proof_preflight.py: 92d37ae34caa462b2513df7e39dd0ac5e2027ac9
.ai/results/RESULT-064.md: 67342890c09d3e125612dcf94a63dacbd72d4212
```

## FIX Delta Audit

PASS. Exact FIX delta from `a8a4d65435879f00092285eca25b7516d18ec9da` to `5a714a410d4a4d5fc0b76cea62e7fd164f0cdd54` is:

```text
bridge.py
tests/test_bridge_paid_api_proof_preflight.py
.ai/results/RESULT-064.md  # Bridge publication output only
```

This is within the REVIEW-064 FIX writable scope. No additional production/test path changed.

Cumulative TASK-064 delta from main is also bounded to the original TASK-064 authorized implementation/test paths, the explicitly authorized legacy preflight test path added by REVIEW-064, and `RESULT-064.md` publication output.

## B1 Resolution — PASS

The TASK-specific production bypass is removed. `paid-proof-preflight` now enforces the canonical completion envelope unconditionally:

```python
if active_grant.max_output_tokens != M11_REAL_PROOF_MAX_OUTPUT_TOKENS:
    fail(...)
```

There is no `TASK-059` exemption or other task-ID exception.

The check occurs immediately after the exact grant task/workspace/actor/provider/model/max-calls bindings and before artifact re-resolution, dependency checks, local tokenizer/counter construction, and the P5 credential-presence boundary. Therefore a non-8192 grant fails before any credential value access, provider construction/invocation, or grant consumption.

The stale TASK-059 success fixture is migrated from `max_output_tokens=4000` to `8192`. A parameterized regression now verifies rejection of `4000`, `2000`, `8191`, `8193`, `64`, and `16384`; the 4000 case directly prevents recurrence of the legacy bypass.

## M11.3D Contract Audit — PASS

The RUN implementation previously reviewed as otherwise correct remains unchanged by the FIX except for the B1 production line above.

```text
M11_REAL_PROOF_MAX_OUTPUT_TOKENS: 8192
SINGLE_OUTPUT_BUDGET_AUTHORITY_PRESERVED: YES
PAID_PROOF_PREFLIGHT_8192_GATE: UNIVERSAL
PAID_PROOF_EXECUTE_8192_GATE: PRESERVED
DIRECT_REAL_ESCAPE_8192_GATE: PRESERVED
8192_TO_MODEL_REQUEST: PRESERVED
8192_TO_MINIMAX_MAX_COMPLETION_TOKENS: PRESERVED
POST_CONSUME_SAFE_DIAGNOSTIC: PRESERVED
UNKNOWN_ERROR_CODE_COLLAPSES_TO_OTHER: PRESERVED
TRUNCATED_OUTPUT_REMAINS_FAILURE: YES
R9_SUCCESS_REQUIREMENTS_UNCHANGED: YES
PROPOSAL_ON_NON_SUCCESS: NO
PROOF_JSON_ON_NON_SUCCESS: NO
CONSUME_BEFORE_CALL: PRESERVED
MAX_CALLS: 1
AUTO_RETRY: 0
SECOND_PAID_PROVIDER: 0
TIMEOUT_CONTRACT_SECONDS: 60..180
EXACT_INPUT_COUNTER_CONTRACT: PRESERVED
MODEL_RESPONSE_SCHEMA_CHANGED: NO
PROOF_LOCK_CHANGED: NO
```

No endpoint/model/proof-lock/tokenizer/chat-template/thinking behavior, retry policy, grant schema/range, ModelGateway contract, or proof receipt schema was changed.

## Tests / Evidence

Fresh FIX evidence:

```text
TARGETED COMMAND:
venv/Scripts/python.exe -m pytest tests/test_bridge_paid_api_proof_preflight.py tests/test_bridge_paid_api_real_escape.py tests/aios_bridge/test_paid_api_real_escape.py tests/aios_bridge/external_brain/test_minimax_provider.py -v
RESULT: 96 passed, 0 skipped, 0 failed

FULL REPOSITORY COMMAND:
venv/Scripts/python.exe -m pytest tests/ -q
RESULT: 1972 passed, 7 skipped, 0 failed
```

Execution-boundary evidence:

```text
REAL_PAID_API_CALL_DURING_FIX: NO
REAL_MINIMAX_NETWORK_DURING_FIX: NO
REAL_API_KEY_VALUE_USE_DURING_FIX: NO
REAL_GRANT_CREATION_DURING_FIX: NO
REAL_GRANT_CONSUME_DURING_FIX: NO
```

The existing credential-boundary tests remain green, including zero credential-value reads during pre-call validation and exactly one permitted read only inside the deferred provider factory after the locked gates.

## Review Decision

```text
TASK-064: PASS
BLOCKERS: 0
B1: RESOLVED
APPROVED: YES
READY_FOR_HUMAN_MERGE: YES
MERGE_AUTHORIZED: NO
LIVE_MINIMAX_PROOF_AUTHORIZED: NO
```

PASS does not authorize a ref move or a paid MiniMax call. Human merge authorization is still required. After a separately authorized merge, any next live M11 proof requires fresh capacity evidence, a fresh one-shot Human paid grant with `max_output_tokens=8192`, a fresh no-spend preflight, and separate explicit Human authorization for the provider call. The consumed grants from prior live attempts remain permanently non-reusable.
