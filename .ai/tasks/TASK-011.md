# TASK-011 — Phase 6 M2.1 Winning Product Intelligence Contracts & Score V1

## Objective
Establish the canonical, deterministic data and scoring contract for Phase 6 M2 Product Intelligence so later discovery adapters can collect cheap market observations and rank candidate products without coupling scoring logic to Shopee/TikTok page implementations or allowing an LLM to invent market facts.

This task is the **contract + pure scoring foundation** for M2. It is intentionally offline/no-network. It does not yet crawl marketplaces, auto-queue products, build the M3 Product Knowledge Base, or generate content.

Canonical baseline when authored:
- `main`: `a3ab8ee06495d06006d6d61d06313c8977f555f0`
- Phase 6 M1 bootstrap/autonomous queue: merged and complete
- Phase 5.6 production reliability controls remain authoritative

Planned M2 sequence after this task:
1. M2.2 — Discovery Adapters (cheap candidate collection; Shopee first, TikTok next)
2. M2.3 — Ranking/Shortlist integration over real snapshots
3. M2.4 — Human-approved shortlist → Phase 6 M1 ingestion queue
4. M3 — Canonical Product Knowledge Base

---

## Core Product-Intelligence Principle

M2 answers:

> “Among many candidate listings, which products deserve deeper Agent resources next, with a reproducible score, confidence, explanation, and evidence trail?”

Canonical flow:

```text
Discovery Adapter
  → ProductCandidateSnapshot
  → normalized/evidenced signals
  → WinningProductScorer (pure/deterministic)
  → WinningProductScore
  → later: ranking/shortlist/human approval
  → existing M1 deep-ingestion queue
```

The discovery layer must remain cheap and wide. Existing Shopee/TikTok deep ingestion remains expensive and narrow, only for selected candidates.

---

## M2.1.1 — Canonical Candidate Snapshot Contract

Introduce immutable typed models, suggested location:

`src/product_intelligence/models.py`

Required concepts:

### `ProductCandidateSnapshot`
Represents one marketplace listing observed at one point in time.

Required identity/source fields:
- `candidate_id: str`
- `platform: str` or a small enum (`shopee`, `tiktok`, extensible)
- `source_product_id: Optional[str]`
- `url: str`
- `observed_at: datetime` or UTC timestamp
- `collector: str`

Required descriptive fields:
- `title: str`
- `shop_id: Optional[str]`
- `shop_name: Optional[str]`
- `category: Optional[str]`
- `brand: Optional[str]`
- `model: Optional[str]`

Required market/economic fields, all nullable when not observed:
- `price: Optional[float]`
- `original_price: Optional[float]`
- `discount_percent: Optional[float]`
- `sold_count: Optional[int]`
- `rating: Optional[float]`
- `review_count: Optional[int]`
- `affiliate_commission_rate: Optional[float]`
- `estimated_commission_value: Optional[float]`
- `creator_count: Optional[int]`
- `video_count: Optional[int]`
- `similar_listing_count: Optional[int]`

Optional prior-observation deltas/derived metrics:
- `sales_velocity: Optional[float]`
- `review_velocity: Optional[float]`
- `creator_velocity: Optional[float]`
- `video_velocity: Optional[float]`

Rules:
- snapshot is immutable after construction;
- unknown values remain `None`; never invent `0` to mean missing;
- counts cannot be negative;
- price/commission/rating ranges are validated;
- `observed_at` is required for every volatile market snapshot;
- exact URL is preserved; aggressive URL canonicalization is out of scope;
- do not embed downloaded image bytes or deep-ingestion assets in this model.

### Snapshot vs Product Entity
A snapshot is a marketplace listing observation, **not** the canonical underlying product entity. Full cross-listing entity resolution belongs to M3. M2 may later carry a lightweight fingerprint/hint only.

---

## M2.1.2 — Evidence Contract

Every factual market signal used by the scorer must be traceable.

