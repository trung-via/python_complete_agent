# RESULT-013

STATUS: READY_FOR_REVIEW

## Summary
TASK-013 FIX: Invoked JS extractor functions properly in Playwright fixture with targetProductId argument, verified nested UGC/recommendation contamination exclusion across scanned product containers, removed stray test_pw.py script, and supplied full verification evidence.

## Task Metadata
- Task: `TASK-013`
- Action: `FIX`
- Authorized Artifact: `.ai/reviews/REVIEW-013.md (20ca158259)`
- Base Main SHA: `(n/a)`
- Branch: `ai/task-013`

## Files Changed
- test_pw.py
- tests/product_source/test_extractor_dom_fixtures.py
- scratch_publish.py

## Diff Stat
```text
test_pw.py                                         |  10 --
 .../product_source/test_extractor_dom_fixtures.py  | 136 ++++++++++++---------
 2 files changed, 81 insertions(+), 65 deletions(-)
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
collecting ... collected 48 items

tests/product_source/test_extractor_dom_fixtures.py::test_shopee_dom_selection_and_ugc_exclusion PASSED [  2%]
tests/product_source/test_extractor_dom_fixtures.py::test_tiktok_dom_selection_and_ugc_exclusion PASSED [  4%]
tests/product_source/test_models.py::test_build_source_pack_id_with_product_id PASSED [  6%]
tests/product_source/test_models.py::test_build_source_pack_id_fallback_url PASSED [  8%]
tests/product_source/test_models.py::test_build_source_pack_id_determinism PASSED [ 10%]
tests/product_source/test_models.py::test_build_source_pack_id_ignores_tracking_and_auth_noise PASSED [ 12%]
tests/product_source/test_models.py::test_sanitize_url_redacts_sensitive_parameters PASSED [ 14%]
tests/product_source/test_models.py::test_product_fact_validation PASSED [ 16%]
tests/product_source/test_models.py::test_product_fact_frozen PASSED     [ 18%]
tests/product_source/test_models.py::test_original_media_ref_validation PASSED [ 20%]
tests/product_source/test_models.py::test_product_source_pack_validation PASSED [ 22%]
tests/product_source/test_models.py::test_description_text_bounded PASSED [ 25%]
tests/product_source/test_models.py::test_facts_media_auto_converted_to_tuples PASSED [ 27%]
tests/product_source/test_models.py::test_product_source_pack_to_dict_secret_safe PASSED [ 29%]
tests/product_source/test_models.py::test_enums_values PASSED            [ 31%]
tests/product_source/test_models.py::test_error_hierarchy PASSED         [ 33%]
tests/product_source/test_original_media_downloader.py::test_preserves_exact_original_bytes PASSED [ 35%]
tests/product_source/test_original_media_downloader.py::test_streaming_oversize_media_aborts_early PASSED [ 37%]
tests/product_source/test_original_media_downloader.py::test_diagnostics_do_not_leak_sensitive_url_tokens PASSED [ 39%]
tests/product_source/test_original_media_downloader.py::test_byte_duplicate_collapse_leaves_no_orphan_files PASSED [ 41%]
tests/product_source/test_original_media_downloader.py::test_canonical_url_dedupe_before_download PASSED [ 43%]
tests/product_source/test_original_media_downloader.py::test_max_media_per_product_enforced PASSED [ 45%]
tests/product_source/test_scrape_tool_compat.py::test_shopee_scrape_tool_schema PASSED [ 47%]
tests/product_source/test_scrape_tool_compat.py::test_tiktok_scrape_tool_schema PASSED [ 50%]
tests/product_source/test_scrape_tool_compat.py::test_shopee_scrape_tool_passes_run_id_to_browser_manager PASSED [ 52%]
tests/product_source/test_scrape_tool_compat.py::test_tiktok_scrape_tool_passes_run_id_to_browser_manager PASSED [ 54%]
tests/product_source/test_scrape_tool_compat.py::test_tools_do_not_call_image_processor PASSED [ 56%]
tests/product_source/test_scrape_tool_compat.py::test_tools_do_not_invoke_llm PASSED [ 58%]
tests/product_source/test_scrape_tool_compat.py::test_partial_upload_returns_partial_success PASSED [ 60%]
tests/product_source/test_scrape_tool_compat.py::test_full_upload_failure_returns_failure PASSED [ 62%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_prefers_structured_data_when_identity_matches PASSED [ 64%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_rejects_unrelated_structured_data_on_identity_mismatch PASSED [ 66%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_fails_closed_when_no_media_found PASSED [ 68%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_collects_explicit_variants PASSED [ 70%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_gallery_fallback_when_no_structured_images PASSED [ 72%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_seller_description_media_labeled PASSED [ 75%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_raises_blocked_on_captcha PASSED [ 77%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_with_strict_browser_manager PASSED [ 79%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_extractor_rejects_overlapping_substring_id PASSED [ 81%]
tests/product_source/test_shopee_source_extractor.py::test_shopee_js_script_excludes_reviews_by_container_provenance PASSED [ 83%]
tests/product_source/test_tiktok_source_extractor.py::test_tiktok_extractor_prefers_structured_data_when_identity_matches PASSED [ 85%]
tests/product_source/test_tiktok_source_extractor.py::test_tiktok_extractor_rejects_unrelated_structured_data_on_identity_mismatch PASSED [ 87%]
tests/product_source/test_tiktok_source_extractor.py::test_tiktok_extractor_fails_closed_when_no_media_found PASSED [ 89%]
tests/product_source/test_tiktok_source_extractor.py::test_tiktok_extractor_collects_explicit_variants PASSED [ 91%]
tests/product_source/test_tiktok_source_extractor.py::test_tiktok_extractor_gallery_fallback PASSED [ 93%]
tests/product_source/test_tiktok_source_extractor.py::test_tiktok_extractor_with_strict_browser_manager PASSED [ 95%]
tests/product_source/test_tiktok_source_extractor.py::test_tiktok_extractor_rejects_overlapping_substring_id PASSED [ 97%]
tests/product_source/test_tiktok_source_extractor.py::test_tiktok_js_script_excludes_reviews_and_no_main_article_fallback PASSED [100%]

============================== warnings summary ===============================
tests/product_source/test_extractor_dom_fixtures.py::test_shopee_dom_selection_and_ugc_exclusion
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:1153: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    return asyncio.get_event_loop_policy()

tests/product_source/test_extractor_dom_fixtures.py: 2 warnings
tests/product_source/test_original_media_downloader.py: 6 warnings
tests/product_source/test_scrape_tool_compat.py: 4 warnings
tests/product_source/test_shopee_source_extractor.py: 10 warnings
tests/product_source/test_tiktok_source_extractor.py: 8 warnings
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:844: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    _restore_event_loop_policy(asyncio.get_event_loop_policy()),

tests/product_source/test_extractor_dom_fixtures.py: 2 warnings
tests/product_source/test_original_media_downloader.py: 6 warnings
tests/product_source/test_scrape_tool_compat.py: 4 warnings
tests/product_source/test_shopee_source_extractor.py: 10 warnings
tests/product_source/test_tiktok_source_extractor.py: 8 warnings
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:1125: DeprecationWarning: 'asyncio.set_event_loop_policy' is deprecated and slated for removal in Python 3.16
    asyncio.set_event_loop_policy(new_loop_policy)

tests/product_source/test_extractor_dom_fixtures.py: 2 warnings
tests/product_source/test_original_media_downloader.py: 6 warnings
tests/product_source/test_scrape_tool_compat.py: 4 warnings
tests/product_source/test_shopee_source_extractor.py: 10 warnings
tests/product_source/test_tiktok_source_extractor.py: 8 warnings
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:1126: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    loop = asyncio.get_event_loop_policy().new_event_loop()

tests/product_source/test_extractor_dom_fixtures.py: 2 warnings
tests/product_source/test_original_media_downloader.py: 6 warnings
tests/product_source/test_scrape_tool_compat.py: 4 warnings
tests/product_source/test_shopee_source_extractor.py: 10 warnings
tests/product_source/test_tiktok_source_extractor.py: 8 warnings
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:859: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    policy = asyncio.get_event_loop_policy()

tests/product_source/test_extractor_dom_fixtures.py: 2 warnings
tests/product_source/test_original_media_downloader.py: 6 warnings
tests/product_source/test_scrape_tool_compat.py: 4 warnings
tests/product_source/test_shopee_source_extractor.py: 10 warnings
tests/product_source/test_tiktok_source_extractor.py: 8 warnings
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:904: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    policy = asyncio.get_event_loop_policy()

tests/product_source/test_extractor_dom_fixtures.py: 2 warnings
tests/product_source/test_original_media_downloader.py: 6 warnings
tests/product_source/test_scrape_tool_compat.py: 4 warnings
tests/product_source/test_shopee_source_extractor.py: 10 warnings
tests/product_source/test_tiktok_source_extractor.py: 8 warnings
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:928: DeprecationWarning: 'asyncio.set_event_loop_policy' is deprecated and slated for removal in Python 3.16
    asyncio.set_event_loop_policy(previous_policy)

tests/product_source/test_extractor_dom_fixtures.py: 2 warnings
tests/product_source/test_original_media_downloader.py: 6 warnings
tests/product_source/test_scrape_tool_compat.py: 4 warnings
tests/product_source/test_shopee_source_extractor.py: 10 warnings
tests/product_source/test_tiktok_source_extractor.py: 8 warnings
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:940: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    policy = asyncio.get_event_loop_policy()

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
====================== 48 passed, 211 warnings in 2.96s =======================
........................................................................ [ 15%]
........................................................................ [ 30%]
........................................................................ [ 46%]
........................................................................ [ 61%]
........................................................................ [ 77%]
........................................................................ [ 92%]
..................................                                       [100%]
466 passed in 48.34s

C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:207: PytestDeprecationWarning: The configuration option "asyncio_default_fixture_loop_scope" is unset.
The event loop scope for asynchronous fixtures will default to the fixture caching scope. Future versions of pytest-asyncio will default the loop scope for asynchronous fixtures to function scope. Set the default fixture loop scope explicitly in order to avoid unexpected behavior in the future. Valid fixture loop scopes are: "function", "class", "module", "package", "session"

  warnings.warn(PytestDeprecationWarning(_DEFAULT_FIXTURE_LOOP_SCOPE_UNSET))
C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:207: PytestDeprecationWarning: The configuration option "asyncio_default_fixture_loop_scope" is unset.
The event loop scope for asynchronous fixtures will default to the fixture caching scope. Future versions of pytest-asyncio will default the loop scope for asynchronous fixtures to function scope. Set the default fixture loop scope explicitly in order to avoid unexpected behavior in the future. Valid fixture loop scopes are: "function", "class", "module", "package", "session"

  warnings.warn(PytestDeprecationWarning(_DEFAULT_FIXTURE_LOOP_SCOPE_UNSET))
```

