# TASK-052 — M11.2B Human Paid API Grant Command + Exact Runtime Binding

STATUS: READY
CLASS: L3 — SECURITY-CRITICAL HUMAN SPEND AUTHORIZATION / RUNTIME CONTROL
MILESTONE: M11.2B
EXECUTOR_MODE: UNIFIED_AIOS_WORKER_DUAL_EXECUTOR

## Baseline

```text
MAIN_SHA: 15a26f7a2810a5540bed0a3f7ad8f662b04533d4
TARGET_BRANCH: ai/task-052
```

## Authoritative Contracts

```text
ADR_036_PATH: .ai/decisions/ADR-036-M11-EXTERNAL-API-ESCAPE-HATCH-ARCHITECTURE-LOCK.md
ADR_036_BLOB_SHA: cf71c571d8e3fd611ea07d21f15ad0bf90ef6ecc
ADR_038_PATH: .ai/decisions/ADR-038-DEFAULT-DUAL-EXECUTOR-TASK-AUTHORING-POLICY-LOCK.md
ADR_038_BLOB_SHA: 72d38bf2f2ff5a07e7b63322116ad87622349df1
BLUEPRINT_PATH: .ai/context/TASK-052-M11.2B-HUMAN-PAID-API-GRANT-COMMAND-BLUEPRINT.md
BLUEPRINT_BLOB_SHA: c50d2acb153356c3e35609101302bf2cf650b735
REVIEW_051_PATH: .ai/reviews/REVIEW-051.md
REVIEW_051_BLOB_SHA: a441e954f9fa84b33d5f0d763f498702e899ae70
M11_1_PATH: src/aios_bridge/paid_api_grant.py
M11_1_BLOB_SHA: 7f1e1fe666154a9b17013a2cb084db9ce36f134f
M11_2A_PATH: src/aios_bridge/runtime_paid_api_grant.py
M11_2A_BLOB_SHA: a3c7a446ff0f8195e68640493900776334a9e551
```

## Objective

Implement the explicit Human Bridge command that creates a fresh bounded paid-API BRAIN grant and activates it in the external runtime M11.2A store.

Also add one read-only diagnostic command for exact grant status.

TASK-052 ends after grant creation/status plumbing. It MUST NOT enable paid dispatch or call a provider.

## Machine-Readable Executor Context

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/decisions/ADR-036-M11-EXTERNAL-API-ESCAPE-HATCH-ARCHITECTURE-LOCK.md","blob_sha":"cf71c571d8e3fd611ea07d21f15ad0bf90ef6ecc"},{"path":".ai/decisions/ADR-038-DEFAULT-DUAL-EXECUTOR-TASK-AUTHORING-POLICY-LOCK.md","blob_sha":"72d38bf2f2ff5a07e7b63322116ad87622349df1"},{"path":".ai/context/TASK-052-M11.2B-HUMAN-PAID-API-GRANT-COMMAND-BLUEPRINT.md","blob_sha":"c50d2acb153356c3e35609101302bf2cf650b735"},{"path":".ai/reviews/REVIEW-051.md","blob_sha":"a441e954f9fa84b33d5f0d763f498702e899ae70"}]

## Machine-Readable Executor Worktree Scope

EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","tests/test_bridge_paid_api_grant.py"]

Bridge-generated `.ai/results/RESULT-052.md` is publication output, not Executor implementation scope.

## Bounded Read-Only Source Scope

Executor MAY read exactly:

```text
bridge.py
src/aios_bridge/paid_api_grant.py
src/aios_bridge/runtime_paid_api_grant.py
src/aios_bridge/continuity/state.py
tests/test_bridge_dispatch.py
```

Do not broaden repository inspection beyond the Bridge-delivered TASK/context and these exact paths.

## Executor Dispatch Policy

DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

This task itself uses subscription Executor capacity only. The paid API being authorized is a future BRAIN call, never a paid Executor.

Human selects exactly one Executor. No silent reroute, second executor, fallback, or paid Executor.

