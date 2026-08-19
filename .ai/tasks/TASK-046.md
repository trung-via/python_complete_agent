# TASK-046 — E5 Zero-Copy/Paste Operational Proof #2

STATUS: READY
CLASS: L4 — REAL OPERATIONAL PROOF / ZERO-COPY-PASTE / E2.1 + E4 AUTOMATED EXECUTION
EXECUTOR_MODE: E4_AUTOMATED_REAL_CODEX

## Baseline

```text
MAIN_SHA: 7b4e8bbe1322c0e26338071ca3be7bf08a3144ec
TARGET_BRANCH: ai/task-046
```

## Authoritative Contract

```text
ADR_PATH: .ai/decisions/ADR-035-E5-SECOND-ZERO-COPY-OPERATIONAL-PROOF-CONTRACT-LOCK.md
ADR_BLOB_SHA: 3e2881b5710c4af85594a6fe9f2f963397dfbd83
BLUEPRINT_PATH: .ai/context/TASK-046-E5-SECOND-ZERO-COPY-OPERATIONAL-PROOF-BLUEPRINT.md
BLUEPRINT_BLOB_SHA: 38fdeeaa0d11ecf85d5b216ee4419079ae4d1cb9
```

## E-Series Position

```text
E1 — Executor Invocation Contract                  COMPLETE
E2 — Codex Local Transport                         COMPLETE
E2.1 — Codex CLI argument compatibility            COMPLETE + MERGED
E3 — Bounded Context Pack Delivery                 COMPLETE
E4 — Result Collection + Auto Publication          COMPLETE
E5 — Zero-Copy/Paste Operational Proof             ← THIS TASK
```

TASK-044 remains a failed E5 attempt and is not valid successful proof. TASK-046 uses fresh challenges and the E2.1-fixed baseline.

## Objective

Prove one successful real E4/E2.1 happy-path execution with no manual executor prompt copy/paste and no manual publication step.

The Human explicitly authorizes TASK-046 for `codex`, then runs only `bridge.py execute 46`. Codex must receive this TASK plus the ordered ADR/blueprint context through E3 and create exactly one proof file. E4 then mechanically validates scope/publication trust, runs the full repository suite, creates RESULT-046, commits, and pushes.

No runtime implementation is requested.

## Fresh Task Challenge

```text
TASK_CHALLENGE: eaddcdd98c49d5c298f2b22dcf3244fe
```

The proof file must recover the independent ADR and blueprint challenges from the E3 context payload.

## Machine-Readable Executor Context

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/decisions/ADR-035-E5-SECOND-ZERO-COPY-OPERATIONAL-PROOF-CONTRACT-LOCK.md","blob_sha":"3e2881b5710c4af85594a6fe9f2f963397dfbd83"},{"path":".ai/context/TASK-046-E5-SECOND-ZERO-COPY-OPERATIONAL-PROOF-BLUEPRINT.md","blob_sha":"38fdeeaa0d11ecf85d5b216ee4419079ae4d1cb9"}]

The order is authoritative and part of this exact Human-approved TASK blob.

## Machine-Readable Executor Worktree Scope

EXECUTOR_ALLOWED_PATHS_JSON: [".ai/proofs/E5-ZERO-COPY-PASTE-OPERATIONAL-PROOF-046.md"]

`RESULT-046.md` is Bridge-generated only and is not Executor-writable scope.

## Executor Dispatch Policy

DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

This policy grants no authority. Human approval explicitly selects `codex`.

## Exact Executor Output

Create exactly:

```text
.ai/proofs/E5-ZERO-COPY-PASTE-OPERATIONAL-PROOF-046.md
```

with exactly this semantic content:

```text
# E5 Zero-Copy/Paste Operational Proof #2

TASK_ID: TASK-046
PROOF_KIND: REAL_E4_CODEX_AUTOMATION_AFTER_E2_1
TASK_CHALLENGE: eaddcdd98c49d5c298f2b22dcf3244fe
ADR_CHALLENGE: ee4b936f9d1394f00af734bae19bc34f
BLUEPRINT_CHALLENGE: 17aab42d282621a9f2d1e89f93887da3
CHALLENGE_DIGEST_SHA256: 0c3e1100d0abf6c249e013fd774823d91ec8472dbb51b24356013e5f729cabbf
EXPECTED_DIRTY_PATH_COUNT: 1
```

A single final newline is allowed. Do not add any other content.

## Executor Instructions

This task becomes executable only through `bridge.py execute 46` after Human approval.

Executor behavior:

```text
1. Use only the TASK/ADR/blueprint content already present in the E3 payload.
2. Do not request manually copied context or an additional prompt.
3. Do not broad-search or redesign the repository.
4. Create the exact proof file only.
5. Do not run repository tests; E4 publication owns the full suite.
6. Do not commit, push, publish, switch branch, merge, retry, or invoke another executor/model.
7. Do not modify Git administration or any path outside the exact allowed file.
8. Return normally after writing the proof file so E2.1 can emit EXITED_ZERO.
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
.ai/proofs/E5-ZERO-COPY-PASTE-OPERATIONAL-PROOF.md
.git/**
```

Do not modify/retry TASK-044. Do not implement M11 or H1-H5.

## Required Operational Path

Successful E5 evidence is valid only when the Human uses:

```text
bridge.py approve 46 --kind task --executor codex
bridge.py execute 46
```

and does NOT use on the successful path:

```text
bridge.py context 46
manual Codex UI prompt
manual codex exec
bridge.py publish 46
```

`git pull`, `bridge.py sync`, and `bridge.py pending` are ancillary synchronization operations and do not transmit executor instructions.

## Expected Bridge Evidence

Bridge-generated RESULT-046 must contain:

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

E4 must automatically run the fixed full repository suite and obtain exit code 0.

Relative to baseline main, task branch changes must be exactly:

```text
.ai/proofs/E5-ZERO-COPY-PASTE-OPERATIONAL-PROOF-046.md
.ai/results/RESULT-046.md
```

## Acceptance

Independent ChatGPT review must prove:

```text
BASELINE_MAIN_EXACT: PASS
BASELINE_INCLUDES_E2_1_FIX: PASS
TASK_BRANCH_FAST_FORWARD: PASS
ONLY_PROOF_PLUS_RESULT_CHANGED: PASS
TASK_CHALLENGE_EXACT: PASS
ADR_CHALLENGE_EXACT: PASS
BLUEPRINT_CHALLENGE_EXACT: PASS
CHALLENGE_DIGEST_EXACT: PASS
E4_AUTO_EXECUTION: PASS
REAL_CODEX_E2_1_RECEIPT_EVIDENCE: PASS
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