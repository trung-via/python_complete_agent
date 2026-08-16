# REVIEW-016 — TASK-016 (AIOS Bridge v0.5-M3 ModelGateway + OpenAI-Compatible Transport + MiniMax Provider + Usage Ledger)

## Status
CHANGES_REQUIRED

## Review Round
2

## Reviewed Head
- Branch: `ai/task-016`
- Reviewed commit: `4c3f868d6e6f63bd456d902917a10ac17cf84c65`
- Previous reviewed commit: `2913729541d48322113714c09a3887d7dd9a2729`
- Canonical baseline: `4f5fafc4f9c4f16413d3e4e2d13adc856509bde9`
- RESULT-016 status: `READY_FOR_REVIEW`

## Round-1 Blockers — RESOLVED
The following prior findings are corrected at this head:

1. `request.provider=None` is accepted and explicit provider mismatch still fails before provider invocation.
2. `GatewayResult.ledger_persisted` is tri-state (`True` / `False` / `None`).
3. Ledger failure exposes only bounded `ledger_error_code="LEDGER_WRITE_FAILED"`; raw exception text is not returned.
4. `UsageRecord` now follows the ADR-007 provider-vs-context telemetry schema with requested/actual model fields and optional reasoning/cached token fields.
5. `UsageLedger.append()` is synchronous and the async gateway offloads it with `asyncio.to_thread()`.
6. Embedded `<think>` markers in final `message.content` fail closed to `INVALID_RESPONSE` without preserving the reasoning text.
7. MiniMax `base_resp.status_msg` is no longer reflected verbatim into normalized errors.

Focused External Brain tests recorded in RESULT-016: **69 passed**.

The implementation is substantially closer to ADR-007, but four remaining blockers must be corrected before M3 can be approved.

---

## Blocker 1 — Explicit model mismatch is not rejected before external call

TASK-016 explicitly requires provider/model mismatch to fail before any network call.

Current Gateway validates `request.provider`, but does not validate `request.model`. The MiniMax adapter then always sends its configured `_model_name` regardless of an explicitly different `request.model`.

Example unsafe ambiguity:

```text
ModelRequest.model = "OtherModel"
configured MiniMax provider model = "MiniMax-M3"
```

Current behavior can still send `MiniMax-M3` externally instead of failing closed.

### Required Fix
Preserve M1 optional semantics:
- `request.model is None` => configured provider model may be used;
- `request.model` explicitly set and equal to configured model => proceed;
- explicit mismatch => fail before transport/network call.

This check may live in `MiniMaxOpenAIProvider.invoke()` before constructing/sending the transport request, or in the gateway if implemented generically without changing the locked ProviderAdapter contract.

Do not add a provider registry/model router.

### Required Tests
1. `request.model=None` -> one provider/transport call using configured `MiniMax-M3`;
2. `request.model="MiniMax-M3"` -> one call;
3. `request.model="OtherModel"` -> `ContractValidationError` or equivalent invariant failure before transport call;
4. transport call count remains zero on mismatch.

---

## Blocker 2 — `TransportRequest` default repr can expose Authorization credentials

ADR-007 transport safety requires Authorization/API-key values never appear in exceptions, logs, or reprs.

`TransportRequest` remains a normal dataclass with the default generated repr while containing raw headers. Therefore a request such as:

```python
TransportRequest(
    ...,
    headers={"Authorization": "Bearer secret-token"},
)
```

can expose the bearer token through `repr(request)` / debugging output.

This becomes security-relevant in M3 because MiniMax is the first live credential-bearing transport path.

### Required Fix
Add a safe representation boundary without changing wire semantics.

Acceptable approach:
- define a custom `TransportRequest.__repr__()` that redacts sensitive header values (`Authorization`, case-insensitive; preferably other obvious auth header names if narrowly implemented);
- preserve actual immutable headers for transport transmission and `to_wire_dict()` behavior where required by the existing M1 wire contract;
- do not log or stringify raw headers elsewhere.

Do not redesign `TransportRequest` or remove its ability to carry the Authorization header to the transport.

### Required Tests
Create a fake secret and prove it is absent from:
- `repr(TransportRequest)`;
- `str(TransportRequest)` if it uses repr;
- transport normalized exception/result diagnostics.

The HTTP mock may still assert the fake header was actually transmitted once.

---

## Blocker 3 — Provider request-ID precedence does not match ADR-007

ADR-007 locks MiniMax response correlation semantics:

```text
use provider response `id` when present;
otherwise use transport/header correlation ID
```

Current provider takes `transport_res.provider_request_id` directly. `OpenAICompatibleTransport` only copies JSON body `id` when no header request ID exists, so if both exist the header wins.

That is the reverse of the locked MiniMax adapter precedence.

### Required Fix
Inside `MiniMaxOpenAIProvider` after confirming a mapping response body:
- if `body["id"]` is a non-empty string, use it as `ModelResponse.provider_request_id`;
- otherwise retain `transport_res.provider_request_id`.

Transport may remain generic; this precedence belongs in the MiniMax provider adapter.

### Required Test
Mock a response with both:

```text
body.id = "body-id"
transport provider_request_id = "header-id"
```

and assert final `ModelResponse.provider_request_id == "body-id"`.
Also test fallback to `header-id` when body id is absent/invalid.

---

## Blocker 4 — RESULT-016 still does not satisfy acceptance evidence

The updated RESULT records only the focused External Brain suite (**69 passed**).

TASK-016 acceptance additionally requires:
- existing bridge tests green;
- full repository suite green with zero regressions;
- exact branch head SHA in RESULT;
- complete/correct changed-file + diff summary;
- explicit `LIVE_SMOKE: NOT_RUN` if no manual live MiniMax call was performed.

The current RESULT still lacks those fields/evidence.

### Required Re-Verification
After the remaining code fixes:
1. run focused External Brain tests;
2. run existing bridge tests;
3. run full repository `tests/` suite;
4. do **not** run a live MiniMax request automatically;
5. update RESULT-016 with:
   - exact branch head;
   - exact focused/bridge/full-suite counts;
   - zero-regression statement only if supported by the run;
   - corrected full task diff summary;
   - `LIVE_SMOKE: NOT_RUN` unless operator explicitly ran one.

A live smoke call is not required for approval.

---

## Scope Guard
Keep this final correction round narrowly within M3:
- no ProviderRegistry;
- no DeepSeek/Kimi/GLM;
- no router/classifier;
- no retry/fallback;
- no quota polling;
- no repo crawling;
- no Antigravity tool/workspace authority;
- no patch auto-application;
- no semantic changes to v0.4 `bridge.py` handoff/authorization/publish;
- no semantic changes to Python Agent `src.providers.LLMProvider`.

Preserve all already-correct properties from the previous round.

## Decision
CHANGES_REQUIRED.

M3 is now structurally close to approval. The remaining work is limited to explicit model pre-call validation, credential-safe transport representation, MiniMax request-ID precedence, and complete acceptance evidence.

Human fix gate:

`/aios-worker FIX TASK-016`
