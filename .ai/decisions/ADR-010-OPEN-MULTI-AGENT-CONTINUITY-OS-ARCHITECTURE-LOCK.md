# ADR-010 — Open Multi-Agent Continuity OS Architecture Lock

STATUS: LOCKED

## Context

The earlier #12 direction centered on an API-first multi-model router: AIOS would classify work and dispatch PLAN/PATCH/DEBUG/REVIEW operations to paid external model APIs such as MiniMax, Kimi, DeepSeek, or OpenAI-compatible providers.

M3/M3.1 successfully proved the External Brain abstraction with MiniMax-M3. That proof remains valid and valuable. However, the primary optimization objective has changed after real-task evaluation:

> Prefer subscription-backed interactive AI capacity before paid per-token API capacity, while preserving continuity, auditability, human authority, and executor safety.

The system must survive:
- chat usage limits;
- executor quota exhaustion;
- model/vendor changes;
- session loss;
- switching between different Brain surfaces;
- switching between different Executor surfaces;
without losing canonical project state or violating authority boundaries.

This ADR supersedes the old API-first #12 Model Router direction.

It does NOT revoke ADR-005 through ADR-009. The existing External Brain contracts, ContextBuilder, ModelGateway, MiniMax provider, transport, usage ledger, and M3.1 proof remain supported as an optional fallback/escape hatch.

---

## Decision 1 — Architecture Name and Core Goal

The new #12 architecture is:

**Open Multi-Agent Continuity OS**

Core properties:

1. Brain-neutral.
2. Executor-neutral.
3. Vendor-neutral.
4. Subscription-first.
5. API-optional.
6. Human-authorized.
7. Canonical-state-driven.
8. Fail-closed at authority and handoff boundaries.

The primary optimization target is no longer `lowest API model cost per call`.

The primary optimization targets are:
- minimal paid external API calls;
- minimal high-value Brain turns per completed task;
- minimal repeated context loading;
- zero manual copy/paste in the normal workflow;
- minimal handoff count;
- continuity across Brain and Executor failover.

---

## Decision 2 — Brain Pool

AIOS SHALL model reasoning surfaces as implementations of a common Brain contract.

Initial intended Brain options:

- `chatgpt-chat`
- `claude-chat`
- `gemini-chat`
- future Brain implementations

Existing API-backed External Brain providers, including MiniMax-M3, remain available as optional fallback capacity.

The default policy intent is:

1. ChatGPT Chat — preferred Primary Brain.
2. Claude Chat — subscription-backed failover Brain.
3. Gemini Chat — subscription-backed tertiary / large-context specialist Brain.
4. External API Brain — optional paid escape hatch.

This ordering is policy, NOT core architecture.

AIOS Continuity Core MUST NOT depend on this ordering.

A deployment MAY choose a different preferred Brain without modifying Continuity Core.

---

## Decision 3 — Brain Operations

A compatible Brain MAY perform only reasoning/advisory operations such as:

- TASK design
- PLAN
- DIAGNOSE_FAILURE / DEBUG
- PATCH_PROPOSAL
- REVIEW

Brain output SHALL remain proposal/control-artifact oriented.

Brain authority SHALL NOT include:

- local shell execution;
- browser execution;
- direct local workspace mutation as Executor authority;
- autonomous RUN/FIX authorization;
- autonomous merge authorization;
- bypass of TASK/ADR contracts;
- secret persistence.

Existing External Brain output contracts remain the conceptual baseline:

PLAN:
- SUMMARY
- STEPS
- FILES
- TESTS
- RISKS

DIAGNOSIS:
- CAUSE
- EVIDENCE
- FIX
- TESTS
- RISKS

PATCH_PROPOSAL:
- SUMMARY
- FILES
- PATCH
- TESTS
- RISKS

REVIEW:
- STATUS
- FINDINGS
- TESTS
- RISKS

