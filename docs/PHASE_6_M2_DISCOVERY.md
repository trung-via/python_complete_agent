# Phase 6 M2.2: Product Intelligence Discovery & Shopee Adapter V1

## 1. Architectural Philosophy: Cheap & Wide vs. Expensive & Narrow

Product Intelligence discovery introduces a clear architectural boundary between candidate collection and deep ingestion:

```text
Marketplace Search/Discovery Surface (e.g. Shopee)
  │
  ▼
ShopeeDiscoveryAdapter (Cheap & Wide: Bounded cards extraction)
  │
  ▼
ProductCandidateSnapshot[] (Canonical M2.1 data contract)
  │
  ▼
Phase 6 M2.3 Normalizer & Scorer (Score, rank, shortlist)
  │
  ▼
Phase 6 M2.4 Human-Approved Queue Handoff (Operator review)
  │
  ▼
Phase 5/6 Deep Ingestion (Expensive & Narrow: detail page, image download, GDrive, video)
```

| Dimension | Discovery (M2.2) | Ingestion (Phase 5/6 M1) |
| :--- | :--- | :--- |
| **Scope** | **Wide & Bounded** (e.g. 20–100 candidates per query) | **Narrow & Deep** (1 product detail page at a time) |
| **Cost** | **Cheap** (Listing card DOM parsing only) | **Expensive** (Images, video, watermark, Drive storage) |
| **Network I/O** | 1–5 search result pages | Full detail page, high-res CDN assets, Drive API |
| **Side Effects** | **Zero** (no Drive uploads, no queue writes, no DB mutation) | Drive uploads, image processing, task status updates |
| **LLM Inference** | **Zero** | Content generation, video scripting, classification |

---

## 2. Discovery Contracts (`src/product_intelligence/discovery.py`)

### 2.1 `DiscoveryRequest`
An immutable, validated request to discover candidate products from a search surface:
- `query: str`: Search query string (must be non-empty after trimming).
- `max_candidates: int`: Maximum unique candidates to return (bounded in $[1, 100]$, default `50`).
- `max_pages: int`: Maximum search pagination depth (bounded in $[1, 5]$, default `1`).
- `locale: str`: Regional marketplace locale (default `"vi-VN"`).

### 2.2 `DiscoveryBatch`
An immutable result containing discovered candidate snapshots and structured diagnostics:
- `platform: str`: Platform identifier (`"shopee"`).
- `query: str`: Executed search query.
- `observed_at: datetime`: Point in time of discovery execution.
- `candidates: Tuple[ProductCandidateSnapshot, ...]`: Deduplicated product snapshots.
- `pages_examined: int`: Actual number of pages navigated and inspected.
- `raw_items_seen: int`: Total raw cards seen across all pages.
- `diagnostic_codes: Tuple[str, ...]`: Deterministic execution codes (e.g. `DISCOVERY_SUCCESS`, `TRUE_EMPTY_SEARCH`, `PARTIAL_EXTRACTION_PAGE_FAILED`).
- `to_dict()`: Clean dictionary serialization containing strictly no raw HTML, cookies, tokens, or credentials.

### 2.3 `ProductDiscoveryAdapter` Protocol
```python
@runtime_checkable
class ProductDiscoveryAdapter(Protocol):
    async def discover(
        self,
        request: DiscoveryRequest,
        *,
        observed_at: Optional[datetime] = None,
    ) -> DiscoveryBatch: ...
```

---

## 3. Shopee Discovery Adapter (`ShopeeDiscoveryAdapter`)

### 3.1 Field Availability & Extraction Boundary
The Shopee discovery adapter inspects search result listing cards only. It never navigates into individual product detail pages during discovery.

