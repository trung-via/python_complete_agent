# ADR-007 — AIOS Bridge v0.5-M3 ModelGateway + OpenAI-Compatible Transport + MiniMax Provider + Usage Ledger

## Status
LOCKED

## Date
2026-08-16

## Preconditions
- ADR-005 / v0.5-M1 External Brain contracts: LOCKED and merged.
- ADR-006 / v0.5-M2 deterministic ContextBuilder + Token Budget: LOCKED and merged.
- Canonical `main` at lock time: `4f5fafc4f9c4f16413d3e4e2d13adc856509bde9`.
- Antigravity remains the sole workspace executor.

## Objective
M3 creates the first real external-model inference path while preserving the v0.4 human approval / handoff workflow and M1/M2 authority boundaries.

```text
M2 ContextBuildResult
        |
        v
ModelRequest
        |
        v
ModelGateway (single configured provider; NO router)
        |
        v
MiniMaxOpenAIProvider
        |
        v
OpenAICompatibleTransport
        |
        v
MiniMax OpenAI Chat Completions API
        |
        v
normalized ModelResponse
        |
        +--> structural output validation
        +--> UsageRecord / UsageLedger
        |
        v
GatewayResult
```

External Brain remains **proposal-only**. M3 does not apply patches, execute tools, browse, run shell commands, mutate the repository, commit, push, merge, or authorize continuation.

---

# Decision 1 — Preserve M1/M2 Contracts

M3 MUST NOT semantically redesign:
- `ContextItem`
- `ModelRequest`
- `ModelResponse`
- `ProviderAdapter`
- `ModelTransport`
- `TransportRequest` / `TransportResult`
- M1 output artifact validators
- M2 `ContextBuilder`, `ContextBudget`, or `ContextBuildResult`

Additive modules are preferred:

```text
src/aios_bridge/external_brain/
├── gateway.py
├── prompt.py
├── usage.py
├── providers/
│   ├── __init__.py
│   └── minimax.py
└── transports/
    ├── __init__.py
    └── openai_compatible.py
```

Small exports from `external_brain/__init__.py` are allowed.

---

# Decision 2 — ModelGateway is Single-Provider Orchestration Only

Required semantic API:

```python
class ModelGateway:
    async def invoke(
        self,
        request: ModelRequest,
        *,
        context_build: ContextBuildResult | None = None,
    ) -> GatewayResult:
        ...
```

V0.5 rules:
1. Exactly one `ProviderAdapter` is injected/configured for a gateway instance.
2. No provider registry.
3. No task classifier.
4. No automatic routing.
5. No cross-provider fallback.
6. No retry loop.
7. No LLM-driven retry/routing decision.
8. A provider is invoked at most once per `ModelGateway.invoke()` call.
9. If `request.provider` is set, it must match the configured adapter's `provider_id`; mismatch fails before any external call.
10. Provider/model configuration is trusted local configuration, never model-supplied authority.

Expected operational failures return normalized failure `ModelResponse` data inside `GatewayResult`; invariant/programming errors may still raise.

---

# Decision 3 — GatewayResult Prevents Accidental Re-Invocation After Ledger Failure

Required semantic contract:

```python
@dataclass(frozen=True)
class GatewayResult:
    response: ModelResponse
    usage_record: UsageRecord
    ledger_persisted: bool | None
    ledger_error_code: str | None = None
```

Semantics:
- `ledger_persisted=True`: configured ledger write succeeded.
- `ledger_persisted=False`: configured ledger write failed after the provider outcome was already obtained.
- `ledger_persisted=None`: no ledger configured.
- A ledger failure MUST NOT cause the provider/model call to be repeated.
- The completed `ModelResponse` remains available even when ledger persistence fails.
- `ledger_error_code` contains a bounded internal code only; it MUST NOT expose secrets, headers, request/response content, or raw credentials.

This wrapper is additive and does not alter the M1 `ProviderAdapter.invoke() -> ModelResponse` contract.

---

# Decision 4 — M2 Correlation into M3 Usage

When `context_build` is supplied to the gateway:
1. `tuple(request.context)` MUST exactly equal `context_build.selected`.
2. A mismatch fails before any external call.
3. The gateway records M2 audit metadata separately from provider-reported token usage.
4. M2 estimated counts MUST NOT be relabeled as provider token usage.

