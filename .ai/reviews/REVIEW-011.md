# REVIEW-011 — TASK-011 (Phase 6 M2.1 Winning Product Intelligence Contracts & Score V1)

## Status
CHANGES_REQUIRED

## Reviewed Head
- Branch: `ai/task-011`
- Reviewed commit: `9c6486002f8bb421e5d6411678c6a716f214beeb`
- Main baseline: `a3ab8ee06495d06006d6d61d06313c8977f555f0`
- Branch relation to main: ahead 1, behind 0 (fast-forward safe)
- Task artifact blob: `677b6f6dd635bfe78d712f492fc818c50f05d7c4`
- RESULT-011 blob: `f07d1889beac9d753e81f07ceb26eedf03c4cea9`
- Exact RUN authorization in RESULT: `.ai/tasks/TASK-011.md (677b6f6dd6)` — matches the current TASK-011 artifact.
- Reported focused Product Intelligence suite: 15 passed, 0 failed.
- Reported full repository suite: 388 passed, 0 failed, exit code 0.

## Summary
The implementation has the right overall architecture: a separate `product_intelligence` package, immutable snapshot/evidence/signal models, six score categories with the agreed 25/20/15/10/15/15 weights, confidence breakdown with 40/25/20/15 weights, no marketplace/network integration, no queue write, and no Phase 5.6 control-plane redesign.

However, several contract-level issues would make real M2.2 ranking behavior misleading or non-reproducible. These block approval because TASK-011 is specifically the canonical scoring contract that later adapters will depend on.

## Blocking Finding 1 — `base_score` does not follow the required available-data normalization contract, and missing signals are not explicit

### Location
- `src/product_intelligence/scoring.py`
- `src/product_intelligence/normalizer.py`
- `tests/product_intelligence/test_scoring.py`

TASK-011 requires `base_score` to be calculated over **available weighted signals/categories while preserving a 0–100 scale**, with sparse-data risk handled by the separate confidence factor.

Current code instead assigns every missing category `raw_score=0`, `coverage=0`, and still keeps that category's full canonical weight in the 100-point denominator. Example: one perfect Demand signal produces `base_score=25`, then confidence reduces it again. The focused test explicitly codifies `25 -> 17.5` for a sparse but perfect Demand candidate.

This double-penalizes missing data and makes `base_score` no longer answer the intended question, “how strong is the observed evidence?”, independently from “how confident are we that the evidence is complete?”. It also conflicts with the task's required high-base/weak-completeness scenario.

Additionally, `SnapshotNormalizer` simply omits unavailable fields. `NormalizedSignal` has a `MISSING` provenance, but normal normalization never emits explicit missing signals, and `missing_or_weak_signals` only reports an entire missing category. If Demand has `sold_count` but no `review_count`, Demand coverage becomes 1.0 and the missing review-depth signal is invisible to completeness and explanation.

### Required Fix
- Compute `base_score` from available category/signal weight and renormalize it to a 0–100 scale; keep the canonical category weights as relative importance.
- Let confidence carry the missing-data penalty rather than silently charging missing categories twice.
- Define a deterministic expected-signal/coverage contract so partially populated categories have partial completeness instead of binary 0/1 coverage.
- Make missing expected signals explicit in output (`MISSING` signal objects or an equivalent typed expected-signal registry) and include them in `missing_or_weak_signals`/completeness.
- Add regressions proving a sparse but excellent observed subset can have a high `base_score` while a low completeness/confidence materially lowers `final_score`.

## Blocking Finding 2 — Determinism is optional because the scorer/normalizer call `datetime.now()` internally

### Location
- `WinningProductScorer.score()`
- `WinningProductScorer.score_snapshot()`
- `SnapshotNormalizer.normalize_snapshot()`

TASK-011 explicitly requires the scorer to receive an explicit `evaluated_at` and forbids internal current-time lookup that makes repeated results drift.

Current public APIs accept `evaluated_at=None` and fall back to `datetime.now(timezone.utc)`. For `score_snapshot`, this changes freshness/confidence/final score over time. For direct `score`, even when signal scores are fixed, serialized output changes because `evaluated_at` changes. Therefore identical caller inputs are not guaranteed to produce byte-for-byte equivalent output unless the caller happens to pass an evaluation time.

### Required Fix
- Require an explicit `evaluated_at` at the public deterministic scoring boundary, or provide a clearly separate convenience wrapper outside the pure scoring contract that obtains current time before calling the pure scorer.
- Remove `datetime.now()` from the canonical pure scorer/normalizer path.
- Add a regression that the canonical API cannot silently use wall-clock time.

## Blocking Finding 3 — Canonical commission-rate units are ambiguous and the normalizer has a discontinuity at `1.0`

### Location
- `ProductCandidateSnapshot.affiliate_commission_rate`
- `SnapshotNormalizer.normalize_snapshot()` commercial normalization

The snapshot validates commission rate in `[0, 100]`, which naturally reads as percentage points. But the normalizer treats values `<= 1.0` as fractions and values `> 1.0` as percentages:

- `1.0` becomes `100%` and scores as maximum commission.
- `1.01` becomes `1.01%` and scores near zero.

That discontinuity is unsafe for future marketplace adapters and violates the purpose of M2.1 as the canonical cross-platform contract.

### Required Fix
- Choose one unit for the canonical snapshot contract (recommended: percentage points in `[0,100]`, because that is already the model validation/documentation shape), document it, and normalize only that unit.
- If adapters receive fractions, convert them in the adapter before constructing the canonical snapshot.
- Add boundary tests for `0`, `1`, typical values such as `10/15`, and `100` so no dual-unit ambiguity remains.

## Blocking Finding 4 — Policy validation is not actually strict enough for a configurable scoring authority

### Location
`src/product_intelligence/policy.py`

The policy docstring says all weights/thresholds are strictly validated, but current validation mainly checks the two sums, threshold ordering, and positive freshness half-life. Negative category/confidence weights can still pass if another weight compensates so the totals remain 100/1.0. Decision thresholds can also be outside their natural score/confidence ranges.

Because this policy is the canonical scoring authority, such values can create negative/illogical completeness contributions and rely on downstream clamping rather than rejecting an invalid policy.

### Required Fix
- Validate every category weight is finite and non-negative (normally strictly positive for the six canonical V1 categories).
- Validate every confidence weight is finite and in `[0,1]` and remains non-negative.
- Validate score thresholds in `[0,100]`, confidence thresholds in `[0,1]`, and all numeric policy values are finite.
- Add targeted invalid-policy tests, including a negative weight set that still sums correctly.

## RESULT / Evidence Finding
`RESULT-011.md` reports the full-suite command and 388 passes, and notes the focused suite as 15 passes. However, its required `Diff Stat` block is empty, and the focused verification is not recorded with the exact required command plus exit code in the verification section. TASK-011 explicitly requires both. Refresh RESULT-011 after FIX with the complete GitHub-visible diff stat and exact focused/full commands, exit codes, and pass counts.

## Non-Blocking Notes
- The current package separation and no-network/no-auto-queue boundary are good and should be preserved.
- The six category weights and four confidence weights match the approved M2.1 design.
- The current `WinningProductScore` uses a mutable `dict` for `category_scores` inside a frozen dataclass. Consider making the contained mapping immutable as well so the output contract is deeply immutable, but this is secondary to the blockers above.
- The synthetic documentation example should be regenerated from the corrected scorer so its numerical breakdown is executable evidence rather than hand-maintained approximations.

## Decision
CHANGES_REQUIRED.

Publish fixes only through the exact current REVIEW-011 artifact. Do not merge automatically. After the FIX is published, request `Review TASK-011` again.
