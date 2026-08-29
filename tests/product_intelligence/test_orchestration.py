from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from typing import List, Optional, Sequence, Tuple
import pytest

from src.product_intelligence import (
    CandidateRanker,
    CandidateRankingError,
    DiscoveryBatch,
    DiscoveryBlockedError,
    DiscoveryError,
    DiscoveryNavigationError,
    DiscoveryRequest,
    DiscoveryOrchestrator,
    OrchestrationError,
    OrchestrationInvalidRequestError,
    OrchestrationResult,
    PlatformDiscoveryPlan,
    ProductCandidateSnapshot,
    RankedCandidate,
    orchestrate_discovery,
)
from src.product_intelligence.scoring import WinningProductScorer


EVALUATED_AT = datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc)
OBSERVED_AT = datetime(2026, 8, 29, 11, 0, tzinfo=timezone.utc)


class FakeDiscoveryAdapter:
    """Deterministic in-memory fake discovery adapter for testing."""

    def __init__(
        self,
        platform: str,
        candidates: Sequence[ProductCandidateSnapshot] = (),
        pages_examined: int = 1,
        raw_items_seen: int = 10,
        diagnostic_codes: Tuple[str, ...] = ("TEST_BATCH",),
        raise_error: Optional[Exception] = None,
        override_batch_platform: Optional[str] = None,
        override_batch_query: Optional[str] = None,
    ) -> None:
        self.platform = platform
        self.candidates = tuple(candidates)
        self.pages_examined = pages_examined
        self.raw_items_seen = raw_items_seen
        self.diagnostic_codes = diagnostic_codes
        self.raise_error = raise_error
        self.override_batch_platform = override_batch_platform
        self.override_batch_query = override_batch_query
        self.discover_calls: List[Tuple[DiscoveryRequest, Optional[datetime]]] = []

    async def discover(
        self,
        request: DiscoveryRequest,
        *,
        observed_at: Optional[datetime] = None,
    ) -> DiscoveryBatch:
        self.discover_calls.append((request, observed_at))
        if self.raise_error is not None:
            raise self.raise_error

        batch_platform = self.override_batch_platform or self.platform
        batch_query = self.override_batch_query or request.query
        batch_observed_at = observed_at or EVALUATED_AT

        return DiscoveryBatch(
            platform=batch_platform,
            query=batch_query,
            observed_at=batch_observed_at,
            candidates=self.candidates,
            pages_examined=self.pages_examined,
            raw_items_seen=self.raw_items_seen,
            diagnostic_codes=self.diagnostic_codes,
        )


def _make_candidate(
    candidate_id: str,
    platform: str,
    title: str = "Test Product",
    **kwargs: object,
) -> ProductCandidateSnapshot:
    fields = {
        "candidate_id": candidate_id,
        "platform": platform,
        "url": f"https://{platform}.vn/{candidate_id}",
        "observed_at": OBSERVED_AT,
        "title": title,
    }
    fields.update(kwargs)
    return ProductCandidateSnapshot(**fields)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_ac1_ac2_multi_platform_discovery_produces_immutable_batches_and_ranked_shortlist() -> None:
    shopee_candidate = _make_candidate(
        "shopee:111",
        "shopee",
        title="Wireless Ergonomic Mouse",
        sold_count=5000,
        review_count=800,
        rating=4.9,
    )
    tiktok_candidate = _make_candidate(
        "tiktok:222",
        "tiktok",
        title="Wireless Ergonomic Mouse RGB",
        sold_count=1000,
        review_count=150,
        rating=4.7,
    )

    shopee_adapter = FakeDiscoveryAdapter("shopee", [shopee_candidate], pages_examined=2, raw_items_seen=40)
    tiktok_adapter = FakeDiscoveryAdapter("tiktok", [tiktok_candidate], pages_examined=1, raw_items_seen=20)

    plans = (
        PlatformDiscoveryPlan(
            platform="shopee",
            adapter=shopee_adapter,
            request=DiscoveryRequest(query="wireless mouse", max_candidates=20),
        ),
        PlatformDiscoveryPlan(
            platform="tiktok",
            adapter=tiktok_adapter,
            request=DiscoveryRequest(query="wireless mouse", max_candidates=20),
        ),
    )

    result = await DiscoveryOrchestrator.orchestrate(
        plans,
        evaluated_at=EVALUATED_AT,
        observed_at=OBSERVED_AT,
    )

    assert isinstance(result, OrchestrationResult)
    assert len(result.batches) == 2
    assert result.batches[0].platform == "shopee"
    assert result.batches[0].candidates == (shopee_candidate,)
    assert result.batches[0].pages_examined == 2
    assert result.batches[0].raw_items_seen == 40
    assert result.batches[1].platform == "tiktok"
    assert result.batches[1].candidates == (tiktok_candidate,)
    assert result.batches[1].pages_examined == 1
    assert result.batches[1].raw_items_seen == 20

    assert len(result.shortlist) == 2
    assert tuple(entry.candidate_id for entry in result.shortlist) == ("shopee:111", "tiktok:222")
    assert result.shortlist[0].candidate.platform == "shopee"
    assert result.shortlist[1].candidate.platform == "tiktok"

    # Immutability verification
    with pytest.raises(FrozenInstanceError):
        result.batches = ()  # type: ignore[misc]

    # Functional helper matches class method
    func_result = await orchestrate_discovery(
        plans,
        evaluated_at=EVALUATED_AT,
        observed_at=OBSERVED_AT,
    )
    assert func_result == result


