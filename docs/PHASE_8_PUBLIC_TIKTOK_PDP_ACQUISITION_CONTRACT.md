# Phase 8 — Public TikTok Shop PDP Acquisition Contract

Status: **TASK-231 publication-gated DONE only as
`PUBLIC_PDP_ACQUISITION_CONTRACT_ONLY`.**

Authorization owner: **HUMAN / BRAIN**

## 1. Classification and purpose

This document is the one canonical contract for a later bounded public TikTok Shop PDP
acquisition capability. TASK-231 defines architecture and authorizes a separately authored,
offline-first implementation commitment. It does not implement a collector, browse TikTok,
acquire or accept evidence, produce a live snapshot, score or rank a product, recommend or approve
a decision, authorize a test, or perform a commerce action.

The governing separation is:

- `CAPABILITY_IS_NOT_AUTHORITY`: deterministic ability to observe a public PDP does not authorize
  use of that ability against a live marketplace.
- `EVIDENCE_IS_NOT_PRODUCT_TRUTH`: an admitted observation remains time-bound source evidence, not
  canonical product truth.
- `SOURCE_IDENTITY_IS_NOT_CANONICAL_IDENTITY`: an exact TikTok source product ID proves only the
  external listing observation boundary.
- `SNAPSHOT_IS_NOT_TREND`: one point-in-time observation proves no direction or future behavior.

Public-PDP acquisition is therefore only a transport and admission capability beneath existing
Product Intelligence semantics. Evidence truth, Product Source facts/media, Affiliate economics,
scoring, recommendation, Human decision, test authorization, and action authority remain separate.

## 2. Existing semantic owners remain exclusive

Product Intelligence remains the sole canonical owner of public marketplace observation
semantics. `ProductCandidateSnapshot` is the existing exact-listing/public-market observation
contract for fields it already owns. `SignalEvidence` is the existing field-evidence contract
created by Product Intelligence normalization. A later collector may construct the existing
snapshot and allow the existing normalizer to create its existing evidence; it must not create a
second public-PDP observation model, evidence envelope, market-metric owner, or competing identity
semantics.

`ProductSourcePack` remains the authority for seller/source facts, descriptions, and original
media. It is not an owner of public price, discount, sold count, rating, review count, source
identity, or Product Intelligence evidence. Public PDP market observations must not depend on
`ProductSourcePack` extraction, trusted-media availability, `TikTokSourceExtractor`, media
download, filesystem persistence, Google Drive, or `TikTokScrapeTool`. Missing seller facts or
media cannot invalidate an otherwise lawfully admitted public market observation, and successful
media extraction cannot make an ambiguous market metric exact.

The canonical TikTok product-ID and parsing authority remains
`src/product_intelligence/adapters/tiktok_parsing.py`. A later strict exact-PDP admission/parsing
path may be added within that authority. It must not establish a second TikTok parser authority.

## 3. Exact selected case and listing boundary

This contract preserves the selected planning case without observing it:

- context ID: `p8-pilot-001-led-motion-tiktok-vn`;
- marketplace: TikTok Shop Vietnam;
- external source product ID: `1731381331718341815`;
- stable listing reference:
  `https://shop.tiktok.com/vn/pdp/den-led-cam-bien-chuyen-dong-3-che-do-sang-sac-usb-c/1731381331718341815`.

These values are planning and binding inputs only. TASK-231 does not claim that the page is
available or that any title, shop, price, discount, traction, variant, inventory, or Affiliate
value is currently true.

## 4. Future automated public-PDP V1 allowlist

The future V1 implementation is limited to the following existing observation surface:

1. exact `source_product_id`;
2. exact requested URL plus observed/post-navigation URL and deterministic binding context;
3. explicit timezone-aware `observed_at`;
4. title, only when explicitly observed and unambiguously bound to the exact listing;
5. `shop_name`, only when explicitly observed;
6. current scalar `price`, only when explicit and unambiguous;
7. scalar `original_price`, only when explicit and unambiguous;
8. explicit scalar `discount_percent`, only when unambiguous;
9. `sold_count`;
10. `rating`; and
11. `review_count`.

Identity, binding, and observation time are mandatory admission context. Title may be admitted only
when explicit; because the existing snapshot requires a non-empty title, a missing or ambiguous
title prevents snapshot admission rather than permitting an invented placeholder. Other optional
values that are missing, unavailable, conflicting, malformed, or ambiguous remain `None`/unknown;
they are never false, zero, a default, or an inferred substitute. The existing snapshot field
`price` is the V1 current-price field; no schema alias or duplicate model is introduced. Sold count,
rating, and review count are admitted only when explicitly observed and deterministically parsed.

Everything outside this allowlist is unauthorized for V1. In particular, Affiliate eligibility,
Affiliate commission rate, estimated commission value, creator/video/similar-listing counts,
Wave-2 evidence, audience fit, competition saturation, velocity, momentum, trajectory, forecast,
variant expansion, and inventory expansion remain unauthorized or deferred.
`variant_descriptor` and `inventory_availability` remain P8.2/P8.3 contextual/provenance concerns;
TASK-231 does not add them to `ProductCandidateSnapshot`, create new P7.4 dimensions, or authorize
their V1 acquisition. Deeper variant or availability semantics require a fresh Human/Brain
decision if they later become decision-relevant.

## 5. Exact-PDP price law

`AMBIGUOUS_PRICE_IS_NOT_EXACT_PRICE`.

