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
transitive sellable-variant truth. Family-ID allocation, singleton admission,
canonical profile construction, sellable-variant identity, and catalog persistence
remain later concerns; catalog-wide registration reuse is owned only by TASK-118.

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

## Canonical Sellable-Variant Admission

`create_canonical_sellable_variant` is the narrow identity-binding boundary
after TASK-116 Human review. It accepts exactly one existing
`SellableVariantDecisionRecord` whose decision is explicit `APPROVE` and one
keyword-only, caller-supplied `variant_id`. `REJECT`, a different record type,
or an implicit approval path fails closed. No family, family ID, member,
proposal, projection, or evidence input is accepted separately, so none can
diverge from the approved lineage.

The variant ID is opaque and is preserved exactly. It must be a non-empty,
single-line, NUL-free string with no leading or trailing whitespace; admission
does not parse, normalize, hash, prefix, generate, or derive it. The immutable
`CanonicalSellableVariant` stores only that explicit identity and the exact
TASK-116 approval record. Its proposal, source family, family ID, members, and
Human provenance are read-only views reached through that same record. Thus the
source family is the exact `approval.proposal.source_family` object and members
remain the exact TASK-116 tuple, whether an approved proposal is a singleton or
contains multiple members. All TASK-114, TASK-115, and TASK-116 objects remain
unchanged and auditable by object lineage.

Admission performs no evidence projection, variant proposal or decision
construction, family admission, resolver or grouping work, identity generation,
profile aggregation, persistence, or external operation. It makes no catalog
claim about global or per-family ID uniqueness, ID reuse, one-time admission,
idempotent insertion, cross-record member exclusivity, or future-exhaustive
membership. Those in-memory registration-integrity claims belong only to TASK-118;
durable persistence, profile aggregation, retrieval, and RAG remain deferred to
later milestones.

## Canonical Catalog Integrity

TASK-118 is the sole canonical catalog integrity authority. Its
`CanonicalCatalogState` is an immutable, in-memory snapshot whose exact admitted
families and sellable variants are ordered by their opaque IDs. Separate pure
registration operations enforce family and variant ID uniqueness, reject reuse of
one admission lineage under a different ID, and ensure one source observation is
not assigned to distinct families or distinct variants. Re-registering the same
value, including independently reconstructed value-equal lineage, is an explicit
`ALREADY_PRESENT` no-op that returns the unchanged catalog; a successful new
registration returns `INSERTED` with a new catalog snapshot.

Variant registration requires its exact value-equal source family to have already
been registered under the same family ID. It never admits that family
automatically and never rewrites the variant's identity, approval, family, members,
or evidence lineage. Families may remain without variants, and their members may
remain partially or wholly unassigned. The catalog does not infer a complete
variant partition or a different-variant relationship from unassigned membership.

This boundary is append-only and performs no upstream admission, resolution,
grouping, evidence projection, Human decision creation, identity generation,
profile aggregation, persistence, or external work.

## Canonical Catalog Snapshot Representation

TASK-119 is the representation and trusted-rehydration authority for one exact
TASK-118 catalog snapshot. `encode_canonical_catalog` emits deterministic,
versioned canonical UTF-8 JSON. Families retain their members, complete pair
evidence, and Human approval provenance. Variants refer by index to their source
family, source-family members, and source-family pair evidence, including direct
exact evidence, exactness-gap witnesses, and selected pair evidence. The snapshot
therefore records one bounded value graph rather than recursively duplicating its
lineage.

`decode_canonical_catalog` accepts only the exact canonical V1 byte
representation. It fails closed for malformed or alternate JSON, invalid schema
or fields, invalid scalar values, broken indexes, and inconsistent retained
lineage. Decoding privately rebuilds the already-admitted proposal structures;
it does not run resolution, grouping, projection, proposal discovery, or Human
decision factories. Reconstructed families and evidence values are reused by
variant lineage, then families and variants pass in canonical order through the
TASK-118 registration operations. TASK-118 remains the sole catalog-integrity
authority.

