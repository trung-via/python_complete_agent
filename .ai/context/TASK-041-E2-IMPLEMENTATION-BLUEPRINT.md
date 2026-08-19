# TASK-041 — E2 Codex Local Transport — Implementation Blueprint

STATUS: LOCKED BLUEPRINT

## 1. Baseline / Authority

```text
TASK_ID: TASK-041
MILESTONE: E2 — Codex Local Transport
BASELINE_MAIN_SHA: 1c35ce096f366d9d87250b5e8ae1759327dc5a51
TARGET_BRANCH: ai/task-041
ADR_PATH: .ai/decisions/ADR-030-E2-CODEX-LOCAL-TRANSPORT-CONTRACT-LOCK.md
ADR_BLOB_SHA: e5c0dd2214ea81ae01e903847d4563ab88f983cb
E1_CONTRACT_PATH: src/aios_bridge/continuity/executor_transport.py
E1_CONTRACT_BLOB_SHA: bbe7b517202ea446e727752955e004d9464934bd
EXECUTOR_MODE: THIN_EXECUTOR
```

E2 adds one concrete local Codex process transport. It does not integrate it into Bridge.

## 2. Allowed Files

Executor may create only:

```text
src/aios_bridge/executor_transports/__init__.py
src/aios_bridge/executor_transports/codex_local.py
tests/aios_bridge/test_codex_local_transport.py
```

Bridge publication may generate:

```text
.ai/results/RESULT-041.md
```

All other files are forbidden.

Explicitly forbidden modifications:

```text
bridge.py
src/aios_bridge/continuity/executor_transport.py
src/aios_bridge/continuity/executor.py
src/aios_bridge/continuity/lease.py
src/aios_bridge/continuity/dispatch.py
src/aios_bridge/runtime_dispatch.py
src/aios_bridge/runtime_lease.py
src/aios_bridge/continuity/hot_handoff.py
src/aios_bridge/continuity/executor_failover.py
src/aios_bridge/external_brain/**
src/providers/**
docs/**
```

No H-Series abstraction.

## 3. Read Budget

Read only:

```text
src/aios_bridge/continuity/executor_transport.py
src/aios_bridge/continuity/errors.py
docs/AIOS_CODEX_EXECUTOR_WINDOWS.md
```

plus the exact TASK / ADR / blueprint from `origin/ai-control`.

Do not broad-search the repository.

## 4. New Package

Create:

```text
src/aios_bridge/executor_transports/__init__.py
src/aios_bridge/executor_transports/codex_local.py
```

`__init__.py` shall export only the E2 public concrete transport surface:

```text
CODEX_EXECUTOR_ID
CODEX_TRANSPORT_ID
DEFAULT_CODEX_TIMEOUT_SECONDS
CodexLocalTransport
```

Do not re-export it from Continuity Core.

## 5. Imports for codex_local.py

Expected bounded imports:

```python
from __future__ import annotations

import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
from typing import Mapping

from src.aios_bridge.continuity.errors import ContinuityStateValidationError
from src.aios_bridge.continuity.executor_transport import (
    ExecutionTransport,
    ExecutorInvocation,
    InvocationReceipt,
    InvocationStatus,
    validate_invocation_payload,
    validate_invocation_receipt,
    validate_transport_binding,
)
```

Do not import `bridge`, dispatcher, runtime stores, lease store, providers, model SDKs, HTTP clients, browser modules, or External Brain.

`ExecutionTransport` import exists for conformance/type clarity; no subclassing is required because it is a Protocol.

## 6. Constants

Define exactly:

```python
CODEX_EXECUTOR_ID = "codex"
CODEX_TRANSPORT_ID = "codex-local-v1"
DEFAULT_CODEX_TIMEOUT_SECONDS = 1800
MAX_CODEX_TIMEOUT_SECONDS = 7200

ERROR_CODEX_NOT_FOUND = "CODEX_NOT_FOUND"
ERROR_CODEX_START_FAILED = "CODEX_START_FAILED"
ERROR_WORKSPACE_PRECONDITION_FAILED = "WORKSPACE_PRECONDITION_FAILED"
ERROR_CODEX_EXIT_NONZERO = "CODEX_EXIT_NONZERO"
ERROR_CODEX_TIMEOUT = "CODEX_TIMEOUT"
ERROR_CALLER_INTERRUPTED = "CALLER_INTERRUPTED"
ERROR_CODEX_EXIT_CODE_INVALID = "CODEX_EXIT_CODE_INVALID"
```

All error codes fit the E1 canonical error-code domain.

## 7. Environment Allowlist

Define closed sets, not prefix matching.

