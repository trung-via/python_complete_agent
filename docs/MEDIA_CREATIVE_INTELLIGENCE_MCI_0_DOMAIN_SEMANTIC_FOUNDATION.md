# Media/Creative Intelligence (MCI.0) Domain Semantic Foundation

TASK-271 revision 1 canonicalizes `MCI.0_DOMAIN_SEMANTIC_FOUNDATION` as the bounded semantic foundation of the Human-selected `MEDIA_CREATIVE_INTELLIGENCE` domain following exact reviewed TASK-270 publication (`fd2a07fcf5e4634ac0dcf6b1aa1d9f9c8dae9b11`).

This task is classified strictly as `MCI_0_DOMAIN_SEMANTIC_FOUNDATION_ONLY`. It defines semantic architecture, conceptual boundaries, and governance constraints only. It authorizes and implements **zero production Python code under `src/`**, creates no `media_creative_intelligence` executable package, selects no providers or models, generates no media assets, and performs no distribution, scoring, campaign, market-test, or commerce actions.

---

## 1. Domain Responsibility and Boundary

Media/Creative Intelligence (MCI) establishes **one coherent product-semantic responsibility**:
> **Creative-specific semantic interpretation over explicit canonical inputs, including creative-local context, falsifiable creative hypotheses, derived creative asset identity and lineage, and advisory creative assessment.**

MCI operates as an advisory interpretation layer over canonical upstream artifacts. To prevent authority drift, duplicate ownership, and shadow authorities, MCI is strictly bounded:

- **Does NOT absorb Product Intelligence**: Source media, source evidence provenance, product identity, canonical product truth, catalog entries, ranking, seller-evidence ingestion, and media storage remain solely owned by Product Intelligence.
- **Does NOT absorb Commerce Opportunity Intelligence**: Commercial decision questions, business objectives, market/channel opportunities, audience boundaries, economic constraints, risk thresholds, decision deadlines, and raw post-intervention outcome evidence remain solely owned by Commerce Opportunity Intelligence (`P7.3` and `P7.6`).
- **Does NOT absorb Distribution Intelligence**: Channel selection, campaign setup, traffic routing, budget allocation, bidding strategies, ad publishing, and distribution operations remain distinct future or external authorities.
- **Does NOT possess Decision or Action Authority**: MCI provides advisory hypotheses, lineage tracking, and contextual assessment. It never decides whether to launch a creative, authorizes spend, approves a product, or executes commerce actions.

---

## 2. Conceptual Semantic Concepts

MCI.0 establishes **exactly four conceptual semantic concepts**. In MCI.0, these are semantic specifications and contract boundaries only; no executable Python classes, constructors, database tables, or serialization formats are authorized or created.

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        UPSTREAM CANONICAL AUTHORITIES                  │
│                                                                        │
│   Product Intelligence                  Commerce Opportunity           │
│   (P6 / TASK-125 / TASK-013)            Intelligence (P7.3 / P7.6)     │
│   ├── ProductSourcePack                 ├── DecisionContext            │
│   ├── OriginalMediaRef                  ├── OpportunityHypothesis      │
│   └── Canonical Product Truth           └── MarketTestEvidenceProfile  │
└──────────────────┬──────────────────────────────────┬──────────────────┘
                   │                                  │
                   ▼ (explicit reference)             ▼ (explicit reference)
