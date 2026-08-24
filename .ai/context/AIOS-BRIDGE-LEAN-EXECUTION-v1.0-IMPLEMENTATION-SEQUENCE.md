# AIOS Bridge Lean Execution v1.0 — Implementation Sequence

This artifact is the execution sequence companion to the locked roadmap. It creates no authority beyond the canonical roadmap and ADR-056.

## Immediate Sequence

```text
TASK-082 independent review / canonical closure
        |
        v
TASK-083 — P0 Validation Ownership + Full-Suite Dedup Foundation
        |
        v
P0 verification: prove one T2 owner + full-suite count telemetry
        |
        v
P0 follow-up task only if telemetry contract is incomplete
        |
        v
P0 milestone completion record
        |
        v
P1 — Unified Validation Profiles + Capability Batch
        |
        v
Python Agent PRODUCT_DELIVERY_FAST pilot
        |
        v
Measure TTTC + AIOS_OVERHEAD_RATIO
        |
        +--> if session/context/capacity remains material -> P2
        |
        +--> otherwise continue product delivery before more platform work
```

## P0 Task Decomposition

### TASK-083 — Validation Ownership + Dedup Foundation

Deliver:
- closed validation tiers/owners;
- explicit validation plan;
- one T2 canonical owner;
- Codex duplicate full-suite elimination;
- Antigravity parity;
- full-suite count/time telemetry;
- no authority changes.

### Optional TASK-084 — Telemetry Completion / Compatibility Cleanup

Create only if TASK-083 evidence proves a bounded missing telemetry or migration gap. Do not pre-create automatically.

Possible scope if needed:
- legacy task compatibility cleanup;
- richer bounded timing telemetry;
- validation receipt persistence;
- operator diagnostics.

If TASK-083 fully satisfies P0, skip this task.

## P1 Expected Task Decomposition

Author only after P0 completion.

Likely bounded slices:

```text
P1-A Validation Profiles + Fail-Conservative Impact Contract
P1-B Capability Batch + Certified Integration Lane
P1-C Python Agent Fast-Lane Pilot + TTTC Measurement
```

Do not implement P1 on AIOS/H-Series as a demonstration. The required proof target is a real Python Agent capability.

## P2 Expected Task Decomposition

Author only if P1 telemetry shows session/context/capacity is still a material bottleneck.

Likely bounded slices:

```text
P2-A Provider-Neutral Executor Session Contract
P2-B Safe Checkpoint + Next-Task Admission
P2-C Capacity Suspension/Resume
P2-D Codex Persistent Mapping + Antigravity Attached Mapping
```

Keep existing one-shot Codex path as fallback during migration.

## P3 Expected Task Decomposition

Author only after P2.

```text
P3-A Common Executor Adapter Contract
P3-B Claude Code Adapter
P3-C Comparable Executor Quality/Tendency Telemetry
P3-D Human-Authorized Cross-Executor Continuation Proof
```

## Stop Rules

Stop platform work and return to Python Agent when:

```text
AIOS_OVERHEAD_RATIO <= 20%
AND
full-suite duplication == 0
AND
product fast-lane main certification remains reliable
```

Even before that threshold, do not open a later phase merely because its architecture is attractive. Each phase requires measured payback.

## H-Series Boundary

TASK-082/H4 is separate from this roadmap. H5 is not opened by Lean Execution work. H-Series progression may resume only under its own canonical roadmap authority after Lean Execution priorities and product-delivery economics are satisfied.
