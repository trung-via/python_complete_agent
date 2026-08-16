# TASK-020 — Post-Merge Independent Audit

STATUS: FINDINGS_REQUIRE_REMEDIATION

## Audit Basis

This is a retrospective Full Semantic Review + Final Independent Audit of merged TASK-020 under ADR-017 Uniform Assurance Pipeline.

Historical TASK-020 merge/review history is not rewritten. Findings below SHALL be remediated by a new task.

Reviewed boundary:
- `.ai/tasks/TASK-020.md`
- ADR-014 Usage & Efficiency Telemetry Contract
- `.ai/results/RESULT-020.md`
- historical `.ai/reviews/REVIEW-020.md`
- `src/aios_bridge/continuity/usage.py`
- `src/aios_bridge/continuity/__init__.py`
- `tests/aios_bridge/continuity/test_usage.py`
- `.ai/metrics/TASK-019-USAGE.json`
- coupled shared actor validator in `state.py`

TASK-020 merged head:

```text
5c93561bf08d7fb0ed91c9199b0ae023c8b1ea4b
```

Current `usage.py` on main retains the same blob as the merged TASK-020 implementation.

---

## Finding P20-1 — Usage actor IDs are strip-valid but not exact-canonical

Severity: HIGH

`BrainUsageRecord.__post_init__()` and `ExecutorUsageRecord.__post_init__()` call the shared `_validate_actor_id()` but ignore its returned canonical value. The shared validator strips leading/trailing whitespace before validating.

Therefore values such as:

```text
chatgpt-chat
 chatgpt-chat 
```

can both validate while remaining different serialized/fingerprinted telemetry identities.

This violates deterministic actor identity and repeats the representational ambiguity already hardened at later Brain boundaries.

Required remediation:
- BrainUsageRecord and ExecutorUsageRecord actor IDs must be exact-canonical at the Usage boundary;
- padded actor IDs must fail closed rather than silently normalize;
- do not change the generic `state.py` validator contract in this task;
- add round-trip/fingerprint tests proving only one representation exists.

---

## Finding P20-2 — Counts, byte values, and token ranges are not semantically bounded

Severity: HIGH

ADR-014 Decision 3 requires all counts to be non-negative integers **and bounded**. TASK-020 likewise requires immutable/bounded types and bounded ESTIMATED token ranges.

The current `_validate_non_negative_int()` enforces type and lower bounds only. No explicit maximum exists for:
- token min/max values;
- Brain round/turns/byte/read/API counters;
- Executor runs/bytes/test/API counters;
- Human counters/copy-paste bytes;
- Efficiency byte counters;
- byte-estimator input.

The 16 KiB TaskUsageRecord serialized-size cap is useful but is not a semantic upper bound for individual numeric measurements, and nested usage types/helpers can be constructed independently of the top-level record.

Required remediation:
- define explicit deterministic upper bound(s) for telemetry numeric measurements;
- apply them consistently to token ranges, counts and byte metrics;
- estimator input must use the same bounded byte rule;
- keep bool rejection and lower-bound semantics;
- add exact max / max+1 tests for each numeric category or shared validator path.

A broad 64-bit-safe cap is acceptable if documented and consistently enforced; do not invent provider quota semantics.

---

## Finding P20-3 — context_efficiency_ratio can be supplied when exact inputs are UNKNOWN

Severity: HIGH

ADR-014 defines:

```text
context_efficiency_ratio = useful / brain_context_bytes
```

and requires unavailable useful/redundant classification to remain UNKNOWN rather than guessed. TASK-020 also requires efficiency ratio calculation only when required exact byte components are known.

Current `EfficiencyMetrics` validates a supplied ratio against `useful_context_bytes` and `brain_context_bytes` only when both are present. If either input is `None`, any ratio in `[0, 1]` is accepted. A ratio can also survive when `brain_context_bytes == 0`, even though `calculate_context_efficiency_ratio()` correctly returns `None` for a zero denominator.

Required remediation:
- non-null context_efficiency_ratio requires known `useful_context_bytes` and known positive `brain_context_bytes`;
- if either required input is UNKNOWN or total is zero, ratio must be `None`;
- when supplied, ratio must equal the deterministic helper result exactly;
- preserve partial partition semantics for byte components themselves.

---

## Finding P20-4 — Ratio numeric representation is not canonical

Severity: MEDIUM

`context_efficiency_ratio` and `full_file_read_rate` accept both int and float values and persist the raw numeric representation.

Semantically equivalent values such as:

```text
1
1.0
-0.0
0.0
```

can therefore serialize differently and produce different TaskUsageRecord fingerprints while representing the same ratio.

Required remediation:
- define one canonical persisted numeric representation for ratio fields;
- normalize or reject alternative representations deterministically at construction;
- normalize negative zero to canonical zero;
- preserve range checks and finite-value rejection;
- add JSON round-trip/fingerprint equivalence tests.

---

## Finding P20-5 — Required token aggregation is generic, not by actor class

Severity: MEDIUM

TASK-020 requires a deterministic helper for aggregation of min/max token ranges **by actor class**.

The current `aggregate_token_ranges()` only aggregates an already-selected sequence of TokenMeasurement values. It has no TaskUsageRecord/Brain-vs-Executor grouping semantics, so callers must perform the actor-class partition themselves.

Required remediation:
- add a deterministic task-level/class-level aggregation helper that produces separate Brain and Executor token ranges (or an equivalently explicit actor-class result);
- UNKNOWN in one actor class must not erase a known aggregate for the other class;
- preserve the existing generic helper for compatibility unless there is a strong reason to replace it;
- no vendor-specific grouping/routing behavior.

---

## Positive Findings

The audit reconfirms that TASK-020 correctly established:
- REPORTED / ESTIMATED / UNKNOWN provenance classes;
- exact REPORTED range semantics;
- ESTIMATED range + bounded method identifier requirement;
- UNKNOWN token-value/method rejection;
- deterministic TaskUsageRecord canonical JSON + SHA-256 fingerprint;
- 16 KiB top-level record/parser cap;
- fail-closed unknown-field handling;
- historical TASK-019 estimates clearly labeled ESTIMATED with uncaptured exact byte/read proxies left null;
- deterministic byte-based estimator with explicit versioned method and no model/API calls;
- mixed UNKNOWN token aggregation preserving incompleteness;
- exact efficiency partition validation when all components are known;
- no Bridge/provider/router/executor/authority widening.

Historical RESULT evidence reported 36 Continuity, 122 Bridge and 596 full-repository tests passing at tested implementation `9128906ed12688cc74397a0a52dd776ab2123d19`. This retrospective audit did not independently execute that historical test suite.

---

## Decision

TASK-020 remains historically MERGED; its history SHALL NOT be rewritten.

Post-merge audit verdict:

```text
REMEDIATION_REQUIRED
```

Create a bounded telemetry-hardening task before relying on M1.5 telemetry as a strict measurement foundation for subsequent usage comparisons. This remediation does not invalidate TASK-021/022/023 semantic control contracts and does not require Bridge lifecycle changes.
