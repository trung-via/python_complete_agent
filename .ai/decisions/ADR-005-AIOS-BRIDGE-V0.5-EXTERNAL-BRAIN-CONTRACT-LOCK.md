# ADR-005 — AIOS Bridge v0.5 External Brain M1 Contract Lock

## Status
LOCKED

## Date
2026-08-16

## Baseline
- Repository: `trung-via/python_complete_agent`
- Canonical implementation baseline inspected: `main@9d3dcfeab5ffc98bf6aeb3ef7a67912a5bc1fd52`
- Existing bridge: `bridge.py` — AI Engineering OS Lite Bridge v0.4.0
- Existing Python Agent LLM contract: `src/providers/base.py::LLMProvider`
- Existing active execution lane at lock time: TASK-013 / REVIEW-013 = `CHANGES_REQUIRED`

## Decision Summary
AIOS Bridge v0.5 introduces an **External Brain** subsystem without replacing or weakening the v0.4 Zero-Touch Handoff.

The architecture is intentionally split:

```text
TASK / REVIEW
    |
    v
AIOS Bridge v0.4 control + authorization
    |
    v
Antigravity (SOLE EXECUTOR)
    |
    +--> External Brain request
    |       |
    |       v
    |    ModelGateway (M3)
    |       |
    |       v
    |    ProviderAdapter
    |       |
    |       v
    |    ModelTransport
    |       |
    |       v
    |    External model
    |       |
    |       v
    |    PLAN / PATCH_PROPOSAL / DIAGNOSIS / REVIEW
    |
    +--> Antigravity applies edits, runs tests, uses browser, git
    |
    v
RESULT -> existing v0.4 publication/review flow
```

### Core invariant
**External models are Brain only. Antigravity remains the only executor.**

External Brain v0.5 MUST NOT receive direct filesystem, shell, browser, git, commit, push, or merge authority.

---

## Audit Findings

### A1 — Preserve v0.4 control-plane semantics
Current `bridge.py` already provides:
- external runtime storage outside the Git worktree;
- TASK/REVIEW synchronization from `ai-control`;
- explicit RUN/FIX authorization records;
- safe local-main reconciliation;
- task branch preparation;
- fail-closed dirty/diverged Git handling;
- RESULT publication through the existing authorized path.

External Brain MUST be additive. M1-M3 MUST NOT redesign `cmd_handoff`, authorization storage, task-branch semantics, sync semantics, publish semantics, or RESULT/REVIEW handoff.

### A2 — Do not reuse `src.providers.LLMProvider` as the External Brain contract
`src/providers/base.py::LLMProvider` is the Python Agent runtime provider abstraction. It accepts unified chat history + tool schemas and returns `LLMResponse` with tool calls.

External Brain has different semantics:

```text
bounded TASK/context -> one requested operation -> normalized artifact
```

and explicitly has **no tool execution authority**.

Therefore v0.5 MUST NOT overload, rename, or mutate the existing `LLMProvider` / `LLMResponse` contract for External Brain. Shared lower-level transport code may be reused later only when semantics remain clean.

### A3 — Isolate the subsystem
Preferred package boundary:

```text
src/aios_bridge/
  __init__.py
  external_brain/
    __init__.py
    contracts.py
    provider.py
    transport.py
    errors.py
```

M2 may add `context.py` / `budget.py`; M3 may add `gateway.py`, provider descriptors/configuration, and usage ledger integration.

No provider-specific HTTP client belongs in `bridge.py`.

---

# Locked Contract 1 — ContextItem

`ContextItem` is one bounded, explicit unit of information supplied to an External Brain request.

Required semantic fields:

```python
@dataclass(frozen=True)
class ContextItem:
    kind: ContextKind
    content: str
    path: str | None = None
    priority: int = 0
    content_sha256: str | None = None
```

