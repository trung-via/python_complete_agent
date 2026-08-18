# REVIEW-037 — M10.1 Quota-Efficient Deterministic Dispatch Policy

STATUS: PASS
APPROVED: YES
READY_FOR_HUMAN_MERGE: YES
MERGE_AUTHORIZED: NO

## Review Round

Round 1 — final independent architecture, scope, determinism, authority, and adversarial-test audit.

## Authoritative Anchors

```text
TASK_ID: TASK-037
BASELINE_MAIN_SHA: 57a6674887b43e3e91fc01b73479964506b2283e
TASK_BRANCH: ai/task-037
FINAL_TASK_HEAD_SHA: b1f85034c1b18b3d3526f6ece85afd04cdcdc17e
TASK_BLOB_SHA: ba731df482a999ac0840251c54767e6f96139cf0
ADR_026_BLOB_SHA: 842b6954396ed2fac7ea6e25179ca6dd9d853911
BLUEPRINT_BLOB_SHA: fdcb4feef9defb43de970b87cf6764fe55050fe8
RESULT_BLOB_SHA: 2c58a82853ea828a3553b4a6149103201fb8ff64
DISPATCH_BLOB_SHA: 9169884c079302f86bbda5f77a9a9d7ea6800dd9
INIT_BLOB_SHA: fd4bf696ff08916428334ab777710e549a85f4d4
TEST_BLOB_SHA: c0c68bd299ab7a4dea2f401399ac01a1050d1b3e
```

## Lineage / Scope Audit

Fresh remote `main` remains exactly the TASK baseline.

```text
COMMITS_AHEAD_OF_BASELINE: 1
COMMITS_BEHIND_BASELINE: 0
MERGE_BASE: 57a6674887b43e3e91fc01b73479964506b2283e
CHANGED_PATHS:
  .ai/results/RESULT-037.md
  src/aios_bridge/continuity/__init__.py
  src/aios_bridge/continuity/dispatch.py
  tests/aios_bridge/continuity/test_dispatch.py
SCOPE_AUDIT: PASS
```

No `bridge.py`, Brain/Executor core contract, lease, stable failover, hot handoff, runtime lease, provider, or External Brain implementation changed.

## Pure / Zero-Token Architecture Audit

`dispatch.py` is a pure recommendation module. Its imports are bounded to:

```text
dataclasses
enum
hashlib
json
typing
BrainCapability
ExecutorCapabilities / ExecutionOperation / ExecutionCapability
ContinuityStateValidationError
SCHEMA_VERSION / MAX_SERIALIZED_BYTES / BrainOperation / actor validation
```

It contains no Bridge, lease store, runtime state, environment, clock, filesystem, Git, subprocess, network, provider, LLM, or paid-API invocation surface.

```text
PURE_RECOMMENDATION_ONLY: PASS
ZERO_TOKEN_SELECTION: PASS
NO_RUNTIME_QUOTA_PROBING: PASS
NO_AUTHORIZATION_MUTATION: PASS
NO_LEASE_MUTATION: PASS
NO_AGENT_INVOCATION: PASS
NO_API_INVOCATION: PASS
NO_MERGE_OR_PUBLISH_AUTHORITY: PASS
HUMAN_AUTHORITY_PRESERVED: PASS
```

## Deterministic Policy Audit

The implementation uses the locked ranking tuple:

```text
1. CapacityClass: SUBSCRIPTION before PAID_API
2. CapacityState: AVAILABLE before LIMITED
3. preference_rank: lower integer first
4. actor_id: lexical ascending final tie-break
```

Candidate inputs are canonicalized by actor ID before request serialization/fingerprinting, and result evaluations are canonicalized by actor ID.

```text
INPUT_ORDER_INDEPENDENT: PASS
REQUEST_FINGERPRINT_DETERMINISTIC: PASS
RESULT_FINGERPRINT_DETERMINISTIC: PASS
LEXICAL_TIE_BREAK: PASS
SUBSCRIPTION_FIRST: PASS
AVAILABLE_BEFORE_LIMITED: PASS
PREFERENCE_RANK_ORDER: PASS
```

## Compatibility / Capacity Semantics

Brain dispatch mechanically filters by:
- requested BrainOperation;
- required context bytes versus bounded max context;
- paid-API policy gate.

Executor dispatch mechanically filters by:
- requested ExecutionOperation;
- required ExecutionCapability subset;
- paid-API policy gate.

Capacity state semantics match ADR-026:

```text
AVAILABLE       -> compatible+runnable when policy/capability compatible
LIMITED         -> compatible+runnable, lower than AVAILABLE
QUOTA_EXHAUSTED -> compatible but non-runnable
UNAVAILABLE     -> compatible but non-runnable
UNKNOWN         -> compatible but non-runnable
```

