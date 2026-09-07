# Post-P5 P6 Quality and Scale Roadmap

Status: **CANONICAL POST-P5 AUDIT RESULT; P6 CURRENT / IN PROGRESS**
Current boundary: **P6.0 Live Real-Evidence Certification (CURRENT)**
Current candidate: **P6.0a TASK-150 Live Marketplace Discovery -> Persisted Product Source Pack Certification**

## 1. Post-P5 Audit Context

Following the completion of P1 through P5, the repository possesses complete, tested, and
published vertical capabilities across all baseline Product Intelligence stages:
- **P1 Live Acquisition Foundation (CLOSED via TASK-137)**: Authenticated CDP attachment to operator-owned Chromium.
- **P2 Source Evidence Intake (CLOSED via TASK-138)**: Bounded local-filesystem intake for persisted V1 `source_pack.json` manifests.
- **P3 Human-Governed Knowledge Update Workflow (CLOSED via TASK-139, TASK-140, TASK-141)**: Human review and durable SQLite admission of canonical families and sellable variants.
- **P4 Live Grounded-QA Provider Certification (CLOSED via TASK-144)**: Vertex AI ADC provider certification for grounded QA.
- **P5 Human-Facing Product Intelligence Surface (CLOSED via TASK-145, TASK-146, TASK-147, TASK-148, TASK-149)**: Seven-command CLI (`evidence`, `catalog`, `ask`, `discover`, `decide`, `family-decide`, `variant-decide`).

However, the post-P5 audit reveals a critical empirical gap: although each individual module
has been proven offline and provider connectivity was certified in isolation (TASK-144), the
end-to-end acquisition pipeline has not yet been certified on live marketplace listings to prove
that real discovery produces genuine, persisted, typed `ProductSourcePack` evidence.

Attempting to introduce semantic retrieval, vector search, product-truth reconciliation, identity
migrations, automated review, or background serving before acquiring and evaluating real evidence
would introduce architectural bloat without empirical justification.

Therefore, Phase 6 is canonically ordered into three sequential disciplines:
```
CERTIFY  -->  EVALUATE  -->  IMPROVE
```

## 2. Ordered P6 Capability Boundaries

### P6.0 Live Real-Evidence Certification — CURRENT / IN PROGRESS

Certify the live operational boundaries against real marketplace targets using operator-owned
authenticated CDP sessions before building quality or scale features on top of simulated data.

Live full production certification remains distinct from provider-only TASK-144 (which verified
only the Vertex AI LLM invocation transport).

- **P6.0a Live Marketplace Discovery -> Persisted Product Source Pack Certification (CURRENT CANDIDATE — TASK-150)**:
  Certifies that one explicit live marketplace route (`shopee` or `tiktok`) using the existing
  CDP browser manager, existing discovery adapter, and existing platform scrape tool can discover
  a real candidate listing and persist a valid, typed V1 `ProductSourcePack` locally beneath
  `tmp_path`. Rehydration is strictly verified through TASK-125 `deserialize_product_source_pack`.
  Google Drive publication is satisfied by a test-only zero-network Drive sink and is deliberately
  not certified. TASK-150 certifies only one explicit marketplace route at a time; P6.0 remains
  IN PROGRESS upon TASK-150 completion.

- **P6.0b Real-Evidence Canonical Knowledge + Grounded-QA Certification (UNIMPLEMENTED / FUTURE)**:
  Certifies the downstream ingestion slice on real marketplace evidence: intaking real persisted
  source packs via TASK-138, admitting them into canonical SQLite catalog state via P3 / M3,
  and executing persistent grounded QA via TASK-135 against real evidence. P6.0 reaches CLOSED
  status only after P6.0b certification is designed and successfully executed.

### P6.1 Retrieval-Quality Evaluation / Baseline — UNIMPLEMENTED / FUTURE

Establish rigorous, reproducible evaluation baselines for retrieval quality on real acquired
product evidence before introducing any new retrieval paradigm.

