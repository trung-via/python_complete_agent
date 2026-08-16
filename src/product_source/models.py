from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Any
from datetime import datetime
import hashlib
import urllib.parse

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

@dataclass(frozen=True)
class ProductFact:
    key: str
    value: str
    source_section: str
    provenance: str
    unit: Optional[str] = None

    def __post_init__(self):
        if not self.key:
            raise ValueError("key cannot be empty")
        if not self.value:
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
    if source_product_id:
        return f"{platform}_{source_product_id}"
    parsed = urllib.parse.urlparse(product_url)
    canonical_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    if parsed.query:
        canonical_url += f"?{parsed.query}"
    url_hash = hashlib.sha256(canonical_url.encode('utf-8')).hexdigest()
    return f"{platform}_{url_hash}"

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
        
        # Bypass frozen dataclass to set attributes
        if self.description_text is not None and len(self.description_text) > 10000:
            object.__setattr__(self, 'description_text', self.description_text[:10000])
        
        if not isinstance(self.facts, tuple):
            object.__setattr__(self, 'facts', tuple(self.facts))
            
        if not isinstance(self.media, tuple):
            object.__setattr__(self, 'media', tuple(self.media))
            
        if not isinstance(self.diagnostic_codes, tuple):
            object.__setattr__(self, 'diagnostic_codes', tuple(self.diagnostic_codes))

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_pack_id": self.source_pack_id,
            "platform": self.platform,
            "product_url": self.product_url,
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
                    "provenance": f.provenance
                }
                for f in self.facts
            ],
            "media": [
                {
                    "source_url": m.source_url,
                    "platform": m.platform,
                    "role": m.role.value if hasattr(m.role, 'value') else m.role,
                    "provenance": m.provenance.value if hasattr(m.provenance, 'value') else m.provenance,
                    "ordinal": m.ordinal,
                    "alt_text": m.alt_text,
                    "variant_label": m.variant_label,
                    "content_type": m.content_type,
                    "byte_size": m.byte_size,
                    "sha256_hash": m.sha256_hash,
                    "perceptual_hash": m.perceptual_hash,
                    "local_filename": m.local_filename
                }
                for m in self.media
            ],
            "diagnostic_codes": list(self.diagnostic_codes)
        }
