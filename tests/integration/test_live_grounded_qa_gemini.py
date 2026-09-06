"""Credentialed P4.2 certification of the persistent grounded-QA path.

This module is intentionally a live, fail-closed certification boundary. It builds
only temporary deterministic evidence and performs one application call through
TASK-135; it does not provide reusable product or provider behavior.
"""

import asyncio
from datetime import datetime, timezone

import pytest

from src.core.errors import AgentException
from src.product_intelligence.canonical_catalog_sqlite import (
    create_sqlite_canonical_catalog,
    register_sqlite_canonical_family,
    register_sqlite_canonical_variant,
)
from src.product_intelligence.canonical_family import create_canonical_family
from src.product_intelligence.canonical_variant import (
    create_canonical_sellable_variant,
)
from src.product_intelligence.entity_grouping import group_resolution_graph
from src.product_intelligence.entity_resolution import (
    EntityResolutionResult,
    ProductRelationship,
    ResolutionEvidence,
    SourceObservationIdentity,
)
from src.product_intelligence.entity_resolution_graph import (
    MultiObservationResolutionGraph,
)
from src.product_intelligence.family_merge_approval import (
    FamilyMergeDecision,
    create_family_merge_decision_record,
    create_family_merge_proposal,
)
from src.product_intelligence.grounded_answer import (
    GroundedAnswer,
    GroundedAnswerError,
)
from src.product_intelligence.grounded_invocation import GroundedInvocationError
from src.product_intelligence.persistent_grounded_qa import (
    answer_persisted_grounded_question,
)
from src.product_intelligence.sellable_variant_approval import (
    SellableVariantDecision,
    create_sellable_variant_decision_record,
    create_sellable_variant_proposal,
)
from src.product_source.models import ProductFact, ProductSourcePack
from src.product_source.serialization import serialize_source_pack
from src.providers.gemini import GeminiProvider


_OBSERVED_AT = datetime(2026, 9, 1, 9, 0, tzinfo=timezone.utc)
_CERTIFICATION_MODEL = "gemini-3.8-flash"
_QUESTION = "What color is the Acme Trail Bottle?"


def _source_pack(name: str, platform: str) -> ProductSourcePack:
    return ProductSourcePack(
        source_pack_id=f"p4-certification-{name}",
        platform=platform,
        product_url=f"https://{platform}.fixture.invalid/products/trail-bottle",
        observed_at=_OBSERVED_AT,
        collector="task-143-deterministic-fixture",
        title="Acme Trail Bottle",
        source_product_id=f"trail-bottle-{name}",
        shop_name="Acme Fixture Shop",
        brand="Acme",
        model_sku="TRAIL-750-BLUE",
        description_text="A blue 750 ml trail bottle.",
        facts=(
            ProductFact(
                key="Color",
                value="Blue",
                unit=None,
                source_section="specifications",
                provenance="fixture table",
            ),
        ),
    )


def _persist_fixture(tmp_path):
    left_pack = _source_pack("left", "fixture-market-left")
    right_pack = _source_pack("right", "fixture-market-right")
    left_path = serialize_source_pack(left_pack, str(tmp_path / "source-left"))
    right_path = serialize_source_pack(right_pack, str(tmp_path / "source-right"))

    left = SourceObservationIdentity.from_pack(left_pack)
    right = SourceObservationIdentity.from_pack(right_pack)
    resolution = EntityResolutionResult(
        relationship=ProductRelationship.EXACT_VARIANT_MATCH,
        confidence=1.0,
        left=left,
        right=right,
        reasons=("Deterministic fixture observations describe one sellable variant.",),
        evidence=(
            ResolutionEvidence(
                "TASK143-FIXTURE-MATCH",
                "The fixed model SKU and color are identical.",
            ),
        ),
    )
    graph = MultiObservationResolutionGraph(
        observations=(left, right),
        pairwise_results=(resolution,),
        conflicts=(),
    )
    family_proposal = create_family_merge_proposal(
        graph, group_resolution_graph(graph).groups[0]
    )
    family_decision = create_family_merge_decision_record(
        family_proposal,
        decision=FamilyMergeDecision.APPROVE,
        actor="task-143-fixture-reviewer",
        decided_at=datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc),
    )
    family = create_canonical_family(
        family_decision, family_id="task-143-trail-bottle-family"
    )
    variant_proposal = create_sellable_variant_proposal(family, (left, right))
    variant_decision = create_sellable_variant_decision_record(
        variant_proposal,
        decision=SellableVariantDecision.APPROVE,
        actor="task-143-fixture-reviewer",
        decided_at=datetime(2026, 9, 1, 10, 30, tzinfo=timezone.utc),
    )
    variant = create_canonical_sellable_variant(
        variant_decision, variant_id="task-143-trail-bottle-blue"
    )

    database_path = tmp_path / "canonical-catalog.sqlite"
    create_sqlite_canonical_catalog(database_path)
    register_sqlite_canonical_family(database_path, family)
    register_sqlite_canonical_variant(database_path, variant)
    return database_path, (left_path, right_path)


def _contains_provider_availability_cause(
    error: BaseException | None,
    seen: set[int] | None = None,
) -> bool:
    if error is None:
        return False
    visited = set() if seen is None else seen
    identity = id(error)
    if identity in visited:
        return False
    visited.add(identity)
    if isinstance(error, AgentException) and error.code == "LLM_PROVIDER_ERROR":
        return True
    return _contains_provider_availability_cause(
        error.__cause__, visited
    ) or _contains_provider_availability_cause(error.__context__, visited)


def test_live_gemini_persistent_grounded_qa_certification(tmp_path):
    database_path, source_pack_paths = _persist_fixture(tmp_path)
    provider = GeminiProvider(model_name=_CERTIFICATION_MODEL)
    assert provider.model_name == _CERTIFICATION_MODEL

    failure_category = None
    try:
        answer = asyncio.run(
            answer_persisted_grounded_question(
                database_path,
                source_pack_paths,
                question=_QUESTION,
                provider=provider,
            )
        )
    except GroundedInvocationError as error:
        if _contains_provider_availability_cause(error):
            failure_category = "Gemini provider unavailable"
        else:
            failure_category = "grounded invocation or response structure invalid"
    except GroundedAnswerError:
        failure_category = "grounded answer structure invalid"

    if failure_category is not None:
        pytest.fail(f"P4.2 certification failed: {failure_category}", pytrace=False)

    assert type(answer) is GroundedAnswer
    assert answer.context.hits