When `context_build` is absent, M3 may still invoke a valid `ModelRequest`; M2 audit fields remain `None`.

---

# Decision 5 — Deterministic Provider-Neutral Prompt Rendering

Add one deterministic helper, conceptually:

```python
def render_model_messages(request: ModelRequest) -> tuple[dict[str, str], ...]:
    ...
```

Requirements:
- deterministic for the same `ModelRequest`;
- include request role, operation, instruction, requested output type, and required output sections;
- serialize context using M2 `render_context_item()` rather than inventing a second context framing;
- do not read additional files;
- do not add hidden repository context;
- do not include secrets/credentials;
- do not include callable tools or tool schemas;
- explicitly state proposal-only / no execution authority;
- require the model to emit only the requested artifact structure.

No provider adapter may silently append repo files or hidden task context.

---

# Decision 6 — Generic OpenAI-Compatible Transport

Implement `OpenAICompatibleTransport(ModelTransport)` as a generic JSON-over-HTTP POST transport.

Requirements:
1. It consumes existing immutable `TransportRequest` and returns `TransportResult`.
2. It performs one HTTP POST only; no retries.
3. No provider routing or MiniMax-specific status mapping inside the transport.
4. Use finite connect/read bounds and a finite overall async wait bound derived from `TransportRequest.timeout_seconds`.
5. HTTP/network timeout becomes a transport timeout exception/status consumable by the provider.
6. DNS/connect/network/provider-unavailable errors are distinguishable from timeout where practical.
7. Parse JSON responses when possible.
8. If a response body is not JSON, keep only a bounded diagnostic raw text body; do not retain an unbounded body.
9. Capture a provider request/correlation ID from standard response headers if available.
10. Never include Authorization/API-key header values in exceptions, logs, reprs, or diagnostic bodies.
11. No logging of full request headers.
12. No automatic HTTP retry.
13. No new provider SDK is required.

The repository already has `requests`; M3 SHOULD avoid adding an OpenAI SDK merely to issue this request.

Because `ModelTransport.send()` is async while `requests` is synchronous, an implementation may use `asyncio.to_thread()` plus `asyncio.wait_for()` as long as the observable call has finite bounds and no retry behavior.

---

# Decision 7 — MiniMax Provider Configuration

Implement a dedicated `MiniMaxOpenAIProvider(ProviderAdapter)` outside `src/providers/`.

Locked provider identity:

```text
provider_id = "minimax"
```

Default official configuration:

```text
base_url = https://api.minimax.io/v1
path     = /chat/completions
model    = MiniMax-M3
```

The exact model ID MUST remain configurable. `MiniMax-M3` is the M3 default, not an architectural constant.

Credential rules:
- use a dedicated local environment/config credential such as `AIOS_MINIMAX_API_KEY`;
- Token Plan keys and pay-as-you-go keys are both credentials; M3 does not infer billing mode from key prefix;
- do not validate or depend on a particular secret prefix;
- never store the API key in `ModelRequest`, `ContextItem`, RESULT, REVIEW, usage ledger, exception text, repr, git artifact, or test fixture output;
- tests use fake credentials only.

A small provider config dataclass may contain non-secret values such as base URL, model ID, and timeout. If an API key is held by a provider object, it must be a private field and excluded from repr/serialization.

---

# Decision 8 — MiniMax OpenAI-Compatible Request Mapping

MiniMax request payload for V1:

```text
POST /v1/chat/completions
Authorization: Bearer <secret>
Content-Type: application/json
```

Payload semantics:
- `model`: configured model ID;
- `messages`: deterministic rendered messages from Decision 5;
- `stream`: `false`;
- `reasoning_split`: `true` for MiniMax so thinking/reasoning is separated from final response content;
- if `ModelRequest.max_output_tokens` is supplied, map it to `max_completion_tokens` (not deprecated `max_tokens`);
- do NOT send tools/function schemas;
- do NOT set `service_tier=priority`; use standard behavior / omit the field in v0.5;
- temperature/top_p/thinking policy are not router-controlled in M3; prefer provider defaults unless a narrowly justified static provider config is added.

