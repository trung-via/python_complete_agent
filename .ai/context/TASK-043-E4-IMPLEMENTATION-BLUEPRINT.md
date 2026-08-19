# TASK-043 — E4 Result Collection + Auto Publication — Implementation Blueprint

STATUS: LOCKED BLUEPRINT

## 1. Baseline / Authority

```text
TASK_ID: TASK-043
MILESTONE: E4 — Result Collection + Auto Publication
BASELINE_MAIN_SHA: 91813c04160cb664af47c5f0b04fea37ef9aa076
TARGET_BRANCH: ai/task-043
ADR_PATH: .ai/decisions/ADR-032-E4-APPROVED-EXECUTOR-AUTOMATION-AND-AUTO-PUBLICATION-CONTRACT-LOCK.md
ADR_BLOB_SHA: 22c300f882327aa812ad5e3250bf53ba8cf85eb5
EXECUTOR_MODE: THIN_EXECUTOR
```

Existing production anchors on baseline:

```text
BRIDGE_BLOB_SHA: f0b28cdddc610ea330ec9403bd111bc37bc93ac1
M1_STATE_BLOB_SHA: 3b2c04169a85c54ccac1abe0736934cee1624af1
M4_EXECUTOR_BLOB_SHA: f144ea399c11f89809ecdf4f3d62098ee356ed7a
M5_LEASE_BLOB_SHA: 81a1373d6e04084b7c28d67699f4f613e4f0ee47
E1_TRANSPORT_CONTRACT_BLOB_SHA: bbe7b517202ea446e727752955e004d9464934bd
E2_CODEX_LOCAL_BLOB_SHA: dd1fae54506459a2a638441a35d5a327d89da8cc
E3_CONTEXT_COMPOSER_BLOB_SHA: 79a2f2c0f3f5f1c2de6dead7528dff62fee9e8c8
M10_RUNTIME_DISPATCH_BLOB_SHA: 01a35d0ffed48f2fbb70649f4c67f0e894910805
```

Do not modify those contract modules.

## 2. Allowed Files

Executor may modify/create only:

```text
bridge.py
src/aios_bridge/executor_automation.py
tests/aios_bridge/test_executor_automation.py
tests/test_bridge_executor_automation.py
```

Bridge publication may generate:

```text
.ai/results/RESULT-043.md
```

No other path.

Explicitly forbidden production changes:

```text
src/aios_bridge/continuity/**
src/aios_bridge/executor_transports/**
src/aios_bridge/executor_context.py
src/aios_bridge/runtime_dispatch.py
src/aios_bridge/runtime_lease.py
src/aios_bridge/external_brain/**
src/providers/**
docs/**
```

No E5, M11, or H-Series work.

## 3. Thin Executor Read Budget

Read only:

```text
bridge.py
src/aios_bridge/continuity/state.py
src/aios_bridge/continuity/executor.py
src/aios_bridge/continuity/lease.py
src/aios_bridge/continuity/executor_transport.py
src/aios_bridge/executor_context.py
src/aios_bridge/executor_transports/codex_local.py
src/aios_bridge/runtime_dispatch.py
```

and exact TASK / ADR / blueprint from `origin/ai-control`.

Read only the functions/types named by this blueprint when practical.
Do not broad-search repository unless a concrete blocker exists.

## 4. New Pure E-Series Helper Module

Create:

```text
src/aios_bridge/executor_automation.py
```

This is E4-specific composition/validation, not a generic Driver/Envelope/Event Journal abstraction.

Allowed imports are standard-library pure helpers plus existing M1/M4/M5/E3 contracts.
It MUST NOT import `bridge`, E2 transport, subprocess, os environment, provider/model SDKs, network libraries, runtime lease store, or runtime capacity store.

Expected imports conceptually:

```python
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Mapping, Sequence

from src.aios_bridge.continuity.errors import ContinuityStateValidationError
from src.aios_bridge.continuity.state import (
    ArtifactRef,
    BranchState,
    BrainState,
    ContinuityArtifacts,
    ContinuityPhase,
    ContinuityState,
    ExecutorState,
    FreshnessStatus,
    NextOperation,
    SCHEMA_VERSION,
    StateObservation,
    check_freshness,
)
from src.aios_bridge.continuity.executor import (
    ExecutionCapability,
    ExecutionOperation,
    ExecutionRequest,
    ExecutionResult,
    ExecutionResultStatus,
    ExecutorCapabilities,
    PreparedExecution,
    validate_execution_request_against_state,
    validate_execution_result_against_request,
    validate_executor_eligibility,
    validate_prepared_execution_against_request,
)
from src.aios_bridge.continuity.lease import ExecutorLease
from src.aios_bridge.executor_context import (
    ExecutorAuthorizationBinding,
    ExecutorContextPack,
    build_executor_context_pack,
)
```

## 5. Marker Constants / Models

Define:

```python
EXECUTOR_CONTEXT_REFS_MARKER = "EXECUTOR_CONTEXT_REFS_JSON:"
EXECUTOR_ALLOWED_PATHS_MARKER = "EXECUTOR_ALLOWED_PATHS_JSON:"
MAX_AUTOMATION_CONTEXT_REFS = 7
```

Implement immutable:

```python
@dataclass(frozen=True)
class ExecutorContextRefSpec:
    path: str
    blob_sha: str
```

Validation:
- path exact non-empty repository-relative POSIX string;
- must start `.ai/`;
- no absolute path, backslash, empty/dot/dot-dot segments;
- exact lowercase 40-hex blob SHA.

Implement immutable:

```python
@dataclass(frozen=True)
class ExecutorAutomationMarkers:
    context_refs: tuple[ExecutorContextRefSpec, ...]
    allowed_paths: tuple[str, ...]
```

## 6. Exact Marker Parser

Implement:

```python
def parse_executor_automation_markers(
    content: str,
    *,
    work_path: str,
) -> ExecutorAutomationMarkers:
```

Requirements:
- content exact `str`;
- exactly one line starting each marker prefix;
- malformed/missing/duplicate marker fails closed;
- context JSON root exact non-empty list with <=7 entries;
- every context entry exact object keys `{path, blob_sha}`;
- context paths unique;
- no context path equals `work_path`;
- allowed-path JSON root exact non-empty list of strings;
- allowed paths unique and preserve marker order;
- allowed path canonical repository-relative POSIX path;
- reject `.git` or `.git/**`;
- reject these Executor-writable namespaces:
  - `.ai/results/**`
  - `.ai/auth/**`
  - `.ai/inbox/**`
  - `.ai/state/**`
  - `.ai/bridge/**`
- reject control characters.

Do not infer paths from prose headings such as `Allowed Files`.

## 7. Deterministic IDs

Implement:

```python
@dataclass(frozen=True)
class ExecutorAutomationIds:
    request_id: str
    execution_id: str
    invocation_id: str
```

and:

```python
def derive_executor_automation_ids(
    task_id: str,
    lease_fingerprint: str,
) -> ExecutorAutomationIds:
```

Use exact 16-hex suffix from lease fingerprint and deterministic lowercase forms:

```text
req-task-043-<16hex>
exec-task-043-<16hex>
invoke-task-043-<16hex>
```

No timestamp/random input.

## 8. Pure Launch Plan

Implement immutable:

```python
@dataclass(frozen=True)
class ExecutorAutomationLaunchPlan:
    continuity_state: ContinuityState
    execution_request: ExecutionRequest
    prepared_execution: PreparedExecution
    context_pack: ExecutorContextPack
```

Implement public builder:

```python
def build_executor_automation_launch_plan(
    *,
    task_id: str,
    operation: ExecutionOperation,
    executor_id: str,
    main_branch: str,
    main_sha: str,
    target_branch: str,
    task_head_sha: str,
    work_ref: ArtifactRef,
    context_refs: tuple[ArtifactRef, ...],
    prior_result_ref: ArtifactRef | None,
    required_capabilities: tuple[ExecutionCapability, ...],
    executor_capabilities: ExecutorCapabilities,
    executor_lease: ExecutorLease,
    authorization_binding: ExecutorAuthorizationBinding,
    artifact_payloads: Mapping[str, bytes],
    transport_id: str,
) -> ExecutorAutomationLaunchPlan:
```

