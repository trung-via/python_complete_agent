# Phase 8 Public TikTok PDP DOM Diagnostic Generation-4 Authorization

## Decision and exact publication lineage

TASK-241 is classified exactly as
`FRESH_GENERATION_4_COMMERCE_OBSERVABILITY_DIAGNOSTIC_AUTHORIZATION_ONLY`. It records
`source_task_id=TASK-240`, `source_run_id=RUN-240-002`,
`source_review_id=REVIEW-240-001`, and
`source_published_sha=8ef61df3936652fb7aeda8ca31ce1db3621ff4cf`. The exact published V2
implementation is separately bound as
`diagnostic_v2_implementation_source_sha=8ef61df3936652fb7aeda8ca31ce1db3621ff4cf`.
TASK-240's completed historical record is backfilled with
`published_source_sha=8ef61df3936652fb7aeda8ca31ce1db3621ff4cf`; its older
`diagnostic_implementation_source_sha=fbdb8851b9f27d24eff11c509db3009e2c614952`
retains its original provenance meaning.

This authorization changes no diagnostic, CLI, browser, collector, parser, Product Intelligence,
evidence, ranking, approval, test, or action implementation. It authorizes exactly one fresh
Human-operated generation-4 diagnostic attempt after exact reviewed TASK-241 publication.

## Preserved consumed history

Generations 1, 2, and 3 remain consumed historical records. Generation 3 is not retried or
reopened: `generation_3_diagnostic_executed=true`, `diagnostic_outcome=FAIL_CLOSED`,
`diagnostic_failure_reason=NO_BOUNDED_PDP_ROOT`, `diagnostic_artifact_created=true`,
`generation_3_authorized_diagnostic_attempts=1`,
`generation_3_authorized_diagnostic_attempts_remaining=0`,
`generation_3_diagnostic_execution_owner=HUMAN_OPERATOR`, and its historical
`live_dom_diagnostic_authority=NONE`.

The immutable generation-3 V1 artifact remains engineering diagnostic context only:

- `schema_version=1`
- `filename=tiktok-pdp-dom-diagnostic-v1.json`
- `sha256=4CE631661F897F16133EFEAA3CC1CA03C5E468CC56F1F7D46B7F2FF53EBDF00E`
- `size_bytes=755`
- `observed_at=2026-09-22T05:59:34.977481+00:00`
- `evidence_authority=NONE`

Its exact historical `root_probe` remains: `title_anchor_count=1`,
`price_anchor_count=0`, `action_anchor_count=0`,
`visible_explicit_pdp_root_count=0`, `explicit_root_with_commerce_anchors_count=0`,
`main_present=false`, `main_visible=false`, `main_has_commerce_anchors=false`,
`multi_anchor_common_ancestor_found=false`, and `selected_root_kind=NONE`.

## Exact generation-4 boundary

Only exact reviewed TASK-241 publication sets:

- `diagnostic_authorization_generation=4`
- `live_dom_diagnostic_authority=ONE_SHOT_ATTACH_ONLY_EXACT_LISTING`
- `generation_4_authorized_diagnostic_attempts=1`
- `generation_4_authorized_diagnostic_attempts_remaining=1`
- `generation_4_diagnostic_execution_owner=HUMAN_OPERATOR`
- `generation_4_diagnostic_executed=false`

The attempt is bound only to context `p8-pilot-001-led-motion-tiktok-vn`, source ID
`1731381331718341815`, and exact listing
`https://shop.tiktok.com/vn/pdp/den-led-cam-bien-chuyen-dong-3-che-do-sang-sac-usb-c/1731381331718341815`.
It grants no replacement product, arbitrary target, search, batch, inferred identity,
variant-switching, acquisition, selector-repair, market-test, or commerce-action authority.

The only authorized carrier is `src/product_intelligence/tiktok_pdp_dom_diagnostic.py` as
published at `8ef61df3936652fb7aeda8ca31ce1db3621ff4cf`, with `schema_version=2`, exact
create-exclusive filename `tiktok-pdp-dom-diagnostic-v2.json`, and
`evidence_authority=NONE`. The canonical CLI command is `tiktok-pdp-dom-diagnostic`, supplied
one new explicit external generation-4 job root and CDP endpoint `http://127.0.0.1:9222`.
The carrier borrows exactly one session, performs exactly one
`session.evaluate(DIAGNOSTIC_SCRIPT)`, performs zero navigation, refresh, click, type, or scroll,
and uses TASK-137 manager-mediated borrowed-session cleanup. TASK-231 remains the sole public PDP
acquisition contract.

