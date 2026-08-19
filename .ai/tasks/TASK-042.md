# TASK-042 — E3 Bounded Context Pack Delivery

STATUS: READY
CLASS: L3 — PURE CONTEXT COMPOSITION / CONTENT ADDRESSING / TOKEN BOUNDS / AUTHORITY PRESERVATION
EXECUTOR_MODE: THIN_EXECUTOR

## Baseline

```text
MAIN_SHA: 7ea6197063dbcede82ec24b23cc3bad2621e8c8a
TARGET_BRANCH: ai/task-042
```

## Authoritative Contract

```text
ADR_PATH: .ai/decisions/ADR-031-E3-BOUNDED-EXECUTOR-CONTEXT-PACK-CONTRACT-LOCK.md
ADR_BLOB_SHA: 5ee1d936f17f1b3530cbe23d6a0157f6d1116fd9
BLUEPRINT_PATH: .ai/context/TASK-042-E3-IMPLEMENTATION-BLUEPRINT.md
BLUEPRINT_BLOB_SHA: 0aad2280e685dc1cdfd80cdd2665197e2cc0f2d2
```

Existing production anchors:

```text
M4_EXECUTOR_BLOB_SHA: f144ea399c11f89809ecdf4f3d62098ee356ed7a
M5_LEASE_BLOB_SHA: 81a1373d6e04084b7c28d67699f4f613e4f0ee47
E1_TRANSPORT_CONTRACT_BLOB_SHA: bbe7b517202ea446e727752955e004d9464934bd
ARTIFACT_REF_STATE_BLOB_SHA: 3b2c04169a85c54ccac1abe0736934cee1624af1
E2_CODEX_LOCAL_BLOB_SHA: dd1fae54506459a2a638441a35d5a327d89da8cc
```

## E-Series Position

```text
E1 — Executor Invocation Contract                  COMPLETE
E2 — Codex Local Transport                         COMPLETE
E3 — Bounded Context Pack Delivery                 ← THIS TASK
E4 — Result Collection + Auto Publication
E5 — Zero-Copy/Paste Operational Proof
```

H-Series remains separate and DEFERRED.

## Objective

Implement one pure deterministic E-Series context-pack composer that takes already-bound M4/M5 execution objects plus exact control-artifact bytes, verifies those bytes against exact Git blob refs, applies strict context-budget bounds, renders one content-addressed UTF-8 executor payload, and constructs the exact E1 `ExecutorInvocation` bound to that payload.

E3 removes the need for a Human to manually assemble/copy a long executor prompt in the future, but E3 itself does NOT read local files and does NOT launch Codex.

## Executor Dispatch Policy

DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX","RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX","RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"claude-code","preference_rank":2,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX","RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

This marker is recommendation policy only. It grants no authority.

## Allowed Files

Exactly:

```text
src/aios_bridge/executor_context.py
tests/aios_bridge/test_executor_context_pack.py
.ai/results/RESULT-042.md        # Bridge-generated only
```

## Forbidden Scope

Do NOT modify:

```text
bridge.py
src/aios_bridge/continuity/**
src/aios_bridge/executor_transports/**
src/aios_bridge/runtime_dispatch.py
src/aios_bridge/runtime_lease.py
src/aios_bridge/external_brain/**
src/providers/**
docs/**
```

Do NOT implement:
- E2 transport invocation;
- Bridge auto-invoke;
- filesystem/Git artifact loading;
- auto approval;
- lease acquisition/release;
- result collection or auto publication;
- E4/E5;
- M11;
- H1 Event Journal;
- H2 Capability Seams;
- H3 Execution Envelope;
- H4 Provider Lifecycle;
- H5 Driver Contract.

## Required Surface

Implement exactly according to ADR-031 and locked blueprint:

```text
ExecutorAuthorizationBinding
ContextArtifactRole
ContextArtifactManifestEntry
ExecutorContextManifest
ExecutorContextPack
build_executor_context_pack(...)
```

plus only bounded private validation/render helpers required by the blueprint.

