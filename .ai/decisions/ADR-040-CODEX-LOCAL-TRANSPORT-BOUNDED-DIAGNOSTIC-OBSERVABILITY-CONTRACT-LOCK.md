# ADR-040 — Codex Local Transport Bounded Diagnostic Observability Contract Lock

STATUS: LOCKED
CLASS: E2.2 / E4.1 SUPPORTING REFINEMENT — CODEX LOCAL EXECUTOR OBSERVABILITY
BASELINE_MAIN_SHA: 75866e0e033364fbcc308904e9b8e7572e8d2f48
APPLIES_AFTER: TASK-066 PASS + HUMAN MERGE / H0 COMPLETE
RELATED: ADR-029 / ADR-030 / ADR-032 / ADR-034 / ADR-037 / ADR-039

## Context

AIOS already has a dual-executor control plane and a concrete local Codex transport. The current Codex path is safe but insufficiently observable during real failures.

The current merged transport deliberately launches one bounded headless Codex process with the locked safe command shape and exact payload bytes, but it currently routes both process output streams to `subprocess.DEVNULL`.

Real evidence now includes two distinct no-publication Codex outcomes:

```text
TASK-064 attempt:
  transport status = EXITED_ZERO
  worktree delta   = none
  E4 result        = rejected: Executor produced no worktree delta

TASK-066 attempt:
  transport status = EXITED_NONZERO
  exit code        = 1
  worktree delta   = none
  E4 result        = no publication / no retry
```

The safety behavior is correct. The observability is not sufficient to distinguish a local CLI/auth/config/sandbox/runtime failure from a completed Codex turn that simply produced no authorized edit.

ADR-030 Decision 9 already permits stdout/stderr to be sent to a **bounded non-authoritative diagnostic sink** while forbidding raw bodies in `InvocationReceipt`. ADR-040 activates that previously permitted diagnostic path without changing E1 authority or canonical receipt semantics.

This is a supporting Bridge refinement between H0 and H1. It is not M12 and does not alter H-Series authority.

---

## Decision 1 — E1 InvocationReceipt Remains Unchanged

ADR-040 MUST NOT modify:

```text
src/aios_bridge/continuity/executor_transport.py
ExecutorInvocation schema
InvocationReceipt schema
InvocationStatus enum
FORBIDDEN_INVOCATION_KEYS
```

Canonical E1 receipt semantics remain:

```text
exit 0       -> EXITED_ZERO
exit nonzero -> EXITED_NONZERO / CODEX_EXIT_NONZERO
timeout      -> TIMED_OUT / CODEX_TIMEOUT
interrupt    -> INTERRUPTED / CALLER_INTERRUPTED
```

A diagnostic record is supplementary non-authoritative evidence. It is not task success, authorization, dispatch, lease, publication, review, or merge evidence.

---

## Decision 2 — Add Codex-Specific Immutable Diagnostic Outcome

The concrete Codex transport MAY add Codex-specific immutable types under `src/aios_bridge/executor_transports/codex_local.py` equivalent to:

```text
CodexTransportDiagnostic
CodexInvocationOutcome
```

Required semantic shape for `CodexTransportDiagnostic`:

```text
schema_version
code                         # bounded stable diagnostic enum/token
stdout_total_bytes           # exact non-negative int
stderr_total_bytes           # exact non-negative int
stdout_scan_truncated        # bool
stderr_scan_truncated        # bool
stdout_json_line_count       # exact non-negative int
stdout_non_json_line_count   # exact non-negative int
stdout_event_types           # bounded tuple of safe canonical event type tokens
last_stdout_event_type       # optional safe canonical token
```

`CodexInvocationOutcome` binds exactly:

```text
receipt: InvocationReceipt
diagnostic: CodexTransportDiagnostic
```

No raw stdout/stderr text or bytes may be fields of either type.

The existing protocol method:

```text
CodexLocalTransport.invoke(...) -> InvocationReceipt
```

must continue to work unchanged for E1 Protocol conformance.

