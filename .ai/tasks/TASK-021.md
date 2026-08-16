# TASK-021 — Open Multi-Agent Continuity OS M2 Brain-Neutral Contract

## Work Class

`L3 — ARCHITECTURE / HIGH-RISK`

ChatGPT owns the contract and review. Antigravity owns detailed implementation planning, repository inspection, code, tests, and self-audit under ADR-015.

No separate ChatGPT implementation PLAN is required for this task.

## Baseline

Current canonical `main` at authoring:

```text
5c93561bf08d7fb0ed91c9199b0ae023c8b1ea4b
```

TASK-019 Canonical Project State and TASK-020 Usage & Efficiency Telemetry are merged.

## Objective

Implement the **Brain-Neutral Contract** milestone of ADR-010 without changing current execution authority.

The Continuity Core must be able to represent a Brain request/result independently of ChatGPT, Claude, Gemini, MiniMax, or any future provider surface.

This task defines the neutral contract only. It does not implement multi-Brain routing, automatic failover, chat UI automation, or a new execution path.

## Required Architecture

Add a small vendor-neutral Brain contract under:

```text
src/aios_bridge/continuity/
```

Preferred module:

```text
brain.py
```

Exact file structure may differ if Antigravity can justify a smaller/cleaner implementation while preserving the contract below.

## Required Concepts

Implement immutable, bounded types equivalent to:

```text
BrainId
BrainCapability
BrainOperation
BrainRequest
BrainResult
BrainResultStatus
BrainArtifactRef / evidence pointer as needed
```

Do not duplicate an existing suitable Continuity enum/type when reuse is semantically correct.

### Brain operations

At minimum the neutral contract must support the currently locked reasoning operations:

```text
TASK
TASK_AND_PLAN
PLAN
DIAGNOSIS
PATCH_PROPOSAL
REVIEW
```

### Brain result status

Use a small closed set sufficient to represent contract-level outcomes, for example:

```text
SUCCESS
REJECTED
FAILED
INCOMPLETE
```

Exact names may vary if semantics remain closed and deterministic.

## BrainRequest Contract

A neutral request SHALL carry only bounded control/navigation data required for a Brain operation. It SHOULD support concepts equivalent to:

```text
schema_version
task_id
request_id
brain_id
operation
objective_or_instruction
context_refs[]
output_contract
```

Important constraints:
- no vendor-specific request payload branch;
- no API key/token/session/cookie fields;
- no raw chat transcript persistence;
- no hidden reasoning / chain-of-thought field;
- no arbitrary repository dump;
- no execution authority;
- no shell/filesystem/browser/Git mutation instructions beyond bounded advisory task context;
- request identity and artifact paths/refs must fail closed.

Context references must point to bounded AIOS/Git artifacts or explicit evidence descriptors; they are navigation pointers, not embedded whole-repo context.

## BrainResult Contract

A neutral result SHALL represent an advisory Brain outcome without granting execution authority. It SHOULD support concepts equivalent to:

```text
schema_version
task_id
request_id
brain_id
operation
status
output_type
artifact_ref | bounded_content_ref
usage_ref | null
error_code | null
```

The result MUST NOT persist hidden reasoning. A Brain may produce a TASK/PLAN/REVIEW/etc artifact, but Continuity Core stores only the bounded result/artifact pointer and deterministic metadata needed for continuation.

## Brain Capability Contract

Represent capability declaratively and vendor-neutrally. At minimum distinguish whether a Brain surface can perform the supported reasoning operations.

Capability data is descriptive. It MUST NOT itself:
- select a Brain automatically;
- invoke a Brain;
- authorize execution;
- trigger fallback/failover.

No LLM router or classifier in TASK-021.

## Determinism / Validation

