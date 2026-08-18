# ADR-029 — E1 Executor Invocation Contract Lock

STATUS: LOCKED

## Context

M4 intentionally separated the logical `ExecutorAdapter` contract from transport. ADR-018 Decision 12 states that M4 does not implement `ExecutionTransport`, and later integration may combine `ExecutorAdapter + ExecutionTransport` without changing the M4 request/result contract.

M10 is now complete. AIOS can deterministically recommend a compatible Executor, preserve Human RUN/FIX authority, bind an active ExecutorLease, and prove a real Codex selection. The remaining operator friction is the physical invocation boundary: after approval, the Human still launches/pastes instructions into the selected Executor manually.

E-Series exists to remove that transport friction without weakening authority:

```text
E1 — Executor Invocation Contract
E2 — Codex Local Transport
E3 — Bounded Context Pack Delivery
E4 — Result Collection + Auto Publication
E5 — Zero-Copy/Paste Operational Proof
```

The existing H-Series backlog remains separate and DEFERRED:

```text
H1 Event Journal
H2 Capability Seams
H3 Execution Envelope
H4 Provider Lifecycle
H5 Driver Contract
TRIGGER: evidence from real Python Agent workloads
```

E1 MUST NOT pre-implement or rename any H-Series item.

---

## Decision 1 — E1 Is Pure Contract Only

E1 SHALL introduce the transport-neutral invocation boundary under:

```text
src/aios_bridge/continuity/executor_transport.py
```

E1 SHALL define only immutable canonical records, a vendor-neutral transport Protocol, and pure validators.

E1 MUST NOT:
- invoke Codex, Antigravity, Claude Code, any model, provider, or API;
- call `subprocess`, shell, browser, network, Git, filesystem mutation, Bridge commands, or runtime stores;
- authorize RUN/FIX/MERGE;
- acquire/release ExecutorLease;
- change deterministic dispatch;
- build the E3 context pack;
- collect canonical M4 `ExecutionResult`;
- publish RESULT, commit, push, or merge.

Concrete invocation begins only in E2.

---

## Decision 2 — Preserve M4 Adapter / Transport Separation

E1 SHALL NOT redefine `ExecutorAdapter` or M4 request/result semantics.

Existing M4 flow remains:

```text
ExecutionRequest
    -> ExecutorAdapter.prepare(...)
    -> PreparedExecution
```

E1 adds the orthogonal transport boundary:

```text
PreparedExecution + active execution binding + bounded payload identity
    -> ExecutionTransport.invoke(...)
    -> InvocationReceipt
```

Later E4 may use `ExecutorAdapter.collect_result(...)` after transport completion.

`InvocationReceipt` is transport evidence only and MUST NOT be treated as an `ExecutionResult`.

---

## Decision 3 — Canonical ExecutorInvocation

E1 SHALL define an immutable, strict-schema, bounded, SHA-256-fingerprintable `ExecutorInvocation` record containing exactly the transport-neutral identity required to invoke one already-selected Executor.

Required semantic fields:

```text
schema_version
invocation_id
task_id
request_id
executor_id
transport_id
operation
workspace_id
target_branch
execution_id
request_fingerprint
prepared_execution_fingerprint
lease_fingerprint
execution_fingerprint
payload_sha256
payload_size_bytes
```

Requirements:
- `task_id` exact case-sensitive `TASK-<digits>`;
- invocation/request/execution/executor/transport IDs exact canonical conservative lowercase IDs, bounded length, no whitespace normalization;
- operation exact M4 `RUN` or `FIX`; MERGE rejected;
- workspace/request/prepared/lease/execution/payload fingerprints exact lowercase 64-hex SHA-256;
- target branch exact safe Git ref;
- `payload_size_bytes` exact positive int, bool rejected;
- hard safety ceiling `MAX_INVOCATION_PAYLOAD_BYTES = 1_048_576`;
- unknown fields rejected;
- deterministic canonical JSON and fingerprint;
- > existing `MAX_SERIALIZED_BYTES` canonical-record size rejected.

The 1 MiB limit is a transport safety ceiling only. E3 SHALL define a much tighter operational context budget based on bounded task context. E1 does not decide token budgeting.

---

## Decision 4 — Invocation Is Not Authorization

`ExecutorInvocation` MUST NOT contain or accept:

```text
approved
human_approved
authorization_token
merge_allowed
api_key
token
cookie/cookies
auth/auth_header
session_secret
```

Its existence grants no RUN/FIX authority.

A future runtime caller may invoke a transport only after independently establishing all of the following:

```text
exact ACTIVE Human-authorized RUN/FIX record
+ exact selected executor identity
+ exact active ExecutorLease
+ exact authorized artifact binding
+ exact current workspace/branch binding
```

