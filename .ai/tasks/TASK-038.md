# TASK-038 — M10.2 Runtime Capacity Snapshot + Bridge Recommendation Surface

STATUS: READY
CLASS: L3 — RUNTIME CAPACITY / READ-ONLY DISPATCH INTEGRATION / HUMAN-AUTHORITY PRESERVATION
EXECUTOR_MODE: THIN_EXECUTOR

## Baseline

```text
MAIN_SHA: b1f85034c1b18b3d3526f6ece85afd04cdcdc17e
TARGET_BRANCH: ai/task-038
```

## Authoritative Contract

```text
ADR_PATH: .ai/decisions/ADR-027-M10.2-RUNTIME-CAPACITY-BRIDGE-RECOMMENDATION-CONTRACT-LOCK.md
ADR_BLOB_SHA: 11674c9b5b2c3639552678f7371dba5c3d0599cd
BLUEPRINT_PATH: .ai/context/TASK-038-M10.2-IMPLEMENTATION-BLUEPRINT.md
BLUEPRINT_BLOB_SHA: df5531a590ebbe999d107cecc0cdbf6340eae506
```

## Objective

Integrate M10.1 deterministic dispatch with explicit external runtime capacity observations and a read-only Bridge recommendation surface.

M10.2 MUST preserve the invariant:

```text
RECOMMENDATION != AUTHORIZATION
```

Bridge may record/show capacity and recommend an executor. Human remains the sole authority for RUN/FIX/MERGE and explicit executor choice.

## Exact Executor Dispatch Policy

DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX","RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX","RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"claude-code","preference_rank":2,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX","RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

This marker is policy evidence only. It does not authorize any candidate.

## Required Deliverables

```text
src/aios_bridge/runtime_dispatch.py
tests/aios_bridge/test_runtime_dispatch.py
tests/test_bridge_dispatch.py
bridge.py
```

Bridge may generate:

```text
.ai/results/RESULT-038.md
```

## Allowed Files

```text
src/aios_bridge/runtime_dispatch.py
tests/aios_bridge/test_runtime_dispatch.py
tests/test_bridge_dispatch.py
bridge.py
.ai/results/RESULT-038.md
```

## Forbidden Scope

Do NOT modify:

```text
src/aios_bridge/continuity/dispatch.py
src/aios_bridge/continuity/brain.py
src/aios_bridge/continuity/executor.py
src/aios_bridge/continuity/lease.py
src/aios_bridge/continuity/executor_failover.py
src/aios_bridge/continuity/hot_handoff.py
src/aios_bridge/continuity/state.py
src/aios_bridge/runtime_lease.py
src/aios_bridge/external_brain/**
src/providers/**
```

No M10.1 ranking redesign.
No M5/M6/M9 contract change.
No M11 API escape-hatch implementation.
No provider/model quota probing.
No automatic actor invocation.
No automatic RUN/FIX/MERGE authorization.
No automatic lease mutation.

## Required Behavior

Implement ADR-027 and the implementation blueprint exactly.

At minimum:
- persist per-actor runtime capacity records outside Git worktree;
- records are canonical, fingerprinted, TTL-bound and atomic;
- missing/expired observation becomes effective `UNKNOWN`;
- malformed/corrupt observation fails closed;
- parse exactly one task/review `DISPATCH_EXECUTOR_POLICY_JSON` marker;
- construct existing M10.1 `ExecutorDispatchRequest` from static policy + dynamic capacity;
- call existing `dispatch_executor()` rather than duplicating ranking;
- expose `capacity-set`, `capacity-show`, and `recommend` Bridge commands;
- `recommend` binds to exact authoritative TASK/REVIEW blob;
- recommendation output includes policy/request/result/observation fingerprints;
- recommendation always reports `HUMAN_APPROVAL_REQUIRED: YES`;
- recommendation never creates authorization or lease evidence.

## Required Operational Shape

For fresh observations:

```text
antigravity = QUOTA_EXHAUSTED
codex       = AVAILABLE
```

with both candidates satisfying the exact required capabilities above:

```text
bridge.py recommend 38 --kind executor --action RUN
```

must deterministically produce:

```text
STATUS: SELECTED
SELECTED_EXECUTOR: codex
HUMAN_APPROVAL_REQUIRED: YES
AUTHORIZATION_CHANGED: NO
LEASE_CHANGED: NO
```

The Human then separately decides whether to run:

```text
bridge.py approve 38 --kind task --executor codex
```

The recommendation command itself MUST NOT run that approval.

## Required Tests

Implement all ADR-027 Decision 15 and blueprint test requirements, including:
- atomic record persistence/tamper/freshness/path safety;
- generic Brain/Executor capacity store support;
- exact policy parsing and fail-closed malformed markers;
- exact TASK and CHANGES_REQUIRED REVIEW binding;
- control-artifact drift rejection;
- antigravity exhausted + codex available recommendation;
- no authorization/lease mutation;
- no forbidden paid-API fallback;
- existing M10.1 dispatcher unchanged;
- full repository suite green under Bridge publication.

## Thin Executor Mode

Primary Brain has completed architecture and implementation design.

Executor SHALL:
- read only the bounded files listed by the blueprint;
- follow ADR-027/blueprint exactly;
- not redesign runtime dispatch;
- not broad-search the repository;
- not modify M10.1/lease/failover/hot-handoff contracts;
- run targeted tests only;
- stop after targeted tests pass.

## Targeted Test Commands

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_bridge/test_runtime_dispatch.py -q
.\venv\Scripts\python.exe -m pytest tests/test_bridge_dispatch.py -q
.\venv\Scripts\python.exe -m pytest tests/aios_bridge/continuity/test_dispatch.py -q
```

Do NOT run the full repository suite from the Executor. Bridge publication owns it.

## Publication Gate

After targeted tests pass, Human runs:

```powershell
.\venv\Scripts\python.exe .\bridge.py publish 38 --action RUN --test ".\venv\Scripts\python.exe -m pytest tests/ -q"
```

## Acceptance

PASS requires:

```text
RUNTIME_CAPACITY_STORE: PASS
TTL_FAIL_SAFE_UNKNOWN: PASS
ATOMIC_PERSISTENCE: PASS
EXACT_POLICY_MARKER: PASS
EXACT_CONTROL_BLOB_BINDING: PASS
M10_1_REUSE_WITHOUT_RANKING_CHANGE: PASS
CODEX_RECOMMENDATION_SCENARIO: PASS
RECOMMENDATION_ONLY: PASS
HUMAN_AUTHORITY_PRESERVED: PASS
LEASE_AUTH_UNCHANGED: PASS
PROVIDER_API_PROBING: NONE
FULL_REPO_TESTS: PASS
REGRESSIONS: 0
M10_2: PASS
M10_3_PROVEN: NO
```

M10.3 real operational dispatch proof remains separate.