Locked `ContextKind` V1 values:
- `TASK`
- `CONTRACT`
- `SOURCE`
- `TEST`
- `DIFF`
- `ERROR`
- `ARCHITECTURE`

Rules:
1. `content` is the actual bounded payload sent to the model.
2. `path` is metadata only; it grants no filesystem access.
3. `content_sha256`, when present, is standard SHA-256 of the exact UTF-8 content.
4. `priority` is deterministic context-selection metadata. Higher number = higher retention priority.
5. ContextBuilder M2 determines selection/order/budget. Provider adapters MUST NOT silently append repository files.
6. Secrets, credentials, cookies, auth headers, `.env` values, access tokens, private keys, and raw browser profiles are forbidden context.

---

# Locked Contract 2 — ModelRequest

`ModelRequest` is the only supported logical request boundary between AIOS and an External Brain provider.

Required semantic fields:

```python
@dataclass(frozen=True)
class ModelRequest:
    schema_version: str
    request_id: str
    task_id: str
    role: BrainRole
    operation: BrainOperation
    instruction: str
    context: tuple[ContextItem, ...]
    output_format: BrainOutputType
    provider: str | None = None
    model: str | None = None
    max_input_tokens: int | None = None
    max_output_tokens: int | None = None
```

Locked `schema_version`: `1`

Locked `BrainRole` V1 values:
- `ARCHITECT`
- `CODER`
- `DEBUGGER`
- `REVIEWER`

Locked `BrainOperation` V1 values:
- `PLAN`
- `GENERATE_PATCH`
- `DIAGNOSE_FAILURE`
- `REVIEW_PATCH`

Rules:
1. `request_id` is globally traceable for one External Brain invocation.
2. `task_id` MUST use the current AIOS task identity such as `TASK-014`.
3. `provider` / `model` are optional at the logical contract because v0.7 routing may resolve them later. V0.5 may require explicit provider configuration before Gateway invocation.
4. No credential material is allowed in `ModelRequest`.
5. No filesystem handle, shell handle, browser/session object, Git object, callable tool, or tool schema is allowed in `ModelRequest` V1.
6. `context` order presented to the provider MUST be deterministic after ContextBuilder has finalized it.

---

# Locked Contract 3 — ModelResponse

Every provider result is normalized into one `ModelResponse` before returning to Antigravity/Bridge integration.

Required semantic fields:

```python
@dataclass(frozen=True)
class ModelResponse:
    schema_version: str
    request_id: str
    task_id: str
    provider: str
    model: str
    status: ModelResponseStatus
    output_type: BrainOutputType | None
    content: str | None
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: int | None = None
    provider_request_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
```

Locked `ModelResponseStatus` V1 values:
- `SUCCESS`
- `FAILED`
- `RATE_LIMITED`
- `UNAVAILABLE`
- `TIMEOUT`
- `AUTH_ERROR`
- `INVALID_RESPONSE`

Locked `BrainOutputType` V1 values:
- `PLAN`
- `PATCH_PROPOSAL`
- `DIAGNOSIS`
- `REVIEW`

Rules:
1. `request_id` and `task_id` MUST correlate exactly with the originating request.
2. `SUCCESS` requires non-empty `content` and a non-null valid `output_type` matching the requested operation.
3. Failure statuses MUST NOT masquerade as successful text.
4. Token counts are optional because some subscription/coding endpoints do not expose exact usage. Unknown remains `None`; never fabricate token counts.
5. Provider-specific fields remain behind the adapter and MUST NOT leak into consumers as required fields.
6. Operational provider failures are normalized. They MUST NOT crash or mutate the v0.4 handoff state.

---

# Locked Contract 4 — ProviderAdapter

External Brain providers normalize model semantics; they do not execute repository actions.

Required protocol:

```python
class ProviderAdapter(Protocol):
    @property
    def provider_id(self) -> str: ...

    async def invoke(self, request: ModelRequest) -> ModelResponse: ...
```

