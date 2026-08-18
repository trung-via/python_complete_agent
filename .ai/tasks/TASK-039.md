# TASK-039 — M10.3 Real Operational Dispatch Proof

STATUS: READY
CLASS: L4 — REAL OPERATIONAL PROOF / DETERMINISTIC DISPATCH / HUMAN AUTHORITY
EXECUTOR_MODE: THIN_EXECUTOR

## Baseline

```text
MAIN_SHA: ff5d78abd71086ecb814255d4a589370e5660332
TARGET_BRANCH: ai/task-039
```

## Authoritative Contract

```text
ADR_PATH: .ai/decisions/ADR-028-M10.3-REAL-OPERATIONAL-DISPATCH-PROOF-CONTRACT-LOCK.md
ADR_BLOB_SHA: 10de8fbf67bd4b0f44d4f3297da4078ff79d019d
BLUEPRINT_PATH: .ai/context/TASK-039-M10.3-IMPLEMENTATION-BLUEPRINT.md
BLUEPRINT_BLOB_SHA: a4d179dcdac3647b9dc8c65a8ec95b6aa436c9d2
```

## Objective

Prove a real M10 operational dispatch chain in which explicit fresh runtime capacity observations cause the already-implemented deterministic dispatcher to recommend Codex, while Human authority remains the only path that turns recommendation into RUN authorization and an active ExecutorLease.

This task proves AIOS behavior. It does not independently prove the vendor's internal quota accounting system.

## Exact Executor Dispatch Policy

DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX","RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX","RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

This marker is recommendation policy only. It is not execution authorization.

## Canonical Real Scenario

```text
CAPACITY_SOURCE: HUMAN_DECLARED
antigravity: QUOTA_EXHAUSTED, fresh
codex:       AVAILABLE, fresh
allow_paid_api: false
```

Expected real Bridge recommendation:

```text
STATUS: SELECTED
SELECTED_EXECUTOR: codex
HUMAN_APPROVAL_REQUIRED: YES
AUTHORIZATION_CHANGED: NO
LEASE_CHANGED: NO
```

If Antigravity is no longer actually quota-exhausted at capture time, Human MUST NOT record a false observation. Stop and reconsider the proof setup.

## Mandatory Human Pre-Authorization Gate

Before `approve 39`, Human SHALL:
1. sync local `main` to the exact baseline;
2. sync control artifacts;
3. record fresh `HUMAN_DECLARED` capacity for `antigravity = QUOTA_EXHAUSTED` and `codex = AVAILABLE`;
4. run the real Bridge recommendation command;
5. capture its successful stdout to the exact external runtime receipt path `dispatch/proofs/TASK-039/recommendation.txt`;
6. inspect that it selects `codex` and still says Human approval is required;
7. only then explicitly authorize Codex with the existing `approve` command.

The recommendation receipt MUST predate authorization. Executor must not fabricate or replace it.

## Required Deliverables

```text
scripts/aios_m10_real_dispatch_proof.py
tests/aios_bridge/test_m10_real_dispatch_proof.py
proofs/TASK-039-M10/executor-stage.txt
proofs/TASK-039-M10/recommendation-receipt.txt
proofs/TASK-039-M10/PROOF.json
.ai/results/RESULT-039.md
```

## Allowed Files

Exactly:

```text
scripts/aios_m10_real_dispatch_proof.py
tests/aios_bridge/test_m10_real_dispatch_proof.py
proofs/TASK-039-M10/executor-stage.txt
proofs/TASK-039-M10/recommendation-receipt.txt
proofs/TASK-039-M10/PROOF.json
.ai/results/RESULT-039.md
```

## Forbidden Scope

Do NOT modify:

```text
bridge.py
src/aios_bridge/runtime_dispatch.py
src/aios_bridge/continuity/dispatch.py
src/aios_bridge/continuity/brain.py
src/aios_bridge/continuity/executor.py
src/aios_bridge/continuity/lease.py
src/aios_bridge/continuity/executor_failover.py
src/aios_bridge/continuity/hot_handoff.py
src/aios_bridge/continuity/state.py
src/aios_bridge/runtime_lease.py
src/aios_bridge/external_brain/**
src/providers/**
```

No M10.1 ranking change.
No M10.2 runtime capacity/recommendation change.
No M5/M6/M9 contract change.
No M11 implementation.
No model/provider quota probing.
No automatic approval.
No automatic lease mutation.
No automatic executor invocation.

