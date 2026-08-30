"""Deterministic, side-effect-free entity resolution for two source packs.

The resolver deliberately favors an unresolved decision over an unsafe merge.
Marketplace identifiers, prose, and media are never promoted to authoritative
cross-platform product identity.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Optional

from src.product_source.models import MediaRole, ProductSourcePack


class ProductRelationship(str, Enum):
    EXACT_VARIANT_MATCH = "EXACT_VARIANT_MATCH"
    SAME_PRODUCT_FAMILY = "SAME_PRODUCT_FAMILY"
    DIFFERENT_PRODUCT = "DIFFERENT_PRODUCT"
    UNCERTAIN = "UNCERTAIN"


@dataclass(frozen=True)
class SourceObservationIdentity:
    source_pack_id: str
    platform: str
    source_product_id: Optional[str]
    product_url: str

    @classmethod
    def from_pack(cls, pack: ProductSourcePack) -> "SourceObservationIdentity":
        return cls(pack.source_pack_id, pack.platform, pack.source_product_id, pack.product_url)


@dataclass(frozen=True)
class ResolutionEvidence:
    code: str
    detail: str


@dataclass(frozen=True)
class EntityResolutionResult:
    relationship: ProductRelationship
    confidence: float
    left: SourceObservationIdentity
    right: SourceObservationIdentity
    reasons: tuple[str, ...]
    evidence: tuple[ResolutionEvidence, ...]

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")


_SPACE_RE = re.compile(r"[^a-z0-9]+")
_PACK_RE = re.compile(r"\b(?:pack\s*(?:of\s*)?|x\s*)(\d+)\b|\b(\d+)\s*(?:pack|pcs?|pieces?|units?)\b")
_BUNDLE_RE = re.compile(r"\b(bundle|combo|set)\b")
_SINGLE_RE = re.compile(r"\b(single|one\s+(?:piece|unit)|1\s*(?:pack|pc|piece|unit))\b")

_GLOBAL_ID_KEYS = {
    "ean", "ean13", "gtin", "gtin8", "gtin12", "gtin13", "gtin14",
    "isbn", "upc", "upca", "upce",
}
_MANUFACTURER_ID_KEYS = {"mpn", "manufacturerpartnumber", "manufacturerproductnumber"}
_BRAND_KEYS = {"brand", "manufacturer"}
_MODEL_KEYS = {"model", "modelnumber", "productmodel"}
_VARIANT_KEYS = {
    "color", "colour", "capacity", "storage", "size", "variantsize",
    "flavor", "flavour", "scent", "style", "material", "voltage",
    "edition", "configuration", "variant", "variantname", "option",
}
_COUNT_KEYS = {"count", "itemcount", "packcount", "quantity", "quantityperpack", "unitsperpack"}
_COMPOSITION_KEYS = {"bundle", "isbundle", "composition", "packagecontent", "productcomposition"}


def _norm(value: Optional[str]) -> Optional[str]:
    if value is None or not value.strip():
        return None
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii").lower()
    normalized = _SPACE_RE.sub(" ", value).strip()
    return normalized or None


def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", _norm(value) or "")


def _facts(pack: ProductSourcePack) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for fact in pack.facts:
        value = _norm(fact.value)
        if value:
            result.setdefault(_key(fact.key), set()).add(value)
    return result


def _values(facts: dict[str, set[str]], keys: Iterable[str]) -> set[str]:
    return {value for key in keys for value in facts.get(key, ())}


def _brand(pack: ProductSourcePack, facts: dict[str, set[str]]) -> set[str]:
    values = _values(facts, _BRAND_KEYS)
    normalized = _norm(pack.brand)
    if normalized:
        values.add(normalized)
    return values


def _models(pack: ProductSourcePack, facts: dict[str, set[str]]) -> set[str]:
    # model_sku is intentionally excluded: its namespace is marketplace/extractor
    # scoped unless another explicit fact identifies a manufacturer model.
    return _values(facts, _MODEL_KEYS)


def _variants(pack: ProductSourcePack, facts: dict[str, set[str]]) -> dict[str, frozenset[str]]:
    variants = {key: frozenset(facts[key]) for key in _VARIANT_KEYS if key in facts}
    labels = {
        value
        for media in pack.media
        if media.role == MediaRole.VARIANT
        for value in [_norm(media.variant_label)]
        if value
    }
    # One label can describe the observed variant. Multiple labels describe a
    # listing's option catalogue and therefore do not identify the sold option.
    if len(labels) == 1 and not variants:
        variants["variantlabel"] = frozenset(labels)
    return variants


def _composition(pack: ProductSourcePack, facts: dict[str, set[str]]) -> Optional[str]:
    counts = _values(facts, _COUNT_KEYS)
    if counts:
        parsed = {int(match.group()) for value in counts for match in re.finditer(r"\d+", value)}
        if parsed and min(parsed) > 1:
            return "multi"
        if parsed == {1}:
            return "single"
    composition = " ".join(sorted(_values(facts, _COMPOSITION_KEYS)))
    text = " ".join(part for part in (composition, _norm(pack.title) or "") if part)
    match = _PACK_RE.search(text)
    if match and int(next(group for group in match.groups() if group)) > 1:
        return "multi"
    if _BUNDLE_RE.search(text):
        return "multi"
    if _SINGLE_RE.search(text):
        return "single"
    return None


def _overlap(left: set[str], right: set[str]) -> bool:
    return bool(left and right and left.intersection(right))


def _disjoint(left: set[str], right: set[str]) -> bool:
    return bool(left and right and left.isdisjoint(right))


def _result(
    relationship: ProductRelationship,
    confidence: float,
    left: ProductSourcePack,
    right: ProductSourcePack,
    reasons: Iterable[str],
    evidence: Iterable[ResolutionEvidence],
) -> EntityResolutionResult:
    return EntityResolutionResult(
        relationship=relationship,
        confidence=confidence,
        left=SourceObservationIdentity.from_pack(left),
        right=SourceObservationIdentity.from_pack(right),
        reasons=tuple(sorted(set(reasons))),
        evidence=tuple(sorted(set(evidence), key=lambda item: (item.code, item.detail))),
    )


def resolve_product_entities(left: ProductSourcePack, right: ProductSourcePack) -> EntityResolutionResult:
    """Resolve exactly two observations without mutation or external effects."""
    lf, rf = _facts(left), _facts(right)
    evidence: list[ResolutionEvidence] = []

    lc, rc = _composition(left, lf), _composition(right, rf)
    if lc and rc and lc != rc:
        evidence.append(ResolutionEvidence("COMPOSITION_CONFLICT", f"{min(lc, rc)} versus {max(lc, rc)}"))
        return _result(ProductRelationship.DIFFERENT_PRODUCT, 0.99, left, right,
                       ("materially different sellable composition",), evidence)

    lg = _values(lf, _GLOBAL_ID_KEYS)
    rg = _values(rf, _GLOBAL_ID_KEYS)
    if _disjoint(lg, rg):
        evidence.append(ResolutionEvidence("GLOBAL_IDENTIFIER_CONFLICT", "authoritative identifier values differ"))
        return _result(ProductRelationship.DIFFERENT_PRODUCT, 0.99, left, right,
                       ("reliable product-family identifiers conflict",), evidence)

    lb, rb = _brand(left, lf), _brand(right, rf)
    lm, rm = _models(left, lf), _models(right, rf)
    lmpn, rmpn = _values(lf, _MANUFACTURER_ID_KEYS), _values(rf, _MANUFACTURER_ID_KEYS)
    if _disjoint(lb, rb) and (_disjoint(lm, rm) or _disjoint(lmpn, rmpn)):
        evidence.append(ResolutionEvidence("FAMILY_IDENTITY_CONFLICT", "brand and manufacturer model evidence differ"))
        return _result(ProductRelationship.DIFFERENT_PRODUCT, 0.97, left, right,
                       ("reliable product-family identity conflicts",), evidence)
    if _overlap(lb, rb) and (_disjoint(lm, rm) or _disjoint(lmpn, rmpn)):
        evidence.append(ResolutionEvidence("MODEL_CONFLICT", "same brand has different manufacturer model"))
        return _result(ProductRelationship.DIFFERENT_PRODUCT, 0.96, left, right,
                       ("reliable manufacturer model evidence conflicts",), evidence)

    family_strength = 0
    if _overlap(lg, rg):
        family_strength = 3
        evidence.append(ResolutionEvidence("GLOBAL_IDENTIFIER_MATCH", "authoritative identifier matches"))
    elif _overlap(lb, rb) and (_overlap(lm, rm) or _overlap(lmpn, rmpn)):
        family_strength = 3
        evidence.append(ResolutionEvidence("BRAND_MODEL_MATCH", "brand and manufacturer model match"))
    elif (left.platform.casefold() == right.platform.casefold()
          and left.source_product_id and left.source_product_id == right.source_product_id):
        family_strength = 2
        evidence.append(ResolutionEvidence("SCOPED_LISTING_MATCH", "platform-scoped listing identifier matches"))

    lv, rv = _variants(left, lf), _variants(right, rf)
    if family_strength:
        shared = set(lv).intersection(rv)
        if any(lv[key].isdisjoint(rv[key]) for key in shared):
            evidence.append(ResolutionEvidence("VARIANT_CONFLICT", "observed sellable variant attributes differ"))
            return _result(ProductRelationship.SAME_PRODUCT_FAMILY, 0.96, left, right,
                           ("same product family", "different sellable variant"), evidence)
        if lv and rv and lv == rv:
            evidence.append(ResolutionEvidence("VARIANT_MATCH", "observed sellable variant attributes match"))
            return _result(ProductRelationship.EXACT_VARIANT_MATCH, 0.98, left, right,
                           ("same product family", "same observed sellable variant"), evidence)
        return _result(ProductRelationship.SAME_PRODUCT_FAMILY, 0.86, left, right,
                       ("same product family", "insufficient variant evidence for exact match"), evidence)

    weak: list[str] = []
    if _norm(left.title) and _norm(left.title) == _norm(right.title):
        weak.append("matching normalized title")
        evidence.append(ResolutionEvidence("TITLE_SIMILARITY", "titles match after normalization"))
    left_hashes = {m.sha256_hash.lower() for m in left.media if m.sha256_hash}
    right_hashes = {m.sha256_hash.lower() for m in right.media if m.sha256_hash}
    if left_hashes.intersection(right_hashes):
        weak.append("matching media hash")
        evidence.append(ResolutionEvidence("MEDIA_SIMILARITY", "exact media hash matches"))
    if (left.platform.casefold() != right.platform.casefold() and left.source_product_id
            and left.source_product_id == right.source_product_id):
        evidence.append(ResolutionEvidence("CROSS_PLATFORM_SCOPED_ID_EQUALITY",
                                             "same text in different marketplace namespaces"))
    if left.model_sku and right.model_sku and _norm(left.model_sku) == _norm(right.model_sku):
        evidence.append(ResolutionEvidence("UNSCOPED_MODEL_SKU_EQUALITY",
                                             "model_sku text matches without authoritative namespace"))
    return _result(ProductRelationship.UNCERTAIN, 0.35 if weak else 0.1, left, right,
                   tuple(weak) + ("insufficient reliable identity evidence",), evidence)


# Concise public alias for callers that prefer the domain operation name.
resolve_products = resolve_product_entities
resolve_product_source_packs = resolve_product_entities
EntityRelationship = ProductRelationship
ProductEntityResolutionResult = EntityResolutionResult


class ProductEntityResolver:
    """Stateless facade for dependency-injected application code."""

    def resolve(self, left: ProductSourcePack, right: ProductSourcePack) -> EntityResolutionResult:
        return resolve_product_entities(left, right)
