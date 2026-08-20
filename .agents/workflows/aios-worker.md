---
name: aios-worker
description: >
  Antigravity-only /aios-worker workflow. Operates the AIOS worker protocol
  (RUN TASK-N, FIX TASK-N, STATUS TASK-N) through the repository-owned AIOS
  Bridge control surface with executor identity antigravity.
  THIS WORKFLOW IS THE ANTIGRAVITY /aios-worker SURFACE ONLY.
  It must never serve the Codex $aios-worker surface.
---

# AIOS Worker — Antigravity Workflow

**Surface:** Antigravity `/aios-worker` slash command only.
**Executor identity:** `antigravity` — passed as `--adapter antigravity` to the shared adapter.

> This workflow is the **Antigravity-exclusive** operator surface.
> The Codex `$aios-worker` surface is `.agents/skills/aios-worker/SKILL.md` — a physically separate file.
> Neither surface may infer, reroute, or substitute the other executor.

## Locked Identity Contract

```text
/aios-worker  -> Antigravity workflow -> --adapter antigravity -> executor_id = antigravity
$aios-worker  -> Codex skill          -> --adapter codex       -> executor_id = codex
```

Cross-surface identity confusion is **forbidden**. This workflow must never use `--adapter codex`.

## Explicit Invocation

```text
/aios-worker RUN TASK-N
/aios-worker FIX TASK-N
/aios-worker STATUS TASK-N
```

Where `TASK-N` is the exact user-supplied task identifier (e.g. `TASK-060`).

## Operator Role and Boundaries

The visible Antigravity session is the operator UI and the implementation executor.
For RUN/FIX, this workflow performs handoff via Bridge then continues implementation
in the **same** interactive Antigravity session — Bridge does **not** launch a
separate bounded executor process for the antigravity adapter.

### Strict Execution Constraints

When this workflow is invoked:

1. Parse the exact Human command (`RUN TASK-N`, `FIX TASK-N`, or `STATUS TASK-N`).
2. Treat invocation of this Antigravity workflow as explicit Human selection of executor `antigravity`.
3. Echo the requested task ID, action, and selected executor (`antigravity`).
4. Invoke the checked-in shared adapter script `.agents/skills/aios-worker/scripts/aios_worker.py`
   with **`--adapter antigravity`** using the repository virtual environment interpreter
   (`venv/Scripts/python.exe` on Windows or `venv/bin/python` on POSIX).
   If the repository venv interpreter is absent, fail immediately and notify the Human
   rather than silently selecting an unknown interpreter.
5. **DO NOT** use `--adapter codex`. Using `--adapter codex` from this workflow is **forbidden**.
6. **DO NOT** invoke raw `codex` or `codex exec` directly.
7. **DO NOT** call `bridge.py approve` directly.
8. **DO NOT** call `bridge.py publish` directly.
9. **DO NOT** call `bridge.py execute` directly (that is the Codex executor path only).
10. **DO NOT** run `bridge.py context`.
11. **DO NOT** perform automatic retries or rerouting upon failure.
12. **DO NOT** authorize or perform branch merge (`MERGE` is strictly reserved for the Human
    and ChatGPT review boundary).
13. **DO NOT** delegate or reroute to the Codex `$aios-worker` skill.
14. After successful handoff, continue the implementation work in this same Antigravity session.
15. On task completion and Bridge publication, instruct the Human:
    ```text
    Review TASK-N in ChatGPT
    ```

## Command Details

### RUN TASK-N

Authorizes a new task run via Bridge handoff (antigravity adapter = handoff only, no auto-execute):

```powershell
.\venv\Scripts\python.exe .agents/skills/aios-worker/scripts/aios_worker.py RUN TASK-N --adapter antigravity
```

After the handoff succeeds, implementation continues in this Antigravity session.

### FIX TASK-N

Authorizes a fix run on an active review via Bridge handoff:

```powershell
.\venv\Scripts\python.exe .agents/skills/aios-worker/scripts/aios_worker.py FIX TASK-N --adapter antigravity
```

After the handoff succeeds, fix implementation continues in this Antigravity session.

### STATUS TASK-N

Synchronizes control plane artifacts and displays pending tasks non-destructively:

```powershell
.\venv\Scripts\python.exe .agents/skills/aios-worker/scripts/aios_worker.py STATUS TASK-N --adapter antigravity
```

STATUS is non-authorizing and never acquires leases or triggers execution on either surface.
