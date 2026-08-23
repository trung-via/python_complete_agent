# AIOS Unified Worker Workflow

This document describes the unified AIOS worker control surface defined in ADR-037 and implemented in TASK-048, with UI identity hardening applied in TASK-060.

---

## 1. Single Semantic Protocol

AIOS defines a single unified semantic protocol for Human operators across all supported AI environments:

```text
RUN TASK-N
FIX TASK-N
STATUS TASK-N
```

### UI Surface Parity

Depending on the environment in which the Human operator is working, the protocol is invoked via thin UI adapters that are **physically separate** surface files:

| Environment | Explicit Invocation Command | Surface File | Selected Executor |
|:---|:---|:---|:---|
| **Antigravity** | `/aios-worker RUN TASK-N` | `.agents/workflows/aios-worker.md` | `antigravity` |
| **Codex** | `$aios-worker RUN TASK-N` | `.agents/skills/aios-worker/SKILL.md` | `codex` |

Both UI adapters delegate 100% of authorization, lease management, state transitions, and publication to **AIOS Bridge** via the shared `aios_worker.py` adapter script.

---

## 2. Locked Identity Contract

Each UI surface is permanently bound to a single executor identity. **No cross-surface reroute, inference, or substitution is allowed.**

```text
/aios-worker  -> .agents/workflows/aios-worker.md  -> --adapter antigravity -> executor_id = antigravity
$aios-worker  -> .agents/skills/aios-worker/SKILL.md -> --adapter codex     -> executor_id = codex
```

The two surface files are physically separate to prevent any AI tool from resolving the wrong surface. Antigravity must always select `--adapter antigravity`; Codex must always select `--adapter codex`.

---

## 3. Shared State Architecture

Neither Antigravity nor Codex owns or persists task state locally. All state is strictly centralized:

1. **GitHub `origin/ai-control`**: Canonical tasks, reviews, and architecture decisions.
2. **AIOS Bridge Runtime**: Local filesystem state for authorization events, active executor leases, and workspace verification.
3. **Task Branch**: Local and remote git branches (`ai/task-N`).

### Synchronization Invariants

- Switching between Antigravity and Codex does **not** create a new task state or dual state store.
- Any attempt to run or fix a task while an incompatible lease is held or after authorization has been consumed is rejected fail-closed by Bridge.
- The UI adapter is a thin front end; it cannot manufacture authorization or bypass Bridge verification.

---

## 4. Worker Operations

### RUN TASK-N

- **Purpose**: Authorize and execute a fresh task run.
- **Codex Flow**: Invokes `bridge.py handoff N --action run --executor codex`, then `bridge.py execute N` to launch the automated E2/E4 execution process.
- **Antigravity Flow**: Invokes `bridge.py handoff N --action run --executor antigravity` (handoff only). Execution continues in the interactive Antigravity session; Bridge does **not** launch a separate executor process.
- **Completion**: Once published, the operator returns to ChatGPT for independent review.

### FIX TASK-N

- **Purpose**: Authorize and execute a fix cycle after a review requests changes.
- **Prerequisite**: An authoritative `REVIEW-*.md` with `STATUS: CHANGES_REQUIRED` must be present and verified by Bridge.
- **Flow**: Follows the same pattern as `RUN`, validating review state before execution.

### STATUS TASK-N

- **Purpose**: Synchronize control plane artifacts and view pending work.
- **Behavior**: Runs `bridge.py sync` followed by `bridge.py pending`. Identical behavior on both surfaces.
- **Safety**: `STATUS` is strictly non-authorizing. It never acquires leases, never triggers executor processes, and never modifies task state.

---

## 5. Review & Merge Boundaries

### Independent Review Loop

After a worker finishes execution and publishes to `ai/task-N`, the operator prompts ChatGPT:

```text
Review TASK-N
```

ChatGPT performs an independent semantic audit and emits `REVIEW-N.md` with either `PASS` or `CHANGES_REQUIRED`.

### Merge Boundary

`MERGE` is **never** a worker command and is intentionally omitted from both the skill and the workflow:

- Worker executors **NEVER** merge code into `main`.
- Under ADR-042 standing Human authorization, the ChatGPT review boundary executes the deterministic lean auto-merge transaction immediately after a valid `PASS` audit without requiring a separate second Human merge command.
- Workers stop immediately after publication and instruct the Human operator to review the task in ChatGPT (`Review TASK-N in ChatGPT`).

---

## 6. Elimination of Routine Manual PowerShell Sequences

Prior to TASK-048, operating Codex required manual multi-step PowerShell sequences (`sync -> pending -> approve -> execute -> publish`).

With the unified `aios-worker` control surface:

- **Antigravity Routine Operation**: Human simply enters `/aios-worker RUN TASK-N` in Antigravity.
- **Codex Routine Operation**: Human simply enters `$aios-worker RUN TASK-N` in Codex.
- **PowerShell Role**: Direct PowerShell commands remain available exclusively for system diagnosis, recovery, and offline bootstrapping.

---

## 7. Surface File Format Standards

To ensure unambiguous discovery and reliable tool parsing across all AI environments:

- **Encoding**: UTF-8 strictly without BOM (`\xef\xbb\xbf`).
- **Frontmatter Delimiter**: Frontmatter must begin at byte 0 with `b"---\n"` (LF).
- **Physical Separation**:
  - Antigravity workflow: `.agents/workflows/aios-worker.md`
  - Codex skill: `.agents/skills/aios-worker/SKILL.md`
- **Scope Isolation**: Surface files are dedicated to operator protocol translation and must never duplicate implementation logic.