Introduce an immutable `SignalEvidence` concept with at least:
- `signal_name`
- `source_type` / platform
- `source_url` or stable source reference
- `observed_at`
- `collector`
- optional `raw_value_repr` safe for diagnostics
- optional `source_reliability` in `[0, 1]`

Evidence rules:
- no prompt, credential, cookie, secret, or large raw payload leakage;
- a numeric/market fact without evidence may still exist as an input object for tests, but confidence must reflect missing evidence;
- LLM-generated semantic assessments must be clearly labeled as inferred/semantic, never as observed marketplace facts.

Suggested signal provenance enum:
- `OBSERVED`
- `DERIVED`
- `INFERRED`
- `MISSING`

---

## M2.1.3 — Winning Product Score V1 Categories

Implement a pure deterministic scorer, suggested location:

`src/product_intelligence/scoring.py`

Overall V1 score is 0–100 with a full breakdown. Six categories are canonical:

1. **Demand — 25 points**
   - absolute demand evidence such as sold count / review depth / platform demand proxy.

2. **Momentum — 20 points**
   - sales velocity, review velocity, creator/video growth where observed.
   - velocity must come from multiple snapshots or explicit observed deltas; never infer time growth from one absolute count.

3. **Commercial Attractiveness — 15 points**
   - affiliate commission rate/value, discount/value proposition, price attractiveness.

4. **Trust — 10 points**
   - rating quality plus review-depth strength.
   - e.g. a high rating with very few reviews must not score like the same rating with substantial review evidence.

5. **Contentability — 15 points**
   - visual demo potential, problem/solution clarity, hookability/UGC potential.
   - these may be supplied later by a semantic assessor, but the core scorer only consumes explicit normalized signals; it does not call an LLM.

6. **Competition Opportunity — 15 points**
   - score is higher when saturation/competition is more favorable.
   - possible inputs include creator saturation, video saturation, similar listings, seller concentration.

Total category weights must equal exactly 100.

### Important Semantics
- category score is always “higher is better”; competition is represented as an **opportunity score**, not a negative-number special case;
- no hidden magic bonus/penalty outside the published breakdown;
- weights must live in one typed/configurable V1 policy object, not scattered constants;
- same inputs + same policy must produce byte-for-byte equivalent serialized scoring output where practical.

---

## M2.1.4 — Normalized Signal Contract

The scorer should consume normalized signal values in `[0, 1]` rather than hard-code Shopee/TikTok field names.

Introduce a typed concept similar to:

`NormalizedSignal(name, category, score, provenance, evidence_refs, freshness, source_reliability)`

Requirements:
- score must be in `[0,1]`;
- missing signal is explicit and not silently converted to zero data;
- provenance differentiates observed/derived/inferred/missing;
- evidence references are immutable;
- optional semantic signals are allowed but clearly marked `INFERRED`;
- no platform-specific branching in the core score aggregation.

Platform-specific normalization from raw candidate fields belongs to adapters/normalizers around the core scorer. A small generic V1 normalizer may be included only if it is deterministic and platform-independent.

---

## M2.1.5 — Missing Data & Confidence Policy

A high score with weak data must not outrank a slightly lower score backed by strong evidence without an explicit confidence penalty.

Implement `confidence` in `[0,1]` using a deterministic published breakdown. V1 default weights:

- **data completeness: 40%**
- **freshness: 25%**
- **source reliability: 20%**
- **evidence coverage: 15%**

The confidence subweights must sum to 1.0 and live in the scoring policy.

### Required scoring behavior

1. Calculate `base_score` from the category score over **available weighted signals/categories**, preserving a 0–100 scale.
2. Calculate deterministic `confidence` from the four confidence dimensions.
3. Calculate `final_score = base_score * confidence` for V1.
4. Missing data therefore cannot create an artificially excellent production rank merely because observed signals were strong.
5. Output must include `base_score`, `confidence`, and `final_score`; do not expose only the final number.

If the implementation uses a mathematically equivalent formulation, document it precisely and test the same invariants.

