# RESULT-020

STATUS: READY_FOR_REVIEW

## Summary
Implement #12-M1.5 Quota & Efficiency Telemetry contract, pure estimation/aggregation helpers, historical TASK-019 baseline artifact, and comprehensive tests (src/aios_bridge/continuity/usage.py)

## Task Metadata
- Task: `TASK-020`
- Action: `FIX`
- Authorized Artifact: `.ai/reviews/REVIEW-020.md (7e96b9c56d)`
- Base Main SHA: `5484462208dd47b9fbb3fd5ad382f423301c468a`
- Branch: `ai/task-020`

## Files Changed
- .ai/metrics/TASK-019-USAGE.json
- .ai/results/RESULT-020.md
- src/aios_bridge/continuity/__init__.py
- src/aios_bridge/continuity/usage.py
- tests/aios_bridge/continuity/test_usage.py

## Diff Stat
```text
 .ai/metrics/TASK-019-USAGE.json            | 107 ++++
 .ai/results/RESULT-020.md                  | 107 ++++
 src/aios_bridge/continuity/__init__.py     |  26 +-
 src/aios_bridge/continuity/usage.py        | 752 +++++++++++++++++++++++++++++
 tests/aios_bridge/continuity/test_usage.py | 427 ++++++++++++++++
 5 files changed, 1418 insertions(+), 1 deletion(-)
```

## Tests
Command: `.\venv\Scripts\python -c "import subprocess, sys; r1 = subprocess.run([r'.\venv\Scripts\pytest', 'tests/aios_bridge/continuity/', '-q'], capture_output=True, text=True); r2 = subprocess.run([r'.\venv\Scripts\pytest', 'tests/aios_bridge/', '-q'], capture_output=True, text=True); r3 = subprocess.run([r'.\venv\Scripts\pytest', 'tests/', '-q', '-W', 'ignore'], capture_output=True, text=True); print('=== Focused Continuity Suite: ' + r1.stdout.strip().splitlines()[-1] + ' ===\n' + '=== Bridge Suite: ' + r2.stdout.strip().splitlines()[-1] + ' ===\n' + '=== Full Repository Suite: ' + r3.stdout.strip().splitlines()[-1] + ' ===\n\n' + '[Full Suite Output]\n' + r3.stdout.strip()); sys.exit(max(r1.returncode, r2.returncode, r3.returncode))"`  
Exit code: 0

```text
=== Focused Continuity Suite: 36 passed, 1 warning in 0.09s ===
=== Bridge Suite: 122 passed, 204 warnings in 0.36s ===
=== Full Repository Suite: 596 passed in 67.62s (0:01:07) ===

[Full Suite Output]
........................................................................ [ 12%]
........................................................................ [ 24%]
........................................................................ [ 36%]
........................................................................ [ 48%]
........................................................................ [ 60%]
........................................................................ [ 72%]
........................................................................ [ 84%]
........................................................................ [ 96%]
....................                                                     [100%]
596 passed in 67.62s (0:01:07)

```

## Risks / Notes
## Milestone M1.5 Quota & Efficiency Telemetry
IMPLEMENTATION_HEAD: c079e69d0cbb7764b4585515805b35add1dddb50
USAGE_SCHEMA_VERSION: 1
TASK_019_BASELINE_VALID: YES
TELEMETRY_MODEL_TURNS_ADDED: 0
LIVE_EXTERNAL_CALLS: 0
BRIDGE_V0_4_BEHAVIOR_CHANGED: NO
AUTHORITY_WIDENED: NO
SECRETS_OR_REASONING_PERSISTED: NO

## Review Manifest (ADR-013 / ADR-014 Delta-First Evidence)
BASE_SHA: 5484462208dd47b9fbb3fd5ad382f423301c468a
IMPLEMENTATION_SHA: c079e69d0cbb7764b4585515805b35add1dddb50
PREVIOUS_REVIEW_SHA: 579ef1ddd6dab291492f6039357361a080709f27
CHANGED_FILES:
- .ai/metrics/TASK-019-USAGE.json
- .ai/results/RESULT-020.md
- src/aios_bridge/continuity/__init__.py
- src/aios_bridge/continuity/usage.py
- tests/aios_bridge/continuity/test_usage.py
TEST_SUMMARY: 36 passed in Focused Continuity Suite; 122 passed in Bridge Suite; 596 passed in Full Repository Suite (0 regressions)
BRIDGE_BEHAVIOR_CHANGED: NO
AUTHORITY_WIDENED: NO
LIVE_EXTERNAL_CALLS: 0

## REVIEW-020 Required Changes Addressed
1. R1-1 (Bounded method): TokenMeasurement.method is validated as a bounded conservative lowercase identifier (max 64 chars) with regex ^[a-z0-9]+(?:[a-z0-9_.-]+)*$; estimate_tokens_from_bytes() fails closed on unsupported method labels.
2. R1-2 (Nullable exact proxies): BrainUsageRecord and ExecutorUsageRecord exact proxy counts (full_file_reads, artifact_reads, test_runs) are now nullable; .ai/metrics/TASK-019-USAGE.json baseline records null for unmeasured proxy counts instead of fabricating 0.
3. R1-3 (Partition equality & ratio check): EfficiencyMetrics enforces exact component sum equality (useful + redundant + escalated == total) when all partition components and total are known, and verifies supplied context_efficiency_ratio matches useful/total bytes ratio.
4. R1-4 (Incomplete token aggregation): aggregate_token_ranges() returns (None, None) when any measurement is UNKNOWN or missing tokens, preventing partial sums from masquerading as complete aggregates.

## Test Suites Execution Evidence (against implementation c079e69d0cbb7764b4585515805b35add1dddb50)
- Focused Continuity Suite: 36 passed in ~0.23s (tests/aios_bridge/continuity/)
- Bridge Suite: 122 passed in ~0.58s (tests/aios_bridge/)
- Full Repository Suite: 596 passed in ~57s (0 regressions against canonical baseline 5484462208dd47b9fbb3fd5ad382f423301c468a)

## Generated
2026-08-16T20:24:50+07:00
