# P6.1b Real-Evidence Retrieval Baseline

Status: CLOSED / PUBLISHED by TASK-168 revision 2 at source candidate
`0e6626a53c10609a1a7b282d7ca49af33e4d5573`.

## Frozen corpus

TASK-168 freezes the second Human-reviewed TASK-166 READY bundle as immutable,
fixture-only benchmark input. The first READY bundle remains Human-rejected
operational evidence and was not imported, repaired, merged, relabeled, or used
to derive this corpus. TASK-167 is CLOSED and published.

The committed `capture_bundle.json` is an exact byte copy with SHA-256
`68370824e3a8dcd075a3ceb2b766ba644f9e042ab197528b9a50eb0097b5cf7e`.
Its six ordered `source_pack.json` references are also copied byte-for-byte.
`benchmark.json` records every original bundle-relative manifest path, digest,
and deterministic fixture target. Normal verification uses only committed
fixtures and a temporary SQLite catalog; it neither reads
`PI_P6_1B_CAPTURE_ROOT` nor performs live or external I/O.

The three Human-reviewed cohort intents, in fixed order, are:

1. `bình giữ nhiệt inox`
2. `bàn phím cơ`
3. `chuột không dây`

Human review fixes cohort relevance and ordering before retrieval runs. It is
not derived from retrieved hits, source fields, provider output, or metrics.

## Revision-2 identity representation

RUN-168-001 is preserved as a contract-design failure with zero source delta.
Revision 1 incorrectly required each two-observation cohort to become one
full-member sellable variant. The accepted observations resolve as one
two-member `SAME_PRODUCT_FAMILY` cohort, but TASK-116 does not permit that
relationship to stand in for direct `EXACT_VARIANT_MATCH` evidence. The failure
was corrected without recapture, source mutation, evidence substitution, or a
change to TASK-116.

Revision 2 therefore creates one canonical two-member family per cohort, then
reviews and admits each member in canonical family-member order as its own
explicit singleton benchmark variant. This is evidence-conservative
canonicalization: it refuses to collapse siblings without direct exact-variant
evidence. It does **not** prove that sibling observations are different
real-world variants, claim a complete family variant partition, or create
product truth.

## Offline authority replay

The integration benchmark composes existing authorities only:

- TASK-138 intake runs once per committed cohort root.
- TASK-139/TASK-140 create, approve, and durably admit exactly three
  two-member families through TASK-120.
- TASK-141 invokes TASK-116 singleton proposals and admits exactly six
  one-member variants through TASK-120.
- TASK-120 reloads the disposable catalog, and TASK-121 projects exactly six
  canonical profiles with one-to-one singleton source-pack binding.
- TASK-164 executes the four frozen cases once with `limit=3`; TASK-122 remains
  reachable only through that evaluator.
- Each case receives one TASK-123 context and one TASK-133 grounded-answer
  call. The test-only zero-network provider branches only on the explicit value
  `bool(rag_context.hits)`, after which TASK-164 evaluates citation fidelity
  once.

No production Python, retrieval/ranking behavior, identity authority,
admission semantics, or benchmark-label authority is added or modified.

## Empirical results

The exact snapshot in `benchmark.json` is:

| Case | TP | FP | FN | Precision | Recall | Citation fidelity |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `p6-1b-001` — `bình giữ nhiệt inox` | 2 | 0 | 0 | 1/1 | 1/1 | 1/1 |
| `p6-1b-002` — `bàn phím cơ` | 2 | 0 | 0 | 1/1 | 1/1 | 1/1 |
| `p6-1b-003` — `chuột không dây` | 2 | 0 | 0 | 1/1 | 1/1 | 1/1 |
| `p6-1b-004` — `shopee` | 3 | 0 | 3 | 1/1 | 1/2 | 1/1 |
| **Micro aggregate** | **9** | **0** | **3** | **1/1** | **3/4** | n/a |

These are observations, not acceptance thresholds. TASK-122 owns lexical
matching, witness selection, ordering, and limits; TASK-164 only computes exact
`Fraction` metrics against fixed Human labels. In particular, the broad
`shopee` case exposes the expected `limit=3` recall ceiling against six relevant
variants.

Citation fidelity is deterministic structural provenance relevance. The
provider cites `H001-W001` when a context has hits and emits an
insufficient-evidence response otherwise. The resulting 1/1 values do not grade
answer prose, semantic entailment, factual accuracy, hallucinations, marketplace
identity, or product truth.

## Downstream gate

TASK-168 received Runtime PASS, ChatGPT semantic PASS, and publication. P6.2
remains a separate Brain/Human decision gate; no value in this baseline opened
semantic/vector work automatically.
