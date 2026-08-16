# Phase 6 M2.2A — Product Source Pack & Original Media Extraction V1

## 1. Problem Context: Review-Image Contamination in Deep-Ingestion

In prior deep-ingestion iterations, scraping tools relied on broad DOM queries (e.g. `[role="main"] img`, `.page-product__detail img`, and whole-page `document.querySelectorAll('img')`) followed by heuristic filters based on bounding box Y-coordinates or section headers (e.g. "Đánh giá sản phẩm", "Customer Reviews").

This approach exhibited severe defects:
1. **Dynamic Layout Shifts & Lazy Loading**: Dynamic content hydration and asynchronous layout changes caused review or recommendation images to load before the estimated bounding box boundary was calculated.
2. **Shared CDN URLs**: Seller images and customer review uploads on Shopee and TikTok Shop are hosted on identical CDN infrastructures (e.g., `*.susercontent.com`, `*.ibyteimg.com`). Hostname-based matching alone cannot determine image ownership.
3. **UGC Ingestion**: Customer review photos, customer uploaded videos/stills, reviewer avatars, and "You may also like" product cards were inadvertently collected as seller original media.

TASK-013 replaces the heuristic paradigm (*"scan page broadly, then attempt to prune review regions"*) with an evidence-first, positive-inclusion architecture (*"extract exclusively from positively verified seller product containers, structured data first, with fail-closed bounds"*).

---

## 2. Trusted Extraction Priority Chain

Platform extractors (`ShopeeSourceExtractor` and `TikTokSourceExtractor`) execute a deterministic 4-tier extraction cascade:

```text
Priority 1: Embedded Structured Product Data
  ├── JSON-LD Product / ProductGroup schemas
  ├── Serialized Product State (SIGI_STATE, __NEXT_DATA__)
  └── Validates current-product identity before accepting payload
        │ (if incomplete or absent)
        ▼
Priority 2: Semantic Product Gallery & Carousel Containers
  ├── .product-image-carousel, .product-image__content (Shopee)
  ├── .product-image, .pdp-image, [data-testid*="gallery"] (TikTok)
  └── Strictly scoped to gallery containers; review subtrees explicitly excluded
        │ (for description-specific media)
        ▼
Priority 3: Seller Description Media
  ├── .product-detail, .product-description, [class*="seller-description"]
  ├── Labeled with SELLER_DESCRIPTION role
  └── Only from positively identified seller detail containers
        │ (if structured and gallery are both empty)
        ▼
Priority 4: Bounded Platform-Scoped Fallback
  ├── Strictly confined to current product summary container (.page-product__briefing)
  ├── Hard limit: Maximum 10 elements
  └── Fails closed if trusted containers are missing; NEVER executes global page scan
```

### Why Global Page Scans and Y-Coordinate Cutoffs Are Forbidden
- Global DOM sweeps (`document.querySelectorAll('img')` or `document.querySelectorAll('*')`) inspect every rendered node, making isolation impossible when third-party widgets or recommendation carousels are present.
- Y-coordinate heuristics (`rect.top + window.scrollY < reviewHeaderY`) break on responsive mobile views, infinite-scroll sidebars, floating widgets, and lazy-loaded DOM re-renderings.
- If all trusted paths yield no media, the extractor raises an explicit `SourcePackExtractionError` or `SourcePackBlockedError` rather than silently falling back to unverified elements.

---

## 3. Product Source Pack Schema & Provenance Model

The canonical `ProductSourcePack` serves as the immutable data contract between marketplace extraction and downstream asset processing.

### Data Models
- **`ProductSourcePack`**:
  - `source_pack_id`: Deterministic ID (`{platform}_{source_product_id}` or SHA-256 URL fingerprint).
  - `platform`: Marketplace identifier (`"shopee"`, `"tiktok"`).
  - `product_url`: Canonicalized input URL.
  - `observed_at`: Extraction timestamp (UTC).
  - `collector`: Collector identifier string.
  - `title`, `shop_name`, `brand`, `model_sku`: Observed seller metadata (None if unobserved).
  - `description_text`: Clean seller text bounded to 10,000 characters.
  - `facts`: Ordered tuple of `ProductFact` instances.
  - `media`: Ordered tuple of `OriginalMediaRef` instances.
  - `diagnostic_codes`: Deterministic diagnostic strings.

- **`ProductFact`**:
  - `key`: Fact name (e.g. `"Weight"`, `"Material"`, `"Brand"`).
  - `value`: Stated fact value (e.g. `"200g"`, `"100% Cotton"`).
  - `unit`: Optional measurement unit.
  - `source_section`: Section origin (`"specification_table"`, `"structured_data"`, `"description"`).
  - `provenance`: Extraction strategy used.

