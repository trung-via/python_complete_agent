# ADR-018 — AIOS Continuity M4 Executor-Neutral Contract Lock

STATUS: LOCKED

## Context

ADR-010 Open Multi-Agent Continuity OS requires execution/coding agents to become interchangeable behind a vendor-neutral contract before any Executor Lease or Executor Failover milestone is attempted.

M1–M3 are now complete:
- M1 Canonical Project State;
- M2 Brain-Neutral Contract;
- M3A deterministic Brain failover contract/harness;
- M3B real ChatGPT Chat -> Claude Chat continuity proof.

The current repository still has no canonical Executor-neutral request/result/capability contract. Antigravity remains the only Executor proven by the existing Bridge workflow. `src/aios_bridge/continuity/usage.py` contains `ExecutorAction(RUN, FIX)` only as usage/telemetry vocabulary; it is not an execution authority or adapter contract.

M4 must establish a deterministic execution boundary without silently implementing M5 Lease, M6 Executor Failover, M10 dispatch, vendor adapters, transports, or new authority.

This ADR is required because the M4 data model and adapter boundary are reusable architecture invariants for every later Executor milestone.

---

## Decision 1 — M4 Scope

M4 SHALL introduce a vendor-neutral Executor contract under:

```text
src/aios_bridge/continuity/executor.py
```

The contract SHALL formalize, at minimum:
- `ExecutionOperation`;
- `ExecutionCapability`;
- `ExecutionRequest`;
- `ExecutionResultStatus`;
- `ExecutionResult`;
- `ExecutorCapabilities`;
- `PreparedExecution` (or an equivalently small request-binding preparation record if required by the adapter Protocol);
- `ExecutorAdapter` Protocol;
- pure deterministic validators for capability eligibility, canonical-state anchoring, and request/result binding.

M4 SHALL NOT create a concrete Antigravity/Codex/Claude-Code adapter.

---

## Decision 2 — Execution Operations Are RUN / FIX Only

The canonical execution-operation domain for M4 is:

```text
RUN
FIX
```

`MERGE` MUST NOT be an Executor operation.

Human MERGE authority remains outside Executor contracts.

`ExecutionOperation` is an operational contract concept. Existing `usage.ExecutorAction` remains telemetry vocabulary and SHALL NOT become an authority dependency. M4 SHOULD NOT make `executor.py` depend on `usage.py` merely to reuse the enum.

The two domains may intentionally share the values `RUN` / `FIX`; tests SHOULD protect semantic alignment without introducing a circular dependency or changing existing telemetry behavior.

---

## Decision 3 — ExecutionRequest Is Intent, Not Authorization

An `ExecutionRequest` is an immutable, bounded, content-addressed description of work presented to one candidate/active Executor.

Its existence MUST NOT grant RUN/FIX authority.

It SHALL contain enough identity to reconstruct and validate the requested stable execution boundary, including at minimum:
- schema version;
- exact `task_id`;
- exact `request_id`;
- exact `executor_id`;
- `ExecutionOperation`;
- exact canonical `ContinuityState` fingerprint;
- exact target task branch/ref identity;
- one exact content-addressed work/control artifact (`TASK` for RUN, `REVIEW` for FIX);
- bounded ordered content-addressed context references as needed;
- bounded required Executor capabilities;
- exact expected RESULT artifact path for the active task.

The contract MUST NOT contain:
- `approved=true` or an equivalent self-authorizing flag;
- API keys/tokens/cookies/auth headers;
- raw chat transcripts;
- hidden reasoning;
- unbounded prompt/instruction dumps;
- shell commands intended to bypass TASK/ADR scope;
- merge authority.

Human/Bridge authorization remains an external precondition under the existing control plane.

---

## Decision 4 — Work Artifact Role Is Exact

The request's work/control artifact is content-addressed using canonical repository identity (`path`, `ref`, `blob_sha`).

For `RUN`:

```text
work_ref.path == .ai/tasks/TASK-NNN.md
```

for the exact active `task_id`.

For `FIX`:

```text
work_ref.path == .ai/reviews/REVIEW-NNN.md
```

where `NNN` is the exact task number representation from the active `TASK-NNN` identity.

Role/path/task identity MUST be exact and delimiter-aware. Padded/case/substring aliases MUST fail closed.

`work_ref` MUST have an exact safe Git ref and exact lowercase 40-hex Git blob SHA.

