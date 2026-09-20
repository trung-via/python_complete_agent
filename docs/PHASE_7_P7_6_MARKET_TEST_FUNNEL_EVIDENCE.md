# Phase 7 P7.6 — Market Test / Funnel Evidence

Status: **TASK-224 / P7.6 is publication-gated DONE. It becomes effective only
after canonical Runtime PASS, ChatGPT semantic PASS, and source-only publication
of the exact reviewed candidate. P7.7 Calibration & Winner Validation is the
single NEXT commitment after that publication.**

## 1. Authority and purpose

P7.6 establishes `COMMERCE_OPPORTUNITY_INTELLIGENCE_P7_6` in
`src/commerce_opportunity_intelligence/market_test_evidence.py` as the
canonical production semantic authority for market test and funnel outcome
evidence within the Commerce Opportunity Intelligence domain. It is subordinate
to Product Contract v2, the published P7.2 Winning Opportunity Semantic
Reconciliation, the published P7.3 Decision Context + Opportunity Hypothesis
authority, the published P7.4 TikTok Affiliate Evidence Profile authority, and
the published P7.5 Value-of-Information Planning authority.

The authority owns one immutable, deterministic semantic value, one canonical
dimension enumeration, and one pure construction surface:

- `MarketTestEvidenceProfile` represents one post-intervention evidence envelope
  bound to stable `profile_id`, stable `test_id`, exact `decision_context_id`,
  and exact `hypothesis_id`. It carries mandatory opaque lineage references
  (`test_design_ref`, `authorization_ref`, `action_ref`), explicit timezone-aware
  timestamps (`test_started_at`, `test_ended_at`, `as_of`), and four ordered
  evidence dimensions (`exposure_evidence_refs`, `funnel_evidence_refs`,
  `economic_evidence_refs`, `quality_evidence_refs`).
- `MARKET_TEST_EVIDENCE_DIMENSIONS` defines the four ordered evidence dimensions:
  `exposure_evidence_refs`, `funnel_evidence_refs`, `economic_evidence_refs`,
  and `quality_evidence_refs`.
- `create_market_test_evidence_profile` purely validates exact identity binding
  between `DecisionContext` and `OpportunityHypothesis`, verifies time-window
  consistency (`test_started_at <= test_ended_at <= as_of`), enforces reference
  uniqueness within each dimension, and guarantees at least one supplied evidence
  reference across the profile without performing implicit network, provider,
  marketplace, persistence, or runtime actions.

## 2. Epistemic and decision boundaries

The following distinctions are explicit, mandatory, and non-negotiable:

- **evidence profile != test authorization.** Storing an evidence profile does
  not grant authority to design, schedule, approve, or execute an intervention.
- **test_design_ref != test-design authority.** The opaque `test_design_ref`
  records lineage to caller-supplied test specifications; P7.6 does not define,
  evaluate, or approve test criteria or methodology.
- **authorization_ref != approval.** An `authorization_ref` is an opaque pointer
  to an external authorization record; its presence does not mean P7.6 granted,
  verified, or endorsed test authorization.
- **action_ref != action authority.** An `action_ref` is an opaque lineage
  reference to an intervention that occurred; P7.6 does not initiate, manage, or
  execute actions.
- **represented != sufficient.** The presence of evidence references in an
  evidence dimension indicates caller-supplied coverage only, not evidential
  quality, completeness, or decision sufficiency.
- **unrepresented != zero/failure.** An empty evidence dimension indicates that
  no evidence was supplied for that dimension in this profile; it does not mean
  zero outcome, test failure, or absence of evidence in the world.
- **outcome != attribution.** Observed post-action data constitutes outcome
  evidence, not causal attribution or statistical proof of treatment effect.
- **outcome != retroactive proof.** A favorable observed outcome does not
  retroactively prove that the prior hypothesis, context, or decision was correct.
- **measurement != winner.** Measuring post-intervention funnel, economic, or
  quality evidence does not declare a candidate a winner.
- **one favorable test != scalable winner.** A favorable result from a single
  market test does not establish a scalable, sustainable, or repeatable winner.
- **P7.6 != P7.7.** P7.6 organizes bounded post-action evidence references; it
  does not perform P7.7 calibration, winner validation, causal inference,
  scorer reweighting, or policy learning.
