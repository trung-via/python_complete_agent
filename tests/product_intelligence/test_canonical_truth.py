"""Offline contract regressions for TASK-171 descriptive truth reconciliation.

These synthetic multi-observation profiles exercise the production contract;
they do not certify live multi-member product truth.
"""

from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timezone
from inspect import Parameter, signature
from unittest.mock import patch

import pytest

import src.product_intelligence.canonical_truth as canonical_truth_module
from src.product_intelligence import (
    CanonicalProfileObservation,
    CanonicalTruthDecision,
    CanonicalTruthDecisionAction,
    CanonicalTruthError,
    CanonicalTruthEvidenceOption,
    CanonicalTruthField,
    CanonicalTruthFieldResolution,
    CanonicalTruthResolutionStatus,
    CanonicalVariantProfile,
    CanonicalVariantTruth,
    SourceObservationIdentity,
    reconcile_canonical_variant_truth,
)


DECIDED_AT = datetime(2026, 9, 8, 9, 30, tzinfo=timezone.utc)


def member(name: str) -> SourceObservationIdentity:
    return SourceObservationIdentity(
        source_pack_id=f"pack-{name}",
        platform=f"market-{name}",
        source_product_id=f"product-{name}",
        product_url=f"https://example.test/{name}?Exact=Yes",
        observed_at=datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc),
    )


def profile_for(
    rows: tuple[
        tuple[
            str | None,
            str | None,
            str | None,
            str | None,
            str | None,
        ],
        ...,
    ],
) -> CanonicalVariantProfile:
    members = tuple(member(str(index)) for index in range(len(rows)))
    observations = tuple(
        CanonicalProfileObservation(
            member=members[index],
            collector=f"collector-{index}",
            title=row[0],
            shop_name=row[1],
            brand=row[2],
            model_sku=row[3],
            description_text=row[4],
        )
        for index, row in enumerate(rows)
    )
    return CanonicalVariantProfile(
        variant_id="Variant/Exact",
        family_id="Family/Exact",
        members=members,
        observations=observations,
        fact_evidence=(),
        media_evidence=(),
    )


def decision(
    field: CanonicalTruthField,
    action: CanonicalTruthDecisionAction,
    *,
    selected_member: SourceObservationIdentity | None = None,
    actor: str = " Human Reviewer ",
    decided_at: datetime = DECIDED_AT,
) -> CanonicalTruthDecision:
    return CanonicalTruthDecision(
        field=field,
        action=action,
        actor=actor,
        decided_at=decided_at,
        selected_member=selected_member,
    )


def resolution(
    truth: CanonicalVariantTruth,
    field: CanonicalTruthField,
) -> CanonicalTruthFieldResolution:
    return next(value for value in truth.field_resolutions if value.field is field)


