# Post-P5 P6 Quality and Scale Roadmap

Status: **P6.0, P6.1, and P6.3 are CLOSED. TASK-170 / P6.1d is CLOSED / PUBLISHED at candidate `0781e0810d161ad1a4936c0e3ea31aada5704da1`. P6.2 is PARKED / NOT JUSTIFIED BY CURRENT EVIDENCE and remains reopenable from future evidence. P6.3 is CLOSED with TASK-171 / P6.3a CLOSED / PUBLISHED at candidate `3a33748905154b4822cfc164999e5c57780e67f2`, TASK-172 / P6.3b source hardening CLOSED / PUBLISHED at `63525151e4dbb7a1c30454a301e3c0e20ae771e9`, TASK-173 live-DOM hardening CLOSED / PUBLISHED at `f91dfe0f900664c835fef86bdf5d6c75879dbbdc`, TASK-174 structural-depth hardening CLOSED / PUBLISHED at `8c5a0b2a6a935c5bbecff5cde7b1a32956aa8d32`, TASK-175 same-target acquisition-continuity hardening CLOSED / PUBLISHED at candidate `61f78f8ac1cd14e6e110552ba638eb9ca149403f`, and TASK-176 recording the bounded K550 live certification passage. The fresh architecture/value audit selects the separately justified P7 Commerce Opportunity Intelligence branch. TASK-181 is the open P7.0 evaluation-contract gate; a separate real-evidence coverage baseline is NEXT. P6.4-P6.6 remain DEFERRED / UNIMPLEMENTED, and P7.0 is not CLOSED before canonical Runtime and semantic-review PASS on the same source candidate.**
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

### P7 Commerce Opportunity Intelligence — SELECTED / NOT YET CLOSED

The fresh architecture/value audit found no current retrieval, identity-migration,
review-automation, or serving bottleneck that outranks the measurable undercoverage of the
already-defined M2 Winning Product evidence model. P6.2 therefore remains PARKED, and P6.4-P6.6
remain DEFERRED / UNIMPLEMENTED.

- **P7.0 Winning Product Evidence-Coverage Evaluation (TASK-181 — OPEN GATE)**: freeze one pure,
  bounded evaluator over existing `WinningProductScorer` outputs. It measures scorer-emitted
  category coverage and missing factual signals without changing discovery, normalization,
  scoring, ranking, approval, persistence, retrieval, truth, or collection. TASK-181/P7.0 is not
  CLOSED until canonical Runtime PASS and ChatGPT semantic-review PASS exist on the same source
  candidate.
- **NEXT — separate real-evidence coverage baseline**: after P7.0 closure, run the frozen evaluator
  on reviewed real marketplace observations. No live coverage percentage is claimed by TASK-181,
  and longitudinal, commercial/affiliate, competition, or semantic Contentability enrichment
  remains conditional on that later baseline.

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
