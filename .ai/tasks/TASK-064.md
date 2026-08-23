# TASK-064 — M11.3D Paid Brain Completion Envelope & Post-Consume Diagnostics Hardening

STATUS: READY
CLASS: L3 — SECURITY-CRITICAL PAID-API RUNTIME HARDENING
MILESTONE: M11.3D
EXECUTOR_MODE: UNIFIED_AIOS_WORKER_DUAL_EXECUTOR
RECOMMENDED_EXECUTOR: codex

## Baseline

```text
MAIN_SHA: 67aa98132ca0413fda320929375887b8efed1fa6
TARGET_BRANCH: ai/task-064
```

TASK-063 is PASS + merged. The second post-merge real operational attempt is now closed forensic evidence and its consumed grant MUST NEVER be reused, retried, reactivated, or mutated.

## Purpose

Harden the exact M11.3 real paid-Brain proof path against the new production behavior discovered after TASK-063:

```text
M11.3C timeout envelope: PROVEN
120-second live timeout wiring: PROVEN
live response latency: 15287 ms
exact full provider input: 3155 local == 3155 provider
live max output: 2000
provider output: 2000
normalized status: INVALID_RESPONSE
error: TRUNCATED_OUTPUT
successful R9 proof: NO
```

TASK-064 MUST:

1. lock one explicit conservative completion envelope for the M11.3 live-proof path without introducing a second output-budget authority; and
2. replace the overly coarse post-consume response failure with a bounded secret-safe diagnostic classification while preserving fail-closed R9 semantics.

TASK-064 RUN/FIX is strictly no-spend. It MUST NOT make a real provider call, use a real API credential value, create/consume a real paid grant, or mutate any prior live forensic evidence.

## Authoritative Contracts

```text
ADR_036_PATH: .ai/decisions/ADR-036-M11-EXTERNAL-API-ESCAPE-HATCH-ARCHITECTURE-LOCK.md
ADR_036_BLOB_SHA: cf71c571d8e3fd611ea07d21f15ad0bf90ef6ecc
FORENSIC_PATH: .ai/context/TASK-064-M11.3D-LIVE-ATTEMPT-2-FORENSIC.md
FORENSIC_BLOB_SHA: 78291ca0eddc41cf1958fb947ef35b9a9220cf75
BLUEPRINT_PATH: .ai/context/TASK-064-M11.3D-COMPLETION-DIAGNOSTICS-BLUEPRINT.md
BLUEPRINT_BLOB_SHA: ae49e6c898c1bd1bc61a267d444989392d711dbc
PROOF_LOCK_PATH: .ai/context/TASK-062-PROOF-LOCK.json
PROOF_LOCK_BLOB_SHA: 9ff47f47c987f7e626f73b26ea9c783a59f6fd45
```

## Machine-Readable Executor Context

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/decisions/ADR-036-M11-EXTERNAL-API-ESCAPE-HATCH-ARCHITECTURE-LOCK.md","blob_sha":"cf71c571d8e3fd611ea07d21f15ad0bf90ef6ecc"},{"path":".ai/context/TASK-064-M11.3D-LIVE-ATTEMPT-2-FORENSIC.md","blob_sha":"78291ca0eddc41cf1958fb947ef35b9a9220cf75"},{"path":".ai/context/TASK-064-M11.3D-COMPLETION-DIAGNOSTICS-BLUEPRINT.md","blob_sha":"ae49e6c898c1bd1bc61a267d444989392d711dbc"},{"path":".ai/context/TASK-062-PROOF-LOCK.json","blob_sha":"9ff47f47c987f7e626f73b26ea9c783a59f6fd45"}]

## Exact Writable Scope

EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","src/aios_bridge/paid_api_real_escape.py","tests/test_bridge_paid_api_real_escape.py","tests/aios_bridge/test_paid_api_real_escape.py","tests/aios_bridge/external_brain/test_minimax_provider.py"]

Bridge-generated `.ai/results/RESULT-064.md` is publication output only.

If any other production/test path appears necessary, STOP and publish no implementation rather than broadening scope.

## Executor Dispatch Policy

DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

Human selects exactly one subscription Executor. No silent reroute, paid Executor, automatic executor failover, or second executor.

## Source Anchors — Current Main