def test_public_surface_fixed_fields_shapes_signature_and_immutability():
    assert canonical_truth_module.__all__ == [
        "CanonicalTruthError",
        "CanonicalTruthField",
        "CanonicalTruthDecisionAction",
        "CanonicalTruthDecision",
        "CanonicalTruthResolutionStatus",
        "CanonicalTruthEvidenceOption",
        "CanonicalTruthFieldResolution",
        "CanonicalVariantTruth",
        "reconcile_canonical_variant_truth",
    ]
    assert tuple(CanonicalTruthField) == (
        CanonicalTruthField.TITLE,
        CanonicalTruthField.SHOP_NAME,
        CanonicalTruthField.BRAND,
        CanonicalTruthField.MODEL_SKU,
        CanonicalTruthField.DESCRIPTION_TEXT,
    )
    assert tuple(CanonicalTruthDecisionAction) == (
        CanonicalTruthDecisionAction.SELECT_SOURCE,
        CanonicalTruthDecisionAction.LEAVE_UNRESOLVED,
    )
    assert tuple(CanonicalTruthResolutionStatus) == (
        CanonicalTruthResolutionStatus.NO_EVIDENCE,
        CanonicalTruthResolutionStatus.UNCONTESTED,
        CanonicalTruthResolutionStatus.HUMAN_SELECTED,
        CanonicalTruthResolutionStatus.UNRESOLVED,
    )
    assert tuple(value.name for value in fields(CanonicalTruthDecision)) == (
        "field",
        "action",
        "actor",
        "decided_at",
        "selected_member",
    )
    assert tuple(value.name for value in fields(CanonicalTruthEvidenceOption)) == (
        "value",
        "supporting_members",
    )
    assert tuple(value.name for value in fields(CanonicalTruthFieldResolution)) == (
        "field",
        "status",
        "resolved_value",
        "supporting_members",
        "options",
        "decision",
    )
    assert tuple(value.name for value in fields(CanonicalVariantTruth)) == (
        "variant_id",
        "family_id",
        "members",
        "field_resolutions",
    )
    parameters = tuple(signature(reconcile_canonical_variant_truth).parameters.values())
    assert tuple(value.name for value in parameters) == ("profile", "decisions")
    assert parameters[0].kind is Parameter.POSITIONAL_OR_KEYWORD
    assert parameters[1].kind is Parameter.KEYWORD_ONLY

    exact_profile = profile_for((("title", None, None, None, None),))
    human_decision = decision(
        CanonicalTruthField.TITLE,
        CanonicalTruthDecisionAction.LEAVE_UNRESOLVED,
    )
    option = CanonicalTruthEvidenceOption("title", exact_profile.members)
    with pytest.raises(FrozenInstanceError):
        human_decision.actor = "changed"
    with pytest.raises(FrozenInstanceError):
        option.value = "changed"


def test_all_none_is_no_evidence_in_fixed_field_order():
    exact_profile = profile_for(((None, None, None, None, None),) * 2)

    truth = reconcile_canonical_variant_truth(exact_profile)

    assert truth.variant_id is exact_profile.variant_id
    assert truth.family_id is exact_profile.family_id
    assert truth.members is exact_profile.members
    assert tuple(value.field for value in truth.field_resolutions) == tuple(
        CanonicalTruthField
    )
    assert all(
        value.status is CanonicalTruthResolutionStatus.NO_EVIDENCE
        and value.resolved_value is None
        and value.supporting_members == ()
        and value.options == ()
        and value.decision is None
        for value in truth.field_resolutions
    )


def test_one_exact_value_plus_missing_and_repeats_is_uncontested():
    exact_profile = profile_for(
        (
            (None, None, " Brand A ", None, None),
            (None, None, None, None, None),
            (None, None, " Brand A ", None, None),
        )
    )

    brand = resolution(
        reconcile_canonical_variant_truth(exact_profile), CanonicalTruthField.BRAND
    )

    assert brand.status is CanonicalTruthResolutionStatus.UNCONTESTED
    assert brand.resolved_value == " Brand A "
    assert len(brand.options) == 1
    assert brand.supporting_members == (
        exact_profile.members[0],
        exact_profile.members[2],
    )
    assert brand.options[0].supporting_members is brand.supporting_members
    assert all(
        projected is original
        for projected, original in zip(
            brand.supporting_members,
            (exact_profile.members[0], exact_profile.members[2]),
        )
    )


def test_exact_string_conflict_stays_unresolved_and_preserves_first_value_order():
    exact_profile = profile_for(
        (
            ("Title", None, "Brand", None, "shared"),
            ("Title", None, " brand ", None, "shared"),
            ("Title", None, "Brand", None, None),
        )
    )

    truth = reconcile_canonical_variant_truth(exact_profile)
    brand = resolution(truth, CanonicalTruthField.BRAND)

    assert brand.status is CanonicalTruthResolutionStatus.UNRESOLVED
    assert brand.resolved_value is None
    assert brand.supporting_members == ()
    assert brand.decision is None
    assert tuple(option.value for option in brand.options) == ("Brand", " brand ")
    assert brand.options[0].supporting_members == (
        exact_profile.members[0],
        exact_profile.members[2],
    )
    assert brand.options[1].supporting_members == (exact_profile.members[1],)
    assert resolution(truth, CanonicalTruthField.TITLE).status is (
        CanonicalTruthResolutionStatus.UNCONTESTED
    )
    assert resolution(truth, CanonicalTruthField.SHOP_NAME).status is (
        CanonicalTruthResolutionStatus.NO_EVIDENCE
    )


