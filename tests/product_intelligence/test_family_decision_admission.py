"""TASK-140 regressions for planned family decision and durable admission."""

from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timezone

import pytest

import src.product_intelligence as product_intelligence
from src.product_intelligence import family_decision_admission
from src.product_intelligence.canonical_catalog import (
    CatalogRegistrationStatus,
    create_empty_canonical_catalog,
    register_canonical_family,
)
from src.product_intelligence.canonical_catalog_sqlite import (
    create_sqlite_canonical_catalog,
    load_sqlite_canonical_catalog,
)
from src.product_intelligence.canonical_family import (
    CanonicalFamilyAdmissionError,
    create_canonical_family,
)
from src.product_intelligence.family_decision_admission import (
    DurableFamilyAdmissionResult,
    FamilyDecisionAdmissionError,
    durably_admit_planned_family,
    record_planned_family_decision,
)
from src.product_intelligence.family_merge_approval import (
    FamilyMergeApprovalError,
    FamilyMergeDecision,
    create_family_merge_decision_record,
)
from src.product_intelligence.family_review_planning import (
    plan_family_knowledge_review,
)
from src.product_intelligence.source_evidence_intake import SourceEvidenceInventory
from src.product_source.models import ProductFact, ProductSourcePack


_DECIDED_AT = datetime(2026, 9, 6, 9, 30, tzinfo=timezone.utc)


def _real_plan(*, suffix: str = ""):
    facts = (
        ProductFact("Brand", "Acme", "specifications", "structured"),
        ProductFact("Model", "Phone X", "specifications", "structured"),
        ProductFact("Color", "Black", "specifications", "structured"),
    )
    packs = tuple(
        ProductSourcePack(
            source_pack_id=f"task-140-{platform}{suffix}",
            platform=platform,
            product_url=f"https://{platform}.example/item{suffix}",
            source_product_id=f"item-{platform}{suffix}",
            observed_at=datetime(2026, 9, index, tzinfo=timezone.utc),
            collector="task-140-test",
            facts=facts,
        )
        for index, platform in enumerate(("shopee", "tiktok"), start=1)
    )
    inventory = SourceEvidenceInventory(
        tuple(f"manifest-{index}{suffix}" for index in range(2)),
        packs,
    )
    plan = plan_family_knowledge_review(inventory)
    assert len(plan.proposals) == 1
    return plan


def _approve(plan):
    return record_planned_family_decision(
        plan,
        plan.proposals[0],
        decision=FamilyMergeDecision.APPROVE,
        actor="human-reviewer",
        decided_at=_DECIDED_AT,
    )


def test_public_surface_and_result_are_exact_factory_only_and_frozen(tmp_path):
    expected = {
        "FamilyDecisionAdmissionError",
        "DurableFamilyAdmissionResult",
        "record_planned_family_decision",
        "durably_admit_planned_family",
    }
    assert family_decision_admission.__all__ == [
        "FamilyDecisionAdmissionError",
        "DurableFamilyAdmissionResult",
        "record_planned_family_decision",
        "durably_admit_planned_family",
    ]
    assert {
        name
        for name in vars(family_decision_admission)
        if not name.startswith("_")
    } == expected
    assert [field.name for field in fields(DurableFamilyAdmissionResult)] == [
        "decision_record",
        "family",
        "registration",
    ]
    assert all(product_intelligence.__all__.count(name) == 1 for name in expected)

    plan = _real_plan()
    decision = _approve(plan)
    family = create_canonical_family(decision, family_id="family-task-140")
    registration = register_canonical_family(create_empty_canonical_catalog(), family)
    with pytest.raises(FamilyDecisionAdmissionError, match="must be created"):
        DurableFamilyAdmissionResult(decision, family, registration)

    database_path = tmp_path / "catalog.sqlite3"
    create_sqlite_canonical_catalog(database_path)
    result = durably_admit_planned_family(
        plan,
        decision,
        family_id="family-task-140",
        database_path=database_path,
    )
    with pytest.raises(FrozenInstanceError):
        result.family = family


