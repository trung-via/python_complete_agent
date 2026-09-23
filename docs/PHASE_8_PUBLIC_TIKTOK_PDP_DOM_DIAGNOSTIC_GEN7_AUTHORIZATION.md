# Phase 8 Public TikTok PDP DOM Diagnostic Generation-7 Authorization

## Decision and exact publication lineage

TASK-247 is classified exactly as
`FRESH_GENERATION_7_BOUNDED_TITLE_LOCAL_COMMERCE_ROOT_DIAGNOSTIC_AUTHORIZATION_ONLY`. It records
`source_task_id=TASK-246`, `source_run_id=RUN-246-002`,
`source_review_id=REVIEW-246-001`, and
`source_published_sha=60da55d5241c7b4c433d9b2d7d5d3725556f443c`. The exact reviewed and published
TASK-246 source candidate `60da55d5241c7b4c433d9b2d7d5d3725556f443c` is canonicalized as both the V4
implementation source (`diagnostic_v4_implementation_source_sha=60da55d5241c7b4c433d9b2d7d5d3725556f443c`)
and the generation-7 execution source
(`generation_7_execution_source_sha=60da55d5241c7b4c433d9b2d7d5d3725556f443c`). The failed
candidate `538fc65dd737e5c70e7b7ec93dfb6ab0bee8ba6f` is historical failed-run lineage only
and is not generation-7 implementation or execution authority.

Historical implementation and execution provenance remains unchanged: TASK-244 V3 implementation SHA
`bc4c48de89129583f024ab622051ea322f9ff5ea` and generation-6 execution SHA `bc4c48de89129583f024ab622051ea322f9ff5ea`,
TASK-240 V2 implementation SHA `8ef61df3936652fb7aeda8ca31ce1db3621ff4cf`, and TASK-242 generation-5
execution SHA `d113c4a7ce2e2835d532935bc195c922aa3628ca`.

This authorization changes no production diagnostic, parser, CLI, browser, collector, Product
Intelligence, evidence, ranking, approval, test, or action code. It becomes effective only when the
exact reviewed TASK-247 candidate is published.

## Immutable consumed generations 1-6

Generations 1-5 remain their existing consumed historical records. Generation 6 remains consumed history:
`generation_6_diagnostic_executed=true`, `generation_6_authorized_diagnostic_attempts=1`,
`generation_6_authorized_diagnostic_attempts_remaining=0`, owner `HUMAN_OPERATOR`,
`diagnostic_outcome=FAIL_CLOSED`, `diagnostic_failure_reason=NO_BOUNDED_PDP_ROOT`, artifact created,
`evidence_authority=NONE`, and `live_dom_diagnostic_authority=NONE`. No unobserved process exit code
is invented or asserted because the Human-operated terminal transcript did not establish an exact exit-code observation.

The exact generation-6 V3 artifact remains immutable: schema version 3, filename
`tiktok-pdp-dom-diagnostic-v3.json`, SHA256
`A5CD014DD2A9B10DD969843BA37369815A9595248DFB5DD29355376B51143764`, size `27549` bytes,
observed at `2026-09-23T13:14:40.397608+00:00`, with `evidence_authority=NONE`.

Its exact global root probe demonstrated: `title_anchor_count=1`, `price_anchor_count=0`,
`action_anchor_count=0`, `visible_explicit_pdp_root_count=0`,
`explicit_root_with_commerce_anchors_count=0`, `main_present=false`, `main_visible=false`,
`main_has_commerce_anchors=false`, `multi_anchor_common_ancestor_found=false`, and
`selected_root_kind=NONE`.

Its bounded title-local topology probe demonstrated that ancestor level 2 contained 3 currency-like
signals, 2 commerce-semantic actions, and 2 native/role controls within 84 untruncated nodes, which
justified the published V4 `TITLE_LOCAL_COMMERCE_QUORUM` fallback hardening. Generation 7 is not a retry
or reinterpretation of generation 6.

## Exact generation-7 authority

Only exact reviewed TASK-247 publication sets:

