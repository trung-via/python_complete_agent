# TASK-062 — M11.3C Real Operational Escape Harness

STATUS: READY
CLASS: L3 — SECURITY-CRITICAL PAID-API RUNTIME HARNESS
MILESTONE: M11.3C
EXECUTOR_MODE: UNIFIED_AIOS_WORKER_DUAL_EXECUTOR
RECOMMENDED_EXECUTOR: codex

## Baseline

```text
MAIN_SHA: d6f51f14188ffc56fd06bc887b68d9cad550c9e0
TARGET_BRANCH: ai/task-062
```

TASK-061 is ABORTED/CLOSED and is not a predecessor, implementation source, or reusable task. TASK-062 starts only from current merged main.

## Purpose

Implement the final reusable M11.3C real paid-API Brain escape harness while preserving a strict no-spend boundary during executor RUN/FIX.

TASK-062 itself MUST NOT make a real paid provider call, consume a real Human paid grant, or read/use a real API credential. The live MiniMax proof happens only after TASK-062 PASS + Human merge and a separate explicit Human paid-spend authorization.

## Authoritative Contracts

```text
ADR_036_PATH: .ai/decisions/ADR-036-M11-EXTERNAL-API-ESCAPE-HATCH-ARCHITECTURE-LOCK.md
ADR_036_BLOB_SHA: cf71c571d8e3fd611ea07d21f15ad0bf90ef6ecc
REVIEW_059_PATH: .ai/reviews/REVIEW-059.md
REVIEW_059_BLOB_SHA: aa8d0c3539b36051c17c44ed2b4724ba2c6d84f7
BLUEPRINT_PATH: .ai/context/TASK-062-M11.3C-REAL-OPERATIONAL-ESCAPE-HARNESS-BLUEPRINT.md
BLUEPRINT_BLOB_SHA: 5b9a6a366a390a2f9f0735ebeff022cf62c9b551
```

## Machine-Readable Executor Context

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/decisions/ADR-036-M11-EXTERNAL-API-ESCAPE-HATCH-ARCHITECTURE-LOCK.md","blob_sha":"cf71c571d8e3fd611ea07d21f15ad0bf90ef6ecc"},{"path":".ai/context/TASK-062-M11.3C-REAL-OPERATIONAL-ESCAPE-HARNESS-BLUEPRINT.md","blob_sha":"5b9a6a366a390a2f9f0735ebeff022cf62c9b551"},{"path":".ai/reviews/REVIEW-059.md","blob_sha":"aa8d0c3539b36051c17c44ed2b4724ba2c6d84f7"}]

## Exact Writable Scope

EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","src/aios_bridge/minimax_m3_input_counter.py","src/aios_bridge/paid_api_real_escape.py","tests/aios_bridge/test_minimax_m3_input_counter.py","tests/aios_bridge/test_paid_api_real_escape.py","tests/test_bridge_paid_api_real_escape.py"]

Bridge-generated `.ai/results/RESULT-062.md` is publication output only.

## Executor Dispatch Policy

DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

Human selects exactly one subscription Executor through the correct surface. No silent reroute, failover, paid Executor, or second executor.

## Source Anchors — Current Main

```text
bridge.py: 87f867af9cb4581724b4aaaee7b3cbf1bbe9a6d3
src/aios_bridge/continuity/dispatch.py: 9169884c079302f86bbda5f77a9a9d7ea6800dd9
src/aios_bridge/runtime_dispatch.py: 01a35d0ffed48f2fbb70649f4c67f0e894910805
src/aios_bridge/runtime_paid_api_grant.py: a3c7a446ff0f8195e68640493900776334a9e551
src/aios_bridge/paid_api_brain_escape.py: a3978dd69df6617b6fbf96f3f297ae4891e23b5a
src/aios_bridge/paid_api_operational_proof.py: 8425c49a571cbfa8959fb8c9d39b39100d3e4466
src/aios_bridge/paid_api_proof_preflight.py: 428006d82e611ea3a05681a44e3cd3bd7f408813
src/aios_bridge/minimax_m3_proof_lock.py: 76227e2d06d8067b934411b46a8ad6aa70b6ebb2
src/aios_bridge/minimax_m3_input_counter.py: 5dc1dc9cb6b7a65ccd944ef4c221c0863574a08b
src/aios_bridge/external_brain/gateway.py: 45d6ec94f3916362783f03f1474b6cc651d8d9e5
src/aios_bridge/external_brain/providers/minimax.py: f907deeccf5d24ec80d4de58f7769330126f3624
src/aios_bridge/external_brain/usage.py: 20abd5b43b723935c6632b95d22ec8794e20ae7c
```

These anchors are read-only authorities unless the path is explicitly in `EXECUTOR_ALLOWED_PATHS_JSON`.

## Core Requirement 1 — Exact Context Counter Seam

Extend `MiniMaxM3LocalProviderInputCounter` only enough to satisfy the existing External Brain `TokenCounter` surface:

```text
count(text: str) -> exact non-negative int
counter_id -> existing counter identity
is_exact -> true
```

`count(text)` MUST use the same already-loaded proof-locked pinned MiniMax tokenizer as `count_request()`.

Forbidden:

```text
second tokenizer implementation
download/network
fallback/approximate counter
new caller-controlled tokenizer path
manifest-only trust
```

Preserve all M11.2C.2/M11.3B proof-lock, digest, sandbox, symlink, size, and exact-class protections.

## Core Requirement 2 — `paid_api_real_escape` Runtime Orchestrator

