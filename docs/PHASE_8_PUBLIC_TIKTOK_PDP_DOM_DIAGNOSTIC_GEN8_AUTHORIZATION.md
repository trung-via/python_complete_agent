# Phase 8 Public TikTok PDP DOM Diagnostic Generation-8 Authorization

## 1. Decision and Exact Publication Lineage

- **Classification**: `FRESH_GENERATION_8_BOUNDED_PRICE_ROLE_DIAGNOSTIC_AUTHORIZATION_ONLY`
- **Source Task ID**: `TASK-251`
- **Source Run ID**: `RUN-251-004`
- **Source Review ID**: `REVIEW-251-003`
- **Source Published SHA**: `0c23b4f0530f17f8bb77e23f8199fc167a6e68b1`
- **Diagnostic V5 Implementation Source SHA**: `0c23b4f0530f17f8bb77e23f8199fc167a6e68b1`
- **Generation-8 Execution Source SHA**: `0c23b4f0530f17f8bb77e23f8199fc167a6e68b1`

TASK-252 canonicalizes exactly one fresh Human-operated generation-8 bounded TikTok PDP price-role diagnostic authorization for the already-selected exact listing, using only the reviewed and published TASK-251 schema-V5 diagnostic implementation at `0c23b4f0530f17f8bb77e23f8199fc167a6e68b1`.

Historical implementation and execution provenance remains immutable:
- TASK-246 V4 implementation and generation-7 execution source: `60da55d5241c7b4c433d9b2d7d5d3725556f443c`
- TASK-244 V3 implementation and generation-6 execution source: `bc4c48de89129583f024ab622051ea322f9ff5ea`
- TASK-240 V2 implementation source: `8ef61df3936652fb7aeda8ca31ce1db3621ff4cf`
- TASK-242 generation-5 execution source: `d113c4a7ce2e2835d532935bc195c922aa3628ca`
- TASK-248 collector baseline source: `39979020a10b78e1f86c30cf2b704f2f975daec9`
- TASK-249 validation carrier source: `84739c2a13d9d89ef5379ecba7a9d4b83ed64771`

TASK-252 is authorization-only: it changes zero production code, modifies no diagnostic or collector implementation, accesses no live TikTok or CDP session during engineering or deterministic verification, and grants zero automated or market-action authority.

---

## 2. Immutable Prior Evidence & Uncertainty State

TASK-251 publication truth remains immutable completed history:
- `current_price_validation_status: UNKNOWN`
- `current_price_observed: null`
- `original_price_validation_status: OBSERVED_ONLY`
- `original_price_observed: 68220.0`
- `canonical_evidence_ingested: false`
- `price_role_resolution_complete: false`
- `selector_repair_complete: false`
- `generation_8_authorized: false`
- `generation_8_authorized_diagnostic_attempts: 0`
- `generation_8_authorized_diagnostic_attempts_remaining: 0`
- `generation_8_diagnostic_execution_owner: NONE`
- `live_dom_diagnostic_authority: NONE`

Current uncertainty remains strictly unchanged during TASK-252 authorization engineering:
- Under `OPERATION_SUCCESS_IS_NOT_FIELD_VALIDATION_SUCCESS`, the prior post-TASK250 live validation success established only that one conforming listing snapshot was returned; it did not extract current price.
- Under `AMBIGUOUS_PRICE_IS_NOT_EXACT_PRICE`, the observed scalar `68220.0` is an admitted `original_price` candidate observed via strike-through presentation, not current price.
- Current price remains strictly `UNKNOWN` / `null`.
- Optional validation fields (`shop_name`, `discount_percent`, `sold_count`, `rating`, `review_count`) remain strictly `UNKNOWN` / `null`.
- No prior live evidence is promoted into Product Truth, canonical current price, trend, ranking, approval, or repair authority.

Prior consumed diagnostic generations 1-7 and live validation attempts remain immutable external historical records:
- Generation 7 executed with terminal status `SUCCESS`, selected root `TITLE_LOCAL_COMMERCE_QUORUM` (level 2), creating `tiktok-pdp-dom-diagnostic-v4.json` with `evidence_authority=NONE`.
- Post-TASK250 validation attempt executed with terminal status `SUCCESS` / `OBSERVED`, creating `tiktok-pdp-live-validation-attempt-v2.json` and `tiktok-pdp-live-validation-result-v2.json`.

---

## 3. Exact Generation-8 Authority & Bounded Context

Only exact reviewed TASK-252 publication grants:
- `diagnostic_authorization_generation: 8`
- `live_dom_diagnostic_authority: ONE_SHOT_ATTACH_ONLY_EXACT_LISTING`
- `generation_8_authorized: true`
- `generation_8_authorized_diagnostic_attempts: 1`
- `generation_8_authorized_diagnostic_attempts_remaining: 1`
- `generation_8_diagnostic_execution_owner: HUMAN_OPERATOR`
- `generation_8_diagnostic_executed: false`

Before exact TASK-252 publication, Generation 8 remains unauthorized.

