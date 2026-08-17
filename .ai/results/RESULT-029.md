# RESULT-029: Open Multi-Agent Continuity OS Executor Lease Enforcement (M5)

STATUS: READY_FOR_REVIEW

## Review Manifest
```yaml
TASK_ID: TASK-029
ACTION: FIX
BASE_SHA: de556e5065ab1aea08fc832d2541532fe7085e33
IMPLEMENTATION_SHA: 1ffebb3c58f1f4d1647c8372d13278ecdc1c559f
PREVIOUS_REVIEW_SHA: 682f8436c43dcdc73bb048c10732f34f1b2445b9
REVIEW_ROUND: 1
M5_EXECUTOR_LEASE: PASS
COMPARE_AND_RELEASE: PASS
BRIDGE_V0_4_BEHAVIOR_CHANGED: YES — ADR-019-authorized M5 lease gate only
AUTHORITY_WIDENED: NO
ACTIVE_RUNTIME_EXECUTOR: antigravity
ALTERNATE_EXECUTORS_ACTIVATED: 0
LIVE_EXTERNAL_CALLS: 0
PAID_EXTERNAL_API_CALLS: 0
TOTAL_REPO_TESTS: 703
FOCUSED_TESTS: 56
```

## Summary
Resolved all Round 1 review findings (R1-1 through R1-5) from `REVIEW-029.md` on `ai/task-029`:
- **R1-1 (TOCTOU race in release)**: Implemented cross-thread and cross-process `_task_mutation_guard` in `AtomicExecutorLeaseStore` using in-process `threading.RLock` per task and OS file locking (`msvcrt.locking` on Windows / `fcntl.flock` on POSIX). Both `acquire()` and `release()` are synchronized under this guard. Stale releases are strictly rejected and cannot remove newly acquired leases.
- **R1-2 (Failed-writer cleanup safety)**: `acquire()` now tracks `created_by_this_call = False` and sets it to `True` only after exclusive creation succeeds. Cleanup on exception targets `ACTIVE.json` only when `created_by_this_call` is `True`, ensuring existing leases are never deleted by a failed contender.
- **R1-3 (Durable complete write & fsync)**: `acquire()` now implements a write-all loop verifying all canonical JSON bytes are written, and strictly executes `os.fsync(fd)`, failing closed on any I/O or fsync failure.
- **R1-4 (`cmd_approve()` ordering & retryability)**: `cmd_approve()` now acquires the executor lease BEFORE mutating the inbox event or operational state. If lease acquisition conflicts or fails, the inbox event remains `PENDING` and state is untouched, ensuring the approval remains fully retryable.
- **R1-5 (Adversarial test evidence & manifest)**: Added comprehensive unit and fault-injection tests in `tests/aios_bridge/test_runtime_lease.py` and `tests/test_bridge.py` covering stale release race prevention, failed-writer cleanup safety, write/fsync fault injection, `cmd_approve` conflict retryability, and lease retention on test/commit/push failure. Formally structured RESULT-029 Review Manifest.

## Task Metadata
- Task: `TASK-029`
- Milestone: `M5`
- Action: `FIX`
- Authorized Artifact: `.ai/reviews/REVIEW-029.md` (`abc8357b8b7adfd315f6c6cc255e2f2e2b718c6a`)
- Base Main SHA: `de556e5065ab1aea08fc832d2541532fe7085e33`
- Implementation Commit SHA: `1ffebb3c58f1f4d1647c8372d13278ecdc1c559f`
- Target Branch: `ai/task-029`
- Active Runtime Executor: `antigravity`
- Alternate Executors Activated: `0`
- Paid External API Calls: `0`
- Live External Calls: `0`

## Round 1 Findings Resolution Audit
- [x] **R1-1**: Implemented `_task_mutation_guard(task_dir, task_id)` wrapping `acquire()` and `release()`. Added `test_compare_and_release_interleaving_race_prevents_stale_release_removing_new_lease`.
- [x] **R1-2**: Added `created_by_this_call` state tracking in `acquire()`. Added `test_failed_writer_cleanup_safety_when_open_fails` and `test_failed_writer_cleanup_only_removes_own_created_file_on_write_error`.
- [x] **R1-3**: Implemented write-all loop and strict `os.fsync(fd)` validation. Added `test_partial_write_fault_injection_fails_closed` and `test_fsync_failure_fault_injection_fails_closed`.
- [x] **R1-4**: Reordered `cmd_approve()` in `bridge.py` to acquire lease before modifying inbox event or operational state. Added `test_cmd_approve_lease_conflict_preserves_pending_event_and_state`.
- [x] **R1-5**: Added missing lifecycle tests (test failure, commit failure, push failure lease retention in `test_publish_commit_and_push_failure_retains_exact_lease`) and generated formal Review Manifest.

