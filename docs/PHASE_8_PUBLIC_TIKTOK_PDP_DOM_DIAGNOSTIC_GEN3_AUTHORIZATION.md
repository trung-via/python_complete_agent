# Phase 8 Public TikTok PDP DOM Diagnostic Generation-3 Authorization

Status: publication-gated TASK-239 authorization  
Classification: `FRESH_GENERATION_3_ROOT_OBSERVABILITY_DIAGNOSTIC_AUTHORIZATION_ONLY`

## Exact published implementation provenance

TASK-239 authorizes use of the already reviewed and published TASK-238 diagnostic implementation without
changing it. The unambiguous publication provenance is:

- `source_task_id=TASK-238`;
- `source_run_id=RUN-238-002`;
- `source_review_id=REVIEW-238-001`;
- `diagnostic_implementation_source_sha=fbdb8851b9f27d24eff11c509db3009e2c614952`;
- `published_source_sha=fbdb8851b9f27d24eff11c509db3009e2c614952`.

These fields do not reinterpret any older `source_sha` field. TASK-239 makes no change to
`src/product_intelligence/tiktok_pdp_dom_diagnostic.py` or its product-intelligence tests. The published
carrier already implements one attach, exactly one `session.evaluate(DIAGNOSTIC_SCRIPT)`, exact-current-page
identity validation, safe challenge/login/unavailable gates, bounded `root_probe` output, zero navigation or
interaction, and TASK-137 manager-mediated borrowed-session cleanup.

## Preserved consumed histories

Generation 1 remains historical and unchanged: TASK-235/TASK-236 executed once, ended `FAIL_CLOSED`, created
no artifact, and has one authorized attempt with zero remaining. Its historical failure reason remains
`LEGACY_COMBINED_PUBLIC_PDP_AVAILABILITY_GATE`.

Generation 2 also remains historical and consumed: TASK-237 executed once under Human operator ownership,
ended `FAIL_CLOSED` with `NO_BOUNDED_PDP_ROOT`, created no artifact, and has one authorized attempt with zero
remaining. TASK-239 does not retry, resume, repair, or otherwise reopen either history.

## Generation-3 authorization

Only on exact reviewed TASK-239 publication, the state grants:

- `diagnostic_authorization_generation=3`;
- `live_dom_diagnostic_authority=ONE_SHOT_ATTACH_ONLY_EXACT_LISTING`;
- `generation_3_authorized_diagnostic_attempts=1`;
- `generation_3_authorized_diagnostic_attempts_remaining=1`;
- `generation_3_diagnostic_execution_owner=HUMAN_OPERATOR`;
- `generation_3_diagnostic_executed=false`.

The authorization is bound only to context `p8-pilot-001-led-motion-tiktok-vn`, source ID
`1731381331718341815`, and the fixed selected listing:

`https://shop.tiktok.com/vn/pdp/den-led-cam-bien-chuyen-dong-3-che-do-sang-sac-usb-c/1731381331718341815`

It grants no arbitrary-target, batch, search, replacement-product, inferred-identity, retry, acquisition,
selector-repair, ranking, test, recommendation, approval, or commerce-action authority.

## Preflight and consuming invocation

Non-consuming preflight is limited to establishing that Chrome/CDP 9222 is reachable, that the exact selected
PDP is the currently open intended page, and that a new explicit external generation-3 job root does not
already contain the fixed artifact. Preflight must not invoke the diagnostic carrier.

Starting the canonical diagnostic CLI invocation consumes the single generation-3 attempt, whether it ends in
`SUCCESS` or `FAIL`. There is no automatic retry, refresh, resume, second invocation, or replacement target.
The invocation uses only the published TASK-238 carrier: one attach, exactly one evaluate, zero navigation or
interaction, exact-current-page identity validation, safe gates, bounded root observability, and TASK-137
manager-mediated cleanup.

`SUCCESS` may create the existing bounded diagnostic artifact. `NO_BOUNDED_PDP_ROOT` may create the existing
safe create-exclusive `FAIL_CLOSED` root-probe artifact and must still return nonzero. `BLOCKED_OR_CHALLENGE`,
`LOGIN_GATE`, `LISTING_UNAVAILABLE`, `IDENTITY_MISMATCH`, and `MALFORMED_DIAGNOSTIC_PAYLOAD` remain fail-closed
and create no failure artifact.

Every artifact retains `evidence_authority=NONE`. A `root_probe` is engineering diagnostic input only for
later Human/Brain judgment. It is not `ProductCandidateSnapshot`, `SignalEvidence`, marketplace evidence,
Product Truth, ranking, recommendation, approval, trend, test-readiness evidence, or commerce-action evidence.
The laws `CAPABILITY_IS_NOT_AUTHORITY`, `EVIDENCE_IS_NOT_PRODUCT_TRUTH`,
`SOURCE_IDENTITY_IS_NOT_CANONICAL_IDENTITY`, `SNAPSHOT_IS_NOT_TREND`, and
`ONE_CAPABILITY_ONE_AUTHORITY` remain mandatory.

## Publication gate and handoff

On exact reviewed TASK-239 publication, `root_observability_hardening_implemented=true`,
`selector_repair_complete=false`, `live_public_pdp_acquisition_authority=NONE`,
`automated_public_pdp_acquisition_authority=NONE`, `market_test_or_action_authority=NONE`,
`automatic_progression=false`, `next_milestone=null`, and pending commitments remain empty.

The exact handoff is `HUMAN_OPERATOR_GENERATION_3_ROOT_OBSERVABILITY_DIAGNOSTIC_EXECUTION`. After the one live
invocation, regardless of outcome, further engineering action requires Human/Brain review of the actual safe
terminal/artifact result and a separate canonical successor decision. TASK-239 selects no successor and
authorizes no automatic progression.
