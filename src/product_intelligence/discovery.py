from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol, Sequence, Tuple, runtime_checkable

from src.product_intelligence.models import ProductCandidateSnapshot

# Safe operational bounds for discovery requests
MIN_CANDIDATES = 1
MAX_CANDIDATES = 100
MIN_PAGES = 1
MAX_PAGES = 5


class DiscoveryError(Exception):
    """Base exception for all product intelligence discovery errors."""
    pass


class DiscoveryInvalidRequestError(DiscoveryError):
    """Raised when a discovery request fails parameter validation."""
    pass


class DiscoveryNavigationError(DiscoveryError):
    """Raised when the discovery adapter encounters a fatal navigation error."""
    pass


class DiscoveryBlockedError(DiscoveryError):
    """Raised when the discovery adapter encounters an anti-bot challenge / captcha / block page."""
    pass


@dataclass(frozen=True)
class DiscoveryRequest:
    """
    Immutable search request for candidate discovery across marketplace listing surfaces.
    """
    query: str
    max_candidates: int = 50
    max_pages: int = 1
    locale: str = "vi-VN"

    def __post_init__(self) -> None:
        trimmed_query = self.query.strip() if self.query else ""
        if not trimmed_query:
            raise DiscoveryInvalidRequestError("Discovery query cannot be empty or whitespace only")

        if not (MIN_CANDIDATES <= self.max_candidates <= MAX_CANDIDATES):
            raise DiscoveryInvalidRequestError(
                f"max_candidates must be in [{MIN_CANDIDATES}, {MAX_CANDIDATES}], got {self.max_candidates}"
            )

        if not (MIN_PAGES <= self.max_pages <= MAX_PAGES):
            raise DiscoveryInvalidRequestError(
                f"max_pages must be in [{MIN_PAGES}, {MAX_PAGES}], got {self.max_pages}"
            )


@dataclass(frozen=True)
class DiscoveryBatch:
    """
    Immutable collection of product candidates discovered from a search surface.
    Strictly contains only structured diagnostic data, never raw HTML, cookies, tokens, or credentials.
    """
    platform: str
    query: str
    observed_at: datetime
    candidates: Tuple[ProductCandidateSnapshot, ...]
    pages_examined: int
    raw_items_seen: int
    diagnostic_codes: Tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "platform": self.platform,
            "query": self.query,
            "observed_at": self.observed_at.isoformat(),
            "candidate_count": len(self.candidates),
            "candidates": [c.to_dict() for c in self.candidates],
            "pages_examined": self.pages_examined,
            "raw_items_seen": self.raw_items_seen,
            "diagnostic_codes": list(self.diagnostic_codes),
        }


@runtime_checkable
class ProductDiscoveryAdapter(Protocol):
    """
    Platform-independent interface for discovering product candidate snapshots.
    """
    async def discover(
        self,
        request: DiscoveryRequest,
        *,
        observed_at: Optional[datetime] = None,
    ) -> DiscoveryBatch:
        """
        Executes bounded discovery for a search query and returns a batch of candidate snapshots.
        """
        ...
