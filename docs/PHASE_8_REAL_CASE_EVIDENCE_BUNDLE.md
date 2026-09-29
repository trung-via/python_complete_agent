# Phase 8 — Real Case Evidence Bundle Carrier and Authorization

## 1. Classification, Exact Case, and Authority Lineage

- **Classification**: `P8_REAL_CASE_SOURCE_OBSERVATION_BUNDLE_ONE_SHOT_ONLY`
- **Task ID**: `TASK-263`, revision 1
- **Authorization Owner**: `HUMAN_BRAIN`
- **Context ID**: `p8-pilot-001-led-motion-tiktok-vn`
- **Authorized Source ID**: `1731381331718341815`
- **Stable Listing Reference**: `https://shop.tiktok.com/vn/pdp/den-led-cam-bien-chuyen-dong-3-che-do-sang-sac-usb-c/1731381331718341815`
- **Carrier Production Module**: `src/product_intelligence/tiktok_pdp_case_bundle.py`
- **Canonical CLI Subcommand**: `tiktok-pdp-case-bundle`
- **Preceding Milestone**: `TASK-262` (`POST_TASK261_ONE_SHOT_VALIDATION_SUCCESS_RECONCILIATION_ONLY`)

TASK-263 creates one bounded attach-only carrier and one-shot Human authorization for the exact selected TikTok Shop Vietnam PDP listing. It does not perform the live capture itself, construct canonical evidence, mutate P7 semantics, infer Product Truth, use MCP, call marketplace APIs, or generalize acquisition beyond the single P8 case.

---

## 2. Carrier Architecture & Atomic Browser Capabilities

The bundle carrier is an attach-only orchestration tool that borrows the existing already-open session from the Human-owned browser via Chromium DevTools Protocol (CDP):

- **Existing Lifecycle Reuse**: Uses only existing `BrowserSession` `evaluate()` and `screenshot()` lifecycle capabilities defined under `TASK-137`.
- **Zero Interactive Mutation**: Performs zero navigation (`navigate()`), zero clicks (`click()`), zero typing (`type_text()`), zero keypresses (`press()`), and zero scrolling.
- **Single Evaluation & Screenshot**: Evaluates JavaScript in the page exactly once to capture the sanitized structural projection, and invokes `screenshot()` exactly once for full-page visual cross-check.
- **Session Release Ownership**: Releases/closes only the borrowed session via `close_session()` without terminating or disturbing the Human-owned browser process.
- **No Browser API Changes**: Requires no changes to `BrowserSession`, `BrowserManager`, or Playwright session protocols.

---

## 3. Fixed Three-Artifact Contract & Durable Consumption Boundary

The carrier produces exactly three final artifacts in an explicit external job root:

1. `p8-real-case-manifest-v1.json` — Bounded provenance, hashes, sizes, timestamps, and review flags.
2. `p8-real-case-page-projection-v1.json` — Deterministic, sanitized rendered-page structural projection.
3. `p8-real-case-full-page-v1.png` — External full-page screenshot visual cross-check.

No fourth output, log, cache, checkpoint, HAR, HTML dump, or network payload is created.

### In-Memory Preparation & Manifest-First Consumption Boundary

1. **Pre-Manifest Memory Preparation**: Both projection JSON payload and full-page PNG screenshot bytes are fully retrieved, validated, serialized, and hashed (SHA256) in memory before any final artifact path is created on disk.
2. **Durable One-Shot Consumption Boundary**: `p8-real-case-manifest-v1.json` is written create-exclusively first. Successful creation of the manifest constitutes the irrevocable one-shot consumption boundary.
3. **Fail-Closed Post-Manifest Failure**: After manifest creation, `p8-real-case-page-projection-v1.json` and `p8-real-case-full-page-v1.png` are written create-exclusively and verified against manifest hashes. If either write fails, the operation returns a fail-closed consumed outcome; the manifest is never mutated, repaired, deleted, or substituted.
4. **Non-Consuming Pre-Manifest Failure**: Before manifest creation, failures in input validation, preflight, session borrowing, evaluation, or screenshot preparation fail without consuming only when no artifact path exists in the job root.

---

## 4. Rendered Structural Projection v1 Sanitation & Truncation

The projection capture is a bounded rendered-source observation, NOT raw DOM serialization:

- **Visible Elements Only**: Traverses visible elements using a light-DOM TreeWalker (`NodeFilter.SHOW_ELEMENT`), skipping `<script>`, `<style>`, `<noscript>`, `<template>`, `<svg>`, and `<iframe>` boundaries.
- **Strict Structural Allowlist**:
  - `ordinal` (integer 1..N)
  - `tag_name` (bounded lowercase string, e.g. `h1`, `span`, `div`, `button`)
  - `role`, `itemprop`, `data-testid`, `data-e2e` (safe alphanumeric atoms)
  - `class_tokens` (up to 4 safe tokens, max 48 chars each)
  - `section_heading_context` (closest visible heading text, clipped to 60 chars)
  - `visible_text` (direct text node content, clipped to 160 chars)
  - `is_leaf` (boolean)
