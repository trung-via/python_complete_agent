# REVIEW-048 — Unified AIOS Worker Control Surface

STATUS: CHANGES_REQUIRED
APPROVED: NO
READY_FOR_HUMAN_MERGE: NO
MERGE_AUTHORIZED: NO
MERGED_TO_MAIN: NO

## Authoritative Anchors

```text
TASK_ID: TASK-048
MILESTONE: Unified AIOS Worker Control Surface
BASELINE_MAIN_SHA: 22a05d1f4880daf3a9f964e0564c658b051039cd
TASK_BRANCH: ai/task-048
REVIEWED_TASK_HEAD_SHA: 7746a8e1fb97bceeaabf25c208c0bba294e3b3e5
TASK_BLOB_SHA: 72e4610ca6d3f72bdf4049903308b476a48a2c9e
ADR_037_BLOB_SHA: 6c30cd6d2b9dea5dd4d20b687353471ba80dae8b
BLUEPRINT_BLOB_SHA: fbd0641b7198a92fc8edd9014469da07414791ac
RESULT_048_BLOB_SHA: 32fc709256bd8ca40d2d0cde0d1d18b80499e03b
SKILL_BLOB_SHA: 221372e912ce315c555fafcd23afce20b24ac9fb
ADAPTER_BLOB_SHA: 3126ff802d27ddecc2c97c41a46584103068d889
TEST_BLOB_SHA: c31409613642bb3548507e040eab421ec8be9d5d
DOC_BLOB_SHA: 6a2fe3b88ea9e2410e82d720f8c898389cbd66ad
```

## Fresh Lineage / Scope Audit

Fresh GitHub comparison against the locked baseline establishes:

```text
STATUS: ahead
AHEAD: 1
BEHIND: 0
MERGE_BASE: 22a05d1f4880daf3a9f964e0564c658b051039cd
TASK_HEAD: 7746a8e1fb97bceeaabf25c208c0bba294e3b3e5
```

Repository delta is exactly:

```text
.agents/skills/aios-worker/SKILL.md
.agents/skills/aios-worker/scripts/aios_worker.py
.ai/results/RESULT-048.md
docs/AIOS_UNIFIED_WORKER_WORKFLOW.md
tests/aios_bridge/test_aios_worker_control_surface.py
```

The four Executor-owned implementation paths are exactly the TASK-048 allowed scope; `.ai/results/RESULT-048.md` is Bridge-generated.

## Test Evidence

Executor targeted suite reported 65 passing tests before publication.

Bridge publication then ran the required full repository suite:

```text
.\venv\Scripts\python.exe -m pytest tests/ -q
1502 passed, 7 skipped, 1533 warnings in 158.31s
EXIT_CODE: 0
```

Full-suite green status does not close the finding below because the defect is in the precision of the control-contract tests themselves.

## Finding F048-001

FINDING_ID: F048-001
SEVERITY: MEDIUM

ROOT_CAUSE:
The TASK-048 test file labels the Codex RUN/FIX subprocess checks as an exact argv contract, but the core assertions verify token presence and selected values (`"handoff" in cmd`, `"48" in cmd`, lookup around `--action` / `--executor`) rather than equality of the entire ordered argv list. The same pattern appears in Antigravity and STATUS assertions. As written, an implementation could append or inject an unauthorized extra argument while these tests still pass.

BROKEN_INVARIANT:
TASK-048 locked exact command composition for the worker adapter. Codex RUN/FIX must invoke only the exact Bridge handoff argv followed by the exact execute argv; Antigravity RUN/FIX must invoke only exact handoff argv; STATUS must invoke only exact sync then pending argv. The test suite must mechanically lock those boundaries rather than merely prove that expected tokens are present.

REQUIRED_BEHAVIOR:
Strengthen `tests/aios_bridge/test_aios_worker_control_surface.py` so the subprocess call list and every `cmd` are compared by full ordered equality against the exact expected argv. Preserve the existing production adapter behavior. Add explicit malformed task-ID padding coverage so whitespace-padded task IDs are mechanically rejected.

FORBIDDEN_IMPLEMENTATIONS:
- Do not modify `.agents/skills/aios-worker/scripts/aios_worker.py` unless a newly strengthened exact test proves the current production behavior itself is wrong.
- Do not modify `.agents/skills/aios-worker/SKILL.md`.
- Do not modify `docs/AIOS_UNIFIED_WORKER_WORKFLOW.md` for this finding.
- Do not modify `bridge.py` or `src/**`.
- Do not weaken ADR-037, the TASK-048 blueprint, Human authority, review/merge boundaries, or no-retry/no-fallback semantics.
- Do not add new executor behavior, M11 behavior, paid API behavior, automatic merge, failover, or H-Series work.

REQUIRED_TESTS:
1. Codex RUN asserts the exact first argv:
   `[sys.executable, str(repo_root / "bridge.py"), "handoff", "48", "--action", "run", "--executor", "codex"]`.
2. Codex RUN asserts the exact second argv:
   `[sys.executable, str(repo_root / "bridge.py"), "execute", "48"]`.
3. Codex FIX locks the same exact lists with `"fix"`.
4. Antigravity RUN/FIX each lock one exact handoff argv and prove there is no second subprocess call.
5. STATUS locks exactly two argv lists: `sync`, then `pending`, with no additional arguments or subprocess calls.
6. All subprocess calls continue to lock `sys.executable`, exact absolute `bridge.py`, `cwd=repo_root`, `shell=False`.
7. Add explicit rejection cases for leading/trailing whitespace padding around canonical task IDs.

ADVERSARIAL_TESTS/CHECKS:
- Exact-argv assertions must fail if any extra token is appended to handoff, execute, sync, or pending.
- Exact-argv assertions must fail if executor/action/task-number order changes.
- `" TASK-48"`, `"TASK-48 "`, and equivalent whitespace-padded forms must be rejected.
- No retry, fallback, direct `publish`, direct `approve`, raw `codex`, or MERGE path may be introduced.

CLOSE_CONDITIONS:
- Only the authorized test file changes, plus Bridge-generated RESULT update during publication.
- Strengthened targeted suite passes.
- Bridge full repository suite passes.
- Fresh GitHub diff remains within authorized FIX scope.
- Independent ChatGPT re-review confirms exact argv equality coverage and no production semantic drift.

ALLOWED_FILES:
```text
tests/aios_bridge/test_aios_worker_control_surface.py
```

FORBIDDEN_SCOPE:
```text
bridge.py
src/**
.agents/skills/aios-worker/SKILL.md
.agents/skills/aios-worker/scripts/aios_worker.py
docs/AIOS_UNIFIED_WORKER_WORKFLOW.md
.ai/tasks/**
.ai/decisions/**
.ai/context/**
.ai/proofs/**
```

## Machine-Readable FIX Context

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/tasks/TASK-048.md","blob_sha":"72e4610ca6d3f72bdf4049903308b476a48a2c9e"},{"path":".ai/decisions/ADR-037-UNIFIED-AIOS-WORKER-CONTROL-SURFACE-CONTRACT-LOCK.md","blob_sha":"6c30cd6d2b9dea5dd4d20b687353471ba80dae8b"},{"path":".ai/context/TASK-048-UNIFIED-AIOS-WORKER-CONTROL-SURFACE-BLUEPRINT.md","blob_sha":"fbd0641b7198a92fc8edd9014469da07414791ac"}]

EXECUTOR_ALLOWED_PATHS_JSON: ["tests/aios_bridge/test_aios_worker_control_surface.py"]

DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]}],"operation":"FIX","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

TASK-048 remains in review. Only Human may authorize FIX. Do not merge.
