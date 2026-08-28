---
# Format: UTF-8 without BOM, LF line endings
name: aios-renew-worker
description: >
  Antigravity-only /aios-renew-worker workflow. Operates the AIOS worker
  protocol (RUN TASK-N, FIX TASK-N, STATUS TASK-N) through the exact pinned
  AIOS-renew kernel with executor identity antigravity.
---

# AIOS-renew Worker — Antigravity Workflow

**Surface:** Antigravity `/aios-renew-worker` slash command only.
**Executor identity:** `antigravity` — passed as `--executor antigravity` to the shared launcher.

This is the only active Antigravity execution surface. It must never serve the
Codex worker surface or infer, reroute, or substitute another executor.

## Explicit Invocation

```text
/aios-renew-worker RUN TASK-N
/aios-renew-worker FIX TASK-N
/aios-renew-worker STATUS TASK-N
```

`TASK-N` is the exact user-supplied task identifier.

## Operator Boundary

The visible Antigravity session is operator UI only. After dispatch it must not
inspect TASK implementation context, edit product files, execute verification,
synthesize evidence, review semantics, retry, reroute, or continue coding.

## Strict Execution Contract

1. Parse the exact Human command (`RUN TASK-N`, `FIX TASK-N`, or `STATUS TASK-N`).
2. Echo the requested task ID, action, and selected executor (`antigravity`).
3. Resolve the deterministic Python 3.11+ bootstrap host described below.
4. Invoke the checked-in shared launcher
   `.agents/skills/aios-worker/scripts/aios_worker.py` exactly once with the
   requested action, exact task ID, and `--executor antigravity`.
5. Do not invoke an executor directly, retry, reroute, or select another executor.
6. Do not reconstruct TASK, RESULT, EVIDENCE, REVIEW, or REMEDIATION semantics.
7. Do not authorize or perform a branch merge. Guarded post-PASS publication is
   owned by the shared launcher.
8. After dispatch, stop. On successful execution and publication, report:

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
report exactly `BOOTSTRAP_INTERPRETER_UNAVAILABLE`. The bootstrap host never
provides runtime authority; AIOS-renew runs only from the launcher's separate
`.git/aios/worker-runtime`.

## Command Details

### RUN TASK-N

Delegates one primary execution to AIOS-renew and permits guarded publication
only after canonical PASS:

```powershell
<resolved bootstrap-host argv> .agents/skills/aios-worker/scripts/aios_worker.py RUN TASK-N --executor antigravity
```

### FIX TASK-N

Resolves one exact local canonical REVIEW/REMEDIATION lineage and delegates only
AIOS-renew remediation semantics. Missing, ambiguous, or invalid lineage fails closed:

```powershell
<resolved bootstrap-host argv> .agents/skills/aios-worker/scripts/aios_worker.py FIX TASK-N --executor antigravity
```

### STATUS TASK-N

Delegates to AIOS-renew task-description semantics. STATUS is read-only for the
product worktree, branch, TASK/RUN state, publication, and executor authority:

```powershell
<resolved bootstrap-host argv> .agents/skills/aios-worker/scripts/aios_worker.py STATUS TASK-N --executor antigravity
```

STATUS may initialize the dedicated untracked worker runtime but must not invoke
an executor or become a second status or review authority.