- **Strictly Excluded**:
  - Input and form values (`<input>`, `<textarea>`, `<select>` values are never extracted)
  - Script and stylesheet contents
  - Raw HTML (`innerHTML`, `outerHTML`)
  - Attributes outside the allowlist
  - `href` and URL query strings
  - Event handlers (`onclick`, etc.)
  - Hidden elements and hidden text
  - Account, session, cookie, and credential metadata
- **Explicit Truncation Bounds**:
  - Scanned nodes bound: max 2,000 nodes (`scanned_nodes_truncated`)
  - Persisted records bound: max 500 records (`records_truncated`)
  - Per-text length bound: max 160 characters (`text_truncated`)
  - Serialized byte bound: max 256 KB (`bytes_truncated`)
  - If any bound is reached, `is_truncated: true` is explicitly recorded. Truncation preserves deterministic document order and is never treated as exhaustive coverage.
- **Independent Source Binding**:
  - Verifies observed URL against `https://shop.tiktok.com/vn/pdp/.../1731381331718341815`.
  - Fails closed on `IDENTITY_MISMATCH`, `BLOCKED_OR_CHALLENGE`, `LOGIN_GATE`, and `LISTING_UNAVAILABLE`.

---

## 5. Visual Cross-Check PNG & Human Safety Review

- **External Visual Reference Only**: `p8-real-case-full-page-v1.png` is an external visual cross-check for human verification, not canonical evidence.
- **Human Safety Review Required**: Marked `screenshot_review_status: HUMAN_REVIEW_REQUIRED` in the manifest. Human safety review must check for account names, profile pictures, or private personal data before any future freeze.
- **No Inferred Image Safety**: TASK-263 does not automate image redaction, OCR, or infer screenshot safety.

---

## 6. Epistemic Boundaries & Authority Preservation

- **No Decision or Intelligence Construction**: The carrier never constructs `ProductCandidateSnapshot`, `SignalEvidence`, `TikTokAffiliateEvidenceProfile`, `ValueOfInformationPlan`, `MarketTestEvidenceProfile`, or `CommerceDecisionLoopCase`.
- **No Derived Commerce Fields**: Does not infer discount percent, affiliate eligibility, commission rates, sales velocity, scores, recommendations, rankings, or approval.
- **TASK-262 Historical Immutability**: TASK-262 remains immutable completed history: observed current price `33600.0` and original price `68220.0` remain `OBSERVED_ONLY` at timestamp `2026-09-29T11:50:28.968397+00:00`.
- **Decision State**: Current decision state remains strictly `MARKET_TEST_READINESS_NOT_ESTABLISHED`.
- **Engineering Flags**: `selector_repair_complete: false`, `canonical_evidence_ingested: false`.
- **All Closed Authorities Preserved**:
  - `automated_public_pdp_acquisition_authority: NONE`
  - `market_test_or_action_authority: NONE`
  - `second_invocation_authority: NONE`
  - `arbitrary_target_authority: NONE`
  - `replacement_target_authority: NONE`
  - `search_authority: NONE`
  - `batch_authority: NONE`
  - `inferred_identity_authority: NONE`
  - `variant_switching_authority: NONE`
  - `automatic_live_pilot: false`
  - `automatic_progression: false`

---

## 7. Human Operating Boundary & Non-Consuming Preflight

### Operator Preflight Checklist
Before invoking the carrier, the Human operator must confirm:
1. Operator-owned Chromium browser is running with remote debugging at `127.0.0.1:9222`.
2. Exactly one normal `type=page` target is open and navigated to the exact PDP (`1731381331718341815`).
3. External job root is outside the Git repository.
4. Job root contains none of the three final artifact files (`p8-real-case-manifest-v1.json`, `p8-real-case-page-projection-v1.json`, `p8-real-case-full-page-v1.png`).

### Canonical Command Line
```powershell
python -m src.product_intelligence.cli tiktok-pdp-case-bundle --job-root <external-job-root> --cdp-endpoint http://127.0.0.1:9222
```

### Post-Publication Canonical Handoff
On exact reviewed TASK-263 publication:
- Planning hands off strictly to: `HUMAN_OPERATOR_P8_REAL_CASE_BUNDLE_CAPTURE`
- Followed by mandatory review: `HUMAN_BRAIN_P8_REAL_CASE_BUNDLE_REVIEW`
- `active_track.next_milestone: null`
- `post_p8_planning_handoff.next_milestone: null`
- `pending_commitments: []`
- `post_run_engineering_successor: null`
- `automatic_progression: false`
- No TASK-264 is authored or selected automatically.

---

## 8. Mandatory Governance Invariants

- `BUNDLE_IS_NOT_CANONICAL_EVIDENCE`
- `EVIDENCE_IS_NOT_KNOWLEDGE`
- `EVIDENCE_IS_NOT_PRODUCT_TRUTH`
- `SNAPSHOT_IS_NOT_TREND`
- `CAPABILITY_IS_NOT_AUTHORITY`
- `OPERATION_SUCCESS_IS_NOT_FIELD_VALIDATION_SUCCESS`
- `ONE_CAPABILITY_ONE_AUTHORITY`
