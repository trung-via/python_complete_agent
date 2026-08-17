# TASK-033 — Codex Primary Executor Operationalization & Windows Runbook

## Work Class

`L1 — OPERATIONALIZATION / EXECUTOR PORTABILITY / DOCUMENTATION-PROOF`

This is a deliberately small post-M8 task.

Primary Brain owns:
- task contract;
- review;
- PASS / CHANGES_REQUIRED decision.

Active Executor owns:
- repository inspection;
- bounded documentation implementation;
- tests/evidence;
- RESULT publication only through AIOS Bridge.

Human remains sole authority for:
- RUN;
- FIX;
- MERGE;
- explicit Executor selection.

---

# Baseline

Canonical `main` at task authoring:

```text
445198fd7bd5342c2d83b12d32794b5925a550ae
```

TASK-032 / M8 is final-review PASS and merged to `main`.

Existing executor architecture already supports explicit Executor selection. This task MUST NOT redesign executor routing, lease semantics, failover semantics, or Continuity Core.

---

# Objective

Prove one ordinary bounded task can be executed with:

```text
ChatGPT Primary Brain
        ↓
AIOS Bridge authority
        ↓
Human explicitly selects codex
        ↓
Codex CLI executes bounded work
        ↓
AIOS Bridge validates/tests/publishes
        ↓
GitHub RESULT records executor_id = codex
        ↓
ChatGPT independent review
```

The purpose is operational, not architectural:

```text
Antigravity MUST NOT be required on the critical path.
AIOS Bridge remains the authorization / lease / publication authority.
Codex is only the selected Executor.
```

---

# Locked Contracts

## C1 — Explicit Human Executor selection

TASK-033 SHALL be activated with:

```text
executor_id = codex
```

Selection MUST come from an explicit Human approval/handoff action.

Forbidden:
- automatic executor routing;
- Codex self-selecting itself;
- changing the repository default executor merely to make this task pass.

---

## C2 — Fresh ordinary RUN, not failover

TASK-033 is a new ordinary task.

Expected publication semantics:

```text
ACTION: RUN
EXECUTOR_ID: codex
EXECUTOR_FAILOVER: NO
```

Do not manufacture or reuse M6/M8 failover evidence.

---

## C3 — Bridge remains the authority

Codex MUST NOT directly publish the task.

Required authority split:

```text
Human            -> approves RUN / FIX / MERGE
AIOS Bridge       -> authorization, lease, test gate, RESULT, commit, push
Codex             -> inspect, edit allowed files, run bounded local checks
Primary Brain     -> independent review
```

Codex MUST NOT manually:
- `git commit`;
- `git push`;
- forge RESULT proof/status fields;
- modify runtime authorization/lease files.

---

## C4 — Codex must consume Bridge context first

Before implementation, Codex SHALL run the repository-local Bridge context command for TASK-033 using the repository virtual environment interpreter.

Preferred Windows command:

```powershell
.\venv\Scripts\python.exe .\bridge.py context 33
```

Do not rely on a global `python` command being present in the Codex shell PATH.

The Executor must treat returned TASK / authorization / branch / lease context as authoritative.

---

## C5 — Required implementation artifact

Create exactly one operational runbook:

```text
docs/AIOS_CODEX_EXECUTOR_WINDOWS.md
```

The runbook MUST document the normal Windows workflow for using Codex as an AIOS Bridge Executor.

It MUST include at minimum:

1. prerequisites:
   - repository cloned;
   - Codex CLI installed and authenticated;
   - repository virtual environment exists;
2. why `AIOS Bridge` remains authority and Codex is only Executor;
3. exact fresh-task workflow:
   - `bridge.py sync`;
   - `bridge.py pending`;
   - Human `approve ... --executor codex`;
   - `bridge.py context <id>`;
   - launch `codex`;
   - bounded implementation;
   - Bridge `publish --action RUN`;
   - Primary Brain review;
4. exact review-fix workflow using `--action FIX`;
5. Windows interpreter guidance using:

```text
.\venv\Scripts\python.exe
```

rather than assuming global `python` is available inside Codex;
6. explicit prohibition on Codex manually committing/pushing when Bridge owns publication;
7. recovery guidance for:
   - no pending TASK/REVIEW;
   - consumed authorization;
   - dirty worktree;
   - missing interpreter / PATH mismatch;
8. quota/provider independence note:
   - exhaustion of one Executor provider must not redefine Bridge authority;
   - Human may select another already-supported Executor on a future authorized boundary;
9. a compact copy/paste operator checklist.

The runbook MUST describe current behavior truthfully. Do not claim automation that is not present.