- `diagnostic_authorization_generation=7`
- `live_dom_diagnostic_authority=ONE_SHOT_ATTACH_ONLY_EXACT_LISTING`
- `generation_7_authorized=true`
- `generation_7_authorized_diagnostic_attempts=1`
- `generation_7_authorized_diagnostic_attempts_remaining=1`
- `generation_7_diagnostic_execution_owner=HUMAN_OPERATOR`
- `generation_7_diagnostic_executed=false`

Current generation-7 authorization state must not inherit generic generation-6 terminal fields as if
generation 7 already executed. No current `diagnostic_outcome` or `diagnostic_failure_reason` is
asserted before the attempt.

The attempt is bound only to context `p8-pilot-001-led-motion-tiktok-vn`, source ID
`1731381331718341815`, and exact selected listing
`https://shop.tiktok.com/vn/pdp/den-led-cam-bien-chuyen-dong-3-che-do-sang-sac-usb-c/1731381331718341815`.
It grants no arbitrary, replacement, inferred-identity, search, batch, acquisition,
variant-switching, selector-repair, collector-repair, market-test, or commerce-action authority.

The only authorized carrier is `src/product_intelligence/tiktok_pdp_dom_diagnostic.py`,
content-equivalent to `generation_7_execution_source_sha` `60da55d5241c7b4c433d9b2d7d5d3725556f443c`.
The active contract is `schema_version=4`, exact create-exclusive filename
`tiktok-pdp-dom-diagnostic-v4.json`, and `evidence_authority=NONE`.
The canonical CLI subcommand is `tiktok-pdp-dom-diagnostic`. The carrier borrows one session, performs
exactly one `session.evaluate(DIAGNOSTIC_SCRIPT)`, performs zero navigation, refresh, click, type, or
scroll, and retains TASK-137 manager-mediated cleanup. Light-DOM traversal only is enforced, with no
shadow root or iframe traversal.

Root-selection precedence and `TITLE_LOCAL_COMMERCE_QUORUM` semantics are frozen exactly:
1. `EXPLICIT_PDP_ROOT`
2. `MAIN`
3. `MULTI_ANCHOR_COMMON_ANCESTOR`
4. `TITLE_LOCAL_COMMERCE_QUORUM`

The title-local commerce-quorum fallback evaluates candidate ancestor levels in strict ascending order
from narrowest (level 1) to widest (level 6) starting from the unique visible title anchor. Quorum
strictly requires currency-like signal plus a `BUY_LIKE` or `CART_LIKE` action structurally paired to
a visible button control within the candidate ancestor subtree, deduplicating paired controls.
Supporting hints such as `QUANTITY_LIKE`, `VARIANT_LIKE`, and pointer-only interactions cannot satisfy
quorum. The scan fails closed immediately if a narrower unresolved subtree is truncated.

Generation-7 `SUCCESS` is valid for any root kind allowed by published V4. TASK-247 does not require
`TITLE_LOCAL_COMMERCE_QUORUM`, selected ancestor level 2, or any specific root kind. Bounded root
selection means only that the bounded diagnostic root contract is satisfied.

## Non-consuming preflight

Preflight is separate from invocation, must not invoke the diagnostic carrier, and does not consume
the attempt. It may only establish all of the following:

1. CDP `127.0.0.1:9222` is reachable.
2. Read-only browser target enumeration reports exactly one normal `type=page` target in total, and that
   sole target is the exact selected PDP for source ID `1731381331718341815`.
3. A fresh explicit external generation-7 job root contains none of
   `tiktok-pdp-dom-diagnostic-v1.json`, `tiktok-pdp-dom-diagnostic-v2.json`,
   `tiktok-pdp-dom-diagnostic-v3.json`, or `tiktok-pdp-dom-diagnostic-v4.json`.
4. All five execution-critical files are content-equivalent to the exact TASK-246 publication at
   `60da55d5241c7b4c433d9b2d7d5d3725556f443c`:
   - `src/product_intelligence/tiktok_pdp_dom_diagnostic.py`
   - `src/product_intelligence/cli.py`
   - `src/product_intelligence/adapters/tiktok_parsing.py`
   - `src/integrations/playwright/manager.py`
   - `src/integrations/playwright/session.py`

