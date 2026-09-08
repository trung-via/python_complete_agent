# Phase 6 P6.1 — Retrieval-Quality Evaluation: P6.1a Evaluation Contract

## 1. Overview & System Boundaries

Phase 6 follows the canonical discipline:
```
CERTIFY  -->  EVALUATE  -->  IMPROVE
```

With the completion of **TASK-154** (P6.0a live discovery and typed source-pack persistence) and **TASK-163** (P6.0b real-evidence canonical knowledge composition and grounded QA), **P6.0 Live Real-Evidence Certification is CLOSED**.

**P6.1 Retrieval-Quality Evaluation** is the **CURRENT** capability boundary. To ensure that evaluation metrics are frozen, reproducible, and decoupled from benchmark curation, P6.1 is deliberately split into two sequential sub-stages:
- **P6.1a Evaluation Contract (TASK-164 — CURRENT)**: Establishes one pure, deterministic, in-memory evaluation authority over existing TASK-122 lexical retrieval hits and TASK-129 grounded answers.
- **P6.1b Real-Evidence Benchmark Execution (NEXT)**: Curates and executes a reviewed real-evidence benchmark corpus over acquired marketplace evidence using this frozen evaluator.
- **P6.2 Conditional Semantic / Vector Retrieval or Reranking (FUTURE / BLOCKED)**: Strictly blocked until reviewed empirical P6.1b benchmark evidence proves measurable deficiencies in lexical retrieval that semantic search specifically remedies.

TASK-164 adds **zero** new retrieval, planner, provider, persistence, ranking, semantic-search, or truth-resolution APIs. Predecessor implementation modules remain strictly unchanged.

---

## 2. Separation of Concerns & Authority Boundaries

| Domain / Concept | Authoritative Boundary | P6.1a TASK-164 Boundary |
| --- | --- | --- |
| **Canonical Product Truth** | M3 Entity Resolution / Catalog (`TASK-108`..`TASK-125`) | Human-authored benchmark relevance labels (`relevant_variant_ids`) are test evaluation inputs only. They never define or alter canonical product truth, entity identity, or catalog membership, and are never written into canonical state. |
| **Business Ranking & Approval** | M2 Discovery / Ranking / Approval (`TASK-095`, `TASK-096`, `TASK-146`, `TASK-147`) | Benchmark relevance is not an M2 business score, recommendation, or approval decision. TASK-164 does not rank candidates, prioritize listings, or alter ingestion queues. |
| **Lexical Retrieval Semantics** | TASK-122 (`canonical_retrieval.py`) | TASK-122 remains the sole lexical retrieval authority (tokenization, NFKC normalization, match classes, witness selection, hit ordering, limits). TASK-164 delegates retrieval to TASK-122 unchanged and never reimplements or alters matching logic. |
| **Structural Grounding** | TASK-129 (`grounded_answer.py`) | TASK-129 validates structural context-local citation addresses and answer invariants. TASK-164 evaluates whether an already-valid `GroundedAnswer` cites benchmark-relevant retrieved variants. |
| **Semantic Entailment** | Outside System Boundary | TASK-164 **never** interprets answer prose, parses natural language, grades semantic entailment, detects hallucinations, or claims factual correctness. Citation fidelity measures structural provenance relevance only. |

---

## 3. Data Structures & Contract Invariants

All evaluation structures are immutable (`@dataclass(frozen=True)`):

### 3.1 `RetrievalBenchmarkCase`
Represents one Human-authored benchmark case:
- `case_id`: Non-blank, single-line string of at most 128 UTF-8 bytes.
- `question`: Non-blank string of at most 4096 UTF-8 bytes.
- `retrieval_query`: Exact string passed unchanged to TASK-122 retrieval. TASK-164 performs no local tokenization, normalization, or planning.
- `relevant_variant_ids`: Non-empty tuple of unique, non-blank variant IDs in caller-supplied order.

### 3.2 `RetrievalCaseEvaluation`
Captures the evaluation result for a single benchmark case:
- `case`: Exact supplied `RetrievalBenchmarkCase`.
- `limit`: Exact evaluator limit used for retrieval.
- `hits`: Exact tuple of `CanonicalVariantRetrievalHit` returned by TASK-122.
- `true_positive_variant_ids`: Retrieved variant IDs present in `relevant_variant_ids`, preserving exact TASK-122 hit order.
- `false_positive_variant_ids`: Retrieved variant IDs absent from `relevant_variant_ids`, preserving exact TASK-122 hit order.
- `false_negative_variant_ids`: Relevant variant IDs not retrieved, preserving exact Human benchmark order.
- `precision`: Exact `fractions.Fraction` precision.
- `recall`: Exact `fractions.Fraction` recall.