Windows allowlist should be sufficient for ordinary process/auth resolution and may contain only OS/runtime basics such as:

```text
PATH
PATHEXT
SystemRoot
WINDIR
COMSPEC
USERPROFILE
HOMEDRIVE
HOMEPATH
LOCALAPPDATA
APPDATA
TEMP
TMP
CODEX_HOME
LANG
LC_ALL
TERM
```

POSIX allowlist may contain only basics such as:

```text
PATH
HOME
USER
LOGNAME
SHELL
TMPDIR
LANG
LC_ALL
TERM
CODEX_HOME
```

Define explicit deny set containing at least:

```text
OPENAI_API_KEY
ANTHROPIC_API_KEY
GOOGLE_API_KEY
GEMINI_API_KEY
DEEPSEEK_API_KEY
MINIMAX_API_KEY
GITHUB_TOKEN
GH_TOKEN
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_SESSION_TOKEN
AZURE_OPENAI_API_KEY
```

Implement pure-ish helper:

```python
def _build_child_environment(source: Mapping[str, str]) -> dict[str, str]:
```

Requirements:
- copy only exact allowlisted keys present in source;
- explicitly remove every denylisted key even if accidentally added to allowlist later;
- no `source` mutation;
- no secret values logged or returned elsewhere;
- use `os.name` only to choose Windows vs POSIX allowlist.

Do not forward the whole parent environment and then delete a few keys.

## 8. Timeout Validation

Implement:

```python
def _validate_timeout_seconds(value: object) -> int:
```

Require:
- `type(value) is int` exactly;
- `1 <= value <= MAX_CODEX_TIMEOUT_SECONDS`;
- bool rejected.

Raise `ContinuityStateValidationError` on invalid constructor input.

## 9. Codex Executable Resolution

Implement:

```python
def _resolve_codex_executable(spec: str) -> str | None:
```

Rules:
- `spec` must be exact non-empty string with no leading/trailing whitespace;
- if it contains a path separator or is absolute, require an existing file and return its resolved path string;
- otherwise resolve with `shutil.which(spec)`;
- no recursive search;
- no install/upgrade;
- no shell lookup command.

Default constructor spec:

```text
codex
```

Do not resolve at import time.

## 10. Workspace Resolution

Constructor accepts one exact workspace path.

Resolve it once during construction or invoke using `Path.resolve(strict=True)`.

Require directory.

Do not create the directory.

Do not change process-global cwd.

## 11. Read-Only Git Preflight

Implement a private helper that uses argument arrays and `shell=False` only.

Required checks:

### exact toplevel

```text
git -C <workspace> rev-parse --show-toplevel
```

Resolve returned path and require it equals exact workspace path.

### exact branch

```text
git -C <workspace> branch --show-current
```

Require exact stdout (after terminal newline removal only) equals `invocation.target_branch`.

Detached HEAD / empty branch fails.

### clean worktree

```text
git -C <workspace> status --porcelain --untracked-files=all
```

Require empty stdout.

Use bounded timeout for each Git preflight command, e.g. 10 seconds.

No Git mutation commands.

Any preflight failure returns a `FAILED_TO_START` receipt with:

```text
WORKSPACE_PRECONDITION_FAILED
```

Do not attempt repair.

The Git subprocess environment should use the same minimal child environment plus safe locale values if needed. Never forward secrets merely for Git.

## 12. Exact Codex argv Builder

Implement private helper equivalent to:

```python
def _build_codex_argv(executable: str, workspace: Path) -> list[str]:
```

It must return exactly one argument vector equivalent to:

```text
<resolved-codex>
exec
--ephemeral
--json
--color
never
--sandbox
workspace-write
--ask-for-approval
never
-c
sandbox_workspace_write.network_access=false
-c
web_search="disabled"
-C
<exact-workspace>
-
```

Order shall be stable and tested exactly.

Forbidden tokens anywhere in argv:

```text
--dangerously-bypass-approvals-and-sandbox
danger-full-access
--skip-git-repo-check
--add-dir
--full-auto
```

Payload bytes MUST NOT appear in argv.

Do not use shell command strings.

## 13. CodexLocalTransport

Implement a small final-style concrete class, no inheritance hierarchy needed:

```python
class CodexLocalTransport:
    def __init__(
        self,
        workspace: str | Path,
        *,
        codex_executable: str = "codex",
        timeout_seconds: int = DEFAULT_CODEX_TIMEOUT_SECONDS,
    ) -> None:
        ...

    @property
    def transport_id(self) -> str:
        return CODEX_TRANSPORT_ID

    @property
    def executor_id(self) -> str:
        return CODEX_EXECUTOR_ID

    def invoke(
        self,
        invocation: ExecutorInvocation,
        payload: bytes,
    ) -> InvocationReceipt:
        ...
```

