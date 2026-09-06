"""TASK-141 regressions for sellable-variant review and durable admission."""

from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

import src.product_intelligence as product_intelligence
from src.product_intelligence import sellable_variant_review_admission
from src.product_intelligence.canonical_catalog import (
    CatalogRegistrationStatus,
    create_empty_canonical_catalog,
    register_canonical_family,
    register_canonical_variant,
)
from src.product_intelligence.canonical_catalog_sqlite import (
    create_sqlite_canonical_catalog,
    load_sqlite_canonical_catalog,
)
from src.product_intelligence.canonical_variant import (
    CanonicalVariantAdmissionError,
    create_canonical_sellable_variant,
)
from src.product_intelligence.canonical_family import create_canonical_family
from src.product_intelligence.family_decision_admission import (
    durably_admit_planned_family,
    record_planned_family_decision,
)
from src.product_intelligence.family_merge_approval import FamilyMergeDecision
from src.product_intelligence.family_review_planning import (
    plan_family_knowledge_review,
)
from src.product_intelligence.sellable_variant_approval import (
    SellableVariantApprovalError,
    SellableVariantDecision,
    create_sellable_variant_decision_record,
    create_sellable_variant_proposal,
)
from src.product_intelligence.sellable_variant_review_admission import (
    DurableSellableVariantAdmissionResult,
    SellableVariantReview,
    SellableVariantWorkflowError,
    durably_admit_reviewed_sellable_variant,
    prepare_sellable_variant_review,
    record_reviewed_sellable_variant_decision,
)
from src.product_intelligence.source_evidence_intake import SourceEvidenceInventory
from src.product_source.models import ProductFact, ProductSourcePack


_FAMILY_DECIDED_AT = datetime(2026, 9, 6, 9, 30, tzinfo=timezone.utc)
_VARIANT_DECIDED_AT = datetime(2026, 9, 6, 10, 15, tzinfo=timezone.utc)