---

## Decision 5 — Canonical State and Branch Anchor

Every `ExecutionRequest` SHALL carry an exact lowercase 64-hex canonical-state fingerprint.

M4 SHALL provide a pure validator equivalent to:

```python
validate_execution_request_against_state(request, state)
```

It MUST fail closed if:
- task IDs differ;
- supplied state fingerprint differs from `state.fingerprint()`;
- request target branch differs from the state's task-branch identity;
- the request's expected task-head identity, where represented, contradicts the supplied state;
- RUN work_ref does not equal the authoritative TASK artifact in state;
- FIX work_ref does not equal the authoritative REVIEW artifact in state or the state has no authoritative review;
- a request context ref overlaps an authoritative state artifact path but carries a different ref/blob;
- authoritative/context paths collide ambiguously.

This is validation only. M4 does not update `CURRENT-STATE`, the Continuity lifecycle, Git, Bridge state, or worktrees.

---

## Decision 6 — Context References Are Bounded and Content-Addressed

Executor context SHALL be artifact/reference oriented, not a transcript dump.

Every persisted/request context entry SHALL have exact:
- canonical repository-relative path;
- safe Git ref;
- lowercase 40-hex blob SHA.

Context references are ordered because the request fingerprint must preserve the exact provided context pack.

Requirements:
- bounded count;
- bounded serialization;
- no duplicate exact paths;
- no duplicate/conflicting authoritative role paths;
- no sensitive/unsafe paths under existing Continuity path policy;
- no arbitrary iterables whose iteration order may vary; construction SHALL accept only explicitly supported deterministic sequence forms and freeze/copy them internally.

Whole-repository context is not part of M4.

---

## Decision 7 — ExecutorCapabilities Are Declarative Only

`ExecutorCapabilities` SHALL be immutable, bounded, strict-schema, deterministic and descriptive.

It SHALL include:
- exact `executor_id`;
- supported execution operations;
- a bounded set of execution capability dimensions;
- optional bounded descriptive capacity metadata only where useful;
- an explicit declarative-only invariant.

Initial capability dimensions MAY include a closed set sufficient for current/future known Executor selection, such as:
- repository read/local Git;
- filesystem/workspace write;
- shell/tool execution;
- test execution;
- browser execution.

Capability declarations MUST NOT:
- authorize execution;
- acquire a lease;
- choose/rank an Executor;
- call an Executor;
- create a transport session;
- widen TASK/ADR scope.

M4 SHALL provide a pure capability validator equivalent to:

```python
validate_executor_eligibility(request, capabilities)
```

that verifies executor identity, requested operation support and all required capabilities.

---

## Decision 8 — ExecutionResult Represents a Stable Boundary

`ExecutionResult` SHALL be immutable, bounded, strict-schema, canonical and SHA-256 fingerprintable.

It SHALL include at minimum:
- schema version;
- task ID;
- request ID;
- executor ID;
- execution operation;
- result status;
- exact implementation/tested commit SHA for successful execution;
- exact RESULT artifact pointer for successful execution;
- bounded optional evidence pointers;
- bounded error code for non-success states.

M4 result statuses SHALL be a closed domain equivalent to:

```text
SUCCESS
FAILED
REJECTED
INCOMPLETE
```

Payload matrix:

### SUCCESS
- exact request/task/executor/operation identity;
- `implementation_sha` REQUIRED and exact lowercase 40-hex;
- `result_ref` REQUIRED and exact `.ai/results/RESULT-NNN.md` for the active task;
- `result_ref.ref` MUST equal the request target branch;
- `error_code` MUST be null;
- no contradictory payload.

### FAILED / REJECTED / INCOMPLETE
- exact request/task/executor/operation identity;
- `implementation_sha` MUST be null for M4 stable-boundary semantics;
- authoritative success `result_ref` MUST be null;
- bounded `error_code` REQUIRED;
- bounded evidence pointers MAY be present only as non-authoritative evidence.

This deliberately does NOT encode dirty-workspace/mid-task handoff. Hot handoff remains M9 and requires a future contract.

---

## Decision 9 — Request / Result Binding Must Be Mechanical

M4 SHALL expose a pure validator equivalent to:

```python
validate_execution_result_against_request(result, request)
```

It MUST verify exact equality of:
- schema version;
- task ID;
- request ID;
- executor ID;
- operation;
- target RESULT role/path/ref where SUCCESS;
- successful/non-success payload matrix.

