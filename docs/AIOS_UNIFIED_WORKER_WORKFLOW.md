# AIOS Unified Worker Workflow

As of TASK-097 revision 3, the repository-owned Codex and Antigravity worker
surfaces delegate exclusively to the frozen AIOS-renew kernel at commit
`2ee57fd87316fdf8eb52a77777c51dff6d023214`. Legacy AIOS Bridge source remains
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
| **Antigravity** | `/aios-worker RUN TASK-N` | `.agents/workflows/aios-worker.md` | `antigravity` |
| **Codex** | `$aios-worker RUN TASK-N` | `.agents/skills/aios-worker/SKILL.md` | `codex` |

Both surfaces call the same `aios_worker.py` launcher. The selected executor is
the only semantic difference. TASK/RUN/RESULT/EVIDENCE, synchronization,
executor invocation, review validation, and remediation behavior all come from
the same pinned AIOS-renew distribution.

---

## 2. Locked Identity Contract

Each UI surface is permanently bound to a single executor identity. **No cross-surface reroute, inference, or substitution is allowed.**

```text
/aios-worker  -> .agents/workflows/aios-worker.md   -> executor antigravity -> AIOS-renew
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

## 5. PASS Publication, Review, and Merge Boundaries

After a successful RUN/FIX whose canonical AIOS baseline differs from canonical
head, the launcher publishes exactly once with a normal non-force push of `HEAD`
to the attached branch's configured remote+merge ref. The launcher never uses a
local HEAD sampled before the kernel call as the execution baseline.

For PRIMARY RUN it requires exactly one valid `base_sha` and one valid
`head_sha` in one `AIOS RUN PASS` summary. For remediation it requires exactly
one valid `reviewed_sha` and one valid `head_sha` in one
`AIOS REMEDIATION PASS` summary, and `reviewed_sha` must equal the resolved local
canonical lineage. Missing, duplicate, malformed, mixed, or inconsistent fields
fail closed before publication. Publication additionally requires:

1. The worktree is clean.
2. Local HEAD exactly equals the canonical summary `head_sha`.
3. Canonical baseline and `head_sha` differ.
4. The attached branch has a configured remote and `refs/heads/...` merge ref.

AIOS failure causes zero push. Canonical baseline equal to `head_sha` causes zero
push even when PRIMARY synchronization moved local HEAD before the executor ran.
Publication failure is reported separately from AIOS PASS, does not rerun AIOS,
and does not rewrite the canonical RESULT.

### Independent Review Loop

After a worker finishes and the launcher publishes, the operator prompts ChatGPT:

```text
Review TASK-N
```

ChatGPT performs an independent semantic audit and emits `REVIEW-N.md` with either `PASS` or `CHANGES_REQUIRED`.

### Merge Boundary

`MERGE` is never a worker command:

- Worker executors **NEVER** merge code into `main`.
- Workers stop immediately after publication and instruct the Human operator to review the task in ChatGPT (`Review TASK-N in ChatGPT`).

---

## 6. Single-Command Operator Flow

- **Antigravity**: The Human enters `/aios-worker RUN TASK-N`.
- **Codex**: The Human enters `$aios-worker RUN TASK-N`.
- **Completion**: Successful advancing PASS includes guarded publication; no
  routine manual Git push step remains before ChatGPT review.
- **Recovery**: A distinct publication failure preserves the valid AIOS result
  and repository state for explicit Human-directed recovery.

---

## 7. Surface File Format Standards

To ensure unambiguous discovery and reliable tool parsing across all AI environments:

- **Encoding**: UTF-8 strictly without BOM (`\xef\xbb\xbf`).
- **Frontmatter Delimiter**: Frontmatter must begin at byte 0 with `b"---\n"` (LF).
- **Physical Separation**:
  - Antigravity workflow: `.agents/workflows/aios-worker.md`
  - Codex skill: `.agents/skills/aios-worker/SKILL.md`
- **Scope Isolation**: Surface files are dedicated to operator protocol translation and must never duplicate implementation logic.

## 8. Migration Certification Boundary

Repository-owned skill/workflow files may be cached by an already-open operator
session. After the TASK-097 migration commit is present, start a fresh or
explicitly reloaded Codex/Antigravity session before exercising the migrated
surface.

TASK-096 remains pending and must not be executed or treated as completed until
this TASK-097 migration is certified. TASK-097 does not change Product
Intelligence or any TASK-096 product scope.
