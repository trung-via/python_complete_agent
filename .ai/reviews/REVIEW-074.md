# REVIEW-074 — Codex Terminal Diagnostic Tail Capture & Productive Nonzero Recovery Hardening

STATUS: CHANGES_REQUIRED
PUBLISHER_PROFILE: CANONICAL_E4
APPROVED: NO
AUTO_MERGE_ELIGIBLE: NO
MERGED_TO_MAIN: NO
AUTO_MERGE_EXECUTED: NO

TASK_ID: TASK-074
REVIEWED_TASK_HEAD_SHA: 0b70eb08628d7660c8c0a7657ddef1c4f2262d9d
REVIEWED_BASE_MAIN_SHA: c6bd8943b0e2420391961fe2d3203ec0b65068c9
TASK_ARTIFACT_BLOB_SHA: 6dabbfa8274ac544cdd96b03cc07a8a00b3e31cc
EXECUTOR_ID: antigravity
LIVE_PAID_API_AUTHORIZED: NO

## Reviewed Snapshot

```text
BASE_MAIN_SHA: c6bd8943b0e2420391961fe2d3203ec0b65068c9
BRANCH: ai/task-074
REVIEWED_TASK_HEAD_SHA: 0b70eb08628d7660c8c0a7657ddef1c4f2262d9d
PRE_MERGE_STATUS: AHEAD
PRE_MERGE_AHEAD_BY: 1
PRE_MERGE_BEHIND_BY: 0
PRE_MERGE_MERGE_BASE_SHA: c6bd8943b0e2420391961fe2d3203ec0b65068c9
AUTO_MERGE: BLOCKED
```

Cumulative implementation scope is exact: `bridge.py`, `src/aios_bridge/executor_transports/__init__.py`, `src/aios_bridge/executor_transports/codex_local.py`, `tests/aios_bridge/test_codex_local_transport.py`, `tests/test_bridge_executor_automation.py`, plus Bridge-generated `.ai/results/RESULT-074.md`.

## Findings

### B1 — BLOCKER / HIGH — Productive-nonzero full-suite failure records the wrong operational state

`cmd_execute()` routes a productive nonzero candidate into `cmd_publish()` with the canonical full-suite command. On any test failure, the existing `cmd_publish()` path unconditionally executes:

```text
update_state(task_id, "CHANGES_REQUIRED", "Tests failed; do not publish")
```

ADR-047 / TASK-074 require this specific recovery class to preserve the work and enter `RECOVERY_REQUIRED`, not `CHANGES_REQUIRED`. `CHANGES_REQUIRED` is review semantics and is incorrect when no review artifact was published.

The added test named `test_productive_nonzero_failed_test_suite_does_not_publish_and_enters_recovery` does not exercise the real test-failure path: it replaces `cmd_publish` with a function that immediately raises `SystemExit` and then only asserts one executor invocation. It therefore does not prove the required recovery state or no-publication behavior.

Required repair:

- productive-nonzero canonical full-suite failure -> `RECOVERY_REQUIRED`;
- no commit/push/publication;
- work preserved;
- no retry/reroute/second executor;
- add a test that exercises the actual productive-nonzero publication test-failure path and asserts the state and publication boundary.

### B2 — BLOCKER / HIGH — Publication trust is not reverified after executing changed repository tests

`cmd_execute()` captures the E4 publication-trust snapshot before executor invocation and verifies it immediately after invocation. It then enters `cmd_publish()`, which runs the canonical full repository suite. After that test execution succeeds, there is no second verification of the captured protected Git-administration trust immediately before RESULT generation / Git mutation / commit / push.

TASK-074 explicitly requires publication-trust mismatch to block productive-nonzero publication. Because tests are repository code and may themselves be part of the authorized executor delta, a changed test can mutate protected Git administration after the current trust check but before publication.

Required repair:

- keep the existing pre/post-executor trust check;
- reverify the exact captured E4 publication-trust snapshot after canonical tests return zero and before any publication Git mutation;
- if it drifted: no commit/push, preserve work, `RECOVERY_REQUIRED`, no retry/reroute;
- add regression coverage where canonical test execution mutates a protected Git-admin surface and prove publication is blocked.

### B3 — BLOCKER / CONTRACT — `is_productive_nonzero_recovery_candidate()` is true before the locked eligibility conditions are complete

The new predicate returns true from only transport status/error, branch identity, HEAD identity, and a non-empty dirty set. It does not itself require the exact allowed-scope result, protected-trust validity, or exact active authorization/lease/execution binding that ADR-047 defines as mandatory before a productive-nonzero invocation is eligible for recovery consideration.

The later flow does run the scope validator and `cmd_publish()` revalidates authorization/lease, so current publication remains partly fail-closed. However, the named recovery-candidate classification is broader than the locked contract and its unit test explicitly asserts `True` without those required conditions.

Required repair: either move final productive-nonzero eligibility classification until after all locked conditions are mechanically established, or explicitly make the current function a non-authoritative pre-candidate and introduce/test one final eligibility boundary that cannot be true before exact scope/trust/binding verification.

### B4 — BLOCKER / CORRECTNESS — Tail boundary fragments are still parsed instead of being ignored as fragments

For a truncated tail, `_analyze_diagnostic_stream()` marks the first tail line as a boundary fragment, but `_process_line()` still attempts UTF-8/JSON parsing and accepts it if parsing succeeds. The boundary flag only suppresses `non_json_line_count` when parsing fails.

ADR-047 requires complete NDJSON records only and requires slice-cut boundary fragments to be ignored. Current behavior can falsely accept a syntactically-valid suffix of a cut/mixed-output line as a real event, including a false `error` / `turn.failed`. Conversely, because the first tail line is always marked as a boundary fragment, a genuine malformed complete line is silently ignored when the tail happens to start exactly on a record boundary.

Required repair:

- mechanically distinguish a cut first-tail fragment from a complete first-tail record while keeping total per-stream analysis <= 65536 bytes;
- never parse a proven cut fragment as an event;
- preserve chronological complete-record parsing;
- add adversarial tests for a cut suffix that is syntactically valid JSON and for an exact record-boundary start.

## Positive Findings

```text
EXACT_BASE_ANCESTRY: PASS
AUTHORIZED_SCOPE_ONLY: PASS
HEAD_TAIL_TOTAL_BUDGET_NOT_INCREASED: PASS
TAIL_TURN_FAILED_VISIBLE_IN_COVERED_CASE: PASS
TAIL_ERROR_VISIBLE_IN_COVERED_CASE: PASS
TAIL_TURN_COMPLETED_VISIBLE_IN_COVERED_CASE: PASS
CANONICAL_RECEIPT_EXIT_NONZERO_PRESERVED: PASS
NO_AUTO_RETRY_INTRODUCED: PASS
NO_AUTO_REROUTE_INTRODUCED: PASS
NO_SECOND_EXECUTOR_INTRODUCED: PASS
NO_PAID_API_AUTHORITY_INTRODUCED: PASS
NO_FORCE_PUSH_INTRODUCED: PASS
H_SERIES_CODE_CHANGED: NO
```

## Validation Evidence

RESULT-074 reports:

```text
TARGETED_TESTS: 149 passed
FULL_REPOSITORY_TESTS: 2312 passed, 7 skipped, 0 failed
```

These green suites are useful regression evidence but do not cover B1-B4 above. `git diff --check` evidence is not present in RESULT-074 and must be rerun after the repair together with both required pytest commands.

## Decision

```text
TASK-074: CHANGES_REQUIRED
AUTO_MERGE: BLOCKED
MERGED_TO_MAIN: NO
H3_IMPLEMENTATION_AUTHORIZED: NO
LIVE_PAID_API_AUTHORIZED: NO
```

Repair only the findings above. Do not broaden Codex authority, retry/reroute behavior, network access, paid-provider authority, worker-surface authority, or H-Series scope.