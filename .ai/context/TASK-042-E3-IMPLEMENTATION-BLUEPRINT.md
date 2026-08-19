# TASK-042 — E3 Bounded Context Pack Delivery — Implementation Blueprint

STATUS: LOCKED BLUEPRINT

## 1. Baseline / Authority

```text
TASK_ID: TASK-042
MILESTONE: E3 — Bounded Context Pack Delivery
BASELINE_MAIN_SHA: 7ea6197063dbcede82ec24b23cc3bad2621e8c8a
TARGET_BRANCH: ai/task-042
ADR_PATH: .ai/decisions/ADR-031-E3-BOUNDED-EXECUTOR-CONTEXT-PACK-CONTRACT-LOCK.md
ADR_BLOB_SHA: 5ee1d936f17f1b3530cbe23d6a0157f6d1116fd9
EXECUTOR_MODE: THIN_EXECUTOR
```

Existing anchors on baseline:

```text
M4_EXECUTOR_BLOB_SHA: f144ea399c11f89809ecdf4f3d62098ee356ed7a
M5_LEASE_BLOB_SHA: 81a1373d6e04084b7c28d67699f4f613e4f0ee47
E1_TRANSPORT_CONTRACT_BLOB_SHA: bbe7b517202ea446e727752955e004d9464934bd
ARTIFACT_REF_STATE_BLOB_SHA: 3b2c04169a85c54ccac1abe0736934cee1624af1
E2_CODEX_LOCAL_BLOB_SHA: dd1fae54506459a2a638441a35d5a327d89da8cc
```

E3 is pure composition only. It must not invoke E2.

## 2. Allowed Files

Executor may create only:

```text
src/aios_bridge/executor_context.py
tests/aios_bridge/test_executor_context_pack.py
```

Bridge publication may generate:

```text
.ai/results/RESULT-042.md
```

No other file.

Explicitly forbidden modifications:

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

No E4/E5, H-Series, or M11 work.

## 3. Thin Executor Read Budget

Read only:

```text
src/aios_bridge/continuity/state.py
src/aios_bridge/continuity/executor.py
src/aios_bridge/continuity/lease.py
src/aios_bridge/continuity/executor_transport.py
```

plus exact TASK / ADR / blueprint from `origin/ai-control`.

Do not broad-search the repository.
Do not read E2 implementation unless a concrete import/type blocker exists; E3 must not invoke it.

## 4. Module Imports

Create `src/aios_bridge/executor_context.py` with bounded standard-library imports only:

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import re
from typing import Any, Mapping

from src.aios_bridge.continuity.errors import ContinuityStateValidationError
from src.aios_bridge.continuity.executor import (
    ExecutionCapability,
    ExecutionOperation,
    ExecutionRequest,
    PreparedExecution,
    validate_prepared_execution_against_request,
)
from src.aios_bridge.continuity.executor_transport import (
    MAX_INVOCATION_PAYLOAD_BYTES,
    ExecutorInvocation,
    validate_executor_invocation,
    validate_invocation_payload,
)
from src.aios_bridge.continuity.lease import (
    ExecutorLease,
    validate_executor_lease_binding,
)
from src.aios_bridge.continuity.state import ArtifactRef, SCHEMA_VERSION
```

No `os`, `pathlib`, `subprocess`, Git library, HTTP/network, browser, provider/model SDK, Bridge runtime, dispatcher, lease store, or E2 transport import.

## 5. Constants

Define exactly:

```python
CONTEXT_FORMAT_VERSION = "aios-executor-context-v1"
CONTEXT_INSTRUCTION_PROFILE = "thin-executor-v1"
ACTIVE_AUTHORIZATION_STATUS = "ACTIVE"

