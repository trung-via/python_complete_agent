# Post-M4 Product Intelligence Roadmap — Live Product Enablement

Status: canonical post-M4 architecture roadmap; P1-P5, P6.0, P6.1, and P6.3 are CLOSED.
TASK-170 / P6.1d is CLOSED / PUBLISHED at candidate
`0781e0810d161ad1a4936c0e3ea31aada5704da1`. P6.2 is PARKED / NOT JUSTIFIED BY
CURRENT EVIDENCE and remains reopenable from future evidence. P6.3 is CLOSED with
TASK-171 / P6.3a CLOSED / PUBLISHED at candidate
`3a33748905154b4822cfc164999e5c57780e67f2`, TASK-172 / P6.3b source hardening
CLOSED / PUBLISHED at `63525151e4dbb7a1c30454a301e3c0e20ae771e9`, TASK-173
live-DOM hardening CLOSED / PUBLISHED at `f91dfe0f900664c835fef86bdf5d6c75879dbbdc`,
TASK-174 structural-depth hardening CLOSED / PUBLISHED at
`8c5a0b2a6a935c5bbecff5cde7b1a32956aa8d32`, TASK-175 same-target
acquisition-continuity hardening CLOSED / PUBLISHED at candidate
`61f78f8ac1cd14e6e110552ba638eb9ca149403f`, and TASK-176 recording the bounded
K550 live certification passage. The fresh architecture/value audit selects the separately
justified P7 Commerce Opportunity Intelligence branch. TASK-181/P7.0 is CLOSED / PUBLISHED at
`9e835ed2c551c2fa3a8b66b82caa238bd41b152c`. TASK-182/RUN-182-006 remains BLOCKED /
UNPUBLISHED. TASK-185 is CLOSED / PUBLISHED at
`6b03dc14f88ddb98baeb6ae726f0dd913b323ba1`. TASK-186/RUN-186-003 is BLOCKED /
UNPUBLISHED with no source candidate because of current Shopee live-DOM incompatibility.
TASK-187 is the narrow prerequisite; a fresh P7.1 successor requires TASK-187 Runtime PASS,
semantic PASS, and source-only publication. P6.4-P6.6 remain DEFERRED / UNIMPLEMENTED.
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
closed P4, and published TASK-149 subsequently closed P5 Human-Facing Product
Intelligence Surface.

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

### P5 — Human-Facing Product Intelligence Surface — CLOSED

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
CLOSED. Published TASK-154 closed P6.0a. Published TASK-163 closed P6.0b and P6.0.
P6.1 is CLOSED / PUBLISHED.

### P6 — Quality and Scale Enhancements — P6.0/P6.1/P6.3 CLOSED, P6.2 PARKED

Following the post-P5 architecture audit (recorded in `docs/POST_P5_P6_QUALITY_SCALE_ROADMAP.md`),
Phase 6 is explicitly ordered as a `CERTIFY -> EVALUATE -> IMPROVE` discipline:

#### P6.0 Live Real-Evidence Certification — CLOSED (TASK-154, TASK-163)
Certify live operational boundaries against real marketplace targets using operator-owned
authenticated CDP sessions before building downstream quality or scale features. Full live
production certification remains distinct from provider-only TASK-144.
- **P6.0a Successor Live Marketplace Discovery -> Persisted Product Source Pack Certification (TASK-154 — CLOSED)**:
  Published at candidate `27ec982a96619379e8e387f0e8781b9503be2c59` after canonical Runtime and
  semantic-review PASS. It certifies only one explicit current
  marketplace route (`shopee` or `tiktok`) discovering a candidate and persisting typed V1
  `ProductSourcePack` evidence beneath `tmp_path`, rehydrated via TASK-125.
  Historical TASK-150 (RUN-150-001..005) and TASK-152 (RUN-152-001) are preserved as failed
  historical certification evidence. Published TASK-151 (readiness polling and anchor fallback) and
  TASK-153 (nullable card mapping) hardened Shopee discovery to resolve prior blockers without
  creating new semantic authority. TASK-154 itself certifies only one explicit current marketplace
  route through real local evidence. It does not claim both marketplaces, Google Drive, Human
  approval/queue, M3 admission, grounded QA, product truth, semantic retrieval, identity migration,
  automation, or serving are certified.
