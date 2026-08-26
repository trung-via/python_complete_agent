---
name: aios-kernel-worker
description: Operates AIOS Kernel v1 worker surface (RUN, FIX, STATUS, COMPLETE, CANCEL) through Kernel control surface.
---

# AIOS Kernel Worker Skill ($aios-kernel-worker)

Operates the AIOS Bridge Kernel v1 execution protocol.

## Commands

- `$aios-kernel-worker RUN TASK-N`: Authorize and execute RUN for TASK-N.
- `$aios-kernel-worker FIX TASK-N`: Authorize and execute FIX for TASK-N.
- `$aios-kernel-worker STATUS TASK-N`: Query status for TASK-N.
- `$aios-kernel-worker COMPLETE TASK-N`: Complete candidate verification and publication.
- `$aios-kernel-worker CANCEL TASK-N`: Cancel task authorization.

## Worker Rules

1. Selected visible session acts as the implementation executor.
2. Edit ONLY paths listed in `allowed_paths`.
3. DO NOT launch nested model sessions or `codex exec`.
4. DO NOT run canonical T0/T1 test suite manually during development.
5. Execute `python.exe aios_kernel.py complete TASK-N` ONCE to verify and publish.
