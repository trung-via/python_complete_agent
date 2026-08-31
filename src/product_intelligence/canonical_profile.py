"""Evidence-preserving projection for one registered canonical variant.

TASK-121 binds an already-registered TASK-117 variant to exactly its supplied
``ProductSourcePack`` observations.  It preserves source values and provenance
without resolving conflicts, selecting preferred truth, persisting state, or
performing external work.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from src.product_intelligence.canonical_catalog import CanonicalCatalogState
from src.product_intelligence.canonical_variant import CanonicalSellableVariant
from src.product_intelligence.entity_resolution import SourceObservationIdentity
from src.product_source.models import (
    OriginalMediaRef,
    ProductFact,
    ProductSourcePack,
)


class CanonicalVariantProfileError(ValueError):
    """Raised when registered variant evidence cannot be bound exactly."""


@dataclass(frozen=True)
class CanonicalProfileObservation:
    """One source observation bound to its registered canonical member."""

    member: SourceObservationIdentity
    collector: str
    title: str | None
    shop_name: str | None
    brand: str | None
    model_sku: str | None
    description_text: str | None


@dataclass(frozen=True)
class CanonicalProfileFactEvidence:
    """One original product fact bound to its registered canonical member."""

    member: SourceObservationIdentity
    fact: ProductFact


@dataclass(frozen=True)
class CanonicalProfileMediaEvidence:
    """One original media reference bound to its registered canonical member."""

    member: SourceObservationIdentity
    media: OriginalMediaRef


@dataclass(frozen=True)
class CanonicalVariantProfile:
    """Immutable evidence projection for one registered sellable variant."""

    variant_id: str
    family_id: str
    members: tuple[SourceObservationIdentity, ...]
    observations: tuple[CanonicalProfileObservation, ...]
    fact_evidence: tuple[CanonicalProfileFactEvidence, ...]
    media_evidence: tuple[CanonicalProfileMediaEvidence, ...]


def build_canonical_variant_profile(
    catalog: CanonicalCatalogState,
    *,
    variant_id: str,
    source_packs: Iterable[ProductSourcePack],
) -> CanonicalVariantProfile:
    """Project exact source evidence for one already-registered variant."""

    if type(catalog) is not CanonicalCatalogState:
        raise CanonicalVariantProfileError(
            "catalog must be an exact CanonicalCatalogState"
        )
    if not isinstance(variant_id, str):
        raise CanonicalVariantProfileError("variant_id must be an exact opaque string")

    registered_variant = _find_registered_variant(catalog, variant_id)
    packs = _require_source_packs(source_packs)
    bindings = _bind_source_packs(registered_variant, packs)

    observations = tuple(
        CanonicalProfileObservation(
            member=member,
            collector=pack.collector,
            title=pack.title,
            shop_name=pack.shop_name,
            brand=pack.brand,
            model_sku=pack.model_sku,
            description_text=pack.description_text,
        )
        for member, pack in bindings
    )
    fact_evidence = tuple(
        CanonicalProfileFactEvidence(member=member, fact=fact)
        for member, pack in bindings
        for fact in pack.facts
    )
    media_evidence = tuple(
        CanonicalProfileMediaEvidence(member=member, media=media)
        for member, pack in bindings
        for media in pack.media
    )

    return CanonicalVariantProfile(
        variant_id=registered_variant.variant_id,
        family_id=registered_variant.family_id,
        members=registered_variant.members,
        observations=observations,
        fact_evidence=fact_evidence,
        media_evidence=media_evidence,
    )


def _find_registered_variant(
    catalog: CanonicalCatalogState,
    variant_id: str,
) -> CanonicalSellableVariant:
    matches = tuple(
        variant for variant in catalog.variants if variant.variant_id == variant_id
    )
    if len(matches) != 1:
        raise CanonicalVariantProfileError(
            "variant_id must identify exactly one registered canonical variant"
        )
    return matches[0]


def _require_source_packs(
    source_packs: Iterable[ProductSourcePack],
) -> tuple[ProductSourcePack, ...]:
    try:
        packs = tuple(source_packs)
    except TypeError as exc:
        raise CanonicalVariantProfileError(
            "source_packs must be an iterable of exact ProductSourcePack values"
        ) from exc

    if any(type(pack) is not ProductSourcePack for pack in packs):
        raise CanonicalVariantProfileError(
            "source_packs must contain exact ProductSourcePack values only"
        )
    return packs


def _bind_source_packs(
    variant: CanonicalSellableVariant,
    packs: tuple[ProductSourcePack, ...],
) -> tuple[tuple[SourceObservationIdentity, ProductSourcePack], ...]:
    identities = tuple(SourceObservationIdentity.from_pack(pack) for pack in packs)

    if any(
        left == right
        for index, left in enumerate(identities)
        for right in identities[index + 1 :]
    ):
        raise CanonicalVariantProfileError(
            "source_packs contain a duplicate source observation identity"
        )
    if len(packs) != len(variant.members):
        raise CanonicalVariantProfileError(
            "source_packs must bind one-to-one with all registered variant members"
        )

    bindings: list[tuple[SourceObservationIdentity, ProductSourcePack]] = []
    matched_indexes: set[int] = set()
    for member in variant.members:
        matches = tuple(
            index for index, identity in enumerate(identities) if identity == member
        )
        if len(matches) != 1:
            raise CanonicalVariantProfileError(
                "each registered variant member must have exactly one matching source pack"
            )
        matched_index = matches[0]
        matched_indexes.add(matched_index)
        bindings.append((member, packs[matched_index]))

    if len(matched_indexes) != len(packs):
        raise CanonicalVariantProfileError(
            "source_packs contain an unmatched source observation identity"
        )
    return tuple(bindings)


__all__ = [
    "CanonicalVariantProfileError",
    "CanonicalProfileObservation",
    "CanonicalProfileFactEvidence",
    "CanonicalProfileMediaEvidence",
    "CanonicalVariantProfile",
    "build_canonical_variant_profile",
]
