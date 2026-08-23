# REVIEW-075 — H3 Exact-Snapshot Artifact Role Summaries & Python Symbol Intelligence

STATUS: CHANGES_REQUIRED
PUBLISHER_PROFILE: CANONICAL_E4
APPROVED: NO
AUTO_MERGE_ELIGIBLE: NO

TASK_ID: TASK-075
REVIEWED_TASK_HEAD_SHA: 4639c9b89572bd64cf7243e0b248fa45d4ededf8
REVIEWED_BASE_MAIN_SHA: a5dba4d85cccc94ea4364d6a2eb52e905f3a40fe
TASK_ARTIFACT_BLOB_SHA: 7e12b18356844f9c51586bb20fbbe8f5b22a13bb
RESULT_BLOB_SHA: 23c34435d5d52a9f6492d04e9a0458a331f0816a
EXECUTOR_ID: codex
BLOCKERS_REMAINING: 2
H3_COMPLETE: NO
H4_IMPLEMENTATION_AUTHORIZED: NO
LIVE_PAID_API_AUTHORIZED: NO

## Machine-Readable E4 FIX Inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/decisions/ADR-038-AIOS-ENGINEERING-H-SERIES-H0-AUTHORITY-BOUNDARY-CONTRACT-LOCK.md","blob_sha":"be56f92eef5dcffdc37cebafea280399730b151f"},{"path":".ai/decisions/ADR-043-AIOS-ENGINEERING-H1-REPOSITORY-SNAPSHOT-DISCOVERY-PROVENANCE-CONTRACT-LOCK.md","blob_sha":"140e1a03593e31f6681016ae45b427f9b16ee8c9"},{"path":".ai/decisions/ADR-045-AIOS-ENGINEERING-H2-DETERMINISTIC-TASK-RELEVANCE-RANKING-BOUNDED-SELECTION-CONTRACT-LOCK.md","blob_sha":"0cbb4fc90e75bff533e1fd99397f4a1470e39c72"},{"path":".ai/decisions/ADR-048-AIOS-ENGINEERING-H3-EXACT-SNAPSHOT-ARTIFACT-ROLE-PYTHON-SYMBOL-INTELLIGENCE-CONTRACT-LOCK.md","blob_sha":"5f595a20e10541f6c53f8ecc2d061157d79a284c"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["src/aios_engineering/harness/__init__.py","src/aios_engineering/harness/roles.py","tests/aios_engineering/harness/test_roles.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]},{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]}],"operation":"FIX","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

The review and the three marker lines above create FIX authorization inputs only after a fresh Human FIX command. They create no retry, reroute, paid-provider, merge, executor-substitution, or H4 authority.

## Reviewed Snapshot

```text
BASE_MAIN_SHA: a5dba4d85cccc94ea4364d6a2eb52e905f3a40fe
BRANCH: ai/task-075
REVIEWED_TASK_HEAD_SHA: 4639c9b89572bd64cf7243e0b248fa45d4ededf8
STATUS_VS_MAIN: AHEAD
AHEAD_BY: 1
BEHIND_BY: 0
MERGE_BASE_SHA: a5dba4d85cccc94ea4364d6a2eb52e905f3a40fe
CUMULATIVE_SCOPE: EXACT
```

Cumulative delta is limited to the three authorized H3 files plus Bridge-generated `.ai/results/RESULT-075.md`.

Codex transport completed normally:

```text
E4_TRANSPORT_STATUS: EXITED_ZERO
E4_ALLOWED_SCOPE_VERIFIED: PASS
E4_PUBLICATION_TRUST_VERIFIED: PASS
E4_DIRTY_PATH_COUNT: 3
```

Canonical full repository suite recorded in RESULT-075:

```text
2339 passed, 7 skipped, 0 failed
```

## Findings

### B1 — Exact blob identity is not re-proven from the bytes actually analyzed

ADR-048 requires exact blob identity and exact-snapshot provenance before content is promoted into H3 role/symbol evidence.

