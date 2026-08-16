# REVIEW-014 — TASK-014 (AIOS Bridge v0.5-M1 External Brain Contract Implementation)

## Status
CHANGES_REQUIRED

## Reviewed Head
- Branch: `ai/task-014`
- Reviewed commit: `f69fa64efd12581bf2cfc514b12cb6d1f7fdf04e`
- Parent / canonical baseline: `540f4cb20b56cf72db333192d49ccf6eb295e9c4`
- Branch relation: ahead 1, behind 0; merge base exactly canonical baseline
- RESULT-014 status: `READY_FOR_REVIEW`

## Verification Recorded in RESULT-014
- Focused External Brain suite: **17 passed**
- Full repository suite: **491 passed**
- No live external-model request was made
- No semantic changes to `bridge.py`, `src/providers/base.py`, `src/providers/gemini.py`, AgentLoop/retry/checkpoint/idempotency, browser stack, or Product Source Pack

The overall structure is good: the subsystem is isolated under `src/aios_bridge/external_brain/`, the existing Python Agent `LLMProvider` contract is untouched, operation-to-output mapping is centralized, request/response correlation exists, and output artifact parsing remains deliberately small.

However, two contract defects violate explicit TASK-014 review/acceptance requirements and should be corrected before M1 is locked.

---

## Blocker 1 — `TransportRequest` is only shallow-frozen; caller-owned mutable state can still change the contract after construction

Current `TransportRequest` is declared `@dataclass(frozen=True)`, but stores caller-provided mappings directly:

```python
headers: Mapping[str, str] = field(default_factory=dict)
payload: Mapping[str, Any] = field(default_factory=dict)
```

A frozen dataclass only prevents assigning `request.headers = ...`; it does not make the referenced dictionary or nested payload immutable.

Example of the current problem:

```python
headers = {"Authorization": "Bearer A"}
payload = {"messages": [{"role": "user", "content": "A"}]}

req = TransportRequest(..., headers=headers, payload=payload)

headers["Authorization"] = "Bearer B"
payload["messages"][0]["content"] = "B"

# req now observes mutated values even though it is described as immutable/frozen.
```

This matters for v0.5 because the transport boundary will later carry credentials and the exact payload that is audited/sent. TASK-014 explicitly calls out **"mutable dict/list fields inside otherwise frozen dataclasses"** as a review focus, and M1.6 requires the transport boundary to be immutable where practical.

### Required fix
Make the stored transport request independent of caller-owned mutable objects and read-only after construction.

Acceptable approaches include a small deterministic deep-freeze/canonicalization helper, or equivalent defensive-copy + immutable representation. At minimum:
- caller mutations after construction MUST NOT change `req.headers` or `req.payload`;
- direct mutation through the stored object MUST be rejected or impossible;
- nested dict/list payload state must not remain an alias to caller-owned objects;
- keep the representation generic for future OpenAI-compatible / Anthropic-compatible transport use.

Do not add HTTP networking or provider logic while fixing this.

### Required regression tests
Add focused tests proving:
1. mutating the original `headers` dict after construction does not mutate the request;
2. mutating the original `payload`, including a nested list/dict value, does not mutate the request;
3. mutating `req.headers` / stored payload through the contract is rejected or impossible;
4. existing timeout/URL validation remains green.

---

## Blocker 2 — `ModelResponse(status=SUCCESS)` accepts contradictory failure metadata

TASK-014 M1.4 explicitly requires successful responses to have **no contradictory required failure state**.

The current `ModelResponse.__post_init__` validates `output_type` and non-empty content for SUCCESS, but does not reject:

```python
ModelResponse(
    ...,
    status=ModelResponseStatus.SUCCESS,
    output_type=BrainOutputType.PLAN,
    content="valid plan",
    error_code="AUTH_ERROR",
    error_message="authentication failed",
)
```

That produces a logically contradictory normalized response. Future Gateway/accounting code should never have to decide whether `status` or the failure fields are authoritative.

### Required fix
For `ModelResponseStatus.SUCCESS`:
- `error_code` MUST be `None`;
- `error_message` MUST be `None`.

Failure statuses may continue to carry optional error metadata and may preserve unknown usage as `None`.

### Required regression tests
Add focused tests proving:
1. SUCCESS + `error_code` is rejected;
2. SUCCESS + `error_message` is rejected;
3. normal SUCCESS remains valid;
4. non-success response with error metadata remains valid.

---

## Non-Blocking Hardening
Python `bool` is a subclass of `int`, so current integer checks can accept values such as `True` for token limits / latency / priority / status code. This is not the reason for CHANGES_REQUIRED, but while touching validation it is reasonable to reject booleans where the contract semantically requires an integer/number. Keep this small if addressed.

---

## Preserve Existing Good Boundaries
The fix MUST NOT:
- modify v0.4 `bridge.py` handoff semantics;
- modify `src.providers.LLMProvider` / `GeminiProvider`;
- add a live MiniMax/DeepSeek/Kimi call;
- add ContextBuilder, ModelGateway, router, fallback, retries, provider registry, MCP, or usage ledger;
- add filesystem/shell/browser/Git/tool authority to External Brain;
- make provider-specific assumptions leak into the generic contracts.

This should remain a small M1 contract correction only.

---

## Re-Verification Required
After the fix:
1. run the focused `tests/aios_bridge/external_brain/` suite;
2. run existing bridge tests;
3. run the full repository suite;
4. update `RESULT-014` with the exact new counts and fix delta;
5. publish the new branch head for re-review.

## Decision
CHANGES_REQUIRED.

Human fix gate:

`/aios-worker FIX TASK-014`
