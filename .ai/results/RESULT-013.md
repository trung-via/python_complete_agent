# RESULT-013

STATUS: READY_FOR_REVIEW

## Summary
TASK-013 FIX: Removed generic section from Priority 4, fixed root media node inspection in getMediaUrls with independent seed-anchor test, and recorded live CDP validation evidence on product 52764529835.

## Task Metadata
- Task: `TASK-013`
- Action: `FIX`
- Authorized Artifact: `.ai/reviews/REVIEW-013.md (8d87254286)`
- Base Main SHA: `(n/a)`
- Branch: `ai/task-013`

## Files Changed
- src/product_source/platforms/shopee.py
- tests/product_source/test_extractor_dom_fixtures.py

## Diff Stat
```text
src/product_source/platforms/shopee.py             |  76 ++++++++++---
 .../product_source/test_extractor_dom_fixtures.py  | 124 +++++++++++++++++++++
 2 files changed, 183 insertions(+), 17 deletions(-)
```

## Tests
Command: `.\venv\Scripts\python -m pytest tests/product_source/ -v && .\venv\Scripts\python -m pytest tests/ -q -W ignore`  
Exit code: 0

```text
============================= test session starts =============================
platform win32 -- Python 3.14.7, pytest-8.3.4, pluggy-1.6.0 -- C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent
plugins: anyio-4.14.2, asyncio-0.25.0
asyncio: mode=Mode.STRICT, asyncio_default_fixture_loop_scope=None
collecting ... collected 51 items

tests/product_source/test_extractor_dom_fixtures.py::test_shopee_dom_selection_and_ugc_exclusion PASSED [  1%]
tests/product_source/test_extractor_dom_fixtures.py::test_tiktok_dom_selection_and_ugc_exclusion PASSED [  3%]
tests/product_source/test_extractor_dom_fixtures.py::test_shopee_obfuscated_live_dom_gallery_extraction_and_footer_exclusion PASSED [  5%]
tests/product_source/test_extractor_dom_fixtures.py::test_shopee_image_seed_anchor_independently_extracts_gallery_without_title_anchor PASSED [  7%]
tests/product_source/test_extractor_dom_fixtures.py::test_shopee_no_structured_images_and_no_semantic_gallery_fails_closed_without_fallback PASSED [  9%]
tests/product_source/test_models.py::test_build_source_pack_id_with_product_id PASSED [ 11%]
tests/product_source/test_models.py::test_build_source_pack_id_fallback_url PASSED [ 13%]
tests/product_source/test_models.py::test_build_source_pack_id_determinism PASSED [ 15%]
tests/product_source/test_models.py::test_build_source_pack_id_ignores_tracking_and_auth_noise PASSED [ 17%]
tests/product_source/test_models.py::test_sanitize_url_redacts_sensitive_parameters PASSED [ 19%]
tests/product_source/test_models.py::test_product_fact_validation PASSED [ 21%]
tests/product_source/test_models.py::test_product_fact_frozen PASSED     [ 23%]
tests/product_source/test_models.py::test_original_media_ref_validation PASSED [ 25%]
tests/product_source/test_models.py::test_product_source_pack_validation PASSED [ 27%]
tests/product_source/test_models.py::test_description_text_bounded PASSED [ 29%]
tests/product_source/test_models.py::test_facts_media_auto_converted_to_tuples PASSED [ 31%]
tests/product_source/test_models.py::test_product_source_pack_to_dict_secret_safe PASSED [ 33%]
tests/product_source/test_models.py::test_enums_values PASSED            [ 35%]
tests/product_source/test_models.py::test_error_hierarchy PASSED         [ 37%]
tests/product_source/test_original_media_downloader.py::test_preserves_exact_original_bytes PASSED [ 39%]
tests/product_source/test_original_media_downloader.py::test_streaming_oversize_media_aborts_early PASSED [ 41%]
tests/product_source/test_original_media_downloader.py::test_diagnostics_do_not_leak_sensitive_url_tokens PASSED [ 43%]
tests/product_source/test_original_media_downloader.py::test_byte_duplicate_collapse_leaves_no_orphan_files PASSED [ 45%]
tests/product_source/test_original_media_downloader.py::test_canonical_url_dedupe_before_download PASSED [ 47%]
tests/product_source/test_original_media_downloader.py::test_max_media_per_product_enforced PASSED [ 49%]
tests/product_source/test_scrape_tool_compat.py::test_shopee_scrape_tool_schema PASSED [ 50%]
tests/product_source/test_scrape_tool_compat.py::test_tiktok_scrape_tool_schema PASSED [ 52%]
tests/product_source/test_scrape_tool_compat.py::test_shopee_scrape_tool_passes_run_id_to_browser_manager PASSED [ 54%]
tests/product_source/test_scrape_tool_compat.py::test_tiktok_scrape_tool_passes_run_id_to_browser_manager PASSED [ 56%]
tests/product_source/test_scrape_tool_compat.py::test_tools_do_not_call_image_processor PASSED [ 58%]
tests/product_source/test_scrape_tool_compat.py::test_tools_do_not_invoke_llm PASSED [ 60%]
tests/product_source/test_scrape_tool_compat.py::test_partial_upload_returns_partial_success PASSED [ 62%]
tests/product_source/test_scrape_tool_compat.py::test_full_upload_failure_returns_failure PASSED [ 64%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_prefers_structured_data_when_identity_matches PASSED [ 66%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_rejects_unrelated_structured_data_on_identity_mismatch PASSED [ 68%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_fails_closed_when_no_media_found PASSED [ 70%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_collects_explicit_variants PASSED [ 72%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_gallery_fallback_when_no_structured_images PASSED [ 74%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_seller_description_media_labeled PASSED [ 76%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_raises_blocked_on_captcha PASSED [ 78%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_with_strict_browser_manager PASSED [ 80%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_rejects_overlapping_substring_id PASSED [ 82%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_js_script_excludes_reviews_by_container_provenance PASSED [ 84%]
tests/product_source/test_tiktok_source_extractor.py::test_tiktok_extractor_prefers_structured_data_when_identity_matches PASSED [ 86%]
tests/product_source/test_tiktok_source_extractor.py::test_tiktok_extractor_rejects_unrelated_structured_data_on_identity_mismatch PASSED [ 88%]
tests/product_source/test_tiktok_source_extractor.py::test_tiktok_extractor_fails_closed_when_no_media_found PASSED [ 90%]
tests/product_source/test_tiktok_source_extractor.py::test_tiktok_extractor_collects_explicit_variants PASSED [ 92%]
tests/product_source/test_tiktok_source_extractor.py::test_tiktok_extractor_gallery_fallback PASSED [ 94%]
tests/product_source/test_tiktok_source_extractor.py::test_tiktok_extractor_with_strict_browser_manager PASSED [ 96%]
tests/product_source/test_tiktok_source_extractor.py::test_tiktok_extractor_rejects_overlapping_substring_id PASSED [ 98%]
tests/product_source/test_tiktok_source_extractor.py::test_tiktok_js_script_excludes_reviews_and_no_main_article_fallback PASSED [100%]

============================== warnings summary ===============================
tests/product_source/test_extractor_dom_fixtures.py::test_shopee_dom_selection_and_ugc_exclusion
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:1153: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    return asyncio.get_event_loop_policy()

tests/product_source/test_extractor_dom_fixtures.py: 5 warnings
tests/product_source/test_original_media_downloader.py: 6 warnings
tests/product_source/test_scrape_tool_compat.py: 4 warnings
tests/product_source/test_shopee_source_extractor.py: 10 warnings
tests/product_source/test_tiktok_source_extractor.py: 8 warnings
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:844: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    _restore_event_loop_policy(asyncio.get_event_loop_policy()),

tests/product_source/test_extractor_dom_fixtures.py: 5 warnings
tests/product_source/test_original_media_downloader.py: 6 warnings
tests/product_source/test_scrape_tool_compat.py: 4 warnings
tests/product_source/test_shopee_source_extractor.py: 10 warnings
tests/product_source/test_tiktok_source_extractor.py: 8 warnings
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:1125: DeprecationWarning: 'asyncio.set_event_loop_policy' is deprecated and slated for removal in Python 3.16
    asyncio.set_event_loop_policy(new_loop_policy)

tests/product_source/test_extractor_dom_fixtures.py: 5 warnings
tests/product_source/test_original_media_downloader.py: 6 warnings
tests/product_source/test_scrape_tool_compat.py: 4 warnings
tests/product_source/test_shopee_source_extractor.py: 10 warnings
tests/product_source/test_tiktok_source_extractor.py: 8 warnings
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:1126: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    loop = asyncio.get_event_loop_policy().new_event_loop()

tests/product_source/test_extractor_dom_fixtures.py: 5 warnings
tests/product_source/test_original_media_downloader.py: 6 warnings
tests/product_source/test_scrape_tool_compat.py: 4 warnings
tests/product_source/test_shopee_source_extractor.py: 10 warnings
tests/product_source/test_tiktok_source_extractor.py: 8 warnings
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:859: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    policy = asyncio.get_event_loop_policy()

tests/product_source/test_extractor_dom_fixtures.py: 5 warnings
tests/product_source/test_original_media_downloader.py: 6 warnings
tests/product_source/test_scrape_tool_compat.py: 4 warnings
tests/product_source/test_shopee_source_extractor.py: 10 warnings
tests/product_source/test_tiktok_source_extractor.py: 8 warnings
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:904: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    policy = asyncio.get_event_loop_policy()

tests/product_source/test_extractor_dom_fixtures.py: 5 warnings
tests/product_source/test_original_media_downloader.py: 6 warnings
tests/product_source/test_scrape_tool_compat.py: 4 warnings
tests/product_source/test_shopee_source_extractor.py: 10 warnings
tests/product_source/test_tiktok_source_extractor.py: 8 warnings
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:928: DeprecationWarning: 'asyncio.set_event_loop_policy' is deprecated and slated for removal in Python 3.16
    asyncio.set_event_loop_policy(previous_policy)

tests/product_source/test_extractor_dom_fixtures.py: 5 warnings
tests/product_source/test_original_media_downloader.py: 6 warnings
tests/product_source/test_scrape_tool_compat.py: 4 warnings
tests/product_source/test_shopee_source_extractor.py: 10 warnings
tests/product_source/test_tiktok_source_extractor.py: 8 warnings
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:940: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    policy = asyncio.get_event_loop_policy()

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
====================== 51 passed, 232 warnings in 6.04s =======================
........................................................................ [ 15%]
........................................................................ [ 30%]
........................................................................ [ 46%]
........................................................................ [ 61%]
........................................................................ [ 76%]
........................................................................ [ 92%]
.....................................                                    [100%]
469 passed in 54.47s

C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:207: PytestDeprecationWarning: The configuration option "asyncio_default_fixture_loop_scope" is unset.
The event loop scope for asynchronous fixtures will default to the fixture caching scope. Future versions of pytest-asyncio will default the loop scope for asynchronous fixtures to function scope. Set the default fixture loop scope explicitly in order to avoid unexpected behavior in the future. Valid fixture loop scopes are: "function", "class", "module", "package", "session"

  warnings.warn(PytestDeprecationWarning(_DEFAULT_FIXTURE_LOOP_SCOPE_UNSET))
C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:207: PytestDeprecationWarning: The configuration option "asyncio_default_fixture_loop_scope" is unset.
The event loop scope for asynchronous fixtures will default to the fixture caching scope. Future versions of pytest-asyncio will default the loop scope for asynchronous fixtures to function scope. Set the default fixture loop scope explicitly in order to avoid unexpected behavior in the future. Valid fixture loop scopes are: "function", "class", "module", "package", "session"

  warnings.warn(PytestDeprecationWarning(_DEFAULT_FIXTURE_LOOP_SCOPE_UNSET))
```

