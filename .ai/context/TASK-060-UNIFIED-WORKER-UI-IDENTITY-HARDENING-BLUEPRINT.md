# TASK-060 — Unified Worker UI Identity Hardening Blueprint

STATUS: LOCKED_FOR_IMPLEMENTATION
CLASS: L2 — CONTROL-SURFACE IDENTITY HOTFIX
BASELINE_MAIN_SHA: 0d7bddac2066ad508bf68fbb4d3bd8b69b18d1b3
TARGET_BRANCH: ai/task-060

## Incident

Human invoked `/aios-worker RUN TASK-059` from Antigravity, but the visible UI selected `Executor: codex` and launched the Codex path. The Bridge did not silently reroute; the wrong executor identity was supplied by the UI/operator layer.

Observed consequences were contained: no remote `ai/task-059` publication, no active lease remained after recovery, and abandoned local partial delta was preserved externally then removed.

## Root Cause

The repository exposes `.agents/skills/aios-worker/SKILL.md` with Codex-specific instructions and a hard-coded `--adapter codex`. Antigravity also discovers workspace skills under `.agents/skills/`, so `/aios-worker` can resolve to the Codex-specific skill.

Official Antigravity workspace slash workflows are registered under `.agents/workflows/<name>.md`; use that mechanism to give Antigravity a physically separate `/aios-worker` surface.

## Locked Identity Contract

```text
Antigravity `/aios-worker ...`
  -> `.agents/workflows/aios-worker.md`
  -> shared adapter with `--adapter antigravity`
  -> Bridge handoff only
  -> executor_id = antigravity

Codex `$aios-worker ...`
  -> `.agents/skills/aios-worker/SKILL.md`
  -> shared adapter with `--adapter codex`
  -> Bridge handoff + execute
  -> executor_id = codex
```

Cross-surface identity confusion is forbidden. Neither UI may infer, reroute, or substitute the other executor.

## Required Implementation

1. Create `.agents/workflows/aios-worker.md` as the Antigravity slash workflow.
2. The Antigravity workflow must parse only `RUN TASK-N`, `FIX TASK-N`, `STATUS TASK-N` and invoke the checked-in shared adapter with exact `--adapter antigravity`.
3. The workflow must explicitly forbid `--adapter codex`, raw `codex`, `bridge.py execute`, direct publish/merge, retry, or reroute.
4. Keep `.agents/skills/aios-worker/SKILL.md` Codex-only; strengthen wording so it is explicitly the `$aios-worker` Codex surface and must never serve Antigravity `/aios-worker`.
5. Shared `aios_worker.py` remains the single semantic adapter implementation and must preserve current split:
   - codex RUN/FIX = handoff + execute;
   - antigravity RUN/FIX = handoff only;
   - STATUS = sync + pending only.
6. Update workflow documentation and tests to prove surface parity plus identity separation.

## Required Tests

At minimum:

```text
ANTIGRAVITY_WORKFLOW_EXISTS
ANTIGRAVITY_WORKFLOW_BINDS_ADAPTER_ANTIGRAVITY
ANTIGRAVITY_WORKFLOW_FORBIDS_ADAPTER_CODEX
ANTIGRAVITY_WORKFLOW_RUN_FIX_DO_NOT_REQUIRE_BRIDGE_EXECUTE
CODEX_SKILL_BINDS_ADAPTER_CODEX
CODEX_SKILL_EXPLICITLY_NOT_ANTIGRAVITY_SURFACE
SHARED_ADAPTER_ANTIGRAVITY_HANDOFF_ONLY
SHARED_ADAPTER_CODEX_HANDOFF_THEN_EXECUTE
STATUS_NON_AUTHORIZING_BOTH_SURFACES
NO_RETRY_OR_REROUTE
NO_MERGE_AUTHORITY
FULL_REPO_TESTS_PASS
```

## Exact Writable Scope

```text
.agents/workflows/aios-worker.md
.agents/skills/aios-worker/SKILL.md
.agents/skills/aios-worker/scripts/aios_worker.py
tests/aios_bridge/test_aios_worker_control_surface.py
docs/AIOS_UNIFIED_WORKER_WORKFLOW.md
```

Bridge may separately publish `.ai/results/RESULT-060.md`.

## Read-Only Anchors

```text
.agents/skills/aios-worker/SKILL.md blob 221372e912ce315c555fafcd23afce20b24ac9fb
bridge.py
.ai/decisions/ADR-037-UNIFIED-AIOS-WORKER-CONTROL-SURFACE-CONTRACT-LOCK.md
.ai/tasks/TASK-059.md
```

## Explicit Out of Scope

```text
TASK-059 IMPLEMENTATION: NO
M11.3B CONTRACT CHANGE: NO
M11.3C: NO
CODEX PROCESS PID TRACKING: DEFERRED SEPARATE HARDENING
LEASE SEMANTICS CHANGE: NO
DISPATCHER CHANGE: NO
PAID API: NO
```

## Recovery Policy

The abandoned TASK-059 local partial implementation is forensic-only and MUST NOT be imported, copied, or reused by TASK-060.

## Completion

After publication:

```text
STOP
NEXT: Review TASK-060
```

Only after TASK-060 PASS + Human merge may TASK-059 be run again from Antigravity.