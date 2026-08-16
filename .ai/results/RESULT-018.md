# RESULT-018

STATUS: READY_FOR_REVIEW

## Summary
Implement ADR-009 v0.5-M3.0.1 MiniMax timeout configurability

## Task Metadata
- Task: `TASK-018`
- Action: `RUN`
- Authorized Artifact: `.ai/tasks/TASK-018.md (58d5c0309b)`
- Base Main SHA: `6fd3cb155c9edf6aaebbf85c5ad0812e7e737abb`
- Branch: `ai/task-018`

## Files Changed
- src/aios_bridge/external_brain/providers/minimax.py
- tests/aios_bridge/external_brain/test_minimax_provider.py

## Diff Stat
```text
.../external_brain/providers/minimax.py            | 22 +++++++++-
 .../external_brain/test_minimax_provider.py        | 49 +++++++++++++++++++++-
 2 files changed, 67 insertions(+), 4 deletions(-)
```

## Tests
Command: `.\venv\Scripts\python -c "import subprocess, sys; r1 = subprocess.run([r'.\venv\Scripts\pytest', 'tests/aios_bridge/external_brain/', '-q'], capture_output=True, text=True); r2 = subprocess.run([r'.\venv\Scripts\pytest', 'tests/aios_bridge/', '-q'], capture_output=True, text=True); r3 = subprocess.run([r'.\venv\Scripts\pytest', 'tests/', '-q', '-W', 'ignore'], capture_output=True, text=True); print('=== Focused External Brain: ' + r1.stdout.strip().splitlines()[-1] + ' ===\n' + '=== Bridge Suite: ' + r2.stdout.strip().splitlines()[-1] + ' ===\n' + '=== Full Repository Suite: ' + r3.stdout.strip().splitlines()[-1] + ' ===\n\n' + '[Full Suite Output]\n' + r3.stdout.strip()); sys.exit(max(r1.returncode, r2.returncode, r3.returncode))"`  
Exit code: 0

```text
=== Focused External Brain: 73 passed, 155 warnings in 0.26s ===
=== Bridge Suite: 73 passed, 155 warnings in 0.25s ===
=== Full Repository Suite: 547 passed in 61.89s (0:01:01) ===

[Full Suite Output]
........................................................................ [ 13%]
........................................................................ [ 26%]
........................................................................ [ 39%]
........................................................................ [ 52%]
........................................................................ [ 65%]
........................................................................ [ 78%]
........................................................................ [ 92%]
...........................................                              [100%]
547 passed in 61.89s (0:01:01)
```

## Risks / Notes
- LIVE_SMOKE: NOT_RUN (no automated live MiniMax network calls in test suites)
- Test Suites Summary:
  * Focused External Brain Suite: 73 passed (tests/aios_bridge/external_brain/)
  * Existing Bridge Suite: 73 passed (tests/aios_bridge/)
  * Full Repository Suite: 547 passed in ~59s (0 regressions against canonical baseline 6fd3cb155c9edf6aaebbf85c5ad0812e7e737abb)
- Changed Production Files:
  * src/aios_bridge/external_brain/providers/minimax.py (added timeout_seconds parameter with positive finite validation, forwarded explicitly to TransportRequest)
- Changed Test Files:
  * tests/aios_bridge/external_brain/test_minimax_provider.py (added timeout configurability, validation, and repr tests)
- Governance confirmation:
  * Single-call / no-retry / no-fallback preserved
  * External brain remains strictly proposal-only with zero execution authority
  * Credential isolation preserved in repr/str

## Generated
2026-08-16T15:02:55+07:00