Locked sequence:

1. Exact types and task/action/executor/branch/lease relational validation.
2. Derive deterministic IDs from exact lease fingerprint.
3. RUN state:
   - phase RUNNING / WAIT_FOR_RESULT;
   - `work_ref` must be exact `.ai/tasks/<task_id>.md`;
   - task artifact = work_ref;
   - contracts = all context refs;
   - no prior result/review.
4. FIX state:
   - phase FIXING / WAIT_FOR_RESULT;
   - `work_ref` must be exact canonical review path;
   - context refs must contain exactly one exact canonical task path;
   - task artifact = that task ref;
   - contracts = remaining context refs preserving order;
   - prior_result_ref required and exact canonical RESULT path;
   - review artifact = work_ref.
5. Construct `ContinuityState` with:
   - exact main branch/SHA;
   - exact task branch/pre-execution HEAD;
   - `BrainState()`;
   - `ExecutorState(last_id=executor_id)`.
6. Construct explicit `StateObservation` from the exact launch facts/artifact blobs and require `check_freshness(...).status is FRESH`.
7. Construct M4 `ExecutionRequest`:
   - state fingerprint = exact continuity state fingerprint;
   - request ID = deterministic ID;
   - expected task head = pre-execution HEAD;
   - work/context refs unchanged;
   - required capabilities exact input;
   - expected result path exact `.ai/results/RESULT-NNN.md`.
8. Call `validate_execution_request_against_state()`.
9. Call `validate_executor_eligibility()` using exact policy candidate capabilities.
10. Construct `PreparedExecution` with deterministic execution ID and request fingerprint.
11. Call `validate_prepared_execution_against_request()`.
12. Call E3 `build_executor_context_pack()` with deterministic invocation ID and explicit transport ID.
13. Return launch plan.

The builder performs no I/O and never invokes E2.

## 9. Dirty Delta Validator

Implement pure:

```python
def validate_executor_worktree_delta(
    *,
    pre_branch: str,
    post_branch: str,
    pre_head_sha: str,
    post_head_sha: str,
    dirty_paths: Sequence[str],
    allowed_paths: Sequence[str],
) -> tuple[str, ...]:
```

Requirements:
- exact branch equality;
- exact pre/post 40-hex HEAD equality;
- dirty paths canonical, unique after normalization;
- dirty set non-empty;
- every dirty path in exact allowed set;
- return deterministic sorted tuple;
- never mutate/reset/stash/revert.

## 10. Post-Publication M4 Result Builder

Implement:

```python
def build_published_execution_result(
    request: ExecutionRequest,
    *,
    published_sha: str,
    result_ref: ArtifactRef,
) -> ExecutionResult:
```

Construct exact SUCCESS result:

```text
schema_version = request.schema_version
task_id = request.task_id
request_id = request.request_id
executor_id = request.executor_id
operation = request.operation
status = SUCCESS
implementation_sha = published_sha
result_ref = supplied exact RESULT ref
evidence_refs = ()
error_code = None
```

Call `validate_execution_result_against_request()` before return.

## 11. Bridge Imports

Modify `bridge.py` imports only as needed to reuse:
- M1/M4 types needed at orchestration edge;
- E3 `ExecutorAuthorizationBinding`;
- E2 `CodexLocalTransport`, constants/status;
- new E4 helper module functions/models;
- `ExecutorCapabilities` for M10 candidate conversion if not built in helper.

Do not modify existing contract modules.

## 12. Runtime Path

Extend `get_runtime_paths()` with one external namespace:

```text
executor_automation = <runtime-root>/executor_automation
```

This directory remains outside Git worktree.
Do not add tracked runtime files.

## 13. Exact Binary Git Helpers

Add Bridge-local bounded helpers conceptually:

```python
def resolve_git_blob_sha(ref: str, path: str) -> str:
    ... git rev-parse <ref>:<path> ...

def read_git_blob_bytes(ref: str, path: str) -> bytes:
    ... subprocess.run(["git", "cat-file", "blob", f"{ref}:{path}"], ... text=False, shell=False) ...
```