Create `src/aios_bridge/paid_api_real_escape.py` implementing the blueprint R0-R10 semantics as reusable, bounded orchestration helpers.

Tests must be able to inject fake gateway/provider dependencies. The module MUST NOT perform repository discovery, hidden network, package install, asset download, task merge, executor activation, or grant creation.

The real production provider may be constructed only after all pre-call gates have succeeded.

## Core Requirement 3 — Bridge `paid-proof-execute`

Add the exact command:

```text
python bridge.py paid-proof-execute <task_id>
  --grant-id <grant-id>
  --proof-lock-path <canonical .ai/ path>
  --proof-lock-blob-sha <exact 40-hex blob>
  --subscription-brain-id <canonical actor id>
  --subscription-capacity-fingerprint <exact 64-hex>
  --paid-capacity-fingerprint <exact 64-hex>
```

No security override flags.

Implement exact R0-R10 order from the blueprint, including:

```text
R0 clean current main == origin/main; local refs only; no hidden fetch
R1 exact Git-bound MiniMax proof lock
R2 exact ACTIVE Human paid grant; PLAN-only proof; max_calls=1
R3 exact grant-bound authorized TASK artifact as deterministic context
R4 proof-locked local assets + same exact tokenizer for ContextBuilder and provider-input proof
R5 exactly two fresh BRAIN RuntimeCapacityRecord values
R6 subscription QUOTA_EXHAUSTED/UNAVAILABLE, paid MiniMax AVAILABLE; M10 paid selection only after grant-aware enablement
R7 exact context/full-input/output grant budgets
R8 durable consume-before-call + one ModelGateway invocation + no retry/failover
R9 original pre-call evidence correlated into PaidApiOperationalProofReceipt; persist bounded proposal/proof in external runtime
R10 replay with same consumed grant rejected before provider construction/call
```

## Core Requirement 4 — External Proof Artifacts

On a successful future live run, atomically/durably persist under external runtime only:

```text
paid_api_proofs/TASK-N/<sha256(grant_id)>/proposal.md
paid_api_proofs/TASK-N/<sha256(grant_id)>/proof.json
```

No worktree mutation.

`proposal.md` is validated advisory `ModelResponse.content` only.

`proof.json` must bind at least:

```text
runtime_main_sha
control_commit_sha
proof_lock_path/blob/fingerprint
subscription capacity fingerprint
paid capacity fingerprint
preflight fingerprint
operational proof fingerprint
proposal logical path + SHA-256
proof logical path
grant_consumed = true
provider_call_count = 1
retry_count = 0
executor_authority_created = false
```

No API key, auth header, raw provider body, raw request body, hidden reasoning, cookie, or absolute path.

## Core Requirement 5 — Failure/Replay Safety

Before grant consumption, any failure => zero provider call and grant remains ACTIVE.

After durable consume, any timeout/error/ledger failure/proof-write failure/crash => grant remains CONSUMED and no automatic retry.

Same-grant replay must fail before provider construction/invocation and tests must prove zero additional call count.

## Core Requirement 6 — Tests Are Strictly No-Spend

TASK-062 RUN/FIX must never make a real network/provider call.

Mandatory tests use fake/local transport, temp runtime stores, and dummy credential values only. Any actual external network path reached during tests must fail the test.

Required coverage includes:

```text
R0-R10 ordering
canonical proof lock and endpoint binding
exact ACTIVE grant and PLAN-only restriction
fresh BRAIN capacity records and exact fingerprints
subscription unavailable / paid available dispatch semantics
exact ContextBuilder count through pinned tokenizer seam
full provider-input budget proof
consume-before-call
one provider call only
no retry/failover
successful operational receipt correlation
external proposal/proof atomic persistence
no secret/absolute path leakage
provider failure leaves CONSUMED
ledger failure leaves CONSUMED
same-grant replay => zero extra provider calls
no Executor authority
```

Run targeted tests and full repository suite.

## Locked No-Spend Boundary for the Executor Task

```text
REAL_PAID_API_CALL_DURING_TASK: FORBIDDEN
REAL_MINIMAX_NETWORK_DURING_TASK: FORBIDDEN
REAL_API_KEY_USE_DURING_TASK: FORBIDDEN
REAL_GRANT_CONSUME_DURING_TASK: FORBIDDEN
AUTO_CREATE_PAID_GRANT: FORBIDDEN
AUTO_RUN_POST_MERGE_PROOF: FORBIDDEN
```

The presence of test code or a production command is never spend authorization.

## Out of Scope

```text
M11 paid Executor transport
OpenAI/Anthropic/Gemini paid provider additions
H1-H5 activation
TASK-061 implementation or ADR-039 recovery work
executor lifecycle/lease semantic changes
ModelGateway redesign
MiniMax provider redesign
M10 dispatch redesign
automatic patch application
merge automation
```

## Acceptance Criteria

TASK-062 may be published READY_FOR_REVIEW only if:

```text
HARNESS_IMPLEMENTED: YES
TARGETED_TESTS_PASS: YES
FULL_REPO_TESTS_PASS: YES
SCOPE_EXACT: YES
REAL_PAID_API_CALL_DURING_TASK: NO
REAL_API_KEY_USE_DURING_TASK: NO
REAL_GRANT_CONSUME_DURING_TASK: NO
```

TASK-062 PASS + merge does NOT itself complete the live M11.3C proof.

After merge, ChatGPT will prepare the separate Human-controlled live proof procedure. Only then may the Human create a fresh grant and explicitly authorize exactly one MiniMax call.
