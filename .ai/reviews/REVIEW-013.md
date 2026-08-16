# REVIEW-013 — TASK-013 (Phase 6 M2.2A Product Source Pack & Original Media Extraction V1)

## Status
CHANGES_REQUIRED

## Reviewed Head
- Branch: `ai/task-013`
- Reviewed commit: `079061f1800ed6f7f20a48d921bca9a32a09f958`
- Main baseline: `9d3dcfeab5ffc98bf6aeb3ef7a67912a5bc1fd52`
- Branch relation to main: ahead 1, behind 0 (fast-forward safe)
- Task artifact blob: `c0144bc2e7ffc21422a491ca621a0fe7ceceecde`
- RESULT-013 blob: `822377c0eaa76fe6052f288b95fe4603670f8e76`
- RESULT action: `RUN`
- Exact RUN authorization recorded by worker: `.ai/tasks/TASK-013.md (c0144bc2e7)` — matches the task artifact.

## Review Summary
The implementation moves in the right direction: it introduces a platform-independent source-pack model, dedicated Shopee/TikTok source extractors, byte-preserving media download code, deterministic manifest serialization, and refactors both legacy scrape tools away from `ImageProcessor.process_and_save()`.

However, TASK-013 is not yet ready for merge. Several acceptance-critical issues remain in the real browser integration, source-ownership guarantees, fallback scope, secret-safe serialization, media-byte bounding, variant handling, and durable verification evidence.

## Blocking Finding 1 — Real BrowserManager integration is broken for both platform extractors

### Locations
- `src/product_source/platforms/shopee.py`
- `src/product_source/platforms/tiktok.py`
- `tests/product_source/test_shopee_source_extractor.py`
- `tests/product_source/test_tiktok_source_extractor.py`
- `tests/product_source/test_scrape_tool_compat.py`

Both extractors call `await browser.get_or_create_session()` with no `run_id`.

The project's actual `PlaywrightBrowserManager.get_or_create_session` requires `run_id: str` as a positional argument. Therefore the new deep-ingestion path will fail against the real manager before navigation/extraction.

The current fakes hide this defect because their `get_or_create_session` accepts only `**kwargs` and therefore does not enforce the actual contract.

### Required Fix
Use an explicit deterministic run/session identifier or pass the tool/run identity through the extractor boundary. Preserve the existing BrowserManager contract; do not weaken it.

Add regressions whose fake manager has the same required signature as the real manager, e.g. `get_or_create_session(run_id: str, config=None)`, and prove both Shopee and TikTok extraction paths work through it.

## Blocking Finding 2 — Structured data is not tied to the current product identity

### Locations
- `src/product_source/platforms/shopee.py`
- `src/product_source/platforms/tiktok.py`

TASK-013 explicitly requires structured current-product identity checks so recommendation/review/unrelated payloads cannot become canonical product evidence.

Shopee currently accepts any JSON-LD object with `@type == "Product"` and copies its title/images/brand/description without verifying that it belongs to the requested Shopee product ID/URL.

TikTok is broader: after loading `SIGI_STATE` / `__NEXT_DATA__`, the recursive `findValues(...)` helper searches the whole nested state and takes the first matching `title`, `images`, `description`, `brand`, `sellerInfo`, or `specifications`. That can select an unrelated recommendation/card/entity from a global page state.

### Required Fix
Require an authoritative current-product identity match before accepting structured facts/media. Suitable evidence can be a product/item ID, canonical URL, or a product-scoped object whose identity can be matched to the requested URL. If identity cannot be established, do not label the result `STRUCTURED_PRODUCT_DATA`; fall back to trusted semantic containers or fail closed.

Add fixtures containing both the current product and unrelated recommendation product data, including same-CDN images, and prove only the requested product is accepted.

## Blocking Finding 3 — TikTok fallback is still a broad page scan

### Location
`src/product_source/platforms/tiktok.py`

The V1 fallback includes:

`[class*="product-detail"], [class*="product-info"], main, article`

and then scans every `img` descendant. `main` / `article` are not a sufficiently tight current-product ownership boundary and can include seller cards, recommendations, reviews whose class names do not contain the current negative-keyword list, navigation assets, or other page content.

This directly conflicts with TASK-013's rule that no whole-page/broad main-container scan may be a success fallback.

### Required Fix
Remove `main` / generic `article` from the accepted fallback success path. Use only positively identified TikTok product-owned containers, bounded and deterministic. If none is confidently detected, return explicit extraction failure/partial diagnostics rather than broadening the scan.

