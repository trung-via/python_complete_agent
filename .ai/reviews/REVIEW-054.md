# REVIEW-054 — TASK-054 M11.2C Grant-Aware Brain Dispatch + Consume-Before-Call

STATUS: PASS
APPROVED: YES
READY_FOR_HUMAN_MERGE: YES
MERGE_AUTHORIZED: YES
MERGED_TO_MAIN: YES

## Review Anchors

```text
TASK_ID: TASK-054
MILESTONE: M11.2C — Grant-Aware Brain Dispatch + Consume-Before-Call
BASELINE_MAIN_SHA: d3f66189431755cc8c188ab5bc9866c069f0e3e3
TASK_BRANCH: ai/task-054
REVIEWED_TASK_HEAD_SHA: 439f073da2a112531dc78669dfb4aea53f88439b
TASK_BLOB_SHA: f60fad076033fb7a0fa5e32122ae9f7d464b158f
BLUEPRINT_BLOB_SHA: 7ca33e405293dbc3033ca178ba54a3ce94830891
RESULT_054_BLOB_SHA: 0cc06ef62cbc4206aac35297615221a041037eb3
PRODUCTION_BLOB_SHA: bb4694201ac3ead22e43ecadc0bf78c8ff788e5c
TEST_BLOB_SHA: 012148fff7309bb3451c63f61cd0a505ad3e11cc
E4_CONTROL_COMMIT_SHA: 35d1a5d874d88479c2473e2bcea6f6e40a2913d2
```

## Lineage / Scope

Independent GitHub comparison before merge proved:

```text
main: d3f66189431755cc8c188ab5bc9866c069f0e3e3
ai/task-054: 439f073da2a112531dc78669dfb4aea53f88439b
status: ahead
commits_ahead: 1
commits_behind: 0
merge_base: d3f66189431755cc8c188ab5bc9866c069f0e3e3
```

Changed files are exactly:

```text
.ai/results/RESULT-054.md
src/aios_bridge/paid_api_brain_escape.py
tests/aios_bridge/test_paid_api_brain_escape.py
```

Executor implementation scope is therefore exact: the two authorized files plus Bridge-generated RESULT publication.

## Independent Contract Audit — PASS

### Paid enablement boundary
- Incoming value must be exact `BrainDispatchRequest` with `allow_paid_api is False`.
- Exactly one PAID_API Brain candidate is required.
- That one paid candidate must exactly match `grant.brain_id`.
- No Executor request/authority surface exists in the coordinator.
- The effective request with `allow_paid_api=True` is constructed only after ACTIVE grant, provider/model, operation, artifact/context and exact-token validation.

### Exact ACTIVE grant binding
- `AtomicPaidApiGrantStore.require_active()` is called before paid enablement.
- Existing M11.1 binding validation enforces exact task/workspace/brain/provider/model/continuity operation/artifact path/blob identity.
- Gateway provider `provider_id` and `model_name` must be exact non-empty strings and match the grant.
- `ModelRequest.provider`, `model`, task and mapped External Brain operation are also checked exactly.

### Operation mapping
Exact supported mapping is implemented without aliases:

```text
continuity.PLAN           -> external.PLAN
continuity.DIAGNOSIS      -> external.DIAGNOSE_FAILURE
continuity.PATCH_PROPOSAL -> external.GENERATE_PATCH
continuity.REVIEW         -> external.REVIEW_PATCH
```

`TASK` and `TASK_AND_PLAN` fail closed.

### Artifact-in-context proof
- Artifact pointer path/blob must exactly equal the grant binding.
- Exactly one selected ContextItem must carry the authorized path.
- The exact UTF-8 content is converted to canonical Git blob SHA-1 using `blob <len>\0<payload>` framing.
- Any content/blob mismatch fails before paid dispatch enablement, consume or gateway invocation.

### Exact token/budget gate
Before paid enablement:

```text
context_build.token_count_is_exact == True
counter_id is exact non-empty string
max_input_tokens is exact positive int
max_output_tokens is exact positive int
context_build.max_context_tokens == model_request.max_input_tokens
counted_tokens + protocol_reserve_tokens <= max_context_tokens
```

M11.1 budget validation then proves the request token envelope is within the Human grant. Conservative/non-exact counters are rejected.

### M10 ranking preserved
The module calls existing `dispatch_brain()` unchanged. It does not alter M10 dispatch contracts or ranking.

A runnable SUBSCRIPTION Brain still wins over PAID_API even with a worse preference rank. On subscription / WAIT / no-compatible outcomes:

```text
grant consume calls: 0
gateway calls: 0
grant remains ACTIVE
gateway_result: None
```

### Consume-before-call / one-shot safety
Paid selection path is mechanically ordered:

```text
dispatch selects exact granted paid Brain
↓
AtomicPaidApiGrantStore.consume(grant) succeeds
↓
await ModelGateway.invoke(...) exactly once
```

There is no provider call before consume and no retry loop.

If consume fails, gateway calls remain zero.
If gateway/provider/ledger fails after consume, ACTIVE is never restored.
Sequential replay fails before a second provider call.
No second provider/fallback path exists.

