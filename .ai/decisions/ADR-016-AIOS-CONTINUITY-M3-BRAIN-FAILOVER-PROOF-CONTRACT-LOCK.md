# ADR-016 — AIOS Continuity M3 Brain Failover Proof Contract Lock

STATUS: LOCKED

## Context

ADR-010 requires stable-boundary Brain failover across interchangeable Brain surfaces without relying on prior chat history or hidden reasoning. TASK-021/M2 now provides the vendor-neutral `BrainRequest`, `BrainResult`, `BrainCapability`, bounded context references, deterministic serialization/fingerprints, and strict output-role validation needed to build that proof.

M3 must prove continuity, not merely add a router or rename a Brain ID. It must also avoid claiming a real cross-Brain proof from mocks alone.

## Decision 1 — M3 Is Split Into Contract/Harness Then Real Proof

M3 SHALL be completed in two steps:

1. **M3A — deterministic failover contract + proof harness**: implemented by TASK-022 with no live Brain invocation.
2. **M3B — real cross-chat Brain proof**: performed only after M3A is merged, using two distinct compliant Brain surfaces against the same canonical task-state snapshot.

M3 is NOT considered complete until M3B succeeds.

TASK-022 therefore proves the mechanics and invariants of failover, not the availability or behavior of any specific chat product.

## Decision 2 — Stable-Boundary Failover Unit

The failover unit is one pending advisory Brain operation represented by:

- an immutable `BrainRequest`;
- a canonical `ContinuityState` fingerprint/snapshot identity;
- bounded artifact/context references already carried by the request;
- optional non-success source `BrainResult` evidence.

A replacement Brain restarts the pending operation from canonical inputs. Prior transient reasoning is not transferred.

No dirty transcript, hidden reasoning, raw prompt/response body, session cookie, API token, or chat-memory dump is part of the failover contract.

## Decision 3 — Replacement Request Equivalence

A replacement request MUST preserve the operation semantics of the source request.

The following MUST remain identical:

- schema version;
- task ID;
- Brain operation;
- objective/instruction;
- ordered bounded context refs and their blob identities;
- output contract;
- canonical state fingerprint supplied to the failover proof.

Only these request identity fields may change for failover:

- `brain_id`;
- `request_id`.

The replacement `brain_id` MUST differ from the source `brain_id`.

Any mutation of task, operation, objective, context refs, output role/path, or canonical state identity is a new request/operation and MUST NOT be accepted as equivalent failover.

## Decision 4 — Capability Gate Is Descriptive and Deterministic

Before a replacement request is considered eligible, a supplied `BrainCapability` for the replacement Brain MUST:

- have the same `brain_id` as the replacement request;
- declare support for the pending operation.

Capability checking is a pure eligibility gate only.

It MUST NOT:

- choose a vendor;
- rank Brains;
- invoke a Brain;
- authorize RUN/FIX/MERGE;
- trigger automatic fallback.

## Decision 5 — No Competing Successful Outputs

Failover of the same pending operation is permitted only when there is no authoritative successful source result for that operation.

If the source Brain has already produced a `BrainResult(status=SUCCESS)` for the source request, replacement execution of the same operation MUST be rejected as failover. A subsequent reasoning round must use a new explicitly-scoped request/round instead.

A missing source result or a source result with `REJECTED`, `FAILED`, or `INCOMPLETE` MAY be eligible for failover, subject to all other invariants.

This rule prevents two Brains from creating competing authoritative outputs for one logical operation.

## Decision 6 — Canonical State Anchor

Failover proof MUST be anchored to a deterministic `ContinuityState.fingerprint()` and matching `task_id`.

The proof MUST fail closed if:

- the state task does not match the Brain request task;
- the supplied state fingerprint is malformed or does not equal the actual canonical state fingerprint;
- the replacement proof refers to a different state snapshot.

TASK-022 SHALL NOT change the existing Continuity lifecycle/state machine or Bridge lifecycle semantics.

## Decision 7 — Failover Proof Record

M3A SHALL introduce a small immutable vendor-neutral proof/record equivalent to:

- schema version;
- task ID;
- operation;
- canonical state fingerprint;
- source Brain ID;
- source request fingerprint;
- source result status or null;
- replacement Brain ID;
- replacement request fingerprint;
- deterministic proof status/validation outcome metadata as needed.

The record MUST be bounded, strict-schema, canonically serialized, SHA-256 fingerprintable, and subject to the existing 16 KiB Continuity limit.

The record MUST NOT persist raw Brain output, transcript, hidden reasoning, secrets, vendor session data, or authority tokens.

## Decision 8 — Pure Failover Builder/Validator

M3A MAY expose pure helpers equivalent to:

- build a replacement `BrainRequest` from a source request + replacement Brain identity/request identity;
- validate source/replacement semantic equivalence;
- validate capability compatibility;
- validate state anchoring;
- create/validate a deterministic failover proof record.

These helpers MUST have zero provider calls, zero filesystem writes, zero Bridge calls, zero Git mutation, zero shell/browser execution, and zero model turns.

## Decision 9 — Vendor Neutrality

Continuity Core MUST NOT branch on names such as `chatgpt`, `claude`, `gemini`, `minimax`, or any future vendor.

Tests may use neutral fixture IDs such as `brain-a` and `brain-b`.

The later M3B real proof MAY record the actual Brain IDs used, but no vendor-specific behavior may enter Continuity Core.

## Decision 10 — M3B Real Cross-Chat Proof

After TASK-022 is merged, a separate bounded proof SHALL use two distinct compliant Brain surfaces.

The real proof SHALL demonstrate:

1. Brain A receives/reconstructs a pending operation from the canonical snapshot;
2. Brain A is treated as unavailable/non-success at a stable boundary;
3. Brain B receives an equivalent replacement request tied to the exact same canonical snapshot;
4. Brain B produces a valid bounded result/artifact pointer;
5. no prior Brain transcript or hidden reasoning is required;
6. no Brain gains execution or merge authority.

The specific alternate Brain is deployment/user choice. M3B MUST NOT require a particular vendor or paid API.

Human-triggered interaction is allowed. Chat-web UI automation is prohibited.

## Decision 11 — Authority Remains Unchanged

Nothing in M3 grants execution authority.

- Brain output remains advisory/control-artifact oriented.
- Antigravity remains the sole implemented Executor under the current Bridge workflow.
- Human RUN approval remains mandatory.
- Human FIX approval remains mandatory.
- Human MERGE approval remains mandatory.
- `bridge.py` v0.4 handoff/sync/authorization/publish semantics remain unchanged.

## Decision 12 — Workload Allocation

TASK-022 is `L3 — ARCHITECTURE / HIGH-RISK`.

Under ADR-015:

- ChatGPT owns this architecture/contract and final semantic/security review;
- Antigravity owns detailed repository inspection, implementation planning, code, tests, and self-audit;
- no separate ChatGPT implementation PLAN is required by default;
- deterministic evidence/telemetry should be generated mechanically where possible.

## Non-Goals

TASK-022/M3A MUST NOT implement:

- automatic Brain selection or ranking;
- router/fallback orchestration;
- live ChatGPT/Claude/Gemini/MiniMax invocation;
- chat UI automation;
- External Brain provider changes;
- ExecutorAdapter or Executor Lease;
- executor failover;
- Bridge lifecycle/authorization changes;
- source-code execution from Brain results;
- a claim that M3 is complete before M3B real proof.

## Acceptance Criteria

ADR-016 is satisfied when:

1. M3A can deterministically derive and validate an equivalent replacement Brain request from canonical inputs.
2. Semantic drift across failover fails closed.
3. same-Brain pseudo-failover fails closed.
4. unsupported replacement capability fails closed.
5. successful source-result duplication fails closed.
6. state/task/fingerprint mismatch fails closed.
7. proof records are bounded, deterministic, strict-schema and contain no transcript/reasoning/secrets/authority.
8. zero model/API calls are needed for M3A mechanics.
9. existing Continuity/Bridge/full tests remain green.
10. M3 remains explicitly incomplete until a later real two-Brain proof succeeds.