@pytest.mark.asyncio
async def test_ac3_budget_validation_fails_before_adapter_execution() -> None:
    shopee_adapter = FakeDiscoveryAdapter("shopee", [])
    tiktok_adapter = FakeDiscoveryAdapter("tiktok", [])

    plans = (
        PlatformDiscoveryPlan(
            platform="shopee",
            adapter=shopee_adapter,
            request=DiscoveryRequest(query="desk lamp", max_candidates=60),
        ),
        PlatformDiscoveryPlan(
            platform="tiktok",
            adapter=tiktok_adapter,
            request=DiscoveryRequest(query="desk lamp", max_candidates=50),
        ),
    )

    with pytest.raises(OrchestrationInvalidRequestError, match="Aggregate candidate budget exceeds maximum"):
        await DiscoveryOrchestrator.orchestrate(plans, evaluated_at=EVALUATED_AT)

    assert len(shopee_adapter.discover_calls) == 0
    assert len(tiktok_adapter.discover_calls) == 0


@pytest.mark.asyncio
async def test_ac4_duplicate_platform_plans_fail() -> None:
    adapter1 = FakeDiscoveryAdapter("shopee", [])
    adapter2 = FakeDiscoveryAdapter("shopee", [])

    plans = (
        PlatformDiscoveryPlan(
            platform="shopee",
            adapter=adapter1,
            request=DiscoveryRequest(query="desk lamp", max_candidates=10),
        ),
        PlatformDiscoveryPlan(
            platform="shopee",
            adapter=adapter2,
            request=DiscoveryRequest(query="desk lamp", max_candidates=10),
        ),
    )

    with pytest.raises(OrchestrationInvalidRequestError, match="Duplicate platform"):
        await DiscoveryOrchestrator.orchestrate(plans, evaluated_at=EVALUATED_AT)


@pytest.mark.asyncio
async def test_ac4_query_mismatch_across_plans_fails() -> None:
    adapter1 = FakeDiscoveryAdapter("shopee", [])
    adapter2 = FakeDiscoveryAdapter("tiktok", [])

    plans = (
        PlatformDiscoveryPlan(
            platform="shopee",
            adapter=adapter1,
            request=DiscoveryRequest(query="desk lamp", max_candidates=10),
        ),
        PlatformDiscoveryPlan(
            platform="tiktok",
            adapter=adapter2,
            request=DiscoveryRequest(query="floor lamp", max_candidates=10),
        ),
    )

    with pytest.raises(OrchestrationInvalidRequestError, match="matching search queries"):
        await DiscoveryOrchestrator.orchestrate(plans, evaluated_at=EVALUATED_AT)


@pytest.mark.asyncio
async def test_ac4_mismatched_returned_batch_platform_fails() -> None:
    adapter = FakeDiscoveryAdapter("shopee", override_batch_platform="lazada")
    plans = (
        PlatformDiscoveryPlan(
            platform="shopee",
            adapter=adapter,
            request=DiscoveryRequest(query="desk lamp", max_candidates=10),
        ),
    )

    with pytest.raises(OrchestrationError, match="DiscoveryBatch platform mismatch"):
        await DiscoveryOrchestrator.orchestrate(plans, evaluated_at=EVALUATED_AT)


@pytest.mark.asyncio
async def test_ac4_mismatched_returned_batch_query_fails() -> None:
    adapter = FakeDiscoveryAdapter("shopee", override_batch_query="different query")
    plans = (
        PlatformDiscoveryPlan(
            platform="shopee",
            adapter=adapter,
            request=DiscoveryRequest(query="desk lamp", max_candidates=10),
        ),
    )

    with pytest.raises(OrchestrationError, match="DiscoveryBatch query mismatch"):
        await DiscoveryOrchestrator.orchestrate(plans, evaluated_at=EVALUATED_AT)


