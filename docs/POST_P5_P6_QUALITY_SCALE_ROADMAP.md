# Post-P5 P6 Quality and Scale Roadmap

Status: **P6.0, P6.1, and P6.3 are CLOSED. TASK-170 / P6.1d is CLOSED / PUBLISHED at candidate `0781e0810d161ad1a4936c0e3ea31aada5704da1`. P6.2 is PARKED / NOT JUSTIFIED BY CURRENT EVIDENCE and remains reopenable from future evidence. P6.3 is CLOSED with TASK-171 / P6.3a CLOSED / PUBLISHED at candidate `3a33748905154b4822cfc164999e5c57780e67f2`, TASK-172 / P6.3b source hardening CLOSED / PUBLISHED at `63525151e4dbb7a1c30454a301e3c0e20ae771e9`, TASK-173 live-DOM hardening CLOSED / PUBLISHED at `f91dfe0f900664c835fef86bdf5d6c75879dbbdc`, TASK-174 structural-depth hardening CLOSED / PUBLISHED at `8c5a0b2a6a935c5bbecff5cde7b1a32956aa8d32`, TASK-175 same-target acquisition-continuity hardening CLOSED / PUBLISHED at candidate `61f78f8ac1cd14e6e110552ba638eb9ca149403f`, and TASK-176 recording the bounded K550 live certification passage. The fresh architecture/value audit selects the separately justified P7 Commerce Opportunity Intelligence branch. TASK-181/P7.0 is CLOSED / PUBLISHED at `9e835ed2c551c2fa3a8b66b82caa238bd41b152c`. TASK-182/RUN-182-006 remains BLOCKED / UNPUBLISHED. TASK-185 is CLOSED / PUBLISHED at `6b03dc14f88ddb98baeb6ae726f0dd913b323ba1`. TASK-186/RUN-186-003 is BLOCKED / UNPUBLISHED with no source candidate. TASK-187 is CLOSED / PUBLISHED at `857e6b5d0009e9327e1a92d5f62b91432e28f150`. TASK-188/RUN-188-004 is BLOCKED / UNPUBLISHED with no source candidate; its diagnostics are not baseline truth. TASK-189 is CLOSED / PUBLISHED at candidate `9fa1b2583380e1b6378e5aba3d720c2e78a4b9d4`. TASK-190 is CLOSED / PUBLISHED at `22d8837e5955ed78185426f293e874625a34d469`. Following completion of the post-publication Human review gate accepting one READY `discovery_capture_bundle.json`, TASK-191 is the fresh offline P7.1 baseline successor, freezing that accepted bundle into repository fixtures and recording the deterministic measured baseline offline. P6.4-P6.6 remain DEFERRED / UNIMPLEMENTED.**

P7.2-P7.7 is DONE through exact published TASK-225 source
`6302dd7d01be90624d5ed0072cffbc3c23f2e4a2`. Fresh Human/Brain selection established
P8.0 Real Commerce Decision Loop Composition is DONE at exact published TASK-226 source
`a9429a5db859ebc6fe7e5fea19aaf17ee11d0d3e`. The Human then selected one exact TikTok Shop
Vietnam listing for P8.1. TASK-227 records that selection as a publication-gated DONE
`PILOT_CASE_SELECTION_ONLY` commitment; it does not execute a real pilot, assert live marketplace
facts, or authorize evidence acquisition or a test. P8.2 is publication-gated DONE through TASK-228
only as `PRE_ACTION_EVIDENCE_ACQUISITION_PLAN_ONLY`, with no live evidence, action, or automatic
P8.3. Control returns to Human/Brain for an explicit bounded evidence-acquisition authorization
decision. P6.2 remains PARKED and P6.4-P6.6 remain DEFERRED / UNIMPLEMENTED.
Scope: Python Agent product architecture post-P5; AIOS-renew remains execution substrate only.

## 1. Canonical Post-P5 Architecture Audit

