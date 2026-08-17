# RESULT-029: Open Multi-Agent Continuity OS Executor Lease Enforcement (M5)

STATUS: READY_FOR_REVIEW

## Review Manifest
```yaml
TASK_ID: TASK-029
ACTION: FIX
BASE_SHA: de556e5065ab1aea08fc832d2541532fe7085e33
IMPLEMENTATION_SHA: bb84e0facb6b24d4c5fdd0eb636b45b9d89ab0b5
PREVIOUS_REVIEW_SHA: 1b975d9972fee5a929de6374f7aee9740b47ba09
REVIEW_ROUND: 4
M5_EXECUTOR_LEASE: PASS
MAX_ACTIVE_EXECUTORS_PER_TASK: 1
CANONICAL_EXECUTOR_LEASE: PASS
ATOMIC_CREATE_IF_ABSENT: PASS
RACE_EXACTLY_ONE_WINNER: PASS
COMPARE_AND_RELEASE: PASS
CORRUPT_ACTIVE_FAIL_CLOSED: PASS
HANDOFF_RUN_LEASE_GATE: PASS
HANDOFF_FIX_LEASE_GATE: PASS
LEGACY_APPROVE_LEASE_GATE: PASS
PUBLISH_REQUIRES_LEASE: PASS
SUCCESSFUL_PUBLISH_RELEASES_LEASE: PASS
TEST_FAILURE_RETAINS_LEASE: PASS
HUMAN_RECOVERY_RELEASE: PASS
EXECUTOR_FAILOVER_ADDED: NO
LEASE_TTL_OR_HEARTBEAT_ADDED: NO
LEASE_STEAL_ADDED: NO
DISPATCH_ROUTER_ADDED: NO
BRIDGE_V0_4_BEHAVIOR_CHANGED: YES — ADR-019-authorized M5 lease gate only
AUTHORITY_WIDENED: NO
ACTIVE_RUNTIME_EXECUTOR: antigravity
ALTERNATE_EXECUTORS_ACTIVATED: 0
LIVE_EXTERNAL_CALLS: 0
PAID_EXTERNAL_API_CALLS: 0
REGRESSIONS: 0
EXECUTOR_RUNS: 1
EXECUTOR_FIX_RUNS: 4
FOCUSED_LEASE_TESTS: 13/13 passed
RUNTIME_LEASE_TESTS: 14/14 passed
BRIDGE_TESTS: 36/36 passed
CONTINUITY_TESTS: 127/127 passed
FULL_REPO_TESTS: 710/710 passed
```

## Summary
Resolved all Round 4 review findings (R1-1 and R2-1) from `REVIEW-029.md` on `ai/task-029`:
- **R1-1 (Deterministic Lock Probe TOCTOU Proof with Zero Sleep / No Scheduler Delay Assumption)**: Replaced the sleep-based assertion in `test_deterministic_compare_and_release_toctou_interleaving_proof` with direct non-blocking probes on the in-process `threading.RLock` (`acquire(blocking=False) == False`) and the OS file lock (`.lease_mutation.lock` non-blocking probe raises `OSError`/`BlockingIOError`). This deterministically proves that while Releaser 1 is inside the critical section (between `require_active` validation and `os.replace`), competing contenders are strictly locked out without requiring any scheduler delays or sleep. After Releaser 1 linearizes and completes release, Acquirer B acquires Lease B, and Stale Releaser 3 fails closed without removing Lease B.
- **R2-1 (Lease-Release-Aware Rollback State & Diagnostics in `cmd_approve()`)**: Updated `cmd_approve()` in `bridge.py` so that `PENDING_APPROVAL` is selected ONLY when BOTH `lease_released` AND `inbox_restored` succeed. If `store.release()` fails during rollback (even if inbox restoration succeeds), operational state is truthfully marked as `RECOVERY_REQUIRED` and `lease_release_failed` is preserved in diagnostics. Added dedicated fault-injection test `test_cmd_approve_post_acquire_rollback_lease_release_failure_reports_recovery_required`.
- **R1-5 (Review Manifest Compliance)**: Structured complete formal Review Manifest in `RESULT-029.md` bound to previous review blob `1b975d9972fee5a929de6374f7aee9740b47ba09` and updated test counts.

