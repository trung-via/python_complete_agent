# TASK-040 — E1 Executor Invocation Contract

STATUS: READY
CLASS: L3 — EXECUTOR TRANSPORT CONTRACT / AUTHORITY PRESERVATION / ZERO-INVOCATION
EXECUTOR_MODE: THIN_EXECUTOR

## Baseline

```text
MAIN_SHA: b22a48b14c5fc07007caf498fedc6503656c73e6
TARGET_BRANCH: ai/task-040
```

## Authoritative Contract

```text
ADR_PATH: .ai/decisions/ADR-029-E1-EXECUTOR-INVOCATION-CONTRACT-LOCK.md
ADR_BLOB_SHA: e041197922abc0aaa15083202919a622f21282b8
BLUEPRINT_PATH: .ai/context/TASK-040-E1-IMPLEMENTATION-BLUEPRINT.md
BLUEPRINT_BLOB_SHA: 566cdeb93164121097960e7669d5e631a3b8f448
```

## E-Series Position

```text
E1 — Executor Invocation Contract                  ← THIS TASK
E2 — Codex Local Transport
E3 — Bounded Context Pack Delivery
E4 — Result Collection + Auto Publication
E5 — Zero-Copy/Paste Operational Proof
```

H-Series remains a separate DEFERRED backlog and MUST NOT be implemented by this task.

## Objective

Implement the pure vendor-neutral invocation seam explicitly reserved by M4/ADR-018 so later AIOS milestones can call an already-Human-authorized Executor without manual prompt copy/paste.

TASK-040 defines only the invocation data/validation/Protocol boundary. It performs zero real Executor invocation.

## Executor Dispatch Policy

DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX","RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX","RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"claude-code","preference_rank":2,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX","RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

This marker is recommendation policy only and is not authorization.

## Allowed Files

Exactly:

```text
src/aios_bridge/continuity/executor_transport.py
src/aios_bridge/continuity/__init__.py
tests/aios_bridge/continuity/test_executor_transport.py
.ai/results/RESULT-040.md        # Bridge-generated only
```

## Forbidden Scope

Do NOT modify:

```text
bridge.py
src/aios_bridge/continuity/executor.py
src/aios_bridge/continuity/lease.py
src/aios_bridge/continuity/dispatch.py
src/aios_bridge/runtime_dispatch.py
src/aios_bridge/runtime_lease.py
src/aios_bridge/continuity/hot_handoff.py
src/aios_bridge/continuity/executor_failover.py
src/aios_bridge/external_brain/**
src/providers/**
```

Do NOT implement:
- Codex CLI/process invocation;
- Antigravity/Claude transport;
- subprocess/shell/network/browser execution;
- context-pack rendering;
- automatic result collection;
- automatic publication;
- automatic approval/lease acquisition;
- M11 API fallback;
- H1 Event Journal;
- H2 Capability Seams;
- H3 Execution Envelope;
- H4 Provider Lifecycle;
- H5 Driver Contract.

## Required Production Contract

Implement exactly according to ADR-029 and the locked blueprint:

```text
InvocationStatus
ExecutorInvocation
InvocationReceipt
ExecutionTransport Protocol
validate_executor_invocation
validate_invocation_payload
validate_invocation_receipt
validate_transport_binding
MAX_INVOCATION_PAYLOAD_BYTES
```

The invocation must mechanically bind existing:

```text
M4 ExecutionRequest
M4 PreparedExecution
M5 ExecutorLease
```

without redefining any of them.

## Authority Invariant

The following distinction is locked:

```text
M10 recommendation
    != Human authorization
    != ExecutorLease
    != ExecutorInvocation
    != InvocationReceipt
    != M4 ExecutionResult
    != publication
    != merge
```

An invocation object or receipt MUST NOT authorize anything.

## Payload Invariant

Canonical invocation stores only:

```text
payload_sha256
payload_size_bytes
```

It MUST NOT store raw prompt/context bytes.

Exact runtime payload bytes must mechanically match both fields.

## Required Tests

Implement the complete positive/adversarial matrix from ADR-029 Decision 14 and blueprint section 15.

Especially prove:
- exact request/prepared/lease binding;
- exact payload byte/hash/size binding;
- transport/executor identity binding;
- receipt status payload matrix;
- receipt/invocation fingerprint binding;
- authority/secret/raw-payload fields rejected;
- vendor-neutral second/third transport stubs;
- zero I/O / zero real invocation / zero Bridge mutation.

## Thin Executor Read Budget

Read only these production files unless a concrete blocker exists:

```text
src/aios_bridge/continuity/executor.py
src/aios_bridge/continuity/lease.py
src/aios_bridge/continuity/state.py
src/aios_bridge/continuity/__init__.py
```

Read authoritative TASK/ADR/blueprint directly from the exact `origin/ai-control` ref or Bridge runtime artifact cache. Do not require those logical control files to exist in the task worktree.

Do not repository-wide search.
Do not redesign E-Series.

## Targeted Commands

Run only:

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_bridge/continuity/test_executor_transport.py -q
.\venv\Scripts\python.exe -m pytest tests/aios_bridge/continuity/test_executor.py tests/aios_bridge/test_runtime_lease.py tests/aios_bridge/continuity/test_dispatch.py -q
```

Do NOT run full repository suite.

When targeted tests pass:
- report files changed;
- report targeted test counts;
- report blockers if any;
- STOP.

Do not commit.
Do not push.
Do not publish.

## Publication

Human uses Bridge:

```powershell
.\venv\Scripts\python.exe .\bridge.py publish 40 `
  --action RUN `
  --test ".\venv\Scripts\python.exe -m pytest tests/ -q"
```

Bridge owns full-suite, RESULT generation, commit, and push.

## Acceptance

PASS requires:

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

Only Human may authorize merge.