With published TASK-149 (candidate `132deef99363ffce0c3162c5f59d1b1349563995`), the P5 Human-Facing
Product Intelligence Surface is CLOSED across read-only inspection (`evidence`, `catalog`, `ask`),
live discovery and shortlisting (`discover`), in-process live decision to ingestion queue (`decide`),
family decision and durable admission (`family-decide`), and sellable-variant review, decision,
and durable admission (`variant-decide`).

P6.0a subsequently established the first real-evidence acquisition boundary. The remaining P6.0
closure question is the downstream composition of that evidence through the already-published
intake, Human-governed canonical admission, durable SQLite, and grounded-QA authorities.

Historical certification and blocker lineage:
- **TASK-150**: Attempted P6.0a certification, but its candidate was never published. Execution lineage
  (RUN-150-001..005) exposed CDP unavailability, CAPTCHA/timing challenges, and an adapter readiness
  synchronization gap. RUN-150-005 failed with `LIVE_DISCOVERY_UNAVAILABLE` despite a clean non-CAPTCHA
  marketplace surface. TASK-150 remains failed historical certification evidence.
- **TASK-151**: Published narrow Shopee discovery blocker correction / readiness hardening (closed by
  RUN-151-001 Runtime PASS, REVIEW-151-001 PRIMARY PASS, candidate `39f39df0efe23c0d18a7292a0b27f92f40a64832`).
  It hardened same-page readiness polling and anchor fallback.
- **TASK-152**: Attempted P6.0a successor certification (RUN-152-001, failed_head_sha `f3836e8bac206e65dbe789633eec0f680220f6a6`).
  It passed its offline suite (121 tests), progressed past the prior zero-card failure, but failed in
  Shopee discovery due to an uncaught `AttributeError: 'NoneType' object has no attribute 'strip'` when
  a sparse live card emitted explicit JSON `null` for attributes. Because TASK-152 was certification-only,
  it could not modify production Python; its candidate remains failed historical certification evidence.
- **TASK-153**: Published narrow Shopee card mapping blocker correction (closed by RUN-153-002 REMEDIATION PASS,
  REVIEW-153-002 DELTA PASS, candidate `d8be80c1ea5edc1fca1c2c7c10919431f142d9c9`). It made `_map_card_to_snapshot`
  null-safe for required and optional fields without altering parsing or identity semantics.
- Neither blocker correction (TASK-151 / TASK-153) creates a new semantic authority.
- **TASK-154**: CLOSED and published at candidate
  `27ec982a96619379e8e387f0e8781b9503be2c59` after canonical Runtime and semantic-review PASS.
  It established P6.0a for one explicit current marketplace route from live discovery through local
  persisted typed `ProductSourcePack` evidence.
- **TASK-156 / RUN-156-009**: Preserved historical failed P6.0b certification evidence. Discovery
  succeeded, but live Shopee acquisition failed with bounded category
  `LIVE_P6B_ACQUISITION_EXTRACTION` at failed head
  `38e087e6925b1e7bac81c0eddc8b4dbb8992ff25`. This lineage is not a publication candidate and is
  not repaired, rerun, cherry-picked, or merged by its successor.
- **TASK-162**: CLOSED and published as the narrow Shopee product-page acquisition-readiness blocker
  correction at candidate `065124f0bc414eb0222db14c07179d66ddce946c`. Its bounded same-page
  readiness sampling remains production `ShopeeSourceExtractor` authority rather than certification
  fixture behavior.
- **TASK-163**: CLOSED after canonical Runtime verification (RUN-163-002 PASS) and
  ChatGPT PRIMARY semantic review (REVIEW-163-002 PASS) on candidate
  `fa2a49326be28422484db4a37c932681210d8060`. It certified one current Shopee candidate
  selected by the existing discovery/ranking path, acquired twice as two planned persisted
  observations, then composed through TASK-138/139/140/141, TASK-120 SQLite durability, and TASK-135
  persistent grounded QA with a deterministic zero-network provider. With this passage, P6.0b and P6.0
  are CLOSED. TASK-170 subsequently closed P6.1 at published candidate
  `0781e0810d161ad1a4936c0e3ea31aada5704da1`.

