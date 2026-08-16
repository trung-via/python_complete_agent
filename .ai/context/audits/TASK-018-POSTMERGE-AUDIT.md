# TASK-018 — Post-Merge Independent Audit

STATUS: FINDINGS_REQUIRE_REMEDIATION

## Audit Basis

Retrospective Full Semantic Review + Final Independent Audit under ADR-017.

TASK-018 remains historically MERGED. Historical REVIEW-018 is not rewritten.

Reviewed boundary:
- `.ai/tasks/TASK-018.md`
- ADR-009 MiniMax Timeout Configuration Contract
- `.ai/results/RESULT-018.md`
- historical `.ai/reviews/REVIEW-018.md`
- `src/aios_bridge/external_brain/providers/minimax.py`
- `tests/aios_bridge/external_brain/test_minimax_provider.py`
- `TransportRequest` / `OpenAICompatibleTransport` only to verify timeout propagation semantics

Historical merged head:

```text
54303dc7d56ddce4ae9b22ef05c7dd310e731737
```

---

## P18-1 — Extreme integer timeout can escape the provider validation contract

Severity: MEDIUM

ADR-009 requires MiniMax provider timeout configuration to be a positive finite number, invalid input to fail during provider construction, and the stored provider value to be a normalized finite float.

Current constructor checks:

```python
isinstance(timeout_seconds, bool)
not isinstance(timeout_seconds, (int, float))
not math.isfinite(timeout_seconds)
timeout_seconds <= 0
```

and later stores:

```python
self._timeout_seconds = float(timeout_seconds)
```

For an arbitrarily large Python integer (for example `10**10000`), numeric conversion inside `math.isfinite()` and/or `float()` can raise raw `OverflowError` before the provider converts the condition into `ContractValidationError`. Formatting the enormous integer into an error message can also hit Python's integer string conversion limit.

This means the constructor is not fully fail-closed inside the External Brain contract error domain for all accepted Python `int|float` input types.

Required remediation:
- validate type/bool first;
- convert to float inside a guarded conversion boundary;
- catch conversion overflow/value errors and raise `ContractValidationError` with bounded diagnostics;
- validate the normalized float is finite and > 0;
- store that normalized float;
- do not impose a provider quota/heuristic maximum that ADR-009 did not authorize;
- preserve default 30.0, explicit 90.0 forwarding, single-call/no-retry behavior and credential-safe repr/str.

Required regression tests:
- huge positive integer timeout -> `ContractValidationError` during construction;
- huge negative integer timeout -> `ContractValidationError` during construction;
- error path must not require rendering the full huge integer;
- ordinary valid integer timeout (e.g. `90`) normalizes to `90.0` and is forwarded;
- existing zero/negative/bool/NaN/infinity cases stay green;
- no transport call occurs for invalid construction inputs.

---

## Positive Findings

The audit reconfirms TASK-018 correctly implemented its main contract:
- provider-level timeout option is additive and defaults to `30.0`;
- explicit `90.0` is stored/forwarded to every created `TransportRequest`;
- normal invalid zero/negative/bool/NaN/infinity cases fail before invocation;
- API key is not exposed through provider repr/str;
- MiniMax payload/model/endpoint semantics were not changed;
- exactly-one-call/no-retry/no-fallback behavior remains intact;
- `TransportRequest` remains wire-level timeout authority;
- OpenAI-compatible transport consumes request timeout for both HTTP timeout and outer async safety timeout;
- no Bridge/runtime-provider/execution authority widening occurred.

Historical RESULT reports 73 External Brain, 73 AIOS Bridge and 547 full-repository tests passing at tested implementation `86d157af7efadacdb0f5fff172f9dea16ee0a39a`. This retrospective audit did not independently execute the historical suite.

---

## Decision

```text
REMEDIATION_REQUIRED
```

The defect is narrow and does not invalidate the successful TASK-017 real-task proof that used ordinary finite timeout values. Create a small provider-local timeout validation hardening task; do not redesign generic transport semantics.
