"""Pure append-only integrity state for canonical families and variants.

TASK-118 is the sole in-memory authority for admitting existing TASK-114 family
and TASK-117 sellable-variant values into a catalog.  Registration validates
identity and observation exclusivity without recreating canonical records,
calling upstream factories, persisting state, or performing external work.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass
from enum import Enum

from src.product_intelligence.canonical_family import CanonicalProductFamily
from src.product_intelligence.canonical_variant import CanonicalSellableVariant


class CanonicalCatalogIntegrityError(ValueError):
    """Raised when a catalog value or append-only registration is invalid."""


class CatalogRegistrationStatus(str, Enum):
    """The complete set of successful append-only registration outcomes."""

    INSERTED = "INSERTED"
    ALREADY_PRESENT = "ALREADY_PRESENT"


_CANONICAL_CATALOG_BOUNDARY = object()


@dataclass(frozen=True)
class CanonicalCatalogState:
    """One immutable, canonically ordered family and variant catalog snapshot."""

    families: tuple[CanonicalProductFamily, ...]
    variants: tuple[CanonicalSellableVariant, ...]
    _boundary: InitVar[object] = None

    def __post_init__(self, _boundary: object) -> None:
        if _boundary is not _CANONICAL_CATALOG_BOUNDARY:
            raise CanonicalCatalogIntegrityError(
                "CanonicalCatalogState must be created by the canonical catalog boundary"
            )


@dataclass(frozen=True)
class CatalogRegistrationResult:
    """The immutable result of one successful append-only registration."""

    catalog: CanonicalCatalogState
    status: CatalogRegistrationStatus

    def __post_init__(self) -> None:
        if type(self.catalog) is not CanonicalCatalogState:
            raise CanonicalCatalogIntegrityError(
                "catalog must be an exact CanonicalCatalogState"
            )
        if type(self.status) is not CatalogRegistrationStatus:
            raise CanonicalCatalogIntegrityError(
                "status must be an exact CatalogRegistrationStatus"
            )


def create_empty_canonical_catalog() -> CanonicalCatalogState:
    """Return a canonical empty immutable catalog without external work."""

    return _create_catalog_state(families=(), variants=())


def register_canonical_family(
    catalog: CanonicalCatalogState,
    family: CanonicalProductFamily,
) -> CatalogRegistrationResult:
    """Append one exact canonical family or report a value-equal no-op."""

    _require_catalog(catalog)
    if type(family) is not CanonicalProductFamily:
        raise CanonicalCatalogIntegrityError(
            "family must be an exact CanonicalProductFamily"
        )

    for registered in catalog.families:
        if registered.family_id == family.family_id:
            if registered == family:
                return CatalogRegistrationResult(
                    catalog=catalog,
                    status=CatalogRegistrationStatus.ALREADY_PRESENT,
                )
            raise CanonicalCatalogIntegrityError(
                "family_id is already bound to different canonical lineage"
            )

    incoming_lineage = _family_lineage(family)
    for registered in catalog.families:
        if _family_lineage(registered) == incoming_lineage:
            raise CanonicalCatalogIntegrityError(
                "canonical family lineage is already bound to a different family_id"
            )
        if _members_overlap(registered.members, family.members):
            raise CanonicalCatalogIntegrityError(
                "a source observation is already bound to a distinct canonical family"
            )

    return CatalogRegistrationResult(
        catalog=_create_catalog_state(
            families=tuple(
                sorted(
                    (*catalog.families, family),
                    key=lambda value: value.family_id,
                )
            ),
            variants=catalog.variants,
        ),
        status=CatalogRegistrationStatus.INSERTED,
    )


def register_canonical_variant(
    catalog: CanonicalCatalogState,
    variant: CanonicalSellableVariant,
) -> CatalogRegistrationResult:
    """Append one exact canonical variant or report a value-equal no-op."""

    _require_catalog(catalog)
    if type(variant) is not CanonicalSellableVariant:
        raise CanonicalCatalogIntegrityError(
            "variant must be an exact CanonicalSellableVariant"
        )

    registered_family = next(
        (
            family
            for family in catalog.families
            if family.family_id == variant.family_id
        ),
        None,
    )
    if registered_family is None:
        raise CanonicalCatalogIntegrityError(
            "variant source family must be registered before the variant"
        )
    if registered_family != variant.source_family:
        raise CanonicalCatalogIntegrityError(
            "variant source family conflicts with registered canonical lineage"
        )

    for registered in catalog.variants:
        if registered.variant_id == variant.variant_id:
            if registered == variant:
                return CatalogRegistrationResult(
                    catalog=catalog,
                    status=CatalogRegistrationStatus.ALREADY_PRESENT,
                )
            raise CanonicalCatalogIntegrityError(
                "variant_id is already bound to different canonical lineage"
            )

    incoming_lineage = _variant_lineage(variant)
    for registered in catalog.variants:
        if _variant_lineage(registered) == incoming_lineage:
            raise CanonicalCatalogIntegrityError(
                "canonical variant lineage is already bound to a different variant_id"
            )
        if _members_overlap(registered.members, variant.members):
            raise CanonicalCatalogIntegrityError(
                "a source observation is already bound to a distinct canonical variant"
            )

    return CatalogRegistrationResult(
        catalog=_create_catalog_state(
            families=catalog.families,
            variants=tuple(
                sorted(
                    (*catalog.variants, variant),
                    key=lambda value: value.variant_id,
                )
            ),
        ),
        status=CatalogRegistrationStatus.INSERTED,
    )


def _create_catalog_state(
    *,
    families: tuple[CanonicalProductFamily, ...],
    variants: tuple[CanonicalSellableVariant, ...],
) -> CanonicalCatalogState:
    return CanonicalCatalogState(
        families=families,
        variants=variants,
        _boundary=_CANONICAL_CATALOG_BOUNDARY,
    )


def _require_catalog(catalog: object) -> None:
    if type(catalog) is not CanonicalCatalogState:
        raise CanonicalCatalogIntegrityError(
            "catalog must be an exact CanonicalCatalogState"
        )


def _family_lineage(family: CanonicalProductFamily) -> tuple[object, object]:
    return family.members, family.approval


def _variant_lineage(variant: CanonicalSellableVariant) -> object:
    return variant.approval


def _members_overlap(left: tuple[object, ...], right: tuple[object, ...]) -> bool:
    return any(left_member == right_member for left_member in left for right_member in right)


__all__ = [
    "CanonicalCatalogIntegrityError",
    "CanonicalCatalogState",
    "CatalogRegistrationResult",
    "CatalogRegistrationStatus",
    "create_empty_canonical_catalog",
    "register_canonical_family",
    "register_canonical_variant",
]