Do not add dispatch/authorization/lease/publication methods.

## 14. invoke() Required Sequence

The sequence is locked:

1. `validate_transport_binding(self, invocation)`.
2. `validate_invocation_payload(invocation, payload)`.
3. validate configured workspace path.
4. run exact read-only Git preflight against `invocation.target_branch`.
5. resolve Codex executable.
6. build exact minimal child environment.
7. build exact argv.
8. spawn one process with `shell=False`, exact workspace cwd, stdin PIPE, stdout/stderr DEVNULL.
9. send exact payload via `communicate(input=payload, timeout=...)`.
10. map transport outcome to canonical receipt.
11. `validate_invocation_receipt(receipt, invocation)`.
12. return receipt.

No retry.
No fallback argv.
No second Codex process.
No payload mutation.

## 15. Process Creation

Use `subprocess.Popen`, not `os.system` and not shell invocation.

Required settings:

```text
cwd = exact workspace
stdin = subprocess.PIPE
stdout = subprocess.DEVNULL
stderr = subprocess.DEVNULL
shell = False
env = minimal child environment
```

For POSIX, use `start_new_session=True` to obtain a killable process group.

For Windows, use `subprocess.CREATE_NEW_PROCESS_GROUP` when available.

Do not use `CREATE_NEW_CONSOLE`.

Do not persist stdout/stderr/final message in E2.

## 16. Receipt Construction Helper

Implement one private helper so every receipt is constructed with identity copied mechanically from `invocation`:

```python
def _make_receipt(
    invocation: ExecutorInvocation,
    *,
    status: InvocationStatus,
    exit_code: int | None,
    error_code: str | None,
) -> InvocationReceipt:
```

Fields copied exactly:

```text
schema_version
invocation_id
task_id
request_id
executor_id
transport_id
operation
execution_id
invocation_fingerprint = invocation.fingerprint()
```

Always call `validate_invocation_receipt` before return from `invoke`.

## 17. Outcome Mapping

### executable missing

No spawn:

```text
FAILED_TO_START
exit_code = None
error_code = CODEX_NOT_FOUND
```

### preflight failure

```text
FAILED_TO_START
exit_code = None
error_code = WORKSPACE_PRECONDITION_FAILED
```

### Popen OSError / launch failure

```text
FAILED_TO_START
exit_code = None
error_code = CODEX_START_FAILED
```

### exit 0

```text
EXITED_ZERO
exit_code = 0
error_code = None
```

### normal nonzero int within signed 32-bit range

```text
EXITED_NONZERO
exit_code = returncode
error_code = CODEX_EXIT_NONZERO
```

### return code outside E1 domain

```text
FAILED_TO_START
exit_code = None
error_code = CODEX_EXIT_CODE_INVALID
```

### timeout

terminate process group/tree best-effort, then:

```text
TIMED_OUT
exit_code = None
error_code = CODEX_TIMEOUT
```

### KeyboardInterrupt

terminate process group/tree best-effort, then:

```text
INTERRUPTED
exit_code = None
error_code = CALLER_INTERRUPTED
```

Do not convert `EXITED_ZERO` into task SUCCESS.

## 18. Process Cleanup

Implement private best-effort cleanup with bounded behavior.

POSIX:
- if process still alive and has its own session/process group, send SIGTERM to group;
- bounded wait;
- SIGKILL group if still alive.

Windows:
- first attempt direct terminate/kill on process;
- a bounded `taskkill /PID <pid> /T /F` may be used only for cleanup and only with argument-vector `shell=False`;
- discard cleanup stdout/stderr;
- cleanup failure must not trigger a second Codex invocation.

Do not raise a cleanup exception over the primary timeout/interruption result unless process creation state is internally inconsistent.

Tests monkeypatch cleanup boundaries; do not spawn real Codex.

## 19. Tests

Create:

```text
tests/aios_bridge/test_codex_local_transport.py
```

Use E1 canonical test fixture builders locally in this file. Do not import helper functions from another test module.

Use neutral canonical request/prepared/lease records only as needed to construct a valid `ExecutorInvocation` with:

```text
executor_id = codex
transport_id = codex-local-v1
```

Payload example:

```python
PAYLOAD = b"E2 bounded transport payload\n"
```

No real Codex/model call in pytest.

Monkeypatch:
- `subprocess.run` for Git preflight;
- `subprocess.Popen` for Codex process;
- `shutil.which` for discovery;
- environment mapping as needed;
- cleanup helper where platform-dependent.

## 20. Mandatory Test Matrix

At minimum:

### Protocol / command
- `isinstance(transport, ExecutionTransport)`;
- exact IDs;
- exact stable argv equality;
- final positional `-`;
- exact workspace via `-C`;
- no forbidden argv tokens;
- payload bytes absent from argv;
- `shell=False`;
- stdout/stderr DEVNULL;
- exact stdin bytes reach `communicate` unchanged.

### Workspace preflight
- valid exact Git toplevel/branch/clean state;
- missing workspace;
- non-directory workspace;
- git command nonzero;
- toplevel mismatch;
- wrong branch;
- detached/empty branch;
- dirty tracked file;
- dirty untracked file;
- preflight refusal does not spawn Codex.

### Environment
- only allowlisted OS/Codex keys copied;
- arbitrary env var stripped;
- every explicit secret key stripped;
- `OPENAI_API_KEY` stripped even when present;
- input environment not mutated.

### E1 validation
- wrong executor rejected before preflight/spawn;
- wrong transport rejected before preflight/spawn;
- payload one-byte mutation rejected before preflight/spawn;
- payload non-bytes rejected;
- no payload normalization.

### Process outcomes
- missing executable -> FAILED_TO_START / CODEX_NOT_FOUND;
- Popen OSError -> FAILED_TO_START / CODEX_START_FAILED;
- zero -> EXITED_ZERO;
- positive nonzero -> EXITED_NONZERO;
- negative nonzero within domain -> EXITED_NONZERO;
- out-of-domain return -> FAILED_TO_START / CODEX_EXIT_CODE_INVALID;
- TimeoutExpired -> cleanup + TIMED_OUT;
- KeyboardInterrupt -> cleanup + INTERRUPTED;
- no retry after any failure;
- one invocation means at most one Codex process spawn.

### Authority/scope guards
AST/import inspection proves the module does not import/call:

```text
bridge
runtime_dispatch
runtime_lease
dispatch_executor
approve
handoff
publish
commit
push
merge
ExecutorLease store acquire/release
provider/model SDK
requests/httpx/urllib
browser
```

Also assert source contains no:

```text
--dangerously-bypass-approvals-and-sandbox
danger-full-access
--skip-git-repo-check
--add-dir
resume
```

except test strings that assert their absence from argv; production source must not construct/use them.

## 21. No Real Codex Smoke Inside Executor Run

The Codex Executor implementing TASK-041 MUST NOT recursively launch another real Codex session during its own execution.

E2 pytest uses process doubles only.

A real installed-CLI smoke/proof is deferred to a Human-controlled follow-up after E2 is independently reviewed/merged, and ultimately to E5 operational proof.

This prevents nested Codex sessions and accidental double quota consumption while building the transport.

## 22. Targeted Executor Commands

Run ONLY:

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_bridge/test_codex_local_transport.py -q

.\venv\Scripts\python.exe -m pytest tests/aios_bridge/continuity/test_executor_transport.py tests/aios_bridge/continuity/test_executor.py tests/aios_bridge/test_runtime_lease.py -q
```

Do NOT run the full repository suite.

Do NOT invoke real Codex from the tests.

Do NOT commit, push, publish, or merge.

## 23. Bridge Publication Gate

After targeted tests pass, Human runs:

```powershell
.\venv\Scripts\python.exe .\bridge.py publish 41 `
  --action RUN `
  --test ".\venv\Scripts\python.exe -m pytest tests/ -q"
```

Bridge owns full-suite, RESULT generation, commit, and push.

## 24. Acceptance

Final independent review requires:

```text
CODEX_LOCAL_TRANSPORT_CONCRETE: PASS
E1_PROTOCOL_CONFORMANCE: PASS
EXACT_STDIN_PAYLOAD: PASS
SAFE_CODEX_EXEC_ARGV: PASS
WORKSPACE_BRANCH_PREFLIGHT: PASS
DIRTY_WORKTREE_FAIL_CLOSED: PASS
SUBSCRIPTION_FIRST_ENVIRONMENT: PASS
SECRET_ENV_STRIPPING: PASS
TOOL_NETWORK_DISABLED: PASS
DANGER_BYPASS_FORBIDDEN: PASS
PROCESS_STATUS_MAPPING: PASS
TIMEOUT_INTERRUPT_CLEANUP: PASS
EXIT_ZERO_IS_TRANSPORT_ONLY: PASS
NO_REAL_CODEX_IN_TESTS: PASS
NO_BRIDGE_INTEGRATION: PASS
H_SERIES_REMAINS_DEFERRED: PASS
FULL_REPO_TESTS: PASS
REGRESSIONS: 0
FINAL_INDEPENDENT_AUDIT: PASS
E2: PASS
```

Only Human may authorize merge.