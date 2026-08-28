---
# Format: UTF-8 without BOM, LF line endings
name: aios-worker
description: >
  Antigravity-only /aios-worker workflow. Operates the AIOS worker protocol
  (RUN TASK-N, FIX TASK-N, STATUS TASK-N) through the exact pinned AIOS-renew
  kernel with executor identity antigravity.
  THIS WORKFLOW IS THE ANTIGRAVITY /aios-worker SURFACE ONLY.
  It must never serve the Codex $aios-worker surface.
---

# AIOS-renew Worker — Antigravity Workflow

**Surface:** Antigravity `/aios-worker` slash command only.
**Executor identity:** `antigravity` — passed as `--executor antigravity` to the shared launcher.

> This workflow is the **Antigravity-exclusive** operator surface.
> The Codex `$aios-worker` surface is `.agents/skills/aios-worker/SKILL.md` — a physically separate file.
> Neither surface may infer, reroute, or substitute the other executor.

## Locked Identity Contract

```text
/aios-worker  -> Antigravity workflow -> executor antigravity -> AIOS-renew
$aios-worker  -> Codex skill          -> executor codex       -> AIOS-renew
```

Cross-surface identity confusion is **forbidden**. This workflow must never select
the Codex executor.

## Explicit Invocation

```text
/aios-worker RUN TASK-N
/aios-worker FIX TASK-N
/aios-worker STATUS TASK-N
```

Where `TASK-N` is the exact user-supplied task identifier (e.g. `TASK-060`).

## Operator Role and Boundaries

The visible Antigravity session is only the operator UI. For RUN/FIX, the pinned
AIOS-renew kernel launches the one Antigravity executor adapter. The visible
session must not inspect the TASK as implementation context, edit product files,
execute verification, synthesize evidence, or continue implementation after dispatch.

### Strict Execution Constraints

When this workflow is invoked:

1. Parse the exact Human command (`RUN TASK-N`, `FIX TASK-N`, or `STATUS TASK-N`).
2. Treat invocation of this Antigravity workflow as explicit Human selection of executor `antigravity`.
3. Echo the requested task ID, action, and selected executor (`antigravity`).
4. Invoke the checked-in shared adapter script `.agents/skills/aios-worker/scripts/aios_worker.py`
   with **`--executor antigravity`** using an available Python 3.11+ bootstrap
   interpreter. The launcher creates and proves its separate repository-local
   pinned runtime; do not require the product virtualenv or a global `aios` command.
5. **DO NOT** select the Codex executor from this workflow.
6. **DO NOT** invoke raw `codex`, `codex exec`, or `agy` directly.
7. **DO NOT** manually reconstruct TASK, RESULT, EVIDENCE, REVIEW, or REMEDIATION semantics.
8. **DO NOT** perform automatic retries or executor rerouting upon failure.
9. **DO NOT** authorize or perform branch merge. Publication is the launcher's
   guarded normal push to the already-configured upstream after AIOS-renew PASS.
10. **DO NOT** delegate or reroute to the Codex `$aios-worker` skill.
11. **DO NOT** continue implementation in this visible session after dispatch.
12. Reload or start a fresh Antigravity session after the migration commit so
    this repository-owned workflow is not served from a stale cache.
13. On successful execution and publication, instruct the Human:
    ```text
    Review TASK-N in ChatGPT
    ```

## Command Details

### RUN TASK-N

Delegates one primary execution to AIOS-renew and publishes an advancing PASS:

```powershell
python .agents/skills/aios-worker/scripts/aios_worker.py RUN TASK-N --executor antigravity
```

### FIX TASK-N

Resolves one exact local canonical REVIEW/REMEDIATION lineage and delegates only
AIOS-renew remediation semantics. Missing, ambiguous, or invalid lineage fails closed.

```powershell
python .agents/skills/aios-worker/scripts/aios_worker.py FIX TASK-N --executor antigravity
```

### STATUS TASK-N

Delegates to AIOS-renew task description semantics. STATUS is read-only for the
product worktree, branch, TASK/RUN state, publication, and executor authority.

```powershell
python .agents/skills/aios-worker/scripts/aios_worker.py STATUS TASK-N --executor antigravity
```

STATUS may initialize the dedicated untracked worker runtime but must not invoke
an executor or become a second status/review authority.