┌────────────────────────────────────────────────────────────────────────┐
│                   MEDIA / CREATIVE INTELLIGENCE (MCI.0)                │
│                                                                        │
│   1. CreativeContext                                                   │
│      ├── Bound to exact P7.3 DecisionContext reference                 │
│      └── Creative-local presentation scope, modality, message intent   │
│                                                                        │
│   2. CreativeHypothesis                                                │
│      ├── Bound to CreativeContext                                      │
│      └── Falsifiable claim on creative levers, assumptions, unknowns   │
│                                                                        │
│   3. DerivedCreativeAsset                                              │
│      ├── Parent reference (OriginalMediaRef or DerivedCreativeAsset)   │
│      ├── Derivation classification & transformation lineage            │
│      └── Lineage != Product Truth != Effectiveness                     │
│                                                                        │
│   4. CreativeAssessment                                                │
│      ├── Advisory interpretation over CreativeContext/Hypothesis/Asset │
│      ├── Visible uncertainty, limitations, counter-evidence            │
│      └── Advisory only: No causal attribution, universal winner, action│
└────────────────────────────────────────────────────────────────────────┘
```

### 2.1 CreativeContext
`CreativeContext` represents creative-local, decision-relative framing for creative interpretation:
- **Decision-Relative Binding**: When used within a commercial decision process, `CreativeContext` binds explicitly to an existing P7.3 `DecisionContext` reference (`decision_context_id`). It never duplicates or mutates `market`, `audience`, `channel`, `objective`, `time_horizon`, `decision_deadline`, `economic_constraints`, `risk_constraints`, or `alternatives`.
- **Creative-Local Scope**: It captures only creative-specific framing: intended creative modality (image, video, text, layout), target presentation format (e.g. aspect ratio, duration, placement template), core creative message intent, and reference constraints.
- **Pure Context Value**: It is neither a campaign configuration, a media buy order, a distribution instruction, nor a creative brief authorization.

### 2.2 CreativeHypothesis
`CreativeHypothesis` represents an explicit, falsifiable creative-domain claim bound to a `CreativeContext`:
- **Hypothesis Structure**: Preserves explicit assumptions, supporting evidence references, counter-evidence references, important unknowns, disconfirming conditions, and expected observable outcomes.
- **Creative Focus**: Articulates falsifiable propositions about creative levers (e.g., visual angle, focal benefit emphasis, narrative opening hook, visual demonstration vs. lifestyle staging).
- **Authority Preservation**: It does not duplicate or mutate P7.3 `OpportunityHypothesis` (which addresses commercial market opportunity, viability, and demand).
- **Epistemic Boundary**: A hypothesis is strictly an unvalidated proposition. It must never be treated as established truth, creative quality proof, a launch recommendation, test readiness, approval, or action.

### 2.3 DerivedCreativeAsset
`DerivedCreativeAsset` represents semantic identity and derivation lineage for any asset transformed, synthesized, inferred, or generated from explicit parent inputs:
- **Explicit Parent Lineage**: Captures references to immediate parent inputs—either canonical Product Intelligence source media (`OriginalMediaRef`) or another prior `DerivedCreativeAsset`.
- **Derivation Classification**: Records the transformation category (e.g., background removal, studio render, re-framing, visual crop, resolution adjustment, overlay composition).
- **Temporal and Step Lineage**: Preserves the derivation path, input hashes, transformation timestamp, and processing steps.
- **Strict Epistemic Isolation (Lineage != Fidelity != Effectiveness)**:
  - Provenance and lineage prove **origin and transformation history only**; they do **not** prove factual fidelity to the physical product.
  - High aesthetic or visual fidelity does **not** prove canonical Product Truth. A photorealistic render can depict false product features.
  - Valid derivation and asset existence do **not** imply creative or commercial effectiveness. Storing or generating an asset is not performance.
  - A `DerivedCreativeAsset` is never promoted to source evidence, canonical product truth, or a catalog asset.

### 2.4 CreativeAssessment
`CreativeAssessment` represents bounded advisory interpretation over explicit creative context, creative hypotheses, derived assets, and observable evidence:
- **Advisory Synthesis**: Structures supporting evidence, counter-evidence, unresolved observations, uncertainty intervals, context boundaries, and analytical limitations.
- **Context-Sensitive Limits**: Explicitly records the bounded conditions under which observations were made (e.g. specific audience, placement, seasonal period, platform version).
- **Non-Ownership of Evidence**: References caller-supplied evidence or P7.6 `MarketTestEvidenceProfile` references without owning, duplicating, persisting, or synthesizing raw marketplace observations.
- **Strict Advisory Limits**: It must **never**:
  - Claim causal attribution (correlation or observed metric lift is not proof of creative causation).
  - Declare a "universal winner" across channels, audiences, or time periods.
  - Approve, certify, or select a creative for commercial distribution.
  - Authorize budgets, campaign launches, or marketplace interventions.

---

## 3. Relationships to Existing Canonical Authorities

MCI.0 maintains rigorous architectural boundaries with existing authorities:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                       AUTHORITY MATRIX & BOUNDARIES                    │
├─────────────────────────┬──────────────────────────────────────────────┤
│ Authority Domain        │ Exclusive Responsibilities (MCI Must Not Own)│
├─────────────────────────┼──────────────────────────────────────────────┤
│ Product Intelligence    │ • Source media extraction & byte-preserving  │
│ (M1, M2, M3, P6)        │   download (OriginalMediaRef, MediaRole)     │
│                         │ • MediaProvenance & source URL deduplication │
│                         │ • ProductSourcePack serialization/persistence│
│                         │ • Canonical Product Truth & Catalog          │
│                         │ • Product ranking, filtering & Human approval│
├─────────────────────────┼──────────────────────────────────────────────┤
│ Commerce Opportunity    │ • DecisionContext (market, audience, channel,│
│ Intelligence (P7.3)     │   deadline, economic/risk constraints)       │
│                         │ • OpportunityHypothesis (commercial viability│
│                         │   and market opportunity claims)             │
├─────────────────────────┼──────────────────────────────────────────────┤
│ Commerce Evidence &     │ • MarketTestEvidenceProfile (exposure, funnel│
│ Validation (P7.6, P7.7) │   economic, quality evidence organization)   │
│                         │ • Bounded post-intervention raw evidence     │
│                         │ • Statistical validation boundaries          │
├─────────────────────────┼──────────────────────────────────────────────┤
│ Distribution &          │ • Channel/ad platform selection              │
│ Operations (External)   │ • Campaign execution, budgets, bidding       │
│                         │ • Inventory, order, price mutations          │
├─────────────────────────┼──────────────────────────────────────────────┤
│ Media/Creative          │ • CreativeContext (creative-local scope only)│
│ Intelligence (MCI.0)    │ • CreativeHypothesis (creative claims only)  │
│                         │ • DerivedCreativeAsset (lineage & identity)  │
│                         │ • CreativeAssessment (bounded advisory only) │
└─────────────────────────┴──────────────────────────────────────────────┘
```

