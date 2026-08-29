from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional, Sequence, Set, Tuple

from src.product_intelligence.discovery import (
    DiscoveryBatch,
    DiscoveryRequest,
    ProductDiscoveryAdapter,
)
from src.product_intelligence.models import ProductCandidateSnapshot
from src.product_intelligence.policy import ScoringPolicy
from src.product_intelligence.ranking import (
    MAX_RANKING_CANDIDATES,
    MAX_SHORTLIST_SIZE,
    MIN_RANKING_CANDIDATES,
    MIN_SHORTLIST_SIZE,
    CandidateRanker,
    CandidateRankingError,
    RankedCandidate,
)


class OrchestrationError(Exception):
    """Base exception for all product intelligence orchestration errors."""
    pass


class OrchestrationInvalidRequestError(OrchestrationError):
    """Raised when an orchestration request or plan configuration is invalid."""
    pass


@dataclass(frozen=True)
class PlatformDiscoveryPlan:
    """
    Deterministic specification for a single platform's discovery phase within an orchestration run.
    """
    platform: str
    adapter: ProductDiscoveryAdapter
    request: DiscoveryRequest

    def __post_init__(self) -> None:
        if not self.platform or not isinstance(self.platform, str) or not self.platform.strip():
            raise OrchestrationInvalidRequestError("Platform identifier must be a non-empty string")
        if self.adapter is None or not hasattr(self.adapter, "discover") or not callable(getattr(self.adapter, "discover")):
            raise OrchestrationInvalidRequestError(f"Adapter for platform '{self.platform}' must implement ProductDiscoveryAdapter")
        if not isinstance(self.request, DiscoveryRequest):
            raise OrchestrationInvalidRequestError(f"Request for platform '{self.platform}' must be a DiscoveryRequest instance")


@dataclass(frozen=True)
class OrchestrationResult:
    """
    Immutable result containing the exact per-platform DiscoveryBatch results and the ranked shortlist.
    """
    batches: Tuple[DiscoveryBatch, ...]
    shortlist: Tuple[RankedCandidate, ...]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "batches": [b.to_dict() for b in self.batches],
            "shortlist": [
                {
                    "candidate": r.candidate.to_dict(),
                    "score": r.score.to_dict(),
                }
                for r in self.shortlist
            ],
            "total_candidates_discovered": sum(len(b.candidates) for b in self.batches),
            "shortlist_count": len(self.shortlist),
        }


