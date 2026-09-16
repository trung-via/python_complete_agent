# Phase 7 P7.3 — Decision Context + Opportunity Hypothesis

Status: **TASK-215 / P7.3 is publication-gated DONE. It becomes effective only
after canonical Runtime PASS, ChatGPT semantic PASS, and source-only publication
of the exact reviewed candidate. P7.4 TikTok Affiliate Evidence Profile is the
single NEXT commitment after that publication.**

## 1. Authority and purpose

P7.3 establishes `COMMERCE_OPPORTUNITY_INTELLIGENCE_P7_3` in
`src/commerce_opportunity_intelligence/decision_context.py` as the first bounded
production semantic authority of the Commerce Opportunity Intelligence domain.
It is subordinate to Product Contract v2 and the published P7.2 Winning
Opportunity Semantic Reconciliation.

The authority owns only two immutable, deterministic semantic values and one
pure construction surface:

- `DecisionContext` preserves one decision question, objective, caller-supplied
  as-of time, and any explicitly supplied market, audience, channel, horizon,
  deadline, constraints, alternatives, economics, and risk context.
- `OpportunityHypothesis` preserves one explicit falsifiable claim about one
  opaque subject reference, tied to exactly one DecisionContext identifier, with
  caller-supplied identity and time, assumptions, supporting and counter-evidence
  references, important unknowns, disconfirming conditions, and expected outcomes.
- `create_opportunity_hypothesis` validates exact context binding and constructs
  the value only from caller-supplied inputs.

Optional context remains absent when it is not supplied. No market observation,
score, model response, environment value, wall clock, generated UUID, or
marketplace metadata fills it implicitly. Ordered collections preserve caller
order, and JSON-serializable projections use ISO-8601 timestamps.

## 2. Epistemic and decision boundaries

The following distinctions are explicit and non-negotiable:

- **DecisionContext != Decision.** Context records the situation in which an
  authorized decision may later be made. It contains no approval, rejection,
  selected winner, score, confidence probability, recommended action, execution
  authority, Human priority, or inferred risk acceptance.
- **OpportunityHypothesis != Truth.** A hypothesis is a claim that evidence can
  support, contradict, or disconfirm. Construction does not establish Product
  Truth, canonical identity, commercial success, or scientific sufficiency.
- **Evidence reference != evidence ownership.** Supporting and counter-evidence
  values are opaque references to evidence owned elsewhere. P7.3 neither creates
  nor normalizes evidence, dereferences it, infers provenance, adjudicates
  conflicts, or upgrades it into knowledge or truth.
- **Hypothesis != recommendation.** The existence or apparent support of a
  hypothesis recommends no action and ranks no hypothesis or alternative.
- **Product Candidate Triage score/rank != opportunity judgment.** Existing
  `WinningProductScorer` and `CandidateRanker` behavior remains Product Candidate
  Triage V1 and is unchanged. P7.3 neither calls nor re-exports it.
- **Opportunity hypothesis != TEST_READY.** A P7.3 value is not proof of test
  readiness and creates no test design, workflow transition, or promotion.
- **Observed later outcome != causal attribution.** Sequence or association does
  not establish that an action caused an outcome.
- **One favorable outcome != scalable winner.** Scalability requires later,
  separately authorized evidence and judgment appropriate to expansion.

Falsifiability is structural but bounded. At least one non-empty disconfirming
condition is required. P7.3 does not judge whether it is scientifically adequate.
A hypothesis may have no supplied supporting or counter-evidence references at
creation; an empty collection means only that none were supplied, not that
evidence exists or does not exist in the world.

## 3. Composition without re-ownership

Commerce Opportunity Intelligence is compositional. A caller may select an
opaque subject reference that points to a discovered product candidate or to a
later authorized commerce subject. The string grants no source identity,
canonical identity, platform, URL, family, variant, catalog membership, approval,
or Product Truth claim.

Likewise, a caller may supply references to evidence produced by canonical domain
authorities. Those authorities retain evidence creation, provenance, temporal
meaning, uncertainty, and truth boundaries. Composition does not silently mutate
Product Intelligence state, canonical product truth, Human approval, or any
future test, action, persistence, or lifecycle authority.

P7.3 creates no marketplace acquisition, provider or model invocation, browser,
network, persistence, database, queue, service, worker, autonomous agent loop,
scoring, ranking, recommendation, Value-of-Information planning, TikTok affiliate
profile, test execution, outcome validation, calibration, or scalability
authority.

## 4. P7.2 lifecycle preservation

P7.2's five names remain conceptual reasoning semantics only:
DISCOVERED_CANDIDATE -> OPPORTUNITY_HYPOTHESIS -> TEST_READY ->
VALIDATED_WINNER -> SCALABLE_WINNER. P7.3 does not encode them as an Enum, stored
status, workflow state, decision band, automatic transition, or auto-advance
mechanism. The Python presence of an `OpportunityHypothesis` establishes only
the bounded P7.3 artifact.

TASK-191 remains immutable P7.1 measurement history at
`40da098b3b0dcf3d1994fc510dd55717b81a2f67`. TASK-214/P7.2 is CLOSED / PUBLISHED
at `123bbb71d44ad15a25e07b07f21f6cb2dd00d20b`. Governance Foundation lineage,
Brain planning authority, Human priority authority, and the exact AIOS-renew pin
`91a177d5b96b2197a4d8223dbb727dda6201cb64` remain unchanged.

## 5. Roadmap boundary

TASK-215 implements only P7.3 and is publication-gated DONE. After its exact
reviewed source is published, P7.4 TikTok Affiliate Evidence Profile becomes the
single NEXT commitment. P7.5 Value-of-Information Planning, P7.6 Market Test /
Funnel Evidence, and P7.7 Calibration & Winner Validation remain ordered
NOT_DONE commitments. This document grants none of those future capabilities
implementation, acquisition, test, action, or decision authority.