Repository HEAD equality is not required. Preflight does not invoke the carrier and does not consume
the attempt. This target-unambiguity gate preserves TASK-137 as the sole browser/CDP lifecycle and
page-borrowing authority; it creates no second page-selection owner.

The exact fresh external generation-7 job root that passes preflight is bound to the subsequent consuming
invocation. If that root or browser target state is intentionally changed before invocation, the
non-consuming preflight must be repeated; repeating preflight without carrier invocation does not
consume the generation-7 attempt.

## One-line transport and consuming invocation

The Human-facing invocation must be entered as exactly one physical PowerShell line, with no backtick
or multiline continuation:

```powershell
python -m src.product_intelligence.cli tiktok-pdp-dom-diagnostic --job-root <fresh-external-generation-7-job-root> --cdp-endpoint http://127.0.0.1:9222
```

A shell or PowerShell parser/transport failure before a valid `tiktok-pdp-dom-diagnostic` subcommand
dispatches into the carrier is a transport failure and does not by itself consume the attempt. Once
valid carrier invocation begins, every terminal outcome consumes the only generation-7 attempt:
`SUCCESS`, `NO_BOUNDED_PDP_ROOT`, `BLOCKED_OR_CHALLENGE`, `LOGIN_GATE`, `LISTING_UNAVAILABLE`,
`IDENTITY_MISMATCH`, `MALFORMED_DIAGNOSTIC_PAYLOAD`, evaluation/session failure, or any other terminal
outcome. There is no retry, refresh, resume, second invocation, or replacement target.

`SUCCESS` may create the bounded V4 artifact. `NO_BOUNDED_PDP_ROOT` retains the create-exclusive V4
`FAIL_CLOSED` artifact contract. Other safe failures may remain artifact-free under the published
carrier. Every artifact retains `evidence_authority=NONE`.

## Interpretation and handoff

Mandatory post-attempt review authority returns to
`HUMAN_BRAIN_GENERATION_7_BOUNDED_TITLE_LOCAL_COMMERCE_ROOT_DIAGNOSTIC_REVIEW`. Brain review must use
actual terminal output plus the exact V4 artifact if created; if an artifact exists, its actual
SHA256, size, and timestamp are review evidence and must not be guessed.

Preserve epistemic boundaries after the attempt: V4 `SUCCESS` does not prove canonical price, canonical
action capability, Product Truth, acquisition success, or collector readiness; `NO_BOUNDED_PDP_ROOT`
does not self-authorize repair. Root, topology, and quorum observations remain engineering diagnostic
hints only.

`root_observability_hardening_implemented=true`, `commerce_observability_hardening_implemented=true`,
and `diagnostic_hardening_implemented=true` remain true. `selector_repair_complete=false`,
`live_public_pdp_acquisition_authority=NONE`, `automated_public_pdp_acquisition_authority=NONE`,
`market_test_or_action_authority=NONE`, and `automatic_progression=false`.
`active_track.next_milestone` remains null, `post_p8_planning_handoff.next_milestone` remains null,
pending commitments remain empty, and `post_run_engineering_successor=null`.

The exact current global handoff is
`HUMAN_OPERATOR_GENERATION_7_BOUNDED_TITLE_LOCAL_COMMERCE_ROOT_DIAGNOSTIC_EXECUTION`. After the single
Human-operated attempt terminates, review authority returns to
`HUMAN_BRAIN_GENERATION_7_BOUNDED_TITLE_LOCAL_COMMERCE_ROOT_DIAGNOSTIC_REVIEW`. TASK-247 selects no
engineering successor and authorizes no automatic progression. `CAPABILITY_IS_NOT_AUTHORITY`,
`EVIDENCE_IS_NOT_PRODUCT_TRUTH`, `SOURCE_IDENTITY_IS_NOT_CANONICAL_IDENTITY`, `SNAPSHOT_IS_NOT_TREND`,
and `ONE_CAPABILITY_ONE_AUTHORITY` remain mandatory.
