# REVIEW-045 — E2.1 Codex CLI Argument Compatibility Fix

STATUS: PASS
APPROVED: YES
READY_FOR_HUMAN_MERGE: YES
MERGE_AUTHORIZED: YES
MERGED_TO_MAIN: YES

## Authoritative Anchors

```text
TASK_ID: TASK-045
MILESTONE: E2.1 — Codex CLI Argument Compatibility Fix
BASELINE_MAIN_SHA: a01b5f4b028ccdc416004b3d25608d23fb922c51
TASK_BRANCH: ai/task-045
FINAL_REVIEWED_TASK_HEAD_SHA: 7b4e8bbe1322c0e26338071ca3be7bf08a3144ec

TASK_BLOB_SHA: ee9042adb35b0e0e5d5907b4b3e6c8703fad4811
ADR_034_BLOB_SHA: cbe66ff7ae5db159ed96c0310f1271d9527d3bae
BLUEPRINT_BLOB_SHA: 783ddad9ff55db166d4091fbd75b6f34d2f8075c
RESULT_045_BLOB_SHA: 7a19c205f8ca7a29d14a4f618f4994070d499e22
CODEX_LOCAL_BLOB_SHA: b3a2c29fae7acab549bf26d0c621117923037375
CODEX_LOCAL_TEST_BLOB_SHA: 57a489182d2f3195a84d15de33013b914ba1bd73
```

Fresh lineage before merge:

```text
main -> ai/task-045
STATUS: ahead
AHEAD: 1
BEHIND: 0
MERGE_BASE: a01b5f4b028ccdc416004b3d25608d23fb922c51
FAST_FORWARD_LINEAGE: YES
```

Fresh final drift check before merge:

```text
7b4e8bbe1322c0e26338071ca3be7bf08a3144ec -> ai/task-045
STATUS: identical
AHEAD: 0
BEHIND: 0
```

## Scope Audit

Repository-wide TASK-045 delta is exactly:

```text
.ai/results/RESULT-045.md                       # Bridge-generated
src/aios_bridge/executor_transports/codex_local.py
tests/aios_bridge/test_codex_local_transport.py
```

No bridge.py, continuity, E3, E4, dispatch, lease, proof, M11, or H-Series files changed.

SCOPE_AUDIT: PASS

## Production Contract Audit

`_build_codex_argv()` now returns exactly:

```text
executable
--ask-for-approval
never
exec
--ephemeral
--json
--color
never
--sandbox
workspace-write
-c
sandbox_workspace_write.network_access=false
-c
web_search="disabled"
-C
workspace
-
```

The only production semantic delta is moving the existing `--ask-for-approval never` pair across the `exec` parser boundary. No argv element was added or removed and the remaining order is unchanged.

```text
ROOT_CAUSE_LOCALIZED_TO_E2_ARGV: PASS
GLOBAL_APPROVAL_FLAG_BEFORE_EXEC: PASS
APPROVAL_FLAG_EXACTLY_ONCE: PASS
ALL_OTHER_ARGV_ELEMENTS_UNCHANGED: PASS
TRANSPORT_ID_UNCHANGED: PASS
```

No changes were made to workspace/Git preflight, executable resolution, shell mode, stdin payload delivery, stdout/stderr discard policy, child environment, secret denylist, timeout/interrupt cleanup, receipt mapping, retry/fallback semantics, or authority boundaries.

## Regression Test Audit

The existing exact argv/process-contract test now mechanically requires:

```text
argv.count("--ask-for-approval") == 1
argv.index("--ask-for-approval") == 1
argv[1:3] == ["--ask-for-approval", "never"]
argv.index("exec") == 3
argv.index("--ask-for-approval") < argv.index("exec")
```

while retaining full exact-list equality and the existing assertions for one spawn, shell=False, stdin PIPE, stdout/stderr DEVNULL, unchanged payload bytes, environment handling, preflight failure, exit-status mapping, timeout/interruption, and process cleanup.

No real Codex subprocess test was added.

REGRESSION_LOCK: PASS

## Full Repository Gate

Bridge publication reports:

```text
Command: .\venv\Scripts\python.exe -m pytest tests/ -q
Exit code: 0
1437 passed, 7 skipped, 1533 warnings in 134.37s
```

The full suite includes the TASK-045 targeted test files and therefore independently exercises the modified transport test together with E1/E3/E4 surrounding tests.

```text
TARGETED_TEST_CONTRACTS_COVERED_BY_FULL_SUITE: PASS
FULL_REPO_TESTS: PASS
REGRESSIONS_OBSERVED: 0
```

## Authority / Boundary Audit

```text
HUMAN_AUTHORITY_UNCHANGED: PASS
AUTOMATIC_APPROVAL_ADDED: NO
AUTOMATIC_EXECUTOR_SELECTION_ADDED: NO
RETRY_ADDED: NO
FALLBACK_ADDED: NO
OUTPUT_CAPTURE_ADDED: NO
RUNTIME_CLI_PROBING_ADDED: NO
E1_CHANGED: NO
E3_CHANGED: NO
E4_CHANGED: NO
M11_IMPLEMENTED: NO
H_SERIES_ACTIVATED: NO
TASK_044_RETRIED_OR_PUBLISHED: NO_EVIDENCE_IN_TASK_045_DELTA
```

TASK-044 remains a failed E5 proof and is not converted into PASS by this fix.

## Merge Event

Human explicitly authorized merge with command `Merge TASK-045`.

Fresh preflight immediately before ref update proved:

```text
main -> ai/task-045
STATUS: ahead
AHEAD: 1
BEHIND: 0
BASE_MAIN_SHA: a01b5f4b028ccdc416004b3d25608d23fb922c51
MERGE_BASE: a01b5f4b028ccdc416004b3d25608d23fb922c51
EXACT_REVIEWED_HEAD -> ai/task-045: identical
```

GitHub `main` was then fast-forwarded with `force=false` to the exact reviewed head:

```text
7b4e8bbe1322c0e26338071ca3be7bf08a3144ec
```

Fresh post-merge branch verification proved `main` is exactly that SHA and its parent is the locked baseline main SHA.

## Final Decision

```text
BLOCKING_FINDINGS: 0
ROOT_CAUSE_LOCALIZED: PASS
GLOBAL_APPROVAL_FLAG_BEFORE_EXEC: PASS
APPROVAL_FLAG_EXACTLY_ONCE: PASS
ALL_OTHER_ARGV_UNCHANGED: PASS
PAYLOAD_BYTES_UNCHANGED: PASS
ONE_SPAWN: PASS
SHELL_FALSE: PASS
CLOSED_ENVIRONMENT: PASS
NO_RETRY: PASS
NO_FALLBACK: PASS
RECEIPT_SEMANTICS_UNCHANGED: PASS
E1_E3_E4_UNCHANGED: PASS
HUMAN_AUTHORITY_UNCHANGED: PASS
FULL_REPO_TESTS: PASS
REGRESSIONS: 0
FINAL_INDEPENDENT_AUDIT: PASS
E2_1: PASS
STATUS: PASS
APPROVED: YES
READY_FOR_HUMAN_MERGE: YES
MERGE_AUTHORIZED: YES
MERGED_TO_MAIN: YES
```

TASK-045 is accepted and merged at exact reviewed head `7b4e8bbe1322c0e26338071ca3be7bf08a3144ec`.

E5 must restart with a fresh task number and fresh challenge values; TASK-044 must not be reused as successful E5 evidence.
