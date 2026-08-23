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
REVIEWED_TASK_HEAD_SHA: c0cd7d45c2d09318938121e721ff5f2bce2511e9
REVIEWED_BASE_MAIN_SHA: c6bd8943b0e2420391961fe2d3203ec0b65068c9
TASK_ARTIFACT_BLOB_SHA: 6dabbfa8274ac544cdd96b03cc07a8a00b3e31cc
EXECUTOR_ID: antigravity
LIVE_PAID_API_AUTHORIZED: NO

## Reviewed Snapshot

```text
BASE_MAIN_SHA: c6bd8943b0e2420391961fe2d3203ec0b65068c9
BRANCH: ai/task-074
REVIEWED_TASK_HEAD_SHA: c0cd7d45c2d09318938121e721ff5f2bce2511e9
PRE_MERGE_STATUS: AHEAD
PRE_MERGE_AHEAD_BY: 2
PRE_MERGE_BEHIND_BY: 0
PRE_MERGE_MERGE_BASE_SHA: c6bd8943b0e2420391961fe2d3203ec0b65068c9
AUTO_MERGE: BLOCKED
```

Cumulative implementation scope remains exact: `bridge.py`, `src/aios_bridge/executor_transports/__init__.py`, `src/aios_bridge/executor_transports/codex_local.py`, `tests/aios_bridge/test_codex_local_transport.py`, `tests/test_bridge_executor_automation.py`, plus Bridge-generated `.ai/results/RESULT-074.md`.

## Findings

### B1 — BLOCKER / REGRESSION — Normal EXITED_ZERO test-failure semantics were changed

`cmd_execute()` now passes `failure_state="RECOVERY_REQUIRED"` to `cmd_publish()` for both productive-nonzero and normal EXITED_ZERO publication paths. The pre-TASK-074 canonical publisher used `CHANGES_REQUIRED` on a normal implementation whose canonical tests fail, and TASK-074 explicitly requires the normal EXITED_ZERO path to remain unchanged.

Required repair: choose the failure state by transport class. Productive-nonzero canonical-suite failure must use `RECOVERY_REQUIRED`; the normal EXITED_ZERO path must retain its pre-existing test-failure state/behavior. Add regression coverage for both paths.

### B2 — BLOCKER / FAIL-CLOSED — Final productive-nonzero eligibility is still fail-open and not rebound after invocation

`is_productive_nonzero_recovery_candidate()` now accepts `allowed_paths`, `publication_trust_valid`, and `authorization_binding_valid`, but all three are optional/fail-open (`allowed_paths=None`, booleans default `True`). Production then calls the function with literal `publication_trust_valid=True` and `authorization_binding_valid=True` rather than deriving a fresh post-invocation exact authorization/lease/execution-binding proof at the final eligibility boundary.

Required repair: make the final eligibility API fail-closed (no permissive defaults), and mechanically re-read/revalidate the ACTIVE authorization plus exact lease/execution binding after executor return before the productive-nonzero path can be eligible. Scope/trust/binding must be proven facts, not caller assertions.

### B3 — BLOCKER / TOCTOU + TEST COVERAGE — Changed canonical tests are still able to alter publish-relevant state after the first scope/binding checks

The new post-test Git-administration trust reverification is correct, but `cmd_publish()` does not re-collect/revalidate exact dirty scope or revalidate ACTIVE authorization/lease after the canonical repository tests run and immediately before RESULT/Git mutation. Repository tests are code from the candidate worktree; a changed test can therefore create an out-of-scope worktree delta or alter runtime authorization/lease after the earlier checks while leaving protected Git-administration trust unchanged.

The new B1/B2 regression tests also monkeypatch `cmd_publish()` itself, so they do not execute the actual canonical test -> post-test revalidation -> publication boundary.

Required repair: after canonical tests return zero and before RESULT generation / `git add` / commit / push, reverify the captured Git-admin trust, exact current branch/head, exact dirty paths against allowed scope, and exact ACTIVE authorization/lease/execution binding. Add real-path tests that exercise `cmd_publish()` behavior rather than replacing it: one test for productive-nonzero suite failure -> `RECOVERY_REQUIRED`, and one where the test command mutates protected/publish-relevant state and publication is blocked with work preserved.

### B4 — BLOCKER / RESOURCE CONTRACT — Boundary detection reads one additional raw byte outside the 65536-byte analysis budget

For a truncated stream, `_read_bounded_stream()` reads 32768 bytes of head + 32768 bytes of tail, then separately reads the predecessor byte at `tail_start - 1` to decide whether the tail starts on a record boundary. That predecessor byte is raw stream data inspected for semantics, so the actual analyzed/read diagnostic data becomes 65537 bytes for that stream, while ADR-047/TASK-074 lock the total analyzed raw bytes per stream to `<= 65536`.

Required repair: include any boundary-lookbehind byte inside the fixed 65536-byte budget (for example reduce one slice accordingly or use an equivalent bounded representation) and add a test that counts/ proves the total raw bytes inspected for diagnostic analysis never exceeds the locked budget.

## Positive Findings

The FIX correctly improves the tail boundary classification logic, adds post-test Git-admin trust verification, preserves the canonical EXITED_NONZERO receipt, and keeps no-retry/no-reroute/no-second-executor/no-paid-API/no-force-push boundaries. Exact ancestry and writable scope remain clean.

## Validation Evidence

RESULT-074 reports `152 passed` targeted, `2315 passed, 7 skipped, 0 failed` full repository, and a clean `git diff --check`. These suites are green but do not close B1-B4 above.

## Decision

```text
TASK-074: CHANGES_REQUIRED
BLOCKERS_REMAINING: 4
AUTO_MERGE: BLOCKED
MERGED_TO_MAIN: NO
H3_IMPLEMENTATION_AUTHORIZED: NO
LIVE_PAID_API_AUTHORIZED: NO
```

Repair only B1-B4 above. Do not broaden Codex authority, retry/reroute behavior, network access, paid-provider authority, worker-surface authority, or H-Series scope.
