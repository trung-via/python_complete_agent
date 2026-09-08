# Phase 6 P6.1 — Real-Evidence Retrieval Baseline (P6.1b)

## 1. Executive Summary & Objective

Phase 6 adheres strictly to the canonical sequence:
```
CERTIFY  -->  EVALUATE  -->  IMPROVE
```

With **TASK-164 (P6.1a)** establishing the pure, deterministic retrieval-quality and citation-fidelity evaluation contract over frozen interfaces, **TASK-165 (P6.1b)** executes this evaluation against a reviewed, genuine marketplace evidence corpus.

This baseline exercises the entire post-M4 pipeline offline:
1. **Intake (TASK-138)**: Recursively intakes frozen `ProductSourcePack` manifests from three distinct Shopee acquisition cohorts.
2. **Family Knowledge Review & Admission (TASK-139 / TASK-140)**: Derives actionable family merge proposals and durably registers three two-observation canonical families (`p6-benchmark-family-001` .. `003`) into disposable SQLite (`TASK-120`).
3. **Sellable Variant Review & Admission (TASK-141)**: Reviews and durably registers three complete-pair sellable variants (`p6-benchmark-variant-001` .. `003`).
4. **Canonical Variant Profile Projection (TASK-121)**: Reconstructs canonical variant profiles binding exact source pack evidence.
5. **Lexical Retrieval Evaluation (TASK-164 / TASK-122)**: Evaluates lexical retrieval against four fixed Human-authored benchmark cases at `limit=3`.
6. **Grounded Context & Citation Fidelity (TASK-123 / TASK-133 / TASK-164)**: Constructs canonical RAG context, invokes a deterministic zero-network provider, and evaluates structural citation fidelity.

---

## 2. Benchmark Corpus Composition

The frozen benchmark corpus comprises exactly three distinct Shopee cohorts corresponding to the three fixed Human search intents:

| Cohort | Case Directory | Search Intent / Retrieval Query | Selected Listing Title | Source Product ID | Observations | Admitted Variant ID |
| --- | --- | --- | --- | --- | --- | --- |
| **Cohort 1** | `case-001` | `bình giữ nhiệt inox` | Bình Giữ Nhiệt Inox 304 Dung tích 300ml | `18680482120` | 2 | `p6-benchmark-variant-001` |
| **Cohort 2** | `case-002` | `bàn phím cơ` | Bàn phím cơ Gaming TEKKIN JK540 Full LED Bàn Phím Cao Cấp Dành Cho Game Thủ Văn Phòng | `23865249083` | 2 | `p6-benchmark-variant-002` |
| **Cohort 3** | `case-003` | `chuột không dây` | (Bán Chạy) Đèn Lồng Lân Sư 2026 Điều Khiển Dây Kéo Sinh Động Thủ Công Đồ Chơi Trung Thu Cho Bé | `29595660451` | 2 | `p6-benchmark-variant-003` |

### Invariants of the Frozen Fixtures
- **Authenticity**: Captured through the authenticated CDP browser path via `ShopeeScrapeTool` and `ShopeeSourceExtractor`.
- **Identity Distinctness**: All six observations have pairwise distinct `SourceObservationIdentity` values (`(platform, source_product_id, observed_at)`).
- **Zero Committed Media / Raw Artifacts**: Only the six clean, typed-rehydratable `source_pack.json` manifests are committed. No binary image payloads, raw HTML dumps, browser profiles, cookies, or secrets are stored.
- **Offline Determinism**: Verification runs 100% offline against temporary SQLite databases beneath `tmp_path`, requiring zero network I/O, browser processes, or provider credentials.

---

## 3. Measured Empirical Baseline Snapshot

The benchmark evaluates four fixed Human cases using exact `fractions.Fraction` arithmetic with `limit=3`:

### 3.1 Per-Case Measurement Summary

| Case ID | Retrieval Query | Relevant Variant IDs (Human Label) | Retrieved Variant IDs (TASK-122) | TP | FP | FN | Precision | Recall | Grounded Answer Status | Citation Fidelity |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `p6-1b-001` | `bình giữ nhiệt inox` | `p6-benchmark-variant-001` | `p6-benchmark-variant-001` | 1 | 0 | 0 | **1/1** (1.0) | **1/1** (1.0) | `ANSWERED` | **1/1** (1.0) |
| `p6-1b-002` | `bàn phím cơ` | `p6-benchmark-variant-002` | `p6-benchmark-variant-002` | 1 | 0 | 0 | **1/1** (1.0) | **1/1** (1.0) | `ANSWERED` | **1/1** (1.0) |
| `p6-1b-003` | `chuột không dây` | `p6-benchmark-variant-003` | *(None)* | 0 | 0 | 1 | **0/1** (0.0) | **0/1** (0.0) | `INSUFFICIENT_EVIDENCE` | **None** |
| `p6-1b-004` | `shopee` | `p6-benchmark-variant-001`, `p6-benchmark-variant-002`, `p6-benchmark-variant-003` | `p6-benchmark-variant-001`, `p6-benchmark-variant-002`, `p6-benchmark-variant-003` | 3 | 0 | 0 | **1/1** (1.0) | **1/1** (1.0) | `ANSWERED` | **1/1** (1.0) |

