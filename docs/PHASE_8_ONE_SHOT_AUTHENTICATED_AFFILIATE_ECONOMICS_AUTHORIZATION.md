# Phase 8 one-shot authenticated Affiliate economics authorization

TASK-267 revision 1 is `ONE_SHOT_AUTHENTICATED_AFFILIATE_ECONOMICS_AUTHORIZATION_ONLY`. Human/Brain authorizes one later Human-operated lookup attempt **only after exact reviewed TASK-267 publication**. TASK-267 performs no login, marketplace interaction, live acquisition, contribution, review of live values, evidence ingestion, or commerce action. The authority follows exact reviewed TASK-266 revision 1 / RUN-266-002 / REVIEW-266-001, published at `96016e7601ae5d8b45d42376b4a16686abf0e15b`.

## Exact case and observation authority

- `context_id`: `p8-pilot-001-led-motion-tiktok-vn`
- `source_id`: `1731381331718341815`
- `stable_listing_reference`: `https://shop.tiktok.com/vn/pdp/den-led-cam-bien-chuyen-dong-3-che-do-sang-sac-usb-c/1731381331718341815`
- Identity boundary: `SOURCE_IDENTITY_IS_NOT_CANONICAL_IDENTITY`.
- `authorized_authenticated_lookup_attempts: 1`; `authorized_authenticated_lookup_attempts_remaining: 1`; `lookup_execution_owner: HUMAN_OPERATOR`; `lookup_executed: false` at publication.
- `authenticated_affiliate_lookup_authority: ONE_SHOT_EXACT_LISTING_THREE_FIELD_ONLY` effective only after exact reviewed publication.

The **entire ordered observation allowlist** is `affiliate_eligibility`, `affiliate_commission_rate`, and `estimated_commission_value`. The authoritative source for every contributed value is the Human-visible authenticated `TIKTOK_AFFILIATE_UI` creator-affiliate surface. The public PDP is at most an auxiliary, non-authoritative identity reference and cannot establish these values. Omission or non-display is `UNKNOWN` / `NOT_ESTABLISHED`, never a zero, false, or inferred value. This does not reopen historical TASK-229/P8.3's broader 11-field Wave-1 scope.

The Human/operator may manually navigate only as needed to locate this exact source ID or stable listing reference in the authenticated Affiliate surface. There is no general search, discovery, batch, related-product, recommendation-feed, other-listing, or broader Wave-1 authority. Each reviewable observation must have an inspectable binding basis tied to the authenticated observation: exact source ID visibly present; exact stable listing reference visibly present; or a direct product-link destination visibly containing `1731381331718341815`. Title, image, seller, slug, product-concept similarity, and Human memory do not bind the listing. If the exact listing cannot be located or exactly bound, fail closed without substitution.

## External transport-only envelope

The following schema is an external Human transport contract, not a production model, repository schema authority, evidence owner, canonical truth object, or automatic ingestion surface. The top-level keys are exactly those shown. `observations` is ordered, contains only the three allowlisted names, and may omit names that were not displayed. Each item has exactly the five required keys shown and may add only `variant_context`; multiple items may cite one artifact.

```yaml
schema: authenticated-affiliate-economics-one-shot/v1
context_id: p8-pilot-001-led-motion-tiktok-vn
source_id: "1731381331718341815"
stable_listing_reference: https://shop.tiktok.com/vn/pdp/den-led-cam-bien-chuyen-dong-3-che-do-sang-sac-usb-c/1731381331718341815
observed_at: "<one Human-supplied timezone-aware RFC 3339 timestamp with explicit UTC offset>"
attempt_number: 1
operation_status: "<SUCCESS | FAIL_CLOSED | INCONCLUSIVE>"
observations:
  - name: affiliate_eligibility
    displayed_value: "<verbatim visible authenticated display>"
    source_surface: TIKTOK_AFFILIATE_UI
    binding_basis: "<inspectable exact-listing basis tied to this observation>"
    artifact_ref: "<safe opaque provenance handle>"
    variant_context: "<optional visible variant context>"
```

The example observation is a field-shape placeholder, not a claim that the value exists. `attempt_number` must be `1`. `observed_at` is one Human/operator-supplied RFC 3339 timestamp with an explicit UTC offset. `displayed_value` must be copied from the visible authenticated source without interpretation, normalization, arithmetic, or inference. `displayed_value` and `binding_basis` are non-empty single-line text of at most 500 Unicode scalar values; `artifact_ref` is a non-empty safe opaque single-line handle of at most 300; optional `variant_context` is single-line text of at most 200. No extra fields, additional observation names, or source surfaces are authorized. An empty `observations` list is valid for a failed or inconclusive attempt; omissions remain unknown.

