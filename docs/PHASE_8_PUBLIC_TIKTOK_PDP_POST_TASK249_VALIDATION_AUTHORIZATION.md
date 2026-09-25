# Phase 8 Public TikTok PDP Post-TASK249 Validation Authorization

## 1. Decision and Exact Publication Lineage

- **Classification**: `ONE_SHOT_POST_TASK249_PUBLIC_PDP_VALIDATION_AUTHORIZATION_ONLY`
- **Source Task ID**: `TASK-249`
- **Source Run ID**: `RUN-249-002`
- **Source Review ID**: `REVIEW-249-001`
- **Source Published SHA**: `84739c2a13d9d89ef5379ecba7a9d4b83ed64771`
- **Validation Carrier Source SHA**: `84739c2a13d9d89ef5379ecba7a9d4b83ed64771`
- **Carrier Module**: `src/product_intelligence/tiktok_pdp_live_pilot.py`

TASK-250 revision 2 is strictly authorization-only and canonicalizes exactly one Human-operated post-TASK249 live TikTok public-PDP collector validation authorization. It performs zero live operations during engineering or deterministic verification, changes no production code, attaches to no live browser, creates no validation artifacts, and consumes zero attempts.

Carrier execution source and collector baseline provenance are distinct semantic fields:
- **Validation Carrier Execution Source**: exact reviewed and published TASK-249 candidate `84739c2a13d9d89ef5379ecba7a9d4b83ed64771`.
- **Collector Validation Baseline**: exact reviewed and published TASK-248 source `39979020a10b78e1f86c30cf2b704f2f975daec9` (`TikTokPdpCollector` in `src/product_intelligence/adapters/tiktok_pdp.py` with bounded root-scoped price extraction consuming `src/product_intelligence/tiktok_pdp_dom_scope.py`).

Historical TASK-233 capture history (`authorized_capture_attempts: 1`, `authorized_capture_attempts_remaining: 0`) is preserved solely as consumed historical lineage and grants no validation authority. Prior TASK-249 zero-at-publication authority facts (`authorized_validation_attempts: 0`, `authorized_validation_attempts_remaining: 0`) remain immutable historical facts for TASK-249.

---

## 2. Fixed Target Listing & Bounded Scope

The single validation attempt is bound strictly and exclusively to the already-selected listing:
- **Context ID**: `p8-pilot-001-led-motion-tiktok-vn`
- **Source Product ID**: `1731381331718341815`
- **Selected Stable Listing Reference**: `https://shop.tiktok.com/vn/pdp/den-led-cam-bien-chuyen-dong-3-che-do-sang-sac-usb-c/1731381331718341815`
- **Operator CDP Endpoint**: `http://127.0.0.1:9222`

This authorization grants:
- `arbitrary_target_authority: NONE`
- `replacement_target_authority: NONE`
- `search_authority: NONE`
- `batch_authority: NONE`
- `inferred_identity_authority: NONE`
- `variant_switching_authority: NONE`
- `selector_repair_authority: NONE`
- `automated_public_pdp_acquisition_authority: NONE`
- `market_test_or_action_authority: NONE`
- `automatic_live_pilot: false`
- `automatic_progression: false`

---

## 3. Publication-Gated Validation Authority

Only exact reviewed and published TASK-250 revision 2 sets:
- `authorized_validation_attempts: 1`
- `authorized_validation_attempts_remaining: 1`
- `validation_execution_owner: HUMAN_OPERATOR`
- `validation_executed: false`
- `live_public_pdp_acquisition_authority: ONE_SHOT_EXACT_LISTING_ONLY`

Before exact publication, the fresh validation attempt remains unauthorized (`authorized_validation_attempts: 0`, `authorized_validation_attempts_remaining: 0`).

---

## 4. Mandatory Non-Consuming Execution Preflight

Preflight is strictly non-consuming and separate from carrier invocation. It must never call `tiktok-pdp-live-pilot`, must not create the attempt marker or result artifact, and must not navigate, evaluate, click, type, refresh, or mutate the browser session or target page.

Preflight must prove all of the following:
1. **CDP Reachability**: `http://127.0.0.1:9222` is reachable.
2. **Page Target Unambiguity**: Read-only browser target enumeration reports exactly one normal `type=page` target in total across all contexts, and that sole page is the exact selected PDP for source ID `1731381331718341815`.
3. **Fresh External Job Root**: The explicit external job root is strictly outside the Git repository and contains none of:
   - `tiktok-pdp-live-pilot-result-v1.json` (legacy V1)
   - `tiktok-pdp-live-validation-attempt-v2.json` (V2 marker)
   - `tiktok-pdp-live-validation-result-v2.json` (V2 result)
4. **Ten-File Content Equivalence**: All ten execution-critical files are content-equivalent to exact TASK-249 published source `84739c2a13d9d89ef5379ecba7a9d4b83ed64771`:
   - `src/product_intelligence/tiktok_pdp_live_pilot.py`
   - `src/product_intelligence/cli.py`
   - `src/product_intelligence/adapters/tiktok_pdp.py`
   - `src/product_intelligence/adapters/tiktok_parsing.py`
   - `src/product_intelligence/tiktok_pdp_dom_scope.py`
   - `src/product_intelligence/models.py`
   - `src/integrations/playwright/manager.py`
   - `src/integrations/playwright/session.py`
   - `src/browser/session.py`
   - `src/browser/models.py`

Repository HEAD equality is not required.

