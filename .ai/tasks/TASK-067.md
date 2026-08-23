# TASK-067 — Codex Transport Diagnostic & Reliability Hardening

STATUS: READY
CLASS: L2 — AIOS BRIDGE SUPPORTING REFINEMENT / LOCAL-EXECUTOR OBSERVABILITY
MILESTONE: E2.2 / E4.1 SUPPORTING HARDENING BETWEEN H0 AND H1
EXECUTOR_MODE: ANTIGRAVITY_ONLY_BOUNDED_REPAIR
RECOMMENDED_EXECUTOR: antigravity

## Baseline

```text
MAIN_SHA: 75866e0e033364fbcc308904e9b8e7572e8d2f48
TARGET_BRANCH: ai/task-067
H0_STATUS: COMPLETE
H1_STARTED: NO
M11_STATUS: OPERATIONALLY_PROVEN / CLOSED
M12_CREATED: NO
REAL_CODEX_PROOF_DURING_TASK: FORBIDDEN
PAID_API_CALL_ALLOWED: NO
AUTO_RETRY_ALLOWED: NO
AUTO_REROUTE_ALLOWED: NO
```

TASK-067 is the bounded post-H0 refinement approved before H1. It does not reopen M11 and is not an H-Series milestone. Its purpose is to make the existing Codex local execution path observable enough to diagnose real no-delta/nonzero failures without weakening any authority, sandbox, or publication gate.

## Observed Problem

Current merged `CodexLocalTransport` safely launches the exact bounded Codex CLI process but routes:

```text
stdout = subprocess.DEVNULL
stderr = subprocess.DEVNULL
```

E4 currently persists canonical `InvocationReceipt` and Git/worktree evidence, but raw process diagnostics are unavailable after a failure.

Real evidence already observed:

```text
TASK-064 Codex attempt:
  EXITED_ZERO
  dirty_paths = []
  E4 rejected: Executor produced no worktree delta

TASK-066 Codex attempt:
  EXITED_NONZERO
  exit_code = 1
  dirty_paths = []
  no publication
  no retry
```

Safety behavior is correct. Diagnostic observability is insufficient.

## Authoritative Context

```text
ADR_040_PATH: .ai/decisions/ADR-040-CODEX-LOCAL-TRANSPORT-BOUNDED-DIAGNOSTIC-OBSERVABILITY-CONTRACT-LOCK.md
ADR_040_BLOB_SHA: 04937776829675e77a1651152bba16e7e7f31426

ADR_030_PATH: .ai/decisions/ADR-030-E2-CODEX-LOCAL-TRANSPORT-CONTRACT-LOCK.md
ADR_030_BLOB_SHA: e5c0dd2214ea81ae01e903847d4563ab88f983cb

ADR_032_PATH: .ai/decisions/ADR-032-E4-APPROVED-EXECUTOR-AUTOMATION-AND-AUTO-PUBLICATION-CONTRACT-LOCK.md
ADR_032_BLOB_SHA: 22c300f882327aa812ad5e3250bf53ba8cf85eb5

ADR_034_PATH: .ai/decisions/ADR-034-E2.1-CODEX-CLI-GLOBAL-APPROVAL-FLAG-COMPATIBILITY-CONTRACT-LOCK.md
ADR_034_BLOB_SHA: cbe66ff7ae5db159ed96c0310f1271d9527d3bae
```

## Machine-Readable Executor Context

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/decisions/ADR-040-CODEX-LOCAL-TRANSPORT-BOUNDED-DIAGNOSTIC-OBSERVABILITY-CONTRACT-LOCK.md","blob_sha":"04937776829675e77a1651152bba16e7e7f31426"},{"path":".ai/decisions/ADR-030-E2-CODEX-LOCAL-TRANSPORT-CONTRACT-LOCK.md","blob_sha":"e5c0dd2214ea81ae01e903847d4563ab88f983cb"},{"path":".ai/decisions/ADR-032-E4-APPROVED-EXECUTOR-AUTOMATION-AND-AUTO-PUBLICATION-CONTRACT-LOCK.md","blob_sha":"22c300f882327aa812ad5e3250bf53ba8cf85eb5"},{"path":".ai/decisions/ADR-034-E2.1-CODEX-CLI-GLOBAL-APPROVAL-FLAG-COMPATIBILITY-CONTRACT-LOCK.md","blob_sha":"cbe66ff7ae5db159ed96c0310f1271d9527d3bae"}]

