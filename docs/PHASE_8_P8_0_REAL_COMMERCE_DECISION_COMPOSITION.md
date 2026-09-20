# Phase 8 / P8.0 — Real Commerce Decision Loop Composition

Status: **TASK-226 publication-gated DONE. Composition contract frozen; no real pilot executed.**

Authority identifier: `COMMERCE_DECISION_LOOP_P8_0`

Semantic owner: `src/commerce_decision_loop/real_decision_composition.py`

## Purpose and authority

P8.0 provides one pure composition boundary for an inspectable commerce decision-loop
case. It binds exact, already-owned P7.3 through P7.7 artifacts and external opaque
decision lineage without copying or merging their authorities. Its only authority is
exact cross-domain composition lineage and deterministic representation-gap reporting.

P8.0 owns no underlying evidence, Product Intelligence, commerce-opportunity
intelligence, Human decision, approval, action, outcome, attribution, product truth,
roadmap choice, or future intelligence-domain semantics. **Composition != authority.**

`CommerceDecisionLoopCase` is immutable and factory-only. A caller supplies a stable
`case_id`, exact `DecisionContext` and `OpportunityHypothesis`, and a timezone-aware
`as_of`. The factory rejects mismatched context/hypothesis lineage. The mandatory P7.3
foundations are not optional loop components.

## Exact optional component order

1. `TIKTOK_AFFILIATE_EVIDENCE`
2. `VALUE_OF_INFORMATION_PLAN`
3. `DECISION_AUTHORIZATION`
4. `MARKET_TEST_EVIDENCE`
5. `WINNER_VALIDATION_ASSESSMENT`

`represented_components` and `unrepresented_components` partition exactly this list in
this order. They report only whether an exact artifact or opaque reference was supplied.
**Representation != sufficiency. Missing component != authorization to build it.** The
gap view is not a score, confidence, readiness judgment, lifecycle state,
recommendation, automatic successor, or future-domain selector.

## Binding rules

- A P7.4 `TikTokAffiliateEvidenceProfile` must exactly match the P7.3 context and
  hypothesis and cannot postdate the case.
- A P7.5 `ValueOfInformationPlan` requires and exactly binds the supplied P7.4 profile,
  P7.3 foundations, and case time. Its disposition remains advisory. **VOI `CONTINUE`
  != authorization**, and no VOI disposition is an action or test gate.
- `decision_authorization_ref` is one bounded, single-line, opaque reference to authority
  owned elsewhere. P8.0 does not dereference it, validate its legitimacy, infer its actor,
  or grant authority. **decision_authorization_ref != decision authority.**
- Ordered P7.6 `MarketTestEvidenceProfile` values require that reference, must have
  unique IDs, must exactly match context, hypothesis, authorization lineage, and time,
  and retain caller order. A VOI plan is not required. **Action lineage != action
  authority. Outcome != attribution.**
- A P7.7 `WinnerValidationAssessment` requires the exact ordered P7.6 profile IDs and
  exact context, hypothesis, and time binding. `SUPPORTED`, `CONTRADICTED`, and
  `INCONCLUSIVE` remain bounded P7.7 interpretations. **Winner assessment != decision**;
  it is not approval, action, causality, scalability, or roadmap authority.

The public projection includes only bounded lineage IDs/references, ISO-8601 `as_of`,
and the ordered component partition. It is deterministic and JSON-serializable. Blank,
multiline, overlong, secret/cookie/session, model-prompt, execution-metadata, raw-HTML,
object-representation, and memory-address payloads fail closed.

## Publication and pilot boundary

TASK-226 freezes this composition contract. Its deterministic fixtures are synthetic
verification inputs: **synthetic fixture != real pilot**. They are not live marketplace
evidence, a Human decision, an authorized intervention, a market-test result, or proof
that any real commerce decision loop has run. **Composition completeness != real-world
success.**

The P7 sequence remains DONE through TASK-225 candidate
`6302dd7d01be90624d5ed0072cffbc3c23f2e4a2`. P8.0 becomes DONE only when the safe
Publisher publishes the exact reviewed TASK-226 source candidate. There is no automatic
P8.1 or other successor. P8.0 does not select Media/Creative Intelligence, Distribution
Intelligence, Commerce Operations Intelligence, evidence acquisition, Product
Intelligence rework, or another future domain. One later real pilot requires a fresh
Human/Brain selection of the actual commerce decision case and legitimate external
decision/action lineage before any domain branch is authorized. Runtime, workers, gap
reports, component presence, and assessment dispositions cannot make that selection.

The AIOS control-plane history and exact downstream pin
`edd7d8d92d54900c56442bbfcddb8648ec4d2e09` / TASK-207 revision 8 conformance remain
unchanged.
