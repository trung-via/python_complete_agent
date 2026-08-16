# REVIEW-013 — TASK-013 (Phase 6 M2.2A Product Source Pack & Original Media Extraction V1)

## Status
CHANGES_REQUIRED

## Reviewed Head
- Branch: `ai/task-013`
- Reviewed commit: `f7cd4296d4efe0ed6b8e2dcaa506766fb7a9260f`
- Parent reviewed head: `53b9ffc0c4bc1ca391d1e5ee78c553bd8c96e079`
- Current main: `9d3dcfeab5ffc98bf6aeb3ef7a67912a5bc1fd52`
- Branch relation to main: ahead 13, behind 0 (fast-forward safe at review time)
- RESULT-013 blob: `3fc44afe4e3e5de8d21e21acebd3f41acaffac84`
- RESULT action: `FIX`
- FIX authorization recorded by worker: `.ai/reviews/REVIEW-013.md (74e632f80c)` — matches the prior CHANGES_REQUIRED artifact.
- Delta from prior reviewed head: 1 commit, 3 changed files (`RESULT-013.md`, `shopee.py`, DOM fixture tests).

## Verification
The RESULT records:
- Focused Product Source Pack suite: **52 passed, 0 failed**.
- Full repository suite: **470 passed, 0 failed**.
- New regression `test_shopee_near_seed_ancestor_with_two_images_expands_to_full_sibling_thumbnail_strip` passes.
- Non-challenged live validation on Shopee product `52764529835` reports `blocked=False`, one structured image, six gallery media entries, zero variants/description/fallback, and no footer/review/recommendation/SVG media.

The branch remains a clean fast-forward from current main.

## Resolved Prior Blocker
The prior under-extraction defect is fixed: Strategy 2B no longer stops at the first near ancestor with two URLs. It now carries the verified seed upward, retains the largest positively anchored media set found within the bounded ancestor walk, and stops at the enclosing briefing/section boundary. The exact live product now includes the sibling thumbnail strip instead of returning only two items.

## Blocking Finding
### Product-media cluster expansion currently accepts a non-product overlay as canonical gallery media
The new regression explicitly models the near-seed second image as an `overlay-badge` and asserts that it is accepted into `result["gallery"]`. The live RESULT likewise describes the six accepted entries as the main image, a badge overlay, and the thumbnail strip.

That conflicts with TASK-013's source-media boundary. The task requires accepted media to be seller-original product media and explicitly excludes promotional/banner/non-product imagery that is not part of the current product media set. A standalone UI/promo/badge overlay is not a product view and must not be persisted as `SEMANTIC_PRODUCT_GALLERY` merely because it shares the positively anchored media cluster.

The original live DOM evidence for this product showed the seller thumbnail strip as the authoritative gallery relationship: the main image is repeated in the strip together with the additional seller product views, while a separate image inside the main-image stack is rendered alongside the main image. The current fix solves under-extraction by admitting every image in the common cluster, but in doing so it over-extracts that separate overlay asset.

Required correction:
1. Keep the verified structured-image seed and bounded ancestor expansion.
2. Treat the associated thumbnail strip / carousel relationship as the authoritative gallery set when present, plus the verified main seed; do not automatically admit every sibling image in the enclosing cluster.
3. Exclude standalone overlay/badge/promo imagery from canonical gallery media even when it lives inside the positively owned product-media area.
4. Update the deterministic regression so the near-seed overlay image is **rejected**, while the main seed and all sibling thumbnail-strip product images are accepted.
5. Keep unrelated obfuscated sections, reviews, recommendations, footer/app-shell media excluded.
6. Re-run focused and full suites.
7. Re-run the non-challenged live validation on product `52764529835`; the accepted set should correspond to actual seller product views/thumbnails only, without the overlay asset.

## Decision
CHANGES_REQUIRED.

Do not merge TASK-013.

The next authorized worker action is:

`/aios-worker FIX TASK-013`

After the worker publishes a new head and RESULT, request `Review TASK-013` again. Approval can only be restored after the live seller gallery is complete **and** the non-product overlay is excluded from canonical source media.