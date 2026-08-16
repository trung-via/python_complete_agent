# REVIEW-013 — TASK-013 (Phase 6 M2.2A Product Source Pack & Original Media Extraction V1)

## Status
CHANGES_REQUIRED

## Reviewed Head
- Branch: `ai/task-013`
- Reviewed commit: `2b2e7a4fd209c0fda7aaa482b1da418dcc91e42a`
- Parent reviewed head: `a45cb80e242f7e4b25afa40860f2e0ecb2907e1d`
- Main baseline/current main: `9d3dcfeab5ffc98bf6aeb3ef7a67912a5bc1fd52`
- Branch relation to main: ahead 10, behind 0 (fast-forward safe at review time)
- RESULT-013 blob: `4b50f7cdb8f99601e4a9bc01e03d4bd04f198e7d`
- RESULT action: `FIX`
- FIX authorization recorded by worker: `.ai/reviews/REVIEW-013.md (af397858b5)` — matches the prior CHANGES_REQUIRED artifact.
- Delta from prior reviewed head: 1 commit, 3 changed files (`RESULT-013.md`, `shopee.py`, DOM fixture tests).

## Test Evidence
The RESULT records:
- Focused Product Source Pack suite: 49 passed, 0 failed.
- Full repository suite: 467 passed, 0 failed.
- New deterministic fixture: `test_shopee_obfuscated_live_dom_gallery_extraction_and_footer_exclusion` passes.

The test evidence is green, but it does not resolve the acceptance-critical ownership issue below.

## Findings

### 1. BLOCKER — Structural gallery fallback is not positively bounded to the current product
The new Strategy 2B is described as "top product section" discovery, but the implementation actually selects **every** `section` in the document (plus briefing selectors), then scans **every** descendant `div` in every non-excluded section.

A descendant container is admitted as gallery when it has `>= 2` media URLs, or when it has a single URL while the gallery is still empty. There is no positive proof that the candidate section belongs to the current product, no relation to the identity-gated structured product object, no structural relationship to the current product title/summary card, and no bounded stop condition after the true gallery is found.

This means an obfuscated unrelated section with two images — for example a shop promotion, campaign carousel, bundle panel, or recommendation block whose generated class names do not contain one of the known exclusion keywords — can be labeled `SEMANTIC_PRODUCT_GALLERY` and persisted as seller-product source media.

That violates TASK-013's fail-closed seller-original-only requirement and can reintroduce exactly the contamination class this task exists to prevent.

Required correction: use a **positive ownership anchor** for structural discovery. A strong option is to use identity-gated structured product media as a seed, locate the corresponding DOM media node, and expand only to its nearest product-media/gallery ancestor/thumbnail cluster. If no trustworthy positive anchor can be established, fail closed rather than scanning generic page sections. Other structurally equivalent positive-ownership strategies are acceptable, but generic whole-page `section` discovery is not.

### 2. BLOCKER — New regression fixture does not exercise the unsafe case
The new fixture proves rejection of elements carrying semantic exclusion signals such as `product-ratings`, `similar-products`, `<header>`, and `<footer>`.

It does **not** include an unrelated obfuscated/generic `<section>` containing multiple same-CDN images with no `review`, `recommend`, `footer`, etc. token. Such a fixture would currently be eligible under Strategy 2B.

Add a deterministic negative regression where a generic/obfuscated non-product section contains two or more same-CDN images and prove they are not returned as gallery media.

### 3. BLOCKER — Required live re-validation on the same Shopee product is still missing
The prior review explicitly required a re-run of the actual extractor against Shopee product `52764529835` before approval could be restored.

The new RESULT records the deterministic DOM reproduction and green suites, but it does not record a new live CDP run against that product or the resulting extraction counts/accepted media set.

After the ownership fix is implemented and tests pass, re-run the actual `_SHOPEE_EXTRACTION_SCRIPT` on the same authenticated live page and record at minimum:
- exact product identity/title and `blocked` status;
- structured/gallery/variant/description/fallback counts;
- enough accepted gallery URL/path evidence to confirm multiple seller gallery images are captured;
- confirmation that footer/review/recommendation media are absent.

No captcha or anti-bot bypass is permitted; a blocked page must be reported as blocked.

## Positive Notes
- The worker used the exact authorized prior review artifact.
- Main has not drifted and the task branch remains fast-forward safe.
- The new helper supports `img`, `data-src`, `srcset`, and inline background-image media.
- Footer/header/nav and known UGC/recommendation exclusion handling was strengthened.
- Existing identity gating, downloader bounds, byte preservation, and no-AI/no-scoring boundaries remain intact according to the reviewed diff and RESULT.

## Decision
CHANGES_REQUIRED.

Do not merge TASK-013.

The next authorized worker action is:

`/aios-worker FIX TASK-013`

After the worker publishes a new head and RESULT, request `Review TASK-013` again. Approval can only be restored after both fail-closed positive gallery ownership and the required live Shopee re-validation are demonstrated.