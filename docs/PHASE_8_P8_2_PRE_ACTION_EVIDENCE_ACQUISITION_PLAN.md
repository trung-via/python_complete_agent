# Phase 8 / P8.2 — Pre-Action Evidence Acquisition Plan

Status: **TASK-228 publication-gated DONE as `PRE_ACTION_EVIDENCE_ACQUISITION_PLAN_ONLY`; no live evidence acquired and no real pilot executed.**

Plan identifier: `p8-pilot-001-pre-action-evidence-plan`

Planning owner: **HUMAN / BRAIN**

## 1. Classification, exact binding, and authority

This is exactly one advisory plan for the Human-selected P8.1 case. It is not collector
configuration, acquisition authorization, execution state, evidence truth, test readiness, or
decision authority. It neither recommends an action nor grants an acquisition order. Technical
capability does not authorize use.

- Context ID: `p8-pilot-001-led-motion-tiktok-vn`
- Product selection label: **“Đèn LED Cảm Biến Chuyển Động Tự Động Bật Tắt Điều Chỉnh 3 Chế Độ Sáng”**
- Marketplace: **TikTok Shop Vietnam**
- Channel context: **TikTok Shop Affiliate**
- External source ID: `1731381331718341815`
- Stable listing reference:
  `https://shop.tiktok.com/vn/pdp/den-led-cam-bien-chuyen-dong-3-che-do-sang-sac-usb-c/1731381331718341815`
- Identity scope: `SOURCE_IDENTITY_IS_NOT_CANONICAL_IDENTITY`

The source ID and stable reference identify the selected external listing only. They are not
canonical product identity or current marketplace truth. Similar listings, search results, URL slug
text, synthetic fixtures, historical cohorts, or other products cannot substitute for evidence
about this exact listing.

P7.3 remains the sole owner of `DecisionContext` and `OpportunityHypothesis`; P7.4 remains the sole
owner of `TikTokAffiliateEvidenceProfile`; P7.5 remains the sole owner of VOI planning; P7.6 remains
the sole owner of market-test evidence; P7.7 remains the sole owner of winner validation; and P8.0
remains the sole decision-loop composition owner. Product Intelligence remains the sole owner of
`ProductCandidateSnapshot`, `SignalEvidence`, Product Source Pack, discovery, scoring/ranking,
approval, identity/catalog, persistence, and product-truth semantics. P8.2 plans questions and
possible acquisition paths without owning evidence or changing any of those meanings.

The preserved P8.1 hypothesis is planning context only: under an authorized bounded TikTok Shop
affiliate market test, this exact listing could produce positive contribution margin subject to
Human-defined quality, exposure, economic, and risk constraints. This plan supplies no universal
contribution-margin formula or threshold and does not authorize a test.

## 2. Fixed P7.4 evidence-dimension boundary

Every evidence inquiry below is organized by exactly the six P7.4 dimensions, in their canonical
order:

1. `affiliate_economics`
2. `market_traction`
3. `creator_ecosystem`
4. `content_activity`
5. `audience_channel_fit`
6. `competition_saturation`

These labels are an organization boundary, not new ownership. Exact-listing identity, provenance,
observation time, source facts/media, inventory, and availability are acceptance or contextual
properties attached to a question; they do not create additional P7.4 dimensions. Represented does
not mean sufficient, missing does not mean absent, and missing does not authorize collection.

## 3. Current capability and gap matrix

| Surface | Current bounded capability | Current gap for this pilot | Authority boundary |
|---|---|---|---|
| Product Intelligence models | Model `price`, `original_price`, `discount_percent`, `sold_count`, `rating`, `review_count`, `affiliate_commission_rate`, `estimated_commission_value`, `creator_count`, `video_count`, `similar_listing_count`, `sales_velocity`, `review_velocity`, `creator_velocity`, and `video_velocity`. | A modeled field does not establish that a trustworthy exact-listing source currently supplies it. | Product Intelligence owns these observed-fact semantics; P8.2 neither duplicates nor fills them. |
| `TikTokDiscoveryAdapter` search-card discovery | Can observe bounded visible search-card price, original price, discount, sold count, rating, and review count when present. | It intentionally leaves affiliate commission, creator, video, similar-listing, and velocity fields `None` when unavailable. A search card or similar listing is not exact-listing evidence. | Discovery capability is not authorization, evidence quality, exact identity, approval, or current listing truth. |
| `TikTokSourceExtractor` | Can produce typed exact-product `ProductSourcePack` identity, facts, and seller-media evidence when product identity is safely bound. | It is not an authority for affiliate economics, creator ecosystem, content activity, audience-channel fit, competition saturation, or market-test evidence. The selected `/pdp` identity is not currently bindable by its parser. | Source Pack evidence remains source evidence, not canonical identity/truth or affiliate/test authority. |
| Exact-listing live evidence paths | No canonical live collector is currently established for this pilot's exact-listing affiliate eligibility/commission, creator ecosystem, content activity, audience-channel fit, or competition saturation. | Those paths are unavailable or unproven; no field may be fabricated, inferred from the slug, or borrowed from another listing. | A later Human/Brain authorization and the relevant existing semantic owner are required. |
| Human-operated capture architecture | Historical P6 architecture supports external, operator-owned authenticated capture with a Human review gate and deterministic later replay. | No capture is authorized for this pilot, and no READY artifact exists for it. | Login/session/CAPTCHA and live operation remain Human/operator-owned outside ordinary AIOS verification. |