MAX_CONTEXT_ARTIFACTS = 8
MAX_CONTEXT_ARTIFACT_BYTES = 131_072
MAX_CONTEXT_RAW_ARTIFACT_BYTES = 196_608
MAX_CONTEXT_PACK_BYTES = 262_144
```

Assert/validate in module logic that `MAX_CONTEXT_PACK_BYTES <= MAX_INVOCATION_PAYLOAD_BYTES`; do not mutate E1 constant.

Conservative local patterns:

```text
canonical ID: lowercase [a-z0-9] with . _ - : allowed internally, <=64
Git blob SHA: exactly 40 lowercase hex
fingerprint: exactly 64 lowercase hex
```

## 6. Authorization Binding Model

Implement:

```python
@dataclass(frozen=True)
class ExecutorAuthorizationBinding:
    schema_version: str
    task_id: str
    operation: ExecutionOperation
    executor_id: str
    target_branch: str
    artifact_path: str
    artifact_blob_sha: str
    lease_id: str
    lease_fingerprint: str
    workspace_id: str
    execution_fingerprint: str
    status: str = ACTIVE_AUTHORIZATION_STATUS
```

`__post_init__` requirements:
- exact `SCHEMA_VERSION`;
- task ID exact `TASK-<digits>`;
- operation exact RUN/FIX only;
- canonical non-empty executor ID;
- target branch non-empty/no surrounding whitespace; relational validation against `ExecutionRequest` later is authoritative;
- artifact path non-empty/no surrounding whitespace;
- artifact blob SHA exact 40 lowercase hex;
- lease ID canonical bounded ID;
- lease/workspace/execution fingerprints exact 64 lowercase hex;
- status must be exact string `ACTIVE`;
- bool rejected where relevant.

Implement:

```text
to_dict()
to_canonical_json()
fingerprint()
```

`to_dict()` contains exactly the model fields above. No timestamps or secrets.

No `approve()` or authority mutation method.

## 7. Artifact Role / Manifest Entry

Implement:

```python
class ContextArtifactRole(str, Enum):
    WORK = "WORK"
    CONTEXT = "CONTEXT"
```

and:

```python
@dataclass(frozen=True)
class ContextArtifactManifestEntry:
    role: ContextArtifactRole
    ordinal: int
    path: str
    ref: str
    blob_sha: str
    content_sha256: str
    size_bytes: int
```

Validation:
- role exact enum;
- ordinal exact int >=0, bool rejected;
- path/ref non-empty exact strings without surrounding whitespace;
- blob SHA exact 40 lowercase hex;
- content SHA exact 64 lowercase hex;
- size exact int 1..MAX_CONTEXT_ARTIFACT_BYTES.

Implement deterministic `to_dict()` only; manifest owns canonical JSON.

## 8. Context Manifest

Implement immutable:

```python
@dataclass(frozen=True)
class ExecutorContextManifest:
    schema_version: str
    format_version: str
    instruction_profile: str
    task_id: str
    operation: ExecutionOperation
    request_id: str
    executor_id: str
    transport_id: str
    target_branch: str
    workspace_id: str
    execution_id: str
    request_fingerprint: str
    prepared_execution_fingerprint: str
    lease_id: str
    lease_fingerprint: str
    execution_fingerprint: str
    authorization_binding_fingerprint: str
    expected_task_head_sha: str | None
    expected_result_path: str
    required_capabilities: tuple[ExecutionCapability, ...]
    artifacts: tuple[ContextArtifactManifestEntry, ...]
```

Require exact `CONTEXT_FORMAT_VERSION` and `CONTEXT_INSTRUCTION_PROFILE`.
Validate canonical IDs/fingerprints similarly to E1 local semantics.
`artifacts` count 1..MAX_CONTEXT_ARTIFACTS, ordinals exactly contiguous `0..n-1`, path unique, first role WORK, remaining roles CONTEXT.
`required_capabilities` preserve canonical `ExecutionRequest.required_capabilities` order.

Implement:

```text
to_dict()
to_canonical_json()
fingerprint()
```

No payload bytes stored in manifest.

## 9. Final Bundle

Implement:

```python
@dataclass(frozen=True)
class ExecutorContextPack:
    manifest: ExecutorContextManifest
    payload: bytes
    invocation: ExecutorInvocation
```

`__post_init__` at minimum:
- exact types;
- payload exact bytes, non-empty;
- `len(payload) <= MAX_CONTEXT_PACK_BYTES`;
- `validate_invocation_payload(invocation, payload)`;
- manifest identity fields equal invocation identity where shared (`task_id`, operation, request_id, executor_id, transport_id, target_branch, workspace_id, execution_id, request/prepared/lease/execution fingerprints).

This is a value bundle, not a transport/session/result object.

## 10. Git Blob Helper

Implement pure:

```python
def _git_blob_sha1(content: bytes) -> str:
    header = b"blob " + str(len(content)).encode("ascii") + b"\0"
    return hashlib.sha1(header + content).hexdigest()
