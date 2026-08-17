# RESULT-029: Open Multi-Agent Continuity OS Executor Lease Enforcement (M5)

STATUS: READY_FOR_REVIEW

## Summary
Completed Milestone M5 Open Multi-Agent Continuity OS Executor Lease Enforcement under ADR-010, ADR-018, and ADR-019.
This milestone implements strict vendor-neutral single-active-executor lease ownership (`MAX_ACTIVE_EXECUTORS_PER_TASK = 1`), OS-level atomic filesystem creation (`O_CREAT | O_EXCL`), strict fail-closed active verification, compare-and-release mechanics, and full bridge integration.

## Task Metadata
- Task: `TASK-029`
- Milestone: `M5`
- Action: `RUN`
- Authorized Artifact: `.ai/tasks/TASK-029.md` (`954f5041b9c92e6d28b736455f6829b1f746ec77`)
- Base Main SHA: `de556e5065ab1aea08fc832d2541532fe7085e33`
- Implementation Commit SHA: `580739b1e9daadf6e4cf7a44bb6e39ad77d08b81`
- Target Branch: `ai/task-029`
- Active Runtime Executor: `antigravity`
- Alternate Executors Activated: `0`
- Paid External API Calls: `0`
- Live External Calls: `0`

## Key Implementations
1. **Pure Lease Model (`src/aios_bridge/continuity/lease.py`)**:
   - `MAX_ACTIVE_EXECUTORS_PER_TASK = 1` non-configurable immutable constant.
   - `ExecutorLease` frozen dataclass with schema version `1`, exact task ID validation (`^TASK-\d+$`), exact 64-hex SHA-256 workspace and execution fingerprints, conservative lowercase lease ID (`<= 64` chars), canonical actor ID validation, and strict `ExecutionOperation` domain (`RUN`, `FIX`).
   - Boundary enforcement (`MAX_SERIALIZED_BYTES = 16384`) and safe UTF-8 decoding wrapping in `ContinuityStateValidationError`.
   - `FORBIDDEN_LEASE_KEYS` rejection in `from_dict()` (preventing authority, token, TTL, or secret leakage).
   - `validate_executor_lease_binding()` pure relational 5-tuple validator (`task_id`, `workspace_id`, `executor_id`, `operation`, `execution_fingerprint`).
2. **Public Module Exports (`src/aios_bridge/continuity/__init__.py`)**:
   - Exported `MAX_ACTIVE_EXECUTORS_PER_TASK`, `ExecutorLease`, `validate_executor_lease_binding`.
3. **Atomic Runtime Lease Store (`src/aios_bridge/runtime_lease.py`)**:
   - `AtomicExecutorLeaseStore` using atomic OS create-if-absent (`O_CREAT | O_EXCL | O_WRONLY`) for single-active-executor exclusivity.
   - `acquire()`: atomic creation; collision fails closed with existing owner details.
   - `load_active()`: strict read failing closed on empty, corrupt, mismatched, or oversized active lease files.
   - `require_active()`: strict verification of active lease identity, fingerprint, and binding before execution or mutation.
   - `release()`: atomic compare-and-release moving active lease to `history/RELEASED-<lease_id>-<timestamp>.json`.
4. **Bridge v0.4 Integration (`bridge.py`)**:
   - Added runtime path `leases/` outside worktree.
   - `get_workspace_id()`, `build_execution_fingerprint()`, `build_executor_lease_candidate()`, `get_lease_store()`.
   - Integrated atomic lease acquisition into `cmd_handoff` (RUN & FIX) and `cmd_approve` before recording ACTIVE authorization with rollback on failure.
   - Integrated strict lease gate into `cmd_publish`: requires active lease before test execution/mutation, retains lease on failure, releases lease after remote push success.
   - Added `lease-status` and `lease-release` (with `--confirm-stopped` flag) for human recovery.
5. **Comprehensive Test Suites**:
   - `tests/aios_bridge/continuity/test_lease.py`: 13 pure unit tests covering schema, bounds, invariants, UTF-8 wrapping, and binding validators.
   - `tests/aios_bridge/test_runtime_lease.py`: 7 tests covering atomic create, 2-store concurrent race linearization, corrupt/empty/oversized fail-closed, require_active, and compare-and-release.
   - `tests/test_bridge.py`: 29 tests updated and expanded with M5 lease lifecycle and recovery tests.

