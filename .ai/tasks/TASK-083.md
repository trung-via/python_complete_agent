# TASK-083 — P0 Validation Ownership + Full-Suite Deduplication Foundation

STATUS: BLOCKED_PENDING_TASK_082_CLOSURE
PUBLISHER_PROFILE: CANONICAL_E4
CLASS: L3 — AIOS BRIDGE LEAN EXECUTION / P0 FOUNDATION
MILESTONE: P0
CAPABILITY_ID: P0_VALIDATION_OWNERSHIP_TELEMETRY
EXECUTOR_MODE: DUAL_EXECUTOR_ALLOWED
RECOMMENDED_EXECUTOR: antigravity
PAID_API_CALL_ALLOWED: NO
AUTO_RETRY_ALLOWED: NO
AUTO_REROUTE_ALLOWED: NO

ROADMAP_ID: AIOS-BRIDGE-LEAN-EXECUTION
ROADMAP_VERSION: 1.0
CANONICAL_ROADMAP: .ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.0.md
CANONICAL_DECISION: .ai/decisions/ADR-056-AIOS-BRIDGE-LEAN-EXECUTION-CONTROLLED-EVOLUTION-CONTRACT-LOCK.md

## Activation Boundary

TASK-083 is intentionally authored now but MUST NOT RUN until TASK-082 is independently reviewed and its canonical disposition is complete. At activation time, Bridge/task-authoring must bind TASK-083 to the then-current canonical `main` and exact roadmap/decision blob identities before execution authorization.

If the current executable-task contract cannot safely rebind a pre-authored blocked task to the new canonical main without violating immutable task authority, author a replacement executable task from the then-current main and close this artifact as blueprint-only. Do not weaken baseline binding to force execution.

## Purpose

Implement the first P0 slice of the locked AIOS Bridge Lean Execution Refactor:

1. establish explicit single-owner validation semantics;
2. remove duplicate full-repository test execution from the Codex E4 path;
3. make Antigravity and Codex share the same validation ownership contract;
4. add bounded telemetry proving how many full suites actually ran;
5. preserve all existing Bridge authority and publication safety semantics.

This task is a surgical refactor, not a Bridge rewrite.

## Required Invariants

```text
TASK_AUTHORITY_UNCHANGED: YES
REVIEW_AUTHORITY_UNCHANGED: YES
LEASE_SEMANTICS_UNCHANGED: YES
ROADMAP_BINDING_UNCHANGED: YES
SCOPE_ENFORCEMENT_UNCHANGED: YES
MERGE_AUTHORITY_UNCHANGED: YES
AUTO_RETRY: NO
AUTO_REROUTE: NO
H5_OPENED: NO
```

## P0 Validation Ownership Contract

Define explicit validation tiers equivalent to:

```text
T0_MICRO
T1_TARGETED_IMPACT
T2_FULL_CANONICAL
T3_RELEASE
```

and owner classes equivalent to:

```text
EXECUTOR
CERTIFICATION_BOUNDARY
RELEASE_BOUNDARY
```

For normal canonical task publication under this P0 slice:

```text
T0/T1 -> executor owned
T2    -> certification boundary owned
```

Exactly one T2 owner is permitted.

## Machine-Readable Validation Plan

Introduce a bounded immutable validation plan sufficient to express at least:

```text
profile_id
executor_test_tiers
certification_test_tiers
diff_check_required
expected_full_suite_execution_count
```

Initial profiles must include a strict compatibility profile. Do not implement P1 product batching in this task.

Legacy task artifacts that explicitly request a full suite must not cause a second identical T2 run if the certification boundary already owns it. Compatibility behavior must be deterministic, tested, and fail-conservative.

## Codex Deduplication

Current Codex `bridge execute` hard-codes:

```text
python -m pytest tests/ -q
```

while tasks may independently instruct the executor to run the same full suite.

Refactor so T2 canonical certification is invoked exactly once by its declared owner.

Do not simply delete all tests from `cmd_execute`; preserve certification semantics through the validation plan/controller. If ownership is ambiguous, fall back to the strict existing-safe behavior and surface telemetry rather than silently skipping full certification.

## Antigravity Parity

