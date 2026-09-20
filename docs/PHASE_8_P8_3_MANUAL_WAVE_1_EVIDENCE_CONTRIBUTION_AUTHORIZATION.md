# Phase 8 / P8.3 — Manual Wave-1 Evidence Contribution Authorization

Status: **TASK-229 publication-gated DONE only as `MANUAL_WAVE_1_EVIDENCE_CONTRIBUTION_AUTHORIZATION_ONLY`; no evidence is contributed or accepted by this task and no real pilot is executed.**

Authorization owner: **HUMAN / BRAIN**

## 1. Classification, exact case, and authority

This document creates exactly one narrow authorization for a later Human-operated manual
observation and contribution. It is not evidence, evidence acceptance, a collector, a production
input API, a repository truth model, Product Intelligence ingestion, P7.4 or P7.5 construction,
market-test authorization, or commerce-action authority.

- Context ID: `p8-pilot-001-led-motion-tiktok-vn`
- Marketplace: **TikTok Shop Vietnam**
- External source ID: `1731381331718341815`
- Stable listing reference:
  `https://shop.tiktok.com/vn/pdp/den-led-cam-bien-chuyen-dong-3-che-do-sang-sac-usb-c/1731381331718341815`
- Identity scope: `SOURCE_IDENTITY_IS_NOT_CANONICAL_IDENTITY`

These values bind the authorization to one external listing. They do not establish canonical
product identity or current marketplace truth. Similar listings, title similarity, image
similarity, seller identity, URL slug text, product-concept similarity, search ranking, historical
cohorts, synthetic fixtures, and Human memory cannot substitute for exact-listing evidence.

P7.3 remains the sole owner of `DecisionContext` and `OpportunityHypothesis`; P7.4 remains the sole
owner of `TikTokAffiliateEvidenceProfile`; P7.5 remains the sole owner of VOI planning; P7.6 and
P7.7 retain market-test and winner-validation authority; P8.0 retains composition authority.
Product Intelligence remains the sole owner of `ProductCandidateSnapshot`, `SignalEvidence`,
discovery, scoring/ranking, approval, identity/catalog, persistence, and product-truth semantics.
P8.3 owns none of those semantics.

## 2. Exact authorized observation set

The ordered allowlist is exactly:

1. `variant_descriptor`
2. `current_price`
3. `original_price`
4. `discount_percent`
5. `affiliate_eligibility`
6. `affiliate_commission_rate`
7. `estimated_commission_value`
8. `sold_count`
9. `rating`
10. `review_count`
11. `inventory_availability`

Omission means unknown and unrepresented, never zero, false, unavailable, or absent. The source is
not claimed to expose every allowed observation, and this authorization does not claim that the
listing is affiliate-eligible.

For organization only, `current_price`, `original_price`, `discount_percent`,
`affiliate_eligibility`, `affiliate_commission_rate`, and `estimated_commission_value` are
candidate source observations relevant to the existing P7.4 `affiliate_economics` dimension.
`sold_count`, `rating`, and `review_count` are candidate source observations relevant to the
existing P7.4 `market_traction` dimension. `variant_descriptor` and
`inventory_availability` are provenance/context helpers, not new P7.4 dimensions. P8.3 does not
construct, interpret, score, normalize, or own any dimension.

Product/source facts and seller media are not required here and remain `DEFERRED` unless a fresh
Human/Brain VOI decision later justifies deeper manual Wave-1 product-source evidence. Wave 2
creator, content, audience, competition, and velocity capture is not authorized.

## 3. Human-only operating boundary

The authorized operation is ordinary Human interaction with Human-visible
`TIKTOK_SHOP_PDP` and `TIKTOK_AFFILIATE_UI` surfaces only. The Human may view the exact listing,
copy visible displayed values without interpretation, and prepare the external transport envelope
defined below.

There is no authority for AIOS, Codex, a parser fix, `TikTokDiscoveryAdapter`,
`TikTokSourceExtractor`, `TikTokScrapeTool`, browser/CDP automation, a marketplace API, scraper,
script, production mutation, background worker, watcher, scheduler, queue, automated retry, proxy,
stealth, evasion, bypass, or automated CAPTCHA handling. The current
`/vn/pdp/<slug>/<id>` parser incompatibility remains unchanged and does not block a Human who can
directly demonstrate the exact source identity.

A CAPTCHA or security challenge may be resolved manually by the Human/operator outside ordinary
AIOS verification. Automated solving, automated retry, proxy use, stealth, evasion, and bypass
remain forbidden. Resolving a challenge grants no additional acquisition, evidence, test, or
action authority.

## 4. External transport-only contribution envelope

The following is an inspectable carrier contract for a later Human operation. It must remain
outside the repository and ordinary AIOS deterministic verification until a future explicitly
authorized deterministic freeze. It must not be implemented as production code, a database, an
evidence store, a Product Intelligence model, or a repository truth model.

Fixed schema/version identifier: `manual-wave-1-evidence-contribution/v1`.
The envelope carries only the top-level and observation fields shown below; no extension or
free-form metadata field is authorized.

