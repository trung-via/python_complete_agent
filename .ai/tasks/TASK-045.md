# TASK-045 — E2.1 Codex CLI Argument Compatibility Fix

STATUS: READY
CLASS: L2 — MINIMAL TRANSPORT COMPATIBILITY FIX / REGRESSION LOCK
EXECUTOR_MODE: THIN_EXECUTOR

## Baseline

```text
MAIN_SHA: a01b5f4b028ccdc416004b3d25608d23fb922c51
TARGET_BRANCH: ai/task-045
```

## Authoritative Contract

```text
ADR_PATH: .ai/decisions/ADR-034-E2.1-CODEX-CLI-GLOBAL-APPROVAL-FLAG-COMPATIBILITY-CONTRACT-LOCK.md
ADR_BLOB_SHA: cbe66ff7ae5db159ed96c0310f1271d9527d3bae
BLUEPRINT_PATH: .ai/context/TASK-045-E2.1-CODEX-CLI-ARGUMENT-COMPATIBILITY-BLUEPRINT.md
BLUEPRINT_BLOB_SHA: 783ddad9ff55db166d4091fbd75b6f34d2f8075c
```

## Existing Production Anchors

```text
E2_CODEX_LOCAL_PATH: src/aios_bridge/executor_transports/codex_local.py
E2_CODEX_LOCAL_BLOB_SHA: dd1fae54506459a2a638441a35d5a327d89da8cc
E2_TEST_PATH: tests/aios_bridge/test_codex_local_transport.py
E2_TEST_BLOB_SHA: 366ba89921d462bca1b908b4628d055099753f90
```

## Root Cause

The first real E5 attempt, TASK-044, reached the real local Codex transport but returned:

```text
STATUS: EXITED_NONZERO
EXIT_CODE: 2
ERROR_CODE: CODEX_EXIT_NONZERO
DIRTY_PATHS: []
PUBLICATION: NONE
```

Local Codex CLI 0.147.0 exposes `--ask-for-approval` at top-level `codex --help`, not `codex exec --help`.

Current E2 argv incorrectly places the flag after `exec`:

```text
codex exec ... --ask-for-approval never ...
```

TASK-045 fixes only this parser-boundary incompatibility.

## Objective

Change the E2 argv builder from:

```text
codex exec ... --ask-for-approval never ...
```

to:

```text
codex --ask-for-approval never exec ...
```

with every other argv element and all runtime behavior unchanged.

## Machine-Readable Executor Context

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/decisions/ADR-034-E2.1-CODEX-CLI-GLOBAL-APPROVAL-FLAG-COMPATIBILITY-CONTRACT-LOCK.md","blob_sha":"cbe66ff7ae5db159ed96c0310f1271d9527d3bae"},{"path":".ai/context/TASK-045-E2.1-CODEX-CLI-ARGUMENT-COMPATIBILITY-BLUEPRINT.md","blob_sha":"783ddad9ff55db166d4091fbd75b6f34d2f8075c"}]

## Machine-Readable Executor Worktree Scope

EXECUTOR_ALLOWED_PATHS_JSON: ["src/aios_bridge/executor_transports/codex_local.py","tests/aios_bridge/test_codex_local_transport.py"]

`RESULT-045.md` is Bridge-generated only.

## Executor Dispatch Policy

DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

This marker is recommendation/capability evidence only and grants no authority.

## Exact Required Production Diff

In `_build_codex_argv(...)`, required exact list:

```python
[
    executable,
    "--ask-for-approval",
    "never",
    "exec",
    "--ephemeral",
    "--json",
    "--color",
    "never",
    "--sandbox",
    "workspace-write",
    "-c",
    "sandbox_workspace_write.network_access=false",
    "-c",
    'web_search="disabled"',
    "-C",
    str(workspace),
    "-",
]
```

No other production behavior change is authorized.

## Exact Required Test Diff

Update the existing exact argv assertion and mechanically prove:

```python
argv.count("--ask-for-approval") == 1
argv.index("--ask-for-approval") == 1
argv[1:3] == ["--ask-for-approval", "never"]
argv.index("exec") == 3
argv.index("--ask-for-approval") < argv.index("exec")
```

Retain full exact-list equality and all existing process/payload/environment assertions.

## Allowed Files

Exactly:

```text
src/aios_bridge/executor_transports/codex_local.py
tests/aios_bridge/test_codex_local_transport.py
.ai/results/RESULT-045.md      # Bridge-generated only
```

## Forbidden Scope

Do not modify:

```text
bridge.py
src/aios_bridge/continuity/**
src/aios_bridge/executor_context.py
src/aios_bridge/executor_automation.py
src/aios_bridge/runtime_dispatch.py
src/aios_bridge/runtime_lease.py
tests/test_bridge_executor_automation.py
.ai/proofs/**
```

Do not:
- retry or publish TASK-044;
- implement E5;
- invoke real Codex through E2/E4 while implementing this fix;
- add runtime CLI version/help probing;
- add stderr/stdout capture;
- add retry/fallback;
- create a new transport ID;
- implement M11 or H1-H5;
- auto merge.

## Special Execution Rule

Because TASK-045 repairs the real Codex E2 invocation path itself:

```text
bridge.py execute 45: FORBIDDEN FOR TASK-045 IMPLEMENTATION
```

TASK-045 must use the pre-E4 manual thin-executor path and manual Bridge publication once. This does not count as E5 evidence.

## Targeted Tests

Executor runs only:

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_bridge/test_codex_local_transport.py -q

.\venv\Scripts\python.exe -m pytest tests/aios_bridge/continuity/test_executor_transport.py tests/aios_bridge/test_executor_context_pack.py tests/aios_bridge/test_executor_automation.py -q
```

Do not run full repository suite. Bridge publication owns it.

## Acceptance

```text
ROOT_CAUSE_LOCALIZED: PASS
GLOBAL_APPROVAL_FLAG_BEFORE_EXEC: PASS
APPROVAL_FLAG_EXACTLY_ONCE: PASS
ALL_OTHER_ARGV_UNCHANGED: PASS
PAYLOAD_BYTES_UNCHANGED: PASS
ONE_SPAWN: PASS
SHELL_FALSE: PASS
CLOSED_ENVIRONMENT: PASS
NO_RETRY: PASS
NO_FALLBACK: PASS
RECEIPT_SEMANTICS_UNCHANGED: PASS
E1_E3_E4_UNCHANGED: PASS
HUMAN_AUTHORITY_UNCHANGED: PASS
TARGETED_TESTS: PASS
FULL_REPO_TESTS: PASS
REGRESSIONS: 0
FINAL_INDEPENDENT_AUDIT: PASS
E2_1: PASS
```

Only Human may authorize merge.

After TASK-045 PASS + merge, E5 must restart with a fresh task number and fresh challenge values.