### Concurrency note — non-blocking
The TASK-054 integration test uses two `asyncio.gather()` callers and observes one success / one failure / one provider call. Because the coordinator has no `await` before synchronous atomic `consume()`, that test does not force a cross-thread pre-consume overlap.

This is not a blocking implementation defect: M11.2A already provides task-scoped cross-thread/cross-process atomic consume with exactly one ACTIVE->CONSUMED winner, and TASK-054 places that atomic consume synchronously before the first gateway await. The composed one-shot property therefore remains fail-closed. A future stress test may add a true cross-thread coordinator race for stronger integration evidence.

## Security / Authority Boundary

TASK-054 does not:

```text
read API credentials directly
persist credentials
use subprocess/socket/requests/urllib
mutate Git or .ai/ worktree artifacts
create Executor authorization or lease
change M10 ranking/contracts
change M11.1 / M11.2A / M11.2B
retry provider calls
select a second paid provider
apply model output to worktree
perform a real network call in tests
implement M11.3
activate H-Series
```

The runtime coordinator can invoke only the caller-supplied existing `ModelGateway`; Brain output remains proposal-only and grants no worktree authority.

## Test Evidence

Bridge-owned full repository suite:

```text
1724 passed, 7 skipped, 1533 warnings in 153.32s
EXIT_CODE: 0
```

E4 evidence:

```text
ACTION: RUN
EXECUTOR_ID: codex
E4_AUTO_EXECUTION: YES
E4_CONTROL_COMMIT_SHA: 35d1a5d874d88479c2473e2bcea6f6e40a2913d2
E4_TRANSPORT_STATUS: EXITED_ZERO
E4_PRE_EXECUTION_HEAD: d3f66189431755cc8c188ab5bc9866c069f0e3e3
E4_ALLOWED_SCOPE_VERIFIED: PASS
E4_PUBLICATION_TRUST_VERIFIED: PASS
E4_DIRTY_PATH_COUNT: 2
```

## Findings

```text
BLOCKING_FINDINGS: 0
NON_BLOCKING_FINDINGS: 1
N1: coordinator concurrency integration test does not force cross-thread overlap; atomic safety is already supplied by merged M11.2A and preserved by consume-before-first-await ordering
REGRESSIONS: 0
```

## Acceptance

```text
CHILD_EXECUTOR_ROLE_LOCK: PASS
ONE_GRANTED_PAID_CANDIDATE_ONLY: PASS
ACTIVE_EXACT_GRANT_REQUIRED: PASS
OPERATION_MAPPING_EXACT: PASS
UNSUPPORTED_CONTINUITY_OPERATIONS_FAIL_CLOSED: PASS
TASK_WORKSPACE_PROVIDER_MODEL_BINDING: PASS
AUTHORIZED_ARTIFACT_CONTENT_BINDING: PASS
EXACT_COUNTER_REQUIRED: PASS
TOKEN_BOUNDS_REQUIRED: PASS
SUBSCRIPTION_STILL_PREFERRED: PASS
SUBSCRIPTION_WIN_GRANT_REMAINS_ACTIVE: PASS
SUBSCRIPTION_WIN_GATEWAY_CALLS_ZERO: PASS
PAID_WIN_CONSUME_BEFORE_GATEWAY: PASS
CONSUME_FAILURE_GATEWAY_CALLS_ZERO: PASS
GATEWAY_EXCEPTION_GRANT_STAYS_CONSUMED: PASS
PROVIDER_FAILURE_GRANT_STAYS_CONSUMED: PASS
LEDGER_FAILURE_GRANT_STAYS_CONSUMED: PASS
REPLAY_GATEWAY_CALLS_ZERO: PASS
CONCURRENT_ONE_SHOT_SAFETY: PASS
NO_RETRY: PASS
NO_SECOND_PROVIDER: PASS
NO_EXECUTOR_AUTHORITY: PASS
NO_GIT_WORKTREE_MUTATION: PASS
NO_REAL_NETWORK_TEST: PASS
FULL_REPO_TESTS: PASS
REGRESSIONS: 0
FINAL_INDEPENDENT_AUDIT: PASS
```

## Merge Receipt

Human explicitly authorized:

```text
Merge TASK-054
```

Merge execution:

```text
MERGE_METHOD: FAST_FORWARD_REF_UPDATE
FORCE: FALSE
PRE_MERGE_MAIN_SHA: d3f66189431755cc8c188ab5bc9866c069f0e3e3
MERGED_TASK_HEAD_SHA: 439f073da2a112531dc78669dfb4aea53f88439b
POST_MERGE_MAIN_SHA: 439f073da2a112531dc78669dfb4aea53f88439b
POST_MERGE_COMPARE_STATUS: IDENTICAL
FAST_FORWARD_MERGE: PASS
POST_MERGE_EXACT_HEAD: PASS
```

## Decision

TASK-054 / M11.2C is merged to `main` at the exact independently reviewed head:

```text
439f073da2a112531dc78669dfb4aea53f88439b
```

M11.3 is not started by this merge. Any real paid API operational proof still requires a separate explicit Human authorization.