```yaml
schema: manual-wave-1-evidence-contribution/v1
context_id: p8-pilot-001-led-motion-tiktok-vn
source_id: "1731381331718341815"
stable_listing_reference: https://shop.tiktok.com/vn/pdp/den-led-cam-bien-chuyen-dong-3-che-do-sang-sac-usb-c/1731381331718341815
observed_at: "<Human-supplied timezone-aware timestamp>"
observations:
  - name: "<one exact allowed observation name>"
    displayed_value: "<bounded single-line text copied from the visible source>"
    source_surface: "<TIKTOK_SHOP_PDP or TIKTOK_AFFILIATE_UI>"
    binding_basis: "<exact visible source-ID, exact visible stable-URL, or direct-link destination basis>"
    artifact_ref: "<opaque safe provenance handle>"
    variant_context: "<optional bounded single-line visible variant context>"
```

`observed_at` must be one Human/operator-supplied RFC 3339 timestamp with an explicit UTC offset.
`observations` is ordered. Each item must use one allowlisted `name`; one non-empty
`displayed_value` of at most 500 Unicode scalar values copied from the visible source without
inference or normalization; one allowed `source_surface`; one `binding_basis` of at most 500
Unicode scalar values; one safe opaque `artifact_ref` of at most 300 Unicode scalar values; and,
only when useful, one `variant_context` of at most 200 Unicode scalar values. Those four textual
fields must each be single-line with no carriage return or line feed. Multiple items may cite the
same safe artifact. Artifact references are opaque provenance handles only and P8.3 must not
dereference, fetch, parse, or interpret them automatically. Omitted items remain unknown.

Conversational uploads, external files, screenshots, and staging artifacts do not become canonical
repository evidence by being supplied. Manual evidence staging remains external until explicit
Human review and a future deterministic freeze task.

## 5. Fail-closed exact-listing binding and artifact safety

Each observation may be considered for later Human review only when its `binding_basis`
demonstrates exact source identity through at least one of:

- the exact source ID `1731381331718341815` visibly present;
- the exact stable listing reference visibly present; or
- a direct product link whose visible destination contains exact source ID
  `1731381331718341815`.

Title-only, image-only, seller-only, slug-only, product-concept similarity, similar listings,
search ranking, or Human memory is insufficient. If exact binding cannot be demonstrated, the
observation remains unaccepted and unknown.

Every displayed value requires a safe artifact reference. Do not contribute cookies, tokens,
headers, credentials, raw HTML, browser-profile paths, QR/login codes, unnecessary account
identifiers, private messages, exception traces, or local absolute paths. Screenshots should be
cropped or redacted to the minimum product/economics/traction content required while retaining the
exact-listing binding and displayed-value context.

## 6. Separate Human review gate

Contribution is followed by a separate Human review. The reviewer evaluates every observation
individually for:

1. exact-listing binding;
2. timezone-aware observation time;
3. displayed-value transcription fidelity;
4. variant context where relevant;
5. artifact safety; and
6. usability only as source evidence.

For each observation the Human reviewer may record `ACCEPT`, `REJECT`, or `UNKNOWN`. `ACCEPT`
means only that the contributed item is usable as source evidence within the review boundary. It
does not create canonical truth, canonical identity, Product Intelligence approval, a P7.4
profile, a P7.5 plan or disposition, `TEST_READY`, a recommendation, a winner judgment, or test or
action authority. `REJECT` and `UNKNOWN` items must not be repaired, inferred, filled, relabeled,
or promoted into accepted evidence.

## 7. STOP, DEFER, and fresh-decision boundary

After contribution and review, Human/Brain must make a fresh decision. If affiliate eligibility,
commission/economics, or market-traction evidence is sufficient to stop or defer, do not authorize
Wave 0 or Wave 2 merely to complete fields. Missing fields remain unknown.

If decision-changing information is still justified, Human/Brain must freshly choose among Wave 0
compatibility work, deeper manual Wave-1 product-source evidence, Wave 2, or defining missing
Human-owned test constraints. Nothing progresses automatically, including P8.4 or a market test.

Budget, duration, exposure controls, contribution-margin threshold, success/failure criteria,
target audience, quality constraints, risk constraints, risk acceptance, and decision deadline
remain unset unless separately supplied by the Human. Marketplace observations cannot infer them.

Only after a concrete Human contribution and explicit Human review may a fresh deterministic task
be considered to freeze exactly the accepted safe evidence, bind it to existing P7.3 semantics,
and construct an existing P7.4 profile and/or P7.5 plan if separately justified. This statement
describes a possible successor boundary; it does not authorize that task, freeze, construction,
test, or action.

## 8. Publication-gated closure and handoff

On exact reviewed TASK-229 source publication, P8.3 becomes DONE only as
`MANUAL_WAVE_1_EVIDENCE_CONTRIBUTION_AUTHORIZATION_ONLY`. `real_pilot_executed` remains false;
TASK-229 claims no concrete task-acquired live evidence; `next_milestone` remains null; and
`pending_commitments` remains empty. The handoff destination is exactly
`HUMAN_OPERATOR_MANUAL_WAVE_1_CONTRIBUTION_AND_REVIEW`, with `automatic_next: false` and
`automatic_p8_4: false`.

P8.3 does not perform the manual operation, publish evidence, mutate production, authorize Wave 0
or Wave 2, construct P7.4/P7.5 values, authorize a market test, or select any future milestone.