Important safety/contract rule:
- The adapter MUST parse and validate only final answer content intended for the artifact.
- `reasoning_content`, `reasoning_details`, `<think>` blocks, or equivalent provider reasoning must not be returned as `ModelResponse.content`, written to the usage ledger, or exposed as an AIOS artifact.
- If provider formatting causes reasoning and final output to be inseparable, normalize conservatively or return `INVALID_RESPONSE`; do not persist hidden reasoning.

---

# Decision 9 — MiniMax Response / Error Normalization

On HTTP success, inspect both the OpenAI-compatible response shape and MiniMax `base_resp` when present.

Success requires at least:
- HTTP success status;
- MiniMax `base_resp.status_code` absent or `0`;
- exactly usable first choice;
- non-empty final `message.content` after reasoning separation;
- no structural/provider parse contradiction.

Use provider response `id` as `provider_request_id` when present, otherwise transport correlation ID.

Provider token usage mapping:
- `usage.prompt_tokens` -> `ModelResponse.input_tokens`;
- `usage.completion_tokens` -> `ModelResponse.output_tokens`;
- unknown values remain `None`;
- do not fabricate token counts.

Normalized failures must include bounded provider-specific `error_code` metadata without leaking credentials or full prompt/content.

Minimum MiniMax mapping:
- auth failures / HTTP 401/403 / MiniMax 1004 or 2049 -> `AUTH_ERROR`;
- HTTP 429 / MiniMax 1002 or 2056 -> `RATE_LIMITED`;
- HTTP/request timeout / MiniMax 1001 -> `TIMEOUT`;
- transport/network unavailable / HTTP 5xx / MiniMax provider/internal errors such as 1000, 1024, 1033 -> `UNAVAILABLE`;
- malformed JSON/choices/content shape -> `INVALID_RESPONSE`;
- parameter/content/token-limit/balance class failures not covered above -> `FAILED` unless a more specific locked status applies.

`finish_reason == "length"` MUST NOT be accepted as a successful patch/review artifact merely because some text exists; normalize to `INVALID_RESPONSE` / output-truncated failure.

No retry is performed by the provider or gateway in M3.

---

# Decision 10 — Structural Output Validation Lives at the Gateway Boundary

After provider normalization:
1. Validate request/response correlation with the M1 helper.
2. On `SUCCESS`, run M1 `validate_artifact_structure(response.output_type, response.content)`.
3. If correlation/output structure fails, convert the outcome to normalized `INVALID_RESPONSE` while preserving provider/model/request/task/usage/latency/request-ID metadata where safe.
4. Do not apply or execute PATCH_PROPOSAL content.
5. Never convert malformed content into success by guessing missing sections.

---

# Decision 11 — UsageRecord Separates Provider Usage from M2 Budget Estimates

Required semantic record:

```python
@dataclass(frozen=True)
class UsageRecord:
    schema_version: str
    timestamp_utc: str
    request_id: str
    task_id: str
    provider: str
    requested_model: str | None
    actual_model: str
    status: ModelResponseStatus
    provider_input_tokens: int | None
    provider_output_tokens: int | None
    provider_reasoning_tokens: int | None
    provider_cached_tokens: int | None
    latency_ms: int | None
    provider_request_id: str | None
    context_fingerprint: str | None
    context_counted_tokens: int | None
    context_counter_id: str | None
    context_count_is_exact: bool | None
    error_code: str | None
```

Rules:
- no prompt/instruction/context/output content;
- no API key, Authorization header, cookies, raw request/response body, or error body;
- `provider_*_tokens` come only from provider-reported usage when available;
- `context_counted_tokens` comes from M2 and remains separately labeled;
- unknown values remain `None`;
- timestamps use timezone-aware UTC ISO-8601;
- token fields reject booleans/negative values.

Provider-specific optional usage details such as cached/reasoning tokens may be extracted when present but MUST remain optional.

---

# Decision 12 — UsageLedger is Explicit, Append-Only, and Outside the Worktree

Required protocol:

```python
class UsageLedger(Protocol):
    def append(self, record: UsageRecord) -> None: ...
```

Implement a simple local append-only ledger such as `JsonlUsageLedger` with an **explicit caller-supplied path**.

Rules:
1. M3 MUST NOT choose the repository worktree as a default ledger path.
2. No implicit `.ai/usage` file is written into the task branch/worktree.
3. Tests use temporary directories.
4. Append one bounded JSON record per invocation outcome.
5. Flush after append; `fsync` is preferred for the local durable implementation.
6. A ledger write failure does not trigger another provider call.
7. GatewayResult exposes persistence failure.
8. Ledger records never contain model prompt/output content or secrets.

