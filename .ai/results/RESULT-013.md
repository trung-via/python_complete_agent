# RESULT-013

STATUS: READY_FOR_REVIEW

## Summary
TASK-013 FIX (Round 2): Authoritative structured product identity matching, fail-closed media extraction, strict BrowserManager contract, and durable test evidence

## Task Metadata
- Task: `TASK-013`
- Action: `FIX`
- Authorized Artifact: `.ai/reviews/REVIEW-013.md (527d3d5a0b)`
- Base Main SHA: `(n/a)`
- Branch: `ai/task-013`

## Files Changed
- src/product_source/platforms/shopee.py
- src/product_source/platforms/tiktok.py
- tests/product_source/test_scrape_tool_compat.py
- tests/product_source/test_shopee_source_extractor.py
- tests/product_source/test_tiktok_source_extractor.py

## Diff Stat
```text
src/product_source/platforms/shopee.py             | 37 ++++++++-----
 src/product_source/platforms/tiktok.py             | 60 ++++++++++++----------
 tests/product_source/test_scrape_tool_compat.py    |  5 +-
 .../product_source/test_shopee_source_extractor.py | 33 ++++++++++--
 .../product_source/test_tiktok_source_extractor.py | 38 ++++++++++++--
 5 files changed, 123 insertions(+), 50 deletions(-)
```

## Tests
Command: `.\venv\Scripts\python -m pytest tests/product_source/ -v`  
Exit code: 0

```text
============================= test session starts =============================
platform win32 -- Python 3.14.7, pytest-8.3.4, pluggy-1.6.0 -- C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent
plugins: anyio-4.14.2, asyncio-0.25.0
asyncio: mode=Mode.STRICT, asyncio_default_fixture_loop_scope=None
collecting ... collected 44 items

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

============================== warnings summary ===============================
tests/product_source/test_models.py::test_build_source_pack_id_with_product_id
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:1153: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    return asyncio.get_event_loop_policy()

tests/product_source/test_original_media_downloader.py: 6 warnings
tests/product_source/test_scrape_tool_compat.py: 4 warnings
tests/product_source/test_shopee_source_extractor.py: 9 warnings
tests/product_source/test_tiktok_source_extractor.py: 7 warnings
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:844: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    _restore_event_loop_policy(asyncio.get_event_loop_policy()),

tests/product_source/test_original_media_downloader.py: 6 warnings
tests/product_source/test_scrape_tool_compat.py: 4 warnings
tests/product_source/test_shopee_source_extractor.py: 9 warnings
tests/product_source/test_tiktok_source_extractor.py: 7 warnings
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:1125: DeprecationWarning: 'asyncio.set_event_loop_policy' is deprecated and slated for removal in Python 3.16
    asyncio.set_event_loop_policy(new_loop_policy)

tests/product_source/test_original_media_downloader.py: 6 warnings
tests/product_source/test_scrape_tool_compat.py: 4 warnings
tests/product_source/test_shopee_source_extractor.py: 9 warnings
tests/product_source/test_tiktok_source_extractor.py: 7 warnings
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:1126: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    loop = asyncio.get_event_loop_policy().new_event_loop()

tests/product_source/test_original_media_downloader.py: 6 warnings
tests/product_source/test_scrape_tool_compat.py: 4 warnings
tests/product_source/test_shopee_source_extractor.py: 9 warnings
tests/product_source/test_tiktok_source_extractor.py: 7 warnings
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:859: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    policy = asyncio.get_event_loop_policy()

tests/product_source/test_original_media_downloader.py: 6 warnings
tests/product_source/test_scrape_tool_compat.py: 4 warnings
tests/product_source/test_shopee_source_extractor.py: 9 warnings
tests/product_source/test_tiktok_source_extractor.py: 7 warnings
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:904: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    policy = asyncio.get_event_loop_policy()

tests/product_source/test_original_media_downloader.py: 6 warnings
tests/product_source/test_scrape_tool_compat.py: 4 warnings
tests/product_source/test_shopee_source_extractor.py: 9 warnings
tests/product_source/test_tiktok_source_extractor.py: 7 warnings
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:928: DeprecationWarning: 'asyncio.set_event_loop_policy' is deprecated and slated for removal in Python 3.16
    asyncio.set_event_loop_policy(previous_policy)

tests/product_source/test_original_media_downloader.py: 6 warnings
tests/product_source/test_scrape_tool_compat.py: 4 warnings
tests/product_source/test_shopee_source_extractor.py: 9 warnings
tests/product_source/test_tiktok_source_extractor.py: 7 warnings
  C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:940: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    policy = asyncio.get_event_loop_policy()

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
====================== 44 passed, 183 warnings in 0.34s =======================

C:\Users\TRUNG\.gemini\antigravity\scratch\python_complete_agent\venv\Lib\site-packages\pytest_asyncio\plugin.py:207: PytestDeprecationWarning: The configuration option "asyncio_default_fixture_loop_scope" is unset.
The event loop scope for asynchronous fixtures will default to the fixture caching scope. Future versions of pytest-asyncio will default the loop scope for asynchronous fixtures to function scope. Set the default fixture loop scope explicitly in order to avoid unexpected behavior in the future. Valid fixture loop scopes are: "function", "class", "module", "package", "session"

  warnings.warn(PytestDeprecationWarning(_DEFAULT_FIXTURE_LOOP_SCOPE_UNSET))
```

## Risks / Notes
Resolved all review findings across structured data identity, fail-closed exhaustion, and verification reporting.

## Generated
2026-08-16T08:05:30+07:00