### Freshness
- freshness is computed from `observed_at`/signal observation timestamps and policy thresholds;
- the scorer receives an explicit evaluation timestamp (`evaluated_at`) so tests are deterministic;
- do not call `datetime.now()` internally in a way that makes repeated test results drift;
- default volatile-signal freshness windows may be configurable; do not hard-code marketplace-specific values throughout the scorer.

---

## M2.1.6 — Score Explanation Contract

Introduce immutable output models such as:

- `CategoryScore`
- `ConfidenceBreakdown`
- `WinningProductScore`

`WinningProductScore` must include at least:
- candidate identity/reference
- `base_score`
- `confidence`
- `final_score`
- category breakdown for all six categories
- key supporting signal names
- missing/weak signal names
- evidence references used
- deterministic reason codes, not only prose

Suggested reason-code examples:
- `STRONG_DEMAND`
- `HIGH_MOMENTUM`
- `FAVORABLE_ECONOMICS`
- `TRUST_SIGNAL_STRONG`
- `CONTENTABILITY_HIGH`
- `COMPETITION_FAVORABLE`
- `INSUFFICIENT_MOMENTUM_DATA`
- `COMMISSION_UNKNOWN`
- `STALE_MARKET_DATA`
- `LOW_EVIDENCE_COVERAGE`

Do not require LLM prose generation in this task. Human-readable prose may be derived later from deterministic reason codes.

---

## M2.1.7 — Initial Decision Bands

Provide a deterministic helper/classification for operator review. V1 defaults:

- `RECOMMENDED`: `final_score >= 80` **and** `confidence >= 0.75`
- `NEEDS_REVIEW`: `final_score >= 65` **and** `confidence >= 0.65`, but not RECOMMENDED
- `INSUFFICIENT_DATA`: `confidence < 0.50`
- `HOLD`: all other cases

These bands are advisory only in TASK-011.

**No candidate may be auto-written to `tasks.txt` in TASK-011.** Human approval remains mandatory before M1 ingestion until a later task explicitly changes that policy.

---

## M2.1.8 — LLM Boundary

The Product Intelligence core must make the following distinction explicit:

### LLM MAY later help infer semantic signals
Examples:
- category inference
- audience hypothesis
- problem/benefit extraction
- visual-demo potential
- hookability / UGC potential
- semantic duplicate hints

### LLM MUST NOT be source-of-truth for observed market facts
Examples it must not fabricate:
- sold count
- rating/review count
- commission rate
- price
- creator/video count
- sales velocity

TASK-011 scorer itself must make zero provider/LLM calls.

---

## M2.1.9 — Determinism / Purity / Safety

The scoring subsystem must be:
- pure and side-effect free;
- no network calls;
- no browser calls;
- no Google Drive calls;
- no filesystem mutation required for scoring;
- no checkpoint/retry/idempotency redesign;
- deterministic with explicit `evaluated_at`;
- safe for repeated evaluation of the same immutable snapshot/signals.

Phase 5.6 reliability control-plane semantics remain untouched.

---

## M2.1.10 — Tests

Add focused tests, suggested locations:

- `tests/product_intelligence/test_models.py`
- `tests/product_intelligence/test_scoring.py`

Cover at least:

1. immutable snapshot construction and serialization;
2. invalid negative counts rejected;
3. invalid rating/commission/normalized ranges rejected;
4. missing value remains missing, not zero;
5. category weights equal exactly 100;
6. confidence weights equal exactly 1.0;
7. identical input + policy + evaluated_at produces identical output;
8. score stays within 0–100;
9. confidence stays within 0–1;
10. final_score equals documented V1 confidence-adjusted score;
11. high base score with weak completeness gets materially reduced final score;
12. stronger evidence/freshness increases confidence without changing observed market facts;
13. missing evidence lowers evidence-coverage confidence;
14. stale signals lower freshness confidence deterministically;
15. one-snapshot absolute sold count cannot masquerade as velocity/momentum;
16. competition category remains “higher is better”;
17. semantic/inferred signal cannot be mislabeled as observed by helper constructors/validation;
18. score output lists missing/weak signals and deterministic reason codes;
19. RECOMMENDED threshold behavior at exact boundaries;
20. NEEDS_REVIEW threshold behavior at exact boundaries;
21. confidence < 0.50 yields INSUFFICIENT_DATA regardless of attractive base score;
22. scorer performs no LLM/provider/tool/network calls;
23. scorer performs no filesystem mutation;
24. serialization contains no secrets/raw payload blobs;
25. existing Phase 5.6 + Phase 6 M1 tests remain green.