def test_select_source_resolves_exact_option_and_retains_all_equal_supporters():
    exact_profile = profile_for(
        (
            (None, None, "A", None, None),
            (None, None, "B", None, None),
            (None, None, "A", None, None),
        )
    )
    selected = decision(
        CanonicalTruthField.BRAND,
        CanonicalTruthDecisionAction.SELECT_SOURCE,
        selected_member=exact_profile.members[2],
    )

    brand = resolution(
        reconcile_canonical_variant_truth(exact_profile, decisions=(selected,)),
        CanonicalTruthField.BRAND,
    )

    assert brand.status is CanonicalTruthResolutionStatus.HUMAN_SELECTED
    assert brand.resolved_value == "A"
    assert brand.supporting_members == (
        exact_profile.members[0],
        exact_profile.members[2],
    )
    assert brand.decision is selected
    assert brand.decision.actor == " Human Reviewer "
    assert brand.decision.decided_at is DECIDED_AT
    assert brand.decision.selected_member is exact_profile.members[2]
    assert tuple(option.value for option in brand.options) == ("A", "B")


def test_leave_unresolved_preserves_options_and_explicit_human_record():
    exact_profile = profile_for(
        ((None, "Shop A", None, None, None), (None, "Shop B", None, None, None))
    )
    leave = decision(
        CanonicalTruthField.SHOP_NAME,
        CanonicalTruthDecisionAction.LEAVE_UNRESOLVED,
    )

    shop = resolution(
        reconcile_canonical_variant_truth(exact_profile, decisions=(leave,)),
        CanonicalTruthField.SHOP_NAME,
    )

    assert shop.status is CanonicalTruthResolutionStatus.UNRESOLVED
    assert shop.resolved_value is None
    assert shop.supporting_members == ()
    assert tuple(option.value for option in shop.options) == ("Shop A", "Shop B")
    assert shop.decision is leave


def test_duplicate_non_conflict_and_malformed_decisions_fail_closed():
    exact_profile = profile_for(
        (("same", None, "A", None, None), ("same", None, "B", None, None))
    )
    select = decision(
        CanonicalTruthField.BRAND,
        CanonicalTruthDecisionAction.SELECT_SOURCE,
        selected_member=exact_profile.members[0],
    )
    leave = decision(
        CanonicalTruthField.BRAND,
        CanonicalTruthDecisionAction.LEAVE_UNRESOLVED,
    )
    invalid_inputs = (
        (select, leave),
        (
            decision(
                CanonicalTruthField.TITLE,
                CanonicalTruthDecisionAction.LEAVE_UNRESOLVED,
            ),
        ),
        (object(),),
        (
            CanonicalTruthDecision(
                field="BRAND",
                action=CanonicalTruthDecisionAction.LEAVE_UNRESOLVED,
                actor="reviewer",
                decided_at=DECIDED_AT,
                selected_member=None,
            ),
        ),
        (
            CanonicalTruthDecision(
                field=CanonicalTruthField.BRAND,
                action="SELECT_SOURCE",
                actor="reviewer",
                decided_at=DECIDED_AT,
                selected_member=exact_profile.members[0],
            ),
        ),
    )

    for supplied in invalid_inputs:
        with pytest.raises(CanonicalTruthError):
            reconcile_canonical_variant_truth(exact_profile, decisions=supplied)


