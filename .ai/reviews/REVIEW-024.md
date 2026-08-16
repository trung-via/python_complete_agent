# REVIEW-024 — TASK-024 Usage & Efficiency Telemetry Hardening

STATUS: CHANGES_REQUIRED

## Review Scope
- Review round: `1` — ADR-017 Full Semantic Review
- Reviewed branch: `ai/task-024`
- Reviewed branch head: `7b42e5bb52dec69d93508c083266c6d55983921f`
- Tested implementation SHA reported by RESULT: `6a6d88e3b29403d6ad1c555f5b7b0ccc09281fec`
- Base main: `f47cc9d7e2d954413918ef7b7a2ab7a90bb1a6d8`
- Branch relation: ahead `2`, behind `0`; merge-base exact current main.
- `6a6d88e... -> 7b42e5b...` changes only `.ai/results/RESULT-024.md`; production code/tests at final branch head equal tested implementation.
- Review mode: ADR-017 first-review Full Semantic Review of TASK-024 Contract + Architecture Implementation Plan + Adversarial Checklist, complete Usage production boundary, focused tests, TASK-019 baseline compatibility, RESULT and SHA relation.
- Test counts below are RESULT evidence from Antigravity; this review did not independently execute the repository test suite.

## Semantic Review Result

TASK-024 correctly closes most of P20-1 through P20-5, but the bounded aggregation contract is not complete. The current implementation also contains a Review Manifest identity error that must be corrected in the next RESULT.

## Blocking Findings

### R1-1 — Aggregate token ranges can exceed the locked numeric bound
Severity: HIGH

TASK-024 introduces `MAX_USAGE_INT = 2**63 - 1` and correctly applies it to individual token values, counts, byte metrics and estimator input. However `aggregate_token_ranges()` sums valid `TokenMeasurement.min_tokens/max_tokens` values without validating the cumulative totals against `MAX_USAGE_INT`.

Example:

```text
m1 = REPORTED(MAX_USAGE_INT)
m2 = REPORTED(MAX_USAGE_INT)
aggregate_token_ranges([m1, m2])
    -> (2 * MAX_USAGE_INT, 2 * MAX_USAGE_INT)
```

Both inputs are individually valid, but the returned aggregate is outside the deterministic telemetry bound. `aggregate_token_ranges_by_actor_class()` delegates directly to this helper and therefore inherits the same behavior.

This violates:
- C2: explicit bounded numeric telemetry;
- C5: actor-class aggregate return shape must be bounded and explicit;
- the stated purpose of a single signed-64-bit-safe observability ceiling.

Required fix:
- make cumulative min/max aggregation fail closed if either aggregate would exceed `MAX_USAGE_INT`;
- prefer reusing the same Usage bounded-integer rule rather than introducing a second limit;
- do not saturate/truncate, because that would fabricate a measurement;
- preserve `(None, None)` behavior when an UNKNOWN measurement is encountered;
- preserve `(0, 0)` for an empty sequence/class;
- add regression tests for:
  - generic aggregate exactly at `MAX_USAGE_INT` -> pass;
  - generic aggregate `MAX_USAGE_INT + 1` through multiple individually valid measurements -> fail closed;
  - Brain class cumulative overflow -> fail closed;
  - Executor class cumulative overflow -> fail closed;
  - UNKNOWN behavior remains unchanged.

### R1-2 — RESULT Review Manifest mislabels TASK blob as PREVIOUS_REVIEW_SHA
Severity: MEDIUM — evidence integrity

This is the first review after `RUN`, so there is no previous REVIEW artifact. `RESULT-024.md` currently records:

```text
PREVIOUS_REVIEW_SHA: 9e54b70645d297c7e6b3d11fd32cbd04398f77cd
```

That SHA is the authorized `TASK-024.md` blob, not a REVIEW blob. `PREVIOUS_REVIEW_SHA` is a semantic manifest field and must not be repurposed to mean the task authorization artifact.

Required fix in the next RESULT:
- for the original RUN evidence, previous review is `null` / absent according to the manifest convention;
- for the upcoming FIX result, `PREVIOUS_REVIEW_SHA` must point to this REVIEW-024 artifact blob SHA, not the TASK blob;
- keep `Authorized Artifact` separate and correctly labeled.

No production code change is required for R1-2.

## Positive Evidence

The Full Semantic Review confirms these TASK-024 changes are substantively correct:
- Usage-local exact-canonical actor validation rejects padded Brain/Executor identities;
- all listed schema-v1 integer fields and estimator input use the common `MAX_USAGE_INT` boundary;
- bool and negative integer rejection are preserved;
- `context_efficiency_ratio` must remain `None` when useful/total bytes are unknown or total is zero;
- ratio values are normalized to canonical float representation, including canonical positive zero, and NaN/Infinity are rejected;
- actor-class aggregation separates Brain and Executor UNKNOWN state correctly;
- TASK-019 historical baseline is unchanged and remains ESTIMATED;
- current byte estimator semantics are preserved;
- 16 KiB top-level TaskUsageRecord/parser protection remains present;
- no Bridge/provider/Brain/failover/Executor/human authority behavior was changed.

RESULT reports against implementation `6a6d88e3b29403d6ad1c555f5b7b0ccc09281fec`:

```text
Continuity: 71 passed
AIOS Bridge: 157 passed
Full repository: 631 passed
Regressions: 0
LIVE_EXTERNAL_CALLS: 0
BRIDGE_V0_4_BEHAVIOR_CHANGED: NO
AUTHORITY_WIDENED: NO
EXECUTOR_RUNS: 1
EXECUTOR_FIX_RUNS: 0
TASK_019_BASELINE_VALID: YES
TASK_019_BASELINE_CHANGED: NO
```

## Required FIX Scope

Expected changes should remain bounded to:

```text
src/aios_bridge/continuity/usage.py
tests/aios_bridge/continuity/test_usage.py
.ai/results/RESULT-024.md
```

`src/aios_bridge/continuity/__init__.py` should not need another production change unless public exports actually change.

Do not modify `state.py`, `brain.py`, `failover.py`, Bridge, provider layers, Executor authority or Canonical State lifecycle.

## Required Re-Test

```text
pytest tests/aios_bridge/continuity/test_usage.py -q
pytest tests/aios_bridge/continuity/ -q
pytest tests/aios_bridge/ -q
pytest tests/ -q -W ignore
```

No live external calls.

## ADR-017 Stage Status

```text
FULL_SEMANTIC_REVIEW: FAIL
KNOWN_FINDINGS: OPEN
DELTA_FIX_REVIEW: NOT_RUN
FINAL_INDEPENDENT_AUDIT: NOT_RUN
```

Final Independent Audit must not run for approval until R1-1 and R1-2 are closed. After the FIX delta passes, perform a fresh Final Independent Audit against the final tested implementation and telemetry/baseline boundary before emitting APPROVED.

## Decision

`CHANGES_REQUIRED`