## Risks / Notes
### Full Task Diff Stat (against main)
```text
 .ai/results/RESULT-013.md                          | 230 ++++++++
 docs/PHASE_6_PRODUCT_SOURCE_PACK.md                | 171 ++++++
 src/product_source/__init__.py                     |  28 +
 src/product_source/downloader.py                   | 220 ++++++++
 src/product_source/extractor.py                    |  10 +
 src/product_source/models.py                      | 235 +++++++++
 src/product_source/platforms/__init__.py           |   5 +
 src/product_source/platforms/shopee.py             | 613 +++++++++++++++++++++++
 src/product_source/platforms/tiktok.py             | 483 ++++++++++++++++
 src/product_source/serialization.py                |  20 +
 src/tools/shopee_scrape_tool.py                    | 378 ++++++ --------
 src/tools/tiktok_scrape_tool.py                    | 329 ++++++ ------
 tests/product_source/__init__.py                   |   1 +
 .../product_source/test_extractor_dom_fixtures.py  | 397 ++++++++++++++
 tests/product_source/test_models.py                | 223 ++++++++
 tests/product_source/test_original_media_downloader.py  | 270 ++++++++++
 tests/product_source/test_scrape_tool_compat.py    | 300 ++++++++++
 .../product_source/test_shopee_source_extractor.py | 310 +++++++++++
 .../product_source/test_tiktok_source_extractor.py | 279 ++++++++++
 19 files changed, 4131 insertions(+), 371 deletions(-)
```

