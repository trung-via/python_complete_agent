# Phase 8 Public TikTok PDP DOM Diagnostic Gen2 Review and Root Observability

Status: publication-gated TASK-238 reconciliation and offline root-observability hardening  
Classification: `GENERATION_2_FAIL_CLOSED_RECONCILIATION_AND_BOUNDED_ROOT_OBSERVABILITY_HARDENING_ONLY`

## Consumed generation-2 attempt

TASK-237 was published on canonical main `4991ade68a5743af7e886342684751744bee49ed` from exact source
`a53510ff353cdf926a76f1dc84363b7835c5cb4d`. It authorized exactly one Human-operated fresh generation-2
diagnostic attempt for context `p8-pilot-001-led-motion-tiktok-vn`, source ID `1731381331718341815`,
and the fixed selected listing:

`https://shop.tiktok.com/vn/pdp/den-led-cam-bien-chuyen-dong-3-che-do-sang-sac-usb-c/1731381331718341815`

The Human operator executed that attempt after TASK-237 publication with the operator-owned Chrome/CDP
endpoint reachable. The single-evaluate attach-only diagnostic completed its execution and returned the
stable safe failure reason `NO_BOUNDED_PDP_ROOT`. Validation terminated before artifact persistence,
so no `tiktok-pdp-dom-diagnostic-v1.json` artifact was created.

Under the TASK-237 authorization contract, either success or failure consumes the attempt. The reconciled
state is therefore:
- `diagnostic_authorization_generation=2`;
- `diagnostic_executed=true`;
- `diagnostic_outcome=FAIL_CLOSED`;
- `diagnostic_failure_reason=NO_BOUNDED_PDP_ROOT`;
- `diagnostic_artifact_created=false`;
- `authorized_diagnostic_attempts=1`;
- `authorized_diagnostic_attempts_remaining=0`;
- `execution_owner=HUMAN_OPERATOR`;
- `live_dom_diagnostic_authority=NONE`.

Historical generation 1 (`TASK-235`/`TASK-236`) remains separately represented and unchanged:
- Generation-1 outcome: `FAIL_CLOSED`;
- Generation-1 artifact created: `false`;
- Generation-1 authorized diagnostic attempts: `1`;
- Generation-1 diagnostic attempts remaining: `0`;
- Historical failure reason: `LEGACY_COMBINED_PUBLIC_PDP_AVAILABILITY_GATE`.

The Human terminal output and screenshot context are `NON_CANONICAL_DIAGNOSTIC_CONTEXT` only. They
demonstrate execution context but prove neither canonical marketplace evidence nor Product Truth.
No terminal text or screenshot-visible marketplace value is transcribed into canonical fields,
`ProductCandidateSnapshot`, or `SignalEvidence`.

TASK-233 capture history remains unchanged (`authorized_capture_attempts_remaining=0`,
`live_public_pdp_acquisition_authority=NONE`). The consumed generation-2 diagnostic does not reopen
capture, acquisition, evidence, ranking, approval, test, recommendation, or action authority.

## Bounded root-observability hardening

The safe reason `NO_BOUNDED_PDP_ROOT` established that blocked/challenge, login, listing-unavailable,
and exact URL identity gates did not terminate first, but it did not reveal whether title, price, or
commerce-action anchors were absent or which bounded root stage failed. Bounded root-observability
hardening extends the single-evaluate diagnostic without broadening authority or capturing page text.

The diagnostic preserves:
- Exactly one `session.evaluate(DIAGNOSTIC_SCRIPT)` call;
- Zero navigation or interaction (no navigate, refresh, click, type, scroll, search, or change variants);
- Exact current-page URL identity binding through the canonical TikTok parser;
- Safe failure gates (`BLOCKED_OR_CHALLENGE`, `LOGIN_GATE`, `LISTING_UNAVAILABLE`, `IDENTITY_MISMATCH`);
- TASK-137 manager-mediated borrowed-session cleanup (`close_session`).

The diagnostic payload is extended with one deterministic, allowlisted `root_probe` object containing
only structural counts and booleans capped by existing bounded discovery limits:
- `title_anchor_count` (capped at 12);
- `price_anchor_count` (capped at 12);
- `action_anchor_count` (capped at 12);
- `visible_explicit_pdp_root_count` (capped at 8);
- `explicit_root_with_commerce_anchors_count` (capped at 8);
- `main_present` (boolean);
- `main_visible` (boolean);
- `main_has_commerce_anchors` (boolean);
- `multi_anchor_common_ancestor_found` (boolean);
- `selected_root_kind` (one of `NONE`, `EXPLICIT_PDP_ROOT`, `MAIN`, `MULTI_ANCHOR_COMMON_ANCESTOR`).

The `root_probe` contains no raw HTML, full body/page text, cookies, storage, headers, credentials,
tokens, screenshots, network payloads, user profile data, or arbitrary DOM serialization.

For the specific post-identity safe failure `NO_BOUNDED_PDP_ROOT`, the diagnostic persists exactly one
create-exclusive external failure diagnostic artifact (`tiktok-pdp-dom-diagnostic-v1.json`) containing
only schema version, `FAIL_CLOSED` diagnostic metadata, fixed context/source identity, `observed_at`,
`evidence_authority=NONE`, `failure_reason=NO_BOUNDED_PDP_ROOT`, and the validated `root_probe`. It then
preserves the nonzero error result by re-raising `NO_BOUNDED_PDP_ROOT`. Other safe failures
(`BLOCKED_OR_CHALLENGE`, `LOGIN_GATE`, `LISTING_UNAVAILABLE`, `IDENTITY_MISMATCH`,
`MALFORMED_DIAGNOSTIC_PAYLOAD`) do not gain failure artifacts.

Successful diagnostic artifacts include the same validated `root_probe` additively while preserving the
existing bounded candidate allowlist and `evidence_authority=NONE`.

Artifact creation on `NO_BOUNDED_PDP_ROOT` is diagnostic observability only. It is not
`ProductCandidateSnapshot`, `SignalEvidence`, canonical evidence, Product Truth, ranking,
recommendation, approval, trend, test-readiness evidence, or commerce-action evidence.

## Publication gate and handoff

On exact reviewed TASK-238 publication:
- `live_dom_diagnostic_authority=NONE`;
- `diagnostic_authorization_generation=2`;
- `diagnostic_executed=true`;
- `diagnostic_outcome=FAIL_CLOSED`;
- `diagnostic_failure_reason=NO_BOUNDED_PDP_ROOT`;
- `diagnostic_artifact_created=false`;
- `authorized_diagnostic_attempts=1`;
- `authorized_diagnostic_attempts_remaining=0`;
- `root_observability_hardening_implemented=true`;
- `selector_repair_complete=false`;
- `live_public_pdp_acquisition_authority=NONE`;
- `automated_public_pdp_acquisition_authority=NONE`;
- `market_test_or_action_authority=NONE`;
- `automatic_progression=false`;
- `next_milestone=null`;
- `pending_commitments` are empty.

The exact post-publication handoff is `HUMAN_BRAIN_FRESH_ROOT_OBSERVABILITY_DIAGNOSTIC_AUTHORIZATION`.
TASK-238 does not authorize generation 3 or any live invocation. Any future live invocation requires a
fresh Human/Brain authorization. There is no automatic retry, selector repair, successor task,
acquisition, test, or commerce action.
