# AIOS Bridge Lean Execution v1.1 — Implementation Sequence

This companion follows canonical roadmap `.ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.1.md` and ADR-056/ADR-057/ADR-061/ADR-062/ADR-063. It creates no authority beyond those artifacts.

## Current Sequence

```text
P0 / TASK-083 PASS + merged at d55a5b168f6833558c3f9db63f46dd1817392283
        |
        v
P0 FORMAL COMPLETION RECORDED
        |
        v
TASK-085 — SUPERSEDED_NO_IMPLEMENTATION
opaque Codex CLEAN_NO_WORKTREE_DELTA
        |
        v
TASK-086 — PAUSED_DIAGNOSTIC_REQUIRED
second opaque Codex CLEAN_NO_WORKTREE_DELTA
        |
        v
TASK-088 — Codex No-Op Outcome Observability   <-- NOW
execute with Antigravity
        |
        v
independent review + merge
        |
        v
re-author/rebind TASK-086 on exact new main
        |
        v
TASK-086 — P1.0A Transactional RUN/FIX + Evidence Refresh
        |
        v
independent review + merge
        |
        v
TASK-087 — P1.0B Failure Classification + Deterministic Next Action
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

## TASK-088 Diagnostic Gate

Two consecutive Codex bounded RUNs exited zero with no implementation delta even though TASK-086 required baseline-missing work. The canonical WORK artifact was verified to be included in the context pack and passed byte-for-byte to `codex exec -` under `workspace-write` sandbox. The remaining gap is terminal executor-outcome observability.

TASK-088 must add only bounded safe outcome evidence. It must not capture chain-of-thought, reasoning-event content, or raw stdout. Existing clean-noop fail-closed publication semantics remain unchanged.

TASK-088 is intentionally implemented by Antigravity because Codex bounded execution is the component under diagnosis.

## P1.0 Mandatory Gate

P1 capability batching MUST NOT begin until the ordered P1.0 prerequisites prove:

```text
TASK-088:
  opaque Codex no-op becomes bounded/observable

TASK-086:
  RUN TASK-N -> no prior STATUS required
  FIX TASK-N -> no prior STATUS required
  FIX IMPLEMENTATION -> bounded executor path
  FIX EVIDENCE_REFRESH -> no executor; certify + republish

TASK-087:
  clean no-op/timeout -> deterministic classification + one next action
  preserved dirty timeout -> RECOVERY_REQUIRED; no blind restart
```

These are implementation refinements under locked roadmap v1.1. They do not add or rename canonical P1 requirements and do not individually complete P1.

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

Do not open P2 merely because recent control-plane tasks exposed Codex timeout/no-op/self-hosting recovery. First close TASK-088/086/087, finish P1, pilot PRODUCT_DELIVERY_FAST on Python Agent, then measure whether session/context/capacity overhead remains material.

## H-Series Boundary

H5 remains paused/not authorized. Lean Execution work does not change H-Series milestone definitions or automatically resume H-Series progression.