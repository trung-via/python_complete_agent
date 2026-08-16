# TASK-017 — AIOS Bridge v0.5-M3.1 Real-Task Proof + Manual External Brain PLAN Runner

## Objective
Execute the first **real repository task assisted by MiniMax-M3** under the contract locked in:

`.ai/decisions/ADR-008-AIOS-BRIDGE-V0.5-M3.1-REAL-TASK-PROOF-CONTRACT-LOCK.md`

Canonical baseline when authored:
- `main`: `6fd3cb155c9edf6aaebbf85c5ad0812e7e737abb`
- v0.5-M1/M2/M3: merged / APPROVED
- ADR-005 / ADR-006 / ADR-007 / ADR-008: LOCKED
- manual synthetic MiniMax-M3 live smoke: SUCCESS

The real implementation target is a small reusable **manual External Brain PLAN runner**. The MiniMax plan is advisory; Antigravity remains the sole workspace executor.

```text
TASK-017 + ADR-008 + explicit M3 source/test context
        |
        v
M2 ContextBuilder
        |
        v
MiniMax-M3 LIVE PLAN
        |
        v
.ai/context/TASK-017-MINIMAX-PLAN.md
        |
        v
USER APPROVE RUN
        |
        v
Antigravity implements/tests
        |
        v
RESULT-017
        |
        v
ChatGPT review
```

---

# Pre-Execution Gate — REQUIRED

**Do not begin implementation until the advisory live PLAN artifact exists:**

```text
.ai/context/TASK-017-MINIMAX-PLAN.md
```

If TASK-017 is RUN before that artifact is available to the worker, Antigravity MUST fail closed / stop before coding and request the missing plan context.

The PLAN artifact does not authorize execution. Human `/aios-worker RUN TASK-017` approval remains required.

---

# Implementation Scope

Implement a small operator utility, preferably:

```text
scripts/aios_external_brain_plan.py
```

A thin helper module under `src/aios_bridge/external_brain/` is allowed only where needed for testability. Do not introduce a new framework.

The utility must reuse the existing M1-M3 implementation rather than duplicating transport/provider/gateway logic.

---

# Functional Requirements

## 1. Explicit task input

The runner MUST accept an explicit repository/local task file path.

Example conceptual usage:

```text
python scripts/aios_external_brain_plan.py \
  --task-file .ai/tasks/TASK-017.md \
  --context CONTRACT:.ai/decisions/ADR-008-...md \
  --context SOURCE:src/aios_bridge/external_brain/gateway.py \
  --context SOURCE:src/aios_bridge/external_brain/providers/minimax.py \
  --context TEST:tests/aios_bridge/external_brain/test_gateway.py
```

Exact CLI spelling may differ if the MiniMax advisory PLAN proposes a cleaner minimal interface, but all locked semantics below must hold.

## 2. Explicit context only

The runner MUST:
- accept zero or more explicit context file specifications;
- require/derive a valid `ContextKind` for each supplied context;
- read only explicitly supplied files;
- perform no repo crawl, glob expansion across the repo, semantic search, index lookup, or automatic dependency discovery;
- send the resulting candidates through the existing M2 `ContextBuilder` and finite `ContextBudget`.

TASK content must enter context as `ContextKind.TASK`.

## 3. Existing M1/M2/M3 pipeline only

The runner MUST build a valid `ModelRequest` and invoke the existing path:

```text
ContextBuilder
  -> ModelRequest
  -> ModelGateway
  -> MiniMaxOpenAIProvider
  -> OpenAICompatibleTransport
  -> MiniMax-M3
  -> validated ModelResponse
  -> optional UsageLedger
```

Do not duplicate MiniMax HTTP payload/parsing logic in the script.

## 4. PLAN-only authority

For M3.1 the runner is locked to:

```text
role      = ARCHITECT
operation = PLAN
output    = PLAN
provider  = minimax
```