def test_actor_timestamp_action_and_member_validation_fail_closed():
    exact_profile = profile_for(
        ((None, None, "A", None, None), (None, None, "B", None, None))
    )
    foreign = member("foreign")
    invalid = (
        decision(
            CanonicalTruthField.BRAND,
            CanonicalTruthDecisionAction.SELECT_SOURCE,
            selected_member=None,
        ),
        decision(
            CanonicalTruthField.BRAND,
            CanonicalTruthDecisionAction.SELECT_SOURCE,
            selected_member=foreign,
        ),
        decision(
            CanonicalTruthField.BRAND,
            CanonicalTruthDecisionAction.LEAVE_UNRESOLVED,
            selected_member=exact_profile.members[0],
        ),
        decision(
            CanonicalTruthField.BRAND,
            CanonicalTruthDecisionAction.SELECT_SOURCE,
            selected_member=exact_profile.members[0],
            actor=" \t\n ",
        ),
        decision(
            CanonicalTruthField.BRAND,
            CanonicalTruthDecisionAction.SELECT_SOURCE,
            selected_member=exact_profile.members[0],
            decided_at=datetime(2026, 9, 8, 9, 30),
        ),
    )

    for supplied in invalid:
        with pytest.raises(CanonicalTruthError):
            reconcile_canonical_variant_truth(exact_profile, decisions=(supplied,))


def test_none_valued_selected_member_is_rejected_even_when_member_is_canonical():
    exact_profile = profile_for(
        (
            (None, None, "A", None, None),
            (None, None, "B", None, None),
            (None, None, None, None, None),
        )
    )
    invalid = decision(
        CanonicalTruthField.BRAND,
        CanonicalTruthDecisionAction.SELECT_SOURCE,
        selected_member=exact_profile.members[2],
    )

    with pytest.raises(CanonicalTruthError):
        reconcile_canonical_variant_truth(exact_profile, decisions=(invalid,))


def test_reconciliation_is_deterministic_pure_and_does_not_mutate_inputs():
    first = profile_for(
        (
            ("A", "S", "B", "M1", "D"),
            ("A", "S", "C", "M2", "D"),
        )
    )
    reconstructed = profile_for(
        (
            ("A", "S", "B", "M1", "D"),
            ("A", "S", "C", "M2", "D"),
        )
    )
    first_decisions = (
        decision(
            CanonicalTruthField.BRAND,
            CanonicalTruthDecisionAction.SELECT_SOURCE,
            selected_member=first.members[1],
        ),
        decision(
            CanonicalTruthField.MODEL_SKU,
            CanonicalTruthDecisionAction.LEAVE_UNRESOLVED,
        ),
    )
    reconstructed_decisions = (
        decision(
            CanonicalTruthField.BRAND,
            CanonicalTruthDecisionAction.SELECT_SOURCE,
            selected_member=reconstructed.members[1],
        ),
        decision(
            CanonicalTruthField.MODEL_SKU,
            CanonicalTruthDecisionAction.LEAVE_UNRESOLVED,
        ),
    )
    before = (first, first_decisions)

    with (
        patch("builtins.open") as filesystem_open,
        patch("sqlite3.connect") as sqlite_connect,
        patch("urllib.request.urlopen") as network,
        patch("subprocess.run") as subprocess_run,
        patch("time.time") as clock,
        patch("random.random") as random_value,
        patch("uuid.uuid4") as uuid_value,
        patch("os.getenv") as environment,
    ):
        first_truth = reconcile_canonical_variant_truth(
            first, decisions=first_decisions
        )
        repeated = reconcile_canonical_variant_truth(first, decisions=first_decisions)
        rebuilt = reconcile_canonical_variant_truth(
            reconstructed, decisions=reconstructed_decisions
        )

    assert first == reconstructed and first is not reconstructed
    assert first_truth == repeated == rebuilt
    assert (first, first_decisions) == before
    for mocked in (
        filesystem_open,
        sqlite_connect,
        network,
        subprocess_run,
        clock,
        random_value,
        uuid_value,
        environment,
    ):
        mocked.assert_not_called()


def test_requires_exact_profile_and_iterable_exact_decisions():
    exact_profile = profile_for(((None, None, None, None, None),))

    for invalid_profile in (None, object(), "profile"):
        with pytest.raises(CanonicalTruthError):
            reconcile_canonical_variant_truth(invalid_profile)
    with pytest.raises(CanonicalTruthError):
        reconcile_canonical_variant_truth(exact_profile, decisions=None)
