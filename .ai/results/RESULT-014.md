# RESULT-014

STATUS: READY_FOR_REVIEW

## Summary
TASK-014: Implemented AIOS Bridge v0.5-M1 External Brain typed contract foundation in src/aios_bridge/external_brain/ according to ADR-005.

## Task Metadata
- Task: `TASK-014`
- Action: `RUN`
- Authorized Artifact: `.ai/tasks/TASK-014.md (914a0947b1)`
- Base Main SHA: `540f4cb20b56cf72db333192d49ccf6eb295e9c4`
- Branch: `ai/task-014`

## Files Changed
- src/aios_bridge/
- tests/aios_bridge/

## Diff Stat
```text

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
collecting ... collected 17 items

tests/aios_bridge/external_brain/test_contracts.py::test_enum_string_values_match_adr005 PASSED [  5%]
tests/aios_bridge/external_brain/test_contracts.py::test_operation_to_expected_output_type_mapping PASSED [ 11%]
tests/aios_bridge/external_brain/test_contracts.py::test_context_item_immutability_and_validation PASSED [ 17%]
tests/aios_bridge/external_brain/test_contracts.py::test_model_request_validation PASSED [ 23%]
tests/aios_bridge/external_brain/test_contracts.py::test_model_response_validation PASSED [ 29%]
tests/aios_bridge/external_brain/test_contracts.py::test_validate_request_response_correlation PASSED [ 35%]
tests/aios_bridge/external_brain/test_contracts.py::test_deterministic_serialization_equality PASSED [ 41%]
tests/aios_bridge/external_brain/test_contracts.py::test_context_immutability_and_order_preservation PASSED [ 47%]
tests/aios_bridge/external_brain/test_output_contract.py::test_plan_structural_validation PASSED [ 52%]
tests/aios_bridge/external_brain/test_output_contract.py::test_patch_proposal_structural_validation_and_data_treatment PASSED [ 58%]
tests/aios_bridge/external_brain/test_output_contract.py::test_diagnosis_structural_validation PASSED [ 64%]
tests/aios_bridge/external_brain/test_output_contract.py::test_review_structural_validation_and_allowed_statuses PASSED [ 70%]
tests/aios_bridge/external_brain/test_provider_contract.py::test_provider_adapter_protocol_conformance PASSED [ 76%]
tests/aios_bridge/external_brain/test_provider_contract.py::test_runtime_llm_provider_remains_untouched PASSED [ 82%]
tests/aios_bridge/external_brain/test_transport_contract.py::test_transport_protocol_conformance PASSED [ 88%]
tests/aios_bridge/external_brain/test_transport_contract.py::test_transport_request_validation PASSED [ 94%]
tests/aios_bridge/external_brain/test_transport_contract.py::test_transport_result_validation PASSED [100%]

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
======================= 17 passed, 15 warnings in 0.06s =======================
........................................................................ [ 14%]
........................................................................ [ 29%]
........................................................................ [ 43%]
........................................................................ [ 58%]
........................................................................ [ 73%]
........................................................................ [ 87%]
...........................................................              [100%]
491 passed in 61.82s (0:01:01)

C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:207: PytestDeprecationWarning: The configuration option "asyncio_default_fixture_loop_scope" is unset.
The event loop scope for asynchronous fixtures will default to the fixture caching scope. Future versions of pytest-asyncio will default the loop scope for asynchronous fixtures to function scope. Set the default fixture loop scope explicitly in order to avoid unexpected behavior in the future. Valid fixture loop scopes are: "function", "class", "module", "package", "session"

  warnings.warn(PytestDeprecationWarning(_DEFAULT_FIXTURE_LOOP_SCOPE_UNSET))
C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:207: PytestDeprecationWarning: The configuration option "asyncio_default_fixture_loop_scope" is unset.
The event loop scope for asynchronous fixtures will default to the fixture caching scope. Future versions of pytest-asyncio will default the loop scope for asynchronous fixtures to function scope. Set the default fixture loop scope explicitly in order to avoid unexpected behavior in the future. Valid fixture loop scopes are: "function", "class", "module", "package", "session"

  warnings.warn(PytestDeprecationWarning(_DEFAULT_FIXTURE_LOOP_SCOPE_UNSET))
```

## Risks / Notes
### Implementation Details:
1. External Brain Subsystem (`src/aios_bridge/external_brain/`):
   - Enums: `ContextKind`, `BrainRole`, `BrainOperation`, `BrainOutputType`, `ModelResponseStatus` with stable string-backed values.
   - Value Objects & Contracts:
     - `ContextItem`: Frozen dataclass with strict validation for non-null string content, priority, and 64-hex SHA-256 validation.
     - `ModelRequest`: Frozen dataclass with `schema_version="1"`, `TASK-<digits>` ID validation, non-empty instruction, immutable context tuple, positive token limits, and strict operation-to-output-type mapping.
     - `ModelResponse`: Frozen dataclass with `schema_version="1"`, SUCCESS status constraints (non-empty content & non-null output_type), non-negative token/latency validation, and preservation of unknown usage as `None`.
     - `validate_request_response_correlation`: Strict correlation checking (matching request_id, task_id, and expected output_type for SUCCESS).
   - Protocols:
     - `ProviderAdapter`: Pure protocol with `provider_id` property and `async def invoke(request) -> ModelResponse`.
     - `ModelTransport`: Pure protocol with `async def send(request) -> TransportResult`.
     - `TransportRequest` & `TransportResult`: Clean HTTP boundary data structures with URL scheme and positive timeout validation.
   - Error Taxonomy (`errors.py`):
     - `ExternalBrainError`, `ContractValidationError`, `CorrelationError`, `OutputContractError`.
   - Structural Artifact Validation (`validation.py`):
     - Parsers and validators for `PLAN`, `PATCH_PROPOSAL`, `DIAGNOSIS`, `REVIEW` (`PASS` / `CHANGES_REQUIRED`).
2. Verification & Safety:
   - Zero external live model calls made (pure contract boundary).
   - Zero changes to protected files (`bridge.py`, `src/providers/base.py`, etc.).
   - Focused test suite (`tests/aios_bridge/external_brain/`): 17 passed.
   - Full repository test suite (`tests/`): 491 passed, 0 regressions.

## Generated
2026-08-16T12:28:38+07:00
