# TASK-013 — Phase 6 M2.2A Product Source Pack & Original Media Extraction V1

## Objective
Build a **canonical, evidence-first Product Source Pack** for selected Shopee and TikTok Shop product URLs and replace the current broad page-image scraping behavior with a deterministic seller-media extraction pipeline that prioritizes **original product media** and explicitly excludes review/comment/UGC images.

This is an inserted hardening milestone between merged M2.2 discovery and the planned M2.3 scoring/ranking work. It addresses a real deep-ingestion defect observed in prior runs: product scrapers can collect images from reviews/comments because their current DOM strategy scans broad page regions and relies on layout/position heuristics.

Canonical baseline when authored:
- `main`: `9d3dcfeab5ffc98bf6aeb3ef7a67912a5bc1fd52`
- TASK-012 / Phase 6 M2.2 Shopee Discovery Adapter V1: merged and authoritative
- Public `BrowserSession.evaluate(script)` from TASK-012 is available and should be preferred for DOM extraction through the existing browser abstraction
- Existing Phase 5.6 reliability and Phase 6 M1 queue semantics remain authoritative

The target architecture is:

```text
Selected product URL
  → platform ProductSourceExtractor
  → ProductSourcePack (facts + seller media refs + provenance)
  → OriginalMediaDownloader (byte-preserving source assets)
  → source_pack.json + original media files
  → existing storage/GDrive publication boundary
  → later Derived AI Assets (background removal / clean renders / multi-view / 360 reconstruction)
  → later Content Factory
```

TASK-013 does **not** generate AI images, remove backgrounds, synthesize 360° views, or write marketing copy. It builds the trusted source layer those later systems will depend on.

---

## Problem Statement

The current deep-ingestion tools are too permissive:

- Shopee extraction scans broad selectors including `[role="main"] img`, product-detail descendants, and background images, then tries to stop before reviews using Y-position and text/header heuristics.
- TikTok extraction scans essentially all page images/background images before a guessed review/recommendation Y boundary.

This is fragile. Marketplace layout changes, lazy hydration, review placement, banners, related products, or UGC using the same CDN can cause non-product images to be accepted as product originals.

TASK-013 must replace the core rule:

> “scan most of the page, then try to exclude review areas”

with:

> “extract only from positively identified seller-product sources, with structured data first and tightly scoped semantic containers second.”

No whole-page image sweep may be used as the normal or fallback success path.

---

## Core Principles

1. **Positive inclusion beats negative filtering.**
   Only accept media from sources that are positively identified as seller-owned product media.

2. **Structured product data first.**
   Prefer embedded product state / JSON-LD / structured page data that explicitly associates media with the current product.

3. **Semantic product containers second.**
   If structured data is unavailable, use platform-specific gallery, variant, and seller-description containers.

4. **No global DOM fallback.**
   If trusted extraction paths fail, fail closed or return explicit partial diagnostics. Do not scan every image on the page.

5. **Source originals are immutable evidence.**
   Seller media must be downloaded without watermarking, resizing, recomposition, background removal, or JPEG re-encoding.

6. **Unknown product facts remain unknown.**
   Brand, model, dimensions, material, claims, and other facts are populated only when observed in trusted structured/spec/description sources. Never infer them from an image or title in this task.

7. **Derived AI assets are a separate layer.**
   Future AI-generated clean renders / background-free images / inferred views must never overwrite or masquerade as seller-source originals.

---

## M2.2A.1 — Product Source Pack Contract

Add a small platform-independent package, suggested location:

`src/product_source/`

Suggested modules:
- `models.py`
- `extractor.py`
- `downloader.py`
- `serialization.py` if useful

### Required source pack concepts

#### `ProductSourcePack`
Immutable/canonical result containing at minimum:
- `source_pack_id`
- `platform`
- `product_url`
- `source_product_id` if observed
- `observed_at`
- `collector`
- `title`
- `shop_name` if observed
- `brand` if explicitly observed
- `model` / seller SKU if explicitly observed
- `description_text` if explicitly observed and safely bounded
- ordered immutable `facts`
- ordered immutable `media`
- deterministic diagnostic/reason codes

