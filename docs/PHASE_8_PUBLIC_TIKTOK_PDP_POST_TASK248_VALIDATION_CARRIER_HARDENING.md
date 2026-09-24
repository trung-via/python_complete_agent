# Phase 8 Public TikTok PDP Post-TASK248 Validation Carrier Hardening

## 1. Executive Summary & Purpose

TASK-249 revision 2 hardens only the existing Human-operated carrier (`src/product_intelligence/tiktok_pdp_live_pilot.py`) so that a later, separately authorized post-TASK248 one-shot collector validation has:
- Durable attempt-consumption lineage via a two-phase V2 artifact contract,
- Exact engineering provenance bound to the reviewed and published TASK-248 collector baseline,
- Bounded terminal evidence persisted for both clean success and fail-closed outcomes,
- Unambiguous process and power interruption visibility,
- Guaranteed secret-safe and credential-free external artifacts, and
- Unchanged CLI non-zero exit behavior for all fail-closed operations.

TASK-249 performs zero live network or CDP operations and grants zero live validation attempts (`authorized_validation_attempts: 0`, `authorized_validation_attempts_remaining: 0`). Control returns to `HUMAN_BRAIN_LIVE_PUBLIC_PDP_PILOT_AUTHORIZATION` for a separate later decision.

---

## 2. Exact TASK-248 Baseline Provenance

The collector validation baseline is strictly pinned to the published TASK-248 implementation:
- **Baseline Task ID**: `TASK-248`
- **Baseline Source Commit SHA**: `39979020a10b78e1f86c30cf2b704f2f975daec9`
- **Baseline Scope**: `TikTokPdpCollector` in `src/product_intelligence/adapters/tiktok_pdp.py` with bounded root-scoped price extraction consuming `src/product_intelligence/tiktok_pdp_dom_scope.py`.

This provenance is implementation lineage only. It does not cite or depend on generation-7 live diagnostic values (such as ancestor levels, node counts, class names, or observed HTML tokens) as runtime facts, selectors, expected results, or Product Truth.

---

## 3. Two-Phase V2 Artifact Contract & Fixed Filenames

The carrier introduces a V2 external validation-artifact contract with exactly two fixed filenames:
1. `tiktok-pdp-live-validation-attempt-v2.json` — Durable validation attempt marker.
2. `tiktok-pdp-live-validation-result-v2.json` — Terminal validation result.

Both files are create-exclusive (`open("x")`), reside in an explicit external directory outside the Git repository, and exclude all sensitive data.

A job root containing either V2 artifact or the legacy `tiktok-pdp-live-pilot-result-v1.json` fails immediately during preflight so that a single job root cannot mix legacy and hardened attempt lineage.

---

## 4. Local Non-Consuming Pre-Marker Gates

All validation of environment, arguments, and boundaries executes strictly before the durable attempt marker is created:
1. **Explicit External Job Root**: The job root must be a non-empty path, resolved, and verified to be strictly outside the Git repository.
2. **Artifact Pre-Existence Check**: Neither `tiktok-pdp-live-pilot-result-v1.json`, `tiktok-pdp-live-validation-attempt-v2.json`, nor `tiktok-pdp-live-validation-result-v2.json` may exist in the job root.
3. **CDP Endpoint Input**: The operator-owned `--cdp-endpoint` must be a non-empty, non-whitespace string.
4. **Timezone-Aware Timestamp**: The operation start timestamp (`started_at`) obtained from the clock must be timezone-aware.

If any of these gates fails, no marker is created, and no browser or collector interaction occurs.

---

## 5. Durable Attempt Marker & Consumption Boundary

Successful create-exclusive persistence of `tiktok-pdp-live-validation-attempt-v2.json` is the carrier's durable consumption boundary for any later separately authorized execution.
- **Marker Absence**: The carrier has not crossed its consuming boundary.
- **Marker Presence**: The attempt has crossed the boundary, even if the process was interrupted immediately after marker creation.

The attempt marker contains only a bounded allowlist:
- `schema_version`: `2`
- `record_type`: `"VALIDATION_ATTEMPT_MARKER"`
- `contract_identifier`: `"POST_TASK248_LIVE_PUBLIC_PDP_COLLECTOR_VALIDATION"`
- `context_id`: `"p8-pilot-001-led-motion-tiktok-vn"`
- `source_product_id`: `"1731381331718341815"`
- `requested_url`: Authorized TikTok Shop Vietnam listing URL
- `started_at`: ISO 8601 UTC timestamp
- `execution_owner`: `"HUMAN_OPERATOR"`
- `review_status`: `"HUMAN_REVIEW_REQUIRED"`
- `collector_baseline_task_id`: `"TASK-248"`
- `collector_baseline_source_sha`: `"39979020a10b78e1f86c30cf2b704f2f975daec9"`

The carrier never deletes, overwrites, truncates, or silently replaces the marker.

