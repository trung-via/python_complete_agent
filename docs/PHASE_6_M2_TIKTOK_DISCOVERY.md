# Phase 6 M2.2: TikTok Discovery Adapter & Parsing Specification

This document specifies the browser-backed discovery adapter and parsing contracts for **TikTok Shop Product Discovery** in Phase 6 M2.2.

---

## 1. Scope & System Boundary

The TikTok discovery subsystem advances Phase 6 M2 by introducing bounded browser-backed discovery alongside pure deterministic parsing and identity helpers for TikTok Shop search and listing card representations.

- **Deterministic Parsing (TASK-098)**: Pure deterministic parsing, product ID extraction, candidate ID generation, search URL construction, and scalar parsing (`price`, `sold_count`, `rating`, `review_count`, `discount_percent`).
- **Browser-Backed Discovery (TASK-102)**: `TikTokDiscoveryAdapter` implementing the `ProductDiscoveryAdapter` protocol for cheap & wide listing extraction across search result pages.

```text
Marketplace Search Surface (TikTok Shop)
  │
  ▼
TikTokDiscoveryAdapter (Browser-backed bounded listing card extraction)
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

## 2. Discovery Adapter Contract (`src/product_intelligence/adapters/tiktok.py`)

### 2.1 Adapter Lifecycle & Dependencies
- `TikTokDiscoveryAdapter` implements `ProductDiscoveryAdapter` and returns `DiscoveryBatch(platform="tiktok", ...)`.
- Requires an injected browser dependency (`Playwright Browser/BrowserContext`, `BrowserManager`, `BrowserSession`, or async callable) and fails explicitly with `DiscoveryError` if none is provided.
- Properly cleans up owned temporary pages when applicable without creating a secondary browser lifecycle manager.

### 2.2 Bounded Search & Pagination
- Navigates via `build_tiktok_search_url` for every requested page.
- Bounded strictly by `DiscoveryRequest.max_pages` (up to 5) and `DiscoveryRequest.max_candidates` (up to 100).
- Halts immediately when `max_candidates` is reached without continuing unnecessary page navigations.
- Deduplicates candidates across cards and pages by `candidate_id` while preserving first-seen order.

### 2.3 Error & Diagnostic Semantics
- **Anti-bot / Challenge / Captcha**: Raises `DiscoveryBlockedError`.
- **True Empty Search**: When explicit empty-search markers are present on the initial page, returns an empty `DiscoveryBatch` with `TRUE_EMPTY_SEARCH` diagnostic code.
- **Zero Cards Without Marker**: Raises `DiscoveryNavigationError` on page 1 rather than masking failure as an empty search.
- **First-Page Navigation / Evaluation Failure**: Raises fatal `DiscoveryNavigationError`.
- **Later-Page Partial Failure**: Returns partial batch with `PARTIAL_EXTRACTION_PAGE_FAILED` or `PARTIAL_EXTRACTION_EVAL_FAILED` diagnostic code.

---

## 3. Parsing & Identity Contract (`src/product_intelligence/adapters/tiktok_parsing.py`)

### 3.1 Product ID Extraction (`extract_tiktok_product_id`)
Extracts the stable TikTok Shop product/item ID from URL paths, query parameters, or element attributes:
- `/product/<id>` (e.g. `https://www.tiktok.com/view/product/1729482910481234567`)
- `/item/<id>` (e.g. `https://shop.tiktok.com/item/1729482910481234567`)
- `itemId=<id>` (e.g. `https://www.tiktok.com/shop?itemId=1729482910481234567`)
- Direct DOM attributes (e.g. `item_id_attr="1729482910481234567"`)
- Returns `None` when unparseable or missing.

### 3.2 Candidate Identity (`build_tiktok_candidate_id`)
Ensures deterministic, collision-resistant candidate IDs across runs:
- **Primary**: `tiktok_{source_product_id}` when a stable product ID is present.
- **Fallback**: `tiktok_url_{sha256[:16]}` where the URL is normalized by stripping fragments (`#...`) and trailing slashes.
- Strictly avoids Python's process-randomized `hash()`.

### 3.3 Search URL Construction (`build_tiktok_search_url`)
- URL-encodes search queries (`q=<query>`).
- Supports bounded positive 1-indexed pagination (`page >= 1`).
- Fails fast (`ValueError`) on empty queries or non-positive page numbers.

### 3.4 Localized Scalar Parsers
- `parse_tiktok_price`: Extracts lower-bound float price from localized VND/international string representations, handling currency symbols and multipliers (`k`, `tr`, `m`). Returns `None` for malformed, zero, or negative numbers.
- `parse_tiktok_sold_count`: Extracts positive integer sold counts supporting multipliers (`k`, `tr`, `m`). Returns `None` on missing, malformed, zero, or negative counts.
- `parse_tiktok_rating`: Extracts float ratings strictly bounded in $[0.0, 5.0]$.
- `parse_tiktok_review_count`: Extracts positive integer review counts from standalone strings or parenthetical labels.
- `parse_tiktok_discount_percent`: Extracts float discount percentages strictly bounded in $[0.0, 100.0]$.

---

## 4. Guarantees & Constraints

1. **Zero Side Effects**: Discovery does not invoke deep ingestion, media download, Google Drive, scoring, ranking, human review queues, LLMs, or external live network.
2. **Missing-Value Semantics**: Missing, invalid, unpopulated, or explicit `None` optional market metrics and shop attributes evaluate strictly to `None`, never fabricated or coerced to `0` or empty strings.
3. **Compatibility**: Preserves existing Shopee discovery, scoring, and M1 ingestion contracts intact.

