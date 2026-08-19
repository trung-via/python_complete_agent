# TASK-048 — Unified AIOS Worker Control Surface — Implementation Blueprint

STATUS: LOCKED BLUEPRINT
BASELINE_MAIN_SHA: 22a05d1f4880daf3a9f964e0564c658b051039cd
TARGET_BRANCH: ai/task-048
CLASS: OPERATOR ADAPTER / CODEX SKILL / ANTIGRAVITY PARITY
BOOTSTRAP_EXECUTOR: antigravity

## Contract Anchor

```text
ADR_PATH: .ai/decisions/ADR-037-UNIFIED-AIOS-WORKER-CONTROL-SURFACE-CONTRACT-LOCK.md
ADR_BLOB_SHA: 6c30cd6d2b9dea5dd4d20b687353471ba80dae8b
```

## Objective

Create a repository-scoped Codex `aios-worker` skill plus one thin shared adapter script so the Human can operate AIOS from Codex with the same semantic workflow previously used from Antigravity.

Normal Codex operator UX after merge:

```text
$aios-worker RUN TASK-N
$aios-worker FIX TASK-N
$aios-worker STATUS TASK-N
```

No routine Human PowerShell sequence.

## Exact Allowed Files

Create/update exactly:

```text
.agents/skills/aios-worker/SKILL.md
.agents/skills/aios-worker/scripts/aios_worker.py
tests/aios_bridge/test_aios_worker_control_surface.py
docs/AIOS_UNIFIED_WORKER_WORKFLOW.md
```

Do not modify `bridge.py`.

## Shared Adapter Script

Path:

```text
.agents/skills/aios-worker/scripts/aios_worker.py
```

### CLI

Accept exactly:

```text
aios_worker.py RUN TASK-<digits> --adapter <codex|antigravity>
aios_worker.py FIX TASK-<digits> --adapter <codex|antigravity>
aios_worker.py STATUS TASK-<digits> --adapter <codex|antigravity>
```

Case-sensitive canonical output action may be normalized internally only after strict parsing of accepted upper-case verbs.

Reject:
- unknown verbs;
- missing task;
- non-canonical task forms;
- zero/negative/non-digit task IDs;
- unknown adapter;
- extra positional arguments.

Do not support MERGE.

### Repository / Interpreter

Resolve repository root deterministically from the checked-in script location, not from an arbitrary current directory.

Expected checked-in layout:

```text
<repo>/.agents/skills/aios-worker/scripts/aios_worker.py
```

Use `sys.executable` as the interpreter for every Bridge child command.

Bridge path must be exact:

```text
<repo>/bridge.py
```

Fail closed if it is missing/not a file.

Use `subprocess.run` with:
- argv list;
- `shell=False`;
- `cwd=<repo root>`;
- inherited normal stdout/stderr so the UI shows Bridge output;
- no command-string shell composition.

Do not call Git directly.
Do not inspect or mutate Bridge runtime files directly.

### RUN — Codex adapter

Invoke exactly once, in order:

```text
<sys.executable> bridge.py handoff <N> --action run --executor codex
<sys.executable> bridge.py execute <N>
```

Only invoke `execute` if `handoff` exits 0.

If either command exits nonzero:
- return that nonzero code;
- stop immediately;
- no retry;
- no fallback;
- no publish substitute;
- no cleanup/reset/stash/revert.

On success print a concise terminal message containing:

```text
AIOS_WORKER_STATUS: PUBLISHED
TASK_ID: TASK-N
ACTION: RUN
EXECUTOR: codex
NEXT: Review TASK-N in ChatGPT
```

Do not invent the published SHA; Bridge already prints authoritative publication evidence.

### FIX — Codex adapter

Same structure, except first command is:

```text
<sys.executable> bridge.py handoff <N> --action fix --executor codex
```

Then exact one `bridge.py execute <N>` on successful handoff.

Handoff remains responsible for validating authoritative `CHANGES_REQUIRED` review state.

Success output uses `ACTION: FIX`.

### RUN/FIX — Antigravity adapter

The shared script provides parity at the Bridge authorization boundary.

Invoke exactly once:

```text
<sys.executable> bridge.py handoff <N> --action <run|fix> --executor antigravity
```

Do NOT invoke `bridge.py execute`, because E4 v1 automated transport is Codex-only and the visible Antigravity session remains its executor UI.

After successful handoff print:

```text
AIOS_WORKER_STATUS: AUTHORIZED
TASK_ID: TASK-N
ACTION: <RUN|FIX>
EXECUTOR: antigravity
NEXT: continue in the authorized Antigravity worker session
```

This task does not redesign the existing Antigravity worker implementation.

### STATUS — both adapters

STATUS is non-authorizing.

Invoke, in order:

```text
<sys.executable> bridge.py sync
<sys.executable> bridge.py pending
```

If `sync` fails, do not run `pending`.

STATUS MUST NOT invoke any of:

```text
handoff
approve
execute
publish
hot-handoff
merge
codex
```

