# Post-M4 Product Intelligence Roadmap — Live Product Enablement

Status: canonical post-M4 architecture roadmap; P3 CLOSED by TASK-139 P3.1,
TASK-140 P3.2, and TASK-141 P3.3; P4 Live Grounded-QA Provider Certification is
the next current boundary
Scope: Python Agent product architecture; AIOS-renew remains execution substrate only.

## 1. Starting point

Phase 6 M4 is canonically complete at the TASK-136 reviewed source candidate. TASK-137 subsequently closed P1 Live Acquisition Foundation by repairing the current browser runtime so production AgentController wiring can explicitly attach to the operator-owned authenticated Chromium through CDP, while retaining isolated launch mode and the existing Product Source Pack semantics.

The completed application core can reconstruct canonical knowledge after restart and answer a natural-language question through deterministic query planning, canonical grounded context, a generic `LLMProvider`, and validated `GroundedAnswer`.

TASK-138 subsequently closed the boundary between persisted live acquisition evidence and the already-built M3/M4 core. Existing Shopee/TikTok scrape tools persist V1 `source_pack.json` manifests under deterministic local source-pack directories, and the P2 intake now locates those manifests only beneath explicit local roots and returns the discovered set as aligned paths and typed packs.

Current repository evidence establishes:

- M2 already owns discovery, deterministic ranking, explicit Human approval, and the bridge that enqueues an approved product into the M1 ingestion queue.
- TASK-137 owns only the repaired live browser/CDP transport and browser-session contract; it creates no Product Intelligence evidence or identity authority.
- Shopee/TikTok scrape tools already persist V1 `source_pack.json` under deterministic local source-pack directories and upload the same evidence to Drive.
- TASK-125 remains the sole typed Product Source Pack persisted-evidence rehydration authority.
- M3 already owns entity resolution, Human-reviewed family/variant admission, catalog integrity, SQLite durability, profiles, lexical retrieval, and grounded-context construction.
- TASK-135 already owns persistent grounded-QA composition from an explicit caller-supplied manifest path set; it intentionally performs no filesystem discovery.
- M4 already owns grounded answer construction and persistent grounded-QA composition. These authorities must not be reopened merely to make persisted evidence discoverable.

Historical TASK-126 remains stale lineage and is superseded only in useful browser intent by the published TASK-137 source candidate. It must not be mechanically rerun or repaired.

## 2. Ordered post-M4 capability boundaries

### P1 — Live Acquisition Foundation — CLOSED

TASK-137 completed this boundary.

Outcome:

- the existing Playwright manager/session can explicitly attach to the operator-owned authenticated Chromium through CDP while preserving launch mode for isolated consumers;
- borrowed browser/context/page resources are not owned or closed by Python Agent;
- attachment fails closed and never silently falls back to a fresh browser;
- the browser-session `evaluate(script, arg)` contract matches deep-ingestion callers while preserving `evaluate(script)` compatibility;
- default `AgentController` production wiring uses the authenticated CDP path, while explicitly injected managers retain caller authority.

This remains a browser/runtime integration authority only. It creates no Product Intelligence identity, ranking, evidence, catalog, retrieval, prompt, provider, or answer authority.

### P2 — Source Evidence Intake — CLOSED

TASK-138 completed this boundary by adding one bounded deterministic local-filesystem intake surface for persisted V1 Product Source Pack manifests produced by existing scrape tools.

Required outcome:

- callers provide explicit local root directories; intake never scans outside those configured roots;
- intake recursively discovers only exact `source_pack.json` manifest files and produces a deterministic immutable manifest inventory independent of filesystem enumeration order and caller root ordering;
- every discovered manifest is typed-rehydrated only through TASK-125 `deserialize_product_source_pack`;
- the inventory exposes aligned exact manifest paths and typed `ProductSourcePack` values, so the typed packs can enter existing M3 resolution/proposal workflows while the exact manifest path tuple can be supplied to TASK-135 persistent grounded QA;
- duplicate exact source observations or ambiguous/out-of-root filesystem aliases fail closed rather than silently duplicating evidence;
- no second codec, registry database, shadow catalog, identity inference, evidence mutation, Drive enumeration, network download, auto-admission, or product-truth reconciliation is introduced.

P2 owns only **bounded manifest discovery + deterministic immutable intake inventory**. Product Source Pack schema/rehydration remains TASK-125 authority; source identity remains existing M3 authority; catalog/admission remains existing Human-governed M3 authority.

### P3 — Human-Governed Knowledge Update Workflow — CLOSED

Compose existing M3 authorities into an application workflow that takes newly ingested typed source observations through existing resolution/grouping/proposal boundaries, exposes required Human family/variant decisions, and persists only explicitly approved canonical admissions through TASK-118/119/120 authority.

This layer must orchestrate existing boundaries; it must not replace Human approval, auto-generate canonical IDs unless a separate explicit authority is designed, reconcile product truth, or create a second catalog/persistence model.