## Risks / Notes
1. DOM Fixture Invocation Fix:
- Extractor scripts are arrow functions (targetProductId) => { ... } evaluated directly through page.evaluate(_SHOPEE_EXTRACTION_SCRIPT, "123") and page.evaluate(_TIKTOK_EXTRACTOR_JS, "123").

2. Nested UGC/Review Contamination Exclusion Verification:
- Playwright DOM fixtures in tests/product_source/test_extractor_dom_fixtures.py now explicitly nest review, comment, rating, and recommendation subtrees directly INSIDE scanned product containers (.product-briefing, .product-image-carousel, .product-detail for Shopee; .pdp-container, .product-image, .seller-description for TikTok) sharing identical CDN hosts.
- Assertions prove that valid seller/gallery images are accepted, while all nested UGC and recommendation subtrees are rejected specifically by container/subtree ownership exclusion.

3. Stray Script Cleanup:
- Removed stray test_pw.py debug script from repository.

4. Durable Verification Evidence:
- Focused suite (tests/product_source/): 48 passed, 0 failed.
- Full repository suite (tests/): 466 passed, 0 failed.

5. Architectural Invariants Preserved:
- Exact identity matching (no substring overlap).
- Structured product fields strictly gated behind identity.
- Model/SKU captured when present.
- Pattern-based URL sensitive parameter redaction.
- Fail-closed on zero accepted seller media.
- Known limitations: M2.2A establishes canonical Product Source Packs; M2.3 cross-platform scoring/ranking and M2.4 queue handoff remain scheduled for future milestones.
- Merge governance: Do not merge automatically. Human review required.

## Generated
2026-08-16T08:32:56+07:00
