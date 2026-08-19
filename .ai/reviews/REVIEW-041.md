# REVIEW-041 — E2 Codex Local Transport

STATUS: PASS
APPROVED: YES
READY_FOR_HUMAN_MERGE: YES
MERGE_AUTHORIZED: NO

## Review Round

Round 2 — final independent close-condition audit for R1-1 plus fresh lineage, scope, process-cleanup, receipt-semantics, authority, and regression verification.

## Authoritative Anchors

```text
TASK_ID: TASK-041
BASELINE_MAIN_SHA: 1c35ce096f366d9d87250b5e8ae1759327dc5a51
TASK_BRANCH: ai/task-041
ROUND_1_TASK_HEAD_SHA: 42efc392336bfc79baab8fe52a63fcd6aaea9f24
FINAL_TASK_HEAD_SHA: 7ea6197063dbcede82ec24b23cc3bad2621e8c8a
TASK_BLOB_SHA: 497f61d72edd93739bccb6f3a3e7a73fc0b6108b
ADR_030_BLOB_SHA: e5c0dd2214ea81ae01e903847d4563ab88f983cb
BLUEPRINT_BLOB_SHA: f67686829c79c3e34973a981cda9d3d2042863ad
RESULT_BLOB_SHA: dfc3af3201dba9d84e22e48719a82829fcf14607
CODEX_LOCAL_BLOB_SHA: dd1fae54506459a2a638441a35d5a327d89da8cc
PACKAGE_INIT_BLOB_SHA: 560d303f06e63705bcbdcb8b75b04c16fb254929
TEST_BLOB_SHA: 366ba89921d462bca1b908b4628d055099753f90
```

Fresh final drift check:

```text
7ea6197063dbcede82ec24b23cc3bad2621e8c8a -> ai/task-041
STATUS: identical
AHEAD: 0
BEHIND: 0
```

Fresh main check:

```text
main: 1c35ce096f366d9d87250b5e8ae1759327dc5a51
MAIN_DRIFT_FROM_TASK_BASELINE: NO
```

## Lineage / Scope Audit

Across TASK-041 from baseline:

```text
COMMITS_AHEAD_OF_BASELINE: 2
COMMITS_BEHIND_BASELINE: 0
MERGE_BASE: 1c35ce096f366d9d87250b5e8ae1759327dc5a51
```

The second commit is the Human-authorized FIX publication.

Round-2 delta from the reviewed Round-1 head is exactly:

```text
.ai/results/RESULT-041.md
src/aios_bridge/executor_transports/codex_local.py
tests/aios_bridge/test_codex_local_transport.py
```

No E1 contract, Bridge, dispatch, lease, failover, hot-handoff, provider, External Brain, docs, E3/E4/E5, H-Series, or M11 path changed.

```text
SCOPE_AUDIT: PASS
ROUND_2_ALLOWED_FILES_ONLY: PASS
```

## R1-1 Close Audit

### Root Cause Removed

Round 1 found that Windows cleanup could return as soon as the parent Codex process exited, skipping process-tree cleanup. The final implementation removes that early-success behavior.

`_cleanup_process()` now captures a valid positive PID before cleanup and:

### Windows

```text
best-effort direct terminate
-> if valid PID: bounded taskkill /PID <pid> /T /F
   shell=False
   minimal child environment
   bounded timeout
-> bounded parent wait
-> direct kill + bounded wait only as fallback when parent did not exit
```

The tree-cleanup attempt is no longer skipped merely because the parent was already exited or exits promptly after terminate.

### POSIX

For a valid PID/process-group identity:

```text
best-effort killpg(SIGTERM)
-> bounded wait
-> best-effort killpg(SIGKILL)
-> bounded wait
```

An already-exited group leader no longer creates an early return that suppresses group cleanup.

For malformed/non-positive PID, cleanup remains bounded and falls back to direct-process best effort without fabricating a process-group identity.

Cleanup exceptions remain swallowed as best-effort cleanup errors and do not replace the primary transport receipt.

```text
R1-1: CLOSED
WINDOWS_PARENT_EXIT_SKIP_REMOVED: PASS
WINDOWS_TREE_CLEANUP_BOUNDED: PASS
POSIX_GROUP_CLEANUP_BOUNDED: PASS
INVALID_PID_BOUNDED: PASS
CLEANUP_EXCEPTION_PRESERVES_PRIMARY_RESULT: PASS
```

## Direct Cleanup Test Audit

Round 2 adds deterministic tests that exercise the production `_cleanup_process()` implementation itself rather than only monkeypatching the function away.

Mechanical coverage includes:

