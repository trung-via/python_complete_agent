"""Persistent grounded-QA application composition over canonical catalog knowledge.

TASK-135 provides the Phase 6 M4.6 bounded persistent application boundary that
starts from an existing TASK-120 SQLite canonical catalog and caller-supplied
persisted Product Source Pack manifests, reconstructs the exact canonical variant
profile corpus through existing M3 authorities, derives one TASK-134 retrieval query,
builds one TASK-123 canonical RAG context, and delegates grounded answer generation
to TASK-133.
"""

from collections.abc import Iterable as _Iterable
import os as _os

from src.product_intelligence.canonical_catalog_sqlite import (
    load_sqlite_canonical_catalog as _load_sqlite_canonical_catalog,
)
from src.product_intelligence.canonical_profile import (
    build_canonical_variant_profile as _build_canonical_variant_profile,
)
from src.product_intelligence.canonical_rag_context import (
    build_canonical_rag_context as _build_canonical_rag_context,
)
from src.product_intelligence.entity_resolution import (
    SourceObservationIdentity as _SourceObservationIdentity,
)
from src.product_intelligence.grounded_answer import (
    GroundedAnswer as _GroundedAnswer,
)
from src.product_intelligence.grounded_qa import (
    answer_grounded_context as _answer_grounded_context,
)
from src.product_intelligence.grounded_query_planning import (
    plan_grounded_retrieval_query as _plan_grounded_retrieval_query,
)
from src.product_source.models import (
    ProductSourcePack as _ProductSourcePack,
)
from src.product_source.serialization import (
    deserialize_product_source_pack as _deserialize_product_source_pack,
)
from src.providers.base import LLMProvider as _LLMProvider


class PersistentGroundedQaError(ValueError):
    """Raised when persisted grounded QA input is invalid or incomplete."""


async def answer_persisted_grounded_question(
    database_path: _os.PathLike[str] | str,
    source_pack_paths: _Iterable[str],
    *,
    question: str,
    provider: _LLMProvider,
    max_hits: int = 5,
    max_context_utf8_bytes: int = 32768,
) -> _GroundedAnswer:
    """Answer a grounded question against persisted catalog and source packs."""

    catalog = _load_sqlite_canonical_catalog(database_path)

    if isinstance(source_pack_paths, (str, bytes)):
        raise PersistentGroundedQaError(
            "source_pack_paths must be an iterable of manifest paths, not str or bytes"
        )
    try:
        manifest_paths = tuple(source_pack_paths)
    except TypeError as exc:
        raise PersistentGroundedQaError(
            "source_pack_paths must be an iterable of manifest paths"
        ) from exc

    for path in manifest_paths:
        if type(path) is not str or not path:
            raise PersistentGroundedQaError(
                "each member of source_pack_paths must be an exact non-empty str"
            )

    packs = tuple(_deserialize_product_source_pack(path) for path in manifest_paths)

    supplied_packs_by_identity: dict[_SourceObservationIdentity, _ProductSourcePack] = {}
    for pack in packs:
        identity = _SourceObservationIdentity.from_pack(pack)
        if identity in supplied_packs_by_identity:
            raise PersistentGroundedQaError(
                f"duplicate supplied source identity: {identity.source_pack_id}"
            )
        supplied_packs_by_identity[identity] = pack

    catalog_members: set[_SourceObservationIdentity] = set()
    for variant in catalog.variants:
        for member in variant.members:
            if member in catalog_members:
                raise PersistentGroundedQaError(
                    f"variant member {member.source_pack_id} appears in multiple variants"
                )
            catalog_members.add(member)
            if member not in supplied_packs_by_identity:
                raise PersistentGroundedQaError(
                    f"missing manifest for registered variant member: {member.source_pack_id}"
                )

    if len(supplied_packs_by_identity) != len(catalog_members):
        unbound = set(supplied_packs_by_identity.keys()) - catalog_members
        raise PersistentGroundedQaError(
            f"supplied source packs contain {len(unbound)} identities not bound to any registered variant member"
        )

    profiles = tuple(
        _build_canonical_variant_profile(
            catalog,
            variant_id=variant.variant_id,
            source_packs=tuple(
                supplied_packs_by_identity[member] for member in variant.members
            ),
        )
        for variant in catalog.variants
    )

    planned_query = _plan_grounded_retrieval_query(profiles, question=question)

    context = _build_canonical_rag_context(
        profiles,
        question=question,
        retrieval_query=planned_query,
        max_hits=max_hits,
        max_context_utf8_bytes=max_context_utf8_bytes,
    )

    return await _answer_grounded_context(context, provider)


__all__ = [
    "PersistentGroundedQaError",
    "answer_persisted_grounded_question",
]
