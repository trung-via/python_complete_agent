# TASK-014 — AIOS Bridge v0.5-M1 External Brain Contract Implementation

## Objective
Implement the **contract-only foundation** for AIOS Bridge v0.5 External Brain exactly as locked in:

`.ai/decisions/ADR-005-AIOS-BRIDGE-V0.5-EXTERNAL-BRAIN-CONTRACT-LOCK.md`

This task creates the typed, validated, test-covered boundary for future external-model use while preserving the existing AIOS Bridge v0.4 Zero-Touch Handoff unchanged.

Canonical baseline when authored:
- `main`: `540f4cb20b56cf72db333192d49ccf6eb295e9c4`
- TASK-013 is already present on `main` at its approved reviewed head
- AIOS Bridge v0.4 remains authoritative for TASK/REVIEW sync, RUN/FIX authorization, branch safety, publish, RESULT, and review handoff
- ADR-005 status: `LOCKED`

Target architecture boundary:

```text
TASK / REVIEW
    |
    v
AIOS Bridge v0.4 control + authorization
    |
    v
Antigravity (SOLE EXECUTOR)
    |
    +--> External Brain contracts (TASK-014)
              |
              +--> future ContextBuilder (M2)
              +--> future ModelGateway (M3)
              +--> future ProviderAdapter implementation (M3)
              +--> future ModelTransport implementation (M3)
```

TASK-014 MUST NOT make live external-model calls.

---

## Core Invariants

1. **External Brain = Brain only.**
   No filesystem, shell, browser, Git, commit, push, merge, or tool execution authority.

2. **Antigravity remains the sole executor.**
   External Brain outputs are proposal artifacts only.

3. **Do not modify v0.4 handoff semantics.**
   `bridge.py` RUN/FIX authorization, sync, branch preparation, publish, RESULT, and review behavior remain unchanged.

4. **Do not overload the existing Python Agent LLM provider contract.**
   `src/providers/base.py::LLMProvider` and `LLMResponse` remain untouched. They serve the Python Agent runtime and tool-calling loop, not External Brain.

5. **External Brain lives in a separate namespace.**

Suggested package:

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

6. **No provider-specific HTTP client in `bridge.py`.**

7. **No routing/fallback in M1.**

---

# M1.1 — Contract Enums / Value Objects

Implement frozen/enumerated V1 contract values from ADR-005.

## `ContextKind`
Required values:
- `TASK`
- `CONTRACT`
- `SOURCE`
- `TEST`
- `DIFF`
- `ERROR`
- `ARCHITECTURE`

## `BrainRole`
Required values:
- `ARCHITECT`
- `CODER`
- `DEBUGGER`
- `REVIEWER`

## `BrainOperation`
Required values:
- `PLAN`
- `GENERATE_PATCH`
- `DIAGNOSE_FAILURE`
- `REVIEW_PATCH`

## `BrainOutputType`
Required values:
- `PLAN`
- `PATCH_PROPOSAL`
- `DIAGNOSIS`
- `REVIEW`

## `ModelResponseStatus`
Required values:
- `SUCCESS`
- `FAILED`
- `RATE_LIMITED`
- `UNAVAILABLE`
- `TIMEOUT`
- `AUTH_ERROR`
- `INVALID_RESPONSE`

Use stable serialized string values. Do not rely on Python enum ordinal values.

---

# M1.2 — `ContextItem`

Implement an immutable dataclass/value object equivalent to:

```python
@dataclass(frozen=True)
class ContextItem:
    kind: ContextKind
    content: str
    path: str | None = None
    priority: int = 0
    content_sha256: str | None = None
```

Requirements:
- immutable/frozen;
- `content` must be a string and must not be `None`;
- reject invalid enum values at construction/validation boundary;
- if `content_sha256` is provided, validate standard lowercase/uppercase hex SHA-256 shape (64 hex chars) but do not require automatic hashing in M1;
- `path` is metadata only and MUST NOT imply filesystem access;
- deterministic serialization;
- no hidden provider-specific fields.

Do not implement ContextBuilder or secret scanning in M1. The contract must only support those future layers cleanly.

---

# M1.3 — `ModelRequest`

Implement an immutable request contract equivalent to:

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

Locked schema version:

```text
1
```

Validation requirements:
- `schema_version == "1"`;
- `request_id` is non-empty;
- `task_id` must follow AIOS task identity form `TASK-<digits>`; accept zero-padded values such as `TASK-014`;
- `instruction` is non-empty after trimming;
- `context` is immutable/deterministic (`tuple` or equivalent frozen collection);
- optional token limits, when present, must be positive integers;
- no credential fields;
- no tools/tool schemas/callables/session objects;
- provider/model may remain `None` at logical contract level for future routing compatibility.

## Operation → expected output mapping

Lock this mapping in one explicit helper/validator, not scattered conditionals:

```text
PLAN              -> PLAN
GENERATE_PATCH    -> PATCH_PROPOSAL
DIAGNOSE_FAILURE  -> DIAGNOSIS
REVIEW_PATCH      -> REVIEW
```

A request whose `output_format` does not match its operation must be rejected.

---

# M1.4 — `ModelResponse`

Implement an immutable response contract equivalent to:

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

Validation requirements:
- schema version is exactly `"1"`;
- request/task/provider/model identity fields are non-empty where required;
- `SUCCESS` requires:
  - non-null valid `output_type`;
  - non-empty `content` after trimming;
  - no contradictory required failure state;
- non-success statuses may have `output_type=None` and `content=None`;
- token counts, when present, must be non-negative integers;
- `latency_ms`, when present, must be non-negative;
- unknown usage remains `None`; MUST NOT fabricate `0` merely because provider omitted usage;
- provider-specific response fields are not added to the logical contract.

Implement a correlation validator/helper that can assert a `ModelResponse` belongs to a specific `ModelRequest`:
- request IDs match exactly;
- task IDs match exactly;
- successful `output_type` matches the request's expected output type.

Correlation mismatch MUST be rejected deterministically.

---

# M1.5 — `ProviderAdapter` Protocol

Create an External Brain provider protocol separate from `src.providers.LLMProvider`.

Required shape:

```python
class ProviderAdapter(Protocol):
    @property
    def provider_id(self) -> str: ...

    async def invoke(self, request: ModelRequest) -> ModelResponse: ...
```

Requirements:
- type/protocol only in M1;
- no live provider implementation;
- no file reads;
- no shell/browser/Git/tool execution;
- no provider fallback;
- no router;
- no mutation of v0.4 Bridge state;
- no imports from MiniMax/DeepSeek/Kimi SDKs.

A small deterministic fake provider may exist only under tests if useful.

---

# M1.6 — `ModelTransport` Protocol

Create transport-boundary data contracts/protocols sufficient for M3 without implementing networking.

Required conceptual protocol:

```python
class ModelTransport(Protocol):
    async def send(self, request: TransportRequest) -> TransportResult: ...
```

`TransportRequest` must support at minimum:
- trusted endpoint/base URL;
- request path/operation;
- sanitized headers mapping;
- JSON-compatible payload;
- finite timeout.

`TransportResult` must support at minimum:
- HTTP/status code when applicable;
- parsed JSON-compatible body OR bounded diagnostic body representation;
- elapsed/latency time;
- provider request/correlation ID when exposed.

Requirements:
- immutable where practical;
- finite timeout must be positive;
- do not add routing policy;
- do not add model-selection policy;
- do not add retries/fallback in M1;
- do not implement HTTP calls;
- names should remain generic enough for future OpenAI-compatible and Anthropic-compatible transports.

M3 is expected to implement `OpenAICompatibleTransport` from this boundary without changing `ModelRequest` or `ModelResponse`.

---

# M1.7 — Error Taxonomy

Add a small External Brain error taxonomy for programmer/contract validation boundaries, separate from normalized provider operational statuses.

Suggested minimum concepts:
- contract validation error;
- request/response correlation error;
- output contract error.

Do not create a giant exception hierarchy.

Expected operational provider failures in M3 will normalize to `ModelResponseStatus` values rather than being used as control-flow exceptions across the Gateway boundary.

---

# M1.8 — Deterministic Serialization

Provide explicit serialization helpers for the logical contracts, or a clearly documented deterministic equivalent.

Requirements:
- enum values serialize as their stable string value;
- context tuple order is preserved;
- no object memory addresses / repr leakage;
- same object values serialize identically across repeated runs;
- JSON-compatible output;
- do not serialize secrets because secret-bearing fields do not exist in these contracts.

No persistence ledger is required in M1.

---

# M1.9 — Output Artifact Validation Helpers

Implement only **structural validation helpers** for the V1 text artifact contract. Do not call models and do not apply patches.

Required sections:

## PLAN
- `SUMMARY`
- `STEPS`
- `FILES`
- `TESTS`
- `RISKS`

## PATCH_PROPOSAL
- `SUMMARY`
- `FILES`
- `PATCH`
- `TESTS`
- `RISKS`

## DIAGNOSIS
- `CAUSE`
- `EVIDENCE`
- `FIX`
- `TESTS`
- `RISKS`

## REVIEW
- `STATUS`
- `FINDINGS`
- `TESTS`
- `RISKS`

Allowed REVIEW statuses:
- `PASS`
- `CHANGES_REQUIRED`

Validation rules:
- section matching is deterministic/case-normalized;
- missing required section -> output contract validation failure;
- do not guess omitted content;
- do not execute `PATCH` content;
- malformed output is represented by validation failure now and will map to `INVALID_RESPONSE` at Gateway integration in M3.

Keep parser deliberately small; this is not a Markdown rendering engine.

