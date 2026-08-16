# RESULT-014

STATUS: READY_FOR_REVIEW

## Summary
TASK-014 FIX: Implemented deep immutability for TransportRequest and rejected contradictory error metadata on ModelResponse(SUCCESS).

## Task Metadata
- Task: `TASK-014`
- Action: `FIX`
- Authorized Artifact: `.ai/reviews/REVIEW-014.md (25df1c3e9e)`
- Base Main SHA: `(n/a)`
- Branch: `ai/task-014`

## Files Changed
- src/aios_bridge/external_brain/contracts.py
- src/aios_bridge/external_brain/transport.py
- tests/aios_bridge/external_brain/test_contracts.py
- tests/aios_bridge/external_brain/test_transport_contract.py

## Diff Stat
```text
src/aios_bridge/external_brain/contracts.py        | 16 +++--
 src/aios_bridge/external_brain/transport.py        | 34 ++++++++--
 tests/aios_bridge/external_brain/test_contracts.py | 78 ++++++++++++++++++++++
 .../external_brain/test_transport_contract.py      | 48 ++++++++++++-
 4 files changed, 165 insertions(+), 11 deletions(-)
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
collecting ... collected 19 items

tests/aios_bridge/external_brain/test_contracts.py::test_enum_string_values_match_adr005 PASSED [  5%]
tests/aios_bridge/external_brain/test_contracts.py::test_operation_to_expected_output_type_mapping PASSED [ 10%]
tests/aios_bridge/external_brain/test_contracts.py::test_context_item_immutability_and_validation PASSED [ 15%]
tests/aios_bridge/external_brain/test_contracts.py::test_model_request_validation PASSED [ 21%]
tests/aios_bridge/external_brain/test_contracts.py::test_model_response_validation PASSED [ 26%]
tests/aios_bridge/external_brain/test_contracts.py::test_model_response_rejects_contradictory_success_failure_metadata PASSED [ 31%]
tests/aios_bridge/external_brain/test_contracts.py::test_validate_request_response_correlation PASSED [ 36%]
tests/aios_bridge/external_brain/test_contracts.py::test_deterministic_serialization_equality PASSED [ 42%]
tests/aios_bridge/external_brain/test_contracts.py::test_context_immutability_and_order_preservation PASSED [ 47%]
tests/aios_bridge/external_brain/test_output_contract.py::test_plan_structural_validation PASSED [ 52%]
tests/aios_bridge/external_brain/test_output_contract.py::test_patch_proposal_structural_validation_and_data_treatment PASSED [ 57%]
tests/aios_bridge/external_brain/test_output_contract.py::test_diagnosis_structural_validation PASSED [ 63%]
tests/aios_bridge/external_brain/test_output_contract.py::test_review_structural_validation_and_allowed_statuses PASSED [ 68%]
tests/aios_bridge/external_brain/test_provider_contract.py::test_provider_adapter_protocol_conformance PASSED [ 73%]
tests/aios_bridge/external_brain/test_provider_contract.py::test_runtime_llm_provider_remains_untouched PASSED [ 78%]
tests/aios_bridge/external_brain/test_transport_contract.py::test_transport_protocol_conformance PASSED [ 84%]
tests/aios_bridge/external_brain/test_transport_contract.py::test_transport_request_validation PASSED [ 89%]
tests/aios_bridge/external_brain/test_transport_contract.py::test_transport_result_validation PASSED [ 94%]
tests/aios_bridge/external_brain/test_transport_contract.py::test_transport_request_deep_immutability_and_defensive_copy PASSED [100%]

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
======================= 19 passed, 15 warnings in 0.07s =======================
........................................................................ [ 14%]
........................................................................ [ 29%]
........................................................................ [ 43%]
........................................................................ [ 58%]
........................................................................ [ 73%]
........................................................................ [ 87%]
.............................................................            [100%]
493 passed in 58.80s

C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:207: PytestDeprecationWarning: The configuration option "asyncio_default_fixture_loop_scope" is unset.
The event loop scope for asynchronous fixtures will default to the fixture caching scope. Future versions of pytest-asyncio will default the loop scope for asynchronous fixtures to function scope. Set the default fixture loop scope explicitly in order to avoid unexpected behavior in the future. Valid fixture loop scopes are: "function", "class", "module", "package", "session"

  warnings.warn(PytestDeprecationWarning(_DEFAULT_FIXTURE_LOOP_SCOPE_UNSET))
C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:207: PytestDeprecationWarning: The configuration option "asyncio_default_fixture_loop_scope" is unset.
The event loop scope for asynchronous fixtures will default to the fixture caching scope. Future versions of pytest-asyncio will default the loop scope for asynchronous fixtures to function scope. Set the default fixture loop scope explicitly in order to avoid unexpected behavior in the future. Valid fixture loop scopes are: "function", "class", "module", "package", "session"

  warnings.warn(PytestDeprecationWarning(_DEFAULT_FIXTURE_LOOP_SCOPE_UNSET))
```

## Risks / Notes
### Corrections Implemented (Review Round 1 Fixes):
1. Fixed Blocker 1 (`TransportRequest` Deep Immutability):
   - Implemented `_deep_freeze` in `src/aios_bridge/external_brain/transport.py` converting dicts/mappings into `MappingProxyType`, lists to `tuple`, and sets to `frozenset`.
   - Both `headers` and `payload` (including arbitrary nested structures) are now deeply frozen and defensively copied during `TransportRequest.__post_init__`.
   - Caller mutations after construction or direct mutation attempts on `req.headers` / `req.payload` are prevented.
   - Added regression test `test_transport_request_deep_immutability_and_defensive_copy` in `tests/aios_bridge/external_brain/test_transport_contract.py`.
2. Fixed Blocker 2 (`ModelResponse(SUCCESS)` Contradictory Metadata):
   - `ModelResponse.__post_init__` now strictly rejects `error_code` and `error_message` when `status == ModelResponseStatus.SUCCESS`.
   - Added regression test `test_model_response_rejects_contradictory_success_failure_metadata` in `tests/aios_bridge/external_brain/test_contracts.py`.
3. Non-Blocking Hardening:
   - Added `not isinstance(..., bool)` checks to all integer/numeric fields (`priority`, `max_input_tokens`, `max_output_tokens`, `input_tokens`, `output_tokens`, `latency_ms`, `timeout_seconds`, `status_code`).
4. Invariants Preserved:
   - Zero live external-model calls.
   - Zero changes to protected files (`bridge.py`, `src/providers/base.py`, `src/providers/gemini.py`, AgentLoop, etc.).
   - Focused test suite (`tests/aios_bridge/external_brain/`): 19 passed.
   - Full repository test suite (`tests/`): 493 passed, 0 regressions.

## Generated
2026-08-16T12:35:41+07:00