```

Only exact `bytes` accepted by calling validator.

Do not use Git subprocess/library.

## 11. Artifact Validation Helper

Implement private helper conceptually:

```python
def _validate_artifact_content(
    ref: ArtifactRef,
    payload: object,
    *,
    role: ContextArtifactRole,
    ordinal: int,
) -> ContextArtifactManifestEntry:
```

Locked checks in this order:
1. `ref` exact `ArtifactRef`.
2. `type(payload) is bytes` exactly.
3. non-empty.
4. size <= MAX_CONTEXT_ARTIFACT_BYTES.
5. no `b"\x00"`.
6. strict UTF-8 decode succeeds (discard decoded value; never re-render from it).
7. `_git_blob_sha1(payload) == ref.blob_sha`.
8. create entry with `hashlib.sha256(payload).hexdigest()` and exact byte size.

No normalization/mutation.

## 12. Exact Artifact Set Helper

For one `ExecutionRequest`:

```python
ordered_refs = (request.work_ref, *request.context_refs)
```

Require:
- `1 <= len(ordered_refs) <= MAX_CONTEXT_ARTIFACTS`;
- exact unique paths;
- `artifact_payloads` is a Mapping;
- every mapping key exact string;
- `set(artifact_payloads.keys()) == {ref.path for ref in ordered_refs}`;
- no missing/extra entries.

Mapping order is ignored.
Output order uses `ordered_refs` only.

After individual validation, sum raw artifact sizes and require `<= MAX_CONTEXT_RAW_ARTIFACT_BYTES`.

No truncation.

## 13. Authorization/Request/Lease Binding Helper

Implement private:

```python
def _validate_authorization_binding(
    binding: ExecutorAuthorizationBinding,
    request: ExecutionRequest,
    prepared: PreparedExecution,
    lease: ExecutorLease,
) -> None:
```

Sequence:
1. exact types.
2. `validate_prepared_execution_against_request(prepared, request)`.
3. binding fields exact-match request:
   - schema_version
   - task_id
   - operation
   - executor_id
   - target_branch
   - artifact_path == request.work_ref.path
   - artifact_blob_sha == request.work_ref.blob_sha
4. binding fields exact-match lease:
   - schema_version
   - task_id
   - operation
   - executor_id
   - lease_id
   - lease_fingerprint == lease.fingerprint()
   - workspace_id
   - execution_fingerprint
5. call `validate_executor_lease_binding(lease, task_id=request.task_id, workspace_id=binding.workspace_id, executor_id=request.executor_id, operation=request.operation, execution_fingerprint=binding.execution_fingerprint)`.

No state mutation.

## 14. Fixed Instruction Block

Define one module constant exact UTF-8/ASCII-compatible text; no caller override:

```text
AUTHORITY NOTICE
This context pack is transport material bound to externally verified authorization evidence. The pack itself does not grant or extend RUN, FIX, or MERGE authority.