Introducing semantic retrieval, vector search, identity migrations, automated review,
or background serving still requires its own empirical justification. P6.3 established
the bounded descriptive truth foundation and certified the selected-variant source
evidence composition on one explicit current Shopee listing.

Therefore, Phase 6 is canonically ordered into three sequential disciplines:
```
CERTIFY  -->  EVALUATE  -->  IMPROVE
```

## 2. Ordered P6 Capability Boundaries

### P6.0 Live Real-Evidence Certification — CLOSED (TASK-154, TASK-163)

Certify live operational boundaries against real marketplace targets using operator-owned
authenticated CDP sessions before building quality or scale features on top of simulated data.

Live full production certification remains distinct from provider-only TASK-144 (which verified
only the Vertex AI LLM invocation transport).

- **P6.0a Successor Live Marketplace Discovery -> Persisted Product Source Pack Certification (TASK-154 — CLOSED)**:
  Published TASK-154 established the first live evidence certification boundary from the published
  TASK-151 + TASK-153 hardened main. It certified that one explicit live marketplace route using the
  existing CDP browser manager, existing discovery adapter (with published TASK-151 readiness and
  TASK-153 card mapping hardening), and existing platform scrape tool can discover a real candidate
  listing and persist a valid, typed V1 `ProductSourcePack` locally beneath `tmp_path`. Rehydration is
  strictly verified through TASK-125 `deserialize_product_source_pack`. Google Drive publication is
  satisfied by a test-only zero-network Drive sink and was deliberately not certified. TASK-154
  certified only one explicit marketplace route, not both marketplaces.
  Historical TASK-150 and TASK-152 remain preserved as historical failure evidence. Published
  TASK-151 and TASK-153 remain narrow blocker corrections, not new semantic authorities.

- **P6.0b Real-Evidence Canonical Knowledge + Grounded-QA Certification (TASK-163 — CLOSED)**:
  TASK-163 certified the downstream composition slice on current real Shopee evidence: two planned
  acquisitions of one discovered listing, one TASK-138 intake, one TASK-139 actionable family plan,
  explicit certification-local TASK-140 family approval/admission, two singleton TASK-141 variant
  approvals/admissions into disposable TASK-120 SQLite state, and one TASK-135 grounded-QA call from
  the durable database plus exact persisted manifests. Canonical Runtime verification (RUN-163-002 PASS)
  and ChatGPT PRIMARY semantic review (REVIEW-163-002 PASS) both passed on candidate `fa2a49326be28422484db4a37c932681210d8060`.
  P6.0b and P6.0 are CLOSED.

### P6.1 Retrieval-Quality Evaluation / Baseline — CLOSED / PUBLISHED

Establish rigorous, reproducible evaluation baselines for retrieval quality on real acquired
product evidence before introducing any new retrieval paradigm.

P6.1 now proceeds through these ordered gates:
- **P6.1a Evaluation Contract (TASK-164 — CLOSED)**:
  Establishes the pure deterministic evaluation authority over existing TASK-122 lexical retrieval
  and TASK-129 grounded answers, defining `RetrievalBenchmarkCase`, `RetrievalCaseEvaluation`,
  `RetrievalQualityReport`, `GroundedCitationFidelity`, `evaluate_lexical_retrieval_quality`, and
  `evaluate_grounded_answer_citation_fidelity` in `src/product_intelligence/retrieval_quality_evaluation.py`.
  It measures explicit Human-authored benchmark labels using exact Fraction arithmetic, without
  changing retrieval, query planning, RAG context, answer semantics, ranking, canonical knowledge,
  or product truth.
- **P6.1 Live-Capture Blocker Hardening (TASK-166 — CLOSED / PUBLISHED)**:
  TASK-165 remains unpublished blocked P6.1b evidence. REVIEW-165-003 F1 and the failed
  remediation/repair continuation lineage showed that mutable live marketplace interaction does not belong inside
  deterministic AIOS engineering verification. TASK-166 added the explicit external-root,
  checkpoint/resume capture boundary documented in
  `docs/PHASE_6_P6_1_LIVE_CAPTURE_CHECKPOINT.md`.
