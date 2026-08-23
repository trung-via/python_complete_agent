# REVIEW-065 — M11 Operational Proof Closure & Production Baseline Lock

STATUS: CHANGES_REQUIRED
APPROVED: NO
READY_FOR_HUMAN_MERGE: NO
MERGE_AUTHORIZED: NO
M11_CLOSED_BY_REVIEW: NO
LIVE_PAID_API_AUTHORIZED: NO

## Reviewed Snapshot

```text
TASK_ID: TASK-065
BASE_MAIN_SHA: 5a714a410d4a4d5fc0b76cea62e7fd164f0cdd54
BRANCH: ai/task-065
BRANCH_STATUS_VS_MAIN: AHEAD
AHEAD_BY: 1
BEHIND_BY: 0
MERGE_BASE_SHA: 5a714a410d4a4d5fc0b76cea62e7fd164f0cdd54
TASK_BLOB_SHA: 9218a6a23415b5f26f74648dce2a546c4b0d69e7
CLOSURE_BLOB_SHA: 6af75547093b916dd5b497f62fc617374d03a34c
RESULT_BLOB_SHA: 1ca814bee0998f57c397ec6031523eba8ad1d8c2
```

## Scope Audit — PASS

The task branch changes exactly:

```text
.ai/proofs/M11-OPERATIONAL-PROOF-CLOSURE-065.md
.ai/results/RESULT-065.md  # Bridge publication output only
```

No production code, test code, schema, proof-lock, ADR, grant, capacity state, usage ledger, or prior proof artifact is changed.

The reported closure evidence is otherwise directionally correct: final grant consumed, one provider call, zero retry, no executor authority created, proposal SHA match, operational-proof fingerprint match, single-call ledger evidence, exact input-token correlation, and no provider call/API-key value read during TASK-065.

## Finding B1 — BLOCKER — Locked machine-readable invariant keys are not preserved exactly

TASK-065 explicitly requires the closure record to preserve the following exact invariant keys:

```text
EXECUTOR_AUTHORITY_CREATED_BY_BRAIN: FALSE
R9_SUCCESS_REQUIRED: YES
TRUNCATED_OUTPUT_ACCEPTED: NO
LIVE_PROOF_OUTPUT_ENVELOPE: 8192
```

The current closure uses semantic aliases instead:

```text
EXECUTOR_AUTHORITY_CREATED: FALSE
R9_OPERATIONAL_PROOF_STRICTNESS: PRESERVED
REAL_PROOF_MAX_OUTPUT_TOKENS: 8192
```

and does not include `TRUNCATED_OUTPUT_ACCEPTED: NO` in the locked invariant block.

For a durable baseline-lock artifact, aliases are not sufficient. Downstream/manual verification must be able to compare the closure record against the frozen contract without interpretation.

### Required correction B1

In section `6. Locked Safety Invariants`, include the exact locked keys and values from TASK-065. Existing human-readable aliases may remain only if they do not contradict the exact keys.

At minimum the block must include exactly:

```text
MAX_CALLS: 1
AUTO_RETRY: 0
SECOND_PAID_PROVIDER: 0
CONSUME_BEFORE_CALL: REQUIRED
GRANT_REUSE: FORBIDDEN
GRANT_REACTIVATION: FORBIDDEN
EXECUTOR_AUTHORITY_CREATED_BY_BRAIN: FALSE
R9_SUCCESS_REQUIRED: YES
TRUNCATED_OUTPUT_ACCEPTED: NO
INPUT_TOKEN_EXACT_MATCH_REQUIRED: YES
TIMEOUT_CONTRACT_SECONDS: 60..180
LIVE_PROOF_OUTPUT_ENVELOPE: 8192
```

## Finding B2 — BLOCKER — `0 active grants remain for TASK-062` overstates the durable grant-store state

The closure currently states:

```text
0 active grants remain for TASK-062.
```

That wording conflates persistent runtime state with current usability.

During the final-proof preparation, a fresh one-shot TASK-062 grant was created and successfully preflighted, then expired before execution; a second fresh grant was then created for the final successful live proof. The expired preflight-only grant was never consumed or reactivated.

`AtomicPaidApiGrantStore` does not automatically delete or move an expired ACTIVE-state file when another grant is created. Expiration makes `require_active(...)` fail closed, but the persisted state can still be `ACTIVE` while usability is `EXPIRED`. Creating a later grant uses a different grant ID and does not clean earlier expired state.

