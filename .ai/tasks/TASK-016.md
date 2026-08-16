# TASK-016 — AIOS Bridge v0.5-M3 ModelGateway + OpenAI-Compatible Transport + MiniMax Provider + Usage Ledger

## Objective
Implement **AIOS Bridge v0.5-M3** exactly as locked in:

`.ai/decisions/ADR-007-AIOS-BRIDGE-V0.5-M3-GATEWAY-MINIMAX-USAGE-CONTRACT-LOCK.md`

Canonical baseline when authored:
- `main`: `4f5fafc4f9c4f16413d3e4e2d13adc856509bde9`
- v0.5-M1: merged / APPROVED
- v0.5-M2: merged / APPROVED
- ADR-005 / ADR-006 / ADR-007: LOCKED

M3 is the first real external-model inference path. It must remain proposal-only and must not change Antigravity's sole execution authority.

```text
ContextBuildResult (M2)
        |
        v
ModelRequest
        |
        v
ModelGateway
        |
        v
MiniMaxOpenAIProvider
        |
        v
OpenAICompatibleTransport
        |
        v
MiniMax-M3
        |
        v
normalized + validated ModelResponse
        |
        +--> UsageRecord / optional UsageLedger
        |
        v
GatewayResult
```

---

# Implementation Scope

Prefer additive files:

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

Tests should be added under:

```text
tests/aios_bridge/external_brain/
```

Small exports from `src/aios_bridge/external_brain/__init__.py` are allowed.

Do not place this implementation under the existing Python Agent runtime namespace `src/providers/`.

---

# M3.1 — Deterministic Prompt Renderer

Implement a provider-neutral deterministic message renderer for `ModelRequest`.

Requirements:
- includes `role`, `operation`, `instruction`, `output_format`, required artifact sections, and proposal-only authority wording;
- reuses M2 `render_context_item()` for every selected context item;
- does not silently read or append files;
- does not add tools/function schemas;
- does not include credentials;
- equivalent request -> equivalent message payload;
- include focused snapshot/structural tests.

The model is a Brain only. Prompt wording must not authorize filesystem, shell, browser, Git, commit, merge, or patch application.

---

# M3.2 — OpenAICompatibleTransport

Implement a concrete `OpenAICompatibleTransport` satisfying existing M1 `ModelTransport`.

Required behavior:
- one JSON HTTP POST per `send()`;
- no retry;
- finite connect/read timeout plus finite overall async bound;
- parse JSON when possible;
- bound non-JSON diagnostic text;
- return `TransportResult` with status/body/latency/provider request ID;
- never leak Authorization/API key in exception strings, repr, logs, or diagnostics;
- do not log full request headers;
- no MiniMax-specific response-code mapping inside transport;
- no provider routing;
- no new OpenAI SDK dependency.

Use existing `requests` dependency or standard library. If using `requests` behind async protocol, `asyncio.to_thread()` + `asyncio.wait_for()` is acceptable.

Tests:
- use mocks/fakes or local test HTTP server only;
- verify one-call behavior;
- verify timeout normalization;
- verify JSON and bounded non-JSON body handling;
- verify no secret leakage;
- verify no retry.

---

# M3.3 — MiniMaxOpenAIProvider

Implement `MiniMaxOpenAIProvider(ProviderAdapter)` with:

```text
provider_id = minimax
base_url    = https://api.minimax.io/v1
path        = /chat/completions
default model = MiniMax-M3
```

Model ID must remain configurable.

Credential:
- dedicated env/local input, preferably `AIOS_MINIMAX_API_KEY`;
- no key-prefix assumptions;
- private/in-memory only;
- not serialized, logged, repr'd, stored in usage record, RESULT, or tests.

MiniMax payload V1:
- `model` = configured model;
- deterministic `messages` from M3.1;
- `stream = false`;
- `reasoning_split = true`;
- `ModelRequest.max_output_tokens` -> `max_completion_tokens`;
- no `tools`;
- no deprecated `max_tokens`;
- do not send `service_tier=priority`;
- no router-controlled temperature/thinking policy in M3.

