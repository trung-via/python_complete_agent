# AIOS Unified Worker Workflow

As of TASK-099 revision 1, the repository-owned Codex and Antigravity worker
surfaces delegate exclusively to the released AIOS-renew v0.1.3 kernel at commit
`6e2fab2cb1fc32e2002d41f3d21e4019a8844e1a`. Legacy AIOS Bridge source remains
archived in this repository, but it is inactive and unreachable from these
RUN/FIX/STATUS surfaces.

---

## 1. Single Semantic Protocol

AIOS defines a single unified semantic protocol for Human operators across all supported AI environments:

```text
RUN TASK-N
FIX TASK-N
STATUS TASK-N
```

### UI Surface Parity

The protocol is invoked through physically separate, thin operator files:

| Environment | Explicit Invocation Command | Surface File | Selected Executor |
|:---|:---|:---|:---|
| **Antigravity** | `/aios-renew-worker RUN TASK-N` | `.agents/workflows/aios-renew-worker.md` | `antigravity` |
| **Codex** | `$aios-worker RUN TASK-N` | `.agents/skills/aios-worker/SKILL.md` | `codex` |

Both surfaces call the same `aios_worker.py` launcher. The selected executor is
the only semantic difference. TASK/RUN/RESULT/EVIDENCE, synchronization,
executor invocation, review validation, and remediation behavior all come from
the same pinned AIOS-renew distribution.

---

## 2. Locked Identity Contract

Each UI surface is permanently bound to a single executor identity. **No cross-surface reroute, inference, or substitution is allowed.**

```text
/aios-renew-worker -> .agents/workflows/aios-renew-worker.md -> executor antigravity -> AIOS-renew
$aios-worker  -> .agents/skills/aios-worker/SKILL.md -> executor codex       -> AIOS-renew
```

The two surface files are physically separate to prevent an operator tool from
selecting the wrong identity. Neither surface may retry with or reroute to the
other executor.

---

## 3. Dedicated Pinned Runtime and Shared State

The launcher does not depend on a global `aios` executable, a preinstalled
`aios_renew` import, a bare `python` command, or a machine-specific source
checkout. Before dispatch, each surface probes the same fixed Python 3.11+ host
order:

- Windows: repository `venv/Scripts/python.exe` when present, `py -3.11`,
  `python3`, `python`.
- POSIX: repository `venv/bin/python` when present, `python3`, `python`.

Each candidate receives only the fixed version probe. The first successful
candidate starts the launcher exactly once; if none qualifies, the surface
reports `BOOTSTRAP_INTERPRETER_UNAVAILABLE` before creating an AIOS RUN. A
repository product virtualenv is permitted only as this bootstrap host. Its
packages are irrelevant and AIOS-renew is never installed into or imported from
it.

On first use, the selected host creates a dedicated runtime below
`<git-dir>/aios/worker-runtime` and installs exactly the one immutable dependency in
`.agents/skills/aios-worker/requirements-aios-renew.txt`.

Every invocation validates installed PEP 610 direct-source metadata against the
authoritative repository and commit. A dedicated `worker-bootstrap.lock`
serializes concurrent first use and is separate from the kernel's
`operator.lock`. Valid runtimes are reused without reinstalling; incomplete,
stale, alternate-source, or unverifiable runtimes are rebuilt fail-closed before
an AIOS RUN can exist.

AIOS-renew owns local RUN, handoff, RESULT, and operator-lock state below the
Git-dir AIOS area. Switching between Codex and Antigravity does not create a
second semantic state store.

---

## 4. Worker Operations

### RUN TASK-N

- **Codex**: Calls AIOS-renew `run` once with the exact TASK ID, explicit Python
  Agent repository root, executor `codex`, and sandbox `danger-full-access`.
- **Antigravity**: Calls the same AIOS-renew `run` once with executor
  `antigravity`; the visible operator session does not implement the task.