| Field | Availability on Search Card | Snapshot Status |
| :--- | :--- | :--- |
| `platform` | Known | `"shopee"` |
| `url` | Visible on card link | Full canonical URL |
| `title` | Visible on card | Extracted text |
| `source_product_id` | Present in link (`-i.{shop_id}.{item_id}`) or data attribute | Extracted item ID |
| `price` | Visible on card | Parsed VND float |
| `original_price` | Visible on card if discounted | Parsed VND float (or `None`) |
| `discount_percent` | Visible badge (e.g. `-25%`) | Parsed float $[0.0, 100.0]$ (or `None`) |
| `sold_count` | Visible on card (e.g. `Đã bán 1.2k`) | Parsed integer count (or `None`) |
| `rating` | Visible star rating (e.g. `4.8`) | Parsed float $[0.0, 5.0]$ (or `None`) |
| `review_count` | Visible in parentheses | Parsed integer count (or `None`) |
| `shop_name` | Visible on card | Extracted string (or `None`) |
| `observed_at` | Discovery timestamp | UTC datetime |
| `collector` | Adapter version | `"shopee_discovery_v1"` |
| `affiliate_commission_rate` | **Not visible on search card** | `None` (Never fabricated) |
| `estimated_commission_value` | **Not visible on search card** | `None` (Never fabricated) |
| `creator_count` | **Not visible on search card** | `None` (Never fabricated) |
| `video_count` | **Not visible on search card** | `None` (Never fabricated) |
| `similar_listing_count` | **Not visible on search card** | `None` (Never fabricated) |
| `sales_velocity` | **Not visible on single observation** | `None` (Never fabricated) |
| `review_velocity` | **Not visible on single observation** | `None` (Never fabricated) |
| `creator_velocity` | **Not visible on single observation** | `None` (Never fabricated) |
| `video_velocity` | **Not visible on single observation** | `None` (Never fabricated) |

### 3.2 Candidate Identity & Deduplication
- **Identity Rule**:
  - When `source_product_id` (item ID) is extracted: `candidate_id = f"shopee_{source_product_id}"`.
  - Fallback: SHA-256 digest of clean URL: `candidate_id = f"shopee_url_{digest[:16]}"`.
  - Never uses process-randomized `hash()`.
- **Deduplication Rule**:
  - Duplicate cards for the same listing across cards or pages are collapsed into a single candidate.
  - First-seen order and first-seen metadata are preserved.

### 3.3 Parsing Semantics & Missing-Value Policy
- Parsing helpers in `src/product_intelligence/adapters/shopee_parsing.py` are pure, deterministic functions.
- Multiplier suffixes (`k`, `K`, `tr`, `triệu`) and Vietnamese decimal/thousand conventions are supported.
- Malformed, unparseable, or out-of-range strings evaluate strictly to `None`, never converted to `0` or negative numbers.
- A malformed field in one listing card does not discard valid sibling cards or abort the discovery batch.

### 3.4 Failure & Anti-Bot Block Semantics
- **Invalid Request**: Fails immediately (`DiscoveryInvalidRequestError`) before invoking the browser.
- **Missing Dependency**: Raises `DiscoveryError` if browser dependency is `None`.
- **First Page Navigation Failure**: Raises `DiscoveryNavigationError` fail-closed (never returns a fake successful empty search).
- **Anti-Bot / Captcha Challenge**: Detects security verification indicators (`.shopee-captcha`, `#challenge-running`, `"Please verify you are human"`) and raises `DiscoveryBlockedError` with `BLOCKED_PAGE_DETECTED`.
- **True Empty Search**: Successfully parsed page container with zero matching cards emits diagnostic `TRUE_EMPTY_SEARCH` and returns an empty candidate list.
- **Subsequent Page Failure**: If page 1 succeeds but page 2 fails, returns the partial batch with diagnostic `PARTIAL_EXTRACTION_PAGE_FAILED`.

---

## 4. Isolation & Resilience Guarantees

- **Scorer Purity**: Discovery produces `ProductCandidateSnapshot` instances without executing scoring, LLM generation, or ranking.
- **DOM Isolation**: Platform DOM extraction rules reside strictly in `src/product_intelligence/adapters/shopee.py` and `shopee_parsing.py`. Any future marketplace DOM changes are isolated to this adapter without contaminating the M2.1 scoring engine.
- **Zero Drive / Queue Side Effects**: Discovery does not download media, does not upload to Google Drive, and does not append items to `tasks.txt`.
