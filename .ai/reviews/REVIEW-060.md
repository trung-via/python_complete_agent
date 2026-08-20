# REVIEW-060 — Unified Worker UI Identity Hardening

STATUS: CHANGES_REQUIRED
APPROVED: NO
READY_FOR_HUMAN_MERGE: NO
MERGE_AUTHORIZED: NO
MERGED_TO_MAIN: NO

## Review Binding

```text
TASK_ID: TASK-060
BASELINE_MAIN_SHA: 0d7bddac2066ad508bf68fbb4d3bd8b69b18d1b3
IMPLEMENTATION_COMMIT_SHA: c5995097748498052381bebf3479edcb3c024aa2
REVIEWED_HEAD_SHA: 9e658797c0e874d16ff822afd078d677f28d9e14
TARGET_BRANCH: ai/task-060
TASK_BLOB_SHA: b404be869367ddfd6d8c10cfa36b326c53b19469
BLUEPRINT_BLOB_SHA: bd8859a4fa6a19792945c62809cf82acd9414e31
```

Independent compare from baseline to reviewed head is ahead by 2 commits, behind by 0. The actual repository delta is bounded to the authorized TASK-060 implementation paths plus Bridge-generated `.ai/results/RESULT-060.md`.

## Findings

### B1 — Surface frontmatter is BOM-prefixed instead of beginning with exact `---`

**Severity:** BLOCKING — CONTROL-SURFACE DISCOVERY / IDENTITY

Both newly written operator-surface artifacts are committed with a UTF-8 BOM before the YAML frontmatter delimiter:

```text
.agents/workflows/aios-worker.md
    bytes/text begin: BOM + ---

.agents/skills/aios-worker/SKILL.md
    bytes/text begin: BOM + ---
```

GitHub's implementation diff exposes this as `﻿---` rather than `---` at the beginning of each file.

TASK-060 exists specifically to remove UI discovery ambiguity. Antigravity's documented workspace workflow format uses `.agents/workflows/<workflow>.md` with YAML frontmatter beginning at the start of the file, and the existing Codex skill previously had clean frontmatter. A BOM-dependent parser outcome is therefore not acceptable at this identity boundary.

Current tests read the Markdown with normal UTF-8 and search for substrings such as `name: aios-worker` / `--adapter antigravity`; they do not prove that the first bytes/characters form scanner-compatible frontmatter.

**Required fix:**

```text
1. Rewrite `.agents/workflows/aios-worker.md` as UTF-8 without BOM.
2. Rewrite `.agents/skills/aios-worker/SKILL.md` as UTF-8 without BOM.
3. Add regression tests that read raw bytes and require each surface file to start with b"---\n" or the repository's explicitly locked LF equivalent.
4. Keep the Antigravity workflow bound only to `--adapter antigravity`.
5. Keep the Codex skill bound only to `--adapter codex`.
```

Do not broaden this fix into adapter, Bridge, dispatcher, lease, TASK-059, or paid-API changes.

### B2 — RESULT-060 does not provide authoritative implementation/test publication evidence

**Severity:** BLOCKING — REVIEW EVIDENCE / PUBLICATION TRUST

The implementation commit message states:

```text
Full repo suite: 1865 passed, 9 skipped, 0 failures
```

but the canonical publication artifact `.ai/results/RESULT-060.md` says:

```text
Files Changed: (none before result generation)
Command: (not supplied)
Exit code: 0
(no test command supplied)
```

There are no GitHub workflow runs on the reviewed implementation/publication SHAs that independently supply the missing test evidence.

TASK-060 explicitly requires `FULL_REPO_TESTS_PASS`. A commit-message assertion is not a substitute for the Bridge RESULT evidence expected by this workflow.

**Required fix:**

```text
1. Run the focused TASK-060 control-surface tests after B1 is fixed.
2. Run the full repository test suite.
3. Republish RESULT-060 with the exact test command(s), exit code(s), and actual pass/skip counts.
4. RESULT-060 must accurately record the implementation scope/diff evidence instead of reporting no changed files for the reviewed implementation.
```

No retry/reroute to another executor is authorized. Use the same Human-selected Antigravity path for the FIX.

## Semantic Audit — Otherwise Acceptable

Subject to B1/B2, the implementation direction is consistent with the locked identity contract:

```text
Antigravity /aios-worker
  -> .agents/workflows/aios-worker.md
  -> shared adapter --adapter antigravity
  -> handoff only

Codex $aios-worker
  -> .agents/skills/aios-worker/SKILL.md
  -> shared adapter --adapter codex
  -> handoff + execute
```

The shared adapter implementation remains unchanged, preserving the previously reviewed RUN/FIX/STATUS split. The new workflow text explicitly forbids Codex routing, raw Codex invocation, Bridge execute, retry/reroute, publish/merge authority, and the Codex skill explicitly forbids serving the Antigravity slash surface.

## Scope / Lineage

```text
BASELINE -> ai/task-060: ahead 2, behind 0
REVIEWED_HEAD: 9e658797c0e874d16ff822afd078d677f28d9e14

Observed implementation paths:
- .agents/skills/aios-worker/SKILL.md
- .agents/workflows/aios-worker.md
- docs/AIOS_UNIFIED_WORKER_WORKFLOW.md
- tests/aios_bridge/test_aios_worker_control_surface.py

Shared adapter:
- .agents/skills/aios-worker/scripts/aios_worker.py (unchanged)

Publication:
- .ai/results/RESULT-060.md
```

No TASK-059 implementation, M11.3B contract, dispatcher, lease semantics, process PID tracking, or paid-API change is part of this reviewed delta.

## Required Next Gate

```text
FIX TASK-060
```

After a fresh FIX publication:

```text
Review TASK-060
```

Do not merge TASK-060 and do not re-run TASK-059 until TASK-060 receives a fresh PASS review and Human merge.