# RESULT-015

STATUS: READY_FOR_REVIEW

## Summary
TASK-015: Implemented AIOS Bridge v0.5-M2 Deterministic ContextBuilder, Token Budget, and Sensitive Context Safety Gate according to ADR-006.

## Task Metadata
- Task: `TASK-015`
- Action: `RUN`
- Authorized Artifact: `.ai/tasks/TASK-015.md (fc3012e4af)`
- Base Main SHA: `34b331c75d0577e403bb80b2ba0fe9818183b4f9`
- Branch: `ai/task-015`

## Files Changed
- src/aios_bridge/external_brain/__init__.py
- src/aios_bridge/external_brain/errors.py
- src/aios_bridge/external_brain/budget.py
- src/aios_bridge/external_brain/context.py
- tests/aios_bridge/external_brain/test_context_budget.py
- tests/aios_bridge/external_brain/test_context_builder.py

## Diff Stat
```text
src/aios_bridge/external_brain/__init__.py | 28 ++++++++++++++++++++++++++++
 src/aios_bridge/external_brain/errors.py   | 20 ++++++++++++++++++++
 2 files changed, 48 insertions(+)
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
collecting ... collected 41 items

tests/aios_bridge/external_brain/test_context_budget.py::test_utf8_conservative_counter_properties_and_determinism PASSED [  2%]
tests/aios_bridge/external_brain/test_context_budget.py::test_token_counter_protocol_conformance PASSED [  4%]
tests/aios_bridge/external_brain/test_context_budget.py::test_context_budget_validation PASSED [  7%]
tests/aios_bridge/external_brain/test_context_budget.py::test_context_budget_to_dict PASSED [  9%]
tests/aios_bridge/external_brain/test_context_builder.py::test_canonical_context_rendering PASSED [ 12%]
tests/aios_bridge/external_brain/test_context_builder.py::test_integrity_verification_sha_matching_and_mismatch PASSED [ 14%]
tests/aios_bridge/external_brain/test_context_builder.py::test_sensitive_context_safety_gate_path_rejections PASSED [ 17%]
tests/aios_bridge/external_brain/test_context_builder.py::test_sensitive_context_safety_gate_content_rejections PASSED [ 19%]
tests/aios_bridge/external_brain/test_context_builder.py::test_missing_mandatory_task_error PASSED [ 21%]
tests/aios_bridge/external_brain/test_context_builder.py::test_contract_is_mandatory_when_supplied PASSED [ 24%]
tests/aios_bridge/external_brain/test_context_builder.py::test_mandatory_context_overflow_fails_closed PASSED [ 26%]
tests/aios_bridge/external_brain/test_context_builder.py::test_exact_deduplication_collapses_duplicates_and_audits PASSED [ 29%]
tests/aios_bridge/external_brain/test_context_builder.py::test_different_path_or_kind_does_not_dedupe PASSED [ 31%]
tests/aios_bridge/external_brain/test_context_builder.py::test_input_permutation_invariance_and_stable_fingerprint PASSED [ 34%]
tests/aios_bridge/external_brain/test_context_builder.py::test_optional_ranking_order_priority_kind_path_digest PASSED [ 36%]
tests/aios_bridge/external_brain/test_context_builder.py::test_atomic_greedy_budget_selection_and_skipping PASSED [ 39%]
tests/aios_bridge/external_brain/test_context_builder.py::test_context_build_result_immutability_and_audit PASSED [ 41%]
tests/aios_bridge/external_brain/test_context_builder.py::test_invalid_counter_returns_rejected PASSED [ 43%]
tests/aios_bridge/external_brain/test_context_builder.py::test_fingerprint_sensitivity PASSED [ 46%]
tests/aios_bridge/external_brain/test_context_builder.py::test_builder_exactness_metadata PASSED [ 48%]
tests/aios_bridge/external_brain/test_context_builder.py::test_context_builder_purity_no_filesystem_side_effects PASSED [ 51%]
tests/aios_bridge/external_brain/test_contracts.py::test_enum_string_values_match_adr005 PASSED [ 53%]
tests/aios_bridge/external_brain/test_contracts.py::test_operation_to_expected_output_type_mapping PASSED [ 56%]
tests/aios_bridge/external_brain/test_contracts.py::test_context_item_immutability_and_validation PASSED [ 58%]
tests/aios_bridge/external_brain/test_contracts.py::test_model_request_validation PASSED [ 60%]
tests/aios_bridge/external_brain/test_contracts.py::test_model_response_validation PASSED [ 63%]
tests/aios_bridge/external_brain/test_contracts.py::test_model_response_rejects_contradictory_success_failure_metadata PASSED [ 65%]
tests/aios_bridge/external_brain/test_contracts.py::test_validate_request_response_correlation PASSED [ 68%]
tests/aios_bridge/external_brain/test_contracts.py::test_deterministic_serialization_equality PASSED [ 70%]
tests/aios_bridge/external_brain/test_contracts.py::test_context_immutability_and_order_preservation PASSED [ 73%]
tests/aios_bridge/external_brain/test_output_contract.py::test_plan_structural_validation PASSED [ 75%]
tests/aios_bridge/external_brain/test_output_contract.py::test_patch_proposal_structural_validation_and_data_treatment PASSED [ 78%]
tests/aios_bridge/external_brain/test_output_contract.py::test_diagnosis_structural_validation PASSED [ 80%]
tests/aios_bridge/external_brain/test_output_contract.py::test_review_structural_validation_and_allowed_statuses PASSED [ 82%]
tests/aios_bridge/external_brain/test_provider_contract.py::test_provider_adapter_protocol_conformance PASSED [ 85%]
tests/aios_bridge/external_brain/test_provider_contract.py::test_runtime_llm_provider_remains_untouched PASSED [ 87%]
tests/aios_bridge/external_brain/test_transport_contract.py::test_transport_protocol_conformance PASSED [ 90%]
tests/aios_bridge/external_brain/test_transport_contract.py::test_transport_request_validation PASSED [ 92%]
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
======================= 41 passed, 15 warnings in 0.09s =======================
........................................................................ [ 13%]
........................................................................ [ 27%]
........................................................................ [ 41%]
........................................................................ [ 55%]
........................................................................ [ 69%]
........................................................................ [ 83%]
........................................................................ [ 97%]
...........                                                              [100%]
515 passed in 54.53s

C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:207: PytestDeprecationWarning: The configuration option "asyncio_default_fixture_loop_scope" is unset.
The event loop scope for asynchronous fixtures will default to the fixture caching scope. Future versions of pytest-asyncio will default the loop scope for asynchronous fixtures to function scope. Set the default fixture loop scope explicitly in order to avoid unexpected behavior in the future. Valid fixture loop scopes are: "function", "class", "module", "package", "session"

  warnings.warn(PytestDeprecationWarning(_DEFAULT_FIXTURE_LOOP_SCOPE_UNSET))
C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:207: PytestDeprecationWarning: The configuration option "asyncio_default_fixture_loop_scope" is unset.
The event loop scope for asynchronous fixtures will default to the fixture caching scope. Future versions of pytest-asyncio will default the loop scope for asynchronous fixtures to function scope. Set the default fixture loop scope explicitly in order to avoid unexpected behavior in the future. Valid fixture loop scopes are: "function", "class", "module", "package", "session"

  warnings.warn(PytestDeprecationWarning(_DEFAULT_FIXTURE_LOOP_SCOPE_UNSET))
```