```text
bridge.py: 3104796c62b365595c73670b4a4ef740daa26d53
src/aios_bridge/paid_api_real_escape.py: cd7ff36e64b3952b6db25b452b1da76c555b3265
tests/test_bridge_paid_api_real_escape.py: de0ade1b0d7add90b25876ca46ba25b5565af254
tests/aios_bridge/test_paid_api_real_escape.py: 11fa3de7133c6a062a15c0b724c6e9c235d8d309
tests/aios_bridge/external_brain/test_minimax_provider.py: a155f5fe86b3bf53b2ebf39e849f6e6b9aec4e4a
src/aios_bridge/external_brain/providers/minimax.py: f907deeccf5d24ec80d4de58f7769330126f3624  # READ ONLY
src/aios_bridge/external_brain/contracts.py: 325795cf541bacb6ab8b9be4bc9a88d9b9e16349  # READ ONLY
src/aios_bridge/external_brain/gateway.py: 45d6ec94f3916362783f03f1474b6cc651d8d9e5  # READ ONLY
src/aios_bridge/external_brain/usage.py: 20abd5b43b723935c6632b95d22ec8794e20ae7c  # READ ONLY
```

## Locked Implementation Contract A — Exact M11 Live-Proof Completion Envelope

Define one canonical policy authority in `src/aios_bridge/paid_api_real_escape.py` for the M11.3 real-proof completion envelope:

```text
M11_REAL_PROOF_MAX_OUTPUT_TOKENS: 8192
SEMANTICS: exact required value
```

Exact rules:

1. `PaidApiGrant.max_output_tokens` remains the sole Human spend/output authority.
2. Do NOT add `--provider-output-tokens`, `--max-completion-tokens`, or any second CLI override.
3. Generic `PaidApiGrant` schema/ranges and generic `paid-grant-create` semantics MUST NOT change.
4. `paid-proof-preflight` MUST reject an ACTIVE grant whose `max_output_tokens != 8192` before credential value access, provider construction, provider invocation, or grant consumption.
5. `paid-proof-execute` MUST independently reject a grant whose `max_output_tokens != 8192` before credential value access, provider construction, provider invocation, or grant consumption.
6. Direct `execute_paid_api_real_escape(...)` callers MUST also be protected by the exact same canonical policy authority before provider construction/invocation or grant consumption.
7. The accepted value MUST flow unchanged:

```text
PaidApiGrant.max_output_tokens = 8192
-> ModelRequest.max_output_tokens = 8192
-> MiniMaxOpenAIProvider payload.max_completion_tokens = 8192
```

8. `8192` is an AIOS next-live-proof policy envelope only. Do not label it MiniMax-M3's provider maximum or recommended default.

The official current MiniMax OpenAI Chat Completions API supports `MiniMax-M3` on the already proof-locked `/v1/chat/completions` surface and documents a substantially larger provider completion allowance. TASK-064 therefore MUST preserve the existing endpoint/model/proof-lock rather than migrate API surfaces.

## Locked Implementation Contract B — Bounded Post-Consume Response Diagnostics

After one paid candidate has been selected, the grant has been durably consumed, and exactly one Gateway result exists, a non-SUCCESS normalized provider response MUST fail with a bounded diagnostic instead of collapsing only to `OPERATIONAL_PROOF_FAILED_AFTER_CONSUME`.

Required semantic output:

```text
POST_CONSUME_RESPONSE_REJECTED
STATUS=<bounded allowlisted status>
ERROR_CODE=<bounded allowlisted error code or OTHER>
GRANT_CONSUMED=YES
RETRY_COUNT=0
```

The implementation may choose deterministic separators/formatting, but these semantics must be machine-testable and stable.

At minimum preserve the following safe error classifications when exact:

```text
TRUNCATED_OUTPUT
INVALID_ARTIFACT_STRUCTURE
CORRELATION_ERROR
MALFORMED_RESPONSE
EMPTY_CONTENT
TIMEOUT
AUTH_ERROR
RATE_LIMITED
UNAVAILABLE
```

Any unknown, provider-specific, malformed, padded, oversized, or otherwise non-allowlisted `error_code` MUST collapse to `OTHER`; never echo it raw.

The diagnostic MUST NOT contain, directly or indirectly:

```text
response.content
reasoning content / reasoning_content
request prompt/instruction/context
response.error_message
raw provider_request_id
credential/API key/header/cookie
raw provider body
local absolute filesystem path
```

