---
# Format: UTF-8 without BOM, LF line endings
name: aios-worker
description: >
  Codex-only $aios-worker skill. Operates the AIOS worker protocol
  (RUN TASK-N, FIX TASK-N, STATUS TASK-N) through the exact pinned AIOS-renew
  kernel with executor identity codex.
  THIS SKILL IS THE CODEX $aios-worker SURFACE ONLY.
  It must never serve the Antigravity /aios-worker surface.
---

# AIOS-renew Worker Operator Skill — Codex Surface

**Surface:** Codex `$aios-worker` skill invocation only.
**Executor identity:** `codex` — passed as `--executor codex` to the shared launcher.

> This skill is the **Codex-exclusive** operator surface.
> The Antigravity `/aios-worker` surface is `.agents/workflows/aios-worker.md` — a physically separate file.
> Neither surface may infer, reroute, or substitute the other executor.
> This skill must **never** serve the Antigravity `/aios-worker` slash command.

## Locked Identity Contract

```text
$aios-worker  -> Codex skill          -> executor codex       -> AIOS-renew
/aios-worker  -> Antigravity workflow -> executor antigravity -> AIOS-renew
```

Cross-surface identity confusion is **forbidden**. This skill must never select
the Antigravity executor.

## Explicit Invocation

```text
$aios-worker RUN TASK-N
$aios-worker FIX TASK-N
$aios-worker STATUS TASK-N
```

Where `TASK-N` is the exact user-supplied task identifier (e.g. `TASK-048`).

## Operator Role and Boundaries

The visible Codex session is only the operator UI. For RUN/FIX, the pinned
AIOS-renew kernel launches the one bounded Codex executor. The visible session
must not inspect the TASK as implementation context, edit product files, execute
verification, synthesize evidence, or duplicate the implementation work.

### Strict Execution Constraints

When this skill is invoked:

1. Parse the exact Human command (`RUN TASK-N`, `FIX TASK-N`, or `STATUS TASK-N`).
2. Treat invocation of this Codex skill as explicit Human selection of executor `codex`.
3. Echo the requested task ID, action, and selected executor (`codex`).
4. Invoke the checked-in shared adapter script `.agents/skills/aios-worker/scripts/aios_worker.py`
   with **`--executor codex`** using an available Python 3.11+ bootstrap
   interpreter. The launcher creates and proves its separate repository-local
   pinned runtime; do not require the product virtualenv or a global `aios` command.
5. **DO NOT** select the Antigravity executor from this skill.
6. **DO NOT** edit implementation or test files in the parent Codex session.
7. **DO NOT** manually reconstruct TASK, RESULT, EVIDENCE, REVIEW, or REMEDIATION semantics.
8. **DO NOT** invoke raw `codex` or `codex exec` directly.
9. **DO NOT** perform automatic retries or executor rerouting upon failure.
10. **DO NOT** authorize or perform branch merge. Publication is the launcher's
    guarded normal push to the already-configured upstream after AIOS-renew PASS.
11. **DO NOT** delegate or reroute to the Antigravity `/aios-worker` workflow.
12. Reload or start a fresh Codex session after the migration commit so this
    repository-owned skill is not served from a stale cache.
13. On successful execution and publication, instruct the Human:
    ```text
    Review TASK-N in ChatGPT
    ```

## Command Details

### RUN TASK-N

Delegates one primary execution to AIOS-renew and publishes an advancing PASS:

```powershell
python .agents/skills/aios-worker/scripts/aios_worker.py RUN TASK-N --executor codex
```

### FIX TASK-N

Resolves one exact local canonical REVIEW/REMEDIATION lineage and delegates only
AIOS-renew remediation semantics. Missing, ambiguous, or invalid lineage fails closed.

```powershell
python .agents/skills/aios-worker/scripts/aios_worker.py FIX TASK-N --executor codex
```

### STATUS TASK-N

Delegates to AIOS-renew task description semantics. STATUS is read-only for the
product worktree, branch, TASK/RUN state, publication, and executor authority.

```powershell
python .agents/skills/aios-worker/scripts/aios_worker.py STATUS TASK-N --executor codex
```

STATUS may initialize the dedicated untracked worker runtime but must not invoke
an executor or become a second status/review authority.
