# RESULT-031

STATUS: READY_FOR_REVIEW

## Review Manifest
```yaml
TASK_ID: TASK-031
ACTION: FIX
EXECUTOR_ID: claude-code
EXECUTOR_FAILOVER: YES
FAILOVER_FROM_EXECUTOR: antigravity
FAILOVER_TO_EXECUTOR: claude-code
FAILOVER_SOURCE_PUBLISHED_SHA: 258e1c220542e9d493480d6884c23d965bf79230
FAILOVER_PROOF_FINGERPRINT: 541b5cdb1a5418f4095b9f95596da9cd9985ebb6d4291f9ecbbcae2797b6f06a
FAILOVER_REVIEW_BLOB_SHA: 6cd99884462574a082c6db23f3875737a517e2c3
BASE_SHA: 8a1550b40692798fe0c049aa2ad74d55c54618ee
M7_THIRD_EXECUTOR_PORTABILITY: IMPLEMENTED
SUPPORTED_RUNTIME_EXECUTORS: antigravity,codex,claude-code
CONTINUITY_CORE_CHANGED: NO
M5_LEASE_SEMANTICS_CHANGED: NO
M6_FAILOVER_CONTRACT_CHANGED: NO
AUTOMATIC_EXECUTOR_ROUTING: NO
HOT_HANDOFF_ADDED: NO
FOURTH_EXECUTOR_ADDED: NO
PAID_EXTERNAL_API_CALLS: 0
LIVE_EXTERNAL_CALLS_AUTOMATED_TESTS: 0
M7_REAL_PROOF_ANTIGRAVITY_TO_CLAUDE_CODE: PASS
M7_REAL_PROOF_CLAUDE_CODE_TO_ANTIGRAVITY: PENDING
BRIDGE_TESTS: 56/56 pass
CONTINUITY_TESTS: 152/152 pass
FULL_REPO_TESTS: 755/755 pass
REGRESSIONS: 0
```

## Summary
Implementation completed by claude-code; pending ChatGPT review.

## Task Metadata
- Task: `TASK-031`
- Action: `FIX`
- Executor: `claude-code`
- Authorized Artifact: `.ai/reviews/REVIEW-031.md (6cd9988446)`
- Base Main SHA: `(n/a)`
- Branch: `ai/task-031`

## Files Changed
- (none before result generation)

## Diff Stat
```text

```

## Tests
Command: `.\venv\Scripts\python -m pytest tests/ -v`  
Exit code: 0

