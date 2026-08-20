# REVIEW-058 — TASK-058 M11.3A Operational Paid-API Proof Receipt + Correlation Verifier

STATUS: PASS
APPROVED: YES
READY_FOR_HUMAN_MERGE: YES
MERGE_AUTHORIZED: NO
MERGED_TO_MAIN: NO

## Review Anchors

```text
TASK_ID: TASK-058
MILESTONE: M11.3A — OPERATIONAL ESCAPE PROOF RECEIPT / OFFLINE CORRELATION
BASELINE_MAIN_SHA: 1331813af4e21fa4e1769bcfe439abb1c67f7f20
TASK_BRANCH: ai/task-058
FINAL_REVIEWED_TASK_HEAD_SHA: 0d7bddac2066ad508bf68fbb4d3bd8b69b18d1b3
TASK_BLOB_SHA: 6f59b037d7fefe4e2f1602b86315c55b0865e8d7
BLUEPRINT_BLOB_SHA: 403e2df4971781fb0b6226001b581014700c5e77
RESULT_058_BLOB_SHA: 35825b6eaa4f0fd7f5a852c1e80b8ce8cbdb9fb0
PAID_ESCAPE_BLOB_SHA: a3978dd69df6617b6fbf96f3f297ae4891e23b5a
OPERATIONAL_PROOF_BLOB_SHA: 8425c49a571cbfa8959fb8c9d39b39100d3e4466
PAID_ESCAPE_TEST_BLOB_SHA: d35d133c79146b840aa59821af11f25201ff175c
OPERATIONAL_PROOF_TEST_BLOB_SHA: 1f2b72198abd778805cfa51612d234882f2d3eb0
E4_CONTROL_COMMIT_SHA: d6d9ae5a4660e7a81420f9fc770137be61fd5d4e
```

## Lineage / Scope — PASS

Independent GitHub comparison proves:

```text
main: 1331813af4e21fa4e1769bcfe439abb1c67f7f20
ai/task-058: 0d7bddac2066ad508bf68fbb4d3bd8b69b18d1b3
status: ahead
commits_ahead: 1
commits_behind: 0
merge_base: 1331813af4e21fa4e1769bcfe439abb1c67f7f20
```

Changed files are exactly the four authorized implementation/test paths plus Bridge-generated RESULT:

```text
.ai/results/RESULT-058.md
src/aios_bridge/paid_api_brain_escape.py
src/aios_bridge/paid_api_operational_proof.py
tests/aios_bridge/test_paid_api_brain_escape.py
tests/aios_bridge/test_paid_api_operational_proof.py
```

Final reviewed SHA -> `ai/task-058` compares IDENTICAL.

## Core Requirement 1 — Original Pre-call Evidence — PASS

`PaidApiBrainEscapeResult` now requires exact `ProviderInputCountEvidence`.

The coordinator stores the exact object produced by the existing single:

```text
count_request(model_request)
```

and returns that same object on every normal dispatch return. No second counter call was introduced and the count remains before paid enablement/dispatch.

Regression coverage proves:

```text
ESCAPE_RESULT_REQUIRES_PRECALL_EVIDENCE
COORDINATOR_RETURNS_ORIGINAL_EVIDENCE
COUNTER_EXACTLY_ONCE
PROOF_DOES_NOT_COUNT_AGAIN
```

The integration test creates the operational receipt after a paid-path synthetic gateway result and verifies the counter call count remains exactly one.

## Core Requirement 2 — Operational Proof Verifier — PASS

`paid_api_operational_proof.py` implements a frozen bounded receipt plus a read-only/offline verifier.

Verified proof chain:

```text
Human grant semantics
  -> effective paid dispatch exact binding
  -> exact PAID_API Brain selection
  -> durable CONSUMED-only grant state
  -> original exact precall ProviderInputCountEvidence
  -> exact ModelRequest fingerprint/bounds
  -> exact successful GatewayResult/ModelResponse
  -> exact provider request ID + input/output usage
  -> durable ledger success indicator
  -> exact UsageRecord correlation
  -> bounded deterministic receipt
```

### Paid Selection / Authority

Verifier requires:

```text
paid_candidate_selected == True
grant_consumed == True
effective allow_paid_api == True
dispatch status == SELECTED
actor_kind == BRAIN
selected actor == grant.brain_id
selected granted candidate == PAID_API
dispatch request fingerprint exact
Brain operation exact
```

### Durable Grant State

Verifier only calls `load_active()` and `load_consumed()`.

It requires:

```text
ACTIVE == None
CONSUMED == exact grant
CONSUMED fingerprint == exact grant fingerprint
workspace binding exact
```

No grant activation, consume, reactivation, clock lookup, or mutation exists in the verifier.