P3.1 Family Review Planning is closed by TASK-139. It composes one exact TASK-138
inventory through TASK-109 resolution, TASK-111 grouping, and TASK-112 actionable
proposal construction while retaining all groups for Human review. It creates no
Human decision, canonical family or variant, ID, catalog mutation, or durable write.

P3.2 Family Decision + Durable Admission is closed by TASK-140. It binds an
explicit Human decision to one exact proposal retained by a P3.1 plan, delegates
decision semantics to TASK-112, family admission and caller-supplied opaque
`family_id` semantics to TASK-114, catalog integrity to TASK-118, codec semantics
to TASK-119, and SQLite durability to TASK-120. A `REJECT` has no independent
durable history authority and cannot mutate the catalog through this boundary.

P3.3 Sellable-Variant Review + Durable Admission is closed by TASK-141. It wraps
the exact TASK-116 proposal in a factory-only Human review value, delegates the
explicit Human decision unchanged to TASK-116, proves exact proposal object
lineage, then delegates canonical admission with the caller-supplied opaque
`variant_id` to TASK-117 and durable registration to TASK-120. TASK-115 remains
the sole sellable-variant evidence and diagnostic authority; TASK-116 remains
the sole selection/proposal/Human-decision authority; TASK-117 remains the sole
canonical variant-admission and variant-ID validation authority; and
TASK-118/119/120 retain catalog integrity, codec/rehydration, and SQLite
transaction/durability authority respectively. Variant `REJECT` has no durable
mutation or independent durable-history authority.

P3 closure does not claim family or variant ID allocation, identity evolution
or membership extension, conflict repair or singleton family admission,
product-truth reconciliation, durable REJECT history, or autonomous approval.
Those remain deferred non-blocking future work. P4 Live Grounded-QA Provider
Certification is now the next current post-M4 boundary.

### P4 — Live Grounded-QA Provider Certification

Certify the already-complete M4 generic provider path against an explicit production provider configuration. If the existing provider adapter requires modernization, that adapter work must remain provider-specific and must not change TASK-129/131/132/133/134/135 semantics.

Certification must distinguish provider/network/account availability from grounded-answer structural correctness. Retry/fallback/model-selection policy requires separate explicit authority if ever added.

### P5 — Human-Facing Product Intelligence Surface

Add a thin CLI/API/application presentation boundary over the existing discovery, ranking, approval, evidence-intake, canonical-knowledge, and grounded-QA services.

Presentation must not become a new semantic authority. It may expose state and invoke canonical operations, but may not silently rank, approve, merge, reconcile, or rewrite evidence.

### P6 — Quality and Scale Enhancements

Only after the live vertical slice is operating with real evidence should later work consider:

- semantic/vector retrieval or reranking;
- product-truth reconciliation and preferred/latest/majority selection;
- identity evolution and migrations;
- caches/registries and background serving;
- higher-level automation around Human review;
- live end-to-end production certification.

These are not blockers for P1-P5 and must each receive a separate authority audit before implementation.

## 3. Priority decision

P1 is closed by TASK-137. P2 is closed by TASK-138: persisted Product Source Pack evidence is now discoverable through an explicit-root, bounded local intake, and current downstream consumers can receive either typed `ProductSourcePack` values or the aligned explicit manifest paths without duplicating filesystem discovery.

P3 is closed. TASK-139 closes P3.1 family review planning, TASK-140 closes P3.2
family decision plus durable family admission, and TASK-141 closes P3.3 explicit
sellable-variant review, Human decision, and durable admission while preserving
TASK-115/116/117/118/119/120 authority. M3 remains the sole identity, catalog,
persistence, and evidence authority; P3 remains application composition rather
than a replacement semantic layer. P4 Live Grounded-QA Provider Certification
is the next current post-M4 boundary.

## 4. Authority invariants

Across all post-M4 work:

1. M2 remains sole discovery/ranking/Human approval authority.
2. Product Source Pack serialization/extraction and TASK-125 typed rehydration semantics remain with their existing product-source modules.
3. P2 may own only bounded configured-root manifest discovery and immutable inventory composition; it must not create a second evidence store/codec or identity authority.
4. M3 remains sole identity, catalog, persistence, profile, lexical retrieval, and grounded-context authority.
5. M4 remains sole grounded prompt/invocation/answer composition authority.
6. Browser/CDP work owns transport/lifecycle only and must not infer product truth.
7. New application layers compose existing owners; they do not create shadow stores, shadow rankings, shadow retrieval, or implicit approval paths.
8. AIOS-renew remains execution substrate and does not define Python Agent product roadmap semantics.

## 5. Naming boundary

This roadmap deliberately uses post-M4 P1-P6 labels rather than retroactively naming a Phase 6 M5. A future phase name may be introduced only if a later canonical architecture audit finds that it materially improves product governance.
