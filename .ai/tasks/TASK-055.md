# TASK-055 — M11.2C.1 Full Provider Input Budget Proof Hardening

STATUS: READY
CLASS: L3 — SECURITY-CRITICAL PAID-API INPUT-BUDGET AUTHORIZATION HARDENING
MILESTONE: M11.2C.1
EXECUTOR_MODE: UNIFIED_AIOS_WORKER_DUAL_EXECUTOR

## Baseline

```text
MAIN_SHA: 439f073da2a112531dc78669dfb4aea53f88439b
TARGET_BRANCH: ai/task-055
```

## Purpose

Close the pre-M11.3 budget-proof gap where exact `ContextBuildResult` evidence covers selected ContextItems but not the full provider input added by External Brain prompt rendering.

After TASK-055, paid dispatch must be impossible unless a separate exact full-provider-input counter proves the complete ModelRequest input is within both the ModelRequest ceiling and the Human grant.

No real paid API call is authorized.

## Authoritative Contracts

```text
ADR_036_PATH: .ai/decisions/ADR-036-M11-EXTERNAL-API-ESCAPE-HATCH-ARCHITECTURE-LOCK.md
ADR_036_BLOB_SHA: cf71c571d8e3fd611ea07d21f15ad0bf90ef6ecc
BLUEPRINT_PATH: .ai/context/TASK-055-M11.2C1-FULL-PROVIDER-INPUT-BUDGET-PROOF-HARDENING-BLUEPRINT.md
BLUEPRINT_BLOB_SHA: ee17d57a47c2a315877dae91ff448733e29347d8
REVIEW_054_PATH: .ai/reviews/REVIEW-054.md
REVIEW_054_BLOB_SHA: 8ee2e8550012c63ca1441dbc2b65d4c02aa87bd3
```

Merged source anchors:

```text
src/aios_bridge/paid_api_brain_escape.py                  bb4694201ac3ead22e43ecadc0bf78c8ff788e5c
src/aios_bridge/external_brain/context.py                 b0cbaa7ee6f59fe25f7242c7f28ce5d08e61a774
src/aios_bridge/external_brain/prompt.py                  5e43eec724c8efebc47a2f1dc741e5cf8b616601
src/aios_bridge/external_brain/providers/minimax.py       f907deeccf5d24ec80d4de58f7769330126f3624
```

## Machine-Readable Executor Context

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/decisions/ADR-036-M11-EXTERNAL-API-ESCAPE-HATCH-ARCHITECTURE-LOCK.md","blob_sha":"cf71c571d8e3fd611ea07d21f15ad0bf90ef6ecc"},{"path":".ai/context/TASK-055-M11.2C1-FULL-PROVIDER-INPUT-BUDGET-PROOF-HARDENING-BLUEPRINT.md","blob_sha":"ee17d57a47c2a315877dae91ff448733e29347d8"},{"path":".ai/reviews/REVIEW-054.md","blob_sha":"8ee2e8550012c63ca1441dbc2b65d4c02aa87bd3"}]

## Machine-Readable Executor Worktree Scope

EXECUTOR_ALLOWED_PATHS_JSON: ["src/aios_bridge/provider_input_budget.py","src/aios_bridge/paid_api_brain_escape.py","tests/aios_bridge/test_paid_api_brain_escape.py"]

Bridge-generated `.ai/results/RESULT-055.md` is publication output only.

## Executor Dispatch Policy

DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

Human selects exactly one subscription Executor. No silent reroute, no paid Executor.

## Child Executor Role Lock

The Bridge E4-spawned Codex process is the bounded implementation Executor child, NOT the visible `aios-worker` operator UI.

```text
visible Codex + aios-worker skill = operator UI
Bridge E4 spawned Codex process  = bounded implementation Executor
```

The child MUST implement this task now. It MUST NOT invoke the worker adapter again and MUST NOT commit, push, publish, or merge.

## Exact Writable Files

```text
src/aios_bridge/provider_input_budget.py
src/aios_bridge/paid_api_brain_escape.py
tests/aios_bridge/test_paid_api_brain_escape.py
```

No other implementation file may change.

## Bounded Read-Only Scope

```text
src/aios_bridge/paid_api_brain_escape.py
src/aios_bridge/paid_api_grant.py
src/aios_bridge/runtime_paid_api_grant.py
src/aios_bridge/continuity/dispatch.py
src/aios_bridge/external_brain/contracts.py
src/aios_bridge/external_brain/context.py
src/aios_bridge/external_brain/prompt.py
src/aios_bridge/external_brain/gateway.py
src/aios_bridge/external_brain/providers/minimax.py
```

## Required Implementation

Follow the blueprint exactly.

Create an immutable full-provider-input evidence contract and counter protocol in `provider_input_budget.py`, including canonical SHA-256 fingerprinting of exact `ModelRequest.to_dict()` semantics.

Harden `execute_paid_api_brain_escape(...)` with a required `provider_input_counter` argument.

Before constructing any effective request with `allow_paid_api=True`, require:

```text
COUNTER_PROVIDER == grant.provider_id
COUNTER_MODEL == grant.model_id
COUNTER_IS_EXACT == TRUE
COUNT_REQUEST_CALLS == 1
EVIDENCE_PROVIDER == grant.provider_id
EVIDENCE_MODEL == grant.model_id
EVIDENCE_COUNTER_ID == counter.counter_id
EVIDENCE_IS_EXACT == TRUE
EVIDENCE_REQUEST_FINGERPRINT == canonical fingerprint(model_request)
EVIDENCE_COUNTED_INPUT_TOKENS <= model_request.max_input_tokens
model_request.max_input_tokens <= grant.max_input_tokens
model_request.max_output_tokens <= grant.max_output_tokens
```

All existing ContextBuildResult validation remains required. Context-only exact evidence must no longer be sufficient by itself.

## Safety Ordering

```text
all existing grant/context/artifact/provider checks
↓
full-provider-input counter proof
↓
Human grant budget proof
↓
ONLY THEN allow_paid_api=True
↓
M10 dispatch
↓
paid selected → durable consume → one gateway call
```

Every full-input proof failure must occur before paid enablement, grant consume, and gateway invocation.

## Counter Restrictions for TASK-055

The counter seam in this task is local/pure only.

Forbidden:

```text
HTTP/network token-count endpoint
API key read
provider credential read
tokenizer download
real MiniMax tokenizer implementation
real provider initialization
real provider call
```

Tests use deterministic offline fake counters.

## Preserve Existing Invariants

```text
EXACT_ONE_PAID_BRAIN: PASS
ACTIVE_GRANT_REQUIRED: PASS
ARTIFACT_CONTENT_BLOB_PROOF: PASS
EXACT_CONTEXT_COUNTER: PASS
SUBSCRIPTION_PREFERENCE: PASS
CONSUME_BEFORE_GATEWAY: PASS
ONE_GATEWAY_CALL_MAX: PASS
REPLAY_CLOSED: PASS
NO_RETRY: PASS
NO_SECOND_PROVIDER: PASS
NO_EXECUTOR_AUTHORITY: PASS
```

## Required Acceptance Tests

At minimum mechanically prove:

```text
COUNTER_REQUIRED
COUNTER_PROVIDER_MISMATCH_REJECTED
COUNTER_MODEL_MISMATCH_REJECTED
COUNTER_NOT_EXACT_REJECTED
COUNTER_CALLED_EXACTLY_ONCE
EVIDENCE_EXACT_TYPE_REQUIRED
EVIDENCE_PROVIDER_MODEL_COUNTER_BINDING
EVIDENCE_EXACT_FLAG_REQUIRED
MODEL_REQUEST_FINGERPRINT_DETERMINISTIC
MODEL_REQUEST_FINGERPRINT_MUTATION_SENSITIVE
EVIDENCE_REQUEST_FINGERPRINT_MISMATCH_REJECTED
FULL_INPUT_COUNT_OVER_REQUEST_LIMIT_REJECTED
FULL_INPUT_COUNT_AT_REQUEST_LIMIT_ACCEPTED
FULL_INPUT_COUNT_WITHIN_HUMAN_GRANT_ACCEPTED
CONTEXT_ONLY_EXACT_NOT_SUFFICIENT
FAILURE_BEFORE_ALLOW_PAID_ENABLEMENT
FAILURE_BEFORE_CONSUME
FAILURE_BEFORE_GATEWAY
SUBSCRIPTION_STILL_PREFERRED
PAID_WIN_CONSUME_BEFORE_GATEWAY
REPLAY_STILL_CLOSED
NO_NETWORK_COUNTER_SURFACE
NO_REAL_PROVIDER_CALL
TARGETED_TESTS_PASS
FULL_REPO_TESTS_PASS
REGRESSIONS: 0
```

## Targeted Test

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_bridge/test_paid_api_brain_escape.py -q
```

Executor runs targeted tests. Bridge publication owns full repo tests.

## Out of Scope

```text
REAL_PAID_API_CALL: NO
MINIMAX_M3_TOKENIZER_COUNTER: NEXT SUBTASK, NOT THIS TASK
M11.3_REAL_PROOF: NOT_STARTED
CONTEXT_BUILDER_CHANGE: NO
PROMPT_RENDERER_CHANGE: NO
MINIMAX_PROVIDER_CHANGE: NO
MODEL_GATEWAY_CHANGE: NO
M10_CHANGE: NO
M11.1_CHANGE: NO
M11.2A_CHANGE: NO
M11.2B_CHANGE: NO
H_SERIES: DEFERRED
```

## Human RUN Choice

Choose exactly one:

```text
Antigravity:
/aios-worker RUN TASK-055

Codex:
$aios-worker RUN TASK-055
```

## Completion Boundary

After Bridge publication:

```text
STOP
NEXT: Review TASK-055
```

Do not begin the MiniMax tokenizer implementation or M11.3 real proof automatically.