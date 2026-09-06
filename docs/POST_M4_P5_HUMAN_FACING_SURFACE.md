# Post-M4 P5 Human-Facing Product Intelligence Surface

Status: **P5 CURRENT / IN PROGRESS**  
Current candidate: **TASK-146 P5.2 live discovery + deterministic shortlist surface**

## Stage boundary

Published TASK-144 closed P4 after canonical Runtime PASS and ChatGPT
semantic-review PASS were recorded for the same source candidate. P5 is now the
current post-M4 boundary, but it is deliberately staged: presentation of
persisted state, live discovery and shortlisting, and Human-authorized mutation
do not share one implicit authority.

Published TASK-145 closed P5.1 by supplying the initial Product Intelligence CLI
at `src/product_intelligence/cli.py` for read-only inspection (`evidence`,
`catalog`, `ask`).

TASK-146 extends that same CLI with the P5.2 candidate `discover` operation,
composing existing P1 PlaywrightBrowserManager CDP runtime, existing Shopee/TikTok
discovery adapters, and existing M2 DiscoveryOrchestrator / CandidateRanker
vertical slice without introducing a second browser, discovery, scoring, ranking,
approval, or ingestion authority.

P5.2 is closed on the TASK-146 candidate only after canonical Runtime PASS and
ChatGPT semantic-review PASS are both recorded for that same candidate. Until
then it remains a candidate within P5, and overall P5 remains in progress.

## P5.1 read-only operations — CLOSED

The CLI provides three read-only inspection operations closed by TASK-145:

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

## P5.2 live discovery + deterministic shortlist surface — CANDIDATE (TASK-146)

TASK-146 adds the fourth operation to `src/product_intelligence/cli.py`:

- `discover` requires an exact Human search `--query`, one or more repeated
  Human-selected `--platform` arguments (`shopee` or `tiktok` in caller order),
  and an explicit `--cdp-endpoint` URL, with an optional `--shortlist-size` limit.
  It constructs exactly one `PlaywrightBrowserManager` attaching to the supplied
  CDP endpoint, constructs canonical `DiscoveryRequest` and platform adapters in
  Human order, captures one timezone-aware UTC timestamp reused for both
  `observed_at` and `evaluated_at`, and delegates discovery and candidate ranking
  to existing `orchestrate_discovery`. Successful output is exactly the canonical
  `OrchestrationResult.to_dict()` JSON document.
  Browser cleanup (`close_all()`) is attempted exactly once upon completion or
  failure, preserving the primary error if cleanup also fails.

Placeholder discover example using explicit placeholder CDP endpoint:

```powershell
python -m src.product_intelligence.cli discover --query "bình giữ nhiệt inox" --platform shopee --platform tiktok --cdp-endpoint http://127.0.0.1:9222 --shortlist-size 5
```

P5.2 is a live-capable composition surface, but TASK-146 deterministic
verification is entirely offline (mocked CDP / unit tests) and does not certify
marketplace availability, login state, captcha freedom, selector freshness, or
ranking quality.

## Unimplemented later stages

P5.3 explicit Human action and mutation remains a separate, unimplemented
boundary. No P5.1 or P5.2 command approves, admits, enqueues, registers, writes,
or otherwise changes Product Intelligence canonical state.

P5.2 candidate verification does not close overall P5. P5 remains CURRENT / IN
PROGRESS, and P6 is not current.
