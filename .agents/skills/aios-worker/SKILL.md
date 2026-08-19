---
name: aios-worker
description: Operate the AIOS worker workflow (RUN TASK-N, FIX TASK-N, STATUS TASK-N) through the repository-owned AIOS Bridge control surface.
---

# AIOS Worker Operator Skill

This repository-scoped skill allows Human operators to trigger canonical AIOS worker workflows from Codex.

## Explicit Invocation

```text
$aios-worker RUN TASK-N
$aios-worker FIX TASK-N
$aios-worker STATUS TASK-N
```

Where `TASK-N` is the exact user-supplied task identifier (e.g. `TASK-048`).

## Operator Role and Boundaries

The visible Codex session is the operator UI. For RUN/FIX, Bridge E2/E4 launches the bounded executor Codex process; the visible session must not duplicate the implementation work.

### Strict Execution Constraints

When this skill is invoked:
1. Parse the exact Human command (`RUN TASK-N`, `FIX TASK-N`, or `STATUS TASK-N`).
2. Treat invocation of this Codex skill as explicit Human selection of executor `codex`.
3. Echo the requested task ID, action, and selected executor (`codex`).
4. Invoke the checked-in shared adapter script `.agents/skills/aios-worker/scripts/aios_worker.py` with `--adapter codex` using the repository virtual environment interpreter (`venv/Scripts/python.exe` on Windows or `venv/bin/python` on POSIX). If the repository venv interpreter is absent, fail immediately and notify the Human rather than silently selecting an unknown interpreter.
5. **DO NOT** edit implementation or test files in the parent Codex session.
6. **DO NOT** manually read, parse, or reconstruct `TASK-*.md`, `ADR-*.md`, or blueprints as executor context.
7. **DO NOT** run `bridge.py context`.
8. **DO NOT** invoke raw `codex` or `codex exec` directly.
9. **DO NOT** call `bridge.py approve` directly.
10. **DO NOT** call `bridge.py publish` directly.
11. **DO NOT** perform automatic retries or rerouting upon failure.
12. **DO NOT** authorize or perform branch merge (`MERGE` is strictly reserved for the Human and ChatGPT review boundary).
13. On successful execution, instruct the Human:
    ```text
    Review TASK-N in ChatGPT
    ```

## Command Details

### RUN TASK-N
Authorizes and executes a new task run via Bridge:
```powershell
.\venv\Scripts\python.exe .agents/skills/aios-worker/scripts/aios_worker.py RUN TASK-N --adapter codex
```

### FIX TASK-N
Authorizes and executes a fix run on an active review via Bridge:
```powershell
.\venv\Scripts\python.exe .agents/skills/aios-worker/scripts/aios_worker.py FIX TASK-N --adapter codex
```

### STATUS TASK-N
Synchronizes control plane artifacts and displays pending tasks non-destructively:
```powershell
.\venv\Scripts\python.exe .agents/skills/aios-worker/scripts/aios_worker.py STATUS TASK-N --adapter codex
```
STATUS is non-authorizing and never acquires leases or triggers execution.
