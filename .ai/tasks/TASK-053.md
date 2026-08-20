# TASK-053 — M11.2C Grant-Aware Brain Dispatch + Consume-Before-Call

STATUS: READY
CLASS: L3 — SECURITY-CRITICAL PAID-API BRAIN RUNTIME / ONE-SHOT SPEND
MILESTONE: M11.2C
EXECUTOR_MODE: UNIFIED_AIOS_WORKER_DUAL_EXECUTOR

## Baseline

```text
MAIN_SHA: d3f66189431755cc8c188ab5bc9866c069f0e3e3
TARGET_BRANCH: ai/task-053
```

## Authoritative Contracts

```text
ADR_036_PATH: .ai/decisions/ADR-036-M11-EXTERNAL-API-ESCAPE-HATCH-ARCHITECTURE-LOCK.md
ADR_036_BLOB_SHA: cf71c571d8e3fd611ea07d21f15ad0bf90ef6ecc
ADR_038_PATH: .ai/decisions/ADR-038-DEFAULT-DUAL-EXECUTOR-TASK-AUTHORING-POLICY-LOCK.md
ADR_038_BLOB_SHA: 72d38bf2f2ff5a07e7b63322116ad87622349df1
BLUEPRINT_PATH: .ai/context/TASK-053-M11.2C-GRANT-AWARE-BRAIN-DISPATCH-PRECALL-BLUEPRINT.md
BLUEPRINT_BLOB_SHA: 93cab4add451f58082e760fdd5fe8cde6bad5401
REVIEW_052_PATH: .ai/reviews/REVIEW-052.md
REVIEW_052_BLOB_SHA: 06ddb1061af2bb21432c3e4910f4fc183f54f2e5
```

Merged source anchors at baseline:

```text
src/aios_bridge/paid_api_grant.py                    7f1e1fe666154a9b17013a2cb084db9ce36f134f
src/aios_bridge/runtime_paid_api_grant.py            a3c7a446ff0f8195e68640493900776334a9e551
src/aios_bridge/continuity/dispatch.py                9169884c079302f86bbda5f77a9a9d7ea6800dd9
src/aios_bridge/continuity/state.py                   3b2c04169a85c54ccac1abe0736934cee1624af1
src/aios_bridge/continuity/brain.py                   3516423a53d8dad59b1b1e0ab9c292b1abb0337b
src/aios_bridge/external_brain/contracts.py           325795cf541bacb6ab8b9be4bc9a88d9b9e16349
src/aios_bridge/external_brain/context.py             b0cbaa7ee6f59fe25f7242c7f28ce5d08e61a774
src/aios_bridge/external_brain/gateway.py             45d6ec94f3916362783f03f1474b6cc651d8d9e5
src/aios_bridge/external_brain/provider.py            1f2ed691913b0b1b1d73887a7c73a7a34434cf3a
```

## Objective

Implement the M11.2C runtime coordinator that may unlock exactly one Human-granted PAID_API Brain candidate, lets existing M10 deterministic dispatch decide whether subscription still wins, and if paid Brain is selected consumes the exact grant durably before one and only one `ModelGateway.invoke()`.

No real paid network call is authorized by TASK-053. Tests must be offline.

## Machine-Readable Executor Context

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/decisions/ADR-036-M11-EXTERNAL-API-ESCAPE-HATCH-ARCHITECTURE-LOCK.md","blob_sha":"cf71c571d8e3fd611ea07d21f15ad0bf90ef6ecc"},{"path":".ai/decisions/ADR-038-DEFAULT-DUAL-EXECUTOR-TASK-AUTHORING-POLICY-LOCK.md","blob_sha":"72d38bf2f2ff5a07e7b63322116ad87622349df1"},{"path":".ai/context/TASK-053-M11.2C-GRANT-AWARE-BRAIN-DISPATCH-PRECALL-BLUEPRINT.md","blob_sha":"93cab4add451f58082e760fdd5fe8cde6bad5401"},{"path":".ai/reviews/REVIEW-052.md","blob_sha":"06ddb1061af2bb21432c3e4910f4fc183f54f2e5"}]

## Machine-Readable Executor Worktree Scope

EXECUTOR_ALLOWED_PATHS_JSON: ["src/aios_bridge/paid_api_brain_escape.py","tests/aios_bridge/test_paid_api_brain_escape.py"]

Bridge-generated `.ai/results/RESULT-053.md` is publication output, not Executor implementation scope.

## Executor Dispatch Policy

DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

TASK-053 implementation itself uses subscription Executor capacity only. It must never use a paid Executor.

Human selects exactly one Executor. No silent reroute, no second Executor, no paid Executor.

## Human RUN Choice

Choose exactly one:

```text
Antigravity:
/aios-worker RUN TASK-053

Codex:
$aios-worker RUN TASK-053
```

## Exact Writable Files

Executor may create/modify exactly:

```text
src/aios_bridge/paid_api_brain_escape.py
tests/aios_bridge/test_paid_api_brain_escape.py
```

Do not modify any existing production module.

## Bounded Read-Only Source Scope

Executor MAY read exactly:

```text
src/aios_bridge/paid_api_grant.py
src/aios_bridge/runtime_paid_api_grant.py
src/aios_bridge/continuity/dispatch.py
src/aios_bridge/continuity/state.py
src/aios_bridge/continuity/brain.py
src/aios_bridge/external_brain/contracts.py
src/aios_bridge/external_brain/context.py
src/aios_bridge/external_brain/gateway.py
src/aios_bridge/external_brain/provider.py
```

Do not broaden repository inspection beyond Bridge-delivered TASK/context and these paths.

## Required Runtime Contract

Implement the exact blueprint semantics.

Critical invariants:

