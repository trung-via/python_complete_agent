# TASK-002 — AIOS Bridge v0.3.2 Stabilization

## Objective
Eliminate branch-coupled AIOS runtime state so task/review approvals can switch Git branches without stash/copy/setup workarounds.

## Scope
- Update AIOS Bridge runtime storage so transient runtime files do not live inside the Git worktree.
- Keep durable control-plane artifacts in Git as appropriate (TASK, REVIEW, ADR, context/history).
- Preserve human approval gates for RUN/FIX and preserve no-auto-merge behavior.
- Keep existing ai-control and ai/task-XXX branch workflow compatible.

## Required Behavior
- `bridge.py setup` stores runtime/config/checkpoint/inbox state outside the repository worktree, preferably in a deterministic per-repository user-local directory.
- `bridge.py watch` can run while the repository switches between `main`, `ai-control`, and `ai/task-XXX` branches without creating Git conflicts or dirtying the worktree.
- `bridge.py approve <ID>` and `bridge.py approve <ID> --kind review` must not require stash/copy/manual runtime-file movement solely because of Bridge state.
- Watcher remains notification/sync only; it must never auto-execute code.
- Bridge must never auto-merge.
- Existing UTF-8, checkpoint-before-notification, best-effort popup, and watcher retry fixes from v0.3.1 must remain intact.

## Constraints
- Keep this stabilization narrowly scoped to AIOS tooling.
- Do not modify Python Agent application behavior.
- Do not introduce cloud services or databases.
- Prefer standard-library Python and simple local filesystem state.
- Do not weaken safety checks for unrelated dirty worktree changes.

## Acceptance Criteria
- [ ] Bridge runtime files are outside the Git worktree.
- [ ] Fresh setup works from the repository root.
- [ ] Watcher receives TASK/REVIEW events without dirtying Git status.
- [ ] Approving a TASK can switch/create `ai/task-XXX` without runtime-file checkout conflicts.
- [ ] Approving a REVIEW on an existing task branch works without stash/manual file movement.
- [ ] Non-AIOS dirty files still block unsafe branch switching.
- [ ] UTF-8 console/Git behavior remains correct.
- [ ] Notification failure cannot prevent checkpoint/sync.
- [ ] Fetch/auth/network failure is retried by watcher rather than terminating permanently.
- [ ] No auto-execution and no auto-merge.

## Test Requirements
Add or update automated tests covering at minimum:
1. runtime state path is outside repository worktree;
2. task approval branch switch succeeds with Bridge runtime present;
3. review approval succeeds without stash/manual runtime movement;
4. unrelated dirty file still blocks switch;
5. popup/notification failure does not break sync/checkpoint;
6. watcher retries after fetch/auth/network error;
7. UTF-8 output/path handling remains functional.

Run the relevant AIOS test suite and report exact pass/fail totals.

## Delivery
- Publish implementation on branch `ai/task-002`.
- Provide RESULT with summary, tests, and commit SHA.
- Do not merge automatically.