Review status remains:
- PASS / APPROVED equivalent as defined by the consuming workflow;
- CHANGES_REQUIRED.

---

## Decision 4 — BrainAdapter Must Be Vendor-Neutral

The Continuity Core SHALL interact with Brains through a vendor-neutral abstraction.

Conceptual interface:

```python
class BrainAdapter(Protocol):
    @property
    def brain_id(self) -> str: ...

    def capabilities(self) -> BrainCapabilities: ...
```

Interactive chat surfaces MAY be human-triggered rather than programmatically invoked.

Therefore `BrainAdapter` is a logical architecture boundary, not a requirement that every chat product expose a callable API.

The core MUST NOT contain vendor branching such as:

```python
if brain == "chatgpt": ...
elif brain == "claude": ...
elif brain == "gemini": ...
```

Vendor-specific behavior belongs in adapters/capability declarations/integration edges.

Adding a new Brain MUST NOT require modification of AIOS Continuity Core.

---

## Decision 5 — Brain Capability Model

Brain selection SHALL be capability-driven rather than vendor-driven.

Example capability dimensions MAY include:

- supported operations;
- human trigger required;
- direct repo read availability;
- control-artifact write availability;
- large-context suitability;
- connector/MCP availability;
- interactive-only vs programmatic;
- subscription-backed vs paid API-backed.

Capability declarations MUST NOT grant authority beyond the locked Brain contract.

Gemini Chat is accepted as a valid future BrainAdapter option.

Gemini SHALL NOT require direct GitHub import to participate. AIOS must be able to provide Gemini a bounded canonical Brain Context Pack instead.

---

## Decision 6 — Executor Pool

AIOS SHALL model coding/execution agents as implementations of a common Executor contract.

Initial intended Executor options:

- `antigravity`
- `codex`
- `claude-code`
- future coding agents

The current preferred Executor may remain Antigravity, but preference is policy rather than architecture.

Executor responsibilities MAY include, subject to capability and authorization:

- filesystem edits;
- test execution;
- shell/tool execution;
- browser work where supported;
- local Git inspection;
- preparation of implementation evidence.

Executor authority MUST remain bounded by TASK/ADR/control authorization.

Human approval for RUN/FIX remains mandatory unless a future ADR explicitly changes this invariant.

Merge remains human-authorized.

---

## Decision 7 — ExecutorAdapter Must Be Vendor-Neutral

Conceptual interface:

```python
class ExecutorAdapter(Protocol):
    @property
    def executor_id(self) -> str: ...

    def capabilities(self) -> ExecutorCapabilities: ...

    def prepare(self, request: ExecutionRequest) -> PreparedExecution: ...

    def collect_result(self, execution_id: str) -> ExecutionResult: ...
```

Continuity Core MUST NOT contain executor-vendor branching such as:

```python
if executor == "antigravity": ...
elif executor == "codex": ...
elif executor == "claude-code": ...
```

Adding a new Executor MUST require only adapter/integration/capability work and MUST NOT require architectural modification of Continuity Core.

A key acceptance criterion for the architecture is:

> Adding the third Executor (for example Claude Code after Antigravity and Codex) does not require changing the Continuity Core contract/state machine.

---

## Decision 8 — Executor and Transport Are Separate Concerns

Where programmatic integration exists, Executor identity SHALL be separated from communication/execution transport.

Conceptual examples:

- AntigravityAdapter + HandoffTransport / CLI transport when available
- CodexAdapter + Local transport / Cloud transport
- ClaudeCodeAdapter + LocalCLITransport

The core SHALL reason about capabilities and execution contracts, not product-specific command syntax.

---

## Decision 9 — Canonical Project State Lives Outside Chat Memory

Chat history SHALL NOT be canonical project state.

Agent conversation history SHALL NOT be required for failover.

Canonical continuity state SHALL be externalized into project/control artifacts and repository state.

Planned canonical state artifacts include concepts such as:

- TASK
- ADR / contract
- PLAN / context artifact
- RESULT
- REVIEW
- CURRENT-STATE
- context manifest / bounded context pack metadata
- execution handoff/checkpoint when applicable

The invariant is:

> Brain memory != project memory.
> Executor conversation != execution state.
> Canonical state = AIOS artifacts + repository/workspace evidence.

A new Brain or Executor MUST be able to resume from canonical state without receiving the entire prior conversation transcript.

Conversation dumps SHALL NOT be the normal continuity mechanism.

---

## Decision 10 — CURRENT-STATE as Save-Point Concept

AIOS SHALL introduce a compact canonical current-state representation in a future milestone.

It SHOULD contain only operationally necessary metadata such as:

- schema version;
- current task;
- lifecycle phase;
- canonical main SHA;
- task branch;
- task head;
- authoritative TASK;
- authoritative ADRs;
- active PLAN/context artifact;
- latest RESULT;
- latest REVIEW;
- next required operation;
- current/last Brain metadata where useful;
- current/last Executor metadata where useful.

CURRENT-STATE MUST remain small and deterministic.

It MUST NOT become a conversation transcript or unrestricted context dump.

---

## Decision 11 — Brain Failover

The system SHALL support future stable-boundary Brain failover such as:

- ChatGPT Chat -> Claude Chat
- Claude Chat -> ChatGPT Chat
- ChatGPT/Claude -> Gemini Chat
- any supported Brain -> optional External API Brain

A replacement Brain SHALL reconstruct task context from canonical artifacts.

It SHALL NOT need hidden reasoning or chat history from the prior Brain.

If a Brain stops before publishing a valid authoritative artifact, its unfinished reasoning is non-authoritative transient state.

The next Brain restarts the pending operation from canonical inputs.

---

## Decision 12 — Executor Lease

AIOS SHALL introduce a future Executor Lease contract.

Invariant:

`MAX_ACTIVE_EXECUTORS_PER_TASK = 1`

Only one Executor may own the active execution lease for a task/workspace at a time, unless a future explicitly-scoped parallel-worktree ADR permits controlled parallel exploration.

Executor failover SHALL follow:

1. stop/release current executor;
2. capture required canonical execution state/evidence;
3. release lease;
4. acquire lease for replacement executor;
5. resume according to the same TASK/PLAN/authorization.

Concurrent uncontrolled mutation of the same workspace by Antigravity, Codex, Claude Code, or another Executor is prohibited.

---

## Decision 13 — Stable-Boundary Failover Before Hot Handoff

Executor continuity SHALL be developed in this order:

1. stable-boundary failover first;
2. hot/local mid-task handoff later and only after separate contract/audit.

Examples of stable-boundary failover:

- Antigravity RUN -> RESULT -> Codex FIX
- Codex RUN -> RESULT -> Antigravity FIX
- Claude Code RUN -> RESULT -> another Executor FIX

Mid-task dirty-workspace handoff is NOT authorized by this ADR alone.

It requires a future checkpoint/handoff contract.

---

## Decision 14 — Subscription-First Capacity Policy

Normal operation SHALL prefer already-paid subscription capacity before paid per-token API capacity when the required capability is available and safe.

Conceptual capacity pools:

Brain subscription pool:
- ChatGPT Chat
- Claude Chat
- Gemini Chat

Executor subscription/plan pool:
- Antigravity
- Codex
- Claude Code

Paid API escape hatch:
- MiniMax
- Kimi
- DeepSeek
- OpenAI API
- other future providers

External API usage MUST be optional in the normal interactive workflow.

M3/M3.1 External Brain work remains preserved precisely as this escape hatch.

---

## Decision 15 — Deterministic Dispatch Before Smart Routing

No LLM-based model/executor router is required for #12 core.

Initial dispatch SHALL be deterministic and zero-token.

Examples:

Brain:
- preferred Brain available -> preferred Brain
- unavailable/limited -> next compatible subscription Brain
- large-context specialist needed -> compatible large-context Brain
- urgent and API explicitly allowed -> External API Brain
- otherwise -> WAIT

Executor:
- required capabilities filter first;
- available compatible executor next;
- quota/user preference may choose among compatible executors;
- browser-required tasks may prefer an executor with browser capability;
- repo-only tasks may use any compatible executor.

Dispatch policy MUST NOT silently weaken contracts or authority.

---

## Decision 16 — Human Trigger Is an Accepted Cost Optimization

Interactive Brain surfaces such as ChatGPT Chat, Claude Chat, and Gemini Chat may require a short human trigger, for example:

- `Design next task`
- `Plan TASK-N`
- `Debug TASK-N`
- `Review TASK-N`
- `Resume TASK-N`

This is an intentional trade-off to consume subscription-backed chat capacity rather than paid API tokens.

The system SHOULD minimize Brain turns by combining logically compatible work, for example:

- TASK + PLAN in one high-value Brain turn;
- REVIEW + DIAGNOSIS + FIX instruction in one Brain turn when changes are required.

Target metric concepts include:

- `CHATGPT_TURNS_PER_TASK`
- `CLAUDE_TURNS_PER_TASK`
- `GEMINI_TURNS_PER_TASK`
- `EXTERNAL_API_CALLS_PER_TASK`
- `HANDOFF_CONTEXT_TOKENS`
- `HUMAN_COPY_PASTE_BYTES`
- `FAILOVER_RECOVERY_TURNS`

Normal-task target intent:

- paid External API calls = 0;
- manual copy/paste = 0;
- approximately 2 high-value Brain turns for a clean task;
- approximately 3 Brain turns for a one-fix task.

These are optimization targets, not correctness contracts.

---

## Decision 17 — No Chat-Web Browser Automation as API Substitute

AIOS SHALL NOT depend on browser automation that logs into ChatGPT, Claude, Gemini, or similar chat products and simulates UI input merely to convert a subscription chat surface into a pseudo-API.

Reasons:

- brittle UI/session behavior;
- difficult structured-output guarantees;
- weak auditability;
- unstable authentication boundaries;
- increased safety/security complexity.

Interactive chat surfaces remain human-triggered unless an official supported integration surface exists.

---

## Decision 18 — Existing Bridge v0.4 Authority Remains Locked

Until explicitly superseded by a future ADR:

- `bridge.py` v0.4 handoff/sync/authorization/publish semantics remain authoritative;
- human RUN approval remains mandatory;
- human FIX approval remains mandatory;
- human MERGE approval remains mandatory;
- runtime control state remains outside the worktree;
- fail-closed branch reconciliation remains;
- TASK/REVIEW authorization semantics remain;
- Antigravity remains the currently proven sole executor for the existing workflow until Executor-Neutral milestones are implemented and proven.

This ADR defines future architecture direction. It does not silently grant Codex or Claude Code execution authority in the current implementation.

---

## Decision 19 — Existing External Brain Contracts Remain Valid

ADR-005 through ADR-009 and TASK-014 through TASK-018 evidence remain historical and technical foundations.

Specifically:

- External Brain remains proposal-only;
- M2 ContextBuilder remains a valid bounded context mechanism;
- ModelGateway remains valid for programmatic API Brains;
- MiniMax-M3 remains a proven External API Brain;
- usage telemetry remains valuable;
- no router/fallback was required for M3/M3.1 and none is retroactively added.

External Brain is demoted from planned primary path to optional fallback path; it is not removed.

---

## Decision 20 — Planned Milestone Order

The preferred #12 roadmap is:

### M1 — Canonical Project State
Introduce compact CURRENT-STATE / state contract.

### M2 — Brain-Neutral Contract
Formalize interactive Brain capabilities and canonical context handoff.

### M3 — Brain Failover Proof
Prove continuity across at least two chat Brains using the same canonical task state.