- **P6.0b Real-Evidence Canonical Knowledge + Grounded-QA Certification (TASK-163 — CLOSED)**:
  TASK-156 remains preserved historical failed certification evidence. Its RUN-156-009 reached live
  discovery but failed Shopee acquisition with `LIVE_P6B_ACQUISITION_EXTRACTION` at failed head
  `38e087e6925b1e7bac81c0eddc8b4dbb8992ff25`; it is not repaired or published by this successor.
  TASK-162 is CLOSED and published at candidate `065124f0bc414eb0222db14c07179d66ddce946c`;
  it narrowly corrected the existing `ShopeeSourceExtractor` product-page readiness authority. Fresh TASK-163
  certified one Shopee listing acquired twice as two planned observations, one TASK-138 intake,
  TASK-139/140/141 Human-governed family and singleton-variant composition into disposable TASK-120
  SQLite state, and one TASK-135 persistent grounded-QA call with a deterministic zero-network provider.
  Canonical Runtime verification (RUN-163-002 PASS) and ChatGPT PRIMARY semantic review (REVIEW-163-002 PASS)
  both passed on candidate `fa2a49326be28422484db4a37c932681210d8060`. P6.0b and P6.0 are CLOSED.

#### P6.1 Retrieval-Quality Evaluation / Baseline — CLOSED / PUBLISHED
Establish empirical retrieval benchmarks (precision, recall, citation accuracy) using the existing
lexical retrieval baseline (TASK-122) on real product evidence before introducing any semantic retrieval.
P6.1 now proceeds through these ordered gates:
- **P6.1a Evaluation Contract (TASK-164 — CLOSED)**: Establishes pure deterministic evaluation authority
  over existing TASK-122 lexical retrieval and TASK-129 grounded answers, measuring explicit Human-authored
  benchmark labels with exact Fraction arithmetic.
- **P6.1 Live-Capture Blocker Hardening (TASK-166 — CLOSED / PUBLISHED)**: TASK-165 remains unpublished
  blocked P6.1b evidence. REVIEW-165-003 F1 and its failed remediation/repair continuation lineage established that
  live marketplace interaction inside AIOS engineering verification is the wrong operational
  boundary. TASK-166 provided explicit external-root checkpoint/resume capture; CAPTCHA remains
  Human-owned.
- **P6.1 Shopee Search-Surface Discovery Hardening (TASK-167 — CLOSED / PUBLISHED)**: The first external
  TASK-166 READY bundle was operationally successful but Human-rejected because exact query
  `chuột không dây` mapped to an unrelated lantern listing. It remains operational evidence only,
  not P6.1b benchmark truth. TASK-167 narrowly hardens the existing TASK-151/TASK-153
  `ShopeeDiscoveryAdapter` search-surface provenance boundary without adding semantic relevance
  filtering or changing downstream business ranking.
- **P6.1b Real-Evidence Benchmark Execution (TASK-168 revision 2 — CLOSED / PUBLISHED)**:
  The second reviewed READY bundle is the accepted corpus source. RUN-168-001 remains canonical
  task-design failure evidence with zero source delta: revision 1 wrongly required each
  `SAME_PRODUCT_FAMILY` pair to qualify as one full-member exact variant. Revision 2 preserves
  one two-member family per cohort and admits each canonical member as an explicit singleton
  benchmark variant, without claiming sibling real-world difference or changing TASK-116.
  Exact measured baseline values are documented in
  `docs/PHASE_6_P6_1_REAL_EVIDENCE_BASELINE.md`. TASK-168 is published at
  candidate `0e6626a53c10609a1a7b282d7ca49af33e4d5573`; P6.1b is CLOSED.