## Primary Brain Adversarial Checklist Self-Audit
- [x] **C1 / C2**: `MAX_ACTIVE_EXECUTORS_PER_TASK = 1` invariant explicit in models and store.
- [x] **C3 / C4**: `ExecutorLease` schema validated, frozen, bounded to 16 KiB, forbidden authority/secret/timing keys rejected.
- [x] **C5 / C6**: `workspace_id` is exact 64-hex SHA-256 (no raw filesystem paths in lease); `execution_fingerprint` binds 7 activation parameters.
- [x] **C7**: `validate_executor_lease_binding` tests fail closed on all 5 dimension mismatches.
- [x] **C8 / C9**: `AtomicExecutorLeaseStore` uses `O_CREAT | O_EXCL` and proves concurrent race linearization with 2 independent stores.
- [x] **C10**: Corrupt/empty/oversized active lease files fail closed without auto-repair or overwrite.
- [x] **C11 / C22**: `release()` strictly validates active lease before atomic rename to history; stale release attempts rejected.
- [x] **C16 / C17**: `cmd_handoff` (RUN/FIX) and `cmd_approve` acquire lease before saving ACTIVE authorization with rollback.
- [x] **C20 / C21**: `cmd_publish` requires active lease before test execution; retains lease on test/commit failure; releases lease only after push success.
- [x] **C23**: `lease-status` and `lease-release` commands provided with confirmation gate.
- [x] **C26**: `PreparedExecution != ExecutorLease` strictly tested.
- [x] **C27**: Zero paid external API calls, zero mock drift, single active executor `antigravity`.

## Test Evidence
### Focused Test Suite (`test_lease.py`, `test_runtime_lease.py`, `test_bridge.py`)
```text
============================= test session starts =============================
platform win32 -- Python 3.14.7, pytest-8.3.4, pluggy-1.6.0 -- C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: c:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent
plugins: anyio-4.14.2, asyncio-0.25.0
asyncio: mode=Mode.STRICT, asyncio_default_fixture_loop_scope=None
collecting ... collected 49 items

tests/aios_bridge/continuity/test_lease.py::test_max_active_executors_invariant PASSED [  2%]
tests/aios_bridge/continuity/test_lease.py::test_executor_lease_valid_construction_and_fingerprint PASSED [  4%]
tests/aios_bridge/continuity/test_lease.py::test_executor_lease_whitespace_and_casing_rejection PASSED [  6%]
tests/aios_bridge/continuity/test_lease.py::test_executor_lease_forbidden_authority_and_ttl_keys_fail_closed PASSED [  8%]
tests/aios_bridge/continuity/test_lease.py::test_executor_lease_operation_domain PASSED [ 10%]
tests/aios_bridge/continuity/test_lease.py::test_prepared_execution_distinct_from_executor_lease PASSED [ 12%]
tests/aios_bridge/continuity/test_lease.py::test_validate_executor_lease_binding_success PASSED [ 14%]
tests/aios_bridge/continuity/test_lease.py::test_validate_executor_lease_binding_mismatches PASSED [ 16%]
tests/aios_bridge/continuity/test_lease.py::test_unknown_fields_rejected PASSED [ 18%]
tests/aios_bridge/continuity/test_lease.py::test_missing_required_fields_rejected PASSED [ 20%]
tests/aios_bridge/continuity/test_lease.py::test_oversized_payload_rejected_in_from_json PASSED [ 22%]
tests/aios_bridge/continuity/test_lease.py::test_malformed_json_wraps_continuity_error PASSED [ 24%]
tests/aios_bridge/continuity/test_lease.py::test_invalid_utf8_bytes_wrapped_in_from_json PASSED [ 26%]
tests/aios_bridge/test_runtime_lease.py::test_atomic_lease_store_acquire_and_load_active PASSED [ 28%]
tests/aios_bridge/test_runtime_lease.py::test_atomic_lease_store_acquire_conflict_fails_closed PASSED [ 30%]
tests/aios_bridge/test_runtime_lease.py::test_atomic_lease_store_workspace_mismatch_fails_closed PASSED [ 32%]
tests/aios_bridge/test_runtime_lease.py::test_atomic_lease_store_concurrent_race_linearization PASSED [ 34%]
tests/aios_bridge/test_runtime_lease.py::test_corrupt_empty_and_oversized_active_file_blocks_and_fails_closed PASSED [ 36%]
tests/aios_bridge/test_runtime_lease.py::test_require_active_validation PASSED [ 38%]
tests/aios_bridge/test_runtime_lease.py::test_compare_and_release_lifecycle PASSED [ 40%]
tests/test_bridge.py::test_runtime_state_path_is_outside_repository_worktree PASSED [ 42%]
tests/test_bridge.py::test_sync_does_not_dirty_worktree_and_provides_context PASSED [ 44%]
tests/test_bridge.py::test_changes_required_review_creates_pending_review_event PASSED [ 46%]
tests/test_bridge.py::test_repeated_changes_required_updates_do_not_create_duplicate_pending_events PASSED [ 48%]
tests/test_bridge.py::test_review_update_to_approved_clears_pending_and_sets_approved_state PASSED [ 51%]
tests/test_bridge.py::test_missing_or_unknown_review_status_is_non_actionable PASSED [ 53%]
tests/test_bridge.py::test_handoff_run_without_preexisting_pending_event_records_active_auth_and_creates_branch PASSED [ 55%]
tests/test_bridge.py::test_handoff_run_missing_task_fails_closed PASSED  [ 57%]
tests/test_bridge.py::test_reconcile_local_main_fast_forwards_when_behind PASSED [ 59%]
tests/test_bridge.py::test_reconcile_local_main_fails_closed_when_diverged_or_ahead PASSED [ 61%]
tests/test_bridge.py::test_dirty_worktree_blocks_handoff_and_reconciliation PASSED [ 63%]
tests/test_bridge.py::test_handoff_fix_succeeds_only_for_changes_required_and_binds_exact_blob PASSED [ 65%]
tests/test_bridge.py::test_handoff_fix_fails_closed_when_approved_or_missing_or_unknown_status PASSED [ 67%]
tests/test_bridge.py::test_publish_enforces_active_authorization_and_detects_control_drift PASSED [ 69%]
tests/test_bridge.py::test_publish_consumes_active_authorization_and_creates_result_with_test_evidence PASSED [ 71%]
tests/test_bridge.py::test_publish_preserves_active_authorization_when_tests_fail PASSED [ 73%]
tests/test_bridge.py::test_watcher_notifications_v040_instruct_aios_worker_command PASSED [ 75%]
tests/test_bridge.py::test_popup_notification_failure_does_not_break_sync_or_checkpoint PASSED [ 77%]
tests/test_bridge.py::test_watcher_retries_after_fetch_auth_network_error PASSED [ 79%]
tests/test_bridge.py::test_utf8_output_and_path_handling_remains_functional PASSED [ 81%]
tests/test_bridge.py::test_publish_fails_closed_when_only_legacy_approval_exists_and_no_active_authorization PASSED [ 83%]
tests/test_bridge.py::test_existing_task_branch_resume_fails_when_local_ahead_of_remote PASSED [ 85%]
tests/test_bridge.py::test_existing_task_branch_resume_fails_when_local_and_remote_diverged PASSED [ 87%]
tests/test_bridge.py::test_existing_task_branch_resume_fast_forwards_when_local_strictly_behind PASSED [ 89%]
tests/test_bridge.py::test_publish_fails_when_active_run_auth_has_changes_required_review_on_control PASSED [ 91%]
tests/test_bridge.py::test_publish_fails_when_action_argument_mismatches_active_authorization PASSED [ 93%]
tests/test_bridge.py::test_handoff_run_fails_when_task_artifact_is_malformed PASSED [ 95%]
tests/test_bridge.py::test_handoff_run_acquires_lease_and_second_handoff_conflicts PASSED [ 97%]
tests/test_bridge.py::test_lease_status_and_confirmation_gated_release PASSED [100%]

============================== warnings summary ===============================
tests/aios_bridge/continuity/test_lease.py::test_max_active_executors_invariant
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:1153: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    return asyncio.get_event_loop_policy()

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================= 49 passed, 1 warning in 10.76s ========================

C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:207: PytestDeprecationWarning: The configuration option "asyncio_default_fixture_loop_scope" is unset.
The event loop scope for asynchronous fixtures will default to the fixture caching scope. Future versions of pytest-asyncio will default the loop scope for asynchronous fixtures to function scope. Set the default fixture loop scope explicitly in order to avoid unexpected behavior in the future. Valid fixture loop scopes are: "function", "class", "module", "package", "session"

  warnings.warn(PytestDeprecationWarning(_DEFAULT_FIXTURE_LOOP_SCOPE_UNSET))
```

