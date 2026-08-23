# REVIEW-074 — Codex Terminal Diagnostic Tail Capture & Productive Nonzero Recovery Hardening

STATUS: CHANGES_REQUIRED
PUBLISHER_PROFILE: CANONICAL_E4
APPROVED: NO
AUTO_MERGE_ELIGIBLE: NO
MERGED_TO_MAIN: NO
AUTO_MERGE_EXECUTED: NO

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/decisions/ADR-032-E4-APPROVED-EXECUTOR-AUTOMATION-AND-AUTO-PUBLICATION-CONTRACT-LOCK.md","blob_sha":"22c300f882327aa812ad5e3250bf53ba8cf85eb5"},{"path":".ai/decisions/ADR-040-CODEX-LOCAL-TRANSPORT-BOUNDED-DIAGNOSTIC-OBSERVABILITY-CONTRACT-LOCK.md","blob_sha":"04937776829675e77a1651152bba16e7e7f31426"},{"path":".ai/decisions/ADR-046-CODEX-E4-IMPLEMENTATION-INTENT-CLEAN-NOOP-RECOVERY-CONTRACT-LOCK.md","blob_sha":"de5b63eb0c23681ec3feb427f44b91d8f44151c0"},{"path":".ai/decisions/ADR-047-CODEX-TERMINAL-DIAGNOSTIC-TAIL-PRODUCTIVE-NONZERO-RECOVERY-CONTRACT-LOCK.md","blob_sha":"dfe872e4e2d6ad021ec0c338ed46d730c3c95c26"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","src/aios_bridge/executor_transports/codex_local.py","src/aios_bridge/executor_transports/__init__.py","tests/aios_bridge/test_codex_local_transport.py","tests/test_bridge_executor_automation.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]}],"operation":"FIX","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

TASK_ID: TASK-074
REVIEWED_TASK_HEAD_SHA: aa552af8fc5f9107e6583026a2736cecd786851f
REVIEWED_BASE_MAIN_SHA: c6bd8943b0e2420391961fe2d3203ec0b65068c9
TASK_ARTIFACT_BLOB_SHA: 6dabbfa8274ac544cdd96b03cc07a8a00b3e31cc
EXECUTOR_ID: antigravity
LIVE_PAID_API_AUTHORIZED: NO

## Reviewed Snapshot

```text
BASE_MAIN_SHA: c6bd8943b0e2420391961fe2d3203ec0b65068c9
BRANCH: ai/task-074
REVIEWED_TASK_HEAD_SHA: aa552af8fc5f9107e6583026a2736cecd786851f
PRE_MERGE_STATUS: AHEAD
PRE_MERGE_AHEAD_BY: 3
PRE_MERGE_BEHIND_BY: 0
PRE_MERGE_MERGE_BASE_SHA: c6bd8943b0e2420391961fe2d3203ec0b65068c9
AUTO_MERGE: BLOCKED
```

Cumulative implementation scope remains exact: `bridge.py`, `src/aios_bridge/executor_transports/__init__.py`, `src/aios_bridge/executor_transports/codex_local.py`, `tests/aios_bridge/test_codex_local_transport.py`, `tests/test_bridge_executor_automation.py`, plus Bridge-generated `.ai/results/RESULT-074.md`.

## Findings

### B1 — BLOCKER / CONTRACT ORDER — Existing exact E4 scope validator still runs after productive-nonzero candidate classification

The latest FIX closes the prior normal EXITED_ZERO state regression, derives fresh post-invocation publication-trust and authorization/lease binding facts, adds post-test trust/branch/HEAD/auth/lease/scope revalidation, and keeps the diagnostic byte-read budget at <= 65536.

One locked ordering requirement remains unmet.

TASK-074 Part C requires the nonzero path to execute:

```text
persist canonical invocation evidence
-> verify protected publication trust
-> observe branch/head/dirty paths
-> exact Git/scope validation
-> if productive-nonzero predicate passes
   canonical full suite / publication
```

The current `cmd_execute()` still calls `is_productive_nonzero_recovery_candidate(...)` first and only afterward calls the existing authoritative `validate_executor_worktree_delta(...)`. The predicate contains a second ad-hoc allowed-path membership check, but that is not the locked existing exact E4 scope validator and therefore can classify a recovery candidate before the authoritative validator has mechanically passed.

Required repair:

- on the `EXITED_NONZERO + CODEX_EXIT_NONZERO + dirty work` path, run the existing `validate_executor_worktree_delta(...)` before final productive-nonzero eligibility can be true;
- bind the predicate/final eligibility to the successful exact-validator result (or make the predicate consume a proven exact-scope fact), rather than duplicating a weaker path-membership validator;
- exact-scope failure -> `RECOVERY_REQUIRED`, no publication, work preserved, no retry/reroute/second executor;
- preserve normal EXITED_ZERO behavior and the post-test revalidation already added;
- add/adjust a regression test proving final productive-nonzero candidate classification cannot occur before the authoritative exact scope validator succeeds.

## Closed Findings

```text
B1_PREVIOUS_NORMAL_EXITED_ZERO_TEST_FAILURE_SEMANTICS: PASS
B2_FRESH_POST_INVOCATION_AUTH_LEASE_TRUST_DERIVATION: PASS
B3_POST_TEST_GIT_ADMIN_BRANCH_HEAD_AUTH_LEASE_DIRTY_SCOPE_REVALIDATION: PASS
B4_TOTAL_DIAGNOSTIC_RAW_BYTES_READ_LE_65536: PASS
TAIL_TERMINAL_EVENT_VISIBILITY: PASS
RAW_OUTPUT_PERSISTED: NO
CANONICAL_RECEIPT_REWRITTEN_TO_ZERO: NO
AUTO_RETRY: NO
AUTO_REROUTE: NO
SECOND_EXECUTOR: NO
PAID_API: NO
FORCE_PUSH: NO
```

## Validation Evidence

RESULT-074 reports:

```text
TARGETED_TESTS: 159 passed, 0 skipped, 0 failed
FULL_REPOSITORY_TESTS: 2322 passed, 7 skipped, 0 failed
GIT_DIFF_CHECK: PASS
```

The suites are green; this review blocker is a contract-order/fail-closed issue not covered by the current assertions.

## Decision

```text
TASK-074: CHANGES_REQUIRED
BLOCKERS_REMAINING: 1
AUTO_MERGE: BLOCKED
MERGED_TO_MAIN: NO
H3_IMPLEMENTATION_AUTHORIZED: NO
LIVE_PAID_API_AUTHORIZED: NO
```

Repair only the remaining scope-order blocker. Do not broaden Codex authority, retry/reroute behavior, network access, paid-provider authority, worker-surface authority, or H-Series scope.