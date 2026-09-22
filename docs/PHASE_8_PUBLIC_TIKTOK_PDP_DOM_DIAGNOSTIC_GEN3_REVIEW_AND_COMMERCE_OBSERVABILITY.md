# Phase 8 Public TikTok PDP DOM Diagnostic Generation-3 Review and Commerce Observability

## Decision

TASK-240 is classified exactly as
`GENERATION_3_FAIL_CLOSED_RECONCILIATION_AND_BOUNDED_COMMERCE_OBSERVABILITY_HARDENING_ONLY`.
It reconciles the single Human-operated generation-3 invocation authorized by TASK-239 and
hardens only the attach-only engineering diagnostic. It creates no live invocation, selector
repair, acquisition, ranking, recommendation, approval, test, or commerce-action authority.

## Exact authorization and implementation provenance

The consumed authorization was published as `source_task_id=TASK-239`,
`source_run_id=RUN-239-001`, `source_review_id=REVIEW-239-001`, and
`authorization_published_source_sha=ca2407396931eb03be7f104a25760db4813ab5a1`.
TASK-239's completed historical record is backfilled with
`published_source_sha=ca2407396931eb03be7f104a25760db4813ab5a1`. The diagnostic implementation it
authorized remains exactly `diagnostic_implementation_source_sha=fbdb8851b9f27d24eff11c509db3009e2c614952`.
Older `source_sha` fields retain their historical meanings.

## Consumed generation-3 outcome

Generation 3 is `diagnostic_executed=true`, `diagnostic_outcome=FAIL_CLOSED`,
`diagnostic_failure_reason=NO_BOUNDED_PDP_ROOT`, `diagnostic_artifact_created=true`,
`authorized_diagnostic_attempts=1`, `authorized_diagnostic_attempts_remaining=0`, and
`execution_owner=HUMAN_OPERATOR`. `live_dom_diagnostic_authority=NONE`. Generation-1 and
generation-2 records remain separate and unchanged.

The immutable external V1 artifact is recorded by non-path provenance only:

- `schema_version=1`
- `filename=tiktok-pdp-dom-diagnostic-v1.json`
- `sha256=4CE631661F897F16133EFEAA3CC1CA03C5E468CC56F1F7D46B7F2FF53EBDF00E`
- `size_bytes=755`
- `observed_at=2026-09-22T05:59:34.977481+00:00`
- `evidence_authority=NONE`

No operator-local absolute path is retained. V1 is immutable history: it is not overwritten,
migrated, reinterpreted, or silently treated as V2.

Its exact engineering-only `root_probe` is:

```yaml
title_anchor_count: 1
price_anchor_count: 0
action_anchor_count: 0
visible_explicit_pdp_root_count: 0
explicit_root_with_commerce_anchors_count: 0
main_present: false
main_visible: false
main_has_commerce_anchors: false
multi_anchor_common_ancestor_found: false
selected_root_kind: NONE
```

This probe, Human screenshots, and terminal output are `NON_CANONICAL_DIAGNOSTIC_CONTEXT`.
They cannot mutate or satisfy `ProductCandidateSnapshot`, `SignalEvidence`, Product Truth,
ranking, approval, trend, test-readiness, or action semantics.

## Active V2 contract

The future separately authorized carrier contract is `schema_version=2` with create-exclusive
external filename `tiktok-pdp-dom-diagnostic-v2.json`. It preserves the fixed source identity,
current-page URL binding, safe challenge/login/unavailable gates, exactly one
`session.evaluate(DIAGNOSTIC_SCRIPT)`, zero navigation or interaction, and TASK-137
manager-mediated borrowed-session cleanup.

V2 preserves V1 `root_probe` semantics and adds exactly one validated `commerce_probe`. Its
required scalar fields are `document_ready_state`, `bounded_nodes_scanned`,
`bounded_scan_truncated`, `visible_currency_like_count`, `near_title_currency_like_count`,
`visible_interactive_count`, `near_title_action_like_count`, `visible_loading_marker_count`,
`open_shadow_root_count`, and `visible_iframe_count`. Readiness is one of `LOADING`,
`INTERACTIVE`, `COMPLETE`, or `UNKNOWN`; `COMPLETE` does not prove SPA hydration, commerce
rendering, or network completion.

Traversal is a light-DOM element TreeWalker capped at 600 visited nodes. Reaching the cap while
more nodes remain sets `bounded_scan_truncated=true`. Every count is capped at 600. The carrier
does not enter iframe documents or shadow-root contents; it reports only aggregate visible-iframe
and open-shadow-root boundary hints.

The probe carries one nullable bounded `title_anchor_signature`, at most six
`title_ancestor_signatures`, at most three `currency_candidates`, and at most five
`action_candidates`. Structural signatures contain only `tag_name`, at most four capped
`class_tokens`, capped `data-testid`, `data-e2e`, `role`, `itemprop`, `parent_signature`, and
`grandparent_signature`. Candidate objects contain exactly `candidate_kind`, enum
`match_basis`, enum `semantic_hint`, those bounded structural fields, enum `relation_to_title`,
and boolean `fixed_or_sticky`.

Currency matching may inspect clipped local text and semantic price attributes in memory, but
persists only a match-basis enum. Action matching may inspect clipped local text/attributes in
memory, but persists only `BUY_LIKE`, `CART_LIKE`, `VARIANT_LIKE`, `QUANTITY_LIKE`, or `OTHER`.
Title relation is restricted to `TITLE_NODE`, `TITLE_NEIGHBORHOOD_LEVEL_1` through
`TITLE_NEIGHBORHOOD_LEVEL_6`, or `OUTSIDE_TITLE_NEIGHBORHOOD`.

V2 persists no actual currency/price value, product title, button/link text, raw `aria-label`,
`href`, element id, raw HTML, arbitrary page text, cookies, storage, headers, credentials,
tokens, screenshots, request/response bodies, or user-profile data. Generated or hashed class
tokens remain hints and are insufficient alone for production selector repair.

For `NO_BOUNDED_PDP_ROOT` after identity and safe gates, V2 creates exactly one external
FAIL_CLOSED artifact containing only schema version, bounded metadata, `root_probe`, and
validated `commerce_probe`, then preserves the nonzero result. Other safe failures create no
artifact. Successful output contains the same probes and no marketplace scalar values.

## Publication-gated state

Only exact reviewed TASK-240 publication makes
`commerce_observability_hardening_implemented=true`; `root_observability_hardening_implemented`
remains true. `selector_repair_complete=false`, `live_public_pdp_acquisition_authority=NONE`,
`automated_public_pdp_acquisition_authority=NONE`, `market_test_or_action_authority=NONE`,
`automatic_progression=false`, `next_milestone=null`, and pending commitments are empty.

The exact handoff is
`HUMAN_BRAIN_FRESH_COMMERCE_OBSERVABILITY_DIAGNOSTIC_AUTHORIZATION`. TASK-240 does not authorize
generation 4 or any live marketplace operation. `CAPABILITY_IS_NOT_AUTHORITY`,
`EVIDENCE_IS_NOT_PRODUCT_TRUTH`, `SOURCE_IDENTITY_IS_NOT_CANONICAL_IDENTITY`,
`SNAPSHOT_IS_NOT_TREND`, and `ONE_CAPABILITY_ONE_AUTHORITY` remain mandatory.
