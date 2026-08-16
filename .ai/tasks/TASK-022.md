# TASK-022 — Open Multi-Agent Continuity OS M3A Brain Failover Contract & Proof Harness

## Work Class

`L3 — ARCHITECTURE / HIGH-RISK`

ChatGPT owns the locked M3 failover contract and final review. Antigravity owns detailed implementation planning, repository inspection, code, tests, and self-audit under ADR-015 and ADR-016.

No separate ChatGPT implementation PLAN is required.

## Baseline

Current canonical `main` at authoring:

```text
4978e426f3445c086c017c07c844943ac841e4de
```

M1 Canonical Project State, M1.5 Usage Telemetry, and M2 Brain-Neutral Contract are merged.

## Governing Contracts

- ADR-010 — Open Multi-Agent Continuity OS Architecture Lock
- ADR-011 — Canonical Project State Contract
- ADR-013 — Delta-First Brain Context Budget
- ADR-014 — Usage & Efficiency Telemetry
- ADR-015 — Balanced Brain / Executor Workload Policy
- ADR-016 — M3 Brain Failover Proof Contract Lock

## Objective

Implement **M3A: deterministic Brain failover contract and proof harness** under Continuity Core.

The implementation must prove that one pending neutral Brain operation can be transferred from one Brain identity to a different compatible Brain identity while preserving the exact canonical task semantics and state snapshot.

This task does **not** perform a live cross-chat failover and MUST NOT claim M3 complete. A separate M3B real two-Brain proof follows after TASK-022 is merged.

## Preferred Scope

Preferred new module:

```text
src/aios_bridge/continuity/failover.py
```

Expected tests:

```text
tests/aios_bridge/continuity/test_failover.py
```

`src/aios_bridge/continuity/__init__.py` may export the new public contract types/helpers.

Antigravity may choose a smaller file arrangement if it preserves the locked contract and explains the choice in RESULT.

## Required Concepts

Implement immutable/bounded concepts equivalent to:

```text
BrainFailoverProof / BrainFailoverRecord
replacement-request builder
semantic-equivalence validator
replacement capability validator
canonical-state anchor validator
```

Exact names are implementation detail. Do not duplicate existing M2 types when reuse is semantically correct.

## Replacement Request Contract

Given:

```text
source BrainRequest
replacement brain_id
replacement request_id
```

a pure helper SHOULD be able to derive a replacement `BrainRequest` that preserves all failover-critical semantics.

Only these fields may differ from the source request:

```text
brain_id
request_id
```

The following MUST remain identical:

```text
schema_version
task_id
operation
objective
context_refs in canonical order
output_contract
```

The replacement `brain_id` MUST differ from the source `brain_id`.

Fail closed on any semantic drift.

## Capability Eligibility Contract

A replacement `BrainCapability` MUST:

- belong to the replacement `brain_id`;
- support the request operation;
- remain declarative-only under M2.

No ranking, preference, automatic selection, fallback, or invocation.

## Source Result / Duplicate Output Contract

The failover validator SHALL support:

```text
source_result = null
source_result.status = REJECTED | FAILED | INCOMPLETE
```

for eligible failover when all other invariants pass.

If a matching source request already has:

```text
source_result.status = SUCCESS
```

then same-operation failover MUST fail closed to prevent competing authoritative outputs.

Also reject source-result identity mismatches such as wrong task/request/brain/operation relative to the source request.

## Canonical State Anchor

Failover MUST be bound to a `ContinuityState` snapshot.

At minimum validate:

- state.task_id == source_request.task_id == replacement_request.task_id;
- caller/proof state fingerprint exactly equals `ContinuityState.fingerprint()`;
- fingerprint is exact lowercase 64-char SHA-256 hex;
- replacement proof cannot silently point to a different canonical snapshot.

Do not change `ContinuityState` lifecycle semantics in this task.

## Failover Proof Record

Create a deterministic bounded record carrying only metadata required to audit the handoff, equivalent to:

```text
schema_version
task_id
operation
state_fingerprint
source_brain_id
source_request_fingerprint
source_result_status | null
replacement_brain_id
replacement_request_fingerprint
```

Additional tiny deterministic fields are acceptable only if needed for validation/audit.

Requirements:

- immutable;
- strict unknown-field rejection;
- canonical JSON;
- deterministic SHA-256 fingerprint;
- existing Continuity 16 KiB fail-closed limit;
- no raw prompt/response body;
- no transcript;
- no hidden reasoning;
- no secrets/session data;
- no RUN/FIX/MERGE authorization;
- no arbitrary free-form persistence field.

