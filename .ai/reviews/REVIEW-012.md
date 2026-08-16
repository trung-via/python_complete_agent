# REVIEW-012 — TASK-012 (Phase 6 M2.2 Shopee Discovery Adapter V1)

## Status
CHANGES_REQUIRED

## Reviewed Head
- Branch: `ai/task-012`
- Reviewed commit: `5f2de78c995f8b3e9f9e85add130c18a4a228eaa`
- Main baseline: `68db4d45154994c929bae22e660f1aca236e2bcd`
- Branch relation to main: ahead 1, behind 0 (fast-forward safe)
- Task artifact blob: `86af9ebbcc5aea780146c16625d2820fcc3c1b22`
- RESULT-012 blob: `fd99285b20344b8d42d5175a2bd08f6e6c283a7a`
- RESULT action: `RUN`
- Exact RUN authorization recorded by worker: `.ai/tasks/TASK-012.md (86af9ebbcc)` — matches the task artifact.
- Reported focused Product Intelligence suite: 43 passed, 0 failed, exit code 0.
- Reported full repository suite: 416 passed, 0 failed, exit code 0.

## Review Summary
The implementation is directionally aligned with M2.2: it adds a platform-independent discovery contract, keeps Shopee-specific extraction isolated in an adapter, enforces bounded pages/candidates, uses deterministic candidate IDs and first-seen dedupe, keeps deep-ingestion/GDrive/LLM/scoring/queue concerns out of discovery, and includes deterministic parsing helpers plus injected-browser tests.

Two source-level correctness blockers remain before real marketplace data may feed M2.1/M2.3. There is also one durable RESULT evidence issue.

## Blocking Finding 1 — `review_count` is fabricated from `rating_text`

### Location
- `src/product_intelligence/adapters/shopee.py` — card extraction and `_map_card_to_snapshot`
- `src/product_intelligence/adapters/shopee_parsing.py` — `parse_shopee_review_count`
- `tests/product_intelligence/test_shopee_discovery.py`

The extraction script currently emits `rating_text` but does not emit a distinct review-count field. `_map_card_to_snapshot` then does both:

- `rating = parse_shopee_rating(card_dict.get("rating_text"))`
- `review_count = parse_shopee_review_count(card_dict.get("rating_text"))`

This violates TASK-012's evidence/missing-value boundary. A rating-only string such as `"4.85"` is not review-count evidence. Worse, the current review-count parser treats the plain decimal text as digits after removing separators, so `"4.85"` can become `485` reviews and `"4.9"` can become `49` reviews. The successful discovery fixture uses exactly these rating strings but does not assert that `review_count` stays `None`, so the fabrication is currently untested.

### Required Fix
Keep rating and review-count extraction independent.

- Add a distinct `review_count_text` field only when the listing/search card genuinely exposes review count, or leave it absent/`None` when unavailable.
- Map `review_count` only from that dedicated field.
- A rating-only value must never be reused as review-count evidence.
- Add regressions proving a card with `rating_text="4.85"` and no review-count text yields `rating == 4.85` and `review_count is None`.
- Add a positive fixture only if the listing fixture explicitly contains review-count evidence.

Do not infer review count from stars/rating or from unrelated text.

## Blocking Finding 2 — Unknown extraction failure is silently classified as `TRUE_EMPTY_SEARCH`

### Location
`src/product_intelligence/adapters/shopee.py` — first-page empty-card handling.

After evaluation, the adapter already receives an explicit `is_empty` signal from the extraction script. However, it then contains a second fallback:

```python
if not raw_cards and page_idx == 1:
    diagnostic_codes.append("TRUE_EMPTY_SEARCH")
    break
```

That means a Shopee DOM/layout change, selector miss, incomplete hydration, or otherwise successful JavaScript evaluation returning `{is_blocked: false, is_empty: false, items: []}` is reported as a legitimate zero-result market search. TASK-012 explicitly requires a true empty search to be distinguishable from extraction failure and says blocked/navigation/extraction problems must not be silently converted to ordinary empty marketplace results.

### Required Fix
Fail closed when no cards are extracted unless the page positively proves an empty result.

A small approach is sufficient:
- retain `TRUE_EMPTY_SEARCH` only when the extraction script positively reports the empty-result marker;
- otherwise, on first page with zero extracted cards and no explicit empty marker, raise a typed discovery/extraction error or equivalent fail-closed diagnostic;
- on later pages, if earlier candidates exist, return a partial batch with an explicit extraction-failure diagnostic;
- add regressions for `{is_blocked: false, is_empty: false, items: []}` showing it is not treated as `TRUE_EMPTY_SEARCH`.

If useful, the extraction result may expose a small structural field such as `listing_surface_detected`; do not add a complex framework.

## RESULT Evidence Finding — Diff stat is not the task diff

`RESULT-012` reports a diff stat containing only `src/product_intelligence/__init__.py | 40 ...`, while GitHub's main → task comparison shows the task adds/modifies ten files, including the discovery contract, Shopee adapter/parser, docs, and three focused test files.

Refresh RESULT-012 after the FIX with a concise but accurate task/FIX diff stat. Preserve the exact focused/full commands, pass counts, discovery bounds, identity/dedup policy, missing-value policy, failure semantics, side-effect boundaries, limitations, and no-auto-merge statement.

## Verification Notes
Preserve the currently-correct behavior:
- `max_candidates` is bounded to 1–100 and `max_pages` to 1–5;
- deterministic URL encoding, stable candidate identity, and first-seen dedupe;
- no per-result deep detail-page opening in the normal discovery path;
- no image processing, GDrive, LLM/provider, scoring/ranking, or queue mutation;
- unobserved commission/creator/video/velocity fields remain `None`;
- first-page navigation failure and detected blocked/captcha pages fail closed;
- later-page navigation failure after valid earlier candidates can return explicit partial diagnostics;
- M2.1 scoring/evidence behavior remains unchanged.

## Decision
CHANGES_REQUIRED.

Do not merge automatically. Publish fixes only through this exact REVIEW-012 artifact, then request `Review TASK-012` again.
