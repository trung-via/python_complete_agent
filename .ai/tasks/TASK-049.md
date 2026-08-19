# TASK-049 — M11.1 Paid API Grant Contract

STATUS: READY
CLASS: L3 — PURE SECURITY CONTRACT / PAID-API BRAIN GRANT
MILESTONE: M11.1
EXECUTOR_MODE: UNIFIED_AIOS_WORKER_DUAL_EXECUTOR

## Baseline

```text
MAIN_SHA: 09f5aa30e509bb651a78fa35b696bfbd082d5958
TARGET_BRANCH: ai/task-049
```

## Authoritative Contracts

```text
ADR_036_PATH: .ai/decisions/ADR-036-M11-EXTERNAL-API-ESCAPE-HATCH-ARCHITECTURE-LOCK.md
ADR_036_BLOB_SHA: cf71c571d8e3fd611ea07d21f15ad0bf90ef6ecc
ADR_038_PATH: .ai/decisions/ADR-038-DEFAULT-DUAL-EXECUTOR-TASK-AUTHORING-POLICY-LOCK.md
ADR_038_BLOB_SHA: 72d38bf2f2ff5a07e7b63322116ad87622349df1
BLUEPRINT_PATH: .ai/context/TASK-049-M11.1-PAID-API-GRANT-CONTRACT-BLUEPRINT.md
BLUEPRINT_BLOB_SHA: c78a15e64e1fdc53f9cd0b60559bc2746cb679db
```

## Reissue Boundary

TASK-049 is the fresh post-TASK-048 reissue of the M11.1 work previously designed under TASK-047.

```text
TASK-047_STATUS: DEFERRED
TASK-047_EXECUTED: NO
TASK-047_PUBLISHED: NO
TASK-047_MERGED: NO
TASK-047_REACTIVATION: FORBIDDEN
```

Do not read TASK-047 as active authority. TASK-049 and its exact blueprint are the only RUN authority for this implementation.

## Objective

Implement the pure immutable one-shot Human paid-API Brain grant contract for M11.1.

This task is contract/validation/serialization work only:

```text
REAL_PAID_API_CALL: NO
RUNTIME_GRANT_STORAGE: NO
DISPATCH_WIRING: NO
BRIDGE_COMMAND_CHANGE: NO
PAID_API_EXECUTOR: NO
M11.2: NOT_IN_SCOPE
M11.3: NOT_IN_SCOPE
```

## Machine-Readable Executor Context

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/decisions/ADR-036-M11-EXTERNAL-API-ESCAPE-HATCH-ARCHITECTURE-LOCK.md","blob_sha":"cf71c571d8e3fd611ea07d21f15ad0bf90ef6ecc"},{"path":".ai/decisions/ADR-038-DEFAULT-DUAL-EXECUTOR-TASK-AUTHORING-POLICY-LOCK.md","blob_sha":"72d38bf2f2ff5a07e7b63322116ad87622349df1"},{"path":".ai/context/TASK-049-M11.1-PAID-API-GRANT-CONTRACT-BLUEPRINT.md","blob_sha":"c78a15e64e1fdc53f9cd0b60559bc2746cb679db"}]

## Machine-Readable Executor Worktree Scope

EXECUTOR_ALLOWED_PATHS_JSON: ["src/aios_bridge/paid_api_grant.py","tests/aios_bridge/test_paid_api_grant.py"]

Bridge-generated `.ai/results/RESULT-049.md` is not Executor-writable implementation scope.

## Executor Dispatch Policy

DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

`allow_paid_api:false` above is the Executor routing policy for implementing TASK-049. It MUST NOT be confused with the future M11 Brain paid-API runtime grant. This implementation task itself must not spend paid-API budget.

Both listed executors are eligible. Candidate rank is recommendation metadata only; it does not authorize or select an actor. Human selects exactly one executor by choosing the UI in which RUN is invoked.

## Human RUN Choice

Choose exactly one:

```text
Antigravity:
/aios-worker RUN TASK-049

Codex:
$aios-worker RUN TASK-049
```

