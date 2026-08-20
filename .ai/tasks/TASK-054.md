# TASK-054 — M11.2C Grant-Aware Brain Dispatch + Consume-Before-Call — Reissue

STATUS: READY
CLASS: L3 — SECURITY-CRITICAL PAID-API BRAIN RUNTIME / ONE-SHOT SPEND
MILESTONE: M11.2C
EXECUTOR_MODE: UNIFIED_AIOS_WORKER_DUAL_EXECUTOR

## Baseline

```text
MAIN_SHA: d3f66189431755cc8c188ab5bc9866c069f0e3e3
TARGET_BRANCH: ai/task-054
```

## Reissue Authority

TASK-053 ended as a no-worktree-delta attempt and has no publication authority.

```text
TASK_053_TASK_BLOB_SHA: e65101b5014730e0f55fd6a764a8515517406a9e
TASK_053_BLUEPRINT_BLOB_SHA: 93cab4add451f58082e760fdd5fe8cde6bad5401
TASK_053_REACTIVATION: FORBIDDEN
TASK_053_RETRY: FORBIDDEN
TASK_053_PUBLICATION_AUTHORITY: NONE
TASK_054: SOLE NEW IMPLEMENTATION AUTHORITY FOR M11.2C
```

Human must release the stale TASK-053 lease before RUN TASK-054:

```text
lease-task-053-97d6c81ec7a5
```

No real paid provider call is authorized by TASK-054.

## Authoritative Contracts

```text
ADR_036_PATH: .ai/decisions/ADR-036-M11-EXTERNAL-API-ESCAPE-HATCH-ARCHITECTURE-LOCK.md
ADR_036_BLOB_SHA: cf71c571d8e3fd611ea07d21f15ad0bf90ef6ecc
ADR_038_PATH: .ai/decisions/ADR-038-DEFAULT-DUAL-EXECUTOR-TASK-AUTHORING-POLICY-LOCK.md
ADR_038_BLOB_SHA: 72d38bf2f2ff5a07e7b63322116ad87622349df1
BLUEPRINT_PATH: .ai/context/TASK-054-M11.2C-REISSUE-CHILD-ROLE-LOCK-BLUEPRINT.md
BLUEPRINT_BLOB_SHA: 7ca33e405293dbc3033ca178ba54a3ce94830891
REVIEW_052_PATH: .ai/reviews/REVIEW-052.md
REVIEW_052_BLOB_SHA: 06ddb1061af2bb21432c3e4910f4fc183f54f2e5
```

## Child Executor Role Lock

The Bridge E4-spawned Codex process is the bounded implementation Executor child, NOT the visible `aios-worker` operator UI.

```text
visible Codex + aios-worker skill = operator UI
Bridge E4 spawned Codex process  = bounded implementation Executor
```

The child MUST implement the authorized task now, create the two allowed files, run targeted tests, leave the authorized delta dirty, and exit normally. It MUST NOT invoke the operator skill/adapter again and MUST NOT commit/push/publish/merge.

## Objective

Implement the M11.2C runtime coordinator that:

```text
starts from BrainDispatchRequest allow_paid_api=false
requires one exact ACTIVE Human paid-API Brain grant
validates exact grant/request/artifact/context/provider/model/token binding
requires exactly one PAID_API Brain candidate == grant.brain_id
derives a fresh request with allow_paid_api=true
uses unchanged M10 dispatch_brain()
keeps grant ACTIVE when subscription wins
consumes grant durably before paid gateway invocation
calls ModelGateway at most once
never retries or selects a second paid provider
```

## Machine-Readable Executor Context

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/decisions/ADR-036-M11-EXTERNAL-API-ESCAPE-HATCH-ARCHITECTURE-LOCK.md","blob_sha":"cf71c571d8e3fd611ea07d21f15ad0bf90ef6ecc"},{"path":".ai/decisions/ADR-038-DEFAULT-DUAL-EXECUTOR-TASK-AUTHORING-POLICY-LOCK.md","blob_sha":"72d38bf2f2ff5a07e7b63322116ad87622349df1"},{"path":".ai/context/TASK-054-M11.2C-REISSUE-CHILD-ROLE-LOCK-BLUEPRINT.md","blob_sha":"7ca33e405293dbc3033ca178ba54a3ce94830891"},{"path":".ai/reviews/REVIEW-052.md","blob_sha":"06ddb1061af2bb21432c3e4910f4fc183f54f2e5"}]