Therefore the closure must not claim zero ACTIVE-state records unless an exact read-only inventory actually proves that statement.

### Required correction B2

Perform read-only inventory of TASK-062 grant state and record the distinction precisely, without copying any raw grant ID into the closure.

Acceptable semantics are:

```text
FINAL_SUCCESSFUL_GRANT_STATE: CONSUMED
PRIOR_LIVE_CALL_GRANTS_REUSABLE: NO
UNEXPIRED_USABLE_GRANTS_FOR_FINAL_PROOF: 0
EXPIRED_PREFLIGHT_ONLY_GRANT_STATE: NON_USABLE
```

If an expired preflight-only grant remains physically under `active/`, state that fact safely using count/state semantics only; do not include its raw grant ID. Do not mutate, delete, revoke, consume, reactivate, or clean up any grant during this FIX.

The required security conclusion is `no reusable/usable grant remains`, not an inaccurate claim that no ACTIVE-state file exists.

## Exact FIX Writable Scope

EXECUTOR_ALLOWED_PATHS_JSON: [".ai/proofs/M11-OPERATIONAL-PROOF-CLOSURE-065.md"]

Bridge-generated `.ai/results/RESULT-065.md` remains publication output only.

No production/test/runtime path is authorized.

## FIX Executor Dispatch Policy

DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]},{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]}],"operation":"FIX","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

Human selects exactly one subscription Executor. No silent reroute, paid Executor, automatic failover, or second executor.

## FIX Validation

No provider call and no runtime mutation are permitted.

Required checks:

```text
git diff --check
exact writable-scope check
read-only TASK-062 grant-state inventory
exact invariant-key presence check
no raw grant ID / secret / raw provider body / provider request ID / absolute local path leakage
```

Do not independently rerun the full repository suite merely for this documentation-only FIX. If Bridge publication enforces its own mandatory repository test gate, let Bridge perform it.

Required evidence:

```text
EXACT_LOCKED_INVARIANT_KEYS_PRESENT: YES
FINAL_SUCCESSFUL_GRANT_STATE: CONSUMED
PRIOR_LIVE_CALL_GRANTS_REUSABLE: NO
UNEXPIRED_USABLE_GRANTS_FOR_FINAL_PROOF: 0
GRANT_STATE_WORDING_ACCURATE: YES
NO_GRANT_MUTATION_DURING_FIX: YES
NO_PROVIDER_CALL_DURING_FIX: YES
NO_API_KEY_VALUE_READ_DURING_FIX: YES
NO_PRODUCTION_CODE_CHANGE: YES
NO_TEST_CODE_CHANGE: YES
NO_SECRET_OR_RAW_RESPONSE_LEAK: YES
SCOPE_EXACT: YES
```

## Evidence Already Passing

`RESULT-065.md` reports:

```text
M11_STATUS: OPERATIONALLY_PROVEN
M11_CLOSED: YES
FINAL_GRANT_STATE: CONSUMED
FINAL_PROVIDER_CALL_COUNT: 1
FINAL_RETRY_COUNT: 0
FINAL_EXECUTOR_AUTHORITY_CREATED: NO
FINAL_PROPOSAL_SHA256_MATCH: YES
FINAL_OPERATIONAL_PROOF_FINGERPRINT_MATCH: YES
FINAL_LEDGER_SINGLE_CALL_EVIDENCE: YES
FINAL_INPUT_TOKEN_CORRELATION_EXACT: YES
NO_RUNTIME_MUTATION: YES
NO_PROVIDER_CALL_DURING_TASK: YES
NO_API_KEY_VALUE_READ_DURING_TASK: YES
SCOPE_EXACT: YES
```

Bridge publication also reports the repository suite green at `1972 passed, 7 skipped, 0 failed`. These do not override B1/B2 because TASK-065 is a durable evidence contract and the closure text itself must be exact.

## Review Decision

```text
TASK-065: CHANGES_REQUIRED
BLOCKERS: 2
B1: RESTORE EXACT LOCKED INVARIANT KEYS
B2: CORRECT ACTIVE-STATE VS USABILITY GRANT CLAIM
MERGE: FORBIDDEN
M11_CLOSURE_EVENT: NOT YET FINAL
PAID PROVIDER CALL: FORBIDDEN
```

After a clean documentation-only FIX publication, ChatGPT must review the new closure blob before merge. No new paid API call is needed or authorized.