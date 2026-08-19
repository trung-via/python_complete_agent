# TASK-043 — E4 Result Collection + Auto Publication

STATUS: READY
CLASS: L4 — AUTHORIZED LOCAL EXECUTION / BRIDGE INTEGRATION / AUTO PUBLICATION / FAIL-CLOSED RECOVERY
EXECUTOR_MODE: THIN_EXECUTOR

## Baseline

```text
MAIN_SHA: 91813c04160cb664af47c5f0b04fea37ef9aa076
TARGET_BRANCH: ai/task-043
```

## Authoritative Contract

```text
ADR_PATH: .ai/decisions/ADR-032-E4-APPROVED-EXECUTOR-AUTOMATION-AND-AUTO-PUBLICATION-CONTRACT-LOCK.md
ADR_BLOB_SHA: 22c300f882327aa812ad5e3250bf53ba8cf85eb5
BLUEPRINT_PATH: .ai/context/TASK-043-E4-IMPLEMENTATION-BLUEPRINT.md
BLUEPRINT_BLOB_SHA: 2c938752f70fd22070baaf5b1b22aa6f68f7f3b6
```

Existing anchors:

```text
BRIDGE_BLOB_SHA: f0b28cdddc610ea330ec9403bd111bc37bc93ac1
M1_STATE_BLOB_SHA: 3b2c04169a85c54ccac1abe0736934cee1624af1
M4_EXECUTOR_BLOB_SHA: f144ea399c11f89809ecdf4f3d62098ee356ed7a
M5_LEASE_BLOB_SHA: 81a1373d6e04084b7c28d67699f4f613e4f0ee47
E1_TRANSPORT_CONTRACT_BLOB_SHA: bbe7b517202ea446e727752955e004d9464934bd
E2_CODEX_LOCAL_BLOB_SHA: dd1fae54506459a2a638441a35d5a327d89da8cc
E3_CONTEXT_COMPOSER_BLOB_SHA: 79a2f2c0f3f5f1c2de6dead7528dff62fee9e8c8
M10_RUNTIME_DISPATCH_BLOB_SHA: 01a35d0ffed48f2fbb70649f4c67f0e894910805
```

## E-Series Position

```text
E1 — Executor Invocation Contract                  COMPLETE
E2 — Codex Local Transport                         COMPLETE
E3 — Bounded Context Pack Delivery                 COMPLETE
E4 — Result Collection + Auto Publication          ← THIS TASK
E5 — Zero-Copy/Paste Operational Proof
```

H-Series remains separate and DEFERRED.

## Objective

Implement the first approved automatic Codex execution path in AIOS Bridge:

```text
Human approve
  -> existing ACTIVE authorization + lease
  -> bridge.py execute
  -> exact control/context snapshot
  -> M1/M4 launch state
  -> E3 bounded context pack
  -> E2 local Codex invoke
  -> post-execution Git/scope gates
  -> existing Bridge full-suite publisher
  -> RESULT + commit + push
  -> canonical post-publication M4 result verification
```

`execute` must never approve, choose an executor, acquire a lease, retry automatically, or merge.

## Machine-Readable Executor Context

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/decisions/ADR-032-E4-APPROVED-EXECUTOR-AUTOMATION-AND-AUTO-PUBLICATION-CONTRACT-LOCK.md","blob_sha":"22c300f882327aa812ad5e3250bf53ba8cf85eb5"},{"path":".ai/context/TASK-043-E4-IMPLEMENTATION-BLUEPRINT.md","blob_sha":"2c938752f70fd22070baaf5b1b22aa6f68f7f3b6"}]

This ordered marker is part of the exact Human-approved TASK blob. E4 implementation must parse this marker generically for future automatic runs; TASK-043 itself is still executed manually because E4 does not exist yet.

## Machine-Readable Executor Worktree Scope

EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","src/aios_bridge/executor_automation.py","tests/aios_bridge/test_executor_automation.py","tests/test_bridge_executor_automation.py"]

RESULT-043 is Bridge-generated and is not Executor-writable scope.

## Executor Dispatch Policy

DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX","RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX","RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"claude-code","preference_rank":2,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX","RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

This remains recommendation/capability policy only and grants no authority.

## Allowed Files

Exactly:

```text
bridge.py
src/aios_bridge/executor_automation.py
tests/aios_bridge/test_executor_automation.py
tests/test_bridge_executor_automation.py
.ai/results/RESULT-043.md      # Bridge-generated only
```

## Forbidden Scope

Do NOT modify:

```text
src/aios_bridge/continuity/**
src/aios_bridge/executor_transports/**
src/aios_bridge/executor_context.py
src/aios_bridge/runtime_dispatch.py
src/aios_bridge/runtime_lease.py
src/aios_bridge/external_brain/**
src/providers/**
docs/**
```

Do NOT implement:
- E5 real operational proof;
- another Executor transport;
- automatic Executor recommendation/selection;
- automatic approval;
- automatic lease acquisition;
- retry loop;
- auto reset/stash/clean/revert;
- auto merge;
- generic test-driver framework;
- M11 API escape hatch;
- H1 Event Journal;
- H2 Capability Seams;
- H3 Execution Envelope;
- H4 Provider Lifecycle;
- H5 Driver Contract.

## Required Behavior

Follow ADR-032 and locked blueprint exactly.

Critical chain:

```text
ACTIVE AUTH + ACTIVE LEASE
        ↓
bridge.py execute TASK-N
        ↓
freeze exact control snapshot
        ↓
verify exact WORK + context blob refs
        ↓
verify dispatch capability contract
        ↓
build M1 ContinuityState + FRESH observation
        ↓
build M4 ExecutionRequest + PreparedExecution
        ↓
build E3 ExecutorContextPack
        ↓
E2 CodexLocalTransport.invoke exactly once
        ↓
InvocationReceipt persisted externally
        ↓
branch/head unchanged + exact allowed dirty scope
        ↓
existing cmd_publish full repository suite
        ↓
RESULT + commit + push + lease release + auth CONSUMED
        ↓
post-publication M4 ExecutionResult validation
```

