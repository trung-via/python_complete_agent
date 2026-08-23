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
AHEAD_BY: 2
BEHIND_BY: 0
MERGE_BASE_SHA: 75866e0e033364fbcc308904e9b8e7572e8d2f48
RESULT_STATUS: READY_FOR_REVIEW
RESULT_BLOB_SHA: e2173538ce0f8a03643deb6a6f91364d5d1ee43f
BRIDGE_BLOB_SHA: ba27d96122095a9cc97aa4fd117a8ef35ef7bc92
CODEX_LOCAL_BLOB_SHA: e235039aed85051e9c88db053fee517fad16aa66
TRANSPORT_TESTS_BLOB_SHA: bc2ad77152fe78de81f2f159d9b6b7b5f10dbe50
E4_TESTS_BLOB_SHA: 1ebd60bb175e8f02f2bc013c47f1ed3447eab05d
```

The task branch remains a clean fast-forward descendant of the exact H0-merged main baseline. This review remains CHANGES_REQUIRED; no merge or real Codex proof authority is created.

## Scope / Authority Audit — PASS

Cumulative TASK-067 delta remains confined to the five authorized implementation/test paths plus Bridge-generated `.ai/results/RESULT-067.md`:

```text
bridge.py
src/aios_bridge/executor_transports/__init__.py
src/aios_bridge/executor_transports/codex_local.py
tests/aios_bridge/test_codex_local_transport.py
tests/test_bridge_executor_automation.py
.ai/results/RESULT-067.md
```

No continuity schema, executor-context core, dispatcher, lease, paid-provider/grant, H-Series, worker surface, dependency, task, or ADR path changed. Safe Codex argv, one-spawn semantics, exact stdin payload, no retry/reroute/paid fallback, and the E4 zero-exit/no-delta rejection remain intact.

## Test Evidence Observed

Latest RESULT-067 reports:

```text
TARGETED: 125 passed, 0 skipped, 0 failed
FULL:     2087 passed, 7 skipped, 0 failed
REAL_CODEX_CALL_DURING_TASK: NO
```

Green tests are necessary but B2 below is still a contract/runtime mismatch not covered by the new tests.

## Prior Findings Status

```text
B1_REAL_CODEX_EVENT_COMPATIBILITY: PASS
B2_TEMP_CAPTURE_LOCATION_FAIL_CLOSED: FAIL
B3_STABLE_DIAGNOSTIC_CODE_VOCABULARY: PASS
B4_EXACT_EVENT_COLLECTION_CONTRACT: PASS
```

### B1 — PASS

The event-token contract now permits `.` and uses exact bounded full-match semantics. Regression tests use real Codex-style top-level tokens including `thread.started`, `turn.started`, `item.completed`, `turn.completed`, `turn.failed`, and `error`. Failure classification is now exact-token based (`error`, `turn.failed`) rather than substring/prose inference.

### B3 — PASS

`CodexDiagnosticCode` now defines a closed stable vocabulary and the diagnostic contract rejects otherwise well-shaped unsupported codes.

### B4 — PASS

`stdout_event_types` now requires an exact tuple at the public contract boundary; list/string/dict shapes are rejected.

## B2 — Persistent Runtime Root Resolution Does Not Match Bridge — BLOCKER

The new fail-closed temp-location helper is directionally correct, but it does not protect the actual runtime configuration contract used by `bridge.py`.

`codex_local.py` currently treats the following as persistent runtime roots:

```text
AIOS_BRIDGE_RUNTIME_DIR
LOCALAPPDATA/aios-bridge          # Windows only
~/.aios_bridge                   # underscore
```

The production Bridge actually resolves its persistent runtime through:

```text
AIOS_RUNTIME_DIR                  # exact override
AIOS_HOME                         # runtime base override
LOCALAPPDATA/aios-bridge          # Windows default base
~/.aios-bridge                    # Windows fallback
XDG_DATA_HOME/aios-bridge         # POSIX default base when set
~/.aios-bridge                    # POSIX fallback
```

Therefore valid Bridge configurations are currently missed. Examples:

```text
AIOS_RUNTIME_DIR=<temp root>
AIOS_HOME=<temp root>
XDG_DATA_HOME=<parent of temp root on POSIX>
~/.aios-bridge on POSIX/Windows fallback
```

In those cases `_resolve_safe_temporary_dir()` can accept a location that is actually the persistent AIOS runtime area and then open raw Codex stdout/stderr temporary files there. That violates ADR-040/TASK-067 even though the files remain invocation-lifetime-only.

The current adversarial test sets `AIOS_BRIDGE_RUNTIME_DIR`, which Bridge does not use, so it proves the wrong configuration surface.

### Required FIX for B2

Make the transport's persistent-runtime exclusion mechanically mirror the production `bridge.py::get_runtime_dir()` configuration semantics without importing or mutating Bridge authority.

At minimum cover:

```text
AIOS_RUNTIME_DIR
AIOS_HOME
LOCALAPPDATA/aios-bridge
XDG_DATA_HOME/aios-bridge
~/.aios-bridge
```

A stricter rejection of the entire configured runtime base is acceptable. Remove or retain extra legacy names only if they do not substitute for the real Bridge names.

Add adversarial zero-spawn tests for at least:

```text
AIOS_RUNTIME_DIR -> temp root inside exact override
AIOS_HOME        -> temp root inside configured runtime base
POSIX fallback/XDG base semantics
```

and keep the existing workspace-inside-temp rejection. The accepted temporary capture must still be outside worktree/runtime and closed/deleted before return.

Expected evidence:

```text
BRIDGE_RUNTIME_OVERRIDE_NAMES_MATCH: YES
AIOS_RUNTIME_DIR_TEMP_REJECTED: YES
AIOS_HOME_TEMP_REJECTED: YES
XDG_OR_HOME_AI0S_BRIDGE_TEMP_REJECTED: YES
UNSAFE_TEMP_LOCATION_SPAWN_COUNT: 0
RAW_CAPTURE_PERSISTENT_RUNTIME_LOCATION: FORBIDDEN
```

## FIX Scope

This should be a very small FIX. Prefer modifying only:

```text
src/aios_bridge/executor_transports/codex_local.py
tests/aios_bridge/test_codex_local_transport.py
```

`src/aios_bridge/executor_transports/__init__.py` may change only if mechanically necessary. Bridge-generated `.ai/results/RESULT-067.md` may be republished.

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

Do not run a real Codex call in this FIX.

## Decision

```text
TASK-067: CHANGES_REQUIRED
SCOPE_AUTHORITY_AUDIT: PASS
B1_REAL_CODEX_EVENT_COMPATIBILITY: PASS
B2_TEMP_CAPTURE_LOCATION_FAIL_CLOSED: FAIL
B3_STABLE_DIAGNOSTIC_CODE_VOCABULARY: PASS
B4_EXACT_EVENT_COLLECTION_CONTRACT: PASS
TARGETED_TESTS: PASS
FULL_REPOSITORY_TESTS: PASS
REAL_CODEX_PROOF_AUTHORIZED: NO
H1_AUTHORIZED: NO
MERGE_AUTHORIZED: NO
```

Do not run TASK-068 or any real Codex operational proof until TASK-067 receives PASS and is Human-merged.