### Exact `/pdp` identity compatibility blocker

Both current TikTok ID-parsing surfaces recognize `/product/<id>`, `/item/<id>`, and supported query
identifiers, but not the selected `/vn/pdp/<slug>/<id>` form. The affected surfaces are
`src/product_intelligence/adapters/tiktok_parsing.py` and
`src/product_source/platforms/tiktok.py`. Therefore exact-listing `ProductSourcePack` live
acquisition for this pilot is not authorized or trustworthy until a later, separately reviewed,
narrow compatibility correction proves binding to source ID `1731381331718341815`. TASK-228 does
not fix either parser and does not prescribe implementation HOW.

## 4. Evidence waves and non-progression rule

Wave labels partition planning scope; they do not rank evidence, schedule work, authorize a
collector, or trigger progression.

### `WAVE_0_COMPATIBILITY_PREREQUISITE`

Wave 0 may exist only as a later separately authorized engineering correction if Human/Brain elects
to use the existing deep PDP capture path for this pilot. Its bounded outcome would be exact
selected-listing ID compatibility plus regression preservation. It is not marketplace evidence,
must not acquire marketplace evidence, must not expand collector semantics, and must not
automatically trigger Wave 1.

### `WAVE_1_MINIMUM_DECISION_EVIDENCE`

Wave 1 is the smallest pre-action evidence set worth considering before deeper acquisition:

- exact-listing identity and provenance as a mandatory acceptance gate;
- current listing/variant price economics where observable;
- current sold count, review count, and rating observations where observable;
- current affiliate eligibility, affiliate commission, and estimated commission where legitimately
  available;
- exact product/source facts and seller media only when useful to the decision; and
- inventory or availability only when decision-relevant.

Missing Wave-1 evidence stays unknown. It must not be replaced with a similar listing, search-card
proxy, URL slug inference, synthetic value, or stale observation presented as current.

### `WAVE_2_CONDITIONAL_EVIDENCE`

Wave 2 is conditional, never automatic: creator ecosystem, content/video activity,
audience-channel fit, competition saturation, longitudinal velocity, and deeper contentability or
competitive evidence. It may be considered only after Human review of Wave 1 and qualitative
P7.5-style VOI reasoning concludes that the additional answer could materially change the Human
decision enough to justify its cost, latency, access risk, fragility, reliability limits, and
opportunity cost. That conclusion is still not acquisition authorization.

## 5. Inspectable Wave-1 evidence inquiries

Each inquiry records all nine P7.5 considerations qualitatively. `CONTINUE`, `DEFER`, and `STOP`
below, where used, are planning dispositions only and never collection authorization.

### W1-A — Current exact-listing price and affiliate economics

- **P7.4 dimension:** `affiliate_economics`.
- **Question:** For the exact listing and currently selected/available variant, what price,
  discount, affiliate eligibility, commission rate, estimated commission value, and decision-relevant
  availability are observable through a legitimate source?
- **Expected decision impact:** Could change whether the Human sees a plausible economic basis for
  considering a bounded test; it cannot decide margin or approval by itself.
- **Uncertainty reduction:** Reduces listing-specific offer/economics unknowns only for the observed
  time and variant.
- **Cost:** Requires bounded Human/operator effort and possibly authenticated access; no cost is
  assumed or approved here.
- **Latency:** Depends on a separately authorized legitimate source and Human availability.
- **Access risk:** Affiliate account or authenticated marketplace access may carry platform,
  account, policy, privacy, and credential-handling risk.
