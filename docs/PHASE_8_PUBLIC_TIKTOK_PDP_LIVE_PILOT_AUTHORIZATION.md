# Phase 8 Public TikTok PDP Live-Pilot Authorization

Status: publication-gated TASK-233 authorization and enablement only  
Classification: `ONE_SHOT_LIVE_PUBLIC_PDP_PILOT_ENABLEMENT_AND_AUTHORIZATION`

## Human authorization

The Human authorizes one attempted public-PDP observation for context
`p8-pilot-001-led-motion-tiktok-vn`, source ID `1731381331718341815`, at exactly:

`https://shop.tiktok.com/vn/pdp/den-led-cam-bien-chuyen-dong-3-che-do-sang-sac-usb-c/1731381331718341815`

This listing-specific, operation-specific authority becomes usable only after the exact reviewed
TASK-233 candidate is published. Publication does not perform the capture. The Human operator owns
execution, the already-running browser, its login/session state, and the explicit CDP endpoint.
The endpoint is invocation-only secret transport input and is never persisted.

## Carrier and ownership boundary

`src/product_intelligence/tiktok_pdp_live_pilot.py` is orchestration only. It borrows one session
through `PlaywrightBrowserManager`, invokes the published `TikTokPdpCollector` exactly once with a
timezone-aware invocation timestamp, and releases the acquired session in `finally` through
`manager.close_session(run_id)`. It does not call `session.close()` directly, `close_all()`, or
browser/context/page close operations. Under TASK-137, manager-mediated release stops only Python
Agent-owned Playwright connection/listener resources and does not terminate borrowed Human-owned
Chromium, context, or page. This TASK-234 clarification supersedes only the earlier
consumer-level prohibition on `manager.close_session`; browser lifecycle authority remains with
TASK-137 and does not transfer to Product Intelligence.
The target cannot be overridden. There is no search, batch, credential, profile, Affiliate,
scheduler, cadence, retry, resume, proxy, stealth, CAPTCHA-solving, parser, ranking, approval, or
canonical-persistence control.

`TikTokPdpCollector` remains the exact-PDP collection authority,
`src/product_intelligence/adapters/tiktok_parsing.py` remains the canonical TikTok parser, and
`ProductCandidateSnapshot` remains the observation contract. The carrier creates no duplicate
marketplace, evidence, Product Source, Affiliate, identity, truth, or persistence owner.

## Safe external artifact

The CLI requires an explicit external `--job-root` and explicit operator-owned `--cdp-endpoint`.
Repository-contained roots fail closed. Success exclusively creates one fixed-name JSON document
and never overwrites an existing capture. Its allowlist is operation status and fixed authorization
metadata, requested/observed exact-binding data, transport-only identity bases, observation time,
and the TASK-231 ProductCandidateSnapshot V1 fields. It excludes the CDP endpoint, raw HTML,
headers, cookies, tokens, credentials, browser-profile paths, arbitrary page text, screenshots,
media, Affiliate values, and every non-V1 field.

A CAPTCHA/security challenge, login wall, access block, unavailable page, navigation/evaluation
failure, identity mismatch/conflict/unverifiability, or required-title extraction failure stops the
attempt with no successful snapshot. There is no automatic retry, refresh, resume, rebind, bypass,
or second capture. Human resolution of a challenge does not revive the spent authorization; a
later attempt requires fresh Human/Brain authorization.

## Meaning and review gate

Any successful artifact is source evidence for mandatory Human review only.
`SOURCE_IDENTITY_IS_NOT_CANONICAL_IDENTITY`, `EVIDENCE_IS_NOT_PRODUCT_TRUTH`, and
`SNAPSHOT_IS_NOT_TREND` remain binding. Public-PDP observation is independent from authenticated
TikTok Affiliate eligibility or economics. The artifact is not automatically normalized, ingested,
scored, ranked, approved, frozen, converted into trend or velocity, or used to construct P7.4/P7.5.
It is not `TEST_READY`, a recommendation, a decision, market-test evidence, Product Truth, or
commerce-action authority.

On exact reviewed publication, authority is `ONE_SHOT_EXACT_LISTING_ONLY`, authorized attempts are
`1`, execution owner is `HUMAN_OPERATOR`, automated acquisition remains `NONE`, and automatic live
pilot remains false. No live evidence or real pilot is claimed by engineering publication. The
next milestone remains null, pending commitments remain empty, and the exact handoff is
`HUMAN_OPERATOR_ONE_SHOT_PUBLIC_PDP_CAPTURE_EXECUTION`.