- **P6.1 Shopee Search-Surface Discovery Hardening (TASK-167 — CLOSED / PUBLISHED)**:
  TASK-166 is CLOSED and published. Its first external READY bundle proved the external capture
  operation, but Human cohort review rejected it because exact query `chuột không dây` mapped to
  an unrelated lantern listing. That bundle remains operational evidence only and is not P6.1b
  benchmark truth. TASK-167 narrowly hardens the existing TASK-151/TASK-153
  `ShopeeDiscoveryAdapter` search-surface provenance boundary; it adds no semantic relevance or
  business-ranking authority.
- **P6.1b Real-Evidence Benchmark Execution (TASK-168 revision 2 — CLOSED / PUBLISHED)**:
  The second reviewed READY bundle is the accepted corpus source. RUN-168-001 remains canonical
  task-design failure evidence with zero source delta: revision 1 wrongly required each
  `SAME_PRODUCT_FAMILY` pair to qualify as one full-member exact variant. Revision 2 preserves
  one two-member family per cohort while representing each canonical member as an explicit
  singleton benchmark variant without claiming sibling real-world difference or changing TASK-116.
  The frozen TASK-164 evaluator records the measured empirical baseline in
  `docs/PHASE_6_P6_1_REAL_EVIDENCE_BASELINE.md`. TASK-168 is published at
  candidate `0e6626a53c10609a1a7b282d7ca49af33e4d5573`; P6.1b is CLOSED.
- **P6.1c Retrieval Stress Benchmark (TASK-169 revision 2 — CLOSED / PUBLISHED)**:
  Reuses the immutable published TASK-168 corpus in place and sends six fixed
  Human-authored paraphrase/attribute cases to TASK-164 exactly once with
  `limit=3`. The measured lexical snapshot is 2 TP, 0 FP, 10 FN, micro precision
  1/1, and micro recall 1/6. These values are observations without a threshold
  or automatic roadmap decision. TASK-169 is published at candidate
  `52d539aa1a2b880f488987cb07c46ea9347dcdcc`; P6.1c is CLOSED. TASK-169 revision
  1, which proposed opening P6.3, was never executed and remains superseded
  authoring history only.
- **P6.1d Planner-Assisted Retrieval Stress Benchmark (TASK-170 — CLOSED / PUBLISHED)**:
  Replays the exact six published TASK-169 stress intents once each through
  TASK-134, then evaluates all six exact planned queries in one TASK-164 call at
  `limit=3` over the immutable TASK-168 corpus. The measured snapshot is 12 TP,
  0 FP, 0 FN, and micro precision and recall of 1/1. This measures the existing
  TASK-134 -> TASK-122 composition without claiming semantic understanding or
  making an automatic architecture decision. TASK-170 is published at candidate
  `0781e0810d161ad1a4936c0e3ea31aada5704da1`; P6.1d and P6.1 are CLOSED.

### P6.2 Conditional Semantic / Vector Retrieval or Reranking — PARKED / NOT JUSTIFIED BY CURRENT EVIDENCE

Raw TASK-122 stress recall was 1/6, but the existing production TASK-134 -> TASK-122
composition recovered 12 TP, 0 FP, 0 FN and micro precision/recall of 1/1 on the
same measured corpus. Separate Brain/Human review therefore does not justify a new
semantic/vector authority from current evidence. P6.2 is parked, not permanently
rejected, and remains reopenable when new evidence demonstrates a need. No metric
threshold declares lexical retrieval universally sufficient.

- Any semantic index must remain a derivative, disposable secondary index; it must never become
  the canonical store of product knowledge or supersede SQLite durability (TASK-120).
- Lexical retrieval must remain available as a deterministic fallback.
- No vector database, external service, or background indexing daemon may be introduced without
  prior architectural authorization and evidence-backed necessity.

### P6.3 Product-Truth Reconciliation — CLOSED (TASK-171 / P6.3a, TASK-172 through TASK-175 / P6.3b, TASK-176)

