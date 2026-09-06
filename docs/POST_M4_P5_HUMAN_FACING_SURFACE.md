# Post-M4 P5 Human-Facing Product Intelligence Surface

Status: **P5 CURRENT / IN PROGRESS**  
Current candidate: **TASK-145 P5.1 read-only CLI foundation**

## Stage boundary

Published TASK-144 closed P4 after canonical Runtime PASS and ChatGPT
semantic-review PASS were recorded for the same source candidate. P5 is now the
current post-M4 boundary, but it is deliberately staged: presentation of
persisted state, live discovery and shortlisting, and Human-authorized mutation
do not share one implicit authority.

TASK-145 supplies only P5.1, a separate Product Intelligence CLI at
`src/product_intelligence/cli.py`. It is invoked from the repository root as
`python -m src.product_intelligence.cli` and does not replace or wrap the
existing autonomous `main.py` / `AgentController` task-queue surface.

P5.1 is closed on the TASK-145 candidate only after canonical Runtime PASS and
ChatGPT semantic-review PASS are both recorded for that same candidate. Until
then it remains a candidate within P5, and overall P5 remains in progress.

## P5.1 read-only operations

The CLI exposes exactly three operations:

- `evidence` delegates configured-root discovery and typed intake once to
  TASK-138, then presents the returned aligned manifest paths and bounded source
  pack fields in their returned order.
- `catalog` delegates one SQLite catalog load to TASK-120, then presents exact
  family and variant counts, identifiers, and member `source_pack_id` sequences
  in catalog order.
- `ask` requires a Human to select `developer_api` or `vertex_ai`, delegates
  intake once to TASK-138, constructs the existing `GeminiProvider` for only
  that selected backend, and delegates the persisted grounded question once to
  TASK-135. Its output is limited to the TASK-129 answer status, text,
  citation identifiers, and limitations.

Examples use placeholder local paths and contain no credential, account,
project, or secret values:

```powershell
python -m src.product_intelligence.cli evidence --root .\local-evidence --root .\imported-evidence
python -m src.product_intelligence.cli catalog --database .\state\canonical-catalog.sqlite3
python -m src.product_intelligence.cli ask --database .\state\canonical-catalog.sqlite3 --root .\local-evidence --question "Which persisted variants mention a stainless-steel body?" --backend vertex_ai
```

Provider credentials and provider-specific environment configuration remain
outside this CLI and under the existing `GeminiProvider` / Google SDK
boundaries. The CLI has no credential, model, project, location, retry,
fallback, or provider-routing option. It does not persist answers or mutate
evidence or catalog state.

## Unimplemented later stages

P5.2 live discovery plus deterministic shortlist remains a separate,
unimplemented boundary. It will require its own authority design over existing
M2 discovery and ranking rather than extending P5.1 inspection into an implicit
search operation.

P5.3 explicit Human action and mutation also remains a separate, unimplemented
boundary. No P5.1 command approves, admits, enqueues, registers, writes, or
otherwise changes Product Intelligence state.

P5.1 therefore does not close overall P5. P6 has not advanced.
