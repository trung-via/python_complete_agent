# REVIEW-004 — TASK-004

## Status
CHANGES_REQUIRED

## Summary
TASK-004 correctly fixes the reproduced terminal-review bug: `APPROVED` reviews are cached externally, stale pending review events are cleared, state becomes `APPROVED`, and no FIX approval instruction is emitted. However, one acceptance-criteria gap remains for repeated `CHANGES_REQUIRED` updates.

## Blocking Finding — Repeated CHANGES_REQUIRED edits can create duplicate pending review events

### Location
`bridge.py` — `sync_once()` CHANGES_REQUIRED branch and `write_pending()`

### Problem
`write_pending()` names review inbox files using the review blob SHA. If the same `REVIEW-XXX.md` is edited while its status remains `CHANGES_REQUIRED`, the blob SHA changes and a second pending JSON is created. The earlier pending JSON is not cleared first.

That means `python bridge.py pending` can show two actionable REVIEW entries for the same task/review. This conflicts with TASK-004 acceptance criterion:

> Updating a review to `CHANGES_REQUIRED` still creates exactly one actionable pending review with the current human-approval gate.

The current focused test only covers a single first-time `CHANGES_REQUIRED` sync, so it does not catch the duplicate-on-edit case.

### Required Fix
Before creating a new actionable pending REVIEW for `CHANGES_REQUIRED`, ensure any prior pending REVIEW event(s) for that same task/review are removed or superseded so there is exactly one actionable pending review after the sync.

A minimal acceptable approach is to clear prior REVIEW pending events for that task immediately before writing the new current-SHA pending event. Preserve approved/non-review events as appropriate.

### Required Test
Add a regression test that:
1. syncs `REVIEW-004.md` with `CHANGES_REQUIRED` at blob SHA A;
2. updates the same review content while keeping `CHANGES_REQUIRED` at blob SHA B;
3. syncs again;
4. asserts `pending_events()` contains exactly one REVIEW event for TASK-004, corresponding to the current update;
5. asserts worktree remains clean/non-mutated by sync.

## What Already Looks Correct
- `APPROVED` review handling is non-actionable and clears stale review pending state.
- Missing/unknown statuses are non-actionable.
- External-runtime design remains intact.
- Scope is limited to `bridge.py` and `tests/test_bridge.py`.

## Re-review Requirements
After fixing, report:
1. new commit SHA on `ai/task-004`;
2. focused duplicate-CHANGES_REQUIRED regression test result;
3. AIOS Bridge test total;
4. full repository test total.

Do not merge automatically.