TASK-171 / P6.3a is CLOSED and PUBLISHED at candidate `3a33748905154b4822cfc164999e5c57780e67f2`,
establishing the Human-governed descriptive-field foundation over exact TASK-121
evidence. It resolves uncontested values, preserves unresolved conflicts, and
permits only explicit Human selection of an existing exact source value.

TASK-172 / P6.3b source hardening is CLOSED and PUBLISHED at candidate
`63525151e4dbb7a1c30454a301e3c0e20ae771e9`. TASK-173 live-DOM hardening is CLOSED
and PUBLISHED at `f91dfe0f900664c835fef86bdf5d6c75879dbbdc`. TASK-174 structural-depth
hardening is CLOSED and PUBLISHED at `8c5a0b2a6a935c5bbecff5cde7b1a32956aa8d32`.
TASK-175 same-target acquisition-continuity hardening is CLOSED and PUBLISHED at candidate
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

### P6.4 Identity Evolution and Migrations — UNIMPLEMENTED / FUTURE / DEFERRED

Define a canonical identity evolution and schema migration authority for long-term catalog lifecycle.

- Handle merge, split, deprecation, and historical lineage tracking for canonical product families
  and sellable variants across schema versions.
- Ensure backwards-compatible rehydration and referential integrity across historical SQLite
  databases.
- Preserve existing M3 / TASK-117 / TASK-118 invariants.

### P6.5 Higher-Level Human-Review Automation — UNIMPLEMENTED / FUTURE / DEFERRED

Introduce higher-level automation to assist the Human review workflow without removing or diluting
explicit Human approval authority.

- Triage assistance: grouping, sorting, and highlighting high-confidence merge proposals to optimize
  operator attention.
- Autonomous approval remains strictly forbidden; every canonical admission must retain explicit
  Human actor attribution and immutable decision records (TASK-140, TASK-141).

### P6.6 Caches and Background Serving — UNIMPLEMENTED / FUTURE / DEFERRED

Implement performance caching and background serving infrastructure only after observed operational
workloads require them.

- Introduce in-memory or persisted query result caches only when profiling demonstrates latency
  or throughput bottlenecks in live environments.
- Maintain strict cache invalidation boundaries tied to SQLite catalog mutation transactions.
- Zero cache or background server infrastructure is permitted during P6.0.

### P7 Commerce Opportunity Intelligence — ACTIVE

The fresh architecture/value audit found no current retrieval, identity-migration,
review-automation, or serving bottleneck that outranks the measurable undercoverage of the
already-defined M2 Winning Product evidence model. P6.2 therefore remains PARKED, and P6.4-P6.6
remain DEFERRED / UNIMPLEMENTED.

- **P7.0 Winning Product Evidence-Coverage Evaluation (TASK-181 — CLOSED / PUBLISHED at `9e835ed2c551c2fa3a8b66b82caa238bd41b152c`)**: freezes one pure,
  bounded evaluator over existing `WinningProductScorer` outputs. It measures scorer-emitted
  category coverage and missing factual signals without changing discovery, normalization,
  scoring, ranking, approval, persistence, retrieval, truth, or collection.
- **TASK-182 / RUN-182-006 — BLOCKED / UNPUBLISHED**: semantic review found malformed Shopee
  `sold_count` evidence, so candidate `94c4e5105e593b9136f186882daacb466c9a304d` and its
  measurements are not baseline truth. Its fixture/test/docs delta, RUN/RESULT/FAILURE/REPAIR
  lineage, and REVIEW-182-006 remain immutable and unpublished.
- **TASK-185 — CLOSED / PUBLISHED at `6b03dc14f88ddb98baeb6ae726f0dd913b323ba1`**:
  hardened the existing Shopee sold-evidence input boundary without changing downstream
  normalization, scoring, ranking, approval, or truth.
- **TASK-186 / RUN-186-003 — BLOCKED / UNPUBLISHED, no source candidate**: the attempted fresh
  baseline stopped because Human-visible current Shopee results were not recognized by the
  existing adapter.
- **TASK-187 — CLOSED / PUBLISHED at `857e6b5d0009e9327e1a92d5f62b91432e28f150`**:
  hardened only the existing Shopee search-result DOM recognition boundary.