## Human RUN Choice

Choose exactly one:

```text
Antigravity:
/aios-worker RUN TASK-052

Codex:
$aios-worker RUN TASK-052
```

## Exact Writable Files

Executor may modify/create exactly:

```text
bridge.py
tests/test_bridge_paid_api_grant.py
```

Do not modify M11.1 or M11.2A production contracts.

## Required Bridge Runtime Path

Add external runtime path:

```python
"paid_api_grants": rdir / "paid_api_grants"
```

`ensure_dirs()` must create it.

Add `get_paid_api_grant_store()` bound to exact current `workspace_id`.

No grant state under `.ai/` or Git worktree.

## Required Human Command

Add:

```text
paid-grant-create
```

Required canonical CLI arguments:

```text
paid-grant-create <task_id>
  --brain-id <id>
  --provider-id <id>
  --model-id <id>
  --operation <BrainOperation>
  --artifact-path <canonical .ai path>
  --max-input-tokens <int>
  --max-output-tokens <int>
  --ttl-seconds <int 1..900>
  --confirm-paid-api-spend
```

No defaults for Human spend semantics.

Without `--confirm-paid-api-spend`, fail before any activation.

Forbidden create-command inputs:

```text
--grant-id
--artifact-blob-sha
--workspace-id
--actor-kind
--max-calls
--api-key
--authorization-header
--token
--cookie
```

## Required Grant Construction

On one successful Human invocation, Bridge MUST:

```text
fetch configured ai-control
resolve exact artifact blob from ai-control
bind task_id = TASK-<N>
bind actor_kind = BRAIN
bind exact brain_id/provider_id/model_id
bind exact continuity BrainOperation
bind exact artifact path/blob
bind exact max_input_tokens/max_output_tokens
bind max_calls = 1
bind exact current workspace_id
observe int(time.time()) exactly once
bind expires_at = now + ttl
Bridge-generate one fresh grant_id
construct immutable PaidApiGrant
activate exactly once
require_active exact readback
print safe non-secret receipt
STOP
```

Grant ID format:

```text
grant-task-<zero-padded task>-<lowercase random hex>
```

Use one `secrets.token_hex()` generation. No automatic retry on collision or store failure.

TTL contract:

```text
MIN_PAID_API_GRANT_TTL_SECONDS: 1
MAX_PAID_API_GRANT_TTL_SECONDS: 900
```

No default TTL, no grace, no extension.

## Required Read-Only Status Command

Add:

```text
paid-grant-status <task_id> --grant-id <grant_id>
```

Report exact runtime state:

```text
ACTIVE
CONSUMED
NONE
```

For ACTIVE also classify with read-only current time:

```text
USABILITY: UNEXPIRED | EXPIRED
```

Status is non-authorizing and MUST NOT activate, consume, delete, refresh, extend, dispatch, or call provider.

## Explicit Out of Scope

```text
REAL_PAID_API_CALL: NO
BRAIN_DISPATCH_REQUEST_ALLOW_PAID_API: NO
M10_BRAIN_RUNTIME_WIRING: NO
PAID_CANDIDATE_SELECTION: NO
MODEL_GATEWAY_INVOCATION: NO
PROVIDER_INVOCATION: NO
PROVIDER_CREDENTIAL_READ: NO
EXECUTOR_PAID_API: NO
GRANT_REVOKE_DELETE: NO
M11.2C: NOT_IN_SCOPE
M11.3: NOT_IN_SCOPE
H1_H5: DEFERRED
```

Do not set `allow_paid_api=true` anywhere.

Do not create grant authorization from TASK markers, dispatch recommendations, capacity exhaustion, or credential presence.

## Safe Output Requirements

Successful create output must include:

