# Phase 6 M2 — Product Intelligence Vertical Slice (Discovery to Shortlist)

## Purpose

The Discovery Orchestration vertical slice is the platform-neutral composition boundary that connects multiple marketplace discovery adapters (e.g. Shopee and TikTok) to deterministic candidate ranking (`CandidateRanker`).

It executes discovery across injected platform adapters sequentially in caller-specified order, aggregates and validates candidates, and delegates ranking to produce an immutable, auditable cross-platform shortlist.

```text
PlatformDiscoveryPlan(s) [Shopee, TikTok, ...]
  ↓
DiscoveryOrchestrator.orchestrate
  ↓
Sequential Injected Discovery Adapters (`adapter.discover`)
  ↓
Immutable DiscoveryBatch results (preserves diagnostics)
  ↓
Aggregate Validation (Budget <= 100, Query match, Unique candidate IDs)
  ↓
CandidateRanker.rank (Pure & Deterministic Scoring/Ranking)
  ↓
OrchestrationResult (batches + shortlist)
```

## Contract & Constraints

### 1. Injected Platform Plans (`PlatformDiscoveryPlan`)
Each plan specifies:
- `platform`: non-empty platform identifier matching the adapter (e.g. `"shopee"`, `"tiktok"`);
- `adapter`: injected implementation of `ProductDiscoveryAdapter`;
- `request`: canonical `DiscoveryRequest` with query and bounded candidate count.

Multiple plans execute strictly in caller-supplied order.

### 2. Validation Before Execution (Fail-Closed)
Before calling any discovery adapter:
- `observed_at` is required and must be timezone-aware (no wall-clock defaults);
- `evaluated_at` is required and must be timezone-aware (no wall-clock defaults);
- Plan platform identifiers must be unique across the run;
- All plans must target the same search query;
- The sum of `max_candidates` across all plans must not exceed the global limit of 100 (`MAX_RANKING_CANDIDATES`);
- `shortlist_size`, if supplied, must be an integer in `[1, 100]`.

### 3. Post-Discovery Validation
After receiving each `DiscoveryBatch`:
- Returned batch `platform` and `query` must match the plan;
- Candidate snapshot `platform` attributes must match the plan platform;
- Candidate IDs across all batches must be unique (duplicate IDs fail closed rather than being silently merged).

### 4. Zero-Candidate and Partial-Candidate Semantics
- If all participating platforms return zero candidates, orchestration returns a deterministic empty shortlist without fabricating candidates or calling `CandidateRanker` with an invalid zero-candidate input.
- Original `DiscoveryBatch` diagnostic codes, pages examined, and raw items seen are preserved intact in the final `OrchestrationResult`.
- If an adapter raises `DiscoveryError`, `DiscoveryBlockedError`, or `DiscoveryNavigationError`, the error propagates fail-closed and is never converted to a silent success or empty batch.

### 5. Isolation from M3 and Ingestion
- **No entity resolution**: Cross-platform listings are not merged based on title, brand, or similarity. Physical-product equivalence is explicitly deferred to M3.
- **No side effects**: The orchestration layer performs zero browser lifecycle management, live network I/O, LLM calls, human approval, queue writes (`tasks.txt`), ingestion starts, or Google Drive operations.

## Usage Example

```python
from datetime import datetime, timezone

from src.product_intelligence import (
    DiscoveryRequest,
    DiscoveryOrchestrator,
    PlatformDiscoveryPlan,
    ShopeeDiscoveryAdapter,
    TikTokDiscoveryAdapter,
)

observed_at = datetime.now(timezone.utc)
evaluated_at = datetime.now(timezone.utc)

plans = (
    PlatformDiscoveryPlan(
        platform="shopee",
        adapter=ShopeeDiscoveryAdapter(browser_session=session),
        request=DiscoveryRequest(query="ergonomic keyboard", max_candidates=25),
    ),
    PlatformDiscoveryPlan(
        platform="tiktok",
        adapter=TikTokDiscoveryAdapter(browser_session=session),
        request=DiscoveryRequest(query="ergonomic keyboard", max_candidates=25),
    ),
)

result = await DiscoveryOrchestrator.orchestrate(
    plans,
    observed_at=observed_at,
    evaluated_at=evaluated_at,
    shortlist_size=10,
)

print(f"Discovered {len(result.batches)} batches, Shortlist: {len(result.shortlist)}")
```
