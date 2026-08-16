# REVIEW-012 — TASK-012 (Phase 6 M2.2 Shopee Discovery Adapter V1)

## Status
CHANGES_REQUIRED

## Reviewed Head
- Branch: `ai/task-012`
- Reviewed commit: `3543f017fb2bacefcd06268011a06d49dea0734e`
- Main baseline: `68db4d45154994c929bae22e660f1aca236e2bcd`
- Branch relation to main: ahead 2, behind 0 (fast-forward safe)
- Task artifact blob: `86af9ebbcc5aea780146c16625d2820fcc3c1b22`
- Prior CHANGES_REQUIRED authorization blob: `408cbc0c03e2a6c71559e506c1cecd98264dc11b`
- RESULT-012 blob: `b5e8d27f699ac1c43e80f808da6536a34caa744d`
- RESULT action: `FIX`
- Exact FIX authorization recorded by worker: `.ai/reviews/REVIEW-012.md (408cbc0c03)` — matches the prior review artifact exactly.
- Reported focused Product Intelligence suite: 44 passed, 0 failed, exit code 0.
- Reported full repository suite: 417 passed, 0 failed, exit code 0.

## Re-review Summary
The three prior findings are closed correctly:

1. `review_count` is now isolated from `rating_text`; rating-only cards preserve `review_count=None`, while explicit review text is parsed separately.
2. First-page zero-card extraction without a positive empty-result marker now fails closed instead of being reported as `TRUE_EMPTY_SEARCH`; later-page zero-card extraction returns an explicit partial diagnostic.
3. RESULT-012 now gives an accurate FIX diff stat and preserves the requested verification/bounds/governance evidence.

One integration-level blocker remains against TASK-012's explicit dependency-injection requirement.

## Blocking Finding — Shopee discovery is not actually compatible with the project's existing BrowserManager/BrowserSession abstraction

### Locations
- `src/product_intelligence/adapters/shopee.py` — `_acquire_page`, `_light_scroll`, `_evaluate_script`
- `src/browser/manager.py` / `src/browser/session.py`
- `src/integrations/playwright/manager.py` / `src/integrations/playwright/session.py`
- `tests/product_intelligence/test_shopee_discovery.py`

TASK-012 requires the adapter to consume an injected browser/browser-manager dependency compatible with the existing project browser abstraction.

The adapter advertises a BrowserManager path in `_acquire_page`: when an object exposes `get_or_create_session`, it calls `get_or_create_session("discovery_run")` and returns that session. The project's real `PlaywrightBrowserManager` does exactly this and returns a `BrowserSession` / `PlaywrightBrowserSession`.

However, the public `BrowserSession` contract exposes `navigate`, `inspect`, `click`, `type_text`, `press`, and `screenshot`; it does **not** expose a public `evaluate` method. The concrete `PlaywrightBrowserSession` likewise evaluates JavaScript only internally against its private `_page`. Therefore after the adapter acquires a real project BrowserSession:

- navigation works through `session.navigate(url)`;
- `_light_scroll()` becomes a no-op because the session has no public `evaluate`;
- `_evaluate_script()` returns its fallback `{is_blocked: false, is_empty: false, items: []}` because the session has no public `evaluate`;
- the newly-correct fail-closed logic then raises `DiscoveryNavigationError` on page 1.

So the adapter passes its fake-page tests but cannot perform discovery through the actual browser dependency used by `AgentController`, where both `browser` and `browser_manager` point to `PlaywrightBrowserManager`.

The current test named `test_shopee_discovery_with_browser_manager_dependency` does not exercise the real manager contract: its `FakeBrowser` exposes `new_page()` directly, which follows the adapter's Playwright-page path rather than the project's `BrowserManager.get_or_create_session()` path.

### Required Fix
Keep this small and preserve abstraction boundaries. Make one supported path work end-to-end with the real project browser stack, and test that exact contract.

Acceptable approaches include:
- add a small, generic public script-evaluation capability to the project BrowserSession abstraction and Playwright implementation, then use it from discovery; or
- add a narrowly scoped injected discovery-page/session adapter that is intentionally supported by the existing Playwright integration without reaching into private `_page`; or
- another minimal equivalent that keeps platform DOM logic in Shopee discovery and does not construct a second browser framework.

Do **not** access `PlaywrightBrowserSession._page` directly from Product Intelligence, and do not redesign the whole browser subsystem.

Add a regression using a fake shaped like the real `BrowserManager` (`get_or_create_session`) returning a fake shaped like the public session contract/capability chosen by the fix. It must prove search navigation, extraction, candidate mapping, and bounded behavior can execute through that path.

If the browser abstraction gains a new generic capability, preserve existing browser-tool behavior and run the full suite.

## Verification Notes
Preserve the now-correct behavior from the current head:
- dedicated review-count evidence; no reuse of rating text;
- positive-marker-only `TRUE_EMPTY_SEARCH` classification;
- first-page unknown extraction failure fails closed;
- `max_candidates` 1–100 and `max_pages` 1–5;
- deterministic candidate identity and first-seen dedupe;
- unobserved commission/creator/video/velocity fields stay `None`;
- no per-candidate deep ingestion, image download, GDrive, LLM/provider, scoring/ranking, or queue mutation;
- 44 focused tests and 417 full-suite tests are reported green at the reviewed head.

## Decision
CHANGES_REQUIRED.

Do not merge automatically. Publish the compatibility fix only through this exact updated REVIEW-012 artifact, then request `Review TASK-012` again.