### 3.3 `RetrievalQualityReport`
Aggregates quality metrics across multiple benchmark cases:
- `limit`: Exact evaluator limit.
- `case_evaluations`: Tuple of `RetrievalCaseEvaluation` in caller case order.
- `true_positive_count`: Total true positives across all cases.
- `false_positive_count`: Total false positives across all cases.
- `false_negative_count`: Total false negatives across all cases.
- `micro_precision`: Exact `fractions.Fraction` micro precision.
- `micro_recall`: Exact `fractions.Fraction` micro recall.

### 3.4 `GroundedCitationFidelity`
Evaluates citation alignment for an already-valid `GroundedAnswer`:
- `case_evaluation`: Exact supplied `RetrievalCaseEvaluation`.
- `answer`: Exact supplied `GroundedAnswer`.
- `leaf_citation_ids`: Tuple of leaf citations preserving `answer.citation_ids` order (hit-header `Hxxx` citations excluded).
- `relevant_leaf_citation_ids`: Leaf citations tracing to parent hits whose `variant_id` is in `relevant_variant_ids`.
- `irrelevant_leaf_citation_ids`: Leaf citations tracing to parent hits whose `variant_id` is not in `relevant_variant_ids`.
- `fidelity`: Exact `fractions.Fraction` ($relevant / total$), or `None` when zero leaf citations exist.

---

## 4. Exact Metric Calculations

All metrics use exact rational arithmetic via `fractions.Fraction`. No floating-point rounding, macro-averaging, weighted relevance, NDCG, MRR, or F1 scores are introduced.

### 4.1 Per-Case Metrics
- **Retrieved Count**: $N_{retrieved} = |hits| = |TP| + |FP|$
- **Relevant Count**: $N_{relevant} = |case.relevant\_variant\_ids| = |TP| + |FN| \ge 1$
- **Precision**:
  $$\text{precision} = \begin{cases} \text{Fraction}(0, 1) & \text{if } N_{retrieved} = 0 \\ \text{Fraction}(|TP|, N_{retrieved}) & \text{if } N_{retrieved} > 0 \end{cases}$$
- **Recall**:
  $$\text{recall} = \text{Fraction}(|TP|, N_{relevant})$$

### 4.2 Micro Aggregation
- **Micro-Precision**:
  $$\text{micro\_precision} = \begin{cases} \text{Fraction}(0, 1) & \text{if } \sum |TP| + \sum |FP| = 0 \\ \text{Fraction}(\sum |TP|, \sum |TP| + \sum |FP|) & \text{otherwise} \end{cases}$$
- **Micro-Recall**:
  $$\text{micro\_recall} = \text{Fraction}\left(\sum |TP|, \sum |TP| + \sum |FN|\right)$$
  *(Denominator is always $\ge 1$ because every case has $\ge 1$ relevant variant ID).*

### 4.3 Grounded Citation Fidelity
- **Leaf Addresses**: Witness citations (`Hxxx-Wyyy`) and supplemental evidence citations (`Hxxx-Eyyy`) derived from `CanonicalRagContext`.
- **Hit Headers**: Hit-header citations (`Hxxx`) are excluded from the fidelity denominator because TASK-129 does not treat them as leaf grounding.
- **Fidelity**:
  $$\text{fidelity} = \begin{cases} \text{None} & \text{if } |leaf\_citations| = 0 \\ \text{Fraction}(|relevant\_leaves|, |leaf\_citations|) & \text{if } |leaf\_citations| > 0 \end{cases}$$

---

## 5. Pure Deterministic Execution Guarantees

1. **Single Materialization**: `evaluate_lexical_retrieval_quality` materializes profiles and cases iterables exactly once.
2. **Corpus Validation Delegation**: Profiles are validated through TASK-122 delegation; `CanonicalProfileRetrievalError` propagates unchanged.
3. **Gold ID Binding**: Every `relevant_variant_id` must bind to a variant in the validated corpus; unknown gold IDs fail closed with `RetrievalQualityEvaluationError`.
4. **Continuity Enforcement**: `evaluate_grounded_answer_citation_fidelity` requires exact question, query, limit, and value-equal hit continuity between `case_evaluation` and `answer.context`. Unrelated contexts fail closed.
5. **Zero Side-Effects**: No filesystem, database, network, clock, random, UUID, model provider, query planning, or subprocess operations are performed.
