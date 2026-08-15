# REVIEW-011 — TASK-011 (Phase 6 M2.1 Winning Product Intelligence Contracts & Score V1)

## Status
CHANGES_REQUIRED

## Reviewed Head
- Branch: `ai/task-011`
- Reviewed commit: `2eb0fbc390e0c60051e72dfc055862523f61e5d1`
- Main baseline: `a3ab8ee06495d06006d6d61d06313c8977f555f0`
- Branch relation to main: ahead 3, behind 0 (fast-forward safe)
- Task artifact blob: `677b6f6dd635bfe78d712f492fc818c50f05d7c4`
- Prior CHANGES_REQUIRED authorization blob: `028595bba76fe08c048306c9f5d3ab9730dae643`
- RESULT-011 blob: `dfac2c7a4e4ab81780d54523fda8f3a4df5c9805`
- RESULT action: `FIX`
- Exact FIX authorization recorded by worker: `.ai/reviews/REVIEW-011.md (028595bba7)` — matches the prior review artifact exactly.
- Reported focused Product Intelligence suite: 20 passed, 0 failed, exit code 0.
- Reported full repository suite: 393 passed, 0 failed, exit code 0.

## Re-review Summary
The previous two findings were partially addressed in the right direction:

1. `NormalizedSignal` now rejects `INFERRED` provenance in factual score categories, rejects `OBSERVED` provenance in `CONTENTABILITY`, and makes `MISSING` signals structurally non-contributing.
2. `SignalEvidence.raw_value_repr` now has a 120-character bound, rejects multiline strings, and blocks several obvious bearer/cookie/HTML/JSON markers.

These are useful improvements, and the earlier M2.1 fixes remain intact: available-data base-score renormalization, explicit missing signals/partial coverage, mandatory `evaluated_at`, percentage-point commission units, strict policy validation, deterministic confidence damping, and no network/LLM/queue side effects.

Two contract gaps remain before M2.2 adapters should depend on this foundation.

## Blocking Finding 1 — Provenance validation is category-only; canonical signal identity/category pairing is still unenforced

### Location
- `src/product_intelligence/models.py` — `NormalizedSignal.__post_init__`
- `src/product_intelligence/normalizer.py` — canonical V1 signal names emitted by the snapshot normalizer
- `tests/product_intelligence/`

The updated validator checks only the category/provenance pair. It still permits a caller to move a semantic or factual signal into the wrong category and thereby bypass the intended boundary. For example, these structurally invalid combinations remain constructible:

- `visual_demo_potential` + `DEMAND` + `OBSERVED`
- `sold_volume` + `CONTENTABILITY` + `INFERRED`
- `commission_rate` + an unrelated factual category with otherwise allowed provenance

That means the system still lacks the small canonical V1 signal registry/validator requested in the prior review: signal name → canonical category → allowed provenance class. Category-only validation prevents one class of misuse but does not make the scoring contract authoritative for M2.2/M2.3 producers.

### Required Fix
Add a minimal platform-independent V1 signal contract/registry for the canonical factual signals emitted by the normalizer, at least:

- `sold_volume` → `DEMAND`
- `review_depth` → `DEMAND`
- `sales_velocity` → `MOMENTUM`
- `creator_growth` → `MOMENTUM`
- `commission_rate` → `COMMERCIAL_ATTRACTIVENESS`
- `discount_appeal` → `COMMERCIAL_ATTRACTIVENESS`
- `rating_quality` → `TRUST`
- `market_whitespace` → `COMPETITION_OPPORTUNITY`
- `creator_whitespace` → `COMPETITION_OPPORTUNITY`

Canonical factual signal names must reject wrong categories and must reject `INFERRED`. Contentability may remain extensible for semantic signal names, but it must reject `OBSERVED` marketplace provenance. `MISSING` instances must remain consistent with the same canonical category contract.

Add targeted regressions showing wrong-name/wrong-category combinations are rejected, not merely wrong provenance within an already-correct category. This can stay as a small validator; do not add a framework or LLM call.

## Blocking Finding 2 — `raw_value_repr` is still an arbitrary short string channel, so common credential/cookie/payload forms still serialize

### Location
`src/product_intelligence/models.py` — `SignalEvidence.raw_value_repr` validation.

The new length/multiline checks are good, but the denylist is too narrow to satisfy the evidence contract. The current forbidden tokens cover `bearer `, `set-cookie:`, a few HTML tags, and the exact JSON opener `{"`. Common sensitive/payload forms can still pass, for example:

- `cookie=session=abc`
- `authorization: Basic abc`
- `token=abc`
- `secret=abc`
- JSON-like text with whitespace such as `{ "x": 1 }`
- other short raw markup/payload fragments

Because `raw_value_repr` is serialized verbatim, a real M2.2 adapter can still accidentally persist sensitive debug material while satisfying all current validation.

### Required Fix
Keep this small, but make `raw_value_repr` a genuinely constrained scalar representation rather than an arbitrary short string. Prefer either:

- a safe scalar formatter/constructor that accepts only scalar market values and produces the representation, or
- a stricter validation contract that rejects credential/header/key-value/payload-like forms broadly enough to cover cookie/token/authorization/secret and JSON/markup cases.

Add regressions for at least generic cookie, authorization/token/secret, whitespace-variant JSON, oversized, multiline, and HTML/payload attempts. Do not build a general secret scanner.

## RESULT Evidence Finding
`RESULT-011` now contains a real diff stat and reports focused/full pass counts. However, the focused test entry is still recorded as shorthand `pytest tests/product_intelligence/ -v`, while TASK-011 requires the exact focused command and exit code. Refresh the result with the actual executed command, ideally the required `.\venv\Scripts\python -m pytest tests/product_intelligence/ -v`, plus exit code and pass count.

## Verification Notes
Preserve the currently-correct behavior:
- six category weights `25/20/15/10/15/15 = 100`;
- confidence weights `40/25/20/15 = 1.0`;
- `final_score = base_score * confidence`;
- available-data base score is renormalized independently from completeness;
- expected missing signals reduce confidence rather than double-penalizing base score;
- `evaluated_at` is mandatory;
- commission rate is percentage points `[0,100]`;
- policy validation fails fast;
- scorer stays offline/pure and does not auto-write to the M1 queue.

The previously noted deep immutability of `WinningProductScore.category_scores` remains optional/non-blocking for TASK-011.

## Decision
CHANGES_REQUIRED.

Publish only through this exact updated REVIEW-011 artifact. Do not merge automatically. After the FIX is published, request `Review TASK-011` again.