E1 itself does not read Bridge authorization state. E4 Bridge integration SHALL mechanically enforce this runtime precondition before invoking any transport.

A dispatcher recommendation alone MUST NEVER satisfy the invocation authority precondition.

---

## Decision 5 — Mechanical Binding to Existing M4/M5 Contracts

E1 SHALL expose a pure validator equivalent to:

```python
validate_executor_invocation(
    invocation,
    execution_request,
    prepared_execution,
    executor_lease,
)
```

It MUST reuse existing M4/M5 validators where semantically correct and fail closed unless:
- invocation task/request/executor/operation identities equal the `ExecutionRequest`;
- invocation target branch equals the request target branch;
- invocation request fingerprint equals `ExecutionRequest.fingerprint()`;
- `PreparedExecution` mechanically validates against the exact request;
- invocation execution ID equals `PreparedExecution.execution_id`;
- invocation prepared fingerprint equals `PreparedExecution.fingerprint()`;
- invocation task/executor/operation/workspace/execution fingerprint equal the exact ExecutorLease;
- invocation lease fingerprint equals `ExecutorLease.fingerprint()`.

A valid lease for another task, workspace, executor, operation, or execution fingerprint MUST fail closed.

E1 MUST NOT reinterpret `ExecutorLease` as Human authorization. Lease binding and Human authorization remain distinct invariants.

---

## Decision 6 — Payload Is Runtime Bytes, Canonical Record Stores Identity Only

E1 canonical records MUST NOT embed prompt/context bytes.

`ExecutorInvocation` stores only:

```text
payload_sha256
payload_size_bytes
```

E1 SHALL expose a pure helper equivalent to:

```python
validate_invocation_payload(invocation, payload_bytes)
```

Required behavior:
- payload must be `bytes` exactly; bytearray/string/generator rejected;
- payload must be non-empty;
- payload length must equal `payload_size_bytes` exactly;
- payload length must not exceed `MAX_INVOCATION_PAYLOAD_BYTES`;
- SHA-256 of exact bytes must equal `payload_sha256`;
- a one-byte payload mutation must fail closed.

E1 does not define prompt composition. E3 will create bounded, content-addressed payload bytes.

---

## Decision 7 — Transport-Level Invocation Status Domain

E1 SHALL define a closed `InvocationStatus` domain:

```text
EXITED_ZERO
EXITED_NONZERO
FAILED_TO_START
TIMED_OUT
INTERRUPTED
```

These statuses describe transport/process mechanics only.

`EXITED_ZERO` MUST NOT mean task success, review PASS, publication success, or merge approval.

---

## Decision 8 — Canonical InvocationReceipt

E1 SHALL define immutable, strict-schema, bounded, fingerprintable `InvocationReceipt` with exact identity binding to one invocation.

Required fields:

```text
schema_version
invocation_id
task_id
request_id
executor_id
transport_id
operation
execution_id
invocation_fingerprint
status
exit_code
error_code
```

Payload matrix:

### EXITED_ZERO
- `exit_code == 0` exactly;
- `error_code is None`.

### EXITED_NONZERO
- `exit_code` exact non-zero int, bool rejected;
- bounded canonical `error_code` required.

### FAILED_TO_START / TIMED_OUT / INTERRUPTED
- `exit_code is None`;
- bounded canonical `error_code` required.

Receipt MUST NOT contain:
- stdout/stderr bodies;
- prompt/context bytes;
- source code;
- credentials/environment values;
- implementation commit SHA;
- RESULT artifact;
- approval/lease ownership fields;
- merge authority.

Detailed transport logs, if later required, belong in bounded external runtime evidence and are not E1 canonical records.

---

## Decision 9 — Receipt / Invocation Binding Is Mechanical

E1 SHALL expose a pure validator equivalent to:

```python
validate_invocation_receipt(receipt, invocation)
```

It MUST verify exact equality of:
- schema version;
- invocation ID;
- task ID;
- request ID;
- executor ID;
- transport ID;
- operation;
- execution ID;
- `invocation_fingerprint == invocation.fingerprint()`;
- valid status payload matrix.

A receipt from another invocation/executor/transport/task/request MUST fail closed.

---

## Decision 10 — Vendor-Neutral ExecutionTransport Protocol

E1 SHALL define a runtime-checkable Protocol equivalent in spirit to:

```python
class ExecutionTransport(Protocol):
    @property
    def transport_id(self) -> str: ...

    @property
    def executor_id(self) -> str: ...

    def invoke(self, invocation: ExecutorInvocation, payload: bytes) -> InvocationReceipt: ...
```

E1 SHALL also expose a pure identity validator equivalent to:

```python
validate_transport_binding(transport, invocation)
```

which requires exact `transport_id` and `executor_id` equality before invocation.

The Protocol itself SHALL NOT execute anything. E1 tests use neutral stubs only.