## Test Evidence
### Focused Test Suite (`test_lease.py`, `test_runtime_lease.py`, `test_bridge.py`)
```text
============================= test session starts =============================
platform win32 -- Python 3.14.7, pytest-8.3.4, pluggy-1.6.0 -- C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: c:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent
plugins: anyio-4.14.2, asyncio-0.25.0
asyncio: mode=Mode.STRICT, asyncio_default_fixture_loop_scope=None
collecting ... collected 56 items

tests/aios_bridge/continuity/test_lease.py::test_max_active_executors_invariant PASSED [  1%]
tests/aios_bridge/continuity/test_lease.py::test_executor_lease_valid_construction_and_fingerprint PASSED [  3%]
tests/aios_bridge/continuity/test_lease.py::test_executor_lease_whitespace_and_casing_rejection PASSED [  5%]
tests/aios_bridge/continuity/test_lease.py::test_executor_lease_forbidden_authority_and_ttl_keys_fail_closed PASSED [  7%]
tests/aios_bridge/continuity/test_lease.py::test_executor_lease_operation_domain PASSED [  8%]
tests/aios_bridge/continuity/test_lease.py::test_prepared_execution_distinct_from_executor_lease PASSED [ 10%]
tests/aios_bridge/continuity/test_lease.py::test_validate_executor_lease_binding_success PASSED [ 12%]
tests/aios_bridge/continuity/test_lease.py::test_validate_executor_lease_binding_mismatches PASSED [ 14%]
tests/aios_bridge/continuity/test_lease.py::test_unknown_fields_rejected PASSED [ 16%]
tests/aios_bridge/continuity/test_lease.py::test_missing_required_fields_rejected PASSED [ 17%]
tests/aios_bridge/continuity/test_lease.py::test_oversized_payload_rejected_in_from_json PASSED [ 19%]
tests/aios_bridge/continuity/test_lease.py::test_malformed_json_wraps_continuity_error PASSED [ 21%]
tests/aios_bridge/continuity/test_lease.py::test_invalid_utf8_bytes_wrapped_in_from_json PASSED [ 23%]
tests/aios_bridge/test_runtime_lease.py::test_atomic_lease_store_acquire_and_load_active PASSED [ 25%]
tests/aios_bridge/test_runtime_lease.py::test_atomic_lease_store_acquire_conflict_fails_closed PASSED [ 26%]
tests/aios_bridge/test_runtime_lease.py::test_atomic_lease_store_workspace_mismatch_fails_closed PASSED [ 28%]
tests/aios_bridge/test_runtime_lease.py::test_atomic_lease_store_concurrent_race_linearization PASSED [ 30%]
tests/aios_bridge/test_runtime_lease.py::test_corrupt_empty_and_oversized_active_file_blocks_and_fails_closed PASSED [ 32%]
tests/aios_bridge/test_runtime_lease.py::test_require_active_validation PASSED [ 33%]
tests/aios_bridge/test_runtime_lease.py::test_compare_and_release_lifecycle PASSED [ 35%]
tests/aios_bridge/test_runtime_lease.py::test_compare_and_release_interleaving_race_prevents_stale_release_removing_new_lease PASSED [ 37%]
tests/aios_bridge/test_runtime_lease.py::test_failed_writer_cleanup_safety_when_open_fails PASSED [ 39%]
tests/aios_bridge/test_runtime_lease.py::test_failed_writer_cleanup_only_removes_own_created_file_on_write_error PASSED [ 41%]
tests/aios_bridge/test_runtime_lease.py::test_partial_write_fault_injection_fails_closed PASSED [ 42%]
tests/aios_bridge/test_runtime_lease.py::test_fsync_failure_fault_injection_fails_closed PASSED [ 44%]
tests/test_bridge.py::test_runtime_state_path_is_outside_repository_worktree PASSED [ 46%]
tests/test_bridge.py::test_sync_does_not_dirty_worktree_and_provides_context PASSED [ 48%]
tests/test_bridge.py::test_changes_required_review_creates_pending_review_event PASSED [ 50%]
tests/test_bridge.py::test_repeated_changes_required_updates_do_not_create_duplicate_pending_events PASSED [ 51%]
tests/test_bridge.py::test_review_update_to_approved_clears_pending_and_sets_approved_state PASSED [ 53%]
tests/test_bridge.py::test_missing_or_unknown_review_status_is_non_actionable PASSED [ 55%]
tests/test_bridge.py::test_handoff_run_without_preexisting_pending_event_records_active_auth_and_creates_branch PASSED [ 57%]
tests/test_bridge.py::test_handoff_run_missing_task_fails_closed PASSED  [ 58%]
tests/test_bridge.py::test_reconcile_local_main_fast_forwards_when_behind PASSED [ 60%]
tests/test_bridge.py::test_reconcile_local_main_fails_closed_when_diverged_or_ahead PASSED [ 62%]
tests/test_bridge.py::test_dirty_worktree_blocks_handoff_and_reconciliation PASSED [ 64%]
tests/test_bridge.py::test_handoff_fix_succeeds_only_for_changes_required_and_binds_exact_blob PASSED [ 66%]
tests/test_bridge.py::test_handoff_fix_fails_closed_when_approved_or_missing_or_unknown_status PASSED [ 67%]
tests/test_bridge.py::test_publish_enforces_active_authorization_and_detects_control_drift PASSED [ 69%]
tests/test_bridge.py::test_publish_consumes_active_authorization_and_creates_result_with_test_evidence PASSED [ 71%]
tests/test_bridge.py::test_publish_preserves_active_authorization_when_tests_fail PASSED [ 73%]
tests/test_bridge.py::test_watcher_notifications_v040_instruct_aios_worker_command PASSED [ 75%]
tests/test_bridge.py::test_popup_notification_failure_does_not_break_sync_or_checkpoint PASSED [ 76%]
tests/test_bridge.py::test_watcher_retries_after_fetch_auth_network_error PASSED [ 78%]
tests/test_bridge.py::test_utf8_output_and_path_handling_remains_functional PASSED [ 80%]
tests/test_bridge.py::test_publish_fails_closed_when_only_legacy_approval_exists_and_no_active_authorization PASSED [ 82%]
tests/test_bridge.py::test_existing_task_branch_resume_fails_when_local_ahead_of_remote PASSED [ 83%]
tests/test_bridge.py::test_existing_task_branch_resume_fails_when_local_and_remote_diverged PASSED [ 85%]
tests/test_bridge.py::test_existing_task_branch_resume_fast_forwards_when_local_strictly_behind PASSED [ 87%]
tests/test_bridge.py::test_publish_fails_when_active_run_auth_has_changes_required_review_on_control PASSED [ 89%]
tests/test_bridge.py::test_publish_fails_when_action_argument_mismatches_active_authorization PASSED [ 91%]
tests/test_bridge.py::test_handoff_run_fails_when_task_artifact_is_malformed PASSED [ 92%]
tests/test_bridge.py::test_handoff_run_acquires_lease_and_second_handoff_conflicts PASSED [ 94%]
tests/test_bridge.py::test_lease_status_and_confirmation_gated_release PASSED [ 96%]
tests/test_bridge.py::test_cmd_approve_lease_conflict_preserves_pending_event_and_state PASSED [ 98%]
tests/test_bridge.py::test_publish_commit_and_push_failure_retains_exact_lease PASSED [100%]

============================== warnings summary ===============================
tests/aios_bridge/continuity/test_lease.py::test_max_active_executors_invariant
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:1153: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    return asyncio.get_event_loop_policy()

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================= 56 passed, 1 warning in 11.01s ========================

C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:207: PytestDeprecationWarning: The configuration option "asyncio_default_fixture_loop_scope" is unset.
The event loop scope for asynchronous fixtures will default to the fixture caching scope. Future versions of pytest-asyncio will default the loop scope for asynchronous fixtures to function scope. Set the default fixture loop scope explicitly in order to avoid unexpected behavior in the future. Valid fixture loop scopes are: "function", "class", "module", "package", "session"

  warnings.warn(PytestDeprecationWarning(_DEFAULT_FIXTURE_LOOP_SCOPE_UNSET))
```