```text
BASE_ALLOW_PAID_API: FALSE REQUIRED
PAID_API_BRAIN_CANDIDATES: EXACTLY ONE
GRANTED_PAID_BRAIN: EXACT MATCH
ACTIVE_GRANT: REQUIRED BEFORE ENABLE
M10_RANKING: UNCHANGED
SUBSCRIPTION_PREFERENCE: PRESERVED
CONSUME_BEFORE_GATEWAY: REQUIRED
GATEWAY_CALLS_MAX: 1
AUTO_RETRY: FORBIDDEN
SECOND_PAID_PROVIDER: FORBIDDEN
EXECUTOR_AUTHORITY: NONE
REAL_NETWORK_TEST: FORBIDDEN
```

## Exact Operation Mapping

Use explicit continuity -> External Brain mapping only:

```text
PLAN           -> PLAN
DIAGNOSIS      -> DIAGNOSE_FAILURE
PATCH_PROPOSAL -> GENERATE_PATCH
REVIEW         -> REVIEW_PATCH
```

Fail closed for:

```text
TASK
TASK_AND_PLAN
```

No aliasing to PLAN.

## Grant Binding Before Effective allow_paid_api=true

Before constructing any effective dispatch request with `allow_paid_api=true`, prove exact:

```text
persisted ACTIVE grant / fingerprint / unexpired state
workspace
model_request.task_id
paid candidate brain_id
provider_id
model_id
continuity operation
authorized artifact path/blob
configured gateway provider identity
configured gateway provider model_name
ModelRequest external operation
ModelRequest context correlation
Human token envelope
```

Use existing M11.1 validators where applicable.

## Artifact-in-Context Proof

The grant-bound control artifact must actually be in the selected paid model context.

Require exactly one selected ContextItem at the grant path and prove its exact UTF-8 bytes yield the grant Git blob SHA using canonical Git blob hashing:

```text
SHA1("blob <byte-length>\0" + exact UTF-8 bytes)
```

Mismatch fails before dispatch enablement, consume, or gateway call.

## Exact Token / Budget Gate

Require:

```text
context_build.token_count_is_exact == true
model_request.max_input_tokens != None
model_request.max_output_tokens != None
context_build.max_context_tokens == model_request.max_input_tokens
counted_tokens + protocol_reserve_tokens <= max_context_tokens
model_request.max_input_tokens <= grant.max_input_tokens
model_request.max_output_tokens <= grant.max_output_tokens
```

Use `validate_paid_api_grant_budget()` for the Human grant envelope.

A conservative `Utf8ByteConservativeCounter` result must be rejected even if numerically below the grant.

## M10 Selection Rule

After all preconditions pass, build a new immutable `BrainDispatchRequest` with only:

```text
allow_paid_api: true
```

changed from the base request, then call existing `dispatch_brain()`.

If M10 selects a runnable SUBSCRIPTION Brain, TASK-053 must:

```text
NOT consume grant
NOT call gateway
return dispatch evidence
```

If M10 selects paid Brain, it must be exactly `grant.brain_id`.

## One-Shot Call Rule

Paid selection path:

```text
dispatch selected granted paid brain
↓
AtomicPaidApiGrantStore.consume(grant) succeeds
↓
await ModelGateway.invoke(model_request, context_build=context_build) exactly once
```

Never gateway-before-consume.

After consume succeeds, any provider/gateway/ledger failure leaves grant CONSUMED terminal.

Never restore ACTIVE.

## Concurrency / Replay

Two callers racing the same grant must produce at most:

```text
1 successful consume
1 gateway invocation
```

The loser must fail at consume before gateway.

Second sequential replay must also fail before gateway.

## Explicit Out of Scope

```text
REAL_PAID_API_CALL: NO
MINIMAX_CREDENTIAL_READ: NO
BRIDGE_PAID_CALL_COMMAND: NO
BRAIN_RUNTIME_CAPACITY_DISCOVERY_REDESIGN: NO
M10_CONTRACT_CHANGE: NO
M10_RANKING_CHANGE: NO
M11_1_CHANGE: NO
M11_2A_CHANGE: NO
M11_2B_CHANGE: NO
MODEL_GATEWAY_CHANGE: NO
PROVIDER_ADAPTER_CHANGE: NO
EXECUTOR_PAID_API: NO
AUTO_PATCH_APPLICATION: NO
M11_3: NOT_IN_SCOPE
H1_H5: DEFERRED
```

## Required Tests / Acceptance

Mechanically prove at minimum all blueprint cases, including:

```text
ONE_GRANTED_PAID_CANDIDATE_ONLY: PASS
ACTIVE_EXACT_GRANT_REQUIRED: PASS
OPERATION_MAPPING_EXACT: PASS
UNSUPPORTED_CONTINUITY_OPERATIONS_FAIL_CLOSED: PASS
TASK_PROVIDER_MODEL_WORKSPACE_BINDING: PASS
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
CONCURRENT_SINGLE_GATEWAY_WINNER: PASS
NO_RETRY: PASS
NO_SECOND_PROVIDER: PASS
NO_EXECUTOR_AUTHORITY: PASS
NO_GIT_WORKTREE_MUTATION: PASS
NO_REAL_NETWORK: PASS
TARGETED_TESTS: PASS
FULL_REPO_TESTS: PASS
REGRESSIONS: 0
FINAL_INDEPENDENT_AUDIT: PASS
```

## Targeted Test Command

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_bridge/test_paid_api_brain_escape.py -q
```

Executor runs targeted tests only. Bridge publication owns the full repository suite.

## Completion Boundary

After Bridge publication:

```text
STOP
NEXT: Review TASK-053
```

Do not start M11.3 and do not perform a real paid API call automatically.