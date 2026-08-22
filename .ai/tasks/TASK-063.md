# TASK-063 — M11.3C Paid Brain Single-Call Timeout Envelope Hardening

STATUS: READY
CLASS: L3 — SECURITY-CRITICAL PAID-API RUNTIME HARDENING
MILESTONE: M11.3C
EXECUTOR_MODE: UNIFIED_AIOS_WORKER_DUAL_EXECUTOR
RECOMMENDED_EXECUTOR: codex

## Baseline

```text
MAIN_SHA: 2beadb559ade5b46442b26d5b720357faf94f518
TARGET_BRANCH: ai/task-063
```

TASK-062 is PASS + merged. Its first post-merge real operational attempt is closed forensic evidence and must never be retried with the same grant.

## Purpose

Correct the single live-proof operational issue discovered by M11.3C attempt #1: the production `paid-proof-execute` path hard-codes a 30-second MiniMax provider timeout, and the real call returned `TIMEOUT` at approximately 30.265 seconds.

TASK-063 MUST replace that magic timeout with a required explicit bounded timeout parameter while preserving every existing paid-API safety invariant.

TASK-063 RUN/FIX is strictly no-spend. It MUST NOT make a real paid provider call, use a real API credential, create/consume a real paid grant, or mutate the external forensic evidence from attempt #1.

## Authoritative Contracts

```text
ADR_036_PATH: .ai/decisions/ADR-036-M11-EXTERNAL-API-ESCAPE-HATCH-ARCHITECTURE-LOCK.md
ADR_036_BLOB_SHA: cf71c571d8e3fd611ea07d21f15ad0bf90ef6ecc
FORENSIC_PATH: .ai/context/TASK-063-M11.3C-LIVE-ATTEMPT-1-FORENSIC.md
FORENSIC_BLOB_SHA: 4c1fa6718ff7c59a1d33aa6f38fc238ea7bb6fba
BLUEPRINT_PATH: .ai/context/TASK-063-M11.3C-PAID-BRAIN-TIMEOUT-ENVELOPE-BLUEPRINT.md
BLUEPRINT_BLOB_SHA: 754f87d4feba0fa240461c05211740c3b4408d1a
PROOF_LOCK_PATH: .ai/context/TASK-062-PROOF-LOCK.json
PROOF_LOCK_BLOB_SHA: 9ff47f47c987f7e626f73b26ea9c783a59f6fd45
```

## Machine-Readable Executor Context

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/decisions/ADR-036-M11-EXTERNAL-API-ESCAPE-HATCH-ARCHITECTURE-LOCK.md","blob_sha":"cf71c571d8e3fd611ea07d21f15ad0bf90ef6ecc"},{"path":".ai/context/TASK-063-M11.3C-LIVE-ATTEMPT-1-FORENSIC.md","blob_sha":"4c1fa6718ff7c59a1d33aa6f38fc238ea7bb6fba"},{"path":".ai/context/TASK-063-M11.3C-PAID-BRAIN-TIMEOUT-ENVELOPE-BLUEPRINT.md","blob_sha":"754f87d4feba0fa240461c05211740c3b4408d1a"},{"path":".ai/context/TASK-062-PROOF-LOCK.json","blob_sha":"9ff47f47c987f7e626f73b26ea9c783a59f6fd45"}]

## Exact Writable Scope

EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","tests/test_bridge_paid_api_real_escape.py"]

Bridge-generated `.ai/results/RESULT-063.md` is publication output only.

If any other production/test path appears necessary, STOP and publish no implementation rather than broadening scope.

## Executor Dispatch Policy

DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

Human selects exactly one subscription Executor. No silent reroute, paid Executor, automatic executor failover, or second executor.

## Source Anchors — Current Main

```text
bridge.py: 20309cd003295e6f989adb84401ce4e36d30687f
tests/test_bridge_paid_api_real_escape.py: ea0fcfc0461f41728fe255336be518a05a939e85
src/aios_bridge/external_brain/providers/minimax.py: f907deeccf5d24ec80d4de58f7769330126f3624  # READ ONLY
```

## Locked Implementation Contract

Extend only the existing `paid-proof-execute` CLI with:

```text
--provider-timeout-seconds <integer>
```

Exact contract:

```text
REQUIRED: YES
MIN_SECONDS: 60
MAX_SECONDS: 180
DEFAULT_IF_OMITTED: NONE
RECOMMENDED_NEXT_LIVE_PROOF_SECONDS: 120
```

