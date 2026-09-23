# Phase 8 Public TikTok PDP DOM Diagnostic Generation-6 Authorization

## Decision and exact publication lineage

TASK-245 is classified exactly as
`FRESH_GENERATION_6_TITLE_LOCAL_COMMERCE_OBSERVABILITY_DIAGNOSTIC_AUTHORIZATION_ONLY`. It records
`source_task_id=TASK-244`, `source_run_id=RUN-244-002`,
`source_review_id=REVIEW-244-001`, and
`source_published_sha=bc4c48de89129583f024ab622051ea322f9ff5ea`. The exact reviewed and published
source candidate `bc4c48de89129583f024ab622051ea322f9ff5ea` is canonicalized as both the V3
implementation source (`diagnostic_v3_implementation_source_sha=bc4c48de89129583f024ab622051ea322f9ff5ea`)
and the generation-6 execution source
(`generation_6_execution_source_sha=bc4c48de89129583f024ab622051ea322f9ff5ea`). The failed
pre-repair candidate `ce9f50bc8344988181b3520eccc189ef51a38b13` is historical failed-run lineage only
and is not generation-6 implementation or execution authority.

The historical TASK-240 V2 implementation provenance remains unchanged as
`diagnostic_v2_implementation_source_sha=8ef61df3936652fb7aeda8ca31ce1db3621ff4cf`, and historical
TASK-242 generation-5 execution provenance remains
`generation_5_execution_source_sha=d113c4a7ce2e2835d532935bc195c922aa3628ca`.

This authorization changes no production diagnostic, parser, CLI, browser, collector, Product
Intelligence, evidence, ranking, approval, test, or action code. It becomes effective only when the
exact reviewed TASK-245 candidate is published.

## Immutable consumed generations 1-5

Generations 1-4 remain their existing consumed historical records. Generation 5 remains
`generation_5_diagnostic_executed=true`, `generation_5_authorized_diagnostic_attempts=1`,
`generation_5_authorized_diagnostic_attempts_remaining=0`, owner `HUMAN_OPERATOR`,
`diagnostic_outcome=FAIL_CLOSED`, `diagnostic_failure_reason=NO_BOUNDED_PDP_ROOT`, process exit code 1,
`diagnostic_artifact_created=true`, and `live_dom_diagnostic_authority=NONE`.

The exact generation-5 V2 artifact remains immutable: schema version 2, filename
`tiktok-pdp-dom-diagnostic-v2.json`, SHA256
`03CB57F0BA9838985233C919E144416416E1A17DD2DA033F8B5F8A3FE224EA1F`, size 6130 bytes,
observed at `2026-09-22T23:00:39.526520+00:00`, with `evidence_authority=NONE`.

Its exact root probe is: `title_anchor_count=1`, `price_anchor_count=0`, `action_anchor_count=0`,
`visible_explicit_pdp_root_count=0`, `explicit_root_with_commerce_anchors_count=0`,
`main_present=false`, `main_visible=false`, `main_has_commerce_anchors=false`,
`multi_anchor_common_ancestor_found=false`, and `selected_root_kind=NONE`.

Its exact commerce summary is: `document_ready_state=COMPLETE`, `bounded_nodes_scanned=600`,
`bounded_scan_truncated=true`, `visible_currency_like_count=0`,
`near_title_currency_like_count=0`, `visible_interactive_count=106`,
`near_title_action_like_count=91`, `visible_loading_marker_count=0`,
`open_shadow_root_count=0`, and `visible_iframe_count=0`.

The price and action anchor counts are full-`document.body` current-selector queries. Their zero
results are selector-family misses and are not caused by the separate 600-node TreeWalker cap. The
global currency-like zero is non-exhaustive because that global scan was truncated. The legacy
near-title action count of 91 is a broad V2 ancestor-containment heuristic, not evidence of 91
commerce controls and not authority to broaden action selectors. Generation 6 is not a retry or
reinterpretation of generation 5.

## Exact generation-6 authority

Only exact reviewed TASK-245 publication sets:

- `diagnostic_authorization_generation=6`
- `live_dom_diagnostic_authority=ONE_SHOT_ATTACH_ONLY_EXACT_LISTING`
- `generation_6_authorized=true`
- `generation_6_authorized_diagnostic_attempts=1`
- `generation_6_authorized_diagnostic_attempts_remaining=1`
- `generation_6_diagnostic_execution_owner=HUMAN_OPERATOR`
- `generation_6_diagnostic_executed=false`

The attempt is bound only to context `p8-pilot-001-led-motion-tiktok-vn`, source ID
`1731381331718341815`, and exact selected listing
`https://shop.tiktok.com/vn/pdp/den-led-cam-bien-chuyen-dong-3-che-do-sang-sac-usb-c/1731381331718341815`.
It grants no arbitrary, replacement, inferred-identity, search, batch, acquisition,
variant-switching, selector-repair, market-test, or commerce-action authority.

The only authorized carrier is `src/product_intelligence/tiktok_pdp_dom_diagnostic.py`,
content-equivalent to `generation_6_execution_source_sha`. The active contract is `schema_version=3`,
exact create-exclusive filename `tiktok-pdp-dom-diagnostic-v3.json`, and `evidence_authority=NONE`.
The canonical CLI subcommand is `tiktok-pdp-dom-diagnostic`. The carrier borrows one session, performs
exactly one `session.evaluate(DIAGNOSTIC_SCRIPT)`, performs zero navigation, refresh, click, type, or
scroll, and retains TASK-137 manager-mediated cleanup. Light-DOM traversal only is enforced, with no
shadow root or iframe traversal.

