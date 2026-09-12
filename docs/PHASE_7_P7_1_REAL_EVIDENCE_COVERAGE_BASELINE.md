# Phase 7 P7.1 — Real-Evidence Winning Product Coverage Baseline

Status: **TASK-191 baseline candidate. This document records benchmark evidence,
not a quality threshold, winner selection, approval, or enrichment decision.**

## 1. Bounded methodology and provenance

The baseline freezes exactly one Human-accepted discovery capture bundle from the
Human-operated TASK-190 staging boundary. Predecessor attempts remain canonical
historical evidence: TASK-182 candidate `94c4e5105e593b9136f186882daacb466c9a304d`
and REVIEW-182-006 remain BLOCKED / UNPUBLISHED because malformed Shopee sold
evidence invalidated that cohort; TASK-186/RUN-186-003 and TASK-188/RUN-188-004
remain BLOCKED / UNPUBLISHED with no source candidate and their diagnostics are not
baseline truth.

TASK-190 provided operational capture staging for the 3-query discovery cohort
under the `p7-1-discovery-cohort` profile. The Human post-publication review gate
was executed, and exactly one bundle was ACCEPTED for exact query sequence, order,
candidate count, structural integrity, and relevance:

- **Fixture**: `tests/fixtures/p7_1_winning_product_coverage/discovery_capture_bundle.json`
- **SHA-256**: `aba1cdbc0a74d591a7da6c6dce11b9ae06bb7c16b0fe151490bb74da3efc465a`
- **Byte count**: 16047
- **Capture task**: `TASK-190`
- **Capture source candidate**: `22d8837e5955ed78185426f293e874625a34d469`
- **Human review**: `ACCEPTED`

The accepted bundle contains three ordered batches corresponding to the three
Human-authored queries:

1. `bình giữ nhiệt inox`
2. `bàn phím cơ`
3. `chuột không dây`

Every batch used `platform="shopee"`, `pages_examined=1`, `candidate_count=5`,
and retained diagnostic code `DISCOVERY_SUCCESS`. Their exact timestamps and
raw-item counts are:

| Query order | Query | `observed_at` | `raw_items_seen` | Candidate count |
| ---: | --- | --- | ---: | ---: |
| 1 | `bình giữ nhiệt inox` | `2026-09-12T12:06:22.951315+00:00` | 20 | 5 |
| 2 | `bàn phím cơ` | `2026-09-12T12:06:28.241736+00:00` | 20 | 5 |
| 3 | `chuột không dây` | `2026-09-12T12:06:33.110964+00:00` | 5 | 5 |

The fifteen candidate IDs and URLs are pairwise distinct. Candidate order is the
exact query order followed by exact card order; no scorer, ranker, shortlist,
approval, or post-hoc filtering selected or altered the cohort. The immutable fixture
preserves only exact public `DiscoveryBatch.to_dict()` and `ProductCandidateSnapshot.to_dict()`
projections. Unknown marketplace fields remain `None`; nothing is normalized,
enriched, inferred, repaired, or filled after capture.

`evaluated_at` is derived deterministically as the maximum batch timestamp,
`2026-09-12T12:06:33.110964+00:00`. Offline replay losslessly reconstructs each
exact `ProductCandidateSnapshot` and `DiscoveryBatch`, proves that public projections
match the frozen fixture byte-for-byte, concatenates all fifteen candidates in frozen
order, and calls published TASK-181 `evaluate_winning_product_coverage` exactly once
with `policy=None`.

## 2. Exact measured report

The deterministic JSON fixture `tests/fixtures/p7_1_winning_product_coverage/baseline.json`
is the sole canonical measured snapshot, recording bundle provenance plus the exact
TASK-181 report. The human-readable projection below records the cohort and evaluator
outputs without recomputation.