Omission, malformed/non-integer input, or an out-of-range value MUST fail before credential value access, grant consumption, provider construction, or provider invocation.

The validated timeout must be passed unchanged to the existing `MiniMaxOpenAIProvider(..., timeout_seconds=...)` production constructor.

Remove the live-path hard-coded `timeout_seconds=30.0`. Do not replace it with another hidden/default magic value.

Do not modify `MiniMaxOpenAIProvider`, `ModelGateway`, `paid_api_real_escape`, grant semantics, capacity semantics, M10 dispatch, proof-lock semantics, or proof receipt schemas.

## Safety Invariants — Preserve Exactly

```text
MAX_CALLS: 1
AUTO_RETRY: 0
SECOND_PAID_PROVIDER: 0
PAID_EXECUTOR: FORBIDDEN
GRANT_REUSE: FORBIDDEN
GRANT_REACTIVATION: FORBIDDEN
CONSUME_BEFORE_CALL: REQUIRED
MODEL_GATEWAY_INVOCATIONS: EXACTLY_ONE
EXECUTOR_AUTHORITY_CREATED: FALSE
BRAIN_OUTPUT_WORKTREE_AUTHORITY: FORBIDDEN
SECRET_VALUE_READ_BEFORE_EXISTING_POST-GATE_FACTORY: FORBIDDEN
```

A longer timeout is only a bounded wait envelope for the same one call. It grants no retry or extra spend authority.

## Mandatory Tests

Use only fake/local dependencies and dummy credentials/grants. Required coverage:

```text
1. paid-proof-execute requires --provider-timeout-seconds.
2. 60, 120, 180 are accepted.
3. 59, 181, zero, negative, malformed/non-integer values are rejected before execution.
4. The exact validated timeout reaches MiniMaxOpenAIProvider unchanged.
5. No fallback/default 30.0 remains on the live command path.
6. Invalid timeout => zero provider construction and zero provider call.
7. Credential value remains unread before the existing deferred post-gate provider factory.
8. Consume-before-call remains unchanged.
9. Provider TIMEOUT after consume leaves grant CONSUMED and causes zero retry/failover.
10. Same-grant replay still causes zero additional provider calls.
11. No test reaches external network or uses a real credential/grant.
```

Run targeted bridge paid-real-escape tests and full repository suite.

## Locked No-Spend Boundary

```text
REAL_PAID_API_CALL_DURING_TASK: FORBIDDEN
REAL_MINIMAX_NETWORK_DURING_TASK: FORBIDDEN
REAL_API_KEY_USE_DURING_TASK: FORBIDDEN
REAL_GRANT_CONSUME_DURING_TASK: FORBIDDEN
OLD_ATTEMPT_1_GRANT_REUSE: FORBIDDEN
NEW_PAID_GRANT_CREATION: FORBIDDEN
AUTO_RUN_POST_MERGE_PROOF: FORBIDDEN
```

## Out of Scope

```text
retry policy changes
provider failover
MiniMax provider redesign
ModelGateway redesign
M10 dispatch redesign
grant schema/consume changes
proof-lock/tokenizer/assets changes
proof receipt schema changes
capacity semantics
Executor lifecycle/lease changes
H1-H5 activation
Lean Merge Gate refinement
```

## Acceptance Criteria

TASK-063 may be published READY_FOR_REVIEW only if:

```text
HARD_CODED_30_SECOND_LIVE_TIMEOUT_REMOVED: YES
REQUIRED_BOUNDED_TIMEOUT_PARAMETER: YES
TIMEOUT_RANGE_SECONDS: 60..180
EXACT_TIMEOUT_WIRED_TO_PROVIDER: YES
CONSUME_BEFORE_CALL_PRESERVED: YES
MAX_CALLS_ONE_PRESERVED: YES
AUTO_RETRY_ZERO_PRESERVED: YES
SECOND_PAID_PROVIDER_ZERO_PRESERVED: YES
SECRET_BOUNDARY_PRESERVED: YES
TARGETED_TESTS_PASS: YES
FULL_REPO_TESTS_PASS: YES
SCOPE_EXACT: YES
REAL_PAID_API_CALL_DURING_TASK: NO
REAL_API_KEY_USE_DURING_TASK: NO
REAL_GRANT_CONSUME_DURING_TASK: NO
```

TASK-063 PASS + merge does not authorize another live MiniMax call. After merge, ChatGPT must prepare a fresh no-spend preflight using fresh capacity evidence and a fresh bounded Human paid grant. The next live call requires separate explicit Human authorization and will use `--provider-timeout-seconds 120`.
