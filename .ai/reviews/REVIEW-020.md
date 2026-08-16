# REVIEW-020 — TASK-020 Quota & Efficiency Telemetry

STATUS: CHANGES_REQUIRED

## Review Scope
- Review round: `2`
- Reviewed branch: `ai/task-020`
- Reviewed branch head: `fdbd0703188422c19192fac5bdc9659c7c114e48`
- Tested implementation SHA: `c079e69d0cbb7764b4585515805b35add1dddb50`
- Base main: `5484462208dd47b9fbb3fd5ad382f423301c468a`
- Branch relation: ahead `4`, behind `0`; merge-base is exact current main.
- Implementation-to-reviewed-head relation: one evidence-only RESULT update after the tested implementation; production code/tests at reviewed head equal the tested implementation.
- Review mode: ADR-013 Round-2 delta-first. Reviewed previous REVIEW, new RESULT, FIX delta, and finding-scoped tests only. No full TASK/ADR/source/test reload.

## Round-1 Findings

### R1-1 — Bounded method / truthful estimator provenance
RESOLVED.

- `TokenMeasurement.method` is now bounded to a conservative lowercase identifier with a 64-character cap.
- required identifiers such as `utf8-bytes-div4-v1` and `historical-audit-estimate-v1` remain valid.
- `estimate_tokens_from_bytes()` rejects unsupported estimation method labels.
- tests cover free-form/oversized identifiers and unsupported estimator methods.

### R1-2 — Historical exact proxies must remain UNKNOWN when uncaptured
RESOLVED.

- relevant exact proxy fields are nullable.
- TASK-019 baseline now records uncaptured `full_file_reads`, `artifact_reads`, and executor `test_runs` as `null` rather than fabricated zeroes.
- known zero `external_api_calls` remains explicit.
- baseline tests assert the unknown/null semantics.

### R1-3 — Efficiency partition and ratio integrity
PARTIALLY RESOLVED.

- fully-known partition components now require exact equality with `brain_context_bytes`.
- partially-known partitions retain the safe partial-sum `<= total` rule.
- tests cover both over-filled and under-filled fully-known partitions.

One small integrity defect remains in the supplied ratio check. The implementation currently accepts a ratio whenever:

```python
abs(float(self.context_efficiency_ratio) - expected_ratio) <= 1e-4
```

But `expected_ratio` is already the deterministic helper result rounded to 4 decimal places. This tolerance can accept a value whose own 4-decimal rounding differs from the expected value; e.g. expected `0.8000`, supplied `0.80009` is within `1e-4` but rounds to `0.8001`. Such a value is not the locked deterministic ratio and would serialize/fingerprint differently.

Required final fix:
- require the supplied ratio to match the deterministic 4-decimal convention exactly, e.g. compare `round(float(supplied), 4)` to `expected_ratio`, or normalize/store the ratio deterministically before comparison;
- add a boundary test proving a near-but-different value such as `0.80009` is rejected (or normalized deterministically to the canonical expected value).

### R1-4 — Mixed UNKNOWN aggregation
RESOLVED.

- a mixed known + UNKNOWN sequence now returns `(None, None)` rather than a misleading known-only subtotal.
- fully-known sequences still aggregate deterministically.
- empty sequence behavior is explicitly defined and tested.

## Evidence
- FIX implementation commit: `c079e69d0cbb7764b4585515805b35add1dddb50`.
- Final reviewed head: `fdbd0703188422c19192fac5bdc9659c7c114e48`; only `.ai/results/RESULT-020.md` changes after the tested implementation.
- RESULT reports: Continuity `36 passed`; Bridge `122 passed`; full repository `596 passed`; no regressions.
- `LIVE_EXTERNAL_CALLS: 0`.
- `TELEMETRY_MODEL_TURNS_ADDED: 0`.
- `BRIDGE_V0_4_BEHAVIOR_CHANGED: NO`.
- `AUTHORITY_WIDENED: NO`.

## Evidence Note
`RESULT-020` currently labels `PREVIOUS_REVIEW_SHA` with the previously reviewed branch head (`579ef1...`) while the exact authorized REVIEW artifact is separately recorded as `7e96b9c56d...`. This does not block correctness because the authorized artifact pointer is present, but future Review Manifest generation should standardize this field to unambiguously identify the previous REVIEW artifact rather than a reviewed implementation/head SHA.

## Final FIX Scope
Expected production delta is extremely small:

```text
src/aios_bridge/continuity/usage.py
tests/aios_bridge/continuity/test_usage.py
.ai/results/RESULT-020.md
```

No Bridge, authority, routing, model invocation, or unrelated telemetry changes.

## Decision

`CHANGES_REQUIRED`

All substantive Round-1 issues except the final deterministic ratio boundary are resolved. Fix only that boundary, re-run the required suites, and publish evidence. Round 3 should require only the tiny implementation/test delta plus RESULT evidence.