Status semantics are exact:

```text
SELECTED                -> at least one compatible runnable candidate
WAIT                    -> compatible candidate(s) exist, none runnable
NO_COMPATIBLE_CANDIDATE -> no policy/capability/context-compatible candidate
```

A forbidden PAID_API candidate is not silently used to escape WAIT.

## Real Policy-Shaped Scenario

Focused coverage includes the exact M10 operational shape:

```text
antigravity = QUOTA_EXHAUSTED
codex       = AVAILABLE
required capabilities = repo read + filesystem write + shell + tests + local git
=> SELECTED: codex
```

The test repeats this across candidate permutations and proves the same selected actor and result fingerprint.

```text
REAL_SCENARIO_CODEX_SELECTED: PASS
REAL_SCENARIO_ORDER_INDEPENDENT: PASS
```

This selection remains recommendation evidence only; it does not create authorization or ExecutorLease evidence.

## Fail-Closed / Adversarial Audit

ADR-026 Decision 14 coverage is present for:

```text
1  identical input determinism
2  input-order independence
3  operation/capability mismatch exclusion
4  executor required-capability subset
5  Brain context-too-large exclusion
6  AVAILABLE outranks LIMITED
7  QUOTA_EXHAUSTED never selected
8  UNKNOWN never selected
9  SUBSCRIPTION outranks PAID_API
10 PAID_API excluded unless explicitly allowed
11 WAIT with compatible but non-runnable subscription capacity
12 NO_COMPATIBLE with no compatible candidate
13 lower preference rank wins
14 lexical actor-id tie-break
15 duplicate actor IDs reject
16 embedded capability actor mismatch rejects
17 bool/negative preference rank rejects
18 duplicate required capabilities reject
19 bounded source/AST guard against I/O/clock/network/LLM/store surfaces
20 antigravity exhausted + codex available => codex
21 DispatchResult does not create authorization/lease evidence
```

Additional validation coverage includes invalid context byte values, unknown enums, and non-canonical/case-aliased actor IDs.

```text
ADR_026_DECISION_14_COVERAGE: PASS
NO_FUZZY_ACTOR_MATCHING: PASS
NO_CASE_ALIASING: PASS
FAIL_CLOSED_VALIDATION: PASS
```

## Existing Contract Preservation

`__init__.py` only exports the new M10.1 public enums/models/functions. There is no redesign of existing M1-M9 contracts.

```text
BRAIN_CONTRACT_UNCHANGED: PASS
EXECUTOR_CONTRACT_UNCHANGED: PASS
LEASE_CONTRACT_UNCHANGED: PASS
STABLE_FAILOVER_UNCHANGED: PASS
HOT_HANDOFF_UNCHANGED: PASS
BRIDGE_AUTHORIZATION_UNCHANGED: PASS
M11_API_ESCAPE_HATCH_NOT_IMPLEMENTED: PASS
```

## Full Repository Test Gate

Bridge publication executed:

```text
.\venv\Scripts\python.exe -m pytest tests/ -q
927 passed, 4 skipped, 1533 warnings in 127.23s
exit code 0
```

There are zero failures and no regression signal.

## Findings

```text
SEMANTIC_FINDINGS: NONE
SECURITY_AUTHORITY_FINDINGS: NONE
SCOPE_FINDINGS: NONE
DETERMINISM_FINDINGS: NONE
```

## M10.1 Acceptance Audit

```text
PURE_DETERMINISTIC_DISPATCHER: PASS
CAPABILITY_FIRST_FILTERING: PASS
EXPLICIT_CAPACITY_SNAPSHOT_INPUT: PASS
SUBSCRIPTION_FIRST_POLICY: PASS
PAID_API_EXPLICIT_GATE: PASS
WAIT_FAIL_SAFE: PASS
CANONICAL_EVIDENCE_OUTPUT: PASS
ZERO_TOKEN_ROUTING: PASS
HUMAN_RUN_FIX_MERGE_AUTHORITY: PASS
FULL_REPO_TESTS: PASS
REGRESSIONS: 0
M10_1: PASS
M10_2_PROVEN: NO
M10_3_PROVEN: NO
M11_PROVEN: NO
FINAL_INDEPENDENT_AUDIT: PASS
```

## Final Decision

TASK-037 satisfies ADR-026 and the locked implementation blueprint.

```text
STATUS: PASS
APPROVED: YES
READY_FOR_HUMAN_MERGE: YES
MERGE_AUTHORIZED: NO
```

Human may authorize merge. M10.2 runtime capacity snapshot / Bridge recommendation integration remains a separate future task.