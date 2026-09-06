# Post-M4 P5 Human-Facing Product Intelligence Surface

Status: **P5 CURRENT / IN PROGRESS**  
Current candidate: **TASK-148 P5.3b Human family decision + durable admission presentation**

## Stage boundary

Published TASK-144 closed P4 after canonical Runtime PASS and ChatGPT
semantic-review PASS were recorded for the same source candidate. P5 is now the
current post-M4 boundary, but it is deliberately staged: presentation of
persisted state, live discovery and shortlisting, and Human-authorized mutation
do not share one implicit authority.

Published TASK-145 closed P5.1 by supplying the initial Product Intelligence CLI
at `src/product_intelligence/cli.py` for read-only inspection (`evidence`,
`catalog`, `ask`).

Published TASK-146 closed P5.2 by extending that same CLI with the `discover`
operation, composing existing P1 PlaywrightBrowserManager CDP runtime, existing
Shopee/TikTok discovery adapters, and existing M2 DiscoveryOrchestrator /
CandidateRanker vertical slice without introducing a second browser, discovery,
scoring, ranking, approval, or ingestion authority.

Published TASK-147 closed P5.3a by adding the `decide` operation to that same CLI,
providing an in-process Human review/action boundary over the live discovery
shortlist and delegating approved candidates to the existing TASK-096 M1 queue
bridge without reconstructing candidates or creating persistent review stores.

TASK-148 introduces the P5.3b candidate `family-decide` operation to that same
CLI, providing an in-process Human review, selection, and durable admission
boundary over persisted source evidence and canonical SQLite storage via
TASK-138, TASK-139, and TASK-140 without reconstructing proposals or creating
persistent review stores.

Overall P5 remains CURRENT / IN PROGRESS, and P6 is not current.

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

## P5.2 live discovery + deterministic shortlist surface — CLOSED

Published TASK-146 added the fourth operation to `src/product_intelligence/cli.py`:

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

P5.2 is a live-capable composition surface, but deterministic verification is
entirely offline (mocked CDP / unit tests) and does not certify marketplace
availability, login state, captcha freedom, selector freshness, or ranking
quality.

## P5.3a live shortlist Human decision + M1 queue bridge — CLOSED

Published TASK-147 closed P5.3a by adding the fifth operation to `src/product_intelligence/cli.py`:

- `decide` requires the exact bounded discovery inputs (`--query`, one or more
  repeated `--platform` (`shopee` / `tiktok`), `--cdp-endpoint`, optional
  `--shortlist-size`), plus explicit Human identity and timestamp representation
  (`--actor`, `--decided-at` in ISO-8601 format).
- It reuses the canonical private live-discovery helper shared with `discover`,
  completing browser cleanup before any Human interaction begins.
- If discovery or cleanup fails, or if the returned shortlist is empty, execution
  fails closed with zero approval records created and zero queue mutations.
- After successful discovery and cleanup, `decide` renders exactly one current
  review preview to `stderr` using `OrchestrationResult.to_dict()` without
  reordering, filtering, rescoring, or summarizing. The preview is presentation
  only and is never persisted.
- Only the fresh shortlist displayed inside the same `decide` invocation is
  eligible for that decision; prior `discover` JSON is advisory presentation
  only and cannot be rehydrated into approval authority.
- Following the preview, `decide` reads exactly two bounded lines from `stdin`:
  first a 1-based shortlist position, then an exact decision token `APPROVE` or
  `REJECT`. Any EOF, malformed/non-decimal/out-of-range position, extra tokens,
  or non-matching decision fails closed before approval or queue interaction.
- The selected position forwards the exact existing `RankedCandidate` object by
  identity to TASK-096 `create_approval_record` exactly once. Machine scores,
  decision bands, or candidate fields never infer or modify the Human decision.
- For `REJECT`: zero enqueue calls and zero queue filesystem access occur; the
  output document contains `queue: null`.
- For `APPROVE`: delegates exactly once to TASK-096 `enqueue_approval` with default
  queue paths, preserving canonical task construction, idempotency, append
  durability, and completed-file semantics unchanged.
- Successful stdout output is exactly one JSON document with top-level keys
  `approval` and `queue`.

Placeholder decide example using explicit placeholder CDP endpoint:

```powershell
python -m src.product_intelligence.cli decide --query "bình giữ nhiệt inox" --platform shopee --platform tiktok --cdp-endpoint http://127.0.0.1:9222 --shortlist-size 5 --actor "operator@example.com" --decided-at "2026-09-06T12:00:00Z"
```

## P5.3b Human family decision + durable admission presentation — CANDIDATE (TASK-148)

TASK-148 adds the sixth operation to `src/product_intelligence/cli.py`:

- `family-decide` requires one or more repeated Human-supplied `--root` paths,
  exactly one `--database` path, exactly one `--actor` string, and exactly one
  `--decided-at` ISO-8601 timestamp.
- It calls TASK-138 `intake_product_source_evidence` exactly once with the root
  list, then TASK-139 `plan_family_knowledge_review` exactly once with the returned
  inventory.
- If intake or planning fails, execution fails closed with zero Human interaction,
  zero decisions recorded, and zero database mutations.
- After planning succeeds, `family-decide` renders exactly one current review
  preview to `stderr` derived only from the exact `FamilyKnowledgeReviewPlan`,
  exposing all provisional groups in canonical order (including `SINGLETON` and
  `CONFLICTED` diagnostics) and all proposals in exact tuple order with their
  members and pairwise evidence (relationship, confidence, reasons, codes, details)
  without rescoring, filtering, or recommendation.
- Only the exact current in-process TASK-139 proposal shown in that invocation is
  eligible for Human decision; prior JSON cannot be rehydrated into decision/admission
  authority.
- If planning yields zero actionable proposals, the preview is rendered to `stderr`
  so non-actionable groups remain visible, and execution fails closed before
  reading `stdin` and before TASK-140 calls.
- Following the preview, `family-decide` reads exactly two initial bounded lines
  from `stdin`: first a 1-based proposal position within `plan.proposals`, then an
  exact decision token `APPROVE` or `REJECT`.
- The selected position forwards the exact existing `FamilyMergeProposal` object
  by identity to TASK-140 `record_planned_family_decision` exactly once.
- For `REJECT`: zero `family_id` read, zero durable admission or database access
  occur; output document contains `admission: null`.
- For `APPROVE`: reads exactly one additional line from `stdin` containing caller-supplied
  `family_id` (stripping only terminal CR/LF, preserving whitespace for upstream
  validation). It forwards that exact `family_id`, the exact current plan, the
  exact decision record, and the exact `--database` string to TASK-140
  `durably_admit_planned_family` exactly once.
- Successful stdout output is exactly one JSON document with top-level keys
  `decision` and `admission`. For `APPROVE`, `admission` contains `family_id`,
  `member_source_pack_ids`, and `registration_status`.

Placeholder family-decide example:

```powershell
python -m src.product_intelligence.cli family-decide --root .\local-evidence --database .\state\canonical-catalog.sqlite3 --actor "operator@example.com" --decided-at "2026-09-06T12:00:00Z"
```

## Unimplemented later stages

Later P5.3 stages remain unimplemented:

- P5.3c sellable-variant review / decision / durable admission presentation over TASK-141.

No command in P5.1, P5.2, P5.3a, or P5.3b creates persistent review or proposal history
outside canonical SQLite catalog admission, or triggers background ingestion.
Overall P5 remains CURRENT / IN PROGRESS after TASK-148, and P6 is not current.
