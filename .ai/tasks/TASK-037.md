# TASK-037 — M10.1 Quota-Efficient Deterministic Dispatch Policy

STATUS: READY
CLASS: L3 — CONTINUITY POLICY / ZERO-TOKEN DISPATCH / HUMAN-AUTHORITY PRESERVATION

## Baseline

```text
MAIN_SHA: 57a6674887b43e3e91fc01b73479964506b2283e
TARGET_BRANCH: ai/task-037
```

## Authoritative Contract

```text
.ai/decisions/ADR-026-M10.1-DETERMINISTIC-DISPATCH-POLICY-CONTRACT-LOCK.md
.ai/context/TASK-037-M10.1-IMPLEMENTATION-BLUEPRINT.md
```

## Objective

Implement M10.1 as a pure, deterministic, zero-token Brain/Executor recommendation engine using existing capability contracts and explicit capacity snapshots.

The dispatcher recommends an actor only. It MUST NOT authorize execution, mutate leases/runtime state, invoke agents/models/APIs, or modify Bridge behavior.

## Required Deliverables

```text
src/aios_bridge/continuity/dispatch.py
tests/aios_bridge/continuity/test_dispatch.py
src/aios_bridge/continuity/__init__.py
```

Bridge may generate:

```text
.ai/results/RESULT-037.md
```

## Allowed Files

```text
src/aios_bridge/continuity/dispatch.py
src/aios_bridge/continuity/__init__.py
tests/aios_bridge/continuity/test_dispatch.py
.ai/results/RESULT-037.md   # Bridge-generated only
```

## Forbidden Scope

Do NOT modify:

```text
bridge.py
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

No routing/provider/API integration.
No automatic quota probing.
No automatic executor/brain invocation.
No RUN/FIX/MERGE authorization.
No lease acquisition/release.

## Required Behavior

Implement exactly ADR-026 + the supplied implementation blueprint.

At minimum the dispatcher SHALL:
- filter Brain candidates by operation/context/policy compatibility;
- filter Executor candidates by operation/required capabilities/policy compatibility;
- consume explicit AVAILABLE/LIMITED/QUOTA_EXHAUSTED/UNAVAILABLE/UNKNOWN state;
- prefer subscription capacity before paid API capacity;
- exclude paid API unless explicitly allowed;
- rank deterministically by capacity class, runnable capacity state, preference rank, then actor ID;
- return SELECTED, WAIT, or NO_COMPATIBLE_CANDIDATE with machine-readable candidate evaluations;
- be input-order independent;
- produce deterministic canonical fingerprints;
- fail closed on malformed/duplicate/aliased inputs.

Required scenario:

```text
antigravity = QUOTA_EXHAUSTED
codex       = AVAILABLE
required executor capabilities are satisfied by both
paid API is not needed
=> SELECTED: codex
```

This is a recommendation only. Human authorization remains mandatory.

## Required Tests

Implement every adversarial test enumerated in ADR-026 Decision 14 and blueprint section 11.

## Thin Executor Mode

The Primary Brain has already completed architecture and implementation design.

Executor SHALL:
- read only the bounded files in the blueprint;
- follow the blueprint exactly;
- not redesign the dispatcher;
- not perform broad repository exploration;
- not modify Bridge or existing continuity contracts;
- run targeted tests only;
- stop after targeted tests pass.

## Targeted Test Commands

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_bridge/continuity/test_dispatch.py -q
.\venv\Scripts\python.exe -m pytest tests/aios_bridge/continuity/test_executor.py tests/aios_bridge/continuity/test_brain.py -q
```

Do NOT run the full repository suite manually. Bridge publication owns the full-suite gate once.

## Acceptance Criteria

```text
PURE_FUNCTION_DISPATCH: PASS
ZERO_TOKEN_ROUTING: PASS
DETERMINISTIC_SELECTION: PASS
INPUT_ORDER_INDEPENDENCE: PASS
CAPABILITY_FILTERING: PASS
QUOTA_EXHAUSTED_NOT_SELECTED: PASS
SUBSCRIPTION_FIRST: PASS
PAID_API_EXPLICIT_GATE: PASS
WAIT_SEMANTICS: PASS
HUMAN_AUTHORITY_PRESERVED: PASS
NO_LEASE_MUTATION: PASS
NO_BRIDGE_AUTH_CHANGE: PASS
NO_M11_API_INVOCATION: PASS
TARGETED_TESTS: PASS
FULL_REPO_TESTS: PASS
REGRESSIONS: 0
```

M10.1 does NOT complete M10.2/M10.3 and does NOT authorize M11.
