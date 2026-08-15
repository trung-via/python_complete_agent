# REVIEW-002 — TASK-002

STATUS: CHANGES_REQUIRED

## Summary
The external runtime directory implementation is directionally correct and covers the original branch-coupled runtime files, but one acceptance criterion is still not met: watcher sync still writes inbound TASK/REVIEW/control artifacts into the active Git worktree, so receiving an event can dirty `git status` and can still couple watcher activity to branch switching.

## Finding 1 — Watcher still dirties the Git worktree (blocking)

`sync_once()` reads inbound files from `ai-control` and writes them directly to `PROJECT / path`, e.g. `.ai/tasks/TASK-XXX.md` and `.ai/reviews/REVIEW-XXX.md`.

This violates TASK-002 acceptance criterion:
- "Watcher receives TASK/REVIEW events without dirtying Git status."

It also leaves a residual branch-coupling risk because `.ai/tasks/*` / `.ai/reviews/*` can be untracked or modified on whichever branch is currently checked out.

### Required fix
Change watcher/control-artifact synchronization so polling TASK/REVIEW events does not modify the active Git worktree solely to deliver the event. Keep the implementation narrow and preserve the existing control-plane model. The implementation may mirror/read inbound control artifacts from external runtime storage or another branch-independent location, as long as Antigravity/Bridge can still access the approved task/review context.

Do not weaken the human approval gate, dirty-file safety checks, watcher retry behavior, UTF-8 handling, or no-auto-merge guarantee.

## Finding 2 — Missing acceptance test (blocking)

The new tests validate that runtime state paths are external, but the notification/sync test currently asserts that `.ai/tasks/TASK-001.md` is written inside the repository. It does not assert that `git status` remains clean after receiving a TASK/REVIEW event.

### Required test
Add an automated test using a real temporary Git repo that:
1. starts from a clean worktree;
2. simulates receiving a new TASK (and preferably REVIEW) from the control branch;
3. runs the sync path used by watcher;
4. asserts `git status --porcelain` remains clean;
5. confirms the pending event/context remains available for `approve` / worker execution.

## Re-review criteria
- Watcher TASK/REVIEW receipt does not dirty the active worktree.
- TASK approval can switch/create the task branch without stash/manual movement.
- REVIEW approval works on the existing task branch without stash/manual movement.
- All existing 7 behavioral guarantees remain intact.
- New clean-worktree sync test passes.
- Full repository test suite remains green.
- Publish a new SHA on `ai/task-002`; do not merge automatically.
