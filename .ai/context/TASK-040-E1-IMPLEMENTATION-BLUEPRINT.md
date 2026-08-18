# TASK-040 — E1 Executor Invocation Contract — Implementation Blueprint

STATUS: LOCKED BLUEPRINT

## 1. Baseline / Authority

```text
TASK_ID: TASK-040
MILESTONE: E1 — Executor Invocation Contract
BASELINE_MAIN_SHA: b22a48b14c5fc07007caf498fedc6503656c73e6
TARGET_BRANCH: ai/task-040
ADR_PATH: .ai/decisions/ADR-029-E1-EXECUTOR-INVOCATION-CONTRACT-LOCK.md
ADR_BLOB_SHA: e041197922abc0aaa15083202919a622f21282b8
EXECUTOR_MODE: THIN_EXECUTOR
```

E1 is pure contract only. No real Executor invocation occurs in TASK-040.

## 2. Allowed Files

Executor may create/modify only:

```text
src/aios_bridge/continuity/executor_transport.py
src/aios_bridge/continuity/__init__.py
tests/aios_bridge/continuity/test_executor_transport.py
```

Bridge publication may generate/update:

```text
.ai/results/RESULT-040.md
```

All other files are forbidden.

Explicitly forbidden:

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

Do not introduce an H-Series abstraction.

## 3. New Module

Create:

```text
src/aios_bridge/continuity/executor_transport.py
```

Module-level imports should remain pure and bounded. Expected imports:

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import re
from typing import Any, Protocol, runtime_checkable