The attempt is bound strictly and exclusively to the selected listing:
- **Context ID**: `p8-pilot-001-led-motion-tiktok-vn`
- **Authorized Source Product ID**: `1731381331718341815`
- **Selected Stable Listing Reference**: `https://shop.tiktok.com/vn/pdp/den-led-cam-bien-chuyen-dong-3-che-do-sang-sac-usb-c/1731381331718341815`
- **Operator CDP Endpoint**: `http://127.0.0.1:9222`

TASK-252 preserves all closed authorities:
- `arbitrary_target_authority: NONE`
- `replacement_target_authority: NONE`
- `search_authority: NONE`
- `batch_authority: NONE`
- `inferred_identity_authority: NONE`
- `variant_switching_authority: NONE`
- `selector_repair_authority: NONE`
- `live_public_pdp_acquisition_authority: NONE`
- `automated_public_pdp_acquisition_authority: NONE`
- `market_test_or_action_authority: NONE`
- `automatic_live_pilot: false`
- `automatic_progression: false`

---

## 4. Frozen Schema-V5 Carrier & Bounded Observation Semantics

The published schema-V5 carrier is frozen exactly with zero production-code modification:
- **Sole Diagnostic Owner**: `src/product_intelligence/tiktok_pdp_dom_diagnostic.py`
- **Canonical CLI Subcommand**: `tiktok-pdp-dom-diagnostic`
- **Artifact Contract**:
  - Filename: `tiktok-pdp-dom-diagnostic-v5.json`
  - `schema_version: 5`
  - Create-exclusive external persistence
  - `evidence_authority: NONE`
- **Browser Contract**:
  - Attach-only borrowed session (`TASK-137`)
  - Exactly one `session.evaluate(DIAGNOSTIC_SCRIPT)`
  - Zero navigation, refresh, click, type, scroll, or variant switching
  - Manager-mediated session cleanup preserved
  - Light-DOM traversal only; zero shadow-root or iframe traversal

### Bounded Root Scope Resolution
The diagnostic consumes `src/product_intelligence/tiktok_pdp_dom_scope.py` completely unmodified, preserving exact frozen root-selection precedence:
1. `EXPLICIT_PDP_ROOT`
2. `MAIN`
3. `MULTI_ANCHOR_COMMON_ANCESTOR`
4. `TITLE_LOCAL_COMMERCE_QUORUM` (unique visible title fallback, narrowest-first ascending ancestor search levels 1-6, max 300 descendant elements per subtree, fail-closed unresolved narrower-subtree truncation, strong currency plus paired `BUY_LIKE` / `CART_LIKE` control quorum).

### Bounded Sanitized Price-Role Probe
The V5 `price_role_probe` is strictly observation-only:
- Exposes 12 bounded structural counts and up to 8 sanitized `candidate_samples`.
- Strictly structural and presentation properties only; zero raw candidate price text, numbers, HTML, style strings, or arbitrary attributes are persisted.
- Normalizes candidate text in-memory only to assign opaque group identifiers (`TEXT_GROUP_1`, `TEXT_GROUP_2`); zero raw text or reversible hashes are persisted.
- Does not invoke `parse_tiktok_pdp_price`, does not select a scalar, does not infer current or original roles, and creates no second price authority.
- Zero candidates and unresolved roles are valid `SUCCESS` observations observing uncertainty rather than inventing carrier failure taxonomies.
- Fail-closed path (`NO_BOUNDED_PDP_ROOT`) emits a conforming V5 payload with an empty/zeroed `price_role_probe`.

---

## 5. Non-Consuming Preflight

The non-consuming Gen-8 preflight is separate from the consuming invocation, must not invoke the diagnostic carrier, and does not consume the attempt. It may only establish:

1. CDP `127.0.0.1:9222` is reachable.
2. Read-only browser target enumeration reports exactly one normal `type=page` target total, and that sole target is the exact selected PDP for source ID `1731381331718341815`.
3. A fresh explicit external generation-8 job root contains none of:
   - `tiktok-pdp-dom-diagnostic-v1.json`
   - `tiktok-pdp-dom-diagnostic-v2.json`
   - `tiktok-pdp-dom-diagnostic-v3.json`
   - `tiktok-pdp-dom-diagnostic-v4.json`
   - `tiktok-pdp-dom-diagnostic-v5.json`
4. All seven execution/interpretation-critical files are content-equivalent to `generation_8_execution_source_sha` `0c23b4f0530f17f8bb77e23f8199fc167a6e68b1`:
   - `src/product_intelligence/tiktok_pdp_dom_diagnostic.py`
   - `src/product_intelligence/tiktok_pdp_dom_scope.py`
   - `src/product_intelligence/adapters/tiktok_pdp.py`
   - `src/product_intelligence/adapters/tiktok_parsing.py`
   - `src/product_intelligence/cli.py`
   - `src/integrations/playwright/manager.py`
   - `src/integrations/playwright/session.py`

Repository HEAD equality is not required. Preflight does not invoke the carrier and does not consume the attempt.

