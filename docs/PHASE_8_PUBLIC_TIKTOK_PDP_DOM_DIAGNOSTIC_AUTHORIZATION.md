# Phase 8 Public TikTok PDP DOM Diagnostic Authorization

Status: publication-gated TASK-235 Human/Brain authorization only  
Classification: `ONE_SHOT_ATTACH_ONLY_PUBLIC_PDP_DOM_DIAGNOSTIC_AUTHORIZATION_ONLY`

## Human approval and exact target

The Human/Brain authorizes exactly one diagnostic attempt, executable only after exact reviewed
TASK-235 publication, for context `p8-pilot-001-led-motion-tiktok-vn`, source ID
`1731381331718341815`, and this fixed selected listing:

`https://shop.tiktok.com/vn/pdp/den-led-cam-bien-chuyen-dong-3-che-do-sang-sac-usb-c/1731381331718341815`

The authorized carrier is the exact TASK-234 implementation at source
`2859813fd58e63f5434d44f9e76eba78d8a9c41f`:
`src/product_intelligence/tiktok_pdp_dom_diagnostic.py`. This record grants no arbitrary URL,
source, query, product, batch, recurring, retry, refresh, resume, alternate-page, second-capture,
or second-attempt scope. TASK-233 remains consumed with
`authorized_capture_attempts_remaining=0`; this authorization does not reopen public-PDP capture
authority.

## Human-operated attach-only execution

Execution owner is `HUMAN_OPERATOR`. Before invocation, the operator-owned Chrome 9222 session and
page must already be open on the exact selected PDP. The invocation requires an explicit external
`--job-root` and the operator-owned `--cdp-endpoint`; neither input grants browser lifecycle or
navigation authority.

The carrier may attach to the existing page and perform its single bounded evaluation. It has zero
authority to navigate, refresh, click, type, scroll, search, change a variant, open another page,
or otherwise interact. Exact current-page identity is mandatory. Login, challenge, CAPTCHA,
unavailable, unrelated, malformed, unverifiable, or different-product state fails closed before a
diagnostic artifact is created. A failed operation consumes the one attempt. Human resolution of a
gate does not authorize another invocation; every later attempt requires fresh Human/Brain
authorization.

TASK-137 remains the sole browser/CDP lifecycle authority. The Human operator owns Chrome, its
session, context, page, login state, and the decision to invoke. TASK-235 is an authorization
record, not execution: it performs no TikTok/CDP operation and does not claim that the diagnostic
has run.

## External diagnostic artifact boundary

The fixed output remains external structural diagnostic output with `evidence_authority=NONE`.
It is not `ProductCandidateSnapshot`, `SignalEvidence`, canonical evidence, Product Truth, ranking,
recommendation, approval, trend, test readiness, market-test evidence, or commerce-action evidence.
It cannot mutate or satisfy any of those semantics. TASK-231 remains the only public-PDP
acquisition contract; `ProductCandidateSnapshot` remains the marketplace observation contract and
`SignalEvidence` remains the field-evidence owner.

`CAPABILITY_IS_NOT_AUTHORITY`, `EVIDENCE_IS_NOT_PRODUCT_TRUTH`,
`SOURCE_IDENTITY_IS_NOT_CANONICAL_IDENTITY`, `SNAPSHOT_IS_NOT_TREND`, and
`ONE_CAPABILITY_ONE_AUTHORITY` remain mandatory. The external artifact may inform a later Human/
Brain decision about selector repair only after review; it cannot itself authorize or implement
that repair.

## Publication gate and mandatory handoff

On exact reviewed TASK-235 publication:

- `live_dom_diagnostic_authority=ONE_SHOT_ATTACH_ONLY_EXACT_LISTING`;
- `authorized_diagnostic_attempts=1` and `authorized_diagnostic_attempts_remaining=1`;
- `diagnostic_execution_owner=HUMAN_OPERATOR`;
- `diagnostic_implementation_exists=true`, `diagnostic_executed=false`, and
  `selector_repair_complete=false`;
- `live_public_pdp_acquisition_authority=NONE`,
  `automated_public_pdp_acquisition_authority=NONE`, and
  `market_test_or_action_authority=NONE`;
- `automatic_progression=false`, `next_milestone=null`, and pending commitments are empty.

The exact handoff is `HUMAN_OPERATOR_ONE_SHOT_PUBLIC_PDP_DOM_DIAGNOSTIC_EXECUTION`. After the one
attempt, success or failure, mandatory Human/Brain review is required. No extractor repair,
successor, acquisition, retry, test, or action follows automatically.

## Historical execution reconciliation

The one attempt was subsequently invoked and failed closed with the legacy combined message
`the current page is not an available public PDP`; it created no artifact. TASK-236 records the
attempt as consumed with `diagnostic_executed=true`, `diagnostic_outcome=FAIL_CLOSED`,
`authorized_diagnostic_attempts_remaining=0`, and `live_dom_diagnostic_authority=NONE`. Because
this TASK-235 carrier combined multiple admission gates, the historical cause is only
`LEGACY_COMBINED_PUBLIC_PDP_AVAILABILITY_GATE`. Human screenshot context is
`NON_CANONICAL_DIAGNOSTIC_CONTEXT` and proves neither the internal gate nor marketplace evidence.
See `docs/PHASE_8_PUBLIC_TIKTOK_PDP_DOM_DIAGNOSTIC_REVIEW_AND_HARDENING.md`. A later attempt requires
the exact fresh handoff `HUMAN_BRAIN_FRESH_ONE_SHOT_PUBLIC_PDP_DOM_DIAGNOSTIC_AUTHORIZATION`.
