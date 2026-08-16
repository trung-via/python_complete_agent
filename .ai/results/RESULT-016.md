# RESULT-016

STATUS: READY_FOR_REVIEW

## Summary
Fix ADR-007 contracts: request.provider=None support, tri-state ledger_persisted, bounded ledger_error_code, ADR-007 UsageRecord schema, embedded reasoning fail-closed check, bounded provider status_msg

## Task Metadata
- Task: `TASK-016`
- Action: `FIX`
- Authorized Artifact: `.ai/reviews/REVIEW-016.md (b17321c88a)`
- Base Main SHA: `(n/a)`
- Branch: `ai/task-016`

## Files Changed
- src/aios_bridge/external_brain/gateway.py
- src/aios_bridge/external_brain/providers/minimax.py
- src/aios_bridge/external_brain/usage.py
- tests/aios_bridge/external_brain/test_gateway.py
- tests/aios_bridge/external_brain/test_minimax_provider.py
- tests/aios_bridge/external_brain/test_usage.py

## Diff Stat
```text
src/aios_bridge/external_brain/gateway.py          |  51 +++++----
 .../external_brain/providers/minimax.py            |  58 ++++++++---
 src/aios_bridge/external_brain/usage.py            | 112 +++++++++++---------
 tests/aios_bridge/external_brain/test_gateway.py   |  58 ++++++++---
 .../external_brain/test_minimax_provider.py        |  51 ++++++++-
 tests/aios_bridge/external_brain/test_usage.py     | 116 +++++++++++++--------
 6 files changed, 295 insertions(+), 151 deletions(-)
```

## Tests
Command: `.\venv\Scripts\pytest tests/aios_bridge/external_brain/ -q`  
Exit code: 0

```text
.....................................................................    [100%]
============================== warnings summary ===============================
tests/aios_bridge/external_brain/test_context_budget.py::test_utf8_conservative_counter_properties_and_determinism
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:1153: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    return asyncio.get_event_loop_policy()

tests/aios_bridge/external_brain/test_gateway.py: 7 warnings
tests/aios_bridge/external_brain/test_minimax_provider.py: 5 warnings
tests/aios_bridge/external_brain/test_provider_contract.py: 1 warning
tests/aios_bridge/external_brain/test_transport.py: 5 warnings
tests/aios_bridge/external_brain/test_transport_contract.py: 1 warning
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:844: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    _restore_event_loop_policy(asyncio.get_event_loop_policy()),

tests/aios_bridge/external_brain/test_gateway.py: 7 warnings
tests/aios_bridge/external_brain/test_minimax_provider.py: 5 warnings
tests/aios_bridge/external_brain/test_provider_contract.py: 1 warning
tests/aios_bridge/external_brain/test_transport.py: 5 warnings
tests/aios_bridge/external_brain/test_transport_contract.py: 1 warning
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:1125: DeprecationWarning: 'asyncio.set_event_loop_policy' is deprecated and slated for removal in Python 3.16
    asyncio.set_event_loop_policy(new_loop_policy)

tests/aios_bridge/external_brain/test_gateway.py: 7 warnings
tests/aios_bridge/external_brain/test_minimax_provider.py: 5 warnings
tests/aios_bridge/external_brain/test_provider_contract.py: 1 warning
tests/aios_bridge/external_brain/test_transport.py: 5 warnings
tests/aios_bridge/external_brain/test_transport_contract.py: 1 warning
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:1126: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    loop = asyncio.get_event_loop_policy().new_event_loop()

tests/aios_bridge/external_brain/test_gateway.py: 7 warnings
tests/aios_bridge/external_brain/test_minimax_provider.py: 5 warnings
tests/aios_bridge/external_brain/test_provider_contract.py: 1 warning
tests/aios_bridge/external_brain/test_transport.py: 5 warnings
tests/aios_bridge/external_brain/test_transport_contract.py: 1 warning
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:859: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    policy = asyncio.get_event_loop_policy()

tests/aios_bridge/external_brain/test_gateway.py: 7 warnings
tests/aios_bridge/external_brain/test_minimax_provider.py: 5 warnings
tests/aios_bridge/external_brain/test_provider_contract.py: 1 warning
tests/aios_bridge/external_brain/test_transport.py: 5 warnings
tests/aios_bridge/external_brain/test_transport_contract.py: 1 warning
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:904: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    policy = asyncio.get_event_loop_policy()

tests/aios_bridge/external_brain/test_gateway.py: 7 warnings
tests/aios_bridge/external_brain/test_minimax_provider.py: 5 warnings
tests/aios_bridge/external_brain/test_provider_contract.py: 1 warning
tests/aios_bridge/external_brain/test_transport.py: 5 warnings
tests/aios_bridge/external_brain/test_transport_contract.py: 1 warning
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:928: DeprecationWarning: 'asyncio.set_event_loop_policy' is deprecated and slated for removal in Python 3.16
    asyncio.set_event_loop_policy(previous_policy)

tests/aios_bridge/external_brain/test_gateway.py: 7 warnings
tests/aios_bridge/external_brain/test_minimax_provider.py: 5 warnings
tests/aios_bridge/external_brain/test_provider_contract.py: 1 warning
tests/aios_bridge/external_brain/test_transport.py: 5 warnings
tests/aios_bridge/external_brain/test_transport_contract.py: 1 warning
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:940: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    policy = asyncio.get_event_loop_policy()

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
69 passed, 134 warnings in 0.22s

C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:207: PytestDeprecationWarning: The configuration option "asyncio_default_fixture_loop_scope" is unset.
The event loop scope for asynchronous fixtures will default to the fixture caching scope. Future versions of pytest-asyncio will default the loop scope for asynchronous fixtures to function scope. Set the default fixture loop scope explicitly in order to avoid unexpected behavior in the future. Valid fixture loop scopes are: "function", "class", "module", "package", "session"

  warnings.warn(PytestDeprecationWarning(_DEFAULT_FIXTURE_LOOP_SCOPE_UNSET))
```

## Risks / Notes
(none supplied)

## Generated
2026-08-16T13:37:10+07:00
