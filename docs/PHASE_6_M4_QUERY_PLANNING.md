# Phase 6 M4.5 — Grounded Retrieval Query Planning

## Purpose and public API

TASK-134 provides a bounded, deterministic query-planning boundary that derives one explicit TASK-122-compatible `retrieval_query` from a caller's natural-language question and a supplied canonical profile corpus.

The public surface consists of exactly:

- `GroundedQueryPlanningError`
- `plan_grounded_retrieval_query(profiles, *, question) -> str`

The function is a synchronous, pure in-memory planner. It returns only the selected retrieval query string as transient application input for TASK-123. It exposes no candidate lists, hits, scores, confidence metrics, product selections, or hidden state.

## Authority boundaries and chain

| Authority | Ownership |
| --- | --- |
| TASK-121 | Evidence-preserving projection of `CanonicalVariantProfile` instances from canonical catalog entities and observations. |
| TASK-122 | Sole authority for lexical token normalization, matching classes, witness generation, hit ordering, and all corpus retrieval probes. |
| TASK-134 (M4.5) | Sole authority for deterministic question span segmentation, candidate span generation (length 1..12), candidate preference ranking, and fallback policy. |
| TASK-123 / TASK-124 | Later performs the single canonical retrieval with the planned query, context budgeting, and formatting of `CanonicalRagContext`. |
| TASK-133 | Grounded-QA composition across context, prompt package, invocation, and final answer; begins from an already-built context and remains unchanged. |

The authority chain is strictly delineated:
- TASK-122 owns every retrieval probe.
- TASK-134 owns only deterministic query-span selection.
- TASK-123 later performs the one canonical retrieval that becomes context.
- TASK-133 still begins from an already-built context and remains unchanged.

Planning probes executed during TASK-134 are transient inspection probes only; they are never retained, returned, cached, or reused as context evidence.

## Deterministic planning contract

1. **Question input validation**:
   - `question` must be an exact `str`, contain at least one non-whitespace character, and not exceed 4096 UTF-8 bytes.
   - Invalid input fails closed with `GroundedQueryPlanningError`.

2. **Lexical segmentation**:
   - Scans the question left-to-right to retain maximal runs of characters for which `str.isalnum()` is true.
   - Preserves original string bytes, casing, and source order.
   - Performs no NFKC normalization, casefold, accent stripping, transliteration, stemming, synonym expansion, or stop-word filtering.
   - Questions producing 0 runs or more than 24 runs fail closed with `GroundedQueryPlanningError`.

3. **Candidate span generation and evaluation order**:
   - Candidates are contiguous spans of original tokens of lengths 1..12, joined by a single ASCII space (`" "`).
   - Evaluated strictly in descending span length, then ascending start position.
   - No token reordering, non-contiguous term selection, term deletion, spelling/case modification, or token fabrication.

4. **TASK-122 delegation**:
   - Every corpus probe delegates to `retrieve_canonical_variant_profiles(corpus, query=candidate, limit=2)`.
   - TASK-134 uses no private retrieval helpers and does not reproduce TASK-122 matching logic.
   - Any `CanonicalProfileRetrievalError` from TASK-122 propagates unchanged under TASK-122 authority.
   - `limit=2` is used solely to distinguish zero hits, exactly one hit, and multiple matches; hit count is not a product score.

5. **Selection preference**:
   - **Preference Class 1**: Exactly-one-hit candidate where at least one witness has `CanonicalRetrievalField` in `TITLE`, `BRAND`, `MODEL_SKU`, or `MEDIA_VARIANT_LABEL`. These witness fields act as planner heuristics only and create no canonical identity or truth claims. The first observed candidate in this class is returned immediately because no later candidate can outrank it under the contract.
   - **Preference Class 2**: Exactly-one-hit candidate on any witness field (e.g., `DESCRIPTION_TEXT`, `SHOP_NAME`, `PLATFORM`, `FACT_KEY`, `FACT_VALUE`, `FACT_UNIT`, `MEDIA_ALT_TEXT`).
   - **Preference Class 3**: Candidate returning two hits, indicating multiple matches.
   - Within the same preference class, ties are resolved by longer span length, then earlier start position. Because candidate generation already follows that order, the first observed candidate in a class is its canonical representative.

6. **No-hit fallback**:
   - Zero-hit candidates are not evidence of failure and are never returned merely because they were probed.
   - If every candidate produces 0 hits and the complete question contains at most 12 lexical runs, the planner returns the complete lexical question formed by joining all retained runs with one ASCII space. This deliberate fallback enables downstream TASK-123/TASK-122 to produce an empty grounded context so TASK-129 can represent insufficient evidence.
   - If every candidate produces 0 hits and the question contains more than 12 lexical runs, the planner fails closed with `GroundedQueryPlanningError` rather than arbitrarily truncating or dropping terms.

7. **Empty corpus and determinism**:
   - An empty profile corpus is valid and follows the no-hit fallback rule.
   - Repeated calls with identical inputs and permutations of valid corpus profiles are strictly deterministic because TASK-122 retrieval ordering is corpus-order invariant and TASK-134 does not use caller corpus order as a tie-breaker.

## Non-goals and non-authoritative behavior

- **No semantic understanding or model inference**: Does not perform semantic search, entity recognition, embeddings, vector search, BM25, LLM inference, or prompt-injection defense.
- **No truth, ranking, or approval claims**: Witness field hints are lexical heuristics only; they create no product-truth claims, M2 ranking, or human approval decisions.
- **No storage or external I/O**: Pure in-memory synchronous execution without filesystem, database, network, clock, or random dependencies.
- **Conservative lexical bounds**: V1 planning is deliberately lexical and conservative; an empty downstream retrieval remains an authorized, valid outcome indicating insufficient evidence.
