# RESULT-013

STATUS: READY_FOR_REVIEW

## Summary
TASK-013 FIX (Round 2): Implemented authoritative structured product identity validation gating all structured-derived fields (title, brand, shop, description, specs, and media), fail-closed error handling upon extraction exhaustion, strict `BrowserManager.get_or_create_session(run_id)` protocol compliance, and comprehensive verification evidence.

## Task Metadata
- Task: `TASK-013`
- Action: `FIX`
- Authorized Artifact: `.ai/reviews/REVIEW-013.md (527d3d5a0b)`
- Base Main SHA: `9d3dcfeab5ffc98bf6aeb3ef7a67912a5bc1fd52`
- Branch: `ai/task-013`

## Files Changed
- `docs/PHASE_6_PRODUCT_SOURCE_PACK.md`
- `src/product_source/__init__.py`
- `src/product_source/downloader.py`
- `src/product_source/extractor.py`
- `src/product_source/models.py`
- `src/product_source/platforms/__init__.py`
- `src/product_source/platforms/shopee.py`
- `src/product_source/platforms/tiktok.py`
- `src/product_source/serialization.py`
- `src/tools/shopee_scrape_tool.py`
- `src/tools/tiktok_scrape_tool.py`
- `tests/product_source/__init__.py`
- `tests/product_source/test_models.py`
- `tests/product_source/test_original_media_downloader.py`
- `tests/product_source/test_scrape_tool_compat.py`
- `tests/product_source/test_shopee_source_extractor.py`
- `tests/product_source/test_tiktok_source_extractor.py`

## Diff Stat
```text
 docs/PHASE_6_PRODUCT_SOURCE_PACK.md                | 171 ++++++++
 src/product_source/__init__.py                     |  28 ++
 src/product_source/downloader.py                   | 220 ++++++++++
 src/product_source/extractor.py                    |  10 +
 src/product_source/models.py                       | 227 ++++++++++
 src/product_source/platforms/__init__.py           |   5 +
 src/product_source/platforms/shopee.py             | 387 +++++++++++++++++
 src/product_source/platforms/tiktok.py             | 456 +++++++++++++++++++++
 src/product_source/serialization.py                |  20 +
 src/tools/shopee_scrape_tool.py                    | 378 ++++++++---------
 src/tools/tiktok_scrape_tool.py                    | 329 ++++++++-------
 tests/product_source/__init__.py                   |   1 +
 tests/product_source/test_models.py                | 216 ++++++++++
 .../test_original_media_downloader.py              | 270 ++++++++++++
 tests/product_source/test_scrape_tool_compat.py    | 297 ++++++++++++++
 .../product_source/test_shopee_source_extractor.py | 252 ++++++++++++
 .../product_source/test_tiktok_source_extractor.py | 217 ++++++++++
 17 files changed, 3113 insertions(+), 371 deletions(-)
```

## Tests

### Focused Test Suite
Command: `.\venv\Scripts\python -m pytest tests/product_source/ -v`  
Exit code: 0  
Results: 44 passed, 0 failed in 0.34s

