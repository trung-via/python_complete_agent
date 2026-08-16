# REVIEW-013 — TASK-013 (Phase 6 M2.2A Product Source Pack & Original Media Extraction V1)

## Status
CHANGES_REQUIRED

## Reviewed Head
- Branch: `ai/task-013`
- Reviewed commit: `53b9ffc0c4bc1ca391d1e5ee78c553bd8c96e079`
- Parent reviewed head: `9ffe8fe51001da2d9615cca68f2c131acfc41d0e`
- Current main at prior review: `9d3dcfeab5ffc98bf6aeb3ef7a67912a5bc1fd52`
- RESULT-013 blob: `423cf9bd633e0013a4f65fa74beee51bbcd1523d`
- RESULT action: `FIX`

## Prior Static Verification
The RESULT recorded:
- Focused Product Source Pack suite: **51 passed, 0 failed**.
- Full repository suite: **469 passed, 0 failed**.
- Image-seed anchor regression passed.
- No-structured/no-semantic-gallery fail-closed regression passed.

Those checks remain useful, but the user's requested non-challenged live validation on the original product has now exposed an acceptance-critical seller-gallery omission.

## Pre-Merge Live Validation — 2026-08-16
Exact local task head was verified as:

`53b9ffc0c4bc1ca391d1e5ee78c553bd8c96e079`

The user then re-ran the actual `_SHOPEE_EXTRACTION_SCRIPT` against the original Shopee regression product `52764529835` in the authenticated Chrome CDP session after the product page was reopened successfully.

Observed live result:
- product URL resolved to item `52764529835`;
- title matched the TP-Link TC70 product;
- `PRODUCT_ID: 52764529835`;
- `BLOCKED: False`;
- `STRUCTURED_IMAGES: 1`;
- `GALLERY: 2`;
- `VARIANTS: 0`;
- `DESCRIPTION_MEDIA: 0`;
- `FALLBACK_MEDIA: 0`.

The two accepted gallery paths were the main seller image plus one additional seller-owned media item. However, the same product's earlier inspected live DOM showed a seller thumbnail strip with several additional product images under the same positively owned top product-media cluster. Therefore the current implementation still under-extracts the live seller gallery on the exact product that motivated this fix.

## Blocking Finding
**The positive anchor expansion stops too early inside the media cluster.**

Current Strategy 2B walks upward from the verified seed node and accepts the first ancestor whose `getMediaUrls(...)` result has at least two media URLs, then stops. On the live Shopee DOM, the seed image's near ancestor can already contain two seller media URLs while the actual thumbnail strip is a sibling under a higher common product-media ancestor. Stopping at the first `>= 2` ancestor therefore yields an incomplete gallery.

This is visible in the implementation's early break after `candidateUrls.length >= 2` and is now confirmed by the exact non-challenged live run.

Required correction:
1. Preserve the positive ownership seed; do **not** return to generic page/section scanning.
2. Expand from the verified seed to the smallest trustworthy enclosing product-media cluster that includes both the main-image area and its associated thumbnail strip, rather than stopping at the first ancestor with two URLs.
3. Keep unrelated obfuscated sections, reviews, recommendations, footer/app-shell media excluded.
4. Add a deterministic regression where a near seed ancestor contains two media URLs but the sibling thumbnail strip under a higher owned ancestor contains additional seller images; prove the full owned gallery is returned while unrelated sections remain excluded.
5. Re-run focused and full suites.
6. Re-run the non-challenged live validation on product `52764529835` and demonstrate that the seller thumbnail images previously observed on the page are captured, with no non-product contamination.

## Decision
CHANGES_REQUIRED.

Do not merge TASK-013.

The next authorized worker action is:

`/aios-worker FIX TASK-013`

After the worker publishes a new head and RESULT, request `Review TASK-013` again. Approval can only be restored after the exact live product returns a complete, positively owned seller gallery without contamination.