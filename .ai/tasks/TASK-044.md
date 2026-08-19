# TASK-044 — E5 Zero-Copy/Paste Operational Proof

STATUS: READY
CLASS: L4 — REAL OPERATIONAL PROOF / ZERO-COPY-PASTE / E4 AUTOMATED EXECUTION
EXECUTOR_MODE: E4_AUTOMATED_REAL_CODEX

## Baseline

```text
MAIN_SHA: a01b5f4b028ccdc416004b3d25608d23fb922c51
TARGET_BRANCH: ai/task-044
```

## Authoritative Contract

```text
ADR_PATH: .ai/decisions/ADR-033-E5-ZERO-COPY-PASTE-OPERATIONAL-PROOF-CONTRACT-LOCK.md
ADR_BLOB_SHA: b9f98dfd59d4785682ea5917052ca11be91274cd
BLUEPRINT_PATH: .ai/context/TASK-044-E5-ZERO-COPY-PASTE-OPERATIONAL-PROOF-BLUEPRINT.md
BLUEPRINT_BLOB_SHA: 67747c4eb73f75f6f562ed4ebe5bc3fde4d68480
```

## E-Series Position

```text
E1 — Executor Invocation Contract                  COMPLETE
E2 — Codex Local Transport                         COMPLETE
E3 — Bounded Context Pack Delivery                 COMPLETE
E4 — Result Collection + Auto Publication          COMPLETE
E5 — Zero-Copy/Paste Operational Proof             ← THIS TASK
```

H-Series remains separate and DEFERRED. M11 remains separate.

## Objective

Prove one real E4 happy-path execution with no manual executor prompt copy/paste and no manual publication step.

The Human will authorize TASK-044 for `codex`, then run only the merged E4 execute command. The executor must receive this TASK plus its ordered ADR/blueprint context through E3 and create exactly one proof file. E4 must then automatically run its Git/scope/trust gates, full repository suite, RESULT generation, commit, and push.

No runtime implementation is requested by TASK-044.

## Task Challenge

```text
TASK_CHALLENGE: 723736ac142eb3afc6593e8328c584e5
```

The proof file must also recover the independent ADR and blueprint challenges from the E3-delivered context artifacts.

## Machine-Readable Executor Context

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/decisions/ADR-033-E5-ZERO-COPY-PASTE-OPERATIONAL-PROOF-CONTRACT-LOCK.md","blob_sha":"b9f98dfd59d4785682ea5917052ca11be91274cd"},{"path":".ai/context/TASK-044-E5-ZERO-COPY-PASTE-OPERATIONAL-PROOF-BLUEPRINT.md","blob_sha":"67747c4eb73f75f6f562ed4ebe5bc3fde4d68480"}]

The order is authoritative and part of the exact Human-approved TASK blob.

## Machine-Readable Executor Worktree Scope

EXECUTOR_ALLOWED_PATHS_JSON: [".ai/proofs/E5-ZERO-COPY-PASTE-OPERATIONAL-PROOF.md"]

`RESULT-044.md` is Bridge-generated only and is not Executor-writable scope.

## Executor Dispatch Policy

DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

This policy grants no authority. The Human must explicitly select `codex` during approval.

## Exact Executor Output

Create exactly one file:

```text
.ai/proofs/E5-ZERO-COPY-PASTE-OPERATIONAL-PROOF.md
```

with exactly this semantic content:

```text
# E5 Zero-Copy/Paste Operational Proof

TASK_ID: TASK-044
PROOF_KIND: REAL_E4_CODEX_AUTOMATION
TASK_CHALLENGE: 723736ac142eb3afc6593e8328c584e5
ADR_CHALLENGE: a9eb3fa7b39555d964f0d03dfd74dcd6
BLUEPRINT_CHALLENGE: b60d55bc08ce25adab0658c10e4348a8
CHALLENGE_DIGEST_SHA256: 8661ac8bf8c0b8382a5161b746facb0d70fe6146ea6b20b06bf702d88dc16073
EXPECTED_DIRTY_PATH_COUNT: 1
```

