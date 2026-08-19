# TASK-048 — Unified AIOS Worker Control Surface

STATUS: READY
CLASS: L3 — OPERATOR CONTROL ADAPTER / CODEX SKILL / ANTIGRAVITY PARITY
EXECUTOR_MODE: ANTIGRAVITY_BOOTSTRAP

## Baseline

```text
MAIN_SHA: 22a05d1f4880daf3a9f964e0564c658b051039cd
TARGET_BRANCH: ai/task-048
```

## Authoritative Contract

```text
ADR_PATH: .ai/decisions/ADR-037-UNIFIED-AIOS-WORKER-CONTROL-SURFACE-CONTRACT-LOCK.md
ADR_BLOB_SHA: 6c30cd6d2b9dea5dd4d20b687353471ba80dae8b
BLUEPRINT_PATH: .ai/context/TASK-048-UNIFIED-AIOS-WORKER-CONTROL-SURFACE-BLUEPRINT.md
BLUEPRINT_BLOB_SHA: fbd0641b7198a92fc8edd9014469da07414791ac
```

## Objective

Make Codex use the same AIOS worker semantics already used from Antigravity, with Bridge remaining the only shared control/authorization/publication state.

After this task is merged, normal Human operation becomes:

```text
Antigravity: /aios-worker RUN TASK-N
Codex:       $aios-worker RUN TASK-N
```

and similarly for `FIX` and `STATUS`.

No routine manual PowerShell sequence should be required from Codex.

## Bootstrap Reason

The Codex repo skill does not exist until this task lands. Therefore TASK-048 itself is intentionally bootstrapped through the already-established Antigravity worker workflow.

Human invocation of `/aios-worker RUN TASK-048` is the RUN authorization and selects executor `antigravity`.

## Machine-Readable Executor Context

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/decisions/ADR-037-UNIFIED-AIOS-WORKER-CONTROL-SURFACE-CONTRACT-LOCK.md","blob_sha":"6c30cd6d2b9dea5dd4d20b687353471ba80dae8b"},{"path":".ai/context/TASK-048-UNIFIED-AIOS-WORKER-CONTROL-SURFACE-BLUEPRINT.md","blob_sha":"fbd0641b7198a92fc8edd9014469da07414791ac"}]

## Machine-Readable Executor Worktree Scope

EXECUTOR_ALLOWED_PATHS_JSON: [".agents/skills/aios-worker/SKILL.md",".agents/skills/aios-worker/scripts/aios_worker.py","tests/aios_bridge/test_aios_worker_control_surface.py","docs/AIOS_UNIFIED_WORKER_WORKFLOW.md"]

Bridge-generated `.ai/results/RESULT-048.md` is not Executor-writable scope.

## Executor Dispatch Policy

DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

## Required Implementation

Create exactly:

```text
.agents/skills/aios-worker/SKILL.md
.agents/skills/aios-worker/scripts/aios_worker.py
tests/aios_bridge/test_aios_worker_control_surface.py
docs/AIOS_UNIFIED_WORKER_WORKFLOW.md
```

Follow the locked blueprint exactly.

### Shared semantics

```text
RUN TASK-N
FIX TASK-N
STATUS TASK-N
```

### Codex adapter

For RUN/FIX, the parent Codex skill invokes the shared script with adapter `codex`; the script delegates authority to existing Bridge handoff and then invokes existing `bridge.py execute N` exactly once.

The visible Codex session MUST NOT implement the task itself. Existing E3/E2/E4 remains the bounded executor/publication path.

### Antigravity adapter

Shared script supports adapter `antigravity` at the same Bridge handoff boundary, but does not invoke E4 Codex execution. This task does not redesign Antigravity execution.

### STATUS

STATUS is non-authorizing and may only synchronize/display existing Bridge status.

## Required Safety Properties

```text
ONE_SHARED_BRIDGE_STATE: YES
SECOND_UI_STATE_STORE: NO
PARENT_CODEX_EXECUTOR_DUPLICATION: NO
DIRECT_CODEX_EXEC_FROM_SKILL: NO
DIRECT_APPROVE_FROM_SKILL: NO
DIRECT_PUBLISH_FROM_SKILL: NO
AUTO_RETRY: NO
AUTO_FALLBACK: NO
AUTO_MERGE: NO
HUMAN_RUN_FIX_AUTHORITY: PRESERVED
CHATGPT_REVIEW_BOUNDARY: PRESERVED
```

## TASK-047 Boundary

TASK-047 is DEFERRED and MUST NOT be executed or reactivated by this task.

After TASK-048 PASS + merge, M11.1 will be reissued under a new task ID and fresh baseline. That reissued task will be the first real Codex operator proof using `$aios-worker RUN TASK-N`.

## Targeted Tests

Run only:

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_bridge/test_aios_worker_control_surface.py -q
```

Do not run the full repository suite as executor if Bridge publication already owns it in the active Antigravity workflow.

## Forbidden Scope

Do not modify:

```text
bridge.py
src/**
.ai/tasks/**
.ai/reviews/**
.ai/decisions/**
.ai/context/**
.ai/proofs/**
```

Do not implement M11.1/M11.2/M11.3.
Do not add paid API behavior.
Do not modify E1-E5.
Do not add automatic merge/retry/failover.
Do not activate H-Series.

## Acceptance

```text
REPO_CODEX_SKILL_DISCOVERABLE_LAYOUT: PASS
SINGLE_WORKER_SEMANTIC_PROTOCOL: PASS
CODEX_RUN_TO_HANDOFF_TO_EXECUTE: PASS
CODEX_FIX_TO_HANDOFF_TO_EXECUTE: PASS
STATUS_NON_AUTHORIZING: PASS
ANTIGRAVITY_HANDOFF_PARITY: PASS
SHARED_BRIDGE_STATE_ONLY: PASS
NO_MANUAL_POWERSHELL_NORMAL_CODEX_FLOW: PASS
NO_PARENT_CODEX_IMPLEMENTATION_DUPLICATION: PASS
NO_DIRECT_CONTEXT_RECONSTRUCTION: PASS
NO_DIRECT_APPROVE: PASS
NO_DIRECT_PUBLISH: PASS
NO_DIRECT_CODEX_EXEC: PASS
NO_RETRY_FALLBACK: PASS
MERGE_BOUNDARY_PRESERVED: PASS
TASK_047_REMAINS_DEFERRED: PASS
TARGETED_TESTS: PASS
FULL_REPO_TESTS: PASS
REGRESSIONS: 0
FINAL_INDEPENDENT_AUDIT: PASS
```

Only Human authorizes RUN/FIX/MERGE and executor choice. ChatGPT remains independent reviewer/merge gate.