@pytest.mark.asyncio
async def test_ac4_candidate_platform_mismatch_fails() -> None:
    rogue_candidate = _make_candidate("rogue:1", platform="tiktok")
    adapter = FakeDiscoveryAdapter("shopee", [rogue_candidate])
    plans = (
        PlatformDiscoveryPlan(
            platform="shopee",
            adapter=adapter,
            request=DiscoveryRequest(query="desk lamp", max_candidates=10),
        ),
    )

    with pytest.raises(OrchestrationError, match="Candidate platform mismatch"):
        await DiscoveryOrchestrator.orchestrate(plans, evaluated_at=EVALUATED_AT)


@pytest.mark.asyncio
async def test_ac4_duplicate_aggregate_candidate_id_fails() -> None:
    c1 = _make_candidate("shared:123", platform="shopee")
    c2 = _make_candidate("shared:123", platform="tiktok")

    shopee_adapter = FakeDiscoveryAdapter("shopee", [c1])
    tiktok_adapter = FakeDiscoveryAdapter("tiktok", [c2])

    plans = (
        PlatformDiscoveryPlan(
            platform="shopee",
            adapter=shopee_adapter,
            request=DiscoveryRequest(query="desk lamp", max_candidates=10),
        ),
        PlatformDiscoveryPlan(
            platform="tiktok",
            adapter=tiktok_adapter,
            request=DiscoveryRequest(query="desk lamp", max_candidates=10),
        ),
    )

    with pytest.raises(OrchestrationError, match="Duplicate candidate_id"):
        await DiscoveryOrchestrator.orchestrate(plans, evaluated_at=EVALUATED_AT)


@pytest.mark.asyncio
@pytest.mark.parametrize("shortlist_size", [0, -1, 101, 1.5, True, "5"])
async def test_ac4_invalid_shortlist_bounds_fail_before_discovery(shortlist_size: object) -> None:
    adapter = FakeDiscoveryAdapter("shopee", [])
    plans = (
        PlatformDiscoveryPlan(
            platform="shopee",
            adapter=adapter,
            request=DiscoveryRequest(query="desk lamp", max_candidates=10),
        ),
    )

    with pytest.raises(OrchestrationInvalidRequestError, match="shortlist_size"):
        await DiscoveryOrchestrator.orchestrate(
            plans,
            evaluated_at=EVALUATED_AT,
            shortlist_size=shortlist_size,  # type: ignore[arg-type]
        )
    assert len(adapter.discover_calls) == 0


@pytest.mark.asyncio
async def test_ac4_invalid_timestamps_fail() -> None:
    adapter = FakeDiscoveryAdapter("shopee", [])
    plans = (
        PlatformDiscoveryPlan(
            platform="shopee",
            adapter=adapter,
            request=DiscoveryRequest(query="desk lamp", max_candidates=10),
        ),
    )

    # Missing evaluated_at
    with pytest.raises(OrchestrationInvalidRequestError, match="evaluated_at"):
        await DiscoveryOrchestrator.orchestrate(plans, evaluated_at=None)  # type: ignore[arg-type]

    # Naive evaluated_at
    naive_dt = datetime(2026, 8, 29, 12, 0)
    with pytest.raises(OrchestrationInvalidRequestError, match="timezone-aware"):
        await DiscoveryOrchestrator.orchestrate(plans, evaluated_at=naive_dt)

    # Naive observed_at
    with pytest.raises(OrchestrationInvalidRequestError, match="timezone-aware"):
        await DiscoveryOrchestrator.orchestrate(plans, evaluated_at=EVALUATED_AT, observed_at=naive_dt)