- **P6.1c Retrieval Stress Benchmark (TASK-169 revision 2 — CLOSED / PUBLISHED)**:
  Reuses the immutable published TASK-168 corpus in place and submits six fixed
  Human-authored paraphrase/attribute cases to TASK-164 exactly once with
  `limit=3`. The exact measured lexical snapshot is 2 TP, 0 FP, 10 FN, micro
  precision 1/1, and micro recall 1/6. It sets no threshold and makes no automatic
  roadmap decision. TASK-169 is published at candidate
  `52d539aa1a2b880f488987cb07c46ea9347dcdcc`; P6.1c is CLOSED. TASK-169 revision
  1, which proposed opening P6.3, was never executed and remains superseded
  authoring history only.
- **P6.1d Planner-Assisted Retrieval Stress Benchmark (TASK-170 — CLOSED / PUBLISHED)**:
  Replays the exact six published TASK-169 stress intents once each through TASK-134,
  then evaluates all six planned queries in one TASK-164 call at `limit=3` over the
  immutable TASK-168 corpus. The measured snapshot is 12 TP, 0 FP, 0 FN, and micro
  precision and recall of 1/1. This measures the existing TASK-134 -> TASK-122
  composition without claiming semantic understanding or making an automatic
  architecture decision. TASK-170 is published at candidate
  `0781e0810d161ad1a4936c0e3ea31aada5704da1`; P6.1d and P6.1 are CLOSED.

#### P6.2 Conditional Semantic / Vector Retrieval or Reranking — PARKED / NOT JUSTIFIED BY CURRENT EVIDENCE
Raw TASK-122 stress weakness was fully recovered by the existing production
TASK-134 -> TASK-122 composition on the measured corpus: 12 TP, 0 FP, 0 FN and
micro precision/recall of 1/1. Current evidence therefore does not justify a new
semantic/vector authority. P6.2 remains reopenable if future evidence changes;
parking it does not claim lexical retrieval is universally sufficient. SQLite
remains the canonical store; any future vector index would remain secondary and disposable.

#### P6.3 Product-Truth Reconciliation — CLOSED (TASK-171 / P6.3a, TASK-172 through TASK-175 / P6.3b, TASK-176)
TASK-171 / P6.3a is CLOSED / PUBLISHED at candidate `3a33748905154b4822cfc164999e5c57780e67f2`,
establishing the Human-governed descriptive-field foundation over exact TASK-121
evidence. TASK-172 / P6.3b source hardening is CLOSED / PUBLISHED at candidate
`63525151e4dbb7a1c30454a301e3c0e20ae771e9`. TASK-173 live-DOM hardening is CLOSED /
PUBLISHED at `f91dfe0f900664c835fef86bdf5d6c75879dbbdc`. TASK-174 structural-depth
hardening is CLOSED / PUBLISHED at `8c5a0b2a6a935c5bbecff5cde7b1a32956aa8d32`.
TASK-175 same-target acquisition-continuity hardening is CLOSED / PUBLISHED at candidate
`61f78f8ac1cd14e6e110552ba638eb9ca149403f`, preserving an acquired page when host equality
and current-path Shopee product identity prove the same source item while retaining one exact
target navigation for unproven locations.

Following TASK-175 publication, the Human executed the external live checkpoint using the
operator-owned authenticated Chromium/CDP session and one clean Shopee K550 page for
`source_product_id 10374101498` with explicit rendered Human selection `"Model: K550 Trắng Red V4"`.
Two distinct live `ProductSourcePack` observations preserved that exact selected-variant fact with
distinct `observed_at` identities; TASK-108 returned `EXACT_VARIANT_MATCH`; the conflict-free
two-member family and two-member TASK-116 sellable-variant proposal with one direct exact pair
succeeded; in-memory canonical family/variant/catalog admission succeeded; TASK-121 built a
two-member, two-observation profile retaining both variant facts; TASK-171 reconciliation completed;
and the script reached exactly `P6.3 LIVE RESULT: PASS`. TASK-176 records this bounded live passage,
closing P6.3.

