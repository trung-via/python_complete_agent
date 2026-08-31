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

## Multi-Observation Resolution Graph

Evaluating collections of 2 to 100 `ProductSourcePack` observations operates through
the `resolve_multi_observations` boundary:

1. **Exact Pairwise Evaluation**: Delegates to `resolve_product_entities` for each of
   the $N \times (N - 1) / 2$ unordered pairs without independently recreating pairwise
   semantics or deriving aggregate confidence.
2. **Deterministic Pre-Validation**: Input cardinality (2 to 100) and exact
   `SourceObservationIdentity` uniqueness are verified prior to pairwise evaluation.
   Observations sharing `source_pack_id` but with different `observed_at` timestamps
   remain valid distinct observations.
3. **Auditable Product-Family Consistency Conflicts**: When observations connected
   through a path of positive product-family relationships (`EXACT_VARIANT_MATCH` or
   `SAME_PRODUCT_FAMILY`) also contain a direct `DIFFERENT_PRODUCT` pairwise decision,
   the graph records an auditable `ProductFamilyConsistencyConflict` preserving the
   contradictory pair, positive path evidence, and affected observation identities.
4. **UNCERTAIN Boundary**: `UNCERTAIN` relationships do not establish positive family
   connectivity or trigger consistency conflicts.
5. **Conflict Isolation Without Repair**: Consistency diagnostics never repair, merge,
   cluster, or rewrite observations or pairwise results.

## Provisional Product-Family Grouping

Partitioning an existing `MultiObservationResolutionGraph` operates through the
`group_resolution_graph` projection boundary:

1. **Pure Projection Over Existing Graph**: Accepts exactly one `MultiObservationResolutionGraph`
   and executes zero additional pairwise or multi-observation entity resolution calls.
2. **Positive-Family Connectivity Partition**: Groups are derived exclusively from positive
   pairwise relationships (`EXACT_VARIANT_MATCH` and `SAME_PRODUCT_FAMILY`). `UNCERTAIN` and
   `DIFFERENT_PRODUCT` edges never bridge components.
3. **Exact Invariant Partitioning**: Every `SourceObservationIdentity` in `graph.observations`
   appears in exactly one provisional group; no observations are dropped, duplicated, or merged.
4. **Provisional Statuses**:
   - `SINGLETON`: Exactly one observation in the component.
   - `POSITIVE_CONNECTED`: Two or more observations connected by positive edges with zero consistency conflicts.
   - `CONFLICTED`: Two or more observations containing one or more existing `ProductFamilyConsistencyConflict` values from the graph.
5. **Conflict Preservation**: Existing graph conflicts are retained on the respective group without
   repair, suppression, or winner-selection.
6. **Deterministic & Immutable**: Group membership, member ordering, and outer group order are strictly
   canonical and permutation-invariant.

## Deferred M3 work

Merge proposal, human merge approval, autonomous merge policy, canonical product-family IDs,
sellable variant IDs, persistent catalog mutation, evidence aggregation, retrieval, and RAG are
explicitly deferred to later M3 milestones.


