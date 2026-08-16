from src.product_intelligence.discovery import (
    DiscoveryBatch,
    DiscoveryBlockedError,
    DiscoveryError,
    DiscoveryInvalidRequestError,
    DiscoveryNavigationError,
    DiscoveryRequest,
    ProductDiscoveryAdapter,
)
from src.product_intelligence.models import (
    CANONICAL_FACTUAL_SIGNALS,
    CANONICAL_SEMANTIC_SIGNALS,
    CategoryScore,
    ConfidenceBreakdown,
    DecisionBand,
    NormalizedSignal,
    ProductCandidateSnapshot,
    ScoreCategory,
    SignalEvidence,
    SignalProvenance,
    WinningProductScore,
)
from src.product_intelligence.normalizer import SnapshotNormalizer
from src.product_intelligence.policy import ScoringPolicy
from src.product_intelligence.scoring import WinningProductScorer
from src.product_intelligence.adapters.shopee import ShopeeDiscoveryAdapter
from src.product_intelligence.adapters.shopee_parsing import (
    build_shopee_candidate_id,
    build_shopee_search_url,
    extract_shopee_product_id,
    parse_shopee_discount_percent,
    parse_shopee_price,
    parse_shopee_rating,
    parse_shopee_review_count,
    parse_shopee_sold_count,
)

__all__ = [
    "ProductCandidateSnapshot",
    "SignalEvidence",
    "SignalProvenance",
    "ScoreCategory",
    "DecisionBand",
    "NormalizedSignal",
    "CategoryScore",
    "ConfidenceBreakdown",
    "WinningProductScore",
    "CANONICAL_FACTUAL_SIGNALS",
    "CANONICAL_SEMANTIC_SIGNALS",
    "ScoringPolicy",
    "SnapshotNormalizer",
    "WinningProductScorer",
    "DiscoveryRequest",
    "DiscoveryBatch",
    "ProductDiscoveryAdapter",
    "DiscoveryError",
    "DiscoveryInvalidRequestError",
    "DiscoveryNavigationError",
    "DiscoveryBlockedError",
    "ShopeeDiscoveryAdapter",
    "parse_shopee_price",
    "parse_shopee_sold_count",
    "parse_shopee_rating",
    "parse_shopee_review_count",
    "parse_shopee_discount_percent",
    "extract_shopee_product_id",
    "build_shopee_candidate_id",
    "build_shopee_search_url",
]
