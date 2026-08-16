# REVIEW-017 — TASK-017 Manual External Brain PLAN Runner

STATUS: CHANGES_REQUIRED

## Scope
- Reviewed branch: `ai/task-017`
- Reviewed head: `a50aa3bb44be695496afe8c196af16c9adaf29fd`
- Base main: `54303dc7d56ddce4ae9b22ef05c7dd310e731737`
- PLAN adoption remains `ACCEPTED_WITH_LOCAL_ADJUSTMENTS`.
- `CHATGPT_REPLAN_REQUIRED: NO`.

## Required Changes

1. Remove the operator CLI `--api-key` option. TASK-017 requires the production runner to use `AIOS_MINIMAX_API_KEY` from the local environment. Test-only dependency injection may remain internal, but must not be an operator CLI option.

2. Keep M3.1 locked to `provider=minimax` and `model=MiniMax-M3`. Remove operator-facing `--provider` / `--model` generalization or fail closed unless those exact locked values are used. Do not introduce routing or provider selection in TASK-017.

3. Fail closed on invalid task identity. The current helper silently substitutes `TASK-017` when the task filename does not begin with `TASK-`. Require the existing `TASK-<digits>` identity contract and return non-zero before provider invocation on invalid input.

4. On non-SUCCESS provider outcomes, do not print `ModelResponse.error_message`. Output only normalized safe status/error-code information plus permitted telemetry. Add a regression test proving provider error text is not emitted.

5. Fix RESULT-017 exact evidence. Current values are not acceptable:
   - `IMPLEMENTATION_HEAD: (pre-publish branch commit)` must become the exact tested implementation commit SHA.
   - `PLAN_ARTIFACT_IDENTITY: 54303dc...` is the base-main SHA, not the PLAN artifact identity.
   - Actual validated PLAN artifact identities at review time: control commit `8b65bca623ccfba95d9ea0956f960a3eb8efd93a`; file blob `7cfe32d75a8989a58a45c08aaca4084c6323e78e`.
   If needed, use an evidence-only RESULT follow-up commit after the tested implementation commit.

6. Complete RESULT changed-file evidence. `## Diff Stat` is empty and `Files Changed` should list exact paths rather than `scripts/`.

7. Extend focused tests for the fixes: no operator CLI key option; locked provider/model; invalid task identity fails before provider call; provider failure text not emitted; invalid context kind fails before provider call; zero live external calls remains true.

## Existing Good Evidence
- Branch is ahead 1 / behind 0 from current main.
- Existing M1/M2/M3 components are reused; provider HTTP logic is not duplicated.
- No retry/fallback/router/repo crawl was found in the reviewed delta.
- Current RESULT reports External Brain 83 passed, Bridge 83 passed, full repository 557 passed; rerun all after fixes.
- Live PLAN proof remains valid: request `m31-real-plan-task017-005`, status `SUCCESS`, 7921 input tokens, 4232 output tokens, 84525 ms, ledger persisted.

## Re-review Gate
Run the normal human-approved fix workflow:

`/aios-worker FIX TASK-017`

Then publish a new branch head and updated RESULT-017 with exact evidence and all required suites green.