Every contributed observation needs safe artifact provenance. Screenshots should be cropped or redacted to the minimum exact-listing Affiliate economics content needed to retain binding and displayed-value context. Do not persist credentials, cookies, tokens, headers, raw HTML, QR/login codes, browser profile paths, unrelated account identity, private messages, exception traces, or local absolute paths. Artifact references remain opaque; TASK-267 does not fetch or parse them. External screenshots and envelopes remain outside canonical repository truth.

## Attempt consumption, Human review, and closure

The one attempt is consumed by the Human operation, including blocked access, unavailable listing, failed binding, or unavailable UI values. `SUCCESS` means only that at least one displayed, exactly bound observation is reviewable; it does not mean eligibility, positive economics, acceptance, readiness, or business success. Record `FAIL_CLOSED` when access or exact binding prevents reviewable contribution, and `INCONCLUSIVE` when the exact listing is bound but required values are not exposed or the attempt otherwise cannot resolve the question. No automatic or implied retry exists; another attempt needs fresh Human/Brain authorization.

Human login, session preparation, CAPTCHA, and security-challenge handling stay external and manual. There is zero authority for automatic credential capture, login, CAPTCHA solving, retry, proxy, stealth, evasion, bypass, background waiting, browser/CDP automation, API call, scraper, scheduler, or agent operation. AIOS engineering and Runtime verification remain deterministic and offline.

After the operation, mandatory Human review assesses **each** contributed observation independently for exact-listing binding, observation time, transcription fidelity, artifact safety, and usability as source evidence. The per-observation disposition is `ACCEPT`, `REJECT`, or `UNKNOWN`. `ACCEPT` means only usable source evidence: `SOURCE_EVIDENCE_IS_NOT_CANONICAL_TRUTH`. Neither contribution nor review constructs P7.3 DecisionContext/OpportunityHypothesis, P7.4 TikTokAffiliateEvidenceProfile, P7.5 ValueOfInformationPlan or disposition, P7.6 MarketTestEvidenceProfile, P7.7 WinnerValidationAssessment, P8.0 CommerceDecisionLoopCase, ProductCandidateSnapshot, SignalEvidence, canonical identity, Product Intelligence approval, `TEST_READY`, recommendation, winner judgment, or action authority. Those owners retain their existing boundaries. Rejected/unknown items are not inferred or promoted.

TASK-266's ten Human-owned planning input names and their values remain exactly as published: 5,000,000 VND budget hard ceiling; 14 days; initial at-risk tranche 750,000 VND with mandatory Human/Brain review before more exposure; creator/affiliate cumulative settled contribution margin `GT_0_VND`; target audience `người trẻ có thời lượng sử dụng mạng xã hội cao`; 15 percent / 750,000 VND maximum accepted economic loss; day-7 checkpoint and day-14 final review; and the published success/failure criteria. `quality_constraints: UNSET` and `risk_constraints: UNSET` still block later market-test authorization. Affiliate eligibility, commission rate, estimated commission, actual settled commission, refunds, and attributable costs remain unestablished at publication. `affiliate_economics: NOT_ESTABLISHED`, `MARKET_TEST_READINESS_NOT_ESTABLISHED`, `canonical_evidence_ingested: false`, and `market_test_or_action_authority: NONE` remain.

Historical TASK-264 through TASK-266 observations, provenance, screenshot restrictions, consumed one-shot captures, failed/repaired RUN lineage, and closed authorities remain unchanged. On exact reviewed TASK-267 publication, the sole planning/operation handoff is `HUMAN_OPERATOR_ONE_SHOT_AUTHENTICATED_AFFILIATE_ECONOMICS_LOOKUP_AND_REVIEW`. `next_milestone: null`, `pending_commitments: []`, `post_run_engineering_successor: null`, and `automatic_progression: false`; no TASK-268 is preselected. Only after a concrete Human operation and explicit Human review may Human/Brain consider a separately authorized deterministic freeze/replay/semantic-construction task. This authorization does not select or start one and grants no market test, spend, traffic, campaign, affiliate participation, content, outreach, inventory/price change, or other commerce action.
