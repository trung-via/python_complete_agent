# REVIEW-071 — Executable Task Authoring Preflight & Zero-Touch Start Hardening

STATUS: CHANGES_REQUIRED
APPROVED: NO
AUTO_MERGE_ELIGIBLE: NO
MERGED_TO_MAIN: NO

TASK_ID: TASK-071
REVIEWED_TASK_HEAD_SHA: cd3eb3432a1717ac6fd194731624b0e40c6b562f
REVIEWED_BASE_MAIN_SHA: 2eb9822bfcd923bd937598def9fcf1f2c93b6c9b
RESULT_BLOB_SHA: e93040ef7e8159d6cff325785416b590f3419d8e
TASK_ARTIFACT_BLOB_SHA: c830eeb40aad0498391fee19d20133ca38ed891c
EXECUTOR_ID: antigravity
TASK_071_IMPLEMENTATION_PASS: NO
H2_IMPLEMENTATION_AUTHORIZED: NO
LIVE_PAID_API_AUTHORIZED: NO
PUBLISHER_PROFILE: CANONICAL_E4

## Machine-Readable FIX Inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/tasks/TASK-071.md","blob_sha":"c830eeb40aad0498391fee19d20133ca38ed891c"},{"path":".ai/decisions/ADR-044-EXECUTABLE-TASK-AUTHORING-PREFLIGHT-ZERO-TOUCH-START-CONTRACT-LOCK.md","blob_sha":"24b212d96d5fa650241a71049ce114f7a3a85489"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","src/aios_bridge/task_authoring.py","tests/test_bridge.py","tests/test_bridge_task_authoring.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]},{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]}],"operation":"FIX","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

The three E4 markers and the publisher-profile marker above are the complete executable FIX authoring inputs. They create no retry, reroute, paid-provider, merge, or cross-executor authority.

## Reviewed Snapshot

```text
BASE_MAIN_SHA: 2eb9822bfcd923bd937598def9fcf1f2c93b6c9b
BRANCH: ai/task-071
REVIEWED_TASK_HEAD_SHA: cd3eb3432a1717ac6fd194731624b0e40c6b562f
BRANCH_STATUS_VS_MAIN: AHEAD
AHEAD_BY: 2
BEHIND_BY: 0
MERGE_BASE_SHA: 2eb9822bfcd923bd937598def9fcf1f2c93b6c9b
```

Cumulative scope remains exact: the four executor-writable paths plus Bridge-generated `.ai/results/RESULT-071.md`. No H-Series implementation, worker surface, dependency, lease schema, paid-API grant, review-merge, or continuity contract path changed.

## Runtime / Test Evidence

```text
ACTION: FIX
EXECUTOR_ID: antigravity
TARGETED_TESTS: 82 passed, 0 skipped, 0 failed
FULL_REPOSITORY_TESTS: 2240 passed, 7 skipped, 0 failed
```

The prior B1 is partially resolved, but the executable path still has two fail-open edges.

## Prior B1 Progress — PASS

```text
DUPLICATE_PUBLISHER_PROFILE: REJECTED
CONFLICTING_PUBLISHER_PROFILE: REJECTED
UNSUPPORTED_PUBLISHER_PROFILE: REJECTED
TASK_070_LITERAL_CUSTOM_RESULT_CASE: REJECTED
CANONICAL_E4_PROFILE: ACCEPTED
EXISTING_HANDOFF_ORDERING: PRESERVED
ZERO_TOUCH_START: PRESERVED
```

## Finding B1 — Publisher contract is still not closed on the real handoff path

STATUS: FAIL / BLOCKER

### B1a — Missing publisher profile is still accepted by real RUN/FIX handoff

`preflight_executable_artifact()` defaults `require_explicit_profile=False`. Both RUN and FIX calls in `cmd_handoff()` invoke it without overriding that argument. Therefore an executable TASK/REVIEW with zero `PUBLISHER_PROFILE:` lines still passes the real handoff path.

The dedicated test only proves that `validate_publisher_profile(..., require_explicit_profile=True)` rejects a missing profile; it does not prove that Bridge handoff enables that strict mode.

Required fix:

```text
- real RUN handoff must require exactly one explicit publisher profile;
- real FIX handoff must require exactly one explicit publisher profile;
- missing profile must fail before reconciliation/branch/lease/auth/state mutation;
- add cmd_handoff integration tests for RUN and FIX proving missing profile fails before all authority/worktree mutations.
```

### B1b — Custom-result grammar remains permissive

The current validator scans `## RESULT Evidence` tokens, but explicitly accepts any token beginning with `TASK_` or `STEP_` even when it is not part of the canonical publisher contract:

```python
if token not in CANONICAL_RESULT_KEYS and not token.startswith("TASK_") and not token.startswith("STEP_"):
    reject
```

Therefore arbitrary requirements such as `TASK_CUSTOM_PUBLISHER_KEY` or `STEP_CUSTOM_EVIDENCE` can still pass. This is incompatible with the requested closed contract.

The section recognizer is also tied to one exact heading shape (`## RESULT Evidence`), so small authoring variants can evade the guard. The fix must not become an expanding blacklist or naming-prefix heuristic.

Required fix:

```text
- remove TASK_*/STEP_* wildcard acceptance;
- do not accept result keys merely because their names look familiar;
- define a closed canonical publisher profile from publisher-owned semantics;
- executable artifact custom-result requirements outside that closed profile must fail closed;
- add negative tests for TASK_CUSTOM_PUBLISHER_KEY and STEP_CUSTOM_EVIDENCE;
- add at least one heading/spacing variant regression so the TASK-070 failure class cannot bypass by trivial Markdown spelling changes;
- do not expand the RESULT publisher schema.
```

A simpler acceptable solution is to make `PUBLISHER_PROFILE: CANONICAL_E4` the sole publisher-authority declaration and mechanically forbid task-authored hard-result requirement sections/markers under that profile, while keeping implementation-specific proof in tests + ChatGPT review. The important property is a closed grammar, not heuristic recognition of possible keys.

## Required Validation Before Re-review

Run:

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_bridge_task_authoring.py tests/test_bridge.py -q
.\venv\Scripts\python.exe -m pytest tests/ -q
git diff --check
```

Tests must additionally prove:

```text
REAL_RUN_HANDOFF_MISSING_PROFILE: REJECT_BEFORE_MUTATION
REAL_FIX_HANDOFF_MISSING_PROFILE: REJECT_BEFORE_MUTATION
EXACTLY_ONE_CANONICAL_PROFILE_REQUIRED: YES
TASK_CUSTOM_PUBLISHER_KEY: REJECT
STEP_CUSTOM_EVIDENCE: REJECT
RESULT_REQUIREMENT_HEADING_VARIANT_BYPASS: NO
CUSTOM_RESULT_SCHEMA_EXPANDED: NO
ZERO_TOUCH_START_PRESERVED: YES
```

## Decision

```text
TASK-071: CHANGES_REQUIRED
PRIOR_B1_PARTIAL_PROGRESS: PASS
B1_REAL_HANDOFF_STRICT_PROFILE: FAIL
B1_CLOSED_RESULT_GRAMMAR: FAIL
BLOCKERS_REMAINING: 1
AUTO_MERGE: NO
TASK_AUTHORING_PREFLIGHT_COMPLETE: NO
H2_IMPLEMENTATION_AUTHORIZED: NO
```

Apply only B1 inside the existing writable scope. Preserve the already-correct preflight ordering and zero-touch reconciliation behavior. Do not change executor identity, lease, paid-API, retry/failover, Lean Auto-Merge, H-Series, or RESULT publisher schema semantics.
