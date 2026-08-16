# RESULT-014

STATUS: READY_FOR_REVIEW

## Summary
TASK-014 FIX: Rejected unordered sets and non-finite floats in transport payload to ensure deterministic JSON wire serialization.

## Task Metadata
- Task: `TASK-014`
- Action: `FIX`
- Authorized Artifact: `.ai/reviews/REVIEW-014.md (fb2a4f4d47)`
- Base Main SHA: `(n/a)`
- Branch: `ai/task-014`

## Files Changed
- src/aios_bridge/external_brain/transport.py
- tests/aios_bridge/external_brain/test_transport_contract.py

## Diff Stat
```text
src/aios_bridge/external_brain/transport.py        | 19 +++++++++----
 .../external_brain/test_transport_contract.py      | 31 ++++++++++++++++++++++
 2 files changed, 45 insertions(+), 5 deletions(-)
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
collecting ... collected 20 items

tests/aios_bridge/external_brain/test_contracts.py::test_enum_string_values_match_adr005 PASSED [  5%]
tests/aios_bridge/external_brain/test_contracts.py::test_operation_to_expected_output_type_mapping PASSED [ 10%]
tests/aios_bridge/external_brain/test_contracts.py::test_context_item_immutability_and_validation PASSED [ 15%]
tests/aios_bridge/external_brain/test_contracts.py::test_model_request_validation PASSED [ 20%]
tests/aios_bridge/external_brain/test_contracts.py::test_model_response_validation PASSED [ 25%]
tests/aios_bridge/external_brain/test_contracts.py::test_model_response_rejects_contradictory_success_failure_metadata PASSED [ 30%]
tests/aios_bridge/external_brain/test_contracts.py::test_validate_request_response_correlation PASSED [ 35%]
tests/aios_bridge/external_brain/test_contracts.py::test_deterministic_serialization_equality PASSED [ 40%]
tests/aios_bridge/external_brain/test_contracts.py::test_context_immutability_and_order_preservation PASSED [ 45%]
tests/aios_bridge/external_brain/test_output_contract.py::test_plan_structural_validation PASSED [ 50%]
tests/aios_bridge/external_brain/test_output_contract.py::test_patch_proposal_structural_validation_and_data_treatment PASSED [ 55%]
tests/aios_bridge/external_brain/test_output_contract.py::test_diagnosis_structural_validation PASSED [ 60%]
tests/aios_bridge/external_brain/test_output_contract.py::test_review_structural_validation_and_allowed_statuses PASSED [ 65%]
tests/aios_bridge/external_brain/test_provider_contract.py::test_provider_adapter_protocol_conformance PASSED [ 70%]
tests/aios_bridge/external_brain/test_provider_contract.py::test_runtime_llm_provider_remains_untouched PASSED [ 75%]
tests/aios_bridge/external_brain/test_transport_contract.py::test_transport_protocol_conformance PASSED [ 80%]
tests/aios_bridge/external_brain/test_transport_contract.py::test_transport_request_validation PASSED [ 85%]
tests/aios_bridge/external_brain/test_transport_contract.py::test_transport_result_validation PASSED [ 90%]
tests/aios_bridge/external_brain/test_transport_contract.py::test_transport_request_deep_immutability_and_defensive_copy PASSED [ 95%]
tests/aios_bridge/external_brain/test_transport_contract.py::test_transport_request_json_payload_wire_serialization PASSED [100%]

============================== warnings summary ===============================
tests/aios_bridge/external_brain/test_contracts.py::test_enum_string_values_match_adr005
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
======================= 20 passed, 15 warnings in 0.06s =======================
........................................................................ [ 14%]
........................................................................ [ 29%]
........................................................................ [ 43%]
........................................................................ [ 58%]
........................................................................ [ 72%]
........................................................................ [ 87%]
..............................................................           [100%]
494 passed in 66.14s (0:01:06)

C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:207: PytestDeprecationWarning: The configuration option "asyncio_default_fixture_loop_scope" is unset.
The event loop scope for asynchronous fixtures will default to the fixture caching scope. Future versions of pytest-asyncio will default the loop scope for asynchronous fixtures to function scope. Set the default fixture loop scope explicitly in order to avoid unexpected behavior in the future. Valid fixture loop scopes are: "function", "class", "module", "package", "session"

  warnings.warn(PytestDeprecationWarning(_DEFAULT_FIXTURE_LOOP_SCOPE_UNSET))
C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:207: PytestDeprecationWarning: The configuration option "asyncio_default_fixture_loop_scope" is unset.
The event loop scope for asynchronous fixtures will default to the fixture caching scope. Future versions of pytest-asyncio will default the loop scope for asynchronous fixtures to function scope. Set the default fixture loop scope explicitly in order to avoid unexpected behavior in the future. Valid fixture loop scopes are: "function", "class", "module", "package", "session"

  warnings.warn(PytestDeprecationWarning(_DEFAULT_FIXTURE_LOOP_SCOPE_UNSET))
```

## Risks / Notes
### Corrections Implemented (Review Round 3 Fixes):
1. Rejection of Unordered Sets & Non-Finite Floats:
   - Updated `_validate_and_freeze_payload` in `src/aios_bridge/external_brain/transport.py` to strictly reject `set` and `frozenset` with `ContractValidationError` instead of non-deterministically coercing them to tuples.
   - Strictly enforced finite floats (rejecting `NaN`, `+Inf`, `-Inf`) via `math.isfinite()`.
2. Regression Tests Added:
   - Added tests in `tests/aios_bridge/external_brain/test_transport_contract.py` asserting deterministic rejection of `set`, `frozenset`, `NaN`, and `Inf`.
3. Invariants Preserved:
   - Zero live external-model calls.
   - Zero changes to protected files (`bridge.py`, `src/providers/base.py`, `src/providers/gemini.py`, AgentLoop, etc.).
   - Focused test suite (`tests/aios_bridge/external_brain/`): 20 passed.
   - Full repository test suite (`tests/`): 494 passed, 0 regressions.

## Generated
2026-08-16T12:46:22+07:00
