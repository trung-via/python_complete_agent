# REVIEW-011 — TASK-011 (Phase 6 M2.1 Winning Product Intelligence Contracts & Score V1)

## Status
CHANGES_REQUIRED

## Reviewed Head
- Branch: `ai/task-011`
- Reviewed commit: `0efaac1ce0e6317fb87ab4b354b82fdc4d248c58`
- Main baseline: `a3ab8ee06495d06006d6d61d06313c8977f555f0`
- Branch relation to main: ahead 2, behind 0 (fast-forward safe)
- Task artifact blob: `677b6f6dd635bfe78d712f492fc818c50f05d7c4`
- Prior CHANGES_REQUIRED authorization blob: `6b65308264097fea6d525924f645a95fb8eb8719`
- RESULT-011 blob: `c20985398732cf489c4b3a013c21e608fc92d691`
- RESULT action: `FIX`
- Exact FIX authorization recorded by worker: `.ai/reviews/REVIEW-011.md (6b65308264)` — matches the prior review artifact exactly.
- Reported focused Product Intelligence suite: 19 passed, 0 failed, exit code 0.
- Reported full repository suite: 392 passed, 0 failed, exit code 0.

## Re-review Summary
The four blockers from the previous review are materially fixed:

1. `base_score` is now renormalized over available categories to a 0–100 scale, while missing expected snapshot signals are emitted explicitly as `MISSING` and partial category coverage feeds confidence rather than double-penalizing the base score.
2. The canonical scorer and normalizer now require explicit `evaluated_at`; the wall-clock fallback was removed from the pure path.
3. `affiliate_commission_rate` now has one canonical unit: percentage points in `[0,100]`, and normalization is continuous around `1.0`.
4. `ScoringPolicy` now rejects invalid/non-finite weights and out-of-range thresholds, and RESULT evidence was refreshed with a real diff stat and focused/full verification counts.

These fixes are good. Two remaining contract-level gaps still block approval because TASK-011 is the authority that later M2.2 adapters and semantic assessors will depend on.

## Blocking Finding 1 — Provenance rules are still descriptive, not enforced; inferred semantic data can impersonate observed market facts

### Location
- `src/product_intelligence/models.py` — `NormalizedSignal`
- `src/product_intelligence/scoring.py` — public `score()` aggregation
- `tests/product_intelligence/`

TASK-011 explicitly requires that semantic/inferred signals cannot be mislabeled as observed by validation/helper constructors, and the LLM boundary says inferred semantic assessments must never become source-of-truth market facts.

Current `NormalizedSignal` validates numeric ranges but does not validate the relationship between signal identity/category and provenance. Therefore callers can legally construct examples such as:

- `commission_rate` or `sold_volume` with `provenance=INFERRED`, then pass it to `WinningProductScorer.score()`;
- `visual_demo_potential` with `provenance=OBSERVED` even though the contract defines it as semantic/inferred;
- arbitrary inferred signals in Demand, Momentum, Commercial, Trust, or Competition categories.

The scorer treats every non-`MISSING` signal as available scoring evidence regardless of provenance, so an LLM-side semantic producer could directly influence factual market categories without violating any runtime validation. This defeats the canonical M2.1 LLM boundary and leaves M2.2/M2.3 vulnerable to accidental provenance drift.

### Required Fix
Add a small canonical signal/provenance validation contract without redesigning the scorer. A minimal acceptable approach is a typed/central registry or validator that defines the canonical V1 signal names/categories and allowed provenance classes, then rejects illegal combinations before scoring.

At minimum:
- factual marketplace signals used for Demand/Momentum/Commercial/Trust/Competition must not accept `INFERRED` provenance;
- semantic Contentability signals must not be silently presented as `OBSERVED` marketplace facts;
- `MISSING` signals must remain non-contributing and structurally consistent;
- direct public `score()` must enforce the rule as well as `score_snapshot()`;
- add targeted regression tests for the explicit TASK-011 requirement that inferred/semantic signals cannot masquerade as observed facts.

Keep the implementation small and platform-independent. Do not add an LLM call or a new framework.

## Blocking Finding 2 — Evidence serialization still permits raw secret/payload leakage despite the evidence-safety contract

### Location
`src/product_intelligence/models.py` — `SignalEvidence.raw_value_repr` / `to_dict()`.

TASK-011 requires evidence to avoid prompt, credential, cookie, secret, or large raw payload leakage, and its verification list requires serialization to contain no secrets/raw payload blobs.

Current `SignalEvidence` accepts an unrestricted `raw_value_repr: Optional[str]` and serializes it verbatim. The existing test only checks that dictionary key names like `token`, `cookie`, and `secret` are absent; it does not prevent a caller from placing a bearer token, cookie string, prompt, signed URL fragment, or a very large HTML/JSON payload inside `raw_value_repr` itself.

This becomes important as soon as M2.2 adapters consume real marketplace responses: a debugging shortcut could permanently copy sensitive/raw source material into score evidence and downstream artifacts.

### Required Fix
Make `raw_value_repr` a genuinely safe diagnostic scalar rather than an unrestricted payload channel. A minimal solution should:
- enforce a conservative bounded length;
- reject multiline/large raw payload-like content, or route construction through a safe scalar formatter;
- document that adapters must supply only scalar market-value representations, never headers/cookies/tokens/raw HTML/JSON;
- add regressions proving oversized/raw-payload-like evidence is rejected or safely bounded before serialization.

Do not build a generic secret-scanning framework; this should stay a small contract-level guard.

## Verification Notes
What is now correct and should be preserved:
- six canonical category weights remain `25/20/15/10/15/15 = 100`;
- confidence remains `40/25/20/15 = 1.0`;
- `final_score = base_score * confidence` remains explicit;
- sparse strong evidence can retain a high base score while low completeness damps final score;
- individual expected snapshot signals now produce partial coverage rather than binary category coverage;
- deterministic `evaluated_at` is mandatory;
- commission normalization is percentage-point based and continuous;
- policy validation is fail-fast;
- scorer remains offline/pure with no queue write, Product KB work, or Phase 5.6 redesign;
- RESULT now contains a non-empty FIX diff stat and reports focused 19 / full 392 passing.

The previous non-blocking note about deep immutability of the `category_scores` mapping remains optional for this task.

## Decision
CHANGES_REQUIRED.

Publish only through this exact updated REVIEW-011 artifact. Do not merge automatically. After the FIX is published, request `Review TASK-011` again.