Requirements:
- no shell;
- exact bytes from stdout;
- nonzero Git status fails closed;
- no decoding/newline normalization in binary helper;
- stderr bounded/not persisted as raw execution evidence;
- no fallback to filesystem copies or `read_remote_file()` for E3 pack bytes.

## 14. Control Snapshot Resolver

Add Bridge-local helper conceptually:

```python
def resolve_e4_control_snapshot(cfg: dict, auth: dict) -> ...:
```

Sequence:
1. fetch control branch;
2. resolve exact remote control commit SHA;
3. work path = auth artifact path;
4. work blob at snapshot must equal auth artifact blob;
5. read work raw bytes;
6. strict UTF-8 decode only for marker/policy parsing;
7. parse E4 markers;
8. parse existing `DISPATCH_EXECUTOR_POLICY_JSON` from same exact work content;
9. policy operation must equal auth action;
10. find exact active executor candidate exactly once;
11. every context marker path resolves at same control snapshot to exact marker blob;
12. read every context as raw bytes;
13. construct immutable `ArtifactRef`s with `ref=control_commit_sha`;
14. artifact payload mapping uses exact raw bytes.

No history search.
No nearest control commit.

## 15. Main / Task / Prior Result Snapshot

Before launch:
- require current branch exact authorization branch;
- require current workspace ID exact auth workspace ID;
- require clean worktree;
- fetch configured remote base branch without changing task HEAD;
- resolve exact remote base SHA;
- resolve exact current task HEAD;
- for FIX resolve exact prior `.ai/results/RESULT-NNN.md` blob at pre-execution HEAD and create an `ArtifactRef`.

Do not rebase/merge task branch here.

## 16. Authorization / Lease / E3 Binding

`cmd_execute()` must:
1. load exact ACTIVE auth;
2. reconstruct expected lease using existing `reconstruct_expected_executor_lease()`;
3. require active exact lease via existing lease store;
4. require auth executor `codex`;
5. build E3 `ExecutorAuthorizationBinding` from exact auth fields;
6. build candidate `ExecutorCapabilities` from exact M10 policy candidate;
7. call pure E4 launch-plan builder.

No call to `store.acquire()` or approval function is allowed inside execute path.

## 17. E2 Invocation

Instantiate:

```python
CodexLocalTransport(
    PROJECT,
    codex_executable=args.codex_executable,
    timeout_seconds=args.timeout_seconds,
)
```

then call exactly once:

```python
receipt = transport.invoke(
    launch.context_pack.invocation,
    launch.context_pack.payload,
)
```

No retry loop.
No recursive Codex invocation in TASK-043 tests.

## 18. Complete Dirty-Path Collection

Add a Bridge-local collector that does NOT rely only on the old `changed_files()` parser.

Use Git evidence conceptually:

```text
git diff --name-status HEAD
git ls-files --others --exclude-standard
```

Parse tracked/staged/unstaged changes relative to HEAD and untracked files.
For rename/copy rows include both old and new paths.
Reject malformed Git output.
Return deterministic unique POSIX paths.

This collector is used only for E4 post-executor scope gate; existing `changed_files()` may remain unchanged for compatibility.

## 19. External Execution Receipt

Persist after E2 returns and after collecting post-execution branch/HEAD/dirty facts, before auto-publication.

Path conceptually:

```text
<runtime>/executor_automation/TASK-043/<invocation_fingerprint>.json
```

Record exact keys only:

```text
schema_version
task_id
action
executor_id
transport_id
control_commit_sha
pre_head_sha
post_head_sha
pre_branch
post_branch
manifest_fingerprint
invocation_fingerprint
payload_sha256
payload_size_bytes
invocation_receipt
invocation_receipt_fingerprint
dirty_paths
published_sha            # initially null; may be filled after publication
result_blob_sha          # initially null; may be filled after publication
execution_result_fingerprint  # initially null; may be filled after publication
```

No raw payload/prompt/stdout/stderr/secrets.

Use existing external `save_json()` and exact read-back equality.
If initial write/read-back fails, no auto-publish.

## 20. Transport Status Gate

After initial receipt persistence:

```text
FAILED_TO_START -> no publish
EXITED_NONZERO  -> no publish
TIMED_OUT       -> no publish
INTERRUPTED     -> no publish
EXITED_ZERO     -> continue only after all Git/scope gates
```

For branch/HEAD drift or partial uncertain execution, update operational state to `RECOVERY_REQUIRED` and fail.
For clean FAILED_TO_START, a bounded `EXECUTION_BLOCKED` operational status is acceptable.

Do not release lease automatically on E4 failure.

## 21. Auto Publication

For EXITED_ZERO only:
1. call `validate_executor_worktree_delta()` with exact allowed paths;
2. build fixed full-suite command from current `sys.executable`:

```text
<current python> -m pytest tests/ -q
```

Use platform-safe quoting (`subprocess.list2cmdline` on Windows; `shlex.join` on POSIX) because legacy `cmd_publish` accepts one command string.
Do not read test command from TASK/REVIEW/caller.
3. construct an `argparse.Namespace` compatible with existing `cmd_publish()`:

```text
task_id = current task
action = exact auth action
test = fixed full suite command
summary = "Implementation completed by codex through E4 approved automatic execution; pending ChatGPT review."
notes = bounded E4 evidence block
message = None
```

Evidence notes must include at least:

```text
E4_AUTO_EXECUTION: YES
E4_CONTROL_COMMIT_SHA: ...
E4_CONTEXT_MANIFEST_FINGERPRINT: ...
E4_INVOCATION_FINGERPRINT: ...
E4_INVOCATION_RECEIPT_FINGERPRINT: ...
E4_TRANSPORT_STATUS: EXITED_ZERO
E4_PRE_EXECUTION_HEAD: ...
E4_ALLOWED_SCOPE_VERIFIED: PASS
```

Then call existing `cmd_publish()` exactly once.
Do not duplicate its test/result/commit/push/lease/auth logic.

## 22. Post-Publish Verification

After successful return from `cmd_publish()`:
1. reload auth;
2. require `status == CONSUMED`;
3. require exact `published_sha` 40-hex;
4. require branch HEAD == published SHA;
5. resolve exact RESULT blob at `published_sha`;
6. create `ArtifactRef(path=request.expected_result_path, ref=request.target_branch, blob_sha=result_blob)`;
7. call pure `build_published_execution_result()`;
8. update external E4 receipt with `published_sha`, `result_blob_sha`, and execution result fingerprint;
9. read back exact record.

If this post-publish integrity step fails, set `RECOVERY_REQUIRED` and fail without history rewrite/force push.

## 23. CLI

Add:

```text
bridge.py execute <task_id>
    [--codex-executable codex]
    [--timeout-seconds 1800]
```

Default timeout should reuse E2 `DEFAULT_CODEX_TIMEOUT_SECONDS`.
E2 validates maximum.

Modify successful `cmd_approve()` final guidance only:
- if selected executor is `codex`, tell Human to run `bridge.py execute <task_id>`;
- other executors retain existing manual `/aios-worker` guidance.

Do NOT auto-call execute from approve.

## 24. Public Helper Surface

`src/aios_bridge/executor_automation.py.__all__` should expose only:

```text
EXECUTOR_ALLOWED_PATHS_MARKER
EXECUTOR_CONTEXT_REFS_MARKER
MAX_AUTOMATION_CONTEXT_REFS
ExecutorAutomationIds
ExecutorAutomationLaunchPlan
ExecutorAutomationMarkers
ExecutorContextRefSpec
build_executor_automation_launch_plan
build_published_execution_result
derive_executor_automation_ids
parse_executor_automation_markers
validate_executor_worktree_delta
```

## 25. Unit Tests

Create:

```text
tests/aios_bridge/test_executor_automation.py
```

Pure tests only; no subprocess/model call.
Cover:
- valid RUN markers;
- valid FIX markers;
- duplicate/missing/malformed markers;
- blob/path validation;
- allowed path sensitive namespace rejection;
- deterministic IDs;
- valid RUN launch M1/M4/E3 composition;
- valid FIX launch with prior result;
- FIX task context missing -> reject;
- M1 freshness semantics;
- M4 eligibility mismatch;
- request/prepared/context-pack exact bindings;
- deterministic repeat build;
- worktree delta pass;
- branch drift/head drift/empty/out-of-scope/rename-source-dest cases;
- published M4 ExecutionResult pass and mismatch rejects;
- AST purity: no subprocess/os/network/bridge/E2/provider imports.