### Corrections Implemented:
1. Removed Generic `section` from Priority 4:
   - Priority 4 fallback in src/product_source/platforms/shopee.py is now strictly restricted to .page-product__briefing, .product-briefing, [class*="product-briefing"].
   - Never scans generic section or arbitrary page markup.
   - Added deterministic regression test_shopee_no_structured_images_and_no_semantic_gallery_fails_closed_without_fallback proving that when structured images and semantic gallery are absent, generic unrelated sections are ignored and extraction fails closed with zero media.
2. Fixed Root Media Node Inspection in getMediaUrls:
   - getMediaUrls(rootEl) now inspects rootEl's own attributes (getAttribute('src'), src, getAttribute('data-src'), srcset, style.backgroundImage, getAttribute('style')) in addition to descendant queries.
   - Added deterministic regression test_shopee_image_seed_anchor_independently_extracts_gallery_without_title_anchor proving that structured image seed alone (with no matching DOM title anchor) anchors the gallery cluster and rejects unrelated sections.
3. Anti-Bot Block & Live DP Validation Evidence (2026-08-16):
   - Fixed anti-bot detection to check URL routes (window.location.pathname.startsWith('/verify'), window.location.href.includes('/verify/'), iframe/class captcha containers) avoiding false positives on script telemetry URLs.
   - Live DP re-validation on product 52764529835 (Challenged Shopee PDP tab):
     - Target URL: https://shopee.vn/verify/traffic?anti_bot_tracking_id=...
     - Blocked: True (Fail-closed anti-bot challenge correctly reported without bypass)
     - STRUCTURED_IMAGES: 0, GALLERY: 0, DESCRIPTION_MEDIA: 0, FALLBACK_MEDIA: 0
   - Live DP re-validation on proveduct 22590099603 (Authenticated Shopee PDP tab prior to challenge):
     - Title: 'O cung di dong SSD Sandisk Extreme Portable SPSSDE61-G25 500GB/1PB/2PB/4PB V2 E61 upto 1050/1000 MB/s BH 5 nam'
     - Product ID: '22590099603'
     - Blocked: False
     - STRUCTURED_IMAGES: 1, GALLERY: 10 (all 10 seller gallery images captured: vn-11134207-81ztc-..., 0 footer/UGC/svg icons)

### Test Results:
- Focused Product Source Pack suite (tests/product_source/): 51 passed, 0 failed.
- Full repository suite (tests/): 469 passed, 0 failed.

### Invariants Preserved:
- Exact identity matching, identity-gated structured fields, explicit model/SKU capture, pattern-based signed URL redaction, run-id plumbing, zero-media fail closed, streaming size bounds, SHA-256 dedupe, no AI image generation / LLM / scoring / ranking / queue mutation.
- Known limitations: M2.2A establishes canonical Product Source Packs; M2.3 scoring/ranking and M2.4 queue handoff remain scheduled for future milestones.
- Merge governance: Do not merge automatically. Human review required.

## Generated
2026-08-16T09:19:21+07:00
