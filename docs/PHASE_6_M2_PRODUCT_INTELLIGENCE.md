# Phase 6 M2 — Winning Product Intelligence (Contracts & Score V1)

This document specifies the architecture, data models, evidence provenance, and deterministic scoring system for **Phase 6 M2 Winning Product Intelligence**.

---

## 1. Objective & System Boundaries

### Mission
Product Intelligence answers the question:
> *"Among hundreds of candidate listings across marketplaces, which products deserve deeper Agent resources next, with a reproducible score, confidence, explanation, and evidence trail?"*

### Discovery vs Ingestion Architecture
```text
Discovery Adapters (M2.2) [Cheap & Wide]
  ↓
ProductCandidateSnapshot + Evidence
  ↓
SnapshotNormalizer (Platform-Agnostic)
  ↓
WinningProductScorer (Pure & Deterministic)
  ↓
WinningProductScore (Base + Confidence + Breakdown + Reasons)
  ↓
Human-in-the-Loop Review / Approval (M2.4)
  ↓
Autonomous Queue (tasks.txt) → Deep Ingestion (M1) [Expensive & Narrow]
  ↓
Canonical Product Knowledge Base (M3)
```

- **M2 (Discovery & Intelligence)**: Collects lightweight listing observations cheaply and ranks candidates purely and deterministically.
- **M1 (Ingestion & Processing)**: Heavy Playwright browser scraping, watermarking, and Google Drive publishing (only runs on approved candidates).
- **M3 (Product Knowledge Base)**: Cross-listing entity resolution, persistent product catalog, and RAG knowledge base.

---

## 2. Canonical Contracts

### `ProductCandidateSnapshot` (`src/product_intelligence/models.py`)
Represents an immutable observation of a marketplace listing at a single point in time:
- **Identity / Source**: `candidate_id`, `platform` (e.g. `"shopee"`, `"tiktok"`), `url`, `observed_at`, `collector`, `source_product_id`.
- **Descriptive**: `title`, `shop_id`, `shop_name`, `category`, `brand`, `model`.
- **Observed Market Metrics (Nullable)**: `price`, `original_price`, `discount_percent`, `sold_count`, `rating`, `review_count`, `affiliate_commission_rate`, `estimated_commission_value`, `creator_count`, `video_count`, `similar_listing_count`.
- **Velocity / Deltas (Nullable)**: `sales_velocity`, `review_velocity`, `creator_velocity`, `video_velocity`.

> [!IMPORTANT]
> Unknown market values remain `None`. The system never converts missing data to `0`.

### `SignalEvidence` & `SignalProvenance`
Every factual signal must be auditable:
- `SignalProvenance`: `OBSERVED` (directly scraped), `DERIVED` (computed across observations), `INFERRED` (semantic assessment), or `MISSING`.
- `SignalEvidence`: Contains `signal_name`, `source_type`, `source_url`, `observed_at`, `collector`, `raw_value_repr`, `source_reliability`. Contains no secrets, tokens, or raw HTML dumps.

---

## 3. Winning Product Score V1 (0–100 Scale)

The score is computed across **6 canonical categories** with strictly fixed weights totaling **100 points**:

| Category | Weight | Description & Signal Sources |
| :--- | :---: | :--- |
| **Demand** | **25** | Absolute volume evidence: `sold_count`, `review_count`. |
| **Momentum** | **20** | Explicit observed deltas/velocities: `sales_velocity`, `creator_velocity`. (*Never inferred from static single-snapshot counts*). |
| **Commercial Attractiveness** | **15** | Monetization appeal: `affiliate_commission_rate`, `discount_percent`. |
| **Trust** | **10** | Quality score: `rating` damped by review volume depth. |
| **Contentability** | **15** | Hookability, visual demo potential, problem/solution clarity (`INFERRED` semantic signals). |
| **Competition Opportunity** | **15** | Market whitespace: lower creator/competitor saturation yields a **higher** opportunity score. |
| **Total** | **100** | |

---

## 4. Confidence Formula & Missing-Data Damping

To ensure that sparse or unverified data cannot artificially inflate a candidate's rank, V1 computes an explicit 4-dimensional confidence factor in `[0.0, 1.0]`:

$$\text{Confidence} = 0.40 \cdot \text{Completeness} + 0.25 \cdot \text{Freshness} + 0.20 \cdot \text{Reliability} + 0.15 \cdot \text{Evidence Coverage}$$

- **Data Completeness (40%)**: Weighted coverage across the 6 categories.
- **Freshness (25%)**: Exponential decay based on observation age ($t_{1/2} = 72$ hours by default).
- **Source Reliability (20%)**: Reliability score of the data sources.
- **Evidence Coverage (15%)**: Fraction of signals backed by verifiable factual evidence.

### Final Score Formula
$$\text{Final Score} = \text{Base Score} \times \text{Overall Confidence}$$

---

## 5. Advisory Decision Bands

- **`RECOMMENDED`**: `final_score >= 80.0` **and** `confidence >= 0.75`.
- **`NEEDS_REVIEW`**: `final_score >= 65.0` **and** `confidence >= 0.65` (not RECOMMENDED).
- **`INSUFFICIENT_DATA`**: `confidence < 0.50` (regardless of base score).
- **`HOLD`**: All other candidates.

> [!NOTE]
> In TASK-011, decision bands are advisory only. No candidate is automatically written to `tasks.txt`.

---

## 6. LLM Boundary

- **LLM MAY**: Infer semantic qualities such as contentability, visual demo potential, UGC hook angles, or audience hypotheses (`SignalProvenance.INFERRED`).
- **LLM MUST NOT**: Fabricate, hallucinate, or directly assign numerical market facts (`sold_count`, `rating`, `price`, `commission_rate`, `velocity`).
- **Scorer Core**: The scoring subsystem (`WinningProductScorer`) is 100% pure and deterministic, performing zero network or LLM calls.

---

## 7. Synthetic Worked Example

Given a candidate snapshot:
- `title`: *"Magnetic Wireless Car Charger 15W"*
- `sold_count`: 8,500 (Demand score = 0.98)
- `sales_velocity`: 35/day (Momentum score = 0.91)
- `affiliate_commission_rate`: 15% (Commercial score = 0.75)
- `rating`: 4.85 with 1,200 reviews (Trust score = 0.92)
- `contentability`: 0.85 (inferred semantic signal)
- `similar_listing_count`: 4 (Competition whitespace score = 0.82)

### Score Breakdown:
1. **Category Points**:
   - Demand: $0.98 \times 25 = 24.50$
   - Momentum: $0.91 \times 20 = 18.20$
   - Commercial: $0.75 \times 15 = 11.25$
   - Trust: $0.92 \times 10 = 9.20$
   - Contentability: $0.85 \times 15 = 12.75$
   - Competition: $0.82 \times 15 = 12.30$
   - **Base Score**: **`88.20 / 100.0`**

2. **Confidence Components**:
   - Data Completeness: $1.00 \times 0.40 = 0.400$
   - Freshness (observed 1 hour ago): $0.99 \times 0.25 = 0.248$
   - Reliability: $1.00 \times 0.20 = 0.200$
   - Evidence Coverage (5 of 6 observed/derived): $0.83 \times 0.15 = 0.125$
   - **Overall Confidence**: **`0.973`**

3. **Result**:
   - **`Final Score`**: $88.20 \times 0.973 = \mathbf{85.82}$
   - **`Decision Band`**: **`RECOMMENDED`**
   - **`Reason Codes`**: `STRONG_DEMAND`, `HIGH_MOMENTUM`, `FAVORABLE_ECONOMICS`, `TRUST_SIGNAL_STRONG`, `CONTENTABILITY_HIGH`, `COMPETITION_FAVORABLE`, `HIGH_DATA_COMPLETENESS`, `FRESH_MARKET_DATA`, `HIGH_EVIDENCE_COVERAGE`, `HIGH_SOURCE_RELIABILITY`.

---

## 8. Next Milestones

- **Phase 6 M2.2**: Discovery Adapters (Shopee first, TikTok next) for wide candidate collection.
- **Phase 6 M2.3**: Candidate Ranking & Shortlist UI.
- **Phase 6 M2.4**: Human approval bridge to Phase 6 M1 ingestion queue.
