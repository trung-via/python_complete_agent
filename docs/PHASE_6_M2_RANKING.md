# Phase 6 M2.3 — Deterministic Candidate Ranking

## Purpose

The ranking core turns a bounded collection of `ProductCandidateSnapshot` values
into an immutable, reproducible shortlist. It is platform-neutral and has no
network, browser, LLM, filesystem, Drive, approval, ingestion, or queue behavior.

## Contract

`CandidateRanker.rank` (also exposed as `rank_candidates`) requires:

- between 1 and 100 candidate snapshots;
- one explicit `evaluated_at` timestamp;
- unique `candidate_id` values; and
- an optional integer `shortlist_size` between 1 and 100 that does not exceed
  the supplied candidate count.

Validation completes before scoring begins. Invalid requests raise
`CandidateRankingError`; duplicate identities are never collapsed.

Each result is a frozen `RankedCandidate` containing the original snapshot and
the exact `WinningProductScore` returned by
`WinningProductScorer.score_snapshot`. The full result is a tuple, and taking a
top-N prefix does not mutate or approve candidates.

## Canonical ordering

Candidates are ordered ascending by the following composite key (negative signs
mean the numeric field is ranked descending):

1. `-final_score`
2. `-confidence`
3. `-base_score`
4. `-data_completeness`
5. `-freshness`
6. `-source_reliability`
7. `-evidence_coverage`
8. `candidate_id`

The candidate ID is the final stable tie-break, so reversing or otherwise
reordering identical input candidates cannot change the ranked output.

## Missing data and policy ownership

Ranking does not normalize signals or implement scoring formulas. Every snapshot
is delegated to `WinningProductScorer.score_snapshot` with the same explicit
evaluation timestamp and optional `ScoringPolicy`. Consequently, missing values
remain missing and retain the scorer's existing confidence damping semantics.