---

## C6 — No control-plane redesign

Semantic changes are FORBIDDEN in:

```text
bridge.py
src/aios_bridge/continuity/*
src/aios_bridge/runtime_lease.py
```

No changes to:
- M5 lease semantics;
- M6 stable-boundary failover;
- M7 executor portability contracts;
- M8 multi-agent continuity contracts;
- executor allowlist/routing behavior.

This task proves existing portability through normal use; it does not extend the architecture.

---

## C7 — Scope isolation

Expected implementation change before RESULT generation:

```text
docs/AIOS_CODEX_EXECUTOR_WINDOWS.md
```

No unrelated product/source/scraper code changes.

If the Executor determines a code change is required to make Codex function, it MUST stop and report the blocker instead of silently broadening scope.

---

## C8 — Test / validation evidence

Before publication:

1. run a documentation/basic repository integrity check such as:

```powershell
git diff --check
```

2. run the Bridge test suite:

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_bridge.py -q
```

3. run the full repository suite through the Bridge publish test gate:

```powershell
.\venv\Scripts\python.exe -m pytest tests/ -q
```

Do not hard-code expected test counts in implementation logic or documentation. RESULT evidence must be execution-derived.

---

## C9 — Acceptance evidence in RESULT-033

Bridge-published RESULT-033 MUST truthfully show at minimum:

```text
TASK_ID: TASK-033
ACTION: RUN
EXECUTOR_ID: codex
EXECUTOR_FAILOVER: NO
```

And execution evidence must show:
- tests exit code 0;
- no regressions observed;
- only allowed implementation scope before RESULT generation.

The RESULT is evidence generated by Bridge, not a file Codex may manually author to claim success.

---

## C10 — Independent review

Primary Brain SHALL independently verify after publication:

```text
Human selected codex
Bridge authorization bound executor_id=codex
Codex implementation stayed in allowed scope
runbook is operationally correct
Bridge produced RESULT-033
RESULT records ACTION=RUN
RESULT records EXECUTOR_ID=codex
RESULT records EXECUTOR_FAILOVER=NO
Bridge/full tests are green
no control-plane semantics changed
```

Only Primary Brain may issue final PASS / CHANGES_REQUIRED.

---

# Allowed Files

Implementation:

```text
docs/AIOS_CODEX_EXECUTOR_WINDOWS.md
```

Bridge-generated publication artifact:

```text
.ai/results/RESULT-033.md
```

No other repository changes are expected.

---

# Forbidden Scope

```text
bridge.py
src/aios_bridge/continuity/*
src/aios_bridge/runtime_lease.py
scraper/product-source implementation
new executor routing
new failover behavior
new Brain behavior
M9+ architecture work
```

---

# Executor Instructions

Recommended Human activation:

```powershell
.\venv\Scripts\python.exe .\bridge.py sync
.\venv\Scripts\python.exe .\bridge.py pending
.\venv\Scripts\python.exe .\bridge.py approve 33 --kind task --executor codex
.\venv\Scripts\python.exe .\bridge.py context 33
```

Then launch:

```powershell
codex
```

First Codex instruction:

```text
You are the explicitly authorized Codex executor for TASK-033.

First run:
.\venv\Scripts\python.exe .\bridge.py context 33

Read the authoritative TASK-033 and authorization context.
Implement only TASK-033.
Do not modify Bridge/Continuity Core.
Do not commit or push.
Run git diff --check and the targeted Bridge tests.
When complete, report files changed, validation results, and risks, then stop.
```

Publication remains a Human/Bridge action after Codex completes:

```powershell
.\venv\Scripts\python.exe .\bridge.py publish 33 --action RUN --test ".\venv\Scripts\python.exe -m pytest tests/ -q"
```

---

# Completion Contract

TASK-033 is complete only when all are true:

```text
[ ] Human explicitly authorized executor_id=codex
[ ] Codex consumed Bridge context before implementation
[ ] docs/AIOS_CODEX_EXECUTOR_WINDOWS.md exists and satisfies C5
[ ] no forbidden control-plane files changed
[ ] Codex did not manually commit/push
[ ] git diff --check passes
[ ] Bridge tests pass
[ ] full repository tests pass through Bridge publish gate
[ ] Bridge publishes RESULT-033
[ ] RESULT-033 records ACTION=RUN
[ ] RESULT-033 records EXECUTOR_ID=codex
[ ] RESULT-033 records EXECUTOR_FAILOVER=NO
[ ] Primary Brain independent review PASS
```

No self-declared PASS by Codex is authoritative.
