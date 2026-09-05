# Phase 6 M4.6 — Persistent Grounded QA Application Boundary

## Purpose and public API

TASK-135 provides the Phase 6 M4.6 bounded persistent application boundary that starts from an existing TASK-120 SQLite canonical catalog and an explicit caller-supplied collection of persisted Product Source Pack manifests, reconstructs the exact canonical variant profile corpus through existing M3 authorities, derives one TASK-134 `retrieval_query`, builds one TASK-123 `CanonicalRagContext`, and delegates grounded answer generation to TASK-133.

The public surface consists of exactly:

- `PersistentGroundedQaError`
- `async def answer_persisted_grounded_question(database_path, source_pack_paths, *, question, provider, max_hits=5, max_context_utf8_bytes=32768) -> GroundedAnswer`

The function is composition and startup authority only. It introduces no service class, startup object, profile-loader result, query-plan result, mutable session, configuration type, or second answer wrapper.

## Authority boundaries and chain

The authority chain across persisted knowledge, query planning, retrieval, and grounded QA is strictly delineated:

| Authority | Ownership |
| --- | --- |
| TASK-120 | Loads the canonical catalog snapshot from SQLite (`load_sqlite_canonical_catalog`). |
| TASK-125 | Rehydrates explicit persisted source evidence from `source_pack.json` files (`deserialize_product_source_pack`). |
| `SourceObservationIdentity` | Supplies exact source identity projection (`SourceObservationIdentity.from_pack`). |
| TASK-121 | Builds `CanonicalVariantProfile` instances for each registered variant (`build_canonical_variant_profile`). |
| TASK-134 | Plans the lexical `retrieval_query` from profile corpus and question (`plan_grounded_retrieval_query`). |
| TASK-123 | Builds `CanonicalRagContext` and executes canonical retrieval (`build_canonical_rag_context`). |
| TASK-133 | Owns prompt package -> model invocation -> validated `GroundedAnswer` composition (`answer_grounded_context`). |
| TASK-135 | Owns only persistent startup, input-completeness validation, and predecessor call order. |

TASK-135 adds zero persistence mechanisms, storage formats, identity schemas, retrieval methods, prompt packages, or answer types.

## Canonical startup and execution sequence

The application entry point performs exactly this sequence:

1. **Load catalog**: Call `load_sqlite_canonical_catalog(database_path)` exactly once to obtain `CanonicalCatalogState`. TASK-135 does not inspect SQLite directly, open raw connections, decode catalog bytes, create missing databases, or register entities.
2. **Materialize manifest paths**: Materialize `source_pack_paths` once from the caller iterable into a tuple of exact non-empty strings. Non-iterable or invalid member shapes fail closed with `PersistentGroundedQaError`.
3. **Rehydrate source packs**: Typed-rehydrate each manifest path exactly once in caller order via `deserialize_product_source_pack(path)`. No globbing, scanning, sibling discovery, or raw JSON parsing is performed.
4. **Project identities and enforce completeness**:
   - Derive each pack's identity via `SourceObservationIdentity.from_pack(pack)`.
   - Ensure supplied source identities contain no duplicates.
   - Enforce exact 1-to-1 completeness: every supplied identity must match exactly one registered member of one catalog variant, and every registered variant member must have exactly one matching supplied manifest.
   - Missing, duplicate, or supplied-but-unbound identities fail closed with `PersistentGroundedQaError`.
5. **Construct profile corpus**: Build `CanonicalVariantProfile` instances in exact `catalog.variants` order. For each variant, collect source packs in exact `variant.members` order and call `build_canonical_variant_profile(catalog, variant_id=variant.variant_id, source_packs=variant_packs)` exactly once.
6. **Plan retrieval query**: Call `plan_grounded_retrieval_query(profiles, question=question)` exactly once with the reconstructed profile corpus and caller question.
7. **Build canonical RAG context**: Call `build_canonical_rag_context(profiles, question=question, retrieval_query=planned_query, max_hits=max_hits, max_context_utf8_bytes=max_context_utf8_bytes)` exactly once, passing inputs through unchanged so TASK-123 retains validation and context semantics.
8. **Delegate grounded QA**: Call `await answer_grounded_context(context, provider)` exactly once and return the exact `GroundedAnswer`.

## Manifest path input and deferred discovery

Explicit manifest paths are V1 caller input. Automatic filesystem discovery, globbing, directory scanning, Google Drive enumeration, and manifest registries remain deferred. The caller is responsible for supplying the exact set of manifest file paths corresponding to the registered catalog variants.

## Invariance to manifest permutation

For value-equal persisted inputs, permuting `source_pack_paths` does not alter profile corpus ordering, planned retrieval queries, canonical context, or downstream grounded answers. Profile ordering is rooted strictly in canonical `catalog.variants` order and variant evidence is bound in canonical `variant.members` order, completely independent of caller manifest path order.

## Error handling and predecessor authority preservation

`PersistentGroundedQaError` is reserved strictly for TASK-135 input-completeness and manifest-list shape failures.

Predecessor exceptions and cancellation propagate without being caught, wrapped, or reclassified:
- `CanonicalCatalogStorageError` from TASK-120
- Filesystem/JSON/schema errors from TASK-125
- `CanonicalVariantProfileError` from TASK-121
- `GroundedQueryPlanningError` from TASK-134
- `CanonicalRagContextError` from TASK-123
- `GroundedPromptError`, `GroundedInvocationError`, and `GroundedAnswerError` from M4 authorities
- Provider failures and `asyncio.CancelledError`

## Non-goals and non-authoritative behavior

- **No semantic understanding or factual correctness**: TASK-135 does not claim semantic understanding, factual correctness, product truth, or hallucination freedom.
- **No prompt-injection immunity**: Prompt injection defense is outside the application boundary.
- **No recommendation or approval authority**: Returned answers are structured grounded QA responses, not M2 purchase recommendations or human approval decisions.
- **No live-provider certification**: Provider certification and live networking remain deferred; tests use deterministic fakes and offline mocks.
- **No mutations or writes**: Execution performs zero catalog writes, manifest writes, directory creations, or state mutations.
