# Post-M4 Product Intelligence Roadmap — Live Product Enablement

Status: canonical post-M4 architecture roadmap after TASK-136 closure  
Scope: Python Agent product architecture; AIOS-renew remains execution substrate only.

## 1. Starting point

Phase 6 M4 is canonically complete at the TASK-136 reviewed source candidate. The completed application core can reconstruct canonical knowledge after restart and answer a natural-language question through deterministic query planning, canonical grounded context, a generic `LLMProvider`, and validated `GroundedAnswer`.

The next product problem is not another RAG or answer layer. It is turning the already-built offline/canonical core into a reliable live Product Intelligence system without duplicating M2/M3/M4 authorities.

Current repository evidence establishes the following live-path gap:

- M2 already owns discovery, deterministic ranking, explicit Human approval, and the bridge that enqueues an approved product into the M1 ingestion queue.
- M1 `AgentController` still defaults to a launch-based `PlaywrightBrowserManager`, so production ingestion cannot reuse the operator's authenticated persistent Chrome session.
- `BrowserSession.evaluate` and `PlaywrightBrowserSession.evaluate` accept only `evaluate(script)`, while `ShopeeSourceExtractor` calls `evaluate(script, product_id)`. The production wrapper contract therefore does not match the deep-ingestion caller.
- Shopee/TikTok scrape tools already persist V1 `source_pack.json` under deterministic local source-pack directories and upload the same evidence to Drive.
- M3 already owns entity resolution, Human-reviewed family/variant admission, catalog integrity, SQLite durability, profiles, lexical retrieval, and grounded-context construction.
- M4 already owns grounded answer construction and persistent grounded-QA composition. These authorities must not be reopened merely to make the live path usable.

Historical TASK-126 targeted the browser/CDP gap on an older repository baseline and ended in old repair/control-plane lineage. It is not current-main architecture authority and must not be mechanically rerun or repaired. Any successor work must be authored against current main and preserve all authorities added since that baseline.

## 2. Ordered post-M4 capability boundaries

### P1 — Live Acquisition Foundation

Make the existing M1/M2 browser-backed acquisition path production-usable without changing marketplace extraction or Product Intelligence semantics.

Required outcome:

- the existing Playwright manager/session can explicitly attach to the operator-owned authenticated Chromium through CDP while preserving launch mode for isolated consumers;
- borrowed browser/context/page resources are not owned or closed by Python Agent;
- attachment fails closed and never silently falls back to a fresh browser;
- the browser-session `evaluate(script, arg)` contract matches deep-ingestion callers while preserving `evaluate(script)` compatibility;
- default `AgentController` production wiring uses the authenticated CDP path, while explicitly injected managers retain caller authority.

This is a browser/runtime integration and regression boundary only. It creates no Product Intelligence identity, ranking, evidence, catalog, retrieval, prompt, provider, or answer authority.

### P2 — Source Evidence Intake

After live acquisition is reliable, add a bounded deterministic intake surface for persisted V1 Product Source Pack manifests produced by existing scrape tools.

The intake layer may discover/index manifests only within explicit configured roots and rehydrate them through the existing Product Source Pack serialization authority. It must not create another source-pack codec, mutate evidence, infer product identity, or auto-admit catalog state.

Its output should be suitable for the existing M3 resolution/proposal workflow and for reconstructing the exact source-manifest set required by persistent grounded QA.

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

P1 is the immediate next boundary because it closes a concrete correctness and authentication gap in the already-existing M2 approval -> M1 ingestion -> Product Source Pack path. Provider certification, UI, vector search, and product-truth reconciliation do not fix the fact that the current production browser path can fail before canonical source evidence is created.

The first current-main implementation task after this audit therefore must re-author the useful intent of historical TASK-126 as a new task rather than continuing its stale lineage.

## 4. Authority invariants

Across all post-M4 work:

1. M2 remains sole discovery/ranking/Human approval authority.
2. Product Source Pack serialization/extraction semantics remain with their existing product-source modules.
3. M3 remains sole identity, catalog, persistence, profile, lexical retrieval, and grounded-context authority.
4. M4 remains sole grounded prompt/invocation/answer composition authority.
5. Browser/CDP work owns transport/lifecycle only and must not infer product truth.
6. New application layers compose existing owners; they do not create shadow stores, shadow rankings, shadow retrieval, or implicit approval paths.
7. AIOS-renew remains execution substrate and does not define Python Agent product roadmap semantics.

## 5. Naming boundary

This roadmap deliberately uses post-M4 P1-P6 labels rather than retroactively naming a Phase 6 M5. A future phase name may be introduced only if a later canonical architecture audit finds that it materially improves product governance.
