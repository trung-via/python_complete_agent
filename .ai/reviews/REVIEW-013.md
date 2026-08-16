# REVIEW-013 — TASK-013 (Phase 6 M2.2A Product Source Pack & Original Media Extraction V1)

## Status
CHANGES_REQUIRED

## Reviewed Head
- Branch: `ai/task-013`
- Reviewed commit: `9ffe8fe51001da2d9615cca68f2c131acfc41d0e`
- Parent reviewed head: `2b2e7a4fd209c0fda7aaa482b1da418dcc91e42a`
- Main baseline/current main: `9d3dcfeab5ffc98bf6aeb3ef7a67912a5bc1fd52`
- Branch relation to main: ahead 11, behind 0 (fast-forward safe at review time)
- RESULT-013 blob: `33cc24f84b5fbf2665109d7496909384b896b616`
- RESULT action: `FIX`
- FIX authorization recorded by worker: `.ai/reviews/REVIEW-013.md (5b33fc835a)` — matches the prior CHANGES_REQUIRED artifact.
- Delta from prior reviewed head: 1 commit, 3 changed files (`RESULT-013.md`, `shopee.py`, DOM fixture tests).

## Test Evidence
The RESULT records:
- Focused Product Source Pack suite: 49 passed, 0 failed.
- Full repository suite: 467 passed, 0 failed.
- The obfuscated live-DOM regression now includes an unrelated same-CDN non-product section and proves it is excluded in that structured-image/title fixture.

These are good improvements, but acceptance-critical issues remain.

## Findings

### 1. BLOCKER — Priority 4 still contains a forbidden global `section` fallback
TASK-013 explicitly requires positive inclusion and states that no whole-page image sweep may be used as a normal or fallback success path. Priority 4 is allowed only inside a **known current-product container**; if trusted paths fail, extraction must fail closed.

The current Shopee implementation still executes this path when both structured images and gallery are empty:

`document.querySelectorAll('section, .page-product__briefing, .product-briefing')`

It then scans media inside every non-excluded `section` and accepts those URLs as `fallback_media`.

A generic or obfuscated promotional/recommendation section with no exclusion keyword can therefore become `PLATFORM_SCOPED_FALLBACK` media when structured images/gallery are absent. This directly violates the task's `No global DOM fallback` rule and the explicit Priority-4 requirement that fallback be bounded to a known current-product container.

Required correction:
- remove generic `section` from Priority 4;
- permit fallback only from a positively identified current-product container/anchor;
- if no such owned container exists, return no fallback media so the Python layer fails closed;
- add a deterministic regression with **no structured image and no semantic gallery** plus an unrelated obfuscated multi-image section, proving the extractor returns no accepted fallback media.

### 2. BLOCKER — Structured-image positive anchor is currently non-functional for the root media node
Strategy 2B attempts to find the structured seed image by iterating DOM media nodes and calling `getMediaUrls(el)` on each node.

However, `getMediaUrls(rootEl)` only queries descendants via `rootEl.querySelectorAll('img')` and descendant background-image selectors; it does not inspect `rootEl` itself. For a root `<img>` node, `querySelectorAll('img')` returns no descendants, so the seed image URL is never observed from that element.

The current fixture still passes because the identity-gated structured title provides Anchor 2. That means the claimed image-seed ownership path is not actually covered independently.

Required correction:
- make the media helper inspect the root element's own `src` / `data-src` / `srcset` / background-image as well as descendants, or use a dedicated root-node extraction helper;
- add a regression where the structured product image is present and identity-matched but no usable title anchor exists, proving the image seed alone anchors the gallery and unrelated sections remain excluded.

### 3. BLOCKER — Required same-product live re-validation was not performed
The prior durable review required re-running the actual extractor against the same Shopee product used to expose the defect: `52764529835`.

The new RESULT instead records a live CDP validation for product `22590099603`. That is useful additional evidence, and it reports `blocked=False`, one structured image, and a 10-image gallery, but it does not satisfy the explicitly required same-product regression check.

Required correction/evidence:
- after the code fixes above, re-run the actual `_SHOPEE_EXTRACTION_SCRIPT` against product `52764529835` in the authenticated CDP session;
- record exact identity/title, blocked status, structured/gallery/variant/description/fallback counts;
- record enough sanitized accepted gallery path evidence to show multiple seller gallery images were captured;
- confirm footer/review/recommendation media are absent;
- do not bypass captcha or anti-bot controls.

## Positive Notes
- The prior broad Strategy-2B whole-document section scan was replaced with a positive-anchor expansion path.
- The new regression now covers an unrelated obfuscated same-CDN section in the structured/title-anchored case.
- Main has not drifted and the task branch remains fast-forward safe.
- Existing exact identity gating, UGC/recommendation exclusion, byte-preserving download, media bounds, signed-URL redaction, and no-AI/no-scoring boundaries remain intact in the reviewed task diff.

## Decision
CHANGES_REQUIRED.

Do not merge TASK-013.

The next authorized worker action is:

`/aios-worker FIX TASK-013`

After the worker publishes a new head and RESULT, request `Review TASK-013` again. Approval can only be restored after the forbidden generic fallback is removed, the image-seed anchor is independently proven, and the required live re-validation on Shopee product `52764529835` is demonstrated.