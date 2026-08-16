# RESULT-013

STATUS: READY_FOR_REVIEW

## Summary
TASK-013 FIX: Resolved TikTok false-positive captcha detection on normal product pages, verified live on product 1729981094029264939 with 7/7 authentic gallery images.

## Task Metadata
- Task: `TASK-013`
- Action: `FIX`
- Authorized Artifact: `.ai/reviews/REVIEW-013.md (fa943b9f3e)`
- Base Main SHA: `(n/a)`
- Branch: `ai/task-013`

## Files Changed
- src/product_source/platforms/tiktok.py
- tests/product_source/test_extractor_dom_fixtures.py
- tests/product_source/test_tiktok_source_extractor.py

## Diff Stat
```text
src/product_source/platforms/tiktok.py             | 64 ++++++++++++++---
 .../product_source/test_extractor_dom_fixtures.py  | 81 ++++++++++++++++++++++
 .../product_source/test_tiktok_source_extractor.py | 45 +++++++++++-
 3 files changed, 180 insertions(+), 10 deletions(-)
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
collecting ... collected 56 items

tests/product_source/test_extractor_dom_fixtures.py::test_shopee_dom_selection_and_ugc_exclusion PASSED [  1%]
tests/product_source/test_extractor_dom_fixtures.py::test_tiktok_dom_selection_and_ugc_exclusion PASSED [  3%]
tests/product_source/test_extractor_dom_fixtures.py::test_shopee_obfuscated_live_dom_gallery_extraction_and_footer_exclusion PASSED [  5%]
tests/product_source/test_extractor_dom_fixtures.py::test_shopee_image_seed_anchor_independently_extracts_gallery_without_title_anchor PASSED [  7%]
tests/product_source/test_extractor_dom_fixtures.py::test_shopee_no_structured_images_and_no_semantic_gallery_fails_closed_without_fallback PASSED [  8%]
tests/product_source/test_extractor_dom_fixtures.py::test_shopee_near_seed_ancestor_with_two_images_expands_to_full_sibling_thumbnail_strip PASSED [ 10%]
tests/product_source/test_extractor_dom_fixtures.py::test_tiktok_dom_global_captcha_scripts_do_not_block_normal_product PASSED [ 12%]
tests/product_source/test_extractor_dom_fixtures.py::test_tiktok_dom_active_challenge_blocks_extraction PASSED [ 14%]
tests/product_source/test_models.py::test_build_source_pack_id_with_product_id PASSED [ 16%]
tests/product_source/test_models.py::test_build_source_pack_id_fallback_url PASSED [ 17%]
tests/product_source/test_models.py::test_build_source_pack_id_determinism PASSED [ 19%]
tests/product_source/test_models.py::test_build_source_pack_id_ignores_tracking_and_auth_noise PASSED [ 21%]
tests/product_source/test_models.py::test_sanitize_url_redacts_sensitive_parameters PASSED [ 23%]
tests/product_source/test_models.py::test_product_fact_validation PASSED [ 25%]
tests/product_source/test_models.py::test_product_fact_frozen PASSED     [ 26%]
tests/product_source/test_models.py::test_original_media_ref_validation PASSED [ 28%]
tests/product_source/test_models.py::test_product_source_pack_validation PASSED [ 30%]
tests/product_source/test_models.py::test_description_text_bounded PASSED [ 32%]
tests/product_source/test_models.py::test_facts_media_auto_converted_to_tuples PASSED [ 33%]
tests/product_source/test_models.py::test_product_source_pack_to_dict_secret_safe PASSED [ 35%]
tests/product_source/test_models.py::test_enums_values PASSED            [ 37%]
tests/product_source/test_models.py::test_error_hierarchy PASSED         [ 39%]
tests/product_source/test_original_media_downloader.py::test_preserves_exact_original_bytes PASSED [ 41%]
tests/product_source/test_original_media_downloader.py::test_streaming_oversize_media_aborts_early PASSED [ 42%]
tests/product_source/test_original_media_downloader.py::test_diagnostics_do_not_leak_sensitive_url_tokens PASSED [ 44%]
tests/product_source/test_original_media_downloader.py::test_byte_duplicate_collapse_leaves_no_orphan_files PASSED [ 46%]
tests/product_source/test_original_media_downloader.py::test_canonical_url_dedupe_before_download PASSED [ 48%]
tests/product_source/test_original_media_downloader.py::test_max_media_per_product_enforced PASSED [ 50%]
tests/product_source/test_scrape_tool_compat.py::test_shopee_scrape_tool_schema PASSED [ 51%]
tests/product_source/test_scrape_tool_compat.py::test_tiktok_scrape_tool_schema PASSED [ 53%]
tests/product_source/test_scrape_tool_compat.py::test_shopee_scrape_tool_passes_run_id_to_browser_manager PASSED [ 55%]
tests/product_source/test_scrape_tool_compat.py::test_tiktok_scrape_tool_passes_run_id_to_browser_manager PASSED [ 57%]
tests/product_source/test_scrape_tool_compat.py::test_tools_do_not_call_image_processor PASSED [ 58%]
tests/product_source/test_scrape_tool_compat.py::test_tools_do_not_invoke_llm PASSED [ 60%]
tests/product_source/test_scrape_tool_compat.py::test_partial_upload_returns_partial_success PASSED [ 62%]
tests/product_source/test_scrape_tool_compat.py::test_full_upload_failure_returns_failure PASSED [ 64%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_prefers_structured_data_when_identity_matches PASSED [ 66%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_rejects_unrelated_structured_data_on_identity_mismatch PASSED [ 67%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_fails_closed_when_no_media_found PASSED [ 69%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_collects_explicit_variants PASSED [ 71%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_gallery_fallback_when_no_structured_images PASSED [ 73%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_seller_description_media_labeled PASSED [ 75%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_raises_blocked_on_captcha PASSED [ 76%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_with_strict_browser_manager PASSED [ 78%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_rejects_overlapping_substring_id PASSED [ 80%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_js_script_excludes_reviews_by_container_provenance PASSED [ 82%]
tests/product_source/test_tiktok_source_extractor.py::test_tiktok_extractor_prefers_structured_data_when_identity_matches PASSED [ 83%]
tests/product_source/test_tiktok_source_extractor.py::test_tiktok_extractor_rejects_unrelated_structured_data_on_identity_mismatch PASSED [ 85%]
tests/product_source/test_tiktok_source_extractor.py::test_tiktok_extractor_fails_closed_when_no_media_found PASSED [ 87%]
tests/product_source/test_tiktok_source_extractor.py::test_tiktok_extractor_collects_explicit_variants PASSED [ 89%]
tests/product_source/test_tiktok_source_extractor.py::test_tiktok_extractor_gallery_fallback PASSED [ 91%]
tests/product_source/test_tiktok_source_extractor.py::test_tiktok_extractor_with_strict_browser_manager PASSED [ 92%]
tests/product_source/test_tiktok_source_extractor.py::test_tiktok_extractor_rejects_overlapping_substring_id PASSED [ 94%]
tests/product_source/test_tiktok_source_extractor.py::test_tiktok_js_script_excludes_reviews_and_no_main_article_fallback PASSED [ 96%]
tests/product_source/test_tiktok_source_extractor.py::test_tiktok_extractor_does_not_block_on_globally_loaded_captcha_scripts PASSED [ 98%]
tests/product_source/test_tiktok_source_extractor.py::test_tiktok_extractor_raises_blocked_on_active_challenge PASSED [100%]

============================== warnings summary ===============================
tests/product_source/test_extractor_dom_fixtures.py::test_shopee_dom_selection_and_ugc_exclusion
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:1153: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    return asyncio.get_event_loop_policy()

tests/product_source/test_extractor_dom_fixtures.py: 8 warnings
tests/product_source/test_original_media_downloader.py: 6 warnings
tests/product_source/test_scrape_tool_compat.py: 4 warnings
tests/product_source/test_shopee_source_extractor.py: 10 warnings
tests/product_source/test_tiktok_source_extractor.py: 10 warnings
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:844: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    _restore_event_loop_policy(asyncio.get_event_loop_policy()),

tests/product_source/test_extractor_dom_fixtures.py: 8 warnings
tests/product_source/test_original_media_downloader.py: 6 warnings
tests/product_source/test_scrape_tool_compat.py: 4 warnings
tests/product_source/test_shopee_source_extractor.py: 10 warnings
tests/product_source/test_tiktok_source_extractor.py: 10 warnings
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:1125: DeprecationWarning: 'asyncio.set_event_loop_policy' is deprecated and slated for removal in Python 3.16
    asyncio.set_event_loop_policy(new_loop_policy)

tests/product_source/test_extractor_dom_fixtures.py: 8 warnings
tests/product_source/test_original_media_downloader.py: 6 warnings
tests/product_source/test_scrape_tool_compat.py: 4 warnings
tests/product_source/test_shopee_source_extractor.py: 10 warnings
tests/product_source/test_tiktok_source_extractor.py: 10 warnings
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:1126: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    loop = asyncio.get_event_loop_policy().new_event_loop()

tests/product_source/test_extractor_dom_fixtures.py: 8 warnings
tests/product_source/test_original_media_downloader.py: 6 warnings
tests/product_source/test_scrape_tool_compat.py: 4 warnings
tests/product_source/test_shopee_source_extractor.py: 10 warnings
tests/product_source/test_tiktok_source_extractor.py: 10 warnings
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:859: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    policy = asyncio.get_event_loop_policy()

tests/product_source/test_extractor_dom_fixtures.py: 8 warnings
tests/product_source/test_original_media_downloader.py: 6 warnings
tests/product_source/test_scrape_tool_compat.py: 4 warnings
tests/product_source/test_shopee_source_extractor.py: 10 warnings
tests/product_source/test_tiktok_source_extractor.py: 10 warnings
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:904: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    policy = asyncio.get_event_loop_policy()

tests/product_source/test_extractor_dom_fixtures.py: 8 warnings
tests/product_source/test_original_media_downloader.py: 6 warnings
tests/product_source/test_scrape_tool_compat.py: 4 warnings
tests/product_source/test_shopee_source_extractor.py: 10 warnings
tests/product_source/test_tiktok_source_extractor.py: 10 warnings
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:928: DeprecationWarning: 'asyncio.set_event_loop_policy' is deprecated and slated for removal in Python 3.16
    asyncio.set_event_loop_policy(previous_policy)

tests/product_source/test_extractor_dom_fixtures.py: 8 warnings
tests/product_source/test_original_media_downloader.py: 6 warnings
tests/product_source/test_scrape_tool_compat.py: 4 warnings
tests/product_source/test_shopee_source_extractor.py: 10 warnings
tests/product_source/test_tiktok_source_extractor.py: 10 warnings
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:940: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    policy = asyncio.get_event_loop_policy()

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
====================== 56 passed, 267 warnings in 11.74s ======================
........................................................................ [ 15%]
........................................................................ [ 30%]
........................................................................ [ 45%]
........................................................................ [ 60%]
........................................................................ [ 75%]
........................................................................ [ 91%]
..........................................                               [100%]
474 passed in 64.64s (0:01:04)

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
 .ai/results/RESULT-013.md                          | 224 ++++++++
 docs/PHASE_6_PRODUCT_SOURCE_PACK.md                | 171 ++++++
 src/product_source/__init__.py                     |  28 +
 src/product_source/downloader.py                   | 220 ++++++++
 src/product_source/extractor.py                    |  10 +
 src/product_source/models.py                       | 235 ++++++++
 src/product_source/platforms/__init__.py           |   5 +
 src/product_source/platforms/shopee.py             | 622 +++++++++++++++++++++
 src/product_source/platforms/tiktok.py             | 529 ++++++++++++++++++
 src/product_source/serialization.py                |  20 +
 src/tools/shopee_scrape_tool.py                    | 378 ++++++-------
 src/tools/tiktok_scrape_tool.py                    | 329 +++++------
 tests/product_source/__init__.py                   |   1 +
 .../product_source/test_extractor_dom_fixtures.py  | 569 +++++++++++++++++++
 tests/product_source/test_models.py                | 223 ++++++++
 .../test_original_media_downloader.py              | 270 +++++++++
 tests/product_source/test_scrape_tool_compat.py    | 300 ++++++++++
 .../product_source/test_shopee_source_extractor.py | 310 ++++++++++
 .../product_source/test_tiktok_source_extractor.py | 322 +++++++++++
 19 files changed, 4395 insertions(+), 371 deletions(-)
```