Rules:
1. ProviderAdapter maps the logical `ModelRequest` into provider/protocol payloads and normalizes the result.
2. ProviderAdapter MUST NOT read additional project files by itself.
3. ProviderAdapter MUST NOT execute tools, shell commands, browser actions, Git operations, commits, pushes, or writes to the working tree.
4. ProviderAdapter obtains credentials from provider configuration/environment/secure local config, never from task artifacts or `ModelRequest`.
5. ProviderAdapter MUST NOT implement routing among providers in v0.5.
6. ProviderAdapter MUST NOT silently fallback to another provider in v0.5.
7. MiniMax M3 is the intended first M3 proof-of-concept provider; DeepSeek is the intended second compatibility proof. These names do not alter the generic contract.

---

# Locked Contract 5 — ModelTransport

Transport is separated from provider semantics so OpenAI-compatible endpoints can be shared across MiniMax, DeepSeek, Kimi, and future providers without duplicating HTTP clients.

Required behavioral protocol:

```python
class ModelTransport(Protocol):
    async def send(self, request: TransportRequest) -> TransportResult: ...
```

M1 locks the boundary behavior, not a provider-specific wire schema.

`TransportRequest` MUST be able to carry at minimum:
- endpoint/base URL selected by trusted provider configuration;
- request path or operation;
- sanitized headers assembled from trusted provider configuration;
- JSON-compatible payload;
- finite timeout.

`TransportResult` MUST be able to carry at minimum:
- HTTP/status outcome when applicable;
- parsed JSON-compatible response body or bounded raw diagnostic body;
- elapsed time;
- provider request/correlation ID when exposed.

Rules:
1. Authorization headers/API/subscription keys MUST be redacted from logs/errors.
2. Transport MUST use finite connect/read/overall timeout semantics.
3. Transport MUST NOT know AIOS task-routing policy.
4. Transport MUST NOT mutate workspace state.
5. M3 SHOULD implement a generic `OpenAICompatibleTransport` first; provider adapters supply endpoint/model normalization.
6. Anthropic-compatible transport may be added later without changing `ModelRequest`/`ModelResponse`.

---

# Locked Contract 6 — Failure / Safety Contract

External Brain v0.5 is fail-closed with respect to execution authority.

## Operational failure normalization
Gateway/provider boundary MUST distinguish at least:
- authentication/authorization failure -> `AUTH_ERROR`
- HTTP/provider rate limit/quota window -> `RATE_LIMITED`
- finite request timeout -> `TIMEOUT`
- provider/network/service unavailable -> `UNAVAILABLE`
- malformed/unparseable contract output -> `INVALID_RESPONSE`
- other expected provider failure -> `FAILED`

## v0.5 policy
- No automatic cross-provider fallback.
- No model retry loop controlled by another LLM.
- No provider/model auto-routing.
- No external workspace mutation.
- No direct patch application by provider code.
- No commit/push/merge from External Brain.
- A failed External Brain call leaves the current Git branch/worktree and v0.4 authorization unchanged.
- Antigravity may choose to continue using its native reasoning or stop/report the failure, but External Brain itself cannot authorize continuation.

Programming errors/invariant violations may raise internal exceptions during development, but the Gateway integration boundary in M3 MUST normalize expected operational failures to `ModelResponse` and preserve Bridge state.

---

# Locked Output Contract V1

Provider prose is not treated as an executable instruction stream. Each successful operation must conform to a bounded artifact structure.

## PLAN
Required sections:
- `SUMMARY`
- `STEPS`
- `FILES`
- `TESTS`
- `RISKS`

## PATCH_PROPOSAL
Required sections:
- `SUMMARY`
- `FILES`
- `PATCH`
- `TESTS`
- `RISKS`

`PATCH` is proposal data only. Antigravity remains responsible for inspecting/applying edits.

## DIAGNOSIS
Required sections:
- `CAUSE`
- `EVIDENCE`
- `FIX`
- `TESTS`
- `RISKS`

