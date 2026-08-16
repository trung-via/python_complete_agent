# REVIEW-013 — TASK-013 (Phase 6 M2.2A Product Source Pack & Original Media Extraction V1)

## Status
CHANGES_REQUIRED

## Reviewed Head
- Branch: `ai/task-013`
- Reviewed commit: `d2e827eef3c5b4450c50055c667cec9f82e97976`
- Main baseline: `9d3dcfeab5ffc98bf6aeb3ef7a67912a5bc1fd52`
- Branch relation to main: ahead 7, behind 0 (fast-forward safe)
- Task artifact blob: `c0144bc2e7ffc21422a491ca621a0fe7ceceecde`
- Prior CHANGES_REQUIRED authorization blob: `20ca15825978fa3efd636691621147c9b17d395b`
- RESULT-013 current head contains `Action: FIX` and records authorization `.ai/reviews/REVIEW-013.md (20ca158259)`, matching the prior review artifact.
- Focused Product Source suite reported: 48 passed, exit code 0.
- Full repository suite reported: 466 passed, exit code 0.

## Re-review Summary
The substantive source-extraction blockers from the previous review are now closed:

1. The Playwright DOM fixtures invoke the real extractor arrow functions with a target product ID.
2. Review/comment/recommendation nodes are nested inside containers the extraction pass actually scans, using the same CDN host as accepted seller media, and are excluded in both Shopee and TikTok fixtures.
3. Exact identity matching, identity-gated structured fields, explicit model/SKU capture, pattern-based signed-URL redaction, run-id plumbing, zero-media fail-closed behavior, bounded fallback, byte-preserving downloads, streaming limits, and SHA-256 dedupe remain intact.
4. Required focused and full repository test commands are now durably recorded and green.

TASK-013 is very close, but the reviewed branch still contains one stray publication helper and the durable RESULT diff description does not match the actual task state.

## Blocking Finding 1 — `scratch_publish.py` is a stray repository-root publication helper

### Location
`scratch_publish.py`

The branch removed the prior `test_pw.py` debug script, but introduced a new repository-root `scratch_publish.py` helper. It shells out to `bridge.py publish 13` with hard-coded TASK-013 summary/test text and then exits.

This file is not part of the Product Source Pack architecture, runtime, test suite, or documented TASK-013 deliverable. It is another ad-hoc task-publication helper and should not be merged into `main`.

### Required Fix
Remove `scratch_publish.py` from the task branch. Do not replace it with another task-specific root helper. The bridge workflow should publish RESULT artifacts without adding temporary publication scripts to product code history.

## Blocking Finding 2 — RESULT-013 diff evidence is not accurate for the reviewed head

### Location
`.ai/results/RESULT-013.md`

The current RESULT lists `scratch_publish.py` under `Files Changed`, but its shown diff stat contains only `test_pw.py` and `tests/product_source/test_extractor_dom_fixtures.py`.

Live `main → ai/task-013` comparison at reviewed head contains 20 changed files and includes `scratch_publish.py`; therefore the durable diff description is not an accurate representation of the reviewed state.

The verification commands and counts are now good and should be preserved.

### Required Fix
After removing `scratch_publish.py`, refresh RESULT-013 once against the final head so it contains:
- exact FIX authorization reference;
- exact focused/full commands, exit codes, and pass counts;
- an accurate current task diff summary, or clearly labeled FIX-only diff plus a separate current task diff;
- the existing known-limitations and no-auto-merge statement.

Do not regress the currently recorded test evidence.

## Preserve During Fix
Preserve all now-correct implementation behavior, especially the real nested same-CDN UGC exclusion fixtures, exact product identity matching, structured-field gating, model/SKU capture, secret-safe URL serialization, BrowserManager compatibility, zero-media fail-closed semantics, narrow platform fallback, variant provenance, byte-preserving originals, streaming bounds, SHA-256 evidence, and the no-LLM/no-scoring/no-ranking/no-queue boundary.

## Decision
CHANGES_REQUIRED.

Do not merge automatically. Publish the next FIX only through this exact REVIEW-013 artifact, then request `Review TASK-013` again.
