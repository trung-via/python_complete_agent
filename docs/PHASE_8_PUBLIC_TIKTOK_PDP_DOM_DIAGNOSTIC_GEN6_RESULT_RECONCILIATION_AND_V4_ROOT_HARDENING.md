# Phase 8 Public TikTok PDP DOM Diagnostic Generation-6 Result Reconciliation and V4 Root Hardening

## Classification and publication lineage

TASK-246 is `GENERATION_6_RESULT_RECONCILIATION_AND_BOUNDED_TITLE_LOCAL_COMMERCE_ROOT_V4_HARDENING_ONLY`.
It records exact reviewed publication lineage `TASK-245` / `RUN-245-003` / `REVIEW-245-001` /
`12c9a9852a32d8f0e79303803797ebf1e1fa98c2`. Historical implementation and execution provenance
remain distinct: `diagnostic_v3_implementation_source_sha=bc4c48de89129583f024ab622051ea322f9ff5ea`
and `generation_6_execution_source_sha=bc4c48de89129583f024ab622051ea322f9ff5ea`.
Failed intermediate candidates `622a1d2e94ed5c118ebf9855db80b61f7f1b0177` and
`2dc1b67ad52e3c2e844d3499550dd56f734ca49c` remain non-authoritative history.

## Consumed generation-6 result

The sole Human-operated generation-6 invocation is consumed. Its terminal state is
`generation_6_diagnostic_executed=true`, `generation_6_authorized_diagnostic_attempts=1`,
`generation_6_authorized_diagnostic_attempts_remaining=0`, owner `HUMAN_OPERATOR`,
`diagnostic_outcome=FAIL_CLOSED`, `diagnostic_failure_reason=NO_BOUNDED_PDP_ROOT`, artifact created,
and `live_dom_diagnostic_authority=NONE`. In accordance with policy, no unobserved process exit code
is invented or asserted because the Human-operated terminal transcript did not establish an exact exit-code observation.

The immutable external generation-6 artifact is schema version 3, filename
`tiktok-pdp-dom-diagnostic-v3.json`, SHA256
`A5CD014DD2A9B10DD969843BA37369815A9595248DFB5DD29355376B51143764`, size `27549` bytes,
observed at `2026-09-23T13:14:40.397608+00:00`, with `evidence_authority=NONE`.

Its exact global root probe is: `title_anchor_count=1`, `price_anchor_count=0`,
`action_anchor_count=0`, `visible_explicit_pdp_root_count=0`,
`explicit_root_with_commerce_anchors_count=0`, `main_present=false`, `main_visible=false`,
`main_has_commerce_anchors=false`, `multi_anchor_common_ancestor_found=false`, and
`selected_root_kind=NONE`.

Its bounded title-local topology probe demonstrates:
- Ancestor level 1: 32 nodes scanned, untruncated, 3 currency-like signals, 0 commerce-semantic actions, 0 native/role controls.
- Ancestor level 2: 84 nodes scanned, untruncated, 3 currency-like signals, 2 commerce-semantic actions, 2 native/role controls, 14 pointer-only interactions.
- Ancestor level 3: 85 nodes scanned, untruncated, with materially identical commerce topology.
- Ancestor levels 4–6: truncated at 300 nodes, rendering negative observations non-exhaustive.

These observations provide engineering diagnostic context justifying bounded root-selection fallback
hardening, but they do not constitute canonical Product Truth or pre-select a root.

## Active V4 diagnostic contract

The active contract advances to schema version 4 and create-exclusive
`tiktok-pdp-dom-diagnostic-v4.json`; historical V1, V2, and V3 artifacts and their provenance remain immutable.
`evidence_authority` remains `NONE`. Existing `rootSelector`, `titleSelectors`, `priceSelectors`, and
`actionSelectors` are preserved byte-for-byte in semantic meaning. TASK-246 is root-selection hardening,
not selector repair; `selector_repair_complete` remains `false`.

Existing root-selection precedence is preserved exactly:
1. `EXPLICIT_PDP_ROOT`
2. `MAIN`
3. `MULTI_ANCHOR_COMMON_ANCESTOR`
4. `TITLE_LOCAL_COMMERCE_QUORUM` (fallback added in V4)

The title-local commerce-quorum fallback evaluates candidate ancestor levels in strict ascending order
from narrowest (level 1) to widest (level 6) starting from the unique visible title anchor (`title_anchor_count == 1`).
A candidate ancestor subtree qualifies only if:
- `bounded_scan_truncated` is `false`. If a narrower unresolved ancestor is truncated before a qualifying ancestor is found, fallback selection fails closed immediately and must not skip the unresolved subtree to select a wider ancestor.
- It contains at least one visible currency-like structural signal (`currency_like_count >= 1`).
- It contains at least one strong commerce semantic action (`BUY_LIKE` or `CART_LIKE`) that structurally pairs to a visible button (`button` or `role="button"`) within the candidate ancestor subtree.
- Supporting hints such as `QUANTITY_LIKE` and `VARIANT_LIKE` and pointer-only interactions cannot satisfy root quorum.
- Paired strong controls are deduplicated before counting.

When qualified, the algorithm deterministically selects the narrowest qualifying untruncated ancestor.
The selected result records `selected_title_local_ancestor_level` (1..6) and `selected_root_kind="TITLE_LOCAL_COMMERCE_QUORUM"`.
V4 title-local records add `strong_commerce_action_like_count`, `paired_strong_commerce_control_count`, and
`title_local_root_quorum_satisfied`. All output remains strictly sanitized—no raw marketplace scalar, price, button text,
HTML, href, aria-label, token, or arbitrary page content is persisted.

Selection of a root indicates only that the bounded diagnostic root contract is satisfied; it does not prove canonical
price, action capability, product truth, acquisition success, ranking evidence, approval, recommendation, or market action.

The carrier preserves exactly one borrowed session, exactly one `session.evaluate(DIAGNOSTIC_SCRIPT)`, zero
navigation/refresh/click/type/scroll, TASK-137 browser lifecycle authority and cleanup, light-DOM-only traversal,
no shadow-root traversal, and no iframe-document traversal. Safe failure taxonomy and create-exclusive artifact
behavior are preserved; `NO_BOUNDED_PDP_ROOT` remains fail-closed and persists the V4 diagnostic artifact before re-raising.

## Authority closure

Generations 1 through 6 are historical. `root_observability_hardening_implemented=true`,
`commerce_observability_hardening_implemented=true`, and `diagnostic_hardening_implemented=true`;
`selector_repair_complete=false`. `live_dom_diagnostic_authority`, `live_public_pdp_acquisition_authority`,
`automated_public_pdp_acquisition_authority`, and `market_test_or_action_authority` remain `NONE`.
`generation_6_authorized=false` and `generation_7_authorized=false`.
`automatic_progression=false`, `active_track.next_milestone=null`, pending commitments are empty,
and `post_run_engineering_successor=null`.

The only post-publication planning handoff is
`HUMAN_BRAIN_FRESH_GENERATION_7_BOUNDED_TITLE_LOCAL_COMMERCE_ROOT_DIAGNOSTIC_AUTHORIZATION`.
TASK-246 performs no live TikTok/CDP execution and authorizes no generation 7 attempt.

`CAPABILITY_IS_NOT_AUTHORITY`, `EVIDENCE_IS_NOT_PRODUCT_TRUTH`,
`SOURCE_IDENTITY_IS_NOT_CANONICAL_IDENTITY`, `SNAPSHOT_IS_NOT_TREND`, and
`ONE_CAPABILITY_ONE_AUTHORITY` remain mandatory.