Add a fixture where `main` contains current-product media plus unrelated same-CDN images outside the product container and prove the unrelated images are rejected.

## Blocking Finding 4 — Variant media contract is declared but not implemented

### Locations
- `src/product_source/models.py`
- `src/product_source/platforms/shopee.py`
- `src/product_source/platforms/tiktok.py`

`MediaRole.VARIANT` and `SEMANTIC_VARIANT_MEDIA` exist, but neither platform extractor currently collects explicit variant media or emits `MediaRole.VARIANT` refs.

TASK-013 requires explicit variant images to be separately labeled when present and lists variant coverage in the focused acceptance tests.

### Required Fix
Add a small platform-scoped variant extraction path for clearly product-associated variant controls/media. Do not infer variant labels from arbitrary text. If a platform fixture exposes no explicit variant image, leave it absent; but when explicit variant media exists, preserve its role/provenance and optional variant label.

## Blocking Finding 5 — Manifest/diagnostics can persist raw tokenized URLs

### Locations
- `src/product_source/models.py`
- `src/product_source/downloader.py`
- `src/product_source/serialization.py`

`ProductSourcePack.to_dict()` serializes `product_url` and every media `source_url` verbatim. Downloader diagnostics also embed the full source URL in error strings. There is no redaction/canonicalization layer for sensitive query parameters.

This means signed CDN URLs, auth-like query parameters, session tokens, or other temporary credentials can be written into `source_pack.json` or diagnostics, contrary to the task requirement that manifests/logs contain no tokens/credentials.

The current test only checks a clean example dictionary does not literally contain the words `cookies` or `html`; it does not test a tokenized URL.

### Required Fix
Separate ephemeral fetch URL from persisted safe/canonical URL, or sanitize/redact sensitive query parameters before manifest/diagnostic serialization. Do not strip parameters required only for the in-memory download before the download occurs. Add regressions with representative `token=`, `auth=`, `signature=`, `session=`-like query parameters and prove serialized output/diagnostics do not expose them.

Also canonicalize URL-fingerprint identity so tracking/auth query noise does not create a new source-pack identity for the same product.

## Blocking Finding 6 — 20 MiB limit is checked only after the entire response is buffered

### Location
`src/product_source/downloader.py`

The downloader currently executes `data = await response.read()` and only then checks `len(data) > MAX_FILE_BYTES`.

That eventually rejects an oversized image, but it does not enforce the resource bound during transfer/read; an arbitrarily large body can still be buffered before rejection.

### Required Fix
Honor `Content-Length` when trustworthy and stream the response in bounded chunks with a running byte counter that aborts once `MAX_FILE_BYTES` is exceeded. Preserve exact bytes for accepted media. Add a deterministic streaming/oversize regression so the implementation proves it stops at the bound rather than reading the entire payload first.

Also ensure SHA-256 duplicate collapse does not leave duplicate orphan files in `original/` after the duplicate ref is removed from the manifest.

## Blocking Finding 7 — RESULT-013 does not contain required verification evidence

### Location
`.ai/results/RESULT-013.md`

RESULT-013 reports:
- `Command: (not supplied)`
- `(no test command supplied)`

It therefore provides no focused test command/pass count and no full-suite command/pass count. Its diff stat also covers only the two legacy scrape tools even though main → task changes eighteen files.

The task explicitly requires exact focused/full commands, exit codes, pass counts, accurate concise diff evidence, schema/priority/bounds/dedupe/provenance/browser-compatibility statements, limitations, and no-auto-merge governance.

### Required Fix
After code fixes, run at minimum:

```powershell
.\venv\Scripts\python -m pytest tests/product_source/ -v
.\venv\Scripts\python -m pytest tests/ -q -W ignore
```

Refresh RESULT-013 with exact commands, exit codes, pass counts, an accurate diff summary, and all required behavior/governance evidence. Do not mark `READY_FOR_REVIEW` until those commands are actually green.

## Preserve During Fix
Keep the useful direction already implemented:
- dedicated Product Source Pack contract and source/derived boundary;
- no source-original use of `ImageProcessor.process_and_save()`;
- byte-preserving accepted media writes;
- SHA-256 evidence;
- product facts remain source claims rather than AI-generated facts;
- no LLM/scoring/ranking/queue mutation;
- public tool names/schemas remain backward compatible;
- partial publication semantics remain honest;
- no broad Y-coordinate / “before review” heuristic is reintroduced.

## Decision
CHANGES_REQUIRED.

Do not merge automatically. Publish fixes only through this exact REVIEW-013 artifact, then request `Review TASK-013` again.
