# Phase 6 M3 Completion — Persistent Product Knowledge Base

## Completed Boundary

Phase 6 M3 is complete when the full TASK-125 acceptance contract and its
phase-level Product Intelligence regression gate pass. The completed boundary is
cross-listing entity resolution, Human-approved canonical family and sellable
variant lineage, a persistent canonical product catalog, evidence-preserving
profiles, lexical retrieval, and deterministic grounded RAG knowledge that can
be rebuilt from persisted catalog and Product Source Pack inputs after restart.

TASK-125 adds only strict typed V1 Product Source Pack rehydration and the
restart-style integration proof. It does not reconcile product truth, invoke a
model, synthesize an answer, generate prompts, or implement application behavior.

## Exact Authority Map

| Task | Sole or bounded authority |
| --- | --- |
| TASK-108 | Deterministic pairwise `ProductSourcePack` entity relationship and evidence. |
| TASK-109 | Bounded multi-observation pairwise graph and family-consistency conflict reporting. |
| TASK-110 | Historical AIOS worker synchronization only; no Product Intelligence semantic authority. |
| TASK-111 | Deterministic provisional product-family grouping over an existing TASK-109 graph. |
| TASK-112 | Evidence-complete family merge proposal and explicit Human decision record. |
| TASK-113 | Canonical AIOS REPAIR worker entry only; no Product Intelligence semantic authority. |
| TASK-114 | Canonical product-family admission from exact Human approval and caller-supplied opaque ID. |
| TASK-115 | Read-only sellable-variant direct-exact evidence and exactness-gap projection. |
| TASK-116 | Evidence-complete sellable-variant proposal and explicit Human decision record. |
| TASK-117 | Canonical sellable-variant admission from exact Human approval and caller-supplied opaque ID. |
| TASK-118 | In-memory canonical catalog integrity and registration semantics. |
| TASK-119 | Canonical catalog V1 bytes and trusted catalog rehydration. |
| TASK-120 | Local SQLite catalog durability and transaction boundary over TASK-119 bytes. |
| TASK-121 | Evidence-preserving registered canonical variant profile projection. |
| TASK-122 | Deterministic in-memory lexical retrieval and exact evidence witnesses. |
| TASK-123 | Deterministic bounded grounded RAG context construction and rendering. |
| TASK-124 | Grounded-context packing integrity and fail-closed render semantics. |
| TASK-125 | Strict typed Product Source Pack V1 rehydration under the existing serialization authority, restart integration certification, and M3 phase closure. |

The Product Source Pack manifest remains owned only by
`src/product_source/serialization.py`. TASK-118 remains the catalog-integrity
authority; TASK-119 remains the catalog representation and trusted catalog
rehydration authority; TASK-120 remains the SQLite authority; TASK-121 remains
the profile authority; TASK-122 remains the retrieval authority; and
TASK-123/TASK-124 remain the grounded-context authority. No second evidence
codec, source store, profile store, retrieval store, RAG store, or shadow catalog
exists.

## Phase-Completion Verification Record

The canonical runtime owns execution and evidence for the complete original
TASK-125 delta. The repair executor does not rerun these commands or manufacture
their outcomes. M3 is complete only when the runtime records PASS for each exact
gate on the final candidate reported as `ResultPackage.result.head_sha`:

```text
python -m pytest tests/product_source/test_source_pack_serialization.py tests/product_intelligence/test_m3_persistent_knowledge_restart.py
python -m pytest tests/product_intelligence
git diff --check
```

The first command covers typed decode, strict rejection, raw-dict and serialized
V1 compatibility, deterministic ordering, URL-sanitized round trips, and the
restart proof. The second command is the one-time M3 phase-transition subsystem
gate. It does not establish a rule that every later narrow FIX or REPAIR must run
the complete subsystem suite. The third command is the final whitespace gate.

Source candidate: the exact committed SHA in the canonical execution result's
`ResultPackage.result.head_sha`. Verification results: the runtime-owned results
for the three commands above. A missing, unresolved, or non-PASS runtime result
means this completion declaration is not effective.

## Post-M3 Deferrals and M4 Boundary

Autonomous merge policy, family or variant ID allocation, migrations,
cryptographic authenticity, identity evolution, product-truth reconciliation,
preferred/latest/majority evidence selection, embeddings and vector search,
model invocation, model-driven answer synthesis, and provider-specific prompt
generation are post-M3 deferred capabilities. They are not unfinished M3
blockers and cannot be inferred from M3 data structures.

The next phase boundary is **Phase 6 M4 — Grounded Product Intelligence
Application Layer**. M4 may consume the catalog, typed source evidence, canonical
profiles, retrieval hits, and grounded context exposed by M3. It must not change
M3 product-truth, family/variant identity, catalog integrity, lexical retrieval,
or grounded-context authority. TASK-125 implements no M4 behavior.