```text
[PAID API GRANT ACTIVE]
TASK_ID
GRANT_ID
ACTOR_KIND: BRAIN
BRAIN_ID
PROVIDER_ID
MODEL_ID
BRAIN_OPERATION
AUTHORIZED_ARTIFACT_PATH
AUTHORIZED_ARTIFACT_BLOB_SHA
MAX_INPUT_TOKENS
MAX_OUTPUT_TOKENS
MAX_CALLS: 1
EXPIRES_AT_EPOCH_SECONDS
WORKSPACE_ID
GRANT_FINGERPRINT
HUMAN_SPEND_AUTHORIZATION: YES
PAID_API_DISPATCH_ENABLED: NO
PROVIDER_CALL_STARTED: NO
```

Never print raw grant JSON or credentials.

## Targeted Test Command

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_bridge_paid_api_grant.py -q
```

Executor runs only targeted tests. Bridge publication owns the full repository suite.

## Required Tests / Acceptance

Mechanically prove:

```text
PAID_API_RUNTIME_PATH_EXTERNAL: PASS
STORE_BINDS_CURRENT_WORKSPACE: PASS
HUMAN_CONFIRMATION_GATE: PASS
ALL_SPEND_FIELDS_EXPLICIT: PASS
FORBIDDEN_AUTHORITY_FLAGS_ABSENT: PASS
TTL_1_ACCEPTED: PASS
TTL_900_ACCEPTED: PASS
TTL_0_REJECTED: PASS
TTL_901_REJECTED: PASS
ONE_WALL_CLOCK_OBSERVATION_CREATE: PASS
BRIDGE_GENERATED_GRANT_ID: PASS
NO_GRANT_ID_COLLISION_RETRY: PASS
BRAIN_ONLY_GRANT: PASS
MAX_CALLS_ONE: PASS
CANONICAL_CONTROL_ARTIFACT_RESOLUTION: PASS
HUMAN_BLOB_OVERRIDE_FORBIDDEN: PASS
CURRENT_WORKSPACE_BINDING: PASS
EXACT_BRAIN_PROVIDER_MODEL_OPERATION_BINDING: PASS
EXACT_TOKEN_BOUNDS: PASS
MISSING_ARTIFACT_FAILS_BEFORE_ACTIVATION: PASS
INVALID_GRANT_FAILS_BEFORE_ACTIVE_PERSISTENCE: PASS
ACTIVATE_ONCE_AND_REQUIRE_EXACT: PASS
SAFE_RECEIPT_OUTPUT: PASS
CREDENTIALS_NOT_PERSISTED_OR_PRINTED: PASS
NO_DISPATCH_OR_PROVIDER_CALL: PASS
NO_EXECUTOR_AUTH_OR_LEASE_MUTATION: PASS
READ_ONLY_STATUS_ACTIVE: PASS
READ_ONLY_STATUS_EXPIRED: PASS
READ_ONLY_STATUS_CONSUMED: PASS
READ_ONLY_STATUS_NONE: PASS
CORRUPT_STATUS_FAIL_CLOSED: PASS
NO_REVOKE_DELETE_REFRESH: PASS
M11_2C_NOT_IMPLEMENTED: PASS
M11_3_NOT_IMPLEMENTED: PASS
TARGETED_TESTS: PASS
FULL_REPO_TESTS: PASS
REGRESSIONS: 0
FINAL_INDEPENDENT_AUDIT: PASS
```

## Forbidden Write Scope

Do not modify:

```text
src/aios_bridge/paid_api_grant.py
src/aios_bridge/runtime_paid_api_grant.py
src/aios_bridge/runtime_dispatch.py
src/aios_bridge/runtime_lease.py
src/aios_bridge/continuity/**
src/aios_bridge/external_brain/**
src/aios_bridge/executor_automation.py
src/aios_bridge/executor_context.py
src/aios_bridge/executor_transports/**
.agents/**
existing tests other than the new TASK-052 test file
.ai/tasks/**
.ai/reviews/**
.ai/decisions/**
.ai/context/**
.ai/proofs/**
```

except Bridge-generated `.ai/results/RESULT-052.md` during publication.

## Completion Boundary

After Bridge publication:

```text
STOP
NEXT: Review TASK-052 in ChatGPT
```

Do not begin M11.2C automatically.
