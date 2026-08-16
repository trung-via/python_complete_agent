from __future__ import annotations

import hashlib
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
import pytest

from src.product_source.models import (
    MediaProvenance,
    MediaRole,
    OriginalMediaRef,
    ProductFact,
    ProductSourcePack,
    SourcePackBlockedError,
    SourcePackError,
    SourcePackExtractionError,
    SourcePackNavigationError,
    build_source_pack_id,
    canonicalize_url,
    sanitize_url,
)


def test_build_source_pack_id_with_product_id():
    """1. Deterministic source_pack_id with product_id."""
    assert build_source_pack_id("shopee", "12345", "https://shopee.vn/product/1/12345") == "shopee_12345"


def test_build_source_pack_id_fallback_url():
    """2. URL-fingerprint fallback when product_id is None."""
    url = "https://shopee.vn/item-without-id"
    result = build_source_pack_id("shopee", None, url)
    assert result.startswith("shopee_")
    assert len(result) > len("shopee_")


def test_build_source_pack_id_determinism():
    """3. Same inputs produce same ID (determinism)."""
    assert build_source_pack_id("tiktok", "999", "http://a") == build_source_pack_id(
        "tiktok", "999", "http://a"
    )
    assert build_source_pack_id("tiktok", None, "http://a") == build_source_pack_id(
        "tiktok", None, "http://a"
    )


def test_build_source_pack_id_ignores_tracking_and_auth_noise():
    """4. URL-fingerprint ignores tracking query parameters for identity stability."""
    url1 = "https://shopee.vn/product-name?sp_atk=12345&utm_source=facebook"
    url2 = "https://shopee.vn/product-name?utm_source=google&token=secret123"
    id1 = build_source_pack_id("shopee", None, url1)
    id2 = build_source_pack_id("shopee", None, url2)
    assert id1 == id2


def test_sanitize_url_redacts_sensitive_parameters():
    """5. sanitize_url redacts tokens, auth, signatures, and sessions."""
    url = "https://cf.shopee.vn/file/img.jpg?token=secret_token_123&auth=bearer_xyz&signature=sig456&valid=1"
    sanitized = sanitize_url(url)
    assert "secret_token_123" not in sanitized
    assert "bearer_xyz" not in sanitized
    assert "sig456" not in sanitized
    assert "token=%5BREDACTED%5D" in sanitized or "token=[REDACTED]" in sanitized
    assert "valid=1" in sanitized


def test_product_fact_validation():
    """6. ProductFact validation: Empty key or value raises ValueError."""
    with pytest.raises(ValueError):
        ProductFact(key="", value="val", source_section="desc", provenance="strategy")
    with pytest.raises(ValueError):
        ProductFact(key="key", value="", source_section="desc", provenance="strategy")


def test_product_fact_frozen():
    """7. ProductFact frozen: Cannot modify attributes after creation."""
    fact = ProductFact(key="Brand", value="Acme", source_section="desc", provenance="strategy")
    with pytest.raises((FrozenInstanceError, AttributeError)):
        fact.key = "NewBrand"


def test_original_media_ref_validation():
    """8. OriginalMediaRef validation."""
    with pytest.raises(ValueError, match="http"):
        OriginalMediaRef(
            source_url="ftp://abc.com/img.jpg",
            platform="shopee",
            role=MediaRole.PRIMARY,
            provenance=MediaProvenance.SEMANTIC_PRODUCT_GALLERY,
            ordinal=0,
        )
    with pytest.raises(ValueError, match="ordinal"):
        OriginalMediaRef(
            source_url="http://abc.com/img.jpg",
            platform="shopee",
            role=MediaRole.PRIMARY,
            provenance=MediaProvenance.SEMANTIC_PRODUCT_GALLERY,
            ordinal=-1,
        )
    with pytest.raises(ValueError, match="byte_size"):
        OriginalMediaRef(
            source_url="http://abc.com/img.jpg",
            platform="shopee",
            role=MediaRole.PRIMARY,
            provenance=MediaProvenance.SEMANTIC_PRODUCT_GALLERY,
            ordinal=0,
            byte_size=-5,
        )


