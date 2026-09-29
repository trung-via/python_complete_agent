# Phase 8 Public TikTok PDP Post-TASK253 Validation Carrier Provenance Rebinding

## 1. Decision and Exact Publication Lineage

- **Classification**: `POST_TASK253_PAIRED_PRICE_COLLECTOR_VALIDATION_CARRIER_PROVENANCE_REBINDING_ONLY`
- **Task ID**: `TASK-254`
- **Source Task ID**: `TASK-253`
- **Source Run ID**: `RUN-253-002`
- **Source Review ID**: `REVIEW-253-002`
- **Source Published SHA**: `33776f11b20977f46d45d394fa1c56040029b65d`
- **Collector Baseline Task ID**: `TASK-253`
- **Collector Baseline Source SHA**: `33776f11b20977f46d45d394fa1c56040029b65d`
- **Carrier Module**: `src/product_intelligence/tiktok_pdp_live_pilot.py`
- **Contract Identifier**: `POST_TASK253_PAIRED_PRICE_COLLECTOR_VALIDATION`
- **Context ID**: `p8-pilot-001-led-motion-tiktok-vn`
- **Authorized Source Product ID**: `1731381331718341815`
- **Selected Stable Listing Reference**: `https://shop.tiktok.com/vn/pdp/den-led-cam-bien-chuyen-dong-3-che-do-sang-sac-usb-c/1731381331718341815`
- **Validation Carrier Schema Version**: `2`
- **Validation Attempt Marker Filename**: `tiktok-pdp-live-validation-attempt-v2.json`
- **Validation Attempt Marker Schema Version**: `2`
- **Validation Result Filename**: `tiktok-pdp-live-validation-result-v2.json`
- **Validation Result Schema Version**: `2`

TASK-254 rebinds the existing sole Human-operated TikTok public-PDP validation carrier in place from the historical TASK-248 collector baseline to the exact reviewed/published TASK-253 collector source (`33776f11b20977f46d45d394fa1c56040029b65d`), which hardened bounded paired-price current-role admission under RUN-253-002 / REVIEW-253-002 PASS. Failed primary lineage RUN-253-001 / REVIEW-253-001 CHANGES_REQUIRED remains historical only.

---

## 2. Three-Literal Production Rebind

In `src/product_intelligence/tiktok_pdp_live_pilot.py`, the only permitted production delta is changing exactly three existing top-level assignment values:

```python
CONTRACT_IDENTIFIER = "POST_TASK253_PAIRED_PRICE_COLLECTOR_VALIDATION"
COLLECTOR_BASELINE_TASK_ID = "TASK-253"
COLLECTOR_BASELINE_SOURCE_SHA = "33776f11b20977f46d45d394fa1c56040029b65d"
```

No other production token in `src/product_intelligence/tiktok_pdp_live_pilot.py` changes.

---

## 3. Unchanged Carrier Mechanics, Collector Semantics, and V2 Artifact Structure

1. **Carrier Mechanics and Invariants**:
   - V2 filenames, schema version 2, and all TASK-249 carrier mechanics remain byte-identical and unchanged.
   - Future generated attempt marker (`tiktok-pdp-live-validation-attempt-v2.json`) and every conforming terminal result (`tiktok-pdp-live-validation-result-v2.json`) persist the three new literal provenance values.
   - Historical V2 artifacts remain immutable with their historical TASK-248 provenance.

2. **Collector and Architecture Preservation**:
   - `TikTokPdpCollector` in `src/product_intelligence/adapters/tiktok_pdp.py` remains byte-identical to published TASK-253 source.
   - Scalar price parser `parse_tiktok_pdp_price` in `src/product_intelligence/adapters/tiktok_parsing.py` remains byte-unchanged and the sole scalar admission authority under `AMBIGUOUS_PRICE_IS_NOT_EXACT_PRICE`.
   - Bounded DOM scope resolver (`src/product_intelligence/tiktok_pdp_dom_scope.py`), models (`src/product_intelligence/models.py`), CLI (`src/product_intelligence/cli.py`), and Playwright session/manager lifecycle remain byte-unchanged.
   - No second carrier, collector, parser, lifecycle owner, or history store is created.

---

## 4. Immutable Historical Facts (TASK-249, TASK-250, TASK-251, TASK-253)