## Machine-Readable Executor Worktree Scope

EXECUTOR_ALLOWED_PATHS_JSON: ["src/aios_bridge/paid_api_brain_escape.py","tests/aios_bridge/test_paid_api_brain_escape.py"]

Bridge-generated `.ai/results/RESULT-054.md` is publication output, not Executor implementation scope.

## Executor Dispatch Policy

DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

Human selects exactly one Executor. No silent reroute, no second Executor, no paid Executor.

## Exact Writable Files

```text
src/aios_bridge/paid_api_brain_escape.py
tests/aios_bridge/test_paid_api_brain_escape.py
```

Do not modify existing production files.

## Bounded Read-Only Source Scope

Executor MAY read exactly:

```text
src/aios_bridge/paid_api_grant.py
src/aios_bridge/runtime_paid_api_grant.py
src/aios_bridge/continuity/dispatch.py
src/aios_bridge/continuity/state.py
src/aios_bridge/continuity/brain.py
src/aios_bridge/external_brain/contracts.py
src/aios_bridge/external_brain/context.py
src/aios_bridge/external_brain/gateway.py
src/aios_bridge/external_brain/provider.py
```

Do not broaden repository inspection.

## Required Runtime Contract

Follow the blueprint exactly.

Critical invariants:

```text
BASE_ALLOW_PAID_API: FALSE REQUIRED
PAID_API_BRAIN_CANDIDATES: EXACTLY ONE
GRANTED_PAID_BRAIN: EXACT MATCH
ACTIVE_GRANT: REQUIRED BEFORE ENABLE
EXACT_ARTIFACT_CONTENT_BLOB_PROOF: REQUIRED
EXACT_TOKEN_COUNTER: REQUIRED
M10_RANKING: UNCHANGED
SUBSCRIPTION_PREFERENCE: PRESERVED
CONSUME_BEFORE_GATEWAY: REQUIRED
GATEWAY_CALLS_MAX: 1
AUTO_RETRY: FORBIDDEN
SECOND_PAID_PROVIDER: FORBIDDEN
EXECUTOR_AUTHORITY: NONE
REAL_NETWORK_TEST: FORBIDDEN
```

## Operation Mapping

```text
continuity.PLAN           -> external.PLAN
continuity.DIAGNOSIS      -> external.DIAGNOSE_FAILURE
continuity.PATCH_PROPOSAL -> external.GENERATE_PATCH
continuity.REVIEW         -> external.REVIEW_PATCH
continuity.TASK           -> FAIL CLOSED
continuity.TASK_AND_PLAN  -> FAIL CLOSED
```

## Paid Selection Order

```text
all pre-call validations
↓
new immutable BrainDispatchRequest allow_paid_api=true
↓
dispatch_brain()
↓
if subscription/WAIT/no-compatible:
  consume=NO
  gateway=NO
  grant remains ACTIVE

if granted paid Brain selected:
  AtomicPaidApiGrantStore.consume() DURABLY
  ↓
  ModelGateway.invoke() EXACTLY ONCE
```

Never gateway-before-consume.

## Tests

Tests must be deterministic/offline and prove all locked blueprint cases, especially:

```text
second paid candidate rejected before enablement
subscription still preferred
subscription win leaves grant ACTIVE
authorized artifact bytes match exact Git blob SHA
non-exact counter rejected
budget mismatch rejected
consume precedes gateway
consume failure => gateway calls 0
gateway/provider/ledger failure never restores grant
sequential replay => no gateway
concurrent same-grant => at most one gateway invocation
no retry / no second provider / no Executor authority / no Git mutation / no network
```

## Targeted Test Command

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_bridge/test_paid_api_brain_escape.py -q
```

Executor runs targeted tests only. Bridge publication owns the full repository suite.

## Human RUN Choice

After TASK-053 lease recovery, choose exactly one:

```text
Antigravity:
/aios-worker RUN TASK-054

Codex:
$aios-worker RUN TASK-054
```

## Completion Boundary

After Bridge publication:

```text
STOP
NEXT: Review TASK-054
```

Do not start M11.3 and do not perform a real paid API call automatically.