Print exact requested task ID and adapter for operator orientation, but do not manufacture task state beyond Bridge output.

## Codex Skill

Path:

```text
.agents/skills/aios-worker/SKILL.md
```

Must have valid YAML frontmatter:

```yaml
---
name: aios-worker
description: ...
---
```

Description must front-load triggers for `RUN TASK-`, `FIX TASK-`, and `STATUS TASK-` and state that this is the AIOS Bridge operator workflow.

### Explicit invocation

Document:

```text
$aios-worker RUN TASK-048
$aios-worker FIX TASK-048
$aios-worker STATUS TASK-048
```

The exact task number is user-supplied; examples do not authorize any task.

### Skill behavior

For RUN/FIX:
1. Parse exact Human request.
2. Treat use of the Codex skill as explicit executor selection `codex`.
3. Echo task/action/executor.
4. Invoke the checked-in adapter script with `--adapter codex` using the repository venv Python when present; if the repository venv interpreter is absent, fail and tell the Human rather than silently selecting an unknown interpreter.
5. Do not edit implementation files in the parent Codex session.
6. Do not manually read/reconstruct TASK/ADR/blueprint as executor context.
7. Do not run `bridge.py context`.
8. Do not run `codex exec` directly.
9. Do not call `bridge.py approve` directly.
10. Do not call `bridge.py publish` directly.
11. Do not retry.
12. On success tell Human to return to ChatGPT with `Review TASK-N`.

For STATUS, invoke adapter STATUS only. STATUS never asks to execute task work.

### Parent vs child Codex boundary

Lock this sentence semantically in the skill:

```text
The visible Codex session is the operator UI. For RUN/FIX, Bridge E2/E4 launches the bounded executor Codex process; the visible session must not duplicate the implementation work.
```

## Documentation

Create:

```text
docs/AIOS_UNIFIED_WORKER_WORKFLOW.md
```

Document the single semantic protocol and the two UI forms:

```text
Antigravity  /aios-worker RUN TASK-N
Codex        $aios-worker RUN TASK-N
```

Include RUN, FIX, STATUS, review loop, and merge boundary.

Clearly state:
- Bridge/GitHub/external runtime are shared state;
- switching UI does not create a new task state;
- second/incompatible execution is rejected by Bridge;
- Codex routine flow no longer requires manual PowerShell;
- PowerShell remains diagnosis/recovery/bootstrap only;
- MERGE remains ChatGPT/Human boundary, not a worker command.

## Exact Tests

Path:

```text
tests/aios_bridge/test_aios_worker_control_surface.py
```

No real Codex, no real Bridge mutation, no network.
Mock subprocess boundaries.

Required tests at minimum:

1. canonical RUN/FIX/STATUS TASK IDs parse;
2. malformed action rejected;
3. malformed TASK IDs rejected (`TASK-0`, negative, lowercase, padding, suffix, missing digits);
4. unknown adapter rejected;
5. Codex RUN invokes exact handoff argv then exact execute argv;
6. Codex FIX invokes exact fix handoff then execute;
7. every Bridge child uses `sys.executable`, exact repo `bridge.py`, list argv, `shell=False`, exact repo cwd;
8. handoff nonzero prevents execute;
9. execute nonzero is returned and never retried;
10. no fallback/reroute command occurs;
11. Antigravity RUN/FIX invokes handoff only and never execute;
12. STATUS invokes sync then pending only;
13. STATUS sync failure prevents pending;
14. STATUS never invokes handoff/approve/execute/publish/codex;
15. script never invokes `bridge.py publish`;
16. script never invokes `bridge.py approve`;
17. script never invokes raw `codex`/`codex exec`;
18. MERGE is rejected;
19. SKILL.md exists with exact `name: aios-worker`;
20. skill text includes RUN/FIX/STATUS triggers;
21. skill forbids parent-session implementation duplication;
22. skill routes RUN/FIX through adapter with `--adapter codex`;
23. skill forbids context/approve/publish/direct codex exec/retry/merge;
24. docs state Antigravity/Codex parity and shared Bridge state;
25. no network or external API call exists in adapter.

## Bootstrap Test Command

Executor runs only:

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_bridge/test_aios_worker_control_surface.py -q
```

Bridge publication owns the repository-wide suite under the existing workflow.

## Forbidden Scope

Do not modify:

```text
bridge.py
src/**
.ai/tasks/**
.ai/reviews/**
.ai/decisions/**
.ai/context/**
.ai/proofs/**
```

except Bridge-generated `.ai/results/RESULT-048.md` during publication.

Do not:
- modify E1-E5;
- implement M11.1/M11.2/M11.3;
- reactivate TASK-047;
- add paid API behavior;
- add automatic merge;
- add auto retry/failover;
- alter Human authority semantics;
- activate H-Series.

## Completion

After targeted tests pass, STOP at the existing Bridge publication/review boundary.

TASK-048 PASS proves the adapter implementation contract. The first post-merge reissued M11.1 task will provide the real Codex-UI operational proof.
