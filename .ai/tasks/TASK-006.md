# TASK-006 — AIOS Bridge v0.4.0 Zero-Touch Handoff Workflow

## Objective
Upgrade AI Engineering OS Lite from the current manual bridge workflow to a command-driven human-gate workflow where the user only needs to explicitly issue `RUN`, `FIX`, and `Merge` decisions.

Canonical baseline when this task is authored:
- `main`: `888bb9d7594613e54d354beaa06edbaead0d3269`
- current bridge: v0.3.3
- current daily workflow still requires manual `sync` / `approve` / local Git reconciliation

The target user experience is:

```text
ChatGPT: create TASK-N on ai-control
User in Antigravity: /aios-worker RUN TASK-N
Antigravity: fetch/sync/authorize/prepare/code/test/publish automatically
User in ChatGPT: Review TASK-N
ChatGPT: APPROVED or CHANGES_REQUIRED
If CHANGES_REQUIRED:
User in Antigravity: /aios-worker FIX TASK-N
Antigravity: fetch review/authorize/fix/test/publish automatically
If APPROVED:
User in ChatGPT: Merge TASK-N
ChatGPT: fast-forward remote main
```

After merge, the user must NOT need to manually run:
- `python bridge.py sync`
- `python bridge.py approve ...`
- `git fetch origin --prune`
- `git switch main`
- `git pull --ff-only origin main`
- `git status --short`
- `python bridge.py pending`

The next `RUN TASK-N` invocation must safely reconcile the local repository with remote `main` as part of worker preparation.

---

## Core Safety Principle

This task removes **manual transport ceremony**, not human approval.

The explicit commands themselves are the human gates:

- `/aios-worker RUN TASK-N` = explicit approval to execute the current exact TASK-N artifact.
- `/aios-worker FIX TASK-N` = explicit approval to apply the current exact CHANGES_REQUIRED REVIEW-N artifact.
- `Merge TASK-N` in ChatGPT = explicit approval to fast-forward remote `main`.

Preserve these invariants:
- no automatic task execution merely because a task appears on `ai-control`;
- no automatic fix merely because a review becomes CHANGES_REQUIRED;
- no automatic merge;
- no force-push / reset-hard / destructive branch recovery;
- fail closed on dirty/diverged/ambiguous repository state.

---

## v0.4.0 Architecture

### 1. Add a single worker handoff/preparation command

Add a bridge command suitable for Antigravity to invoke internally, for example:

```text
python bridge.py handoff 6 --action run
python bridge.py handoff 6 --action fix
```

Exact CLI spelling may vary if there is a better fit, but it must provide the semantics below.

The user should never need to invoke this command manually; `/aios-worker RUN/FIX TASK-N` invokes it internally.

The handoff command must NOT depend on a watcher having already run and must NOT require an existing PENDING inbox event.

It must directly fetch `ai-control`, locate the requested artifact, cache it to external runtime storage, validate it, create an exact authorization record, and prepare the correct branch.

### 2. Exact-artifact authorization

Do not treat a generic historical `APPROVED` event for TASK-N as permanent authorization.

Introduce or adapt an external-runtime authorization record containing at least:

```json
{
  "task_id": "TASK-006",
  "action": "RUN",
  "kind": "TASK",
  "artifact_path": ".ai/tasks/TASK-006.md",
  "artifact_blob_sha": "...",
  "approved_at": "...",
  "branch": "ai/task-006",
  "status": "ACTIVE"
}
```

For FIX, the record must point to the exact `REVIEW-N.md` blob SHA and use action `FIX`, kind `REVIEW`.

Requirements:
- authorization is bound to the exact current control artifact blob SHA;
- a changed TASK/REVIEW blob invalidates stale authorization for that action;
- repeated handoff for the same action + same blob may be idempotent;
- a RUN authorization must never authorize a later FIX;
- an old REVIEW authorization must never authorize a newer review revision;
- authorization remains external to the Git worktree;
- successful publish consumes/closes the active authorization so a new publish requires a new explicit RUN/FIX handoff;
- failed tests must not silently consume authorization if the worker needs to correct code in the same explicitly authorized session.

### 3. RUN handoff behavior

When invoked as RUN for TASK-N:

1. Ensure Git repo/config/runtime directories are valid.
2. Fetch `origin` and `ai-control` itself; watcher state is irrelevant.
3. Read the current exact `.ai/tasks/TASK-N.md` from `origin/ai-control`.
4. Fail if TASK-N is missing or malformed.
5. Cache the artifact externally and record its blob SHA.
6. Safely reconcile local `main` with `origin/main` as described below.
7. Create/switch to `ai/task-N` from the synchronized canonical main, or safely resume an already matching task branch.
8. Record exact RUN authorization.
9. Clear/supersede stale pending events for the same TASK where appropriate.
10. Return machine-readable context to `/aios-worker` so it can immediately implement the task.