Current H3 flow verifies `cat-file -t <blob_sha>`, obtains `cat-file -s <blob_sha>`, then reads `cat-file blob <blob_sha>` and checks only the returned byte length. It does not recompute the canonical Git blob object ID from the actual returned body and compare that digest with `evidence.blob_sha` before decode/AST/summary construction.

That leaves an object-store corruption / same-length TOCTOU gap: bytes different from the expected Git object can be analyzed and fingerprinted while the summary still carries the expected `blob_sha`.

Required FIX:

```text
read bounded exact body
    ↓
compute canonical Git blob identity over: b"blob " + decimal_size + b"\0" + body
    ↓
actual_blob_sha == evidence.blob_sha ?
    YES -> decode/parse/summarize
    NO  -> fail closed with RepositoryRoleSummaryGitError (or narrower H3 domain error)
```

The repository contracts currently lock 40-hex Git object IDs, so the implementation must use the corresponding Git SHA-1 object identity semantics without widening the object-ID contract.

Add regression coverage proving that same-length body tampering/corruption is rejected before AST analysis and before any result/receipt is returned.

### B2 — Operational AST failures are incorrectly converted into `SYNTAX_REJECTED`

ADR-048 defines `SYNTAX_REJECTED` specifically for Python AST syntax failure and requires valid bounded Python to produce `PARSED`.

Current code catches:

```text
SyntaxError
ValueError
TypeError
MemoryError
RecursionError
```

and converts every one to `SYNTAX_REJECTED`.

`MemoryError`, `RecursionError`, and `TypeError` are not trustworthy source-syntax evidence. Converting runtime/resource/programming failures into a content status creates false repository evidence instead of failing closed.

Required FIX:

```text
content-derived AST syntax rejection -> SYNTAX_REJECTED
operational/runtime parser failure   -> propagate/fail closed
```

Do not silently create a new analysis status outside ADR-048. If `ValueError` is retained as syntax/content rejection, add an explicit test proving the exact content-derived case being accepted. Add tests injecting/triggering operational parser errors and proving no H3 summary/result/receipt is returned as `SYNTAX_REJECTED`.

## Passing Areas

```text
H2_RANKING_REVALIDATION: PASS
H2_SELECTED_ORDER_PRESERVED: PASS
H2_PRIORITY_PRESERVED: PASS
UNSELECTED_BODY_READ: NO
WORKTREE_BODY_READ: NO
DIRTY_WORKTREE_INDEPENDENCE: PASS
EXACT_COMMIT_TREE_BINDING: PASS
EXACT_SELECTED_OBJECT_TYPE: PASS
ROLE_PRECEDENCE: PASS
PACKAGE_EXPORT_ROLE: PASS
ENTRYPOINT_BASENAME_AND_MAIN_GUARD: PASS
TOP_LEVEL_CLASS_FUNCTION_ASYNC_SYMBOLS: PASS
NESTED_AND_METHOD_SYMBOLS_EXCLUDED: PASS
PER_BLOB_BYTE_BOUND: PASS
AGGREGATE_BODY_BYTE_BOUND: PASS
DECODE_AND_SYNTAX_ACCOUNTING_BASIC_CASES: PASS
SUMMARY_AND_RESULT_FINGERPRINTS: PASS
ZERO_AUTHORITY_RECEIPT: PASS
NETWORK_USED: NO
LLM_USED: NO
PAID_API_USED: NO
EXECUTOR_TENDENCY_INFERRED: NO
BRIDGE_RUNTIME_CHANGED: NO
```

## FIX Validation

After B1-B2 are repaired, run exactly:

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_engineering/harness/test_contracts.py tests/aios_engineering/harness/test_discovery.py tests/aios_engineering/harness/test_ranking.py tests/aios_engineering/harness/test_roles.py -q
.\venv\Scripts\python.exe -m pytest tests/ -q
git diff --check
```

## Decision

```text
TASK-075: CHANGES_REQUIRED
AUTO_MERGE: NO
BLOCKERS_REMAINING: 2
H3_COMPLETE: NO
H4_IMPLEMENTATION_AUTHORIZED: NO
LIVE_PAID_API_AUTHORIZED: NO
```
