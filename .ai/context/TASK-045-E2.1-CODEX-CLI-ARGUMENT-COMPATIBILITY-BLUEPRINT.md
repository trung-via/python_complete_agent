# TASK-045 — E2.1 Codex CLI Argument Compatibility — Implementation Blueprint

STATUS: LOCKED BLUEPRINT
BASELINE_MAIN_SHA: a01b5f4b028ccdc416004b3d25608d23fb922c51
TARGET_BRANCH: ai/task-045
EXECUTOR_MODE: THIN_EXECUTOR
MILESTONE: E2.1

## Contract Anchor

```text
ADR_PATH: .ai/decisions/ADR-034-E2.1-CODEX-CLI-GLOBAL-APPROVAL-FLAG-COMPATIBILITY-CONTRACT-LOCK.md
ADR_BLOB_SHA: cbe66ff7ae5db159ed96c0310f1271d9527d3bae
```

## Current Production Anchors

```text
E2_CODEX_LOCAL_PATH: src/aios_bridge/executor_transports/codex_local.py
E2_CODEX_LOCAL_BLOB_SHA: dd1fae54506459a2a638441a35d5a327d89da8cc
E2_TEST_PATH: tests/aios_bridge/test_codex_local_transport.py
E2_TEST_BLOB_SHA: 366ba89921d462bca1b908b4628d055099753f90
```

## Objective

Make the smallest possible compatibility correction to the existing E2 argv builder so Codex CLI 0.147.0 receives the global approval policy flag before the `exec` subcommand.

This is not an E2 redesign and not an E5 implementation.

## Exact Production Change

Edit only `_build_codex_argv(executable: str, workspace: Path)` in:

```text
src/aios_bridge/executor_transports/codex_local.py
```

Current sequence:

```python
[
    executable,
    "exec",
    "--ephemeral",
    "--json",
    "--color",
    "never",
    "--sandbox",
    "workspace-write",
    "--ask-for-approval",
    "never",
    "-c",
    "sandbox_workspace_write.network_access=false",
    "-c",
    'web_search="disabled"',
    "-C",
    str(workspace),
    "-",
]
```

Required sequence:

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

Do not refactor the function, introduce constants for flags, add version detection, run `codex --help`, probe CLI capabilities, capture stderr, or add compatibility branches.

## Exact Test Change

Edit only the existing exact argv test in:

```text
tests/aios_bridge/test_codex_local_transport.py
```

Update the expected argv list to the required sequence.

Add explicit assertions after the exact-list assertion:

```python
assert argv.count("--ask-for-approval") == 1
approval_index = argv.index("--ask-for-approval")
exec_index = argv.index("exec")
assert argv[approval_index : approval_index + 2] == ["--ask-for-approval", "never"]
assert approval_index < exec_index
assert approval_index == 1
assert exec_index == 3
```

Equivalent assertions are allowed only if they prove the same exact properties without weakening the full-list equality.

Do not add a real Codex invocation test.

## Invariants That Must Remain Byte/Behavior Equivalent

Outside the moved approval flag pair, preserve exactly:

```text
executable
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

Preserve all invocation runtime behavior:

```text
workspace resolution
Git root/branch/clean preflight
codex executable resolution
minimal environment
secret denylist
shell=False
stdin PIPE
exact payload bytes
stdout DEVNULL
stderr DEVNULL
one Popen
no retry
no fallback
timeout mapping
interrupt mapping
nonzero exit mapping
Windows cleanup
POSIX cleanup
E1 validators
```

## Allowed Files

Executor may change exactly:

```text
src/aios_bridge/executor_transports/codex_local.py
tests/aios_bridge/test_codex_local_transport.py
```

Bridge-generated publication artifact:

```text
.ai/results/RESULT-045.md
```

## Forbidden Scope

Do not change:

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

Do not modify TASK-044 evidence or retry TASK-044.
Do not implement E5/M11/H-Series.

## Thin Executor Read Budget

Read only:

```text
.ai/tasks/TASK-045.md
.ai/decisions/ADR-034-E2.1-CODEX-CLI-GLOBAL-APPROVAL-FLAG-COMPATIBILITY-CONTRACT-LOCK.md
.ai/context/TASK-045-E2.1-CODEX-CLI-ARGUMENT-COMPATIBILITY-BLUEPRINT.md
src/aios_bridge/executor_transports/codex_local.py
tests/aios_bridge/test_codex_local_transport.py
```

No broad repository search is needed.

## Targeted Tests

Executor runs only:

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_bridge/test_codex_local_transport.py -q

.\venv\Scripts\python.exe -m pytest tests/aios_bridge/continuity/test_executor_transport.py tests/aios_bridge/test_executor_context_pack.py tests/aios_bridge/test_executor_automation.py -q
```

Do not run full repository suite; Bridge publication owns the full suite.

Do not invoke real Codex through E2/E4 while implementing the fix.

## Completion

When targeted tests are green:
- report exact files changed;
- report exact targeted test counts;
- report blockers;
- STOP.

Do not commit.
Do not push.
Do not publish.
Do not retry TASK-044.
