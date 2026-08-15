# TASK-012 — Phase 6 M2.2 Shopee Discovery Adapter V1

## Objective
Implement the first real Product Intelligence discovery adapter: a **cheap, bounded Shopee candidate collector** that discovers marketplace listings from a keyword/search surface and emits canonical M2.1 `ProductCandidateSnapshot` objects without performing deep ingestion, image downloading, Google Drive upload, scoring, ranking, or queue mutation.

This task turns the merged M2.1 scoring/data contract into a real upstream data source while preserving the architecture:

```text
Shopee search/discovery surface
  → ShopeeDiscoveryAdapter
  → ProductCandidateSnapshot[]
  → later M2.3 normalization/scoring/ranking
  → later M2.4 human-approved queue handoff
  → existing M1 deep ingestion
```

Canonical baseline when authored:
- `main`: `68db4d45154994c929bae22e660f1aca236e2bcd`
- TASK-011 / Phase 6 M2.1: merged and authoritative
- Existing Shopee/TikTok scrape tools remain deep-ingestion tools and must not be repurposed as discovery crawlers
- Phase 5.6 production reliability semantics and Phase 6 M1 queue semantics remain authoritative

---

## Core Principle
Discovery is **cheap and wide**; ingestion is **expensive and narrow**.

TASK-012 must not open every discovered product detail page, download product images, invoke an LLM, score products, upload to Drive, or write candidates into `tasks.txt`.

The adapter collects only fields that are actually visible/available from the discovery/search surface. Unavailable facts stay `None`; never infer or fabricate marketplace metrics.

---

## M2.2.1 — Discovery Request / Result Contract

Add a small platform-independent discovery contract, suggested location:

`src/product_intelligence/discovery.py`

Required concepts:

### `DiscoveryRequest`
Immutable request with at least:
- `query: str`
- `max_candidates: int`
- optional `max_pages: int = 1`
- optional locale/market hint if genuinely needed by the adapter

Validation:
- query must be non-empty after trim;
- `max_candidates` must be bounded and positive (choose a conservative V1 ceiling, e.g. 100);
- `max_pages` must be bounded and positive (e.g. 1–5);
- no unbounded crawling mode.

### `DiscoveryBatch`
Immutable result with at least:
- `platform`
- `query`
- `observed_at`
- ordered tuple/list of `ProductCandidateSnapshot`
- `pages_examined`
- `raw_items_seen`
- deterministic diagnostic/reason codes for partial/empty extraction where useful

The batch must not contain raw HTML, cookies, credentials, or large page payloads.

### Adapter interface
Introduce a small protocol/ABC such as:

`ProductDiscoveryAdapter.discover(request, *, observed_at=None) -> DiscoveryBatch`

or an async equivalent consistent with the existing browser stack.

Keep the interface platform-independent. Shopee-specific DOM rules belong only in the Shopee adapter.

---

## M2.2.2 — Shopee Discovery Adapter

Add a Shopee implementation, suggested location:

`src/product_intelligence/adapters/shopee.py`

Requirements:

1. **Dependency injection**
   - consume an injected browser/browser-manager dependency compatible with the existing project browser abstraction;
   - do not construct a second unrelated browser framework;
   - no Google Drive, image processor, provider/LLM, checkpoint, or queue dependency.

2. **Search URL construction**
   - build Shopee search/discovery URLs from the request query using proper URL encoding;
   - URL construction must be deterministic and unit-testable;
   - no credential/token embedding.

3. **Bounded browsing**
   - inspect at most `max_pages` and stop once `max_candidates` unique candidates are collected;
   - sequential browsing is acceptable/preferred for V1;
   - no background daemon or infinite scrolling loop;
   - if light scrolling is needed to hydrate listing cards, it must use a fixed deterministic bound, not “scroll until nothing changes forever”.

4. **Cheap listing-card extraction**
   - extract candidate data from Shopee search/listing cards only;
   - do not open every product detail page in TASK-012;
   - collect only fields available on the listing/search surface.

5. **Snapshot mapping**
   Populate M2.1 `ProductCandidateSnapshot` fields where actually observed, at minimum when available:
   - `platform="shopee"`
   - `source_product_id`
   - exact product/listing URL
   - `title`
   - `price`
   - `original_price`
   - `discount_percent`
   - `sold_count`
   - `rating`
   - `review_count`
   - `shop_name` if visible
   - `observed_at`
   - `collector` identifying the Shopee discovery adapter/version

   Fields not available on the search surface — especially affiliate commission, creator/video counts, velocity metrics — must remain `None`.