Preflight should record bounded environment provenance when deterministically observable: Python version, installed Playwright package version, and borrowed Chromium/Chrome version. These values are context and uncertainty evidence only, not authority and not Product Truth. Absence of optional provenance never creates retry authority.

The exact job root and browser target state that pass preflight are bound to the subsequent consuming invocation. If job-root contents, normal-page target count, selected target URL, or execution-critical file contents change before invocation, preflight must be rerun. Repeating non-consuming preflight while the V2 marker remains absent does not consume the attempt.

---

## 5. One-Line Physical PowerShell Transport & Consuming Invocation

The Human-facing CLI command surface remains unmodified (`tiktok-pdp-live-pilot`). The operator invocation must be entered as exactly one physical PowerShell command line with no backtick or multiline continuation:

```powershell
python -m src.product_intelligence.cli tiktok-pdp-live-pilot --job-root <fresh-external-validation-job-root> --cdp-endpoint http://127.0.0.1:9222
```

A shell, parser, transport, or local preflight failure occurring before the create-exclusive attempt marker is written does not consume the attempt and may be manually corrected while the marker remains absent. No correction or retry is automatic.

---

## 6. Durable V2 Consumption Boundary & Artifact Preservation

Successful create-exclusive persistence of `tiktok-pdp-live-validation-attempt-v2.json` in the external job root is the durable attempt-consumption boundary.

Once the marker exists, every terminal outcome consumes the one authorized attempt:
- `terminal_outcome_consumption: EVERY_TERMINAL_OUTCOME`
- `automatic_retry_refresh_resume: false`
- `second_invocation_authority: NONE`

Outcomes:
- **`SUCCESS`**: consumed with operation success.
- **`FAIL_CLOSED`**: consumed fail-closed.
- **Missing, malformed, or nonconforming result, process loss, network loss, or power interruption**: `CONSUMED_INTERRUPTED_OR_UNOBSERVED`.

None of these marker-present states authorizes retry, resume, refresh, replacement target, second invocation, or automatic follow-up. Any future attempt requires fresh Human/Brain authorization after mandatory review.

**Artifact Preservation**:
Once created, the external marker and any result artifact must be preserved byte-for-byte through mandatory post-attempt review. Neither Human operator nor automation may delete, edit, truncate, rewrite, or replace either artifact to obtain a cleaner result or regain authorization.

---

## 7. OPERATION_SUCCESS_IS_NOT_FIELD_VALIDATION_SUCCESS

`OPERATION_SUCCESS_IS_NOT_FIELD_VALIDATION_SUCCESS` is an absolute architectural invariant:
- A terminal status of `operation_status: SUCCESS` combined with `observation_status: OBSERVED` establishes only that one admitted bounded listing observation was returned and session release succeeded.
- It does not prove that `price`, `original_price`, `discount_percent`, `sold_count`, `rating`, `review_count`, or any optional field was observed or extracted.
- Null or unknown optional fields remain unknown and must be reviewed field-by-field without fabricating an expected value.
- A successful live observation remains bounded source evidence; it does not grant Product Truth, canonical identity, trend, ranking, recommendation, approval, test readiness, or commerce-action authority.

---

## 8. Human-Operated Execution & Epistemic Boundaries

The Human operator retains exclusive execution ownership:
- `validation_execution_owner: HUMAN_OPERATOR`
- Human operator decides handling of challenge, login, and CAPTCHA states.
- The carrier and collector fail-closed behavior is the only authorized software execution path.
- TASK-250 authorizes no CAPTCHA solving, credential capture, stealth/evasion, alternate accounts, automatic challenge continuation, or exception message semantic reinterpretation.

---

## 9. Mandatory Artifact-Grounded Post-Attempt Review & Governance Handoff

Post-attempt review must derive attempt state from the external V2 artifacts, not from conversational recollection. It must record at minimum:
1. Exact external job-root binding.
2. Marker presence, size in bytes, and SHA256 when present.
3. Result presence, size in bytes, and SHA256 when present.
4. Result conformance to schema V2.
5. Bounded `operation_status`, `observation_status`, `session_release_status`, and `failure_reason` only when present in a conforming result.
6. Bounded snapshot fields only when `OBSERVED`.
7. Process / CLI exit code only when directly observed (must remain `UNKNOWN` if not established).

Governance handoff:
- **Post-Publication Execution Handoff**: `HUMAN_OPERATOR_ONE_SHOT_POST_TASK249_PUBLIC_PDP_VALIDATION_EXECUTION`
- **Post-Attempt Review Authority**: `HUMAN_BRAIN_POST_TASK249_PUBLIC_PDP_VALIDATION_REVIEW`
- **Mandatory Post-Validation Review**: `HUMAN_BRAIN_POST_TASK249_PUBLIC_PDP_VALIDATION_REVIEW`
- `active_track.next_milestone: null`
- `post_p8_planning_handoff.next_milestone: null`
- `pending_commitments: []`
- `post_run_engineering_successor: null`

Core governance principles remain mandatory:
- `CAPABILITY_IS_NOT_AUTHORITY`
- `EVIDENCE_IS_NOT_PRODUCT_TRUTH`
- `SOURCE_IDENTITY_IS_NOT_CANONICAL_IDENTITY`
- `SNAPSHOT_IS_NOT_TREND`
- `AMBIGUOUS_PRICE_IS_NOT_EXACT_PRICE`
- `MEASUREMENT_IS_NOT_AUTHORITY`
- `OPERATION_SUCCESS_IS_NOT_FIELD_VALIDATION_SUCCESS`
- `ONE_CAPABILITY_ONE_AUTHORITY`