## Exact Writable Scope

EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","src/aios_bridge/executor_transports/__init__.py","src/aios_bridge/executor_transports/codex_local.py","tests/aios_bridge/test_codex_local_transport.py","tests/test_bridge_executor_automation.py"]

Bridge-generated `.ai/results/RESULT-067.md` is publication output only.

No other file may be modified. If implementation appears to require changing E1 schemas, executor context composition, dispatch, lease, H-Series, worker surfaces, provider code, dependencies, or task/review/decision artifacts, STOP rather than widening scope.

## Executor Dispatch Policy

DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN","FIX"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

TASK-067 is intentionally Antigravity-only because the Codex transport itself is the component under repair. This is a task-specific incompatibility boundary, not removal of Codex from AIOS.

Do not execute TASK-067 using `$aios-worker` / Codex.

## Locked Non-Changes

The following existing semantics are immutable during TASK-067:

```text
CODEX_EXECUTOR_ID = codex
CODEX_TRANSPORT_ID = codex-local-v1
ExecutionTransport Protocol
ExecutorInvocation schema
InvocationReceipt schema
InvocationStatus enum
canonical receipt error/status mapping
exact safe Codex argv
--ask-for-approval never before exec
--ephemeral
--json
--color never
--sandbox workspace-write
sandbox_workspace_write.network_access=false
web_search="disabled"
-C exact workspace
final stdin sentinel '-'
exact payload bytes
shell=False
one Codex process per invocation
clean worktree preflight
exact target branch preflight
closed child environment allowlist
secret environment denylist
subscription-first local sign-in
no API-key fallback
no retry
no fallback
no silent reroute
E4 real-delta requirement
allowed-path validation
Human RUN/FIX/MERGE authority
```

TASK-067 must not add/remove/reorder Codex CLI flags.

## Required Implementation

### 1. CodexTransportDiagnostic

Add an immutable/frozen Codex-specific diagnostic contract in `codex_local.py` with semantics matching ADR-040.

At minimum it must expose only safe derived metadata equivalent to:

```text
schema_version
diagnostic code
stdout_total_bytes
stderr_total_bytes
stdout_scan_truncated
stderr_scan_truncated
stdout_json_line_count
stdout_non_json_line_count
stdout_event_types
last_stdout_event_type
```

Requirements:

- exact finite validation for all counts/strings/collections;
- bool must not pass integer validation where exact int is required;
- stable deterministic `to_dict()`;
- stable deterministic SHA-256 fingerprint over canonical JSON;
- no raw stdout/stderr body field;
- no prompt/model prose/file contents/tool payload/error body field;
- no authority field.

### 2. CodexInvocationOutcome

Add an immutable/frozen Codex-specific outcome binding exactly:

```text
receipt: InvocationReceipt
diagnostic: CodexTransportDiagnostic
```

It creates zero task-success or authorization semantics.

### 3. Preserve E1 `invoke()`

`CodexLocalTransport.invoke(invocation, payload)` must continue returning the canonical E1 `InvocationReceipt` and satisfying `ExecutionTransport` Protocol.

Add a Codex-specific diagnostic helper such as:

```text
invoke_with_diagnostic(invocation, payload) -> CodexInvocationOutcome
```

Implementation may use a shared private internal execution function, but **one public invocation must never spawn Codex twice**.

### 4. Temporary Diagnostic Capture

When diagnostics are requested, replace direct `DEVNULL` output disposal with non-worktree temporary capture sinks.

Requirements:

```text
MAX_CODEX_DIAGNOSTIC_SCAN_BYTES_PER_STREAM = 65536
```

or an explicitly documented stricter finite value.

- do not buffer arbitrarily large stdout/stderr in Python memory;
- raw temporary output lives only for the invocation lifetime;
- close/delete temporary capture before returning outcome;
- analyze at most the bounded diagnostic scan envelope per stream;
- set truncation flags when total bytes exceed analysis envelope;
- no raw capture written under repo or persistent AIOS runtime directory.

### 5. Safe JSON Event Metadata

Because Codex is invoked with `--json`, bounded stdout analysis may parse NDJSON.

