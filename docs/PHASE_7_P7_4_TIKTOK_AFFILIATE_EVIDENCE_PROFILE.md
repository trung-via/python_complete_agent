# Phase 7 P7.4 — TikTok Affiliate Evidence Profile

Status: **TASK-222 / P7.4 is publication-gated DONE. It becomes effective only
after canonical Runtime PASS, ChatGPT semantic PASS, and source-only publication
of the exact reviewed candidate. P7.5 Value-of-Information Planning is the
single NEXT commitment after that publication.**

## 1. Authority and purpose

P7.4 establishes `COMMERCE_OPPORTUNITY_INTELLIGENCE_P7_4` in
`src/commerce_opportunity_intelligence/tiktok_affiliate_evidence.py` as the
canonical production semantic authority for TikTok affiliate evidence profiles
within the Commerce Opportunity Intelligence domain. It is subordinate to
Product Contract v2, the published P7.2 Winning Opportunity Semantic
Reconciliation, and the published P7.3 Decision Context + Opportunity
Hypothesis authority.

The authority owns one immutable, deterministic semantic value, its canonical
dimension enumeration, and one pure construction surface:

- `TikTokAffiliateEvidenceProfile` organizes caller-supplied opaque references
  around exactly six ordered semantic dimensions tied to one stable caller
  `profile_id`, exact `decision_context_id`, exact `hypothesis_id`, and
  timezone-aware `as_of`.
- `TIKTOK_AFFILIATE_EVIDENCE_DIMENSIONS` defines the fixed six-dimension order:
  `affiliate_economics`, `market_traction`, `creator_ecosystem`,
  `content_activity`, `audience_channel_fit`, and `competition_saturation`.
- `create_tiktok_affiliate_evidence_profile` purely validates exact binding to a
  `DecisionContext` and `OpportunityHypothesis` without performing implicit
  identity, time, provider, network, or runtime inference.

The profile provides deterministic `represented_dimensions()` and
`unrepresented_dimensions()` projections that describe supplied reference
coverage only, preserving the fixed six-dimension order.

## 2. Epistemic and decision boundaries

The following distinctions are explicit and non-negotiable:

- **Evidence profile != evidence.** The profile organizes opaque composition
  handles to already-owned evidence; it does not contain the evidence itself or
  create new evidence facts.
- **Evidence ref != evidence ownership.** References are opaque strings pointing
  to evidence owned elsewhere. P7.4 does not own, store, rehydrate, or validate
  the underlying evidence objects, provenance, or truth.
- **Unrepresented dimension != evidence absent in the world.** An empty
  reference collection means only that caller-supplied references did not
  represent that dimension; it is not proof that evidence does not exist in the
  marketplace or world.
- **Represented dimension != evidence quality.** The presence of references
  reflects only caller-supplied coverage; it makes no claim of evidential
  sufficiency, validity, timeliness, or quality.
- **Evidence profile != score/recommendation/decision.** The profile performs
  no scoring, weighting, ranking, thresholding, filtering, or recommendation. It
  does not decide whether a hypothesis is viable or promote any opportunity.
- **TikTok affiliate profile != live TikTok capability.** The profile is a pure
  offline semantic value; it does not scrape, call TikTok APIs, inspect live
  accounts, browse, or perform marketplace operations.
- **Missing evidence != authorization to collect.** An unrepresented dimension
  identifies an unknown for later reasoning (such as P7.5 Value-of-Information);
  it does not grant authorization to fetch, browse, scrape, or acquire data.
- **Repeated ref across dimensions != multiplied evidence weight.** The same
  opaque reference may inform multiple dimensions without multiplying weight,
  because P7.4 does no counting, scoring, or weighting.

Existing Product Intelligence fields (`affiliate_commission_rate`,
`estimated_commission_value`, `creator_count`, `video_count`) and models
(`ProductCandidateSnapshot`, `SignalEvidence`) remain the sole authorities for
their observed facts; P7.4 carries only opaque references to evidence produced
by canonical authorities. Public projections contain no score, recommendation,
decision, confidence, winner, acquisition order, or lifecycle state.

## 3. Composition without re-ownership

Commerce Opportunity Intelligence is compositional. A caller constructs an
evidence profile by supplying references to evidence already owned by upstream
authorities. P7.4 neither inspects nor mutates those upstream authorities.

A dimension with no supplied references is unrepresented, leaving uncertainty
explicit so future reasoning layers can evaluate whether additional evidence is
worth acquiring. References must be single-line, non-blank, bounded strings that
fail closed on forbidden sensitive or execution payloads (such as API keys,
bearer tokens, cookies, session identifiers, prompts, execution IDs, or raw HTML).

P7.4 operates as a pure value boundary: it introduces zero network, browser,
CDP, filesystem discovery, persistence, database, queue, background worker,
model/LLM invocation, or AIOS lifecycle APIs.

## 4. Lineage and governance preservation

TASK-215 / P7.3 is CLOSED / PUBLISHED at `dc4c4c8e6f3f4d6eb3441ff4873632e5f51655f9`.
TASK-214 / P7.2 is CLOSED / PUBLISHED at `123bbb71d44ad15a25e07b07f21f6cb2dd00d20b`.
TASK-191 / P7.1 is DONE / PUBLISHED at `40da098b3b0dcf3d1994fc510dd55717b81a2f67`.
Governance Foundation lineage, Brain planning authority, and Human priority
authority remain unchanged.
Python Agent's active AIOS-renew authority remains the exact reviewed and published
pin `edd7d8d92d54900c56442bbfcddb8648ec4d2e09`. P7.4 introduces no control-plane,
worker, review, publication, adoption, or conformance authority.

## 5. Roadmap boundary

TASK-222 implements only P7.4 and is publication-gated DONE. After its exact
reviewed source is published, P7.5 Value-of-Information Planning becomes the
single NEXT commitment. P7.6 Market Test / Funnel Evidence and P7.7 Calibration
& Winner Validation remain ordered NOT_DONE commitments. This document grants
none of those future capabilities implementation, acquisition, test, action, or
decision authority.
