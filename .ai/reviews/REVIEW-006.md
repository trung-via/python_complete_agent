# REVIEW-006 — TASK-006

## Status
CHANGES_REQUIRED

## Summary
TASK-006 implements most of the intended v0.4.0 shape correctly: zero-touch `handoff`, exact artifact metadata, safe local-main reconciliation, durable RESULT evidence, updated watcher UX, and a broad bridge regression suite. The task branch is one commit ahead of `main`, based on current canonical `main`, and the published RESULT reports 275/275 tests passing.

However, there are two blocking safety gaps that violate TASK-006's core acceptance criteria.

## Blocking Finding 1 — `cmd_publish` still accepts legacy historical approval when no ACTIVE exact authorization exists

### Location
`bridge.py` — `cmd_publish()` authorization gate.

Current behavior:

```python
auth = get_active_authorization(task_id)
if not auth:
    # Fallback to legacy approval check
    if not latest_approved(task_id):
        fail("Không có ACTIVE authorization cho task này. Không publish.")
```

This fallback defeats the v0.4.0 exact-artifact authorization model. A historical v0.3.3 inbox approval can remain present indefinitely and authorize a later publish even when there is no current ACTIVE RUN/FIX authorization bound to the exact current control artifact.

This directly conflicts with TASK-006 requirements:
- publish must require an ACTIVE authorization;
- stale historical approval must not authorize unrelated later work;
- an old RUN approval must not authorize work after a CHANGES_REQUIRED review;
- publish must verify the current exact TASK/REVIEW blob that the user explicitly authorized.

The current `RESULT-006.md` itself shows `Authorized Artifact: (legacy approval)`, confirming TASK-006 was published through this fallback rather than through the new exact-artifact authorization path.

### Required Fix
Remove the generic legacy-approval fallback from normal `cmd_publish` authorization.

Acceptable options:
1. Require ACTIVE v0.4.0 authorization unconditionally for normal publish; or
2. If a one-time TASK-006 migration bootstrap must remain, scope it narrowly and explicitly to TASK-006 migration only, with deterministic checks that cannot authorize TASK-007+ or later FIX work.

After v0.4.0 behavior is active, `latest_approved()` alone must never authorize publish.

Add regression coverage proving:
- historical APPROVED inbox event + no ACTIVE authorization => publish fails closed;
- historical RUN approval cannot authorize publish after a CHANGES_REQUIRED review appears;
- ACTIVE exact RUN/FIX authorization is still accepted normally.

## Blocking Finding 2 — Existing task-branch resume does not fail closed on local-ahead/diverged ambiguity

### Location
`bridge.py` — `prepare_task_branch()` for both RUN and FIX.

For an existing local branch with a remote counterpart, the code checks only whether local is an ancestor of remote. If yes, it fast-forwards. If that check fails, it simply continues and returns the branch:

```python
if local_branch_exists(branch):
    git("checkout", branch)
    if branch_exists_remote(remote, branch):
        ...
        if p_ancestor.returncode == 0:
            git("merge", "--ff-only", remote_branch_ref, check=False)
    return branch
```

The same pattern exists when the task branch is already current.

Therefore a local task branch that is ahead of remote or diverged from remote is silently resumed instead of failing closed. That violates TASK-006 requirements that existing task branch resume be allowed only when state is safe and unambiguous, with local-ahead/diverged ambiguity rejected rather than rewritten or silently accepted.

This is especially important for FIX: a local-only commit or diverged task branch could cause the worker to modify/publish from code that ChatGPT never reviewed.

### Required Fix
For an existing task branch when remote exists, explicitly classify branch relation:
- local == remote -> continue;
- local strictly behind remote -> fast-forward only and verify success;
- local ahead of remote -> fail closed;
- local/remote diverged -> fail closed.

Do this for both RUN resume and FIX resume, including the case where the task branch is already the current branch.

Do not use `check=False` on the actual fast-forward merge in a way that can silently ignore failure. If fast-forward fails, abort handoff.

Add regression coverage for at least:
- RUN existing task branch local-ahead -> fail;
- RUN existing task branch diverged -> fail;
- FIX existing task branch local-ahead -> fail;
- FIX existing task branch diverged -> fail;
- local-behind -> successful ff-only;
- identical -> continue.

## Additional Review Notes

The safe local-main reconciliation logic is directionally correct: it fetches first, fast-forwards only when local main is strictly behind, and fails on local-main ahead/diverged state.

The exact control-artifact revalidation in the ACTIVE authorization path is also correct in principle: publish refetches `ai-control`, compares current blob SHA with the authorized SHA, and revalidates CHANGES_REQUIRED for FIX.

The durable RESULT artifact is sufficient for the new user experience: ChatGPT can inspect branch HEAD plus `.ai/results/RESULT-N.md` without asking the user to paste the SHA or test output.

## Re-review Requirements
After fixing, publish a new commit on `ai/task-006` and update `RESULT-006.md` through the actual v0.4.0 ACTIVE authorization path. Re-run:
- focused bridge tests covering the two findings above;
- full bridge suite;
- full repository test suite.

The user should then only need to say `Review TASK-006` again. Do not merge automatically.