### M4 — Executor-Neutral Contract
Formalize ExecutionRequest, ExecutionResult, ExecutorCapabilities, adapter boundary.

### M5 — Executor Lease
Enforce exactly one active executor per task/workspace.

### M6 — Stable-Boundary Executor Failover
Prove Antigravity <-> Codex at safe task/result/review boundaries.

### M7 — Third Executor Portability Proof
Add Claude Code without changing Continuity Core contracts/state machine.

### M8 — Multi-Agent Continuity Proof
Prove a real task can cross Brain and Executor boundaries while preserving authority and evidence.

### M9 — Optional Hot Local Handoff
Design/audit checkpoint-based dirty-workspace executor handoff separately.

### M10 — Quota-Efficient Deterministic Dispatch
Add policy/capability selection without LLM routing.

### M11 — External API Escape Hatch
Retain/use MiniMax and future external providers when subscription surfaces are unavailable or unsuitable.

Milestone numbering may be mapped to repository phase numbering in future TASKs; semantic ordering is locked unless a future ADR changes it.

---

## Decision 21 — Acceptance Criteria for Open Architecture

The architecture SHALL be considered correctly abstracted only if all of the following are achievable:

1. Switching Brain from ChatGPT to Claude does not change TASK/ADR/RESULT contracts.
2. Adding Gemini as a Brain does not require Continuity Core changes.
3. Switching Executor from Antigravity to Codex at a stable boundary does not require rewriting the TASK.
4. Adding Claude Code as the third Executor does not require Continuity Core state-machine changes.
5. Brain and Executor may fail over independently.
6. Canonical task state survives chat/session expiration.
7. No prior hidden reasoning is required to resume.
8. Human RUN/FIX/MERGE authority survives every failover.
9. Normal workflow can complete with zero paid External Brain API calls.
10. External API fallback remains available without becoming a mandatory path.

---

## Decision 22 — Non-Goals of This ADR

This ADR does NOT authorize implementation yet of:

- ChatGPT automation;
- Claude automation;
- Gemini automation;
- Codex adapter;
- Claude Code adapter;
- Antigravity CLI integration;
- Executor Lease implementation;
- CURRENT-STATE implementation;
- hot workspace handoff;
- quota detection automation;
- smart/LLM routing;
- automatic API fallback;
- autonomous merge.

Each requires a scoped TASK/ADR/proof as appropriate.

---

## Locked Architectural Summary

```text
                         HUMAN AUTHORITY
                               |
                               v
                     +-------------------+
                     |     BRAIN POOL    |
                     |-------------------|
                     | ChatGPT Chat      |
                     | Claude Chat       |
                     | Gemini Chat       |
                     | future Brains     |
                     +---------+---------+
                               |
                  TASK / PLAN / DEBUG /
                  PATCH PROPOSAL / REVIEW
                               |
                               v
                  +-------------------------+
                  | AIOS CONTINUITY CORE    |
                  |-------------------------|
                  | Canonical State         |
                  | Brain Contract          |
                  | Executor Contract       |
                  | Capability Contracts    |
                  | Executor Lease          |
                  | Handoff / Checkpoint    |
                  +-----------+-------------+
                              |
                       HUMAN RUN / FIX
                              |
                              v
                     +-------------------+
                     |   EXECUTOR POOL   |
                     |-------------------|
                     | Antigravity       |
                     | Codex             |
                     | Claude Code       |
                     | future Executors  |
                     +---------+---------+
                               |
                        code / tests / RESULT
                               |
                               +-------> Brain Pool

              OPTIONAL PAID ESCAPE HATCH
                         ModelGateway
                              |
                  MiniMax / future APIs
```

The system is designed so that:

> Brains can change.
> Executors can change.
> Vendors can change.
> Sessions can expire.
> Quotas can run out.
>
> Canonical project state, contracts, authority, and work continuity survive.

This architecture is LOCKED until explicitly superseded by a future ADR.
