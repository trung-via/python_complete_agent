# AIOS Bridge Lean Execution Refactor Roadmap v1.0

ROADMAP_ID: AIOS-BRIDGE-LEAN-EXECUTION
ROADMAP_VERSION: 1.0
STATUS: LOCKED
AUTHORITY: HUMAN_APPROVED
PURPOSE: Minimize Time-to-Trusted-Capability while preserving AIOS Bridge control-plane authority, provenance, roadmap binding, lease safety, publication trust, and merge safety.

## North Star

AIOS optimizes for Time-to-Trusted-Capability (TTTC), not minimum token use or maximum governance operations per task.

Primary invariant:

```text
AIOS MAY NOT DELAY PRODUCT DELIVERY WITHOUT MEASURABLE PAYBACK.
```

Supporting metric:

```text
AIOS_OVERHEAD_RATIO = coordination + verification + review overhead / total capability delivery time
```

Operational targets:

```text
<= 20%  HEALTHY
20-30%  WATCH
> 30%   OPTIMIZATION_REQUIRED
```

These thresholds are internal operational targets, not external industry benchmarks.

## Scope Boundary

This roadmap is a controlled evolution of the AIOS Bridge execution/validation plane. It does NOT replace or rewrite the proven Bridge control plane.

### Preserve / Do Not Rewrite

```text
authorization model
executor lease semantics
task/review binding
canonical roadmap binding
scope enforcement
provenance
publication trust
reviewed-head merge safety
recovery/handoff authority
no-auto-retry / no-auto-reroute default semantics
```

### Refactor / Extract

```text
validation ownership
executor execution lifecycle
validation profiles
capability batching
execution telemetry
capacity/quota suspension
checkpoint/resume
provider-neutral executor adapters
```

## Provider-Neutral Execution Principle

Antigravity, Codex, and future Claude Code MUST share one semantic execution lifecycle and one validation policy. Executor-specific differences belong only in transport/session adapters.

```text
AIOS Bridge authority
        |
Execution Controller
        |
Executor Session Contract
   |        |        |
Antigravity Codex  Claude
        |
Validation Engine
        |
Certification Gate
        |
Bridge Publish / Merge
```

The UI protocol remains:

```text
RUN TASK-N
FIX TASK-N
STATUS TASK-N
```

Task authority remains separate from execution-session and validation boundaries.

---

# P0 — Validation Ownership + Delivery Telemetry

STATUS: OPEN
PRIORITY: IMMEDIATE
GOAL: Remove duplicate test work, make validation ownership explicit, and measure real delivery overhead before further optimization.

## P0.R1 Single Test Owner

Every validation tier has exactly one owner.

```text
T0 MICRO / developer tests      -> executor
T1 TARGETED / IMPACT tests      -> executor
T2 FULL CANONICAL certification -> AIOS certification boundary
T3 RELEASE / SOAK / fault       -> release boundary
```

An executor MUST NOT run T2 full canonical tests when the certification boundary will run the same suite afterward.

## P0.R2 Explicit Validation Plan

Executable tasks bind a machine-readable validation plan instead of embedding redundant free-form full-suite instructions.

Minimum concepts:

```text
VALIDATION_PROFILE
EXECUTOR_TESTS
CERTIFICATION_TESTS
DIFF_CHECK_REQUIRED
```

Control-plane critical work may use STRICT_TASK profile. Product work may later use PRODUCT_DELIVERY_FAST after P1.

## P0.R3 Full-Suite Deduplication

Codex `bridge execute` MUST NOT hard-code a second full-repository suite if certification already owns T2.

Antigravity publication MUST use the same validation ownership model. The system must prove full-suite execution count rather than infer it from RESULT prose.

Required invariant:

```text
FULL_SUITE_EXECUTION_COUNT == EXPECTED_FULL_SUITE_EXECUTION_COUNT
```

Unexpected duplication fails validation telemetry and is surfaced explicitly.

## P0.R4 Execution Telemetry

Record per task/execution:

```text
executor_id
task_id
action
session_id / invocation_id
start/end wall time
executor active time when observable
shell/tool time
targeted test time
full canonical test time
bridge time
full_suite_execution_count
targeted_test_count
files changed
line churn
review round
recovery events
capacity state before/after
provider usage/quota when exposed
context/session telemetry when exposed
```

Do not fabricate provider token/quota data when unavailable.

## P0.R5 No Governance Weakening

P0 changes validation ownership only. It MUST NOT weaken authorization, lease, roadmap, scope, publication, reviewed-head, or merge safety.

## P0 Completion Contract

P0 is complete only when all supported executors use the same validation ownership semantics and test duplication is machine-observable.

Required proof:

```text
ANTIGRAVITY_VALIDATION_PARITY: PASS
CODEX_VALIDATION_PARITY: PASS
CLAUDE_CONTRACT_COMPATIBLE: PASS
FULL_SUITE_DUPLICATION: ELIMINATED
FULL_SUITE_COUNT_TELEMETRY: PASS
CONTROL_PLANE_AUTHORITY_UNCHANGED: PASS
```

---

# P1 — Unified Validation Profiles + Capability Batch

STATUS: LOCKED_PENDING_P0
GOAL: Move expensive full certification to the correct trust boundary while keeping main certified.

## P1.R1 Two Validation Profiles

### CONTROL_PLANE_STRICT

For Bridge, authorization, lease, roadmap, merge, paid-provider, executor handoff, and other high-blast-radius control-plane changes.

```text
TASK
 -> T0/T1
 -> T2 FULL
 -> independent review
```

### PRODUCT_DELIVERY_FAST

For Python Agent, Product Intelligence, Commerce AI, media/game/product capabilities, and other product-delivery work where bounded impact analysis is available.

```text
TASK A -> T0/T1
TASK B -> T0/T1
TASK C -> T0/T1
          |
CAPABILITY CERTIFICATION BOUNDARY
          |
        T2 FULL once
          |
      capability review
```

Uncertain impact MUST fail conservatively to strict/full certification.

## P1.R2 Capability Batch

A capability batch is an execution/test/review unit containing multiple separately authorized tasks.

Invariant:

```text
TASK = authority unit
CAPABILITY_BATCH = execution / certification unit
```

A batch MUST NOT collapse task authority or allow one task to silently redefine another milestone/capability.

Default initial batch guardrail:

```text
L0/L1: up to 3-5 tasks
L2: up to 3 tasks
L3: up to 1-2 tasks
```

These are secondary guardrails only. Admission policy and telemetry may stop earlier.

## P1.R3 Certified Integration Lane

Intermediate product tasks remain on a bounded integration/capability lane. Main receives the batch only after the capability certification gate and independent review pass.

## P1.R4 Impact Testing

Use dependency/structural evidence where available to select T1 impact tests. If impact confidence is insufficient, run T2 full suite fail-conservatively.

## P1 Completion Contract

```text
STRICT_PROFILE: PASS
PRODUCT_FAST_PROFILE: PASS
CAPABILITY_BATCH_AUTHORITY_ISOLATION: PASS
CERTIFIED_MAIN_PRESERVED: PASS
FULL_SUITE_PER_PRODUCT_BATCH: ONE
UNCERTAIN_IMPACT_FALLBACK_STRICT: PASS
PYTHON_AGENT_PILOT_TTTC_MEASURED: YES
```

---

# P2 — Provider-Neutral Executor Session

STATUS: LOCKED_PENDING_P1
GOAL: Give Antigravity, Codex, and future Claude Code one lifecycle for long-running work, checkpointing, admission, and capacity suspension.

## P2.R1 Executor Session Contract

Common lifecycle:

```text
START
ATTACH
HEARTBEAT
WORK
CHECKPOINT
TASK_COMPLETE
NEXT_TASK_ADMISSION
SUSPEND
RESUME
COMPLETE
ABORT
```

Provider-specific implementations map to this lifecycle.

```text
Antigravity -> INTERACTIVE_ATTACHED
Codex       -> MANAGED_PERSISTENT when supported, one-shot fallback retained
Claude Code -> MANAGED_PERSISTENT when integrated
```