Fail closed for at least:
- unknown schema fields;
- unsupported schema version;
- invalid canonical `^TASK-\d+$` identity;
- invalid/unsafe actor or request IDs;
- unsupported operations/status/output types;
- duplicate context references where duplication is meaningless;
- unsafe/non-AIOS artifact paths where artifact refs are used;
- sensitive credential/profile paths;
- unbounded/free-form persistence fields;
- oversized serialized records.

Reuse the existing Continuity 16 KiB serialized-size policy unless there is a compelling contract reason to be stricter.

Canonical JSON serialization and deterministic SHA-256 fingerprinting are required for top-level request/result records.

## Separation From Existing Provider Layers

Do NOT mutate or merge this contract into:

```text
src/providers/base.py
src/providers/gemini.py
src/aios_bridge/external_brain/*
```

Existing Python Agent runtime providers and External Brain provider/gateway contracts remain intact.

TASK-021 may add compatibility/conversion helpers only if they are pure, one-way/bounded, clearly optional, and do not change those existing contracts. Prefer no adapter implementation in this milestone unless required by tests.

## Authority / Non-Goals

Do NOT implement:
- BrainAdapter execution transport;
- ChatGPT/Claude/Gemini API integration;
- chat.openai.com or other chat UI automation;
- automatic Brain selection/router;
- automatic failover;
- ExecutorAdapter;
- Executor Lease;
- executor switching;
- model invocation;
- Bridge handoff/sync/publish semantic changes;
- RUN/FIX/MERGE authority changes;
- source-code execution from a Brain result.

Antigravity remains the sole implemented Executor for this task. Human approval remains authoritative.

## Executor Planning Requirement

After `/aios-worker RUN TASK-021`, Antigravity SHALL create its own bounded implementation plan before editing code.

The plan may remain executor-local/operational unless an existing workflow requires it to be persisted. It SHALL cover:
- exact files/types to add or reuse;
- validation boundaries;
- serialization/fingerprint design;
- focused test matrix;
- proof that existing provider/Bridge authority contracts remain unchanged.

If Antigravity discovers that fulfilling the task requires changing a locked architectural invariant, STOP and report the conflict rather than inventing a new policy.

## Required Tests

At minimum cover:
1. valid neutral BrainRequest and BrainResult round-trip;
2. deterministic canonical JSON and fingerprint;
3. canonical task identity validation;
4. actor/request ID validation;
5. closed operation/status/output-type validation;
6. unknown-field rejection at locked schema layers;
7. bounded context/evidence references;
8. duplicate reference rejection where applicable;
9. unsafe/sensitive path rejection;
10. 16 KiB fail-closed behavior;
11. capability declarations are descriptive only;
12. no secret/chat transcript/reasoning fields accepted;
13. no invocation/authority side effects;
14. existing Continuity tests green;
15. existing Bridge tests green;
16. full repository tests green.

No live external calls.

## RESULT / Review Manifest

`RESULT-021.md` SHALL include a compact delta-first Review Manifest with:

```text
BASE_SHA
IMPLEMENTATION_SHA
CHANGED_FILES
TEST_SUMMARY
BRIDGE_BEHAVIOR_CHANGED
AUTHORITY_WIDENED
LIVE_EXTERNAL_CALLS
EXECUTOR_PLAN_OWNER: antigravity
CHATGPT_IMPLEMENTATION_PLAN_USED: NO
```

Also include telemetry-compatible observable workload data when available, but do not invent exact token values.

## Acceptance Criteria

1. Neutral Brain request/result/capability contract is implemented under Continuity Core.
2. No vendor-specific branch exists in the core schema.
3. No Brain invocation, router, fallback or execution authority is introduced.
4. Existing runtime provider and External Brain contracts remain unchanged.
5. Deterministic validation/serialization/fingerprint tests pass.
6. Focused Continuity, Bridge and full repository suites pass with zero regressions.
7. RESULT proves Antigravity owned implementation planning and ChatGPT did not create a separate implementation PLAN.
8. Review can be performed delta-first from RESULT + compare/patch evidence.
