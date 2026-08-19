# TASK-051 — M11.2A Atomic Runtime Paid API Grant Store — Reissue

STATUS: READY
CLASS: L3 — SECURITY-CRITICAL RUNTIME STATE / PAID-API BRAIN GRANT
MILESTONE: M11.2A
EXECUTOR_MODE: UNIFIED_AIOS_WORKER_DUAL_EXECUTOR

## Baseline

```text
MAIN_SHA: 883057183adbb234bbc98b04f0055935aed9b091
TARGET_BRANCH: ai/task-051
```

## Reissue Authority

TASK-050 is closed as an aborted/no-publication attempt after E4 observed zero worktree delta and Human recovery cancelled the authorization/released its lease.

```text
TASK_050_RETRY: FORBIDDEN
TASK_050_REACTIVATION: FORBIDDEN
TASK_050_PUBLISHED_SHA: NONE
TASK_051: SOLE ACTIVE AUTHORITY FOR M11.2A IMPLEMENTATION
```

Do not resume, retry, fix, publish, or merge TASK-050.

## Authoritative Contracts

```text
ADR_036_PATH: .ai/decisions/ADR-036-M11-EXTERNAL-API-ESCAPE-HATCH-ARCHITECTURE-LOCK.md
ADR_036_BLOB_SHA: cf71c571d8e3fd611ea07d21f15ad0bf90ef6ecc
ADR_038_PATH: .ai/decisions/ADR-038-DEFAULT-DUAL-EXECUTOR-TASK-AUTHORING-POLICY-LOCK.md
ADR_038_BLOB_SHA: 72d38bf2f2ff5a07e7b63322116ad87622349df1
BLUEPRINT_PATH: .ai/context/TASK-051-M11.2A-RUNTIME-PAID-API-GRANT-STORE-REISSUE-BLUEPRINT.md
BLUEPRINT_BLOB_SHA: 3b4fc2a9377664ea24480f38ded892739dd07f06
M11_1_SOURCE_PATH: src/aios_bridge/paid_api_grant.py
M11_1_SOURCE_BLOB_SHA: 7f1e1fe666154a9b17013a2cb084db9ce36f134f
RUNTIME_LEASE_REFERENCE_PATH: src/aios_bridge/runtime_lease.py
RUNTIME_LEASE_REFERENCE_BLOB_SHA: d0fabf3a19ad30ded8438116ad7fdaf9f21656b5
```

## Objective

Implement the external-runtime durable ACTIVE/CONSUMED store for the immutable one-shot Human paid-API Brain grant from M11.1.

TASK-051 is storage/state-transition only:

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

## Child Executor Role

When Bridge E4 launches the Codex child process, that child is the implementation Executor.

It MUST implement TASK-051 now. It is NOT the visible `aios-worker` operator session and MUST NOT stop merely because `.agents/skills/aios-worker/SKILL.md` says the visible session is operator-only.

## Machine-Readable Executor Context

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/decisions/ADR-036-M11-EXTERNAL-API-ESCAPE-HATCH-ARCHITECTURE-LOCK.md","blob_sha":"cf71c571d8e3fd611ea07d21f15ad0bf90ef6ecc"},{"path":".ai/decisions/ADR-038-DEFAULT-DUAL-EXECUTOR-TASK-AUTHORING-POLICY-LOCK.md","blob_sha":"72d38bf2f2ff5a07e7b63322116ad87622349df1"},{"path":".ai/context/TASK-051-M11.2A-RUNTIME-PAID-API-GRANT-STORE-REISSUE-BLUEPRINT.md","blob_sha":"3b4fc2a9377664ea24480f38ded892739dd07f06"}]

## Machine-Readable Executor Worktree Scope

EXECUTOR_ALLOWED_PATHS_JSON: ["src/aios_bridge/runtime_paid_api_grant.py","tests/aios_bridge/test_runtime_paid_api_grant.py"]

Bridge-generated `.ai/results/RESULT-051.md` is publication output, not Executor-writable implementation scope.

## Exact Read-Only Source Scope

Executor MAY read exactly these two repository source files as bounded dependencies:

```text
src/aios_bridge/paid_api_grant.py
src/aios_bridge/runtime_lease.py
```

They MUST NOT be modified.

No broad repository inspection is authorized beyond:
- Bridge-delivered TASK/context artifacts;
- those two exact read-only dependencies;
- the two exact writable files.

## Executor Dispatch Policy

DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

The implementation task itself uses subscription Executor capacity only. `allow_paid_api:false` here is Executor-routing policy and is unrelated to the paid-API Brain grant store being implemented.

Both listed subscription Executors are eligible. Human selects exactly one. No silent reroute, fallback, second executor, or paid-API executor.

## Human RUN Choice

Choose exactly one:

```text
Antigravity:
/aios-worker RUN TASK-051

Codex:
$aios-worker RUN TASK-051
```

## Required Implementation

Create exactly:

```text
src/aios_bridge/runtime_paid_api_grant.py
tests/aios_bridge/test_runtime_paid_api_grant.py
```

Implement exactly the locked blueprint.

Required API:

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

Exact expiry:

```text
usable iff now_epoch_seconds < expires_at_epoch_seconds
```

At equality, reject.

Security boundary:

```text
ACTIVE
  ↓ later exact pre-call validation
CONSUMED DURABLY
  ↓ only then may later provider invocation begin
```

A crash after consume does not restore authorization.

## Thin Executor Rules

Executor MUST:
- implement the locked TASK/blueprint rather than redesign M11;
- use the exact bounded read/write scope above;
- preserve M11.1 contract unchanged;
- run only the targeted TASK-051 tests;
- leave implementation files uncommitted for Bridge publication;
- stop normally after implementation/testing.

Executor MUST NOT:
- invoke `aios-worker` recursively;
- reinterpret itself as the operator UI;
- modify Bridge/operator/dispatch/External Brain code;
- run full repository suite;
- read provider credentials;
- invoke network/provider/ModelGateway;
- set `allow_paid_api=true`;
- implement M11.2B/M11.2C/M11.3;
- retry/reroute to another executor;
- commit, push, publish RESULT, or merge.

## Targeted Test Command

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_bridge/test_runtime_paid_api_grant.py -q
```

Bridge publication owns repository-wide tests.

## Forbidden Write Scope

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
.agents/**
tests/test_bridge*.py
.ai/tasks/**
.ai/reviews/**
.ai/decisions/**
.ai/context/**
.ai/proofs/**
```

except Bridge-generated `.ai/results/RESULT-051.md` during publication.

Do not add paid-API Executor support, credentials, provider support, retries, fallback, automatic merge, H1-H5, or real paid calls.

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
NEXT: Review TASK-051 in ChatGPT
```

Do not begin M11.2B automatically.
