# ADR-008 — AIOS Bridge v0.5-M3.1 Real-Task Proof Contract Lock

## Status
LOCKED

## Date
2026-08-16

## Preconditions
- ADR-005 / v0.5-M1 External Brain contracts: LOCKED and merged.
- ADR-006 / v0.5-M2 deterministic ContextBuilder + Token Budget: LOCKED and merged.
- ADR-007 / v0.5-M3 ModelGateway + MiniMax + Usage Ledger: LOCKED and merged.
- Canonical `main` at lock time: `6fd3cb155c9edf6aaebbf85c5ad0812e7e737abb`.
- A manual MiniMax-M3 live smoke has succeeded through the real M3 path with normalized `SUCCESS` and persisted usage telemetry.
- Antigravity remains the sole workspace executor.

## Objective
M3.1 proves that the External Brain can contribute useful reasoning to a **real bounded repository task**, not merely a synthetic smoke prompt, while preserving all existing authority boundaries.

The proof must answer one practical question:

> Can MiniMax-M3 produce a contract-compliant PLAN from real selected repository context that Antigravity can use to implement a low-risk task without ChatGPT re-planning the implementation?

M3.1 is an evaluation milestone, not a router, not automatic delegation, and not a new execution authority.

```text
ChatGPT contract / TASK
        |
        v
explicit real repo context candidates
        |
        v
M2 ContextBuilder + budget/safety gates
        |
        v
ModelRequest(operation=PLAN)
        |
        v
M3 ModelGateway -> MiniMax-M3 LIVE
        |
        v
validated PLAN + UsageRecord
        |
        v
advisory plan artifact
        |
        v
Antigravity sole executor
        |
        v
code + tests + RESULT
        |
        v
ChatGPT review
```

---

# Decision 1 — One Bounded Real Task Only

M3.1 evaluates exactly one low-risk repository task: add a reusable **manual External Brain PLAN runner** for operator-controlled live evaluation.

The runner exists to replace pasted ad-hoc Python smoke blocks with a repeatable command before later provider-compatibility and Antigravity-integration milestones.

The task is intentionally bounded:
- explicit task file input;
- explicit context file inputs only;
- PLAN operation only in M3.1;
- MiniMax provider only;
- no automatic repo discovery;
- no router/fallback/retry;
- no patch application;
- no workspace mutation by the model;
- no Git operations;
- no shell/browser/tool authority granted to the model.

---

# Decision 2 — Contract Authority Precedence

Authority order is locked:

```text
ADR/TASK contract
    > safety/integrity invariants
    > selected repository context
    > External Brain PLAN
```

The MiniMax PLAN is advisory.

If the PLAN conflicts with ADR/TASK requirements, Antigravity MUST follow ADR/TASK and record the conflict in RESULT. The plan can never widen scope or authority.

---

# Decision 3 — Real Context Must Use M2 Selection

The real PLAN call MUST use M2 `ContextBuilder` and a finite `ContextBudget`.

Required context:
- TASK-017 content as `ContextKind.TASK`;
- ADR-008 content as `ContextKind.CONTRACT`;
- a small explicit set of relevant M3 source/test files as SOURCE/TEST context.

Rules:
1. No whole-repository dump.
2. No recursive repo crawl.
3. No `.env`, credentials, browser stores, private keys, or sensitive paths.
4. Candidate paths are operator/contract supplied, not model discovered.
5. M2 integrity, dedupe, deterministic ordering, and budget semantics remain authoritative.
6. Request context must exactly match `ContextBuildResult.selected` when passed to `ModelGateway`.

---

# Decision 4 — Live Evaluation Call is PLAN-Only

The pre-implementation real-task call MUST use:

```text
provider  = minimax
model     = MiniMax-M3
role      = ARCHITECT
operation = PLAN
output    = PLAN
```

It MUST:
- invoke the provider at most once;
- use no tools;
- use no retry/fallback;
- use bounded output tokens;
- preserve separated-reasoning safety from ADR-007;
- persist safe usage telemetry outside the worktree when a ledger is configured.

The API key remains local in `AIOS_MINIMAX_API_KEY` and MUST NOT enter Git, TASK, PLAN artifact, RESULT, logs, or review artifacts.

---

# Decision 5 — Advisory PLAN Artifact

After a successful live PLAN call, the final validated PLAN may be stored as a control-plane context artifact:

```text
.ai/context/TASK-017-MINIMAX-PLAN.md
```

The artifact may contain:
- provider/model identity;
- request/task IDs;
- final validated PLAN content;
- safe usage numbers and latency;
- context fingerprint/counter metadata when available.

It MUST NOT contain:
- API key or auth headers;
- raw HTTP request/response bodies;
- chain-of-thought/reasoning content;
- sensitive local paths beyond ordinary repository-relative paths;
- hidden context not selected by M2.

