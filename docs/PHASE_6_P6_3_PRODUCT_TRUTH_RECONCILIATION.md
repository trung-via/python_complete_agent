# P6.3 Product-Truth Reconciliation

Status: P6.3 is CLOSED on successful TASK-176 publication. TASK-171 / P6.3a is
CLOSED / PUBLISHED at candidate `3a33748905154b4822cfc164999e5c57780e67f2`.
TASK-172 / P6.3b source hardening is CLOSED / PUBLISHED at
`63525151e4dbb7a1c30454a301e3c0e20ae771e9`. TASK-173 live-DOM hardening is
CLOSED / PUBLISHED at `f91dfe0f900664c835fef86bdf5d6c75879dbbdc`. TASK-174
structural-depth hardening is CLOSED / PUBLISHED at
`8c5a0b2a6a935c5bbecff5cde7b1a32956aa8d32`. TASK-175 same-target
acquisition-continuity hardening is CLOSED / PUBLISHED at candidate
`61f78f8ac1cd14e6e110552ba638eb9ca149403f`. TASK-176 records the successful
bounded K550 live certification passage, closing P6.3.
P6.2 remains PARKED / reopenable from future evidence. P6.4-P6.6 remain deferred /
unimplemented pending a fresh architecture/value audit.

## P6.3a authority boundary

TASK-171 adds one pure, deterministic, in-memory derivative projection over an
exact TASK-121 `CanonicalVariantProfile`. It considers exactly `title`,
`shop_name`, `brand`, `model_sku`, and `description_text`. For each field it
preserves exact source strings, first-value option order, and every canonical
member supporting each option. Python `None` alone represents missing evidence.
TASK-121 remains the authoritative evidence-preserving projection and is not
modified, rewritten, normalized, or superseded.

No evidence automatically wins a genuine conflict. Zero exact values produces
no evidence; one distinct exact value is uncontested; multiple distinct exact
values remain unresolved unless the caller supplies one explicit valid Human
decision. A Human may select only a canonical member carrying one existing exact
value, in which case every member carrying that same value remains visible, or
may explicitly leave the conflict unresolved. The decision retains the exact
field, action, actor, timezone-aware caller-supplied timestamp, and selected
member when applicable.

TASK-171 introduces no automatic recency, majority, provenance, marketplace,
ranking, confidence, business-signal, retrieval-score, or model preference. It
does not trim, case-fold, accent-fold, normalize, fuzzily equate, synthesize, or
replace source strings. Missing Human review is valid partial truth and never
causes an inferred winner.

## P6.3b selected-variant evidence hardening (TASK-172 through TASK-175)

Published TASK-172 hardens source extraction by observing explicit, complete rendered
variation selection on the current product page strictly inside the positive
current-product briefing scope and appending deterministic `ProductFact`
instances with key `"variant"`, source_section `"selected_variant_controls"`,
and provenance `"selected_variant_controls"` after existing specification and
brand facts.

TASK-173 preserves that contract while correcting one proven live-DOM compatibility
blocker. An identity-matched `section.C21rQm` gallery child may expand only to the
nearest bounded enclosing current-product scope needed to reach sibling details
controls. Exact `selection-box-selected` and `selection-box-unselected` button tokens
join the existing TASK-172 option families under the same deterministic complete-group
coverage rule. Ambiguous or absent roots, gallery thumbnail masks, and lower-page or
add-on content remain fail-closed or out of scope.

TASK-174 preserves the same private observation path and permits the immediate
selection-box option cluster to pass through only a finite bounded chain of
transparent option-bearing wrappers to the nearest structurally proven group.
That group must expose exactly one accepted direct semantic label source and one
option-bearing direct child branch. The observed direct `H2` label `"Model"` is
accepted without a minified class; missing or blank labels, Quantity/stock,
independent option branches, and unrelated higher headings remain fail-closed.

The post-publication raw live checkpoint then observed exactly the complete
selection `Model: K550 Trắng Red V4` on an already-rendered same-target page.
The production acquisition path nevertheless navigated that page again and
cleared the Human-selected state before extraction. TASK-175 narrowly preserves
the acquired page when matching normalized HTTP(S) hosts and current-path Shopee
product identity prove the same source item; every unproven location retains one
exact target navigation. This continuity decision does not select a variant or
authorize facts from URL/query state.