def _real_plan(*, suffix: str = ""):
    facts = (
        ProductFact("Brand", "Acme", "specifications", "structured"),
        ProductFact("Model", "Phone X", "specifications", "structured"),
        ProductFact("Color", "Black", "specifications", "structured"),
    )
    packs = tuple(
        ProductSourcePack(
            source_pack_id=f"task-141-{platform}{suffix}",
            platform=platform,
            product_url=f"https://{platform}.example/item{suffix}",
            source_product_id=f"item-{platform}{suffix}",
            observed_at=datetime(2026, 9, index, tzinfo=timezone.utc),
            collector="task-141-test",
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
    return inventory, plan


def _admit_family(database_path, *, suffix: str = ""):
    inventory, plan = _real_plan(suffix=suffix)
    family_decision = record_planned_family_decision(
        plan,
        plan.proposals[0],
        decision=FamilyMergeDecision.APPROVE,
        actor="family-reviewer",
        decided_at=_FAMILY_DECIDED_AT,
    )
    admitted = durably_admit_planned_family(
        plan,
        family_decision,
        family_id=f"family-task-141{suffix}",
        database_path=database_path,
    )
    return inventory, plan, family_decision, admitted.family


def test_public_surface_and_factory_only_immutable_values(tmp_path):
    expected = {
        "SellableVariantWorkflowError",
        "SellableVariantReview",
        "DurableSellableVariantAdmissionResult",
        "prepare_sellable_variant_review",
        "record_reviewed_sellable_variant_decision",
        "durably_admit_reviewed_sellable_variant",
    }
    assert sellable_variant_review_admission.__all__ == [
        "SellableVariantWorkflowError",
        "SellableVariantReview",
        "DurableSellableVariantAdmissionResult",
        "prepare_sellable_variant_review",
        "record_reviewed_sellable_variant_decision",
        "durably_admit_reviewed_sellable_variant",
    ]
    assert {
        name
        for name in vars(sellable_variant_review_admission)
        if not name.startswith("_")
    } == expected
    assert [field.name for field in fields(SellableVariantReview)] == ["proposal"]
    assert [
        field.name for field in fields(DurableSellableVariantAdmissionResult)
    ] == ["decision_record", "variant", "registration"]
    assert all(product_intelligence.__all__.count(name) == 1 for name in expected)
    assert all(
        getattr(product_intelligence, name)
        is getattr(sellable_variant_review_admission, name)
        for name in expected
    )

    database_path = tmp_path / "catalog.sqlite3"
    create_sqlite_canonical_catalog(database_path)
    _, _, _, family = _admit_family(database_path)
    proposal = create_sellable_variant_proposal(family, family.members)
    decision = create_sellable_variant_decision_record(
        proposal,
        decision=SellableVariantDecision.APPROVE,
        actor="variant-reviewer",
        decided_at=_VARIANT_DECIDED_AT,
    )
    variant = create_canonical_sellable_variant(decision, variant_id="variant-forgery")
    registration = register_canonical_variant(
        register_canonical_family(create_empty_canonical_catalog(), family).catalog,
        variant,
    )
    with pytest.raises(SellableVariantWorkflowError, match="must be created"):
        SellableVariantReview(proposal)
    with pytest.raises(SellableVariantWorkflowError, match="must be created"):
        DurableSellableVariantAdmissionResult(decision, variant, registration)

    review = prepare_sellable_variant_review(family, family.members)
    with pytest.raises(FrozenInstanceError):
        review.proposal = proposal


def test_prepare_delegates_once_with_exact_inputs_and_retains_exact_proposal(monkeypatch):
    _, plan = _real_plan()
    family_decision = record_planned_family_decision(
        plan,
        plan.proposals[0],
        decision=FamilyMergeDecision.APPROVE,
        actor="family-reviewer",
        decided_at=_FAMILY_DECIDED_AT,
    )
    family = create_canonical_family(family_decision, family_id="family-forwarding")
    selected_members = tuple(reversed(family.members))
    expected = create_sellable_variant_proposal(family, selected_members)
    calls = []

    def propose(received_family, received_members):
        calls.append((received_family, received_members))
        return expected

    monkeypatch.setattr(
        sellable_variant_review_admission,
        "_create_sellable_variant_proposal",
        propose,
    )
    review = prepare_sellable_variant_review(family, selected_members)

    assert calls == [(family, selected_members)]
    assert calls[0][0] is family
    assert calls[0][1] is selected_members
    assert review.proposal is expected
    assert not hasattr(review, "family")
    assert not hasattr(review, "selected_members")
    assert not hasattr(review, "evidence")


def test_prepare_propagates_task_116_errors_and_rejects_only_corrupt_lineage(monkeypatch):
    _, plan = _real_plan()
    family_decision = record_planned_family_decision(
        plan,
        plan.proposals[0],
        decision=FamilyMergeDecision.APPROVE,
        actor="family-reviewer",
        decided_at=_FAMILY_DECIDED_AT,
    )
    family = create_canonical_family(family_decision, family_id="family-corruption")
    sentinel = SellableVariantApprovalError("TASK-116 sentinel")
    monkeypatch.setattr(
        sellable_variant_review_admission,
        "_create_sellable_variant_proposal",
        lambda *_args: (_ for _ in ()).throw(sentinel),
    )
    with pytest.raises(SellableVariantApprovalError) as captured:
        prepare_sellable_variant_review(family, family.members)
    assert captured.value is sentinel

    other_family = create_canonical_family(family_decision, family_id="other-family")
    wrong_family_proposal = create_sellable_variant_proposal(
        other_family, other_family.members
    )
    for corrupt in (object(), wrong_family_proposal):
        monkeypatch.setattr(
            sellable_variant_review_admission,
            "_create_sellable_variant_proposal",
            lambda *_args, value=corrupt: value,
        )
        with pytest.raises(SellableVariantWorkflowError):
            prepare_sellable_variant_review(family, family.members)


def test_human_decision_delegates_once_with_unchanged_fields(monkeypatch):
    _, plan = _real_plan()
    family_decision = record_planned_family_decision(
        plan,
        plan.proposals[0],
        decision=FamilyMergeDecision.APPROVE,
        actor="family-reviewer",
        decided_at=_FAMILY_DECIDED_AT,
    )
    family = create_canonical_family(family_decision, family_id="family-human-fields")
    review = prepare_sellable_variant_review(family, family.members)
    expected = create_sellable_variant_decision_record(
        review.proposal,
        decision=SellableVariantDecision.REJECT,
        actor=" exact actor ",
        decided_at=_VARIANT_DECIDED_AT,
    )
    calls = []

    def record(proposal, *, decision, actor, decided_at):
        calls.append((proposal, decision, actor, decided_at))
        return expected

    monkeypatch.setattr(
        sellable_variant_review_admission,
        "_create_sellable_variant_decision_record",
        record,
    )
    actual = record_reviewed_sellable_variant_decision(
        review,
        decision=SellableVariantDecision.REJECT,
        actor=" exact actor ",
        decided_at=_VARIANT_DECIDED_AT,
    )

    assert actual is expected
    assert calls == [
        (
            review.proposal,
            SellableVariantDecision.REJECT,
            " exact actor ",
            _VARIANT_DECIDED_AT,
        )
    ]
    assert calls[0][0] is review.proposal
    assert calls[0][3] is _VARIANT_DECIDED_AT


def test_decision_requires_exact_review_and_task_116_errors_propagate(monkeypatch):
    sentinel = SellableVariantApprovalError("Human field sentinel")
    monkeypatch.setattr(
        sellable_variant_review_admission,
        "_create_sellable_variant_decision_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(sentinel),
    )
    with pytest.raises(SellableVariantWorkflowError):
        record_reviewed_sellable_variant_decision(
            object(),
            decision=SellableVariantDecision.APPROVE,
            actor="reviewer",
            decided_at=_VARIANT_DECIDED_AT,
        )

    # Obtain a real review without depending on durable storage.
    _, plan = _real_plan()
    family_decision = record_planned_family_decision(
        plan,
        plan.proposals[0],
        decision=FamilyMergeDecision.APPROVE,
        actor="family-reviewer",
        decided_at=_FAMILY_DECIDED_AT,
    )
    family = create_canonical_family(family_decision, family_id="family-error")
    review = prepare_sellable_variant_review(family, family.members)
    with pytest.raises(SellableVariantApprovalError) as captured:
        record_reviewed_sellable_variant_decision(
            review,
            decision=SellableVariantDecision.APPROVE,
            actor="reviewer",
            decided_at=_VARIANT_DECIDED_AT,
        )
    assert captured.value is sentinel


def test_durable_admission_enforces_identity_then_delegates_in_exact_order(monkeypatch):
    _, plan = _real_plan()
    family_decision = record_planned_family_decision(
        plan,
        plan.proposals[0],
        decision=FamilyMergeDecision.APPROVE,
        actor="family-reviewer",
        decided_at=_FAMILY_DECIDED_AT,
    )
    family = create_canonical_family(family_decision, family_id="family-order")
    review = prepare_sellable_variant_review(family, family.members)
    decision = record_reviewed_sellable_variant_decision(
        review,
        decision=SellableVariantDecision.APPROVE,
        actor="variant-reviewer",
        decided_at=_VARIANT_DECIDED_AT,
    )
    variant = create_canonical_sellable_variant(decision, variant_id="opaque-id")
    registration = register_canonical_variant(
        register_canonical_family(create_empty_canonical_catalog(), family).catalog,
        variant,
    )
    database_path = object()
    calls = []

    def admit(received_decision, *, variant_id):
        calls.append(("admit", received_decision, variant_id))
        return variant

    def register(received_path, received_variant):
        calls.append(("register", received_path, received_variant))
        return registration

    monkeypatch.setattr(
        sellable_variant_review_admission,
        "_create_canonical_sellable_variant",
        admit,
    )
    monkeypatch.setattr(
        sellable_variant_review_admission,
        "_register_sqlite_canonical_variant",
        register,
    )
    result = durably_admit_reviewed_sellable_variant(
        review,
        decision,
        variant_id="opaque-id",
        database_path=database_path,
    )

    assert calls == [
        ("admit", decision, "opaque-id"),
        ("register", database_path, variant),
    ]
    assert result.decision_record is decision
    assert result.variant is variant
    assert result.registration is registration


def test_stale_cross_review_and_reconstructed_lineage_fail_before_admission(monkeypatch):
    _, plan = _real_plan()
    family_decision = record_planned_family_decision(
        plan,
        plan.proposals[0],
        decision=FamilyMergeDecision.APPROVE,
        actor="family-reviewer",
        decided_at=_FAMILY_DECIDED_AT,
    )
    family = create_canonical_family(family_decision, family_id="family-lineage")
    review = prepare_sellable_variant_review(family, family.members)
    other_review = prepare_sellable_variant_review(family, family.members)
    assert other_review.proposal == review.proposal
    assert other_review.proposal is not review.proposal
    stale = record_reviewed_sellable_variant_decision(
        other_review,
        decision=SellableVariantDecision.APPROVE,
        actor="variant-reviewer",
        decided_at=_VARIANT_DECIDED_AT,
    )
    reconstructed = create_sellable_variant_decision_record(
        create_sellable_variant_proposal(family, family.members),
        decision=SellableVariantDecision.APPROVE,
        actor="variant-reviewer",
        decided_at=_VARIANT_DECIDED_AT,
    )
    monkeypatch.setattr(
        sellable_variant_review_admission,
        "_create_canonical_sellable_variant",
        lambda *_args, **_kwargs: pytest.fail("invalid lineage reached TASK-117"),
    )
    monkeypatch.setattr(
        sellable_variant_review_admission,
        "_register_sqlite_canonical_variant",
        lambda *_args: pytest.fail("invalid lineage reached TASK-120"),
    )

    for invalid_review, invalid_decision in (
        (object(), stale),
        (review, object()),
        (review, stale),
        (review, reconstructed),
    ):
        with pytest.raises(SellableVariantWorkflowError):
            durably_admit_reviewed_sellable_variant(
                invalid_review,
                invalid_decision,
                variant_id="variant-id",
                database_path="catalog.sqlite3",
            )


def test_task_117_and_task_120_failures_propagate_once_without_reroute(monkeypatch):
    _, plan = _real_plan()
    family_decision = record_planned_family_decision(
        plan,
        plan.proposals[0],
        decision=FamilyMergeDecision.APPROVE,
        actor="family-reviewer",
        decided_at=_FAMILY_DECIDED_AT,
    )
    family = create_canonical_family(family_decision, family_id="family-errors")
    review = prepare_sellable_variant_review(family, family.members)
    decision = record_reviewed_sellable_variant_decision(
        review,
        decision=SellableVariantDecision.APPROVE,
        actor="variant-reviewer",
        decided_at=_VARIANT_DECIDED_AT,
    )
    task_117_error = CanonicalVariantAdmissionError("TASK-117 sentinel")
    calls = []

    def fail_admission(received, *, variant_id):
        calls.append((received, variant_id))
        raise task_117_error

    monkeypatch.setattr(
        sellable_variant_review_admission,
        "_create_canonical_sellable_variant",
        fail_admission,
    )
    monkeypatch.setattr(
        sellable_variant_review_admission,
        "_register_sqlite_canonical_variant",
        lambda *_args: pytest.fail("TASK-117 failure must not reach TASK-120"),
    )
    with pytest.raises(CanonicalVariantAdmissionError) as captured:
        durably_admit_reviewed_sellable_variant(
            review,
            decision,
            variant_id=" invalid ",
            database_path="catalog.sqlite3",
        )
    assert captured.value is task_117_error
    assert calls == [(decision, " invalid ")]

    variant = create_canonical_sellable_variant(decision, variant_id="variant-errors")
    task_120_error = RuntimeError("TASK-120 sentinel")
    calls.clear()
    monkeypatch.setattr(
        sellable_variant_review_admission,
        "_create_canonical_sellable_variant",
        lambda received, *, variant_id: variant,
    )

    def fail_registration(received_path, received_variant):
        calls.append((received_path, received_variant))
        raise task_120_error

    monkeypatch.setattr(
        sellable_variant_review_admission,
        "_register_sqlite_canonical_variant",
        fail_registration,
    )
    with pytest.raises(RuntimeError) as captured:
        durably_admit_reviewed_sellable_variant(
            review,
            decision,
            variant_id="variant-errors",
            database_path="catalog.sqlite3",
        )
    assert captured.value is task_120_error
    assert calls == [("catalog.sqlite3", variant)]


def test_real_p3_approve_vertical_persists_human_and_evidence_lineage(tmp_path):
    database_path = tmp_path / "catalog.sqlite3"
    empty = create_sqlite_canonical_catalog(database_path)
    inventory, plan, family_decision, family = _admit_family(database_path)

    review = prepare_sellable_variant_review(family, family.members)
    variant_decision = record_reviewed_sellable_variant_decision(
        review,
        decision=SellableVariantDecision.APPROVE,
        actor="variant-reviewer",
        decided_at=_VARIANT_DECIDED_AT,
    )
    inserted = durably_admit_reviewed_sellable_variant(
        review,
        variant_decision,
        variant_id="variant-task-141",
        database_path=database_path,
    )

    assert empty.families == empty.variants == ()
    assert plan.inventory is inventory
    assert family.approval is family_decision
    assert review.proposal.source_family is family
    assert review.proposal.members == family.members
    assert all(
        reviewed is admitted
        for reviewed, admitted in zip(review.proposal.members, family.members)
    )
    assert variant_decision.proposal is review.proposal
    assert inserted.registration.status is CatalogRegistrationStatus.INSERTED
    assert inserted.decision_record is variant_decision
    assert inserted.variant.approval is variant_decision

    reopened = load_sqlite_canonical_catalog(database_path)
    assert reopened.families == (family,)
    assert reopened.variants == (inserted.variant,)
    persisted_family = reopened.families[0]
    persisted_variant = reopened.variants[0]
    assert persisted_family == family
    assert persisted_variant == inserted.variant
    assert persisted_variant.source_family == persisted_family
    assert persisted_variant.approval == variant_decision
    assert persisted_variant.proposal == review.proposal
    assert persisted_variant.proposal.projection == review.proposal.projection
    assert persisted_variant.proposal.pair_evidence == review.proposal.pair_evidence
    assert persisted_variant.approval.actor == "variant-reviewer"
    assert persisted_variant.approval.decided_at == _VARIANT_DECIDED_AT

    already_present = durably_admit_reviewed_sellable_variant(
        review,
        variant_decision,
        variant_id="variant-task-141",
        database_path=database_path,
    )
    assert (
        already_present.registration.status
        is CatalogRegistrationStatus.ALREADY_PRESENT
    )


def test_real_variant_reject_preserves_exact_record_and_catalog_bytes(tmp_path):
    database_path = tmp_path / "catalog.sqlite3"
    create_sqlite_canonical_catalog(database_path)
    _, _, _, family = _admit_family(database_path, suffix="-reject")
    review = prepare_sellable_variant_review(family, family.members)
    rejected = record_reviewed_sellable_variant_decision(
        review,
        decision=SellableVariantDecision.REJECT,
        actor="variant-reviewer",
        decided_at=_VARIANT_DECIDED_AT,
    )
    before_catalog = load_sqlite_canonical_catalog(database_path)
    before_bytes = database_path.read_bytes()

    with pytest.raises(CanonicalVariantAdmissionError):
        durably_admit_reviewed_sellable_variant(
            review,
            rejected,
            variant_id="rejected-variant",
            database_path=database_path,
        )

    assert rejected.proposal is review.proposal
    assert rejected.decision is SellableVariantDecision.REJECT
    assert database_path.read_bytes() == before_bytes
    assert load_sqlite_canonical_catalog(database_path) == before_catalog


def test_module_has_no_shadow_or_lower_level_authority_names():
    forbidden = {
        "Path",
        "sqlite3",
        "uuid",
        "random",
        "requests",
        "project_sellable_variant_evidence",
        "create_sqlite_canonical_catalog",
        "load_sqlite_canonical_catalog",
        "register_canonical_variant",
        "encode_canonical_catalog",
        "decode_canonical_catalog",
        "create_sellable_variant_proposal",
        "create_sellable_variant_decision_record",
        "create_canonical_sellable_variant",
        "register_sqlite_canonical_variant",
    }
    assert forbidden.isdisjoint(vars(sellable_variant_review_admission))


def test_composition_performs_no_direct_lower_level_external_or_retry_work():
    _, plan = _real_plan()
    family_decision = record_planned_family_decision(
        plan,
        plan.proposals[0],
        decision=FamilyMergeDecision.APPROVE,
        actor="family-reviewer",
        decided_at=_FAMILY_DECIDED_AT,
    )
    family = create_canonical_family(family_decision, family_id="family-no-shadow")
    proposal = create_sellable_variant_proposal(family, family.members)
    decision = create_sellable_variant_decision_record(
        proposal,
        decision=SellableVariantDecision.APPROVE,
        actor="variant-reviewer",
        decided_at=_VARIANT_DECIDED_AT,
    )
    variant = create_canonical_sellable_variant(decision, variant_id="variant-no-shadow")
    registration = register_canonical_variant(
        register_canonical_family(create_empty_canonical_catalog(), family).catalog,
        variant,
    )

    with (
        patch.object(
            sellable_variant_review_admission,
            "_create_sellable_variant_proposal",
            return_value=proposal,
        ) as task_116_proposal,
        patch.object(
            sellable_variant_review_admission,
            "_create_sellable_variant_decision_record",
            return_value=decision,
        ) as task_116_decision,
        patch.object(
            sellable_variant_review_admission,
            "_create_canonical_sellable_variant",
            return_value=variant,
        ) as task_117,
        patch.object(
            sellable_variant_review_admission,
            "_register_sqlite_canonical_variant",
            return_value=registration,
        ) as task_120,
        patch(
            "src.product_intelligence.sellable_variant_evidence."
            "project_sellable_variant_evidence"
        ) as task_115,
        patch("src.product_intelligence.canonical_catalog.register_canonical_variant")
        as task_118,
        patch("src.product_intelligence.canonical_catalog_codec.encode_canonical_catalog")
        as task_119_encode,
        patch("src.product_intelligence.canonical_catalog_codec.decode_canonical_catalog")
        as task_119_decode,
        patch("sqlite3.connect") as sqlite_connect,
        patch("uuid.uuid4") as uuid_generator,
        patch("random.random") as random_generator,
        patch("time.sleep") as retry_sleep,
        patch("builtins.open") as filesystem_open,
    ):
        review = prepare_sellable_variant_review(family, family.members)
        recorded = record_reviewed_sellable_variant_decision(
            review,
            decision=SellableVariantDecision.APPROVE,
            actor="variant-reviewer",
            decided_at=_VARIANT_DECIDED_AT,
        )
        result = durably_admit_reviewed_sellable_variant(
            review,
            recorded,
            variant_id="variant-no-shadow",
            database_path="opaque-database-path",
        )

    task_116_proposal.assert_called_once_with(family, family.members)
    task_116_decision.assert_called_once_with(
        proposal,
        decision=SellableVariantDecision.APPROVE,
        actor="variant-reviewer",
        decided_at=_VARIANT_DECIDED_AT,
    )
    task_117.assert_called_once_with(decision, variant_id="variant-no-shadow")
    task_120.assert_called_once_with("opaque-database-path", variant)
    assert result.registration is registration
    for forbidden_call in (
        task_115,
        task_118,
        task_119_encode,
        task_119_decode,
        sqlite_connect,
        uuid_generator,
        random_generator,
        retry_sleep,
        filesystem_open,
    ):
        forbidden_call.assert_not_called()
