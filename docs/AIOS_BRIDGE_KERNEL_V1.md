# AIOS Bridge Kernel v1 Specification (ADR-068 / TASK-098)

## 1. Overview

AIOS Bridge Kernel v1 introduces a clean, deterministic worker execution lifecycle beside the legacy Bridge:

```text
AUTHORIZE -> EXECUTE -> VERIFY -> PUBLISH
```

Kernel v1 replaces model-driven polling, nested model launches, and duplicate test executions with process-level synchronous waiting and exact machine-derived validation boundaries.

## 2. Canonical Ownership Matrix

| Stage | Owner | Contract |
|---|---|---|
| AUTHORIZE | Kernel | Human-selected executor (`codex` / `antigravity`), exact TASK/REVIEW, exact base/main/head, branch, allowed paths, minimal active authorization record |
| EXECUTE | Visible session | Read bounded compact context, edit only authorized paths; NEVER launch nested model; NEVER merge; NEVER run canonical suite manually |
| VERIFY | Kernel | Run canonical `t0`/`t1` suite captured at AUTHORIZE exactly once after DONE; synchronous foreground process waiting |
| PUBLISH | Kernel | Revalidate exact authorization/scope/trust/head, emit `RESULT-N.md`, commit once, push once, post-fetch remote identity check |

## 3. CLI Commands

```powershell
# Check status of TASK-N
python.exe aios_kernel.py status TASK-098

# Authorize execution for TASK-N
python.exe aios_kernel.py authorize TASK-098 --action run --executor antigravity

# Emit compact context
python.exe aios_kernel.py context TASK-098

# Complete candidate (VERIFY + PUBLISH)
python.exe aios_kernel.py complete TASK-098

# Cancel task authorization
python.exe aios_kernel.py cancel TASK-098
```

## 4. Safety Locks & Constraints

1. **Exact Machine Scope**: `allowed_paths` is derived ONLY from control snapshot markers (`EXECUTOR_ALLOWED_PATHS_JSON:`). No fail-open fallback.
2. **Deterministic VERIFY**: Canonical `t0` and `t1` verify commands (`KERNEL_VERIFY_COMMAND_JSON:`) run exactly once at `complete`.
3. **Synchronous Foreground Wait**: `subprocess.run` waits for completion without timer polling loops.
4. **Fail-Closed Publication Trust**: Git administration and remote configuration drift fail closed immediately with 0 commits and 0 pushes.