M4 may wire this explicit path to the existing AIOS runtime directory outside the worktree without changing M3 contracts.

---

# Decision 13 — Optional Live Smoke Path, Never Automatic in Tests

M3 may add a small manual smoke entrypoint/script for a single bounded PLAN request.

Rules:
- it runs only when explicitly invoked by the user/operator;
- requires `AIOS_MINIMAX_API_KEY` from environment;
- default model may be `MiniMax-M3` but can be overridden by `AIOS_MINIMAX_MODEL`;
- uses tiny synthetic/non-secret context;
- no repository crawling;
- no patch application;
- no automated CI/full-suite live call;
- no key/value printed;
- exit status distinguishes success vs normalized failure;
- the smoke path is diagnostic only and is not Antigravity integration.

---

# Decision 14 — Explicit Non-Goals for M3

M3 MUST NOT add:
- ProviderRegistry;
- DeepSeek/Kimi/GLM provider implementations;
- task classifier;
- smart routing;
- auto fallback;
- retry policy for model calls;
- quota-based route selection;
- automatic Token Plan remaining-quota polling;
- MCP/tool execution authority;
- Antigravity workspace-edit integration;
- repo scan/context discovery;
- embeddings/vector retrieval;
- automatic patch application;
- shell/browser/Git execution by the external model;
- modifications to v0.4 `bridge.py` control/authorization/handoff/publish semantics;
- modifications to existing Python Agent `src.providers.LLMProvider` semantics.

DeepSeek compatibility proof remains M3b after this provider path is accepted.

---

# Acceptance Criteria

M3 is accepted only when all are true:

1. Existing M1/M2 contracts remain backward compatible.
2. ModelGateway uses exactly one injected provider and performs no routing/fallback/retry.
3. Provider is invoked at most once per gateway invocation.
4. Provider mismatch fails before network call.
5. `context_build` mismatch with `request.context` fails before network call.
6. Prompt rendering is deterministic and reuses M2 context framing.
7. Prompt contains no tools and grants no execution authority.
8. OpenAICompatibleTransport performs one bounded JSON POST with no retry.
9. Transport redacts/never exposes Authorization secrets in errors/logs.
10. Non-JSON diagnostic bodies are bounded.
11. MiniMax provider defaults to official OpenAI-compatible endpoint and `MiniMax-M3`, with configurable model ID.
12. MiniMax credential is never serialized/logged/committed.
13. MiniMax payload uses `stream=false`, `reasoning_split=true`, no tools, no priority service tier.
14. `max_output_tokens` maps to `max_completion_tokens`.
15. Reasoning/thinking fields are never surfaced as ModelResponse artifact content or usage-ledger content.
16. MiniMax HTTP/base_resp/auth/rate/timeout/unavailable/malformed failures are normalized per ADR.
17. `finish_reason=length` is not accepted as success.
18. Provider prompt/completion usage maps to ModelResponse when present; unknown stays None.
19. Gateway validates correlation and M1 artifact structure before final SUCCESS.
20. Invalid structured output becomes `INVALID_RESPONSE`, not SUCCESS.
21. UsageRecord contains no prompt/output/secrets and separates provider usage from M2 estimate.
22. UsageLedger path is explicit and outside-worktree by caller choice; tests use tmp paths.
23. Ledger persistence failure never re-invokes provider and is visible in GatewayResult.
24. No live external call runs in normal automated tests.
25. Optional manual smoke path, if implemented, is explicit and secret-safe.
26. No changes to `bridge.py`, AgentLoop/browser/Product Source Pack semantics, or existing runtime `src.providers.LLMProvider`.
27. Focused M3 tests pass.
28. Full repository suite passes with zero regression.

---

# Forward Path

```text
v0.5-M1 contracts
    -> v0.5-M2 deterministic context/budget
    -> v0.5-M3 gateway + transport + MiniMax provider + usage ledger  [THIS ADR]
    -> v0.5-M3b DeepSeek compatibility proof
    -> v0.5-M4 Antigravity tool/handoff integration
    -> v0.6 Kimi + ProviderRegistry
    -> v0.7 deterministic task router + quota policy + explicit fallback
    -> v1.x multi-worker control plane
```
