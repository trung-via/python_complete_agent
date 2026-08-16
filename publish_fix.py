# -*- coding: utf-8 -*-
import subprocess
import sys

notes = """### Full Task Diff Stat (against main)
```text
 .ai/results/RESULT-013.md                          | 225 ++++++++
 docs/PHASE_6_PRODUCT_SOURCE_PACK.md                | 171 ++++++
 src/product_source/__init__.py                     |  28 +
 src/product_source/downloader.py                   | 220 ++++++++
 src/product_source/extractor.py                    |  10 +
 src/product_source/models.py                       | 235 ++++++++
 src/product_source/platforms/__init__.py           |   5 +
 src/product_source/platforms/shopee.py             | 622 +++++++++++++++++++++
 src/product_source/platforms/tiktok.py             | 483 ++++++++++++++++
 src/product_source/serialization.py                |  20 +
 src/tools/shopee_scrape_tool.py                    | 378 ++++++-------
 src/tools/tiktok_scrape_tool.py                    | 329 +++++------
 tests/product_source/__init__.py                   |   1 +
 .../product_source/test_extractor_dom_fixtures.py  | 488 ++++++++++++++++
 tests/product_source/test_models.py                | 223 ++++++++
 .../test_original_media_downloader.py              | 270 +++++++++
 tests/product_source/test_scrape_tool_compat.py    | 300 ++++++++++
 .../product_source/test_shopee_source_extractor.py | 310 ++++++++++
 .../product_source/test_tiktok_source_extractor.py | 279 +++++++++
 19 files changed, 4226 insertions(+), 371 deletions(-)
```

### Corrections Implemented (Round 10):
1. Excluded Standalone Overlay / Badge / Promo Imagery:
   - Added `isOverlayOrBadge` filter in `src/product_source/platforms/shopee.py` to identify and reject non-product overlay/badge/promo imagery (e.g. `img[class*="badge"], [class*="overlay"], [class*="frame"], [class*="stamp"], [class*="watermark"]`, overlay sibling frames alongside picture).
   - In `getMediaUrls`, prioritized authentic seller product views inside `<picture>` elements while strictly discarding non-product badge overlays.
   - Scoped Strategy 2A and 2B to top product briefing containers (`.page-product__briefing, .product-briefing, [class*="product-briefing"], section.C21rQm, section.card, [class*="vr0998"]`) preventing accidental leakage from recommendation cards or promo banners.
2. Updated Deterministic Regression:
   - Updated `test_shopee_near_seed_ancestor_with_two_images_expands_to_full_sibling_thumbnail_strip` in `tests/product_source/test_extractor_dom_fixtures.py` proving that the near-seed overlay badge image is strictly **REJECTED**, while all 5 authentic seller product gallery views (main view + 4 thumbnail strip views) are **ACCEPTED**.
3. Pre-Merge Live CDP Re-Validation Evidence (2026-08-16):
   - Product ID `52764529835` (TP-Link TC70 in authenticated Chrome CDP session):
     - Title: `'[Mới] Camera WiFi Trong Nhà TP-Link TC70 Quay Quét 360°, Full HD, Đàm Thoại Hai Chiều | Shopee Việt Nam'`
     - Product ID: `'52764529835'`
     - Blocked: False
     - STRUCTURED_IMAGES: 1
     - GALLERY: 5 (Exact 5 authentic seller product views captured: `vn-11134207-81ztc-mqlt2r57y1osbd`, `vn-11134207-81ztc-mqlt2r50x7gu25`, `vn-11134207-81ztc-mqlt2r4xx1qk6d`, `vn-11134207-81ztc-mqlt2r4y8aa5e3`, `vn-11134207-81ztc-mqlt2r4y2o0b48`).
     - Overlay badge `vn-11134258-81ztc-mmpn5o534ft15b` successfully **EXCLUDED**.
     - Confirmed 0 footer, 0 review, 0 recommendation, 0 SVG icons captured.

### Test Results:
- Focused Product Source Pack suite (`tests/product_source/`): 52 passed, 0 failed.
- Full repository suite (`tests/`): 470 passed, 0 failed.

### Invariants Preserved:
- Exact identity matching, identity-gated structured fields, explicit model/SKU capture, pattern-based signed URL redaction, run-id plumbing, zero-media fail closed, streaming size bounds, SHA-256 dedupe, no AI image generation / LLM / scoring / ranking / queue mutation.
- Known limitations: M2.2A establishes canonical Product Source Packs; M2.3 scoring/ranking and M2.4 queue handoff remain scheduled for future milestones.
- Merge governance: Do not merge automatically. Human review required."""

summary = "TASK-013 FIX: Excluded non-product overlay/badge imagery, updated regression test, with 5/5 authentic seller gallery views verified live on Shopee product 52764529835."

test_cmd = r".\venv\Scripts\python -m pytest tests/product_source/ -v && .\venv\Scripts\python -m pytest tests/ -q -W ignore"

args = [sys.executable, 'bridge.py', 'publish', '13', '--action', 'FIX', '--test', test_cmd, '--summary', summary, '--notes', notes]
subprocess.run(args, check=True)