### 3.2 Aggregate Metrics

- **Total Benchmark Cases**: 4
- **Aggregate True Positives (TP)**: 5
- **Aggregate False Positives (FP)**: 0
- **Aggregate False Negatives (FN)**: 1
- **Micro-Averaged Precision**: $\frac{\sum \text{TP}}{\sum \text{TP} + \sum \text{FP}} = \frac{5}{5 + 0} =$ **1/1 (1.0)**
- **Micro-Averaged Recall**: $\frac{\sum \text{TP}}{\sum \text{TP} + \sum \text{FN}} = \frac{5}{5 + 1} =$ **5/6 (~0.8333)**

---

## 4. Empirical Analysis & Failure Mode Characterization

### 4.1 Case 3 Lexical Incompleteness Mode
In `case-003`, the Human acquisition intent was `chuột không dây` (wireless mouse). The live marketplace discovery shortlisted candidate `29595660451` titled `"(Bán Chạy) Đèn Lồng Lân Sư 2026 Điều Khiển Dây Kéo Sinh Động Thủ Công Đồ Chơi Trung Thu Cho Bé"`. 

When TASK-122 lexical retrieval queries the profile corpus for `"chuột không dây"`, none of the normalized tokens match any field in the profile (title, brand, model_sku, facts, or descriptions). Consequently:
- Zero hits are returned.
- Precision evaluates to `Fraction(0, 1)`.
- Recall evaluates to `Fraction(0, 1)`.
- RAG context contains zero evidence, prompting the deterministic provider to return `INSUFFICIENT_EVIDENCE` with empty citations.
- Citation fidelity correctly records `None`.

**Significance**: This behavior is an authentic manifestation of real-world discovery-to-retrieval divergence:
1. Live search ranking algorithms may return sponsored, promotional, or noisy items whose textual listing metadata lacks the user's explicit query terms.
2. Lexical keyword matching (TASK-122) cannot bridge semantic divergence when there is zero lexical overlap between the query and candidate profile tokens.
3. This is not a defect of the benchmark or evaluator; it is empirical evidence capturing genuine marketplace retrieval behavior.

---

## 5. Scope Boundaries & Non-Goals

To maintain strict architectural governance, the following boundaries are formally recorded:

1. **Statistical Scope Limitation**: This benchmark operates over a bounded 3-cohort corpus (6 observations). It is designed to provide architectural evidence of pipeline behavior, regression detection, and failure modes—**not** a statistically generalized marketplace accuracy SLA or production ranking quality metric.
2. **Platform Specificity**: Measurements reflect the certified Shopee route only. No claims are made regarding TikTok Shop retrieval behavior, discovery quality, or catalog scale.
3. **Separation from Product Truth**: Human relevance annotations (`relevant_variant_ids`) are benchmark evaluation inputs only. They do not constitute canonical product truth, entity resolution decisions, or catalog state.
4. **Structural Grounding vs. Semantic Entailment**: Citation fidelity measures whether generated answers cite benchmark-relevant context addresses (`H001-W001`). It does **not** evaluate natural language answer fluency, hallucination, or factual veracity.
5. **No Automatic Authorization of P6.2**: A recall of 5/6 does not automatically authorize semantic or vector retrieval (P6.2). Any P6.2 initiative remains a separate Brain decision gate based on whether the specific failure modes justify the operational overhead of embeddings, vector storage, and hybrid retrieval.

---

## 6. Verification and Regression Contract

The offline test `tests/integration/test_p6_1b_real_evidence_retrieval_baseline.py` enforces deterministic replayability:
- Re-runs the entire pipeline from committed fixture manifests into a fresh, isolated SQLite catalog.
- Evaluates lexical retrieval with `evaluate_lexical_retrieval_quality` at `limit=3`.
- Requires exact equality against `tests/fixtures/p6_1b_real_evidence/benchmark.json` down to the exact integer numerator and denominator of every `Fraction`.
- Prevents drift in retrieval, intake, admission, or grounding authorities across future changes.
