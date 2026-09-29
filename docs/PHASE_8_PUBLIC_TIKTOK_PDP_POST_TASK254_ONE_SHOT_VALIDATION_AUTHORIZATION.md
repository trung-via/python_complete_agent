# Phase 8 Public TikTok PDP Post-TASK254 One-Shot Validation Authorization

## 1. Classification, Human Selection, and Exact Lineage

- **Classification**: `ONE_SHOT_POST_TASK254_PUBLIC_PDP_VALIDATION_AUTHORIZATION_ONLY`
- **Task**: `TASK-261`, revision 1
- **Human-selected TASK-260 candidate**: `AUTHORIZE_ONE_SHOT_POST_TASK254_CARRIER_VALIDATION`
- **Selection basis**: Exact TASK-260 r2 publication `6787c746396f333cb7e02d0736ed8beb2417a63c` and explicit Human selection of that candidate only. TASK-260's five-candidate list remains immutable, ordered for serialization only, and unranked.
- **Carrier source task/run/review/publication**: `TASK-254` / `RUN-254-003` / `REVIEW-254-001` / `36627c80e76f156fcb774b10fbd35d14df6d9ea4`
- **Validation carrier source SHA**: `36627c80e76f156fcb774b10fbd35d14df6d9ea4`
- **Distinct collector validation baseline**: `TASK-253` / `33776f11b20977f46d45d394fa1c56040029b65d`
- **Carrier**: `src/product_intelligence/tiktok_pdp_live_pilot.py`, existing V2 mechanics only.

TASK-261 is authorization-only. It performs zero TikTok/CDP operations and changes no carrier, collector, parser, browser/session, CLI, or artifact semantics. Carrier execution source provenance is TASK-254; collector validation baseline provenance remains separately TASK-253. The two fields must never be collapsed.

## 2. One Exact Listing and Publication-Gated Authority

The single Human-operated attempt is bound only to:

- Context: `p8-pilot-001-led-motion-tiktok-vn`
- Source product ID: `1731381331718341815`
- Stable listing: `https://shop.tiktok.com/vn/pdp/den-led-cam-bien-chuyen-dong-3-che-do-sang-sac-usb-c/1731381331718341815`
- CDP endpoint: `http://127.0.0.1:9222`

Only exact reviewed TASK-261 publication may make these values effective:

- `authorized_validation_attempts: 1`
- `authorized_validation_attempts_remaining: 1`
- `validation_execution_owner: HUMAN_OPERATOR`
- `validation_executed: false`
- `live_public_pdp_acquisition_authority: ONE_SHOT_EXACT_LISTING_ONLY`

Before that exact publication, authority remains zero and execution is unauthorized. `automated_public_pdp_acquisition_authority` and `market_test_or_action_authority` remain `NONE`; `automatic_live_pilot` and `automatic_progression` remain `false`. Replacement, arbitrary, inferred-identity, variant, search, batch, or multi-listing scope is not granted.

## 3. Mandatory Non-Consuming Preflight

Preflight is a separate Human-operated, read-only gate. It must not invoke the carrier, create V2 artifacts, or navigate, evaluate, click, type, scroll, refresh, or otherwise mutate the selected page. Before any consuming invocation, the operator must establish all of the following:

1. CDP at `http://127.0.0.1:9222` is reachable.
2. Read-only CDP target enumeration finds exactly one normal `type=page` target total, and that target is the selected exact PDP for source ID `1731381331718341815`.
3. The explicit job root is fresh, external to the Git repository, and contains none of `tiktok-pdp-live-pilot-result-v1.json`, `tiktok-pdp-live-validation-attempt-v2.json`, or `tiktok-pdp-live-validation-result-v2.json`.
4. Each of the following ten execution-critical files is content-equivalent to exact TASK-254 publication `36627c80e76f156fcb774b10fbd35d14df6d9ea4`:
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

Repository HEAD equality is not required. Any file mismatch fails closed and requires a fresh Human/Brain decision; do not substitute a different source. The exact passed job root, target state, and ten file contents bind the later consuming invocation. If any changes before invocation, rerun the non-consuming preflight. Repeating preflight while the marker is absent neither consumes the attempt nor creates an automatic retry loop.

## 4. Existing One-Shot Invocation and Consumption Boundary

The sole existing Human-facing CLI is invoked as one physical PowerShell line with one explicit external job root and the fixed endpoint:

```powershell
python -m src.product_intelligence.cli tiktok-pdp-live-pilot --job-root <fresh-external-validation-job-root> --cdp-endpoint http://127.0.0.1:9222
```

No TASK-261 CLI or production surface is added. A pre-marker shell, transport, preflight, or local-gate failure may be manually corrected under this same authorization only while the marker is absent. No correction is automatic.

Successful create-exclusive persistence of `tiktok-pdp-live-validation-attempt-v2.json` is the durable consumption boundary. Every marker-present terminal or interrupted state consumes the sole attempt: `SUCCESS`, `FAIL_CLOSED`, result-persistence failure, missing/malformed/nonconforming result, or process/network/power interruption. No retry, resume, refresh, replacement target, or second invocation is authorized. Any later live attempt requires fresh Human/Brain authorization.

Marker and result artifacts that exist after consumption must be preserved byte-for-byte through review. Do not reconstruct operation or CLI facts from chat recollection.

## 5. Mandatory Artifact-Grounded Post-Attempt Review

Human/Brain review derives state from exact external artifacts and records:

- Exact external job-root binding.
- Marker and result presence, SHA256, and byte size when present.
- Result V2 conformance and only conforming bounded fields: `operation_status`, `observation_status`, `session_release_status`, and `failure_reason` when available.
- Snapshot fields only when `observation_status` is `OBSERVED`.
- Process or CLI exit code only when directly observed; otherwise it remains `UNKNOWN`.

`OPERATION_SUCCESS_IS_NOT_FIELD_VALIDATION_SUCCESS`: operation success and `OBSERVED` prove only one bounded listing observation. Optional fields may remain unknown. Affiliate eligibility, commission rate, and estimated commission remain `NOT_ESTABLISHED`; a public PDP cannot establish them. No Product Truth, canonical evidence, trend, ranking, approval, market-test readiness, or commerce-action authority follows from authorization or a future `SUCCESS`.

TASK-260 remains immutable completed planning history with `MARKET_TEST_READINESS_NOT_ESTABLISHED` and its original five unranked candidates. The current roadmap prospectively records only the Human-selected authorization. TASK-261 publication hands off only to `HUMAN_OPERATOR_ONE_SHOT_POST_TASK254_PUBLIC_PDP_VALIDATION_EXECUTION`, followed by mandatory `HUMAN_BRAIN_POST_TASK254_PUBLIC_PDP_VALIDATION_REVIEW`. `next_milestone` is `null`, pending commitments are empty, automatic progression is false, and no engineering successor, retry, or market action is preselected.

## 6. Mandatory Governance Invariants

- `CAPABILITY_IS_NOT_AUTHORITY`
- `EVIDENCE_IS_NOT_KNOWLEDGE`
- `EVIDENCE_IS_NOT_PRODUCT_TRUTH`
- `SOURCE_IDENTITY_IS_NOT_CANONICAL_IDENTITY`
- `SNAPSHOT_IS_NOT_TREND`
- `AMBIGUOUS_PRICE_IS_NOT_EXACT_PRICE`
- `OPERATION_SUCCESS_IS_NOT_FIELD_VALIDATION_SUCCESS`
- `AUTOMATION_IS_NOT_INTELLIGENCE`
- `RECOMMENDATION_IS_NOT_DECISION`
- `ONE_CAPABILITY_ONE_AUTHORITY`