```text
der.py::test_preserves_exact_original_bytes PASSED [ 87%]
tests/product_source/test_original_media_downloader.py::test_streaming_oversize_media_aborts_early PASSED [ 87%]
tests/product_source/test_original_media_downloader.py::test_diagnostics_do_not_leak_sensitive_url_tokens PASSED [ 88%]
tests/product_source/test_original_media_downloader.py::test_byte_duplicate_collapse_leaves_no_orphan_files PASSED [ 88%]
tests/product_source/test_original_media_downloader.py::test_canonical_url_dedupe_before_download PASSED [ 88%]
tests/product_source/test_original_media_downloader.py::test_max_media_per_product_enforced PASSED [ 88%]
tests/product_source/test_scrape_tool_compat.py::test_shopee_scrape_tool_schema PASSED [ 88%]
tests/product_source/test_scrape_tool_compat.py::test_tiktok_scrape_tool_schema PASSED [ 88%]
tests/product_source/test_scrape_tool_compat.py::test_shopee_scrape_tool_passes_run_id_to_browser_manager PASSED [ 88%]
tests/product_source/test_scrape_tool_compat.py::test_tiktok_scrape_tool_passes_run_id_to_browser_manager PASSED [ 89%]
tests/product_source/test_scrape_tool_compat.py::test_tools_do_not_call_image_processor PASSED [ 89%]
tests/product_source/test_scrape_tool_compat.py::test_tools_do_not_invoke_llm PASSED [ 89%]
tests/product_source/test_scrape_tool_compat.py::test_partial_upload_returns_partial_success PASSED [ 89%]
tests/product_source/test_scrape_tool_compat.py::test_full_upload_failure_returns_failure PASSED [ 89%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_prefers_structured_data_when_identity_matches PASSED [ 89%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_rejects_unrelated_structured_data_on_identity_mismatch PASSED [ 89%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_fails_closed_when_no_media_found PASSED [ 89%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_collects_explicit_variants PASSED [ 90%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_gallery_fallback_when_no_structured_images PASSED [ 90%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_seller_description_media_labeled PASSED [ 90%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_raises_blocked_on_captcha PASSED [ 90%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_with_strict_browser_manager PASSED [ 90%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_rejects_overlapping_substring_id PASSED [ 90%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_js_script_excludes_reviews_by_container_provenance PASSED [ 90%]
tests/product_source/test_tiktok_source_extractor.py::test_tiktok_extractor_prefers_structured_data_when_identity_matches PASSED [ 90%]
tests/product_source/test_tiktok_source_extractor.py::test_tiktok_extractor_rejects_unrelated_structured_data_on_identity_mismatch PASSED [ 91%]
tests/product_source/test_tiktok_source_extractor.py::test_tiktok_extractor_fails_closed_when_no_media_found PASSED [ 91%]
tests/product_source/test_tiktok_source_extractor.py::test_tiktok_extractor_collects_explicit_variants PASSED [ 91%]
tests/product_source/test_tiktok_source_extractor.py::test_tiktok_extractor_gallery_fallback PASSED [ 91%]
tests/product_source/test_tiktok_source_extractor.py::test_tiktok_extractor_with_strict_browser_manager PASSED [ 91%]
tests/product_source/test_tiktok_source_extractor.py::test_tiktok_extractor_rejects_overlapping_substring_id PASSED [ 91%]
tests/product_source/test_tiktok_source_extractor.py::test_tiktok_js_script_excludes_reviews_and_no_main_article_fallback PASSED [ 91%]
tests/product_source/test_tiktok_source_extractor.py::test_tiktok_extractor_does_not_block_on_globally_loaded_captcha_scripts PASSED [ 92%]
tests/product_source/test_tiktok_source_extractor.py::test_tiktok_extractor_raises_blocked_on_active_challenge PASSED [ 92%]
tests/test_bridge.py::test_runtime_state_path_is_outside_repository_worktree PASSED [ 92%]
tests/test_bridge.py::test_sync_does_not_dirty_worktree_and_provides_context PASSED [ 92%]
tests/test_bridge.py::test_changes_required_review_creates_pending_review_event PASSED [ 92%]
tests/test_bridge.py::test_repeated_changes_required_updates_do_not_create_duplicate_pending_events PASSED [ 92%]
tests/test_bridge.py::test_review_update_to_approved_clears_pending_and_sets_approved_state PASSED [ 92%]
tests/test_bridge.py::test_missing_or_unknown_review_status_is_non_actionable PASSED [ 92%]
tests/test_bridge.py::test_handoff_run_without_preexisting_pending_event_records_active_auth_and_creates_branch PASSED [ 93%]
tests/test_bridge.py::test_handoff_run_missing_task_fails_closed PASSED  [ 93%]
tests/test_bridge.py::test_reconcile_local_main_fast_forwards_when_behind PASSED [ 93%]
tests/test_bridge.py::test_reconcile_local_main_fails_closed_when_diverged_or_ahead PASSED [ 93%]
tests/test_bridge.py::test_dirty_worktree_blocks_handoff_and_reconciliation PASSED [ 93%]
tests/test_bridge.py::test_handoff_fix_succeeds_only_for_changes_required_and_binds_exact_blob PASSED [ 93%]
tests/test_bridge.py::test_handoff_fix_fails_closed_when_approved_or_missing_or_unknown_status PASSED [ 93%]
tests/test_bridge.py::test_publish_enforces_active_authorization_and_detects_control_drift PASSED [ 94%]
tests/test_bridge.py::test_publish_consumes_active_authorization_and_creates_result_with_test_evidence PASSED [ 94%]
tests/test_bridge.py::test_publish_preserves_active_authorization_when_tests_fail PASSED [ 94%]
tests/test_bridge.py::test_watcher_notifications_v040_instruct_aios_worker_command PASSED [ 94%]
tests/test_bridge.py::test_popup_notification_failure_does_not_break_sync_or_checkpoint PASSED [ 94%]
tests/test_bridge.py::test_watcher_retries_after_fetch_auth_network_error PASSED [ 94%]
tests/test_bridge.py::test_utf8_output_and_path_handling_remains_functional PASSED [ 94%]
tests/test_bridge.py::test_publish_fails_closed_when_only_legacy_approval_exists_and_no_active_authorization PASSED [ 94%]
tests/test_bridge.py::test_existing_task_branch_resume_fails_when_local_ahead_of_remote PASSED [ 95%]
tests/test_bridge.py::test_existing_task_branch_resume_fails_when_local_and_remote_diverged PASSED [ 95%]
tests/test_bridge.py::test_existing_task_branch_resume_fast_forwards_when_local_strictly_behind PASSED [ 95%]
tests/test_bridge.py::test_publish_fails_when_active_run_auth_has_changes_required_review_on_control PASSED [ 95%]
tests/test_bridge.py::test_publish_fails_when_action_argument_mismatches_active_authorization PASSED [ 95%]
tests/test_bridge.py::test_handoff_run_fails_when_task_artifact_is_malformed PASSED [ 95%]
tests/test_bridge.py::test_handoff_run_acquires_lease_and_second_handoff_conflicts PASSED [ 95%]
tests/test_bridge.py::test_lease_status_and_confirmation_gated_release PASSED [ 96%]
tests/test_bridge.py::test_cmd_approve_lease_conflict_preserves_pending_event_and_state PASSED [ 96%]
tests/test_bridge.py::test_publish_commit_and_push_failure_retains_exact_lease PASSED [ 96%]
tests/test_bridge.py::test_cmd_approve_post_acquire_inbox_save_failure_rolls_back_lease PASSED [ 96%]
tests/test_bridge.py::test_cmd_approve_post_acquire_update_state_failure_rolls_back_lease PASSED [ 96%]
tests/test_bridge.py::test_cmd_approve_post_acquire_save_auth_failure_rolls_back_lease_and_restores_pending PASSED [ 96%]
tests/test_bridge.py::test_cmd_approve_post_acquire_rollback_failure_reports_recovery_diagnostics PASSED [ 96%]
tests/test_bridge.py::test_cmd_approve_post_acquire_rollback_lease_release_failure_reports_recovery_required PASSED [ 96%]
tests/test_bridge.py::test_reconstruct_expected_executor_lease_valid_and_invalid_cases PASSED [ 97%]
tests/test_bridge.py::test_cmd_publish_missing_executor_id_in_active_auth_fails_closed_and_retains_lease PASSED [ 97%]
tests/test_bridge.py::test_validate_runtime_executor_id_rules PASSED     [ 97%]
tests/test_bridge.py::test_handoff_fix_failover_activation_flow_and_proof_generation PASSED [ 97%]
tests/test_bridge.py::test_handoff_fix_failover_fails_closed_when_prior_auth_not_consumed_or_branch_drift PASSED [ 97%]
tests/test_bridge.py::test_cmd_publish_failover_revalidation_and_result_manifest PASSED [ 97%]
tests/test_bridge.py::test_cmd_publish_failover_tampered_proof_fails_closed_and_retains_lease PASSED [ 97%]
tests/test_bridge.py::test_handoff_and_approve_failover_remote_branch_drift_or_missing_fails_closed PASSED [ 98%]
tests/test_bridge.py::test_handoff_and_approve_failover_requires_explicit_executor PASSED [ 98%]
tests/test_bridge.py::test_publish_failover_control_commit_mismatch_fails_closed PASSED [ 98%]
tests/test_bridge.py::test_handoff_failover_post_acquire_rollback_safety PASSED [ 98%]
tests/test_bridge.py::test_handoff_failover_post_acquire_rollback_restores_prior_consumed_auth_when_update_state_fails PASSED [ 98%]
tests/test_bridge.py::test_handoff_and_approve_fix_fails_closed_when_prior_auth_missing_or_malformed PASSED [ 98%]
tests/test_bridge.py::test_failover_preconditions_reject_when_workspace_on_wrong_branch PASSED [ 98%]
tests/test_bridge.py::test_cmd_publish_task_030_proof_progress_manifest_generation PASSED [ 98%]
tests/test_bridge.py::test_handoff_and_approve_claude_code_transitions PASSED [ 99%]
tests/test_bridge.py::test_cmd_publish_task_031_proof_progress_manifest_generation PASSED [ 99%]
tests/test_bridge.py::test_handoff_and_approve_claude_code_run_activation PASSED [ 99%]
tests/test_bridge.py::test_task_031_portability_scope_validation_fails_closed_on_core_change_or_fourth_executor PASSED [ 99%]
tests/test_bridge.py::test_task_031_test_evidence_truthful_binding_and_negative_subset_cases PASSED [ 99%]
tests/test_gdrive_integrator.py::test_gdrive_auth_success PASSED         [ 99%]
tests/test_gdrive_integrator.py::test_gdrive_auth_no_file PASSED         [ 99%]
tests/test_image_processor.py::test_image_processor_duplicate_logic PASSED [100%]

============================== warnings summary ===============================
tests/aios_bridge/continuity/test_brain.py::test_valid_neutral_brain_request_and_result_round_trip
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:1153: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    return asyncio.get_event_loop_policy()

tests/aios_bridge/external_brain/test_gateway.py: 7 warnings
tests/aios_bridge/external_brain/test_minimax_provider.py: 8 warnings
tests/aios_bridge/external_brain/test_provider_contract.py: 1 warning
tests/aios_bridge/external_brain/test_runner.py: 7 warnings
tests/aios_bridge/external_brain/test_transport.py: 5 warnings
tests/aios_bridge/external_brain/test_transport_contract.py: 1 warning
tests/core/test_recovery_controller.py: 4 warnings
tests/core/test_recovery_diagnostics.py: 4 warnings
tests/core/test_retry.py: 3 warnings
tests/core/test_run_budget.py: 11 warnings
tests/core/test_tool_executor_v2.py: 14 warnings
tests/images/test_pipeline.py: 2 warnings
tests/images/test_storage.py: 2 warnings
tests/integration/test_agent_crash_recovery_integration.py: 4 warnings
tests/integration/test_agent_failures.py: 2 warnings
tests/integration/test_agent_flow.py: 2 warnings
tests/integration/test_agent_loop.py: 5 warnings
tests/integration/test_browser_tools.py: 1 warning
tests/integration/test_cancellation_integration.py: 4 warnings
tests/integration/test_phase55_reliability_suite.py: 4 warnings
tests/integration/test_phase56_concurrency.py: 2 warnings
tests/integration/test_phase56_fault_injection.py: 18 warnings
tests/integration/test_phase56_production_readiness.py: 3 warnings
tests/integration/test_phase56_soak.py: 5 warnings
tests/integration/test_phase6_bootstrap.py: 15 warnings
tests/integration/test_recovery_control_plane.py: 7 warnings
tests/integration/test_retry_policy_integration.py: 3 warnings
tests/integration/test_retry_timeline_integration.py: 6 warnings
tests/integration/test_tool_executor_jsonl_integration.py: 5 warnings
tests/integration/test_tool_executor_ttl_compact_integration.py: 5 warnings
tests/integrations/google_drive/test_publisher.py: 5 warnings
tests/product_intelligence/test_shopee_discovery.py: 12 warnings
tests/product_source/test_extractor_dom_fixtures.py: 8 warnings
tests/product_source/test_original_media_downloader.py: 6 warnings
tests/product_source/test_scrape_tool_compat.py: 4 warnings
tests/product_source/test_shopee_source_extractor.py: 10 warnings
tests/product_source/test_tiktok_source_extractor.py: 10 warnings
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:844: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    _restore_event_loop_policy(asyncio.get_event_loop_policy()),

tests/aios_bridge/external_brain/test_gateway.py: 7 warnings
tests/aios_bridge/external_brain/test_minimax_provider.py: 8 warnings
tests/aios_bridge/external_brain/test_provider_contract.py: 1 warning
tests/aios_bridge/external_brain/test_runner.py: 7 warnings
tests/aios_bridge/external_brain/test_transport.py: 5 warnings
tests/aios_bridge/external_brain/test_transport_contract.py: 1 warning
tests/core/test_recovery_controller.py: 4 warnings
tests/core/test_recovery_diagnostics.py: 4 warnings
tests/core/test_retry.py: 3 warnings
tests/core/test_run_budget.py: 11 warnings
tests/core/test_tool_executor_v2.py: 14 warnings
tests/images/test_pipeline.py: 2 warnings
tests/images/test_storage.py: 2 warnings
tests/integration/test_agent_crash_recovery_integration.py: 4 warnings
tests/integration/test_agent_failures.py: 2 warnings
tests/integration/test_agent_flow.py: 2 warnings
tests/integration/test_agent_loop.py: 5 warnings
tests/integration/test_browser_tools.py: 1 warning
tests/integration/test_cancellation_integration.py: 4 warnings
tests/integration/test_phase55_reliability_suite.py: 4 warnings
tests/integration/test_phase56_concurrency.py: 2 warnings
tests/integration/test_phase56_fault_injection.py: 18 warnings
tests/integration/test_phase56_production_readiness.py: 3 warnings
tests/integration/test_phase56_soak.py: 5 warnings
tests/integration/test_phase6_bootstrap.py: 15 warnings
tests/integration/test_recovery_control_plane.py: 7 warnings
tests/integration/test_retry_policy_integration.py: 3 warnings
tests/integration/test_retry_timeline_integration.py: 6 warnings
tests/integration/test_tool_executor_jsonl_integration.py: 5 warnings
tests/integration/test_tool_executor_ttl_compact_integration.py: 5 warnings
tests/integrations/google_drive/test_publisher.py: 5 warnings
tests/product_intelligence/test_shopee_discovery.py: 12 warnings
tests/product_source/test_extractor_dom_fixtures.py: 8 warnings
tests/product_source/test_original_media_downloader.py: 6 warnings
tests/product_source/test_scrape_tool_compat.py: 4 warnings
tests/product_source/test_shopee_source_extractor.py: 10 warnings
tests/product_source/test_tiktok_source_extractor.py: 10 warnings
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:1125: DeprecationWarning: 'asyncio.set_event_loop_policy' is deprecated and slated for removal in Python 3.16
    asyncio.set_event_loop_policy(new_loop_policy)

tests/aios_bridge/external_brain/test_gateway.py: 7 warnings
tests/aios_bridge/external_brain/test_minimax_provider.py: 8 warnings
tests/aios_bridge/external_brain/test_provider_contract.py: 1 warning
tests/aios_bridge/external_brain/test_runner.py: 7 warnings
tests/aios_bridge/external_brain/test_transport.py: 5 warnings
tests/aios_bridge/external_brain/test_transport_contract.py: 1 warning
tests/core/test_recovery_controller.py: 4 warnings
tests/core/test_recovery_diagnostics.py: 4 warnings
tests/core/test_retry.py: 3 warnings
tests/core/test_run_budget.py: 11 warnings
tests/core/test_tool_executor_v2.py: 14 warnings
tests/images/test_pipeline.py: 2 warnings
tests/images/test_storage.py: 2 warnings
tests/integration/test_agent_crash_recovery_integration.py: 4 warnings
tests/integration/test_agent_failures.py: 2 warnings
tests/integration/test_agent_flow.py: 2 warnings
tests/integration/test_agent_loop.py: 5 warnings
tests/integration/test_browser_tools.py: 1 warning
tests/integration/test_cancellation_integration.py: 4 warnings
tests/integration/test_phase55_reliability_suite.py: 4 warnings
tests/integration/test_phase56_concurrency.py: 2 warnings
tests/integration/test_phase56_fault_injection.py: 18 warnings
tests/integration/test_phase56_production_readiness.py: 3 warnings
tests/integration/test_phase56_soak.py: 5 warnings
tests/integration/test_phase6_bootstrap.py: 15 warnings
tests/integration/test_recovery_control_plane.py: 7 warnings
tests/integration/test_retry_policy_integration.py: 3 warnings
tests/integration/test_retry_timeline_integration.py: 6 warnings
tests/integration/test_tool_executor_jsonl_integration.py: 5 warnings
tests/integration/test_tool_executor_ttl_compact_integration.py: 5 warnings
tests/integrations/google_drive/test_publisher.py: 5 warnings
tests/product_intelligence/test_shopee_discovery.py: 12 warnings
tests/product_source/test_extractor_dom_fixtures.py: 8 warnings
tests/product_source/test_original_media_downloader.py: 6 warnings
tests/product_source/test_scrape_tool_compat.py: 4 warnings
tests/product_source/test_shopee_source_extractor.py: 10 warnings
tests/product_source/test_tiktok_source_extractor.py: 10 warnings
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:1126: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    loop = asyncio.get_event_loop_policy().new_event_loop()

tests/aios_bridge/external_brain/test_gateway.py: 7 warnings
tests/aios_bridge/external_brain/test_minimax_provider.py: 8 warnings
tests/aios_bridge/external_brain/test_provider_contract.py: 1 warning
tests/aios_bridge/external_brain/test_runner.py: 7 warnings
tests/aios_bridge/external_brain/test_transport.py: 5 warnings
tests/aios_bridge/external_brain/test_transport_contract.py: 1 warning
tests/core/test_recovery_controller.py: 4 warnings
tests/core/test_recovery_diagnostics.py: 4 warnings
tests/core/test_retry.py: 3 warnings
tests/core/test_run_budget.py: 11 warnings
tests/core/test_tool_executor_v2.py: 14 warnings
tests/images/test_pipeline.py: 2 warnings
tests/images/test_storage.py: 2 warnings
tests/integration/test_agent_crash_recovery_integration.py: 4 warnings
tests/integration/test_agent_failures.py: 2 warnings
tests/integration/test_agent_flow.py: 2 warnings
tests/integration/test_agent_loop.py: 5 warnings
tests/integration/test_browser_tools.py: 1 warning
tests/integration/test_cancellation_integration.py: 4 warnings
tests/integration/test_phase55_reliability_suite.py: 4 warnings
tests/integration/test_phase56_concurrency.py: 2 warnings
tests/integration/test_phase56_fault_injection.py: 18 warnings
tests/integration/test_phase56_production_readiness.py: 3 warnings
tests/integration/test_phase56_soak.py: 5 warnings
tests/integration/test_phase6_bootstrap.py: 15 warnings
tests/integration/test_recovery_control_plane.py: 7 warnings
tests/integration/test_retry_policy_integration.py: 3 warnings
tests/integration/test_retry_timeline_integration.py: 6 warnings
tests/integration/test_tool_executor_jsonl_integration.py: 5 warnings
tests/integration/test_tool_executor_ttl_compact_integration.py: 5 warnings
tests/integrations/google_drive/test_publisher.py: 5 warnings
tests/product_intelligence/test_shopee_discovery.py: 12 warnings
tests/product_source/test_extractor_dom_fixtures.py: 8 warnings
tests/product_source/test_original_media_downloader.py: 6 warnings
tests/product_source/test_scrape_tool_compat.py: 4 warnings
tests/product_source/test_shopee_source_extractor.py: 10 warnings
tests/product_source/test_tiktok_source_extractor.py: 10 warnings
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:859: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    policy = asyncio.get_event_loop_policy()

tests/aios_bridge/external_brain/test_gateway.py: 7 warnings
tests/aios_bridge/external_brain/test_minimax_provider.py: 8 warnings
tests/aios_bridge/external_brain/test_provider_contract.py: 1 warning
tests/aios_bridge/external_brain/test_runner.py: 7 warnings
tests/aios_bridge/external_brain/test_transport.py: 5 warnings
tests/aios_bridge/external_brain/test_transport_contract.py: 1 warning
tests/core/test_recovery_controller.py: 4 warnings
tests/core/test_recovery_diagnostics.py: 4 warnings
tests/core/test_retry.py: 3 warnings
tests/core/test_run_budget.py: 11 warnings
tests/core/test_tool_executor_v2.py: 14 warnings
tests/images/test_pipeline.py: 2 warnings
tests/images/test_storage.py: 2 warnings
tests/integration/test_agent_crash_recovery_integration.py: 4 warnings
tests/integration/test_agent_failures.py: 2 warnings
tests/integration/test_agent_flow.py: 2 warnings
tests/integration/test_agent_loop.py: 5 warnings
tests/integration/test_browser_tools.py: 1 warning
tests/integration/test_cancellation_integration.py: 4 warnings
tests/integration/test_phase55_reliability_suite.py: 4 warnings
tests/integration/test_phase56_concurrency.py: 2 warnings
tests/integration/test_phase56_fault_injection.py: 18 warnings
tests/integration/test_phase56_production_readiness.py: 3 warnings
tests/integration/test_phase56_soak.py: 5 warnings
tests/integration/test_phase6_bootstrap.py: 15 warnings
tests/integration/test_recovery_control_plane.py: 7 warnings
tests/integration/test_retry_policy_integration.py: 3 warnings
tests/integration/test_retry_timeline_integration.py: 6 warnings
tests/integration/test_tool_executor_jsonl_integration.py: 5 warnings
tests/integration/test_tool_executor_ttl_compact_integration.py: 5 warnings
tests/integrations/google_drive/test_publisher.py: 5 warnings
tests/product_intelligence/test_shopee_discovery.py: 12 warnings
tests/product_source/test_extractor_dom_fixtures.py: 8 warnings
tests/product_source/test_original_media_downloader.py: 6 warnings
tests/product_source/test_scrape_tool_compat.py: 4 warnings
tests/product_source/test_shopee_source_extractor.py: 10 warnings
tests/product_source/test_tiktok_source_extractor.py: 10 warnings
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:904: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    policy = asyncio.get_event_loop_policy()

tests/aios_bridge/external_brain/test_gateway.py: 7 warnings
tests/aios_bridge/external_brain/test_minimax_provider.py: 8 warnings
tests/aios_bridge/external_brain/test_provider_contract.py: 1 warning
tests/aios_bridge/external_brain/test_runner.py: 7 warnings
tests/aios_bridge/external_brain/test_transport.py: 5 warnings
tests/aios_bridge/external_brain/test_transport_contract.py: 1 warning
tests/core/test_recovery_controller.py: 4 warnings
tests/core/test_recovery_diagnostics.py: 4 warnings
tests/core/test_retry.py: 3 warnings
tests/core/test_run_budget.py: 11 warnings
tests/core/test_tool_executor_v2.py: 14 warnings
tests/images/test_pipeline.py: 2 warnings
tests/images/test_storage.py: 2 warnings
tests/integration/test_agent_crash_recovery_integration.py: 4 warnings
tests/integration/test_agent_failures.py: 2 warnings
tests/integration/test_agent_flow.py: 2 warnings
tests/integration/test_agent_loop.py: 5 warnings
tests/integration/test_browser_tools.py: 1 warning
tests/integration/test_cancellation_integration.py: 4 warnings
tests/integration/test_phase55_reliability_suite.py: 4 warnings
tests/integration/test_phase56_concurrency.py: 2 warnings
tests/integration/test_phase56_fault_injection.py: 18 warnings
tests/integration/test_phase56_production_readiness.py: 3 warnings
tests/integration/test_phase56_soak.py: 5 warnings
tests/integration/test_phase6_bootstrap.py: 15 warnings
tests/integration/test_recovery_control_plane.py: 7 warnings
tests/integration/test_retry_policy_integration.py: 3 warnings
tests/integration/test_retry_timeline_integration.py: 6 warnings
tests/integration/test_tool_executor_jsonl_integration.py: 5 warnings
tests/integration/test_tool_executor_ttl_compact_integration.py: 5 warnings
tests/integrations/google_drive/test_publisher.py: 5 warnings
tests/product_intelligence/test_shopee_discovery.py: 12 warnings
tests/product_source/test_extractor_dom_fixtures.py: 8 warnings
tests/product_source/test_original_media_downloader.py: 6 warnings
tests/product_source/test_scrape_tool_compat.py: 4 warnings
tests/product_source/test_shopee_source_extractor.py: 10 warnings
tests/product_source/test_tiktok_source_extractor.py: 10 warnings
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:928: DeprecationWarning: 'asyncio.set_event_loop_policy' is deprecated and slated for removal in Python 3.16
    asyncio.set_event_loop_policy(previous_policy)

tests/aios_bridge/external_brain/test_gateway.py: 7 warnings
tests/aios_bridge/external_brain/test_minimax_provider.py: 8 warnings
tests/aios_bridge/external_brain/test_provider_contract.py: 1 warning
tests/aios_bridge/external_brain/test_runner.py: 7 warnings
tests/aios_bridge/external_brain/test_transport.py: 5 warnings
tests/aios_bridge/external_brain/test_transport_contract.py: 1 warning
tests/core/test_recovery_controller.py: 4 warnings
tests/core/test_recovery_diagnostics.py: 4 warnings
tests/core/test_retry.py: 3 warnings
tests/core/test_run_budget.py: 11 warnings
tests/core/test_tool_executor_v2.py: 14 warnings
tests/images/test_pipeline.py: 2 warnings
tests/images/test_storage.py: 2 warnings
tests/integration/test_agent_crash_recovery_integration.py: 4 warnings
tests/integration/test_agent_failures.py: 2 warnings
tests/integration/test_agent_flow.py: 2 warnings
tests/integration/test_agent_loop.py: 5 warnings
tests/integration/test_browser_tools.py: 1 warning
tests/integration/test_cancellation_integration.py: 4 warnings
tests/integration/test_phase55_reliability_suite.py: 4 warnings
tests/integration/test_phase56_concurrency.py: 2 warnings
tests/integration/test_phase56_fault_injection.py: 18 warnings
tests/integration/test_phase56_production_readiness.py: 3 warnings
tests/integration/test_phase56_soak.py: 5 warnings
tests/integration/test_phase6_bootstrap.py: 15 warnings
tests/integration/test_recovery_control_plane.py: 7 warnings
tests/integration/test_retry_policy_integration.py: 3 warnings
tests/integration/test_retry_timeline_integration.py: 6 warnings
tests/integration/test_tool_executor_jsonl_integration.py: 5 warnings
tests/integration/test_tool_executor_ttl_compact_integration.py: 5 warnings
tests/integrations/google_drive/test_publisher.py: 5 warnings
tests/product_intelligence/test_shopee_discovery.py: 12 warnings
tests/product_source/test_extractor_dom_fixtures.py: 8 warnings
tests/product_source/test_original_media_downloader.py: 6 warnings
tests/product_source/test_scrape_tool_compat.py: 4 warnings
tests/product_source/test_shopee_source_extractor.py: 10 warnings
tests/product_source/test_tiktok_source_extractor.py: 10 warnings
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:940: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    policy = asyncio.get_event_loop_policy()

tests/images/test_models.py::test_image_artifact_validation
tests/images/test_models.py::test_image_artifact_validation
tests/images/test_pipeline.py::test_pipeline_valid_image
tests/images/test_storage.py::test_store_put_and_get
tests/images/test_storage.py::test_store_deduplication
tests/integrations/google_drive/test_publisher.py::test_publisher_remote_idempotency
tests/integrations/google_drive/test_publisher.py::test_publisher_successful_chunked_upload
tests/integrations/google_drive/test_publisher.py::test_publisher_same_artifact_different_destinations
tests/integrations/google_drive/test_publisher.py::test_publisher_unknown_state_recovery_bounded_loop
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\src\images\models.py:63: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

tests/integration/test_phase6_bootstrap.py: 18 warnings
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\src\tools\browser\base.py:20: PydanticDeprecatedSince20: The `schema` method is deprecated; use `model_json_schema` instead. Deprecated in Pydantic V2.0 to be removed in V3.0. See Pydantic V2 Migration Guide at https://errors.pydantic.dev/2.13/migration/
    return self.get_arguments_schema().schema()

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================ 755 passed, 1533 warnings in 78.61s (0:01:18) ================

C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:207: PytestDeprecationWarning: The configuration option "asyncio_default_fixture_loop_scope" is unset.
The event loop scope for asynchronous fixtures will default to the fixture caching scope. Future versions of pytest-asyncio will default the loop scope for asynchronous fixtures to function scope. Set the default fixture loop scope explicitly in order to avoid unexpected behavior in the future. Valid fixture loop scopes are: "function", "class", "module", "package", "session"

  warnings.warn(PytestDeprecationWarning(_DEFAULT_FIXTURE_LOOP_SCOPE_UNSET))
```

## Risks / Notes
(none supplied)

## Generated
2026-08-17T18:06:23+07:00