def test_product_source_pack_validation():
    """9. ProductSourcePack validation."""
    with pytest.raises(ValueError):
        ProductSourcePack(
            source_pack_id="",
            platform="shopee",
            product_url="http://a",
            observed_at=datetime.now(timezone.utc),
            collector="test",
        )
    with pytest.raises(ValueError):
        ProductSourcePack(
            source_pack_id="id",
            platform="",
            product_url="http://a",
            observed_at=datetime.now(timezone.utc),
            collector="test",
        )


def test_description_text_bounded():
    """10. Description text bounded: Text > 10000 chars is truncated."""
    long_desc = "a" * 15000
    pack = ProductSourcePack(
        source_pack_id="id",
        platform="shopee",
        product_url="http://a",
        observed_at=datetime.now(timezone.utc),
        collector="test",
        description_text=long_desc,
    )
    assert len(pack.description_text) <= 10000


def test_facts_media_auto_converted_to_tuples():
    """11. Facts/media auto-converted to tuples."""
    fact = ProductFact(key="k", value="v", source_section="s", provenance="p")
    media = OriginalMediaRef(
        source_url="https://img.com/1.jpg",
        platform="shopee",
        role=MediaRole.PRIMARY,
        provenance=MediaProvenance.STRUCTURED_PRODUCT_DATA,
        ordinal=0,
    )
    pack = ProductSourcePack(
        source_pack_id="id",
        platform="shopee",
        product_url="https://example.com",
        observed_at=datetime.now(timezone.utc),
        collector="test",
        facts=[fact],
        media=[media],
        diagnostic_codes=["CODE1"],
    )
    assert isinstance(pack.facts, tuple)
    assert isinstance(pack.media, tuple)
    assert isinstance(pack.diagnostic_codes, tuple)


def test_product_source_pack_to_dict_secret_safe():
    """12. ProductSourcePack.to_dict(): Produces clean dict with redacted credentials."""
    media = OriginalMediaRef(
        source_url="https://cdn.shopee.vn/img.jpg?token=secret123&session=user999",
        platform="shopee",
        role=MediaRole.VARIANT,
        provenance=MediaProvenance.SEMANTIC_VARIANT_MEDIA,
        ordinal=0,
        variant_label="Red / XL",
    )
    pack = ProductSourcePack(
        source_pack_id="id",
        platform="shopee",
        product_url="https://example.com/item?auth=bearer_token_xyz",
        observed_at=datetime(2026, 8, 16, 12, 0, 0, tzinfo=timezone.utc),
        collector="test",
        title="Test Product",
        media=[media],
        description_text="Clean text description",
    )
    d = pack.to_dict()
    assert "secret123" not in str(d)
    assert "bearer_token_xyz" not in str(d)
    assert "user999" not in str(d)
    assert d["media"][0]["variant_label"] == "Red / XL"
    assert d["media"][0]["role"] == "VARIANT"


def test_enums_values():
    """13. MediaRole and MediaProvenance enums have correct values."""
    assert MediaRole.PRIMARY.value == "PRIMARY"
    assert MediaRole.GALLERY.value == "GALLERY"
    assert MediaRole.VARIANT.value == "VARIANT"
    assert MediaRole.SELLER_DESCRIPTION.value == "SELLER_DESCRIPTION"

    assert MediaProvenance.STRUCTURED_PRODUCT_DATA.value == "STRUCTURED_PRODUCT_DATA"
    assert MediaProvenance.SEMANTIC_PRODUCT_GALLERY.value == "SEMANTIC_PRODUCT_GALLERY"
    assert MediaProvenance.SEMANTIC_VARIANT_MEDIA.value == "SEMANTIC_VARIANT_MEDIA"
    assert MediaProvenance.SEMANTIC_SELLER_DESCRIPTION.value == "SEMANTIC_SELLER_DESCRIPTION"
    assert MediaProvenance.PLATFORM_SCOPED_FALLBACK.value == "PLATFORM_SCOPED_FALLBACK"


def test_error_hierarchy():
    """14. Error hierarchy."""
    assert issubclass(SourcePackExtractionError, SourcePackError)
    assert issubclass(SourcePackBlockedError, SourcePackError)
    assert issubclass(SourcePackNavigationError, SourcePackError)
