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

## Evidence-Complete Family Merge Approval

`create_family_merge_proposal` adds a Human review boundary over existing graph
evidence. It accepts exactly one `MultiObservationResolutionGraph` and one exact
canonical `POSITIVE_CONNECTED` group returned by `group_resolution_graph` for that
graph. `SINGLETON`, `CONFLICTED`, forged, stale, absent, and otherwise non-canonical
groups fail closed. Existing conflicts cannot be suppressed or Human-overridden at
this boundary.

The immutable `FamilyMergeProposal` retains the canonical TASK-111 member tuple and
exactly $N \times (N - 1) / 2$ `FamilyMergePairEvidence` values. Each value copies the
corresponding TASK-109 result's relationship, confidence, reasons, and
`ResolutionEvidence` unchanged. Only endpoint orientation and outer pair ordering
are canonicalized from member order. In particular, a direct `UNCERTAIN` pair stays
visible inside a positive-connected proposal; connectivity is never promoted to
transitive pairwise truth.

`create_family_merge_decision_record` requires an explicit `APPROVE` or `REJECT`, a
non-empty single-line actor, and a timezone-aware `decided_at`. Proposal construction
never creates or implies approval. `APPROVE` authorizes only a future milestone to
treat that exact member set as one canonical family; `REJECT` records only the Human
decision. Neither operation re-runs entity resolution, assigns identity, rewrites
evidence, merges observations, persists data, or performs an external side effect.

## Canonical Product-Family Admission

`create_canonical_family` is the narrow identity admission boundary after Human
review. It accepts exactly one existing `FamilyMergeDecisionRecord` whose decision
is explicit `APPROVE` and one explicit caller-supplied `family_id`. `REJECT`, a
different record type, or any implicit approval path fails closed.

The family ID is opaque and is preserved exactly. It must be a non-empty,
single-line, NUL-free string with no leading or trailing whitespace; the boundary
does not parse, normalize, hash, prefix, generate, or establish catalog-wide
uniqueness for it. The immutable `CanonicalProductFamily` retains the exact
`proposal.members` tuple and the exact decision record as approval provenance, so
the Human actor and timestamp and every relationship, confidence, reason, and
`ResolutionEvidence` value remain auditable without recomputation.

Admission performs no pairwise or multi-observation resolution, grouping, proposal
construction, profile aggregation, sellable-variant assignment, persistence, or
catalog mutation. In particular, preserved `SAME_PRODUCT_FAMILY`,
`EXACT_VARIANT_MATCH`, and `UNCERTAIN` evidence is not rewritten or promoted into
transitive sellable-variant truth. Family-ID allocation and reuse, singleton
admission, canonical profile construction, sellable-variant identity, and catalog
persistence remain later concerns.

## Sellable-Variant Evidence Projection

`project_sellable_variant_evidence` is a read-only evidence and diagnostic
boundary after canonical family admission. It accepts exactly one existing
`CanonicalProductFamily` and reads only the exact `FamilyMergePairEvidence`
objects retained through `family.approval.proposal.pair_evidence`. It neither
accepts nor reconstructs source packs, graphs, provisional groups, proposals, or
resolution inputs.

The immutable projection preserves as direct exact evidence exactly those pair
objects whose relationship is `EXACT_VARIANT_MATCH`. Other direct relationships
remain authoritative and unchanged. If a non-exact endpoint pair is connected
by direct exact edges, one exactness-gap diagnostic preserves that non-exact pair
and a deterministic all-exact witness path. The witness is shortest by edge count,
then canonical by admitted member order. This connectivity is diagnostic only: it
does not infer an exact endpoint relationship or create a variant group, component,
identity, confidence, recommendation, or state.

The projection itself creates no sellable-variant proposal or Human decision.

## Explicit Sellable-Variant Proposal and Human Decision

`create_sellable_variant_proposal` is the bounded review boundary inside exactly
one existing `CanonicalProductFamily`. The caller must explicitly supply a
non-empty member tuple; the operation does not discover, enumerate, rank,
partition, cluster, or recommend candidate variants. Caller order is normalized
to the exact admitted family-member order.

The operation calls `project_sellable_variant_evidence(family)` exactly once and
retains that exact immutable projection as its sole variant-evidence lineage. A
multi-member selection is eligible only when every unordered internal pair has
its preserved **direct** `EXACT_VARIANT_MATCH` `FamilyMergePairEvidence` object.
Exact connectivity through another member is never substituted for a direct
edge. The resulting proposal retains exactly $N \times (N - 1) / 2$ original pair
objects by identity, without copying, inference, rewriting, or confidence
aggregation.

Eligibility also requires exact-edge closure: no direct exact edge may connect a
selected member to an unselected member of the source family. Consequently, an
A-B exact, B-C exact, A-C non-exact gap cannot be bypassed by overlapping A-B or
B-C proposals. The full triple fails its direct all-pairs requirement, while
every proper exact-connected subset fails closure. A singleton is eligible only
when it has no direct exact edge to another family member, and its proposal
retains an empty pair-evidence tuple. Thus an isolated C may be proposed
explicitly alongside a separate closed A-B exact pair without implying a family
partition or automatically creating either proposal.

`create_sellable_variant_decision_record` separately requires one exact canonical
proposal, an explicit `APPROVE` or `REJECT`, a non-empty single-line NUL-free Human
actor, and an explicit timezone-aware decision time. `APPROVE` authorizes no more
than a future milestone admitting those exact members as one canonical sellable
variant within that exact source family. `REJECT` grants no admission authority.
Neither decision states that unselected members are different variants, completes
the family's partition, or makes current membership exhaustive for future
observations.

Proposal and decision construction create no identity or profile, re-run no
resolution/grouping/family admission, mutate no catalog, persist no state, and
perform no external work.

## Deferred M3 work

Autonomous merge policy, family-ID allocation and catalog-wide uniqueness,
canonical sellable-variant identity, variant profile aggregation, persistent
catalog mutation, retrieval, and RAG are explicitly deferred to later M3
milestones.
