# Phase 6 M4 — Grounded Product Intelligence Application Layer: Grounded Answer Contract

## 1. Overview & System Boundaries

Phase 6 M4 introduces the application layer for Product Intelligence, allowing downstream callers and models to query canonical product knowledge.

TASK-129 establishes the first domain contract of Phase 6 M4: an immutable, deterministic `GroundedAnswer` bound directly to an exact `CanonicalRagContext` (established in TASK-123/TASK-124). This boundary enforces strict structural grounding: validating types, text bounds, context-local provenance addresses, leaf-citation minimums, and limitation requirements.

TASK-129 performs zero model invocation, zero provider calls, zero prompt packaging, zero file/database/network I/O, and zero mutation of canonical product knowledge.

---

## 2. Exact Authority Map

| Subsystem / Task | Scope & Authority |
| --- | --- |
| **M2 Discovery, Scoring, Ranking & Approval** (`WinningProductScorer`, `CandidateRanker` / `TASK-095`, `ApprovalRecord` / `TASK-096`) | `WinningProductScorer`, `CandidateRanker` (`TASK-095`), and Human approval (`ApprovalRecord`, `TASK-096`). Sole authority for product discovery, scoring policies, ranking candidates, advisory shortlists, and human ingestion approval decisions. M4 answer statuses, citations, limitations, or text **must never** become a second scoring, ranking, or approval authority. |
| **M3 Knowledge Base** (`TASK-108`..`TASK-125`) | Cross-listing entity resolution, canonical family/variant admissions, persistent SQLite catalog, variant profiles, deterministic lexical retrieval (`TASK-122`), and bounded grounded RAG context construction and rendering (`TASK-123`/`TASK-124`). M3 owns canonical family/variant identity and catalog persistence plus evidence-preserving profiles, lexical retrieval, and grounded context packaging; conflicting evidence remains plural and product-truth reconciliation or preferred/latest/majority selection remains deferred. |
| **TASK-129 (M4.1 Grounded Answer)** | Sole authority for the immutable `GroundedAnswer` data structure, `GroundedAnswerStatus` enum, and deterministic structural validation via `create_grounded_answer`. Owns structural binding of application answers to supplied canonical RAG contexts. |

---

## 3. `GroundedAnswerStatus` Application Semantics

`GroundedAnswerStatus` defines exactly three application-level answer states:

1. `ANSWERED`: The context contained sufficient evidence to answer the question, backed by at least one valid witness or supplemental evidence leaf citation.
2. `INSUFFICIENT_EVIDENCE`: The context did not contain enough evidence to answer the question (including no-hit retrieval results or incomplete evidence). Requires at least one limitation explaining the gap; permits zero or more valid citations.
3. `CONFLICTING_EVIDENCE`: The context contained conflicting evidence across sources or observations. Requires at least two distinct valid leaf citations demonstrating the conflict and at least one limitation.

> [!IMPORTANT]
> `GroundedAnswerStatus` values are **application-answer states only**. They do not constitute canonical product truth, do not resolve source conflicts, and do not imply an M2 business recommendation or ingestion approval decision.

---

## 4. Structural Grounding vs. Semantic Entailment

TASK-129 enforces **structural grounding**, not automated semantic entailment or factual truth:

- **What TASK-129 Proves**:
  - The answer is bound to an exact, unmutated `CanonicalRagContext`.
  - All citation identifiers exist as valid addresses within that context (hit headers, retrieval witnesses, or retained supplemental evidence blocks).
  - Minimum leaf-citation counts are satisfied for the given status (`ANSWERED` $\ge 1$, `CONFLICTING_EVIDENCE` $\ge 2$).
  - Limitations are present for non-answer statuses and strictly bounded in count and byte length.
  - Text fields meet non-blank and UTF-8 byte bounds.

- **What TASK-129 Explicitly Does NOT Claim or Prove**:
  - It does **not** prove that natural-language answer text is semantically entailed by the cited evidence.
  - It does **not** guarantee factual correctness, completeness, or freedom from hallucination.
  - It does **not** interpret, reconcile, or pick a "true" value among conflicting source observations.
  - It does **not** evaluate whether the citation actually supports the claim made in the text.

---

## 5. Untrusted Evidence & Instruction Security

Under TASK-123 and TASK-124, all evidence originating from external marketplaces is treated as untrusted data.