THIN EXECUTOR RULES
- Obey the exact WORK artifact and bounded CONTEXT artifacts below.
- Do not redesign or widen scope beyond those artifacts.
- Do not self-select or change the executor.
- Do not mutate Bridge authorization, lease, dispatch, failover, or hot-handoff state.
- Do not commit, push, publish RESULT, or merge.
- Run only executor-side targeted tests authorized by the control artifacts.
- Stop after bounded implementation/testing and report files changed, test results, and blockers to the caller.
```

Use this exact semantic content; punctuation/newline details may be frozen in tests once implemented.
Do not add free-form user/executor text.

## 15. Payload Renderer

Implement private:

```python
def _render_payload(
    manifest: ExecutorContextManifest,
    ordered: tuple[tuple[ContextArtifactManifestEntry, bytes], ...],
) -> bytes:
```

Construct via `bytearray`/list-of-bytes; never decode and re-encode artifact bytes.

Header must contain:

```text
AIOS_EXECUTOR_CONTEXT_PACK_V1
<fixed instruction block>
MANIFEST_SHA256: <manifest.fingerprint()>
MANIFEST_JSON: <manifest.to_canonical_json()>
```

For each entry, exact ordinal order:

```text
ARTIFACT <n> BEGIN
ROLE: <WORK|CONTEXT>
PATH: <path>
REF: <ref>
BLOB_SHA: <blob_sha>
CONTENT_SHA256: <content_sha256>
SIZE_BYTES: <size_bytes>
CONTENT_BEGIN
```

append exact raw artifact bytes, then append deterministic:

```text
\nCONTENT_END
ARTIFACT <n> END
```

Finish exact marker:

```text
AIOS_EXECUTOR_CONTEXT_PACK_END
```

Require final payload:
- non-empty;
- valid UTF-8 (because all fixed text + artifacts are valid UTF-8);
- `len <= MAX_CONTEXT_PACK_BYTES`;
- `len <= MAX_INVOCATION_PAYLOAD_BYTES`.

If oversized, raise `ContinuityStateValidationError`; never truncate.

## 16. Public Builder

Implement exactly one public builder:

```python
def build_executor_context_pack(
    execution_request: ExecutionRequest,
    prepared_execution: PreparedExecution,
    executor_lease: ExecutorLease,
    authorization_binding: ExecutorAuthorizationBinding,
    artifact_payloads: Mapping[str, bytes],
    *,
    invocation_id: str,
    transport_id: str,
) -> ExecutorContextPack:
```

Locked sequence:
1. validate types and authorization/request/prepared/lease binding.
2. validate artifact set/count.
3. validate each exact artifact bytes and build ordered entries.
4. enforce aggregate raw limit.
5. construct manifest from exact canonical inputs:
   - request identity/fingerprint;
   - prepared fingerprint/execution ID;
   - lease IDs/fingerprints/workspace/execution fingerprint;
   - binding fingerprint;
   - request expected task head/result/capabilities;
   - ordered artifact entries.
6. render exact payload.
7. compute exact payload SHA-256/size.
8. construct `ExecutorInvocation` with:

```text
schema_version = request.schema_version
invocation_id = explicit input
 task_id = request.task_id