- Bounded certification boundary: certifies the exercised authority composition on one explicit
  current Shopee K550 listing/variant under Human-owned authenticated CDP interaction. It does not
  certify all Shopee DOMs, TikTok, cross-platform identity, objective real-world truth, fact/media
  reconciliation, persistent truth history, downstream truth consumption, marketplace SLA, or
  future seller-page stability.
- Evidence, identity, and truth separation: Selected-variant facts are observed source evidence only,
  not canonical variant identity or product truth.
- TASK-108 remains the sole pairwise relationship authority; TASK-116 still governs Human
  exact-variant admission; TASK-121 remains evidence projection; TASK-171 still reconciles
  descriptive truth only after a canonical profile exists.
- No recency, majority, provenance, ranking, model, or other automatic preference is introduced;
  unresolved conflicts and partial truth remain valid.
- P6.3 has no fact/media reconciliation, persistence, downstream consumption, or broad
  multi-marketplace claims.
- P6.3 is CLOSED. The completed fresh architecture/value audit selects the separately justified
  P7 Commerce Opportunity Intelligence extension, beginning with measurement of the existing M2
  Winning Product evidence space. It does not authorize immediate P6.4 implementation.

#### P6.4 Identity Evolution and Migrations — UNIMPLEMENTED / FUTURE / DEFERRED
Define a separate canonical-identity authority for entity lifecycle, merging, splitting, and schema
migrations while preserving M3 integrity.

#### P6.5 Higher-Level Human-Review Automation — UNIMPLEMENTED / FUTURE / DEFERRED
Introduce review triage assistance without removing or bypassing explicit Human approval authority.

#### P6.6 Caches and Background Serving — UNIMPLEMENTED / FUTURE / DEFERRED
Implement performance caches and background serving infrastructure only after an observed operational
workload requires them.

### P7 — Commerce Opportunity Intelligence — SELECTED / NOT YET CLOSED

The fresh architecture/value audit found no current retrieval, identity-migration,
review-automation, or serving bottleneck that outranks the measurable undercoverage of the
already-defined M2 Winning Product evidence model. P6.2 remains PARKED and reopenable from new
evidence; P6.4-P6.6 remain DEFERRED / UNIMPLEMENTED.

- **P7.0 Winning Product Evidence-Coverage Evaluation (TASK-181 — CLOSED / PUBLISHED at `9e835ed2c551c2fa3a8b66b82caa238bd41b152c`)** freezes one pure,
  bounded evaluator over existing `WinningProductScorer` outputs. It adds measurement only and
  changes no discovery, normalization, scoring, ranking, approval, persistence, retrieval, truth,
  or collection authority.
- **TASK-182 / RUN-182-006 — BLOCKED / UNPUBLISHED** attempted the real-evidence baseline, but
  semantic review found malformed Shopee `sold_count` evidence. Candidate
  `94c4e5105e593b9136f186882daacb466c9a304d`, its fixture/test/docs delta,
  RUN/RESULT/FAILURE/REPAIR lineage, and REVIEW-182-006 remain immutable and unpublished; its
  measurements are not baseline truth.
- **TASK-185 — CLOSED / PUBLISHED at `6b03dc14f88ddb98baeb6ae726f0dd913b323ba1`** hardened
  only the existing Shopee sold-evidence input boundary and changed no downstream normalization,
  scoring, ranking, approval, or truth authority.
- **TASK-186 / RUN-186-003 — BLOCKED / UNPUBLISHED, no source candidate** stopped because
  Human-visible current Shopee results were not recognized by the existing adapter.
- **TASK-187 — current narrow prerequisite** hardens only that adapter's current search-result
  DOM recognition boundary while preserving TASK-151, TASK-153, TASK-167, and TASK-185 authority.
- **NEXT — fresh P7.1 real-evidence coverage baseline successor** remains deferred until TASK-187
  Runtime PASS, semantic PASS, and source-only publication. It must be newly authored and capture a
  new reviewed cohort; TASK-186 must not be continued, repaired, or rehabilitated. TASK-187
  establishes no baseline, coverage rate, business value, winner, recommendation, or enrichment
  priority. Later enrichment remains conditional on that fresh evidence.