```text
tests/product_source/test_models.py::test_build_source_pack_id_with_product_id PASSED [  2%]
tests/product_source/test_models.py::test_build_source_pack_id_fallback_url PASSED [  4%]
tests/product_source/test_models.py::test_build_source_pack_id_determinism PASSED [  6%]
tests/product_source/test_models.py::test_build_source_pack_id_ignores_tracking_and_auth_noise PASSED [  9%]
tests/product_source/test_models.py::test_sanitize_url_redacts_sensitive_parameters PASSED [ 11%]
tests/product_source/test_models.py::test_product_fact_validation PASSED [ 13%]
tests/product_source/test_models.py::test_product_fact_frozen PASSED     [ 15%]
tests/product_source/test_models.py::test_original_media_ref_validation PASSED [ 18%]
tests/product_source/test_models.py::test_product_source_pack_validation PASSED [ 20%]
tests/product_source/test_models.py::test_description_text_bounded PASSED [ 22%]
tests/product_source/test_models.py::test_facts_media_auto_converted_to_tuples PASSED [ 25%]
tests/product_source/test_models.py::test_product_source_pack_to_dict_secret_safe PASSED [ 27%]
tests/product_source/test_models.py::test_enums_values PASSED            [ 29%]
tests/product_source/test_models.py::test_error_hierarchy PASSED         [ 31%]
tests/product_source/test_original_media_downloader.py::test_preserves_exact_original_bytes PASSED [ 34%]
tests/product_source/test_original_media_downloader.py::test_streaming_oversize_media_aborts_early PASSED [ 36%]
tests/product_source/test_original_media_downloader.py::test_diagnostics_do_not_leak_sensitive_url_tokens PASSED [ 38%]
tests/product_source/test_original_media_downloader.py::test_byte_duplicate_collapse_leaves_no_orphan_files PASSED [ 40%]
tests/product_source/test_original_media_downloader.py::test_canonical_url_dedupe_before_download PASSED [ 43%]
tests/product_source/test_original_media_downloader.py::test_max_media_per_product_enforced PASSED [ 45%]
tests/product_source/test_scrape_tool_compat.py::test_shopee_scrape_tool_schema PASSED [ 47%]
tests/product_source/test_scrape_tool_compat.py::test_tiktok_scrape_tool_schema PASSED [ 50%]
tests/product_source/test_scrape_tool_compat.py::test_shopee_scrape_tool_passes_run_id_to_browser_manager PASSED [ 52%]
tests/product_source/test_scrape_tool_compat.py::test_tiktok_scrape_tool_passes_run_id_to_browser_manager PASSED [ 54%]
tests/product_source/test_scrape_tool_compat.py::test_tools_do_not_call_image_processor PASSED [ 56%]
tests/product_source/test_scrape_tool_compat.py::test_tools_do_not_invoke_llm PASSED [ 59%]
tests/product_source/test_scrape_tool_compat.py::test_partial_upload_returns_partial_success PASSED [ 61%]
tests/product_source/test_scrape_tool_compat.py::test_full_upload_failure_returns_failure PASSED [ 63%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_prefers_structured_data_when_identity_matches PASSED [ 65%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_rejects_unrelated_structured_data_on_identity_mismatch PASSED [ 68%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_fails_closed_when_no_media_found PASSED [ 70%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_collects_explicit_variants PASSED [ 72%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_gallery_fallback_when_no_structured_images PASSED [ 75%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_seller_description_media_labeled PASSED [ 77%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_raises_blocked_on_captcha PASSED [ 79%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_with_strict_browser_manager PASSED [ 81%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_js_script_excludes_reviews_by_container_provenance PASSED [ 84%]
tests/product_source/test_tiktok_source_extractor.py::test_tiktok_extractor_prefers_structured_data_when_identity_matches PASSED [ 86%]
tests/product_source/test_tiktok_source_extractor.py::test_tiktok_extractor_rejects_unrelated_structured_data_on_identity_mismatch PASSED [ 88%]
tests/product_source/test_tiktok_source_extractor.py::test_tiktok_extractor_fails_closed_when_no_media_found PASSED [ 90%]
tests/product_source/test_tiktok_source_extractor.py::test_tiktok_extractor_collects_explicit_variants PASSED [ 93%]
tests/product_source/test_tiktok_source_extractor.py::test_tiktok_extractor_gallery_fallback PASSED [ 95%]
tests/product_source/test_tiktok_source_extractor.py::test_tiktok_extractor_with_strict_browser_manager PASSED [ 97%]
tests/product_source/test_tiktok_source_extractor.py::test_tiktok_js_script_excludes_reviews_and_no_main_article_fallback PASSED [100%]
```

### Full Repository Test Suite
Command: `.\venv\Scripts\python -m pytest tests/ -q -W ignore`  
Exit code: 0  
Results: 462 passed, 0 failed in 48.24s

## Risks / Notes

1. **Structured Current-Product Identity Verification**:
   - Both Shopee and TikTok JS scripts now require identity evidence (item ID/URL/SKU) to originate directly from the structured object itself.
   - Removed `window.location.href.includes(targetProductId)` from structured identity conditions.
   - All structured fields (title, brand, shop_name, description, specs/facts, and media) are strictly gated behind verified identity. Mismatched recommendation objects are discarded.

2. **Fail-Closed Media Exhaustion**:
   - If structured, gallery, variant, description, and scoped fallback yield 0 accepted media items, both extractors raise `SourcePackExtractionError`.
   - Scrape tools return `ToolStatus.FAILURE` with `EXTRACTION_EMPTY` rather than creating empty manifests.

3. **BrowserManager Contract Compliance**:
   - Both extractors accept `run_id: Optional[str] = None` and call `await browser.get_or_create_session(run_id)`.
   - `ShopeeScrapeTool` and `TikTokScrapeTool` forward `call.run_id`.
   - Regressions enforce the strict positional `run_id` signature matching `PlaywrightBrowserManager`.

4. **Narrow Platform Fallback**:
   - `main` and `article` generic selectors are excluded from fallback queries; fallback is strictly bounded to product-owned containers (max 10 elements).

5. **Variant Media Roles**:
   - Variant options are labeled with `MediaRole.VARIANT`, `MediaProvenance.SEMANTIC_VARIANT_MEDIA`, and `variant_label`.

6. **Secret-Safe URLs & Canonical Fingerprints**:
   - `sanitize_url` redacts auth tokens, session keys, signatures, and tracking tags in manifests and diagnostics.
   - `canonicalize_url` strips query noise so `source_pack_id` is stable.

7. **Streaming Size Bound & Orphan Cleanup**:
   - `OriginalMediaDownloader` streams responses in 64 KiB chunks and aborts immediately upon exceeding `MAX_FILE_BYTES` (20 MiB).
   - Duplicate SHA-256 files are collapsed before writing, preventing orphan files in `original/`.

8. **Side-Effect Guarantees**:
   - Pure source extraction; no AI image generation, background removal, 360° synthesis, LLM calls, scoring, ranking, or queue mutation.

9. **Known Limitations Retained**:
   - M2.2A establishes canonical Product Source Packs; M2.3 cross-platform scoring/ranking, M2.4 queue handoff, and downstream derived AI assets remain scheduled for future milestones.

10. **Merge Governance**:
    - TASK-013 is not auto-merged; human approval required.

## Generated
2026-08-16T08:05:45+07:00
