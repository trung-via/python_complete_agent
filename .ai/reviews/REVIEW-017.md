# REVIEW-017 — TASK-017 Manual External Brain PLAN Runner

STATUS: CHANGES_REQUIRED

## Review Scope
- Review round: `3`
- Reviewed branch: `ai/task-017`
- Reviewed head: `f0a12df6782b31a2c078e517187c5e296d08c66c`
- Tested implementation SHA: `20816d295caaefd0f6cfae316bc73b0923b3f9f5`
- Base main: `54303dc7d56ddce4ae9b22ef05c7dd310e731737`
- Branch relation: ahead 4 / behind 0; merge-base is exact current main.
- PLAN adoption remains `ACCEPTED_WITH_LOCAL_ADJUSTMENTS`.
- `CHATGPT_REPLAN_REQUIRED: NO`.

## Implementation Review — ACCEPTED
The code/test changes required by prior rounds are now satisfied.

1. Task ID validation is now case-sensitive and matches the canonical `^TASK-\d+$` contract. Lowercase/mixed-case task names are rejected.
2. CLI no longer exposes `--api-key`, `--provider`, or `--model`.
3. Internal runner remains locked to provider=`minimax` and model=`MiniMax-M3` and fails closed on mismatch.
4. Non-SUCCESS provider output no longer emits `ModelResponse.error_message`.
5. Explicit-context-only / no repo crawl behavior remains intact.
6. No retry, fallback, router, provider registry, patch application, shell/browser/Git execution, or provider HTTP duplication was introduced.
7. PLAN artifact identity remains correct: control commit `8b65bca623ccfba95d9ea0956f960a3eb8efd93a`, blob `7cfe32d75a8989a58a45c08aaca4084c6323e78e`.
8. The exact tested implementation revision exists and contains the strict task-ID fix: `20816d295caaefd0f6cfae316bc73b0923b3f9f5`.
9. The branch head after that implementation differs only by the RESULT evidence commit, so code under review is the tested code.

## Test Evidence Accepted
RESULT reports suites executed against implementation `20816d295caaefd0f6cfae316bc73b0923b3f9f5`:
- Focused External Brain: `86 passed`
- AIOS Bridge: `86 passed`
- Full repository: `560 passed`
- Live calls in automated tests: `0`
- Credentials persisted: `NO`
- Separated reasoning persisted: `NO`

## Remaining Required Changes — EVIDENCE ONLY
Do not change production code or tests unless needed to regenerate evidence.

1. Fix the top-level `## Files Changed` section in `RESULT-017.md`. It currently says `(none before result generation)`. Replace it with the complete branch paths relative to canonical main:
   - `.ai/results/RESULT-017.md`
   - `scripts/aios_external_brain_plan.py`
   - `src/aios_bridge/external_brain/runner.py`
   - `tests/aios_bridge/external_brain/test_runner.py`

2. Fill the top-level `## Diff Stat` with the complete `main...ai/task-017` branch summary, not a FIX-only delta and not an empty block. At round 3 the branch comparison is four files with additions only; generate the exact `git diff --stat 54303dc7d56ddce4ae9b22ef05c7dd310e731737..20816d295caaefd0f6cfae316bc73b0923b3f9f5` (or equivalent tested-implementation comparison) and place it in RESULT. The evidence-only RESULT commit itself should not be counted as implementation changes.

3. Restore exact task metadata `Base Main SHA: 54303dc7d56ddce4ae9b22ef05c7dd310e731737` instead of `(n/a)`.

`IMPLEMENTATION_HEAD` is now correct and MUST remain `20816d295caaefd0f6cfae316bc73b0923b3f9f5`.

## Re-review Gate
Run `/aios-worker FIX TASK-017` as an evidence-only fix. Update only `.ai/results/RESULT-017.md` if possible. No production-code change and no architectural re-plan are required. Publish the new branch head and request review again.