from .errors import ContinuityStateValidationError
from .executor import (
    ExecutionOperation,
    ExecutionRequest,
    PreparedExecution,
    validate_prepared_execution_against_request,
)
from .lease import ExecutorLease, validate_executor_lease_binding
from .state import MAX_SERIALIZED_BYTES, SCHEMA_VERSION, _validate_actor_id, _validate_safe_git_ref
```

Forbidden imports in this module include:

```text
os
pathlib
subprocess
socket
urllib
requests
httpx
time
datetime
bridge
runtime_dispatch
runtime_lease
provider/model modules
```

`hashlib/json/re` are allowed pure helpers.

## 4. Constants / Validation Vocabulary

Define exact constants:

```python
MAX_INVOCATION_ID_LENGTH = 64
MAX_TRANSPORT_ID_LENGTH = 64
MAX_ERROR_CODE_LENGTH = 64
MAX_INVOCATION_PAYLOAD_BYTES = 1_048_576
MIN_PROCESS_EXIT_CODE = -2_147_483_648
MAX_PROCESS_EXIT_CODE = 2_147_483_647
```

Use conservative exact patterns:

```python
_TASK_ID_PATTERN = re.compile(r"^TASK-\d+$")
_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:[a-z0-9_.\-:]+)*$")
_ERROR_CODE_PATTERN = re.compile(r"^[A-Za-z0-9_.\-]+$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
```

Exact canonical means no trimming/case normalization.

Define an explicit forbidden-key set covering at least:

```text
approved
human_approved
authorization_token
merge_allowed
api_key
token
cookie
cookies
auth
auth_header
session_secret
payload
prompt
context
stdout
stderr
environment
env
command
cwd
```

Unknown fields are rejected regardless; the forbidden set exists to make authority/secret/raw-payload rejection explicit.

## 5. InvocationStatus

Define exactly:

```python
class InvocationStatus(str, Enum):
    EXITED_ZERO = "EXITED_ZERO"
    EXITED_NONZERO = "EXITED_NONZERO"
    FAILED_TO_START = "FAILED_TO_START"
    TIMED_OUT = "TIMED_OUT"
    INTERRUPTED = "INTERRUPTED"
```

No SUCCESS/PASS/MERGE status belongs here.

## 6. ExecutorInvocation

Define:

```python
@dataclass(frozen=True)
class ExecutorInvocation:
    schema_version: str
    invocation_id: str
    task_id: str
    request_id: str
    executor_id: str
    transport_id: str
    operation: ExecutionOperation
    workspace_id: str
    target_branch: str
    execution_id: str
    request_fingerprint: str
    prepared_execution_fingerprint: str
    lease_fingerprint: str
    execution_fingerprint: str
    payload_sha256: str
    payload_size_bytes: int
```

### Validation

`__post_init__` SHALL:
- require `schema_version == SCHEMA_VERSION`;
- validate exact task ID;
- validate `invocation_id`, `request_id`, `execution_id` using exact `_ID_PATTERN`, max 64;
- validate `transport_id` using exact `_ID_PATTERN`, max 64;
- validate executor ID using exact `_validate_actor_id` plus zero-whitespace equality;
- parse/validate `ExecutionOperation`, allowing only RUN/FIX;
- validate workspace/request/prepared/lease/execution/payload fingerprints as exact lowercase 64-hex;
- validate exact target branch using `_validate_safe_git_ref` plus zero-whitespace equality;
- require `payload_size_bytes` type exactly int (bool rejected), `1 <= value <= MAX_INVOCATION_PAYLOAD_BYTES`;
- enforce canonical serialized record <= `MAX_SERIALIZED_BYTES`.

### Serialization

Implement exactly the standard Continuity pattern:

```python
to_dict()
to_canonical_json()
fingerprint()
from_dict()
from_json()
```

`from_dict()`:
- root dict only;
- explicit forbidden authority/secret/raw-payload keys fail closed;
- unknown fields fail closed;
- every field required;
- no defaults that weaken identity.

`from_json()`:
- str/bytes only;
- exact UTF-8 for bytes;
- input byte size <= `MAX_SERIALIZED_BYTES`;
- malformed JSON fails closed.

## 7. validate_executor_invocation

Implement pure function:

```python
def validate_executor_invocation(
    invocation: ExecutorInvocation,
    execution_request: ExecutionRequest,
    prepared_execution: PreparedExecution,
    executor_lease: ExecutorLease,
) -> None:
```

Required sequence:
1. exact type checks for all four arguments;
2. call existing `validate_prepared_execution_against_request(prepared_execution, execution_request)`;
3. compare invocation schema/task/request/executor/operation/target branch against request;
4. require invocation `request_fingerprint == execution_request.fingerprint()`;
5. require invocation `execution_id == prepared_execution.execution_id`;
6. require invocation `prepared_execution_fingerprint == prepared_execution.fingerprint()`;
7. call existing `validate_executor_lease_binding(...)` using invocation task/workspace/executor/operation/execution fingerprint;
8. require invocation `lease_fingerprint == executor_lease.fingerprint()`;
9. require executor lease schema/task/executor/operation equal the invocation/request relationship.

Do not mutate or normalize any object.

Do not infer Human authorization from lease validity.

## 8. validate_invocation_payload

Implement:

```python
def validate_invocation_payload(
    invocation: ExecutorInvocation,
    payload: bytes,
) -> None:
```

Rules:
- invocation exact type;
- `type(payload) is bytes` exactly;
- non-empty;
- `len(payload) <= MAX_INVOCATION_PAYLOAD_BYTES`;
- exact length equals `invocation.payload_size_bytes`;
- `sha256(payload).hexdigest() == invocation.payload_sha256`.

No UTF-8 interpretation in E1. E3 owns payload semantic composition.

## 9. InvocationReceipt

Define exactly:

```python
@dataclass(frozen=True)
class InvocationReceipt:
    schema_version: str
    invocation_id: str
    task_id: str
    request_id: str
    executor_id: str
    transport_id: str
    operation: ExecutionOperation
    execution_id: str
    invocation_fingerprint: str
    status: InvocationStatus
    exit_code: int | None
    error_code: str | None
```

Validate canonical IDs/fingerprint/operation using the same exact helpers.

### Status matrix

`EXITED_ZERO`:

```text
exit_code = 0 exactly
error_code = None
```

`EXITED_NONZERO`:

```text
exit_code = exact int, bool rejected
MIN_PROCESS_EXIT_CODE <= exit_code <= MAX_PROCESS_EXIT_CODE
exit_code != 0
error_code = required bounded canonical error code
```

`FAILED_TO_START`, `TIMED_OUT`, `INTERRUPTED`:

```text
exit_code = None
error_code = required bounded canonical error code
```

`error_code` must have no whitespace padding, max 64, match `_ERROR_CODE_PATTERN`.

Implement same canonical methods:

```python
to_dict()
to_canonical_json()
fingerprint()
from_dict()
from_json()
```

Forbidden/unknown fields fail closed.
Canonical record <= `MAX_SERIALIZED_BYTES`.

## 10. validate_invocation_receipt

Implement:

```python
def validate_invocation_receipt(
    receipt: InvocationReceipt,
    invocation: ExecutorInvocation,
) -> None:
```

Fail closed unless exact equality of:

```text
schema_version
invocation_id
task_id
request_id
executor_id
transport_id
operation
execution_id
invocation_fingerprint == invocation.fingerprint()
```

Receipt status matrix is already constructor-enforced and must remain so.

## 11. ExecutionTransport Protocol

Define:

```python
@runtime_checkable
class ExecutionTransport(Protocol):
    @property
    def transport_id(self) -> str:
        ...

    @property
    def executor_id(self) -> str:
        ...

    def invoke(
        self,
        invocation: ExecutorInvocation,
        payload: bytes,
    ) -> InvocationReceipt:
        ...
```

This Protocol itself performs no I/O.

## 12. validate_transport_binding

Implement pure identity gate:

```python
def validate_transport_binding(
    transport: ExecutionTransport,
    invocation: ExecutorInvocation,
) -> None:
```

Required behavior:
- invocation exact type;
- transport must expose non-empty string `transport_id` and `executor_id`;
- no whitespace normalization;
- exact transport ID must equal invocation.transport_id;
- exact executor ID must equal invocation.executor_id;
- validate IDs conservatively;
- DO NOT call `transport.invoke()`.

A transport that claims another executor fails closed.

## 13. Public Exports

Update only `src/aios_bridge/continuity/__init__.py` to export:

```text
MAX_INVOCATION_PAYLOAD_BYTES
ExecutionTransport
ExecutorInvocation
InvocationReceipt
InvocationStatus
validate_executor_invocation
validate_invocation_payload
validate_invocation_receipt
validate_transport_binding
```

Do not otherwise reorganize existing imports/exports.

## 14. Test Construction Helpers

Create:

```text
tests/aios_bridge/continuity/test_executor_transport.py
```

Use neutral actors only, for example:

```text
executor-a
executor-b
transport-a
transport-b
```

Build valid M4 `ExecutionRequest` / `PreparedExecution` and M5 `ExecutorLease` directly from existing classes. Do not mock Bridge authorization as E1 does not consume it.

Use a deterministic payload such as:

```python
payload = b"bounded executor invocation payload\n"
```

Derive payload SHA mechanically.

## 15. Mandatory Tests

At minimum cover:

### Positive
- valid canonical RUN invocation round-trip;
- valid canonical FIX invocation round-trip;
- invocation binding to exact request/prepared/lease;
- exact payload validation;
- deterministic input ordering/canonical fingerprint behavior;
- valid EXITED_ZERO receipt;
- valid EXITED_NONZERO receipt;
- valid FAILED_TO_START receipt;
- valid TIMED_OUT receipt;
- valid INTERRUPTED receipt;
- receipt binding;
- neutral transport Protocol conformance;
- second/third neutral transport can conform without production change;
- `validate_transport_binding` accepts exact actor/transport pair.

### Identity/adversarial
- padded/noncanonical task/invocation/request/execution/executor/transport IDs;
- MERGE and unknown operation rejected;
- malformed uppercase/short/long SHA-256 fields;
- invalid/padded target branch;
- payload size 0, negative, bool, >1 MiB;
- request/task/executor/operation/branch mismatch;
- prepared request ID/execution ID/request fingerprint drift;
- prepared fingerprint mismatch;
- lease task/workspace/executor/operation/execution fingerprint drift;
- lease fingerprint mismatch;
- non-bytes payload including str, bytearray, memoryview;
- empty payload;
- length mismatch;
- SHA mismatch;
- one-byte payload tamper;
- transport ID mismatch;
- transport executor mismatch;
- prove `validate_transport_binding` never invokes the transport;
- receipt identity drift for every bound field;
- receipt invocation fingerprint mismatch;
- EXITED_ZERO with None/nonzero exit code;
- EXITED_ZERO with error_code;
- EXITED_NONZERO with None/zero/bool/out-of-range exit code;
- EXITED_NONZERO missing/malformed error_code;
- FAILED_TO_START/TIMED_OUT/INTERRUPTED carrying exit_code;
- failure status missing/malformed error_code;
- unknown field rejection;
- explicit authority/secret/raw payload field rejection;
- >16 KiB from_json rejection.

### Zero-I/O authority guard
AST/import inspection must prove `executor_transport.py` does not import or call:

```text
subprocess
os/pathlib filesystem APIs
git
bridge
runtime stores
dispatch
provider/model/network clients
approve/handoff/publish/commit/push
lease acquire/release
```

Importing the pure `lease` model/validator is allowed; calling a runtime lease store is forbidden.

## 16. No Real Transport in E1

No concrete `CodexLocalTransport` class in TASK-040.
No `codex` executable discovery.
No `shutil.which`.
No process spawn.
No CLI flags.
No SDK/API.
No context-pack rendering.
No auto publication.

Those are explicitly E2–E4.

## 17. Targeted Executor Commands

Executor runs only:

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_bridge/continuity/test_executor_transport.py -q
.\venv\Scripts\python.exe -m pytest tests/aios_bridge/continuity/test_executor.py tests/aios_bridge/test_runtime_lease.py tests/aios_bridge/continuity/test_dispatch.py -q
```

Do NOT run full repository suite.

Do NOT commit, push, publish, or merge.

## 18. Bridge Publication Gate

After targeted tests pass, Human runs:

```powershell
.\venv\Scripts\python.exe .\bridge.py publish 40 `
  --action RUN `
  --test ".\venv\Scripts\python.exe -m pytest tests/ -q"
```

Bridge owns full-suite, RESULT generation, commit, and push.

## 19. Acceptance

Final independent review requires:

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