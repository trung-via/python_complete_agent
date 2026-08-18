# Using Codex as an AIOS Bridge Executor on Windows

This runbook covers the normal Windows workflow in which a human explicitly selects Codex to execute a bounded AIOS task. AIOS Bridge remains the control and publication authority; Codex only inspects the authorized context, edits the allowed files, and runs local checks.

## Prerequisites

- The repository is cloned and its Git remote and AIOS Bridge setup are already configured.
- Codex CLI is installed, authenticated, and available as `codex` in PowerShell.
- The repository virtual environment exists at `venv` and contains the project and test dependencies.
- The worktree is clean before approval, and the operator is at the repository root.

On Windows, invoke repository Python commands with the virtual-environment interpreter:

```powershell
.\venv\Scripts\python.exe
```

Do not assume that a global `python` command is installed or visible in the Codex shell. If the command above fails, repair or recreate the repository virtual environment before approving or publishing work; do not substitute an unverified interpreter.

## Authority boundary

The roles remain separate throughout the workflow:

- The human chooses the action and Executor and authorizes `RUN`, `FIX`, and `MERGE` boundaries.
- AIOS Bridge syncs authoritative artifacts, records authorization, binds the executor lease, validates publication, runs the publication test gate, generates the RESULT, commits, and pushes.
- Codex is the selected Executor. It reads Bridge context, makes only the authorized repository edits, runs bounded local checks, and reports back to the operator.
- The Primary Brain independently reviews the Bridge-published result and issues `PASS` or `CHANGES_REQUIRED`.

Selecting `codex` does not transfer Bridge authority to Codex. When Bridge owns publication, Codex must not run `git commit` or `git push`, manually create a RESULT, alter authorization or lease state, self-select an Executor, or publish the task.

## Fresh task workflow (`RUN`)

Replace `<id>` with the numeric task ID. Start from the repository root in PowerShell.

1. Confirm that unrelated work is not present:

   ```powershell
   git status --short
   ```

2. Fetch control artifacts and inspect pending human decisions:

   ```powershell
   .\venv\Scripts\python.exe .\bridge.py sync
   .\venv\Scripts\python.exe .\bridge.py pending
   ```

3. After reading the pending TASK, the human explicitly authorizes a fresh task with Codex:

   ```powershell
   .\venv\Scripts\python.exe .\bridge.py approve <id> --kind task --executor codex
   ```

   This is an ordinary `RUN` authorization. It is not failover and must not be represented as failover evidence.

4. Inspect the authoritative task, branch, authorization, and lease binding:

   ```powershell
   .\venv\Scripts\python.exe .\bridge.py context <id>
   ```

   Verify that the current and expected task branches match, authorization status is `ACTIVE`, action is `RUN`, and `executor_id` is `codex`.

5. Launch Codex from the same repository:

   ```powershell
   codex
   ```

   Tell Codex to run the context command itself before editing, read the authoritative TASK and authorization, obey the allowed-file boundary, run the requested local checks, and stop without committing, pushing, publishing, or creating a RESULT.

6. Review Codex's changes and evidence. Confirm that `git status --short` and `git diff` contain only the authorized implementation files. Run any task-specific local checks that were not already run.

7. The human invokes Bridge publication with the task's required full test gate. For the usual full repository suite:

   ```powershell
   .\venv\Scripts\python.exe .\bridge.py publish <id> --action RUN --test ".\venv\Scripts\python.exe -m pytest tests/ -q"
   ```

   Bridge validates the active authorization and lease, runs the supplied test command, generates the RESULT from execution evidence, commits, pushes the task branch, releases the lease, and consumes the authorization. If tests fail, Bridge does not commit or push.

8. Ask the Primary Brain to review `TASK-<id>` independently. A successful publish means the task is ready for review; it is not a self-declared `PASS`, merge approval, or merge.

## Review-fix workflow (`FIX`)

Use this only after the Primary Brain has published a `CHANGES_REQUIRED` review on the control branch.

1. Sync and confirm that the REVIEW is pending:

   ```powershell
   .\venv\Scripts\python.exe .\bridge.py sync
   .\venv\Scripts\python.exe .\bridge.py pending
   ```

