# Phase 6 M3: Pairwise Product Entity Resolution

M3 begins with a platform-neutral, pairwise identity decision over two immutable
`ProductSourcePack` observations. The resolver is deterministic and read-only;
it performs no network access, ingestion, catalog writes, or automatic merge.

## Identity boundary

Three identities must remain separate:

1. **Marketplace listing** identifies one platform-scoped seller page. Its URL,
   seller, `source_product_id`, and extractor-observed `model_sku` are not global
   product identifiers.
2. **Canonical product family** identifies the underlying model or product line,
   using reliable manufacturer/global identity evidence rather than listing
   similarity.
3. **Sellable variant** identifies a material configuration within a family,
   such as color, capacity, size, voltage, or edition. An explicit bundle or
   multipack is materially different composition, not merely another listing.

`EXACT_VARIANT_MATCH` requires reliable same-family evidence and affirmative
matching observed variant evidence. Missing variant data stays unknown.
`SAME_PRODUCT_FAMILY` covers known different variants and same-family pairs that
lack enough variant evidence for exactness. Reliable family or composition
conflicts produce `DIFFERENT_PRODUCT`. Weak prose or media similarity alone
produces `UNCERTAIN`.

The result retains both source observation identities, bounded confidence,
reason codes, and compact evidence. Reversing inputs preserves relationship and
confidence; left/right observation bindings follow the caller's input order.

## Deferred M3 work

Persistent canonical IDs and catalog mutation, multi-observation evidence
aggregation, clustering/merge approval, retrieval, and RAG are explicitly
deferred to later M3 milestones.