No separate manual `sync` or `approve` is allowed in the normal path.

### 4. FIX handoff behavior

When invoked as FIX for TASK-N:

1. Fetch `origin` and `ai-control` itself.
2. Read current exact `.ai/reviews/REVIEW-N.md` from `origin/ai-control`.
3. Parse review status using the v0.3.3 status parser semantics.
4. Continue **only** when current status is exactly `CHANGES_REQUIRED`.
5. `APPROVED`, missing status, unknown status, missing review, or malformed review must fail closed and must not authorize code changes.
6. Cache the review externally and bind authorization to its exact blob SHA.
7. Fetch and safely switch to the existing `ai/task-N` branch. FIX must not silently start from a new branch and must not rebase/reset the branch onto a newer main.
8. Record exact FIX authorization and supersede stale REVIEW authorization/pending events.
9. Return worker context for immediate fixing.

No separate manual `sync` or `approve --kind review` is allowed in the normal path.

### 5. Safe automatic local-main reconciliation

This replaces the post-merge PowerShell sequence the user currently performs.

RUN preparation must safely make local `main` match canonical `origin/main` before creating a new task branch.

Requirements:
- fetch remote refs first;
- require a clean worktree before automatic branch switching; because runtime data is now external, treat unexpected tracked/untracked worktree changes conservatively;
- if local `main == origin/main`: continue;
- if local `main` is strictly behind `origin/main`: fast-forward only;
- if local `main` is ahead or diverged: fail closed with a clear diagnostic;
- never `reset --hard`;
- never force checkout over local changes;
- never silently delete local commits/files;
- verify the task branch base is the synchronized canonical main for a new RUN.

This reconciliation occurs when the next RUN begins. ChatGPT does not need local-machine access immediately after a merge.

### 6. Safe task-branch preparation

For a new RUN:
- expected branch is `ai/task-N`;
- create it from synchronized `origin/main` when absent;
- if it already exists locally/remotely, only resume it when state is unambiguous and safe;
- fast-forward local task branch from remote when local is strictly behind and worktree is clean;
- fail on local-ahead/diverged ambiguity rather than rewriting history.

For FIX:
- require the task branch to already exist (normally remote branch exists because it was previously published for review);
- fetch it and safely synchronize local task branch with remote if possible;
- do not rebase onto current main automatically.

### 7. Publish must enforce current authorization

Strengthen `cmd_publish` so a stale historical approval cannot authorize unrelated later work.

Before testing/commit/push:
- require an ACTIVE authorization for this task;
- authorization action must be RUN or FIX and match the current worker session;
- fetch `ai-control` and verify the authorized artifact path still has the same blob SHA;
- if the TASK/REVIEW artifact changed since explicit handoff, abort publish and require a fresh RUN/FIX command;
- for FIX, verify the current authorized review still parses as CHANGES_REQUIRED;
- do not accept an old RUN approval as authorization after a CHANGES_REQUIRED review.

After successful commit + push:
- mark the authorization CONSUMED/PUBLISHED with published SHA and timestamp in external runtime state;
- do not merge.

### 8. Durable result evidence so the user does not paste test output/SHA

The worker must continue to publish a durable tracked result artifact:

```text
.ai/results/RESULT-N.md
```

ChatGPT will use GitHub branch state + this file for review, so the user should only need to say:

```text
Review TASK-N
```

Minimum RESULT content:
- `STATUS: READY_FOR_REVIEW`
- task id
- branch
- authorization action (`RUN` or `FIX`)
- authorized artifact path + blob SHA
- base/main SHA used for RUN, when applicable
- summary
- changed files / diff stat
- exact test command(s)
- test exit code(s)
- useful test totals/output
- risks/notes
- generation timestamp

Do not require RESULT to contain its own final commit SHA if that would create a self-reference problem; ChatGPT can read branch HEAD directly from GitHub.

`/aios-worker` must call publish with real test evidence. A normal successful worker run must not leave `Command: (not supplied)` unless the task explicitly requires no tests.

### 9. Watcher and legacy CLI become optional/debug paths

Keep `sync`, `watch`, `pending`, and `approve` for backward compatibility/debugging unless removal is clearly safer, but they must no longer be required for normal work.

Update watcher notifications to reflect the new UX:

For TASK:
```text
TASK-N ready. Run /aios-worker RUN TASK-N when you approve execution.
```

For CHANGES_REQUIRED review:
```text
REVIEW-N requires changes. Run /aios-worker FIX TASK-N when you approve the fix.
```

