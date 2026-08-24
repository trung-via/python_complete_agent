# AIOS Bridge Lean Execution Refactor Roadmap v1.2

ROADMAP_ID: AIOS-BRIDGE-LEAN-EXECUTION
ROADMAP_VERSION: 1.2
STATUS: LOCKED
AUTHORITY: CANONICAL

## Purpose

Minimize Time-to-Trusted-Capability while preserving AIOS Bridge control-plane authority, provenance, roadmap binding, lease safety, publication trust, reviewed-head merge safety, explicit Human authority over executor substitution, and certified delivery.

Version 1.2 is the Human-approved controlled evolution of v1.1 under ADR-064. It preserves P0, P2, and P3 semantics and extends P1 with the Lean Review Pipeline so expensive validation, review, and waiting work is performed only when its evidence is required.

### P0 — Validation Ownership + Delivery Telemetry
CAPABILITY_ID: P0_VALIDATION_OWNERSHIP_TELEMETRY
- P0.R1 — Every validation tier has exactly one owner: T0/T1 executor, T2 certification boundary, T3 release boundary.
- P0.R2 — Executable work uses an explicit bounded validation plan with deterministic ownership and fail-conservative compatibility behavior.
- P0.R3 — Duplicate full-canonical execution is eliminated and actual versus expected full-suite count is machine-observable.
- P0.R4 — Bounded execution telemetry records validation counts and durations plus executor/task/action/review/recovery/capacity facts when observed.
- P0.R5 — Authorization, lease, roadmap, scope, publication, retry/reroute, reviewed-head, and merge authority semantics remain unchanged.

### P1 — Unified Validation Profiles + Capability Batch + Lean Review
CAPABILITY_ID: P1_UNIFIED_VALIDATION_CAPABILITY_BATCH
- P1.R1 — CONTROL_PLANE_STRICT and PRODUCT_DELIVERY_FAST are explicit closed validation profiles with uncertain impact failing conservatively.
- P1.R2 — Capability batches may contain multiple separately authorized tasks without collapsing task authority.
- P1.R3 — Intermediate product work remains on a bounded integration lane and main receives only capability-certified state.
- P1.R4 — Impact testing uses deterministic dependency evidence and falls back to full certification when impact confidence is insufficient.
- P1.R5 — A Python Agent pilot measures Time-to-Trusted-Capability before further platform expansion.
- P1.R6 — Semantic review precedes final T2 certification; semantic acceptance is non-authoritative and final PASS still requires exact-candidate T2 certification plus existing roadmap, reviewed-head, and merge safety.
- P1.R7 — FIX rounds carry forward accepted proofs only while subject and dependency fingerprints remain unchanged; known impact invalidates only affected proof scope and unknown impact expands testing/review fail-conservatively.
- P1.R8 — Review findings use a machine-readable lifecycle and semantic review effort is selected deterministically from bounded risk evidence, with critical changes eligible for an independent second review.
- P1.R9 — Review and certification bind exact candidate identity; superseded work cannot gain authority, and long-running deterministic certification uses a provider-neutral machine job rather than repeated model polling.
- P1.R10 — Review execution uses bounded FIX context packs, deterministic review preflight, compact single-source-of-truth result evidence, delta-plus-impact review, and evidence-driven finding-to-guardrail promotion.

### P2 — Provider-Neutral Executor Session
CAPABILITY_ID: P2_PROVIDER_NEUTRAL_EXECUTOR_SESSION
- P2.R1 — Antigravity, Codex, and future Claude Code map to one executor-session lifecycle with start attach heartbeat work checkpoint complete suspend resume and abort semantics.
- P2.R2 — Safe checkpoints are created at semantic work boundaries without granting new authority.
- P2.R3 — Next-task admission uses measured safe budget, expected task cost, recovery reserve, context/session health, and capacity evidence.
- P2.R4 — Capacity exhaustion is represented as suspension rather than implementation failure when recoverable state is preserved.
- P2.R5 — Resume or cross-executor continuation never creates automatic retry, automatic reroute, or authority escalation.

### P3 — Executor Portability + Adaptive Selection
CAPABILITY_ID: P3_EXECUTOR_PORTABILITY_ADAPTIVE_SELECTION
- P3.R1 — Executor-specific behavior is confined to provider adapters behind one common capability and lifecycle contract.
- P3.R2 — Claude Code integrates through the same session, validation, telemetry, checkpoint, and authority semantics.
- P3.R3 — Executor quality summaries use observed comparable telemetry and remain advisory unless separately authorized.
- P3.R4 — Cross-executor handoff preserves exact task branch checkpoint and provenance and requires explicit Human executor selection.

## Controlled Evolution from v1.1

ADR-064 is the Human-approved change authority for this version.

```text
CHANGE_CLASS: CAPABILITY_EXTENSION
CANONICAL_REQUIREMENT_IDENTITY_CHANGED: YES
APPROVED_CHANGE_ID: ADR-064
PREDECESSOR: AIOS-BRIDGE-LEAN-EXECUTION-v1.1
P0_SEMANTICS_CHANGED: NO
P2_P3_AUTHORIZED: NO
H5_H8_AUTHORIZED: NO
TASK_086_RETROACTIVE_REINTERPRETATION: NO
TASK_087_REBIND_REQUIRED_AFTER_LEAN_REVIEW_IMPLEMENTATION: YES
```

The new P1 requirements are additive refinements to the same P1 capability. They do not declare P1 complete and do not authorize P2, P3, or H-Series work.

## Sequencing

```text
P0
 -> P1.0A transactional worker flow complete through TASK-086
 -> ADR-064 Lean Review Pipeline implementation
 -> rebind and execute reserved TASK-087
 -> remaining P1 capability-batch work
 -> Python Agent fast-lane pilot
 -> P2 only if measured session/context/capacity cost remains material
 -> P3
```

H-Series remains a separate locked roadmap. H5 is not opened by this roadmap.

## North Star

```text
MINIMIZE TIME-TO-TRUSTED-CAPABILITY
subject to authority safety, provenance, bounded risk, and certified delivery.
```

AIOS refinements must justify measurable reduction in delivery time, Human attention, model cost, rework, or recovery cost.
