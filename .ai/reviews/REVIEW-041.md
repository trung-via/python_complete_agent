# REVIEW-041 — E2 Codex Local Transport

STATUS: CHANGES_REQUIRED
APPROVED: NO
READY_FOR_HUMAN_MERGE: NO
MERGE_AUTHORIZED: NO

## Review Round

Round 1 — independent lineage, scope, process-safety, command/env, workspace preflight, E1 binding, authority, cleanup, and regression audit.

## Authoritative Anchors

```text
TASK_ID: TASK-041
BASELINE_MAIN_SHA: 1c35ce096f366d9d87250b5e8ae1759327dc5a51
TASK_BRANCH: ai/task-041
REVIEWED_TASK_HEAD_SHA: 42efc392336bfc79baab8fe52a63fcd6aaea9f24
TASK_BLOB_SHA: 497f61d72edd93739bccb6f3a3e7a73fc0b6108b
ADR_030_BLOB_SHA: e5c0dd2214ea81ae01e903847d4563ab88f983cb
BLUEPRINT_BLOB_SHA: f67686829c79c3e34973a981cda9d3d2042863ad
RESULT_BLOB_SHA: 8365fd8b8aea05ea6fdaa9b1c683b5b07d7f3145
CODEX_LOCAL_BLOB_SHA: a46a608394f3463078ef38b6f17662d902279f53
PACKAGE_INIT_BLOB_SHA: 560d303f06e63705bcbdcb8b75b04c16fb254929
TEST_BLOB_SHA: 60528b583ff636013faf3ddf82eede699966a833
```

Fresh lineage check:

```text
COMMITS_AHEAD_OF_BASELINE: 1
COMMITS_BEHIND_BASELINE: 0
MERGE_BASE: 1c35ce096f366d9d87250b5e8ae1759327dc5a51
MAIN_AT_REVIEW: 1c35ce096f366d9d87250b5e8ae1759327dc5a51
```

Changed paths are exactly:

```text
.ai/results/RESULT-041.md
src/aios_bridge/executor_transports/__init__.py
src/aios_bridge/executor_transports/codex_local.py
tests/aios_bridge/test_codex_local_transport.py
```

SCOPE_AUDIT: PASS

## Passing Contract Areas

The implementation correctly preserves the major E2 boundaries:

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
PROCESS_STATUS_MAPPING: PASS except cleanup close-condition below
EXIT_ZERO_IS_TRANSPORT_ONLY: PASS
NO_REAL_CODEX_IN_TESTS: PASS
NO_BRIDGE_INTEGRATION: PASS
H_SERIES_REMAINS_DEFERRED: PASS
```

The production argv is stable and requests `workspace-write`, approval policy `never`, tool network disabled, web search disabled, exact workspace via `-C`, and exact payload via final stdin `-`. No dangerous bypass/fallback path is present.

The child environment is a closed allowlist and strips the locked API/application-secret keys. Git preflight is read-only and verifies exact toplevel, branch, and clean status before Codex spawn. E1 transport/payload validation runs before preflight/spawn. No Bridge, dispatch, lease-store, provider/model, commit, push, publish, or merge authority is introduced.

Final Bridge publication reports:

```text
1310 passed, 7 skipped, 1533 warnings in 136.55s
exit code 0
```

FULL_REPO_TESTS: PASS
REGRESSIONS: 0

## Findings

### R1-1

```text
FINDING_ID: R1-1
SEVERITY: HIGH
ROOT_CAUSE: On Windows, _cleanup_process() calls process.terminate(), then process.wait(); if that wait succeeds it returns immediately. The process-tree cleanup path using taskkill /PID <pid> /T /F is therefore skipped whenever the Codex parent exits promptly after terminate(). The function also has an initial early-return when process.poll() is already non-None, which similarly prevents any best-effort descendant cleanup.
BROKEN_INVARIANT: ADR-030 Decision 11 and TASK-041 blueprint section 18 require timeout/caller-interruption cleanup to make a best-effort attempt to terminate the Codex process group/tree before returning. Parent-process termination alone is not equivalent to process-tree termination.
REQUIRED_BEHAVIOR: For a timeout or caller interruption, cleanup must not declare completion merely because the parent exited. On Windows, when a valid PID exists, make a bounded best-effort tree-cleanup attempt while preserving shell=False and the minimal environment, and then perform bounded direct-process fallback/wait as necessary. On POSIX, do not let an already-exited process-group leader automatically suppress a best-effort killpg attempt when a valid PID/process-group identity exists. Cleanup remains best-effort and must not replace the primary TIMED_OUT/INTERRUPTED receipt with a cleanup exception.
FORBIDDEN_IMPLEMENTATIONS: No unsafe Codex rerun; no retry; no danger-full-access; no dangerously-bypass-approvals-and-sandbox; no shell=True; no unbounded taskkill/wait loop; no Bridge/lease/dispatch changes; no generic provider/process lifecycle framework; no H-Series abstraction.
REQUIRED_TESTS: Add deterministic cleanup tests that exercise _cleanup_process itself rather than only monkeypatching it away. At minimum prove the Windows branch attempts bounded process-tree cleanup even when direct terminate makes the parent exit immediately, and prove timeout/interruption still return their original canonical receipt with at most one Codex spawn. Add equivalent POSIX coverage or a platform-neutral helper test proving an exited group leader does not bypass the required best-effort group cleanup attempt.
ADVERSARIAL_TESTS: Simulate terminate-success + parent-exited-before-wait; taskkill failure; direct kill failure; process already exited but valid PID; malformed/non-positive PID; cleanup subprocess failure. None may trigger a second Codex invocation or alter receipt identity/status semantics.
CLOSE_CONDITIONS: (1) no early success path can skip the required best-effort group/tree cleanup solely because the parent process exited; (2) bounded Windows tree cleanup is mechanically tested; (3) POSIX process-group cleanup semantics satisfy the same invariant; (4) TIMEOUT/INTERRUPTED receipt mapping remains unchanged; (5) targeted E2 + E1 regression suites green; (6) Bridge full repository publication green; (7) final diff remains inside allowed files.
ALLOWED_FILES: src/aios_bridge/executor_transports/codex_local.py; tests/aios_bridge/test_codex_local_transport.py; .ai/results/RESULT-041.md (Bridge-generated only)
FORBIDDEN_SCOPE: bridge.py; continuity executor_transport/executor/lease/dispatch; runtime_dispatch; runtime_lease; failover; hot_handoff; providers; External Brain; docs; E3/E4/E5; H-Series; M11.
```

## Test-Gap Explanation

The existing timeout/interruption unit test monkeypatches `_cleanup_process` with `cleaned.append`, proving that cleanup is called but not proving the production cleanup implementation satisfies the process-tree contract. Therefore the full green suite does not close R1-1.

## Non-Blocking Publication Observation

`RESULT-041.md` lists the executor transport directory and test file but its generated `Diff Stat` is empty. Independent Git comparison establishes the exact four changed paths, so this is a Bridge RESULT reporting limitation and is not an E2 finding.

## Decision

```text
STATUS: CHANGES_REQUIRED
BLOCKING_FINDINGS: 1
HIGH: 1
E2: NOT_YET_PASS
READY_FOR_HUMAN_MERGE: NO
```

Do not rerun or redesign the real transport workflow. Apply only R1-1 under a fresh Human-authorized FIX boundary, republish through Bridge, then request independent review again.