1. **Product Intelligence Retains Sole Source Ownership**:
   - `ProductSourcePack`, `OriginalMediaRef`, `MediaRole`, `MediaProvenance`, source media files, source identity, canonical catalog identity, product specifications/truth, and Human approval remain solely owned by Product Intelligence.
   - MCI consumes these inputs exclusively via read-only reference. MCI never duplicates source records, re-downloads raw media, or creates shadow catalog stores.
2. **Commerce Opportunity Retains Sole Decision Context & Outcome Evidence**:
   - P7.3 remains sole owner of `DecisionContext` and `OpportunityHypothesis`. MCI references `context_id` and does not create an independent `CreativeDecisionContext` or alter decision deadlines.
   - P7.6 remains sole owner of `MarketTestEvidenceProfile`. Raw exposure, funnel, conversion, and economic observations belong to P7.6. MCI assessments may cite evidence references but never re-ingest, normalize, or own raw outcome evidence.
3. **Distribution & Operations Remain External**:
   - Placement references in MCI are descriptive metadata, not distribution authorizations.
   - Mentioning a platform format (e.g. 9:16 vertical video) confers no right to purchase ad inventory, deploy creative to ad accounts, or execute commercial campaigns.

---

## 4. Semantic Invariants & MCI.0 Domain-Level Consequences

MCI.0 strictly preserves all five foundational invariants established in TASK-270 and adds six audited domain-level consequences:

### 4.1 Preserved Foundational Invariants
1. `SOURCE_EVIDENCE_IS_NOT_DERIVED_ASSET`: Immutable source media captured from seller listings must never be conflated with downstream transformed, rendered, or synthetic media.
2. `DERIVED_ASSET_IS_NOT_SOURCE_EVIDENCE`: An asset produced by background removal, generative inpainting, studio rendering, or synthetic variation cannot serve as evidence of what the seller actually provided or what the product physically is.
3. `SCORE_IS_NOT_INTELLIGENCE`: A numerical score, heuristic index, model loss value, or aesthetic rating is an uncontextualized metric, not semantic intelligence.
4. `RECOMMENDATION_IS_NOT_DECISION`: Advisory creative assessments or recommendations do not constitute commercial decisions or commitments.
5. `INTELLIGENCE_IS_NOT_DECISION`: Domain intelligence provides structured epistemic interpretation; the decision to commit resources, publish creative, or launch market interventions remains a distinct Human or authorized decision-loop authority.

### 4.2 Six Audited MCI.0 Domain-Level Consequences
1. `DERIVED_ASSET_LINEAGE_IS_NOT_PRODUCT_TRUTH`:
   Tracking a derived asset's origin back to an original photo proves its derivation history, but does **not** prove that the visual representation accurately depicts canonical product truth. Generative transformations frequently alter dimensions, materials, finishes, or components.
2. `CREATIVE_FIDELITY_IS_NOT_PRODUCT_TRUTH`:
   Photorealism, crisp resolution, and high perceptual fidelity do not establish factual accuracy. A flawless AI render showing a product with three settings when the canonical listing specifies two is a hallucination, not truth.
3. `ASSET_EXISTENCE_IS_NOT_EFFECTIVENESS`:
   Generating, transforming, validating, or storing a creative asset does not mean the asset is commercially effective, persuasive, or capable of driving engagement. Asset presence is zero evidence of performance.
4. `CREATIVE_MEASUREMENT_IS_NOT_CAUSAL_ATTRIBUTION`:
   Observing high click-through rates, views, or conversions while a creative is active does not prove the creative caused the outcome. Confounding variables (audience selection, bid strategy, platform recommendation biases, seasonality, competitive pricing) prevent direct causal claims without rigorous control mechanisms.
5. `CREATIVE_WINNER_IS_CONTEXTUAL`:
   There is no such thing as an unconditional or "universal" creative winner. Creative performance is intrinsically tied to specific audiences, placements, cultural contexts, seasonal windows, and platform dynamics. Declaring a global winner overgeneralizes bounded evidence.
6. `PLACEMENT_REFERENCE_IS_NOT_DISTRIBUTION_AUTHORITY`:
   Specifying a channel or ad format reference in creative context or assessment does not grant authority to launch, traffic, spend, or publish to that channel. Distribution authority requires explicit external commercial authorization.

---

## 5. Substrate Neutrality & Technical Substrate Boundaries

MCI.0 strictly separates semantic domain concepts from underlying technical substrate:

- **`src/images` Is Technical Substrate Only**:
  - The existing `src/images` modules (`ImageCandidate`, `DownloadedImage`, `ValidatedImage`, `ImageArtifact`, storage layout, download pipeline, validation pipeline, perceptual hash deduplication) provide low-level image processing and byte storage.
  - Their presence does **not** establish Media/Creative Intelligence domain semantics. An `ImageArtifact` storage key is a technical pointer, not an MCI semantic concept.
  - Technical components must not be retroactively rebranded as domain models without canonical architectural design.
- **Provider & Model Neutrality**:
  - MCI.0 selects **no LLM, multimodal model, diffusion model, generative model, or vision provider** (e.g. OpenAI, Anthropic, Google Gemini, Midjourney, Stability AI).
  - MCI.0 selects **no prompt strategy, pipeline framework, orchestrator, or agent architecture**.
- **System Neutrality**:
  - MCI.0 selects **no asset storage backend, database, vector index, or caching layer**.
  - MCI.0 selects **no scoring engine, evaluation harness, or automated testing suite**.
  - MCI.0 selects **no ad network API, distribution pipeline, or campaign manager**.

---

## 6. Bounded Adversarial Failure Modes

