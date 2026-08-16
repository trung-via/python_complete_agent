# RESULT-015

STATUS: READY_FOR_REVIEW

## Summary
TASK-015 FIX: Implemented normalized-path separator tie-breaking for deterministic candidate ranking in ContextBuilder.

## Task Metadata
- Task: `TASK-015`
- Action: `FIX`
- Authorized Artifact: `.ai/reviews/REVIEW-015.md (7dc4745b4f)`
- Base Main SHA: `(n/a)`
- Branch: `ai/task-015`

## Files Changed
- src/aios_bridge/external_brain/context.py
- tests/aios_bridge/external_brain/test_context_builder.py

## Diff Stat
```text
src/aios_bridge/external_brain/context.py          | 15 +++--
 .../external_brain/test_context_builder.py         | 64 ++++++++++++++++++++++
 2 files changed, 74 insertions(+), 5 deletions(-)
```

## Tests
Command: `.\venv\Scripts\python -m pytest tests/aios_bridge/external_brain/ -v && .\venv\Scripts\python -m pytest tests/ -q -W ignore`  
Exit code: 0

```text
============================= test session starts =============================
platform win32 -- Python 3.14.7, pytest-8.3.4, pluggy-1.6.0 -- C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent
plugins: anyio-4.14.2, asyncio-0.25.0
asyncio: mode=Mode.STRICT, asyncio_default_fixture_loop_scope=None
collecting ... collected 43 items

tests/aios_bridge/external_brain/test_context_budget.py::test_utf8_conservative_counter_properties_and_determinism PASSED [  2%]
tests/aios_bridge/external_brain/test_context_budget.py::test_token_counter_protocol_conformance PASSED [  4%]
tests/aios_bridge/external_brain/test_context_budget.py::test_context_budget_validation PASSED [  6%]
tests/aios_bridge/external_brain/test_context_budget.py::test_context_budget_to_dict PASSED [  9%]
tests/aios_bridge/external_brain/test_context_builder.py::test_canonical_context_rendering PASSED [ 11%]
tests/aios_bridge/external_brain/test_context_builder.py::test_integrity_verification_sha_matching_and_mismatch PASSED [ 13%]
tests/aios_bridge/external_brain/test_context_builder.py::test_sensitive_context_safety_gate_path_rejections PASSED [ 16%]
tests/aios_bridge/external_brain/test_context_builder.py::test_sensitive_context_safety_gate_content_rejections PASSED [ 18%]
tests/aios_bridge/external_brain/test_context_builder.py::test_missing_mandatory_task_error PASSED [ 20%]
tests/aios_bridge/external_brain/test_context_builder.py::test_contract_is_mandatory_when_supplied PASSED [ 23%]
tests/aios_bridge/external_brain/test_context_builder.py::test_mandatory_context_overflow_fails_closed PASSED [ 25%]
tests/aios_bridge/external_brain/test_context_builder.py::test_exact_deduplication_collapses_duplicates_and_audits PASSED [ 27%]
tests/aios_bridge/external_brain/test_context_builder.py::test_different_path_or_kind_does_not_dedupe PASSED [ 30%]
tests/aios_bridge/external_brain/test_context_builder.py::test_input_permutation_invariance_and_stable_fingerprint PASSED [ 32%]
tests/aios_bridge/external_brain/test_context_builder.py::test_optional_ranking_order_priority_kind_path_digest PASSED [ 34%]
tests/aios_bridge/external_brain/test_context_builder.py::test_atomic_greedy_budget_selection_and_skipping PASSED [ 37%]
tests/aios_bridge/external_brain/test_context_builder.py::test_context_build_result_immutability_and_audit PASSED [ 39%]
tests/aios_bridge/external_brain/test_context_builder.py::test_invalid_counter_returns_rejected PASSED [ 41%]
tests/aios_bridge/external_brain/test_context_builder.py::test_fingerprint_sensitivity PASSED [ 44%]
tests/aios_bridge/external_brain/test_context_builder.py::test_builder_exactness_metadata PASSED [ 46%]
tests/aios_bridge/external_brain/test_context_builder.py::test_context_builder_purity_no_filesystem_side_effects PASSED [ 48%]
tests/aios_bridge/external_brain/test_context_builder.py::test_normalized_path_separator_ranking_tie_breaks PASSED [ 51%]
tests/aios_bridge/external_brain/test_context_builder.py::test_atomic_budget_selection_follows_normalized_path_tie_break PASSED [ 53%]
tests/aios_bridge/external_brain/test_contracts.py::test_enum_string_values_match_adr005 PASSED [ 55%]
tests/aios_bridge/external_brain/test_contracts.py::test_operation_to_expected_output_type_mapping PASSED [ 58%]
tests/aios_bridge/external_brain/test_contracts.py::test_context_item_immutability_and_validation PASSED [ 60%]
tests/aios_bridge/external_brain/test_contracts.py::test_model_request_validation PASSED [ 62%]
tests/aios_bridge/external_brain/test_contracts.py::test_model_response_validation PASSED [ 65%]
tests/aios_bridge/external_brain/test_contracts.py::test_model_response_rejects_contradictory_success_failure_metadata PASSED [ 67%]
tests/aios_bridge/external_brain/test_contracts.py::test_validate_request_response_correlation PASSED [ 69%]
tests/aios_bridge/external_brain/test_contracts.py::test_deterministic_serialization_equality PASSED [ 72%]
tests/aios_bridge/external_brain/test_contracts.py::test_context_immutability_and_order_preservation PASSED [ 74%]
tests/aios_bridge/external_brain/test_output_contract.py::test_plan_structural_validation PASSED [ 76%]
tests/aios_bridge/external_brain/test_output_contract.py::test_patch_proposal_structural_validation_and_data_treatment PASSED [ 79%]
tests/aios_bridge/external_brain/test_output_contract.py::test_diagnosis_structural_validation PASSED [ 81%]
tests/aios_bridge/external_brain/test_output_contract.py::test_review_structural_validation_and_allowed_statuses PASSED [ 83%]
tests/aios_bridge/external_brain/test_provider_contract.py::test_provider_adapter_protocol_conformance PASSED [ 86%]
tests/aios_bridge/external_brain/test_provider_contract.py::test_runtime_llm_provider_remains_untouched PASSED [ 88%]
tests/aios_bridge/external_brain/test_transport_contract.py::test_transport_protocol_conformance PASSED [ 90%]
tests/aios_bridge/external_brain/test_transport_contract.py::test_transport_request_validation PASSED [ 93%]
tests/aios_bridge/external_brain/test_transport_contract.py::test_transport_result_validation PASSED [ 95%]
tests/aios_bridge/external_brain/test_transport_contract.py::test_transport_request_deep_immutability_and_defensive_copy PASSED [ 97%]
tests/aios_bridge/external_brain/test_transport_contract.py::test_transport_request_json_payload_wire_serialization PASSED [100%]

============================== warnings summary ===============================
tests/aios_bridge/external_brain/test_context_budget.py::test_utf8_conservative_counter_properties_and_determinism
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:1153: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    return asyncio.get_event_loop_policy()

tests/aios_bridge/external_brain/test_provider_contract.py::test_provider_adapter_protocol_conformance
tests/aios_bridge/external_brain/test_transport_contract.py::test_transport_protocol_conformance
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:844: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    _restore_event_loop_policy(asyncio.get_event_loop_policy()),

tests/aios_bridge/external_brain/test_provider_contract.py::test_provider_adapter_protocol_conformance
tests/aios_bridge/external_brain/test_transport_contract.py::test_transport_protocol_conformance
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:1125: DeprecationWarning: 'asyncio.set_event_loop_policy' is deprecated and slated for removal in Python 3.16
    asyncio.set_event_loop_policy(new_loop_policy)

tests/aios_bridge/external_brain/test_provider_contract.py::test_provider_adapter_protocol_conformance
tests/aios_bridge/external_brain/test_transport_contract.py::test_transport_protocol_conformance
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:1126: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    loop = asyncio.get_event_loop_policy().new_event_loop()

tests/aios_bridge/external_brain/test_provider_contract.py::test_provider_adapter_protocol_conformance
tests/aios_bridge/external_brain/test_transport_contract.py::test_transport_protocol_conformance
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:859: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    policy = asyncio.get_event_loop_policy()

tests/aios_bridge/external_brain/test_provider_contract.py::test_provider_adapter_protocol_conformance
tests/aios_bridge/external_brain/test_transport_contract.py::test_transport_protocol_conformance
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:904: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    policy = asyncio.get_event_loop_policy()

tests/aios_bridge/external_brain/test_provider_contract.py::test_provider_adapter_protocol_conformance
tests/aios_bridge/external_brain/test_transport_contract.py::test_transport_protocol_conformance
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:928: DeprecationWarning: 'asyncio.set_event_loop_policy' is deprecated and slated for removal in Python 3.16
    asyncio.set_event_loop_policy(previous_policy)

tests/aios_bridge/external_brain/test_provider_contract.py::test_provider_adapter_protocol_conformance
tests/aios_bridge/external_brain/test_transport_contract.py::test_transport_protocol_conformance
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:940: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    policy = asyncio.get_event_loop_policy()

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================= 43 passed, 15 warnings in 0.09s =======================
........................................................................ [ 13%]
........................................................................ [ 27%]
........................................................................ [ 41%]
........................................................................ [ 55%]
........................................................................ [ 69%]
........................................................................ [ 83%]
........................................................................ [ 97%]
.............                                                            [100%]
517 passed in 54.84s

C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:207: PytestDeprecationWarning: The configuration option "asyncio_default_fixture_loop_scope" is unset.
The event loop scope for asynchronous fixtures will default to the fixture caching scope. Future versions of pytest-asyncio will default the loop scope for asynchronous fixtures to function scope. Set the default fixture loop scope explicitly in order to avoid unexpected behavior in the future. Valid fixture loop scopes are: "function", "class", "module", "package", "session"

  warnings.warn(PytestDeprecationWarning(_DEFAULT_FIXTURE_LOOP_SCOPE_UNSET))
C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:207: PytestDeprecationWarning: The configuration option "asyncio_default_fixture_loop_scope" is unset.
The event loop scope for asynchronous fixtures will default to the fixture caching scope. Future versions of pytest-asyncio will default the loop scope for asynchronous fixtures to function scope. Set the default fixture loop scope explicitly in order to avoid unexpected behavior in the future. Valid fixture loop scopes are: "function", "class", "module", "package", "session"

  warnings.warn(PytestDeprecationWarning(_DEFAULT_FIXTURE_LOOP_SCOPE_UNSET))
```

## Risks / Notes
### Corrections Implemented (Review Round 1 Fixes):
1. Normalized Path Separator Tie-Break (`src/aios_bridge/external_brain/context.py`):
   - Added `_normalized_sort_path(path)` converting `\` to `/` for deterministic lexical tie-breaks across OS platforms.
   - Applied `_normalized_sort_path` to mandatory TASK sorting, mandatory CONTRACT sorting, optional ranking, and audit exclusion sorting.
2. Regression Tests Added (`tests/aios_bridge/external_brain/test_context_builder.py`):
   - Added `test_normalized_path_separator_ranking_tie_breaks` asserting that mixed `\` and `/` paths sort consistently by normalized `/` order.
   - Added `test_atomic_budget_selection_follows_normalized_path_tie_break` asserting that atomic greedy budget selection picks the winner based on normalized path ordering regardless of input ordering.
3. Invariants Preserved:
   - Zero live external model calls.
   - Zero changes to protected files (`bridge.py`, `src/providers/base.py`, etc.).
   - Focused test suite (`tests/aios_bridge/external_brain/`): 43 passed.
   - Full repository test suite (`tests/`): 517 passed, 0 regressions.

## Generated
2026-08-16T13:06:04+07:00
