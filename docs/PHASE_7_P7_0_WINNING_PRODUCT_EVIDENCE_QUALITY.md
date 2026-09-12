# Phase 7 P7.0 — Winning Product Evidence Quality

Status: **P7 Commerce Opportunity Intelligence is selected by the post-P6
architecture/value audit. TASK-181/P7.0 is CLOSED / PUBLISHED at
`9e835ed2c551c2fa3a8b66b82caa238bd41b152c`. TASK-182/RUN-182-006 is BLOCKED by
semantic review because malformed Shopee sold evidence invalidates that attempted
real-evidence baseline. TASK-185 is CLOSED / PUBLISHED at
`6b03dc14f88ddb98baeb6ae726f0dd913b323ba1`. TASK-186/RUN-186-003 is BLOCKED /
UNPUBLISHED by current Shopee live-DOM incompatibility, with no source candidate.
TASK-187 is CLOSED / PUBLISHED at `857e6b5d0009e9327e1a92d5f62b91432e28f150`.
TASK-188/RUN-188-004 is BLOCKED / UNPUBLISHED with no source candidate; its live
diagnostics are not baseline truth. TASK-189 is CLOSED / PUBLISHED at
`9fa1b2583380e1b6378e5aba3d720c2e78a4b9d4`. TASK-190 is CLOSED / PUBLISHED at
`22d8837e5955ed78185426f293e874625a34d469`. Following completion of the required
post-publication Human review gate accepting one READY `discovery_capture_bundle.json`,
TASK-191 is the fresh offline P7.1 baseline successor: it freezes the accepted bundle
byte-for-byte into immutable repository fixtures, losslessly reconstructs the exact
fifteen-candidate cohort, and replays published TASK-181 `evaluate_winning_product_coverage`
fully offline to record the deterministic measured baseline.**


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

P7.0 freezes the evaluation contract; it does not improve coverage. TASK-182 attempted
the separate real-evidence coverage baseline, but semantic review BLOCKED
RUN-182-006: malformed `sold_count` evidence made the frozen cohort untrustworthy.
Candidate `94c4e5105e593b9136f186882daacb466c9a304d`, its fixture/test/docs delta,
RUN/RESULT/FAILURE/REPAIR lineage, and REVIEW-182-006 remain immutable and
unpublished; their measurements are not baseline truth. TASK-185 hardens only the
existing Shopee evidence-input boundary and does not recapture or rewrite that cohort.

TASK-189 is CLOSED / PUBLISHED at `9fa1b2583380e1b6378e5aba3d720c2e78a4b9d4`.
TASK-188/RUN-188-004 remains BLOCKED / UNPUBLISHED with no source candidate, and its diagnostic
observations must not be reused or treated as baseline truth. TASK-190 is CLOSED / PUBLISHED
at `22d8837e5955ed78185426f293e874625a34d469`, providing operational capture staging for the
3-query discovery cohort outside Git and runtime verification.

The post-publication Human review gate completed and ACCEPTED exactly one READY
`discovery_capture_bundle.json` (SHA-256 `aba1cdbc0a74d591a7da6c6dce11b9ae06bb7c16b0fe151490bb74da3efc465a`,
byte count 16047) for exact query sequence, candidate count, integrity, and relevance.
TASK-191 is the fresh offline P7.1 baseline successor: it freezes the accepted bundle byte-for-byte
into repository fixtures and replays TASK-181 fully offline. Rejected or blocked predecessor
bundles remain operational evidence and are permanently excluded from repaired baseline truth.
The baseline records cohort provenance and the exact immutable report under separate Human review,
without acquiring live marketplace evidence inside ordinary offline Runtime verification.

Only that baseline may justify a subsequent improvement proposal. Longitudinal
momentum observations, commercial or affiliate evidence acquisition, competition
evidence acquisition, and semantic Contentability enrichment all remain
conditional. None is selected, ranked, or authorized by TASK-181. Any later work
must retain the existing discovery, normalization, scoring, ranking, approval,
identity, persistence, retrieval, product-truth, and Human-authority boundaries.

## 5. Gate state

TASK-181/P7.0 is CLOSED / PUBLISHED at
`9e835ed2c551c2fa3a8b66b82caa238bd41b152c`. TASK-182/RUN-182-006 remains
semantically BLOCKED and unpublished. TASK-185 is CLOSED / PUBLISHED at
`6b03dc14f88ddb98baeb6ae726f0dd913b323ba1`; it establishes no P7.1 baseline,
coverage rate, business value, winner, recommendation, or enrichment priority.
TASK-186/RUN-186-003 remains BLOCKED / UNPUBLISHED with no source candidate because
current live Shopee result cards were not recognized. TASK-187 is CLOSED / PUBLISHED at
`857e6b5d0009e9327e1a92d5f62b91432e28f150`. TASK-188/RUN-188-004 remains BLOCKED /
UNPUBLISHED with no source candidate and no baseline truth. TASK-189 is CLOSED /
PUBLISHED at `9fa1b2583380e1b6378e5aba3d720c2e78a4b9d4`. TASK-190 is CLOSED /
PUBLISHED at `22d8837e5955ed78185426f293e874625a34d469`. The post-publication
Human review gate accepted one READY `discovery_capture_bundle.json` (SHA-256
`aba1cdbc0a74d591a7da6c6dce11b9ae06bb7c16b0fe151490bb74da3efc465a`, byte count 16047),
and TASK-191 is the fresh offline P7.1 baseline successor, freezing that accepted bundle
into immutable repository fixtures and replaying TASK-181 offline to record the measured
baseline. Predecessor TASK-182, TASK-186, and TASK-188 remain BLOCKED / UNPUBLISHED historical
evidence and must not be continued, repaired, or rehabilitated. Diagnostic observations are
not baseline truth, P6.2 remains PARKED, P6.4-P6.6 remain DEFERRED / UNIMPLEMENTED, and no
evidence-enrichment implementation is opened in advance or authorized before canonical
Runtime PASS, ChatGPT semantic PASS, source-only publication, and separate Brain/Human
interpretation of this measured baseline.
