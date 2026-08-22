---
# Format: UTF-8 without BOM, LF line endings
name: aios-worker
description: >
  Codex-only $aios-worker skill. Operates the AIOS worker protocol
  (RUN TASK-N, FIX TASK-N, STATUS TASK-N) through the repository-owned AIOS
  Bridge control surface with executor identity codex.
  THIS SKILL IS THE CODEX $aios-worker SURFACE ONLY.
  It must never serve the Antigravity /aios-worker surface.
---

# AIOS Worker Operator Skill — Codex Surface

**Surface:** Codex `$aios-worker` skill invocation only.
**Executor identity:** `codex` — passed as `--adapter codex` to the shared adapter.

> This skill is the **Codex-exclusive** operator surface.
> The Antigravity `/aios-worker` surface is `.agents/workflows/aios-worker.md` — a physically separate file.
> Neither surface may infer, reroute, or substitute the other executor.
> This skill must **never** serve the Antigravity `/aios-worker` slash command.

## Locked Identity Contract

```text
$aios-worker  -> Codex skill          -> --adapter codex       -> executor_id = codex
/aios-worker  -> Antigravity workflow -> --adapter antigravity -> executor_id = antigravity
```

Cross-surface identity confusion is **forbidden**. This skill must never use `--adapter antigravity`.

## Explicit Invocation

```text
$aios-worker RUN TASK-N
$aios-worker FIX TASK-N
$aios-worker STATUS TASK-N
```

Where `TASK-N` is the exact user-supplied task identifier (e.g. `TASK-048`).

## Operator Role and Boundaries

The visible Codex session is the operator UI. For RUN/FIX, Bridge E2/E4 launches the bounded executor
Codex process; the visible session must not duplicate the implementation work.

### Strict Execution Constraints

When this skill is invoked:

1. Parse the exact Human command (`RUN TASK-N`, `FIX TASK-N`, or `STATUS TASK-N`).
2. Treat invocation of this Codex skill as explicit Human selection of executor `codex`.
3. Echo the requested task ID, action, and selected executor (`codex`).
4. Invoke the checked-in shared adapter script `.agents/skills/aios-worker/scripts/aios_worker.py`
   with **`--adapter codex`** using the repository virtual environment interpreter
   (`venv/Scripts/python.exe` on Windows or `venv/bin/python` on POSIX).
   If the repository venv interpreter is absent, fail immediately and notify the Human
   rather than silently selecting an unknown interpreter.
5. **DO NOT** use `--adapter antigravity`. Using `--adapter antigravity` from this skill is **forbidden**.
6. **DO NOT** edit implementation or test files in the parent Codex session.
7. **DO NOT** manually read, parse, or reconstruct `TASK-*.md`, `ADR-*.md`, or blueprints as executor context.
8. **DO NOT** run `bridge.py context`.
9. **DO NOT** invoke raw `codex` or `codex exec` directly.
10. **DO NOT** call `bridge.py approve` directly.
11. **DO NOT** call `bridge.py publish` directly.
12. **DO NOT** perform automatic retries or rerouting upon failure.
13. **DO NOT** authorize or perform branch merge (`MERGE` is strictly reserved for the Human
    and ChatGPT review boundary).
14. **DO NOT** delegate or reroute to the Antigravity `/aios-worker` workflow.
15. On successful execution, instruct the Human:
    ```text
    Review TASK-N in ChatGPT
    ```

## Command Details

### RUN TASK-N

Authorizes and executes a new task run via Bridge (codex adapter = handoff + execute):

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

STATUS is non-authorizing and never acquires leases or triggers execution on either surface.
