# REVIEW-001 — TASK-001

STATUS: CHANGES_REQUIRED

## Summary
The requested smoke-test documentation file is correct, but the task branch contains extra AIOS runtime/control artifacts outside the allowed scope.

## Findings
1. `docs/AIOS_BRIDGE_SMOKE.md` exists and contains the required text `AIOS Bridge smoke test passed.`.
2. No Python application source files were changed.
3. Scope violation: TASK-001 requires exactly one new documentation file and no unrelated changes, but `ai/task-001` also adds:
   - `.ai/bridge/config.json`
   - `.ai/bridge/seen.json`
   - `.ai/inbox/.gitkeep`
   - `.ai/inbox/TASK-001.4cbd20b9ba.json`
   - `.ai/results/TASK-001.json`
   - `.ai/state/CURRENT_STATE.json`
4. Before re-review, remove the runtime/control artifacts from the task branch so the branch diff contains only the intended documentation artifact, plus only any result artifact explicitly required by the AIOS protocol if the bridge needs one for review transport.

## Required Fix
Clean the branch so AIOS local runtime files are not committed. Preserve `docs/AIOS_BRIDGE_SMOKE.md`, rerun the verification, publish a new result/SHA, and do not merge.
