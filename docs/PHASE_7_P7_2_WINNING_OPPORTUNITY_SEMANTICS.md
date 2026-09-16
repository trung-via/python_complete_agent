# Phase 7 P7.2 — Winning Opportunity Semantic Reconciliation

Status: **TASK-214 / P7.2 is publication-gated DONE. It becomes effective only
after canonical Runtime PASS, ChatGPT semantic PASS, and source-only publication
of the exact reviewed candidate. P7.3 Decision Context + Opportunity Hypothesis
is the single NEXT commitment.**

## 1. Authority and purpose

This document is subordinate to the current Product Contract v2. It records the
approved P7 interpretation needed to continue product work without duplicating
or replacing that durable authority.

A **Winning Opportunity** is not an intrinsic fact about a product. It is a
decision-relative, time-bounded commerce opportunity hypothesis: an inspectable
claim that a product, in a particular context and under material uncertainty,
may outperform relevant alternatives for an authorized objective.

The relevant context may include the customer or audience need, product, offer,
channel, creative or content, economics, timing, execution and operations,
objective, constraints, alternatives, risk, and uncertainty. Which dimensions
matter, and how much, depends on the decision. This is not a universal formula,
mandatory schema, fixed weighting system, global commerce score, or autonomous
selection rule.

## 2. Conceptual opportunity lifecycle

P7 uses exactly five conceptual reasoning stages:

1. **DISCOVERED_CANDIDATE** — an observed product candidate is eligible for
   bounded triage; discovery is not an opportunity conclusion.
2. **OPPORTUNITY_HYPOTHESIS** — an explicit decision context, objective,
   alternatives, assumptions, supporting and contrary evidence, uncertainty,
   and falsifiable opportunity claim have been stated.
3. **TEST_READY** — the hypothesis has enough decision-relevant evidence and an
   authorized test design, success/failure criteria, constraints, and exposure
   controls to justify a market test.
4. **VALIDATED_WINNER** — authorized observed funnel, economic, and quality
   outcomes appropriate to the decision support the bounded hypothesis. The
   result remains conditional on its tested context and time period.
5. **SCALABLE_WINNER** — repeated or otherwise adequate evidence supports a
   separate conclusion that the opportunity can be expanded while preserving
   required economics, quality, operational feasibility, and risk bounds.

These names are reasoning semantics only. They are not a persisted enum, state
machine, workflow gate, database status, API contract, or authority to advance a
candidate automatically. Movement between concepts requires evidence and the
legitimate decision authority; it is never inferred from presentation labels.

## 3. Product Candidate Triage V1 boundary

The existing `WinningProductScorer`, `CandidateRanker`, `ScoringPolicy`, category
weights, thresholds, decision bands, and names remain unchanged. Together they
are bounded here as **Product Candidate Triage V1**: deterministic prioritization
of a bounded candidate set for deeper attention and resources under the existing
policy.

Product Candidate Triage V1 is not a universal market-winner predictor, a
complete Winning Opportunity judgment, Product Truth, Human approval, or a
substitute for decision context and testing. Its score and rank may inform the
DISCOVERED_CANDIDATE stage, but cannot by themselves establish any later stage.
Renaming, reweighting, or replacing V1 requires separately authorized outcome
evidence; P7.2 provides no such evidence and makes no production-code change.

## 4. Pre-test evidence domains

Before a test, an opportunity hypothesis may draw on these evidence domains:

- market pull and unmet demand;
- momentum and timing;
- product quality and trust;
- audience and creator fit;
- offer and economics;
- creative and content leverage;
- competition, content gap, and differentiation; and
- operational feasibility.

Their relevance is contextual. The list is neither a set of mandatory fields
nor fixed score categories or weights. Evidence must retain source provenance,
observation time, semantic type, uncertainty, assumptions, conflicts, and
material counter-evidence. Missingness identifies an unknown; it does not by
itself authorize collection, enrichment, a new provider, or a changed score.

Additional acquisition is justified only when its expected Value of Information
for the decision warrants its cost, latency, reliability, access risk,
fragility, opportunity cost, and deadline. P7.2 selects no evidence collector,
marketplace path, or enrichment implementation.

## 5. Pre-test and post-test boundary

Pre-test outputs remain hypotheses and test-readiness judgments. Search-card
observations, domain evidence, scores, ranks, model explanations, forecasts, and
confidence do not validate a winner.

Validation requires authorized observed funnel, economic, and quality outcomes
appropriate to the decision and interpreted against the test design, exposure,
alternatives, constraints, and time window. Outcomes must preserve provenance
and uncertainty. An outcome is not causal attribution: association, sequence,
or post-hoc explanation cannot establish that the tested action caused it.

One favorable result does not establish scalability. A VALIDATED_WINNER remains
bounded to the tested context; SCALABLE_WINNER requires separately adequate
evidence about expansion, repeatability, economics, quality, operations, and
risk. Unfavorable or ambiguous results likewise become evidence rather than a
retroactive rewrite of what was known or reasonably decided before the test.

## 6. TASK-191 immutable measurement history

TASK-191 remains the immutable P7.1 checkpoint at
`40da098b3b0dcf3d1994fc510dd55717b81a2f67`. Its fifteen accepted Shopee
search-card candidates produced `INSUFFICIENT_DATA` with zero coverage across
every current Winning Product V1 category.

That result proves only that the bounded search-card surface is insufficient for
the current scorer on that frozen cohort. It does not prove commercial failure,
that every missing field must be collected, that Product Candidate Triage V1
weights or thresholds are wrong, or that any enrichment path has priority or
authority. P7.2 preserves the fixture, report, task, provenance, and historical
interpretation unchanged.

## 7. Approved P7 sequence and boundaries

P7 is the active product track. The Human-approved order is:

1. **P7.2 Winning Opportunity Semantic Reconciliation — TASK-214,
   publication-gated DONE**;
2. **P7.3 Decision Context + Opportunity Hypothesis — NEXT**;
3. **P7.4 TikTok Affiliate Evidence Profile — NOT_DONE**;
4. **P7.5 Value-of-Information Planning — NOT_DONE**;
5. **P7.6 Market Test / Funnel Evidence — NOT_DONE**; and
6. **P7.7 Calibration & Winner Validation — NOT_DONE**.

Only P7.3 is NEXT after P7.2 becomes publication-effective. P7.4 through P7.7
are ordered future commitments, not implementations, approvals, or permission
to collect data. No step auto-advances from Runtime, worker, score, measurement,
or roadmap state. The roadmap remains BRAIN-owned, is not engineering truth, and
priority changes remain Human-owned.

P7.2 changes no discovery, approval, evidence, identity, catalog, retrieval,
truth, scorer, ranker, test, or production authority. The exact AIOS-renew pin
and all Governance Foundation, TASK-191, and TASK-213 provenance remain
unchanged.
