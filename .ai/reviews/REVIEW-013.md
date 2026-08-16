# REVIEW-013 — TASK-013 (Phase 6 M2.2A Product Source Pack & Original Media Extraction V1)

## Status
CHANGES_REQUIRED

## Reviewed Head
- Branch: `ai/task-013`
- Reviewed commit: `a45cb80e242f7e4b25afa40860f2e0ecb2907e1d`
- Main baseline: `9d3dcfeab5ffc98bf6aeb3ef7a67912a5bc1fd52`
- Branch relation at prior review: ahead 9, behind 0 (fast-forward safe)
- Task artifact blob: `c0144bc2e7ffc21422a491ca621a0fe7ceceecde`
- Prior RESULT-013 blob: `5ef20b0e0640449baf418f9c150d4b8d25570b3f`
- Prior RESULT action: `FIX`

## Regression Test Evidence
- Focused command recorded in RESULT: `.\venv\Scripts\python -m pytest tests/product_source/ -v`
  - 48 passed, 0 failed, exit code 0.
- Full repository command recorded in RESULT: `.\venv\Scripts\python -m pytest tests/ -q -W ignore`
  - 466 passed, 0 failed, exit code 0.

## Pre-Merge Live Validation — 2026-08-16
The user intentionally performed a real Shopee validation against the exact approved TASK-013 head before merge, using an authenticated local Chrome session exposed through CDP port 9222.

Live product:
- Shopee product ID: `52764529835`
- Extracted title matched the target product.
- `blocked = false`.
- Structured identity matched exactly.

Observed extraction counts from the actual `_SHOPEE_EXTRACTION_SCRIPT`:
- `STRUCTURED_IMAGES: 1`
- `GALLERY: 0`
- `VARIANTS: 0`
- `DESCRIPTION_MEDIA: 0`
- `FALLBACK_MEDIA: 0`

The live DOM contained multiple seller-owned product gallery images, but the TASK-013 Shopee semantic gallery selectors did not recognize the current Shopee gallery markup. The current implementation only scans:

`'.product-image-carousel, .product-image__content, .V9sV-Q, .xNIlvG'`

The live seller gallery was instead rendered under a top product-media section whose current classes included `SECTION.C21rQm`, with the main product image under `BvNoX2 / OMOWB7` and seller thumbnails under `qIctnQ / mdCA_C / FAWPL0`. Those classes appear hashed/obfuscated and carry no stable semantic attributes in the inspected ancestor chain, so hard-coding `C21rQm` or the other observed hash classes is not an acceptable long-term fix.

A separate group of images at the bottom of the page was confirmed to be under `FOOTER.Dtu9HW`; those are not product-source media and must remain excluded.

## Blocking Finding
**Shopee live gallery compatibility is incomplete.**

TASK-013 currently succeeds with only one structured image on this real Shopee product while missing the remaining seller gallery images. This violates the task objective to capture seller-original product media and means the prior static approval is superseded by this live validation result.

The fix must:
1. Add a robust current-Shopee gallery ownership strategy without relying solely on ephemeral hashed class names.
2. Preserve fail-closed review/comment/UGC/recommendation/footer exclusion.
3. Keep current exact product identity gating and provenance roles.
4. Add deterministic regression coverage reproducing the current live DOM shape, including seller gallery acceptance and footer/review/recommendation rejection.
5. Re-run focused and full tests.
6. Re-run a live Shopee validation on the same product before approval is restored.

## Decision
CHANGES_REQUIRED.

Do not merge TASK-013. The next authorized worker action is `/aios-worker FIX TASK-013`. After the worker publishes the new task head and RESULT, the user must request `Review TASK-013` again. Merge remains forbidden until a new review is APPROVED and the user explicitly says `Merge TASK-013`.
