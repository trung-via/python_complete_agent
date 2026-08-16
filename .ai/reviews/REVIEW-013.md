# REVIEW-013 — TASK-013 (Phase 6 M2.2A Product Source Pack & Original Media Extraction V1)

## Status
CHANGES_REQUIRED

## Reviewed Head
- Branch: `ai/task-013`
- Reviewed commit: `564d69d4aac66d3e541ef82c34b5f756ae5a24e7`
- Parent reviewed head: `c6d1c9607e6e7de71aa9ff1ac8e8f6c1e8ae1d26`
- Current main at prior review: `9d3dcfeab5ffc98bf6aeb3ef7a67912a5bc1fd52`
- RESULT-013 blob at prior review: `7419de97951ab04bafbefd2046493a7be1bd323d`

## Preserved Verification
The prior Shopee validation remains good on the reviewed head:
- exact TP-Link TC70 product `52764529835`;
- `BLOCKED: False`;
- five authentic seller gallery views;
- overlay/badge excluded;
- 12 accepted description-media assets scoped to `DIV product-detail page-product__detail`;
- all 12 returned `EXCLUDED_ANCESTOR: None` for review/recommendation/comment/footer/header/nav checks;
- no broad fallback used.

Focused and full suites previously recorded:
- Product Source Pack suite: **52 passed**;
- Full repository suite: **470 passed**.

## New Pre-Merge Live Blocker — TikTok
The user supplied TikTok regression URL:

`https://vt.tiktok.com/ZS9ky3CJwy3LY-NGB3c/`

It redirected in the authenticated Chrome CDP session to product:

`https://www.tiktok.com/view/product/1729981094029264939`

Visible page title was the intended TikTok Shop product page for UVGREEN KA600.

Running the actual `_TIKTOK_EXTRACTOR_JS` from the reviewed head returned:
- `PRODUCT_ID: None`
- `TITLE: None`
- `BLOCKED: True`
- `STRUCTURED_IMAGES: 0`
- `GALLERY_IMAGES: 0`
- `VARIANTS: 0`
- `SELLER_IMAGES: 0`
- `FALLBACK_IMAGES: 0`

Diagnostic inspection showed:
- normal product path: `/view/product/1729981094029264939`;
- normal visible product title, not a captcha/robot page;
- TikTok loads captcha JavaScript globally on the product page, including `lucifer-captcha-loader-js` and captcha vendor bundles;
- the reviewed extractor marks the page blocked solely because `document.querySelector('script[src*="captcha"]')` exists.

This is a false-positive anti-bot classification on a normal product page. It prevents any TikTok product extraction and violates the task requirement to support selected TikTok product URLs while still failing closed on a real challenge.

## Required Fix
1. Replace the TikTok anti-bot success/block condition so mere presence of globally loaded captcha JavaScript does **not** mark a normal product page blocked.
2. Continue to fail closed when there is positive evidence of an active captcha/robot/challenge UI or challenge page/state.
3. Add a deterministic regression test covering a normal TikTok product page that loads captcha scripts globally but has no active challenge; expected `blocked == false`.
4. Preserve a regression test for an actual active captcha/challenge; expected `blocked == true`.
5. Re-run focused Product Source Pack tests and full repository tests.
6. Repeat the live TikTok test on product `1729981094029264939` and verify exact product identity plus positively scoped seller-product media. No broad DOM fallback, no UGC/review/recommendation contamination, and no captcha bypass.

## Decision
CHANGES_REQUIRED.

Do not merge.

Human fix gate:

`/aios-worker FIX TASK-013`
