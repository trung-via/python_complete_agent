# REVIEW-060 — Unified Worker UI Identity Hardening

STATUS: CHANGES_REQUIRED
APPROVED: NO
READY_FOR_HUMAN_MERGE: NO
MERGE_AUTHORIZED: NO
MERGED_TO_MAIN: NO

## Fresh Re-Review Binding

```text
TASK_ID: TASK-060
BASELINE_MAIN_SHA: 0d7bddac2066ad508bf68fbb4d3bd8b69b18d1b3
PRIOR_REVIEWED_HEAD_SHA: 9e658797c0e874d16ff822afd078d677f28d9e14
TARGET_BRANCH: ai/task-060
TASK_BLOB_SHA: b404be869367ddfd6d8c10cfa36b326c53b19469
BLUEPRINT_BLOB_SHA: bd8859a4fa6a19792945c62809cf82acd9414e31
```

Independent compare at this re-review snapshot:

```text
main -> ai/task-060: ahead 8, behind 0
prior reviewed head 9e658797... -> ai/task-060: ahead 6, behind 0
```

The fresh FIX branch therefore exists and is linearly descended from the previously reviewed head. This review does not authorize merge.

## Re-Review Findings

### B1 — RESOLVED: exact frontmatter bytes / BOM hardening

The prior frontmatter blocker is closed.

Fresh repository bytes for both operator surfaces are BOM-free and begin with exact LF frontmatter:

```text
.agents/workflows/aios-worker.md
base64 prefix: LS0tCg... -> bytes b"---\n"

.agents/skills/aios-worker/SKILL.md
base64 prefix: LS0tCg... -> bytes b"---\n"
```

The FIX also adds raw-byte regression coverage requiring:

```text
not startswith b"\xef\xbb\xbf"
startswith b"---\n"
workflow contains --adapter antigravity
skill contains --adapter codex
```

The identity contract remains semantically correct:

```text
/aios-worker -> Antigravity workflow -> --adapter antigravity
$aios-worker -> Codex skill          -> --adapter codex
```

No further B1 change is required unless a later FIX regresses these bytes.

### B2 — STILL BLOCKING: RESULT-060 has no authoritative test/publication evidence

Fresh `.ai/results/RESULT-060.md` still records:

```text
Files Changed:
- (none before result generation)

Diff Stat:
(empty)

Tests
Command: (not supplied)
Exit code: 0
(no test command supplied)
```

This does not satisfy TASK-060's locked `FULL_REPO_TESTS_PASS` requirement and does not provide review-grade evidence for the fresh FIX implementation. A zero exit code with no command is not an authoritative test proof.

**Required FIX for B2:**

```text
1. Run the focused control-surface suite explicitly.
2. Run the full repository test suite explicitly.
3. Publish RESULT-060 with exact command(s), exit code(s), pass/skip/fail counts,
   and actual implementation changed-file/diff evidence.
4. The fresh RESULT must not say `(not supplied)`, `(none before result generation)`,
   or present an empty diff stat for a branch that contains implementation changes.
```

If the current Antigravity publication path cannot carry explicit test evidence, stop and fix the publication invocation/inputs only through an authorized task scope; do not fabricate RESULT content manually.

### B3 — BLOCKING: `.gitattributes` is outside TASK-060 writable scope

Fresh compare shows a new file:

```text
.gitattributes
```

with content that locks LF for the two operator surface files.

The intent is understandable, but TASK-060's exact writable scope is locked to:

```text
.agents/workflows/aios-worker.md
.agents/skills/aios-worker/SKILL.md
.agents/skills/aios-worker/scripts/aios_worker.py
tests/aios_bridge/test_aios_worker_control_surface.py
docs/AIOS_UNIFIED_WORKER_WORKFLOW.md
```

plus Bridge-generated `.ai/results/RESULT-060.md` as publication output only.

`.gitattributes` is not authorized by the canonical task. Adding it therefore violates the exact scope boundary even though it supports the BOM/LF objective.

**Required FIX for B3:**

```text
1. Remove `.gitattributes` from the TASK-060 branch delta.
2. Keep the two surface files themselves encoded UTF-8 without BOM and LF-frontmatter.
3. Keep the raw-byte regression tests so a future line-ending/BOM regression fails closed.
4. Do not broaden TASK-060 scope to justify `.gitattributes` after the fact.
```

## Semantic Audit — PASS subject to B2/B3

The UI separation itself is now correct:

```text
Antigravity /aios-worker
  -> .agents/workflows/aios-worker.md
  -> shared adapter --adapter antigravity
  -> RUN/FIX handoff only

Codex $aios-worker
  -> .agents/skills/aios-worker/SKILL.md
  -> shared adapter --adapter codex
  -> RUN/FIX handoff + execute

STATUS
  -> non-authorizing on both surfaces
```

The shared adapter remains unchanged in the observed branch delta. No TASK-059 implementation, dispatcher, lease semantic, PID tracking, M11.3B/C, or paid-API change is part of the intended hotfix.

## Fresh Scope Snapshot

Observed `main -> ai/task-060` paths:

```text
.agents/skills/aios-worker/SKILL.md                      authorized
.agents/workflows/aios-worker.md                        authorized
.ai/results/RESULT-060.md                               Bridge publication output
.gitattributes                                          UNAUTHORIZED -> B3
docs/AIOS_UNIFIED_WORKER_WORKFLOW.md                    authorized
tests/aios_bridge/test_aios_worker_control_surface.py   authorized
```

## Required Next Gate

```text
FIX TASK-060
```

The next FIX is narrow:

```text
B1: KEEP RESOLVED
B2: repair real RESULT/test evidence
B3: remove unauthorized .gitattributes delta
```

After a fresh publication:

```text
Review TASK-060
```

Do not merge TASK-060 and do not run TASK-059 until TASK-060 receives a fresh PASS review and explicit Human merge.