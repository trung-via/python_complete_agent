"""TASK-139 regressions for deterministic family review planning."""

from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timezone

import pytest

import src.product_intelligence as product_intelligence
from src.product_intelligence import family_review_planning
from src.product_intelligence.entity_grouping import (
    ProvisionalGroupingResult,
    ProvisionalGroupStatus,
    ProvisionalProductFamilyGroup,
    group_resolution_graph,
)
from src.product_intelligence.entity_resolution import (
    EntityResolutionResult,
    ProductRelationship,
    ResolutionEvidence,
    SourceObservationIdentity,
)
from src.product_intelligence.entity_resolution_graph import (
    MultiObservationResolutionError,
    MultiObservationResolutionGraph,
)
from src.product_intelligence.family_merge_approval import (
    FamilyMergeDecision,
    create_family_merge_decision_record,
    create_family_merge_proposal,
)
from src.product_intelligence.family_review_planning import (
    FamilyKnowledgeReviewPlan,
    FamilyKnowledgeReviewPlanningError,
    plan_family_knowledge_review,
)
from src.product_intelligence.source_evidence_intake import (
    SourceEvidenceInventory,
    intake_product_source_evidence,
)
from src.product_source.models import ProductFact, ProductSourcePack
from src.product_source.serialization import serialize_source_pack


def _identity(name: str) -> SourceObservationIdentity:
    return SourceObservationIdentity(
        source_pack_id=f"pack-{name}",
        platform="test-market",
        source_product_id=name,
        product_url=f"https://market.example/{name}",
        observed_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )


def _pair(
    left: SourceObservationIdentity,
    right: SourceObservationIdentity,
    relationship: ProductRelationship,
) -> EntityResolutionResult:
    return EntityResolutionResult(
        relationship=relationship,
        confidence=0.9,
        left=left,
        right=right,
        reasons=(relationship.value,),
        evidence=(ResolutionEvidence("TASK-139", relationship.value),),
    )


def _two_actionable_group_graph() -> MultiObservationResolutionGraph:
    a, b, c, d = (_identity(name) for name in "abcd")
    return MultiObservationResolutionGraph(
        observations=(d, b, a, c),
        pairwise_results=(
            _pair(a, b, ProductRelationship.SAME_PRODUCT_FAMILY),
            _pair(c, d, ProductRelationship.EXACT_VARIANT_MATCH),
            _pair(a, c, ProductRelationship.DIFFERENT_PRODUCT),
            _pair(a, d, ProductRelationship.DIFFERENT_PRODUCT),
            _pair(b, c, ProductRelationship.DIFFERENT_PRODUCT),
            _pair(b, d, ProductRelationship.DIFFERENT_PRODUCT),
        ),
        conflicts=(),
    )


def _inventory(pack_count: int = 2) -> SourceEvidenceInventory:
    packs = tuple(
        ProductSourcePack(
            source_pack_id=f"pack-{index}",
            platform="test-market",
            product_url=f"https://market.example/{index}",
            observed_at=datetime(2026, 9, index + 1, tzinfo=timezone.utc),
            collector="task-139-test",
        )
        for index in range(pack_count)
    )
    return SourceEvidenceInventory(
        tuple(f"manifest-{index}" for index in range(pack_count)), packs
    )


def test_public_surface_is_exact_and_plan_is_factory_only_and_frozen(monkeypatch):
    expected = {
        "FamilyKnowledgeReviewPlanningError",
        "FamilyKnowledgeReviewPlan",
        "plan_family_knowledge_review",
    }
    assert family_review_planning.__all__ == [
        "FamilyKnowledgeReviewPlanningError",
        "FamilyKnowledgeReviewPlan",
        "plan_family_knowledge_review",
    ]
    assert {
        name for name in vars(family_review_planning) if not name.startswith("_")
    } == expected
    assert [field.name for field in fields(FamilyKnowledgeReviewPlan)] == [
        "inventory",
        "graph",
        "groups",
        "proposals",
    ]
    assert all(product_intelligence.__all__.count(name) == 1 for name in expected)

    inventory = _inventory()
    graph = _two_actionable_group_graph()
    groups = group_resolution_graph(graph).groups
    proposals = tuple(create_family_merge_proposal(graph, group) for group in groups)
    with pytest.raises(FamilyKnowledgeReviewPlanningError, match="must be created"):
        FamilyKnowledgeReviewPlan(inventory, graph, groups, proposals)

    monkeypatch.setattr(family_review_planning, "_resolve_multi_observations", lambda _: graph)
    plan = plan_family_knowledge_review(inventory)
    with pytest.raises(FrozenInstanceError):
        plan.inventory = _inventory()