A Codex-specific helper such as:

```text
invoke_with_diagnostic(...) -> CodexInvocationOutcome
```

is permitted for E4 integration, provided one call launches at most one Codex process and does not cause duplicate model execution.

---

## Decision 3 — Diagnostic Capture Is Temporary, Bounded for Analysis, and Non-Persistent Raw Data

The subprocess may no longer discard output directly to `DEVNULL` when E4 asks for diagnostic execution.

The implementation SHALL use non-worktree temporary capture sinks (for example OS temporary files) so process output is not accumulated without bound in Python memory.

Locked requirements:

```text
RAW_STDOUT_IN_WORKTREE: FORBIDDEN
RAW_STDERR_IN_WORKTREE: FORBIDDEN
RAW_STDOUT_IN_RUNTIME_RECEIPT: FORBIDDEN
RAW_STDERR_IN_RUNTIME_RECEIPT: FORBIDDEN
RAW_OUTPUT_IN_INVOCATION_RECEIPT: FORBIDDEN
RAW_OUTPUT_IN_RESULT_ARTIFACT: FORBIDDEN
```

Analysis of each stream is bounded by a named constant:

```text
MAX_CODEX_DIAGNOSTIC_SCAN_BYTES_PER_STREAM = 65536
```

Equivalent or stricter finite bound is acceptable only if documented and tested.

If total output exceeds the scan bound, metadata must mark the stream as truncated for diagnostic analysis. The full raw temporary capture must be closed/deleted before the transport outcome returns to E4.

No raw output may be committed, pushed, copied into `.ai/results`, or stored under persistent external AIOS runtime directories.

---

## Decision 4 — Persist Only Safe Derived Metadata

Diagnostic parsing may inspect only the bounded captured slice(s) and derive conservative metadata.

For Codex `--json` stdout, the implementation MAY parse newline-delimited JSON and retain only a bounded set of values from the top-level `type` field.

A persisted event type must satisfy a conservative machine-readable token contract, for example:

```text
[a-zA-Z0-9_.:-]{1,64}
```

and the number of retained unique event types must be bounded, recommended:

```text
MAX_CODEX_DIAGNOSTIC_EVENT_TYPES = 32
```

All other JSON fields, including messages, model prose, tool content, file content, reasoning, commands, paths, errors, provider data, and arbitrary nested objects, are discarded from persistent diagnostic evidence.

Stderr body is never persisted. Only safe metadata such as total byte count / presence / truncation may be retained.

---

## Decision 5 — Diagnostic Codes Describe Observed Shape, Not Inferred Root Cause

ADR-040 must not fabricate a semantic root cause from free-form model text.

Stable diagnostic codes may describe mechanically observed conditions, for example:

```text
NO_OUTPUT
STDERR_ONLY
JSON_EVENTS
JSON_ERROR_EVENT
NON_JSON_STDOUT
MIXED_OUTPUT
CAPTURE_FAILED
```

Exact names may vary if they remain bounded canonical tokens and their meaning is documented.

A code such as `JSON_ERROR_EVENT` may be emitted only when a safe parsed stdout event `type` mechanically indicates an error event. The implementation must not scan arbitrary model prose for words like `auth`, `sandbox`, or `error` and promote those words to a root-cause claim.

`diagnostic_code != root_cause` remains locked.

---

## Decision 6 — Exact Safe Codex Argv and Environment Remain Unchanged

ADR-040 does not reopen ADR-034 argv compatibility or ADR-030 sandbox policy.

The exact process argv remains equivalent to:

```text
codex
--ask-for-approval never
exec
--ephemeral
--json
--color never
--sandbox workspace-write
-c sandbox_workspace_write.network_access=false
-c web_search="disabled"
-C <workspace>
-
```

Do not add or remove Codex CLI flags in TASK-067 unless implementation mechanically proves a separate compatibility defect and STOPs for a new architecture decision.

The following remain unchanged:

```text
one Codex process per invocation
shell=False
exact stdin payload bytes
clean-worktree preflight
exact target-branch preflight
closed child environment allowlist
secret environment denylist
subscription-first existing local sign-in
no API-key fallback
no retry
no silent reroute
no weaker sandbox fallback
no web search/tool-side network
```

---

## Decision 7 — E4 Persists Bounded Diagnostic Metadata Beside InvocationReceipt

When the Codex-specific diagnostic execution path is used, E4 SHALL add a sibling bounded field to its external runtime executor-automation receipt record equivalent to:

```text
transport_diagnostic: <CodexTransportDiagnostic.to_dict()>
transport_diagnostic_fingerprint: <64-hex deterministic fingerprint>
```

This field is non-authoritative.

Existing canonical fields remain unchanged, including:

```text
invocation_receipt
invocation_receipt_fingerprint
dirty_paths
published_sha
result_blob_sha
execution_result_fingerprint
```

The runtime receipt must still be written outside the Git worktree under the existing E4 receipt mechanism.

---

## Decision 8 — E4 Failure Messages Surface Stable Codes Only

For non-zero/timeout/start failures, the operator-facing E4 error may include:

```text
InvocationStatus
InvocationReceipt.error_code
diagnostic.code
```

It MUST NOT echo raw stdout/stderr.

Example shape:

```text
E4 transport ended with EXITED_NONZERO; error=CODEX_EXIT_NONZERO; diagnostic=JSON_ERROR_EVENT; no publication and no retry
```

For `EXITED_ZERO` followed by no worktree delta, E4 shall continue to fail closed. The failure message may append the diagnostic code so the operator can distinguish a completed JSON event stream from an empty/no-output execution.

No diagnostic code can override E4 Git/scope validation.

---

## Decision 9 — No-Delta Remains a Hard Failure

ADR-040 does not weaken:

```text
validate_executor_worktree_delta(...)
```

The following remains forbidden:

```text
EXITED_ZERO + dirty_paths=[] -> publish RESULT
```

Exit zero remains transport-only evidence. A real authorized worktree delta inside allowed paths is still required before E4 publication.

---

## Decision 10 — Timeout / Interrupt Cleanup Semantics Remain Intact

Diagnostic capture must not regress process-tree cleanup.

On timeout or caller interruption:

```text
cleanup exact process/process group
build existing canonical InvocationReceipt status
build bounded diagnostic metadata from whatever safe output was captured
close/delete raw temporary sinks
return one outcome
```

No automatic retry follows timeout, interruption, or diagnostic capture failure.

---

## Decision 11 — Diagnostic Failure Must Not Create Execution Authority

If diagnostic analysis itself fails after a process result exists, the implementation may emit a bounded `CAPTURE_FAILED` / `DIAGNOSTIC_FAILED` code while preserving the original canonical `InvocationReceipt` process status.

Diagnostic parsing failure must not:

- convert nonzero to success;
- convert zero to task success;
- rerun Codex;
- broaden allowed paths;
- release/reacquire lease;
- invoke another executor;
- bypass E4 scope validation.

---

## Decision 12 — TASK-067 Is Implementation Hardening, Not the Real Codex Proof

TASK-067 must use fake/monkeypatched subprocesses in automated tests and MUST NOT launch a real Codex model call as part of the test suite.

After TASK-067 PASS + Human merge, a **fresh separate task** must perform the real local Codex operational proof against the merged transport.

Expected sequence:

```text
H0 COMPLETE
  -> TASK-067 diagnostic hardening
  -> Review + Human merge
  -> fresh TASK-068 real local Codex proof
  -> if proof PASS: Codex local path operationally proven
  -> H1
```

If TASK-068 exposes a concrete compatibility/auth/config/sandbox defect, that defect gets its own bounded FIX. Diagnostic evidence does not authorize silent weakening.

---

## Decision 13 — TASK-067 Executor Selection

TASK-067 changes the Codex transport itself while Codex reliability is the subject under repair.