`source_pack_id` must be deterministic for the same platform/product identity. Prefer platform + source product ID; otherwise use a canonicalized URL fingerprint. Do not use Python `hash()`.

#### `ProductFact`
Represent source facts such as:
- brand
- model/SKU
- dimensions
- weight
- material
- color/variant labels
- specifications
- intended use / seller-stated benefits
- seller description claims

At minimum include:
- key/name
- value
- optional unit
- source section/type
- provenance/extraction strategy

Facts must remain source claims. Do not normalize a vague seller claim into a stronger factual assertion.

#### `OriginalMediaRef`
Represent a seller-source media reference before/after download, with at least:
- canonical/source URL
- platform
- media role
- provenance/extraction strategy
- deterministic ordinal / first-seen order
- optional seller-provided alt text
- optional variant label
- optional content type after download
- optional byte size after download
- optional SHA-256 content hash after download
- optional perceptual hash only as a duplicate aid, not as source identity

Suggested media roles:
- `PRIMARY`
- `GALLERY`
- `VARIANT`
- `SELLER_DESCRIPTION`

Review/comment/customer-uploaded media must **not** be represented as accepted original media.

Suggested provenance values:
- `STRUCTURED_PRODUCT_DATA`
- `SEMANTIC_PRODUCT_GALLERY`
- `SEMANTIC_VARIANT_MEDIA`
- `SEMANTIC_SELLER_DESCRIPTION`
- `PLATFORM_SCOPED_FALLBACK`

Do not use provenance values implying certainty when the extraction path is ambiguous.

---

## M2.2A.2 — Platform Source Extractor Interface

Introduce a platform-independent interface such as:

`ProductSourceExtractor.extract(product_url, *, observed_at=None) -> ProductSourcePack`

or async equivalent consistent with the browser stack.

Requirements:
- use the existing injected `BrowserManager` / `BrowserSession` abstraction;
- prefer `get_or_create_session(...)`, `navigate(...)`, and public `evaluate(...)` from TASK-012;
- do not reach into `PlaywrightBrowserSession._page` from Product Source code;
- do not construct a second browser framework;
- keep Shopee/TikTok DOM knowledge isolated in platform modules.

Suggested platform modules:
- `src/product_source/platforms/shopee.py`
- `src/product_source/platforms/tiktok.py`

---

## M2.2A.3 — Extraction Priority: Structured → Semantic Gallery → Scoped Fallback

Implement the following deterministic priority order independently for Shopee and TikTok.

### Priority 1 — Embedded structured product data

Inspect only data already delivered/rendered for the current product page, for example:
- JSON-LD `Product` objects;
- embedded application/json state associated with the product;
- clearly product-scoped serialized state already present in the page.

Extract only fields that can be tied to the current product identity.

Structured product media should be the preferred media source when it exposes product image arrays.

Do **not**:
- reverse-engineer or call private marketplace APIs directly as part of this task;
- bypass authentication/captcha/anti-bot controls;
- scrape arbitrary script blobs without product identity checks;
- treat unrelated recommendations or review payloads as current-product evidence.

### Priority 2 — Semantic product gallery / variant containers

When structured product media is missing/incomplete, extract from positively identified product-owned areas such as:
- main product image gallery/carousel;
- thumbnail strip associated with that gallery;
- seller-defined variant image controls associated with the product.

The extraction must be container/relationship based, not page-position based.

### Priority 3 — Seller description media

Seller-authored product-description images may be collected as `SELLER_DESCRIPTION`, separately labeled from gallery originals.

Only include images from a positively identified seller product-description/details container.

### Priority 4 — Platform-scoped fallback

A small platform-specific fallback is allowed only inside a known current-product container. It must remain bounded and deterministic.

Forbidden fallback patterns include broad success-path scans such as:
- `document.querySelectorAll('img')` across the page;
- `document.querySelectorAll('*')` for all background images;
- `[role="main"] img` without a tighter product ownership boundary;
- selecting images based primarily on `absoluteY`, “before reviews”, screen position, or arbitrary X/Y cutoffs.

If all trusted extraction paths fail, return/raise an explicit extraction failure. Do not silently downgrade to a global scan.

---

## M2.2A.4 — Review / UGC / Non-Product Media Exclusion

