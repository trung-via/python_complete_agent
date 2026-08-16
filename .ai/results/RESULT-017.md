# RESULT-017

STATUS: READY_FOR_REVIEW

## Summary
Fix REVIEW-017 items: remove CLI key/provider/model options, enforce task identity, redact provider error text, and record exact PLAN artifact identity

## Task Metadata
- Task: `TASK-017`
- Action: `FIX`
- Authorized Artifact: `.ai/reviews/REVIEW-017.md (3c42216499)`
- Base Main SHA: `(n/a)`
- Branch: `ai/task-017`

## Files Changed
- scripts/aios_external_brain_plan.py
- src/aios_bridge/external_brain/runner.py
- tests/aios_bridge/external_brain/test_runner.py

## Diff Stat
```text
scripts/aios_external_brain_plan.py             | 23 +-----
 src/aios_bridge/external_brain/runner.py        | 51 ++++++++++----
 tests/aios_bridge/external_brain/test_runner.py | 94 ++++++++++++++++++++++---
 3 files changed, 128 insertions(+), 40 deletions(-)
```

## Tests
Command: `.\venv\Scripts\python -c "import subprocess, sys; r1 = subprocess.run([r'.\venv\Scripts\pytest', 'tests/aios_bridge/external_brain/', '-q'], capture_output=True, text=True); r2 = subprocess.run([r'.\venv\Scripts\pytest', 'tests/aios_bridge/', '-q'], capture_output=True, text=True); r3 = subprocess.run([r'.\venv\Scripts\pytest', 'tests/', '-q', '-W', 'ignore'], capture_output=True, text=True); print('=== Focused External Brain: ' + r1.stdout.strip().splitlines()[-1] + ' ===\n' + '=== Bridge Suite: ' + r2.stdout.strip().splitlines()[-1] + ' ===\n' + '=== Full Repository Suite: ' + r3.stdout.strip().splitlines()[-1] + ' ===\n\n' + '[Full Suite Output]\n' + r3.stdout.strip()); sys.exit(max(r1.returncode, r2.returncode, r3.returncode))"`  
Exit code: 0

```text
=== Focused External Brain: 86 passed, 204 warnings in 0.37s ===
=== Bridge Suite: 86 passed, 204 warnings in 0.30s ===
=== Full Repository Suite: 560 passed in 53.24s ===

[Full Suite Output]
........................................................................ [ 12%]
........................................................................ [ 25%]
........................................................................ [ 38%]
........................................................................ [ 51%]
........................................................................ [ 64%]
........................................................................ [ 77%]
........................................................................ [ 90%]
........................................................                 [100%]
560 passed in 53.24s
```

## Risks / Notes
## Milestone 3.1 Real-Task Proof Telemetry
IMPLEMENTATION_HEAD: (tested implementation commit SHA)
EXTERNAL_BRAIN_PROVIDER: minimax
EXTERNAL_BRAIN_MODEL: MiniMax-M3
EXTERNAL_BRAIN_REQUEST_ID: m31-real-plan-task017-005
EXTERNAL_BRAIN_TASK_ID: TASK-017
EXTERNAL_BRAIN_STATUS: SUCCESS
PROVIDER_INPUT_TOKENS: 7921
PROVIDER_OUTPUT_TOKENS: 4232
LATENCY_MS: 84525
CONTEXT_FINGERPRINT: a2c1611f56260a687849ab8871c6c3ba25d64118ba36abc51464af038803dc4f
CONTEXT_COUNTED_TOKENS: 33354
CONTEXT_COUNTER_ID: utf8-byte-conservative-v1
LEDGER_PERSISTED: True
PLAN_ARTIFACT: .ai/context/TASK-017-MINIMAX-PLAN.md
PLAN_ARTIFACT_IDENTITY: commit: 8b65bca623ccfba95d9ea0956f960a3eb8efd93a / blob: 7cfe32d75a8989a58a45c08aaca4084c6323e78e
PLAN_ADOPTION: ACCEPTED_WITH_LOCAL_ADJUSTMENTS
CHATGPT_REPLAN_REQUIRED: NO
LIVE_CALLS_IN_AUTOMATED_TESTS: 0
CREDENTIALS_PERSISTED: NO
SEPARATED_REASONING_PERSISTED: NO

## REVIEW-017 Required Changes Addressed
1. Operator CLI `--api-key` option removed: API key strictly resolved from AIOS_MINIMAX_API_KEY environment variable.
2. Provider/Model locked: Removed `--provider` and `--model` CLI arguments; runner enforces provider == 'minimax' and model == 'MiniMax-M3' before provider invocation.
3. Task Identity validation: Added extract_task_id enforcing TASK-<digits> format; fails closed with non-zero exit before network call on invalid task names.
4. Error message redaction: ModelResponse.error_message is strictly excluded on failure outcomes; output only contains normalized status and error code.
5. Exact PLAN artifact identity: Recorded commit 8b65bca623ccfba95d9ea0956f960a3eb8efd93a / blob 7cfe32d75a8989a58a45c08aaca4084c6323e78e.
6. Changed files listed with exact paths:
   - scripts/aios_external_brain_plan.py
   - src/aios_bridge/external_brain/runner.py
   - tests/aios_bridge/external_brain/test_runner.py

## Test Suites Execution Evidence
- Focused External Brain Suite: 86 passed in ~0.3s (tests/aios_bridge/external_brain/)
- Existing Bridge Suite: 86 passed in ~0.3s (tests/aios_bridge/)
- Full Repository Suite: 560 passed in ~53s (0 regressions against canonical baseline 54303dc7d56ddce4ae9b22ef05c7dd310e731737)

## Generated
2026-08-16T15:59:54+07:00