## Non-consuming preflight

Preflight is separate from invocation and does not consume the attempt. It is limited to:

1. Verify CDP `127.0.0.1:9222` is reachable without invoking the diagnostic carrier.
2. Use read-only browser target listing to verify that the exact selected PDP is already open.
3. Verify that a new explicit external generation-4 job root contains neither
   `tiktok-pdp-dom-diagnostic-v1.json` nor `tiktok-pdp-dom-diagnostic-v2.json`.
4. Verify file-content equivalence of
   `src/product_intelligence/tiktok_pdp_dom_diagnostic.py`,
   `src/product_intelligence/cli.py`, and `src/integrations/playwright/manager.py` to those exact
   files at published V2 source `8ef61df3936652fb7aeda8ca31ce1db3621ff4cf`.

No post-TASK-241 repository HEAD equality is required. The integrity gate compares the three
execution-critical file contents to the published V2 source; a later governance-only HEAD is
expected to differ.

## Consuming invocation and terminal outcomes

Starting the canonical CLI invocation consumes the sole generation-4 attempt. This is true for
`SUCCESS`, `NO_BOUNDED_PDP_ROOT`, `BLOCKED_OR_CHALLENGE`, `LOGIN_GATE`,
`LISTING_UNAVAILABLE`, `IDENTITY_MISMATCH`, `MALFORMED_DIAGNOSTIC_PAYLOAD`, evaluation or
session failure, and every other terminal outcome. TASK-241 grants zero retry, refresh, resume,
second invocation, replacement target, or automatic progression.

`SUCCESS` may create the bounded V2 artifact. `NO_BOUNDED_PDP_ROOT` preserves V2
create-exclusive `FAIL_CLOSED` artifact semantics and returns nonzero. Other safe failures remain
artifact-free under the published V2 carrier. Every artifact retains `evidence_authority=NONE`.

## Post-run interpretation boundaries

Human/Brain review is mandatory after the invocation and cannot decide or self-authorize repair:

- `price_anchor_count=0` with `visible_currency_like_count>0` supports only a
  selector-family-mismatch hypothesis.
- `action_anchor_count=0` with `visible_interactive_count>0` supports only an
  action-selector-family-mismatch hypothesis.
- `bounded_scan_truncated=true` makes negative bounded-scan observations non-exhaustive.
- `open_shadow_root_count>0` or `visible_iframe_count>0` is a structural hint only and does not
  authorize traversal.
- `document_ready_state=COMPLETE` is not proof of SPA hydration or network completion.

`root_probe` and `commerce_probe` are engineering diagnostic hints only. They are not marketplace
evidence, Product Truth, ranking evidence, approval evidence, trend evidence, test-readiness
evidence, or commerce-action evidence. Readiness, selector, iframe, and shadow hints grant no
repair authority.

## Publication-gated state

`root_observability_hardening_implemented=true` and
`commerce_observability_hardening_implemented=true` remain true.
`selector_repair_complete=false`, `live_public_pdp_acquisition_authority=NONE`,
`automated_public_pdp_acquisition_authority=NONE`, `market_test_or_action_authority=NONE`,
`automatic_progression=false`, `next_milestone=null`, and pending commitments are empty.

The exact handoff is
`HUMAN_OPERATOR_GENERATION_4_COMMERCE_OBSERVABILITY_DIAGNOSTIC_EXECUTION`. TASK-241 selects no
post-run engineering successor. `CAPABILITY_IS_NOT_AUTHORITY`,
`EVIDENCE_IS_NOT_PRODUCT_TRUTH`, `SOURCE_IDENTITY_IS_NOT_CANONICAL_IDENTITY`,
`SNAPSHOT_IS_NOT_TREND`, and `ONE_CAPABILITY_ONE_AUTHORITY` remain mandatory.