## Executor Witness

Codex must create exact file:

```text
proofs/TASK-039-M10/executor-stage.txt
```

Exact bytes:

```text
TASK_ID: TASK-039
STAGE: HUMAN_AUTHORIZED_EXECUTION
EXECUTOR_ID: codex
RECOMMENDED_EXECUTOR_ID: codex
ACTION: RUN
PAYLOAD_VERSION: 1
```

with one final newline.

## Required Verifier Behavior

Implement ADR-028 and the locked blueprint exactly.

The verifier SHALL mechanically bind:
- exact external real recommendation receipt;
- exact TASK-039 control blob and policy fingerprint;
- exact current fresh capacity record fingerprints/states;
- recomputed existing M10.1 request/result fingerprints;
- causal ordering `capacity <= receipt <= authorization` by exact runtime file mtimes;
- exact ACTIVE TASK-039 RUN authorization selecting Codex;
- exact active authorization-bound Codex ExecutorLease;
- exact executor-stage witness;
- deterministic canonical `PROOF.json` fingerprint.

The verifier must copy the validated external receipt byte-for-byte into the committed proof directory.

The verifier MUST NOT create or alter capacity, authorization, lease, recommendation, Executor invocation, commit, push, merge, or provider/model calls.

## Required Adversarial Tests

Cover all ADR-028 Decision 14 and blueprint requirements, including:
- strict receipt scalar/candidate parsing;
- exact TASK/action/path/blob/status/actor authority flags;
- exact capacity states/fingerprints/freshness;
- exact receipt path and symlink/confinement safety;
- causal mtime ordering;
- exact ACTIVE authorization binding;
- active lease failure/mismatch;
- no failover/hot-handoff metadata;
- exact executor witness bytes;
- request/result fingerprint recomputation;
- proof fingerprint tamper detection;
- no alternate history/latest/glob/fuzzy receipt lookup;
- no authority or provider/executor mutation surfaces.

## Thin Executor Instructions

Primary Brain has completed architecture and implementation design.

Codex SHALL:
- read only the bounded files listed in the blueprint;
- not broad-search the repository;
- not redesign M10;
- create only the exact allowed proof/verifier/test files;
- run targeted commands only;
- STOP after targeted commands pass.

## Targeted Commands

```powershell
.\venv\Scripts\python.exe .\scripts\aios_m10_real_dispatch_proof.py verify
.\venv\Scripts\python.exe -m pytest tests/aios_bridge/test_m10_real_dispatch_proof.py -q
.\venv\Scripts\python.exe -m pytest tests/aios_bridge/test_runtime_dispatch.py tests/test_bridge_dispatch.py tests/aios_bridge/continuity/test_dispatch.py -q
```

Executor MUST NOT run the full repository suite.

## Publication Gate

After targeted commands pass, Human runs:

```powershell
.\venv\Scripts\python.exe .\bridge.py publish 39 `
  --action RUN `
  --test ".\venv\Scripts\python.exe -m pytest tests/ -q"
```

Final RESULT must report:

```text
TASK_ID: TASK-039
ACTION: RUN
EXECUTOR_ID: codex
EXECUTOR_FAILOVER: NO
HOT_HANDOFF: NO
```

## Acceptance

PASS requires:

```text
REAL_CAPACITY_OBSERVATIONS: PASS
REAL_BRIDGE_RECOMMENDATION_RECEIPT: PASS
DETERMINISTIC_SELECTED_EXECUTOR_CODEX: PASS
RECOMMENDATION_ONLY_NO_AUTH_MUTATION: PASS
HUMAN_APPROVAL_ORDERING: PASS
ACTIVE_CODEX_RUN_AUTHORIZATION: PASS
ACTIVE_CODEX_EXECUTOR_LEASE: PASS
EXECUTOR_STAGE_WITNESS: PASS
CANONICAL_PROOF_FINGERPRINT: PASS
RESULT_PROOF_AGREEMENT: PASS
M10_1_PRODUCTION_CHANGED: NO
M10_2_PRODUCTION_CHANGED: NO
FULL_REPO_TESTS: PASS
REGRESSIONS: 0
M10_3: PASS
```

After independent review PASS and Human-authorized merge, M10 is complete. M11 remains separate.