Historical validation and diagnostic operations remain strictly immutable through their canonical historical owners:
- **TASK-251 Consumed Operation**:
  - Validation attempts: 1 authorized / 0 remaining (`HUMAN_OPERATOR`, `validation_executed: true`, `operation: SUCCESS`, `observation: OBSERVED`, `session_release: SUCCESS`, `process_exit_code: UNKNOWN`).
  - Marker: schema 2, 633 bytes, SHA256 `3588F3E2416B0E1BA8B3DEF49B73544B8C4D04BF3FEF01D17616393783F7C94E`.
  - Result: schema 2, 1947 bytes, SHA256 `808971B737F9C2647A7618827722E072A34BDEB07E8CD55325765B48D78CFAF2`.
- **TASK-253 Generation-8 Consumed Operation**:
  - Diagnostic attempts: 1 authorized / 0 remaining (`HUMAN_OPERATOR`, `diagnostic_executed: true`, `outcome: SUCCESS`, `artifact_created: true`).
  - V5 Diagnostic Artifact: schema 5, 34929 bytes, SHA256 `A61B58FC41B4CBDDB0F83A65625325F3685147C6948F74CA8D041C8658B40DD7`, `observed_at: 2026-09-26T07:43:19.570359+00:00`.
  - Bounded observations under `TITLE_LOCAL_COMMERCE_QUORUM` (level 2) and `exact_pair_membership_proven: false`.
- **Field Uncertainty Matrix**:
  - `current_price_validation_status: UNKNOWN`, `current_price_observed: null`.
  - `original_price_validation_status: OBSERVED_ONLY`, `original_price_observed: 68220.0`.
  - `canonical_evidence_ingested: false`, `price_role_resolution_complete: false`, `selector_repair_complete: false`.

---

## 5. Closed Positive Current Projection

TASK-254 defines a strict, closed direct-key contract for current state:

1. **`active_track`**:
   Direct keys are limited strictly to exactly 8 keys:
   `id`, `title`, `priority_owner`, `status`, `completion_basis`, `sequence_status`, `current_milestone`, `next_milestone`.
   - `id: P8_PUBLIC_PDP_POST_TASK253_VALIDATION_CARRIER_PROVENANCE_REBINDING`
   - `title: "P8 Public TikTok PDP Post-TASK253 Validation Carrier Provenance Rebinding"`
   - `priority_owner: HUMAN`
   - `status: DONE`
   - `completion_basis: PUBLICATION_GATED`
   - `sequence_status: COMPLETE_ON_EXACT_TASK_254_SOURCE_PUBLICATION`
   - `next_milestone: null`

2. **`active_track.current_milestone`**:
   Direct keys are limited strictly to the 44 specified keys:
   `id`, `task_id`, `title`, `status`, `completion_basis`, `classification`, `authorization_owner`, `source_task_id`, `source_run_id`, `source_review_id`, `source_published_sha`, `context_id`, `authorized_source_id`, `stable_listing_reference`, `collector_validation_baseline`, `carrier_module`, `validation_carrier_schema_version`, `validation_attempt_marker_filename`, `validation_attempt_marker_schema_version`, `validation_result_filename`, `validation_result_schema_version`, `authorized_validation_attempts`, `authorized_validation_attempts_remaining`, `validation_execution_owner`, `validation_executed`, `field_validation_uncertainty`, `current_price_validation_status`, `current_price_observed`, `original_price_validation_status`, `original_price_observed`, `operation_success_is_not_field_validation_success`, `canonical_evidence_ingested`, `price_role_resolution_complete`, `selector_repair_complete`, `live_public_pdp_acquisition_authority`, `automated_public_pdp_acquisition_authority`, `market_test_or_action_authority`, `automatic_live_pilot`, `automatic_progression`, `post_run_engineering_successor`, `next_milestone`, `exact_post_publication_handoff`, `post_publication_handoff`, `effective_only_when`.

3. **`post_p8_planning_handoff`**:
   Direct current scalar/projection keys are strictly limited to the 38 allowed keys:
   `destination`, `status`, `completed_commitment`, `source_task_id`, `source_run_id`, `source_review_id`, `source_published_sha`, `context_id`, `authorized_source_id`, `stable_listing_reference`, `collector_validation_baseline`, `carrier_module`, `validation_carrier_schema_version`, `validation_attempt_marker_filename`, `validation_attempt_marker_schema_version`, `validation_result_filename`, `validation_result_schema_version`, `authorized_validation_attempts`, `authorized_validation_attempts_remaining`, `validation_execution_owner`, `validation_executed`, `field_validation_uncertainty`, `current_price_validation_status`, `current_price_observed`, `original_price_validation_status`, `original_price_observed`, `operation_success_is_not_field_validation_success`, `canonical_evidence_ingested`, `price_role_resolution_complete`, `selector_repair_complete`, `live_public_pdp_acquisition_authority`, `automated_public_pdp_acquisition_authority`, `market_test_or_action_authority`, `automatic_live_pilot`, `automatic_progression`, `next_milestone`, `post_run_engineering_successor`, `boundary`.
   - Pre-existing nested historical mapping containers from canonical base `59272cec5a77db4f71a181a56875f11b94497936` are retained as historical owners and remain semantically immutable.
   - All legacy direct execution/diagnostic scalar residue outside the 38 allowed keys is removed from the direct current projection.

