# REVIEW-055 — TASK-055 M11.2C.1 Full Provider Input Budget Proof Hardening

STATUS: PASS
APPROVED: YES
READY_FOR_HUMAN_MERGE: YES
MERGE_AUTHORIZED: YES
MERGED_TO_MAIN: NO

## Review Anchors

```text
TASK_ID: TASK-055
MILESTONE: M11.2C.1 — FULL PROVIDER INPUT TOKEN BOUND HARDENING
BASELINE_MAIN_SHA: 439f073da2a112531dc78669dfb4aea53f88439b
TASK_BRANCH: ai/task-055
INITIAL_REVIEWED_HEAD_SHA: 42357e7e4dcfd1be7ad6e636e589c14f305ecb51
FINAL_REVIEWED_TASK_HEAD_SHA: 867cb5cdb730639db93a1f184f065dbb97230cd0
TASK_BLOB_SHA: dd46a3615601ed871a7cd73ae80fcc17c8e4c143
BLUEPRINT_BLOB_SHA: ee17d57a47c2a315877dae91ff448733e29347d8
FIX_AUTH_REVIEW_BLOB_SHA: 13738bbe0b6ef82d8aac615a5c8b587e54665c10
RESULT_055_BLOB_SHA: f1ae493afebf728de5b92b43c5dd476cc0d7bb54
PROVIDER_INPUT_BUDGET_BLOB_SHA: 0a6f9b5c5201215ef654b068aea215f370cc4593
PAID_API_BRAIN_ESCAPE_BLOB_SHA: 8d536dd8dff7f7fb562666d6427a661a9e0dd15e
TEST_BLOB_SHA: 7d7c095f103fe302168f3a66682aaeeb3bc09319
E4_FIX_CONTROL_COMMIT_SHA: 85242e9a5ce60a2f8f2938365acececd9918cd3c
```

## Lineage / Scope — PASS

Independent comparison before merge proves:

```text
main: 439f073da2a112531dc78669dfb4aea53f88439b
ai/task-055 final: 867cb5cdb730639db93a1f184f065dbb97230cd0
status: ahead
commits_ahead: 2
commits_behind: 0
merge_base: 439f073da2a112531dc78669dfb4aea53f88439b
reviewed-head -> task-branch: IDENTICAL
```

The FIX delta from the initial reviewed head is exactly one additional commit:

```text
42357e7e4dcfd1be7ad6e636e589c14f305ecb51
  -> 867cb5cdb730639db93a1f184f065dbb97230cd0
```

FIX touched only:

```text
.ai/results/RESULT-055.md
src/aios_bridge/paid_api_brain_escape.py
src/aios_bridge/provider_input_budget.py
tests/aios_bridge/test_paid_api_brain_escape.py
```

Implementation scope remains the three authorized production/test paths plus Bridge-generated RESULT publication.

## Original Budget Hardening — PASS

The merged M11.2C coordinator is now additionally protected by a mandatory full-provider-input proof surface:

- `provider_input_counter` is mandatory and keyword-only; there is no permissive default.
- `ProviderInputCountEvidence` is immutable and stores no prompt body, request body, credential, or authorization header.
- `fingerprint_model_request()` binds evidence to canonical `ModelRequest.to_dict()` semantics using compact sorted UTF-8 JSON + SHA-256.
- Provider/model/counter identity and `is_exact is True` are validated.
- `count_request(model_request)` runs exactly once after trust is established.
- Evidence exact type, provider/model/counter ID, request fingerprint, exactness, and token count are revalidated.
- `counted_input_tokens <= model_request.max_input_tokens` is enforced.
- Existing M11.1 budget validation still enforces `model_request.max_input_tokens <= grant.max_input_tokens` and output bound.
- Context-only `token_count_is_exact=True` is no longer sufficient authorization for paid dispatch.

## B1 Re-review — RESOLVED

Original blocking finding:

```text
B1: local/no-network counter authority was not mechanically enforced
```

The FIX adds an explicit trusted-local implementation authority in `provider_input_budget.py`:

```text
_TRUSTED_LOCAL_COUNTER_TYPES: tuple[type[object], ...] = ()
```

Production state is intentionally closed: no real counter type is trusted yet.

Before any caller-controlled counter property or callback is evaluated, the coordinator now calls:

```text
require_trusted_local_provider_input_counter(provider_input_counter)
```

Trust semantics are exact-type based:

```text
ARBITRARY_PROTOCOL_CONFORMING_COUNTER: REJECT
UNREGISTERED SUBCLASS: REJECT
SELF_ASSERTED is_exact=True: INSUFFICIENT
UNTRUSTED PROPERTY ACCESS: NONE
UNTRUSTED count_request CALLBACK: NONE
TRUSTED EXACT REGISTERED TYPE: REQUIRED
```