## P2.R2 Safe Checkpoints

Checkpoint at semantic boundaries:

```text
plan complete
significant edit batch complete
test boundary
before expensive operation
before next task
capacity AVAILABLE -> LIMITED transition when observable
```

## P2.R3 Next-Task Admission

Primary rule:

```text
Remaining Safe Budget > P90(Expected Next Task Cost) + Recovery Reserve
```

Use measured historical distributions when available. Unknown capacity fails conservatively for large tasks.

## P2.R4 Capacity Suspension

Quota/capacity exhaustion is a capacity event, not an implementation failure.

Desired semantics:

```text
SUSPENDED_CAPACITY
```

A suspended task preserves exact workspace/provenance/checkpoint state and may resume with the same executor after capacity returns, or be handed off only after explicit Human selection and exact checkpoint verification.

No automatic retry or automatic reroute.

## P2 Completion Contract

```text
COMMON_SESSION_LIFECYCLE: PASS
ANTIGRAVITY_MAPPING: PASS
CODEX_MAPPING: PASS
CHECKPOINT_RESUME: PASS
NEXT_TASK_ADMISSION: PASS
CAPACITY_SUSPENSION: PASS
NO_AUTO_REROUTE: PASS
NO_AUTHORITY_ESCALATION: PASS
```

---

# P3 — Executor Portability + Adaptive Selection

STATUS: LOCKED_PENDING_P2
GOAL: Make executors interchangeable runtimes behind the same AIOS execution engine and enable evidence-based recommendations without transferring Human authority.

## P3.R1 Provider Adapter Boundary

Executor-specific code is confined to adapters exposing common capabilities and lifecycle operations.

Common capability descriptor includes concepts equivalent to:

```text
repository_read
filesystem_write
shell
test_execution
persistent_session
checkpoint_resume
context_capacity
capacity_state
usage_reporting
```

## P3.R2 Claude Code Adapter

Add Claude Code through the same session/validation/telemetry contract. Do not create a Claude-specific execution workflow that bypasses common semantics.

## P3.R3 Executor Quality Model

Use observed telemetry to summarize executor tendencies by task class/capability, e.g. median/P90 TTTC, first-pass rate, recovery incidence, quota/capacity behavior, and review rounds.

The quality model is advisory unless a separate Human-approved authority change is made.

## P3.R4 Human-Authorized Handoff

Cross-executor continuation preserves exact task/branch/checkpoint/provenance and requires explicit Human executor selection. No silent model substitution.

## P3 Completion Contract

```text
COMMON_ADAPTER_CONTRACT: PASS
ANTIGRAVITY_ADAPTER: PASS
CODEX_ADAPTER: PASS
CLAUDE_CODE_ADAPTER: PASS
TELEMETRY_COMPARABLE: PASS
HUMAN_AUTHORIZED_HANDOFF: PASS
NO_PROVIDER_LOCK_IN: PASS
```

---

# Sequencing / Stop Rules

Canonical order:

```text
P0 -> P1 -> Python Agent fast-lane pilot -> P2 if telemetry proves session/context/capacity remains material -> P3
```

Do not build P2/P3 infrastructure merely because it is architecturally attractive. Advancement requires measurable TTTC or reliability payoff.

H-Series may continue only when separately authorized; this roadmap does not alter the locked H-Series milestone definitions. H5 should not be opened as a consequence of this roadmap.

# Controlled Evolution

Changes inside a phase that preserve its capability boundary are IMPLEMENTATION_REFINEMENT.

Any new capability, changed trust boundary, changed Human/executor authority, changed automatic reroute/retry semantics, or change to canonical sequencing requires Human-approved roadmap amendment and, where architectural, an ADR/version bump.

# Final Success Definition

The refactor succeeds when:

```text
one execution model serves Antigravity/Codex/Claude
full canonical tests run only at intentional certification boundaries
product capabilities can batch bounded tasks without weakening authority
main remains certified
capacity loss preserves useful work
AIOS overhead is measured and driven downward
Python Agent delivery becomes materially faster
```