A well-formed result for another request/executor/task MUST fail closed.

The result validator grants no authority and performs no I/O.

---

## Decision 10 — PreparedExecution Is a Binding Record, Not a Lease

If the adapter Protocol requires a preparation record, M4 SHALL use a small immutable `PreparedExecution` (or equivalent) containing only identity/binding metadata such as:
- schema version;
- task ID;
- request ID;
- executor ID;
- execution ID;
- request fingerprint.

It MUST NOT contain:
- lease ownership;
- authorization tokens;
- raw command bodies;
- vendor session secrets;
- workspace snapshots;
- hidden state.

`PreparedExecution` is NOT M5 Executor Lease and MUST NOT imply exclusive ownership.

---

## Decision 11 — ExecutorAdapter Is Logical and Vendor-Neutral

M4 SHALL formalize a `typing.Protocol` equivalent in spirit to ADR-010:

```python
class ExecutorAdapter(Protocol):
    @property
    def executor_id(self) -> str: ...

    def capabilities(self) -> ExecutorCapabilities: ...

    def prepare(self, request: ExecutionRequest) -> PreparedExecution: ...

    def collect_result(self, execution_id: str) -> ExecutionResult: ...
```

The Protocol itself does not execute anything.

M4 SHALL NOT add:
- `if executor == "antigravity"` / `codex` / `claude-code` branching in Continuity Core;
- a concrete adapter implementation;
- transport commands;
- automatic invocation;
- fallback/routing.

Tests SHALL use neutral stub identities such as `executor-a`, `executor-b`, `executor-c`.

A third compatible stub Executor MUST be representable without changing the Continuity contract.

---

## Decision 12 — Adapter and Transport Remain Separate

M4 does NOT implement `ExecutionTransport`.

No CLI, cloud, handoff, shell, browser, RPC, MCP, websocket, HTTP or product-specific transport behavior belongs in `executor.py`.

Later integration may combine:

```text
ExecutorAdapter + ExecutionTransport
```

but transport selection is not part of the M4 canonical request/result contract.

---

## Decision 13 — Strict Canonicalization and Determinism

All externally supplied identity fields SHALL be exact-canonical, not merely valid after trimming.

At minimum:
- task IDs exact `TASK-<digits>` case-sensitive;
- executor/request/execution IDs exact conservative lowercase actor/request identifiers;
- branch/ref exact safe Git refs;
- Git blob/commit SHAs exact lowercase 40-hex;
- state fingerprints exact lowercase 64-hex;
- paths exact canonical safe repository-relative paths;
- duplicate set-like capability values fail closed or are deterministically canonicalized under one documented rule;
- ordered context remains ordered;
- list/tuple inputs copied/frozen; unordered/generator inputs rejected where they could create nondeterminism.

All canonical records SHALL:
- reject unknown fields;
- have deterministic `to_dict` / canonical JSON;
- support bounded `from_dict` / `from_json` where persisted/external parsing is expected;
- enforce the existing 16 KiB `MAX_SERIALIZED_BYTES` limit;
- be SHA-256 fingerprintable where they represent canonical handoff identity.

Do not weaken generic `state.py` validators to satisfy M4. Prefer Executor-local exact-boundary wrappers.

---

## Decision 14 — Evidence and Secret Hygiene

Executor-neutral canonical records MUST NOT persist:
- source code bodies;
- shell command transcripts;
- terminal output dumps;
- chat transcripts;
- hidden reasoning;
- credentials;
- environment-variable values;
- cookies/session tokens;
- API keys/auth headers;
- unrestricted vendor metadata.

Detailed code/test evidence remains in bounded RESULT/evidence artifacts referenced by content identity rather than embedded into the M4 canonical request/result objects.

---

## Decision 15 — Existing Authority and Bridge Semantics Remain Locked

M4 changes no current authority.

After M4:
- Antigravity remains the currently proven sole Executor in the existing workflow;
- Human RUN authorization remains mandatory;
- Human FIX authorization remains mandatory;
- Human MERGE authorization remains mandatory;
- `bridge.py` v0.4 handoff/sync/authorization/publish behavior remains unchanged;
- no Codex/Claude Code execution authority is granted merely because they can be described by the new contract;
- no automatic Executor switch is enabled.

M4 creates vocabulary/validation for future portability, not a new control plane.