class DiscoveryOrchestrator:
    """
    Platform-neutral coordinator that executes discovery across multiple platform adapters
    and delegates candidate ranking to the deterministic CandidateRanker.
    """

    @classmethod
    async def orchestrate(
        cls,
        plans: Sequence[PlatformDiscoveryPlan],
        *,
        observed_at: datetime,
        evaluated_at: datetime,
        shortlist_size: Optional[int] = None,
        policy: Optional[ScoringPolicy] = None,
    ) -> OrchestrationResult:
        """
        Executes discovery sequentially across the provided platform plans in caller-supplied order,
        validates the aggregate candidate set, and delegates ranking to CandidateRanker.
        """
        # Validate timestamp requirements
        if observed_at is None:
            raise OrchestrationInvalidRequestError("observed_at timestamp is required for deterministic orchestration")
        if not isinstance(observed_at, datetime) or observed_at.tzinfo is None or observed_at.tzinfo.utcoffset(observed_at) is None:
            raise OrchestrationInvalidRequestError("observed_at must be an explicit timezone-aware datetime")

        if evaluated_at is None:
            raise OrchestrationInvalidRequestError("evaluated_at timestamp is required for deterministic orchestration")
        if not isinstance(evaluated_at, datetime) or evaluated_at.tzinfo is None or evaluated_at.tzinfo.utcoffset(evaluated_at) is None:
            raise OrchestrationInvalidRequestError("evaluated_at must be an explicit timezone-aware datetime")

        # Validate plans collection
        if not plans:
            raise OrchestrationInvalidRequestError("At least one PlatformDiscoveryPlan is required")

        # Validate shortlist_size bounds if provided
        if shortlist_size is not None:
            if isinstance(shortlist_size, bool) or not isinstance(shortlist_size, int):
                raise OrchestrationInvalidRequestError("shortlist_size must be an integer")
            if not (MIN_SHORTLIST_SIZE <= shortlist_size <= MAX_SHORTLIST_SIZE):
                raise OrchestrationInvalidRequestError(
                    f"shortlist_size must be in [{MIN_SHORTLIST_SIZE}, {MAX_SHORTLIST_SIZE}], got {shortlist_size}"
                )

        # Validate plan uniqueness and query consistency
        seen_platforms: Set[str] = set()
        total_max_candidates = 0
        canonical_query = plans[0].request.query.strip()

        for plan in plans:
            if not isinstance(plan, PlatformDiscoveryPlan):
                raise OrchestrationInvalidRequestError(f"Expected PlatformDiscoveryPlan, got {type(plan)}")

            if plan.platform in seen_platforms:
                raise OrchestrationInvalidRequestError(f"Duplicate platform in discovery plans: '{plan.platform}'")
            seen_platforms.add(plan.platform)

            if plan.request.query.strip() != canonical_query:
                raise OrchestrationInvalidRequestError(
                    f"All discovery plans must have matching search queries. "
                    f"Expected '{canonical_query}', got '{plan.request.query.strip()}' for platform '{plan.platform}'"
                )

            total_max_candidates += plan.request.max_candidates

        # Validate aggregate candidate budget before performing any discovery
        if total_max_candidates > MAX_RANKING_CANDIDATES:
            raise OrchestrationInvalidRequestError(
                f"Aggregate candidate budget exceeds maximum of {MAX_RANKING_CANDIDATES}: got {total_max_candidates}"
            )

        # Execute discovery plans sequentially in caller-supplied order
        batches: list[DiscoveryBatch] = []
        for plan in plans:
            batch = await plan.adapter.discover(plan.request, observed_at=observed_at)
            
            # Validate returned batch platform and query match plan specifications
            if batch.platform != plan.platform:
                raise OrchestrationError(
                    f"DiscoveryBatch platform mismatch: plan expected '{plan.platform}', adapter returned '{batch.platform}'"
                )
            if batch.query.strip() != canonical_query:
                raise OrchestrationError(
                    f"DiscoveryBatch query mismatch: expected '{canonical_query}', adapter returned '{batch.query.strip()}'"
                )
            
            # Validate candidate platform integrity
            for candidate in batch.candidates:
                if candidate.platform != plan.platform:
                    raise OrchestrationError(
                        f"Candidate platform mismatch: plan expected '{plan.platform}', candidate has '{candidate.platform}'"
                    )

            batches.append(batch)

        batches_tuple = tuple(batches)

        # Collect aggregate candidates
        all_candidates: list[ProductCandidateSnapshot] = []
        seen_candidate_ids: Set[str] = set()
        duplicate_candidate_ids: Set[str] = set()

        for batch in batches_tuple:
            for candidate in batch.candidates:
                if candidate.candidate_id in seen_candidate_ids:
                    duplicate_candidate_ids.add(candidate.candidate_id)
                seen_candidate_ids.add(candidate.candidate_id)
                all_candidates.append(candidate)

        if duplicate_candidate_ids:
            raise OrchestrationError(
                f"Duplicate candidate_id values detected in aggregate discovery results: "
                f"{', '.join(sorted(duplicate_candidate_ids))}"
            )

        # Bounded empty check
        if not all_candidates:
            return OrchestrationResult(
                batches=batches_tuple,
                shortlist=(),
            )

        # Delegate ranking to CandidateRanker
        try:
            shortlist = CandidateRanker.rank(
                tuple(all_candidates),
                evaluated_at=evaluated_at,
                shortlist_size=shortlist_size,
                policy=policy,
            )
        except CandidateRankingError as err:
            raise OrchestrationError(f"Candidate ranking failed: {err}") from err

        return OrchestrationResult(
            batches=batches_tuple,
            shortlist=shortlist,
        )


async def orchestrate_discovery(
    plans: Sequence[PlatformDiscoveryPlan],
    *,
    observed_at: datetime,
    evaluated_at: datetime,
    shortlist_size: Optional[int] = None,
    policy: Optional[ScoringPolicy] = None,
) -> OrchestrationResult:
    """
    Functional entry point for DiscoveryOrchestrator.orchestrate.
    """
    return await DiscoveryOrchestrator.orchestrate(
        plans,
        observed_at=observed_at,
        evaluated_at=evaluated_at,
        shortlist_size=shortlist_size,
        policy=policy,
    )