- **P7.5 disposition != workflow gate.** P7.5 `CONTINUE`, `DEFER`, or `STOP`
  dispositions remain advisory planning inputs; they are not mandatory
  workflow blockers or authorization prerequisites for P7.6 evidence profiles.
- **single deadline authority.** Canonical decision deadline authority belongs
  exclusively to P7.3 `DecisionContext.decision_deadline`. P7.6 timestamps
  (`test_started_at`, `test_ended_at`, `as_of`) describe the intervention
  window and profile time only; they never duplicate, copy, reinterpret, or own
  the decision deadline.

No success score, funnel score, uplift score, pass/fail result, approval state,
TEST_READY state, VALIDATED_WINNER state, or SCALABLE_WINNER state exists in P7.6.
Public projections contain no scores, recommendations, rankings, or lifecycle transitions.

## 3. The Four Evidence Dimensions

P7.6 organizes caller-supplied opaque references across exactly four ordered
semantic dimensions:

1. **exposure_evidence_refs:** Observations of test delivery, impression volume,
   reach, spend, duration, and audience presentation.
2. **funnel_evidence_refs:** Observations of user engagement, click-through,
   add-to-cart, checkout initiation, conversion, or drop-off through the funnel.
3. **economic_evidence_refs:** Observations of revenue, cost, margin, return on
   ad spend, commission payout, or unit economic performance.
4. **quality_evidence_refs:** Observations of product returns, user feedback,
   ratings, complaint rates, creator feedback, or policy compliance.

Rules for evidence dimensions:
- Each dimension is an ordered sequence of bounded opaque string references.
- Caller-supplied ordering within each dimension is strictly preserved.
- Duplicate references within the same dimension are rejected.
- The same opaque reference may intentionally appear across multiple dimensions
  when one observation provides evidence for distinct semantic dimensions.
- A profile must contain at least one evidence reference across the four dimensions.

## 4. Composition without re-ownership

Commerce Opportunity Intelligence remains compositional and modular:
- P7.3 owns `DecisionContext` and `OpportunityHypothesis`, including the canonical
  decision deadline.
- P7.4 owns `TikTokAffiliateEvidenceProfile` organizing pre-test affiliate signals.
- P7.5 owns `ValueOfInformationPlan` evaluating advisory information acquisition trade-offs.
- P7.6 establishes `MarketTestEvidenceProfile` to organize post-intervention outcome evidence.
- P7.6 binds to exact P7.3 `context_id` and `hypothesis_id` without requiring P7.4 or P7.5.
- P7.6 operates as a pure value boundary: zero network, browser, CDP, filesystem discovery,
  persistence, database, queue, background worker, provider/LLM invocation, or AIOS lifecycle APIs.

## 5. Lineage and governance preservation

- TASK-223 / P7.5 is CLOSED / PUBLISHED at `3c67a828857f74466883463abf35a17ecdcc6775`.
- TASK-222 / P7.4 is CLOSED / PUBLISHED at `ca6da00e9e58f66e25f2f6edcb416677bed70b6d`.
- TASK-215 / P7.3 is CLOSED / PUBLISHED at `dc4c4c8e6f3f4d6eb3441ff4873632e5f51655f9`.
- TASK-214 / P7.2 is CLOSED / PUBLISHED at `123bbb71d44ad15a25e07b07f21f6cb2dd00d20b`.
- TASK-191 / P7.1 is DONE / PUBLISHED at `40da098b3b0dcf3d1994fc510dd55717b81a2f67`.
- Governance Foundation lineage, Brain planning authority, and Human priority
  authority remain unchanged.
- Python Agent's active AIOS-renew authority remains the exact reviewed and published
  pin `edd7d8d92d54900c56442bbfcddb8648ec4d2e09`. P7.6 introduces no control-plane,
  worker, review, publication, adoption, or conformance authority.

## 6. Roadmap boundary

TASK-224 implements only P7.6 and is publication-gated DONE. After its exact
reviewed source is published, P7.7 Calibration & Winner Validation becomes the
single NEXT commitment. P7.7 remains an ordered NOT_DONE commitment before that
publication. This document grants no calibration, winner validation, causal inference,
or test execution authority.