Antigravity currently executes interactively and publishes through Bridge rather than `bridge execute`.

TASK-083 must ensure the same validation plan and T2 ownership semantics govern Antigravity publication. Antigravity must not have a separate policy that happens to produce similar results.

The physical UI surfaces may remain different; validation semantics must be shared.

## Telemetry

Add bounded immutable telemetry/evidence sufficient to record:

```text
task_id
action
executor_id
validation_profile
full_suite_execution_count
expected_full_suite_execution_count
targeted_test_execution_count
full_suite_duration_seconds when observed
targeted_test_duration_seconds when observed
validation_duplication_detected
```

Optional executor/provider usage fields may be added only if actually observed. Do not infer token/quota from wall-clock time.

Required behavior:

```text
full_suite_execution_count == expected -> normal evidence
full_suite_execution_count > expected  -> VALIDATION_DUPLICATION_DETECTED
```

Duplication detection is diagnostic; it does not manufacture a PASS or override failed tests.

## Executor-Neutral Boundary

No P0 validation policy may contain Codex-only or Antigravity-only semantics except in transport adapters required to invoke the shared contract.

Future `claude-code` must be representable by the same validation plan without changing core semantics.

## Explicit Out of Scope

```text
P1 capability batching
product fast lane
integration lane
public RESUME command
persistent Codex sessions
persistent Claude sessions
checkpoint/resume implementation
capacity suspension state
adaptive executor routing
automatic retry
automatic reroute
H5-H8 implementation
Bridge authorization redesign
lease redesign
merge redesign
```

## Suggested Writable Scope

Exact scope must be rebound at activation against current main, but the intended implementation surface is limited to files equivalent to:

```text
bridge.py
src/aios_bridge/validation.py                     # new if appropriate
src/aios_bridge/executor_automation.py            # only if required for shared validation evidence
.agents/skills/aios-worker/scripts/aios_worker.py # only if required for parity wiring
tests/aios_bridge/test_validation.py              # new if appropriate
tests/test_bridge_executor_automation.py
tests/aios_bridge/test_aios_worker_control_surface.py
```

Do not touch H4/H5 feature implementation files.

## Required Tests

Targeted tests must prove at minimum:

```text
VALIDATION_TIER_CLOSED: PASS
VALIDATION_OWNER_CLOSED: PASS
EXACTLY_ONE_T2_OWNER: PASS
LEGACY_FULL_SUITE_COMPATIBILITY: PASS
CODEX_FULL_SUITE_DUPLICATION_ELIMINATED: PASS
ANTIGRAVITY_VALIDATION_PARITY: PASS
CODEX_VALIDATION_PARITY: PASS
CLAUDE_CONTRACT_COMPATIBLE: PASS
FULL_SUITE_COUNT_TELEMETRY: PASS
DUPLICATION_DETECTION: PASS
FAILED_T2_CANNOT_PUBLISH: PASS
AMBIGUOUS_OWNERSHIP_FAILS_CONSERVATIVELY: PASS
TASK_AUTHORITY_UNCHANGED: PASS
LEASE_SEMANTICS_UNCHANGED: PASS
ROADMAP_GOVERNANCE_UNCHANGED: PASS
AUTO_RETRY: NO
AUTO_REROUTE: NO
```

## Validation Commands

Executor runs targeted/impact tests and diff check only.

The certification boundary owns the canonical full suite exactly once.

The task/result evidence must prove the actual full-suite execution count and owner.

## Acceptance Boundary

TASK-083 passes only if:

```text
P0_R1_SINGLE_TEST_OWNER: PASS
P0_R2_EXPLICIT_VALIDATION_PLAN: PASS
P0_R3_FULL_SUITE_DEDUP_FOUNDATION: PASS
P0_R4_TELEMETRY_FOUNDATION: PASS
ANTIGRAVITY_CODEX_POLICY_PARITY: PASS
CONTROL_PLANE_AUTHORITY_UNCHANGED: PASS
FULL_CANONICAL_CERTIFICATION_PRESERVED: PASS
P1_P3_NOT_IMPLEMENTED: PASS
H5_NOT_OPENED: PASS
```
