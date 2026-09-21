# Phase 8 Public TikTok PDP DOM Diagnostic Review and Hardening

Status: publication-gated TASK-236 reconciliation and offline hardening  
Classification: `FAILED_LIVE_DOM_DIAGNOSTIC_RECONCILIATION_AND_BOUNDED_ADMISSION_HARDENING_ONLY`

## Consumed TASK-235 attempt

TASK-235 was published from exact source `eedad88f5c676c647d418da62e554529ea29b161`.
The Human invoked its one authorized attach-only diagnostic attempt exactly once for source ID
`1731381331718341815`. The carrier returned `TikTokPdpDomDiagnosticError` with the exact legacy
message `the current page is not an available public PDP`. No diagnostic artifact was created.

The TASK-235 contract makes either success or failure consume the attempt. The reconciled state is
therefore `diagnostic_executed=true`, `diagnostic_outcome=FAIL_CLOSED`,
`diagnostic_artifact_created=false`, `authorized_diagnostic_attempts=1`,
`authorized_diagnostic_attempts_remaining=0`, and `live_dom_diagnostic_authority=NONE`.
The historical reason is recorded only as `LEGACY_COMBINED_PUBLIC_PDP_AVAILABILITY_GATE`: the old
carrier combined blocked/challenge, login, listing-unavailable, and missing-root gates and cannot
establish which gate fired after the fact.

The Human screenshot is `NON_CANONICAL_DIAGNOSTIC_CONTEXT` only. It showed the exact selected PDP
apparently rendered with ordinary product content and no visually apparent login, CAPTCHA, or
challenge wall. It does not prove the internal failure reason and is not marketplace evidence,
`SignalEvidence`, `ProductCandidateSnapshot`, or Product Truth. No screenshot-visible marketplace
value is admitted or persisted.

TASK-233 capture history is unchanged: `authorized_capture_attempts_remaining=0` and
`live_public_pdp_acquisition_authority=NONE`. The consumed diagnostic does not reopen capture,
acquisition, evidence, ranking, approval, test, recommendation, or action authority.

## Bounded offline hardening

The diagnostic still performs exactly one current-page evaluation, with zero navigation or
interaction. Exact current-URL identity remains mandatory and is revalidated through the canonical
TikTok parser for the fixed source ID. Explicit PDP roots are preferred, followed by a suitable
`main`. If neither is suitable, the script examines capped sets of independent visible
title/heading, current-price, and purchase-action/quantity/variant anchors, walks capped ancestor
chains, and chooses their nearest bounded common ancestor deterministically. `body` is only a
capped discovery boundary after exact URL binding; neither `body` nor `html` can be the output
root. Full body text/HTML and broad page material are never returned or persisted.

Challenge and login checks remain direct, bounded, and page-level. Whole-listing unavailability
now requires an explicit page/listing-level marker or title state; incidental descendant text such
as a sold-out variant does not classify the listing as unavailable. The Python error boundary emits
only stable safe reasons: `BLOCKED_OR_CHALLENGE`, `LOGIN_GATE`, `LISTING_UNAVAILABLE`,
`NO_BOUNDED_PDP_ROOT`, `IDENTITY_MISMATCH`, or `MALFORMED_DIAGNOSTIC_PAYLOAD`. Errors never include
the CDP endpoint, secrets, or raw page material.

Existing candidate caps, deterministic ordering, bounded excerpts and attributes, create-exclusive
external artifact behavior, secret exclusion, and `manager.close_session` borrowed-session cleanup
remain unchanged. A success is structural selector hints only with `evidence_authority=NONE`.
TASK-236 does not change collector selectors, perform a second capture, or create Product
Intelligence evidence, truth, ranking, approval, test, or action authority.

## Publication gate and handoff

On exact reviewed TASK-236 publication, diagnostic hardening is implemented but no live attempt is
authorized: `diagnostic_hardening_implemented=true`, `selector_repair_complete=false`,
`live_dom_diagnostic_authority=NONE`, `automated_public_pdp_acquisition_authority=NONE`,
`live_public_pdp_acquisition_authority=NONE`, and `market_test_or_action_authority=NONE`.
`automatic_progression=false`, `next_milestone=null`, and pending commitments are empty.

Control returns exactly to `HUMAN_BRAIN_FRESH_ONE_SHOT_PUBLIC_PDP_DOM_DIAGNOSTIC_AUTHORIZATION`.
Any later live invocation requires a fresh Human/Brain authorization. There is no automatic retry,
selector repair, successor task, acquisition, test, or action.