- **Fragility:** Price, discount, eligibility, commission, variants, and stock can change quickly.
- **Reliability:** Accept only exact-listing provenance, explicit variant context, observation time,
  and a source legitimately visible to the operator; do not infer missing values.
- **Opportunity cost:** Time spent here may displace Human definition of economic constraints or
  review of already available evidence.
- **Decision-deadline consideration:** No deadline is supplied; urgency must not be invented, and a
  later observation may arrive too late only relative to a future P7.3/Human-owned deadline.

### W1-B — Current market-traction observations

- **P7.4 dimension:** `market_traction`.
- **Question:** What sold count, review count, rating, and—only if decision-relevant—inventory or
  availability are visibly attributable to this exact listing at an explicit observation time?
- **Expected decision impact:** Could alter whether the Human seeks a test, defers, or accepts the
  remaining demand/trust uncertainty; it is not a winner signal.
- **Uncertainty reduction:** Reduces only current exact-listing traction uncertainty, not causality,
  demand quality, future sales, or channel fit.
- **Cost:** Bounded capture and review effort; no spend or acquisition budget is authorized.
- **Latency:** A current observation may be quick only if a legitimate exact-listing path is already
  available; compatibility or access gates can make it unavailable.
- **Access risk:** Any authenticated access remains externally Human-operated and policy-bound.
- **Fragility:** Counts, ratings, reviews, inventory, and availability are mutable and may be stale.
- **Reliability:** Require exact source identity, observation time, field-level provenance, and clear
  treatment of unavailable or ambiguous displays as unknown.
- **Opportunity cost:** Deeper traction inspection may be less valuable than resolving missing
  Human-owned decision constraints.
- **Decision-deadline consideration:** No deadline value exists here; interpret timeliness only
  against a future Human/P7.3 deadline.

### W1-C — Exact source facts and seller media useful to the decision

- **P7.4 dimension:** `audience_channel_fit` (organization only; facts/media do not themselves prove
  audience or channel fit).
- **Question:** Which exact product/source facts and seller media, if any, are necessary for the
  Human to judge whether further fit/contentability inquiry is worth considering?
- **Expected decision impact:** Could expose a decisive product attribute or media limitation, but
  cannot establish audience fit, creative performance, or quality truth alone.
- **Uncertainty reduction:** Reduces selected source-description uncertainty only for captured facts
  and media.
- **Cost:** Deep capture and Human review may be non-trivial and first requires the separate `/pdp`
  compatibility prerequisite if the existing extractor is chosen.
- **Latency:** Blocked for that extractor until separately reviewed exact-ID compatibility exists;
  an independently authorized manual contribution may have different latency.
- **Access risk:** Authenticated interaction and media handling may carry platform, account,
  copyright, privacy, and credential risks.
- **Fragility:** Seller content, variants, and media can change or disappear.
- **Reliability:** Accept only exact-listing seller-source artifacts with observation time and safe
  provenance; do not treat source evidence as canonical truth.
- **Opportunity cost:** Full source capture may be wasteful when price/commission or Human constraints
  already decide STOP or DEFER.
- **Decision-deadline consideration:** No deadline is supplied; the Human must decide whether delayed
  source detail remains useful before authorizing it.

## 6. Inspectable Wave-2 conditional inquiries

### W2-A — Creator ecosystem

- **P7.4 dimension:** `creator_ecosystem`.
- **Question:** Is there exact-listing-attributable creator participation evidence that could
  materially change the Human's decision after Wave 1?
- **Expected decision impact:** Could alter perceived creator supply or execution feasibility, but
  does not recommend participation or predict outcomes.
- **Uncertainty reduction:** Reduces only attributable creator-ecosystem uncertainty; absent visible
  data remains unknown.
- **Cost:** Potentially high Human research and review effort; no collector or account inspection is
  authorized.
- **Latency:** May require slow manual investigation or an unavailable legitimate evidence path.
- **Access risk:** Creator/affiliate surfaces may require authenticated access and carry platform,
  privacy, and policy exposure.
- **Fragility:** Creator participation and eligibility can change rapidly.
- **Reliability:** Require exact-listing attribution and provenance; names/counts from similar
  products are not substitutes.
- **Opportunity cost:** May distract from more decision-material economic or Human-owned constraints.
- **Decision-deadline consideration:** Consider only if the information can arrive before a future
  Human/P7.3 deadline and still change the decision.

### W2-B — Content/video activity and deeper contentability

- **P7.4 dimension:** `content_activity`.
- **Question:** What exact-listing-attributable content/video activity or product-media constraints
  could materially change the Human decision after Wave 1?
