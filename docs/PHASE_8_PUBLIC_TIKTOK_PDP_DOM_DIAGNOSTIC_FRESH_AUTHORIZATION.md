# Phase 8 Public TikTok PDP DOM Diagnostic Fresh Authorization

Status: publication-gated TASK-237 Human/Brain authorization only  
Classification: `FRESH_ONE_SHOT_ATTACH_ONLY_PUBLIC_PDP_DOM_DIAGNOSTIC_AUTHORIZATION_ONLY`

## Human approval and generation-2 exact target

The Human/Brain authorizes exactly one fresh generation-2 diagnostic attempt, executable only
after exact reviewed TASK-237 publication, for context `p8-pilot-001-led-motion-tiktok-vn`, source ID
`1731381331718341815`, and this fixed selected listing:

`https://shop.tiktok.com/vn/pdp/den-led-cam-bien-chuyen-dong-3-che-do-sang-sac-usb-c/1731381331718341815`

The authorized carrier is the exact TASK-236 hardened carrier at source
`a53510ff353cdf926a76f1dc84363b7835c5cb4d`:
`src/product_intelligence/tiktok_pdp_dom_diagnostic.py`. This fresh authorization grants no arbitrary
URL, source ID, search query, second product, batch, recurring scope, automatic retry, refresh,
resume, alternate-page, second-capture, or multi-attempt authority. TASK-233 remains consumed with
`authorized_capture_attempts_remaining=0`; this authorization does not reopen public-PDP capture
authority.

## Human-operated attach-only execution and safe failure boundary

Execution owner is `HUMAN_OPERATOR`. Chrome/CDP (port 9222) and the exact selected PDP page must
already be open under Human control before invocation. The invocation requires a new explicit
external `--job-root` distinct from prior operation roots and the operator-owned `--cdp-endpoint`;
neither input grants browser lifecycle or navigation authority.

The hardened carrier attaches to the existing page and performs its single bounded evaluation.
It retains zero navigation or interaction authority: no navigate, refresh, click, type, scroll,
search, change variants, or open another page. Exact current-page identity is mandatory and
validated through the canonical TikTok parser.

Page-state evaluation fails closed at the Python error boundary with stable safe reason codes:
`BLOCKED_OR_CHALLENGE`, `LOGIN_GATE`, `LISTING_UNAVAILABLE`, `NO_BOUNDED_PDP_ROOT`,
`IDENTITY_MISMATCH`, or `MALFORMED_DIAGNOSTIC_PAYLOAD`. Incidental descendant/variant text (e.g.
an individual sold-out option) does not trigger `LISTING_UNAVAILABLE`. Errors never expose the CDP
endpoint, secrets, or raw page content.

A failed fresh attempt consumes the single generation-2 authorization. Any later invocation, after
either success or failure, requires another fresh Human/Brain authorization. TASK-137 remains the
sole browser/CDP lifecycle authority. TASK-237 is an authorization record, not execution: it
performs no TikTok/CDP operation and does not claim that the diagnostic has run.

## External structural diagnostic output boundary

The fixed output remains external structural diagnostic hints with `evidence_authority=NONE`.
It is not `ProductCandidateSnapshot`, `SignalEvidence`, canonical evidence, Product Truth, ranking,
recommendation, approval, trend, test readiness, market-test evidence, or commerce-action evidence.
It cannot mutate or satisfy any of those semantics. TASK-231 remains the sole public-PDP
acquisition contract; `ProductCandidateSnapshot` remains the marketplace observation contract and
`SignalEvidence` remains the field-evidence owner.

`CAPABILITY_IS_NOT_AUTHORITY`, `EVIDENCE_IS_NOT_PRODUCT_TRUTH`,
`SOURCE_IDENTITY_IS_NOT_CANONICAL_IDENTITY`, `SNAPSHOT_IS_NOT_TREND`, and
`ONE_CAPABILITY_ONE_AUTHORITY` remain mandatory. Diagnostic structural output may inform a later
Human/Brain decision about selector repair only after review; it cannot itself authorize or
implement that repair.

## Preserved generation-1 consumed history

Historical generation 1 remains intact and separately represented from this fresh generation-2
authorization:
- TASK-235 attempt executed: `true`;
- Generation-1 outcome: `FAIL_CLOSED`;
- Generation-1 artifact created: `false`;
- Generation-1 authorized diagnostic attempts: `1`;
- Generation-1 diagnostic attempts remaining: `0`;
- Historical failure reason: `LEGACY_COMBINED_PUBLIC_PDP_AVAILABILITY_GATE`.

The Human screenshot context remains `NON_CANONICAL_DIAGNOSTIC_CONTEXT` and proves neither the
internal gate nor canonical marketplace evidence. Hardening implemented in TASK-236
(`diagnostic_hardening_implemented=true`) remains intact. Generation 2 does not erase, reset, or
rewrite the fact that generation 1 was already executed and consumed.

## Publication gate and mandatory execution handoff

On exact reviewed TASK-237 publication:

- `live_dom_diagnostic_authority=ONE_SHOT_ATTACH_ONLY_EXACT_LISTING`;
- `diagnostic_authorization_generation=2`;
- `fresh_authorized_diagnostic_attempts=1`;
- `fresh_authorized_diagnostic_attempts_remaining=1`;
- `fresh_diagnostic_execution_owner=HUMAN_OPERATOR`;
- `fresh_diagnostic_executed=false`;
- `diagnostic_hardening_implemented=true`;
- `selector_repair_complete=false`;
- `live_public_pdp_acquisition_authority=NONE`;
- `automated_public_pdp_acquisition_authority=NONE`;
- `market_test_or_action_authority=NONE`;
- `automatic_progression=false`;
- `next_milestone=null`;
- `pending_commitments` are empty.

The exact execution handoff is `HUMAN_OPERATOR_FRESH_ONE_SHOT_PUBLIC_PDP_DOM_DIAGNOSTIC_EXECUTION`.
After the single fresh attempt (success or failure), mandatory Human/Brain review is required.
No collector selector repair, successor task, acquisition, retry, test, or commerce action follows
automatically.
