# TASK-003 — Phase 5.6 M1/M2 Integration onto main

## Objective
Integrate the already-completed Phase 5.6 M1 Cancellation Control and M2 Retry Policy Engine from `p0-agent-control` onto the current `main` baseline, without pulling in the unfinished M3 work.

## Source Commits
Completed work to integrate:
- `dd957ddb545b620358ce6bd5cbe3efa467b6e5c6` — Phase 5.6 M1 Cancellation Control & CancellationToken.
- `5ad971c261608ff65ec00288b29cd061d38b6174` — Phase 5.6 M2 Retry & Failure Policy Engine.

Explicitly EXCLUDE the later partial M3 commits for this task:
- `e70900b09ba0413ba087b703d255c7c6fc624ac6`
- `fb5891a1c8ea098f0798c274718954ea4654dc72`
- `4e0b3d6b42a8b59b53d5ac13c1004eb6e6fb1209`

## Scope
- Start from the current `main` baseline used by AIOS.
- Bring in the functional changes from M1 and M2 only.
- Prefer a clean cherry-pick of the two completed commits if conflict-free; otherwise resolve conflicts minimally while preserving the current `main` AIOS files.
- Do not modify AIOS Bridge behavior except where a merge conflict mechanically requires preserving current `main`.
- Do not continue or redesign M3 in this task.

## Expected Functional Areas
M1 should include cancellation control and durable halt behavior, including:
- `src/core/cancellation.py`
- `src/agent/cancellation.py`
- AgentLoop cancellation checks
- checkpoint/contract support needed by M1
- M1 unit/integration tests

M2 should include the pure retry policy engine, including:
- `src/core/retry_policy.py`
- `src/agent/retry_policy.py`
- RetryManager delegation to RetryPolicyEngine
- retry-policy unit/integration tests
- exact call_id/idempotency_key reuse across retries

## Safety / Constraints
- Preserve Phase 5.5 recovery/integrity behavior already on `main`.
- Preserve AIOS v0.3.2 files on `main`.
- No auto-merge.
- No unrelated refactors.
- Do not include any M3-only event logging, FailureClassifier, or per-attempt persistence changes from the excluded commits.

## Acceptance Criteria
- [ ] Current `main` + Phase 5.6 M1/M2 coexist without merge conflicts or regressions.
- [ ] Cancellation behavior remains fail-closed and durable before in-memory cancellation state changes.
- [ ] RetryPolicyEngine remains pure and deterministic.
- [ ] Tool retries reuse the exact `call_id` and `idempotency_key`.
- [ ] No files/behavior from the excluded M3 commits are introduced.
- [ ] AIOS v0.3.2 remains intact.
- [ ] Full repository test suite passes.
- [ ] Branch `ai/task-003` is pushed for ChatGPT review.

## Verification Requirements
Report:
1. exact commits integrated or equivalent conflict-resolved changes;
2. files changed relative to current `main`;
3. focused M1/M2 test totals;
4. full regression test total;
5. final commit SHA.

## Delivery
Publish on `ai/task-003`; do not merge automatically.
