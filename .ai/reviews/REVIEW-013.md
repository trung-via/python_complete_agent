# REVIEW-013 — TASK-013 (Phase 6 M2.2A Product Source Pack & Original Media Extraction V1)

## Status
CHANGES_REQUIRED

## Reviewed Head
- Branch: `ai/task-013`
- Reviewed commit: `5042620ab53c432c7209816b6ac1a4fec817c377`
- Main baseline: `9d3dcfeab5ffc98bf6aeb3ef7a67912a5bc1fd52`
- Branch relation to main: ahead 6, behind 0 (fast-forward safe)
- Task artifact blob: `c0144bc2e7ffc21422a491ca621a0fe7ceceecde`
- Prior CHANGES_REQUIRED authorization blob: `79adc61318d1977d4dacfddb6fd452827ae73a77`
- RESULT-013 blob: `54f1ae0a4a460b7af992e965d1b58b13793740fb`
- RESULT action: `FIX`
- Exact FIX authorization recorded by worker: `.ai/reviews/REVIEW-013.md (79adc61318)` — matches the prior review artifact.

## Re-review Summary
The source-level fixes for the prior identity/SKU/redaction findings are materially improved:

1. Shopee/TikTok JSON-LD identity matching now uses exact ID/SKU equality or an ID parsed from a product/item URL instead of arbitrary substring containment.
2. `model_sku` is now preserved when an identity-matched structured source exposes it.
3. URL redaction now uses pattern-based sensitive-key detection, covering prefixed signature/credential/token/session/policy/key families.
4. The branch remains fast-forward safe against the canonical main baseline.

TASK-013 is still not ready for merge because the new DOM regression does not yet prove the intended extraction behavior, and the durable RESULT verification evidence has regressed.

## Blocking Finding 1 — New DOM fixture does not actually invoke the extraction function

### Location
`tests/product_source/test_extractor_dom_fixtures.py`

Both platform extractor constants are JavaScript arrow functions of the form:

```javascript
(targetProductId) => { ... }
```

The new fixture builds a string like:

```python
script = "const targetProductId = '123';\n" + _SHOPEE_EXTRACTION_SCRIPT
result = await page.evaluate(script)
```

and similarly for TikTok.

That expression defines/evaluates an arrow function but does not call it with the target product ID. Therefore the fixture is not a valid proof that the extraction body ran and returned the expected `gallery` / `seller_images` / fallback structures.

### Required Fix
Invoke the actual extractor function through Playwright, for example by evaluating the existing function source with an argument in the same shape as production (`page.evaluate(_SHOPEE_EXTRACTION_SCRIPT, target_id)` / TikTok equivalent), or wrap-and-call it explicitly.

The regression must run green under the required focused command before review.

## Blocking Finding 2 — The UGC fixture still does not stress the contamination path strongly enough

### Location
`tests/product_source/test_extractor_dom_fixtures.py`

The Shopee review and recommendation nodes are separate siblings outside the positively selected `.product-image-carousel` / `.product-detail` containers. The TikTok review node is likewise outside the selected `.product-image` / `.seller-description` containers.

Those images would be ignored even if the child-level `isExcluded(...)` protection were broken, because the positive container selectors never visit them. This does not directly prove the defect TASK-013 was created to eliminate: review/customer media leaking from inside a broader product/detail container.

### Required Fix
Use same-CDN fixtures where a review/comment/recommendation subtree is nested inside a container that the extraction pass actually scans. Prove that:
- the seller gallery/source image is accepted;
- a review/customer image under the scanned outer product container is rejected specifically by subtree ownership/exclusion;
- a recommendation image under a scanned/bounded product container is rejected;
- TikTok generic outer-page content is not admitted by fallback.

No live marketplace access is needed.

## Blocking Finding 3 — RESULT-013 verification evidence regressed to “not supplied”

### Location
`.ai/results/RESULT-013.md`

The previous reviewed result had exact focused/full commands and green counts. The current RESULT at blob `54f1ae0a4a460b7af992e965d1b58b13793740fb` has replaced that evidence with:

- `Command: (not supplied)`
- `(no test command supplied)`

TASK-013 explicitly requires exact focused and full-suite commands, exit codes, and pass counts. This is a hard review gate, especially because the new Playwright DOM fixture was added in this FIX.

### Required Fix
Run and record at minimum:

```powershell
.\venv\Scripts\python -m pytest tests/product_source/ -v
.\venv\Scripts\python -m pytest tests/ -q -W ignore
```

RESULT-013 must contain the exact commands, exit codes, exact pass counts, current authorization reference, known limitations, and no-auto-merge statement.

## Blocking Finding 4 — Current RESULT diff evidence is incomplete and a stray debug script is in the task diff

### Locations
- `.ai/results/RESULT-013.md`
- `test_pw.py`

Live `main → ai/task-013` comparison currently contains 20 changed files and includes both `tests/product_source/test_extractor_dom_fixtures.py` and a repository-root `test_pw.py` debug script. The current RESULT labels an 8-file FIX diff but lists `test_pw.py` under Files Changed while omitting it from the shown diff stat; it is therefore not an accurate durable description of the reviewed state.

`test_pw.py` is an ad-hoc executable Playwright smoke script (`asyncio.run(main())`) and is not part of the TASK-013 product-source architecture or required test suite.

### Required Fix
Remove the stray debug script unless it is intentionally converted into a proper test under `tests/product_source/`. Then refresh RESULT-013 against the final reviewed head with an accurate task diff (or explicitly labeled FIX-only diff plus a separate current task diff), so the artifact and GitHub state agree.

## Preserve During Fix
Preserve the now-correct direction:
- exact object-owned product identity matching rather than substring matching;
- identity-gated structured fields;
- `model_sku` capture only when explicitly observed;
- pattern-based signed URL redaction;
- explicit `run_id` through BrowserManager/BrowserSession;
- fail-closed zero-media extraction;
- narrow platform-scoped fallback with no generic `main` / `article` success path;
- variant media roles/provenance;
- 20 MiB streaming bound and 30-media cap;
- byte-preserving source originals and SHA-256 evidence;
- no source-original `ImageProcessor.process_and_save()`;
- no AI image generation, LLM, scoring, ranking, or queue mutation;
- backward-compatible `shopee_scrape` / `tiktok_scrape` names and schemas.

## Decision
CHANGES_REQUIRED.

Do not merge automatically. Publish the next FIX only through this exact REVIEW-013 artifact, then request `Review TASK-013` again.