| Order | Candidate ID | Base score | Confidence | Final score | Decision band |
| ---: | --- | ---: | ---: | ---: | --- |
| 1 | `shopee_26025988006` | 0.0 | 0.0 | 0.0 | `INSUFFICIENT_DATA` |
| 2 | `shopee_24632703114` | 0.0 | 0.0 | 0.0 | `INSUFFICIENT_DATA` |
| 3 | `shopee_22552755333` | 0.0 | 0.0 | 0.0 | `INSUFFICIENT_DATA` |
| 4 | `shopee_24233700407` | 0.0 | 0.0 | 0.0 | `INSUFFICIENT_DATA` |
| 5 | `shopee_27156400407` | 0.0 | 0.0 | 0.0 | `INSUFFICIENT_DATA` |
| 6 | `shopee_3408121883` | 0.0 | 0.0 | 0.0 | `INSUFFICIENT_DATA` |
| 7 | `shopee_21523544755` | 0.0 | 0.0 | 0.0 | `INSUFFICIENT_DATA` |
| 8 | `shopee_10476729197` | 0.0 | 0.0 | 0.0 | `INSUFFICIENT_DATA` |
| 9 | `shopee_24512090419` | 0.0 | 0.0 | 0.0 | `INSUFFICIENT_DATA` |
| 10 | `shopee_23943185885` | 0.0 | 0.0 | 0.0 | `INSUFFICIENT_DATA` |
| 11 | `shopee_54158809627` | 0.0 | 0.0 | 0.0 | `INSUFFICIENT_DATA` |
| 12 | `shopee_26389723604` | 0.0 | 0.0 | 0.0 | `INSUFFICIENT_DATA` |
| 13 | `shopee_41656976929` | 0.0 | 0.0 | 0.0 | `INSUFFICIENT_DATA` |
| 14 | `shopee_26692617809` | 0.0 | 0.0 | 0.0 | `INSUFFICIENT_DATA` |
| 15 | `shopee_21062479356` | 0.0 | 0.0 | 0.0 | `INSUFFICIENT_DATA` |

Every candidate has the identical evaluator classification:

- **Zero coverage**: `DEMAND`, `MOMENTUM`, `COMMERCIAL_ATTRACTIVENESS`, `TRUST`,
  `CONTENTABILITY`, and `COMPETITION_OPPORTUNITY` (15 of 15 candidates);
- **Partial coverage**: none (0 of 15 candidates);
- **Full coverage**: none (0 of 15 candidates); and
- **Missing factual signals**, in canonical evaluator order: `sold_volume`,
  `review_depth`, `sales_velocity`, `creator_growth`, `commission_rate`,
  `discount_appeal`, `rating_quality`, `market_whitespace`, and `creator_whitespace`
  (each missing in 15 of 15 candidate evaluations).

The exact ordered category counts are:

| Category | Zero | Partial | Full |
| --- | ---: | ---: | ---: |
| `DEMAND` | 15 | 0 | 0 |
| `MOMENTUM` | 15 | 0 | 0 |
| `COMMERCIAL_ATTRACTIVENESS` | 15 | 0 | 0 |
| `TRUST` | 15 | 0 | 0 |
| `CONTENTABILITY` | 15 | 0 | 0 |
| `COMPETITION_OPPORTUNITY` | 15 | 0 | 0 |

The exact ordered decision-band counts are:

| Decision band | Count |
| --- | ---: |
| `RECOMMENDED` | 0 |
| `NEEDS_REVIEW` | 0 |
| `INSUFFICIENT_DATA` | 15 |
| `HOLD` | 0 |

Contentability has zero coverage, and TASK-181 correctly emits no fabricated
semantic missing-signal names. All fifteen candidates yield decision band
`INSUFFICIENT_DATA`.

## 3. Interpretation boundary

These values measure evidence coverage prevalence in exactly fifteen Shopee
search-card observations. They clearly separate observed evidence prevalence from
economic value:

1. **Prevalence vs. Value**: The fact that a factual signal or category has zero
   coverage or high missingness measures only that the search-card surface does not
   supply that observation. It does not measure the commercial attractiveness or
   economic potential of the underlying product.
2. **No Winner Declaration or Approval**: The baseline neither declares a winning
   product nor approves any listing. Scores, confidence, decision bands, category
   coverage, and missing-signal counts are descriptive benchmark measurements only.
3. **No Quality Threshold**: No business-quality pass/fail threshold exists. The
   distribution is deterministic and canonical regardless of numerical values.
4. **No Automatic Enrichment Selection**: A high missingness rate does not authorize
   immediate construction of a new collector, scraper, or enrichment pipeline.
5. **Bounded Scope**: This baseline applies strictly to the frozen fifteen-candidate
   Shopee search-card cohort. It makes no claims regarding TikTok, cross-platform
   discovery, all-Shopee catalog coverage, longitudinal dynamics, affiliate
   commission networks, creator/video engagement, competition whitespace, or
   semantic Contentability.

Any post-baseline improvement choice is a separate Brain/Human decision. It may
occur only after this TASK-191 source candidate achieves canonical Runtime PASS,
ChatGPT semantic PASS, source-only publication, and subsequent Brain/Human
interpretation of this measured baseline.

## 4. Offline verification boundary

Runtime verification is fully offline and deterministic. It reads only the
committed immutable fixture files (`discovery_capture_bundle.json` and `baseline.json`)
and evaluates the cohort using published M2/TASK-181 authorities. It performs zero
browser/CDP navigation, live marketplace interaction, network requests, provider/LLM
calls, environment-dependent loading, clock reads, UUID generation, subprocesses,
or external persistence. Production Python is unchanged (0 production lines modified),
and the private test loader is strictly integration-test code, not a reusable codec.