Reasoning safety:
- parse/use only final artifact content;
- ignore/discard `reasoning_content`, `reasoning_details`, or separated thinking data;
- do not place reasoning in `ModelResponse.content`, usage ledger, RESULT, or error artifacts;
- if final content cannot be separated safely, return `INVALID_RESPONSE`.

Response parsing:
- inspect HTTP result + MiniMax `base_resp` if present;
- use response `id` as provider request ID when present;
- map provider `usage.prompt_tokens` / `usage.completion_tokens` to M1 usage fields;
- unknown usage stays `None`;
- `finish_reason=length` => `INVALID_RESPONSE` / truncated-output error, never SUCCESS.

Minimum normalized error mapping:
- HTTP 401/403, MiniMax 1004/2049 -> `AUTH_ERROR`;
- HTTP 429, MiniMax 1002/2056 -> `RATE_LIMITED`;
- timeout / MiniMax 1001 -> `TIMEOUT`;
- network/HTTP 5xx, MiniMax 1000/1024/1033 -> `UNAVAILABLE`;
- malformed response -> `INVALID_RESPONSE`;
- remaining parameter/content/token-limit/balance class failures -> `FAILED` unless a locked specific status applies.

No retry and no fallback.

---

# M3.4 — ModelGateway

Implement a single-provider gateway:

```python
async def invoke(
    request: ModelRequest,
    *,
    context_build: ContextBuildResult | None = None,
) -> GatewayResult:
    ...
```

Required sequence:
1. validate configured provider/request provider compatibility;
2. if `context_build` supplied, require exact equality with `request.context`;
3. invoke configured provider exactly once;
4. validate request/response correlation;
5. on provider `SUCCESS`, run M1 `validate_artifact_structure()`;
6. convert malformed correlation/output into normalized `INVALID_RESPONSE` while preserving safe usage/latency/provider IDs;
7. build UsageRecord;
8. append to optional ledger once;
9. return GatewayResult.

No routing, classifier, provider registry, retry, or fallback.

Provider/model mismatch or context correlation mismatch must fail before any network call.

---

# M3.5 — UsageRecord + UsageLedger

Implement immutable `UsageRecord` per ADR-007.

Required fields include:
- request/task/provider/model/status;
- provider input/output tokens;
- optional provider reasoning/cached token details;
- latency/provider request ID;
- optional M2 context fingerprint/count/counter/exactness;
- normalized `error_code` only.

Forbidden in usage record:
- prompt;
- instruction;
- context content;
- output content;
- raw request/response bodies;
- auth headers;
- API keys;
- cookies;
- raw secret-bearing errors.

Implement `UsageLedger` protocol and a simple append-only local concrete ledger such as `JsonlUsageLedger`.

Ledger path requirements:
- explicit caller-supplied path;
- no default inside repository/worktree;
- tests use temporary directory;
- append + flush, preferably fsync;
- failure MUST NOT trigger provider re-invocation.

`GatewayResult` must expose whether ledger persistence succeeded, failed, or was disabled as locked by ADR-007.

---

# M3.6 — Optional Manual MiniMax Smoke Entrypoint

A small manual smoke command/script is allowed and encouraged if it remains isolated.

Rules:
- never runs during normal pytest/full suite;
- explicitly reads `AIOS_MINIMAX_API_KEY`;
- default model `MiniMax-M3`, optional `AIOS_MINIMAX_MODEL` override;
- sends only a tiny synthetic TASK/CONTRACT context;
- performs one bounded PLAN request;
- prints normalized status/model/token counts/provider request ID, not key and not hidden reasoning;
- does not crawl repo or apply patch;
- is diagnostic only, not Antigravity integration.

Do not require a live MiniMax call for CI acceptance because the repository must remain testable without user credentials.

---

# Failure / Safety Invariants

