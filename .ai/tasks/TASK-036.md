# TASK-036 — M9.3 Real Two-Executor Hot Local Handoff Proof

STATUS: READY
WORK_CLASS: L4 — REAL OPERATIONAL PROOF
EXECUTOR_MODE: THIN EXECUTOR

## Baseline

BASELINE_MAIN_SHA: 6b698eca9be428d3043a2e13064a19f1f4dd2faf
TASK_BRANCH: ai/task-036
SOURCE_EXECUTOR: codex
REPLACEMENT_EXECUTOR: antigravity

Authoritative ADR:
`.ai/decisions/ADR-025-M9.3-REAL-TWO-EXECUTOR-HOT-HANDOFF-PROOF-CONTRACT-LOCK.md`
ADR_BLOB_SHA: fd02c610bbe47312292df61e5ba87ab72e5dd585

Authoritative blueprint:
`.ai/context/TASK-036-M9.3-IMPLEMENTATION-BLUEPRINT.md`
BLUEPRINT_BLOB_SHA: d8f82ea11c568999ab3506c5f7e5350c179b0560

## Objective

Prove one real unpublished dirty-workspace continuity chain:

`codex -> M9 checkpoint -> HANDOFF_PREPARED -> antigravity -> Bridge publication -> ChatGPT review`

No M9 core redesign is authorized.

HOT_HANDOFF_ALLOWED_PATHS_JSON: ["proofs/TASK-036-M9/source-stage.txt"]

## Stage A — Codex

After Human approves RUN with `--executor codex`, Codex creates exactly:

`proofs/TASK-036-M9/source-stage.txt`

Exact UTF-8 content with final newline:

```text
TASK_ID: TASK-036
STAGE: SOURCE_PRE_HANDOFF
EXECUTOR_ID: codex
PAYLOAD_VERSION: 1
```

Then Codex reports `git status --short` and STOPS.

Expected dirty state:

```text
?? proofs/TASK-036-M9/source-stage.txt
```

Codex must not create any other file, run full tests, commit, push, publish, or call hot-handoff commands.

## Human prepare + activate

Human alone runs:

```powershell
.\venv\Scripts\python.exe .\bridge.py hot-handoff-prepare 36 --confirm-quiescent
```

Record exact checkpoint fingerprint, then Human alone runs:

```powershell
.\venv\Scripts\python.exe .\bridge.py hot-handoff-activate 36 --executor antigravity --checkpoint <exact-fingerprint>
```

## Stage B — Antigravity

First run:

```powershell
.\venv\Scripts\python.exe .\bridge.py context 36
```

Then follow the authoritative blueprint exactly and create only:

```text
proofs/TASK-036-M9/replacement-stage.txt
scripts/aios_m9_real_hot_handoff_proof.py
tests/aios_bridge/continuity/test_m9_real_hot_handoff_proof.py
proofs/TASK-036-M9/PROOF.json
```

`PROOF.json` must be verifier-generated, never manually authored.

Do not modify `source-stage.txt`.

## Allowed Files

```text
proofs/TASK-036-M9/source-stage.txt
proofs/TASK-036-M9/replacement-stage.txt
proofs/TASK-036-M9/PROOF.json
scripts/aios_m9_real_hot_handoff_proof.py
tests/aios_bridge/continuity/test_m9_real_hot_handoff_proof.py
.ai/results/RESULT-036.md
```

## Forbidden Scope

Do not modify:

```text
bridge.py
src/aios_bridge/continuity/hot_handoff.py
src/aios_bridge/continuity/lease.py
src/aios_bridge/runtime_lease.py
src/aios_bridge/continuity/executor_failover.py
src/aios_bridge/continuity/state.py
```

No routing/provider/quota-policy changes. No M10/M11 work.

## Stage-B test gate

Antigravity runs only:

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_bridge/continuity/test_m9_real_hot_handoff_proof.py -q
.\venv\Scripts\python.exe -m pytest tests/test_bridge_hot_handoff.py -q
.\venv\Scripts\python.exe .\scripts\aios_m9_real_hot_handoff_proof.py verify
```

Then STOP. No commit/push/publish.

## Bridge publication gate

Human runs:

```powershell
.\venv\Scripts\python.exe .\bridge.py publish 36 --action RUN --test ".\venv\Scripts\python.exe -m pytest tests/ -q"
```

Expected RESULT evidence:

```text
TASK_ID: TASK-036
ACTION: RUN
EXECUTOR_ID: antigravity
EXECUTOR_FAILOVER: NO
HOT_HANDOFF: YES
HOT_HANDOFF_FROM_EXECUTOR: codex
HOT_HANDOFF_TO_EXECUTOR: antigravity
HOT_HANDOFF_CHECKPOINT_FINGERPRINT: <same as PROOF.json>
```

## Acceptance

Primary Brain independently verifies branch lineage, exact scope, embedded checkpoint fingerprint, PROOF fingerprint, checkpoint head == baseline, source witness present in checkpoint and unchanged in final commit, replacement witness absent from checkpoint and present in final commit, exact codex -> antigravity actor bindings, RESULT/PROOF agreement, full-suite exit 0, and no M9 core changes.

Free-form Executor claims are not proof.

TASK-036 PASS proves only this one real local two-Executor hot-handoff chain.