request_id = request.request_id
executor_id = request.executor_id
transport_id = explicit input
operation = request.operation
workspace_id = lease.workspace_id
target_branch = request.target_branch
execution_id = prepared.execution_id
request_fingerprint = request.fingerprint()
prepared_execution_fingerprint = prepared.fingerprint()
lease_fingerprint = lease.fingerprint()
execution_fingerprint = lease.execution_fingerprint
payload_sha256 = sha256(payload)
payload_size_bytes = len(payload)
```

9. call `validate_executor_invocation(invocation, request, prepared, lease)`.
10. call `validate_invocation_payload(invocation, payload)`.
11. create `ExecutorContextPack`; return.

No transport call.

## 17. Public Surface

Module `__all__` only:

```text
ACTIVE_AUTHORIZATION_STATUS
CONTEXT_FORMAT_VERSION
CONTEXT_INSTRUCTION_PROFILE
MAX_CONTEXT_ARTIFACTS
MAX_CONTEXT_ARTIFACT_BYTES
MAX_CONTEXT_RAW_ARTIFACT_BYTES
MAX_CONTEXT_PACK_BYTES
ContextArtifactRole
ContextArtifactManifestEntry
ExecutorAuthorizationBinding
ExecutorContextManifest
ExecutorContextPack
build_executor_context_pack
```

Do not export internal rendering/hash helpers.

## 18. Tests

Create:

```text
tests/aios_bridge/test_executor_context_pack.py
```

Build all fixtures locally in this test file.
Do not import helpers from other tests.

Use exact `ArtifactRef` fixtures whose blob SHA is computed from fixture bytes with the real Git blob algorithm.

RUN fixture:
- work ref `.ai/tasks/TASK-042.md`;
- context refs e.g. exact ADR-031 + blueprint refs;
- executor `codex`;
- branch `ai/task-042`.

FIX fixture:
- work ref `.ai/reviews/REVIEW-042.md`;
- context refs e.g. TASK + ADR + blueprint;
- operation FIX.

No real repo file reads are required by tests.
No real Codex/transport call.

## 19. Mandatory Test Matrix

### Positive
- RUN pack valid.
- FIX pack valid.
- manifest fields mechanically match request/prepared/lease/binding.
- work artifact ordinal 0 role WORK.
- context refs preserve request order and role CONTEXT.
- reverse/shuffle input mapping insertion order -> byte-identical payload/fingerprints.
- repeat build -> byte-identical payload, manifest fp, invocation fp.
- raw payload with CRLF/BOM/trailing spaces survives as exact contiguous bytes and manifest SHA/size matches exact input.
- E1 validation passes.
- final `payload_sha256/size` equals exact payload.
- fixed instruction block present exactly once.
- authority notice explicitly says pack itself does not grant/extend authority.

### Artifact adversarial
- mapping missing work artifact.
- mapping missing context artifact.
- extra mapping path.
- wrong bytes for correct ref.
- empty bytes.
- `bytearray` rejected.
- invalid UTF-8 rejected.
- NUL rejected.
- per-artifact >128 KiB rejected.
- aggregate raw >192 KiB rejected.
- >8 request artifacts rejected.
- final pack bound enforced by monkeypatching `MAX_CONTEXT_PACK_BYTES` downward; prove no truncation.

### Binding adversarial
Parametrize one-field drift for:
- task ID;
- operation;
- executor ID;
- target branch;
- artifact path;
- artifact blob SHA;
- lease ID;
- lease fingerprint;
- workspace ID;
- execution fingerprint;
- status != ACTIVE.

All fail before returning a pack.

Also:
- prepared request fingerprint drift rejected;
- lease/request actor/action drift rejected;
- malformed invocation ID rejected by E1 constructor/validation;
- malformed transport ID rejected by E1 constructor/validation.

### Scope / purity guard
AST/source inspection proves production module does not import/use:

```text
os
pathlib
subprocess
socket
requests
httpx
urllib
bridge
runtime_dispatch
runtime_lease
executor_transports
providers
external_brain
openai
anthropic
google
browser
```

and contains no semantic operations for:

```text
approve
publish
commit
push
merge
invoke
Popen
system
checkout
reset
stash
clean
```

Do not reject the field word `invocation`; only reject actual transport `invoke` call/name where applicable.

Assert public builder signature has no `prompt`, `extra_prompt`, `system_prompt`, `instructions`, callback, transport, or model parameter.

## 20. Targeted Tests

Run only:

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_bridge/test_executor_context_pack.py -q

.\venv\Scripts\python.exe -m pytest tests/aios_bridge/continuity/test_executor_transport.py tests/aios_bridge/continuity/test_executor.py tests/aios_bridge/test_runtime_lease.py -q
```

Do NOT run full repository suite.
Bridge publication owns the full suite.

## 21. Stop Conditions

STOP and escalate rather than widen scope if:
- E3 requires changing M4/M5/E1/E2 contracts;
- exact artifact bytes cannot be verified without I/O inside E3;
- Bridge integration appears necessary;
- a generic Execution Envelope/Driver/Provider abstraction appears necessary;
- test requires real Codex invocation.

## 22. Acceptance

PASS requires all ADR-031 acceptance lines plus:

```text
ALLOWED_FILES_ONLY: PASS
RUN_PACK: PASS
FIX_PACK: PASS
AUTH_BINDING_EXACT: PASS
GIT_BLOB_SHA1_EXACT: PASS
CRLF_BOM_BYTE_PRESERVATION: PASS
MAPPING_ORDER_INDEPENDENT: PASS
REPEAT_BUILD_DETERMINISTIC: PASS
MAX_8_ARTIFACTS: PASS
128K_PER_ARTIFACT: PASS
192K_RAW_AGGREGATE: PASS
256K_FINAL_PACK: PASS
NO_TRUNCATION: PASS
NO_FREE_FORM_PROMPT: PASS
NO_IO_IMPORTS: PASS
TARGETED_TESTS: PASS
FULL_REPO_TESTS: PASS
REGRESSIONS: 0
```