### Full Repository Test Suite (`pytest tests/ -q -W ignore`)
```text
........................................................................ [ 10%]
........................................................................ [ 20%]
........................................................................ [ 31%]
........................................................................ [ 41%]
........................................................................ [ 51%]
........................................................................ [ 62%]
........................................................................ [ 72%]
........................................................................ [ 82%]
........................................................................ [ 93%]
................................................                         [100%]
696 passed in 60.34s (0:01:00)

C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:207: PytestDeprecationWarning: The configuration option "asyncio_default_fixture_loop_scope" is unset.
The event loop scope for asynchronous fixtures will default to the fixture caching scope. Future versions of pytest-asyncio will default the loop scope for asynchronous fixtures to function scope. Set the default fixture loop scope explicitly in order to avoid unexpected behavior in the future. Valid fixture loop scopes are: "function", "class", "module", "package", "session"

  warnings.warn(PytestDeprecationWarning(_DEFAULT_FIXTURE_LOOP_SCOPE_UNSET))
```

## Diff Stat
```text
bridge.py                                  | 358 ++++++++++++++++++++++++++++-
 src/aios_bridge/continuity/__init__.py     |   8 +
 src/aios_bridge/continuity/lease.py        | 290 +++++++++++++++++++++++
 src/aios_bridge/runtime_lease.py           | 215 +++++++++++++++++
 tests/aios_bridge/continuity/test_lease.py | 266 +++++++++++++++++++++
 tests/aios_bridge/test_runtime_lease.py    | 214 +++++++++++++++++
 tests/test_bridge.py                       | 235 +++++++++++++++++++
 7 files changed, 1575 insertions(+), 11 deletions(-)
```

## Published At
2026-08-17T00:19:46.910597+00:00