TASK-129 strictly preserves this principle:
- Evidence strings and answer text are treated purely as inert data values.
- Answer construction never parses, executes, or interpolates evidence or answer text into executable code or instructions.
- TASK-129 provides no prompt-injection immunity guarantee and no instruction-execution semantics.

---

## 6. Data Contracts & Validation Rules

### `GroundedAnswer` (`src/product_intelligence/grounded_answer.py`)

An immutable frozen dataclass containing exactly five fields:
- `context`: `CanonicalRagContext` (retains exact supplied object identity).
- `status`: `GroundedAnswerStatus` (`ANSWERED`, `INSUFFICIENT_EVIDENCE`, `CONFLICTING_EVIDENCE`).
- `answer_text`: `str` (preserved byte-for-byte, $\le 32768$ UTF-8 bytes, non-blank).
- `citation_ids`: `tuple[str, ...]` (ordered, unique context-local citation addresses).
- `limitations`: `tuple[str, ...]` (ordered strings, $0 \le \text{count} \le 16$, each $\le 2048$ UTF-8 bytes).

### `create_grounded_answer` Validation Invariants

1. **Exact Types**:
   - `context`: exact `CanonicalRagContext` (no subclasses or coercions).
   - `status`: exact `GroundedAnswerStatus` (no strings or integers).
   - `answer_text`: exact `str`.
   - `citation_ids`: exact `tuple[str, ...]`.
   - `limitations`: exact `tuple[str, ...]`.

2. **Answer Text Bounds**:
   - Must contain at least one non-whitespace character.
   - UTF-8 byte length must not exceed 32,768 bytes.
   - Text is stored byte-for-byte without stripping or normalization.

3. **Citation Address Resolution**:
   - Valid hit address: `hit_context.citation_id` (e.g. `H001`).
   - Valid witness address: derived as `<hit>-W001...` in exact witness order (e.g. `H001-W001`).
   - Valid supplemental evidence address: `block.citation_id` for retained blocks (e.g. `H001-E001`).
   - Omitted evidence (omitted due to M3 byte budgeting) cannot be cited and fails closed.
   - Citations referencing other contexts, fabricated addresses, or malformed strings fail closed.
   - Citations must be unique; duplicate citations fail closed. Caller order is preserved.

4. **Leaf Citation Rules**:
   - A leaf citation is a retrieval witness address or retained supplemental evidence address (hit headers alone are not leaf citations).
   - `ANSWERED`: Requires at least 1 valid leaf citation.
   - `CONFLICTING_EVIDENCE`: Requires at least 2 distinct valid leaf citations.
   - `INSUFFICIENT_EVIDENCE`: Permits 0 or more valid citations.

5. **Limitation Rules**:
   - Non-answer statuses (`INSUFFICIENT_EVIDENCE`, `CONFLICTING_EVIDENCE`) require at least 1 limitation.
   - `ANSWERED` may have 0 limitations.
   - Maximum 16 limitations.
   - Each limitation item must be a non-empty, non-whitespace string of at most 2,048 UTF-8 bytes.
   - Caller order is preserved; limitation text is not deduplicated, normalized, or interpreted.

---

## 7. Durable M4 Milestone Status

TASK-129 originally deferred six capabilities so that each could receive one
bounded owner. The roadmap is now mapped without changing TASK-129's answer
contract or structural-grounding authority:

| Original deferred capability | Milestone owner and status |
| --- | --- |
| Deterministic prompt packaging for provider models | TASK-131 implements deterministic provider-neutral prompt packaging. |
| Generic `LLMProvider` invocation | TASK-132 implements exactly-one generic provider invocation and syntactic response parsing. |
| Grounded QA service and question-answering composition | TASK-133 implements context-to-answer composition while preserving TASK-129 final validation. |
| Natural-question retrieval-query planning | TASK-134 implements deterministic lexical `retrieval_query` planning. |
| Restart-capable persistent application orchestration | TASK-135 implements the persisted-catalog and explicit-manifest application boundary. |
| M4 end-to-end vertical-slice certification | TASK-136 records and certifies the existing TASK-135 offline vertical slice, effective only after canonical Runtime PASS and semantic review PASS. |

When both TASK-136 gates PASS, TASK-131 through TASK-136 close every item in the
original TASK-129 M4 deferred roadmap. Certification is then not an ambiguous
open M4 item. TASK-136 adds no runtime behavior and does not alter the
`GroundedAnswer` data, status, citation, limitation, or validation semantics in
this document.
