# TASK-050 — M11.2A Atomic Runtime Paid API Grant Store

STATUS: READY
CLASS: L3 — SECURITY-CRITICAL RUNTIME STATE / PAID-API BRAIN GRANT
MILESTONE: M11.2A
EXECUTOR_MODE: UNIFIED_AIOS_WORKER_DUAL_EXECUTOR

## Baseline

```text
MAIN_SHA: 883057183adbb234bbc98b04f0055935aed9b091
TARGET_BRANCH: ai/task-050
```

## Authoritative Contracts

```text
ADR_036_PATH: .ai/decisions/ADR-036-M11-EXTERNAL-API-ESCAPE-HATCH-ARCHITECTURE-LOCK.md
ADR_036_BLOB_SHA: cf71c571d8e3fd611ea07d21f15ad0bf90ef6ecc
ADR_038_PATH: .ai/decisions/ADR-038-DEFAULT-DUAL-EXECUTOR-TASK-AUTHORING-POLICY-LOCK.md
ADR_038_BLOB_SHA: 72d38bf2f2ff5a07e7b63322116ad87622349df1
BLUEPRINT_PATH: .ai/context/TASK-050-M11.2A-RUNTIME-PAID-API-GRANT-STORE-BLUEPRINT.md
BLUEPRINT_BLOB_SHA: 8b7f0f87d42d0c2394636f52c2c72bf7c4bd7548
M11_1_CONTRACT_PATH: src/aios_bridge/paid_api_grant.py
M11_1_CONTRACT_BLOB_SHA: 7f1e1fe666154a9b17013a2cb084db9ce36f134f
```

## Objective

Implement the atomic external-runtime ACTIVE/CONSUMED store for the one-shot Human paid-API Brain grant created in M11.1.

TASK-050 is storage/state-transition only:

```text
REAL_PAID_API_CALL: NO
HUMAN_BRIDGE_GRANT_COMMAND: NO
BRAIN_DISPATCH_WIRING: NO
MODEL_GATEWAY_WIRING: NO
PROVIDER_CREDENTIAL_ACCESS: NO
M11.2B: NOT_IN_SCOPE
M11.2C: NOT_IN_SCOPE
M11.3: NOT_IN_SCOPE
```

## M11.2 Sequencing

ADR-036 remains unchanged. M11.2 is implemented in bounded slices:

```text
M11.2A — durable grant state + expiry/replay/consume semantics   ← TASK-050
M11.2B — Human Bridge grant command + exact runtime binding
M11.2C — grant-aware Brain dispatch / pre-call wiring
M11.3  — real operational escape proof
```

The one-shot safety boundary is locked as:

```text
ACTIVE
  ↓ validate exact binding/budget/expiry in later wiring
CONSUMED DURABLY
  ↓ only then may provider invocation begin
```

A crash after consume but before provider invocation loses the authorization and MUST NOT make it reusable. Fail closed over double-spend risk.

## Machine-Readable Executor Context

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/decisions/ADR-036-M11-EXTERNAL-API-ESCAPE-HATCH-ARCHITECTURE-LOCK.md","blob_sha":"cf71c571d8e3fd611ea07d21f15ad0bf90ef6ecc"},{"path":".ai/decisions/ADR-038-DEFAULT-DUAL-EXECUTOR-TASK-AUTHORING-POLICY-LOCK.md","blob_sha":"72d38bf2f2ff5a07e7b63322116ad87622349df1"},{"path":".ai/context/TASK-050-M11.2A-RUNTIME-PAID-API-GRANT-STORE-BLUEPRINT.md","blob_sha":"8b7f0f87d42d0c2394636f52c2c72bf7c4bd7548"}]

## Machine-Readable Executor Worktree Scope

EXECUTOR_ALLOWED_PATHS_JSON: ["src/aios_bridge/runtime_paid_api_grant.py","tests/aios_bridge/test_runtime_paid_api_grant.py"]

Bridge-generated `.ai/results/RESULT-050.md` is not Executor-writable implementation scope.

## Executor Dispatch Policy

DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

The implementation task itself MUST NOT use paid API capacity. `allow_paid_api:false` here is Executor routing policy and is unrelated to the runtime Brain grant being implemented.

Both listed subscription executors are eligible. Candidate rank is recommendation metadata only. Human selects exactly one executor through the UI used to invoke RUN.

## Human RUN Choice

Choose exactly one:

```text
Antigravity:
/aios-worker RUN TASK-050

Codex:
$aios-worker RUN TASK-050
```

No silent reroute, second executor invocation, fallback, or paid API execution.

## Required Implementation

Create exactly:

```text
src/aios_bridge/runtime_paid_api_grant.py
tests/aios_bridge/test_runtime_paid_api_grant.py
```

Follow the locked blueprint exactly.

The implementation must provide:

