# Post-M4 Product Intelligence Roadmap — Live Product Enablement

Status: canonical post-M4 architecture roadmap; P1-P5 CLOSED; P6 CURRENT / IN
PROGRESS (P6.0a TASK-154 active candidate)
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
Those remain deferred non-blocking future work. Published TASK-144 subsequently
closed P4, and P5 Human-Facing Product Intelligence Surface is current.

### P4 — Live Grounded-QA Provider Certification — CLOSED

Certify the already-complete M4 generic provider path against an explicit production provider configuration. If the existing provider adapter requires modernization, that adapter work must remain provider-specific and must not change TASK-129/131/132/133/134/135 semantics.

Certification must distinguish provider/network/account availability from grounded-answer structural correctness. Retry/fallback/model-selection policy requires separate explicit authority if ever added.

P4.1 is the TASK-142 production-provider foundation only. It modernizes the
existing single `GeminiProvider` to the pinned `google-genai` transport, preserves
the generic `LLMProvider` contract and M4 authority chain, and proves message,
manual tool-declaration, and response transport offline. It does not establish
provider account, credential, quota, network, model availability, or a live
grounded answer, and it does not close P4.

TASK-143's Developer API/API-key certification lineage remains parked as
external-provider/authentication evidence and was not published as source.
TASK-144 supplies P4.2 through the same `GeminiProvider` in explicit `vertex_ai`
mode, with ADC owned by the Google SDK/google-auth boundary. Human operators
preconfigure ADC, project, API, IAM, billing/quota, and network access outside
repository code. No fallback or reroute exists between `developer_api` and
`vertex_ai`.

TASK-144 certifies one live call through TASK-135 -> TASK-133 -> TASK-132 using
the existing provider and reports provider availability separately from
TASK-132/TASK-129 grounded structural validation. It adds no retry, fallback,
provider selection, model discovery, or model-selection policy. A successful
call proves only transport availability plus the existing structural contracts;
it does not claim factual truth, semantic quality, provider SLA, or Product
Intelligence truth authority.

Published TASK-144 passed canonical Runtime verification and ChatGPT semantic
review on the same source candidate, closing P4. This closure advances only the
roadmap boundary; it does not broaden provider or Product Intelligence truth
authority.

### P5 — Human-Facing Product Intelligence Surface — CURRENT / IN PROGRESS

Add thin presentation boundaries over the existing Product Intelligence
authorities without collapsing read-only inspection, live discovery, and
Human-governed mutation into one operation.

Presentation must not become a new semantic authority. It may expose state and invoke canonical operations, but may not silently rank, approve, merge, reconcile, or rewrite evidence.

P5.1 is CLOSED by published TASK-145 after canonical Runtime PASS and ChatGPT
semantic-review PASS were recorded for the candidate: one read-only CLI over
TASK-138 persisted evidence intake, TASK-120 canonical catalog loading, and
TASK-135 persistent grounded QA through one Human-explicit existing
`GeminiProvider` backend. It adds no discovery, ranking, approval, admission,
registration, evidence write, answer persistence, provider routing, retry, or
fallback authority.

P5.2 is CLOSED by published TASK-146 after canonical Runtime PASS and ChatGPT
semantic-review PASS were recorded for the candidate: extending the Product
Intelligence CLI with one live discovery and deterministic shortlist command
(`discover`) composing the existing P1 PlaywrightBrowserManager CDP runtime,
existing Shopee/TikTok adapters, and existing M2 DiscoveryOrchestrator /
CandidateRanker vertical slice without introducing a second browser, discovery,
scoring, ranking, approval, or ingestion authority.

The remaining P5.3 boundary is refined into:

- P5.3a live-shortlist Human decision + TASK-096 M1 queue bridge is CLOSED by
  published TASK-147 after canonical Runtime PASS and ChatGPT semantic-review
  PASS: extending the Product Intelligence CLI with one bounded in-process review/action
  command (`decide`) that runs live discovery, renders the exact shortlist preview,
  accepts explicit Human position and APPROVE/REJECT action during that same
  invocation, and delegates the exact RankedCandidate object to TASK-096
  approval/queue authorities without persisting shortlists or reconstructing candidates.
- P5.3b family decision / durable admission presentation over TASK-139 / TASK-140
  is CLOSED by published TASK-148 after canonical Runtime PASS and ChatGPT semantic-review
  PASS: extending the Product Intelligence CLI with one bounded in-process review/selection/action
  command (`family-decide`) that intakes persisted source evidence through TASK-138, prepares
  one in-memory review plan through TASK-139, renders the exact plan preview, accepts
  explicit Human proposal selection and APPROVE/REJECT action during that same invocation,
  delegates the exact selected FamilyMergeProposal to TASK-140 record_planned_family_decision,
  and, only for explicit APPROVE, accepts a caller-supplied family_id and durably admits
  the family into a pre-existing SQLite catalog through TASK-140 durably_admit_planned_family.
- P5.3c sellable-variant review / decision / durable admission presentation over TASK-141
  is CLOSED by published TASK-149 after canonical Runtime PASS and ChatGPT PRIMARY
  semantic PASS on candidate `132deef99363ffce0c3162c5f59d1b1349563995`: extending the
  Product Intelligence CLI with one bounded in-process review/selection/action command
  (`variant-decide`) that loads one pre-existing canonical catalog through TASK-120,
  resolves one Human-specified existing family by exact family_id, renders that exact
  current family for Human member selection, maps explicit 1-based member positions only
  to exact member objects from that family, prepares review through TASK-141, renders the
  exact proposal preview, accepts explicit Human APPROVE/REJECT action, and, only for
  explicit APPROVE, accepts a caller-supplied variant_id and durably admits the variant
  through TASK-141.

