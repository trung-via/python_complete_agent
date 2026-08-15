# REVIEW-011 — TASK-011 (Phase 6 M2.1 Winning Product Intelligence Contracts & Score V1)

## Status
CHANGES_REQUIRED

## Reviewed Head
- Branch: `ai/task-011`
- Reviewed commit: `fb8c3862d855f9ca508f89d101dce76f56172762`
- Main baseline: `a3ab8ee06495d06006d6d61d06313c8977f555f0`
- Branch relation to main: ahead 5, behind 0 (fast-forward safe)
- Task artifact blob: `677b6f6dd635bfe78d712f492fc818c50f05d7c4`
- Prior CHANGES_REQUIRED authorization blob: `c7b49d1c5856bd63ffdc32135cad5ab21ba1f864`
- RESULT-011 blob: `e200c3f0e1a90677fda412af6f034ccbb995b5fc`
- RESULT action: `FIX`
- Exact FIX authorization recorded by worker: `.ai/reviews/REVIEW-011.md (c7b49d1c58)` — matches the prior review artifact exactly.
- Reported focused Product Intelligence suite: 20 passed, 0 failed, exit code 0.
- Reported full repository suite: 393 passed, 0 failed, exit code 0.

## Re-review Summary
The remaining code-level blocker is closed correctly.

`CANONICAL_SEMANTIC_SIGNALS` now registers the known V1 semantic contentability signals (`visual_demo_potential`, `problem_solution_clarity`, `hook_angles`, `ugc_creator_appeal`) and forces them into `CONTENTABILITY`. A known semantic signal can no longer be moved into a factual category even when mislabeled `OBSERVED`, while extensible custom semantic signals remain allowed in `CONTENTABILITY` with `INFERRED` provenance. The requested `visual_demo_potential + DEMAND + OBSERVED` regression is present.

The earlier M2.1 contract fixes also remain intact: canonical factual signal/category mapping, provenance boundaries, bounded evidence serialization, available-data base-score renormalization, explicit `MISSING` signals with partial coverage, mandatory `evaluated_at`, percentage-point commission units, strict scoring-policy validation, deterministic confidence damping, and no network/LLM/queue side effects.

No additional source-code blocker was found in this re-review.

## Blocking Finding — RESULT-011 still does not satisfy its explicit durable-result requirements

### Location
`.ai/results/RESULT-011.md`

TASK-011 explicitly requires RESULT-011 to contain, in addition to commands/pass counts:
- the exact six scoring weights implemented;
- the exact four confidence weights implemented;
- a concise explanation of missing-data / `base_score` / `confidence` / `final_score` semantics;
- known limitations intentionally retained;
- an explicit no-auto-merge statement.

The current RESULT records the exact focused/full commands and pass counts and accurately describes the latest semantic-registry FIX, but it still omits those required durable contract fields.

This is now an artifact/evidence-only blocker. The reviewed source implementation itself is acceptable for TASK-011.

### Required Fix
Refresh `.ai/results/RESULT-011.md` without changing scoring behavior. Add durable entries that state at minimum:

- Category weights: `Demand 25`, `Momentum 20`, `Commercial Attractiveness 15`, `Trust 10`, `Contentability 15`, `Competition Opportunity 15`.
- Confidence weights: `Completeness 0.40`, `Freshness 0.25`, `Source Reliability 0.20`, `Evidence Coverage 0.15`.
- Missing-data semantics: `base_score` is renormalized over available categories; missing expected signals reduce completeness/confidence rather than double-penalizing `base_score`; `final_score = base_score * confidence`.
- Known limitations: M2.1 remains offline/synthetic, no real marketplace discovery, no auto-queue, no M3 entity resolution, no content/distribution work.
- Explicit statement that TASK-011 is not auto-merged.

Preserve the already-correct exact verification evidence:
- `.\venv\Scripts\python -m pytest tests/product_intelligence/ -v` → 20 passed, exit code 0.
- `.\venv\Scripts\python -m pytest tests/ -q -W ignore` → 393 passed, exit code 0.

No source-code change is required for this review finding unless the worker discovers a genuine regression while refreshing the result artifact.

## Verification Notes
The semantic signal identity/provenance blocker is resolved. The evidence-safety blocker is resolved. The deterministic scoring and confidence contracts are acceptable. The task branch remains fast-forward safe against the pinned main baseline.

The previously noted deep immutability of `WinningProductScore.category_scores` remains optional/non-blocking for TASK-011.

## Decision
CHANGES_REQUIRED.

This is an evidence-only finalization fix. Publish only through this exact updated REVIEW-011 artifact. Do not merge automatically. After the refreshed RESULT is published, request `Review TASK-011` again.
