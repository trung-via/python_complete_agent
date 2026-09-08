# P6.3 Product-Truth Reconciliation

Status: P6.3 is CURRENT. TASK-171 / P6.3a is CLOSED / PUBLISHED at candidate
`3a33748905154b4822cfc164999e5c57780e67f2`. TASK-172 opens P6.3b as narrow
Shopee selected-variant evidence hardening. P6.2 remains PARKED / reopenable
from future evidence. P6.4-P6.6 remain deferred.

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

## P6.3b selected-variant evidence hardening (TASK-172)

TASK-172 hardens source extraction by observing explicit, complete rendered
variation selection on the current product page strictly inside the positive
current-product briefing scope and appending deterministic `ProductFact`
instances with key `"variant"`, source_section `"selected_variant_controls"`,
and provenance `"selected_variant_controls"` after existing specification and
brand facts.

Evidence, identity, and truth separation:
- Selected-variant facts are observed source evidence only, not canonical variant
  identity or product truth.
- TASK-108 remains the sole pairwise relationship authority, deciding
  `EXACT_VARIANT_MATCH`, `SAME_PRODUCT_FAMILY`, or `DIFFERENT_PRODUCT`.
- TASK-116 remains the sole sellable-variant proposal and Human decision
  authority governing canonical variant admission.
- TASK-171 reconciles descriptive product truth only after a canonical variant
  profile exists.
- TASK-172 does not claim live exact-variant or live product-truth certification;
  live certification remains downstream.

## Explicit exclusions

P6.3 performs zero fact or media reconciliation and changes no family, variant,
catalog, or source identity. It adds no persistence, truth history, retrieval,
query-planning, RAG, grounded-answer, ranking, provider/model, browser, network,
or downstream-consumption path. Reconciled values are not fed into any existing
production consumer.

The focused offline regressions use synthetic multi-observation profiles to
exercise the contract. The published P6.1 fixtures contain singleton benchmark
variants and do not establish a live multi-member conflict corpus. TASK-171 is
therefore a Human-governed descriptive foundation, not certification of live
product truth and not a claim of objective real-world truth.

P6.4 identity evolution, P6.5 higher-level review automation, and P6.6 serving
and caches remain deferred and unimplemented.
