# TASK-068 — One-Shot Real Codex Local Executor Operational Proof

STATUS: READY
CLASS: L1 — OPERATIONAL PROOF / SUBSCRIPTION LOCAL EXECUTOR
MILESTONE: POST-H0 CODEX RELIABILITY PROOF BEFORE H1
EXECUTOR_MODE: CODEX_ONLY_ONE_SHOT_PROOF
RECOMMENDED_EXECUTOR: codex

## Baseline

```text
MAIN_SHA: 08d82392c807d334636a902fe3bcfa5bd70e7b26
TARGET_BRANCH: ai/task-068
H0_STATUS: COMPLETE
TASK_067_STATUS: PASS / HUMAN_MERGED
CODEX_LOCAL_DIAGNOSTICS_HARDENED: YES
CODEX_LOCAL_PATH_OPERATIONALLY_PROVEN: NO
H1_STARTED: NO
M11_STATUS: OPERATIONALLY_PROVEN / CLOSED
M12_CREATED: NO
PAID_API_CALL_ALLOWED: NO
NETWORK_CALL_ALLOWED: NO
WEB_SEARCH_ALLOWED: NO
AUTO_RETRY_ALLOWED: NO
AUTO_REROUTE_ALLOWED: NO
MAX_REAL_CODEX_INVOCATIONS_PER_ATTEMPT: 1
REAL_CODEX_INVOCATION_PREAUTHORIZED: NO
REAL_CODEX_INVOCATION_ALLOWED_AFTER_EXPLICIT_HUMAN_RUN: YES
```

TASK-068 is a proof-only task. It must not change AIOS Bridge or H-Series production code. Its only purpose is to demonstrate that the merged local Codex executor path can receive the bounded AIOS payload, create one exact authorized worktree delta, pass E4 Git/scope validation, pass the full repository test suite, and publish RESULT through the normal Bridge path.

Creating or reading TASK-068 does not itself authorize a Codex invocation. The real subscription Codex process may start only when the Human explicitly runs the Codex worker surface for this task.

## Authoritative Context

```text
ADR_041_PATH: .ai/decisions/ADR-041-CODEX-LOCAL-EXECUTOR-ONE-SHOT-OPERATIONAL-PROOF-CONTRACT-LOCK.md
ADR_041_BLOB_SHA: a5a238f771ab3f88a2ddb10ce984434c4b4f512d

ADR_040_PATH: .ai/decisions/ADR-040-CODEX-LOCAL-TRANSPORT-BOUNDED-DIAGNOSTIC-OBSERVABILITY-CONTRACT-LOCK.md
ADR_040_BLOB_SHA: 04937776829675e77a1651152bba16e7e7f31426

REVIEW_067_PATH: .ai/reviews/REVIEW-067.md
REVIEW_067_BLOB_SHA: 17d8d878aaf27b0de28389fff5e2872254172b86
```

## Machine-Readable Executor Context

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/decisions/ADR-041-CODEX-LOCAL-EXECUTOR-ONE-SHOT-OPERATIONAL-PROOF-CONTRACT-LOCK.md","blob_sha":"a5a238f771ab3f88a2ddb10ce984434c4b4f512d"},{"path":".ai/decisions/ADR-040-CODEX-LOCAL-TRANSPORT-BOUNDED-DIAGNOSTIC-OBSERVABILITY-CONTRACT-LOCK.md","blob_sha":"04937776829675e77a1651152bba16e7e7f31426"},{"path":".ai/reviews/REVIEW-067.md","blob_sha":"17d8d878aaf27b0de28389fff5e2872254172b86"}]

## Exact Writable Scope

EXECUTOR_ALLOWED_PATHS_JSON: ["proofs/TASK-068-CODEX-LOCAL-EXECUTOR-PROOF.md"]

Bridge-generated publication output:

```text
.ai/results/RESULT-068.md
```

is publication output only and is not executor writable scope.

The executor MUST NOT create, edit, delete, rename, stage, commit, or push any other worktree path.

## Executor Dispatch Policy

DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

TASK-068 is intentionally Codex-only. There is no Antigravity candidate and no fallback candidate.

If the Codex attempt fails, STOP. Do not retry the task, do not reroute to Antigravity, and do not make a second real Codex invocation under the same attempt.

## Exact Executor Instruction

Create exactly one file:

```text
proofs/TASK-068-CODEX-LOCAL-EXECUTOR-PROOF.md
```

with exactly the UTF-8/LF content below and one trailing LF:

```text
# TASK-068 Codex Local Executor Operational Proof

TASK_ID: TASK-068
EXECUTOR_ID: codex
TRANSPORT_ID: codex-local-v1
PROOF_KIND: REAL_LOCAL_EXECUTOR_AUTHORIZED_WRITE
BASELINE_MAIN_SHA: 08d82392c807d334636a902fe3bcfa5bd70e7b26
NETWORK_REQUIRED: NO
WEB_SEARCH_REQUIRED: NO
PAID_API_REQUIRED: NO
AUTO_RETRY_ALLOWED: NO
AUTO_REROUTE_ALLOWED: NO
EXPECTED_DIRTY_PATH_COUNT: 1
EXPECTED_DIRTY_PATH: proofs/TASK-068-CODEX-LOCAL-EXECUTOR-PROOF.md

RESULT: CODEX_CREATED_THIS_AUTHORIZED_DELTA
```

Do not add timestamps, commentary, generated prose, machine-specific paths, model names, reasoning, credentials, tokens, extra headings, or extra whitespace-only lines.

After creating the exact file, stop implementation work. Do not modify production code or tests. E4 owns post-executor Git/scope validation, canonical full-suite testing, commit/push/publication, and RESULT generation.

