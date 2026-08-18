# REVIEW-040 — E1 Executor Invocation Contract

STATUS: PASS
APPROVED: YES
READY_FOR_HUMAN_MERGE: YES
MERGE_AUTHORIZED: NO

## Review Round

Round 1 — final independent lineage, scope, contract-purity, M4/M5 binding, payload identity, receipt semantics, transport-neutrality, authority-boundary, and regression audit.

## Authoritative Anchors

```text
TASK_ID: TASK-040
BASELINE_MAIN_SHA: b22a48b14c5fc07007caf498fedc6503656c73e6
TASK_BRANCH: ai/task-040
FINAL_TASK_HEAD_SHA: 1c35ce096f366d9d87250b5e8ae1759327dc5a51
TASK_BLOB_SHA: cf3e6012af3a86c1babaa7f901495686939c9198
ADR_029_BLOB_SHA: e041197922abc0aaa15083202919a622f21282b8
BLUEPRINT_BLOB_SHA: 566cdeb93164121097960e7669d5e631a3b8f448
RESULT_BLOB_SHA: 077878c1adce97f30f9bca20fc90c1164aba7a75
EXECUTOR_TRANSPORT_BLOB_SHA: bbe7b517202ea446e727752955e004d9464934bd
INIT_EXPORT_BLOB_SHA: 9cc32eb80fca4e53db18dc09b8b788cefbe59138
TEST_BLOB_SHA: 4a15ce638d5268574c22f2ef2bf4529290f956ac
```

Fresh branch-drift check:

```text
1c35ce096f366d9d87250b5e8ae1759327dc5a51 -> ai/task-040
STATUS: identical
AHEAD: 0
BEHIND: 0
```

## Lineage / Scope Audit

```text
COMMITS_AHEAD_OF_BASELINE: 1
COMMITS_BEHIND_BASELINE: 0
MERGE_BASE: b22a48b14c5fc07007caf498fedc6503656c73e6
CHANGED_PATHS:
  .ai/results/RESULT-040.md
  src/aios_bridge/continuity/__init__.py
  src/aios_bridge/continuity/executor_transport.py
  tests/aios_bridge/continuity/test_executor_transport.py
SCOPE_AUDIT: PASS
```

No modification to `bridge.py`, M4 `executor.py`, M5 `lease.py`, M10 dispatch/runtime dispatch, runtime lease store, failover, hot handoff, provider code, External Brain code, or H-Series abstractions.

## Contract Audit

### Canonical ExecutorInvocation

`ExecutorInvocation` is frozen, strict-schema, bounded and canonical. It contains the exact ADR-029 identity fields and stores only `payload_sha256` plus `payload_size_bytes`, never raw prompt/context bytes.

```text
EXECUTOR_INVOCATION_CANONICAL: PASS
PAYLOAD_EMBEDDED_IN_RECORD: NO
MAX_INVOCATION_PAYLOAD_BYTES: 1048576
MERGE_OPERATION_ALLOWED: NO
UNKNOWN_FIELDS_ALLOWED: NO
AUTHORITY_OR_SECRET_FIELDS_ALLOWED: NO
```

### M4 / M5 Mechanical Binding

`validate_executor_invocation(...)` reuses the existing M4 prepared/request validator and M5 lease validator, then mechanically binds:

```text
schema_version
task_id
request_id
executor_id
operation
target_branch
request_fingerprint
execution_id
prepared_execution_fingerprint
workspace_id
lease_fingerprint
execution_fingerprint
```

A lease/request/prepared record from another task, actor, operation, workspace or execution boundary fails closed.

```text
M4_REQUEST_PREPARED_BINDING: PASS
M5_LEASE_BINDING: PASS
LEASE_REINTERPRETED_AS_HUMAN_AUTHORIZATION: NO
```

### Exact Runtime Payload Identity

`validate_invocation_payload(...)` requires exact `bytes`, non-empty content, bounded size, exact length and SHA-256 equality. String/bytearray/memoryview/generator inputs, length drift, hash drift and one-byte mutation are rejected.

```text
PAYLOAD_BYTE_IDENTITY: PASS
PAYLOAD_ONE_BYTE_TAMPER_REJECTED: PASS
PAYLOAD_BOOL_SIZE_REJECTED: PASS
```

### InvocationReceipt Semantics

The status domain is transport/process-only:

```text
EXITED_ZERO
EXITED_NONZERO
FAILED_TO_START
TIMED_OUT
INTERRUPTED
```

`EXITED_ZERO` is mechanically only `exit_code == 0` with no error code; it does not encode task success, Brain PASS, publication or merge authority. Non-zero/failure states enforce the locked payload matrix.

Receipt identity is bound to the exact invocation fingerprint plus task/request/executor/transport/operation/execution identity.

```text
INVOCATION_RECEIPT_TRANSPORT_ONLY: PASS
INVOCATION_RECEIPT_IS_EXECUTION_RESULT: NO
EXITED_ZERO_IMPLIES_TASK_SUCCESS: NO
RECEIPT_IDENTITY_BINDING: PASS
```

### ExecutionTransport Protocol

`ExecutionTransport` is runtime-checkable and vendor-neutral, exposing only exact `transport_id`, `executor_id`, and synchronous `invoke(invocation, payload) -> InvocationReceipt`.

Neutral second and third transports/executors conform without Continuity Core changes. `validate_transport_binding(...)` checks identity and does not call `invoke()`.

```text
EXECUTION_TRANSPORT_PROTOCOL: PASS
VENDOR_NEUTRAL: PASS
CONCRETE_CODEX_TRANSPORT_PRESENT: NO
TRANSPORT_BINDING_INVOKES_TRANSPORT: NO
```

## Purity / Authority Audit

Independent source inspection plus the task's AST guard confirms `executor_transport.py` has no imports/calls that perform filesystem, subprocess, shell, Git, network, Bridge, dispatch, runtime-store, provider/model, authorization, lease acquisition/release, publication or merge actions.

```text
ZERO_REAL_INVOCATION: PASS
SUBPROCESS_SURFACE: NONE
FILESYSTEM_MUTATION_SURFACE: NONE
NETWORK_SURFACE: NONE
BRIDGE_MUTATION_SURFACE: NONE
DISPATCH_MUTATION_SURFACE: NONE
LEASE_STORE_MUTATION_SURFACE: NONE
PROVIDER_MODEL_SURFACE: NONE
AUTO_APPROVAL: NO
AUTO_PUBLICATION: NO
AUTO_MERGE: NO
INVOCATION_IS_NOT_AUTHORIZATION: PASS
BRIDGE_AUTHORITY_UNCHANGED: PASS
M10_UNCHANGED: PASS
H_SERIES_REMAINS_DEFERRED: PASS
```

## Test / Adversarial Audit

The focused suite covers RUN/FIX round trips, canonical fingerprints, exact request/prepared/lease binding, payload byte identity, all receipt statuses, second/third neutral transports, identity drift, MERGE/unknown operation rejection, malformed fingerprints/branches, invalid payload sizes, request/prepared/lease drift, payload tampering, transport mismatch, receipt drift, status payload matrices, forbidden/unknown fields, >16 KiB parsing rejection and zero-I/O AST guards.

Final Bridge publication reports:

```text
1271 passed, 7 skipped, 1533 warnings in 129.77s
exit code 0
```

```text
FULL_REPO_TESTS: PASS
REGRESSIONS: 0
```

## Non-Blocking Publication Observation

`RESULT-040.md` correctly lists all three Executor implementation/test paths in `Files Changed`, while its generated `Diff Stat` section shows only the tracked `__init__.py` modification and omits the two newly added files. Independent Git branch comparison mechanically establishes the complete four-path task scope, so this does not invalidate E1. It appears to be a Bridge RESULT diff-stat reporting limitation rather than an E1 contract defect.

```text
E1_BLOCKING: NO
FOLLOW_UP_REQUIRED_FOR_E1: NO
```

## Findings

```text
BLOCKING_FINDINGS: NONE
SECURITY_AUTHORITY_FINDINGS: NONE
CONTRACT_FINDINGS: NONE
SCOPE_FINDINGS: NONE
REGRESSION_FINDINGS: NONE
```

## E1 Acceptance Audit

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
E1: PASS
```

## Final Decision

TASK-040 satisfies ADR-029 and the locked E1 implementation blueprint.

```text
STATUS: PASS
APPROVED: YES
READY_FOR_HUMAN_MERGE: YES
MERGE_AUTHORIZED: NO
E1: PASS
E2_PROVEN: NO
```

Human may authorize merge. E2 — Codex Local Transport — remains a separate milestone and MUST still preserve explicit Human RUN/FIX authority.