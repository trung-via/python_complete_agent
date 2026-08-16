# REVIEW-014 — TASK-014 (AIOS Bridge v0.5-M1 External Brain Contract Implementation)

## Status
CHANGES_REQUIRED

## Reviewed Head
- Branch: `ai/task-014`
- Reviewed commit: `6f7e0323187b76b71e3466e89c3a6ff04f86caca`
- Previous reviewed head: `f69fa64efd12581bf2cfc514b12cb6d1f7fdf04e`
- Canonical baseline: `540f4cb20b56cf72db333192d49ccf6eb295e9c4`
- Branch relation to main: ahead 2, behind 0; merge base exactly canonical baseline
- RESULT-014 status: `READY_FOR_REVIEW`

## Verification Recorded in Updated RESULT-014
- Focused External Brain suite: **19 passed**
- Full repository suite: **493 passed**
- No live external-model request was made
- No protected subsystem was changed

## Prior Review Blockers — RESOLVED

### Prior Blocker 1 — Transport request aliases mutable caller state
RESOLVED.

The updated implementation defensively deep-freezes caller-provided `headers` and `payload`, including nested mapping/list/set values, so later caller mutation no longer changes the stored request. Regression coverage now exercises the aliasing/direct-mutation cases.

### Prior Blocker 2 — SUCCESS response accepts contradictory error metadata
RESOLVED.

`ModelResponse(status=SUCCESS)` now rejects both non-null `error_code` and non-null `error_message`; failure responses may still carry error metadata. Regression coverage is present.

The small bool-vs-int validation hardening is also acceptable and remains in scope.

---

## New Blocker — Deep-freeze breaks the locked JSON-compatible transport payload boundary

The current fix makes `TransportRequest.payload` immutable by recursively converting mappings to `types.MappingProxyType`:

```python
def _deep_freeze(val):
    if isinstance(val, (dict, Mapping)):
        return MappingProxyType({...})
```

and stores that frozen representation directly as `req.payload`.

This solves immutability, but introduces a new contract problem: Python's standard JSON encoder does **not** serialize `MappingProxyType` directly. A future M3 OpenAI-compatible transport cannot safely assume it can pass the locked `req.payload` to a normal JSON encoder/client without an additional conversion layer.

TASK-014 M1.6 explicitly locks `TransportRequest` as carrying a **JSON-compatible payload** and states that the transport contracts must be sufficient for M3 without changing `ModelRequest` / `ModelResponse`. The current representation is therefore immutable but not directly wire/JSON compatible.

This is not a request to remove deep immutability. Both properties are required:

1. the internal/stored request must remain independent of caller-owned mutable objects and read-only;
2. there must be a deterministic, explicit way to obtain a fresh JSON-compatible wire payload for transport serialization.

### Required fix
Keep the defensive immutable representation, but add a small explicit serialization/wire boundary such as one of these equivalent approaches:

```python
req.to_json_payload() -> dict[str, Any]
```

or

```python
req.to_wire_dict() -> dict[str, Any]
```

or another clearly named deterministic helper.

The helper MUST:
- recursively convert immutable internal mappings/tuples/frozensets used by the contract into fresh JSON-compatible `dict` / `list` primitives;
- preserve normal JSON scalar values (`str`, `int`, `float`, `bool`, `None`);
- return a fresh structure whose mutation cannot mutate the stored `TransportRequest`;
- reject or avoid silently accepting values that cannot be represented as JSON rather than relying on provider-specific magic;
- not expose/redact/log credentials; it is a data conversion helper only;
- not perform HTTP/networking;
- not add provider-specific behavior.

Prefer rejecting non-JSON-compatible payload values at contract construction or serialization rather than silently coercing arbitrary objects.

### Required regression tests
Add tests proving:
1. a nested normal transport payload can be converted and `json.dumps(...)` succeeds;
2. the serialized/wire payload has the expected ordinary `dict`/`list` shape;
3. mutating the returned wire payload does not mutate `req.payload`;
4. caller mutation protection from the prior fix remains green;
5. unsupported non-JSON payload values fail deterministically if accepted at construction today.

`headers` may remain an immutable mapping internally; this blocker specifically concerns the JSON request body/wire representation needed by M3.

---

## Scope Guard
The next fix MUST remain inside M1 contract/serialization support. Do not add:
- HTTP calls;
- MiniMax/DeepSeek/Kimi adapters;
- ContextBuilder;
- ModelGateway;
- router/fallback/retry/quota logic;
- usage ledger;
- filesystem/shell/browser/Git/tool execution authority;
- changes to `bridge.py` or `src.providers.LLMProvider`.

## Re-Verification Required
After the fix:
1. run focused `tests/aios_bridge/external_brain/`;
2. run existing bridge tests;
3. run the full repository suite;
4. update `RESULT-014` with exact test counts and delta;
5. publish the new branch head for re-review.

## Decision
CHANGES_REQUIRED.

The first two blockers are fully resolved; only the JSON-compatible wire-serialization boundary above remains before M1 can be approved.

Human fix gate:

`/aios-worker FIX TASK-014`