### Full Repository Test Suite (`pytest tests/ -q -W ignore`)
```text
........................................................................ [ 10%]
........................................................................ [ 20%]
........................................................................ [ 30%]
........................................................................ [ 40%]
........................................................................ [ 51%]
........................................................................ [ 61%]
........................................................................ [ 71%]
........................................................................ [ 81%]
........................................................................ [ 92%]
.......................................................                  [100%]
703 passed in 57.41s

C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:207: PytestDeprecationWarning: The configuration option "asyncio_default_fixture_loop_scope" is unset.
The event loop scope for asynchronous fixtures will default to the fixture caching scope. Future versions of pytest-asyncio will default the loop scope for asynchronous fixtures to function scope. Set the default fixture loop scope explicitly in order to avoid unexpected behavior in the future. Valid fixture loop scopes are: "function", "class", "module", "package", "session"

  warnings.warn(PytestDeprecationWarning(_DEFAULT_FIXTURE_LOOP_SCOPE_UNSET))
```

## Diff Stat vs Base Main (`de556e5065ab1aea08fc832d2541532fe7085e33`)
```text
.ai/results/RESULT-029.md                  | 170 +++++++++++
 bridge.py                                  | 364 ++++++++++++++++++++++-
 src/aios_bridge/continuity/__init__.py     |   8 +
 src/aios_bridge/continuity/lease.py        | 290 ++++++++++++++++++
 src/aios_bridge/runtime_lease.py           | 290 ++++++++++++++++++
 tests/aios_bridge/continuity/test_lease.py | 266 +++++++++++++++++
 tests/aios_bridge/test_runtime_lease.py    | 339 +++++++++++++++++++++
 tests/test_bridge.py                       | 459 +++++++++++++++++++++++++++++
 8 files changed, 2173 insertions(+), 13 deletions(-)
```

## Published At
2026-08-17T01:44:56.039023+00:00