---

## Decision 16 — No Executor Lease or Failover Yet

M4 MUST NOT implement:
- lease acquisition/release;
- `MAX_ACTIVE_EXECUTORS_PER_TASK` enforcement runtime;
- executor failover;
- dirty-workspace handoff;
- concurrency;
- stable-boundary replacement execution;
- transport switching.

Those belong to M5/M6 and later milestones.

M4 MAY structure request/result identities so those later contracts can bind to them without redesigning M4.

---

## Decision 17 — Compatibility with Existing Continuity Modules

M4 SHOULD reuse existing safe foundational types/validators where semantically correct, especially:
- `SCHEMA_VERSION`;
- `MAX_SERIALIZED_BYTES`;
- `ArtifactRef`;
- `ContinuityState`;
- exact SHA/ref/path validators.

M4 MUST NOT mutate Brain-neutral semantics to make Executor-neutral semantics fit.

`brain.py` and `executor.py` are sibling contracts with different authority roles.

`usage.py` remains telemetry and SHALL NOT become an execution dependency.

`state.py` lifecycle remains unchanged.

---

## Decision 18 — Required Proof/Test Matrix

M4 tests SHALL be deterministic and zero-execution.

Required positive proof:
- valid RUN request;
- valid FIX request with authoritative REVIEW;
- state-anchor validation;
- capability eligibility validation;
- valid SUCCESS result binding;
- valid non-success result binding;
- canonical serialization/fingerprints;
- neutral `ExecutorAdapter` stub conformance;
- a third neutral stub can conform without core modification.

Required negative/adversarial proof includes at minimum:
- padded/noncanonical task/request/executor/execution IDs;
- malformed/uppercase/padded SHA/fingerprint/ref/path identity;
- RUN pointing to REVIEW or FIX pointing to TASK;
- wrong task token / substring alias;
- stale state fingerprint;
- wrong target branch;
- context duplicate/path collision;
- authoritative state artifact blob/ref mismatch;
- unordered/generator sequence nondeterminism;
- duplicate required/supported capabilities;
- wrong executor capability identity;
- unsupported RUN/FIX operation;
- missing required capability;
- MERGE or unknown operation rejection;
- SUCCESS missing implementation SHA/result ref;
- SUCCESS carrying error code;
- non-success carrying authoritative result ref/implementation SHA;
- result request/task/executor/operation drift;
- result path/ref mismatch;
- unknown-field schema drift;
- >16 KiB request/result/capability input;
- proof that no filesystem, subprocess, Git mutation, model/provider or Bridge call occurs.

Existing Continuity, Bridge and full repository suites SHALL remain green.

---

## Decision 19 — Expected Implementation Boundary

Expected production changes for M4 are narrowly bounded to:

```text
src/aios_bridge/continuity/executor.py          # new
src/aios_bridge/continuity/__init__.py          # public exports only
```

Expected tests:

```text
tests/aios_bridge/continuity/test_executor.py   # new
```

Changes to `state.py`, `brain.py`, `failover.py`, `usage.py`, Bridge, providers, runtime Executor code, authorization or lifecycle are NOT expected.

If implementation requires such a change, STOP and escalate before widening scope.

---

## Acceptance Criteria

M4 is complete only when:

1. vendor-neutral ExecutionRequest/Result/Capabilities contracts exist and are strict, bounded, deterministic and fingerprintable;
2. requests are anchored to canonical state/content identities without becoming authorization tokens;
3. capability eligibility is pure and fail-closed;
4. request/result identity and payload binding is mechanically validated;
5. ExecutorAdapter Protocol is vendor-neutral and transport-neutral;
6. no concrete alternate Executor is activated;
7. no lease/failover/router/transport is introduced;
8. no Bridge/authority/lifecycle semantics change;
9. neutral second/third Executor stubs can satisfy the contract without core changes;
10. all focused Continuity, Bridge and full repository tests pass;
11. ADR-017 Full Semantic Review and Final Independent Audit both pass before APPROVED;
12. Human MERGE remains a separate explicit action.

---

## Relationship to Roadmap

After M4 is merged, the next intended milestone is:

```text
M5 — Executor Lease
```

M5 may bind exclusive ownership to M4 request/execution identities, but MUST NOT retroactively redefine M4 request existence as authorization.

M6 may later prove stable-boundary Executor failover using M4 request/result contracts + M5 lease semantics.