The accepted media set must exclude, by construction:
- review/rating/customer-uploaded images;
- comment media;
- shop-review media;
- user avatars/profile images;
- recommendation/similar-product images;
- “you may also like” product cards;
- promotional banners not belonging to the current product media set;
- unrelated navigation/app-shell imagery.

A same-CDN URL is **not** sufficient evidence that an image is seller product media.

Tests must include fixtures where gallery images and review images use the same host/domain, proving container/provenance rules — not hostname alone — determine acceptance.

If an element is under a known review/comment/rating/recommendation subtree, it must not be accepted even when its dimensions and CDN look like a product image.

---

## M2.2A.5 — Product Facts for Later Content Generation

Build the source pack so later AI systems can create reliable descriptions/content without hallucinating product details.

Collect when explicitly available:
- product title;
- shop/seller name;
- brand;
- model/SKU;
- variant names;
- dimensions / size fields;
- weight;
- material;
- capacity/power/technical specs;
- seller description;
- seller-stated use cases;
- seller-stated features/benefits.

Rules:
- structured/spec table evidence takes precedence over loose marketing prose when both express the same key;
- preserve provenance/source section;
- do not infer physical dimensions from pixels or images;
- do not infer brand/model from visual logos in TASK-013;
- do not convert seller marketing claims into verified scientific/performance claims;
- missing facts remain missing/`None`;
- keep raw description/spec text bounded to avoid giant page payloads.

No LLM call is required or allowed for canonical fact extraction in TASK-013.

---

## M2.2A.6 — Original Media Download Semantics

The existing `ImageProcessor.process_and_save()` re-encodes images as JPEG and is useful for transformed/derived workflows, but source originals must remain a separate evidence layer.

Add a small original-media downloader or backward-compatible original-download capability that:
- downloads only accepted `OriginalMediaRef` URLs;
- allows only `http`/`https` URLs;
- uses deterministic finite timeouts;
- validates that the response is an actual supported image;
- enforces conservative per-file byte limits (choose/document a V1 limit, e.g. 20 MiB);
- enforces a bounded maximum media count per product (choose/document a V1 ceiling, e.g. 30);
- writes the original response bytes without resize/watermark/recompression;
- derives extension/content type safely;
- calculates SHA-256 of the downloaded bytes;
- may calculate perceptual hash after decode for visual duplicate detection, while keeping SHA-256/source URL as evidence;
- does not embed cookies, auth headers, tokens, or credentials in manifests/logs.

Deduplication should occur in two stages:
1. deterministic canonical URL/source identity dedupe before download, preserving highest-confidence provenance and first useful order;
2. exact SHA-256 duplicate collapse after download.

Perceptual-hash near-duplicate collapse may be recorded as a diagnostic but must not delete distinct seller views aggressively in V1.

Do not mutate the original bytes to remove backgrounds or watermarks.

---

## M2.2A.7 — Source Pack Serialization / Storage Boundary

Persist a machine-readable `source_pack.json` (or equivalent deterministic JSON manifest) alongside accepted original images.

Manifest requirements:
- deterministic schema/version;
- platform/product identity;
- observed timestamp;
- source facts with provenance;
- accepted media refs/roles/provenance;
- local/or storage filenames after successful download;
- hashes/content type/byte size when available;
- concise diagnostics and missing fields;
- no raw HTML;
- no cookies/headers/tokens/credentials;
- no huge embedded image bytes/base64.

Keep the current GDrive publication role if the deep-ingestion tools require it, but publish the **source pack + original files**, not a transformed JPEG-only approximation.

A reasonable Drive layout is:

```text
<Shopee|TikTok>/<Product>/
  source_pack.json
  original/
    ...source images...
```

Exact folder naming may follow existing GDriveIntegrator capabilities.

If GDrive upload partially fails, preserve existing PARTIAL_SUCCESS semantics; do not claim the source pack is fully published when only some originals were uploaded.

---

## M2.2A.8 — Refactor Existing Deep-Ingestion Tools

Update `ShopeeScrapeTool` and `TikTokScrapeTool` to use the new source pack pipeline while preserving their public tool names and input schema.