## Pure Mechanics Only

TASK-022 mechanics MUST be pure and side-effect free.

Do NOT:

- call any Brain/model/provider;
- call MiniMax/OpenAI/Claude/Gemini APIs;
- automate a chat UI;
- write files from the failover helper itself;
- mutate Git;
- invoke Bridge commands;
- run shell/browser actions from the contract;
- alter authorization state.

Tests may construct in-memory canonical fixtures.

## Vendor Neutrality

Continuity Core must not contain branches keyed on vendor names.

Use neutral test fixture identities such as:

```text
brain-a
brain-b
```

Do not hard-code preferred Brain ordering in M3A.

## Executor Planning Requirement

After `/aios-worker RUN TASK-022`, Antigravity SHALL create its own bounded implementation plan before editing code.

The plan SHALL cover:

- exact types/helpers to add or reuse;
- state/request/result identity relationships;
- semantic-equivalence rules;
- strict serialization/fingerprint validation;
- focused negative-test matrix;
- proof of zero provider/Bridge/authority side effects.

If implementation appears to require widening ADR-016 or changing Bridge/state lifecycle semantics, STOP and report the conflict rather than inventing a new policy.

## Required Tests

At minimum cover:

1. valid source -> replacement request construction;
2. only `brain_id` and `request_id` differ after derivation;
3. same-Brain pseudo-failover rejected;
4. changed task ID rejected;
5. changed operation rejected;
6. changed objective rejected;
7. changed/reordered context refs rejected if canonical semantics differ;
8. changed output contract rejected;
9. replacement capability brain-ID mismatch rejected;
10. replacement capability lacking operation rejected;
11. no source result allows failover;
12. REJECTED / FAILED / INCOMPLETE source results allow failover when identities match;
13. SUCCESS source result rejects duplicate same-operation failover;
14. source-result task/request/brain/operation mismatch rejected;
15. canonical state task mismatch rejected;
16. malformed or stale/wrong state fingerprint rejected;
17. failover proof canonical JSON and fingerprint deterministic;
18. unknown proof fields rejected;
19. 16 KiB proof/input limits fail closed where applicable;
20. no transcript/reasoning/secret/authorization fields accepted;
21. neutral fixture Brain IDs prove no vendor dependency;
22. existing Continuity tests green;
23. existing Bridge tests green;
24. full repository tests green.

No live external calls.

## RESULT / Review Manifest

`RESULT-022.md` SHALL include:

```text
BASE_SHA
IMPLEMENTATION_SHA
CHANGED_FILES
TEST_SUMMARY
BRIDGE_BEHAVIOR_CHANGED
AUTHORITY_WIDENED
LIVE_EXTERNAL_CALLS
EXECUTOR_PLAN_OWNER: antigravity
CHATGPT_IMPLEMENTATION_PLAN_USED: NO
M3A_MECHANICS_PROVED: YES|NO
M3_REAL_CROSS_BRAIN_PROOF_COMPLETE: NO
```

Also include compact evidence showing:

- source and replacement request semantic equivalence is fail-closed;
- successful duplicate-output failover is blocked;
- state fingerprint anchoring is enforced;
- no vendor routing/invocation exists.

Do not invent exact provider-token counts.

## Non-Goals

Do NOT implement:

- M3B live two-chat proof;
- automatic Brain selection/router;
- subscription availability detection;
- API fallback orchestration;
- provider adapters;
- chat UI automation;
- ExecutorAdapter;
- Executor Lease;
- executor failover;
- Bridge handoff/sync/publish changes;
- canonical state lifecycle changes;
- RUN/FIX/MERGE authority changes.

## Acceptance Criteria

1. Equivalent replacement Brain request can be built deterministically from a source request.
2. Only Brain/request identity may change during failover; semantic drift fails closed.
3. replacement capability eligibility is pure and operation-based.
4. same-Brain pseudo-failover fails closed.
5. successful source result blocks competing same-operation failover.
6. source-result identity mismatches fail closed.
7. canonical state snapshot/fingerprint anchors the failover.
8. proof record is deterministic, strict, bounded and contains no raw reasoning/transcript/secrets/authority.
9. no vendor branch, Brain invocation, router, fallback, Bridge mutation, or execution authority is introduced.
10. focused Continuity, Bridge and full repository suites pass with zero regressions.
11. RESULT proves Antigravity owned detailed implementation planning and ChatGPT did not create an implementation PLAN.
12. RESULT explicitly states that real M3 cross-Brain proof is still pending after TASK-022.
