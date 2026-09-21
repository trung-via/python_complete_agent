# Phase 8 Public TikTok PDP Collector Implementation

Classification: **BOUNDED_OFFLINE_FIRST_IMPLEMENTATION_ONLY**  
Task: **TASK-232**  
Publication gate: effective only after independent semantic PASS and exact reviewed-source publication

## Capability and ownership

TASK-232 implements one narrow Product Intelligence capability:
`src/product_intelligence/adapters/tiktok_pdp.py` observes one exact public TikTok Shop PDP and
constructs the existing `ProductCandidateSnapshot`. It does not create another observation,
evidence, Product Truth, Product Source, Affiliate, ranking, recommendation, approval, persistence,
or action owner. Existing downstream normalization remains the sole producer of `SignalEvidence`.
`ProductSourcePack` remains seller-fact and original-media authority only.

The collector accepts an already-provided `BrowserSession`-like dependency and calls only its
single-page `navigate` and `evaluate` capabilities. Browser/profile/page selection, CDP connection,
start, restart, close, login, CAPTCHA handling, retry, and session lifecycle remain with the existing
browser authorities. Capability is not authority: this implementation grants no live acquisition.

## Exact-listing admission

The requested target is parsed only by
`src/product_intelligence/adapters/tiktok_parsing.py::extract_tiktok_product_id`, the one canonical
TikTok source-product parser. After navigation, identity may be established only from the observed
URL and bounded explicit current-product ID attributes. At least one observed basis is required and
every safely established basis must equal the requested ID. Mismatch, conflicting or malformed
explicit IDs, missing identity, login/challenge/block/unavailable state, search or unrelated pages,
and navigation/evaluation failure fail closed without a snapshot. Title, seller, image, slug, SKU,
model SKU, and similarity never substitute for source-product identity.

The page extraction boundary returns raw candidate lists only: observed URL, access state, explicit
identity candidates, title, shop name, current price, original price, discount, sold count, rating,
and review count. JavaScript does not select a factual winner. Python admission deterministically
accepts one compatible value; conflicting optional candidates become unknown. A single explicit,
non-placeholder title is required, so missing, inferred, or conflicting title candidates fail the
required-field gate.

## Strict PDP scalar law

Existing search-card `parse_tiktok_price` semantics remain unchanged, including intentional
range-lower-bound behavior. The exact-PDP helper implements
`AMBIGUOUS_PRICE_IS_NOT_EXACT_PRICE`: displayed ranges, variant-dependent wording, multiple numeric
representations in one candidate, and conflicting scalar candidates become `None`. Equivalent
repeated scalar representations reconcile to one value. No variant is clicked or selected and no
first match, bound, midpoint, or inferred substitute is used.

Exact-PDP sold and review count parsing distinguishes an explicit observed zero from missing or
unparseable data. Optional missing values remain `None`; zero is never converted to missing.

## V1 output and transport provenance

The canonical snapshot contains only the TASK-231 V1 allowlist: `source_product_id`, the safely
admitted observed URL, caller-supplied timezone-aware `observed_at`, explicit title, shop name,
price, original price, discount percent, sold count, rating, and review count. Platform is `tiktok`
and the collector identity is `tiktok_public_pdp_v1`. Category, brand, model, shop ID, Affiliate
economics, creator/video/similar-listing counts, and every velocity field remain `None`.

Requested URL, observed URL, and identity-basis provenance are returned separately in a frozen
transport-only binding receipt. That receipt does not own price, traction, evidence, truth, ranking,
approval, canonical identity, or persistence. `SOURCE_IDENTITY_IS_NOT_CANONICAL_IDENTITY`,
`SNAPSHOT_IS_NOT_TREND`, `EVIDENCE_IS_NOT_PRODUCT_TRUTH`, and `ONE_CAPABILITY_ONE_AUTHORITY` remain
mandatory.

## Offline and authority boundary

This publication records zero live authority.

Tests use only fake sessions and deterministic extraction payloads. They perform no TikTok/network,
Playwright/CDP, credentials, provider/LLM, Drive, wall-clock, filesystem-evidence, variant interaction,
or browser lifecycle operation. They cover exact identity, fail-closed access/identity/title gates,
strict and conflicting prices, equivalent candidates, explicit zero, missing fields, unauthorized
field absence, dependency separation, and preserved discovery parsing behavior.

Publication of TASK-232 records only that this bounded offline-first implementation exists. It
acquires no live evidence and executes no pilot, test, ranking, recommendation, approval, P7.4,
P7.5, P8.4, or commerce action. Live and automated public-PDP acquisition authority remain `NONE`;
`automatic_live_pilot`, `automatic_p8_4`, `real_pilot_executed`, and `live_evidence_acquired` remain
false. The next decision is exactly `HUMAN_BRAIN_LIVE_PUBLIC_PDP_PILOT_AUTHORIZATION`.