Evidence, identity, and truth separation:
- Selected-variant facts are observed source evidence only, not canonical variant
  identity or product truth.
- TASK-108 remains the sole pairwise relationship authority, deciding
  `EXACT_VARIANT_MATCH`, `SAME_PRODUCT_FAMILY`, or `DIFFERENT_PRODUCT`.
- TASK-116 remains the sole sellable-variant proposal and Human decision
  authority governing canonical variant admission.
- TASK-171 reconciles descriptive product truth only after a canonical variant
  profile exists.
- TASK-175 is CLOSED / PUBLISHED at candidate `61f78f8ac1cd14e6e110552ba638eb9ca149403f`.
  Following publication, the post-publication Human-owned live checkpoint executed and
  completed with `P6.3 LIVE RESULT: PASS`, closing P6.3 under TASK-176.

## Bounded K550 live certification record (TASK-176 closure)

Following the publication of TASK-175 at `61f78f8ac1cd14e6e110552ba638eb9ca149403f`,
the Human executed the external live checkpoint using the operator-owned authenticated
Chromium/CDP session and one clean Shopee K550 page for `source_product_id 10374101498`,
with explicit rendered Human selection `"Model: K550 Trắng Red V4"` and no unresolved
CAPTCHA during the successful run.

The successful checkpoint proved the exact authority chain:
1. Two distinct live `ProductSourcePack` observations of the same listing preserved
   exact selected-variant `ProductFact` evidence (`"Model: K550 Trắng Red V4"`) and
   distinct `observed_at` identities.
2. TASK-108 evaluated the two observations and returned `EXACT_VARIANT_MATCH`.
3. A conflict-free two-member family path and a two-member TASK-116 sellable-variant
   proposal with exactly one direct exact pair succeeded.
4. Canonical in-memory family and sellable-variant admission and catalog registration
   succeeded.
5. TASK-121 produced a two-member, two-observation `CanonicalVariantProfile` retaining
   both variant facts.
6. TASK-171 descriptive-truth reconciliation completed.
7. The Human-owned script reached exactly `P6.3 LIVE RESULT: PASS`.

Certification boundary and explicit non-claims:
- **Bounded certification boundary**: The live passage certifies the exercised authority
  composition on one explicit current Shopee K550 listing/variant (`source_product_id 10374101498`,
  rendered selection `"Model: K550 Trắng Red V4"`) under Human-owned authenticated CDP interaction.
- **No overbroad claims**: It does not prove or certify all Shopee pages, all DOM shapes,
  TikTok, cross-platform identity, objective real-world truth, fact/media reconciliation,
  persistent truth history, downstream truth consumption, marketplace SLA, or future
  seller-page stability.
- **Evidence, identity, and truth separation**:
  - Selected-variant facts remain source evidence.
  - TASK-108 remains pairwise relationship authority (`EXACT_VARIANT_MATCH`).
  - TASK-116 remains Human exact-variant proposal/decision authority.
  - TASK-121 remains evidence projection.
  - TASK-171 remains Human-governed descriptive reconciliation where unresolved conflicts
    are valid and no automatic winner is implied.
  - No objective truth, global marketplace, TikTok, cross-platform, fact/media
    reconciliation, persistence, or downstream-consumption claim is introduced.

## Explicit exclusions

P6.3 performs zero fact or media reconciliation and changes no family, variant,
catalog, or source identity. It adds no persistence, truth history, retrieval,
query-planning, RAG, grounded-answer, ranking, provider/model, browser, network,
or downstream-consumption path. Reconciled values are not fed into any existing
production consumer.

The focused offline regressions use synthetic multi-observation profiles to
exercise the contract. The published P6.1 fixtures contain singleton benchmark
variants and do not establish a live multi-member conflict corpus. TASK-171 is
therefore a Human-governed descriptive foundation, not certification of all live
product truth across marketplaces and not a claim of objective real-world truth.

P6.3 is CLOSED. P6.2 remains PARKED / reopenable from future evidence. P6.4 identity
evolution, P6.5 higher-level review automation, and P6.6 serving and caches remain
deferred and unimplemented pending a fresh architecture/value audit across those
boundaries or a separately justified Product Intelligence/Commerce roadmap extension.
Closing P6.3 does not authorize immediate P6.4 implementation.
