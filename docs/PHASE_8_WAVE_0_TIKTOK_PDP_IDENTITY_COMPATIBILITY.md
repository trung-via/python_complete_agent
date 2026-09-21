# Phase 8 Wave 0 — TikTok PDP Identity Compatibility

Classification: `P8_WAVE_0_TIKTOK_PDP_IDENTITY_COMPATIBILITY_ONLY`

TASK-230 is the Human-selected bounded Wave-0 engineering commitment for
`p8-pilot-001-led-motion-tiktok-vn`. It admits this stable TikTok Shop listing reference:

`https://shop.tiktok.com/vn/pdp/den-led-cam-bien-chuyen-dong-3-che-do-sang-sac-usb-c/1731381331718341815`

The compatibility result is source product ID `1731381331718341815`. The result is path-structural:
the canonical parser accepts a TikTok Shop `/<locale>/pdp/<slug>/<numeric-id>` path, ignores a query
or fragment after that valid path, and fails closed for a missing slug, missing or non-numeric ID,
extra path components, unsupported host/path, or arbitrary numeric text. Existing `/product/<id>`,
`/item/<id>`, supported query-key, direct item-id attribute, and candidate-ID behavior remains intact.

## One parser authority

`src/product_intelligence/adapters/tiktok_parsing.py::extract_tiktok_product_id` is the one
canonical TikTok source-product ID parser authority. Product Intelligence candidate identity and
`TikTokSourceExtractor` both consume it. Product Source retains no private TikTok ID parser.
The extractor's existing exact identity gate, media/fact trust precedence, `source_product_id`, and
deterministic `source_pack_id` semantics are unchanged.

## Capability, not evidence

Parser compatibility is capability, not evidence and not acquisition authority. TASK-230 does not
browse, scrape, call TikTok, establish that the listing exists, or acquire, infer, accept, freeze, or
promote a marketplace observation. `SOURCE_IDENTITY_IS_NOT_CANONICAL_IDENTITY` remains intact.
Product Intelligence remains the canonical owner of candidate/product identity, source evidence,
discovery, ranking, approval, persistence, and product truth.

Public PDP product/source intelligence is semantically independent from TikTok Affiliate account
eligibility and access. Affiliate-only economics—including eligibility, commission rate, and estimated
commission value—are not prerequisites for public PDP parsing or Product Source extraction, and this
compatibility does not establish any Affiliate fact.

## Preserved authorization boundary

P8.3 / TASK-229 remains completed authorization history only:
`MANUAL_WAVE_1_EVIDENCE_CONTRIBUTION_AUTHORIZATION_ONLY`. Its contribution and review remain
unperformed. TASK-230 authorizes no manual evidence acceptance, P7.4/P7.5 construction, Wave 1 or
Wave 2 acquisition, Product Intelligence approval, market test, spend, publication, winner judgment,
or commerce action.

On exact reviewed TASK-230 source publication, the compatibility commitment is DONE only as
parser-authority consolidation. `real_pilot_executed` and `live_evidence_acquired` remain false,
`next_milestone` remains null, and `pending_commitments` remains empty. There is no automatic
successor or P8.4 authorization. `automated_public_pdp_acquisition_authority` is `NONE`, and control
passes to `HUMAN_BRAIN_PUBLIC_PDP_ACQUISITION_AUTHORIZATION` for a fresh Human/Brain decision.
