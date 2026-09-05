from __future__ import annotations

from datetime import datetime
import json
import os
import re
from typing import Any
from urllib.parse import urlsplit

from .models import (
    MediaProvenance,
    MediaRole,
    OriginalMediaRef,
    ProductFact,
    ProductSourcePack,
)


_SCHEMA_VERSION = "1.0"
_ROOT_FIELDS = frozenset(
    {
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
)
_FACT_FIELDS = frozenset(
    {"key", "value", "unit", "source_section", "provenance"}
)
_MEDIA_FIELDS = frozenset(
    {
        "source_url",
        "platform",
        "role",
        "provenance",
        "ordinal",
        "alt_text",
        "variant_label",
        "content_type",
        "byte_size",
        "sha256_hash",
        "perceptual_hash",
        "local_filename",
    }
)
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_PERCEPTUAL_HASH_RE = re.compile(r"[0-9a-f]+")


def serialize_source_pack(pack: ProductSourcePack, output_dir: str) -> str:
    os.makedirs(os.path.join(output_dir, 'original'), exist_ok=True)
    out_path = os.path.join(output_dir, 'source_pack.json')
    data = {
        "schema_version": "1.0",
        **pack.to_dict()
    }
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, sort_keys=True, indent=2, ensure_ascii=False)
    return out_path


def deserialize_source_pack(path: str) -> dict[str, Any]:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def deserialize_product_source_pack(path: str) -> ProductSourcePack:
    """Strictly rehydrate one exact V1 manifest as a ``ProductSourcePack``.

    This is the typed compatibility boundary.  ``deserialize_source_pack``
    deliberately remains the historical raw-dict operation.
    """

    with open(path, "r", encoding="utf-8") as manifest:
        root = json.load(
            manifest,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_json_constant,
        )

    _require_object(root, "manifest", _ROOT_FIELDS)
    if _require_str(root["schema_version"], "schema_version") != _SCHEMA_VERSION:
        raise ValueError("unsupported source-pack schema_version")

    observed_at = _decode_observed_at(root["observed_at"])
    facts_value = root["facts"]
    if type(facts_value) is not list:
        raise ValueError("facts must be an exact JSON array")
    facts = tuple(_decode_fact(value, index) for index, value in enumerate(facts_value))

    media_value = root["media"]
    if type(media_value) is not list:
        raise ValueError("media must be an exact JSON array")
    media = tuple(
        _decode_media(value, index) for index, value in enumerate(media_value)
    )

    diagnostics_value = root["diagnostic_codes"]
    if type(diagnostics_value) is not list:
        raise ValueError("diagnostic_codes must be an exact JSON array")
    diagnostic_codes = tuple(
        _require_str(value, f"diagnostic_codes[{index}]")
        for index, value in enumerate(diagnostics_value)
    )

    description_text = _optional_str(root["description_text"], "description_text")
    if description_text is not None and len(description_text) > 10000:
        raise ValueError("description_text exceeds the V1 persisted limit")

    return ProductSourcePack(
        source_pack_id=_require_str(root["source_pack_id"], "source_pack_id"),
        platform=_require_str(root["platform"], "platform"),
        product_url=_require_url(root["product_url"], "product_url"),
        observed_at=observed_at,
        collector=_require_str(root["collector"], "collector"),
        title=_optional_str(root["title"], "title"),
        source_product_id=_optional_str(
            root["source_product_id"], "source_product_id"
        ),
        shop_name=_optional_str(root["shop_name"], "shop_name"),
        brand=_optional_str(root["brand"], "brand"),
        model_sku=_optional_str(root["model_sku"], "model_sku"),
        description_text=description_text,
        facts=facts,
        media=media,
        diagnostic_codes=diagnostic_codes,
    )


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant is not permitted: {value}")


def _require_object(value: Any, name: str, fields: frozenset[str]) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError(f"{name} must be an exact JSON object")
    actual = frozenset(value)
    if actual != fields:
        missing = sorted(fields - actual)
        unknown = sorted(actual - fields)
        raise ValueError(
            f"{name} fields do not match V1; missing={missing}, unknown={unknown}"
        )
    return value