The exact fresh external generation-8 job root and browser target state that pass preflight are bound to the subsequent consuming invocation. If that root or browser target state is intentionally changed before invocation, preflight must be repeated. Repeating preflight without carrier invocation does not consume the attempt and grants no additional authority.

---

## 6. One-Line Transport and Consuming Invocation

The Human-facing invocation must be entered as exactly one physical PowerShell line, with no backtick or multiline continuation:

```powershell
python -m src.product_intelligence.cli tiktok-pdp-dom-diagnostic --job-root <fresh-external-generation-8-job-root> --cdp-endpoint http://127.0.0.1:9222
```

A shell or PowerShell parser transport failure before a valid `tiktok-pdp-dom-diagnostic` carrier invocation begins is a transport failure and does not by itself consume the attempt.

Once valid carrier invocation begins, every terminal outcome consumes the sole generation-8 attempt:
- `SUCCESS`
- `NO_BOUNDED_PDP_ROOT`
- `BLOCKED_OR_CHALLENGE`
- `LOGIN_GATE`
- `LISTING_UNAVAILABLE`
- `IDENTITY_MISMATCH`
- `MALFORMED_DIAGNOSTIC_PAYLOAD`
- Session / evaluation / artifact failure or any other terminal outcome.

No automatic retry, refresh, resume, second invocation, or replacement target is authorized.

`SUCCESS` may create the bounded V5 artifact. `NO_BOUNDED_PDP_ROOT` retains the create-exclusive V5 `FAIL_CLOSED` artifact contract. Other safe failures may remain artifact-free under the published carrier. Every artifact retains `evidence_authority=NONE`. If an artifact exists, later review must use its actual SHA256, size, and observed_at timestamp; TASK-252 must not guess or predeclare those values.

---

## 7. Interpretation Boundaries, Review Authority, and Handoff

Mandatory post-attempt review authority is `HUMAN_BRAIN_GENERATION_8_BOUNDED_PRICE_ROLE_DIAGNOSTIC_REVIEW`. Brain review must use actual terminal output plus the exact V5 artifact if created.

### Diagnostic Interpretation Limits
1. **Marginal Counts Are Not Intersection Proofs**: A non-zero `explicit_current_structural_signal_count` does not prove that the same candidate is collector-eligible, leaf, non-range, or scalar-safe unless the bounded sample evidence establishes that conjunction. Global probe counts must not be combined as if they were candidate intersections.
2. **Sample Non-Exhaustiveness**: `candidate_samples` are bounded to at most eight and are not exhaustive when `currency_candidate_count` exceeds the sample count. Negative sample observations must not be treated as global absence in that case.
3. **Scan Truncation**: If `bounded_scan_truncated` is true, negative observations are non-exhaustive.
4. **Descriptive Ambiguity Hints**: Range-like or multi-numeric observations are descriptive ambiguity hints only and do not independently prove parser defect or root cause.
5. **Epistemic Boundaries**: Diagnostic `SUCCESS` proves only that fixed identity, access, bounded-root resolution, V5 structural observation, and artifact creation succeeded. It does not prove canonical current price, Product Truth, collector defect, parser defect, acquisition readiness, or selector repair.

### Valid Non-Mutating Disposition: `INSUFFICIENT_DIAGNOSTIC_RESOLUTION`
Future Brain review must explicitly allow the disposition `INSUFFICIENT_DIAGNOSTIC_RESOLUTION` when a valid V5 `SUCCESS` still cannot distinguish a sufficiently bounded engineering cause. This disposition grants no retry, repair, selector, collector, acquisition, or action authority. A sufficiently supported bounded engineering cause may justify authoring a separate narrow successor task; the live artifact itself never self-authorizes mutation.

### Execution Handoff
Exact TASK-252 publication hands off only to:
- **Global Execution Handoff**: `HUMAN_OPERATOR_GENERATION_8_BOUNDED_PRICE_ROLE_DIAGNOSTIC_EXECUTION`
- **Post-Attempt Review Authority**: `HUMAN_BRAIN_GENERATION_8_BOUNDED_PRICE_ROLE_DIAGNOSTIC_REVIEW`
- **Mandatory Post-Diagnostic Review**: `HUMAN_BRAIN_GENERATION_8_BOUNDED_PRICE_ROLE_DIAGNOSTIC_REVIEW`
- `active_track.next_milestone`: `null`
- `post_p8_planning_handoff.next_milestone`: `null`
- `pending_commitments`: `[]`
- `post_run_engineering_successor`: `null`

Core governance principles remain mandatory:
- `CAPABILITY_IS_NOT_AUTHORITY`
- `EVIDENCE_IS_NOT_PRODUCT_TRUTH`
- `SOURCE_IDENTITY_IS_NOT_CANONICAL_IDENTITY`
- `SNAPSHOT_IS_NOT_TREND`
- `AMBIGUOUS_PRICE_IS_NOT_EXACT_PRICE`
- `MEASUREMENT_IS_NOT_AUTHORITY`
- `OPERATION_SUCCESS_IS_NOT_FIELD_VALIDATION_SUCCESS`
- `ONE_CAPABILITY_ONE_AUTHORITY`