- Measure baseline precision, recall, and grounded-answer citation fidelity using the existing
  deterministic lexical retrieval engine (TASK-122).
- Create gold-standard query and grounded-QA evaluation benchmarks on real persisted product packs.
- Prohibit introducing semantic/vector retrieval before empirical evidence demonstrates measurable
  deficiencies in lexical retrieval that vector search specifically remedies.

### P6.2 Conditional Semantic / Vector Retrieval or Reranking — UNIMPLEMENTED / FUTURE

Introduce semantic retrieval (e.g., embeddings, vector index, ANN, semantic reranking) **only if**
the measured P6.1 evaluation evidence justifies it.

- Any semantic index must remain a derivative, disposable secondary index; it must never become
  the canonical store of product knowledge or supersede SQLite durability (TASK-120).
- Lexical retrieval must remain available as a deterministic fallback.
- No vector database, external service, or background indexing daemon may be introduced without
  prior architectural authorization and evidence-backed necessity.

### P6.3 Product-Truth Reconciliation — UNIMPLEMENTED / FUTURE

Formulate a separate, explicit Human-governed policy authority for reconciling conflicting product
attributes across multiple source observations (e.g., conflicting titles, specifications, brands,
or variant models).

- Define deterministic conflict resolution rules (e.g., explicit provenance preference, latest
  observation timestamp, or Human override).
- Reconciled truth policies must remain decoupled from evidence capture: raw source pack facts
  must remain immutable and byte-preserving.
- TASK-150 and P6.0 implement zero product-truth reconciliation.

### P6.4 Identity Evolution and Migrations — UNIMPLEMENTED / FUTURE

Define a canonical identity evolution and schema migration authority for long-term catalog lifecycle.

- Handle merge, split, deprecation, and historical lineage tracking for canonical product families
  and sellable variants across schema versions.
- Ensure backwards-compatible rehydration and referential integrity across historical SQLite
  databases.
- Preserve existing M3 / TASK-117 / TASK-118 invariants.

### P6.5 Higher-Level Human-Review Automation — UNIMPLEMENTED / FUTURE

Introduce higher-level automation to assist the Human review workflow without removing or diluting
explicit Human approval authority.

- Triage assistance: grouping, sorting, and highlighting high-confidence merge proposals to optimize
  operator attention.
- Autonomous approval remains strictly forbidden; every canonical admission must retain explicit
  Human actor attribution and immutable decision records (TASK-140, TASK-141).

### P6.6 Caches and Background Serving — UNIMPLEMENTED / FUTURE

Implement performance caching and background serving infrastructure only after observed operational
workloads require them.

- Introduce in-memory or persisted query result caches only when profiling demonstrates latency
  or throughput bottlenecks in live environments.
- Maintain strict cache invalidation boundaries tied to SQLite catalog mutation transactions.
- Zero cache or background server infrastructure is permitted during P6.0.

## 3. Invariants and Authority Preservation

1. **Prior Authority Invariance**: P1 through P5 authorities remain unchanged and respected:
   - CDP transport/session lifecycle remains TASK-137 authority.
   - Discovery/ranking/shortlisting remains TASK-146 / M2 authority.
   - Evidence packaging remains TASK-125 / M1 authority.
   - Canonical entity resolution and admission remains M3 / P3 authority.
   - Grounded QA and prompt construction remains M4 authority.
   - Human-facing presentation remains P5 authority.
2. **Certification Isolation**: Live certification fixtures are certification-only modules
   (`tests/integration/`) and must never be imported by production Python code or define new APIs.
3. **Fail-Closed Governance**: Live test fixtures must fail closed with sanitized error categories
   without leaking marketplace credentials, session tokens, URLs, or raw HTML into outputs.
4. **Step-by-Step Evolution**: No stage in P6 may be bypassed. Optimization and scale follow
   empirical evaluation; evaluation follows real-evidence certification.