Retain only top-level JSON `type` values that satisfy a conservative canonical token pattern and length bound.

Required bound:

```text
MAX_CODEX_DIAGNOSTIC_EVENT_TYPES <= 32
MAX_SINGLE_EVENT_TYPE_LENGTH <= 64
```

or stricter.

Do not persist any other JSON values.

Malformed/non-JSON lines increment a bounded/count metadata field and do not cause raw content persistence.

Diagnostic code must describe observed output shape only, not infer root cause from free-form text.

### 6. E4 Integration

Update the Codex execution path in `bridge.py` so it uses the diagnostic outcome exactly once.

E4 persistent executor-automation receipt must retain all existing fields and additionally include equivalent fields:

```text
transport_diagnostic
tранспорт_diagnostic_fingerprint
```

Use the canonical ASCII field name exactly:

```text
transport_diagnostic_fingerprint
```

Do not use the accidental non-ASCII spelling shown above as an implementation key.

Required persisted shape:

```text
"transport_diagnostic": diagnostic.to_dict()
"transport_diagnostic_fingerprint": diagnostic.fingerprint()
```

No raw stdout/stderr may be placed in the record.

### 7. Operator Failure Visibility

When transport status is not `EXITED_ZERO`, E4 failure output must include only stable bounded metadata:

```text
receipt.status.value
receipt.error_code
diagnostic.code
```

Example semantic shape:

```text
E4 transport ended with EXITED_NONZERO; error=CODEX_EXIT_NONZERO; diagnostic=JSON_ERROR_EVENT; no publication and no retry
```

Do not print raw capture bodies.

For `EXITED_ZERO` followed by no worktree delta, preserve the existing hard failure and append the safe diagnostic code to the failure context when practical.

### 8. No-Delta Gate Remains Hard

Do not change `validate_executor_worktree_delta` semantics.

The following remains rejected:

```text
receipt.status == EXITED_ZERO
AND dirty_paths == []
```

Diagnostic metadata can explain execution shape but cannot authorize publication.

## Explicitly Forbidden Scope

Do not modify:

```text
src/aios_bridge/continuity/**
src/aios_bridge/executor_context.py
src/aios_bridge/executor_automation.py
src/aios_bridge/runtime_dispatch.py
src/aios_bridge/runtime_lease.py
src/aios_bridge/paid_api_*/**
src/aios_engineering/**
.agents/skills/aios-worker/**
.agents/workflows/aios-worker.md
.ai/decisions/**
.ai/reviews/**
.ai/tasks/**
requirements.txt
```

Do not add dependencies.

Do not add:

```text
real Codex call in tests
auto retry
auto reroute
second executor
paid API fallback
API key fallback
sandbox weakening
danger-full-access
--dangerously-bypass-approvals-and-sandbox
web search/network enablement
session resume/history lookup
raw model output persistence
raw stderr persistence
auto merge
```

## Tests

Update existing focused tests only inside the authorized test files.

At minimum prove:

1. `CodexLocalTransport` still satisfies `ExecutionTransport`;
2. exact Codex argv list is unchanged from ADR-034;
3. payload bytes reach stdin exactly once and are not normalized;
4. `invoke()` still returns canonical `InvocationReceipt`;
5. diagnostic invocation returns immutable `CodexInvocationOutcome`;
6. one diagnostic invocation creates exactly one fake process;
7. stdout/stderr raw bodies are absent from diagnostic `to_dict()`;
8. arbitrary JSON nested fields/model text are not persisted;
9. stderr content is not persisted;
10. valid top-level event `type` tokens are retained;
11. invalid/oversized/control-bearing event types are discarded;
12. unique event types are bounded;
13. diagnostic scan bytes are bounded and truncation is deterministic;
14. malformed JSON lines are counted but not persisted;
15. invalid UTF-8 cannot leak raw bytes;
16. empty output produces deterministic safe metadata;
17. nonzero process exit remains canonical `EXITED_NONZERO / CODEX_EXIT_NONZERO`;
18. timeout remains `TIMED_OUT / CODEX_TIMEOUT` and cleanup still runs;
19. interrupt remains `INTERRUPTED / CALLER_INTERRUPTED` and cleanup still runs;
20. diagnostic analysis failure does not rerun process and does not mutate receipt status;
21. E4 receipt record contains diagnostic dict + fingerprint;
22. E4 receipt record contains no raw stdout/stderr;
23. E4 nonzero failure exposes only stable status/error/diagnostic codes;
24. E4 zero-exit/no-delta remains rejected;
25. existing allowed-path/publication semantics remain unchanged;
26. no H0/H-Series files change;
27. no paid API/provider code changes.

