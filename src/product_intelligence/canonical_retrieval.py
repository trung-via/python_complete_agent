"""Deterministic lexical retrieval over canonical variant profile evidence.

TASK-122 performs bounded, transient lexical matching only.  It preserves every
TASK-121 value and evidence object, and creates no product-truth, ranking, index,
storage, embedding, model, or RAG authority.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum

from src.product_intelligence.canonical_profile import (
    CanonicalProfileFactEvidence,
    CanonicalProfileMediaEvidence,
    CanonicalProfileObservation,
    CanonicalVariantProfile,
)


class CanonicalProfileRetrievalError(ValueError):
    """Raised when a lexical retrieval request is outside its bounded contract."""


class CanonicalRetrievalField(Enum):
    """The complete set of TASK-122 searchable evidence fields."""

    PLATFORM = "PLATFORM"
    TITLE = "TITLE"
    SHOP_NAME = "SHOP_NAME"
    BRAND = "BRAND"
    MODEL_SKU = "MODEL_SKU"
    DESCRIPTION_TEXT = "DESCRIPTION_TEXT"
    FACT_KEY = "FACT_KEY"
    FACT_VALUE = "FACT_VALUE"
    FACT_UNIT = "FACT_UNIT"
    MEDIA_ALT_TEXT = "MEDIA_ALT_TEXT"
    MEDIA_VARIANT_LABEL = "MEDIA_VARIANT_LABEL"


class CanonicalRetrievalMatchClass(Enum):
    """Lexical match classes in descending deterministic strength order."""

    EXACT_VALUE = "EXACT_VALUE"
    PHRASE = "PHRASE"
    SINGLE_FIELD_ALL_TERMS = "SINGLE_FIELD_ALL_TERMS"
    CROSS_FIELD_ALL_TERMS = "CROSS_FIELD_ALL_TERMS"


_CanonicalRetrievalEvidence = (
    CanonicalProfileObservation
    | CanonicalProfileFactEvidence
    | CanonicalProfileMediaEvidence
)


@dataclass(frozen=True)
class CanonicalRetrievalWitness:
    """One exact retained evidence value proving lexical query coverage."""

    source_evidence: _CanonicalRetrievalEvidence
    field: CanonicalRetrievalField
    value: str
    normalized_query_terms: tuple[str, ...]


@dataclass(frozen=True)
class CanonicalVariantRetrievalHit:
    """A lexical match that reuses its exact caller-supplied profile."""

    profile: CanonicalVariantProfile
    match_class: CanonicalRetrievalMatchClass
    witnesses: tuple[CanonicalRetrievalWitness, ...]


@dataclass(frozen=True)
class _SearchableField:
    source_evidence: _CanonicalRetrievalEvidence
    field: CanonicalRetrievalField
    value: str
    tokens: tuple[str, ...]


def retrieve_canonical_variant_profiles(
    profiles: Iterable[CanonicalVariantProfile],
    *,
    query: str,
    limit: int = 10,
) -> tuple[CanonicalVariantRetrievalHit, ...]:
    """Return deterministic evidence-backed lexical matches for ``query``."""

    corpus = _require_profiles(profiles)
    query_tokens = _require_query(query)
    _require_limit(limit)

    query_terms = tuple(dict.fromkeys(query_tokens))
    hits = tuple(
        hit
        for profile in corpus
        if (hit := _match_profile(profile, query_tokens, query_terms)) is not None
    )
    ordered_hits: list[CanonicalVariantRetrievalHit] = []
    for match_class in CanonicalRetrievalMatchClass:
        ordered_hits.extend(
            sorted(
                (hit for hit in hits if hit.match_class is match_class),
                key=lambda hit: hit.profile.variant_id,
            )
        )
    return tuple(ordered_hits[:limit])


def _require_profiles(
    profiles: Iterable[CanonicalVariantProfile],
) -> tuple[CanonicalVariantProfile, ...]:
    try:
        corpus = tuple(profiles)
    except TypeError as exc:
        raise CanonicalProfileRetrievalError(
            "profiles must be an iterable of exact CanonicalVariantProfile values"
        ) from exc

    if any(type(profile) is not CanonicalVariantProfile for profile in corpus):
        raise CanonicalProfileRetrievalError(
            "profiles must contain exact CanonicalVariantProfile values only"
        )

    variant_ids: set[str] = set()
    for profile in corpus:
        if profile.variant_id in variant_ids:
            raise CanonicalProfileRetrievalError(
                "profiles must not contain duplicate variant_id values"
            )
        variant_ids.add(profile.variant_id)
    return corpus


def _require_query(query: str) -> tuple[str, ...]:
    if type(query) is not str:
        raise CanonicalProfileRetrievalError("query must be an exact string")
    tokens = _normalize_tokens(query)
    if not tokens:
        raise CanonicalProfileRetrievalError(
            "query must contain at least one Unicode-alphanumeric token"
        )
    if len(tokens) > 12:
        raise CanonicalProfileRetrievalError(
            "query must contain at most 12 normalized tokens"
        )
    return tokens


def _require_limit(limit: int) -> None:
    if type(limit) is not int or not 1 <= limit <= 100:
        raise CanonicalProfileRetrievalError(
            "limit must be an exact integer in the inclusive range 1..100"
        )


def _normalize_tokens(value: str) -> tuple[str, ...]:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    separated = "".join(
        character if character.isalnum() else " " for character in normalized
    )
    return tuple(separated.split())


def _searchable_fields(
    profile: CanonicalVariantProfile,
) -> tuple[_SearchableField, ...]:
    fields: list[_SearchableField] = []
    for member in profile.members:
        for observation in profile.observations:
            if observation.member == member:
                _append_field(
                    fields,
                    observation,
                    CanonicalRetrievalField.PLATFORM,
                    observation.member.platform,
                )
                _append_field(
                    fields,
                    observation,
                    CanonicalRetrievalField.TITLE,
                    observation.title,
                )
                _append_field(
                    fields,
                    observation,
                    CanonicalRetrievalField.SHOP_NAME,
                    observation.shop_name,
                )
                _append_field(
                    fields,
                    observation,
                    CanonicalRetrievalField.BRAND,
                    observation.brand,
                )
                _append_field(
                    fields,
                    observation,
                    CanonicalRetrievalField.MODEL_SKU,
                    observation.model_sku,
                )
                _append_field(
                    fields,
                    observation,
                    CanonicalRetrievalField.DESCRIPTION_TEXT,
                    observation.description_text,
                )

        for evidence in profile.fact_evidence:
            if evidence.member == member:
                _append_field(
                    fields,
                    evidence,
                    CanonicalRetrievalField.FACT_KEY,
                    evidence.fact.key,
                )
                _append_field(
                    fields,
                    evidence,
                    CanonicalRetrievalField.FACT_VALUE,
                    evidence.fact.value,
                )
                _append_field(
                    fields,
                    evidence,
                    CanonicalRetrievalField.FACT_UNIT,
                    evidence.fact.unit,
                )

        for evidence in profile.media_evidence:
            if evidence.member == member:
                _append_field(
                    fields,
                    evidence,
                    CanonicalRetrievalField.MEDIA_ALT_TEXT,
                    evidence.media.alt_text,
                )
                _append_field(
                    fields,
                    evidence,
                    CanonicalRetrievalField.MEDIA_VARIANT_LABEL,
                    evidence.media.variant_label,
                )
    return tuple(fields)


def _append_field(
    fields: list[_SearchableField],
    source_evidence: _CanonicalRetrievalEvidence,
    field: CanonicalRetrievalField,
    value: str | None,
) -> None:
    if value is not None:
        fields.append(
            _SearchableField(
                source_evidence=source_evidence,
                field=field,
                value=value,
                tokens=_normalize_tokens(value),
            )
        )


def _match_profile(
    profile: CanonicalVariantProfile,
    query_tokens: tuple[str, ...],
    query_terms: tuple[str, ...],
) -> CanonicalVariantRetrievalHit | None:
    fields = _searchable_fields(profile)

    for searchable in fields:
        if searchable.tokens == query_tokens:
            return _single_witness_hit(
                profile,
                CanonicalRetrievalMatchClass.EXACT_VALUE,
                searchable,
                query_terms,
            )

    for searchable in fields:
        if _contains_phrase(searchable.tokens, query_tokens):
            return _single_witness_hit(
                profile,
                CanonicalRetrievalMatchClass.PHRASE,
                searchable,
                query_terms,
            )

    required = set(query_terms)
    for searchable in fields:
        if required.issubset(searchable.tokens):
            return _single_witness_hit(
                profile,
                CanonicalRetrievalMatchClass.SINGLE_FIELD_ALL_TERMS,
                searchable,
                query_terms,
            )

    field_coverages = tuple(
        required.intersection(searchable.tokens) for searchable in fields
    )
    if not required.issubset(set().union(*field_coverages)):
        return None

    positions = _minimum_cover_positions(field_coverages, query_terms)
    witnesses = tuple(_witness(fields[position], query_terms) for position in positions)
    return CanonicalVariantRetrievalHit(
        profile=profile,
        match_class=CanonicalRetrievalMatchClass.CROSS_FIELD_ALL_TERMS,
        witnesses=witnesses,
    )


def _contains_phrase(
    field_tokens: tuple[str, ...],
    query_tokens: tuple[str, ...],
) -> bool:
    query_length = len(query_tokens)
    return any(
        field_tokens[start : start + query_length] == query_tokens
        for start in range(len(field_tokens) - query_length + 1)
    )


def _single_witness_hit(
    profile: CanonicalVariantProfile,
    match_class: CanonicalRetrievalMatchClass,
    searchable: _SearchableField,
    query_terms: tuple[str, ...],
) -> CanonicalVariantRetrievalHit:
    return CanonicalVariantRetrievalHit(
        profile=profile,
        match_class=match_class,
        witnesses=(_witness(searchable, query_terms),),
    )


def _witness(
    searchable: _SearchableField,
    query_terms: tuple[str, ...],
) -> CanonicalRetrievalWitness:
    field_terms = set(searchable.tokens)
    return CanonicalRetrievalWitness(
        source_evidence=searchable.source_evidence,
        field=searchable.field,
        value=searchable.value,
        normalized_query_terms=tuple(
            term for term in query_terms if term in field_terms
        ),
    )


def _minimum_cover_positions(
    field_coverages: tuple[set[str], ...],
    query_terms: tuple[str, ...],
) -> tuple[int, ...]:
    term_bits = {term: 1 << position for position, term in enumerate(query_terms)}
    full_mask = (1 << len(query_terms)) - 1
    best: dict[int, tuple[int, ...]] = {0: ()}

    for position, coverage in enumerate(field_coverages):
        coverage_mask = 0
        for term in coverage:
            coverage_mask |= term_bits[term]
        if coverage_mask == 0:
            continue
        updated = dict(best)
        for mask, selected in best.items():
            new_mask = mask | coverage_mask
            candidate = (*selected, position)
            incumbent = updated.get(new_mask)
            if incumbent is None or (len(candidate), candidate) < (
                len(incumbent),
                incumbent,
            ):
                updated[new_mask] = candidate
        best = updated

    return best[full_mask]


__all__ = [
    "CanonicalProfileRetrievalError",
    "CanonicalRetrievalField",
    "CanonicalRetrievalMatchClass",
    "CanonicalRetrievalWitness",
    "CanonicalVariantRetrievalHit",
    "retrieve_canonical_variant_profiles",
]
