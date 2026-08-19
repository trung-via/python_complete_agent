# TASK-047 — M11.1 Paid API Grant Contract

STATUS: READY
CLASS: L2 — PURE CONTRACT / HUMAN PAID-API AUTHORIZATION BOUNDARY
EXECUTOR_MODE: E4_AUTOMATED_THIN_EXECUTOR

## Baseline

```text
MAIN_SHA: 22a05d1f4880daf3a9f964e0564c658b051039cd
TARGET_BRANCH: ai/task-047
```

## Authoritative Contract

```text
ADR_PATH: .ai/decisions/ADR-036-M11-EXTERNAL-API-ESCAPE-HATCH-ARCHITECTURE-LOCK.md
ADR_BLOB_SHA: cf71c571d8e3fd611ea07d21f15ad0bf90ef6ecc
BLUEPRINT_PATH: .ai/context/TASK-047-M11.1-PAID-API-GRANT-CONTRACT-BLUEPRINT.md
BLUEPRINT_BLOB_SHA: db6b9e480ea9debfd79d74b857b3efb97377acd1
```

## M11 Position

```text
M11.1 — Paid API Grant Contract              ← THIS TASK
M11.2 — Runtime Grant + Brain Escape Wiring
M11.3 — Real Operational Escape Proof
```

M11 v1 is Brain-side only. Paid API Executor support is explicitly unsupported/fail-closed and H-Series remains deferred.

## Objective

Implement one pure immutable `PaidApiGrant` contract plus pure exact binding/budget validators.

This task grants no API authority by itself and performs no provider call.

## Machine-Readable Executor Context

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/decisions/ADR-036-M11-EXTERNAL-API-ESCAPE-HATCH-ARCHITECTURE-LOCK.md","blob_sha":"cf71c571d8e3fd611ea07d21f15ad0bf90ef6ecc"},{"path":".ai/context/TASK-047-M11.1-PAID-API-GRANT-CONTRACT-BLUEPRINT.md","blob_sha":"db6b9e480ea9debfd79d74b857b3efb97377acd1"}]

## Machine-Readable Executor Worktree Scope

EXECUTOR_ALLOWED_PATHS_JSON: ["src/aios_bridge/paid_api_grant.py","tests/aios_bridge/test_paid_api_grant.py"]

`RESULT-047.md` is Bridge-generated only.

## Executor Dispatch Policy

DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

The implementation executor remains subscription Codex. This task MUST NOT use a paid API.

## Required Production Surface

Create exactly:

```text
src/aios_bridge/paid_api_grant.py
```

with:

```text
PaidApiGrant
validate_paid_api_grant_binding(...)
validate_paid_api_grant_budget(...)
```

and the public v1 bounds locked by the blueprint.

The grant is:
- immutable;
- deterministic;
- exact-field serialized;
- fingerprinted;
- Brain-only;
- one-call only;
- token bounded;
- secret-free;
- pure.

## Required Test Surface

Create exactly:

```text
tests/aios_bridge/test_paid_api_grant.py
```

Implement the complete adversarial matrix locked in the blueprint, including exact serialization, forged fingerprint rejection, EXECUTOR rejection, all binding mismatches, token budget failures, artifact path canonicality, and secret/network/process absence.

## Allowed Files

Executor may create exactly:

```text
src/aios_bridge/paid_api_grant.py
tests/aios_bridge/test_paid_api_grant.py
```

Bridge may generate:

```text
.ai/results/RESULT-047.md
```

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
.ai/proofs/**
```

Do not:
- implement M11.2/M11.3;
- read/store API keys;
- call any API/network;
- add retries/fallbacks;
- add providers;
- add paid API Executor support;
- activate H1-H5;
- auto merge.

## Targeted Test

Executor runs only:

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_bridge/test_paid_api_grant.py -q
```

Do not run the full suite manually. E4 automatic publication owns the full repository suite.

## Acceptance

```text
PURE_IMMUTABLE_GRANT_CONTRACT: PASS
BRAIN_ONLY: PASS
EXECUTOR_REJECTED: PASS
ONE_CALL_ONLY: PASS
TOKEN_BOUNDS: PASS
EXACT_ARTIFACT_BINDING: PASS
EXACT_WORKSPACE_BINDING: PASS
DETERMINISTIC_FINGERPRINT: PASS
FORGED_FINGERPRINT_REJECTED: PASS
EXACT_FIELD_SERIALIZATION: PASS
SECRET_FREE: PASS
NO_NETWORK: PASS
NO_SUBPROCESS: PASS
NO_RUNTIME_MUTATION: PASS
NO_PAID_API_CALL: PASS
M11_2_NOT_IMPLEMENTED: PASS
H_SERIES_DEFERRED: PASS
TARGETED_TESTS: PASS
FULL_REPO_TESTS: PASS
REGRESSIONS: 0
FINAL_INDEPENDENT_AUDIT: PASS
M11_1: PASS
```

Only Human authorizes RUN and MERGE.