A non-SUCCESS response remains a hard failure. The diagnostic grants no R9 proof authority.

## Locked R9 Semantics — Preserve Exactly

```text
SUCCESS_REQUIRED_FOR_OPERATIONAL_PROOF: YES
TRUNCATED_OUTPUT_ACCEPTED: NO
PARTIAL_PLAN_ACCEPTED: NO
INPUT_TOKEN_EXACT_MATCH_REQUIRED: YES
LEDGER_PERSISTED_REQUIRED: YES
PROVIDER_REQUEST_ID_REQUIRED: YES
CONSUMED_GRANT_PROOF_REQUIRED: YES
PROPOSAL_ON_NON_SUCCESS: FORBIDDEN
PROOF_JSON_ON_NON_SUCCESS: FORBIDDEN
```

Do not weaken or bypass `build_paid_api_operational_proof` for successful proof generation.

## Endpoint / Counter / Thinking Lock — No Change

Preserve exactly:

```text
PROVIDER_ID: minimax
MODEL_ID: MiniMax-M3
ENDPOINT: https://api.minimax.io/v1/chat/completions
PROOF_LOCK: unchanged
PINNED_CHAT_TEMPLATE: unchanged
PINNED_TOKENIZER: unchanged
EXACT_FULL_INPUT_COUNTER: unchanged
THINKING_BEHAVIOR: unchanged
reasoning_split behavior: unchanged
REAL_PROOF_INSTRUCTION: unchanged
PROVIDER_TIMEOUT_CONTRACT: 60..180 unchanged
RECOMMENDED_NEXT_LIVE_TIMEOUT_SECONDS: 120
```

No Responses API migration, native Messages API migration, endpoint swap, model swap, explicit thinking-mode change, tokenizer/template refresh, or proof-lock rewrite is permitted.

## Reasoning-Token Telemetry — Explicitly Deferred

Do NOT add reasoning-token telemetry to TASK-064.

`UsageRecord` has a reasoning-token field, but current `ModelResponse` does not carry that metric. Proper propagation would require a cross-cutting response-contract/schema change across provider, contracts, Gateway, serialization, and compatibility tests.

```text
TASK_064_MODEL_RESPONSE_SCHEMA_CHANGE: FORBIDDEN
TASK_064_REASONING_TOKEN_PLUMBING: FORBIDDEN
POTENTIAL_FOLLOWUP: TASK-065 / M11.3E only if still useful after a successful live proof
```

## Safety Invariants — Preserve Exactly

```text
MAX_CALLS: 1
AUTO_RETRY: 0
SECOND_PAID_PROVIDER: 0
PAID_EXECUTOR: FORBIDDEN
GRANT_REUSE: FORBIDDEN
GRANT_REACTIVATION: FORBIDDEN
CONSUME_BEFORE_CALL: REQUIRED
MODEL_GATEWAY_INVOCATIONS: EXACTLY_ONE
EXECUTOR_AUTHORITY_CREATED: FALSE
BRAIN_OUTPUT_WORKTREE_AUTHORITY: FORBIDDEN
SECRET_VALUE_READ_BEFORE_EXISTING_POST-GATE_FACTORY: FORBIDDEN
PROVIDER_TIMEOUT_RANGE_SECONDS: 60..180
```

Increasing the authorized completion envelope grants no retry, second provider, Executor, tool, filesystem, Git, or worktree authority.

## Mandatory Tests

Use fake/local dependencies and dummy credentials/grants only. Required coverage:

```text
1. Canonical M11 real-proof completion policy is exactly 8192.
2. paid-proof-preflight accepts an otherwise valid ACTIVE grant at exactly 8192.
3. paid-proof-preflight rejects 2000, 8191, 8193, and other non-8192 values without provider construction/call or grant consumption.
4. paid-proof-execute independently rejects a non-8192 grant before credential value access, provider construction/call, or grant consumption.
5. Direct execute_paid_api_real_escape rejects a non-8192 grant before consume/provider work.
6. Accepted 8192 reaches ModelRequest.max_output_tokens unchanged.
7. Existing MiniMax provider payload path sends max_completion_tokens=8192 unchanged using a fake transport; no provider production rewrite.
8. Normalized INVALID_RESPONSE/TRUNCATED_OUTPUT after consume produces the bounded post-consume diagnostic, leaves the grant CONSUMED, performs exactly one provider call, and performs zero retry/failover.
9. Non-success diagnostic never includes response content, error_message, raw provider_request_id, prompt/context, credential material, or absolute path.
10. Unknown/provider-specific error code collapses to OTHER and is never echoed raw.
11. TIMEOUT and at least one other allowlisted normalized failure produce bounded safe classifications after consume and zero retry.
12. Non-SUCCESS response publishes neither proposal.md nor proof.json.
13. Existing SUCCESS path still builds the exact R9 operational proof and durable proposal/proof artifacts.
14. Exact local/provider input-token correlation requirements remain unchanged.
15. TASK-063 timeout validation 60/120/180 and no-default/no-retry semantics remain green.
16. No test reaches external network or uses a real credential/grant.
```

