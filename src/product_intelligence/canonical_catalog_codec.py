"""Deterministic V1 representation for the in-memory canonical catalog.

The codec is deliberately a representation and trusted-rehydration boundary,
not a persistence API.  Its JSON graph uses indexes for every retained family,
member, and pair relationship so decoding can restore the admitted aliasing
without re-running any discovery, resolution, projection, or Human workflow.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
import json
import math
import re
from typing import NoReturn

from src.product_intelligence.canonical_catalog import (
    CanonicalCatalogState,
    create_empty_canonical_catalog,
    register_canonical_family,
    register_canonical_variant,
)
from src.product_intelligence.canonical_family import (
    CanonicalProductFamily,
    create_canonical_family,
)
from src.product_intelligence.canonical_variant import (
    CanonicalSellableVariant,
    create_canonical_sellable_variant,
)
from src.product_intelligence.entity_resolution import (
    ProductRelationship,
    ResolutionEvidence,
    SourceObservationIdentity,
)
from src.product_intelligence.family_merge_approval import (
    FamilyMergeDecision,
    FamilyMergeDecisionRecord,
    FamilyMergePairEvidence,
    _rehydrate_family_merge_proposal,
)
from src.product_intelligence.sellable_variant_approval import (
    SellableVariantDecision,
    SellableVariantDecisionRecord,
    _rehydrate_sellable_variant_proposal,
)
from src.product_intelligence.sellable_variant_evidence import (
    SellableVariantEvidenceProjection,
    SellableVariantExactnessGap,
)


CANONICAL_CATALOG_SCHEMA = "product_intelligence.canonical_catalog"
CANONICAL_CATALOG_SCHEMA_VERSION = 1


class CanonicalCatalogCodecError(ValueError):
    """Raised when a catalog or canonical V1 representation is invalid."""


_DATETIME_RE = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})\.(\d{6})Z$"
)


def encode_canonical_catalog(catalog: CanonicalCatalogState) -> bytes:
    """Encode an exact TASK-118 catalog as deterministic canonical UTF-8 JSON."""

    try:
        if type(catalog) is not CanonicalCatalogState:
            _fail("catalog must be an exact CanonicalCatalogState")
        document = _encode_catalog_document(catalog)
        text = json.dumps(
            document,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        return text.encode("utf-8", errors="strict")
    except CanonicalCatalogCodecError:
        raise
    except (TypeError, ValueError, OverflowError, UnicodeError) as exc:
        raise CanonicalCatalogCodecError("catalog cannot be canonically encoded") from exc


def decode_canonical_catalog(payload: bytes) -> CanonicalCatalogState:
    """Decode only an exact canonical V1 payload and restore admitted lineage."""

    if type(payload) is not bytes:
        raise CanonicalCatalogCodecError("payload must be exact bytes")
    if payload.startswith(b"\xef\xbb\xbf"):
        raise CanonicalCatalogCodecError("UTF-8 BOM is not permitted")

    try:
        text = payload.decode("utf-8", errors="strict")
        document = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_json_constant,
        )
        catalog = _decode_catalog_document(document)
        if encode_canonical_catalog(catalog) != payload:
            _fail("payload is not the exact canonical V1 representation")
        return catalog
    except CanonicalCatalogCodecError:
        raise
    except (UnicodeError, json.JSONDecodeError, TypeError, ValueError, OverflowError) as exc:
        raise CanonicalCatalogCodecError("invalid canonical catalog payload") from exc


def _encode_catalog_document(catalog: CanonicalCatalogState) -> dict[str, object]:
    if type(catalog.families) is not tuple or type(catalog.variants) is not tuple:
        _fail("catalog collections must be exact tuples")
    if tuple(family.family_id for family in catalog.families) != tuple(
        sorted(family.family_id for family in catalog.families)
    ):
        _fail("catalog families are not in canonical order")
    if tuple(variant.variant_id for variant in catalog.variants) != tuple(
        sorted(variant.variant_id for variant in catalog.variants)
    ):
        _fail("catalog variants are not in canonical order")

    family_documents = [_encode_family(family) for family in catalog.families]
    variant_documents = [
        _encode_variant(variant, catalog.families) for variant in catalog.variants
    ]
    return {
        "schema": CANONICAL_CATALOG_SCHEMA,
        "version": CANONICAL_CATALOG_SCHEMA_VERSION,
        "families": family_documents,
        "variants": variant_documents,
    }


def _encode_family(family: CanonicalProductFamily) -> dict[str, object]:
    if type(family) is not CanonicalProductFamily:
        _fail("families must contain exact CanonicalProductFamily values")
    _require_string(family.family_id, "family_id")
    if type(family.members) is not tuple or len(family.members) < 2:
        _fail("canonical family members must be a tuple of at least two values")
    if family.approval.proposal.members is not family.members:
        _fail("canonical family must retain its exact approved member tuple")

    members = [_encode_member(member) for member in family.members]
    member_indexes = {id(member): index for index, member in enumerate(family.members)}
    if len(member_indexes) != len(family.members):
        _fail("canonical family members must be distinct retained values")
    expected_endpoints = tuple(
        (left, right)
        for left in range(len(family.members))
        for right in range(left + 1, len(family.members))
    )
    pairs = family.approval.proposal.pair_evidence
    if type(pairs) is not tuple or len(pairs) != len(expected_endpoints):
        _fail("canonical family pair evidence is not complete")
    pair_documents = []
    for pair, endpoints in zip(pairs, expected_endpoints):
        encoded = _encode_pair(pair, member_indexes)
        if (encoded["left_member"], encoded["right_member"]) != endpoints:
            _fail("canonical family pair evidence is not in canonical order")
        pair_documents.append(encoded)

    approval = family.approval
    if type(approval) is not FamilyMergeDecisionRecord:
        _fail("family approval must be an exact FamilyMergeDecisionRecord")
    if approval.decision is not FamilyMergeDecision.APPROVE:
        _fail("canonical family approval must be APPROVE")
    return {
        "family_id": family.family_id,
        "members": members,
        "pairs": pair_documents,
        "approval": _encode_decision(
            approval.decision,
            approval.actor,
            approval.decided_at,
            FamilyMergeDecision,
        ),
    }


def _encode_member(member: SourceObservationIdentity) -> dict[str, object]:
    if type(member) is not SourceObservationIdentity:
        _fail("family members must be exact SourceObservationIdentity values")
    _require_string(member.source_pack_id, "source_pack_id")
    _require_string(member.platform, "platform")
    if member.source_product_id is not None:
        _require_string(member.source_product_id, "source_product_id")
    _require_string(member.product_url, "product_url")
    return {
        "source_pack_id": member.source_pack_id,
        "platform": member.platform,
        "source_product_id": member.source_product_id,
        "product_url": member.product_url,
        "observed_at": _encode_datetime(member.observed_at),
    }


def _encode_pair(
    pair: FamilyMergePairEvidence,
    member_indexes: dict[int, int],
) -> dict[str, object]:
    if type(pair) is not FamilyMergePairEvidence:
        _fail("pair evidence must contain exact FamilyMergePairEvidence values")
    try:
        left = member_indexes[id(pair.left)]
        right = member_indexes[id(pair.right)]
    except KeyError as exc:
        raise CanonicalCatalogCodecError(
            "pair endpoints must reuse retained family members"
        ) from exc
    if left >= right:
        _fail("pair endpoints must use canonical orientation")
    if type(pair.relationship) is not ProductRelationship:
        _fail("pair relationship must be an exact ProductRelationship")
    confidence = _canonical_confidence(pair.confidence)
    if type(pair.reasons) is not tuple or any(type(value) is not str for value in pair.reasons):
        _fail("pair reasons must be a tuple of strings")
    if type(pair.evidence) is not tuple:
        _fail("pair evidence details must be an exact tuple")
    details = []
    for value in pair.evidence:
        if type(value) is not ResolutionEvidence:
            _fail("pair evidence details must be exact ResolutionEvidence values")
        _require_string(value.code, "evidence code")
        _require_string(value.detail, "evidence detail")
        details.append({"code": value.code, "detail": value.detail})
    return {
        "left_member": left,
        "right_member": right,
        "relationship": pair.relationship.value,
        "confidence": confidence,
        "reasons": list(pair.reasons),
        "evidence": details,
    }


def _encode_decision(
    decision: object,
    actor: object,
    decided_at: object,
    enum_type: type[FamilyMergeDecision] | type[SellableVariantDecision],
) -> dict[str, object]:
    if type(decision) is not enum_type:
        _fail("approval decision has the wrong enum type")
    _require_string(actor, "approval actor")
    return {
        "decision": decision.value,
        "actor": actor,
        "decided_at": _encode_datetime(decided_at),
    }


def _encode_variant(
    variant: CanonicalSellableVariant,
    catalog_families: tuple[CanonicalProductFamily, ...],
) -> dict[str, object]:
    if type(variant) is not CanonicalSellableVariant:
        _fail("variants must contain exact CanonicalSellableVariant values")
    _require_string(variant.variant_id, "variant_id")
    matches = [
        index
        for index, family in enumerate(catalog_families)
        if family == variant.source_family
    ]
    if len(matches) != 1:
        _fail("variant must reference exactly one registered source family")
    source_family_index = matches[0]
    source_family = variant.source_family
    if variant.proposal.projection.source_family is not source_family:
        _fail("variant projection must retain its exact source family")

    member_indexes = {id(member): index for index, member in enumerate(source_family.members)}
    pair_values = source_family.approval.proposal.pair_evidence
    pair_indexes = {id(pair): index for index, pair in enumerate(pair_values)}
    if len(member_indexes) != len(source_family.members) or len(pair_indexes) != len(pair_values):
        _fail("variant source-family values must be distinct retained values")

    selected_members = _identity_references(
        variant.members,
        member_indexes,
        "variant members",
    )
    projection = variant.proposal.projection
    if type(projection) is not SellableVariantEvidenceProjection:
        _fail("variant projection has the wrong type")
    direct_exact = _identity_references(
        projection.direct_exact_evidence,
        pair_indexes,
        "projection direct exact evidence",
    )
    gaps = []
    if type(projection.exactness_gaps) is not tuple:
        _fail("projection exactness gaps must be an exact tuple")
    for gap in projection.exactness_gaps:
        if type(gap) is not SellableVariantExactnessGap:
            _fail("projection gaps must be exact SellableVariantExactnessGap values")
        direct = _identity_reference(gap.direct_evidence, pair_indexes, "gap direct evidence")
        witness = _identity_references(gap.witness_path, pair_indexes, "gap witness path")
        gaps.append({"direct_evidence": direct, "witness_path": witness})
    expected_direct, expected_gaps = _expected_projection(pair_values, len(source_family.members))
    if direct_exact != expected_direct or gaps != expected_gaps:
        _fail("variant projection does not match retained source-family lineage")

    selected_pairs = _identity_references(
        variant.proposal.pair_evidence,
        pair_indexes,
        "variant selected pair evidence",
    )
    approval = variant.approval
    if type(approval) is not SellableVariantDecisionRecord:
        _fail("variant approval must be an exact SellableVariantDecisionRecord")
    if approval.decision is not SellableVariantDecision.APPROVE:
        _fail("canonical variant approval must be APPROVE")
    return {
        "variant_id": variant.variant_id,
        "source_family": source_family_index,
        "members": selected_members,
        "projection": {
            "direct_exact_evidence": direct_exact,
            "exactness_gaps": gaps,
        },
        "pair_evidence": selected_pairs,
        "approval": _encode_decision(
            approval.decision,
            approval.actor,
            approval.decided_at,
            SellableVariantDecision,
        ),
    }


def _decode_catalog_document(document: object) -> CanonicalCatalogState:
    root = _require_object(document, {"schema", "version", "families", "variants"}, "catalog")
    if type(root["schema"]) is not str or root["schema"] != CANONICAL_CATALOG_SCHEMA:
        _fail("unsupported canonical catalog schema")
    if type(root["version"]) is not int or root["version"] != CANONICAL_CATALOG_SCHEMA_VERSION:
        _fail("unsupported canonical catalog schema version")
    family_documents = _require_list(root["families"], "families")
    variant_documents = _require_list(root["variants"], "variants")

    catalog = create_empty_canonical_catalog()
    families: list[CanonicalProductFamily] = []
    for value in family_documents:
        family = _decode_family(value)
        catalog = register_canonical_family(catalog, family).catalog
        families.append(family)

    for value in variant_documents:
        variant = _decode_variant(value, tuple(families))
        catalog = register_canonical_variant(catalog, variant).catalog
    return catalog


def _decode_family(value: object) -> CanonicalProductFamily:
    data = _require_object(value, {"family_id", "members", "pairs", "approval"}, "family")
    family_id = _require_string(data["family_id"], "family_id")
    members = tuple(_decode_member(item) for item in _require_list(data["members"], "members"))
    if len(members) < 2:
        _fail("canonical family must contain at least two members")
    if len(set(members)) != len(members):
        _fail("canonical family members must be unique")

    pairs_data = _require_list(data["pairs"], "pairs")
    expected_count = len(members) * (len(members) - 1) // 2
    if len(pairs_data) != expected_count:
        _fail("canonical family pair evidence is not complete")
    pairs = tuple(_decode_pair(item, members) for item in pairs_data)
    expected_endpoints = tuple(
        (members[left], members[right])
        for left in range(len(members))
        for right in range(left + 1, len(members))
    )
    if any(
        pair.left is not left or pair.right is not right
        for pair, (left, right) in zip(pairs, expected_endpoints)
    ):
        _fail("family pairs are not in canonical member-pair order")

    proposal = _rehydrate_family_merge_proposal(members=members, pair_evidence=pairs)
    approval_data = _decode_decision(data["approval"], FamilyMergeDecision)
    approval = FamilyMergeDecisionRecord(proposal=proposal, **approval_data)
    return create_canonical_family(approval, family_id=family_id)


def _decode_member(value: object) -> SourceObservationIdentity:
    data = _require_object(
        value,
        {"source_pack_id", "platform", "source_product_id", "product_url", "observed_at"},
        "member",
    )
    source_product_id = data["source_product_id"]
    if source_product_id is not None:
        source_product_id = _require_string(source_product_id, "source_product_id")
    return SourceObservationIdentity(
        source_pack_id=_require_string(data["source_pack_id"], "source_pack_id"),
        platform=_require_string(data["platform"], "platform"),
        source_product_id=source_product_id,
        product_url=_require_string(data["product_url"], "product_url"),
        observed_at=_decode_datetime(data["observed_at"]),
    )


def _decode_pair(
    value: object,
    members: tuple[SourceObservationIdentity, ...],
) -> FamilyMergePairEvidence:
    data = _require_object(
        value,
        {"left_member", "right_member", "relationship", "confidence", "reasons", "evidence"},
        "pair",
    )
    left = _require_index(data["left_member"], len(members), "left_member")
    right = _require_index(data["right_member"], len(members), "right_member")
    if left >= right:
        _fail("pair endpoints must be distinct and canonically oriented")
    relationship_text = _require_string(data["relationship"], "relationship")
    try:
        relationship = ProductRelationship(relationship_text)
    except ValueError as exc:
        raise CanonicalCatalogCodecError("invalid pair relationship") from exc
    confidence = _decode_confidence(data["confidence"])
    reasons_data = _require_list(data["reasons"], "reasons")
    reasons = tuple(_require_string(reason, "reason") for reason in reasons_data)
    evidence = tuple(
        ResolutionEvidence(
            code=_require_string(
                _require_object(item, {"code", "detail"}, "resolution evidence")["code"],
                "evidence code",
            ),
            detail=_require_string(item["detail"], "evidence detail"),
        )
        for item in _require_list(data["evidence"], "evidence")
    )
    return FamilyMergePairEvidence(
        left=members[left],
        right=members[right],
        relationship=relationship,
        confidence=confidence,
        reasons=reasons,
        evidence=evidence,
    )


def _decode_variant(
    value: object,
    families: tuple[CanonicalProductFamily, ...],
) -> CanonicalSellableVariant:
    data = _require_object(
        value,
        {"variant_id", "source_family", "members", "projection", "pair_evidence", "approval"},
        "variant",
    )
    variant_id = _require_string(data["variant_id"], "variant_id")
    family_index = _require_index(data["source_family"], len(families), "source_family")
    family = families[family_index]
    pair_values = family.approval.proposal.pair_evidence

    member_refs = _decode_references(data["members"], len(family.members), "variant members")
    if member_refs != sorted(member_refs):
        _fail("variant member references must be in canonical order")
    members = tuple(family.members[index] for index in member_refs)

    projection_data = _require_object(
        data["projection"],
        {"direct_exact_evidence", "exactness_gaps"},
        "projection",
    )
    direct_refs = _decode_references(
        projection_data["direct_exact_evidence"],
        len(pair_values),
        "direct exact evidence",
    )
    gap_data = _require_list(projection_data["exactness_gaps"], "exactness_gaps")
    decoded_gap_refs: list[dict[str, object]] = []
    gaps: list[SellableVariantExactnessGap] = []
    for item in gap_data:
        gap = _require_object(item, {"direct_evidence", "witness_path"}, "exactness gap")
        direct = _require_index(gap["direct_evidence"], len(pair_values), "gap direct evidence")
        witness = _decode_references(
            gap["witness_path"],
            len(pair_values),
            "gap witness path",
        )
        decoded_gap_refs.append({"direct_evidence": direct, "witness_path": witness})
        gaps.append(
            SellableVariantExactnessGap(
                direct_evidence=pair_values[direct],
                witness_path=tuple(pair_values[index] for index in witness),
            )
        )
    expected_direct, expected_gaps = _expected_projection(pair_values, len(family.members))
    if direct_refs != expected_direct or decoded_gap_refs != expected_gaps:
        _fail("variant projection references are inconsistent with its source family")
    projection = SellableVariantEvidenceProjection(
        source_family=family,
        direct_exact_evidence=tuple(pair_values[index] for index in direct_refs),
        exactness_gaps=tuple(gaps),
    )

    selected_pair_refs = _decode_references(
        data["pair_evidence"],
        len(pair_values),
        "variant pair evidence",
    )
    proposal = _rehydrate_sellable_variant_proposal(
        projection=projection,
        members=members,
        pair_evidence=tuple(pair_values[index] for index in selected_pair_refs),
    )
    approval_data = _decode_decision(data["approval"], SellableVariantDecision)
    approval = SellableVariantDecisionRecord(proposal=proposal, **approval_data)
    return create_canonical_sellable_variant(approval, variant_id=variant_id)


def _decode_decision(value: object, enum_type: type) -> dict[str, object]:
    data = _require_object(value, {"decision", "actor", "decided_at"}, "approval")
    decision_text = _require_string(data["decision"], "decision")
    try:
        decision = enum_type(decision_text)
    except ValueError as exc:
        raise CanonicalCatalogCodecError("invalid approval decision") from exc
    if decision.value != "APPROVE":
        _fail("canonical approvals must retain an APPROVE decision")
    return {
        "decision": decision,
        "actor": _require_string(data["actor"], "actor"),
        "decided_at": _decode_datetime(data["decided_at"]),
    }


def _expected_projection(
    pairs: tuple[FamilyMergePairEvidence, ...],
    member_count: int,
) -> tuple[list[int], list[dict[str, object]]]:
    endpoints = tuple(
        (left, right)
        for left in range(member_count)
        for right in range(left + 1, member_count)
    )
    if len(pairs) != len(endpoints):
        _fail("source family pair evidence is incomplete")
    pair_index_by_endpoints = {
        endpoint: index for index, endpoint in enumerate(endpoints)
    }
    direct = [
        index
        for index, pair in enumerate(pairs)
        if pair.relationship is ProductRelationship.EXACT_VARIANT_MATCH
    ]
    adjacency: dict[int, list[tuple[int, int]]] = {
        position: [] for position in range(member_count)
    }
    for pair_index in direct:
        left, right = endpoints[pair_index]
        adjacency[left].append((right, pair_index))
        adjacency[right].append((left, pair_index))
    for neighbors in adjacency.values():
        neighbors.sort(key=lambda value: value[0])

    gaps: list[dict[str, object]] = []
    for left, right in endpoints:
        direct_index = pair_index_by_endpoints[(left, right)]
        if direct_index in direct:
            continue
        witness = _shortest_exact_path(left, right, adjacency)
        if witness is not None:
            gaps.append({"direct_evidence": direct_index, "witness_path": witness})
    return direct, gaps


def _shortest_exact_path(
    start: int,
    end: int,
    adjacency: dict[int, list[tuple[int, int]]],
) -> list[int] | None:
    queue = deque([(start, [])])
    visited = {start}
    while queue:
        current, path = queue.popleft()
        for neighbor, pair_index in adjacency[current]:
            if neighbor in visited:
                continue
            next_path = [*path, pair_index]
            if neighbor == end:
                return next_path
            visited.add(neighbor)
            queue.append((neighbor, next_path))
    return None


def _identity_references(values: object, indexes: dict[int, int], label: str) -> list[int]:
    if type(values) is not tuple:
        _fail(f"{label} must be an exact tuple")
    references = [_identity_reference(value, indexes, label) for value in values]
    if len(set(references)) != len(references):
        _fail(f"{label} must not contain duplicate references")
    return references


def _identity_reference(value: object, indexes: dict[int, int], label: str) -> int:
    try:
        return indexes[id(value)]
    except KeyError as exc:
        raise CanonicalCatalogCodecError(f"{label} must reuse source-family values") from exc


def _decode_references(value: object, size: int, label: str) -> list[int]:
    references = [
        _require_index(item, size, label) for item in _require_list(value, label)
    ]
    if len(set(references)) != len(references):
        _fail(f"{label} contains duplicate references")
    return references


def _encode_datetime(value: object) -> str:
    if type(value) is not datetime or value.tzinfo is None:
        _fail("retained datetimes must be exact timezone-aware datetime values")
    try:
        offset = value.utcoffset()
        if offset is None:
            _fail("retained datetimes must be timezone-aware")
        utc = value.astimezone(timezone.utc)
    except (OverflowError, ValueError) as exc:
        raise CanonicalCatalogCodecError("retained datetime is invalid") from exc
    return (
        f"{utc.year:04d}-{utc.month:02d}-{utc.day:02d}T"
        f"{utc.hour:02d}:{utc.minute:02d}:{utc.second:02d}."
        f"{utc.microsecond:06d}Z"
    )


def _decode_datetime(value: object) -> datetime:
    text = _require_string(value, "datetime")
    match = _DATETIME_RE.fullmatch(text)
    if match is None:
        _fail("datetime must use fixed-microsecond UTC Z representation")
    parts = tuple(int(part) for part in match.groups())
    try:
        return datetime(*parts, tzinfo=timezone.utc)
    except ValueError as exc:
        raise CanonicalCatalogCodecError("datetime value is invalid") from exc


def _canonical_confidence(value: object) -> float:
    if type(value) not in (int, float):
        _fail("confidence must be a finite JSON number")
    converted = float(value)
    if not math.isfinite(converted) or not 0.0 <= converted <= 1.0:
        _fail("confidence must be finite and between 0.0 and 1.0")
    return 0.0 if converted == 0.0 else converted


def _decode_confidence(value: object) -> float:
    if type(value) not in (int, float):
        _fail("confidence must be a JSON number")
    return _canonical_confidence(value)


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            _fail("duplicate JSON object key")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> NoReturn:
    raise CanonicalCatalogCodecError(f"non-finite JSON number is not permitted: {value}")


def _require_object(value: object, fields: set[str], label: str) -> dict[str, object]:
    if type(value) is not dict:
        _fail(f"{label} must be a JSON object")
    if set(value) != fields:
        _fail(f"{label} has unknown or missing fields")
    return value


def _require_list(value: object, label: str) -> list[object]:
    if type(value) is not list:
        _fail(f"{label} must be a JSON array")
    return value


def _require_string(value: object, label: str) -> str:
    if type(value) is not str:
        _fail(f"{label} must be a JSON string")
    return value


def _require_index(value: object, size: int, label: str) -> int:
    if type(value) is not int or value < 0 or value >= size:
        _fail(f"{label} must be an in-range integer index")
    return value


def _fail(message: str) -> NoReturn:
    raise CanonicalCatalogCodecError(message)


__all__ = [
    "CANONICAL_CATALOG_SCHEMA",
    "CANONICAL_CATALOG_SCHEMA_VERSION",
    "CanonicalCatalogCodecError",
    "decode_canonical_catalog",
    "encode_canonical_catalog",
]
