# Phase 8 Public TikTok PDP Live-Pilot Review and DOM Diagnostic

Status: publication-gated TASK-234 reconciliation and offline enablement only  
Classification: `LIVE_PILOT_RECONCILIATION_AND_OFFLINE_DOM_DIAGNOSTIC_ENABLEMENT_ONLY`

## Reviewed TASK-233 execution event

TASK-233 is immutable published history at source
`99338787dcfff5e1897b9d58c12b04f7961f6e58`. After publication, the Human invoked its one
authorized capture attempt for context `p8-pilot-001-led-motion-tiktok-vn` and source ID
`1731381331718341815`. The operation reported `SUCCESS`, bound requested and observed URL through
`OBSERVED_URL`, and acquired one bounded external source artifact. Therefore
`real_pilot_executed=true`, the single authorized attempt is consumed, and
`authorized_capture_attempts_remaining=0`.

Here `live_evidence_acquired` means only `EXTERNAL_BOUNDED_SOURCE_ARTIFACT_ONLY`. The artifact has
not been ingested as canonical evidence: `canonical_evidence_ingested=false`. Identity binding and
title are `OBSERVED`; `shop_name`, `price`, `original_price`, `discount_percent`, `sold_count`,
`rating`, and `review_count` remain `UNKNOWN`.

A contemporaneous Human-visible screenshot showed that several categories were present in the UI.
That is selector-miss diagnostic context only. Screenshot and chat-visible values are explicitly
excluded from canonical evidence and must not be transcribed into `ProductCandidateSnapshot`,
`SignalEvidence`, P7.4/P7.5, scoring, ranking, approval, testing, action, or persistence state.
`EVIDENCE_IS_NOT_PRODUCT_TRUTH`, `SOURCE_IDENTITY_IS_NOT_CANONICAL_IDENTITY`, and
`SNAPSHOT_IS_NOT_TREND` remain binding.

## Attach-only structural diagnostic

`src/product_intelligence/tiktok_pdp_dom_diagnostic.py` implements one fixed, bounded diagnostic
carrier. It accepts only an explicit external `--job-root` and operator-owned `--cdp-endpoint`.
It borrows exactly one existing session, evaluates exactly one bounded script against the already
open page, validates identity using the canonical
`src/product_intelligence/adapters/tiktok_parsing.py` authority, creates one fixed-name artifact
exclusively, and releases the acquired session through `manager.close_session(run_id)`.

The carrier has no URL, source, query, navigation, retry, profile, cookie, Affiliate, scheduler,
or generic scraping control. It cannot navigate, refresh, click, type, scroll, search, change a
variant, open a page, or call `TikTokPdpCollector`. Search, login, challenge, CAPTCHA, unavailable,
unrelated, different-product, malformed, or unverifiable identity state fails closed with no
diagnostic artifact.

The script prefers the visible `main` subtree and bounds its fallback, element count, candidates,
attributes, excerpts, class tokens, signatures, and ordering. Its only hint categories are
`TITLE_LIKE`, `SHOP_LIKE`, `CURRENT_PRICE_LIKE`, `ORIGINAL_PRICE_LIKE`, `DISCOUNT_LIKE`,
`SOLD_LIKE`, `RATING_LIKE`, and `REVIEW_LIKE`. The exact output schema contains only structural
selector hints. It excludes raw HTML, full-page text, cookies, storage, headers, network payloads,
request or response bodies, tokens, credentials, login or QR codes, browser profiles, CDP endpoint,
private messages, screenshots, media, and account identifiers.

Every hint and the artifact as a whole has `evidence_authority=NONE`. A hint is not an admitted
marketplace value and is never parsed into `ProductCandidateSnapshot`. `CAPABILITY_IS_NOT_AUTHORITY`
and `ONE_CAPABILITY_ONE_AUTHORITY` remain binding. Product Intelligence owns only this diagnostic
orchestration; TASK-137 retains browser and borrowed-CDP lifecycle authority, TASK-231 remains the
sole public-PDP acquisition contract, `ProductCandidateSnapshot` remains the marketplace
observation contract, and `SignalEvidence` remains the field-evidence owner.

## TASK-233 cleanup clarification

TASK-233's prohibition on `manager.close_session` was over-conservative. After a session is
acquired, its carrier now calls `manager.close_session(run_id)` in `finally`. It never calls
`session.close()` directly, `close_all()`, or browser/context/page close operations. A primary
operation failure remains primary if cleanup also fails.

Under TASK-137, closing the borrowed `PlaywrightBrowserSession` releases only Python Agent-owned
Playwright connections and listeners; it does not close Human-owned Chromium, browser context, or
page. This clarification supersedes only the TASK-233 consumer cleanup interpretation. It does not
move browser lifecycle authority into Product Intelligence.

## Publication gate and next authority

On exact reviewed TASK-234 publication, diagnostic implementation exists, but
`live_dom_diagnostic_authority=NONE`, `diagnostic_executed=false`,
`selector_repair_complete=false`, `automated_public_pdp_acquisition_authority=NONE`, and
`market_test_or_action_authority=NONE`. The next milestone is null and pending commitments are
empty. No diagnostic, second capture, selector repair, recommendation, test, or action is automatic.
The exact handoff is `HUMAN_BRAIN_ONE_SHOT_PUBLIC_PDP_DOM_DIAGNOSTIC_AUTHORIZATION`.