### Corrections Implemented (Round 12 - TikTok Active Challenge Detection & Extraction):
1. Fixed TikTok False-Positive Captcha Detection:
   - Replaced naive `script[src*="captcha"]` check with `hasActiveChallenge()` in `src/product_source/platforms/tiktok.py`.
   - Now checks for active challenge UI elements (`#captcha-verify-image`, `#captcha_container`, `.captcha_verify_container`, `.secsdk-captcha-drag-icon`, `iframe[src*="captcha"]`, `[class*="captcha-modal"]`, `[class*="secsdk_captcha"]`) and challenge title/paths, rather than globally loaded background captcha bundles.
   - Added support for `.slick-slider`, `.slick-track` in TikTok semantic gallery selectors.
   - Added title fallback to H1 heading and stripped TikTok Shop title suffixes.
2. Deterministic Regression Tests Added:
   - `test_tiktok_extractor_does_not_block_on_globally_loaded_captcha_scripts` and `test_tiktok_extractor_raises_blocked_on_active_challenge` in `tests/product_source/test_tiktok_source_extractor.py`.
   - `test_tiktok_dom_global_captcha_scripts_do_not_block_normal_product` and `test_tiktok_dom_active_challenge_blocks_extraction` in `tests/product_source/test_extractor_dom_fixtures.py`.
