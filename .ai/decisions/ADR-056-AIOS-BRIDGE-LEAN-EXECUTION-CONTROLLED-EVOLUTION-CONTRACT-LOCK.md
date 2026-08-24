# ADR-056 — AIOS Bridge Lean Execution Controlled Evolution Contract Lock

STATUS: ACCEPTED
DECISION_TYPE: ARCHITECTURAL_UPGRADE
HUMAN_APPROVED: YES
CANONICAL_ROADMAP: .ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.0.md
ROADMAP_ID: AIOS-BRIDGE-LEAN-EXECUTION
ROADMAP_VERSION: 1.0

## Context

AIOS Bridge has proven strong control-plane properties: authorization, executor leases, task/review binding, canonical roadmap binding, scope enforcement, provenance, publication trust, reviewed-head merge safety, and bounded recovery/handoff.

Recent delivery evidence shows increasing Time-to-Trusted-Capability overhead from per-task validation/review mechanics, including repeated full-repository testing, uneven executor execution paths, and insufficient execution telemetry. Rewriting the Bridge would discard proven safety work and delay product delivery. The required change is a controlled evolution that preserves authority semantics while extracting/refactoring the execution and validation plane.

## Decision

Adopt the locked AIOS Bridge Lean Execution Refactor roadmap v1.0.

The Bridge remains the control-plane authority. Execution lifecycle and validation policy become explicit, provider-neutral components behind Bridge authority.

### Preserve Exactly

```text
Human/task/review authority boundaries
executor lease semantics
canonical roadmap/task binding
scope enforcement
publication trust
reviewed-head merge safety
no force update
no automatic retry
no automatic reroute
Human authority for executor substitution/handoff
```

### Refactor / Extract

```text
validation ownership
validation plan/profile
full-suite certification ownership
execution telemetry
executor session lifecycle
checkpoint/resume
capacity suspension
provider adapters
capability batching
```

## Provider-Neutral Invariant

Antigravity, Codex, and future Claude Code must use the same semantic execution lifecycle and validation policy. Differences are transport/session implementation details only.

The existing UI surfaces may remain physically distinct for correct executor identity, but they must converge into the same Bridge-authorized execution contract.

## P0 Immediate Boundary

P0 is authorized now and is limited to:

```text
single-owner validation semantics
removal of duplicate full-suite execution
machine-readable validation plan
execution/test telemetry sufficient to count and time validation work
Antigravity/Codex parity at the validation boundary
future Claude compatibility at contract level
```

P0 MUST NOT:

```text
change task/review/lease/roadmap authority
create automatic reroute or retry
batch multiple task authorities
change merge authority
create public resume semantics
open H5
rewrite Bridge from scratch
```

P1-P3 remain locked pending completion/evidence of their predecessor phases under the canonical roadmap.

## Validation Ownership Contract

```text
T0 MICRO / developer tests      -> executor
T1 TARGETED / IMPACT tests      -> executor
T2 FULL CANONICAL certification -> AIOS certification boundary
T3 RELEASE / SOAK / fault       -> release boundary
```

Exactly one layer owns each tier for a given execution.

An executor must not run T2 when the certification boundary will run the same full suite.

Required telemetry includes:

```text
full_suite_execution_count
expected_full_suite_execution_count
targeted_test_count
targeted_test_time
full_test_time
bridge_time
executor_id
task_id
action
review_round
recovery events
capacity state when observable
```

Unknown provider usage/quota must remain unknown; it must not be inferred from wall time or local test duration.

## Compatibility / Migration

Existing `RUN TASK-N`, `FIX TASK-N`, `STATUS TASK-N` semantics remain valid.

Existing Codex one-shot transport remains available as a compatibility fallback until P2.

Existing Antigravity interactive execution remains available until mapped into the common Executor Session Contract in P2.

P0 changes only validation ownership and telemetry, not executor authority.

## Failure Semantics

If validation ownership cannot be proven unambiguously for a task, fail conservatively to the existing strict path rather than silently skipping certification.

If full-suite execution count exceeds the validation plan's expected count, surface `VALIDATION_DUPLICATION_DETECTED` in telemetry/evidence. This diagnostic must not manufacture PASS.

## Consequences

Positive:
- preserves proven Bridge control-plane safety;
- removes a known fixed-cost delivery tax;
- makes Antigravity/Codex/Claude comparable under one validation contract;
- creates evidence needed for P1/P2 decisions;
- supports faster Python Agent delivery without weakening main certification.

Tradeoffs:
- requires temporary compatibility logic while old tasks still contain explicit full-suite commands;
- initial telemetry adds small local bookkeeping overhead;
- P1 batching and P2 session changes remain intentionally deferred until P0 proves the baseline.

## Completion

ADR-056 is implemented only when the P0 completion contract in the canonical roadmap passes. Creating this ADR does not itself complete P0.
