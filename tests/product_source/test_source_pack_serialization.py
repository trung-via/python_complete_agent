"""TASK-125 regressions for strict typed Product Source Pack rehydration."""

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
import json

import pytest

from src.product_source.models import (
    MediaProvenance,
    MediaRole,
    OriginalMediaRef,
    ProductFact,
    ProductSourcePack,
    sanitize_url,
)
from src.product_source.serialization import (
    deserialize_product_source_pack,
    deserialize_source_pack,
    serialize_source_pack,
)


def _representative_pack() -> ProductSourcePack:
    return ProductSourcePack(
        source_pack_id="pack-v1",
        platform="test-market",
        product_url="https://market.example/item/1?utm_source=campaign&keep=yes",
        observed_at=datetime(
            2026,
            8,
            31,
            12,
            30,
            15,
            123456,
            tzinfo=timezone(timedelta(hours=7)),
        ),
        collector="collector-v1",
        title="Exact Seller Title",
        source_product_id="listing-1",
        shop_name=None,
        brand="Observed Brand",
        model_sku=None,
        description_text="Seller description",
        facts=(
            ProductFact("Color", "Red", "specifications", "table"),
            ProductFact("Color", "Red", "specifications", "table"),
            ProductFact("Color", "Blue", "description", "seller_text", "tone"),
        ),
        media=(
            OriginalMediaRef(
                source_url="https://cdn.example/primary.webp?signature=secret&keep=1",
                platform="test-market",
                role=MediaRole.PRIMARY,
                provenance=MediaProvenance.STRUCTURED_PRODUCT_DATA,
                ordinal=0,
                alt_text="Primary view",
                variant_label=None,
                content_type="image/webp",
                byte_size=101,
                sha256_hash="a" * 64,
                perceptual_hash="0123456789abcdef",
                local_filename="orig_000_aaaaaaaaaaaa.webp",
            ),
            OriginalMediaRef(
                source_url="https://cdn.example/variant.webp",
                platform="test-market",
                role=MediaRole.VARIANT,
                provenance=MediaProvenance.SEMANTIC_VARIANT_MEDIA,
                ordinal=1,
                alt_text=None,
                variant_label="Blue",
                content_type=None,
                byte_size=None,
                sha256_hash=None,
                perceptual_hash=None,
                local_filename=None,
            ),
        ),
        diagnostic_codes=("FIRST", "SECOND", "FIRST"),
    )


def _persisted_equivalent(pack: ProductSourcePack) -> ProductSourcePack:
    return ProductSourcePack(
        source_pack_id=pack.source_pack_id,
        platform=pack.platform,
        product_url=sanitize_url(pack.product_url),
        observed_at=pack.observed_at,
        collector=pack.collector,
        title=pack.title,
        source_product_id=pack.source_product_id,
        shop_name=pack.shop_name,
        brand=pack.brand,
        model_sku=pack.model_sku,
        description_text=pack.description_text,
        facts=pack.facts,
        media=tuple(
            OriginalMediaRef(
                source_url=sanitize_url(item.source_url),
                platform=item.platform,
                role=item.role,
                provenance=item.provenance,
                ordinal=item.ordinal,
                alt_text=item.alt_text,
                variant_label=item.variant_label,
                content_type=item.content_type,
                byte_size=item.byte_size,
                sha256_hash=item.sha256_hash,
                perceptual_hash=item.perceptual_hash,
                local_filename=item.local_filename,
            )
            for item in pack.media
        ),
        diagnostic_codes=pack.diagnostic_codes,
    )


def test_v1_round_trip_is_typed_immutable_ordered_and_deterministic(tmp_path):
    original = _representative_pack()
    path = serialize_source_pack(original, str(tmp_path / "source"))

    raw = deserialize_source_pack(path)
    first = deserialize_product_source_pack(path)
    second = deserialize_product_source_pack(path)

    assert type(raw) is dict
    assert raw["schema_version"] == "1.0"
    assert raw["product_url"] == sanitize_url(original.product_url)
    assert first == second == _persisted_equivalent(original)
    assert first is not second and first is not original
    assert type(first) is ProductSourcePack
    assert first.observed_at.utcoffset() == timedelta(hours=7)
    assert first.facts == original.facts
    assert len(first.facts) == 3
    assert [fact.value for fact in first.facts] == ["Red", "Red", "Blue"]
    assert first.media[0].role is MediaRole.PRIMARY
    assert first.media[1].provenance is MediaProvenance.SEMANTIC_VARIANT_MEDIA
    assert [item.ordinal for item in first.media] == [0, 1]
    assert first.media[1].alt_text is None
    assert first.diagnostic_codes == ("FIRST", "SECOND", "FIRST")
    with pytest.raises(FrozenInstanceError):
        first.collector = "changed"


