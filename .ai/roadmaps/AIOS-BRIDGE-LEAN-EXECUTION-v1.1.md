# AIOS Bridge Lean Execution Refactor Roadmap v1.1

ROADMAP_ID: AIOS-BRIDGE-LEAN-EXECUTION
ROADMAP_VERSION: 1.1
STATUS: LOCKED
AUTHORITY: CANONICAL

## Purpose

Minimize Time-to-Trusted-Capability while preserving AIOS Bridge control-plane authority, provenance, roadmap binding, lease safety, publication trust, reviewed-head merge safety, and explicit Human authority over executor substitution.

The v1.1 artifact is a canonical-parser-compatible normalization of the Human-approved v1.0 roadmap. Capability semantics and P0 -> P3 sequencing are unchanged.

### P0 — Validation Ownership + Delivery Telemetry
CAPABILITY_ID: P0_VALIDATION_OWNERSHIP_TELEMETRY
- P0.R1 — Every validation tier has exactly one owner: T0/T1 executor, T2 certification boundary, T3 release boundary.
- P0.R2 — Executable work uses an explicit bounded validation plan with deterministic ownership and fail-conservative compatibility behavior.
- P0.R3 — Duplicate full-canonical execution is eliminated and actual versus expected full-suite count is machine-observable.
- P0.R4 — Bounded execution telemetry records validation counts and durations plus executor/task/action/review/recovery/capacity facts when observed.
- P0.R5 — Authorization, lease, roadmap, scope, publication, retry/reroute, reviewed-head, and merge authority semantics remain unchanged.

### P1 — Unified Validation Profiles + Capability Batch
CAPABILITY_ID: P1_UNIFIED_VALIDATION_CAPABILITY_BATCH
- P1.R1 — CONTROL_PLANE_STRICT and PRODUCT_DELIVERY_FAST are explicit closed validation profiles with uncertain impact failing conservatively.
- P1.R2 — Capability batches may contain multiple separately authorized tasks without collapsing task authority.
- P1.R3 — Intermediate product work remains on a bounded integration lane and main receives only capability-certified state.
- P1.R4 — Impact testing uses deterministic dependency evidence and falls back to full certification when impact confidence is insufficient.
- P1.R5 — A Python Agent pilot measures Time-to-Trusted-Capability before further platform expansion.

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

## Sequencing

```text
P0 -> P1 -> Python Agent fast-lane pilot -> P2 only if measured session/context/capacity cost remains material -> P3
```

H-Series remains a separate locked roadmap. H5 is not opened by this roadmap.

## North Star

```text
MINIMIZE TIME-TO-TRUSTED-CAPABILITY
subject to authority safety, provenance, bounded risk, and certified delivery.
```

AIOS refinements must justify measurable reduction in delivery time, Human attention, model cost, rework, or recovery cost.