A displayed range, multiple unresolved variant prices, a price that requires an unproven selected-
variant assumption, or conflicting price representations is not a scalar exact-PDP price. A later
implementation must not convert it by taking the lower bound, upper bound, midpoint, first variant,
URL hint, title inference, model judgment, or any other substitution. `price` and/or
`original_price` remain unknown unless the implementation can deterministically prove one
unambiguous scalar observation within the V1 boundary. Discount is likewise unknown when its
display or price basis is ambiguous.

The existing search-card parser intentionally has historical/current discovery behavior that may
treat a displayed range by its lower bound. TASK-231 does not change or reinterpret that behavior,
and search-card lower-bound parsing must never be cited as exact-PDP scalar-price evidence. The
later implementation may add strict exact-PDP parsing/admission under the same canonical TikTok
parsing authority while leaving search-card semantics intact.

## 6. Fail-closed exact-listing admission

Before emitting an admitted snapshot, the later implementation must:

1. parse the requested URL with the canonical TikTok product-ID parser;
2. require the requested ID to equal the authorized exact source ID;
3. retain the requested URL and the observed/post-navigation URL as binding context; and
4. verify the current observed listing identity where the public page exposes it.

A redirect to search, login, challenge, or an unrelated page; an explicit conflicting current-
product ID; a different product ID; malformed identity; or identity that cannot be safely
established must not emit an admitted exact-listing snapshot. Title, image, seller, slug, or
product-concept similarity cannot repair failed identity. Even successful exact source-ID matching
does not establish canonical commerce identity.

CAPTCHA/security challenge, login wall, unavailable page, or access failure yields an explicit
blocked/unavailable outcome with zero fabricated observations. There is no authority for automatic
challenge solving, bypass, stealth, proxy rotation, retry evasion, credential capture, or session
capture. Human resolution outside ordinary deterministic verification grants no additional
semantic, evidence, live-acquisition, test, or action authority.

## 7. Public and Affiliate lanes are independent

Public TikTok Shop PDP observations are semantically independent from authenticated TikTok
Affiliate access. A public V1 collector must not require an Affiliate account, Affiliate UI,
Affiliate eligibility, commission availability, or creator-program eligibility. Affiliate-only
eligibility and economics remain in their existing authenticated/manual or future separately
authorized lane and stay `None`/unknown in public V1 when unavailable.

Public price does not become Affiliate economics merely because the selected planning context is
TikTok Shop Affiliate. Likewise, Affiliate access cannot elevate ambiguous PDP data into exact
public marketplace evidence.

## 8. Snapshot is not trend, score, or decision

`SNAPSHOT_IS_NOT_TREND` is mandatory. One public PDP observation leaves `sales_velocity`,
`review_velocity`, `creator_velocity`, and `video_velocity` unknown. It grants no velocity,
momentum, trend, trajectory, forecast, future-demand, winner, recommendation, ranking, approval,
`TEST_READY`, decision, test, or action claim. Repeated-observation and Wave-2 semantics are outside
this V1 authorization and require a fresh contract and sufficient comparable evidence.

Existing normalization, scoring, recommendation, approval, P7.3 decision context, P7.4 Affiliate
evidence organization, P7.5 VOI planning, P7.6 test authority, P7.7 validation, and P8.0 composition
retain their own gates. An acquisition component may not call those gates complete.

## 9. Boundary of the separately authorized implementation

On exact TASK-231 publication, one future commitment is authorized:
`P8_PUBLIC_PDP_COLLECTOR_IMPLEMENTATION`. It is a bounded offline-first implementation only. No
successor TASK number is assigned here, and no collector is claimed to exist.

That later task may use deterministic fixtures/tests to prove the capability and may reuse existing
browser/session infrastructure plus the canonical TikTok identity/parsing authorities where
appropriate. It must not build a generic crawler framework, duplicate browser lifecycle ownership,
claim generic marketplace identity ownership, change Product Intelligence models, expand Product
Source, or make unrelated platform changes. Capability proof is not live evidence.

The post-contract authorization boundary is exactly:

- `implementation_authorized: true`;
- `live_public_pdp_acquisition_authority: NONE`;
- `automatic_live_pilot: false`;
- `automatic_p8_4: false`; and
- `market_test_or_action_authority: NONE`.

The implementation task must be independently reviewed and published before any live use can even
be considered. Control must then return to
`HUMAN_BRAIN_LIVE_PUBLIC_PDP_PILOT_AUTHORIZATION`. The first real TikTok PDP capture requires that
fresh authorization; it is not implied by TASK-231, implementation completion, test passage,
browser availability, or an authenticated session.

## 10. Publication-gated closure and preserved history

On exact reviewed TASK-231 source publication, TASK-231 is DONE only as
`PUBLIC_PDP_ACQUISITION_CONTRACT_ONLY`. TASK-228 remains DONE only as
`PRE_ACTION_EVIDENCE_ACQUISITION_PLAN_ONLY`; TASK-229 remains DONE only as
`MANUAL_WAVE_1_EVIDENCE_CONTRIBUTION_AUTHORIZATION_ONLY`, with contribution and review unperformed;
and TASK-230 remains DONE only as
`P8_WAVE_0_TIKTOK_PDP_IDENTITY_COMPATIBILITY_ONLY`. None is rewritten as evidence, collector
implementation, live acquisition, or pilot completion.

The unique current roadmap NEXT is `P8_PUBLIC_PDP_COLLECTOR_IMPLEMENTATION`, under the bounded
offline-first boundary above. There is no automatic live pilot, P8.4, P7.4/P7.5 construction,
market test, approval, or commerce action.
