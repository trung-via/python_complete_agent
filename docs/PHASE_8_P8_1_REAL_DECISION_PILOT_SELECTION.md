# Phase 8 / P8.1 — Real Decision Pilot Selection

Status: **TASK-227 publication-gated DONE as `PILOT_CASE_SELECTION_ONLY`; no real pilot executed.**

Planning record identifier: `p8-pilot-001-led-motion-tiktok-vn`

Selection owner: **HUMAN**

## Purpose and classification

TASK-227 records one Human-selected real-commerce pilot case for later decision planning. It is
`PILOT_CASE_SELECTION_ONLY`. It is not real-pilot execution, evidence acquisition, Product
Intelligence approval, test authorization, affiliate participation, or commerce action. Selection
does not establish marketplace truth, readiness, a recommendation, a score or rank, a winner,
scalability, or causality.

P7.3 remains the sole semantic owner and constructor of `DecisionContext` and
`OpportunityHypothesis`. The framing below is intended caller-supplied input under that existing
authority; TASK-227 creates no duplicate constructor, model, or semantic owner. P7.4 remains the
sole owner of `TikTokAffiliateEvidenceProfile`; P7.5 remains the sole owner of VOI planning; P7.6
remains the sole owner of market-test evidence; P7.7 remains the sole owner of winner validation;
and P8.0 remains the sole composition owner.

## Human-selected listing

- Product selection label: **“Đèn LED Cảm Biến Chuyển Động Tự Động Bật Tắt Điều Chỉnh 3 Chế Độ Sáng”**
- Marketplace: **TikTok Shop Vietnam**
- Channel context: **TikTok Shop Affiliate planning context**
- External listing/source ID: `1731381331718341815`
- Stable listing reference:
  `https://shop.tiktok.com/vn/pdp/den-led-cam-bien-chuyen-dong-3-che-do-sang-sac-usb-c/1731381331718341815`

The ID and stable URL are source identity / an external listing reference only. **Source identity is
not canonical product identity (`SOURCE_IDENTITY_IS_NOT_CANONICAL_IDENTITY`).** The Human-supplied
product label is a selection label, not independently verified live marketplace truth. Query and
tracking parameters are deliberately excluded from the durable reference. The TikTok Shop
Affiliate channel is planning context only; this record does not claim that the exact listing is
currently affiliate-eligible.

## Intended P7.3 DecisionContext framing

- Proposed context identifier: `p8-pilot-001-led-motion-tiktok-vn`
- Decision question: “Should the Human authorize a bounded TikTok Shop affiliate market test for this exact selected listing after reviewing decision-relevant evidence?”
- Objective: “Reduce uncertainty enough for the Human to decide whether a bounded affiliate market test is justified, while preserving evidence gaps, alternatives, and action authority.”
- Market: **Vietnam**
- Channel: **TikTok Shop Affiliate**

No audience, deadline, budget, duration, economic threshold, exposure limit, risk threshold, or risk
acceptance has been supplied. This planning record does not invent one.

## Intended P7.3 OpportunityHypothesis framing

- Proposed hypothesis identifier: `p8-pilot-001-positive-contribution-margin`
- Bound context: `p8-pilot-001-led-motion-tiktok-vn`
- Bound listing reference:
  `https://shop.tiktok.com/vn/pdp/den-led-cam-bien-chuyen-dong-3-che-do-sang-sac-usb-c/1731381331718341815`
- Falsifiable claim: “Under an authorized bounded TikTok Shop affiliate market test, this exact selected listing can produce positive contribution margin without violating the Human-defined quality, exposure, economic, and risk constraints for that test.”

This is a hypothesis, not truth, approval, recommendation, Product Intelligence judgment, evidence,
or test authorization. It does not imply that the required Human-defined constraints exist yet.

## Initial important unknowns

The following remain explicitly unknown for this exact listing:

- current exact listing price and variant economics;
- affiliate commission rate and estimated commission value;
- current sold, review, and rating evidence;
- creator ecosystem;
- content activity and video evidence;
- audience-channel fit;
- competition saturation;
- inventory or availability where decision-relevant; and
- the Human-owned test design, exposure controls, success and failure criteria,
  contribution-margin threshold, budget, duration, and risk constraints.

**Unknown != absent. Unknown != authorization to collect.** Unknown does not authorize acquisition. Similar-
listing search results, URL slug text, historical benchmark cohorts, and synthetic fixtures cannot
fill these unknowns for the exact selected listing. No current price, shop, sold count, rating,
review count, commission, creator count, video count, velocity, contentability, audience fit,
competition state, stock, variant economics, or other live marketplace attribute is asserted here.
Existing adapters and scrape tools are capabilities, not authority to run them for this pilot.

## Publication boundary and handoff

On exact reviewed TASK-227 source publication, P8.1 is DONE as the explicit Human-selected
pilot-case selection commitment. `real_pilot_executed` remains false, `next_milestone` remains null,
and `pending_commitments` remains empty. No P8.2 or future domain is automatically selected,
authorized, marked NEXT, or made pending.

The next legitimate step is a fresh Human/Brain decision on a bounded **PRE-ACTION EVIDENCE
ACQUISITION PLAN** for this selected case. That later decision must determine which existing
authorities or tools, if any, may acquire which evidence and under what access, cost, latency,
fragility, and provenance constraints. It must not treat these unknowns as acquisition authority.

TASK-227 performs no browsing, fetching, scraping, collection, enrichment, scoring, ranking,
Product Intelligence approval, market action, test authorization, winner/scalability/causal
judgment, or future-domain selection. Human authorization remains required before any live evidence
acquisition or market-test action.
