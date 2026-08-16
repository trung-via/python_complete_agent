# REVIEW-013 — TASK-013 (Phase 6 M2.2A Product Source Pack & Original Media Extraction V1)

## Status
CHANGES_REQUIRED

## Reviewed Head
- Branch: `ai/task-013`
- Reviewed commit: `15c98145098531ff181d2c156d20bcc9c339579c`
- Main baseline: `9d3dcfeab5ffc98bf6aeb3ef7a67912a5bc1fd52`
- Branch relation to main: ahead 5, behind 0 (fast-forward safe)
- Task artifact blob: `c0144bc2e7ffc21422a491ca621a0fe7ceceecde`
- Prior CHANGES_REQUIRED authorization blob: `527d3d5a0bb101739ee13f366088a16ed871707f`
- RESULT-013 blob: `f8f2f29bdfcfc13c281f6b9f7e54df993bec3a7c`
- RESULT action: `FIX`
- Exact FIX authorization recorded by worker: `.ai/reviews/REVIEW-013.md (527d3d5a0b)` — matches the prior review artifact exactly.
- Reported focused Product Source suite: 44 passed, 0 failed, exit code 0.
- Reported full repository suite: 462 passed, 0 failed, exit code 0.

## Re-review Summary
The previous three blockers are materially improved: the page-URL identity bypass was removed, zero-media extraction now fails closed, and RESULT-013 now records exact focused/full test commands with green counts. BrowserManager run-id plumbing, variant roles, bounded streaming, byte-preserving writes, narrow TikTok fallback, and no-LLM/no-scoring/no-queue boundaries remain intact.

TASK-013 is still not ready for merge because the remaining issues affect the exact problem this milestone is meant to solve: authoritative product identity, proof that review/UGC images are excluded by container ownership, secret-safe signed media URLs, explicit seller SKU/model capture, and durable result accuracy.

## Blocking Finding 1 — Structured identity matching still uses substring matching instead of exact product identity

### Locations
- `src/product_source/platforms/shopee.py`
- `src/product_source/platforms/tiktok.py`

The page-URL bypass is gone, which is good, but JSON-LD identity still uses predicates equivalent to:

```javascript
itemUrl.includes(targetProductId) ||
productId.toString().includes(targetProductId) ||
sku.toString().includes(targetProductId)
```

This can false-match another product whose ID/SKU merely contains the requested ID as a substring (for example target `12345` vs unrelated `9123450`) or a URL where the digits occur in a non-identity component.

For a canonical evidence layer, identity must be exact after normalization/parsing, not substring-based.

### Required Fix
- Compare normalized product/item/SKU IDs by exact equality when the structured object exposes an ID.
- When using an object URL, parse the platform product/item identity from that URL and compare exact IDs; do not accept arbitrary string containment.
- Add regressions for overlapping IDs proving an unrelated object such as `9123450` is rejected when target is `12345`.

## Blocking Finding 2 — The core review/UGC exclusion behavior is still not proven by deterministic fixtures

### Locations
- `tests/product_source/test_shopee_source_extractor.py`
- `tests/product_source/test_tiktok_source_extractor.py`
- platform extraction JS in both source extractors

TASK-013 explicitly requires fixtures where seller gallery media and review/customer media use the same CDN, proving container/provenance rules — not hostname — determine acceptance.

Current extractor tests inject pre-built `evaluate_data` dictionaries. Those fakes already contain only the accepted output, so they do not execute the DOM selection/exclusion decision. The review tests only inspect that strings such as `review`, `rating`, `comment`, or `recommend` appear in the JS source.

That does not prove the real regression reported by the user — review images leaking into product originals — is fixed.

### Required Fix
Add deterministic extraction fixtures that exercise the selector/ownership decision itself. Acceptable approaches include a small DOM/HTML fixture runner or extracting the DOM-selection logic into a directly testable deterministic parser. At minimum prove for both platforms that:
- a gallery image and a review/customer image can share the same CDN host;
- the gallery image is accepted;
- the review/customer image is rejected because of container ownership;
- unrelated recommendation/product-card images are rejected;
- TikTok generic outer-page content cannot become fallback media.

No live marketplace test is required.

## Blocking Finding 3 — Secret-safe URL redaction is too narrow for real signed CDN query keys

### Location
`src/product_source/models.py`

`sanitize_url()` redacts only an exact allow-list of sensitive key names such as `token`, `auth`, `signature`, `session`, `credential`, and `expires`.

Common signed media URLs can use prefixed or variant names such as `X-Amz-Signature`, `X-Amz-Credential`, `X-Goog-Signature`, `_signature`, `Key-Pair-Id`, or policy/key-token variants. Those values are not covered by exact-key equality and can therefore be serialized into `source_pack.json` or downloader diagnostics.

TASK-013 explicitly requires that signed CDN/auth-like credentials not be persisted.

### Required Fix
Use normalized/pattern-based sensitive-key detection for auth/signature/token/session/credential/policy/key-pair/expiry families while preserving non-sensitive fetch parameters in memory. Add regression cases for prefixed signature/credential keys and prove their values never appear in serialized manifests or diagnostics.

## Blocking Finding 4 — Explicit model/SKU evidence is still discarded

### Locations
- `src/product_source/platforms/shopee.py`
- `src/product_source/platforms/tiktok.py`
- `ProductSourcePack.model_sku`

The task requires model/SKU to be populated when explicitly observed. The extractors already inspect structured `sku`/product identity fields for matching, but neither platform currently assigns an observed seller SKU/model to `ProductSourcePack.model_sku` or an equivalent source fact.

### Required Fix
When a trusted, identity-matched structured/spec source explicitly provides model/SKU, preserve it with provenance and populate `model_sku` (or an equivalent canonical fact consistent with the task contract). Missing values must remain `None`; do not infer them from title or images.

Add focused tests for observed SKU/model and missing SKU/model.

## Blocking Finding 5 — RESULT-013 diff evidence is stale relative to the reviewed head

### Location
`.ai/results/RESULT-013.md`

The test evidence is now present and green, but the recorded diff stat is not the current `main → ai/task-013` diff. Live comparison at reviewed head shows 18 changed files, including `.ai/results/RESULT-013.md`, and current line counts differ from the 17-file diff recorded in RESULT-013.

The task requires an accurate concise diff summary tied to the reviewed state.

### Required Fix
Refresh RESULT-013 after the final code/test changes with the exact current task diff (or an explicitly labeled code-only diff plus the RESULT artifact itself), while preserving the exact focused/full commands, exit codes, pass counts, authorization reference, limitations, and no-auto-merge statement.

## Preserve During Fix
Preserve the now-correct improvements:
- explicit `run_id` through the real BrowserManager/BrowserSession contract;
- fail-closed zero-media extraction;
- structured fields gated after identity verification;
- narrow platform-scoped fallback with no `main`/generic `article` success path;
- explicit variant media roles/provenance;
- 20 MiB streaming bound and 30-media cap;
- byte-preserving source originals and SHA-256 evidence;
- duplicate collapse before duplicate file persistence;
- source/derived asset boundary;
- no `ImageProcessor.process_and_save()` for source originals;
- no AI image generation, LLM, scoring, ranking, or queue mutation;
- backward-compatible `shopee_scrape` / `tiktok_scrape` names and schemas.

## Decision
CHANGES_REQUIRED.

Do not merge automatically. Publish the next FIX only through this exact REVIEW-013 artifact, then request `Review TASK-013` again.