- **`OriginalMediaRef`**:
  - `source_url`: Canonical media URL (`http://` or `https://`).
  - `platform`: Platform name.
  - `role`: Media role (`PRIMARY`, `GALLERY`, `VARIANT`, `SELLER_DESCRIPTION`).
  - `provenance`: Strategy (`STRUCTURED_PRODUCT_DATA`, `SEMANTIC_PRODUCT_GALLERY`, `SEMANTIC_VARIANT_MEDIA`, `SEMANTIC_SELLER_DESCRIPTION`, `PLATFORM_SCOPED_FALLBACK`).
  - `ordinal`: 0-indexed first-seen ordering.
  - `content_type`, `byte_size`, `sha256_hash`, `local_filename`: Populated upon byte-preserving download.

---

## 4. Product Fact Evidence Policy

1. **Explicit Observation Only**: Facts are populated strictly from structured JSON-LD/state or explicit specification tables.
2. **No AI Inference**: Dimensions, brand, materials, or claims are never inferred from title strings, product images, or logos in this milestone.
3. **Missing Facts Remain None**: Unobserved attributes are preserved as `None` rather than default placeholders.
4. **Seller Claims as Claims**: Descriptive claims are attributed to `"description"` without normalizing or upgrading them to verified scientific assertions.

---

## 5. Original Media Download & Deduplication Semantics

`OriginalMediaDownloader` enforces strict source evidence preservation:

1. **Byte-Preserving Persistence**:
   - Original response bytes are written directly to disk without resizing, watermarking, background removal, or JPEG re-encoding.
   - Enforces per-file limit: 20 MiB (`MAX_FILE_BYTES`).
   - Enforces per-product ceiling: 30 media items (`MAX_MEDIA_PER_PRODUCT`).
   - Validates supported image content types and magic numbers (JPEG, PNG, WebP, GIF, BMP, TIFF, SVG).
   - Filenames are deterministically formatted: `orig_{ordinal:03d}_{sha256[:12]}.{ext}`.

2. **Two-Stage Deduplication**:
   - **Stage 1 (Pre-Download URL Dedupe)**: Collapses identical canonical URLs, retaining the highest-confidence provenance tier (`STRUCTURED_PRODUCT_DATA` > `SEMANTIC_PRODUCT_GALLERY` > `SEMANTIC_VARIANT_MEDIA` > `SEMANTIC_SELLER_DESCRIPTION` > `PLATFORM_SCOPED_FALLBACK`) and first-seen ordinal.
   - **Stage 2 (Post-Download SHA-256 Dedupe)**: Collapses exact byte-identical responses resulting from different CDN URLs.

3. **Perceptual Hash Policy**:
   - Perceptual hashes (`pHash`) may be computed for duplicate analysis, but distinct seller images are never deleted based on visual similarity alone.

---

## 6. Source vs Derived AI Asset Boundary

A strict architectural boundary separates source evidence from downstream generative pipelines:

```text
[SOURCE LAYER] (TASK-013)
  └── ProductSourcePack + Original Media Files
      ├── Immutable evidence directly from seller
      ├── Byte-preserving originals (no alterations)
      └── Stored under <Platform>/<Product>/source_pack.json + original/

[DERIVED LAYER] (Future Milestones)
  └── DerivedAssetManifest + Transformed Media
      ├── Background removal / alpha masking
      ├── Clean studio renders
      ├── Novel camera angle generation
      ├── Approximate 360° view reconstruction (inferred, non-photogrammetric)
      └── Clearly labeled as DERIVED/INFERRED; never overwrites original source assets
```

---

## 7. Storage & Google Drive Publication Layout

Source packs are serialized into a deterministic JSON manifest alongside downloaded original images:

```text
Google Drive Root /
└── <Platform> (Shopee | TikTok) /
    └── <Product Title or Product ID> /
        ├── source_pack.json
        └── original /
            ├── orig_000_3a8f1b9c2d1e.jpg
            ├── orig_001_8f2b7c4a1e9d.png
            └── ...
```

- Manifests contain structured facts, media references, SHA-256 hashes, and diagnostic codes.
- Manifests contain **no** raw HTML, cookies, access tokens, credentials, or embedded base64 image data.
- If Google Drive uploads encounter partial network failures, `ToolStatus.PARTIAL_SUCCESS` is honestly reported with uploaded file counts.

---

## 8. Platform DOM Fragility & Isolation Strategy

Marketplace DOM trees undergo frequent client-side redesigns. To maintain stability:
1. All DOM queries and JS extraction logic are strictly encapsulated within `src/product_source/platforms/`.
2. Extractors interact with browsers exclusively through the injected `BrowserManager` / `BrowserSession` protocol (`get_or_create_session()`, `navigate()`, and `evaluate()`).
3. If marketplace UI structures change, only the platform extraction script requires adjustment; models, downloader, serialization, and tool interfaces remain unaffected.

---

## 9. Next Roadmap Steps

1. **M2.3 Scoring & Ranking**: Return to Product Intelligence cross-platform ranking, candidate scoring, and shortlist creation.
2. **M2.4 Autonomous Queue Handoff**: Connect shortlisted candidates to deep-ingestion source pack generation.
3. **Derived AI Assets**: Construct background removal, studio rendering, and 360° multi-view synthesis upon trusted source packs.