This codec is pure in-memory representation only. Canonical form detects malformed,
non-canonical, or internally inconsistent snapshots but does not authenticate a
snapshot against a malicious party. It provides no transaction/concurrency policy,
backup, migration, signing, MAC, encryption, profile aggregation, retrieval index,
embedding, or RAG behavior.

## Durable Canonical Catalog Snapshot

TASK-120 is the durability and transaction authority for exactly one local SQLite
catalog snapshot. Its V1 store has one schema-constrained singleton row and keeps
the TASK-119 canonical bytes as one opaque BLOB. Creating a store publishes an
empty canonical snapshot without overwriting an existing path; loading strictly
rejects missing, corrupt, version-mismatched, or ambiguous stores rather than
creating, migrating, or repairing them.

Durable family and variant registration reserves the SQLite writer before reading,
decodes the current snapshot through TASK-119, delegates the exact registration to
TASK-118, and updates the BLOB only for `INSERTED`. `ALREADY_PRESENT` commits no
payload update. Each successful insertion writes and commits the complete new
canonical BLOB in one transaction; codec and catalog-integrity failures remain the
distinct TASK-119 and TASK-118 errors and roll back the transaction. SQLite owns
only bounded local durability, writer contention, and recovery of the last committed
snapshot. TASK-118 remains the sole catalog-integrity authority, and TASK-119 remains
the sole canonical-byte and trusted-rehydration authority.

There are no normalized family, variant, member, evidence, or lineage SQL tables;
no arbitrary snapshot replacement API; and no retry loop, WAL policy, migration,
history, backup, replication, identity generation, profile, retrieval, or RAG work.

## Canonical Variant Evidence Profile

TASK-121 adds a pure, read-only evidence projection for one already-registered
canonical sellable variant. `build_canonical_variant_profile` accepts the exact
TASK-118 `CanonicalCatalogState`, locates one variant by its exact opaque ID, and
requires exactly one caller-supplied `ProductSourcePack` for every registered
variant member. Binding uses `SourceObservationIdentity.from_pack(pack)` equality,
while every projected observation, fact, and media item reuses the corresponding
registered canonical member as its evidence-lineage identity.

The profile follows registered variant-member order regardless of source-pack
input order. Within each member it preserves the source pack's descriptive values
exactly, including `None` and conflicting values, and retains every original
`ProductFact` and `OriginalMediaRef` in its source tuple order. It performs no
normalization, deduplication, conflict reconciliation, media selection or
processing, ranking, resolver/grouping/admission workflow, persistence, or
external operation. Conflicting evidence deliberately remains plural; the profile
defines no preferred, best, latest, majority, or averaged product truth.

This profile is only an evidence-preserving projection, not a product-truth
authority, durable storage layer, retrieval index, or RAG document. TASK-118
remains the catalog-integrity authority, TASK-119 remains the canonical-byte
authority, and TASK-120 remains the durability and transaction authority.

## Canonical Profile Lexical Retrieval

TASK-122 adds pure, deterministic, in-memory lexical evidence retrieval over
caller-supplied TASK-121 `CanonicalVariantProfile` values. It applies transient
Unicode NFKC, case folding, and Unicode-alphanumeric tokenization to a bounded
query and to an explicit set of descriptive, fact, and media evidence fields.
Every result requires all distinct query terms and retains exact source evidence
objects and original field values as witnesses. Match classes and exact opaque
variant IDs provide deterministic ordering; no numeric relevance or business
signal participates.

This boundary locates lexical evidence only. It does not select preferred product
truth from conflicting evidence, approve or admit identities, mutate profiles,
persist or index a corpus, use embeddings or models, or perform external work.
M2 `CandidateRanker` remains the separate winning-product business-ranking
authority. RAG document and context construction remain deferred to TASK-123.

## Deferred M3 work

Autonomous merge policy, family-ID allocation, migrations, cryptographic
authenticity, identity evolution, product-truth reconciliation, and RAG/context
construction are explicitly deferred to later M3 milestones, with TASK-123 as
the next RAG/context-construction boundary.