- **TASK-188 / RUN-188-004 — BLOCKED / UNPUBLISHED, no source candidate**: its diagnostic
  observations are not baseline truth and grant no continuation authority.
- **TASK-189 — CLOSED / PUBLISHED at `9fa1b2583380e1b6378e5aba3d720c2e78a4b9d4`**: added Session/Access Continuity V2
  through the existing TASK-137 browser and TASK-166 capture authorities.
- **TASK-190 — operational capture staging for P7.1 discovery cohort (CLOSED / PUBLISHED at `22d8837e5955ed78185426f293e874625a34d469`)**: added the bounded `p7-1-discovery-cohort`
  profile to `live_capture.py` and CLI `capture` outside Git and runtime verification, staging 3 queries (5 items/query,
  total 15 distinct candidates) and establishing the post-publication Human review gate.
- **P7.1 Real-Evidence Winning Product Coverage Baseline (TASK-191 — DONE / PUBLISHED at `40da098b3b0dcf3d1994fc510dd55717b81a2f67`)**: freezes exactly the
  one Human-accepted TASK-190 READY discovery bundle byte-for-byte into immutable repository fixtures (`discovery_capture_bundle.json`,
  SHA-256 `aba1cdbc0a74d591a7da6c6dce11b9ae06bb7c16b0fe151490bb74da3efc465a`, byte count 16047), losslessly reconstructs
  the exact fifteen-candidate cohort, and replays published TASK-181 `evaluate_winning_product_coverage` fully offline to
  record the deterministic measured baseline (`baseline.json`). Predecessors TASK-182, TASK-186, and TASK-188 remain BLOCKED /
  UNPUBLISHED historical evidence and are not continued or repaired. Any post-baseline improvement choice remains for
  separate Brain/Human interpretation after publication. Its zero coverage proves only that the
  bounded search-card surface is insufficient for the current scorer; it is not commercial-failure,
  enrichment-priority, or score-change authority.
- **P7.2 Winning Opportunity Semantic Reconciliation (TASK-214 — CLOSED / PUBLISHED at `123bbb71d44ad15a25e07b07f21f6cb2dd00d20b`)**:
  establishes the contextual Winning Opportunity interpretation, the five conceptual reasoning stages,
  the Product Candidate Triage V1 boundary, and the pre-test/post-test evidence boundary subordinate to
  Product Contract v2.
- **P7.3 Decision Context + Opportunity Hypothesis (TASK-215 — CLOSED / PUBLISHED at `dc4c4c8e6f3f4d6eb3441ff4873632e5f51655f9`)**:
  establishes the bounded Commerce Opportunity Intelligence semantic owner for immutable decision
  context and falsifiable opportunity hypothesis values.
- **P7.4 TikTok Affiliate Evidence Profile (TASK-222 — CLOSED / PUBLISHED at `ca6da00e9e58f66e25f2f6edcb416677bed70b6d`)**:
  establishes the bounded Commerce Opportunity Intelligence semantic owner for immutable TikTok
  affiliate evidence profiles organizing opaque references across six fixed dimensions.
- **P7.5 Value-of-Information Planning (TASK-223 — CLOSED / PUBLISHED at `3c67a828857f74466883463abf35a17ecdcc6775`)**:
  establishes the bounded Commerce Opportunity Intelligence semantic owner for immutable
  Value-of-Information inquiries and plans composing P7.3 context/hypothesis and P7.4 evidence profiles,
  evaluating information relevance and trade-offs under explicit CONTINUE, DEFER, or STOP dispositions.
- **P7.6 Market Test / Funnel Evidence (TASK-224 — CLOSED / PUBLISHED at `d361361958fbcbe791c04aefbeba3d186c5f9608`)**:
  establishes the bounded Commerce Opportunity Intelligence semantic owner for immutable
  market test and funnel evidence profiles organizing caller-supplied opaque references
  across exposure, funnel, economic, and quality dimensions bound to P7.3 context and hypothesis.
  It performs no calibration, winner validation, causal attribution, lifecycle transition, or
  scalability judgment.
