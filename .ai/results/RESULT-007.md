# RESULT-007

STATUS: READY_FOR_REVIEW

## Summary
Fix resume durable tool budget accounting and add regression tests for REVIEW-007

## Task Metadata
- Task: `TASK-007`
- Action: `FIX`
- Authorized Artifact: `.ai/reviews/REVIEW-007.md (1c1aa70b58)`
- Base Main SHA: `(n/a)`
- Branch: `ai/task-007`

## Files Changed
- src/agent/loop.py
- src/core/run_budget.py
- tests/core/test_run_budget.py

## Diff Stat
```text
src/agent/loop.py             | 143 +++++++++++++++++++++++++++-------------
 src/core/run_budget.py        |   3 +
 tests/core/test_run_budget.py | 150 ++++++++++++++++++++++++++++++++++++++++++
 3 files changed, 251 insertions(+), 45 deletions(-)
```

## Tests
Command: `.\venv\Scripts\python -m pytest tests/ -q -W ignore`  
Exit code: 0

```text
........................................................................ [ 23%]
........................................................................ [ 47%]
........................................................................ [ 71%]
........................................................................ [ 95%]
.............                                                            [100%]
301 passed in 30.40s

C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:207: PytestDeprecationWarning: The configuration option "asyncio_default_fixture_loop_scope" is unset.
The event loop scope for asynchronous fixtures will default to the fixture caching scope. Future versions of pytest-asyncio will default the loop scope for asynchronous fixtures to function scope. Set the default fixture loop scope explicitly in order to avoid unexpected behavior in the future. Valid fixture loop scopes are: "function", "class", "module", "package", "session"

  warnings.warn(PytestDeprecationWarning(_DEFAULT_FIXTURE_LOOP_SCOPE_UNSET))
```

## Risks / Notes
(none supplied)

## Generated
2026-08-15T17:26:42+07:00
