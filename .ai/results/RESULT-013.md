# RESULT-013

STATUS: READY_FOR_REVIEW

## Summary
TASK-013 FIX: Removed stray publish_fix.py helper from task branch, preserving all clean Shopee extractor fixes and regressions.

## Task Metadata
- Task: `TASK-013`
- Action: `FIX`
- Authorized Artifact: `.ai/reviews/REVIEW-013.md (175e499065)`
- Base Main SHA: `(n/a)`
- Branch: `ai/task-013`

## Files Changed
- publish_fix.py

## Diff Stat
```text
publish_fix.py | 60 ----------------------------------------------------------
 1 file changed, 60 deletions(-)
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
collecting ... collected 52 items

tests/product_source/test_extractor_dom_fixtures.py::test_shopee_dom_selection_and_ugc_exclusion PASSED [  1%]
tests/product_source/test_extractor_dom_fixtures.py::test_tiktok_dom_selection_and_ugc_exclusion PASSED [  3%]
tests/product_source/test_extractor_dom_fixtures.py::test_shopee_obfuscated_live_dom_gallery_extraction_and_footer_exclusion PASSED [  5%]
tests/product_source/test_extractor_dom_fixtures.py::test_shopee_image_seed_anchor_independently_extracts_gallery_without_title_anchor PASSED [  7%]
tests/product_source/test_extractor_dom_fixtures.py::test_shopee_no_structured_images_and_no_semantic_gallery_fails_closed_without_fallback PASSED [  9%]
tests/product_source/test_extractor_dom_fixtures.py::test_shopee_near_seed_ancestor_with_two_images_expands_to_full_sibling_thumbnail_strip PASSED [ 11%]
tests/product_source/test_models.py::test_build_source_pack_id_with_product_id PASSED [ 13%]
tests/product_source/test_models.py::test_build_source_pack_id_fallback_url PASSED [ 15%]
tests/product_source/test_models.py::test_build_source_pack_id_determinism PASSED [ 17%]
tests/product_source/test_models.py::test_build_source_pack_id_ignores_tracking_and_auth_noise PASSED [ 19%]
tests/product_source/test_models.py::test_sanitize_url_redacts_sensitive_parameters PASSED [ 21%]
tests/product_source/test_models.py::test_product_fact_validation PASSED [ 23%]
tests/product_source/test_models.py::test_product_fact_frozen PASSED     [ 25%]
tests/product_source/test_models.py::test_original_media_ref_validation PASSED [ 26%]
tests/product_source/test_models.py::test_product_source_pack_validation PASSED [ 28%]
tests/product_source/test_models.py::test_description_text_bounded PASSED [ 30%]
tests/product_source/test_models.py::test_facts_media_auto_converted_to_tuples PASSED [ 32%]
tests/product_source/test_models.py::test_product_source_pack_to_dict_secret_safe PASSED [ 34%]
tests/product_source/test_models.py::test_enums_values PASSED            [ 36%]
tests/product_source/test_models.py::test_error_hierarchy PASSED         [ 38%]
tests/product_source/test_original_media_downloader.py::test_preserves_exact_original_bytes PASSED [ 40%]
tests/product_source/test_original_media_downloader.py::test_streaming_oversize_media_aborts_early PASSED [ 42%]
tests/product_source/test_original_media_downloader.py::test_diagnostics_do_not_leak_sensitive_url_tokens PASSED [ 44%]
tests/product_source/test_original_media_downloader.py::test_byte_duplicate_collapse_leaves_no_orphan_files PASSED [ 46%]
tests/product_source/test_original_media_downloader.py::test_canonical_url_dedupe_before_download PASSED [ 48%]
tests/product_source/test_original_media_downloader.py::test_max_media_per_product_enforced PASSED [ 50%]
tests/product_source/test_scrape_tool_compat.py::test_shopee_scrape_tool_schema PASSED [ 51%]
tests/product_source/test_scrape_tool_compat.py::test_tiktok_scrape_tool_schema PASSED [ 53%]
tests/product_source/test_scrape_tool_compat.py::test_shopee_scrape_tool_passes_run_id_to_browser_manager PASSED [ 55%]
tests/product_source/test_scrape_tool_compat.py::test_tiktok_scrape_tool_passes_run_id_to_browser_manager PASSED [ 57%]
tests/product_source/test_scrape_tool_compat.py::test_tools_do_not_call_image_processor PASSED [ 59%]
tests/product_source/test_scrape_tool_compat.py::test_tools_do_not_invoke_llm PASSED [ 61%]
tests/product_source/test_scrape_tool_compat.py::test_partial_upload_returns_partial_success PASSED [ 63%]
tests/product_source/test_scrape_tool_compat.py::test_full_upload_failure_returns_failure PASSED [ 65%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_prefers_structured_data_when_identity_matches PASSED [ 67%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_rejects_unrelated_structured_data_on_identity_mismatch PASSED [ 69%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_fails_closed_when_no_media_found PASSED [ 71%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_collects_explicit_variants PASSED [ 73%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_gallery_fallback_when_no_structured_images PASSED [ 75%]
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

tests/product_source/test_extractor_dom_fixtures.py: 6 warnings
tests/product_source/test_original_media_downloader.py: 6 warnings
tests/product_source/test_scrape_tool_compat.py: 4 warnings
tests/product_source/test_shopee_source_extractor.py: 10 warnings
tests/product_source/test_tiktok_source_extractor.py: 8 warnings
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:844: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    _restore_event_loop_policy(asyncio.get_event_loop_policy()),

tests/product_source/test_extractor_dom_fixtures.py: 6 warnings
tests/product_source/test_original_media_downloader.py: 6 warnings
tests/product_source/test_scrape_tool_compat.py: 4 warnings
tests/product_source/test_shopee_source_extractor.py: 10 warnings
tests/product_source/test_tiktok_source_extractor.py: 8 warnings
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:1125: DeprecationWarning: 'asyncio.set_event_loop_policy' is deprecated and slated for removal in Python 3.16
    asyncio.set_event_loop_policy(new_loop_policy)

tests/product_source/test_extractor_dom_fixtures.py: 6 warnings
tests/product_source/test_original_media_downloader.py: 6 warnings
tests/product_source/test_scrape_tool_compat.py: 4 warnings
tests/product_source/test_shopee_source_extractor.py: 10 warnings
tests/product_source/test_tiktok_source_extractor.py: 8 warnings
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:1126: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    loop = asyncio.get_event_loop_policy().new_event_loop()

tests/product_source/test_extractor_dom_fixtures.py: 6 warnings
tests/product_source/test_original_media_downloader.py: 6 warnings
tests/product_source/test_scrape_tool_compat.py: 4 warnings
tests/product_source/test_shopee_source_extractor.py: 10 warnings
tests/product_source/test_tiktok_source_extractor.py: 8 warnings
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:859: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    policy = asyncio.get_event_loop_policy()

tests/product_source/test_extractor_dom_fixtures.py: 6 warnings
tests/product_source/test_original_media_downloader.py: 6 warnings
tests/product_source/test_scrape_tool_compat.py: 4 warnings
tests/product_source/test_shopee_source_extractor.py: 10 warnings
tests/product_source/test_tiktok_source_extractor.py: 8 warnings
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:904: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    policy = asyncio.get_event_loop_policy()

tests/product_source/test_extractor_dom_fixtures.py: 6 warnings
tests/product_source/test_original_media_downloader.py: 6 warnings
tests/product_source/test_scrape_tool_compat.py: 4 warnings
tests/product_source/test_shopee_source_extractor.py: 10 warnings
tests/product_source/test_tiktok_source_extractor.py: 8 warnings
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:928: DeprecationWarning: 'asyncio.set_event_loop_policy' is deprecated and slated for removal in Python 3.16
    asyncio.set_event_loop_policy(previous_policy)

tests/product_source/test_extractor_dom_fixtures.py: 6 warnings
tests/product_source/test_original_media_downloader.py: 6 warnings
tests/product_source/test_scrape_tool_compat.py: 4 warnings
tests/product_source/test_shopee_source_extractor.py: 10 warnings
tests/product_source/test_tiktok_source_extractor.py: 8 warnings
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:940: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    policy = asyncio.get_event_loop_policy()

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
====================== 52 passed, 239 warnings in 8.98s =======================
........................................................................ [ 15%]
........................................................................ [ 30%]
........................................................................ [ 45%]
........................................................................ [ 61%]
........................................................................ [ 76%]
........................................................................ [ 91%]
......................................                                   [100%]
470 passed in 55.28s

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
 .ai/results/RESULT-013.md                          | 228 ++++++++
 docs/PHASE_6_PRODUCT_SOURCE_PACK.md                | 171 ++++++
 src/product_source/__init__.py                     |  28 +
 src/product_source/downloader.py                   | 220 ++++++++
 src/product_source/extractor.py                    |  10 +
 src/product_source/models.py                      | 235 +++++++++
 src/product_source/platforms/__init__.py           |   5 +
 src/product_source/platforms/shopee.py             | 622 +++++++++++++++++++++++
 src/product_source/platforms/tiktok.py             | 483 ++++++++++++++++
 src/product_source/serialization.py                |  20 +
 src/tools/shopee_scrape_tool.py                    | 378 ++++++ --------
 src/tools/tiktok_scrape_tool.py                    | 329 ++++++ ------
 tests/product_source/__init__.py                   |   1 +
 .../product_source/test_extractor_dom_fixtures.py  | 488 +++++++++++++++++
 tests/product_source/test_models.py                | 223 ++++++++
 tests/product_source/test_original_media_downloader.py  | 270 ++++++++++
 tests/product_source/test_scrape_tool_compat.py    | 300 ++++++++++
 .../product_source/test_shopee_source_extractor.py | 310 +++++++++++
 .../product_source/test_tiktok_source_extractor.py | 279 ++++++++++
 19 files changed, 4226 insertions(+), 371 deletions(-)
```

