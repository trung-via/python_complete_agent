from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone

import pytest

from src.product_intelligence.entity_resolution import ProductRelationship, resolve_products
from src.product_source.models import MediaProvenance, MediaRole, OriginalMediaRef, ProductFact, ProductSourcePack


def fact(key: str, value: str) -> ProductFact:
    return ProductFact(key, value, "specifications", "structured")


def pack(identifier: str, platform: str = "shopee", **kwargs) -> ProductSourcePack:
    return ProductSourcePack(
        source_pack_id=f"{platform}_{identifier}", platform=platform,
        product_url=f"https://{platform}.example/{identifier}",
        source_product_id=identifier, observed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        collector="test", **kwargs,
    )


def identity_facts(color: str = "Black") -> tuple[ProductFact, ...]:
    return (fact("Brand", "Acme"), fact("Model", "Phone X"), fact("Color", color))


def test_cross_platform_exact_variant_is_immutable_and_symmetric():
    left = pack("11", facts=identity_facts(), shop_name="one")
    right = pack("99", platform="tiktok", facts=identity_facts(), shop_name="two")
    result = resolve_products(left, right)
    reverse = resolve_products(right, left)
    assert result.relationship is ProductRelationship.EXACT_VARIANT_MATCH
    assert (result.relationship, result.confidence) == (reverse.relationship, reverse.confidence)
    assert result.left.source_pack_id == left.source_pack_id
    with pytest.raises(FrozenInstanceError):
        result.confidence = 0.0


def test_repeated_listing_observations_keep_distinct_identity_and_symmetric_decision():
    earlier = pack("11", facts=identity_facts())
    later = replace(earlier, observed_at=datetime(2026, 1, 2, tzinfo=timezone.utc))

    result = resolve_products(earlier, later)
    reverse = resolve_products(later, earlier)

    assert result.left.source_pack_id == result.right.source_pack_id
    assert result.left.observed_at != result.right.observed_at
    assert result.left == reverse.right
    assert result.right == reverse.left
    assert (result.relationship, result.confidence) == (reverse.relationship, reverse.confidence)


def test_same_family_different_variant_and_missing_variant():
    assert resolve_products(pack("1", facts=identity_facts("Black")), pack("2", facts=identity_facts("White"))).relationship is ProductRelationship.SAME_PRODUCT_FAMILY
    family_only = (fact("Brand", "Acme"), fact("Model", "Phone X"))
    assert resolve_products(pack("3", facts=family_only), pack("4", facts=family_only)).relationship is ProductRelationship.SAME_PRODUCT_FAMILY


def test_reliable_family_and_bundle_conflicts_win_over_weak_similarity():
    one = pack("1", title="Popular phone single unit", facts=(fact("Brand", "Acme"), fact("Model", "X")))
    other = pack("2", title="Popular phone 2 pack", facts=(fact("Brand", "Other"), fact("Model", "Y")))
    assert resolve_products(one, other).relationship is ProductRelationship.DIFFERENT_PRODUCT


def test_single_item_versus_multipack_is_different_product():
    family = (fact("Brand", "Acme"), fact("Model", "X"))
    one = pack("1", title="Acme X single unit", facts=family)
    multi = pack("2", title="Acme X 3 pack", facts=family)
    assert resolve_products(one, multi).relationship is ProductRelationship.DIFFERENT_PRODUCT


def test_sparse_media_and_cross_platform_identifier_text_are_uncertain():
    media = (OriginalMediaRef("https://img.example/a.jpg", "shopee", MediaRole.PRIMARY,
                              MediaProvenance.STRUCTURED_PRODUCT_DATA, 0, sha256_hash="a" * 64),)
    left = pack("same", title="Thing", media=media, model_sku="SKU-1")
    right_media = (OriginalMediaRef("https://img.example/b.jpg", "tiktok", MediaRole.PRIMARY,
                                    MediaProvenance.STRUCTURED_PRODUCT_DATA, 0, sha256_hash="a" * 64),)
    right = pack("same", platform="tiktok", title="Thing", media=right_media, model_sku="SKU-1")
    result = resolve_products(left, right)
    assert result.relationship is ProductRelationship.UNCERTAIN
    assert 0.0 <= result.confidence <= 1.0


def test_authoritative_identifier_conflict_is_different_product():
    left = pack("1", title="same", facts=(fact("GTIN", "111"),))
    right = pack("2", title="same", facts=(fact("GTIN", "222"),))
    assert resolve_products(left, right).relationship is ProductRelationship.DIFFERENT_PRODUCT