## Risks / Notes
### Implementation Details (v0.5-M2):
1. Token Budget & Counter Subsystem (`src/aios_bridge/external_brain/budget.py`):
   - `TokenCounter(Protocol)`: `counter_id`, `is_exact`, `count(text) -> int`.
   - `Utf8ByteConservativeCounter`: Conservative dependency-free default (`counter_id="utf8-byte-conservative-v1"`, `is_exact=False`, UTF-8 byte counting).
   - `ContextBudget`: Frozen dataclass validating positive `max_context_tokens`, non-negative `protocol_reserve_tokens < max_context_tokens`, and exposing `available_context_tokens`.
2. Deterministic ContextBuilder & Safety Gate (`src/aios_bridge/external_brain/context.py`):
   - Canonical Context Rendering: `render_context_item(item)` deterministically frames kind, path, and unmodified content.
   - Sensitive Context Safety Gate: Path-based rejection of `.env*` (including `.env.example`), `.pem`, `.key`, `id_rsa*`, `id_ed25519*`, `Cookies`, `Login Data`, `Web Data`; Content-based rejection of private key markers (`BEGIN PRIVATE KEY`, etc.) without echoing secret content.
   - Integrity Verification: Computed SHA-256 vs `content_sha256` matching (hard-fail on mismatch with `ContextIntegrityError`).
   - Exact Deduplication: Identity `(kind, path, sha256)` deduplication; duplicates recorded in audit with reason `DUPLICATE`.
   - Mandatory Context: Enforced at least one `TASK` item (otherwise `MissingMandatoryContextError`); `TASK` and `CONTRACT` items are mandatory and cannot be dropped or truncated; mandatory overflow fails closed (`MandatoryContextBudgetError`).
   - Deterministic Optional Ranking: Priority -> Kind Precedence (ERROR/DIFF 80 > TEST 70 > SOURCE 60 > ARCHITECTURE 50) -> Path -> Digest.
   - Atomic Greedy Budget Selection: Bounded by `available_context_tokens`; oversized optional items skipped atomically (`BUDGET` exclusion) while subsequent fitting items are evaluated.
   - Audit & Fingerprint: Immutable `ContextBuildResult` and `ContextExclusion` records; SHA-256 `context_fingerprint` computed over canonical selection/budget/counter state.
   - Purity: Pure in-memory selector; zero repository/filesystem crawling.
3. Test Coverage:
   - `tests/aios_bridge/external_brain/test_context_budget.py` (4 tests)
   - `tests/aios_bridge/external_brain/test_context_builder.py` (17 tests)
   - Total focused External Brain suite: 41 passed.
   - Full repository suite: 515 passed, 0 regressions.
4. Invariants Preserved:
   - Zero live external model calls.
   - Zero changes to protected files (`bridge.py`, `src/providers/base.py`, etc.).

## Generated
2026-08-16T12:58:57+07:00
