"""Bounded exact-public-PDP observation for TikTok Shop.

This adapter borrows an already-owned BrowserSession-like object.  It owns no
browser lifecycle, evidence, persistence, ranking, approval, or Product Source
authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Mapping, Optional, Sequence
from urllib.parse import urlsplit

from src.browser.session import BrowserSession
from src.product_intelligence.adapters.tiktok_parsing import (
    build_tiktok_candidate_id,
    extract_tiktok_product_id,
    parse_tiktok_discount_percent,
    parse_tiktok_pdp_price,
    parse_tiktok_pdp_review_count,
    parse_tiktok_pdp_sold_count,
    parse_tiktok_rating,
)
from src.product_intelligence.models import ProductCandidateSnapshot


TIKTOK_PDP_EXTRACTION_SCRIPT = r"""() => {
    const text = (selector) => Array.from(document.querySelectorAll(selector))
        .map((node) => (node.innerText || node.textContent || '').trim())
        .filter(Boolean);
    const attrs = (selector, attribute) => Array.from(document.querySelectorAll(selector))
        .map((node) => (node.getAttribute(attribute) || '').trim())
        .filter(Boolean);
    const pageTitle = (document.title || '').toLowerCase();
    const bodyText = document.body ? document.body.innerText.toLowerCase() : '';
    const path = window.location.pathname.toLowerCase();
    let accessState = 'PUBLIC';
    if (
        document.querySelector('.tiktok-captcha, #challenge-running, .captcha_container, [data-testid="captcha"], .sec-captcha') ||
        pageTitle.includes('captcha') || pageTitle.includes('security verification') ||
        bodyText.includes('verify you are human') || bodyText.includes('verification challenge')
    ) accessState = 'CHALLENGE';
    else if (
        path.includes('/login') || document.querySelector('[data-testid="login-page"]') ||
        bodyText.includes('log in to continue') || bodyText.includes('sign in to continue')
    ) accessState = 'LOGIN';
    else if (
        document.querySelector('[data-testid="product-unavailable"], .product-unavailable') ||
        bodyText.includes('product is unavailable') || bodyText.includes('page not found')
    ) accessState = 'UNAVAILABLE';

    return {
        observed_url: window.location.href,
        access_state: accessState,
        identity_candidates: [
            ...attrs('main[data-product-id], [data-testid="pdp-container"][data-product-id]', 'data-product-id'),
            ...attrs('meta[name="product_id"], meta[property="product:id"]', 'content')
        ],
        title_candidates: text('h1, [data-testid="product-title"], [data-e2e="product-title"]'),
        shop_name_candidates: text('[data-testid="shop-name"], [data-e2e="shop-name"], main .seller-name'),
        current_price_candidates: text('[data-testid="product-price"], [data-e2e="product-price"], main .current-price'),
        original_price_candidates: text('[data-testid="original-price"], main .original-price, main .line-through'),
        discount_candidates: text('[data-testid="discount"], main .discount-badge, main .discount'),
        sold_count_candidates: text('[data-testid="sold-count"], [data-e2e="sold-count"], main .sold-count'),
        rating_candidates: text('[data-testid="rating-score"], [data-e2e="rating-score"], main .rating-score'),
        review_count_candidates: text('[data-testid="review-count"], [data-e2e="review-count"], main .review-count')
    };
}"""


class TikTokPdpFailureCode(str, Enum):
    BLOCKED_OR_LOGIN = "BLOCKED_OR_LOGIN"
    IDENTITY_MISMATCH_OR_UNVERIFIABLE = "IDENTITY_MISMATCH_OR_UNVERIFIABLE"
    EXTRACTION_FAILURE = "EXTRACTION_FAILURE"


class TikTokPdpCollectionError(RuntimeError):
    """Fail-closed PDP observation outcome; never carries a partial snapshot."""

    code: TikTokPdpFailureCode

    def __init__(self, code: TikTokPdpFailureCode, message: str) -> None:
        super().__init__(message)
        self.code = code


class TikTokPdpBlockedOrLoginError(TikTokPdpCollectionError):
    def __init__(self, message: str) -> None:
        super().__init__(TikTokPdpFailureCode.BLOCKED_OR_LOGIN, message)


class TikTokPdpIdentityError(TikTokPdpCollectionError):
    def __init__(self, message: str) -> None:
        super().__init__(TikTokPdpFailureCode.IDENTITY_MISMATCH_OR_UNVERIFIABLE, message)


class TikTokPdpExtractionError(TikTokPdpCollectionError):
    def __init__(self, message: str) -> None:
        super().__init__(TikTokPdpFailureCode.EXTRACTION_FAILURE, message)


@dataclass(frozen=True)
class TikTokPdpIdentityBasis:
    basis: str
    source_product_id: str


@dataclass(frozen=True)
class TikTokPdpBindingReceipt:
    """Transport provenance only; not observation, evidence, or product truth."""

    requested_url: str
    observed_url: str
    identity_bases: tuple[TikTokPdpIdentityBasis, ...]


@dataclass(frozen=True)
class TikTokPdpCollectionResult:
    snapshot: ProductCandidateSnapshot
    binding: TikTokPdpBindingReceipt


_EXTRACTION_KEYS = frozenset(
    {
        "observed_url",
        "access_state",
        "identity_candidates",
        "title_candidates",
        "shop_name_candidates",
        "current_price_candidates",
        "original_price_candidates",
        "discount_candidates",
        "sold_count_candidates",
        "rating_candidates",
        "review_count_candidates",
    }
)
_CANDIDATE_KEYS = _EXTRACTION_KEYS - {"observed_url", "access_state"}
_PUBLIC_ACCESS_STATES = frozenset({"PUBLIC", "OK", "AVAILABLE"})
_DENIED_ACCESS_STATES = frozenset(
    {"BLOCKED", "LOGIN", "CHALLENGE", "CAPTCHA", "UNAVAILABLE", "UNRELATED"}
)
_PLACEHOLDER_TITLES = frozenset(
    {"product", "product details", "tiktok shop", "unavailable", "not found", "-"}
)


class TikTokPdpCollector:
    """Observe one exact public TikTok PDP through an injected session only."""

    def __init__(
        self,
        session: BrowserSession,
        *,
        collector_name: str = "tiktok_public_pdp_v1",
    ) -> None:
        if session is None or not callable(getattr(session, "navigate", None)) or not callable(
            getattr(session, "evaluate", None)
        ):
            raise TypeError("session must provide navigate() and evaluate()")
        if not collector_name.strip():
            raise ValueError("collector_name cannot be empty")
        self._session = session
        self.collector_name = collector_name.strip()

    async def collect(
        self,
        requested_url: str,
        *,
        observed_at: datetime,
    ) -> TikTokPdpCollectionResult:
        if not isinstance(requested_url, str) or not requested_url.strip():
            raise TikTokPdpIdentityError("requested URL must be a non-empty string")
        requested_id = extract_tiktok_product_id(requested_url)
        if requested_id is None:
            raise TikTokPdpIdentityError("requested URL has no canonical TikTok product ID")
        self._validate_tiktok_url(requested_url, label="requested")
        if (
            not isinstance(observed_at, datetime)
            or observed_at.tzinfo is None
            or observed_at.utcoffset() is None
        ):
            raise TikTokPdpExtractionError("observed_at must be timezone-aware")

        try:
            await self._session.navigate(requested_url)
            raw = await self._session.evaluate(TIKTOK_PDP_EXTRACTION_SCRIPT)
        except Exception as exc:
            raise TikTokPdpExtractionError("PDP navigation or evaluation failed") from exc

        payload = self._admit_payload(raw)
        access_state = str(payload["access_state"]).strip().upper()
        if access_state in _DENIED_ACCESS_STATES:
            raise TikTokPdpBlockedOrLoginError(f"PDP access state is {access_state}")
        if access_state not in _PUBLIC_ACCESS_STATES:
            raise TikTokPdpExtractionError("PDP access state is not safely established")

        observed_url = str(payload["observed_url"]).strip()
        identity_bases = self._admit_identity(
            requested_id=requested_id,
            observed_url=observed_url,
            explicit_candidates=payload["identity_candidates"],
        )

        title = self._reconcile_text(payload["title_candidates"])
        if title is None or title.casefold() in _PLACEHOLDER_TITLES:
            raise TikTokPdpExtractionError("one explicit non-placeholder title is required")

        snapshot = ProductCandidateSnapshot(
            candidate_id=build_tiktok_candidate_id(requested_id, observed_url),
            platform="tiktok",
            source_product_id=requested_id,
            url=observed_url,
            observed_at=observed_at,
            collector=self.collector_name,
            title=title,
            shop_name=self._reconcile_text(payload["shop_name_candidates"]),
            price=self._reconcile_price(
                payload["current_price_candidates"], parse_tiktok_pdp_price
            ),
            original_price=self._reconcile_price(
                payload["original_price_candidates"], parse_tiktok_pdp_price
            ),
            discount_percent=self._reconcile_scalar(
                payload["discount_candidates"], parse_tiktok_discount_percent
            ),
            sold_count=self._reconcile_scalar(
                payload["sold_count_candidates"], parse_tiktok_pdp_sold_count
            ),
            rating=self._reconcile_scalar(
                payload["rating_candidates"], parse_tiktok_rating
            ),
            review_count=self._reconcile_scalar(
                payload["review_count_candidates"], parse_tiktok_pdp_review_count
            ),
        )
        return TikTokPdpCollectionResult(
            snapshot=snapshot,
            binding=TikTokPdpBindingReceipt(
                requested_url=requested_url,
                observed_url=observed_url,
                identity_bases=identity_bases,
            ),
        )

    @staticmethod
    def _admit_payload(raw: Any) -> dict[str, Any]:
        if not isinstance(raw, Mapping):
            raise TikTokPdpExtractionError("PDP extraction did not return a mapping")
        if set(raw) - _EXTRACTION_KEYS:
            raise TikTokPdpExtractionError("PDP extraction returned fields outside the V1 boundary")
        if "observed_url" not in raw or "access_state" not in raw:
            raise TikTokPdpExtractionError("PDP extraction omitted required transport state")

        payload = dict(raw)
        for key in _CANDIDATE_KEYS:
            value = payload.get(key, [])
            if not isinstance(value, (list, tuple)) or any(
                not isinstance(item, (str, int, float)) or isinstance(item, bool)
                for item in value
            ):
                raise TikTokPdpExtractionError(f"{key} must be a bounded scalar candidate list")
            payload[key] = tuple(str(item).strip() for item in value if str(item).strip())
        if not isinstance(payload["observed_url"], str) or not isinstance(
            payload["access_state"], str
        ):
            raise TikTokPdpExtractionError("observed URL and access state must be strings")
        return payload

    @staticmethod
    def _admit_identity(
        *,
        requested_id: str,
        observed_url: str,
        explicit_candidates: Sequence[str],
    ) -> tuple[TikTokPdpIdentityBasis, ...]:
        parsed = TikTokPdpCollector._validate_tiktok_url(observed_url, label="observed")
        if parsed.path.rstrip("/").lower() in {"", "/shop", "/discover", "/feed"}:
            raise TikTokPdpIdentityError("observed URL is an unrelated TikTok page")

        bases: list[TikTokPdpIdentityBasis] = []
        observed_url_id = extract_tiktok_product_id(observed_url)
        if observed_url_id is not None:
            bases.append(TikTokPdpIdentityBasis("OBSERVED_URL", observed_url_id))

        for candidate in explicit_candidates:
            explicit_id = extract_tiktok_product_id(None, item_id_attr=candidate)
            if explicit_id is None:
                raise TikTokPdpIdentityError("an explicit current-product ID is malformed")
            basis = TikTokPdpIdentityBasis("EXPLICIT_CURRENT_PRODUCT_ID", explicit_id)
            if basis not in bases:
                bases.append(basis)

        if not bases:
            raise TikTokPdpIdentityError("no observed product identity could be established")
        if any(basis.source_product_id != requested_id for basis in bases):
            raise TikTokPdpIdentityError("requested and observed product identities disagree")
        return tuple(bases)

    @staticmethod
    def _validate_tiktok_url(url: str, *, label: str) -> Any:
        try:
            parsed = urlsplit(url)
            host = (parsed.hostname or "").lower()
        except ValueError as exc:
            raise TikTokPdpIdentityError(f"{label} URL is malformed") from exc
        if parsed.scheme.lower() not in {"http", "https"} or not (
            host == "tiktok.com" or host.endswith(".tiktok.com")
        ):
            raise TikTokPdpIdentityError(f"{label} URL is not a TikTok page")
        path = parsed.path.lower()
        if any(marker in path for marker in ("/login", "/search", "/challenge", "/captcha")):
            raise TikTokPdpIdentityError(f"{label} URL is not an exact public PDP")
        return parsed

    @staticmethod
    def _reconcile_text(candidates: Sequence[str]) -> Optional[str]:
        unique: dict[str, str] = {}
        for candidate in candidates:
            normalized = " ".join(candidate.split())
            if normalized:
                unique.setdefault(normalized.casefold(), normalized)
        if len(unique) != 1:
            return None
        return next(iter(unique.values()))

    @staticmethod
    def _reconcile_scalar(candidates: Sequence[str], parser: Any) -> Any:
        admitted = {value for candidate in candidates if (value := parser(candidate)) is not None}
        if len(admitted) != 1:
            return None
        return next(iter(admitted))

    @staticmethod
    def _reconcile_price(candidates: Sequence[str], parser: Any) -> Optional[float]:
        if not candidates:
            return None
        parsed = tuple(parser(candidate) for candidate in candidates)
        if any(value is None for value in parsed):
            return None
        admitted = set(parsed)
        if len(admitted) != 1:
            return None
        return next(iter(admitted))


__all__ = [
    "TIKTOK_PDP_EXTRACTION_SCRIPT",
    "TikTokPdpBindingReceipt",
    "TikTokPdpBlockedOrLoginError",
    "TikTokPdpCollectionError",
    "TikTokPdpCollectionResult",
    "TikTokPdpCollector",
    "TikTokPdpExtractionError",
    "TikTokPdpFailureCode",
    "TikTokPdpIdentityBasis",
    "TikTokPdpIdentityError",
]