## Non-consuming preflight

Preflight is separate from invocation, must not invoke the diagnostic carrier, and does not consume
the attempt. It may only establish all of the following:

1. CDP `127.0.0.1:9222` is reachable.
2. Read-only browser target enumeration reports exactly one normal `type=page` target in total, and that
   sole target is the exact selected PDP for source ID `1731381331718341815`.
3. A fresh explicit external generation-6 job root contains none of
   `tiktok-pdp-dom-diagnostic-v1.json`, `tiktok-pdp-dom-diagnostic-v2.json`, or
   `tiktok-pdp-dom-diagnostic-v3.json`.
4. All five execution-critical files are content-equivalent to the exact TASK-244 publication at
   `bc4c48de89129583f024ab622051ea322f9ff5ea`:
   - `src/product_intelligence/tiktok_pdp_dom_diagnostic.py`
   - `src/product_intelligence/cli.py`
   - `src/product_intelligence/adapters/tiktok_parsing.py`
   - `src/integrations/playwright/manager.py`
   - `src/integrations/playwright/session.py`

Repository HEAD equality is not required. Preflight does not invoke the carrier and does not consume
the attempt. This target-unambiguity gate preserves TASK-137 as the sole browser/CDP lifecycle and
page-borrowing authority; it creates no second page-selection owner.

## One-line transport and consuming invocation

The Human-facing invocation must be entered as exactly one physical PowerShell line, with no backtick
or multiline continuation:

```powershell
python -m src.product_intelligence.cli tiktok-pdp-dom-diagnostic --job-root <fresh-external-generation-6-job-root> --cdp-endpoint http://127.0.0.1:9222
```

A shell or PowerShell parser/transport failure before a valid `tiktok-pdp-dom-diagnostic` subcommand
dispatches into the carrier is a transport failure and does not by itself consume the attempt. Once
valid carrier invocation begins, every terminal outcome consumes the only generation-6 attempt:
`SUCCESS`, `NO_BOUNDED_PDP_ROOT`, `BLOCKED_OR_CHALLENGE`, `LOGIN_GATE`, `LISTING_UNAVAILABLE`,
`IDENTITY_MISMATCH`, `MALFORMED_DIAGNOSTIC_PAYLOAD`, evaluation/session failure, or any other terminal
outcome. There is no retry, refresh, resume, second invocation, or replacement target.

`SUCCESS` may create the bounded V3 artifact. `NO_BOUNDED_PDP_ROOT` retains the create-exclusive V3
`FAIL_CLOSED` artifact contract. Other safe failures may remain artifact-free under the published
carrier. Every artifact retains `evidence_authority=NONE`.

## Interpretation and handoff

The V3 `title_local_topology_probe` derives observations from the exact title anchor for at most six
light-DOM ancestor levels, each independently hard-bounded to at most 300 descendant element observations.
It reports counts for current price-selector matches, current action-selector matches, visible
currency-like hints, commerce-semantic action hints, generic native/role controls, pointer-only
interactions, visible loading markers, open-shadow-root boundaries, and visible-iframe boundaries, along
with bounded sanitized structural candidate samples.

All V3 topology and candidate observations remain engineering-diagnostic-only. Local selector matches
mean only that the current selector family matched elements inside that bounded local subtree and do not
prove canonical price or action controls. The `commerce_semantic_action_like_count` is a bounded
BUY/CART/VARIANT/QUANTITY-like heuristic and does not prove that a control performs a commerce action.
Pointer-only interaction counts must never be promoted to commerce-semantic evidence. For any ancestor
whose `bounded_scan_truncated` is true, negative local counts are non-exhaustive. No V3 observation
selects or recommends a root or selector, repairs selectors, or grants Product Truth, ranking, approval,
acquisition, or action authority.

`root_observability_hardening_implemented=true` and `commerce_observability_hardening_implemented=true`
remain true. `selector_repair_complete=false`, `live_public_pdp_acquisition_authority=NONE`,
`automated_public_pdp_acquisition_authority=NONE`, `market_test_or_action_authority=NONE`, and
`automatic_progression=false`. `active_track.next_milestone` remains null and pending commitments remain
empty.

The exact current global handoff is
`HUMAN_OPERATOR_GENERATION_6_TITLE_LOCAL_COMMERCE_OBSERVABILITY_DIAGNOSTIC_EXECUTION`. After the single
Human-operated attempt terminates, review authority returns to
`HUMAN_BRAIN_GENERATION_6_TITLE_LOCAL_COMMERCE_OBSERVABILITY_DIAGNOSTIC_REVIEW`. TASK-245 selects no
engineering repair and authorizes no automatic progression. `CAPABILITY_IS_NOT_AUTHORITY`,
`EVIDENCE_IS_NOT_PRODUCT_TRUTH`, `SOURCE_IDENTITY_IS_NOT_CANONICAL_IDENTITY`, `SNAPSHOT_IS_NOT_TREND`,
and `ONE_CAPABILITY_ONE_AUTHORITY` remain mandatory.
