# AIOS Bridge Lean Execution v1.1 — Implementation Sequence

This companion follows canonical roadmap `.ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.1.md` and ADR-056/ADR-057/ADR-061. It creates no authority beyond those artifacts.

## Current Sequence

```text
P0 / TASK-083 PASS + merged at d55a5b168f6833558c3f9db63f46dd1817392283
        |
        v
P0 FORMAL COMPLETION RECORDED
        |
        v
TASK-085 — P1.0 Transactional Worker Flow + Fix Recovery
        |
        v
independent review
        |
        +--> if P1.0 fails -> bounded FIX only
        |
        v
P1 validation profiles + capability batch / integration lane
        |
        v
Python Agent PRODUCT_DELIVERY_FAST pilot
        |
        v
measure TTTC + AIOS_OVERHEAD_RATIO + Human Attention
        |
        +--> P2 only if measured session/context/capacity cost remains material
        |
        +--> otherwise return to product delivery
```

## P1.0 Mandatory Gate

P1 capability batching MUST NOT begin until TASK-085 proves the operator-flow contract:

```text
RUN TASK-N -> no prior STATUS required
FIX TASK-N -> no prior STATUS required
FIX IMPLEMENTATION -> bounded executor path
FIX EVIDENCE_REFRESH -> no executor; certify + republish
clean timeout -> explicit clean-timeout next action
preserved dirty timeout -> RECOVERY_REQUIRED; no fresh executor start
normal blocked path -> exactly one deterministic next action
```

P1.0 is an implementation refinement under locked roadmap v1.1. It does not add or rename canonical P1 requirements and does not by itself complete P1.

## P0 Validation Ownership — Locked

```text
T0/T1 -> EXECUTOR
T2 -> CERTIFICATION_BOUNDARY
T3 -> RELEASE_BOUNDARY
```

ADR-060 observability boundary remains authoritative: AIOS-managed T2 evidence is exact; executor ad-hoc/global counts remain UNKNOWN when not observable.

## Operator North Star

Normal workflow after P1.0 must be:

```text
ChatGPT authors TASK
        ↓
Human: $aios-worker RUN TASK-N
        ↓
AIOS handles sync/preflight/authorization/execution/certification/publication
        ↓
ChatGPT review
        ↓
if CHANGES_REQUIRED
Human: $aios-worker FIX TASK-N
        ↓
AIOS handles latest review sync + correct FIX mode + continuation
```

`STATUS` is diagnostic only. Manual `sync -> handoff -> execute -> publish` composition is recovery/debug tooling, not the normal operator workflow.

## P2 Stop Rule

Do not open P2 merely because TASK-083 experienced Codex timeout/no-op/self-hosting recovery. First finish P1.0 and P1, pilot PRODUCT_DELIVERY_FAST on Python Agent, then measure whether session/context/capacity overhead remains material.

## H-Series Boundary

H5 remains paused/not authorized. Lean Execution work does not change H-Series milestone definitions or automatically resume H-Series progression.