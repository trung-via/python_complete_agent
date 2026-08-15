# REVIEW-011 — TASK-011 (Phase 6 M2.1 Winning Product Intelligence Contracts & Score V1)

## Status
CHANGES_REQUIRED

## Reviewed Head
- Branch: `ai/task-011`
- Reviewed commit: `880b7a8a4d6e84b89990fd1cf0b890afde92efc3`
- Main baseline: `a3ab8ee06495d06006d6d61d06313c8977f555f0`
- Branch relation to main: ahead 4, behind 0 (fast-forward safe)
- Task artifact blob: `677b6f6dd635bfe78d712f492fc818c50f05d7c4`
- Prior CHANGES_REQUIRED authorization blob: `49469a96e193cafcd2ef488c2864d743ceaa7e1e`
- RESULT-011 blob: `7fbd6fd879b1555eaec5779eb3c69cbc0468c6e3`
- RESULT action: `FIX`
- Exact FIX authorization recorded by worker: `.ai/reviews/REVIEW-011.md (49469a96e1)` — matches the prior review artifact exactly.
- Reported focused Product Intelligence suite: 20 passed, 0 failed, exit code 0.
- Reported full repository suite: 393 passed, 0 failed, exit code 0.

## Re-review Summary
Most of the remaining review findings are now closed correctly:

1. `CANONICAL_FACTUAL_SIGNALS` now enforces the canonical factual signal-name → category pairing for the V1 market signals and rejects `INFERRED` provenance for them.
2. `SignalEvidence.raw_value_repr` now has bounded length, single-line enforcement, structured-payload/assignment character rejection, and broad sensitive-keyword rejection. The requested cookie/auth/token/secret/JSON/HTML regressions are present.
3. RESULT-011 now records the exact focused command `.\\venv\\Scripts\\python -m pytest tests/product_intelligence/ -v`, exit code 0, and 20 passed, plus the exact full-suite command with 393 passed.

The earlier M2.1 scoring-contract fixes also remain intact: available-data base-score renormalization, explicit `MISSING` signals with partial coverage, mandatory `evaluated_at`, canonical commission percentage-point units, strict policy validation, deterministic confidence damping, and no network/LLM/queue side effects.

One exact signal-identity gap remains from the prior review and still permits a semantic signal to masquerade as a factual observed signal.

## Blocking Finding — Known semantic signal names can still be moved into factual categories when marked `OBSERVED`

### Location
- `src/product_intelligence/models.py` — `NormalizedSignal.__post_init__`
- `tests/product_intelligence/test_models.py`

The new registry only covers canonical factual signal names. That correctly rejects examples such as `sold_volume` in `CONTENTABILITY` or `commission_rate` in `MOMENTUM`.

However, a known semantic signal such as `visual_demo_potential` is not registered. Therefore this remains constructible today:

- `name="visual_demo_potential"`
- `category=DEMAND`
- `provenance=OBSERVED`

It passes because:
- the name is not in `CANONICAL_FACTUAL_SIGNALS`;
- the category is not `CONTENTABILITY`, so the semantic-category `OBSERVED` guard does not run;
- factual categories only reject `INFERRED`, not a known semantic name marked `OBSERVED`.

This is the exact bypass called out in the previous review. The current regression checks `visual_demo_potential + DEMAND + INFERRED`, which is rejected by the generic category/provenance rule, but it does not cover `visual_demo_potential + DEMAND + OBSERVED`.

### Required Fix
Keep the fix small and platform-independent.

Add a minimal canonical semantic-signal contract for the known V1 semantic signal names used by this milestone (at minimum `visual_demo_potential`, plus any other named semantic signals the implementation exposes), mapping them to `CONTENTABILITY` and allowing `INFERRED`/`MISSING` but not `OBSERVED`.

Alternatively, use an equivalent centralized validator that guarantees known semantic V1 signal names cannot be placed into factual categories regardless of provenance.

Add a regression proving `visual_demo_potential + DEMAND + OBSERVED` is rejected, while extensible unknown semantic names remain allowed in `CONTENTABILITY` with `INFERRED` if that extensibility is intentionally retained.

Do not redesign scoring or add an LLM call/framework.

## Verification Notes
The evidence-safety finding from the previous review is resolved for TASK-011. Preserve the current bounded scalar validation and its regressions.

The RESULT evidence-format finding is also resolved: the exact focused/full commands, exit codes, and pass counts are now present.

The previously noted deep immutability of `WinningProductScore.category_scores` remains optional/non-blocking for TASK-011.

## Decision
CHANGES_REQUIRED.

Publish only through this exact updated REVIEW-011 artifact. Do not merge automatically. After the FIX is published, request `Review TASK-011` again.
