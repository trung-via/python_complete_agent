"""Credentialed TASK-144 Vertex ADC certification through the TASK-135 chain."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.core.errors import AgentException
from src.product_intelligence.canonical_catalog_sqlite import (
    create_sqlite_canonical_catalog,
    register_sqlite_canonical_family,
    register_sqlite_canonical_variant,
)
from src.product_intelligence.canonical_family import create_canonical_family
from src.product_intelligence.canonical_rag_context import CanonicalRagContext
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
from src.product_intelligence.grounded_answer import GroundedAnswer, GroundedAnswerError
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


_OBSERVED_AT = datetime(2026, 9, 1, 8, 0, tzinfo=timezone.utc)
_DECIDED_AT = datetime(2026, 9, 1, 9, 0, tzinfo=timezone.utc)


def _pack(suffix: str, color: str) -> ProductSourcePack:
    return ProductSourcePack(
        source_pack_id=f"task-144-pack-{suffix}",
        platform=f"task-144-market-{suffix}",
        product_url=f"https://example.invalid/task-144/{suffix}",
        observed_at=_OBSERVED_AT,
        collector="task-144-fixture",
        title=f"Task 144 Example Lamp {color}",
        source_product_id=f"task-144-listing-{suffix}",
        shop_name="Task 144 Example Shop",
        brand="Example Brand",
        model_sku="EXAMPLE-LAMP-144",
        description_text=f"Deterministic fixture evidence for the {color} lamp.",
        facts=(
            ProductFact(
                key="Color",
                value=color,
                unit=None,
                source_section="specifications",
                provenance="fixture",
            ),
        ),
    )


def _build_fixture(tmp_path) -> tuple[object, tuple[str, str]]:
    left_pack = _pack("left", "Blue")
    right_pack = _pack("right", "Blue")
    left_path = serialize_source_pack(left_pack, str(tmp_path / "source-left"))
    right_path = serialize_source_pack(right_pack, str(tmp_path / "source-right"))

    left = SourceObservationIdentity.from_pack(left_pack)
    right = SourceObservationIdentity.from_pack(right_pack)
    pair = EntityResolutionResult(
        relationship=ProductRelationship.EXACT_VARIANT_MATCH,
        confidence=1.0,
        left=right,
        right=left,
        reasons=("Deterministic fixture exact-variant relationship.",),
        evidence=(
            ResolutionEvidence(
                "TASK_144_FIXTURE_MATCH",
                "The fixture observations describe the same example sellable variant.",
            ),
        ),
    )
    graph = MultiObservationResolutionGraph(
        observations=(right, left),
        pairwise_results=(pair,),
        conflicts=(),
    )
    family_proposal = create_family_merge_proposal(
        graph, group_resolution_graph(graph).groups[0]
    )
    family_decision = create_family_merge_decision_record(
        family_proposal,
        decision=FamilyMergeDecision.APPROVE,
        actor="task-144-human-fixture",
        decided_at=_DECIDED_AT,
    )
    family = create_canonical_family(
        family_decision, family_id="task-144-example-family"
    )
    variant_proposal = create_sellable_variant_proposal(
        family, (left, right)
    )
    variant_decision = create_sellable_variant_decision_record(
        variant_proposal,
        decision=SellableVariantDecision.APPROVE,
        actor="task-144-human-fixture",
        decided_at=_DECIDED_AT,
    )
    variant = create_canonical_sellable_variant(
        variant_decision, variant_id="task-144-example-blue-lamp"
    )

    catalog_path = tmp_path / "task-144-catalog.sqlite"
    create_sqlite_canonical_catalog(catalog_path)
    register_sqlite_canonical_family(catalog_path, family)
    register_sqlite_canonical_variant(catalog_path, variant)
    return catalog_path, (left_path, right_path)


def _is_provider_availability_failure(error: GroundedInvocationError) -> bool:
    cause = error.__cause__
    while cause is not None:
        if isinstance(cause, AgentException) and cause.code == "LLM_PROVIDER_ERROR":
            return True
        cause = cause.__cause__
    return False


@pytest.mark.asyncio
async def test_live_grounded_qa_through_vertex_adc(tmp_path) -> None:
    catalog_path, source_paths = _build_fixture(tmp_path)
    provider = GeminiProvider(
        backend="vertex_ai",
        model_name="gemini-3.8-flash",
        location="global",
    )

    try:
        answer = await answer_persisted_grounded_question(
            catalog_path,
            source_paths,
            question="What color is the admitted example lamp?",
            provider=provider,
        )
    except GroundedInvocationError as exc:
        if _is_provider_availability_failure(exc):
            pytest.fail("Vertex AI provider is unavailable.", pytrace=False)
        pytest.fail(
            "Grounded invocation or response-structure validation failed.",
            pytrace=False,
        )
    except GroundedAnswerError:
        pytest.fail("Grounded answer structural validation failed.", pytrace=False)

    if type(answer) is not GroundedAnswer:
        pytest.fail("TASK-135 did not return an exact GroundedAnswer.", pytrace=False)
    if type(answer.context) is not CanonicalRagContext or not answer.context.hits:
        pytest.fail("GroundedAnswer canonical context is empty.", pytrace=False)
    if not any(
        hit.hit.witnesses or hit.supplemental_evidence
        for hit in answer.context.hits
    ):
        pytest.fail("GroundedAnswer canonical evidence is empty.", pytrace=False)