The semantic architecture of MCI.0 explicitly protects against eight concrete adversarial failure modes:

| # | Failure Mode | Adversarial Risk / Mechanism | MCI.0 Semantic Protection |
|---|---|---|---|
| 1 | **Generated Unsupported Product Attributes** | Generative models hallucinate features not present in source product (e.g. adding USB-C port to micro-USB device, changing material from plastic to metal). | `DERIVED_ASSET_LINEAGE_IS_NOT_PRODUCT_TRUTH` & `CREATIVE_FIDELITY_IS_NOT_PRODUCT_TRUTH`: Derived assets are explicitly isolated from Product Truth; visual attributes cannot be promoted to source facts without canonical catalog verification. |
| 2 | **Wrong-Variant Lineage** | Generating creative for Product Variant A (e.g. 3-mode motion sensor) using source media or specs from Variant B (e.g. single-mode base model). | `DerivedCreativeAsset` requires explicit binding to parent `OriginalMediaRef` including specific `variant_label` and `source_section` provenance, preventing cross-variant contamination. |
| 3 | **Compounding Transformation Chains** | Running chained transformations (e.g., crop → background removal → studio relighting → text overlay) where subtle distortions compound into major misrepresentations. | Acyclic lineage tracking records every intermediate transformation step and parent reference; each step is classified and bounded, preventing unobserved semantic drift. |
| 4 | **Stale Source Truth** | Upstream seller alters product specifications or photos on the marketplace, but downstream creative assets and hypotheses remain active based on obsolete facts. | MCI artifacts require explicit timestamped bindings (`as_of` / `observed_at`). Downstream derived assets carry explicit parent references that become invalid when upstream source packs are updated. |
| 5 | **Misleading Crop / Removal** | Automated cropping or background removal removes safety labels, dimension references, scale context, or mandatory warnings, misleading buyers. | Derivation classification explicitly categorizes destructive edits (cropping, masking); prohibits claiming visual fidelity without verifying that mandatory semantic elements are preserved. |
| 6 | **Audience / Placement Confounding** | A creative tested on a high-intent retargeting audience achieves high ROAS, leading an evaluator to falsely attribute the success to creative quality rather than audience intent. | `CREATIVE_MEASUREMENT_IS_NOT_CAUSAL_ATTRIBUTION`: Assessments must isolate audience/channel dimensions and cannot infer creative superiority from confounded aggregate metrics. |
| 7 | **Exposure-Policy Feedback Loops** | Ad platform recommendation algorithms push a creative due to early noise, generating high impressions and engagement that are mistaken for organic creative strength. | `SCORE_IS_NOT_INTELLIGENCE`: Raw platform performance metrics cannot be converted directly into creative intelligence; exposure distribution dynamics must remain explicit unknowns. |
| 8 | **Single-Test Winner Overgeneralization** | Declaring a creative asset the "definitive winner" after a single localized test, rolling it out across all markets where it fails catastrophically. | `CREATIVE_WINNER_IS_CONTEXTUAL`: Creative assessments are strictly bounded to the observed context; declaring global or unconditional winners is architecturally prohibited. |

---

## 7. Roadmap State & Transition Mechanics

Upon exact reviewed source publication of TASK-271:
1. `MCI.0_DOMAIN_SEMANTIC_FOUNDATION` is marked **`DONE`**.
2. The active domain track remains **`MEDIA_CREATIVE_INTELLIGENCE`** (`status: SELECTED`).
3. `pending_commitments` is set to **`[]`** (empty).
4. `next_milestone` is set to **`null`**.
5. `post_run_engineering_successor` is set to **`null`**.
6. `automatic_progression` is set to **`false`**.
7. `task_272_preselected` is set to **`false`**.
8. Planning handoff is set to **`HUMAN_BRAIN_POST_MCI_0_ROADMAP_SELECTION`**.
9. **No MCI.1 successor is preselected**: Any subsequent milestone (e.g., MCI.1 capability design or asset pipelines) remains a nonbinding candidate requiring an explicit, independent Human/Brain roadmap decision.