def test_raw_dict_compatibility_and_serialized_v1_shape_are_unchanged(tmp_path):
    path = serialize_source_pack(_representative_pack(), str(tmp_path / "source"))
    raw = deserialize_source_pack(path)

    assert raw == json.loads((tmp_path / "source" / "source_pack.json").read_text("utf-8"))
    assert set(raw) == {
        "schema_version",
        "source_pack_id",
        "platform",
        "product_url",
        "observed_at",
        "collector",
        "title",
        "source_product_id",
        "shop_name",
        "brand",
        "model_sku",
        "description_text",
        "facts",
        "media",
        "diagnostic_codes",
    }
    assert raw["shop_name"] is None
    assert raw["model_sku"] is None
    assert raw["media"][1]["byte_size"] is None


def _valid_manifest() -> dict:
    pack = _representative_pack()
    return {"schema_version": "1.0", **pack.to_dict()}


def _write_manifest(tmp_path, value) -> str:
    path = tmp_path / "source_pack.json"
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    return str(path)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda root: root.pop("schema_version"),
        lambda root: root.update(schema_version="2.0"),
        lambda root: root.update(unknown=True),
        lambda root: root.pop("collector"),
        lambda root: root.update(source_pack_id=1),
        lambda root: root.update(source_pack_id=""),
        lambda root: root.update(platform=False),
        lambda root: root.update(product_url="ftp://market.example/item/1"),
        lambda root: root.update(product_url="https://"),
        lambda root: root.update(observed_at="2026-08-31T12:30:15"),
        lambda root: root.update(observed_at="2026-08-31T05:30:15Z"),
        lambda root: root.update(observed_at=7),
        lambda root: root.update(title=[]),
        lambda root: root.update(description_text="x" * 10001),
        lambda root: root.update(facts={}),
        lambda root: root["facts"].append("fact"),
        lambda root: root["facts"][0].pop("unit"),
        lambda root: root["facts"][0].update(extra="value"),
        lambda root: root["facts"][0].update(key=" "),
        lambda root: root["facts"][0].update(value=False),
        lambda root: root.update(media={}),
        lambda root: root["media"].append([]),
        lambda root: root["media"][0].pop("alt_text"),
        lambda root: root["media"][0].update(extra="value"),
        lambda root: root["media"][0].update(source_url="file:///tmp/image"),
        lambda root: root["media"][0].update(role="UNKNOWN"),
        lambda root: root["media"][0].update(provenance="UNKNOWN"),
        lambda root: root["media"][0].update(ordinal=True),
        lambda root: root["media"][0].update(ordinal=-1),
        lambda root: root["media"][0].update(byte_size=0),
        lambda root: root["media"][0].update(byte_size=True),
        lambda root: root["media"][0].update(sha256_hash="not-a-digest"),
        lambda root: root["media"][0].update(perceptual_hash="not-hex"),
        lambda root: root.update(diagnostic_codes="code"),
        lambda root: root.update(diagnostic_codes=["ok", None]),
    ],
)
def test_typed_rehydration_rejects_malformed_or_noncanonical_v1(tmp_path, mutate):
    root = _valid_manifest()
    mutate(root)
    path = _write_manifest(tmp_path, root)

    with pytest.raises((TypeError, ValueError)):
        deserialize_product_source_pack(path)


@pytest.mark.parametrize("root", [None, [], "manifest", 1, True])
def test_typed_rehydration_rejects_non_object_roots(tmp_path, root):
    with pytest.raises(ValueError):
        deserialize_product_source_pack(_write_manifest(tmp_path, root))


def test_typed_rehydration_rejects_duplicate_keys_at_every_object_level(tmp_path):
    duplicate_documents = (
        '{"schema_version":"1.0","schema_version":"1.0"}',
        '{"fact":{"key":"a","key":"b"}}',
        '{"media":{"role":"PRIMARY","role":"GALLERY"}}',
    )
    for index, document in enumerate(duplicate_documents):
        path = tmp_path / f"duplicate-{index}.json"
        path.write_text(document, encoding="utf-8")
        with pytest.raises(ValueError, match="duplicate JSON object key"):
            deserialize_product_source_pack(str(path))


def test_typed_rehydration_rejects_nonstandard_json_constants(tmp_path):
    root = _valid_manifest()
    document = json.dumps(root).replace('"ordinal": 0', '"ordinal": NaN', 1)
    path = tmp_path / "constant.json"
    path.write_text(document, encoding="utf-8")

    with pytest.raises(ValueError, match="non-standard JSON constant"):
        deserialize_product_source_pack(str(path))
