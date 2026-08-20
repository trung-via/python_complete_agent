# TASK-060 — Unified Worker UI Identity Hardening

STATUS: READY
CLASS: L2 — CONTROL-SURFACE IDENTITY HOTFIX
MILESTONE: M11 SUPPORTING CONTROL-SURFACE HARDENING
EXECUTOR_MODE: UNIFIED_AIOS_WORKER_DUAL_EXECUTOR

## Baseline

```text
MAIN_SHA: 0d7bddac2066ad508bf68fbb4d3bd8b69b18d1b3
TARGET_BRANCH: ai/task-060
```

## Purpose

Fix the proven operator-surface identity bug where Antigravity `/aios-worker RUN TASK-059` resolved to the Codex-specific skill and selected executor `codex`.

TASK-060 must physically separate Antigravity `/aios-worker` from Codex `$aios-worker` while keeping the shared adapter and Bridge authority model unchanged.

## Authoritative Blueprint

```text
PATH: .ai/context/TASK-060-UNIFIED-WORKER-UI-IDENTITY-HARDENING-BLUEPRINT.md
BLOB_SHA: bd8859a4fa6a19792945c62809cf82acd9414e31
```

## Locked Identity Contract

```text
/aios-worker  -> Antigravity workflow -> --adapter antigravity
$aios-worker  -> Codex skill          -> --adapter codex
```

No cross-surface reroute or inference.

## Exact Writable Scope

EXECUTOR_ALLOWED_PATHS_JSON: [".agents/workflows/aios-worker.md",".agents/skills/aios-worker/SKILL.md",".agents/skills/aios-worker/scripts/aios_worker.py","tests/aios_bridge/test_aios_worker_control_surface.py","docs/AIOS_UNIFIED_WORKER_WORKFLOW.md"]

Bridge-generated `.ai/results/RESULT-060.md` is publication output only.

## Implementation Requirements

- Add `.agents/workflows/aios-worker.md` for Antigravity slash invocation only.
- It must invoke the shared adapter with exact `--adapter antigravity`.
- It must never invoke raw Codex or use `--adapter codex`.
- Antigravity RUN/FIX must remain handoff-only; interactive Antigravity session performs implementation.
- Keep `.agents/skills/aios-worker/SKILL.md` Codex-only and explicitly bound to `$aios-worker`.
- Codex RUN/FIX must preserve handoff + Bridge execute behavior.
- STATUS remains non-authorizing on both surfaces.
- No retry, reroute, merge, direct publish, dispatcher change, or lease semantic change.

## Required Tests

```text
ANTIGRAVITY_WORKFLOW_EXISTS
ANTIGRAVITY_BINDS_ONLY_ADAPTER_ANTIGRAVITY
ANTIGRAVITY_FORBIDS_CODEX_ROUTE
CODEX_SKILL_BINDS_ONLY_ADAPTER_CODEX
CODEX_SKILL_NOT_ANTIGRAVITY_SURFACE
ANTIGRAVITY_RUN_FIX_HANDOFF_ONLY
CODEX_RUN_FIX_HANDOFF_THEN_EXECUTE
STATUS_NON_AUTHORIZING
NO_RETRY_REROUTE_MERGE
FULL_REPO_TESTS_PASS
```

## Incident Recovery Boundary

The abandoned partial TASK-059 worktree delta was preserved externally for forensic purposes and then removed. TASK-060 MUST NOT read, import, copy, or reuse that abandoned implementation.

TASK-059 remains READY on canonical control state but MUST NOT be RUN again until TASK-060 passes independent review and is Human-merged.

## Explicit Out of Scope

```text
TASK-059 IMPLEMENTATION: NO
M11.3B CONTRACT CHANGE: NO
M11.3C: NO
PROCESS PID TRACKING: NO
LEASE RELEASE CHANGE: NO
PAID API: NO
```

## Executor Dispatch Policy

Human selects exactly one executor. For this hotfix, use Antigravity after the local workspace has been switched back to clean `main`.

No silent reroute or second executor.

## Completion

After Bridge publication:

```text
STOP
NEXT: Review TASK-060
```
