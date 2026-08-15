# TASK-004 — AIOS Bridge v0.3.3 Terminal Review Handling

## Objective
Fix the AIOS Bridge so edits to an existing REVIEW artifact do not create a new approval event when that review has already reached a terminal/non-actionable status such as `APPROVED`.

## Problem Reproduced
After TASK-003 was reviewed, `.ai/reviews/REVIEW-003.md` was updated from `CHANGES_REQUIRED` to `APPROVED`. Because the blob SHA changed, `sync_once()` treated it as a new review event and:
- created a new pending REVIEW-003 JSON;
- set runtime state back to `CHANGES_REQUIRED`;
- showed a popup instructing the user to approve a fix that was no longer required.

This is incorrect. A changed review artifact is not always an actionable review event.

## Scope
Update `bridge.py` and tests only as needed.

Required behavior:
1. Continue caching every changed inbound review artifact externally, even if status becomes terminal/non-actionable.
2. Parse review status from review markdown content before creating pending approval work.
3. Create a pending REVIEW event and `CHANGES_REQUIRED` state only when the review status actually requires a fix.
4. For `APPROVED`, do NOT create pending approval work, do NOT instruct `/aios-worker` FIX, and do NOT regress state to `CHANGES_REQUIRED`.
5. Existing pending JSON for the same REVIEW/task must be removed or otherwise rendered non-pending when the review becomes `APPROVED`.
6. Notification for terminal/non-actionable review updates should be informational at most; no approval command should be shown.
7. Preserve current external-runtime design, human gate, retry behavior, UTF-8 handling, and no-auto-merge guarantees.

## Status Parsing Contract
At minimum support review markdown with a section such as:

```md
## Status
CHANGES_REQUIRED
```

and

```md
## Status
APPROVED
```

Parsing should be case-insensitive and tolerant of surrounding whitespace.

If status is missing or unrecognized, fail safe: cache the artifact but do not silently execute anything. Prefer no actionable pending event unless the content explicitly indicates a fix is required.

## Acceptance Criteria
- [ ] Updating `REVIEW-XXX.md` from `CHANGES_REQUIRED` to `APPROVED` does not create a new actionable pending review.
- [ ] Any stale pending JSON for that same review/task is cleared when status becomes `APPROVED`.
- [ ] Runtime state does not regress to `CHANGES_REQUIRED` after an approved review arrives.
- [ ] `python bridge.py pending` is empty after syncing an approved review when no other work is pending.
- [ ] Updating a review to `CHANGES_REQUIRED` still creates exactly one actionable pending review with the current human-approval gate.
- [ ] Re-syncing an unchanged review remains idempotent.
- [ ] Watcher sync still does not dirty the Git worktree.
- [ ] Notification failure still does not break checkpoint/seen-state persistence.
- [ ] Full repository test suite passes.

## Required Tests
Add focused tests covering at least:
1. `CHANGES_REQUIRED` review creates pending REVIEW event.
2. Same review updated to `APPROVED` clears/removes actionable pending state.
3. Approved review does not emit an approval/FIX instruction.
4. Missing/unknown review status is non-actionable and does not auto-create fix work.
5. Worktree remains clean throughout sync.

## Delivery
- Work on `ai/task-004`.
- Report focused AIOS test total and full repository test total.
- Report final commit SHA.
- Push branch for ChatGPT review.
- Do not merge automatically.