## Core Invariants

```text
work/context refs come only from ExecutionRequest
artifact map key set must match request refs exactly
artifact bytes verified against exact Git blob SHA-1
artifact bytes preserved exactly
valid UTF-8 required
NUL forbidden
no truncation
no summarization
no arbitrary extra prompt
max artifacts = 8
max one artifact = 128 KiB
max aggregate raw artifacts = 192 KiB
max final pack = 256 KiB
mapping insertion order cannot affect payload
time/OS/env/cwd cannot affect payload
Human authorization binding is evidence only
pack != authority
pack != invocation execution
pack != result
pack != publication
pack != merge
```

E3 must construct and validate an E1 `ExecutorInvocation` whose payload SHA-256 and size match the exact final rendered bytes.

## Thin Executor Read Budget

Read only:

```text
src/aios_bridge/continuity/state.py
src/aios_bridge/continuity/executor.py
src/aios_bridge/continuity/lease.py
src/aios_bridge/continuity/executor_transport.py
```

and exact TASK/ADR/blueprint from `origin/ai-control`.

Do not broad-search repository.

## Tests

Must include positive RUN/FIX composition plus adversarial coverage required by ADR-031/blueprint, especially:

```text
exact Git blob verification
CRLF/BOM/trailing-space byte preservation
mapping-order independence
repeat-build determinism
missing/extra artifact rejection
wrong bytes rejection
invalid UTF-8/NUL rejection
8/128K/192K/256K bounds
no truncation
all authorization/request/lease drift cases
E1 invocation validation
no free-form prompt parameter
no I/O/Bridge/E2/provider imports or calls
```

No real Codex/model invocation in tests.

## Targeted Commands

Run only:

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_bridge/test_executor_context_pack.py -q

.\venv\Scripts\python.exe -m pytest tests/aios_bridge/continuity/test_executor_transport.py tests/aios_bridge/continuity/test_executor.py tests/aios_bridge/test_runtime_lease.py -q
```

Do NOT run the full repository suite.
Do NOT invoke Codex through E2 from tests or implementation.

When targeted tests pass:
- report files changed;
- report targeted test counts;
- report blockers;
- STOP.

Do not commit.
Do not push.
Do not publish.

## Publication

Human runs:

```powershell
.\venv\Scripts\python.exe .\bridge.py publish 42 `
  --action RUN `
  --test ".\venv\Scripts\python.exe -m pytest tests/ -q"
```

Bridge owns full-suite, RESULT generation, commit, and push.

## Acceptance

PASS requires:

```text
REUSES_M4_ARTIFACT_REFS: PASS
REUSES_E1_INVOCATION: PASS
AUTHORIZATION_BINDING_IS_EVIDENCE_ONLY: PASS
REQUEST_PREPARED_LEASE_AUTH_BINDING: PASS
EXACT_ARTIFACT_SET: PASS
GIT_BLOB_BYTE_IDENTITY: PASS
CRLF_BOM_BYTE_PRESERVATION: PASS
UTF8_NO_MUTATION: PASS
LOW_TOKEN_BOUNDS: PASS
NO_TRUNCATION_OR_SUMMARIZATION: PASS
MAPPING_ORDER_INDEPENDENT: PASS
REPEAT_BUILD_DETERMINISTIC: PASS
DETERMINISTIC_MANIFEST: PASS
DETERMINISTIC_PAYLOAD: PASS
PAYLOAD_CONTENT_ADDRESSED: PASS
E1_INVOCATION_VALIDATED: PASS
NO_FREE_FORM_PROMPT: PASS
NO_IO_IMPORTS: PASS
NO_REAL_TRANSPORT_INVOCATION: PASS
NO_BRIDGE_INTEGRATION: PASS
H_SERIES_REMAINS_DEFERRED: PASS
FULL_REPO_TESTS: PASS
REGRESSIONS: 0
FINAL_INDEPENDENT_AUDIT: PASS
E3: PASS
```

Only Human may authorize merge.