Use synthetic fixtures only; no live marketplace/network credentials.

---

## M2.1.11 — Documentation

Add:

`docs/PHASE_6_M2_PRODUCT_INTELLIGENCE.md`

Document:
- M2 mission and boundary vs M1 and M3;
- discovery-cheap / ingestion-expensive architecture;
- candidate snapshot contract;
- evidence/provenance contract;
- six score categories and exact V1 weights;
- confidence formula and missing-data behavior;
- initial decision bands;
- LLM boundary;
- why score must remain explainable/reproducible;
- next milestone: real discovery adapters.

Include one synthetic worked example showing `base_score`, confidence components, final score, and decision band. Do not use live/sensitive credentials or claim marketplace metrics that were not actually collected.

---

## Acceptance Criteria

TASK-011 is ready for review only if all are true:

- canonical immutable candidate snapshot exists;
- explicit evidence/provenance contract exists;
- normalized signal contract is platform-independent;
- exactly six V1 categories exist with weights 25/20/15/10/15/15 = 100;
- confidence formula is explicit, deterministic, and uses 40/25/20/15 weighting;
- V1 final score is confidence-adjusted and cannot be inflated by sparse data;
- scoring output is explainable via breakdown + reason codes + evidence refs;
- decision bands are deterministic and advisory only;
- scorer makes no LLM/network/tool calls;
- no auto-queue or Product KB work is introduced;
- Phase 5.6 and Phase 6 M1 behavior remains untouched/backward compatible;
- focused tests pass;
- full repository suite passes;
- documentation matches implementation.

---

## Required Verification

Run at minimum:

```powershell
.\venv\Scripts\python -m pytest tests/product_intelligence/ -v
.\venv\Scripts\python -m pytest tests/ -q -W ignore
```

If the implementation places focused tests elsewhere, RESULT-011 must state the exact focused command.

---

## RESULT-011 Requirements

Publish `.ai/results/RESULT-011.md` containing:
- `STATUS: READY_FOR_REVIEW` only when acceptance criteria are met;
- Task: `TASK-011`;
- action (`RUN` or `FIX`);
- exact authorized task/review artifact reference required by AIOS Bridge v0.4.0;
- branch name;
- files changed and concise diff stat;
- exact focused test command + exit code + pass count;
- exact full-suite command + exit code + total pass count;
- exact scoring weights and confidence weights implemented;
- concise explanation of missing-data/final-score semantics;
- known limitations retained intentionally;
- no auto-merge.

---

## Non-Goals

Do **not** in TASK-011:
- crawl/search Shopee/TikTok or any external marketplace;
- modify the existing Shopee/TikTok deep-ingestion algorithms;
- auto-write selected products to `tasks.txt`;
- implement distributed discovery workers/schedulers;
- implement M3 canonical product entity resolution / vector DB / RAG;
- generate content/video/captions;
- publish affiliate posts;
- implement analytics optimization loops;
- let an LLM fabricate or directly assign observed-market numbers;
- redesign AgentLoop, checkpoint, retry, budget, cancellation, idempotency, readiness, or AIOS Bridge;
- auto-merge.

---

## Human Gate

Implementation begins only after explicit:

`/aios-worker RUN TASK-011`

After publication:

`Review TASK-011`

Merge remains a separate explicit human gate:

`Merge TASK-011`