6. **Stable candidate identity**
   - `candidate_id` must be deterministic across repeated collection of the same Shopee listing;
   - prefer stable Shopee item/product ID when extractable;
   - otherwise derive from a documented stable URL identity/fingerprint, not Python's process-randomized `hash()`;
   - duplicate cards for the same listing in one run must collapse to one candidate while preserving first-seen order.

7. **No fabricated momentum**
   - one search observation may provide absolute sold/review counts only;
   - do not populate `sales_velocity`, `review_velocity`, `creator_velocity`, or `video_velocity` from a single snapshot.

---

## M2.2.3 — Deterministic Marketplace Scalar Parsing

Create small pure parsing helpers for marketplace strings returned by the Shopee discovery surface. Suggested location:

`src/product_intelligence/adapters/shopee_parsing.py`

At minimum cover the V1 values needed by the snapshot:
- localized price text;
- sold-count text;
- rating text;
- review-count text;
- discount percent where exposed;
- source product ID / item ID from stable link/attributes where possible.

Rules:
- parsing helpers are pure and deterministic;
- malformed/unknown text returns `None`, not zero;
- no exception from one malformed card should abort an otherwise valid discovery batch;
- support common Vietnamese marketplace abbreviations encountered in fixtures, such as `k`/`K`, `tr`/`triệu` where applicable, and decimal comma/dot forms where unambiguous;
- do not over-guess ambiguous values;
- counts/prices must never become negative.

Do not create a generic international-number framework in this task.

---

## M2.2.4 — Extraction Safety / Failure Semantics

Discovery is an external I/O boundary, so failure behavior must be explicit.

Required behavior:

- invalid request → fail immediately before browser use;
- missing browser dependency → explicit dependency/configuration error;
- navigation failure on the only/first page → return/raise a clear discovery failure according to the chosen typed contract; do not fabricate an empty successful marketplace result;
- extraction failure for one malformed card → skip that card and continue deterministically;
- page-level extraction failure after earlier pages produced valid candidates → partial batch may be returned with a deterministic diagnostic/reason code;
- captcha/challenge/blocked-page indicators, if detected, must not be interpreted as a valid zero-result search;
- no raw page body, cookies, headers, tokens, or credentials in exceptions/result serialization;
- ordinary empty search with a successfully parsed listing container may legitimately return zero candidates.

Keep failure handling local to discovery. Do not redesign AgentLoop/retry/checkpoint/idempotency.

---

## M2.2.5 — Evidence / M2.1 Boundary

TASK-012 emits canonical snapshots; it must respect the evidence/provenance boundaries established by TASK-011.

Requirements:
- observed numeric fields come only from actual extracted marketplace values;
- unknown values remain `None`;
- semantic/contentability values are not generated here;
- no LLM-generated market facts;
- the adapter must preserve enough source identity (`url`, `source_product_id`, `collector`, `observed_at`) for the existing M2.1 normalizer/evidence layer to create traceable facts later;
- do not weaken `SignalEvidence`, signal registries, scoring policy, or confidence semantics.

---

## M2.2.6 — No Coupling to Deep Ingestion

The existing `ShopeeScrapeTool` is a deep-ingestion tool that navigates product detail pages, extracts images, downloads/processes them, and uploads artifacts to Google Drive.

TASK-012 must **not** call that tool from discovery and must not copy its image/GDrive workflow into Product Intelligence.

It is acceptable to reuse small safe ideas/utilities where genuinely generic, but discovery must remain an independent lightweight adapter.

Do not modify `ShopeeScrapeTool` unless a tiny backward-compatible shared helper extraction is objectively necessary. Prefer leaving deep-ingestion behavior untouched.

---

## M2.2.7 — Testability / Browser Fixtures

Add focused tests with no live Shopee network requirement.

Suggested locations:
- `tests/product_intelligence/test_discovery_contract.py`
- `tests/product_intelligence/test_shopee_parsing.py`
- `tests/product_intelligence/test_shopee_discovery.py`

Use fake/injected browser/page objects or deterministic saved HTML-like extraction fixtures. Do not require login, cookies, marketplace credentials, or live internet.

Cover at least:

1. empty/blank query rejected before browser use;
2. invalid `max_candidates` rejected;
3. invalid `max_pages` rejected;
4. deterministic encoded Shopee search URL;
5. listing maps to canonical `ProductCandidateSnapshot`;
6. unavailable commission/creator/video/velocity fields remain `None`;
7. deterministic `candidate_id` for the same listing across runs;
8. duplicate listing cards dedupe while preserving first-seen order;
9. `max_candidates` is enforced;
10. `max_pages` is enforced;
11. price parser handles representative valid fixture forms;
12. sold-count parser handles plain, `k`, and Vietnamese million-style fixture forms conservatively;
13. malformed price/count/rating returns `None`, not zero;
14. one malformed card does not discard valid siblings;
15. successful true-empty search returns an empty batch;
16. blocked/captcha-like page is not classified as an ordinary empty search;
17. first-page navigation failure does not produce fabricated successful empty output;
18. later page failure after valid earlier candidates produces explicit partial diagnostics if partial behavior is implemented;
19. no product-detail page is opened for each result in the normal discovery path;
20. no image processor/GDrive/provider/LLM/queue dependency or side effect is invoked;
21. serialized result contains no raw HTML/cookies/tokens/credentials;
22. repeated same fixture + same `observed_at` yields deterministic serialized candidate ordering/content;
23. existing M2.1 Product Intelligence tests remain green;
24. existing Phase 5.6 + Phase 6 M1 tests remain green.

Aim for roughly 20–35 focused tests rather than a large brittle fixture suite.

---

## M2.2.8 — Documentation

Extend `docs/PHASE_6_M2_PRODUCT_INTELLIGENCE.md` or add a focused discovery document such as:

`docs/PHASE_6_M2_DISCOVERY.md`

Document:
- why discovery is cheap/wide and deep ingestion is expensive/narrow;
- discovery request/result contract;
- Shopee adapter boundaries;
- exact fields available/unavailable in V1;
- candidate identity/dedup rules;
- parsing semantics and missing-value policy;
- failure/blocked-page semantics;
- no LLM/no scoring/no queue/no GDrive guarantees;
- next milestone: M2.3 normalization + score/rank/shortlist over discovered snapshots;
- known fragility: marketplace DOM/layouts can change and adapters are isolated specifically so platform changes do not contaminate the core scorer.

Do not document live credentials or scraping-bypass techniques.

---

## Acceptance Criteria

TASK-012 is ready for review only when all are true:

- a platform-independent discovery request/result/adapter contract exists;
- a bounded Shopee discovery adapter exists;
- adapter outputs canonical M2.1 `ProductCandidateSnapshot` objects;
- stable candidate identity and deterministic first-seen dedupe are implemented;
- no unobserved marketplace metric is fabricated;
- no velocity is inferred from a single observation;
- parsing is deterministic and malformed values become `None`;
- blocked/navigation failure is not silently converted into a legitimate empty market result;
- normal discovery does not deep-open every listing;
- no image download, Google Drive, LLM/provider, scoring, ranking, or `tasks.txt` mutation occurs;
- M2.1 scoring/evidence contracts remain unchanged/backward compatible unless a review-justified minimal compatibility fix is necessary;
- focused tests pass;
- full repository tests pass;
- documentation matches implementation.

---

## Required Verification

Run at minimum:

```powershell
.\venv\Scripts\python -m pytest tests/product_intelligence/ -v
.\venv\Scripts\python -m pytest tests/ -q -W ignore
```

If focused discovery tests are located elsewhere, RESULT-012 must state the exact command in addition to the Product Intelligence suite.

No live marketplace/network test is required for approval of TASK-012; deterministic adapter behavior must be proven with injected fixtures/fakes.

---

## RESULT-012 Requirements

Publish `.ai/results/RESULT-012.md` containing:
- `STATUS: READY_FOR_REVIEW` only when acceptance criteria are met;
- Task: `TASK-012`;
- action (`RUN` or `FIX`);
- exact authorized task/review artifact reference required by AIOS Bridge v0.4.0;
- branch name;
- reviewed baseline/main SHA if available;
- files changed and concise diff stat;
- exact focused test command(s), exit code(s), and pass count(s);
- exact full-suite command, exit code, and total pass count;
- concise statement of discovery bounds (`max_candidates`, `max_pages` ceiling);
- exact candidate identity/dedup strategy;
- exact missing-value policy;
- exact blocked/navigation failure semantics;
- explicit statement that no deep ingestion/GDrive/LLM/scoring/ranking/queue mutation is performed;
- known limitations intentionally retained;
- no auto-merge.

---

## Non-Goals

Do **not** in TASK-012:
- implement TikTok discovery yet;
- implement cross-platform ranking/shortlist orchestration (M2.3);
- auto-write candidates to `tasks.txt` (M2.4);
- build M3 canonical product entity resolution/Product KB/vector DB/RAG;
- generate content/video/captions;
- publish affiliate posts;
- implement analytics optimization loops;
- add anti-bot/captcha bypass mechanisms or credential harvesting;
- redesign AgentLoop, checkpoint, retry, cancellation, budget, idempotency, production readiness, or AIOS Bridge;
- auto-merge.

---

## Human Gate

Implementation begins only after explicit human authorization:

`/aios-worker RUN TASK-012`

After publication, review gate is:

`Review TASK-012`

Merge remains explicit:

`Merge TASK-012`