A single final newline is allowed.

Do not add any other content.

## Executor Instructions

This task is already authorized only when invoked through `bridge.py execute 44` after Human approval.

Executor behavior:

```text
1. Use the TASK/ADR/blueprint content already present in the E3 payload.
2. Do not request a manually copied prompt or additional task context.
3. Do not broad-search or redesign the repository.
4. Create the exact proof file only.
5. Do not run repository tests; E4 publication owns the full suite.
6. Do not commit, push, publish, switch branch, merge, retry, or invoke another executor/model.
7. Do not modify Git administration or any path outside the exact allowed file.
8. Return normally after the proof file is written so E2 can emit EXITED_ZERO.
```

If any challenge/context is missing or inconsistent, fail closed rather than guessing.

## Forbidden Scope

Executor must not modify:

```text
bridge.py
src/**
tests/**
docs/**
.ai/tasks/**
.ai/reviews/**
.ai/decisions/**
.ai/context/**
.ai/results/**
.git/**
```

Do not implement E1-E4 changes, M11, or H1-H5.

## Required Operational Path

Successful E5 evidence is valid only when the Human uses:

```text
bridge.py approve 44 --kind task --executor codex
bridge.py execute 44
```

and does NOT use on the successful path:

```text
bridge.py context 44
manual Codex UI prompt
manual codex exec
bridge.py publish 44
```

Ancillary `git pull`, `bridge.py sync`, and `bridge.py pending` do not weaken zero-copy proof because they do not transmit executor task instructions.

## Expected Bridge Evidence

The Bridge-generated RESULT-044 must contain the E4 automatic-execution notes generated by the merged runtime, including:

```text
E4_AUTO_EXECUTION: YES
E4_CONTROL_COMMIT_SHA: <40-hex>
E4_CONTEXT_MANIFEST_FINGERPRINT: <64-hex>
E4_INVOCATION_FINGERPRINT: <64-hex>
E4_INVOCATION_RECEIPT_FINGERPRINT: <64-hex>
E4_TRANSPORT_STATUS: EXITED_ZERO
E4_ALLOWED_SCOPE_VERIFIED: PASS
E4_PUBLICATION_TRUST_VERIFIED: PASS
E4_DIRTY_PATH_COUNT: 1
```

Full repository tests must be run automatically by E4 and finish with exit code 0.

## Acceptance

Independent ChatGPT review must prove:

```text
BASELINE_MAIN_EXACT: PASS
TASK_BRANCH_FAST_FORWARD: PASS
ONLY_PROOF_PLUS_RESULT_CHANGED: PASS
TASK_CHALLENGE_EXACT: PASS
ADR_CHALLENGE_EXACT: PASS
BLUEPRINT_CHALLENGE_EXACT: PASS
CHALLENGE_DIGEST_EXACT: PASS
E4_AUTO_EXECUTION: PASS
REAL_CODEX_TRANSPORT_RECEIPT_EVIDENCE: PASS
E4_SCOPE_GATE: PASS
E4_PUBLICATION_TRUST_GATE: PASS
E4_DIRTY_PATH_COUNT_1: PASS
FULL_REPO_TESTS: PASS
REGRESSIONS: 0
MANUAL_CONTEXT_REQUIRED: NO
MANUAL_PROMPT_COPY_PASTE_REQUIRED: NO
MANUAL_CODEX_INVOCATION_REQUIRED: NO
MANUAL_PUBLISH_REQUIRED: NO
HUMAN_RUN_AUTHORIZATION_REQUIRED: YES
HUMAN_MERGE_AUTHORIZATION_REQUIRED: YES
FINAL_INDEPENDENT_AUDIT: PASS
E5: PASS
```

Only Human may authorize merge.