See `docs/PHASE_7_P7_0_WINNING_PRODUCT_EVIDENCE_QUALITY.md` for the audit and boundary.

## 3. Priority decision

P1 is closed by TASK-137. P2 is closed by TASK-138: persisted Product Source Pack evidence is now discoverable through an explicit-root, bounded local intake, and current downstream consumers can receive either typed `ProductSourcePack` values or the aligned explicit manifest paths without duplicating filesystem discovery.

P3 is closed (TASK-139, TASK-140, TASK-141). P4 is closed (TASK-142, TASK-144).
P5 is CLOSED: published TASK-145 closed P5.1, published TASK-146 closed P5.2,
published TASK-147 closed P5.3a, published TASK-148 closed P5.3b, and published
TASK-149 closed P5.3c after canonical Runtime PASS and ChatGPT PRIMARY semantic PASS
on source candidate `132deef99363ffce0c3162c5f59d1b1349563995`.

Under the post-P5 quality and scale architecture audit
(`docs/POST_P5_P6_QUALITY_SCALE_ROADMAP.md`), published TASK-154 has closed P6.0a for one explicit
marketplace route. TASK-150 and TASK-152 remain failed historical P6.0a evidence, while TASK-156 /
RUN-156-009 remains historical failed P6.0b evidence after discovery succeeded and acquisition
failed with `LIVE_P6B_ACQUISITION_EXTRACTION`. Published TASK-162 is the narrow Shopee
product-page readiness blocker correction. Published TASK-163 closed P6.0b and P6.0 after
canonical Runtime verification and ChatGPT PRIMARY semantic review both passed. P6.1 is
CLOSED / PUBLISHED through TASK-170 at candidate
`0781e0810d161ad1a4936c0e3ea31aada5704da1`. P6.2 is PARKED / NOT JUSTIFIED BY
CURRENT EVIDENCE because the existing TASK-134 -> TASK-122 composition fully
recovered the measured raw TASK-122 stress weakness; it remains reopenable from
future evidence. P6.3 is CLOSED with TASK-171 / P6.3a CLOSED / PUBLISHED at candidate `3a33748905154b4822cfc164999e5c57780e67f2`, TASK-172 / P6.3b source hardening CLOSED / PUBLISHED at `63525151e4dbb7a1c30454a301e3c0e20ae771e9`, TASK-173 live-DOM hardening CLOSED / PUBLISHED at `f91dfe0f900664c835fef86bdf5d6c75879dbbdc`, TASK-174 structural-depth hardening CLOSED / PUBLISHED at `8c5a0b2a6a935c5bbecff5cde7b1a32956aa8d32`, TASK-175 same-target acquisition-continuity hardening CLOSED / PUBLISHED at candidate `61f78f8ac1cd14e6e110552ba638eb9ca149403f`, and TASK-176 recording the bounded K550 live certification passage (`P6.3 LIVE RESULT: PASS`). P6.2 remains PARKED / reopenable from future evidence. The completed fresh architecture/value audit selects the separately justified P7 Commerce Opportunity Intelligence branch instead of automatically opening P6.4. TASK-181/P7.0 is CLOSED / PUBLISHED at `9e835ed2c551c2fa3a8b66b82caa238bd41b152c`; TASK-182/RUN-182-006 remains BLOCKED / UNPUBLISHED; TASK-185 is CLOSED / PUBLISHED at `6b03dc14f88ddb98baeb6ae726f0dd913b323ba1`; TASK-186/RUN-186-003 remains BLOCKED / UNPUBLISHED with no source candidate; TASK-187 is the narrow current prerequisite; and a fresh P7.1 successor requires TASK-187 Runtime PASS, semantic PASS, and source-only publication rather than continuation or rehabilitation of TASK-186. P6.4-P6.6 remain deferred and unimplemented.
TASK-165 remains unpublished blocked evidence from
REVIEW-165-003 F1 and its failed remediation/repair continuation lineage.

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
