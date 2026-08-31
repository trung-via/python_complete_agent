---
# Format: UTF-8 without BOM, LF line endings
name: aios-worker
description: >
  Codex-only $aios-worker skill. Operates the AIOS worker protocol
  (RUN TASK-N, FIX TASK-N FINDING-ID, STATUS TASK-N) through the exact pinned AIOS-renew
  kernel with executor identity codex.
  THIS SKILL IS THE CODEX $aios-worker SURFACE ONLY.
  It must never serve the Antigravity /aios-renew-worker surface.
---

# AIOS-renew Worker Operator Skill — Codex Surface

**Surface:** Codex `$aios-worker` skill invocation only.
**Executor identity:** `codex` — passed as `--executor codex` to the shared launcher.

> This skill is the **Codex-exclusive** operator surface.
> The active Antigravity surface is `/aios-renew-worker` (`.agents/workflows/aios-renew-worker.md`) — a physically separate file.
> The historical Antigravity `/aios-worker` namespace is permanently retired and fail-closed.
> Neither surface may infer, reroute, or substitute the other executor.

## Locked Identity Contract

```text
$aios-worker        -> Codex skill          -> executor codex       -> AIOS-renew
/aios-renew-worker  -> Antigravity workflow -> executor antigravity -> AIOS-renew
```

Cross-surface identity confusion is **forbidden**. This skill must never select
the Antigravity executor.

## Explicit Invocation

```text
$aios-worker RUN TASK-N
$aios-worker FIX TASK-N FINDING-ID
$aios-worker STATUS TASK-N
```

Where `TASK-N` is the exact user-supplied task identifier (e.g. `TASK-048`)
and `FINDING-ID` is the exact Human-supplied remediation finding identifier.

## Operator Role and Boundaries

The visible Codex session is only the operator UI. For RUN/FIX, the pinned
AIOS-renew kernel launches the one bounded Codex executor. The visible session
must not inspect the TASK as implementation context, edit product files, execute
verification, synthesize evidence, or duplicate the implementation work.

### Strict Execution Constraints

When this skill is invoked:

1. Parse the exact Human command (`RUN TASK-N`, `FIX TASK-N FINDING-ID`, or
   `STATUS TASK-N`). Missing FIX finding identifiers fail before kernel invocation.
2. Treat invocation of this Codex skill as explicit Human selection of executor `codex`.
3. Echo the requested task ID, action, and selected executor (`codex`).
4. Invoke the checked-in shared adapter script `.agents/skills/aios-worker/scripts/aios_worker.py`
   with **`--executor codex`** using the deterministic Python 3.11+ bootstrap-host
   resolution contract below. Invoke the launcher exactly once after probing.
   The launcher creates and proves its separate repository-local pinned runtime;
   the bootstrap host is never AIOS-renew runtime authority.
5. **DO NOT** select the Antigravity executor from this skill.
6. **DO NOT** edit implementation or test files in the parent Codex session.
7. **DO NOT** manually reconstruct TASK, RESULT, EVIDENCE, REVIEW, or REMEDIATION semantics.
8. **DO NOT** invoke raw `codex` or `codex exec` directly.
9. **DO NOT** perform automatic retries or executor rerouting upon failure.
10. **DO NOT** perform publication, push, or branch merge. Successful RUN/FIX leaves
    the advancing implementation commit local for ChatGPT semantic review.
    Guarded publication occurs only after explicit semantic REVIEW PASS.
11. **DO NOT** delegate or reroute to the Antigravity `/aios-renew-worker` workflow.
12. Reload or start a fresh Codex session after the migration commit so this
    repository-owned skill is not served from a stale cache.
13. On successful canonical AIOS PASS, instruct the Human:
    ```text
    Review TASK-N in ChatGPT
    ```

## Deterministic Bootstrap-Host Resolution

Resolve the repository root first. Probe candidate argv in this exact order;
probing is environment discovery and must never invoke AIOS-renew:

- Windows: repository-local `venv/Scripts/python.exe` when present, then
  `py -3.11`, then `python3`, then `python`.
- POSIX: repository-local `venv/bin/python` when present, then `python3`, then
  `python`.

For each candidate, execute only this version probe:

```text
<candidate argv> -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
```

Select the first candidate returning zero, append the launcher/action arguments,
and invoke the launcher exactly once. A missing command or nonzero probe advances
to the next documented candidate. If none qualifies, stop before dispatch and
report exactly `BOOTSTRAP_INTERPRETER_UNAVAILABLE`. Do not install AIOS-renew in
the selected bootstrap host; AIOS-renew runs only from the launcher's separate
`.git/aios/worker-runtime`.

## Command Details

### RUN TASK-N

Delegates one primary execution to AIOS-renew and leaves HEAD local for semantic review:

```powershell
<resolved bootstrap-host argv> .agents/skills/aios-worker/scripts/aios_worker.py RUN TASK-N --executor codex
```

### FIX TASK-N FINDING-ID

Delegates the exact task and Human-supplied finding identifier once to AIOS-renew,
which owns canonical remote remediation lineage resolution. The worker does not
inspect HEAD or local REVIEW/REMEDIATION artifacts, infer a finding, or pass local
lineage, sandbox, scope, or verification authority. Missing finding identifiers
fail before kernel invocation. Leaves HEAD local for semantic review:

```powershell
<resolved bootstrap-host argv> .agents/skills/aios-worker/scripts/aios_worker.py FIX TASK-N FINDING-ID --executor codex
```

### STATUS TASK-N

Delegates to AIOS-renew task description semantics. STATUS is read-only for the
product worktree, branch, TASK/RUN state, publication, and executor authority.

```powershell
<resolved bootstrap-host argv> .agents/skills/aios-worker/scripts/aios_worker.py STATUS TASK-N --executor codex
```

STATUS may initialize the dedicated untracked worker runtime but must not invoke
an executor or become a second status/review authority.

## Immutable Kernel Pin

The only authoritative AIOS-renew kernel is commit
`b5ce283232587c66144a68f842e3b196d7cf2601`. The launcher validates both the
checked-in dependency pin and installed PEP 610 source+commit provenance and
atomically replaces stale or unverifiable worker runtimes.