No `if executor == "codex"` or provider-specific logic belongs in Continuity Core.

---

## Decision 11 — Sync Invocation Semantics for E-Series v1

E1 defines one synchronous `invoke(...) -> InvocationReceipt` contract.

This is sufficient for E2 Codex local-process transport and keeps lifecycle complexity bounded.

E1 does NOT introduce:
- detached sessions;
- background workers;
- process handles;
- callbacks/webhooks;
- retries;
- streaming stdout/stderr;
- cancellation orchestration;
- provider lifecycle abstractions.

If real workload evidence later requires richer async/provider lifecycle behavior, that evidence may trigger the separate deferred H-Series rather than silently expanding E1.

---

## Decision 12 — E-Series / H-Series Boundary Is Locked

E1–E5 solve operator transport automation only.

They MUST NOT opportunistically implement the DEFERRED H-Series:
- no Event Journal framework;
- no new generic Capability Seam architecture;
- no generic Execution Envelope;
- no Provider Lifecycle manager;
- no generic Driver Contract.

A concrete `ExecutionTransport` is not H5 Driver Contract. It is the narrowly scoped transport seam explicitly reserved by ADR-018.

---

## Decision 13 — Existing M10 / Authority Semantics Remain Unchanged

E1 changes none of:
- M10 deterministic ranking;
- runtime capacity records;
- Bridge recommendation behavior;
- Human RUN authority;
- Human FIX authority;
- Human MERGE authority;
- M5 lease semantics;
- M6 stable failover;
- M9 hot handoff;
- M11 API escape hatch.

E1 MUST NOT modify `bridge.py`.

---

## Decision 14 — Required Test / Adversarial Matrix

Required positive tests:
- canonical RUN invocation;
- canonical FIX invocation;
- invocation binds exact `ExecutionRequest` + `PreparedExecution` + `ExecutorLease`;
- exact payload byte validation;
- every valid InvocationReceipt status matrix;
- deterministic serialization/fingerprints;
- neutral `ExecutionTransport` stub conformance;
- a second/third neutral transport/executor can conform without core modification.

Required negative tests include at minimum:
- noncanonical/padded IDs;
- MERGE/unknown operation;
- malformed workspace/request/prepared/lease/execution/payload fingerprints;
- invalid branch;
- zero/negative/bool/oversized payload size;
- request/task/executor/operation/branch drift;
- prepared execution mismatch;
- lease task/workspace/executor/operation/execution-fingerprint mismatch;
- lease fingerprint mismatch;
- payload non-bytes, length mismatch, hash mismatch, one-byte tamper;
- transport executor/transport ID mismatch;
- receipt invocation/task/request/executor/transport/operation/execution drift;
- receipt invocation fingerprint mismatch;
- EXITED_ZERO with non-zero/None exit code or error code;
- EXITED_NONZERO with zero/None exit code or missing error code;
- failure status carrying exit code or missing error code;
- unknown canonical fields;
- authority/secret fields rejected;
- >16 KiB canonical record input;
- proof that `executor_transport.py` performs no filesystem, subprocess, Git, network, Bridge, provider/model, lease-store, dispatch, or authorization I/O.

Full repository suite remains required at Bridge publication.

---

## Decision 15 — Expected Implementation Boundary

Allowed production files for E1:

```text
src/aios_bridge/continuity/executor_transport.py
src/aios_bridge/continuity/__init__.py
```

Expected tests:

```text
tests/aios_bridge/continuity/test_executor_transport.py
```

Bridge publication may generate:

```text
.ai/results/RESULT-040.md
```

No other production path is expected.

If implementation appears to require changes to `executor.py`, `lease.py`, `dispatch.py`, runtime stores, `bridge.py`, provider code, or H-Series abstractions, STOP and escalate rather than widen scope.

---

## E1 Acceptance

E1 is complete only when:

```text
EXECUTOR_INVOCATION_CANONICAL: PASS
PAYLOAD_BYTE_IDENTITY: PASS
M4_REQUEST_PREPARED_BINDING: PASS
M5_LEASE_BINDING: PASS
INVOCATION_IS_NOT_AUTHORIZATION: PASS
INVOCATION_RECEIPT_TRANSPORT_ONLY: PASS
EXECUTION_TRANSPORT_PROTOCOL: PASS
VENDOR_NEUTRAL: PASS
ZERO_REAL_INVOCATION: PASS
M10_UNCHANGED: PASS
BRIDGE_AUTHORITY_UNCHANGED: PASS
H_SERIES_REMAINS_DEFERRED: PASS
FULL_REPO_TESTS: PASS
REGRESSIONS: 0
FINAL_INDEPENDENT_AUDIT: PASS
```

After E1 merges, E2 may implement the first concrete transport:

```text
CodexLocalTransport
```

E2 still may not remove Human RUN/FIX authority.