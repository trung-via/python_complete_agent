from __future__ import annotations

import hashlib
import re
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class MediaRole(Enum):
    PRIMARY = "PRIMARY"
    GALLERY = "GALLERY"
    VARIANT = "VARIANT"
    SELLER_DESCRIPTION = "SELLER_DESCRIPTION"


class MediaProvenance(Enum):
    STRUCTURED_PRODUCT_DATA = "STRUCTURED_PRODUCT_DATA"
    SEMANTIC_PRODUCT_GALLERY = "SEMANTIC_PRODUCT_GALLERY"
    SEMANTIC_VARIANT_MEDIA = "SEMANTIC_VARIANT_MEDIA"
    SEMANTIC_SELLER_DESCRIPTION = "SEMANTIC_SELLER_DESCRIPTION"
    PLATFORM_SCOPED_FALLBACK = "PLATFORM_SCOPED_FALLBACK"


import re

SENSITIVE_QUERY_PATTERNS = re.compile(
    r"(token|auth|sign|sig|session|cred|credential|key|secret|expire|ticket|pass|policy)",
    re.IGNORECASE
)
TRACKING_QUERY_PATTERNS = re.compile(
    r"(spm|utm_|gclid|fbclid)",
    re.IGNORECASE
)

def _is_sensitive_query_key(k: str) -> bool:
    lk = k.lower()
    return bool(SENSITIVE_QUERY_PATTERNS.search(lk) or TRACKING_QUERY_PATTERNS.search(lk))


def sanitize_url(url: str) -> str:
    """
    Sanitizes URL by redacting sensitive, auth-like, or tracking query parameters.
    Used for safe serialization and diagnostic logging.
    """
    if not url:
        return ""
    try:
        parsed = urllib.parse.urlparse(url)
        if not parsed.query:
            return url
        params = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        sanitized_params = []
        for k, v in params:
            if _is_sensitive_query_key(k):
                sanitized_params.append((k, "[REDACTED]"))
            else:
                sanitized_params.append((k, v))
        new_query = urllib.parse.urlencode(sanitized_params)
        return urllib.parse.urlunparse((
            parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment
        ))
    except Exception:
        return url


def canonicalize_url(url: str) -> str:
    """
    Canonicalizes product URL for deterministic fingerprinting.
    Strips noise, query parameters, tracking tags, and trailing slashes.
    """
    if not url:
        return ""
    try:
        parsed = urllib.parse.urlparse(url.strip())
        clean_path = parsed.path.rstrip("/")
        return urllib.parse.urlunparse((
            parsed.scheme.lower(), parsed.netloc.lower(), clean_path, "", "", ""
        ))
    except Exception:
        return url.strip().split("?")[0].rstrip("/")


@dataclass(frozen=True)
class ProductFact:
    key: str
    value: str
    source_section: str
    provenance: str
    unit: Optional[str] = None

    def __post_init__(self):
        if not self.key or not self.key.strip():
            raise ValueError("key cannot be empty")
        if not self.value or not self.value.strip():
            raise ValueError("value cannot be empty")


@dataclass(frozen=True)
class OriginalMediaRef:
    source_url: str
    platform: str
    role: MediaRole
    provenance: MediaProvenance
    ordinal: int
    alt_text: Optional[str] = None
    variant_label: Optional[str] = None
    content_type: Optional[str] = None
    byte_size: Optional[int] = None
    sha256_hash: Optional[str] = None
    perceptual_hash: Optional[str] = None
    local_filename: Optional[str] = None

    def __post_init__(self):
        if not self.source_url.startswith(("http://", "https://")):
            raise ValueError("source_url must start with http:// or https://")
        if self.ordinal < 0:
            raise ValueError("ordinal must be >= 0")
        if self.byte_size is not None and self.byte_size <= 0:
            raise ValueError("byte_size must be > 0 if set")


def build_source_pack_id(platform: str, source_product_id: Optional[str], product_url: str) -> str:
    """
    Builds deterministic source_pack_id from platform + product_id or canonicalized URL hash.
    Never uses Python hash().
    """
    if source_product_id and source_product_id.strip():
        return f"{platform.lower()}_{source_product_id.strip()}"
    canonical_url = canonicalize_url(product_url)
    url_hash = hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()[:16]
    return f"{platform.lower()}_{url_hash}"


class SourcePackError(Exception):
    """Base exception for source pack operations."""


class SourcePackExtractionError(SourcePackError):
    """Extraction failures."""


class SourcePackBlockedError(SourcePackError):
    """Anti-bot/captcha."""


class SourcePackNavigationError(SourcePackError):
    """Navigation failures."""


@dataclass(frozen=True)
class ProductSourcePack:
    source_pack_id: str
    platform: str
    product_url: str
    observed_at: datetime
    collector: str
    title: Optional[str] = None
    source_product_id: Optional[str] = None
    shop_name: Optional[str] = None
    brand: Optional[str] = None
    model_sku: Optional[str] = None
    description_text: Optional[str] = None
    facts: tuple[ProductFact, ...] = field(default_factory=tuple)
    media: tuple[OriginalMediaRef, ...] = field(default_factory=tuple)
    diagnostic_codes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self):
        if not self.source_pack_id:
            raise ValueError("source_pack_id cannot be empty")
        if not self.platform:
            raise ValueError("platform cannot be empty")
        if not self.product_url.startswith(("http://", "https://")):
            raise ValueError("product_url must start with http")

        if self.description_text is not None and len(self.description_text) > 10000:
            object.__setattr__(self, "description_text", self.description_text[:10000])

        if not isinstance(self.facts, tuple):
            object.__setattr__(self, "facts", tuple(self.facts))

        if not isinstance(self.media, tuple):
            object.__setattr__(self, "media", tuple(self.media))

        if not isinstance(self.diagnostic_codes, tuple):
            object.__setattr__(self, "diagnostic_codes", tuple(self.diagnostic_codes))

    def to_dict(self) -> dict[str, Any]:
        """
        Serializes to a clean, secret-safe dictionary.
        All URLs are sanitized (credentials/tokens redacted).
        """
        return {
            "source_pack_id": self.source_pack_id,
            "platform": self.platform,
            "product_url": sanitize_url(self.product_url),
            "observed_at": self.observed_at.isoformat() if self.observed_at else None,
            "collector": self.collector,
            "title": self.title,
            "source_product_id": self.source_product_id,
            "shop_name": self.shop_name,
            "brand": self.brand,
            "model_sku": self.model_sku,
            "description_text": self.description_text[:10000] if self.description_text else None,
            "facts": [
                {
                    "key": f.key,
                    "value": f.value,
                    "unit": f.unit,
                    "source_section": f.source_section,
                    "provenance": f.provenance,
                }
                for f in self.facts
            ],
            "media": [
                {
                    "source_url": sanitize_url(m.source_url),
                    "platform": m.platform,
                    "role": m.role.value if hasattr(m.role, "value") else str(m.role),
                    "provenance": m.provenance.value if hasattr(m.provenance, "value") else str(m.provenance),
                    "ordinal": m.ordinal,
                    "alt_text": m.alt_text,
                    "variant_label": m.variant_label,
                    "content_type": m.content_type,
                    "byte_size": m.byte_size,
                    "sha256_hash": m.sha256_hash,
                    "perceptual_hash": m.perceptual_hash,
                    "local_filename": m.local_filename,
                }
                for m in self.media
            ],
            "diagnostic_codes": list(self.diagnostic_codes),
        }