All subprocess behavior in automated tests must be fake/monkeypatched. Do not consume real Codex subscription quota in TASK-067 validation.

## Validation Commands

Executor must run:

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_bridge/test_codex_local_transport.py tests/test_bridge_executor_automation.py -q
.\venv\Scripts\python.exe -m pytest tests/ -q
git diff --check
```

Also perform exact writable-scope verification.

Pre-task merged baseline:

```text
2055 passed, 7 skipped, 0 failed
```

TASK-067 may increase the passed-test count but must introduce zero failures/regressions.

## Required RESULT-067 Evidence

`RESULT-067.md` must report at minimum:

```text
TASK_067_CLASS: CODEX_DIAGNOSTIC_HARDENING
EXECUTOR_ID: antigravity
REAL_CODEX_CALL_DURING_TASK: NO

E1_INVOCATION_RECEIPT_SCHEMA_CHANGED: NO
SAFE_CODEX_ARGV_CHANGED: NO
PAYLOAD_BYTES_CHANGED: NO
SUBSCRIPTION_FIRST_ENV_CHANGED: NO

DIAGNOSTIC_OUTCOME_PRESENT: YES
DIAGNOSTIC_METADATA_IMMUTABLE: YES
DIAGNOSTIC_SCAN_BOUNDED: YES
DIAGNOSTIC_EVENT_TYPES_BOUNDED: YES
RAW_STDOUT_PERSISTED: NO
RAW_STDERR_PERSISTED: NO
RAW_MODEL_OUTPUT_IN_RESULT: NO

E4_DIAGNOSTIC_PERSISTENCE: PASS
E4_FAILURE_CODE_VISIBILITY: PASS
EXIT_ZERO_NO_DELTA_STILL_REJECTED: YES

AUTO_RETRY: NO
AUTO_REROUTE: NO
PAID_API_USED: NO
H0_CHANGED: NO
H1_STARTED: NO
SCOPE_EXACT: YES
```

Include exact targeted/full test commands, exit codes, pass/skip/fail counts, changed paths, implementation SHA, and branch.

## Acceptance Criteria

TASK-067 may publish READY_FOR_REVIEW only if:

```text
E1_PROTOCOL_CONFORMANCE: PASS
SAFE_ARGV_REGRESSION: PASS
EXACT_STDIN_PAYLOAD: PASS
ONE_SPAWN_PER_INVOCATION: PASS
BOUNDED_TEMP_DIAGNOSTIC_CAPTURE: PASS
RAW_DIAGNOSTIC_PERSISTENCE: NONE
SAFE_EVENT_METADATA_ONLY: PASS
DIAGNOSTIC_FINGERPRINT_DETERMINISTIC: PASS
CANONICAL_RECEIPT_SEMANTICS_UNCHANGED: PASS
TIMEOUT_INTERRUPT_CLEANUP_UNCHANGED: PASS
E4_RECEIPT_DIAGNOSTIC_METADATA: PASS
E4_FAILURE_DIAGNOSTIC_CODES: PASS
EXIT_ZERO_NO_DELTA_REJECTED: PASS
NO_RETRY: PASS
NO_REROUTE: PASS
NO_PAID_API: PASS
NO_H_SERIES_CHANGE: PASS
TARGETED_TESTS: PASS
FULL_REPOSITORY_TESTS: PASS
SCOPE_EXACT: YES
```

## Deferred Operational Proof

TASK-067 PASS + Human merge does **not** mean Codex is operationally reliable yet.

After merge, create a fresh task (expected `TASK-068`) whose only purpose is a real local Codex execution proof against the merged transport:

```text
fresh Human authorization
one Codex executor
one bounded authorized edit
E4 sees real allowed-path delta
publication succeeds
no retry
no reroute
```

Only a successful fresh operational proof permits us to mark the Codex local path operationally proven and continue to H1 without this open reliability caveat.
