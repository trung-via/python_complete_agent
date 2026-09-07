# Post-M4 P5 Human-Facing Product Intelligence Surface

Status: **CLOSED**
Published lineage: TASK-149 closed P5.3c and P5 Human-Facing Product Intelligence Surface

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

Published TASK-148 closed P5.3b by extending that same CLI with the `family-decide`
operation, providing an in-process Human review, selection, and durable admission
boundary over persisted source evidence and canonical SQLite storage via
TASK-138, TASK-139, and TASK-140 without reconstructing proposals or creating
persistent review stores.

Published TASK-149 closed P5.3c by extending that same CLI with the `variant-decide`
operation, providing an in-process Human review, explicit member selection, decision,
and durable admission boundary over persisted canonical SQLite storage via
TASK-120 and TASK-141 without reconstructing proposals, discovering/ranking
variant groups, or creating persistent review stores.

Human member selection is explicit and no variant-group discovery/ranking exists;
only the exact current in-process TASK-141 review may authorize that decision.
Following canonical Runtime PASS and ChatGPT PRIMARY semantic PASS on candidate
132deef99363ffce0c3162c5f59d1b1349563995, P5 Human-Facing Product Intelligence Surface
is CLOSED. P6 is NEXT / CURRENT pending the post-P5 architecture audit.

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

## P5.3b Human family decision + durable admission presentation — CLOSED

Published TASK-148 closed P5.3b by adding the sixth operation to `src/product_intelligence/cli.py`:

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

## P5.3c Human sellable-variant review + decision + durable admission presentation — CLOSED

Published TASK-149 closed P5.3c by adding the seventh operation to `src/product_intelligence/cli.py`:

- `variant-decide` requires exactly one `--database` path, exactly one
  `--family-id` string, exactly one `--actor` string, and exactly one
  `--decided-at` ISO-8601 timestamp. Duplicate occurrences fail closed with
  argparse exit code 2.
- It calls TASK-120 `load_sqlite_canonical_catalog` exactly once with the exact
  Human-supplied `--database` path unchanged, resolving one and only one current
  canonical family by exact string equality with `--family-id` against `catalog.families`.
  Zero matches or ambiguous multiple matches fail closed.
- After resolving the exact current family and before reading Human member selection,
  `variant-decide` renders exactly one bounded family preview to `stderr` exposing
  the exact `family_id` and all family members in canonical family order using the
  bounded `SourceObservationIdentity` representation already introduced in TASK-148,
  without scoring, clustering, recommending, or inferring variant groups.
- Following the family preview, `variant-decide` reads exactly one Human
  member-selection line from `stdin`. The representation must be one or more
  comma-separated 1-based decimal positions without whitespace, signs, ranges,
  wildcard, JSON, or extra tokens. Human position order and duplicates are
  preserved when mapping to exact `family.members` objects; no local variant
  eligibility validation occurs.
- It calls TASK-141 `prepare_sellable_variant_review` exactly once with the exact
  loaded `CanonicalProductFamily` and the exact selected-member tuple. All variant
  eligibility, exact-edge closure, direct-exact matching, singleton proposals, and
  duplicate handling remain delegated solely to TASK-141 / TASK-116.
- After successful review preparation and before reading a Human decision,
  `variant-decide` renders exactly one bounded review preview to `stderr` derived
  only from the exact returned `SellableVariantReview.proposal`, exposing source
  `family_id`, members, and pair evidence (relationship, confidence, reasons, codes,
  details) without reconstructing proposals, scoring, or persisting the preview.
- Only the exact current in-process TASK-141 review prepared in that invocation is
  eligible for Human decision. Following the review preview, `variant-decide`
  reads exactly one additional line from `stdin` containing exact `APPROVE` or
  `REJECT`.
- It maps the decision token to `SellableVariantDecision` and calls TASK-141
  `record_reviewed_sellable_variant_decision` exactly once with the exact current
  review, actor, and parsed decided-at timestamp unchanged.
- For `REJECT`: zero `variant_id` line is read, zero durable admission or SQLite
  mutation occurs, and the output document contains `admission: null`.
- For `APPROVE`: reads exactly one additional line from `stdin` containing
  caller-supplied `variant_id` (stripping only terminal CR/LF, preserving whitespace
  for upstream TASK-117 validation). It delegates durable admission exactly once
  through TASK-141 `durably_admit_reviewed_sellable_variant` with the exact review,
  exact decision record, exact variant_id, and exact database path.
- Successful stdout output is exactly one JSON document with top-level keys
  `decision` and `admission`. For `APPROVE`, `admission` contains `variant_id`,
  `family_id`, `member_source_pack_ids`, and `registration_status`.
- Upstream and application errors remain bounded and sanitized JSON on stderr with
  exit 1 and no traceback.

Placeholder variant-decide example:

```powershell
python -m src.product_intelligence.cli variant-decide --database .\state\canonical-catalog.sqlite3 --family-id "canonical-family-123" --actor "operator@example.com" --decided-at "2026-09-06T12:00:00Z"
```

## Stage completion

With published TASK-149 P5.3c, all seven operations (`evidence`, `catalog`, `ask`,
`discover`, `decide`, `family-decide`, `variant-decide`) across P5.1, P5.2, P5.3a,
P5.3b, and P5.3c are implemented and closed.

Following canonical Runtime PASS and ChatGPT PRIMARY semantic PASS on candidate
132deef99363ffce0c3162c5f59d1b1349563995, P5 Human-Facing Product Intelligence
Surface is CLOSED. P6 is CURRENT / IN PROGRESS under the post-P5 architecture audit
(`docs/POST_P5_P6_QUALITY_SCALE_ROADMAP.md`).

## Post-P5 certification and hardening lineage

- **TASK-150**: Preserved as failed historical certification evidence (RUN-150-001..005,
  latest canonical failure RUN-150-005 with failed_head_sha cb79b3de3c606424632764f3cc24dd2c3925f0bc).
- **TASK-151**: Recorded as published Shopee discovery blocker correction / discovery
  hardening (closed by RUN-151-001 Runtime PASS, REVIEW-151-001 PRIMARY PASS, candidate
  39f39df0efe23c0d18a7292a0b27f92f40a64832), without presenting either as a new semantic authority.
- **TASK-152**: Represented only as the current successor certification (P6.0a)
  re-establishing live discovery-to-persisted-source-pack certification on the published
  TASK-151 fixed baseline.
