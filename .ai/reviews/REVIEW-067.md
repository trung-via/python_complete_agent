# REVIEW-067 — Codex Transport Diagnostic & Reliability Hardening

STATUS: CHANGES_REQUIRED
APPROVED: NO
READY_FOR_HUMAN_MERGE: NO
MERGE_AUTHORIZED: NO
TASK_067_IMPLEMENTATION_PASS: NO
REAL_CODEX_PROOF_AUTHORIZED: NO
H1_AUTHORIZED: NO
LIVE_PAID_API_AUTHORIZED: NO

## Reviewed Snapshot

```text
TASK_ID: TASK-067
BASE_MAIN_SHA: 75866e0e033364fbcc308904e9b8e7572e8d2f48
BRANCH: ai/task-067
BRANCH_STATUS_VS_MAIN: AHEAD
AHEAD_BY: 1
BEHIND_BY: 0
MERGE_BASE_SHA: 75866e0e033364fbcc308904e9b8e7572e8d2f48
RESULT_STATUS: READY_FOR_REVIEW
RESULT_BLOB_SHA: 9acbff4bb7903ae524b4e333fab92b89bfdab76e
BRIDGE_BLOB_SHA: ba27d96122095a9cc97aa4fd117a8ef35ef7bc92
TRANSPORT_EXPORTS_BLOB_SHA: 9ee58ac62fd101493940ddc9d101d62f5dd8d6a3
CODEX_LOCAL_BLOB_SHA: 32ca7f69fe91c2f6886ac236f304584b68115e94
TRANSPORT_TESTS_BLOB_SHA: 42aeaad2ae4e6cca51e01324f66080dc568fbe32
E4_TESTS_BLOB_SHA: 1ebd60bb175e8f02f2bc013c47f1ed3447eab05d
```

The branch is a clean fast-forward descendant of the reviewed main baseline. This review is CHANGES_REQUIRED; no merge authorization is created.

## Scope / Authority Audit — PASS

Cumulative TASK-067 delta is confined to the five TASK-067 writable implementation/test paths plus Bridge-generated `.ai/results/RESULT-067.md`:

```text
bridge.py
src/aios_bridge/executor_transports/__init__.py
src/aios_bridge/executor_transports/codex_local.py
tests/aios_bridge/test_codex_local_transport.py
tests/test_bridge_executor_automation.py
.ai/results/RESULT-067.md
```

No continuity schema, executor context, executor automation core, dispatch, lease, paid-API/provider, H-Series, worker-surface, dependency, task, decision, or prior review path changed.

The existing safe Codex argv remains structurally unchanged, E1 `InvocationReceipt` remains unchanged, no retry/reroute/paid fallback was introduced, and E4 still rejects `EXITED_ZERO + dirty_paths=[]`.

## Test Evidence Observed

RESULT-067 reports:

```text
TARGETED: 118 passed, 0 skipped, 0 failed
FULL:     2080 passed, 7 skipped, 0 failed
REAL_CODEX_CALL_DURING_TASK: NO
```

Green tests are necessary but not sufficient because the focused tests currently model the Codex JSON event vocabulary incorrectly in a way that hides B1 below.

## B1 — Real Codex `--json` Event Vocabulary Is Rejected — BLOCKER

`codex_local.py` currently defines:

```python
_EVENT_TYPE_RE = re.compile(r"\A[A-Za-z0-9_:-]+\Z")
```

The pattern rejects `.`.

Current Codex `exec --json` top-level events are dot-delimited. The upstream `openai/codex` source at `codex-rs/exec/src/exec_events.rs` defines top-level event types including:

```text
thread.started
turn.started
turn.completed
turn.failed
item.started
item.updated
item.completed
error
```

Therefore the current implementation drops nearly every normal real Codex event type from `stdout_event_types` and `last_stdout_event_type`. A real successful stream can be reduced to `JSON_EVENT_STREAM` with no retained event vocabulary, defeating the operational observability purpose of TASK-067. A `turn.failed` event is also discarded as an event type and is not mechanically recognized as a failure-shaped event.

The current tests hide the defect by using synthetic underscore tokens such as:

```text
turn_started
item_started
item_completed
```

### Required FIX for B1

1. Permit the canonical conservative token alphabet required by ADR-040, including `.`; e.g. exact full-match semantics equivalent to:

```text
[A-Za-z0-9_.:-]{1,64}
```

2. Add regression tests using the real top-level Codex vocabulary, at minimum:

```text
thread.started
turn.started
item.completed
turn.completed
turn.failed
error
```

3. `stdout_event_types` and `last_stdout_event_type` must retain valid dotted event types.
4. `JSON_ERROR_EVENT` classification must be based only on mechanically failure-shaped safe top-level event types. At minimum exact `error` and `turn.failed` must classify as failure-shaped. Do not classify arbitrary event types merely because the substring `error` appears somewhere in the token.
5. Do not inspect or persist free-form error/model prose to make this decision.

Expected evidence:

```text
REAL_CODEX_DOTTED_EVENT_TYPES_RETAINED: YES
TURN_FAILED_MECHANICALLY_CLASSIFIED: YES
ARBITRARY_ERROR_SUBSTRING_INFERENCE: NO
RAW_PROSE_ROOT_CAUSE_INFERENCE: NO
```

## B2 — Raw Temporary Capture Location Is Not Fail-Closed — BLOCKER

TASK-067 / ADR-040 requires raw stdout/stderr capture to be non-worktree, invocation-lifetime-only, and never located under the persistent AIOS runtime directory.

The current implementation uses:

```python
with tempfile.TemporaryFile() as out_f, tempfile.TemporaryFile() as err_f:
```

with no explicit capture-directory selection or post-resolution safety check.

Python temporary-file placement can be influenced by process/environment temporary-directory configuration. The transport therefore does not mechanically prove that the raw files are outside:

```text
exact repository workspace
persistent AIOS runtime directory
```

before Codex starts writing raw model/process output. The normal user machine likely places temp files elsewhere, but ADR-040 requires a fail-closed invariant rather than an environmental assumption.

### Required FIX for B2

Before spawning Codex, mechanically establish a temporary capture location that is outside the exact workspace and outside any configured/known persistent AIOS runtime root. If a safe location cannot be proven, fail closed before process spawn.

Add adversarial tests showing that a temp location resolving inside the workspace or persistent runtime is rejected with zero Codex spawn. Also prove the accepted temp location is deleted/closed before the outcome returns.

Do not solve this by placing capture files under `.ai/`, the repository, executor-automation receipts, or another persistent AIOS directory.

Expected evidence:

```text
RAW_CAPTURE_WORKTREE_LOCATION: FORBIDDEN
RAW_CAPTURE_PERSISTENT_RUNTIME_LOCATION: FORBIDDEN
UNSAFE_TEMP_LOCATION_SPAWN_COUNT: 0
TEMP_CAPTURE_LIFETIME_BOUNDED: YES
```

## B3 — Diagnostic Code Contract Is Not Closed to Stable Codes — BLOCKER

ADR-040 requires a stable bounded diagnostic enum/token. The current dataclass accepts any uppercase token matching `_DIAGNOSTIC_CODE_RE`, so values unrelated to the locked diagnostic vocabulary can be constructed and persisted.

Examples that currently satisfy shape validation but are not locked semantics include arbitrary values such as `RANDOM_CODE`.

### Required FIX for B3

Use a closed enum or exact allowlist for the supported diagnostic codes. The implementation may keep the currently used names if semantics remain deterministic, e.g.:

```text
EMPTY_OUTPUT
STDERR_ONLY
JSON_EVENT_STREAM
JSON_ERROR_EVENT
NON_JSON_OUTPUT
MIXED_OUTPUT
UNKNOWN_OUTPUT_SHAPE
CAPTURE_FAILED
```

Unknown diagnostic codes must fail validation. Add a regression test proving an otherwise well-shaped but unsupported code is rejected.

Expected evidence:

```text
DIAGNOSTIC_CODE_VOCABULARY_CLOSED: YES
UNKNOWN_DIAGNOSTIC_CODE_REJECTED: YES
```

## B4 — `stdout_event_types` Collection Validation Is Not Exact — BLOCKER

`CodexTransportDiagnostic` is specified as an immutable/frozen contract with a bounded tuple of event types and exact finite collection validation. The current constructor silently coerces any non-tuple iterable:

```python
if not isinstance(self.stdout_event_types, tuple):
    object.__setattr__(self, "stdout_event_types", tuple(self.stdout_event_types))
```

This accepts lists and can even reinterpret a string as a tuple of single-character event types instead of failing closed.

### Required FIX for B4

Require `stdout_event_types` to be an exact tuple at the public contract boundary. Reject list/string/generator/other collection shapes. Preserve existing bounded count and per-token validation.

Expected evidence:

```text
STDOUT_EVENT_TYPES_EXACT_TUPLE: YES
LIST_EVENT_TYPES_REJECTED: YES
STRING_EVENT_TYPES_REJECTED: YES
```

## FIX Scope

The FIX may modify only the existing TASK-067 writable implementation/test paths that are necessary:

```text
bridge.py
src/aios_bridge/executor_transports/__init__.py
src/aios_bridge/executor_transports/codex_local.py
tests/aios_bridge/test_codex_local_transport.py
tests/test_bridge_executor_automation.py
```

Prefer not to touch `bridge.py` unless B2 integration mechanically requires it. Bridge-generated `.ai/results/RESULT-067.md` may be republished.

Still forbidden:

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
requirements.txt
```

## Required Validation After FIX

Run the TASK-067 focused suite and full repository suite with zero real Codex call. Also run `git diff --check` and exact writable-scope verification.

The next RESULT-067 must retain at minimum:

```text
REAL_CODEX_CALL_DURING_TASK: NO
E1_INVOCATION_RECEIPT_SCHEMA_CHANGED: NO
SAFE_CODEX_ARGV_CHANGED: NO
PAYLOAD_BYTES_CHANGED: NO
RAW_STDOUT_PERSISTED: NO
RAW_STDERR_PERSISTED: NO
EXIT_ZERO_NO_DELTA_STILL_REJECTED: YES
AUTO_RETRY: NO
AUTO_REROUTE: NO
PAID_API_USED: NO
H0_CHANGED: NO
H1_STARTED: NO
SCOPE_EXACT: YES
```

and add explicit B1-B4 evidence described above.

## Decision

```text
TASK-067: CHANGES_REQUIRED
SCOPE_AUTHORITY_AUDIT: PASS
B1_REAL_CODEX_EVENT_COMPATIBILITY: FAIL
B2_TEMP_CAPTURE_LOCATION_FAIL_CLOSED: FAIL
B3_STABLE_DIAGNOSTIC_CODE_VOCABULARY: FAIL
B4_EXACT_EVENT_COLLECTION_CONTRACT: FAIL
REAL_CODEX_PROOF_AUTHORIZED: NO
H1_AUTHORIZED: NO
MERGE_AUTHORIZED: NO
```

Do not run TASK-068 or any real Codex operational proof until TASK-067 receives PASS and is Human-merged.