# REVIEW-017 — TASK-017 Manual External Brain PLAN Runner

STATUS: CHANGES_REQUIRED

## Review Scope
- Review round: `2`
- Reviewed branch: `ai/task-017`
- Reviewed head: `c29ac6c4ad5875c8c69a62b89e197fc96f1411d7`
- Base main: `54303dc7d56ddce4ae9b22ef05c7dd310e731737`
- Branch relation: ahead 2 / behind 0; merge-base is exact current main.
- PLAN adoption remains `ACCEPTED_WITH_LOCAL_ADJUSTMENTS`.
- `CHATGPT_REPLAN_REQUIRED: NO`.

## Round-1 Fixes Accepted
1. Operator CLI `--api-key` removed; production CLI now relies on `AIOS_MINIMAX_API_KEY`.
2. Operator-facing `--provider` / `--model` removed; internal runner fails closed unless provider=`minimax` and model=`MiniMax-M3`.
3. Provider non-SUCCESS output no longer emits `ModelResponse.error_message`.
4. PLAN artifact identity is now correct: control commit `8b65bca623ccfba95d9ea0956f960a3eb8efd93a`, blob `7cfe32d75a8989a58a45c08aaca4084c6323e78e`.
5. Focused regression coverage was extended and current RESULT reports External Brain 86 passed, Bridge 86 passed, full repository 560 passed.
6. No retry/fallback/router/repo crawl/provider HTTP duplication was found in the reviewed delta.

## Remaining Required Changes

1. Enforce the existing task-ID contract **case-sensitively**. The canonical M1 contract uses `^TASK-\d+$`; current `runner.py` uses `re.IGNORECASE` and the test explicitly accepts `task-999.md`, then normalizes it to `TASK-999`. This widens the locked identity contract. Remove `re.IGNORECASE`, do not normalize an invalid lowercase ID into a valid uppercase ID, and add a regression assertion that `task-999.md` fails before provider/network invocation.

2. Fix `RESULT-017` exact tested implementation evidence. It still contains:
   - `IMPLEMENTATION_HEAD: (tested implementation commit SHA)`
   This must be an actual immutable SHA for the implementation revision on which the reported suites were run. After the remaining code/test fix, run the focused, Bridge, and full repository suites on that exact implementation revision and record its SHA. If the RESULT update itself creates a later evidence-only commit, that is acceptable; clearly distinguish tested implementation SHA from evidence/publish head.

3. Replace the current FIX-only diffstat with the required branch changed-file summary / diffstat relative to canonical `main`. At review round 2, `main...ai/task-017` contains four branch files:
   - `.ai/results/RESULT-017.md`
   - `scripts/aios_external_brain_plan.py`
   - `src/aios_bridge/external_brain/runner.py`
   - `tests/aios_bridge/external_brain/test_runner.py`
   The current RESULT diffstat (`3 files changed, 128 insertions(+), 40 deletions(-)`) describes only the round-1 FIX delta, not the complete TASK-017 branch delta. Also restore the exact base-main SHA instead of `Base Main SHA: (n/a)`.

## Evidence Verified in Round 2
- Exact reviewed head: `c29ac6c4ad5875c8c69a62b89e197fc96f1411d7`.
- Round-1 -> Round-2 fix is one commit (`a50aa3b...` -> `c29ac6c...`) touching RESULT, CLI, runner, and runner tests.
- Current RESULT reports:
  - External Brain: `86 passed`
  - Bridge: `86 passed`
  - Full repository: `560 passed`
  - live calls in automated tests: `0`
  - credentials persisted: `NO`
  - separated reasoning persisted: `NO`
- Live MiniMax proof remains valid: request `m31-real-plan-task017-005`, `SUCCESS`, input `7921`, output `4232`, latency `84525 ms`, ledger persisted.

## Re-review Gate
Use the normal human-approved fix workflow:

`/aios-worker FIX TASK-017`

This is a narrow contract/evidence correction only; no architectural re-plan is required. Publish a new branch head with strict uppercase task identity, exact tested implementation SHA, full branch diff evidence, and all required suites green.