Requirements:
- keep `shopee_scrape` / `tiktok_scrape` public tool contracts backward compatible;
- stop using broad whole-page image scans;
- stop using page Y-position / “before review heading” as the core media ownership rule;
- use the existing browser manager/session abstraction rather than assuming `browser.new_page()` exists on `PlaywrightBrowserManager`;
- do not call Product Intelligence scoring/ranking from deep ingestion;
- do not change AgentLoop/retry/checkpoint/idempotency semantics;
- return useful result metadata such as accepted original count, downloaded original count, uploaded count, and source pack identity.

Legacy `ImageProcessor` behavior may remain for future derived assets, but TASK-013 source originals must not pass through transformations that alter the bytes.

---

## M2.2A.9 — Derived AI Asset Boundary

Document, but do not implement, the next layer:

```text
ProductSourcePack + Original Seller Media
  → AI asset preparation
     - background removal
     - product isolation / alpha mask
     - clean studio render
     - alternate-view generation
     - multi-view / approximate 360 reconstruction
  → DerivedAssetManifest
```

Important semantic boundary:
- seller media/facts = `SOURCE` / observed evidence;
- AI-generated or reconstructed media = `DERIVED` / inferred;
- AI-generated views must never be represented as physically measured or seller-provided originals;
- exact 360° geometry cannot be guaranteed from sparse 2D seller images and must later carry an inferred/reconstructed label.

This boundary is required documentation because the source pack is being designed specifically to support later content generation safely.

---

## M2.2A.10 — Testability / Deterministic Fixtures

No live Shopee/TikTok test is required for approval. Use injected browser/session fixtures and local deterministic byte fixtures.

Suggested tests:
- `tests/product_source/test_models.py`
- `tests/product_source/test_shopee_source_extractor.py`
- `tests/product_source/test_tiktok_source_extractor.py`
- `tests/product_source/test_original_media_downloader.py`
- focused compatibility tests for the two scrape tools if needed.

Cover at least:

1. deterministic `source_pack_id` from platform/product ID;
2. deterministic URL-fingerprint fallback identity;
3. structured product image array is preferred over page-wide images;
4. structured current-product identity check prevents unrelated/recommendation payload use;
5. gallery fallback collects gallery images only;
6. seller-description images are separately labeled `SELLER_DESCRIPTION`;
7. variant images are separately labeled when explicit;
8. review image using the same CDN as gallery images is excluded;
9. comment/customer-uploaded media is excluded;
10. related/recommended product images are excluded;
11. banners/avatars/app-shell assets are excluded;
12. no accepted media exists solely because it appears before a review Y-coordinate;
13. no whole-page `img` sweep is used as a success fallback;
14. trusted extraction paths exhausted → explicit extraction failure, not broad scan;
15. malformed one media ref does not discard valid siblings;
16. canonical URL dedupe preserves first useful/highest-confidence provenance order;
17. repeated fixture + same `observed_at` serializes deterministically;
18. title/shop/brand/model/specs only populate when explicitly present;
19. missing dimensions/brand/model remain `None` / absent — no inference;
20. fact provenance points to structured/spec/description source type;
21. raw description/spec text is bounded;
22. downloader preserves exact original bytes;
23. downloader SHA-256 matches source bytes;
24. invalid/non-image payload rejected;
25. non-http(s) media URL rejected;
26. oversize media rejected deterministically;
27. exact byte-duplicate media collapses after download;
28. perceptual-hash near duplicates are not aggressively deleted by default;
29. source manifest contains no raw HTML/cookies/tokens/credentials/base64 image payload;
30. real project-style `BrowserManager.get_or_create_session()` + `BrowserSession.navigate/evaluate()` path works for both platform extractors;
31. `ShopeeScrapeTool` no longer requires `browser.new_page()` on a BrowserManager;
32. `TikTokScrapeTool` no longer requires `browser.new_page()` on a BrowserManager;
33. scrape tools do not call `ImageProcessor.process_and_save()` for source-original persistence;
34. scrape tools do not invoke LLM/provider/scoring/ranking/queue mutation;
35. partial download/upload returns honest partial semantics;
36. full focused tests pass;
37. full repository suite passes.

Aim for a focused, fixture-driven suite rather than brittle snapshots of live marketplace DOM.

---

## Documentation

Add a focused document such as:

`docs/PHASE_6_PRODUCT_SOURCE_PACK.md`

Document:
- why broad DOM scanning caused review-image contamination;
- trusted extraction priority: structured → gallery/variant → seller description → bounded scoped fallback;
- why global page scans and Y-coordinate review cutoffs are forbidden;
- Product Source Pack schema and provenance model;
- seller-media roles;
- product fact evidence policy;
- original-byte download semantics;
- URL + SHA-256 dedupe semantics;
- Source vs Derived AI Asset boundary;
- GDrive/source manifest layout;
- known platform DOM fragility and isolation strategy;
- next planned work: return to Product Intelligence M2.3 score/rank/shortlist, then build derived AI asset generation on top of trusted source packs.

Do not document credential handling tricks, captcha bypass, or scraping circumvention techniques.

---

## Acceptance Criteria

TASK-013 is ready for review only when all are true:

- canonical Product Source Pack contract exists;
- Shopee and TikTok platform source extractors exist behind a shared interface;
- structured current-product data is preferred when available;
- semantic gallery/variant/description extraction is used as bounded fallback;
- broad whole-page image scanning is removed from the deep-ingestion success path;
- review/comment/UGC images are excluded by source/container provenance, including same-CDN fixtures;
- no page-position/Y-coordinate heuristic is the primary media ownership rule;
- product facts have explicit provenance and no AI/image-based fact inference;
- source originals are saved byte-preserving, not re-encoded/watermarked/resized;
- deterministic media bounds and byte limits exist;
- canonical URL + SHA-256 dedupe exists;
- source_pack manifest contains no secrets/raw HTML/embedded image bytes;
- existing Shopee/TikTok scrape tool names/schemas remain backward compatible;
- tools work with the project's BrowserManager/BrowserSession abstraction;
- no LLM, Product Intelligence scoring, ranking, or queue mutation is introduced;
- focused tests pass;
- full repository tests pass;
- documentation matches implementation.

---

## Required Verification

Run at minimum:

```powershell
.\venv\Scripts\python -m pytest tests/product_source/ -v
.\venv\Scripts\python -m pytest tests/ -q -W ignore
```

If scraper compatibility tests live outside `tests/product_source/`, RESULT-013 must include those exact focused commands as well.

No live marketplace/network credentials are required for approval.

---

## RESULT-013 Requirements

Publish `.ai/results/RESULT-013.md` containing:
- `STATUS: READY_FOR_REVIEW` only when acceptance criteria are met;
- Task: `TASK-013`;
- action (`RUN` or `FIX`);
- exact authorized task/review artifact reference required by AIOS Bridge v0.4.0;
- branch name;
- reviewed baseline/main SHA if available;
- files changed and concise accurate diff stat;
- exact focused test command(s), exit code(s), and pass count(s);
- exact full-suite command, exit code, and total pass count;
- Product Source Pack schema/version summary;
- exact trusted media extraction priority;
- explicit review/UGC exclusion semantics;
- exact media-count and byte-size bounds;
- exact original-byte persistence semantics;
- exact URL/SHA-256 dedupe strategy;
- exact ProductFact missing/provenance policy;
- browser abstraction compatibility statement;
- explicit statement that no AI image generation/background removal/360 reconstruction/LLM/scoring/ranking/queue mutation occurs;
- known limitations intentionally retained;
- no auto-merge.

---

## Non-Goals

Do **not** in TASK-013:
- generate background-free product renders;
- generate 360° or novel product views;
- classify camera angle using AI;
- infer dimensions/material/brand/model from images;
- generate marketing descriptions/captions/videos;
- implement Product Intelligence M2.3 ranking/shortlist;
- auto-write candidates to `tasks.txt`;
- implement TikTok discovery search surface;
- build M3 entity resolution/Product KB/vector DB/RAG;
- redesign AgentLoop, retry, checkpoint, cancellation, budget, idempotency, production readiness, or AIOS Bridge;
- add captcha/anti-bot bypass or credential harvesting;
- auto-merge.

---

## Human Gate

Implementation begins only after explicit human authorization:

`/aios-worker RUN TASK-013`

After publication, review gate is:

`Review TASK-013`

Merge remains explicit:

`Merge TASK-013`