1. External Brain never receives tool/workspace execution authority.
2. No provider call can modify repository/worktree.
3. No provider call authorizes RUN/FIX/merge.
4. No external call happens on provider mismatch or M2 context mismatch.
5. No auto retry.
6. No cross-provider fallback.
7. No live external call in automated tests.
8. Expected network/auth/rate/timeout/provider failures become normalized model outcomes, not bridge-state mutations.
9. A ledger write failure never repeats a completed external inference.
10. Credentials never appear in control-plane artifacts or model context.
11. Hidden/provider reasoning is not persisted as artifact content.
12. Existing `bridge.py` / authorization/handoff/publish semantics remain untouched.
13. Existing `src.providers.LLMProvider` / GeminiProvider semantics remain untouched.

---

# Mandatory Tests

Add focused tests covering at least:

## Prompt
- deterministic message rendering;
- exact M2 context framing reuse;
- no tools/execution authority;
- required output sections present.

## Transport
- JSON POST success;
- JSON parse;
- non-JSON bounded diagnostic;
- timeout;
- unavailable/network error;
- no retry;
- secret header never exposed.

## MiniMax Provider
- exact payload fields (`model`, `messages`, `stream=false`, `reasoning_split=true`);
- `max_completion_tokens` mapping;
- no `tools`, no `service_tier=priority`, no deprecated `max_tokens`;
- success parse;
- reasoning fields discarded;
- provider request ID parse;
- usage parse;
- unknown usage remains None;
- auth/rate/timeout/unavailable/base_resp mappings;
- malformed choice/content -> INVALID_RESPONSE;
- finish_reason length -> INVALID_RESPONSE;
- API key not present in repr/errors/records.

## Gateway
- provider invoked exactly once;
- provider mismatch -> zero calls;
- context_build mismatch -> zero calls;
- SUCCESS structural validation;
- malformed artifact -> INVALID_RESPONSE;
- correlation mismatch -> INVALID_RESPONSE;
- no retry after provider failure;
- ledger write exactly once;
- ledger failure does not cause second provider call;
- GatewayResult still exposes completed response on ledger failure.

## Usage
- immutable record;
- provider usage and M2 estimate remain separately labeled;
- no content/secrets in serialized record;
- JSONL append works in tmp directory;
- malformed token fields rejected.

---

# Non-Goals

Do not implement:
- DeepSeek/Kimi/GLM adapters;
- ProviderRegistry;
- smart router/task classifier;
- automatic fallback;
- model retry policy;
- quota polling/remains API;
- token-plan route selection;
- embeddings/vector search;
- repo context discovery;
- truncation/excerpting;
- Antigravity MCP/tool integration;
- patch application;
- shell/browser/Git execution;
- changes to Python Agent runtime provider abstraction;
- changes to AIOS Bridge v0.4 handoff/authorization/publish logic.

---

# Acceptance Criteria

TASK-016 is ready for review only when:
1. ADR-007 is implemented without weakening ADR-005/006.
2. Focused M3 tests pass.
3. Existing External Brain M1/M2 tests remain green.
4. Existing bridge tests remain green.
5. Full repository suite passes with zero regressions.
6. No automated live MiniMax request occurs during tests.
7. Diff is limited to External Brain M3 modules/tests plus RESULT artifact and optional manual smoke script.
8. No protected subsystem is modified.
9. RESULT-016 records exact branch head, changed files, test counts, and whether any manual smoke was run.
10. If no live smoke is run because credentials are unavailable, RESULT must explicitly say `LIVE_SMOKE: NOT_RUN` rather than claiming provider connectivity.

## Review Focus
Reviewer must especially inspect:
- accidental double calls/retries;
- API-key leakage through repr/errors/ledger;
- hidden reasoning leakage into artifact content;
- provider status mapping;
- output validation before SUCCESS;
- ledger failure behavior;
- provider usage vs M2 estimate labeling;
- worktree/runtime boundary;
- scope creep toward routing or Antigravity execution.
