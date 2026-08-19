# AIOS Unified Worker Workflow

This document describes the unified AIOS worker control surface defined in [ADR-037](file:///c:/Users/TRUNG/.gemini/antigravity/scratch/python_complete_agent/.ai/decisions/ADR-037-UNIFIED-AIOS-WORKER-CONTROL-SURFACE-CONTRACT-LOCK.md) and implemented in TASK-048.

---

## 1. Single Semantic Protocol

AIOS defines a single unified semantic protocol for Human operators across all supported AI environments:

```text
RUN TASK-N
FIX TASK-N
STATUS TASK-N
```

### UI Surface Parity

Depending on the environment in which the Human operator is working, the protocol is invoked via thin UI adapters:

| Environment | Explicit Invocation Command | Selected Executor |
|:---|:---|:---|
| **Antigravity** | `/aios-worker RUN TASK-N` | `antigravity` |
| **Codex** | `$aios-worker RUN TASK-N` | `codex` |

Both UI adapters delegate 100% of authorization, lease management, state transitions, and publication to **AIOS Bridge**.

---

## 2. Shared State Architecture

Neither Antigravity nor Codex owns or persists task state locally. All state is strictly centralized:

1. **GitHub `origin/ai-control`**: Canonical tasks, reviews, and architecture decisions.
2. **AIOS Bridge Runtime**: Local filesystem state for authorization events, active executor leases, and workspace verification.
3. **Task Branch**: Local and remote git branches (`ai/task-N`).

### Synchronization Invariants
- Switching between Antigravity and Codex does **not** create a new task state or dual state store.
- Any attempt to run or fix a task while an incompatible lease is held or after authorization has been consumed is rejected fail-closed by Bridge.
- The UI adapter is a thin front end; it cannot manufacture authorization or bypass Bridge verification.

---

## 3. Worker Operations

### RUN TASK-N
- **Purpose**: Authorize and execute a fresh task run.
- **Codex Flow**: Invokes `bridge.py handoff N --action run --executor codex`, which validates the inbound task event and grants an active lease, then invokes `bridge.py execute N` to launch the automated E2/E4 execution process.
- **Antigravity Flow**: Invokes `bridge.py handoff N --action run --executor antigravity`, leaving execution to the interactive Antigravity session.
- **Completion**: Once published, the operator returns to ChatGPT for independent review.

### FIX TASK-N
- **Purpose**: Authorize and execute a fix cycle after a review requests changes.
- **Prerequisite**: An authoritative `REVIEW-*.md` with `STATUS: CHANGES_REQUIRED` must be present and verified by Bridge.
- **Flow**: Follows the same pattern as `RUN`, validating review state before execution.

### STATUS TASK-N
- **Purpose**: Synchronize control plane artifacts and view pending work.
- **Behavior**: Runs `bridge.py sync` followed by `bridge.py pending`.
- **Safety**: `STATUS` is strictly non-authorizing. It never acquires leases, never triggers executor processes, and never modifies task state.

---

## 4. Review & Merge Boundaries

### Independent Review Loop
After a worker finishes execution and publishes to `ai/task-N`, the operator prompts ChatGPT:
```text
Review TASK-N
```
ChatGPT performs an independent semantic audit and emits `REVIEW-N.md` with either `PASS` or `CHANGES_REQUIRED`.

### Merge Boundary
`MERGE` is **never** a worker command and is intentionally omitted from the worker skill:
- Worker skills cannot merge code into `main`.
- Merging is strictly reserved for the Human operator following an explicit `PASS` audit from ChatGPT.

---

## 5. Elimination of Routine Manual PowerShell Sequences

Prior to TASK-048, operating Codex required manual multi-step PowerShell sequences (`sync -> pending -> approve -> execute -> publish`).

With the unified `aios-worker` skill:
- **Routine Operation**: Human simply enters `$aios-worker RUN TASK-N` in Codex.
- **PowerShell Role**: Direct PowerShell commands remain available exclusively for system diagnosis, recovery, and offline bootstrapping.