---

## 6. Absent `validation_carrier_source_sha` Key Until Successor Authorization

`validation_carrier_source_sha` is the canonical carrier execution-source field. To prevent premature binding, its key is strictly **ABSENT** from:
- `active_track.current_milestone`
- `post_p8_planning_handoff` direct current projection
- `completed_milestones` TASK-254 record

No `null`, `PENDING`, `UNKNOWN`, sentinel, guessed, or self SHA is permitted. Exact carrier source SHA binding is deferred to the future Human/Brain authorization task that authorizes live execution.

---

## 7. Governance-Test Historicalization

Governance tests are migrated to historical containers without semantic weakening:
- In `test_task_253_reconciles_gen8_success_and_hardens_paired_price_current_role_admission`, assertions reading TASK-253 from active track or direct handoff are relocated to `public_pdp_gen8_result_and_paired_price_role_hardening` and/or `completed_milestones["TASK-253"]`, proving that global current milestone is no longer TASK-253.
- In TASK-250 and TASK-249 governance tests, direct global handoff assertions for consumed TASK-233 capture attempts (1 authorized / 0 remaining / `HUMAN_OPERATOR`) move to `public_pdp_live_pilot_authorization`.
- Other historical assertions reading earlier tasks' facts from direct current fields are relocated to their respective nested/completed historical owners.

---

## 8. Preserved BP9 and Downstream State

- Active AIOS pin remains exactly `44eee353eda376c9db8cd88d97184d3122651bf5`.
- Historical task contracts (`.ai/tasks/TASK-207.yaml`, `TASK-255.yaml`, `TASK-259.yaml`) referencing TASK-254 revision 4 remain byte-unchanged as truthful historical text.
- Live planning pointers in `.ai/roadmap-state.yaml` prospectively identify the preserved TASK-254 continuation and move from revision 4 to revision 6:
  - `human_priority_side_track.next_after_publication.expected_revision: 6`
  - `human_priority_side_track.preserved_product_commitment.task_revision: 6`
  - `full_downstream_conformance.resume_target.task_revision: 6`
- Downstream conformance, adoption state, P1B Brain/Reviewer registries, and workflow bindings remain intact.

---

## 9. Fresh Validation Authority & Invariants

- Fresh validation authority is exactly 0:
  - `authorized_validation_attempts: 0`
  - `authorized_validation_attempts_remaining: 0`
  - `validation_execution_owner: NONE`
  - `validation_executed: false`
- All live/automated/action authorities remain strictly `NONE`:
  - `live_public_pdp_acquisition_authority: NONE`
  - `automated_public_pdp_acquisition_authority: NONE`
  - `market_test_or_action_authority: NONE`
  - `automatic_live_pilot: false`
  - `automatic_progression: false`
- Planning hands off exclusively to:
  `HUMAN_BRAIN_FRESH_POST_GEN8_PAIRED_PRICE_COLLECTOR_VALIDATION_AUTHORIZATION`
- Boundary: Publication changes provenance and planning state only and grants no live validation or downstream action authority.

### Mandatory Invariants
- `CAPABILITY_IS_NOT_AUTHORITY`: Carrier rebinding capability does not authorize live execution.
- `EVIDENCE_IS_NOT_PRODUCT_TRUTH`: Artifacts and test observations do not establish Product Truth.
- `SOURCE_IDENTITY_IS_NOT_CANONICAL_IDENTITY`: Listing ID preservation grants no live attempt.
- `SNAPSHOT_IS_NOT_TREND`: Point-in-time carrier validation does not establish recurring trend.
- `AMBIGUOUS_PRICE_IS_NOT_EXACT_PRICE`: Ambiguous pricing must not be coerced into exact scalars.
- `OPERATION_SUCCESS_IS_NOT_FIELD_VALIDATION_SUCCESS`: Carrier execution success does not validate field values.
- `MEASUREMENT_IS_NOT_AUTHORITY`: Code metrics and hashes do not convey execution authority.
- `ONE_CAPABILITY_ONE_AUTHORITY`: Carrier owns one-shot orchestration; collector and parser retain their existing authorities.