Published TASK-149 closed P5.3c and P5 Human-Facing Product Intelligence Surface is
CLOSED. P6 is CURRENT / IN PROGRESS under the post-P5 architecture audit.

### P6 — Quality and Scale Enhancements — CURRENT / IN PROGRESS

Following the post-P5 architecture audit (recorded in `docs/POST_P5_P6_QUALITY_SCALE_ROADMAP.md`),
Phase 6 is explicitly ordered as a `certify -> evaluate -> improve` discipline:

#### P6.0 Live Real-Evidence Certification — CURRENT / IN PROGRESS
Certify live operational boundaries against real marketplace targets using operator-owned
authenticated CDP sessions before building downstream quality or scale features. Full live
production certification remains distinct from provider-only TASK-144.
- **P6.0a Successor Live Marketplace Discovery -> Persisted Product Source Pack Certification (CURRENT CANDIDATE — TASK-154)**:
  Re-established from published TASK-151 + TASK-153 hardened main. Certifies only one explicit current
  marketplace route (`shopee` or `tiktok`) discovering a candidate and persisting typed V1
  `ProductSourcePack` evidence beneath `tmp_path`, rehydrated via TASK-125.
  Historical TASK-150 (RUN-150-001..005) and TASK-152 (RUN-152-001) are preserved as failed
  historical certification evidence. Published TASK-151 (readiness polling and anchor fallback) and
  TASK-153 (nullable card mapping) hardened Shopee discovery to resolve prior blockers without
  creating new semantic authority. TASK-154 itself certifies only one explicit current marketplace
  route through real local evidence. It does not claim both marketplaces, Google Drive, Human
  approval/queue, M3 admission, grounded QA, product truth, semantic retrieval, identity migration,
  automation, or serving are certified. P6.0 remains IN PROGRESS until P6.0b is separately designed
  and certified. P6.0a is not claimed as closed until TASK-154 live verification and semantic review
  both PASS.
- **P6.0b Real-Evidence Canonical Knowledge + Grounded-QA Certification (NEXT / UNIMPLEMENTED / FUTURE)**:
  Certifies downstream intake, admission, and grounded QA on real acquired marketplace evidence.

#### P6.1 Retrieval-Quality Evaluation / Baseline — UNIMPLEMENTED / FUTURE
Establish empirical retrieval benchmarks (precision, recall, citation accuracy) using the existing
lexical retrieval baseline (TASK-122) on real product evidence before introducing any semantic retrieval.

#### P6.2 Conditional Semantic / Vector Retrieval or Reranking — UNIMPLEMENTED / FUTURE
Introduce semantic/vector retrieval or reranking only if measured P6.1 evidence justifies it.
Preserves SQLite catalog as the canonical store; vector indexes remain secondary and disposable.

#### P6.3 Product-Truth Reconciliation — UNIMPLEMENTED / FUTURE
Formulate a separate Human-governed policy authority for attribute reconciliation across observations
(e.g., preferred/latest/majority selection rules).

#### P6.4 Identity Evolution and Migrations — UNIMPLEMENTED / FUTURE
Define a separate canonical-identity authority for entity lifecycle, merging, splitting, and schema
migrations while preserving M3 integrity.

#### P6.5 Higher-Level Human-Review Automation — UNIMPLEMENTED / FUTURE
Introduce review triage assistance without removing or bypassing explicit Human approval authority.

#### P6.6 Caches and Background Serving — UNIMPLEMENTED / FUTURE
Implement performance caches and background serving infrastructure only after an observed operational
workload requires them.

## 3. Priority decision

P1 is closed by TASK-137. P2 is closed by TASK-138: persisted Product Source Pack evidence is now discoverable through an explicit-root, bounded local intake, and current downstream consumers can receive either typed `ProductSourcePack` values or the aligned explicit manifest paths without duplicating filesystem discovery.

P3 is closed (TASK-139, TASK-140, TASK-141). P4 is closed (TASK-142, TASK-144).
P5 is CLOSED: published TASK-145 closed P5.1, published TASK-146 closed P5.2,
published TASK-147 closed P5.3a, published TASK-148 closed P5.3b, and published
TASK-149 closed P5.3c after canonical Runtime PASS and ChatGPT PRIMARY semantic PASS
on source candidate `132deef99363ffce0c3162c5f59d1b1349563995`.

P6 is CURRENT / IN PROGRESS under the post-P5 quality and scale architecture audit
(`docs/POST_P5_P6_QUALITY_SCALE_ROADMAP.md`). P6.0 Live Real-Evidence Certification is
CURRENT. Published TASK-151 hardened live Shopee discovery readiness and published TASK-153
hardened live Shopee card mapping. TASK-150 and TASK-152 remain failed historical certification
evidence. TASK-154 is the current P6.0a successor candidate (Live Marketplace Discovery ->
Persisted Product Source Pack Certification) on the published TASK-151 + TASK-153 hardened baseline.
TASK-154 itself certifies only one explicit current marketplace route through real local evidence.
P6.0 remains IN PROGRESS pending separate P6.0b real-evidence knowledge/grounded-QA certification.
Avoid claiming P6.0a is closed until this task's live verification and semantic review both PASS.

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