2. After reading the review, the human explicitly authorizes Codex for the fix boundary:

   ```powershell
   .\venv\Scripts\python.exe .\bridge.py approve <id> --kind review --executor codex
   .\venv\Scripts\python.exe .\bridge.py context <id>
   ```

   Verify that authorization is `ACTIVE`, action is `FIX`, `executor_id` is `codex`, and the authoritative review status is `CHANGES_REQUIRED`.

3. Launch `codex`. Require it to repeat `context <id>`, implement only the review-requested changes within the authorized scope, run the requested checks, and stop without committing, pushing, publishing, or editing RESULT/runtime state.

4. Review the diff, then have the human publish through Bridge with the fix action and required full test gate:

   ```powershell
   .\venv\Scripts\python.exe .\bridge.py publish <id> --action FIX --test ".\venv\Scripts\python.exe -m pytest tests/ -q"
   ```

5. Ask the Primary Brain for another independent review. Repeat only from a newly synchronized and explicitly approved `CHANGES_REQUIRED` review boundary.

## Recovery guide

### No pending TASK or REVIEW

Run `sync` again, followed by `pending`. If nothing appears, stop: there is no Bridge event for the human to approve. Confirm outside the Executor session that the expected TASK or `CHANGES_REQUIRED` REVIEW exists on the configured control branch. Do not invent an approval, edit runtime files, or use a different task's authorization.

### Authorization is consumed or not active

A successful publish consumes its authorization, so it cannot be reused. Run `sync` and `pending`. For a subsequent fix, wait for a pending `CHANGES_REQUIRED` REVIEW and have the human run `approve <id> --kind review --executor codex`. If there is no new authorized boundary, stop and escalate to the human; do not modify authorization or lease records manually.

### Dirty worktree

Bridge approval/handoff preparation fails closed when the worktree is dirty, and publication stages repository changes. Use `git status --short` and `git diff` to identify every path. Preserve unrelated user work and have its owner commit, move, or stash it deliberately before activation; never discard it merely to make Bridge proceed. Before publication, verify that all remaining changes are exactly the task-authorized files. Stop if the scope cannot be isolated safely.

### Missing interpreter or PATH mismatch

If global `python` is unavailable, use `.\venv\Scripts\python.exe`. If that path is missing, create or restore the repository virtual environment and install its declared dependencies before continuing. If `codex` is not found, install it or correct the Codex CLI PATH and authenticate. Do not approve or publish using an unknown Python installation simply to bypass the mismatch.

## Executor-provider independence

Quota exhaustion or an outage at one Executor provider does not change AIOS Bridge authority, authorization, leases, or publication rules. Codex must stop at the current authorized boundary rather than reroute itself. At a future supported and stable authorization boundary, the human may explicitly select another already-supported Executor. Provider availability never authorizes automatic routing, a new failover path, or a change to the repository default Executor.

## Copy/paste operator checklist

Set the task number, then run each block only after its preceding human decision is complete.

```powershell
$TaskId = 33
git status --short
.\venv\Scripts\python.exe .\bridge.py sync
.\venv\Scripts\python.exe .\bridge.py pending
.\venv\Scripts\python.exe .\bridge.py approve $TaskId --kind task --executor codex
.\venv\Scripts\python.exe .\bridge.py context $TaskId
codex
```

After Codex stops and the operator verifies the bounded diff:

```powershell
git status --short
git diff --check
.\venv\Scripts\python.exe .\bridge.py publish $TaskId --action RUN --test ".\venv\Scripts\python.exe -m pytest tests/ -q"
```

For a later `CHANGES_REQUIRED` review, use a new human-approved fix boundary:

```powershell
.\venv\Scripts\python.exe .\bridge.py sync
.\venv\Scripts\python.exe .\bridge.py pending
.\venv\Scripts\python.exe .\bridge.py approve $TaskId --kind review --executor codex
.\venv\Scripts\python.exe .\bridge.py context $TaskId
codex
git status --short
git diff --check
.\venv\Scripts\python.exe .\bridge.py publish $TaskId --action FIX --test ".\venv\Scripts\python.exe -m pytest tests/ -q"
```

After either publish, request Primary Brain review. Do not merge without explicit human authority.