Do not instruct the user to run manual PowerShell `sync`/`approve` in normal notifications.

Watcher remains transport/notification only and must never auto-run RUN/FIX.

### 10. Worker integration contract

Update the repository-owned AIOS worker instructions/configuration if such a tracked source exists.

If `/aios-worker` itself is provided externally by Antigravity and is not repository-tracked, implement the bridge-side command contract completely and document the exact first-step behavior that the worker must follow:

```text
RUN TASK-N -> bridge handoff(action=RUN, N) -> read returned context -> implement -> test -> bridge publish
FIX TASK-N -> bridge handoff(action=FIX, N) -> read returned context -> fix -> test -> bridge publish
```

Do not fake a tracked worker file if none exists.

---

## TASK-006 Bootstrap Requirement

TASK-006 is the migration task from v0.3.3 to v0.4.0.

Because the old bridge is still active before this task is implemented, `/aios-worker RUN TASK-006` may perform the old `sync` + `approve 6` operations **internally as a one-time bootstrap** if required by the current worker implementation.

The user should not have to type those PowerShell commands manually.

After TASK-006 is merged, all later tasks must use the new zero-touch handoff flow.

---

## Required Tests

Add focused tests covering at least:

1. RUN handoff succeeds without a pre-existing pending event.
2. RUN fetches/caches exact TASK blob and records exact RUN authorization.
3. Missing TASK fails closed.
4. RUN safely fast-forwards local main when it is behind origin/main.
5. RUN does nothing destructive when main is already current.
6. Dirty worktree blocks automatic switch/reconciliation.
7. Local-main ahead/diverged state blocks automatic reconciliation.
8. New task branch is based on synchronized canonical main.
9. Existing task branch resume is only allowed in a safe unambiguous state.
10. FIX succeeds only for current `CHANGES_REQUIRED` review.
11. FIX rejects APPROVED, unknown/missing status, or missing review.
12. FIX authorization is bound to exact review blob SHA.
13. Repeated same-blob handoff is idempotent and does not create duplicate active authorizations.
14. New task/review blob invalidates/supersedes stale authorization.
15. Old RUN authorization cannot authorize a FIX publish.
16. Publish verifies authorized control blob is still current before commit/push.
17. Publish aborts when the authorized TASK/REVIEW changed after handoff.
18. Successful publish consumes the active authorization.
19. Failed tests do not commit/push and preserve a safe retryable authorized session.
20. RESULT-N contains durable test evidence and authorization metadata.
21. Watcher notifications no longer tell the user to run manual approve commands.
22. Legacy `sync`/`approve` still work as debug/backward-compat paths unless intentionally deprecated with equivalent coverage.
23. Full bridge test suite passes and normal project tests remain green.
24. No code path merges or force-updates `main`.

Include regression coverage for v0.3.3 terminal review behavior: APPROVED review must not create actionable pending work.

---

## Acceptance Criteria

- [ ] Normal user flow requires no manual PowerShell bridge commands.
- [ ] `/aios-worker RUN TASK-N` is the explicit human execution gate.
- [ ] `/aios-worker FIX TASK-N` is the explicit human fix gate.
- [ ] Handoff works even when watcher is stopped and pending inbox is empty.
- [ ] Exact control artifact blob is authorized, not merely task number.
- [ ] Stale RUN approval cannot authorize later FIX work.
- [ ] Stale review revision cannot authorize a later review revision.
- [ ] Publish revalidates authorization against current `ai-control` before pushing.
- [ ] Local main is safely reconciled at the beginning of the next RUN.
- [ ] User does not need post-merge fetch/switch/pull/status/pending steps.
- [ ] ChatGPT can review from GitHub by task number alone; user does not need to paste SHA or test output.
- [ ] RESULT artifact carries sufficient durable test evidence.
- [ ] Dirty/diverged local states fail closed with clear recovery guidance.
- [ ] No `reset --hard`, force push, automatic merge, automatic execution, or automatic fix.
- [ ] Existing external runtime isolation and UTF-8 behavior remain intact.
- [ ] Full repository test suite passes.

---

## Delivery

- Work on branch `ai/task-006`.
- Start from current canonical `origin/main`.
- Primary expected changes: `bridge.py`, `tests/test_bridge.py`, and any real repository-owned AIOS worker documentation/configuration that actually exists.
- Avoid unrelated application/Phase 5.6 refactors.
- Bump bridge version/documentation to v0.4.0.
- Run focused bridge tests and full repository tests.
- Publish `.ai/results/RESULT-006.md` with durable evidence.
- Push `ai/task-006` for ChatGPT review.
- Do not auto-merge.
