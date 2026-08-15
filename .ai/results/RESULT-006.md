# RESULT-006

STATUS: READY_FOR_REVIEW

## Summary
Fix TASK-006: invalidate RUN auth on CHANGES_REQUIRED review and reject malformed task artifacts

## Task Metadata
- Task: `TASK-006`
- Action: `FIX`
- Authorized Artifact: `.ai/reviews/REVIEW-006.md (ea3d6585bb)`
- Base Main SHA: `(n/a)`
- Branch: `ai/task-006`

## Files Changed
- bridge.py
- tests/test_bridge.py

## Diff Stat
```text
bridge.py            |  28 +++++++-
 tests/test_bridge.py | 190 ++++++++++++++++++++++++++++++++++++++++++++++++++-
 2 files changed, 215 insertions(+), 3 deletions(-)
```

## Tests
Command: `.\venv\Scripts\python -m pytest tests/ -q -W ignore`  
Exit code: 0

```text
........................................................................ [ 25%]
........................................................................ [ 51%]
........................................................................ [ 76%]
..................................................................       [100%]
282 passed in 30.47s

C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:207: PytestDeprecationWarning: The configuration option "asyncio_default_fixture_loop_scope" is unset.
The event loop scope for asynchronous fixtures will default to the fixture caching scope. Future versions of pytest-asyncio will default the loop scope for asynchronous fixtures to function scope. Set the default fixture loop scope explicitly in order to avoid unexpected behavior in the future. Valid fixture loop scopes are: "function", "class", "module", "package", "session"

  warnings.warn(PytestDeprecationWarning(_DEFAULT_FIXTURE_LOOP_SCOPE_UNSET))
```

## Risks / Notes
(none supplied)

## Generated
2026-08-15T17:01:54+07:00
