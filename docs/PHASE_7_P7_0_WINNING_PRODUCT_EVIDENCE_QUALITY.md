# Phase 7 P7.0 — Winning Product Evidence Quality

Status: **CLOSED / PUBLISHED. TASK-181 received canonical Runtime PASS in
RUN-181-001 and ChatGPT semantic-review PASS in REVIEW-181-001 on source
candidate `9e835ed2c551c2fa3a8b66b82caa238bd41b152c`. TASK-182 / P7.1 is the
separate real-evidence coverage baseline gate.**

## 1. Audit decision

P6.0, P6.1, and P6.3 are CLOSED. P6.2 remains PARKED and reopenable only from
new retrieval evidence. P6.4 identity evolution, P6.5 higher-level Human-review
assistance, and P6.6 caches/background serving remain DEFERRED / UNIMPLEMENTED.

The fresh architecture/value audit selects a separately justified Product
Intelligence branch, **P7 Commerce Opportunity Intelligence**, rather than
automatically opening P6.4. The current measurable gap lies inside the existing
M2 Winning Product evidence model: V1 already defines Demand, Momentum,
Commercial Attractiveness, Trust, Contentability, and Competition Opportunity,
but the repository has had no cohort-level authority for observing how much of
that defined evidence space is populated.

No current evidence establishes a retrieval, identity-migration,
review-automation, or serving bottleneck that outranks this measurable evidence
undercoverage:

- P6.2 stays parked because the measured planner-assisted lexical composition
  recovered the published retrieval stress corpus; that result is bounded and
  P6.2 remains reopenable if new retrieval evidence changes it.
- P6.4 stays deferred because no observed identity lifecycle or schema-migration
  bottleneck currently justifies merge/split/migration machinery.
- P6.5 stays deferred because no measured review workload currently justifies a
  new review-triage layer, and explicit Human approval remains authoritative.
- P6.6 stays deferred because no measured latency or throughput workload
  currently justifies caches or background serving.

This choice preserves all prior authority and closure states. It does not claim
that evidence coverage is the repository's only gap or that any missing evidence
class should be implemented.

## 2. Static architecture facts, not a live baseline

The current Shopee and TikTok search-card discovery mappings preserve unavailable
`affiliate_commission_rate`, `estimated_commission_value`, `creator_count`,
`video_count`, `similar_listing_count`, `sales_velocity`, `review_velocity`,
`creator_velocity`, and `video_velocity` as `None`. `CandidateRanker` delegates
to `WinningProductScorer.score_snapshot` without semantic signals. The existing
normalizer and scorer correctly retain these absences through normalized signals,
category coverage, confidence, decision bands, evidence references, and reason
codes.

Those are static repository facts that justify measurement. They are not a live
marketplace sample, do not establish a cohort coverage percentage, and do not
prove which evidence class has the highest commerce value. P7.0 therefore records
no live coverage result.

## 3. P7.0 boundary — measurement only

TASK-181 introduces one pure deterministic evaluator over a caller-supplied,
bounded cohort of exact `ProductCandidateSnapshot` values. It:

- requires an explicit evaluation timestamp and passes an optional exact
  `ScoringPolicy` unchanged to the existing scorer;
- rejects invalid or duplicate candidate identities before any scoring;
- calls `WinningProductScorer.score_snapshot` exactly once per accepted
  candidate in caller order and preserves the exact candidate and returned score
  objects;
- classifies zero, partial, and full category coverage solely from each existing
  `CategoryScore.coverage` value;
- reports missing factual signal names solely when scorer-retained normalized
  signals have `SignalProvenance.MISSING`, in canonical category and scorer signal
  order; and
- aggregates every V1 category and every existing decision band in deterministic
  immutable order, including zero counts.

P7.0 does not inspect candidate fields as a second missing-data authority. In
particular, an empty zero-coverage Contentability category is observable, but the
evaluator does not fabricate missing semantic signal names. It adds no discovery,
normalization, scoring formula, ranking, recommendation, approval, persistence,
retrieval, product-truth, collection, threshold, average, winner label, or roadmap
verdict. `DecisionBand` remains an advisory scorer output, not Human approval or
product truth.

The evaluator performs deterministic in-memory composition only. It introduces no
network, browser/CDP, provider/LLM, filesystem, SQLite, Drive, environment, clock,
random, subprocess, queue, cache, admission, retrieval, or persistence work.

## 4. Measurement before improvement

P7.0 freezes the evaluation contract; it does not improve coverage. Its immediate
successor is TASK-182 / P7.1, a **separate real-evidence coverage baseline** that
freezes one bounded Shopee search-card cohort, records its provenance and exact
immutable report, and replays the published evaluator offline. Live marketplace
capture is implementation-time curation only and is never part of ordinary
offline Runtime verification.

Only that baseline may justify a subsequent improvement proposal. Longitudinal
momentum observations, commercial or affiliate evidence acquisition, competition
evidence acquisition, and semantic Contentability enrichment all remain
conditional. None is selected, ranked, or authorized by TASK-181. Any later work
must retain the existing discovery, normalization, scoring, ranking, approval,
identity, persistence, retrieval, product-truth, and Human-authority boundaries.

## 5. Gate state

TASK-181 / P7.0 is CLOSED / PUBLISHED at source candidate
`9e835ed2c551c2fa3a8b66b82caa238bd41b152c`: RUN-181-001 is the canonical
Runtime PASS and REVIEW-181-001 is the semantic PASS. TASK-182 / P7.1 is the
distinct real-evidence baseline gate; it does not rewrite TASK-181 evaluator
semantics.

No evidence-enrichment implementation is selected by P7.0 or automatically by
P7.1 prevalence. A longitudinal, affiliate/commercial, competition, or semantic
Contentability proposal requires the TASK-182 source candidate to receive both
canonical Runtime PASS and ChatGPT semantic-review PASS, followed by a separate
evidence-driven Brain/Human interpretation and decision.
