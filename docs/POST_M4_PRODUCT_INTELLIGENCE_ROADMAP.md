# Post-M4 Product Intelligence Roadmap — Live Product Enablement

Status: canonical post-M4 architecture roadmap after TASK-137 P1 closure  
Scope: Python Agent product architecture; AIOS-renew remains execution substrate only.

## 1. Starting point

Phase 6 M4 is canonically complete at the TASK-136 reviewed source candidate. TASK-137 subsequently closed P1 Live Acquisition Foundation by repairing the current browser runtime so production AgentController wiring can explicitly attach to the operator-owned authenticated Chromium through CDP, while retaining isolated launch mode and the existing Product Source Pack semantics.

The completed application core can reconstruct canonical knowledge after restart and answer a natural-language question through deterministic query planning, canonical grounded context, a generic `LLMProvider`, and validated `GroundedAnswer`.

The current product problem is now the boundary between persisted live acquisition evidence and the already-built M3/M4 core. Existing Shopee/TikTok scrape tools already persist V1 `source_pack.json` manifests under deterministic local source-pack directories and return each exact `manifest_path`, but callers must still manually locate those manifests before they can use TASK-125 typed rehydration, M3 resolution, or TASK-135 persistent grounded QA.

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

### P2 — Source Evidence Intake — CURRENT

Add one bounded deterministic local-filesystem intake surface for persisted V1 Product Source Pack manifests produced by existing scrape tools.

Required outcome:

- callers provide explicit local root directories; intake never scans outside those configured roots;
- intake recursively discovers only exact `source_pack.json` manifest files and produces a deterministic immutable manifest inventory independent of filesystem enumeration order and caller root ordering;
- every discovered manifest is typed-rehydrated only through TASK-125 `deserialize_product_source_pack`;
- the inventory exposes aligned exact manifest paths and typed `ProductSourcePack` values, so the typed packs can enter existing M3 resolution/proposal workflows while the exact manifest path tuple can be supplied to TASK-135 persistent grounded QA;
- duplicate exact source observations or ambiguous/out-of-root filesystem aliases fail closed rather than silently duplicating evidence;
- no second codec, registry database, shadow catalog, identity inference, evidence mutation, Drive enumeration, network download, auto-admission, or product-truth reconciliation is introduced.

P2 owns only **bounded manifest discovery + deterministic immutable intake inventory**. Product Source Pack schema/rehydration remains TASK-125 authority; source identity remains existing M3 authority; catalog/admission remains existing Human-governed M3 authority.

### P3 — Human-Governed Knowledge Update Workflow

Compose existing M3 authorities into an application workflow that takes newly ingested typed source observations through existing resolution/grouping/proposal boundaries, exposes required Human family/variant decisions, and persists only explicitly approved canonical admissions through TASK-118/119/120 authority.

This layer must orchestrate existing boundaries; it must not replace Human approval, auto-generate canonical IDs unless a separate explicit authority is designed, reconcile product truth, or create a second catalog/persistence model.

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

P1 is closed by TASK-137. P2 is the immediate current boundary because persisted Product Source Pack evidence already exists locally, while current downstream consumers either require typed `ProductSourcePack` values or explicit manifest paths and no current authority owns bounded filesystem discovery/inventory.

P2 therefore closes a concrete composition gap without reopening browser extraction, Product Source Pack serialization, M3 identity/catalog semantics, or M4 grounded-QA semantics.

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