Therefore TASK-067 shall be implemented by:

```text
executor_id = antigravity
```

only.

This is a task-specific incompatibility exception, not a rollback of the dual-executor architecture. Codex becomes eligible again only after the post-merge real proof demonstrates the path.

---

## Decision 14 — Expected Writable Scope

TASK-067 may modify only:

```text
bridge.py
src/aios_bridge/executor_transports/__init__.py
src/aios_bridge/executor_transports/codex_local.py
tests/aios_bridge/test_codex_local_transport.py
tests/test_bridge_executor_automation.py
```

Bridge-generated publication output:

```text
.ai/results/RESULT-067.md
```

No other production/control/H-Series file is expected.

TASK-067 MUST NOT modify:

```text
src/aios_bridge/continuity/**
src/aios_bridge/executor_context.py
src/aios_bridge/executor_automation.py
src/aios_bridge/runtime_dispatch.py
src/aios_bridge/runtime_lease.py
src/aios_engineering/**
.agents/skills/aios-worker/**
.agents/workflows/aios-worker.md
paid API / MiniMax / grant paths
```

---

## Decision 15 — Required Tests

Required focused coverage includes at minimum:

1. existing `ExecutionTransport` protocol still passes;
2. exact safe argv remains byte-for-byte/element-for-element unchanged;
3. exact payload bytes still reach stdin once;
4. `invoke()` still returns canonical `InvocationReceipt` only;
5. diagnostic helper launches exactly one fake process;
6. stdout/stderr are no longer persisted raw;
7. JSON event type extraction retains only safe top-level `type` tokens;
8. arbitrary nested JSON/model content is not present in diagnostic dict;
9. stderr content is never present in diagnostic dict;
10. diagnostic scan byte bound is enforced and truncation flags are correct;
11. unique event-type count is bounded;
12. malformed JSON is counted as non-JSON without throwing authority-changing exceptions;
13. invalid UTF-8 cannot leak raw bytes and produces bounded metadata only;
14. nonzero exit preserves `CODEX_EXIT_NONZERO` canonical receipt semantics;
15. timeout/interrupt preserve existing cleanup behavior;
16. diagnostic parser failure produces bounded diagnostic failure metadata without rerun;
17. E4 external receipt stores diagnostic dict + deterministic fingerprint;
18. E4 nonzero failure message includes only stable receipt/diagnostic codes;
19. E4 zero-exit/no-delta still fails publication;
20. no raw captured output appears in E4 persistent receipt/RESULT/worktree;
21. no retry, fallback, paid API, dispatcher, lease, H-Series or worker-surface change.

Full repository tests remain required.

---

## Acceptance

ADR-040 is implemented only when:

```text
E1_INVOCATION_RECEIPT_SCHEMA_CHANGED: NO
SAFE_CODEX_ARGV_CHANGED: NO
PAYLOAD_BYTES_CHANGED: NO
SUBSCRIPTION_FIRST_ENV_CHANGED: NO
RAW_STDOUT_PERSISTED: NO
RAW_STDERR_PERSISTED: NO
DIAGNOSTIC_SCAN_BOUNDED: YES
DIAGNOSTIC_EVENT_TYPES_BOUNDED: YES
DIAGNOSTIC_METADATA_IMMUTABLE: YES
DIAGNOSTIC_METADATA_NON_AUTHORITATIVE: YES
E4_DIAGNOSTIC_PERSISTENCE: PASS
E4_FAILURE_CODE_VISIBILITY: PASS
EXIT_ZERO_NO_DELTA_STILL_REJECTED: YES
NO_RETRY: YES
NO_SILENT_REROUTE: YES
NO_PAID_API: YES
H0_CHANGED: NO
H1_STARTED: NO
TARGETED_TESTS: PASS
FULL_REPO_TESTS: PASS
REGRESSIONS: 0
```

Only Human may authorize merge. A TASK-067 PASS does not itself prove real Codex execution reliability; that proof belongs to the fresh post-merge operational proof task.