---

# Required Tests

Suggested paths:

```text
tests/aios_bridge/external_brain/test_contracts.py
tests/aios_bridge/external_brain/test_provider_contract.py
tests/aios_bridge/external_brain/test_transport_contract.py
tests/aios_bridge/external_brain/test_output_contract.py
```

Cover at minimum:

1. all enum values serialize to the locked strings;
2. `ContextItem` is immutable;
3. valid SHA-256 metadata accepted;
4. malformed SHA-256 metadata rejected;
5. valid `ModelRequest` construction;
6. invalid schema version rejected;
7. invalid `TASK-*` identity rejected;
8. empty instruction rejected;
9. non-positive input/output token budget rejected;
10. operation/output mismatch rejected;
11. context is immutable and order-preserving;
12. valid success `ModelResponse` accepted;
13. success with empty content rejected;
14. success with missing output type rejected;
15. negative usage/latency rejected;
16. failure response may leave token usage `None`;
17. request/response request-id mismatch rejected;
18. request/response task-id mismatch rejected;
19. successful response output type mismatch rejected;
20. ProviderAdapter can be satisfied by a fake async provider without inheriting runtime `LLMProvider`;
21. transport request rejects non-positive timeout;
22. transport result preserves provider request ID and latency deterministically;
23. deterministic serialization equality across repeated serialization;
24. PLAN with all required sections validates;
25. PLAN missing required section fails;
26. PATCH_PROPOSAL content is treated as data only;
27. DIAGNOSIS required sections validate;
28. REVIEW `PASS` validates;
29. REVIEW `CHANGES_REQUIRED` validates;
30. REVIEW with unsupported status fails;
31. importing/using new External Brain contracts does not alter existing `src.providers.LLMProvider` behavior or public shape;
32. existing bridge tests remain green.

Add more focused tests where necessary, but keep M1 implementation compact.

---

# Files Explicitly Protected From Semantic Change

TASK-014 must not change behavior in:
- `bridge.py`
- `src/providers/base.py`
- `src/providers/gemini.py`
- AgentLoop / retry / checkpoint / idempotency code
- browser execution stack
- Product Source Pack code from TASK-013

If a test import/path issue can be solved without editing these files, prefer that route.

Any unavoidable change to a protected file must be minimal, backward-compatible, explicitly justified in RESULT-014, and is expected to receive extra review scrutiny.

---

# Explicit Non-Goals

TASK-014 MUST NOT implement:
- ContextBuilder;
- token estimation/trimming;
- ModelGateway;
- MiniMax API/subscription call;
- DeepSeek API call;
- Kimi API call;
- provider registry;
- model router;
- quota registry;
- automatic fallback;
- retry policy for external models;
- MCP server;
- external filesystem/shell/browser/Git tools;
- model patch application;
- model-controlled commit/push/merge;
- worktrees/concurrent agents;
- changes to Python Agent runtime provider selection.

---

# Acceptance Criteria

TASK-014 is ready for review only when all are true:

1. `src/aios_bridge/external_brain/` exists as an isolated subsystem.
2. Locked enums/value objects from ADR-005 are implemented with deterministic stable serialization.
3. `ContextItem`, `ModelRequest`, and `ModelResponse` are immutable and enforce required invariants.
4. Operation -> output-type mapping is centralized and validated.
5. Request/response correlation mismatch is deterministically rejected.
6. Successful response with empty/mismatched output is rejected.
7. Failure response can preserve unknown token usage as `None`.
8. ProviderAdapter exists only as External Brain protocol; no live provider call exists.
9. ModelTransport/TransportRequest/TransportResult exist as generic networking boundary; no HTTP implementation exists.
10. V1 PLAN/PATCH_PROPOSAL/DIAGNOSIS/REVIEW structural validators exist and reject malformed artifacts.
11. Existing `src.providers.LLMProvider` / `GeminiProvider` remain semantically untouched.
12. `bridge.py` v0.4 zero-touch behavior remains semantically untouched.
13. Focused new External Brain test suite passes.
14. Existing bridge tests pass.
15. Full repository test suite passes with zero regression.
16. RESULT-014 explicitly reports changed files, focused test count, full-suite count, and confirms no live external-model request was made.

---

# Review Focus

Reviewer should pay special attention to:
- accidental coupling with `src.providers.LLMProvider`;
- accidental introduction of tool/workspace execution authority;
- mutable dict/list fields inside otherwise frozen dataclasses;
- weak request/response correlation;
- fabricated usage values;
- provider-specific assumptions leaking into generic contracts;
- hidden HTTP/network calls;
- modifications to `bridge.py` or existing provider runtime;
- overly clever Markdown parser behavior;
- contract drift from ADR-005.

---

## Human Gate

Do not execute automatically.

After Bridge sync detects TASK-014, execution requires explicit approval:

`/aios-worker RUN TASK-014`