Model may propose only. It MUST NOT receive callable tools or execution authority.

The runner MUST NOT:
- apply patches;
- write/edit repository source files on behalf of the model;
- execute shell commands from model output;
- run browser actions;
- run Git commands;
- commit/push/merge;
- authorize bridge continuation.

## 5. Credential handling

Use `AIOS_MINIMAX_API_KEY` from local environment at runtime.

Requirements:
- missing key fails before network call;
- never print key;
- never include key in repr/error/output/ledger;
- never persist key to repository/control artifacts;
- no assumptions based on key prefix.

## 6. Bounded request configuration

The runner MUST expose or define finite conservative limits for:
- context budget;
- output token budget;
- transport timeout via existing provider/transport configuration.

No unbounded context or output.

No automatic retry/fallback.

## 7. Safe output

On SUCCESS, print at minimum:
- normalized status;
- provider/model;
- provider input/output token counts when available;
- latency;
- provider request ID when available;
- M2 context fingerprint/count/counter metadata when available;
- ledger persistence status when configured;
- final validated PLAN content.

Do not print separated reasoning or raw HTTP bodies.

On provider failure, print only bounded normalized status/error information and return non-zero exit.

## 8. Ledger

If usage ledger persistence is supported by the runner:
- require an explicit caller-supplied ledger path or a clearly documented runtime/temp default outside the repository worktree;
- reuse `JsonlUsageLedger`;
- do not create `.ai/usage` or another in-worktree usage store by default.

---

# Real-Task MiniMax PLAN Inputs

The pre-implementation live PLAN should use a bounded explicit candidate set centered on the following files where present:

```text
.ai/tasks/TASK-017.md                                  TASK
.ai/decisions/ADR-008-AIOS-BRIDGE-V0.5-M3.1-REAL-TASK-PROOF-CONTRACT-LOCK.md  CONTRACT
src/aios_bridge/external_brain/contracts.py            SOURCE
src/aios_bridge/external_brain/context.py              SOURCE
src/aios_bridge/external_brain/gateway.py              SOURCE
src/aios_bridge/external_brain/providers/minimax.py    SOURCE
src/aios_bridge/external_brain/usage.py                SOURCE
src/aios_bridge/external_brain/__init__.py             SOURCE
```

Add at most a small number of directly relevant tests if the context budget permits. Do not dump all tests or the whole repository.

The M2 selection result is authoritative if not every optional candidate fits.

---

# MiniMax PLAN Adoption Rule

Antigravity MUST read `.ai/context/TASK-017-MINIMAX-PLAN.md` before implementation.

Then classify the plan in RESULT as exactly one of:

```text
PLAN_ADOPTION: ACCEPTED_AS_IS
PLAN_ADOPTION: ACCEPTED_WITH_LOCAL_ADJUSTMENTS
PLAN_ADOPTION: REJECTED
```

Rules:
- TASK/ADR contract overrides PLAN on any conflict.
- Minor local adjustments for filenames, existing APIs, or test placement do not automatically mean rejection.
- If the plan requires architectural redesign or ChatGPT must provide a replacement implementation plan before coding can proceed, classify as `REJECTED` and `CHATGPT_REPLAN_REQUIRED: YES`.

For M3.1 proof success, `CHATGPT_REPLAN_REQUIRED` must be `NO`.

---

# Tests

Automated tests MUST use fakes/mocks/local-only mechanisms. They MUST NOT make a live MiniMax call.

Minimum focused coverage:
1. valid explicit TASK + context inputs build through M2 and invoke gateway once;
2. missing credential fails before provider/network invocation;
3. missing/unreadable task file fails before provider/network invocation;
4. invalid context kind/spec fails closed;
5. sensitive context path/content is rejected by existing M2 safety gates;
6. context budget failure propagates safely;
7. provider normalized failure returns non-zero outcome without retry;
8. SUCCESS renders safe telemetry + final PLAN;
9. output does not expose API key or separated reasoning;
10. no repo discovery/crawl is performed;
11. no patch/shell/git/browser/tool execution path exists;
12. automated tests make zero live external requests.