3. Pre-Merge Live CDP Validation Evidence (2026-08-16):
   - TikTok product `1729981094029264939` (UVGREEN KA600 redirected from `https://vt.tiktok.com/ZS9ky3CJwy3LY-NGB3c/`):
     - Title: `'[TẶNG LỌC 1.250K] [Live] Máy Lọc Không Khí Diệt Khuẩn Diệt Khuẩn UVC LED UVGREEN KA600 60m2 - Máy Tạo Ion Âm Air Purifiers Làm Sạch Không Khí, Bộ Lọc HEPA H13 Lọc Sạch Bụi Mịn, Mùi Hôi, Khói, Lông Tóc - Bảo hành chính hãng 24 tháng'`
     - Product ID: `'1729981094029264939'`
     - Blocked: False
     - MEDIA COUNT: 7 (All 7 authentic seller product gallery views captured, 0 UGC/review images, 0 footer/header).
   - TikTok Active Challenge Fail-Closed:
     - Direct unauthenticated navigation to `/vn/pdp/1729981094029264939` correctly detected `#captcha_container` / `Security Check` and raised `SourcePackBlockedError`.
   - Shopee product `52764529835` (TP-Link TC70):
     - Maintained 5/5 authentic seller gallery views with overlay badge excluded and 0 contamination.

### Test Results:
- Focused Product Source Pack suite (`tests/product_source/`): 56 passed, 0 failed.
- Full repository suite (`tests/`): 474 passed, 0 failed.

### Invariants Preserved:
- Exact identity matching, identity-gated structured fields, explicit model/SKU capture, pattern-based signed URL redaction, run-id plumbing, zero-media fail closed, streaming size bounds, SHA-256 dedupe, no AI image generation / LLM / scoring / ranking / queue mutation.
- Known limitations: M2.2A establishes canonical Product Source Packs; M2.3 scoring/ranking and M2.4 queue handoff remain scheduled for future milestones.
- Merge governance: Do not merge automatically. Human review required.

## Generated
2026-08-16T12:11:18+07:00
