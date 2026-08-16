# REVIEW-014 — TASK-014 (AIOS Bridge v0.5-M1 External Brain Contract Implementation)

## Status
CHANGES_REQUIRED

## Reviewed Head
- Branch: `ai/task-014`
- Reviewed commit: `fb970c8325a9fd2887021010c7663868be019d37`
- Previous reviewed head: `6f7e0323187b76b71e3466e89c3a6ff04f86caca`
- Canonical baseline: `540f4cb20b56cf72db333192d49ccf6eb295e9c4`
- RESULT-014 status: `READY_FOR_REVIEW`

## Verification Recorded in RESULT-014
- Focused External Brain suite: **20 passed**
- Full repository suite: **494 passed**
- No live external-model request was made
- Fix delta remains limited to transport contract/serialization tests plus RESULT metadata

## Previous Blocker — RESOLVED
The JSON wire boundary requested in the previous review is now present:
- `TransportRequest.to_json_payload()` returns a fresh ordinary JSON-shaped structure;
- `TransportRequest.to_wire_dict()` returns a fresh wire representation;
- `json.dumps(req.to_json_payload())` is covered and succeeds for normal nested payloads;
- mutating the returned wire payload does not mutate the immutable stored request;
- custom objects/callables are rejected deterministically.

The previous immutability and contradictory-success-metadata fixes remain valid.

---

## Final Blocker — `set` / `frozenset` are silently accepted as JSON payload values and break deterministic serialization

`_validate_and_freeze_payload()` currently contains:

```python
elif isinstance(val, (set, frozenset)):
    return tuple(_validate_and_freeze_payload(v) for v in val)
```

This is inconsistent with the locked transport contract for two reasons:

1. `set` and `frozenset` are not JSON-compatible payload types.
2. Set iteration order is not a stable semantic order, so silently converting a set to tuple/list can make wire serialization non-deterministic across processes/runs.

M1 requires deterministic serialization and the prior review explicitly required unsupported non-JSON payload values to fail rather than be silently coerced by provider-specific or contract-specific magic.

### Required Fix
Do not accept unordered sets as valid JSON request payload data.

Preferred V1 rule:
- accept JSON scalars: `str`, `int`, finite `float`, `bool`, `None`;
- accept mappings with string keys;
- accept ordered sequences (`list`, and `tuple` if intentionally normalized to JSON array);
- reject `set` and `frozenset` with `ContractValidationError`.

Keep the internal immutable mapping/tuple representation and existing `to_json_payload()` / `to_wire_dict()` helpers.

### Required Regression Tests
Add focused tests proving:
1. `payload={"x": {1, 2}}` is rejected;
2. `payload={"x": frozenset({1, 2})}` is rejected;
3. ordinary nested list/dict/tuple payloads remain JSON-serializable and deterministic;
4. previous defensive-copy and wire-copy mutation tests remain green.

Optional but desirable while touching this exact validator: reject non-finite floats (`NaN`, `+Inf`, `-Inf`) so the payload is strict JSON-compatible rather than relying on Python `json.dumps(..., allow_nan=True)` behavior. This is not a separate blocker if left for later, but strict rejection would make the V1 boundary cleaner.

---

## Scope Guard
This remains an M1 contract fix only. Do not add:
- HTTP/networking;
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
3. run full repository tests;
4. update RESULT-014 with exact counts;
5. publish the new branch head for re-review.

## Decision
CHANGES_REQUIRED.

All previous blockers are resolved. Only deterministic rejection of unordered/non-JSON set payloads remains before M1 approval.

Human fix gate:

`/aios-worker FIX TASK-014`
