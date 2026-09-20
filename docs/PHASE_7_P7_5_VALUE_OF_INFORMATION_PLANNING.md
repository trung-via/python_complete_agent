# Phase 7 P7.5 — Value-of-Information Planning

Status: **TASK-223 / P7.5 is publication-gated DONE. It becomes effective only
after canonical Runtime PASS, ChatGPT semantic PASS, and source-only publication
of the exact reviewed candidate. P7.6 Market Test / Funnel Evidence is the
single NEXT commitment after that publication.**

## 1. Authority and purpose

P7.5 establishes `COMMERCE_OPPORTUNITY_INTELLIGENCE_P7_5` in
`src/commerce_opportunity_intelligence/value_of_information.py` as the
canonical production semantic authority for Value-of-Information (VOI) planning
within the Commerce Opportunity Intelligence domain. It is subordinate to
Product Contract v2, the published P7.2 Winning Opportunity Semantic
Reconciliation, the published P7.3 Decision Context + Opportunity Hypothesis
authority, and the published P7.4 TikTok Affiliate Evidence Profile authority.

The authority owns two immutable, deterministic semantic values, one canonical
disposition enumeration, and one pure construction surface:

- `ValueOfInformationInquiry` represents one caller-authored information question
  tied to exactly one P7.4 evidence dimension, carrying explicit caller-supplied
  planning claims across all nine Product-Contract VOI considerations, one
  planning disposition (`CONTINUE`, `DEFER`, or `STOP`), and a bounded rationale.
- `ValueOfInformationPlan` composes an ordered sequence of inquiries bound to
  stable `plan_id`, exact `decision_context_id`, exact `hypothesis_id`, exact
  `profile_id`, and timezone-aware `as_of`, carrying one overall advisory
  disposition and rationale.
- `VALUE_OF_INFORMATION_DISPOSITIONS` defines the three ordered planning
  dispositions: `CONTINUE`, `DEFER`, and `STOP`.
- `create_value_of_information_plan` purely validates exact identity binding across
  `DecisionContext`, `OpportunityHypothesis`, and `TikTokAffiliateEvidenceProfile`
  without performing implicit identity, time, evidence quality, provider, network,
  or runtime inference.

## 2. Epistemic and decision boundaries

The following distinctions are explicit and non-negotiable:

- **missingness != acquisition authorization.** An unrepresented dimension or
  missing data field in P7.4 is not authorization to collect, scrape, query,
  browse, or fetch data.
- **collectability != value.** The technical ability to collect data is not by
  itself evidence that acquisition is worth its cost, latency, or risk.
- **planning claim != evidence truth.** Caller-supplied considerations (expected
  decision impact, uncertainty reduction, cost, latency, access risk, fragility,
  reliability, opportunity cost, and decision deadline) are forward-looking
  planning claims, not measured Product Truth.
- **VOI plan != collector plan.** A VOI plan reasons about information trade-offs
  relative to a material commerce decision; it does not route collectors, select
  providers, schedule jobs, or invoke APIs.
- **CONTINUE != authorization.** A `CONTINUE` disposition means only that
  further information remains worth considering under the stated context; it does
  not authorize collection or spend resources.
- **STOP != proof no evidence exists.** A `STOP` disposition means further
  acquisition for that inquiry or plan is not currently justified; it is not proof
  that information does not exist in the world.
- **DEFER != permanent rejection.** A `DEFER` disposition means acquisition is
  not justified now under current constraints; it preserves the inquiry without
  prematurely closing or executing it.
- **represented != sufficient.** The presence of evidence references in a P7.4
  dimension does not imply evidential sufficiency; represented dimensions remain
  fully eligible for caller-authored inquiries.
- **disposition != decision.** Advisory planning dispositions inform an owning
  decision boundary; they do not make commerce decisions or choose actions.
- **P7.5 != TEST_READY.** Planning that further evidence is worth considering does
  not establish `TEST_READY`, authorize market testing, or allocate budget.

No universal numeric VOI score, fixed cross-context weighting formula, automatic
evidence priority ranking, global threshold, winner score, or confidence score
exists in P7.5. Public projections contain no score, recommendation, decision,
rank, winner, acquisition order, or lifecycle state.

## 3. The Nine Product-Contract VOI Considerations

In alignment with Product Contract v2 (PC5), P7.5 models deeper evidence acquisition
relative to nine explicit caller-supplied planning claims:

1. **expected decision impact:** How and why the answer could alter the decision
   between alternatives.
2. **uncertainty reduction:** The degree to which the inquiry resolves critical
   unknowns.
3. **cost:** Direct computational, financial, or human operational acquisition costs.
4. **latency:** Time required to obtain the additional information.
5. **access risk:** Account, policy, legal, or platform exposure associated with acquisition.
6. **fragility:** Likelihood that the acquired signal changes, breaks, or expires rapidly.
7. **reliability:** Trustworthiness and provenance quality of the expected data source.
8. **opportunity cost:** Alternative analyses or actions foregone while pursuing this inquiry.
9. **decision deadline:** Temporal threshold after which additional information arrives
   too late to improve the decision.

## 4. Composition without re-ownership

Commerce Opportunity Intelligence is compositional:
- P7.3 owns `DecisionContext` and `OpportunityHypothesis`.
- P7.4 owns `TikTokAffiliateEvidenceProfile` organizing opaque evidence references.
- P7.5 composes those authorities into an inspectable `ValueOfInformationPlan`.

P7.5 operates as a pure value boundary: it introduces zero network, browser, CDP,
filesystem discovery, persistence, database, queue, background worker, provider/LLM
invocation, or AIOS lifecycle APIs.

## 5. Lineage and governance preservation

- TASK-222 / P7.4 is CLOSED / PUBLISHED at `ca6da00e9e58f66e25f2f6edcb416677bed70b6d`.
- TASK-215 / P7.3 is CLOSED / PUBLISHED at `dc4c4c8e6f3f4d6eb3441ff4873632e5f51655f9`.
- TASK-214 / P7.2 is CLOSED / PUBLISHED at `123bbb71d44ad15a25e07b07f21f6cb2dd00d20b`.
- TASK-191 / P7.1 is DONE / PUBLISHED at `40da098b3b0dcf3d1994fc510dd55717b81a2f67`.
- Governance Foundation lineage, Brain planning authority, and Human priority
  authority remain unchanged.
- Python Agent's active AIOS-renew authority remains the exact reviewed and published
  pin `edd7d8d92d54900c56442bbfcddb8648ec4d2e09`. P7.5 introduces no control-plane,
  worker, review, publication, adoption, or conformance authority.

## 6. Roadmap boundary

TASK-223 implements only P7.5 and is publication-gated DONE. After its exact
reviewed source is published, P7.6 Market Test / Funnel Evidence becomes the
single NEXT commitment. P7.7 Calibration & Winner Validation remains an ordered
NOT_DONE commitment. This document grants none of those future capabilities
implementation, acquisition, test, action, or decision authority.