## Task Metadata
- Task: `TASK-029`
- Milestone: `M5`
- Action: `FIX`
- Authorized Artifact: `.ai/reviews/REVIEW-029.md` (`1b975d9972fee5a929de6374f7aee9740b47ba09`)
- Base Main SHA: `de556e5065ab1aea08fc832d2541532fe7085e33`
- Implementation Commit SHA: `bb84e0facb6b24d4c5fdd0eb636b45b9d89ab0b5`
- Target Branch: `ai/task-029`
- Active Runtime Executor: `antigravity`
- Alternate Executors Activated: `0`
- Paid External API Calls: `0`
- Live External Calls: `0`

## Round 4 Findings Resolution Audit
- [x] **R1-1**: Implemented direct zero-sleep non-blocking lock probes against both in-process and OS file locks in `test_deterministic_compare_and_release_toctou_interleaving_proof` in `tests/aios_bridge/test_runtime_lease.py`.
- [x] **R2-1**: Updated `cmd_approve()` in `bridge.py` to require both `lease_released` and `inbox_restored` for `PENDING_APPROVAL`, otherwise setting `RECOVERY_REQUIRED`. Added unit test `test_cmd_approve_post_acquire_rollback_lease_release_failure_reports_recovery_required` in `tests/test_bridge.py`.
- [x] **R1-5**: Emitted exact required manifest schema with all required keys, bound `PREVIOUS_REVIEW_SHA` to `1b975d9972fee5a929de6374f7aee9740b47ba09`, and recorded full test counts.

