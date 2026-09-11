# Phase 7 P7.1 — Real-Evidence Winning Product Coverage Baseline

Status: **TASK-182 baseline candidate. This document records benchmark evidence,
not a quality threshold, winner selection, approval, or enrichment decision.**

## 1. Bounded methodology and provenance

The baseline freezes exactly one implementation-time Shopee search-card cohort
from the existing `ShopeeDiscoveryAdapter`. The adapter was called once for each
Human-authored query, in this order:

1. `bình giữ nhiệt inox`
2. `bàn phím cơ`
3. `chuột không dây`

Every call used `max_candidates=5`, `max_pages=1`, locale `vi-VN`, and an explicit
timezone-aware `observed_at`. The accepted batches contained five candidates each,
examined one page each, and retained adapter diagnostics `DISCOVERY_SUCCESS`.
Their exact timestamps and raw-card counts were:

| Query order | `observed_at` | `raw_items_seen` | Candidate count |
| ---: | --- | ---: | ---: |
| 1 | `2026-09-11T13:53:39.512551+00:00` | 10 | 5 |
| 2 | `2026-09-11T13:53:51.373610+00:00` | 15 | 5 |
| 3 | `2026-09-11T13:54:08.574673+00:00` | 5 | 5 |

The fifteen candidate IDs and URLs are pairwise distinct. Candidate order is the
exact query order followed by exact adapter card order; no scorer, ranker,
shortlist, approval, relevance judgment, or computed result selected the sample.
The immutable fixture preserves only exact public `DiscoveryBatch.to_dict()`
projections. Unknown marketplace facts remain `None`; nothing is normalized,
enriched, inferred, repaired, or filled after capture.

`evaluated_at` is exactly the maximum batch timestamp,
`2026-09-11T13:54:08.574673+00:00`. Offline replay losslessly reconstructs each
exact `ProductCandidateSnapshot`, proves that its public projection is unchanged,
concatenates all fifteen in frozen order, and calls the published TASK-181
`evaluate_winning_product_coverage` exactly once with `policy=None`.

## 2. Exact measured report

The deterministic JSON fixture is the immutable exact report, including every
per-candidate `score.to_dict()` field, coverage classification, missing factual
signal name, and ordered aggregate count. The human-readable projection below
records the same cohort and evaluator outputs without recomputation.

| Order | Candidate ID | Base score | Confidence | Final score | Decision band |
| ---: | --- | ---: | ---: | ---: | --- |
| 1 | `shopee_25872232663` | 100.0 | 0.66 | 65.9981 | `NEEDS_REVIEW` |
| 2 | `shopee_26410239101` | 100.0 | 0.66 | 65.9981 | `NEEDS_REVIEW` |
| 3 | `shopee_41267976459` | 100.0 | 0.66 | 65.9981 | `NEEDS_REVIEW` |
| 4 | `shopee_23348470715` | 100.0 | 0.66 | 65.9981 | `NEEDS_REVIEW` |
| 5 | `shopee_48517524869` | 100.0 | 0.66 | 65.9981 | `NEEDS_REVIEW` |
| 6 | `shopee_20773889584` | 100.0 | 0.66 | 65.9989 | `NEEDS_REVIEW` |
| 7 | `shopee_24512090419` | 100.0 | 0.66 | 65.9989 | `NEEDS_REVIEW` |
| 8 | `shopee_23312440166` | 100.0 | 0.66 | 65.9989 | `NEEDS_REVIEW` |
| 9 | `shopee_23943185885` | 100.0 | 0.66 | 65.9989 | `NEEDS_REVIEW` |
| 10 | `shopee_14889414134` | 100.0 | 0.66 | 65.9989 | `NEEDS_REVIEW` |
| 11 | `shopee_29039714011` | 100.0 | 0.66 | 66.0 | `NEEDS_REVIEW` |
| 12 | `shopee_13147522818` | 100.0 | 0.66 | 66.0 | `NEEDS_REVIEW` |
| 13 | `shopee_24447890589` | 100.0 | 0.66 | 66.0 | `NEEDS_REVIEW` |
| 14 | `shopee_29390627708` | 100.0 | 0.66 | 66.0 | `NEEDS_REVIEW` |
| 15 | `shopee_22345097219` | 100.0 | 0.66 | 66.0 | `NEEDS_REVIEW` |

Every candidate has the same evaluator classification:

- partial coverage: `DEMAND`;
- zero coverage: `MOMENTUM`, `COMMERCIAL_ATTRACTIVENESS`, `TRUST`,
  `CONTENTABILITY`, and `COMPETITION_OPPORTUNITY`;
- full coverage: none; and
- missing factual signals, in evaluator order: `review_depth`, `sales_velocity`,
  `creator_growth`, `commission_rate`, `discount_appeal`, `rating_quality`,
  `market_whitespace`, and `creator_whitespace`.

The exact ordered category counts are:

| Category | Zero | Partial | Full |
| --- | ---: | ---: | ---: |
| `DEMAND` | 0 | 15 | 0 |
| `MOMENTUM` | 15 | 0 | 0 |
| `COMMERCIAL_ATTRACTIVENESS` | 15 | 0 | 0 |
| `TRUST` | 15 | 0 | 0 |
| `CONTENTABILITY` | 15 | 0 | 0 |
| `COMPETITION_OPPORTUNITY` | 15 | 0 | 0 |

The exact ordered decision-band counts are `RECOMMENDED=0`, `NEEDS_REVIEW=15`,
`INSUFFICIENT_DATA=0`, and `HOLD=0`. Each of the eight missing factual signal
names occurs in 15 of 15 candidate evaluations. Contentability has zero coverage,
but TASK-181 correctly emits no fabricated semantic missing-signal names.

## 3. Interpretation boundary

These values measure coverage prevalence in exactly fifteen Shopee search-card
observations. They are not evidence of a candidate's economic value, a declaration
that any candidate is a winning product, or approval of any candidate. Scores,
confidence, decision bands, category coverage, and missing-signal prevalence are
recorded outputs only; none is a baseline pass/fail threshold.

A frequently missing field is a candidate for later value investigation, not
automatic authority to build a collector. This cohort does not support TikTok,
cross-platform, all-Shopee, longitudinal, affiliate, creator, competition, semantic
Contentability, general-marketplace, or marketplace-SLA claims. P7.1 selects no
evidence enrichment automatically.

Any post-baseline improvement selection is a separate evidence-driven Brain/Human
decision. It may occur only after this TASK-182 source candidate has canonical
Runtime PASS and ChatGPT semantic-review PASS and the measured evidence has been
interpreted separately.

## 4. Offline verification boundary

Ordinary Runtime verification reads only the committed compact UTF-8 fixture and
uses existing pure M2/TASK-181 authorities. It performs no browser/CDP, network,
marketplace, provider/LLM, environment, clock, random, UUID, subprocess, external
filesystem discovery, persistence, or live acquisition work. Production Python is
unchanged, and the private test-only loader is not a production codec or API.