## 26. Bridge Integration Tests

Create:

```text
tests/test_bridge_executor_automation.py
```

Use temporary real Git repositories where Git byte/status semantics matter and mocks/fakes for remote/control/transport/publisher as appropriate.

MUST NOT invoke real Codex.

Required cases:
- raw Git blob helper preserves CRLF+BOM exact bytes;
- context/control blob drift blocks before fake transport invoke;
- no ACTIVE auth -> zero invoke;
- wrong lease/workspace/branch -> zero invoke;
- non-codex executor -> zero invoke;
- dispatch policy mismatch/ineligible -> zero invoke;
- fake E2 EXITED_ZERO + allowed mutation -> publisher exactly once;
- fake E2 EXITED_ZERO + new untracked out-of-scope file -> zero publisher;
- fake E2 EXITED_ZERO + committed HEAD advance -> zero publisher;
- FAILED_TO_START/NONZERO/TIMEOUT/INTERRUPTED -> zero publisher;
- external evidence write/read-back failure -> zero publisher;
- no automatic retry (invoke count exactly one);
- auto-publish Namespace uses exact auth action and fixed full-suite command;
- E4 evidence notes are bounded and contain no raw payload;
- successful fake publisher post-state produces canonical M4 ExecutionResult;
- post-publish integrity mismatch sets recovery-required;
- `execute` never calls lease acquire / approve / merge.

## 27. Targeted Commands

Executor runs only:

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_bridge/test_executor_automation.py tests/test_bridge_executor_automation.py -q

.\venv\Scripts\python.exe -m pytest tests/aios_bridge/test_executor_context_pack.py tests/aios_bridge/test_codex_local_transport.py tests/aios_bridge/continuity/test_executor_transport.py tests/aios_bridge/continuity/test_executor.py tests/aios_bridge/test_runtime_lease.py tests/test_bridge.py -q
```

Do NOT run the full repository suite.
Do NOT run `bridge.py execute 43` from TASK-043 implementation/tests.
Do NOT invoke real Codex recursively.

When targeted tests pass:
- report files changed;
- report targeted test counts;
- report blockers;
- STOP.

Do not commit.
Do not push.
Do not publish.

## 28. Publication

Human still publishes TASK-043 manually because E4 is the feature being implemented:

```powershell
.\venv\Scripts\python.exe .\bridge.py publish 43 `
  --action RUN `
  --test ".\venv\Scripts\python.exe -m pytest tests/ -q"
```

Bridge owns full-suite, RESULT, commit, and push.

## 29. Acceptance

PASS requires all ADR-032 acceptance fields plus:

```text
EXECUTE_COMMAND_ADDED: PASS
APPROVE_EXECUTE_SEPARATION: PASS
CODEX_ONLY_AUTOMATION_V1: PASS
CONTEXT_MARKER_TRANSITIVE_BINDING: PASS
ALLOWED_SCOPE_MARKER: PASS
RAW_GIT_BYTES_PRESERVED: PASS
CONTROL_SINGLE_SNAPSHOT: PASS
M1_LAUNCH_STATE_FRESH: PASS
M4_REQUEST_PREPARED_VALID: PASS
M10_ELIGIBILITY_VALID: PASS
E3_PACK_VALID: PASS
FAKE_E2_SINGLE_INVOKE: PASS
POST_EXEC_HEAD_IMMUTABLE: PASS
OUT_OF_SCOPE_BLOCKED: PASS
EXTERNAL_RECEIPT_NO_RAW_CONTEXT: PASS
EXISTING_CMD_PUBLISH_REUSED: PASS
FIXED_FULL_SUITE_COMMAND: PASS
POST_PUBLISH_M4_RESULT: PASS
NO_AUTO_RETRY: PASS
NO_AUTO_MERGE: PASS
FULL_REPO_TESTS: PASS
REGRESSIONS: 0
FINAL_INDEPENDENT_AUDIT: PASS
E4: PASS
```