The selected adapter MUST echo and bind the chosen executor. No silent reroute, fallback, or second executor invocation.

## Required Implementation

Create exactly:

```text
src/aios_bridge/paid_api_grant.py
tests/aios_bridge/test_paid_api_grant.py
```

Follow the locked blueprint exactly.

The blueprint already supplies the required existing imports, field contract, validators, canonical serialization/fingerprint rules, security bounds, adversarial cases, and test plan. Broad repository exploration or architecture redesign is not required.

## Core Contract Summary

Production contract must provide:

```text
PaidApiGrant (frozen dataclass)
semantic_dict()
to_dict()
to_canonical_json()
fingerprint()
from_dict()
from_json()
validate_paid_api_grant_binding()
validate_paid_api_grant_budget()
```

with:

```text
actor_kind = BRAIN only
max_calls = 1 only
exact artifact/blob/workspace/provider/model/operation binding
bounded input/output tokens
canonical SHA-256 grant fingerprint
MAX_SERIALIZED_BYTES bound
no credential secrets
no wall-clock lookup
no filesystem mutation
no network
no subprocess
no provider/model call
```

## Thin Executor Rules

Executor MUST:
- read only the bounded context delivered by AIOS Bridge plus the two allowed implementation files it creates;
- follow the blueprint rather than redesign M11;
- implement only the two allowed paths;
- run only the targeted test suite;
- stop normally at the Bridge publication boundary.

Executor MUST NOT:
- broadly inspect unrelated repository files;
- modify existing continuity/dispatch/external-brain/executor code;
- run the full repository suite itself when Bridge publication owns it;
- invoke a paid API;
- implement M11.2/M11.3;
- retry or reroute to another executor;
- merge.

## Targeted Test Command

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_bridge/test_paid_api_grant.py -q
```

Bridge publication owns the repository-wide suite.

## Forbidden Scope

Do not modify:

```text
bridge.py
src/aios_bridge/continuity/**
src/aios_bridge/runtime_dispatch.py
src/aios_bridge/external_brain/**
src/aios_bridge/executor_automation.py
src/aios_bridge/executor_context.py
src/aios_bridge/executor_transports/**
tests/test_bridge_*.py
.ai/tasks/**
.ai/reviews/**
.ai/decisions/**
.ai/context/**
.ai/proofs/**
```

except Bridge-generated `.ai/results/RESULT-049.md` during publication.

Do not add:

```text
paid API Executor support
OpenAI/Anthropic/Gemini provider proliferation
real provider calls
runtime paid-grant storage
Bridge paid-grant commands
M10 dispatch changes
auto retry
auto fallback
auto merge
H1-H5 implementation
```

## Acceptance

```text
PURE_IMMUTABLE_GRANT_CONTRACT: PASS
BRAIN_ONLY_ACTOR_BINDING: PASS
EXECUTOR_GRANT_REJECTED: PASS
ONE_SHOT_MAX_CALLS_CONTRACT: PASS
CANONICAL_FINGERPRINT: PASS
STRICT_EXACT_DESERIALIZATION: PASS
EXACT_TASK_ARTIFACT_WORKSPACE_BINDING: PASS
PROVIDER_MODEL_OPERATION_BINDING: PASS
INPUT_OUTPUT_BUDGET_BOUNDS: PASS
MAX_SERIALIZED_BYTES_BOUND: PASS
NO_CREDENTIAL_SECRET_FIELDS: PASS
NO_ENV_NETWORK_SUBPROCESS_PROVIDER_CALL: PASS
TARGETED_TESTS: PASS
FULL_REPO_TESTS: PASS
REGRESSIONS: 0
FINAL_INDEPENDENT_AUDIT: PASS
```

Only Human authorizes RUN/FIX/MERGE and executor choice. ChatGPT remains the independent review/merge gate.

## Completion Boundary

After successful Bridge publication:

```text
STOP
NEXT: Review TASK-049 in ChatGPT
```

Do not begin M11.2 automatically.