def test_exact_delegation_lineage_actionability_and_order(monkeypatch):
    inventory = _inventory(4)
    graph = _two_actionable_group_graph()
    grouping = group_resolution_graph(graph)
    expected_proposals = tuple(
        create_family_merge_proposal(graph, group) for group in grouping.groups
    )
    calls = []

    def resolve(source_packs):
        calls.append(("resolve", source_packs))
        return graph

    def group(received_graph):
        calls.append(("group", received_graph))
        return grouping

    def propose(received_graph, received_group):
        calls.append(("propose", received_graph, received_group))
        index = grouping.groups.index(received_group)
        return expected_proposals[index]

    monkeypatch.setattr(family_review_planning, "_resolve_multi_observations", resolve)
    monkeypatch.setattr(family_review_planning, "_group_resolution_graph", group)
    monkeypatch.setattr(family_review_planning, "_create_family_merge_proposal", propose)

    plan = plan_family_knowledge_review(inventory)

    assert plan.inventory is inventory
    assert plan.graph is graph
    assert plan.groups is grouping.groups
    assert plan.proposals == expected_proposals
    assert all(actual is expected for actual, expected in zip(plan.proposals, expected_proposals))
    assert calls[0] == ("resolve", inventory.source_packs)
    assert calls[0][1] is inventory.source_packs
    assert calls[1] == ("group", graph)
    assert calls[2:] == [
        ("propose", graph, grouping.groups[0]),
        ("propose", graph, grouping.groups[1]),
    ]


def test_singleton_and_conflicted_groups_remain_visible_without_proposals(monkeypatch):
    inventory = _inventory()
    graph = _two_actionable_group_graph()
    a, b, c = (_identity(name) for name in "xyz")
    marker = object()
    singleton = ProvisionalProductFamilyGroup(
        members=(a,), status=ProvisionalGroupStatus.SINGLETON, conflicts=()
    )
    conflicted = ProvisionalProductFamilyGroup(
        members=(b, c), status=ProvisionalGroupStatus.CONFLICTED, conflicts=(marker,)
    )
    grouping = ProvisionalGroupingResult((singleton, conflicted))
    monkeypatch.setattr(family_review_planning, "_resolve_multi_observations", lambda _: graph)
    monkeypatch.setattr(family_review_planning, "_group_resolution_graph", lambda _: grouping)
    monkeypatch.setattr(
        family_review_planning,
        "_create_family_merge_proposal",
        lambda *_: pytest.fail("non-actionable groups must not reach TASK-112"),
    )

    plan = plan_family_knowledge_review(inventory)

    assert plan.groups is grouping.groups
    assert plan.groups == (singleton, conflicted)
    assert plan.proposals == ()


def test_wrong_inventory_and_upstream_failures_propagate(monkeypatch):
    with pytest.raises(FamilyKnowledgeReviewPlanningError, match="exact SourceEvidenceInventory"):
        plan_family_knowledge_review(object())

    with pytest.raises(MultiObservationResolutionError):
        plan_family_knowledge_review(SourceEvidenceInventory((), ()))

    inventory = _inventory()
    graph = _two_actionable_group_graph()
    grouping = group_resolution_graph(graph)
    sentinel = RuntimeError("upstream sentinel")
    for name, setup in (
        ("_resolve_multi_observations", {}),
        ("_group_resolution_graph", {"_resolve_multi_observations": lambda _: graph}),
        (
            "_create_family_merge_proposal",
            {
                "_resolve_multi_observations": lambda _: graph,
                "_group_resolution_graph": lambda _: grouping,
            },
        ),
    ):
        with monkeypatch.context() as scoped:
            for dependency, value in setup.items():
                scoped.setattr(family_review_planning, dependency, value)

            def fail(*_args, **_kwargs):
                raise sentinel

            scoped.setattr(family_review_planning, name, fail)
            with pytest.raises(RuntimeError) as captured:
                plan_family_knowledge_review(inventory)
            assert captured.value is sentinel


def test_real_serialized_p2_inventory_reaches_unchanged_task_112_decision(tmp_path):
    facts = (
        ProductFact("Brand", "Acme", "specifications", "structured"),
        ProductFact("Model", "Phone X", "specifications", "structured"),
        ProductFact("Color", "Black", "specifications", "structured"),
    )
    packs = tuple(
        ProductSourcePack(
            source_pack_id=f"serialized-{index}",
            platform=platform,
            product_url=f"https://{platform}.example/{index}",
            source_product_id=str(index),
            observed_at=datetime(2026, 9, index + 1, tzinfo=timezone.utc),
            collector="task-139-compatibility",
            facts=facts,
        )
        for index, platform in enumerate(("shopee", "tiktok"), start=1)
    )
    for index, pack in enumerate(packs):
        serialize_source_pack(pack, str(tmp_path / f"source-{index}"))

    inventory = intake_product_source_evidence((str(tmp_path),))
    plan = plan_family_knowledge_review(inventory)

    assert plan.inventory is inventory
    assert len(plan.proposals) == 1
    proposal = plan.proposals[0]
    decision = create_family_merge_decision_record(
        proposal,
        decision=FamilyMergeDecision.APPROVE,
        actor="human-reviewer",
        decided_at=datetime(2026, 9, 6, tzinfo=timezone.utc),
    )
    assert decision.proposal is proposal
    assert not hasattr(plan, "family_id")
    assert not hasattr(plan, "variant_id")


def test_module_has_no_external_or_later_p3_authority_names():
    forbidden = {
        "open",
        "Path",
        "sqlite3",
        "requests",
        "uuid",
        "datetime",
        "create_family_merge_decision_record",
        "create_canonical_family",
        "create_canonical_sellable_variant",
        "register_canonical_family",
        "register_sqlite_canonical_family",
    }
    assert forbidden.isdisjoint(vars(family_review_planning))