def test_record_requires_exact_plan_and_exact_proposal_identity(monkeypatch):
    plan = _real_plan()
    other_plan = _real_plan()
    proposal = plan.proposals[0]
    assert other_plan.proposals[0] == proposal
    assert other_plan.proposals[0] is not proposal

    monkeypatch.setattr(
        family_decision_admission,
        "_create_family_merge_decision_record",
        lambda *_args, **_kwargs: pytest.fail("invalid lineage reached TASK-112"),
    )
    for invalid_plan, invalid_proposal in (
        (object(), proposal),
        (plan, object()),
        (plan, other_plan.proposals[0]),
        (other_plan, proposal),
    ):
        with pytest.raises(FamilyDecisionAdmissionError):
            record_planned_family_decision(
                invalid_plan,
                invalid_proposal,
                decision=FamilyMergeDecision.APPROVE,
                actor="reviewer",
                decided_at=_DECIDED_AT,
            )

    object.__setattr__(plan, "proposals", (proposal, proposal))
    with pytest.raises(FamilyDecisionAdmissionError, match="exactly once"):
        record_planned_family_decision(
            plan,
            proposal,
            decision=FamilyMergeDecision.APPROVE,
            actor="reviewer",
            decided_at=_DECIDED_AT,
        )


def test_record_delegates_once_with_unchanged_human_fields(monkeypatch):
    plan = _real_plan()
    proposal = plan.proposals[0]
    expected = create_family_merge_decision_record(
        proposal,
        decision=FamilyMergeDecision.REJECT,
        actor="human-reviewer",
        decided_at=_DECIDED_AT,
    )
    calls = []

    def record(received_proposal, *, decision, actor, decided_at):
        calls.append((received_proposal, decision, actor, decided_at))
        return expected

    monkeypatch.setattr(
        family_decision_admission,
        "_create_family_merge_decision_record",
        record,
    )
    actual = record_planned_family_decision(
        plan,
        proposal,
        decision=FamilyMergeDecision.REJECT,
        actor="human-reviewer",
        decided_at=_DECIDED_AT,
    )

    assert actual is expected
    assert calls == [
        (proposal, FamilyMergeDecision.REJECT, "human-reviewer", _DECIDED_AT)
    ]
    assert calls[0][0] is proposal
    assert calls[0][3] is _DECIDED_AT


def test_task_112_human_field_errors_propagate_unchanged():
    plan = _real_plan()
    proposal = plan.proposals[0]
    with pytest.raises(FamilyMergeApprovalError) as captured:
        record_planned_family_decision(
            plan,
            proposal,
            decision=FamilyMergeDecision.APPROVE,
            actor="",
            decided_at=_DECIDED_AT,
        )
    assert type(captured.value) is FamilyMergeApprovalError


def test_durable_admission_delegates_task_114_then_task_120_exactly_once(monkeypatch):
    plan = _real_plan()
    decision = _approve(plan)
    family = create_canonical_family(decision, family_id="opaque-family")
    registration = register_canonical_family(create_empty_canonical_catalog(), family)
    database_path = object()
    calls = []

    def admit(received_decision, *, family_id):
        calls.append(("admit", received_decision, family_id))
        return family

    def register(received_path, received_family):
        calls.append(("register", received_path, received_family))
        return registration

    monkeypatch.setattr(family_decision_admission, "_create_canonical_family", admit)
    monkeypatch.setattr(
        family_decision_admission,
        "_register_sqlite_canonical_family",
        register,
    )
    result = durably_admit_planned_family(
        plan,
        decision,
        family_id="opaque-family",
        database_path=database_path,
    )

    assert calls == [
        ("admit", decision, "opaque-family"),
        ("register", database_path, family),
    ]
    assert result.decision_record is decision
    assert result.family is family
    assert result.registration is registration


def test_durable_admission_rejects_wrong_lineage_before_delegation(monkeypatch):
    plan = _real_plan()
    other_plan = _real_plan()
    stale_decision = create_family_merge_decision_record(
        other_plan.proposals[0],
        decision=FamilyMergeDecision.APPROVE,
        actor="reviewer",
        decided_at=_DECIDED_AT,
    )
    monkeypatch.setattr(
        family_decision_admission,
        "_create_canonical_family",
        lambda *_args, **_kwargs: pytest.fail("invalid lineage reached TASK-114"),
    )
    monkeypatch.setattr(
        family_decision_admission,
        "_register_sqlite_canonical_family",
        lambda *_args, **_kwargs: pytest.fail("invalid lineage reached TASK-120"),
    )

    for invalid_plan, invalid_decision in (
        (object(), stale_decision),
        (plan, object()),
        (plan, stale_decision),
    ):
        with pytest.raises(FamilyDecisionAdmissionError):
            durably_admit_planned_family(
                invalid_plan,
                invalid_decision,
                family_id="family-id",
                database_path="catalog.sqlite3",
            )