def _require_str(value: Any, name: str) -> str:
    if type(value) is not str:
        raise ValueError(f"{name} must be an exact string")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError(f"{name} must contain valid UTF-8 text") from exc
    return value


def _optional_str(value: Any, name: str) -> str | None:
    if value is None:
        return None
    return _require_str(value, name)


def _require_url(value: Any, name: str) -> str:
    url = _require_str(value, name)
    try:
        parsed = urlsplit(url)
        hostname = parsed.hostname
        parsed.port
    except ValueError as exc:
        raise ValueError(f"{name} is not a valid HTTP URL") from exc
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or not hostname
        or any(character.isspace() or ord(character) < 32 for character in url)
    ):
        raise ValueError(f"{name} is not a valid HTTP URL")
    return url


def _decode_observed_at(value: Any) -> datetime:
    text = _require_str(value, "observed_at")
    try:
        observed_at = datetime.fromisoformat(text)
        offset = observed_at.utcoffset()
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("observed_at must be a valid ISO datetime") from exc
    if observed_at.tzinfo is None or offset is None:
        raise ValueError("observed_at must include an explicit timezone")
    if observed_at.isoformat() != text:
        raise ValueError("observed_at must use the canonical persisted representation")
    return observed_at


def _decode_fact(value: Any, index: int) -> ProductFact:
    name = f"facts[{index}]"
    fact = _require_object(value, name, _FACT_FIELDS)
    return ProductFact(
        key=_require_str(fact["key"], f"{name}.key"),
        value=_require_str(fact["value"], f"{name}.value"),
        unit=_optional_str(fact["unit"], f"{name}.unit"),
        source_section=_require_str(
            fact["source_section"], f"{name}.source_section"
        ),
        provenance=_require_str(fact["provenance"], f"{name}.provenance"),
    )


def _decode_media(value: Any, index: int) -> OriginalMediaRef:
    name = f"media[{index}]"
    media = _require_object(value, name, _MEDIA_FIELDS)
    ordinal = media["ordinal"]
    if type(ordinal) is not int or ordinal < 0:
        raise ValueError(f"{name}.ordinal must be an exact non-negative integer")

    byte_size = media["byte_size"]
    if byte_size is not None and (type(byte_size) is not int or byte_size <= 0):
        raise ValueError(f"{name}.byte_size must be null or an exact positive integer")

    sha256_hash = _optional_str(media["sha256_hash"], f"{name}.sha256_hash")
    if sha256_hash is not None and _SHA256_RE.fullmatch(sha256_hash) is None:
        raise ValueError(f"{name}.sha256_hash must be a lowercase SHA-256 hex digest")

    perceptual_hash = _optional_str(
        media["perceptual_hash"], f"{name}.perceptual_hash"
    )
    if (
        perceptual_hash is not None
        and _PERCEPTUAL_HASH_RE.fullmatch(perceptual_hash) is None
    ):
        raise ValueError(f"{name}.perceptual_hash must be lowercase hexadecimal")

    try:
        role = MediaRole(_require_str(media["role"], f"{name}.role"))
        provenance = MediaProvenance(
            _require_str(media["provenance"], f"{name}.provenance")
        )
    except ValueError as exc:
        raise ValueError(f"{name} contains an invalid enum value") from exc

    return OriginalMediaRef(
        source_url=_require_url(media["source_url"], f"{name}.source_url"),
        platform=_require_str(media["platform"], f"{name}.platform"),
        role=role,
        provenance=provenance,
        ordinal=ordinal,
        alt_text=_optional_str(media["alt_text"], f"{name}.alt_text"),
        variant_label=_optional_str(
            media["variant_label"], f"{name}.variant_label"
        ),
        content_type=_optional_str(
            media["content_type"], f"{name}.content_type"
        ),
        byte_size=byte_size,
        sha256_hash=sha256_hash,
        perceptual_hash=perceptual_hash,
        local_filename=_optional_str(
            media["local_filename"], f"{name}.local_filename"
        ),
    )


__all__ = [
    "serialize_source_pack",
    "deserialize_source_pack",
    "deserialize_product_source_pack",
]