Run:
- focused M3.1 tests;
- full `tests/aios_bridge/` suite;
- full repository `tests/` suite.

Zero regressions required.

---

# RESULT-017 Required Evidence

`RESULT-017.md` MUST include:

```text
IMPLEMENTATION_HEAD: <sha>
EXTERNAL_BRAIN_PROVIDER: minimax
EXTERNAL_BRAIN_MODEL: MiniMax-M3
EXTERNAL_BRAIN_REQUEST_ID: <id>
EXTERNAL_BRAIN_TASK_ID: TASK-017
EXTERNAL_BRAIN_STATUS: SUCCESS|...
PROVIDER_INPUT_TOKENS: <n|None>
PROVIDER_OUTPUT_TOKENS: <n|None>
LATENCY_MS: <n|None>
CONTEXT_FINGERPRINT: <value|None>
CONTEXT_COUNTED_TOKENS: <n|None>
CONTEXT_COUNTER_ID: <value|None>
LEDGER_PERSISTED: True|False|None
PLAN_ARTIFACT: .ai/context/TASK-017-MINIMAX-PLAN.md
PLAN_ARTIFACT_IDENTITY: <commit/blob/hash>
PLAN_ADOPTION: ACCEPTED_AS_IS|ACCEPTED_WITH_LOCAL_ADJUSTMENTS|REJECTED
CHATGPT_REPLAN_REQUIRED: YES|NO
LIVE_CALLS_IN_AUTOMATED_TESTS: 0
CREDENTIALS_PERSISTED: NO
SEPARATED_REASONING_PERSISTED: NO
```

Also include:
- concise summary of MiniMax plan recommendations;
- concise actual Antigravity implementation summary;
- deviations between plan and actual implementation;
- focused test command/result;
- AIOS Bridge test command/result;
- full repository test command/result;
- branch changed-file summary and diffstat.

Do not include API key, auth headers, raw HTTP bodies, or chain-of-thought/reasoning.

---

# Acceptance Criteria

TASK-017 is PASS only if:
1. Pre-implementation real MiniMax PLAN exists and is structurally valid.
2. Real PLAN used TASK-017 + ADR-008 + bounded explicit repository context through M2.
3. Provider was invoked once with no retry/fallback.
4. Safe usage/context telemetry exists.
5. Manual runner meets all locked authority/safety requirements.
6. Antigravity remained sole executor.
7. `CHATGPT_REPLAN_REQUIRED: NO`.
8. Focused tests pass.
9. `tests/aios_bridge/` passes.
10. Full repository `tests/` passes with zero regressions.
11. Automated tests made zero live MiniMax calls.
12. No credentials or separated reasoning were persisted.
13. `bridge.py` v0.4 semantics are unchanged.
14. Existing Python Agent `src/providers/` semantics are unchanged.

---

# Non-Goals

Do NOT implement in TASK-017:
- DeepSeek/Kimi/GLM providers;
- provider registry;
- task classifier;
- router;
- retry/fallback;
- quota polling;
- automatic Antigravity integration;
- automatic patch application;
- repo-wide discovery/indexing;
- MCP/tool execution by External Brain;
- changes to `bridge.py` authorization/publish semantics;
- changes to Python Agent runtime provider contracts.

---

# Worker Instruction

Before coding:
1. verify ADR-008 is present and LOCKED;
2. verify `.ai/context/TASK-017-MINIMAX-PLAN.md` is present;
3. read TASK-017 + ADR-008 + advisory PLAN;
4. confirm plan does not widen authority;
5. only then implement under human RUN authorization.

If the advisory PLAN conflicts with this TASK or ADR-008, this TASK/ADR wins and the deviation must be recorded in RESULT.