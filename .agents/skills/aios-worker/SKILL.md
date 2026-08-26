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

The visible Codex session is the operator UI and the implementation executor.
For RUN/FIX implementation mode, this skill performs handoff via Bridge adapter, receives `AUTHORIZED`,
and continues implementation in the **same** interactive Codex session — Bridge does **not** launch a
nested child executor process for normal Codex runs.

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
6. **DO NOT** invoke raw `codex` or `codex exec` directly.
7. **DO NOT** call `bridge.py approve` directly.
8. **DO NOT** call `bridge.py execute` directly.
9. **DO NOT** perform automatic retries or rerouting upon failure.
10. **DO NOT** authorize or perform branch merge (worker executors NEVER merge;
    the ChatGPT review boundary may auto-merge after PASS under ADR-042 standing Human authorization).
11. **DO NOT** delegate or reroute to the Antigravity `/aios-worker` workflow.
12. After successful handoff (`AUTHORIZED`), inspect the compact interactive context emitted by handoff.
13. Read only the exact authorized `TASK-*.md`/`REVIEW-*.md` plus bounded semantic refs exposed by Bridge.
14. Edit only authorized paths in `allowed_paths`.
15. Run bounded targeted T0/T1 tests.
16. Invoke existing canonical Bridge publish (`python bridge.py publish N ...`) using exact active authorization and targeted test command.
17. On task completion and Bridge publication, instruct the Human:
    ```text
    Review TASK-N in ChatGPT
    ```

## Command Details

### RUN TASK-N

Authorizes a new task run via Bridge handoff in a single-command transaction (automatically synchronizes before handoff, without requiring prior STATUS):

```powershell
.\venv\Scripts\python.exe .agents/skills/aios-worker/scripts/aios_worker.py RUN TASK-N --adapter codex
```

After handoff succeeds (`AUTHORIZED`), implementation continues in this Codex session.

### FIX TASK-N

Authorizes and processes a fix run on an active review via Bridge in a single-command transaction:

- **IMPLEMENTATION mode (default)**: performs handoff and continues fix implementation in this Codex session upon receiving `AUTHORIZED`.
- **EVIDENCE_REFRESH mode**: performs handoff, skips executor invocation, certifies canonical test suite, and republishes RESULT directly.

```powershell
.\venv\Scripts\python.exe .agents/skills/aios-worker/scripts/aios_worker.py FIX TASK-N --adapter codex
```

### STATUS TASK-N

Synchronizes control plane artifacts and displays pending tasks non-destructively:

```powershell
.\venv\Scripts\python.exe .agents/skills/aios-worker/scripts/aios_worker.py STATUS TASK-N --adapter codex
```

STATUS is diagnostic/non-authorizing and is not a prerequisite for RUN or FIX.