This satisfies the TASK-055 locked allowance for an exact trusted implementation registration seam intended for TASK-056. Structural Protocol conformance alone no longer grants paid-budget authority.

Regression tests mechanically prove:

- a Protocol-conforming subclass is rejected before count/dispatch/consume/provider call;
- an untrusted object with side-effecting properties and `count_request()` triggers zero property accesses and zero callbacks;
- trust decision occurs before `count_request()`;
- a trusted deterministic local test counter is called exactly once;
- all existing provider/model/request fingerprint/budget checks remain active after trust.

Therefore the original network-capable arbitrary-counter path is closed fail-closed.

## Production Trust State

TASK-055 does not register a real MiniMax counter.

```text
PRODUCTION_TRUSTED_COUNTER_TYPES: EMPTY
REAL_MINIMAX_COUNTER: NOT_IMPLEMENTED
REAL_TOKENIZER_DOWNLOAD: NO
NETWORK_TOKEN_COUNT_ENDPOINT: NO
REAL_PROVIDER_CALL: NO
```

TASK-056 may add one audited exact local MiniMax-M3 implementation and explicitly register that exact concrete type. That future registration requires separate review; TASK-055 itself does not open production authority.

## Existing M11.2C Invariants — PRESERVED

```text
BASE_ALLOW_PAID_API_FALSE: PASS
EXACT_ONE_PAID_CANDIDATE: PASS
ACTIVE_GRANT_REQUIRED: PASS
TASK_WORKSPACE_PROVIDER_MODEL_OPERATION_BINDING: PASS
AUTHORIZED_ARTIFACT_CONTENT_BLOB_PROOF: PASS
EXACT_CONTEXT_COUNTER_REQUIRED: PASS
FULL_PROVIDER_INPUT_PROOF_REQUIRED: PASS
FULL_INPUT_REQUEST_FINGERPRINT_BINDING: PASS
FULL_INPUT_WITHIN_MODEL_REQUEST_LIMIT: PASS
MODEL_REQUEST_WITHIN_HUMAN_GRANT: PASS
SUBSCRIPTION_STILL_PREFERRED: PASS
SUBSCRIPTION_WIN_GRANT_REMAINS_ACTIVE: PASS
SUBSCRIPTION_WIN_GATEWAY_CALLS_ZERO: PASS
PAID_WIN_CONSUME_BEFORE_GATEWAY: PASS
CONSUME_FAILURE_GATEWAY_CALLS_ZERO: PASS
GATEWAY_FAILURE_GRANT_STAYS_CONSUMED: PASS
REPLAY_CLOSED: PASS
NO_RETRY: PASS
NO_SECOND_PAID_PROVIDER: PASS
NO_EXECUTOR_AUTHORITY: PASS
```

## Test / E4 Evidence

Bridge-owned full repository suite after FIX:

```text
1752 passed, 7 skipped, 1533 warnings in 153.02s
EXIT_CODE: 0
```

FIX E4 evidence:

```text
ACTION: FIX
EXECUTOR_ID: codex
AUTHORIZED_ARTIFACT: .ai/reviews/REVIEW-055.md @ 13738bbe0b6ef82d8aac615a5c8b587e54665c10
E4_CONTROL_COMMIT_SHA: 85242e9a5ce60a2f8f2938365acececd9918cd3c
E4_TRANSPORT_STATUS: EXITED_ZERO
E4_PRE_EXECUTION_HEAD: 42357e7e4dcfd1be7ad6e636e589c14f305ecb51
E4_ALLOWED_SCOPE_VERIFIED: PASS
E4_PUBLICATION_TRUST_VERIFIED: PASS
E4_DIRTY_PATH_COUNT: 3
```

## Findings

```text
BLOCKING_FINDINGS: 0
B1: RESOLVED
NON_BLOCKING_FINDINGS: 0
N1: RESOLVED
REGRESSIONS_OBSERVED: 0
FINAL_INDEPENDENT_AUDIT: PASS
```

## Merge Authorization Receipt

Human explicitly authorized:

```text
Merge TASK-055
```

Pre-merge authorization is recorded here without claiming the merge has completed. Exact reviewed head and lineage were revalidated immediately before the ref update.

## Decision

TASK-055 / M11.2C.1 remains approved at exact reviewed head:

```text
867cb5cdb730639db93a1f184f065dbb97230cd0
```

MERGED_TO_MAIN remains NO until the exact fast-forward ref update and post-merge verification succeed.
