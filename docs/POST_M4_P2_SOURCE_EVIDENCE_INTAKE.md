# Post-M4 P2 Source Evidence Intake

Status: CLOSED by TASK-138
Scope: bounded, read-only local discovery and immutable evidence inventory

## Boundary

TASK-138 adds one synchronous application boundary:
`intake_product_source_evidence(roots) -> SourceEvidenceInventory`.
Callers supply explicit local directory roots. The intake materializes that input once,
resolves existing directories, recursively selects only regular files named exactly
`source_pack.json`, rejects manifest filesystem aliases, applies private root,
directory, and manifest limits, and orders unique canonical absolute paths
deterministically. It performs no implicit working-tree, Drive, browser, or network
discovery.

The returned `SourceEvidenceInventory` is frozen and contains only two aligned
tuples: `manifest_paths` and `source_packs`. Each typed pack at an index is the exact
result of passing the manifest path at that index once to TASK-125
`deserialize_product_source_pack`. Decoder failures remain decoder failures; intake
does not parse, repair, skip, normalize, copy, or rewrite manifest content.

After rehydration, intake uses only exact `SourceObservationIdentity.from_pack`
equality to reject duplicate observations across distinct manifests. It does not
infer identity, rank evidence, select latest or preferred facts, resolve products,
or admit canonical knowledge.

## Authority ownership

- Scrape tools and Product Source Pack serialization own evidence creation and V1
  persistence.
- TASK-125 owns strict typed rehydration of one explicit persisted manifest.
- TASK-138 owns only configured-root discovery and the immutable aligned inventory.
- `SourceObservationIdentity` owns exact source-observation identity projection.
- M3 owns resolution and Human-governed canonical family/variant admission.
- TASK-135 owns persistent grounded QA from explicit manifest paths.

These authorities are composed but not duplicated. TASK-138 introduces no registry,
database, cache, watcher, background scan, catalog mutation, Human approval action,
grounded-QA call, provider/model call, or remote I/O. Its `source_packs` tuple can be
passed unchanged to the existing M3 multi-observation API, and its
`manifest_paths` tuple is the explicit path shape consumed by TASK-135.

## Next boundary

P3 Human-Governed Knowledge Update Workflow is next. P3 is not implemented here;
it requires a separate authority boundary around composition of existing M3 Human
decision and canonical persistence operations.