## Authority Invariants

```text
recommendation != authorization
authorization != lease
lease != invocation
invocation != transport receipt
transport receipt != task success
publication != review PASS
review PASS != merge authorization
```

Only Human may authorize RUN/FIX/MERGE and select the executor.

`bridge.py execute` must contain no path that creates or infers Human authorization.

## Exact Automation Inputs

E4 v1 automation accepts only:
- exact ACTIVE authorization already created by Bridge approval;
- exact active M5 lease;
- executor `codex`;
- exact work artifact containing all three machine-readable markers;
- exact raw control artifact bytes from one control commit snapshot;
- exact current task worktree/branch facts.

Any missing/malformed/drifted evidence fails closed before real invocation.

## Post-Executor Mechanical Gates

Before auto publication:

```text
post branch == pre branch == authorized task branch
post HEAD == pre HEAD
non-empty dirty path set
all dirty paths subset exact EXECUTOR_ALLOWED_PATHS_JSON
no hidden auto retry
```

Tracked, staged, unstaged, untracked, rename/copy source and destination evidence must be handled.

Codex is forbidden from committing or switching branches; E4 must enforce this mechanically rather than trusting prompt compliance.

## Transport Failure

For:

```text
FAILED_TO_START
EXITED_NONZERO
TIMED_OUT
INTERRUPTED
```

E4 must:
- never call publisher;
- never retry automatically;
- never release/consume authority silently;
- preserve Executor work for Human inspection/recovery;
- persist bounded non-secret invocation evidence when possible.

## Auto Publication

Only after `EXITED_ZERO` plus all post-execution gates pass, call the existing Bridge `cmd_publish()` exactly once using fixed full repository suite from the current Python interpreter:

```text
python -m pytest tests/ -q
```

No test command is accepted from TASK/REVIEW prose for E4 v1.

No second commit/push implementation may be created.

## Tests

All TASK-043 tests use fake/mocked E2 invocation only.
Do NOT invoke real Codex through the newly implemented `execute` command while implementing TASK-043.

Must include all positive/adversarial coverage specified by ADR-032 and blueprint, especially:

```text
marker exactness
raw Git CRLF/BOM bytes
control blob drift
ACTIVE auth + exact lease binding
codex-only automatic transport
M1 freshness
M4 request/prepared validation
M10 capability eligibility
E3 pack validity
single fake E2 invoke
no retry
branch drift block
HEAD commit block
empty delta block
out-of-scope tracked block
out-of-scope untracked block
rename source/destination block
receipt persistence failure block
nonzero/timeout/interruption block
fixed full-suite publisher args
post-publish M4 result validation
no approve/acquire/merge inside execute
```

## Targeted Commands

Run only:

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_bridge/test_executor_automation.py tests/test_bridge_executor_automation.py -q

.\venv\Scripts\python.exe -m pytest tests/aios_bridge/test_executor_context_pack.py tests/aios_bridge/test_codex_local_transport.py tests/aios_bridge/continuity/test_executor_transport.py tests/aios_bridge/continuity/test_executor.py tests/aios_bridge/test_runtime_lease.py tests/test_bridge.py -q
```

Do NOT run the full repository suite.
Do NOT run `bridge.py execute 43`.
Do NOT invoke real Codex recursively.

When targeted tests pass:
- report files changed;
- report targeted test counts;
- report blockers;
- STOP.

Do not commit.
Do not push.
Do not publish.

## Publication

TASK-043 still uses the existing manual publication boundary:

```powershell
.\venv\Scripts\python.exe .\bridge.py publish 43 `
  --action RUN `
  --test ".\venv\Scripts\python.exe -m pytest tests/ -q"
```

## Acceptance

```text
HUMAN_AUTHORITY_UNCHANGED: PASS
EXECUTE_COMMAND_ADDED: PASS
EXECUTE_REQUIRES_ACTIVE_AUTH: PASS
EXECUTE_ACQUIRES_LEASE: NO
CODEX_LOCAL_ONLY_V1: PASS
CONTEXT_MARKER_TRANSITIVE_BINDING: PASS
ALLOWED_SCOPE_MARKER: PASS
RAW_GIT_BYTES_PRESERVED: PASS
CONTROL_SINGLE_SNAPSHOT: PASS
M1_LAUNCH_STATE_FRESH: PASS
M4_REQUEST_PREPARED_VALID: PASS
M10_ELIGIBILITY_VALID: PASS
E3_PACK_VALID: PASS
FAKE_E2_SINGLE_INVOKE: PASS
AUTOMATIC_RETRY: NO
POST_EXEC_HEAD_IMMUTABLE: PASS
OUT_OF_SCOPE_BLOCKED: PASS
EXTERNAL_RECEIPT_NO_RAW_CONTEXT: PASS
EXISTING_CMD_PUBLISH_REUSED: PASS
FIXED_FULL_SUITE_COMMAND: PASS
AUTO_RESULT_COMMIT_PUSH: PASS
POST_PUBLISH_M4_RESULT: PASS
AUTO_MERGE: NO
E1_E2_E3_CORE_CHANGED: NO
H_SERIES_REMAINS_DEFERRED: PASS
FULL_REPO_TESTS: PASS
REGRESSIONS: 0
FINAL_INDEPENDENT_AUDIT: PASS
E4: PASS
E5_PROVEN: NO
```

Only Human may authorize merge.