---

## 6. Terminal Execution Sequencing & Status Separation

Following marker persistence, terminal sequencing executes in strict order:
1. Attempt borrowing the browser session via `manager.get_or_create_session(_SESSION_RUN_ID)`.
2. Invoke `collector.collect(AUTHORIZED_PDP_URL, observed_at=observed_at)` at most once.
3. If a collector result was returned, revalidate the exact-listing binding (platform == "tiktok", source ID, observed URL, identity bases).
4. Attempt session release via `await manager.close_session(_SESSION_RUN_ID)` in a guaranteed `finally` block if a session was acquired.
5. Only after the cleanup outcome is determined, derive the final operation and observation statuses.
6. Make at most one create-exclusive write to `tiktok-pdp-live-validation-result-v2.json`.

### Status Taxonomy:
- **`operation_status`**: `"SUCCESS"` or `"FAIL_CLOSED"`
- **`observation_status`**: `"OBSERVED"` or `"NOT_OBSERVED"`
- **`session_release_status`**: `"SUCCESS"`, `"FAILED"`, or `"NOT_APPLICABLE"`

Clean success requires all three: admitted exact-listing observation, valid binding revalidation, and successful session release (`SUCCESS` / `OBSERVED` / `SUCCESS`).

A valid admitted observation followed by cleanup failure produces `FAIL_CLOSED` / `OBSERVED` / `FAILED` with `failure_reason: "SESSION_RELEASE_FAILED"`, preserving both the snapshot and binding receipt for Human/Brain review.

---

## 7. Canonical Collector-Code Reuse & Failure Taxonomy

For failures originating from `TikTokPdpCollectionError`, the carrier directly reuses `exc.code.value` without inspecting or parsing the exception message text:
- `BLOCKED_OR_LOGIN`
- `IDENTITY_MISMATCH_OR_UNVERIFIABLE`
- `EXTRACTION_FAILURE`

Carrier-local failure classifications are restricted to:
- `BROWSER_SESSION_UNAVAILABLE` (session acquisition failed; cleanup `NOT_APPLICABLE`)
- `RESULT_BINDING_MISMATCH` (collector result violated exact listing binding)
- `SESSION_RELEASE_FAILED` (clean collection but session release failed)
- `UNCLASSIFIED_OPERATION_FAILURE` (unexpected collector exception)

When cleanup fails after a primary collector failure, the primary failure code is preserved and `session_release_status` is recorded as `FAILED`.

---

## 8. CLI Fail-Closed Non-Zero Behavior & Post-Persistence Semantics

The Human-facing CLI command surface (`src/product_intelligence/cli.py`) remains unmodified:
- Only clean `SUCCESS` returns `TikTokPdpLivePilotOutcome`, causing the CLI to output JSON to `stdout` and exit `0`.
- Every terminal `FAIL_CLOSED` outcome whose result artifact is successfully persisted raises a bounded `TikTokPdpLivePilotError(failure_reason)` after persistence.
- The CLI catches this exception, prints the sanitized failure code to `stderr`, and exits `1`.

This preserves non-zero application process semantics for failed operations while ensuring durable external evidence is safely recorded on disk.

If result artifact persistence fails (`open("x")` error), the marker is left intact, and the carrier raises `TikTokPdpLivePilotError("TERMINAL_ARTIFACT_WRITE_FAILED")`.

---

## 9. Interruption Interpretation

An attempt marker existing in a job root without a complete, conforming terminal result indicates that execution was interrupted by process termination, power loss, or artifact write failure.

In all such cases:
- State is interpreted as `CONSUMED_INTERRUPTED_OR_UNOBSERVED`.
- The attempt remains consumed.
- No automatic retry, refresh, resume, or replacement is permitted.
- The disposition is submitted to Human/Brain governance.

---

## 10. Secret Exclusion & Safety Bounds

Under no circumstances do external artifacts contain:
- CDP WebSocket endpoints or URLs containing tokens,
- Cookies, authorization headers, or session tokens,
- Operator credentials or account data,
- Raw HTML, full DOM trees, or screenshots,
- Local machine absolute repository paths.

Carrier exceptions identify only sanitized fixed reason codes and never echo operator endpoint strings or raw exception messages.

---

## 11. Zero Live Authority & Governance Handoff

TASK-249 is strictly an engineering hardening milestone:
- `live_public_pdp_acquisition_authority: NONE`
- `automated_public_pdp_acquisition_authority: NONE`
- `market_test_or_action_authority: NONE`
- `authorized_validation_attempts: 0`
- `authorized_validation_attempts_remaining: 0`
- `automatic_live_pilot: false`
- `automatic_progression: false`

On reviewed publication, TASK-249 becomes the sole active track milestone while TASK-248 becomes historical. Control returns to `HUMAN_BRAIN_LIVE_PUBLIC_PDP_PILOT_AUTHORIZATION`.