- **Expected decision impact:** Could change whether a content-led test is worth considering, without
  predicting creative performance or authorizing publication.
- **Uncertainty reduction:** Reduces uncertainty about observable content activity or content inputs,
  not audience response, causality, or future performance.
- **Cost:** Manual attribution, artifact review, and potentially authenticated access can be costly.
- **Latency:** Content discovery and attribution may take longer than current listing checks.
- **Access risk:** Account, platform-policy, copyright, privacy, and unsafe-artifact risks must be
  bounded by a later authorization.
- **Fragility:** Videos, engagement displays, and seller media may be removed, reordered, or changed.
- **Reliability:** Require exact-listing attribution, observation time, provenance, and distinction
  between seller media and independent creator content.
- **Opportunity cost:** Deep content review can consume attention without resolving test economics or
  missing Human constraints.
- **Decision-deadline consideration:** Do not pursue if it cannot affect the decision before a future
  Human/P7.3 deadline.

### W2-C — Audience-channel fit

- **P7.4 dimension:** `audience_channel_fit`.
- **Question:** What legitimate evidence, beyond source facts/media alone, could change the Human's
  view of fit between this exact product, a Human-defined audience, and TikTok Shop Affiliate?
- **Expected decision impact:** Could alter test consideration only after the Human supplies a target
  audience and quality/risk constraints.
- **Uncertainty reduction:** Cannot reduce audience-fit uncertainty while the Human-owned audience is
  unset; marketplace facts alone cannot supply it.
- **Cost:** Likely requires Human analysis or later test evidence; no market test is authorized.
- **Latency:** Deferred until required Human inputs exist and a lawful evidence path is chosen.
- **Access risk:** Audience or account data may introduce privacy, policy, and credential risk.
- **Fragility:** Audience behavior and channel conditions are context- and time-dependent.
- **Reliability:** Require explicit audience definition, exact-listing provenance, and clear limits;
  proxy audiences and similar products do not bind this case.
- **Opportunity cost:** Premature collection would displace defining the Human-owned audience and
  decision criteria.
- **Decision-deadline consideration:** No deadline exists; this inquiry remains DEFER until inputs and
  timing are explicitly owned by Human/P7.3.

### W2-D — Competition saturation and deeper competitive evidence

- **P7.4 dimension:** `competition_saturation`.
- **Question:** What exact-listing-relevant competitive evidence could materially change the Human's
  decision, without substituting competitors or similar listings for facts about this listing?
- **Expected decision impact:** Could alter the perceived differentiation or crowding context, but
  cannot decide viability or rank the selected product automatically.
- **Uncertainty reduction:** Reduces a bounded competitive-context unknown only; it does not resolve
  exact-listing economics or traction.
- **Cost:** Defining the comparison set and reviewing provenance can be expensive and Human-intensive.
- **Latency:** Competitive observations may take substantial time and may be obsolete on arrival.
- **Access risk:** Marketplace search or authenticated surfaces retain platform and account risk; no
  scraping is authorized.
- **Fragility:** Search placement, offers, competitors, and content volume can change frequently.
- **Reliability:** Require a Human-approved comparison definition, observation time, and provenance;
  `similar_listing_count` must not be fabricated or treated as universal saturation.
- **Opportunity cost:** Broad competitor research may crowd out exact-listing or Human-input work.
- **Decision-deadline consideration:** Stop if competitive evidence cannot arrive while it remains
  capable of changing the Human decision.

### W2-E — Longitudinal velocity

- **P7.4 dimension:** `market_traction` for sales/review velocity, `creator_ecosystem` for creator
  velocity, and `content_activity` for video velocity; the fixed meanings remain externally owned.
- **Question:** Would repeated exact-listing observations of sales, reviews, creators, or videos
  materially change the decision enough to justify waiting and repeated capture?
- **Expected decision impact:** Could change interpretation of momentum, but must not become a score,
  forecast, recommendation, or winner judgment.
- **Uncertainty reduction:** Reduces longitudinal uncertainty only when observations are comparable,
  exact-listing-bound, and separated by explicit observation times.
- **Cost:** Requires repeated Human-authorized operations and review; no scheduler or recurring job is
  authorized.
- **Latency:** Inherently requires waiting across a Human-approved interval that is currently unset.
- **Access risk:** Repeated authenticated access compounds account, policy, and credential exposure.
- **Fragility:** Field definitions, presentation, availability, and listing state may change between
  observations.