```text
Windows terminate makes parent exit immediately -> taskkill tree attempt still occurs
Windows parent already exited + valid PID -> taskkill tree attempt still occurs
Windows taskkill failure -> bounded, no cleanup exception escapes
Windows direct terminate/kill failure -> bounded
invalid/non-positive/non-int PID -> bounded, no taskkill with fabricated PID
POSIX exited group leader -> SIGTERM + SIGKILL group attempts still occur
TIMEOUT with real cleanup failure -> TIMED_OUT / CODEX_TIMEOUT preserved
KeyboardInterrupt with real cleanup failure -> INTERRUPTED / CALLER_INTERRUPTED preserved
one invoke -> at most one Codex process spawn
```

```text
REQUIRED_CLEANUP_TESTS: PASS
ADVERSARIAL_CLEANUP_TESTS: PASS
NO_SECOND_CODEX_SPAWN: PASS
```

## E2 Contract Revalidation

The Round-1 passing areas did not drift. Final source still establishes:

```text
CODEX_LOCAL_TRANSPORT_CONCRETE: PASS
E1_PROTOCOL_CONFORMANCE: PASS
EXACT_STDIN_PAYLOAD: PASS
SAFE_CODEX_EXEC_ARGV: PASS
WORKSPACE_BRANCH_PREFLIGHT: PASS
DIRTY_WORKTREE_FAIL_CLOSED: PASS
SUBSCRIPTION_FIRST_ENVIRONMENT: PASS
SECRET_ENV_STRIPPING: PASS
TOOL_NETWORK_DISABLED: PASS
DANGER_BYPASS_FORBIDDEN: PASS
PROCESS_STATUS_MAPPING: PASS
TIMEOUT_INTERRUPT_CLEANUP: PASS
EXIT_ZERO_IS_TRANSPORT_ONLY: PASS
NO_REAL_CODEX_IN_TESTS: PASS
NO_BRIDGE_INTEGRATION: PASS
H_SERIES_REMAINS_DEFERRED: PASS
```

No retry, sandbox weakening, dangerous bypass, `shell=True`, session resume/history lookup, auto-approval, auto-lease, auto-publication, commit, push, merge, or provider/API fallback was introduced.

E2 remains a concrete transport only. Real safe Windows workspace mutation and the zero-copy/paste operational chain remain separate future proof work; E2 PASS does not claim E5.

## Publication / Regression Gate

Final Bridge publication is a Human-authorized FIX bound to the exact Round-1 review artifact and reports:

```text
ACTION: FIX
EXECUTOR_ID: codex
EXECUTOR_FAILOVER: NO
HOT_HANDOFF: NO
1321 passed, 7 skipped, 1533 warnings in 114.43s
exit code: 0
```

Because the full repository suite includes the E2 transport tests and the existing E1/M4/M5 regression tests, the required targeted surfaces are green within the final publication gate.

```text
FULL_REPO_TESTS: PASS
REGRESSIONS: 0
```

## Findings

```text
R1-1: CLOSED
BLOCKING_FINDINGS: NONE
SECURITY_AUTHORITY_FINDINGS: NONE
CONTRACT_FINDINGS: NONE
SCOPE_FINDINGS: NONE
REGRESSION_FINDINGS: NONE
```

## Final Acceptance

```text
CODEX_LOCAL_TRANSPORT_CONCRETE: PASS
E1_PROTOCOL_CONFORMANCE: PASS
EXACT_STDIN_PAYLOAD: PASS
SAFE_CODEX_EXEC_ARGV: PASS
WORKSPACE_BRANCH_PREFLIGHT: PASS
DIRTY_WORKTREE_FAIL_CLOSED: PASS
SUBSCRIPTION_FIRST_ENVIRONMENT: PASS
SECRET_ENV_STRIPPING: PASS
TOOL_NETWORK_DISABLED: PASS
DANGER_BYPASS_FORBIDDEN: PASS
PROCESS_STATUS_MAPPING: PASS
TIMEOUT_INTERRUPT_CLEANUP: PASS
EXIT_ZERO_IS_TRANSPORT_ONLY: PASS
NO_REAL_CODEX_IN_TESTS: PASS
NO_BRIDGE_INTEGRATION: PASS
H_SERIES_REMAINS_DEFERRED: PASS
FULL_REPO_TESTS: PASS
REGRESSIONS: 0
FINAL_INDEPENDENT_AUDIT: PASS
E2: PASS
```

## Final Decision

TASK-041 satisfies ADR-030 and the locked E2 implementation blueprint after closing R1-1.

```text
STATUS: PASS
APPROVED: YES
READY_FOR_HUMAN_MERGE: YES
MERGE_AUTHORIZED: NO
E2: PASS
E3_PROVEN: NO
E4_PROVEN: NO
E5_PROVEN: NO
```

Only Human may authorize merge.