### Original Pre-call Evidence

Verifier requires exact `ProviderInputCountEvidence` and exact:

```text
provider/model == grant
model_request_fingerprint == fingerprint_model_request(model_request)
token_count_is_exact == True
counter_id bounded/non-empty
local_input exact non-negative int
local_input <= request max_input <= grant max_input
request max_output <= grant max_output
```

### Gateway / Response Success

Verifier rejects every non-SUCCESS response status, including FAILED, RATE_LIMITED, UNAVAILABLE, TIMEOUT, AUTH_ERROR and INVALID_RESPONSE.

For SUCCESS it requires exact request/task/provider/model/output-type correlation, non-empty provider request ID, exact non-negative provider input/output token usage, and output usage within request/Human-grant bounds.

### Critical Token Correlation — PASS

The required operational equality is mechanically enforced:

```text
original local precall counted_input_tokens
  == ModelResponse.input_tokens
  == UsageRecord.provider_input_tokens
```

There is no tolerance, estimate band, cache adjustment, second count, or retry path.

Response output usage must also exactly equal UsageRecord provider output usage.

### Usage Ledger Correlation — PASS

Verifier requires:

```text
gateway_result.ledger_persisted is True
gateway_result.ledger_error_code is None
```

and exact UsageRecord request/task/provider/requested-model/actual-model/status/provider-request-id/input/output correlation.

A provider success whose gateway ledger append failed cannot produce an operational proof receipt.

### Receipt — PASS

Receipt is frozen and validates exact/bounded field types, bool-as-int rejection, Git/SHA formats, SUCCESS-only status, `ledger_persisted=True`, `grant_consumed=True`, `input_token_match=True`, and exact local/provider input equality.

It contains only bounded metadata and a SHA-256 of validated response content; it does not persist prompt/context/output plaintext, API keys, headers, cookies, raw response body, tokenizer/template bytes, or timestamps.

Canonical JSON and receipt fingerprint are deterministic.

## Offline / No-Side-Effect Surface — PASS

The verifier signature accepts only:

```text
escape_result
grant
grant_store
model_request
```

It has no counter, gateway, provider, ledger writer, clock, environment, credential, retry, or dispatch parameter.

Tests prove the verifier performs exactly two read-only grant-state observations and no grant mutation. Production proof module has no network client, subprocess, environment, datetime, provider invocation, counter invocation, dispatch call, or ledger append surface.

## Test / E4 Evidence

Bridge-owned full repository suite:

```text
1833 passed, 9 skipped, 1533 warnings in 175.83s
EXIT_CODE: 0
```

E4:

```text
ACTION: RUN
EXECUTOR_ID: codex
E4_CONTROL_COMMIT_SHA: d6d9ae5a4660e7a81420f9fc770137be61fd5d4e
E4_TRANSPORT_STATUS: EXITED_ZERO
E4_PRE_EXECUTION_HEAD: 1331813af4e21fa4e1769bcfe439abb1c67f7f20
E4_ALLOWED_SCOPE_VERIFIED: PASS
E4_PUBLICATION_TRUST_VERIFIED: PASS
E4_DIRTY_PATH_COUNT: 4
```

## Non-Blocking Evidence Note N1 — RESULT Diff Stat Incomplete

`RESULT-058.md` lists all four implementation/test files under `Files Changed`, but its Diff Stat reports only the modified paid-escape source/test pair and omits the two newly added operational-proof source/test files.

Independent GitHub compare proves the complete actual delta and exact allowed scope, so this is not a TASK-058 code blocker. RESULT diff-stat output should not be treated as complete publication evidence for this run.

## Remaining M11.3 Boundary

TASK-058 is offline proof infrastructure only.

It does NOT authorize or complete:

```text
M11.3B runtime proof command / provisioning preflight
M11.3C real MiniMax call
API key access
asset provisioning
paid spend
retry
second provider
```

Before any real proof, M11.3B must still enforce the exact runtime dependencies/assets, durable `JsonlUsageLedger`, credential boundary, exact Human grant, and one-shot command semantics.

## Findings

```text
BLOCKING_FINDINGS: 0
NON_BLOCKING_FINDINGS: 1
N1: RESULT diff stat incomplete but independently recoverable
REGRESSIONS_OBSERVED: 0
FINAL_INDEPENDENT_AUDIT: PASS
```

## Decision

TASK-058 / M11.3A is approved for Human merge at exact reviewed head:

```text
0d7bddac2066ad508bf68fbb4d3bd8b69b18d1b3
```

No merge is performed by this review.

Human merge gate:

```text
Merge TASK-058
```

Do not begin M11.3B/C automatically. No real paid API call is authorized by this review.