## Test Evidence
### Focused Test Suite (`test_lease.py`, `test_runtime_lease.py`, `test_bridge.py`)
```text
============================= test session starts =============================
platform win32 -- Python 3.14.7, pytest-8.3.4, pluggy-1.6.0 -- C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: c:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent
plugins: anyio-4.14.2, asyncio-0.25.0
asyncio: mode=Mode.STRICT, asyncio_default_fixture_loop_scope=None
collecting ... collected 63 items

tests/aios_bridge/continuity/test_lease.py::test_max_active_executors_invariant PASSED [  1%]
tests/aios_bridge/continuity/test_lease.py::test_executor_lease_valid_construction_and_fingerprint PASSED [  3%]
tests/aios_bridge/continuity/test_lease.py::test_executor_lease_whitespace_and_casing_rejection PASSED [  4%]
tests/aios_bridge/continuity/test_lease.py::test_executor_lease_forbidden_authority_and_ttl_keys_fail_closed PASSED [  6%]
tests/aios_bridge/continuity/test_lease.py::test_executor_lease_operation_domain PASSED [  7%]
tests/aios_bridge/continuity/test_lease.py::test_prepared_execution_distinct_from_executor_lease PASSED [  9%]
tests/aios_bridge/continuity/test_lease.py::test_validate_executor_lease_binding_success PASSED [ 11%]
tests/aios_bridge/continuity/test_lease.py::test_validate_executor_lease_binding_mismatches PASSED [ 12%]
tests/aios_bridge/continuity/test_lease.py::test_unknown_fields_rejected PASSED [ 14%]
tests/aios_bridge/continuity/test_lease.py::test_missing_required_fields_rejected PASSED [ 15%]
tests/aios_bridge/continuity/test_lease.py::test_oversized_payload_rejected_in_from_json PASSED [ 17%]
tests/aios_bridge/continuity/test_lease.py::test_malformed_json_wraps_continuity_error PASSED [ 19%]
tests/aios_bridge/continuity/test_lease.py::test_invalid_utf8_bytes_wrapped_in_from_json PASSED [ 20%]
tests/aios_bridge/test_runtime_lease.py::test_atomic_lease_store_acquire_and_load_active PASSED [ 22%]
tests/aios_bridge/test_runtime_lease.py::test_atomic_lease_store_acquire_conflict_fails_closed PASSED [ 23%]
tests/aios_bridge/test_runtime_lease.py::test_atomic_lease_store_workspace_mismatch_fails_closed PASSED [ 25%]
tests/aios_bridge/test_runtime_lease.py::test_atomic_lease_store_concurrent_race_linearization PASSED [ 26%]
tests/aios_bridge/test_runtime_lease.py::test_corrupt_empty_and_oversized_active_file_blocks_and_fails_closed PASSED [ 28%]
tests/aios_bridge/test_runtime_lease.py::test_require_active_validation PASSED [ 30%]
tests/aios_bridge/test_runtime_lease.py::test_compare_and_release_lifecycle PASSED [ 31%]
tests/aios_bridge/test_runtime_lease.py::test_deterministic_compare_and_release_toctou_interleaving_proof PASSED [ 33%]
tests/aios_bridge/test_runtime_lease.py::test_concurrent_compare_and_release_interleaving_race_protection PASSED [ 34%]
tests/aios_bridge/test_runtime_lease.py::test_cross_process_lease_mutation_guard PASSED [ 36%]
tests/aios_bridge/test_runtime_lease.py::test_failed_writer_cleanup_safety_when_open_fails PASSED [ 38%]
tests/aios_bridge/test_runtime_lease.py::test_failed_writer_cleanup_only_removes_own_created_file_on_write_error PASSED [ 39%]
tests/aios_bridge/test_runtime_lease.py::test_partial_write_fault_injection_fails_closed PASSED [ 41%]
tests/aios_bridge/test_runtime_lease.py::test_fsync_failure_fault_injection_fails_closed PASSED [ 42%]
tests/test_bridge.py::test_runtime_state_path_is_outside_repository_worktree PASSED [ 44%]
tests/test_bridge.py::test_sync_does_not_dirty_worktree_and_provides_context PASSED [ 46%]
tests/test_bridge.py::test_changes_required_review_creates_pending_review_event PASSED [ 47%]
tests/test_bridge.py::test_repeated_changes_required_updates_do_not_create_duplicate_pending_events PASSED [ 49%]
tests/test_bridge.py::test_review_update_to_approved_clears_pending_and_sets_approved_state PASSED [ 50%]
tests/test_bridge.py::test_missing_or_unknown_review_status_is_non_actionable PASSED [ 52%]
tests/test_bridge.py::test_handoff_run_without_preexisting_pending_event_records_active_auth_and_creates_branch PASSED [ 53%]
tests/test_bridge.py::test_handoff_run_missing_task_fails_closed PASSED  [ 55%]
tests/test_bridge.py::test_reconcile_local_main_fast_forwards_when_behind PASSED [ 57%]
tests/test_bridge.py::test_reconcile_local_main_fails_closed_when_diverged_or_ahead PASSED [ 58%]
tests/test_bridge.py::test_dirty_worktree_blocks_handoff_and_reconciliation PASSED [ 60%]
tests/test_bridge.py::test_handoff_fix_succeeds_only_for_changes_required_and_binds_exact_blob PASSED [ 61%]
tests/test_bridge.py::test_handoff_fix_fails_closed_when_approved_or_missing_or_unknown_status PASSED [ 63%]
tests/test_bridge.py::test_publish_enforces_active_authorization_and_detects_control_drift PASSED [ 65%]
tests/test_bridge.py::test_publish_consumes_active_authorization_and_creates_result_with_test_evidence PASSED [ 66%]
tests/test_bridge.py::test_publish_preserves_active_authorization_when_tests_fail PASSED [ 68%]
tests/test_bridge.py::test_watcher_notifications_v040_instruct_aios_worker_command PASSED [ 69%]
tests/test_bridge.py::test_popup_notification_failure_does_not_break_sync_or_checkpoint PASSED [ 71%]
tests/test_bridge.py::test_watcher_retries_after_fetch_auth_network_error PASSED [ 73%]
tests/test_bridge.py::test_utf8_output_and_path_handling_remains_functional PASSED [ 74%]
tests/test_bridge.py::test_publish_fails_closed_when_only_legacy_approval_exists_and_no_active_authorization PASSED [ 76%]
tests/test_bridge.py::test_existing_task_branch_resume_fails_when_local_ahead_of_remote PASSED [ 77%]
tests/test_bridge.py::test_existing_task_branch_resume_fails_when_local_and_remote_diverged PASSED [ 79%]
tests/test_bridge.py::test_existing_task_branch_resume_fast_forwards_when_local_strictly_behind PASSED [ 80%]
tests/test_bridge.py::test_publish_fails_when_active_run_auth_has_changes_required_review_on_control PASSED [ 82%]
tests/test_bridge.py::test_publish_fails_when_action_argument_mismatches_active_authorization PASSED [ 84%]
tests/test_bridge.py::test_handoff_run_fails_when_task_artifact_is_malformed PASSED [ 85%]
tests/test_bridge.py::test_handoff_run_acquires_lease_and_second_handoff_conflicts PASSED [ 87%]
tests/test_bridge.py::test_lease_status_and_confirmation_gated_release PASSED [ 88%]
tests/test_bridge.py::test_cmd_approve_lease_conflict_preserves_pending_event_and_state PASSED [ 90%]
tests/test_bridge.py::test_publish_commit_and_push_failure_retains_exact_lease PASSED [ 92%]
tests/test_bridge.py::test_cmd_approve_post_acquire_inbox_save_failure_rolls_back_lease PASSED [ 93%]
tests/test_bridge.py::test_cmd_approve_post_acquire_update_state_failure_rolls_back_lease PASSED [ 95%]
tests/test_bridge.py::test_cmd_approve_post_acquire_save_auth_failure_rolls_back_lease_and_restores_pending PASSED [ 96%]
tests/test_bridge.py::test_cmd_approve_post_acquire_rollback_failure_reports_recovery_diagnostics PASSED [ 98%]
tests/test_bridge.py::test_cmd_approve_post_acquire_rollback_lease_release_failure_reports_recovery_required PASSED [100%]

============================== warnings summary ===============================
tests/aios_bridge/continuity/test_lease.py::test_max_active_executors_invariant
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:1153: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    return asyncio.get_event_loop_policy()

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================= 63 passed, 1 warning in 15.59s ========================

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
........................................................................ [ 50%]
........................................................................ [ 60%]
........................................................................ [ 70%]
........................................................................ [ 81%]
........................................................................ [ 91%]
..............................................................           [100%]
710 passed in 71.84s (0:01:11)

C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:207: PytestDeprecationWarning: The configuration option "asyncio_default_fixture_loop_scope" is unset.
The event loop scope for asynchronous fixtures will default to the fixture caching scope. Future versions of pytest-asyncio will default the loop scope for asynchronous fixtures to function scope. Set the default fixture loop scope explicitly in order to avoid unexpected behavior in the future. Valid fixture loop scopes are: "function", "class", "module", "package", "session"

  warnings.warn(PytestDeprecationWarning(_DEFAULT_FIXTURE_LOOP_SCOPE_UNSET))
```

## Diff Stat vs Base Main (`de556e5065ab1aea08fc832d2541532fe7085e33`)
```text
.ai/results/RESULT-029.md                  | 193 +++++++
 bridge.py                                  | 439 +++++++++++++--
 src/aios_bridge/continuity/__init__.py     |   8 +
 src/aios_bridge/continuity/lease.py        | 290 ++++++++++
 src/aios_bridge/runtime_lease.py           | 299 ++++++++++
 tests/aios_bridge/continuity/test_lease.py | 266 +++++++++
 tests/aios_bridge/test_runtime_lease.py    | 540 ++++++++++++++++++
 tests/test_bridge.py                       | 874 +++++++++++++++++++++++++++++
 8 files changed, 2873 insertions(+), 36 deletions(-)
```

## Published At
2026-08-17T03:12:55.842476+00:00
