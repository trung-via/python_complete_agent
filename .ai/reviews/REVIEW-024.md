# REVIEW-024 — TASK-024 Usage & Efficiency Telemetry Hardening

STATUS: CHANGES_REQUIRED

## Review Scope
- Review round: `2` — ADR-017 Delta Fix Review + Final Independent Audit attempt
- Reviewed branch: `ai/task-024`
- Reviewed branch head: `d1fd7a7451186e82df142b33c03f5683f5facd47`
- Tested implementation SHA reported by RESULT: `cc96b8f384490f689ef5d2bd1a4c4a6198b63310`
- Previous reviewed branch head: `7b42e5bb52dec69d93508c083266c6d55983921f`
- Base main: `f47cc9d7e2d954413918ef7b7a2ab7a90bb1a6d8`
- Branch relation: ahead `4`, behind `0`; merge-base exact current main.
- `7b42e5b... -> cc96b8f...` changes only `src/aios_bridge/continuity/usage.py` (+4) and `tests/aios_bridge/continuity/test_usage.py` (+55).
- `cc96b8f... -> d1fd7a7...` changes only `.ai/results/RESULT-024.md`; production code/tests at final branch head equal tested implementation.
- Test counts below are RESULT evidence from Antigravity; this review did not independently execute the repository test suite.

## Round-1 Finding Status

### R1-2 — PREVIOUS_REVIEW_SHA evidence identity
RESOLVED.

The FIX RESULT correctly records:

```text
PREVIOUS_REVIEW_SHA: 2501ec720d67ec75ee70c91cd4b0546c6fd568e7
```

which is the Round-1 REVIEW-024 blob SHA. The authorized artifact is separately and correctly labeled as REVIEW-024.

### R1-1 — cumulative token aggregation bound
PARTIALLY RESOLVED; one fail-closed edge remains.

The implementation now validates final `total_min` and `total_max` against `MAX_USAGE_INT` and tests all-known generic, Brain, and Executor overflow. That closes the normal all-known path.

However the helper still returns immediately on the first UNKNOWN measurement before validating/scanning the remaining known measurements. Therefore UNKNOWN can mask a deterministically known overflow.

Example:

```text
MAX = MAX_USAGE_INT
aggregate_token_ranges([
    REPORTED(MAX),
    REPORTED(1),
    UNKNOWN,
])
```

The known subtotal alone is already `MAX + 1`, so no valid bounded aggregate is possible even before accounting for the UNKNOWN contribution. Current code returns `(None, None)` when it reaches UNKNOWN, before the post-loop bound check.

The reverse ordering also matters: an UNKNOWN encountered first prevents inspection of later known records. A deterministic aggregation helper must not let ordering decide whether a provable overflow is detected.

## Blocking Finding R2-1 — UNKNOWN must not mask a provable cumulative overflow
Severity: HIGH

Required fix:
- do not return immediately when UNKNOWN is encountered;
- scan/validate every measurement;
- track `saw_unknown` separately;
- sum known ranges and enforce `MAX_USAGE_INT` on the known subtotal (preferably incrementally or at least after the full scan);
- if known subtotal overflows, fail closed regardless of UNKNOWN presence/order;
- only after all inputs have been inspected and known subtotal is bounded, return `(None, None)` if `saw_unknown`, otherwise return the bounded totals;
- preserve `(0, 0)` for empty input.

Required regression tests:
1. `[MAX, 1, UNKNOWN]` -> fail closed;
2. `[UNKNOWN, MAX, 1]` -> fail closed;
3. bounded known values + UNKNOWN -> `(None, None)`;
4. same semantics through Brain actor-class aggregation;
5. same semantics through Executor actor-class aggregation.

## Blocking Finding R2-2 — ratio validator can leak OverflowError for extreme integer input
Severity: MEDIUM

`_validate_canonical_ratio()` accepts `int | float`, then calls `math.isnan(val)` / `math.isinf(val)` before converting/range-checking. Python's math conversion for an arbitrarily large integer can raise `OverflowError` before the validator reaches its `[0, 1]` rejection.

The Usage validation boundary should reject invalid ratio inputs deterministically with `ContinuityStateValidationError`, not leak a raw numeric conversion exception through `EfficiencyMetrics.from_dict()` / construction.

Required fix:
- make conversion/range validation safe for arbitrary accepted Python `int`/`float` values;
- catch conversion overflow (or check integer range before float conversion) and raise `ContinuityStateValidationError`;
- preserve bool rejection, finite checks, `[0,1]`, canonical float conversion, and `-0.0 -> 0.0` semantics.

Required regression tests:
- very large positive integer ratio fails with `ContinuityStateValidationError`;
- very large negative integer ratio fails with `ContinuityStateValidationError`;
- ordinary `0`, `1`, `0.0`, `1.0`, `-0.0`, NaN and infinities retain current semantics.

## Final Independent Audit — Positive Evidence

Outside the blockers above, the final audit reconfirms:
- exact-canonical Brain/Executor actor identities;
- common signed-64-safe semantic bound on token/count/byte telemetry;
- estimator input bound and existing estimator semantics;
- UNKNOWN context-efficiency rule when useful/total is absent or total is zero;
- canonical persisted ratio floats and canonical positive zero for normal bounded numeric inputs;
- exact efficiency partition checks;
- actor-class aggregation isolation between Brain and Executor;
- REPORTED / ESTIMATED / UNKNOWN provenance semantics;
- strict unknown-field handling and 16 KiB TaskUsageRecord/parser bound;
- TASK-019 baseline remains byte-identical (`be2287e505e32da68f268c632700ac4f8b7ce56b`), ESTIMATED, and un-fabricated;
- no Bridge/provider/Brain/failover/Executor/human authority change.

RESULT reports against tested implementation `cc96b8f384490f689ef5d2bd1a4c4a6198b63310`:

```text
Continuity: 72 passed
AIOS Bridge: 158 passed
Full repository: 632 passed
Regressions: 0
LIVE_EXTERNAL_CALLS: 0
EXECUTOR_RUNS: 1
EXECUTOR_FIX_RUNS: 1
TASK_019_BASELINE_VALID: YES
TASK_019_BASELINE_CHANGED: NO
```

Non-blocking evidence cleanup: RESULT still labels `FAILOVER_SCHEMA_VERSION: 1` inside a Usage Telemetry milestone. This field is not required by TASK-024 and does not affect code correctness; prefer removing it or renaming it to an accurate Usage schema label in the next RESULT rather than carrying cross-milestone terminology forward.

## Required FIX Scope
Expected production/test delta remains tiny and bounded to:

```text
src/aios_bridge/continuity/usage.py
tests/aios_bridge/continuity/test_usage.py
.ai/results/RESULT-024.md
```

No `state.py`, `brain.py`, `failover.py`, Bridge, provider, executor, or authority changes.

## ADR-017 Stage Status

```text
FULL_SEMANTIC_REVIEW: FAIL (Round 1)
R1-2: CLOSED
R1-1: PARTIAL — edge remains
DELTA_FIX_REVIEW: FAIL
FINAL_INDEPENDENT_AUDIT: FAIL — new robustness finding R2-2
APPROVED: NO
```

After the next FIX, use a narrow delta-first review for R2-1/R2-2 and evidence identity. If that delta passes, perform one fresh Final Independent Audit on the resulting final tested implementation before APPROVED.

## Decision

`CHANGES_REQUIRED`