```text
AtomicPaidApiGrantStore
load_active(task_id, grant_id)
load_consumed(task_id, grant_id)
activate(grant, now_epoch_seconds=...)
require_active(expected, now_epoch_seconds=...)
consume(expected, now_epoch_seconds=...)
```

Core invariants:

```text
EXTERNAL_RUNTIME_ONLY: YES
EXACT_WORKSPACE_BINDING: YES
EXACT_TASK_AND_GRANT_ID_NAMESPACE: YES
WINDOWS_SAFE_HASHED_GRANT_KEY: YES
ACTIVE_CONSUMED_DUAL_STATE: FAIL_CLOSED
EXPIRED_AT_NOW: FAIL_CLOSED
CONSUMED_REPLAY: FAIL_CLOSED
ATOMIC_ACTIVATE: REQUIRED
ATOMIC_CONSUME: REQUIRED
CROSS_THREAD_PROCESS_GUARD: REQUIRED
MAX_SERIALIZED_BYTES: ENFORCED
PROVIDER_CALL_INSIDE_STORE: FORBIDDEN
ENV_CREDENTIAL_READ: FORBIDDEN
```

Expiry is exact:

```text
usable iff now_epoch_seconds < expires_at_epoch_seconds
```

At equality, reject.

## Thin Executor Rules

Executor MUST:
- use only bounded context delivered by AIOS Bridge plus the two allowed implementation paths;
- implement the blueprint, not redesign M11;
- run only the targeted TASK-050 tests;
- preserve M11.1 `PaidApiGrant` unchanged;
- stop normally at Bridge publication boundary.

Executor MUST NOT:
- broadly inspect unrelated repository files;
- modify `bridge.py`, M10 dispatch, External Brain, lease code, continuity contracts, or M11.1 contract;
- run the full repository suite itself when Bridge publication owns it;
- read provider credentials;
- invoke ModelGateway/provider/network;
- implement Bridge grant commands;
- set `allow_paid_api=true`;
- implement M11.2B/M11.2C/M11.3;
- retry or reroute to another executor;
- merge.

## Targeted Test Command

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_bridge/test_runtime_paid_api_grant.py -q
```

Bridge publication owns the repository-wide suite.

## Forbidden Scope

Do not modify:

```text
bridge.py
src/aios_bridge/paid_api_grant.py
src/aios_bridge/runtime_dispatch.py
src/aios_bridge/runtime_lease.py
src/aios_bridge/continuity/**
src/aios_bridge/external_brain/**
src/aios_bridge/executor_automation.py
src/aios_bridge/executor_context.py
src/aios_bridge/executor_transports/**
tests/test_bridge*.py
.ai/tasks/**
.ai/reviews/**
.ai/decisions/**
.ai/context/**
.ai/proofs/**
```

except Bridge-generated `.ai/results/RESULT-050.md` during publication.

Do not add:

```text
provider credentials
real paid API call
paid API Executor support
Bridge grant CLI
Brain dispatch changes
ModelGateway changes
retry/fallback/automatic merge
H1-H5 implementation
```

## Acceptance

```text
ATOMIC_RUNTIME_GRANT_STORE: PASS
EXTERNAL_RUNTIME_ONLY: PASS
WINDOWS_SAFE_GRANT_NAMESPACE: PASS
EXACT_WORKSPACE_BINDING: PASS
STRICT_ACTIVE_LOAD: PASS
STRICT_CONSUMED_LOAD: PASS
EXACT_EXPIRY_BOUNDARY: PASS
ACTIVE_CONSUMED_CORRUPTION_FAIL_CLOSED: PASS
DUPLICATE_ACTIVATION_REJECTED: PASS
CONSUMED_REPLAY_REJECTED: PASS
EXACT_REQUIRE_ACTIVE: PASS
ATOMIC_ACTIVE_TO_CONSUMED: PASS
SECOND_CONSUME_REJECTED: PASS
POST_CONSUME_REQUIRE_ACTIVE_REJECTED: PASS
CONCURRENT_ACTIVATE_SINGLE_WINNER: PASS
CONCURRENT_CONSUME_SINGLE_WINNER: PASS
NO_PREEXISTING_STATE_DELETION: PASS
NO_ACTIVE_RECREATION_AFTER_CONSUME: PASS
MAX_SERIALIZED_BYTES_BOUND: PASS
NO_ENV_NETWORK_SUBPROCESS_PROVIDER_GATEWAY_DISPATCH: PASS
TARGETED_TESTS: PASS
FULL_REPO_TESTS: PASS
REGRESSIONS: 0
FINAL_INDEPENDENT_AUDIT: PASS
```

Only Human authorizes RUN/FIX/MERGE and executor choice. ChatGPT remains independent review/merge gate.

## Completion Boundary

After successful Bridge publication:

```text
STOP
NEXT: Review TASK-050 in ChatGPT
```

Do not begin M11.2B automatically.
