# Phase 6 M2.2: TikTok Discovery Parsing & Contract Specification

This document specifies the parsing and identity contracts for **TikTok Shop Product Discovery** in Phase 6 M2.2.

---

## 1. Scope & System Boundary

The TikTok discovery subsystem advances Phase 6 M2 by introducing pure deterministic parsing and identity helpers for TikTok Shop search and listing card representations.

- **Current Step (TASK-098)**: Pure deterministic parsing, product ID extraction, candidate ID generation, search URL construction, and scalar parsing (`price`, `sold_count`, `rating`, `review_count`, `discount_percent`).
- **Next Step**: Browser-backed `TikTokDiscoveryAdapter` implementing the `ProductDiscoveryAdapter` protocol for cheap & wide listing extraction across search result pages.

```text
Marketplace Search Surface (TikTok Shop)
  │
  ▼
TikTokDiscoveryAdapter (Next Step: Browser-backed listing card extraction)
  │
  ├─► Uses pure parsing helpers (src/product_intelligence/adapters/tiktok_parsing.py)
  │
  ▼
ProductCandidateSnapshot[] (Canonical M2.1 data contract)
  │
  ▼
WinningProductScorer / Ranker / Human Review / M1 Ingestion Queue
```

---

## 2. Parsing & Identity Contract (`src/product_intelligence/adapters/tiktok_parsing.py`)

### 2.1 Product ID Extraction (`extract_tiktok_product_id`)
Extracts the stable TikTok Shop product/item ID from URL paths, query parameters, or element attributes:
- `/product/<id>` (e.g. `https://www.tiktok.com/view/product/1729482910481234567`)
- `/item/<id>` (e.g. `https://shop.tiktok.com/item/1729482910481234567`)
- `itemId=<id>` (e.g. `https://www.tiktok.com/shop?itemId=1729482910481234567`)
- Direct DOM attributes (e.g. `item_id_attr="1729482910481234567"`)
- Returns `None` when unparseable or missing.

### 2.2 Candidate Identity (`build_tiktok_candidate_id`)
Ensures deterministic, collision-resistant candidate IDs across runs:
- **Primary**: `tiktok_{source_product_id}` when a stable product ID is present.
- **Fallback**: `tiktok_url_{sha256[:16]}` where the URL is normalized by stripping fragments (`#...`) and query parameters (`?...`).
- Strictly avoids Python's process-randomized `hash()`.

### 2.3 Search URL Construction (`build_tiktok_search_url`)
- URL-encodes search queries (`q=<query>`).
- Supports bounded positive 1-indexed pagination (`page >= 1`).
- Fails fast (`ValueError`) on empty queries or non-positive page numbers.

### 2.4 Localized Scalar Parsers
- `parse_tiktok_price`: Extracts lower-bound float price from localized VND/international string representations, handling currency symbols and multipliers (`k`, `tr`, `m`). Returns `None` for malformed, zero, or negative numbers.
- `parse_tiktok_sold_count`: Extracts positive integer sold counts supporting multipliers (`k`, `tr`, `m`). Returns `None` on missing, malformed, zero, or negative counts.
- `parse_tiktok_rating`: Extracts float ratings strictly bounded in $[0.0, 5.0]$.
- `parse_tiktok_review_count`: Extracts positive integer review counts from standalone strings or parenthetical labels.
- `parse_tiktok_discount_percent`: Extracts float discount percentages strictly bounded in $[0.0, 100.0]$.

---

## 3. Guarantees & Constraints

1. **Zero Side Effects**: Parsing helpers have zero filesystem, network, browser, queue, Google Drive, LLM, or wall-clock dependencies.
2. **Missing-Value Semantics**: Missing, invalid, or out-of-range market metrics evaluate strictly to `None`, never fabricated or coerced to `0`.
3. **Compatibility**: Does not alter Shopee discovery or existing Phase 6 scoring contracts.
