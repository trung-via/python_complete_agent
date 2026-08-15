# REVIEW-006 — TASK-006

## Status
CHANGES_REQUIRED

## Re-review Summary
The two previous blockers are fixed correctly in commit `7dedfe5a585877e070314fa3ba0abf742fa88229`:

- normal `cmd_publish()` now requires an ACTIVE v0.4.0 authorization and no longer falls back to a historical legacy approval;
- existing task-branch resume now explicitly classifies identical / behind / ahead / diverged states, fast-forwards only when behind, and fails closed on ahead/diverged ambiguity;
- `RESULT-006.md` was republished through an exact FIX authorization bound to the current REVIEW-006 blob;
- the reported full suite is 279/279 passing.

One remaining authorization gap still violates TASK-006's explicit acceptance criteria, plus one smaller malformed-task validation gap should be closed in the same pass.

## Blocking Finding 1 — ACTIVE RUN authorization is not invalidated when a CHANGES_REQUIRED review appears

### Location
`bridge.py` — `cmd_publish()` authorization revalidation.

The current publish path correctly revalidates the authorized artifact itself. For a FIX authorization it also re-reads the review and requires `CHANGES_REQUIRED`.

However, for an ACTIVE RUN authorization, publish only verifies that the authorized TASK blob is still unchanged. It does **not** check whether a current `.ai/reviews/REVIEW-N.md` has appeared with status `CHANGES_REQUIRED` after that RUN authorization was created.

That means this sequence is still technically possible:

1. RUN handoff creates ACTIVE RUN authorization bound to TASK-N blob A;
2. a CHANGES_REQUIRED REVIEW-N appears on `ai-control`;
3. TASK-N blob A itself remains unchanged;
4. `cmd_publish()` still accepts the ACTIVE RUN authorization because only the TASK blob is revalidated.

This violates TASK-006's explicit rules:

- `a RUN authorization must never authorize a later FIX`;
- `do not accept an old RUN approval as authorization after a CHANGES_REQUIRED review`;
- required test #15: `Old RUN authorization cannot authorize a FIX publish.`

### Required Fix
When publishing under action `RUN`, after fetching `ai-control`:

- inspect the current `.ai/reviews/REVIEW-N.md` if it exists;
- if its current parsed status is `CHANGES_REQUIRED`, fail closed and require a fresh `/aios-worker FIX TASK-N` handoff;
- an APPROVED or absent review does not need to convert RUN into FIX; preserve normal RUN behavior;
- do not silently mutate the authorization action.

Preferably also make the worker session action explicit to publish (for example `publish ... --action run|fix`) and require it to match the ACTIVE authorization action. If the existing integration already guarantees that deterministically, the review-presence guard above is the minimum blocker fix.

Add regression coverage:

- ACTIVE RUN auth + unchanged TASK blob + current CHANGES_REQUIRED REVIEW -> publish fails;
- ACTIVE RUN auth + no review -> normal publish allowed;
- ACTIVE FIX auth + exact CHANGES_REQUIRED review -> normal publish allowed.

## Finding 2 — RUN handoff does not meaningfully reject malformed TASK artifacts

### Location
`bridge.py` — `cmd_handoff()` RUN artifact validation.

Current validation is effectively only:

```python
content = read_remote_file(...)
if not content.strip():
    fail(...)
```

TASK-006 requires RUN to fail if TASK-N is `missing or malformed`. A non-empty unrelated Markdown file at `.ai/tasks/TASK-N.md` therefore currently passes.

### Required Fix
Add a lightweight deterministic validation appropriate to this bridge layer, for example requiring the requested canonical task identity to be present in the task heading / metadata (`TASK-N`) and rejecting obviously mismatched artifacts. Do not build a large schema parser.

Add focused coverage for a non-empty artifact whose task identity does not match the requested TASK id.

## What Is Now Correct

- Previous Finding 1 is fixed: no generic legacy approval fallback remains in normal publish.
- Previous Finding 2 is fixed: local-ahead/diverged task branches fail closed and ff-only failure is no longer silently ignored.
- FIX RESULT metadata is now exact-artifact based rather than `(legacy approval)`.
- Branch is still based on current `main` history with no unrelated app changes.
- No auto-merge / force update behavior was introduced.

## Re-review Requirements

After fixing, publish a new commit on `ai/task-006`, update `RESULT-006.md` through the exact current FIX authorization, and run the full repository suite again.

The user should only need to say `Review TASK-006` again. Do not merge automatically.
