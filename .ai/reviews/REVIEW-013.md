# REVIEW-013 — TASK-013 (Phase 6 M2.2A Product Source Pack & Original Media Extraction V1)

## Status
CHANGES_REQUIRED

## Reviewed Head
- Branch: `ai/task-013`
- Reviewed commit: `b66dd3cea698a8698ca13429c83c2995c15dad3b`
- Main baseline: `9d3dcfeab5ffc98bf6aeb3ef7a67912a5bc1fd52`
- Branch relation to main: ahead 3, behind 0 (fast-forward safe)
- Task artifact blob: `c0144bc2e7ffc21422a491ca621a0fe7ceceecde`
- Prior CHANGES_REQUIRED authorization blob: `3a3f4aa42352dac74d75f216f926a56eabb083f1`
- RESULT-013 blob: `e66b2cf9fc8ac24fbde98733584c1e88b9117835`
- RESULT action: `FIX`
- Exact FIX authorization recorded by worker: `.ai/reviews/REVIEW-013.md (3a3f4aa423)` — matches the prior review artifact exactly.

## Re-review Summary
Most of the first review's implementation blockers are materially improved:

1. BrowserManager compatibility is fixed: both extractors now acquire sessions with an explicit run ID, the scrape tools pass `call.run_id`, and strict manager-shaped tests were added.
2. TikTok's generic `main` / `article` fallback was removed in favor of narrower product-container selectors.
3. Explicit Shopee/TikTok variant extraction now emits `MediaRole.VARIANT` / `SEMANTIC_VARIANT_MEDIA`.
4. URL fingerprinting now ignores query noise; manifest/diagnostic URLs are sanitized for the tested token/auth/signature/session keys.
5. Original-media downloading now honors `Content-Length`, streams in bounded chunks, and collapses exact SHA-256 duplicates before writing a duplicate file.

Two source-level correctness blockers and one durable RESULT evidence blocker remain.

## Blocking Finding 1 — Structured current-product identity is still not authoritative

### Locations
- `src/product_source/platforms/shopee.py`
- `src/product_source/platforms/tiktok.py`
- `tests/product_source/test_shopee_source_extractor.py`
- `tests/product_source/test_tiktok_source_extractor.py`

Both platform extraction scripts still contain an identity predicate equivalent to:

```javascript
itemUrl.includes(targetProductId) ||
productId.toString().includes(targetProductId) ||
window.location.href.includes(targetProductId)
```

Because the browser is already on the requested product URL, `window.location.href.includes(targetProductId)` is normally true for the target page regardless of which JSON-LD/Product object is currently being inspected. That means an unrelated recommendation `Product` object on the same page can still be accepted and then stamped with `result.structured.product_id = targetProductId`.

TikTok's scoped state candidates have the same bypass: a candidate whose own `productId` does not match can still pass solely because the page URL contains the requested ID.

There is a second layer to the same problem in Python post-processing. The current code gates only structured **media** on `structured.product_id == product_id`; title, brand, description, specs/facts, shop metadata, and other structured values are still consumed from the `structured` object even when its identity is mismatched. The current Shopee mismatch regression only asserts that the unrelated image is excluded, so an unrelated structured title/brand can still contaminate the canonical source pack.

### Required Fix
Make identity evidence belong to the structured object itself, not merely to the browser's current URL.

- For JSON-LD, accept structured facts/media only when the object's own product ID/SKU/URL/canonical identity can be matched to the requested product.
- For embedded TikTok state, require the candidate object's own product/item ID or a product-scoped canonical URL to match.
- Do not set `structured.product_id = targetProductId` unless that identity was actually established from the structured object.
- Gate **all structured-derived fields** — title, brand, shop, description, specs/facts, and media — behind the same verified identity decision.
- If structured identity cannot be established, ignore that structured object and use trusted semantic product containers instead.

Add regressions that exercise the extraction decision itself, not only a pre-baked fake `evaluate_data` dictionary. At minimum prove that an unrelated Product object on a page whose URL contains the target ID is rejected for both media and facts/title/brand.

## Blocking Finding 2 — Trusted extraction exhaustion can still return a successful empty source pack

### Locations
- `src/product_source/platforms/shopee.py`
- `src/product_source/platforms/tiktok.py`
- `src/tools/shopee_scrape_tool.py`
- `src/tools/tiktok_scrape_tool.py`

TASK-013 requires trusted paths exhausted → explicit extraction failure, not a silent successful empty result.

The extractors currently build and return `ProductSourcePack` even when structured, gallery, variant, description, and scoped fallback media are all empty. The scrape tools only fail download when `len(source_pack.media) > 0` but zero items were downloaded. If `source_pack.media` is empty from the start, they can serialize/upload a manifest and return success.

### Required Fix
Fail closed when no trusted seller-product media can be accepted after all bounded extraction tiers are exhausted. A typed `SourcePackExtractionError` is sufficient. If the architecture intentionally allows a facts-only source pack, that must be explicitly defined in the task/result contract and the scrape tool must not report the media-ingestion operation as successful; TASK-013 as authored expects original seller media to be present.

Add Shopee and TikTok regressions for an extraction result with no trusted media, proving it does not become a successful published source pack.

## Blocking Finding 3 — Current RESULT-013 still lacks required verification evidence

### Location
`.ai/results/RESULT-013.md`

The current durable RESULT at blob `e66b2cf9fc8ac24fbde98733584c1e88b9117835` still says:

- `Command: (not supplied)`
- `(no test command supplied)`

It then states `All 42 focused tests and 460 full-suite tests passing`, but without the exact commands/output this is not acceptable evidence under TASK-013. The task requires the exact focused and full commands, exit codes, and pass counts. The current RESULT also removed the detailed schema/priority/bounds/dedupe/provenance/browser-compatibility/governance evidence that had appeared in an intermediate result revision.

### Required Fix
After the code fixes, run and durably record at minimum:

```powershell
.\venv\Scripts\python -m pytest tests/product_source/ -v
.\venv\Scripts\python -m pytest tests/ -q -W ignore
```

RESULT-013 must include the exact commands, exit codes, exact pass counts, accurate task/FIX diff summary, source-pack schema/version, trusted extraction priority, review/UGC exclusion semantics, 30-media/20-MiB bounds, byte-preserving semantics, URL/SHA-256 dedupe, ProductFact provenance/missing-value policy, BrowserManager compatibility, known limitations, explicit non-goals, and no-auto-merge statement.

Do not replace exact verification evidence with a prose claim that tests passed.

## Preserve During Fix
Preserve the now-correct improvements: explicit run IDs through BrowserManager, narrow TikTok fallback, variant media roles, secret-safe serialization for tested sensitive query keys, canonical URL identity without query noise, streaming byte bounds, exact SHA-256 dedupe before duplicate file persistence, byte-preserving source originals, no `ImageProcessor.process_and_save()` for source originals, no LLM/scoring/ranking/queue mutation, and backward-compatible scrape tool names/schemas.

## Decision
CHANGES_REQUIRED.

Do not merge automatically. Publish the next FIX only through this exact REVIEW-013 artifact, then request `Review TASK-013` again.