- **P7.7 Calibration & Winner Validation (TASK-225 — publication-gated DONE; current/final milestone)**:
  establishes one bounded immutable post-test interpretation authority composing exact P7.3
  context/hypothesis with ordered exact P7.6 profiles. It preserves supporting, counter, and
  unresolved evidence without a universal score, probability claim, causal claim, approval,
  lifecycle state, automatic decision, Product Intelligence policy mutation, or scalability truth.

The Human-approved P7.2-P7.7 sequence becomes complete only after source-only publication of the
exact reviewed TASK-225 candidate `6302dd7d01be90624d5ed0072cffbc3c23f2e4a2`. There is no P7.8
or automatic P7 successor. Fresh Human/Brain interpretation selected the bounded P8.0 Real Commerce
Decision Loop Composition contract as the next product commitment without reopening P6.2, P6.4-P6.6,
P7, or Product Intelligence authority.

- **P8.0 Real Commerce Decision Loop Composition (TASK-226 — publication-gated DONE; composition contract only)**:
  establishes `COMMERCE_DECISION_LOOP_P8_0` as one factory-only, pure lineage-composition and
  representation-gap authority over exact P7.3-P7.7 inputs and an optional opaque external decision
  authorization reference. Composition != authority; representation != sufficiency; completeness !=
  real-world success. TASK-226 freezes the contract and does not execute a real pilot, authorize an
  action, perform a market test, attribute an outcome, or select a future intelligence domain.

P8.0 is DONE at exact published source `a9429a5db859ebc6fe7e5fea19aaf17ee11d0d3e`.

- **P8.1 Real Decision Pilot Selection (TASK-227 — publication-gated DONE; `PILOT_CASE_SELECTION_ONLY`)**:
  records the Human-selected product label “Đèn LED Cảm Biến Chuyển Động Tự Động Bật Tắt Điều Chỉnh
  3 Chế Độ Sáng”, TikTok Shop Vietnam source ID `1731381331718341815`, and stable external listing
  reference `https://shop.tiktok.com/vn/pdp/den-led-cam-bien-chuyen-dong-3-che-do-sang-sac-usb-c/1731381331718341815`.
  Source identity is not canonical product identity. P8.1 documents one intended P7.3-owned bounded
  DecisionContext and falsifiable OpportunityHypothesis framing while preserving all live facts,
  affiliate economics, traction, creator/content evidence, audience fit, competition, and
  Human-owned test constraints as unknown. It performs no acquisition, approval, scoring, ranking,
  test authorization, market action, winner/scalability/causal judgment, or future-domain selection.

P8.1 is DONE at exact published source `d2752d69c701dd2483ea30f52be3385b5137e008`.

- **P8.2 Pre-Action Evidence Acquisition Plan (TASK-228 — publication-gated DONE;
  `PRE_ACTION_EVIDENCE_ACQUISITION_PLAN_ONLY`)**: binds only to context
  `p8-pilot-001-led-motion-tiktok-vn`, TikTok Shop Vietnam source ID `1731381331718341815`, and the
  exact P8.1 stable listing reference. It preserves `SOURCE_IDENTITY_IS_NOT_CANONICAL_IDENTITY`, the
  six externally owned P7.4 dimensions, all P7.5 VOI and P7.3-P8.0 authority boundaries, and
  Product Intelligence ownership. It records the current `/vn/pdp/<slug>/<id>` compatibility gap
  as a blocker rather than a completed fix, distinguishes current bounded search-card and Source
  Pack capabilities from unavailable/unproven evidence paths, and defines non-automatic Wave 0,
  Wave 1, and conditional Wave 2 planning with explicit qualitative VOI and STOP conditions. It
  performs no acquisition, parser change, collector configuration, test, approval, spend, market
  action, evidence claim, recommendation, or future-domain selection.

P8.2 is DONE only as plan-only state at exact published source
`eb5b09a8208771a25493fd5a68232bb2dd48c700`; `real_pilot_executed` remains false and it acquired
no live evidence. Human/Brain then explicitly selected the bounded manual Wave-1 contribution path
before Wave 0 compatibility engineering or automated acquisition.