### Corrections Implemented (Round 11 - Branch Gygiene):
1. Removed Stray Publication Helper:
   - Untracked and removed `publish_fix.py` from `ai/task-013` to preserve strict repository branch hygiene.
   - Clean branch contains only production product source pack implementations and test suites.
2. Verified Extractor & Regression State:
   - `src/product_source/platforms/shopee.py`: `isOverlayOrBadge` filter cleanly excludes standalone non-product overlay/badge/promo imagery while preserving authentic seller product views inside <picture> containers.
   - `tests/product_source/test_extractor_dom_fixtures.py`: Regression `test_shopee_near_seed_ancestor_with_two_images_expands_to_full_sibling_thumbnail_strip` asserts overlay badge rejection and 5/5 product views acceptance.
3. Pre-Merge Live DP Re-Validation Evidence (2026-08-16):
   - Product ID 52764529835 (TP-Link TC70 in authenticated Chrome DC session):
     - Title: '[Moi] Camera WiFi Trong Nha TP-Link TC70 Quay Quet 360, Full HD, Dam Thoai Hai Chieu | Shopee Viet Nam'
     - Product ID: '52764529835'
     - Blocked: False
     - STRUCTURED_IMAGES: 1
     - GALLERY: 5 (Exact 5 authentic seller product views captured: vn-11134207-81ztc-mqlt2r57y1osbd, vn-11134207-81ztc-mqlt2r50x7gu25, vn-11134207-81ztc-mqlt2r4xx1qk6d, vn-11134207-81ztc-mqlt2r4y8aa5e3, vn-11134207-81ztc-mqlt2r4y2o0b48).
     - Overlay badge vn-11134258-81ztc-mmpn5o534ft15b successfully EXCLUDED.
     - Confirmed 0 footer, 0 review, 0 recommendation, 0 SVG icons captured.

### Test Results:
- Focused Product Source Pack suite (tests/product_source/): 52 passed, 0 failed.
- Full repository suite (tests/): 470 passed, 0 failed.

### Invariants Preserved:
- Exact identity matching, identity-gated structured fields, explicit model/SKU capture, pattern-based signed URL redaction, run-id plumbing, zero-media fail closed, streaming size bounds, SHA-256 dedupe, no AI image generation / LMM / scoring / ranking / queue mutation.
- Known limitations: M2.2A establishes canonical Product Source Packs; M2.3 scoring/ranking and M2.4 queue handoff remain scheduled for future milestones.
- Merge governance: Do not merge automatically. Human review required.

## Generated
2026-08-16T09:50:04+07:00