## REVIEW
Required sections:
- `STATUS`
- `FINDINGS`
- `TESTS`
- `RISKS`

Allowed review statuses in V1:
- `PASS`
- `CHANGES_REQUIRED`

M3 parser/validator MUST reject missing required sections as `INVALID_RESPONSE` rather than guessing intent.

---

# Compatibility Invariants

The following are explicitly frozen through v0.5-M1/M2/M3 unless a later ADR supersedes them:

1. `bridge.py` v0.4 TASK/REVIEW sync semantics remain authoritative.
2. RUN/FIX remain explicit human authorization gates.
3. Antigravity remains sole execution authority.
4. Current repository workspace remains the source of truth for edits/tests/git.
5. Runtime control state remains outside the Git worktree.
6. Existing `src.providers.LLMProvider` contract remains unchanged for Python Agent runtime.
7. External Brain contracts live in a separate namespace.
8. No whole-repository dump is the default model context path.
9. Secrets/credentials are never model context.
10. Existing RESULT/review/merge flow remains backward compatible.
11. Existing full repository test suite must remain green after each v0.5 implementation milestone.

---

# M1 Implementation Scope

When the active execution lane is available, M1 code implementation should be deliberately small:

```text
src/aios_bridge/__init__.py
src/aios_bridge/external_brain/__init__.py
src/aios_bridge/external_brain/contracts.py
src/aios_bridge/external_brain/provider.py
src/aios_bridge/external_brain/transport.py
src/aios_bridge/external_brain/errors.py

tests/aios_bridge/external_brain/test_contracts.py
tests/aios_bridge/external_brain/test_provider_contract.py
tests/aios_bridge/external_brain/test_transport_contract.py
```

M1 MUST NOT implement a live external model call.
M1 MUST NOT modify Antigravity execution behavior.
M1 MUST NOT add model routing/fallback.

---

# M1 Acceptance Criteria

M1 implementation is accepted only when all are true:

1. Frozen/enumerated contract values above exist and serialize deterministically.
2. `ContextItem`, `ModelRequest`, and `ModelResponse` validate required invariants.
3. Request/response correlation mismatch is rejected.
4. `SUCCESS` with empty content or missing/mismatched output type is rejected.
5. Failure responses can represent unknown token usage without fabrication.
6. `ProviderAdapter` is a structural protocol/interface with no workspace authority.
7. `ModelTransport` is isolated from AIOS routing/task policy.
8. Existing `src.providers.LLMProvider` / `GeminiProvider` are untouched.
9. `bridge.py` zero-touch authorization, handoff, sync, publish, and Git branch behavior are untouched in M1.
10. Focused new tests pass.
11. Full existing repository suite passes with zero regression.

---

# Explicit Non-Goals

Not in M1:
- ContextBuilder implementation
- token estimation/trimming
- ModelGateway implementation
- MiniMax live provider
- DeepSeek live provider
- Kimi provider
- provider registry
- rule-based router
- quota registry
- automatic fallback
- MCP server
- external filesystem/shell/git/browser tools
- concurrent workers/worktrees
- model-controlled commits or pushes

These are intentionally deferred so v0.5 can grow toward v0.6/v0.7 without weakening v0.4 safety.

---

# Forward Compatibility

Expected evolution without breaking M1 contracts:

```text
v0.5-M1  contracts only
    |
v0.5-M2  deterministic ContextBuilder + budget
    |
v0.5-M3  ModelGateway + OpenAICompatibleTransport + MiniMax M3 POC
    |
v0.5-M3b DeepSeek compatibility proof
    |
v0.6     Kimi + ProviderRegistry
    |
v0.7     rule router + quota awareness + explicit fallback policy
    |
v1.x     AIOS Control Plane / multi-worker architecture
```

Any future feature that requires giving an external model direct workspace execution authority requires a separate ADR and MUST NOT be introduced as a silent extension of this contract.
