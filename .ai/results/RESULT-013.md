# RESULT-013

STATUS: READY_FOR_REVIEW

## Summary
Phase 6 M2.2A Product Source Pack & Original Media Extraction V1: Replaced broad whole-page DOM scraping in `ShopeeScrapeTool` and `TikTokScrapeTool` with an evidence-first, canonical `ProductSourcePack` extraction pipeline. Implemented deterministic platform extractors prioritizing structured data over semantic galleries, excluded review/UGC imagery by container provenance, built a byte-preserving `OriginalMediaDownloader` with URL and SHA-256 deduplication, and added comprehensive unit and integration test coverage.

## Task Metadata
- Task: `TASK-013`
- Action: `RUN`
- Authorized Artifact: `.ai/tasks/TASK-013.md (c0144bc2e7)`
- Base Main SHA: `9d3dcfeab5ffc98bf6aeb3ef7a67912a5bc1fd52`
- Branch: `ai/task-013`

## Files Changed
- `src/product_source/__init__.py` (new module exports)
- `src/product_source/models.py` (canonical data contracts & error hierarchy)
- `src/product_source/extractor.py` (ProductSourceExtractor protocol)
- `src/product_source/downloader.py` (byte-preserving original media downloader)
- `src/product_source/serialization.py` (source_pack.json manifest serialization)
- `src/product_source/platforms/__init__.py`
- `src/product_source/platforms/shopee.py` (ShopeeSourceExtractor)
- `src/product_source/platforms/tiktok.py` (TikTokSourceExtractor)
- `src/tools/shopee_scrape_tool.py` (refactored to source pack pipeline)
- `src/tools/tiktok_scrape_tool.py` (refactored to source pack pipeline)
- `tests/product_source/__init__.py`
- `tests/product_source/test_models.py` (16 model contract tests)
- `tests/product_source/test_original_media_downloader.py` (12 downloader tests)
- `tests/product_source/test_scrape_tool_compat.py` (8 scrape tool compatibility tests)
- `tests/product_source/test_shopee_source_extractor.py` (7 Shopee extraction tests)
- `tests/product_source/test_tiktok_source_extractor.py` (6 TikTok extraction tests)
- `docs/PHASE_6_PRODUCT_SOURCE_PACK.md` (architectural documentation)

## Diff Stat
```text
 docs/PHASE_6_PRODUCT_SOURCE_PACK.md                | 170 ++++++++++++
 src/product_source/__init__.py                     |  29 ++
 src/product_source/downloader.py                   | 172 ++++++++++++
 src/product_source/extractor.py                    |  11 +
 src/product_source/models.py                       | 161 +++++++++++
 src/product_source/platforms/__init__.py           |   0
 src/product_source/platforms/shopee.py             | 285 +++++++++++++++++++
 src/product_source/platforms/tiktok.py             | 312 +++++++++++++++++++++
 src/product_source/serialization.py                |  21 ++
 src/tools/shopee_scrape_tool.py                    | 378 +++++++++++--------------
 src/tools/tiktok_scrape_tool.py                    | 329 +++++++++++-----------
 tests/product_source/__init__.py                   |   0
 tests/product_source/test_models.py                | 185 +++++++++++++
 .../test_original_media_downloader.py              | 298 ++++++++++++++++++++
 tests/product_source/test_scrape_tool_compat.py    | 274 +++++++++++++++++++
 .../test_shopee_source_extractor.py                | 178 ++++++++++++
 .../test_tiktok_source_extractor.py                | 172 ++++++++++++
 17 files changed, 2588 insertions(+), 387 deletions(-)
```

## Tests

### Focused Test Suite
Command: `.\venv\Scripts\python -m pytest tests/product_source/ -v`  
Exit code: 0  
Results: 49 passed, 0 failed in 0.36s

### Full Repository Test Suite
Command: `.\venv\Scripts\python -m pytest tests/ -q -W ignore`  
Exit code: 0  
Results: 467 passed, 0 failed in 47.59s

## Implementation Specifications

1. **Product Source Pack Schema**:
   - `ProductSourcePack` (v1.0): Immutable dataclass with deterministic `source_pack_id` (`{platform}_{source_product_id}` or SHA-256 URL hash). Contains canonical observed fields: `platform`, `product_url`, `observed_at`, `collector`, `title`, `source_product_id`, `shop_name`, `brand`, `model_sku`, `description_text` (bounded to 10k chars), `facts` (tuple), `media` (tuple), `diagnostic_codes` (tuple).
   - `ProductFact`: `key`, `value`, `unit`, `source_section`, `provenance`.
   - `OriginalMediaRef`: `source_url`, `platform`, `role`, `provenance`, `ordinal`, `alt_text`, `variant_label`, `content_type`, `byte_size`, `sha256_hash`, `perceptual_hash`, `local_filename`.

2. **Trusted Extraction Priority**:
   - Priority 1: Embedded structured product data (JSON-LD `Product`, `SIGI_STATE`, `__NEXT_DATA__`).
   - Priority 2: Semantic product gallery & carousel containers (`.product-image-carousel`, `.product-image__content`, `[data-testid*="gallery"]`).
   - Priority 3: Seller description media (`.product-detail`, `[class*="seller-description"]`) labeled as `SELLER_DESCRIPTION`.
   - Priority 4: Bounded platform-scoped fallback within current product summary container (max 10 elements). Fails closed if all trusted paths are empty; no whole-page image scanning.

3. **Explicit Review/UGC Exclusion**:
   - Elements under review/rating/comment/recommendation subtrees are rejected by container hierarchy check (`isExcluded` logic).
   - Same-CDN URLs belonging to review or comment sections are rejected by container provenance.

4. **Media Bounds & Byte Limits**:
   - Per-file byte ceiling: 20 MiB (`MAX_FILE_BYTES`).
   - Per-product media ceiling: 30 items (`MAX_MEDIA_PER_PRODUCT`).

5. **Original-Byte Persistence Semantics**:
   - Original response bytes are saved directly without resizing, watermarking, recomposition, or JPEG re-encoding.
   - Formats validated via Content-Type header and file magic bytes.

6. **Two-Stage Deduplication**:
   - Stage 1: Pre-download canonical URL dedupe preserving highest-confidence provenance tier and first-seen ordinal.
   - Stage 2: Post-download exact SHA-256 byte duplicate collapse.

7. **Product Fact Missing/Provenance Policy**:
   - Unobserved facts remain strictly `None`.
   - Fact extraction does not perform LLM or computer-vision inference.
   - Facts have explicit source attribution (`specification_table`, `structured_data`, `description`).

8. **Browser Abstraction Compatibility**:
   - Tools and extractors interact exclusively through the project `BrowserManager` / `BrowserSession` protocol (`get_or_create_session()`, `navigate()`, and `evaluate()`). Direct calls to `browser.new_page()` are eliminated from scrape tools.

9. **Side-Effect Guarantees**:
   - No AI image generation, background removal, or 360° synthesis.
   - No LLM provider calls, no candidate scoring or ranking.
   - No `tasks.txt` mutation.

10. **Known Limitations Retained**:
    - M2.2A establishes canonical Product Source Packs; M2.3 cross-platform scoring/ranking, M2.4 queue handoff, and downstream derived AI asset synthesis are scheduled for future milestones.

11. **Merge Governance**:
    - TASK-013 is not auto-merged; human approval required.

## Generated
2026-08-16T07:50:00+07:00