- **Reliability:** Require comparable provenance and explicit observation times; derived velocity must
  remain under Product Intelligence ownership and unknown when inputs are insufficient.
- **Opportunity cost:** Waiting for trend evidence may delay a decision that the Human could make with
  accepted uncertainty.
- **Decision-deadline consideration:** With no Human/P7.3 deadline or observation interval, this
  inquiry is DEFER; stop if waiting would outlast decision usefulness.

## 7. Explicit STOP and DEFER conditions

Acquisition stops or remains unauthorized when any of the following applies:

- the answer is unlikely to change the Human decision;
- expected benefit does not justify access, cost, latency, risk, or opportunity cost;
- provenance cannot be tied to source ID `1731381331718341815` and the exact stable listing;
- a CAPTCHA/security challenge would require automated solving, automated retry, bypass, evasion,
  proxy/stealth behavior, or other unsafe access behavior;
- no legitimate Human-operated path is available to resolve a CAPTCHA/security challenge outside
  ordinary AIOS verification;
- a Human-owned constraint is missing and further marketplace evidence cannot resolve it;
- evidence is stale or fragile beyond useful interpretation;
- a legitimate exact-listing path is unavailable or the `/pdp` compatibility blocker applies;
- the evidence would merely duplicate sufficient accepted information;
- the Human decides current uncertainty is acceptable for STOP, DEFER, or no-test; or
- a future decision deadline would pass before the evidence could remain useful.

There is no universal numeric VOI score, evidence-priority score, fixed weighting, recommendation,
ranking, deadline value, or acquisition-order authority in this plan.

A CAPTCHA/security challenge does not by itself forbid a later bounded acquisition. A Human may
resolve the challenge outside ordinary AIOS verification, but challenge resolution grants no
evidence, collector, test, or action authority. Any resume requires a separate, fresh explicit
Human/Brain-authorized operation and remains subject to every boundary in this plan.

## 8. Boundary for any later live evidence operation

Any later live operation requires a fresh explicit Human/Brain authorization and must preserve all
of these conditions:

- authenticated marketplace interaction occurs outside ordinary deterministic AIOS engineering
  verification;
- the Human/operator owns login, authenticated session, and CAPTCHA/security-challenge preparation
  and resolution;
- there is zero automatic CAPTCHA solving, retry, proxy, stealth, evasion, or bypass automation;
- artifacts remain under an explicit external job root rather than repository planning state;
- secrets, cookies, access tokens, credentials, raw HTML, and browser-profile paths are not persisted
  into this plan, roadmap state, manifests, logs, or deterministic fixtures;
- exact source identity, variant context where relevant, explicit observation time, acquisition
  method, and field/artifact provenance remain inspectable;
- only safe, bounded artifacts may be presented for review;
- a Human reviews any `READY` capture before a separate, explicitly scoped deterministic
  freeze/replay task may use it; and
- live observations remain source evidence under existing owners, never canonical product identity,
  marketplace truth, approval, or test evidence merely because they were captured.

## 9. Human-owned decision inputs remain separate and unset

The following are required decision inputs, not marketplace evidence to scrape:

- budget;
- test duration;
- exposure controls and limits;
- contribution-margin threshold;
- success and failure criteria;
- target audience;
- quality constraints;
- risk constraints and risk acceptance; and
- any decision deadline.

Every value remains unset until the Human supplies it. TASK-228 does not invent or infer values and
does not authorize Product Intelligence `APPROVE`, ingestion, affiliate participation, campaign
creation, spend, traffic, content publication, a market test, price/inventory mutation, winner or
scalability judgment, or selection of a future intelligence domain.

## 10. Publication closure and Human/Brain handoff

On publication of the exact reviewed TASK-228 source candidate, P8.2 becomes DONE only as
`PRE_ACTION_EVIDENCE_ACQUISITION_PLAN_ONLY`. `real_pilot_executed` remains false, no live evidence
is claimed, `next_milestone` remains null, `pending_commitments` remains empty, and P8.3 is neither
automatic nor pending.

Control passes to `HUMAN_BRAIN_BOUNDED_EVIDENCE_ACQUISITION_AUTHORIZATION`. Human/Brain must
explicitly choose among authorizing a bounded Wave 0 correction, authorizing a bounded Wave-1
acquisition path, accepting a manual evidence contribution, DEFER, or STOP. Runtime or worker output
cannot make that decision, and no choice automatically authorizes Wave 2, a market test, action,
spend, publication, Product Intelligence approval, or a future domain.