- **P8.3 Manual Wave-1 Evidence Contribution Authorization (TASK-229 — publication-gated DONE;
  `MANUAL_WAVE_1_EVIDENCE_CONTRIBUTION_AUTHORIZATION_ONLY`)**: authorizes one Human-only external
  contribution path for the exact P8.1 case and source listing. Its allowlist is limited to variant
  context, current price/discount and affiliate economics, current sold/rating/review traction, and
  inventory availability. It defines a transport-only external envelope, fail-closed exact-listing
  binding, safe-artifact constraints, Human-only CAPTCHA handling, and a separate per-observation
  Human `ACCEPT` / `REJECT` / `UNKNOWN` review gate. It creates no evidence or canonical truth,
  changes no production code or parser, constructs no P7.4/P7.5 value, authorizes neither Wave 0 nor
  Wave 2 nor a market test/action, and supplies no Human-owned economics, test, or risk input.

On exact reviewed TASK-229 source publication, P8.3 is DONE only as authorization;
`real_pilot_executed` remains false, no concrete task-acquired live evidence is claimed, the next
milestone remains null, and pending commitments remain empty. Nothing advances automatically to
P8.4. The handoff is `HUMAN_OPERATOR_MANUAL_WAVE_1_CONTRIBUTION_AND_REVIEW`; only a later concrete
Human contribution, separate Human review, and fresh deterministic authorization can freeze accepted
safe evidence or construct existing P7.4/P7.5 semantics. P6.2 remains PARKED and P6.4-P6.6 remain
DEFERRED / UNIMPLEMENTED.

See `docs/PHASE_8_P8_0_REAL_COMMERCE_DECISION_COMPOSITION.md` for the exact P8.0 source
`a9429a5db859ebc6fe7e5fea19aaf17ee11d0d3e`,
`docs/PHASE_8_P8_1_REAL_DECISION_PILOT_SELECTION.md` for the exact P8.1 selection record, and
`docs/PHASE_8_P8_2_PRE_ACTION_EVIDENCE_ACQUISITION_PLAN.md` for the exact P8.2 source
`eb5b09a8208771a25493fd5a68232bb2dd48c700`, and
`docs/PHASE_8_P8_3_MANUAL_WAVE_1_EVIDENCE_CONTRIBUTION_AUTHORIZATION.md` for the P8.3 authorization.


The complete audit and P7.0 boundary are recorded in
`docs/PHASE_7_P7_0_WINNING_PRODUCT_EVIDENCE_QUALITY.md`.

## 3. Invariants and Authority Preservation

1. **Prior Authority Invariance**: P1 through P5 authorities remain unchanged and respected:
   - CDP transport/session lifecycle remains TASK-137 authority.
   - Discovery/ranking/shortlisting remains TASK-146 / M2 authority.
   - Evidence packaging remains TASK-125 / M1 authority.
   - Canonical entity resolution and admission remains M3 / P3 authority.
   - Grounded QA and prompt construction remains M4 authority.
   - Human-facing presentation remains P5 authority.
2. **Lineage Preservation**: TASK-150 (RUN-150-001..005), TASK-152 (RUN-152-001), and TASK-156
   (through RUN-156-009) remain preserved as historical failure evidence. Published TASK-151 and
   TASK-153 remain P6.0a blocker corrections; published TASK-162 remains the narrow current Shopee
   acquisition-readiness correction. Published TASK-154 closed P6.0a. TASK-163 alone is the fresh
   current-main P6.0b/P6.0 closure gate.
3. **Certification Isolation**: Live certification fixtures are certification-only modules
   (`tests/integration/`) and must never be imported by production Python code or define new APIs.
4. **Fail-Closed Governance**: Live test fixtures must fail closed with sanitized error categories
   without leaking marketplace credentials, session tokens, URLs, or raw HTML into outputs.
5. **Step-by-Step Evolution**: No stage in P6 may be bypassed. Optimization and scale follow
   empirical evaluation; evaluation follows real-evidence certification.
