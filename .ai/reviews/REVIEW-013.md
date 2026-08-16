# REVIEW-013 — TASK-013 (Phase 6 M2.2A Product Source Pack & Original Media Extraction V1)

## Status
CHANGES_REQUIRED

## Reviewed Head
- Branch: `ai/task-013`
- Reviewed commit: `c6d1c9607e6e7de71aa9ff1ac8e8f6c1e8ae1d26`
- Parent reviewed head: `f7cd4296d4efe0ed6b8e2dcaa506766fb7a9260f`
- Current main: `9d3dcfeab5ffc98bf6aeb3ef7a67912a5bc1fd52`
- Branch relation to main: ahead 14, behind 0 (fast-forward safe at review time)
- RESULT-013 blob: `6e0deb9994f32edabd5b4eb0306490ea694e8702`
- RESULT action: `FIX`
- FIX authorization recorded by worker: `.ai/reviews/REVIEW-013.md (d76db97f86)` — matches the prior CHANGES_REQUIRED artifact.
- Delta from prior reviewed head: 1 commit, 4 changed files (`RESULT-013.md`, `publish_fix.py`, `shopee.py`, DOM fixture tests).

## Verification
The RESULT records:
- Focused Product Source Pack suite: **52 passed, 0 failed**.
- Full repository suite: **470 passed, 0 failed**.
- Updated near-seed regression passes with five authentic seller gallery views and the standalone overlay rejected.
- Non-challenged live validation on Shopee product `52764529835` reports `blocked=False`, one structured image, five gallery media entries, and zero footer/review/recommendation/SVG contamination.

The branch remains a clean fast-forward from current main.

## Resolved Prior Blocker
The previous overlay contamination is resolved in both deterministic and live evidence. The new implementation keeps the verified product seed, expands within the bounded product-media scope, prefers product views represented through the gallery `<picture>` relationship, and excludes the standalone overlay/badge asset. The exact live product now reports five seller gallery views with the previously accepted overlay absent.

## Blocking Finding
### Stray publication helper is tracked in the task branch
The current task head adds a root-level file `publish_fix.py`. This file is not part of TASK-013 product-source functionality; it is a one-off publication helper that shells out to `bridge.py publish` and embeds review/result notes and test commands.

This repository has already treated temporary publication helpers as branch-hygiene defects. TASK-013 must not merge operational scratch/publish scripts that exist only to produce the result artifact.

The worker's RESULT also lists `publish_fix.py` under `Files Changed`, while its focused diff-stat section only accounts for `shopee.py` and the DOM fixture file. The authoritative GitHub delta confirms `publish_fix.py` is actually tracked in this commit.

Required correction:
1. Remove `publish_fix.py` from `ai/task-013`.
2. Do not replace it with another tracked temporary helper.
3. Keep the current Shopee extractor and regression changes unchanged unless another defect is found.
4. Re-publish RESULT-013 from the clean branch and ensure the reported changed-file set matches the actual GitHub delta.
5. Re-run the focused and full suites. Because this correction is branch hygiene only and the product-source code need not change, the successful live validation on `52764529835` may be carried forward if the extractor/test blobs remain unchanged.

## Decision
CHANGES_REQUIRED.

Do not merge TASK-013.

The next authorized worker action is:

`/aios-worker FIX TASK-013`

After the worker publishes a clean new head and RESULT, request `Review TASK-013` again. If the only delta is removal of the stray helper plus regenerated result metadata, no additional live Shopee run is required.