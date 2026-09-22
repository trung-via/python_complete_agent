# Phase 8 Public TikTok PDP DOM Diagnostic Generation-5 Authorization

## Decision and exact publication lineage

TASK-243 is classified exactly as
`FRESH_GENERATION_5_COMMERCE_OBSERVABILITY_DIAGNOSTIC_AUTHORIZATION_ONLY`. It records
`source_task_id=TASK-242`, `source_run_id=RUN-242-001`,
`source_review_id=REVIEW-242-001`, and
`source_published_sha=d113c4a7ce2e2835d532935bc195c922aa3628ca`. The distinct generation-5
execution binding is
`generation_5_execution_source_sha=d113c4a7ce2e2835d532935bc195c922aa3628ca`.
The historical TASK-240 V2 implementation provenance remains unchanged as
`diagnostic_v2_implementation_source_sha=8ef61df3936652fb7aeda8ca31ce1db3621ff4cf`.

This authorization changes no production diagnostic, CLI, browser, collector, parser,
Product Intelligence, evidence, ranking, approval, test, or action implementation. It becomes
effective only when the exact reviewed TASK-243 candidate is published.

## Immutable consumed generations 1-4

Generations 1-3 remain their existing consumed historical records. Generation 4 remains
`generation_4_diagnostic_executed=true`, `diagnostic_outcome=FAIL_CLOSED`,
`diagnostic_failure_reason=BOUNDED_CURRENT_PAGE_EVALUATION_FAILED`,
`diagnostic_process_exit_code=1`, `diagnostic_artifact_created=false`,
`generation_4_authorized_diagnostic_attempts=1`,
`generation_4_authorized_diagnostic_attempts_remaining=0`,
`generation_4_diagnostic_execution_owner=HUMAN_OPERATOR`, and
`live_dom_diagnostic_authority=NONE`. Because evaluation returned no payload,
`generation_4_root_probe_observed=false` and
`generation_4_commerce_probe_observed=false`. Generation 5 is not a retry or reinterpretation of
generation 4.

## Exact generation-5 authority

Only exact reviewed TASK-243 publication sets:

- `diagnostic_authorization_generation=5`
- `live_dom_diagnostic_authority=ONE_SHOT_ATTACH_ONLY_EXACT_LISTING`
- `generation_5_authorized_diagnostic_attempts=1`
- `generation_5_authorized_diagnostic_attempts_remaining=1`
- `generation_5_diagnostic_execution_owner=HUMAN_OPERATOR`
- `generation_5_diagnostic_executed=false`

The attempt is bound only to context `p8-pilot-001-led-motion-tiktok-vn`, source ID
`1731381331718341815`, and exact selected listing
`https://shop.tiktok.com/vn/pdp/den-led-cam-bien-chuyen-dong-3-che-do-sang-sac-usb-c/1731381331718341815`.
It grants no arbitrary, replacement, inferred-identity, search, batch, acquisition,
variant-switching, selector-repair, market-test, or commerce-action authority.

The only authorized carrier is `src/product_intelligence/tiktok_pdp_dom_diagnostic.py`, content-
equivalent to `generation_5_execution_source_sha`. The contract remains `schema_version=2`, exact
create-exclusive filename `tiktok-pdp-dom-diagnostic-v2.json`, and
`evidence_authority=NONE`. The canonical CLI subcommand is `tiktok-pdp-dom-diagnostic`. The
carrier borrows one session, performs exactly one `session.evaluate(DIAGNOSTIC_SCRIPT)`, performs
zero navigation, refresh, click, type, or scroll, and retains TASK-137 manager-mediated cleanup.

## Non-consuming preflight

Preflight is separate from invocation, must not invoke the diagnostic carrier, and does not
consume the attempt. It may only establish all of the following:

1. CDP `127.0.0.1:9222` is reachable.
2. Read-only browser target enumeration reports exactly one normal `type=page` target in total,
   and that sole target is the exact selected PDP for source ID `1731381331718341815`.
3. A fresh explicit external generation-5 job root contains neither
   `tiktok-pdp-dom-diagnostic-v1.json` nor `tiktok-pdp-dom-diagnostic-v2.json`.
4. `src/product_intelligence/tiktok_pdp_dom_diagnostic.py`,
   `src/product_intelligence/cli.py`, and `src/integrations/playwright/manager.py` are content-
   equivalent to the exact TASK-242 publication at
   `d113c4a7ce2e2835d532935bc195c922aa3628ca`.

Repository HEAD equality is not required. This target-unambiguity gate preserves TASK-137 as the
sole browser/CDP lifecycle and page-borrowing authority; it creates no second page-selection owner.

## One-line transport and consuming invocation

The Human-facing invocation must be entered as exactly one physical PowerShell line, with no
backtick or multiline continuation:

```powershell
python -m src.product_intelligence.cli tiktok-pdp-dom-diagnostic --job-root <fresh-external-generation-5-job-root> --cdp-endpoint http://127.0.0.1:9222
```

A shell or PowerShell parser/transport failure before a valid
`tiktok-pdp-dom-diagnostic` subcommand dispatches into the carrier is not a real diagnostic
invocation and does not by itself consume the attempt. Once valid carrier invocation begins, every
terminal outcome consumes the only generation-5 attempt: `SUCCESS`, `NO_BOUNDED_PDP_ROOT`,
`BLOCKED_OR_CHALLENGE`, `LOGIN_GATE`, `LISTING_UNAVAILABLE`, `IDENTITY_MISMATCH`,
`MALFORMED_DIAGNOSTIC_PAYLOAD`, evaluation/session failure, or any other terminal outcome. There
is no retry, refresh, resume, second invocation, or replacement target.

`SUCCESS` may create the bounded V2 artifact. `NO_BOUNDED_PDP_ROOT` retains the create-exclusive
V2 `FAIL_CLOSED` artifact contract. Other safe failures may remain artifact-free under the
published carrier. Every artifact retains `evidence_authority=NONE`.

## Interpretation and handoff

`root_probe` and `commerce_probe` remain engineering diagnostic hints only.
`bounded_scan_truncated=true` makes negative bounded-scan observations non-exhaustive. Shadow and
iframe counts are structural hints only and authorize no traversal.
`document_ready_state=COMPLETE` is not proof of SPA hydration or network completion. Selector and
readiness hints do not self-authorize repair.

`root_observability_hardening_implemented=true` and
`commerce_observability_hardening_implemented=true` remain true.
`selector_repair_complete=false`, `live_public_pdp_acquisition_authority=NONE`,
`automated_public_pdp_acquisition_authority=NONE`, `market_test_or_action_authority=NONE`, and
`automatic_progression=false`. `active_track.next_milestone` remains null and pending commitments
remain empty.

The exact current global handoff is
`HUMAN_OPERATOR_GENERATION_5_COMMERCE_OBSERVABILITY_DIAGNOSTIC_EXECUTION`. After the single
Human-operated attempt terminates, authority returns to
`HUMAN_BRAIN_GENERATION_5_DIAGNOSTIC_REVIEW`. TASK-243 selects no engineering repair or automatic
successor. `CAPABILITY_IS_NOT_AUTHORITY`, `EVIDENCE_IS_NOT_PRODUCT_TRUTH`,
`SOURCE_IDENTITY_IS_NOT_CANONICAL_IDENTITY`, `SNAPSHOT_IS_NOT_TREND`, and
`ONE_CAPABILITY_ONE_AUTHORITY` remain mandatory.
