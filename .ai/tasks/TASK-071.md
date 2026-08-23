# TASK-071 — Executable Task Authoring Preflight & Zero-Touch Start Hardening

STATUS: READY
CLASS: L2 — AIOS BRIDGE CONTROL-PLANE HARDENING
MILESTONE: POST-H1 / PRE-H2 REFINEMENT
EXECUTOR_MODE: DUAL_EXECUTOR_ALLOWED
RECOMMENDED_EXECUTOR: antigravity

## Baseline

```text
MAIN_SHA: 2eb9822bfcd923bd937598def9fcf1f2c93b6c9b
TARGET_BRANCH: ai/task-071
H1_STATUS: COMPLETE
H2_IMPLEMENTATION_AUTHORIZED: NO
LEAN_AUTO_MERGE: ENABLED
DUAL_EXECUTOR_OPERATIONAL_BASELINE: PROVEN
ADR: ADR-044
ADR_BLOB_SHA: 24b212d96d5fa650241a71049ce114f7a3a85489
PAID_API_CALL_ALLOWED: NO
AUTO_RETRY_ALLOWED: NO
AUTO_REROUTE_ALLOWED: NO
REAL_CODEX_REQUIRED: NO
```

## Machine-Readable E4 Inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/decisions/ADR-044-EXECUTABLE-TASK-AUTHORING-PREFLIGHT-ZERO-TOUCH-START-CONTRACT-LOCK.md","blob_sha":"24b212d96d5fa650241a71049ce114f7a3a85489"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","src/aios_bridge/task_authoring.py","tests/test_bridge.py","tests/test_bridge_task_authoring.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

The three lines above are the complete E4 machine-readable marker set for this task. They create no retry, reroute, paid-provider, merge, or cross-executor authority.

## Objective

Implement ADR-044 so malformed executable TASK/REVIEW artifacts fail during Bridge handoff preflight before branch/worktree authority mutation, executor lease acquisition, authorization creation, state-authority mutation, or executor invocation.

Preserve the existing v0.4.0 zero-touch RUN behavior: Bridge owns safe local-main reconciliation and the Human must not need a manual post-merge `git pull` merely to start the next task.

## Writable Scope

Executor may modify/create only:

```text
bridge.py
src/aios_bridge/task_authoring.py
tests/test_bridge.py
tests/test_bridge_task_authoring.py
```

Bridge-generated `.ai/results/RESULT-071.md` is publication output, not executor writable scope.

Explicitly forbidden:

```text
src/aios_bridge/executor_automation.py
src/aios_bridge/runtime_dispatch.py
src/aios_bridge/runtime_lease.py
src/aios_bridge/review_merge.py
src/aios_bridge/paid_api_*/**
src/aios_bridge/continuity/**
src/aios_engineering/**
.agents/**
.ai/decisions/**
.ai/reviews/**
.ai/tasks/**
requirements.txt
```

No dependency changes.

## Required Implementation

Introduce a repository-owned deterministic validation surface equivalent to:

```python
preflight_executable_artifact(
    content: str,
    *,
    work_path: str,
    operation: ExecutionOperation,
    selected_executor: str,
) -> ExecutableArtifactPreflight
```

The exact API may vary, but it must:

1. reuse the existing canonical `parse_executor_automation_markers(...)` parser;
2. reuse the existing canonical `parse_executor_dispatch_policy_marker(...)` parser;
3. validate the existing three E4 markers exactly once each;
4. validate requested RUN/FIX operation against dispatch policy;
5. validate the Human-selected executor is an exact declared candidate;
6. validate that candidate supports the requested operation and all required capabilities;
7. create zero authority and perform zero subprocess/network/model work.

Do not duplicate marker grammars or introduce a permissive second parser.

## Handoff Ordering Contract

For both RUN and FIX, `cmd_handoff()` must fetch/read the exact control artifact and perform preflight before any of the following:

```text
reconcile_local_main mutation
prepare/create/switch task branch
lease acquire
authorization write
task/review authority-state mutation
executor process invocation
```

Artifact caching outside the worktree may occur before preflight if it creates no authority.

A preflight failure must not leave a lease requiring Human cleanup.

## Required Failure Cases

Fail closed before authority mutation for at least:

```text
missing EXECUTOR_CONTEXT_REFS_JSON
missing EXECUTOR_ALLOWED_PATHS_JSON
missing DISPATCH_EXECUTOR_POLICY_JSON
duplicate marker
malformed marker JSON
invalid context ref
invalid/duplicate/empty allowed path
malformed dispatch policy
RUN/FIX operation mismatch
selected executor not declared
selected executor lacks requested operation
selected executor lacks required capability
```

No retry or reroute.

## Publisher Authoring Guard

Current Bridge E4 canonical RESULT publication remains unchanged.

Implement a deterministic preflight/authoring rule that prevents executable artifacts from treating unsupported arbitrary custom RESULT keys as publisher-required acceptance evidence. Do not expand the RESULT publisher schema for TASK-071.

Acceptable implementation directions include a closed publisher-profile validator or a narrowly defined executable-artifact authoring rule. It must be testable and fail closed, not a comment-only convention.

Implementation-specific invariants continue to be proven through tests/source review; canonical E4/full-suite evidence remains publisher-owned.

## Zero-Touch Start Preservation

Do not redesign `reconcile_local_main()`.

Tests must preserve/prove:

```text
clean local main behind remote -> automatic fast-forward
identical local/remote main -> continue
local main ahead/diverged -> fail closed
dirty worktree -> fail closed
no reset --hard
no force update
no destructive rebase
manual post-merge pull required for next AIOS RUN -> NO
```

Critically, a malformed artifact must fail before reconciliation mutates local main.

## Mandatory Tests

Add focused unit/integration coverage proving at minimum:

```text
VALID_RUN_PREFLIGHT: PASS
VALID_FIX_PREFLIGHT: PASS
EXISTING_MARKER_PARSERS_REUSED: YES

MISSING_CONTEXT_MARKER_FAILS_BEFORE_LEASE: YES
MISSING_ALLOWED_PATHS_MARKER_FAILS_BEFORE_LEASE: YES
MISSING_DISPATCH_MARKER_FAILS_BEFORE_LEASE: YES
DUPLICATE_MARKER_FAILS_BEFORE_LEASE: YES
MALFORMED_MARKER_FAILS_BEFORE_LEASE: YES
OPERATION_MISMATCH_FAILS_BEFORE_LEASE: YES
EXECUTOR_NOT_DECLARED_FAILS_BEFORE_LEASE: YES
CAPABILITY_MISMATCH_FAILS_BEFORE_LEASE: YES

PREFLIGHT_FAILURE_RECONCILE_CALLED: NO
PREFLIGHT_FAILURE_TASK_BRANCH_MUTATED: NO
PREFLIGHT_FAILURE_LEASE_CREATED: NO
PREFLIGHT_FAILURE_AUTHORIZATION_CREATED: NO
PREFLIGHT_FAILURE_AUTHORITY_STATE_MUTATED: NO
PREFLIGHT_FAILURE_EXECUTOR_CALLED: NO

UNSUPPORTED_CUSTOM_RESULT_REQUIREMENT_ACCEPTED: NO
CANONICAL_E4_PUBLICATION_PROFILE_ACCEPTED: YES

LOCAL_MAIN_BEHIND_REMOTE_AUTO_FAST_FORWARD: PASS
LOCAL_MAIN_DIVERGED_FAIL_CLOSED: PASS
DIRTY_WORKTREE_FAIL_CLOSED: PASS
```

No real Codex or Antigravity process may be launched by automated tests.

## Validation Commands

Run:

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_bridge_task_authoring.py tests/test_bridge.py -q
.\venv\Scripts\python.exe -m pytest tests/ -q
git diff --check
```

## RESULT / Review Evidence

Use the existing canonical Bridge E4 publisher only. Do not require task-specific RESULT keys that the current publisher does not own.

ChatGPT review will verify exact source/tests, cumulative scope, canonical E4 publication, and the preflight-before-authority ordering.

## Acceptance Boundary

TASK-071 passes only if invalid executable artifacts are rejected before authority/worktree mutations while valid RUN/FIX behavior and existing zero-touch local-main reconciliation remain intact.

TASK-071 completion does not silently implement H2. After PASS + auto-merge, ChatGPT may create the separate H2 architecture/task cycle.