@pytest.mark.asyncio
async def test_ac5_delegates_to_candidate_ranker_without_modifying_semantics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    c_shopee = _make_candidate("shopee:1", "shopee", sold_count=500)
    c_tiktok = _make_candidate("tiktok:1", "tiktok", sold_count=2000)

    shopee_adapter = FakeDiscoveryAdapter("shopee", [c_shopee])
    tiktok_adapter = FakeDiscoveryAdapter("tiktok", [c_tiktok])

    plans = (
        PlatformDiscoveryPlan(
            platform="shopee",
            adapter=shopee_adapter,
            request=DiscoveryRequest(query="lamp", max_candidates=10),
        ),
        PlatformDiscoveryPlan(
            platform="tiktok",
            adapter=tiktok_adapter,
            request=DiscoveryRequest(query="lamp", max_candidates=10),
        ),
    )

    ranker_called = False

    def monitored_rank(*args: object, **kwargs: object) -> Tuple[RankedCandidate, ...]:
        nonlocal ranker_called
        ranker_called = True
        return CandidateRanker.rank(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(CandidateRanker, "rank", monitored_rank)

    result = await DiscoveryOrchestrator.orchestrate(
        plans,
        evaluated_at=EVALUATED_AT,
        shortlist_size=1,
    )

    assert ranker_called
    assert len(result.shortlist) == 1
    assert result.shortlist[0].candidate_id == "tiktok:1"


@pytest.mark.asyncio
async def test_ac6_true_empty_across_all_platforms_returns_empty_shortlist_without_calling_ranker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shopee_adapter = FakeDiscoveryAdapter("shopee", [], pages_examined=1, raw_items_seen=0, diagnostic_codes=("EMPTY_SHOPEE",))
    tiktok_adapter = FakeDiscoveryAdapter("tiktok", [], pages_examined=1, raw_items_seen=0, diagnostic_codes=("EMPTY_TIKTOK",))

    plans = (
        PlatformDiscoveryPlan(
            platform="shopee",
            adapter=shopee_adapter,
            request=DiscoveryRequest(query="nonexistent item 12345", max_candidates=10),
        ),
        PlatformDiscoveryPlan(
            platform="tiktok",
            adapter=tiktok_adapter,
            request=DiscoveryRequest(query="nonexistent item 12345", max_candidates=10),
        ),
    )

    def unexpected_rank(*args: object, **kwargs: object) -> None:
        raise AssertionError("CandidateRanker.rank must not be called for zero candidates")

    monkeypatch.setattr(CandidateRanker, "rank", unexpected_rank)

    result = await DiscoveryOrchestrator.orchestrate(
        plans,
        evaluated_at=EVALUATED_AT,
        shortlist_size=5,
    )

    assert len(result.batches) == 2
    assert result.batches[0].diagnostic_codes == ("EMPTY_SHOPEE",)
    assert result.batches[1].diagnostic_codes == ("EMPTY_TIKTOK",)
    assert result.shortlist == ()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error_cls",
    [DiscoveryError, DiscoveryBlockedError, DiscoveryNavigationError],
)
async def test_ac7_adapter_raised_discovery_errors_remain_fail_closed(
    error_cls: type[Exception],
) -> None:
    failing_adapter = FakeDiscoveryAdapter("shopee", raise_error=error_cls("Platform failure"))
    plans = (
        PlatformDiscoveryPlan(
            platform="shopee",
            adapter=failing_adapter,
            request=DiscoveryRequest(query="query", max_candidates=10),
        ),
    )

    with pytest.raises(error_cls, match="Platform failure"):
        await DiscoveryOrchestrator.orchestrate(plans, evaluated_at=EVALUATED_AT)


@pytest.mark.asyncio
async def test_ac8_cross_platform_listings_are_not_entity_resolved() -> None:
    # Identical product titles and specs on different platforms must remain distinct candidates
    c_shopee = _make_candidate(
        "shopee:item_999",
        "shopee",
        title="Exact Same Physical Product 100W",
        sold_count=100,
    )
    c_tiktok = _make_candidate(
        "tiktok:item_888",
        "tiktok",
        title="Exact Same Physical Product 100W",
        sold_count=200,
    )

    shopee_adapter = FakeDiscoveryAdapter("shopee", [c_shopee])
    tiktok_adapter = FakeDiscoveryAdapter("tiktok", [c_tiktok])

    plans = (
        PlatformDiscoveryPlan(
            platform="shopee",
            adapter=shopee_adapter,
            request=DiscoveryRequest(query="exact item", max_candidates=10),
        ),
        PlatformDiscoveryPlan(
            platform="tiktok",
            adapter=tiktok_adapter,
            request=DiscoveryRequest(query="exact item", max_candidates=10),
        ),
    )

    result = await DiscoveryOrchestrator.orchestrate(plans, evaluated_at=EVALUATED_AT)

    assert len(result.shortlist) == 2
    ids = [entry.candidate_id for entry in result.shortlist]
    assert "shopee:item_999" in ids
    assert "tiktok:item_888" in ids


@pytest.mark.asyncio
async def test_ac9_deterministic_orchestration_result_to_dict() -> None:
    c_shopee = _make_candidate(
        "shopee:item_1",
        "shopee",
        title="Mouse",
        sold_count=100,
    )
    shopee_adapter = FakeDiscoveryAdapter("shopee", [c_shopee])

    plans = (
        PlatformDiscoveryPlan(
            platform="shopee",
            adapter=shopee_adapter,
            request=DiscoveryRequest(query="mouse", max_candidates=10),
        ),
    )

    result = await DiscoveryOrchestrator.orchestrate(plans, evaluated_at=EVALUATED_AT)
    serialized = result.to_dict()

    assert serialized["total_candidates_discovered"] == 1
    assert serialized["shortlist_count"] == 1
    assert len(serialized["batches"]) == 1
    assert len(serialized["shortlist"]) == 1
    assert serialized["shortlist"][0]["candidate"]["candidate_id"] == "shopee:item_1"
    assert "final_score" in serialized["shortlist"][0]["score"]