Run targeted Bridge/real-escape/MiniMax-provider tests and the full repository suite.

## Locked No-Spend Boundary

```text
REAL_PAID_API_CALL_DURING_TASK: FORBIDDEN
REAL_MINIMAX_NETWORK_DURING_TASK: FORBIDDEN
REAL_API_KEY_VALUE_USE_DURING_TASK: FORBIDDEN
REAL_GRANT_CREATION_DURING_TASK: FORBIDDEN
REAL_GRANT_CONSUME_DURING_TASK: FORBIDDEN
ATTEMPT_1_GRANT_REUSE: FORBIDDEN
ATTEMPT_2_GRANT_REUSE: FORBIDDEN
AUTO_RUN_POST_MERGE_PROOF: FORBIDDEN
```

## Out of Scope

```text
retry/failover policy changes
second paid provider
MiniMax provider production redesign
ModelResponse schema changes
reasoning-token telemetry plumbing
ModelGateway redesign
M10 dispatch redesign
generic grant schema/range changes
proof-lock/tokenizer/chat-template changes
endpoint/API-surface migration
thinking-mode change
REAL_PROOF_INSTRUCTION change
proof receipt schema changes
capacity semantics
Executor lifecycle/lease changes
H1-H5 activation
Lean Merge Gate refinement
```

## Acceptance Criteria

TASK-064 may be published READY_FOR_REVIEW only if:

```text
M11_REAL_PROOF_MAX_OUTPUT_TOKENS: 8192
SINGLE_OUTPUT_BUDGET_AUTHORITY_PRESERVED: YES
NON_8192_REAL_PROOF_GRANT_FAILS_PRE_SPEND: YES
8192_FLOWS_TO_MODEL_REQUEST_UNCHANGED: YES
8192_FLOWS_TO_MINIMAX_MAX_COMPLETION_TOKENS_UNCHANGED: YES
POST_CONSUME_SAFE_DIAGNOSTIC: YES
UNKNOWN_ERROR_CODE_COLLAPSES_TO_OTHER: YES
DIAGNOSTIC_SECRET_SAFE: YES
TRUNCATED_OUTPUT_REMAINS_FAILURE: YES
R9_SUCCESS_REQUIREMENTS_UNCHANGED: YES
PROPOSAL_ON_NON_SUCCESS: NO
PROOF_JSON_ON_NON_SUCCESS: NO
CONSUME_BEFORE_CALL_PRESERVED: YES
MAX_CALLS_ONE_PRESERVED: YES
AUTO_RETRY_ZERO_PRESERVED: YES
SECOND_PAID_PROVIDER_ZERO_PRESERVED: YES
TIMEOUT_CONTRACT_60_180_PRESERVED: YES
EXACT_INPUT_COUNTER_CONTRACT_PRESERVED: YES
MODEL_RESPONSE_SCHEMA_CHANGED: NO
PROOF_LOCK_CHANGED: NO
TARGETED_TESTS_PASS: YES
FULL_REPO_TESTS_PASS: YES
SCOPE_EXACT: YES
REAL_PAID_API_CALL_DURING_TASK: NO
REAL_API_KEY_VALUE_USE_DURING_TASK: NO
REAL_GRANT_CONSUME_DURING_TASK: NO
```

TASK-064 PASS + merge does NOT authorize another live MiniMax call.

After merge, ChatGPT may prepare a fresh no-spend preflight using fresh capacity evidence and a fresh Human one-shot grant with `max_output_tokens=8192`. The next live call requires separate explicit Human authorization and should retain `--provider-timeout-seconds 120` unless a new reviewed task changes that contract.