def test_task_114_failure_propagates_and_never_calls_task_120(monkeypatch):
    plan = _real_plan()
    decision = _approve(plan)
    sentinel = CanonicalFamilyAdmissionError("TASK-114 sentinel")
    calls = []

    def fail(received_decision, *, family_id):
        calls.append((received_decision, family_id))
        raise sentinel

    monkeypatch.setattr(family_decision_admission, "_create_canonical_family", fail)
    monkeypatch.setattr(
        family_decision_admission,
        "_register_sqlite_canonical_family",
        lambda *_args: pytest.fail("TASK-120 must not run after TASK-114 failure"),
    )
    with pytest.raises(CanonicalFamilyAdmissionError) as captured:
        durably_admit_planned_family(
            plan,
            decision,
            family_id=" invalid ",
            database_path="catalog.sqlite3",
        )
    assert captured.value is sentinel
    assert calls == [(decision, " invalid ")]


def test_task_120_failure_propagates_without_retry(monkeypatch):
    plan = _real_plan()
    decision = _approve(plan)
    family = create_canonical_family(decision, family_id="family-id")
    sentinel = RuntimeError("TASK-120 sentinel")
    calls = []
    monkeypatch.setattr(
        family_decision_admission,
        "_create_canonical_family",
        lambda received, *, family_id: family,
    )

    def fail(database_path, received_family):
        calls.append((database_path, received_family))
        raise sentinel

    monkeypatch.setattr(
        family_decision_admission,
        "_register_sqlite_canonical_family",
        fail,
    )
    with pytest.raises(RuntimeError) as captured:
        durably_admit_planned_family(
            plan,
            decision,
            family_id="family-id",
            database_path="catalog.sqlite3",
        )
    assert captured.value is sentinel
    assert calls == [("catalog.sqlite3", family)]


def test_real_approve_persists_lineage_and_passes_through_both_statuses(tmp_path):
    plan = _real_plan()
    decision = _approve(plan)
    database_path = tmp_path / "catalog.sqlite3"
    create_sqlite_canonical_catalog(database_path)

    inserted = durably_admit_planned_family(
        plan,
        decision,
        family_id="family-task-140",
        database_path=database_path,
    )
    assert inserted.registration.status is CatalogRegistrationStatus.INSERTED
    assert inserted.decision_record is decision
    assert inserted.family.approval is decision

    reopened = load_sqlite_canonical_catalog(database_path)
    assert reopened.families == (inserted.family,)
    persisted = reopened.families[0]
    assert persisted == inserted.family
    assert persisted.approval == decision
    assert persisted.approval.proposal == plan.proposals[0]
    assert persisted.approval.actor == decision.actor
    assert persisted.approval.decided_at == decision.decided_at

    already_present = durably_admit_planned_family(
        plan,
        decision,
        family_id="family-task-140",
        database_path=database_path,
    )
    assert (
        already_present.registration.status
        is CatalogRegistrationStatus.ALREADY_PRESENT
    )
    assert already_present.registration.catalog.families[0] == inserted.family


def test_real_reject_has_no_durable_side_effect(tmp_path, monkeypatch):
    plan = _real_plan()
    proposal = plan.proposals[0]
    decision = record_planned_family_decision(
        plan,
        proposal,
        decision=FamilyMergeDecision.REJECT,
        actor="human-reviewer",
        decided_at=_DECIDED_AT,
    )
    assert decision.proposal is proposal
    assert decision.decision is FamilyMergeDecision.REJECT

    database_path = tmp_path / "catalog.sqlite3"
    before_catalog = create_sqlite_canonical_catalog(database_path)
    before_bytes = database_path.read_bytes()
    monkeypatch.setattr(
        family_decision_admission,
        "_register_sqlite_canonical_family",
        lambda *_args: pytest.fail("REJECT must not reach TASK-120"),
    )
    with pytest.raises(CanonicalFamilyAdmissionError):
        durably_admit_planned_family(
            plan,
            decision,
            family_id="rejected-family",
            database_path=database_path,
        )
    assert database_path.read_bytes() == before_bytes
    assert load_sqlite_canonical_catalog(database_path) == before_catalog


def test_module_has_no_independent_or_later_stage_authority_names():
    forbidden = {
        "Path",
        "sqlite3",
        "uuid",
        "random",
        "requests",
        "create_sqlite_canonical_catalog",
        "load_sqlite_canonical_catalog",
        "register_canonical_family",
        "encode_canonical_catalog",
        "decode_canonical_catalog",
        "create_family_merge_proposal",
        "create_canonical_sellable_variant",
        "register_sqlite_canonical_variant",
    }
    assert forbidden.isdisjoint(vars(family_decision_admission))