This artifact is advisory context only. It is not authorization and cannot replace TASK-017 or human RUN approval.

---

# Decision 6 — Real Task: Manual External Brain PLAN Runner

TASK-017 will implement a small operator utility, preferably:

```text
scripts/aios_external_brain_plan.py
```

Equivalent placement is allowed only if it preserves the same boundary and does not redesign M1-M3 contracts.

Required behavior:
1. Accept an explicit task file path.
2. Accept zero or more explicit context file specifications; no discovery/crawl.
3. Convert explicit files into `ContextItem`s with caller-specified/contract-defined kinds.
4. Use existing M2 `ContextBuilder` and finite budget.
5. Build a valid M1 `ModelRequest` for PLAN.
6. Use existing `MiniMaxOpenAIProvider` + `ModelGateway`; do not duplicate provider HTTP logic.
7. Read the credential only from `AIOS_MINIMAX_API_KEY` (or an explicitly injected equivalent for tests).
8. Print the normalized final PLAN and bounded safe telemetry.
9. Never print or persist secrets or separated reasoning.
10. Never apply a patch, edit repository files, run Git, run shell commands, browse, or invoke tools on behalf of the model.
11. No retry, fallback, provider registry, classifier, or routing.
12. Live network execution remains manual/operator-triggered; automated tests must not call MiniMax.

A thin script may delegate to testable helpers if needed, but M3.1 MUST avoid introducing a new framework.

---

# Decision 7 — Stable Failure Semantics

The manual runner must fail closed before network use for invalid local inputs/contracts when practical.

At minimum:
- missing credential -> non-zero exit without network call;
- missing/unreadable task/context file -> non-zero exit without network call;
- invalid context kind/spec -> non-zero exit without network call;
- M2 sensitive-context/integrity/budget failure -> non-zero exit without network call;
- provider failure -> report normalized status/error code only and non-zero exit;
- `SUCCESS` requires M1 structural PLAN validation already enforced through ModelGateway.

Raw exception messages that could contain secrets or auth material MUST NOT be printed.

---

# Decision 8 — Evaluation Evidence

RESULT-017 must make the M3.1 experiment auditable.

Required evidence fields/sections:
- exact implementation commit tested;
- External Brain provider/model;
- live request/task ID;
- live normalized status;
- provider input/output token counts when reported;
- latency;
- context fingerprint/count/counter metadata when available;
- ledger persistence status;
- plan artifact SHA/hash or Git blob/commit identity if persisted to control plane;
- `PLAN_ADOPTION`: `ACCEPTED_AS_IS`, `ACCEPTED_WITH_LOCAL_ADJUSTMENTS`, or `REJECTED`;
- `CHATGPT_REPLAN_REQUIRED`: `YES` or `NO`;
- concise deviations between MiniMax PLAN and actual Antigravity implementation;
- focused test result;
- full repository test result;
- confirmation that automated tests made zero live MiniMax calls;
- confirmation that no credentials/reasoning were persisted.

No raw API key, auth header, or separated reasoning may appear in RESULT.

---

# Decision 9 — Success Criteria

M3.1 is successful only if all are true:
1. Real selected repository context passes M2 gates.
2. One live MiniMax-M3 PLAN returns normalized `SUCCESS`.
3. PLAN passes M1 structural validation.
4. Usage telemetry is safely recorded.
5. Antigravity implements TASK-017 while remaining sole executor.
6. `CHATGPT_REPLAN_REQUIRED = NO` for implementation planning; ChatGPT may still perform final review.
7. Focused tests pass.
8. Full repository tests pass with zero regressions.
9. No live provider call occurs in automated tests.
10. No secret/reasoning leakage occurs.

If the PLAN is rejected or ChatGPT must redesign the implementation before Antigravity can proceed, the experiment is still valuable evidence but M3.1 is **not proven**; RESULT must say so explicitly.

---

# Decision 10 — Non-Goals

M3.1 MUST NOT implement:
- DeepSeek/Kimi/GLM providers;
- provider registry;
- task classifier;
- automatic model router;
- fallback or retry;
- quota polling;
- automatic Antigravity invocation;
- MCP/tool execution by External Brain;
- automatic patch application;
- repo-wide discovery/indexing/embeddings;
- changes to `bridge.py` v0.4 handoff/authorization/publish semantics;
- semantic changes to the existing Python Agent runtime `src/providers/` layer.

Those remain later milestones.

---

# Compatibility Lock

M3.1 MUST preserve:
- AIOS Bridge v0.4 control-plane semantics;
- ADR-005 M1 contracts;
- ADR-006 M2 context/budget semantics;
- ADR-007 M3 gateway/provider/usage semantics;
- Antigravity as sole executor;
- human RUN/FIX approvals;
- runtime state outside the worktree;
- existing Python Agent provider layer unchanged;
- backward-compatible RESULT/review/merge workflow.

Any future change to these locked boundaries requires a later ADR.