## Proof Invariants

The attempt is valid only if:

```text
EXECUTOR_ID: codex
TRANSPORT_ID: codex-local-v1
REAL_CODEX_PROCESS_SPAWN_COUNT: 1
CANONICAL_RECEIPT_STATUS: EXITED_ZERO
CANONICAL_RECEIPT_EXIT_CODE: 0
EXECUTOR_CREATED_DIRTY_PATH_COUNT: 1
EXECUTOR_CREATED_DIRTY_PATH: proofs/TASK-068-CODEX-LOCAL-EXECUTOR-PROOF.md
OUT_OF_SCOPE_DIRTY_PATH_COUNT: 0
EXECUTOR_HEAD_ADVANCE_BEFORE_E4_PUBLICATION: 0
E4_SCOPE_GATE: PASS
FULL_REPOSITORY_TESTS: PASS
RESULT_068_PUBLICATION: PASS
AUTO_RETRY_COUNT: 0
AUTO_REROUTE_COUNT: 0
SECOND_EXECUTOR_USED: NO
PAID_API_USED: NO
NETWORK_USED_BY_TOOL_SIDE: NO
WEB_SEARCH_USED: NO
RAW_STDOUT_PERSISTED: NO
RAW_STDERR_PERSISTED: NO
```

Transport exit zero without the exact proof-file delta is failure.

## Fail-Closed Conditions

Any of the following ends the attempt:

```text
FAILED_TO_START
EXITED_NONZERO
TIMED_OUT
INTERRUPTED
EXITED_ZERO + no dirty path
wrong proof-file bytes
extra dirty path
out-of-scope dirty path
executor commits or advances HEAD before E4 publication
full repository test failure
publication integrity failure
lease/runtime continuity failure
```

On failure:

```text
RETRY: NO
REROUTE: NO
ANTIGRAVITY_FALLBACK: NO
SECOND_CODEX_CALL: NO
PAID_API_FALLBACK: NO
```

Preserve existing runtime/diagnostic evidence and return control to Human + ChatGPT review.

## Explicitly Forbidden Scope

Do not modify:

```text
bridge.py
src/**
tests/**
requirements.txt
.agents/**
.ai/tasks/**
.ai/reviews/**
.ai/decisions/**
.ai/context/**
.ai/proofs/**
.ai/results/**       # Bridge publication only; executor must not edit manually
docs/**
```

Do not use:

```text
network access
web search
external provider API
provider API keys
MiniMax or other paid API
Codex API-key fallback
second executor
auto retry
auto reroute
manual git commit
manual git push
manual RESULT fabrication
sandbox weakening
session resume/history lookup
```

## E4 Validation

E4 must perform the existing post-executor gates without TASK-068 changing Bridge code:

1. canonical InvocationReceipt validation;
2. one real executor result only;
3. post-executor branch unchanged;
4. pre-publication HEAD unchanged;
5. dirty path set equals exactly the one allowed proof path;
6. no out-of-scope paths;
7. full repository test command succeeds;
8. publication commits/pushes RESULT through the existing E4 path;
9. published SHA and RESULT blob pass existing integrity checks.

Canonical full-suite command remains the Bridge-owned command equivalent to:

```powershell
.\venv\Scripts\python.exe -m pytest tests/ -q
```

Pre-proof merged baseline evidence from TASK-067:

```text
2092 passed, 7 skipped, 0 failed
```

## Required RESULT-068 Evidence

The Bridge-generated RESULT-068 must be consistent with at minimum:

```text
TASK: TASK-068
ACTION: RUN
EXECUTOR: codex
E4_AUTO_EXECUTION: YES
E4_TRANSPORT_STATUS: EXITED_ZERO
E4_ALLOWED_SCOPE_VERIFIED: PASS
E4_PUBLICATION_TRUST_VERIFIED: PASS
E4_DIRTY_PATH_COUNT: 1
FULL_REPOSITORY_TESTS: PASS
```

The exact published task SHA, RESULT blob SHA, invocation/receipt fingerprints, test command/result, and branch must be preserved by the existing publication path.

No manually authored RESULT-068 is acceptable.

## Acceptance Criteria

TASK-068 may be submitted for ChatGPT review only when:

```text
REAL_CODEX_INVOCATION: YES
REAL_CODEX_INVOCATION_COUNT: 1
EXECUTOR_ID: codex
TRANSPORT_ID: codex-local-v1
CANONICAL_RECEIPT_STATUS: EXITED_ZERO
AUTHORIZED_DIRTY_PATH_COUNT: 1
AUTHORIZED_DIRTY_PATH_EXACT: YES
PROOF_FILE_CONTENT_EXACT: YES
OUT_OF_SCOPE_DIRTY_PATH_COUNT: 0
E4_SCOPE_GATE: PASS
FULL_REPOSITORY_TESTS: PASS
RESULT_PUBLICATION: PASS
AUTO_RETRY: NO
AUTO_REROUTE: NO
SECOND_EXECUTOR_USED: NO
PAID_API_USED: NO
H0_CHANGED: NO
H1_STARTED: NO
```

## Post-Task Authority

Successful runtime publication does not itself authorize H1.

Required sequence:

```text
TASK-068 RESULT published
  -> ChatGPT exact-SHA Review TASK-068
  -> PASS
  -> explicit Human Merge TASK-068
  -> CODEX_LOCAL_PATH_OPERATIONALLY_PROVEN: YES
  -> DUAL_EXECUTOR_OPERATIONAL_BASELINE: PROVEN
  -> H1 may be authorized
```

Until Human merge after PASS:

```text
CODEX_LOCAL_PATH_OPERATIONALLY_PROVEN: NO
H1_AUTHORIZED: NO
```