- **Authority**: AIOS-renew retains PRIMARY synchronization, task parsing,
  execution, verification evidence, RESULT validation, and PASS authority.
- **Failure**: There is no automatic retry or executor reroute.

### FIX TASK-N

- **Purpose**: Execute one canonical narrow remediation, never rerun the original
  TASK as an inferred fix.
- **Local transport boundary**: REVIEW files live under
  `<git-dir>/aios/reviews`; REMEDIATION files live under
  `<git-dir>/aios/remediations`.
- **Resolution**: The launcher accepts only one canonical filename/content match
  for the requested TASK and current immutable HEAD. DELTA review lineage must
  resolve to one prior REVIEW. Missing or ambiguous lineage fails closed.
- **Authority**: The launcher passes those exact paths to AIOS-renew `remediate`;
  AIOS-renew performs all semantic validation and execution.

### STATUS TASK-N

- **Behavior**: Calls AIOS-renew `task`/`describe_task` semantics for the exact
  stored TASK.
- **Safety**: STATUS may validate/bootstrap the untracked worker runtime, but is
  read-only for the product worktree, branch/ref, TASK, RUN/RESULT state,
  publication, and executor authority. It does not fetch, synchronize, review,
  execute, or push product state.

---

## 5. Review-Before-Publication and Merge Boundaries

Successful RUN/FIX executions leave the resulting implementation commit local
at `HEAD` for independent semantic review and perform zero automatic push.
The launcher reports `REVIEW_CANDIDATE_HEAD` and directs the operator to ChatGPT.

### Independent Review Loop

After canonical AIOS PASS, the operator prompts ChatGPT:

```text
Review TASK-N
```

ChatGPT performs an independent semantic audit and emits a canonical REVIEW
artifact with verdict `PASS` or `CHANGES_REQUIRED`.

### Publication and Merge Boundary

- **Guarded Publication**: Publication occurs only after explicit semantic
  `REVIEW PASS` through an operator-controlled action outside the worker launcher.
- **Merge Boundary**: `MERGE` is never a worker command:
  - Worker executors **NEVER** merge code into `main`.
  - Worker surfaces stop immediately after canonical PASS and instruct the Human
    operator to review the task in ChatGPT (`Review TASK-N in ChatGPT`).

---

## 6. Single-Command Operator Flow

- **Antigravity**: The Human enters `/aios-renew-worker RUN TASK-N`.
- **Codex**: The Human enters `$aios-worker RUN TASK-N`.
- **Sequence**: AIOS PASS -> ChatGPT semantic review -> explicit guarded publication only after REVIEW PASS.

---

## 7. Surface File Format Standards

To ensure unambiguous discovery and reliable tool parsing across all AI environments:

- **Encoding**: UTF-8 strictly without BOM (`\xef\xbb\xbf`).
- **Frontmatter Delimiter**: Frontmatter must begin at byte 0 with `b"---\n"` (LF).
- **Physical Separation**:
  - Active Antigravity workflow: `.agents/workflows/aios-renew-worker.md`
  - Retired Antigravity stub: `.agents/workflows/aios-worker.md`
  - Codex skill: `.agents/skills/aios-worker/SKILL.md`
- **Scope Isolation**: Surface files are dedicated to operator protocol translation and must never duplicate implementation logic.

## 8. Migration Certification Boundary

Repository-owned skill/workflow files may be cached by an already-open operator
session. After changes are present on `main`, start a fresh or
explicitly reloaded Codex/Antigravity session before exercising the migrated
surface.

This is a hard namespace cutover. Antigravity uses `/aios-renew-worker` from now
on; `/aios-worker` is permanently retired and fail-closed. Stale Antigravity
branches or caches that do not expose `/aios-renew-worker` fail closed instead of
falling back to legacy `/aios-worker` semantics.

Both active worker surfaces use exactly AIOS-renew commit
`6e2fab2cb1fc32e2002d41f3d21e4019a8844e1a`.
