from dataclasses import FrozenInstanceError

import pytest

from src.aios_bridge.continuity.errors import ContinuityStateValidationError
from src.aios_bridge.validation import (
    CONTROL_PLANE_STRICT_COMPAT_POLICY,
    CONTROL_PLANE_STRICT_COMPAT_PLAN,
    CONTROL_PLANE_STRICT_PLAN,
    ExecutorAdHocT2Observability,
    PRODUCT_DELIVERY_FAST_POLICY,
    ValidationEvidence,
    ValidationOwner,
    ValidationPlan,
    ValidationProfile,
    ValidationTier,
    certification_commands_for_plan,
    classify_validation_command,
    executor_commands_for_plan,
    product_delivery_fast_impact_is_eligible,
    require_certification_for_publication,
    require_review_first_candidate_publication,
    review_first_candidate_test_command,
    validation_owner,
    validation_plan_for_task,
    validation_policy_for_profile,
    validation_profile_for_task,
)
from src.aios_bridge.review_pipeline import ImpactConfidence


LEAN_TASK = (
    'ROADMAP_BINDING_JSON: {"roadmap_id":"AIOS-BRIDGE-LEAN-EXECUTION",'
    '"roadmap_version":"1.1","milestone":"P0"}\n'
)

STRICT_TASK = LEAN_TASK + "VALIDATION_PROFILE: CONTROL_PLANE_STRICT\n"
FAST_TASK = LEAN_TASK + "VALIDATION_PROFILE: PRODUCT_DELIVERY_FAST\n"


def evidence(**overrides):
    values = {
        "task_id": "TASK-083",
        "action": "RUN",
        "executor_id": "codex",
        "validation_profile": ValidationProfile.CONTROL_PLANE_STRICT_COMPAT,
        "full_suite_execution_count": 1,
        "expected_full_suite_execution_count": 1,
        "targeted_test_execution_count": 2,
        "full_suite_duration_seconds": 3.25,
        "targeted_test_duration_seconds": 0.5,
    }
    values.update(overrides)
    return ValidationEvidence(**values)


def test_validation_tier_and_owner_are_closed():
    assert tuple(item.value for item in ValidationTier) == (
        "T0_MICRO",
        "T1_TARGETED_IMPACT",
        "T2_FULL_CANONICAL",
        "T3_RELEASE",
    )
    assert tuple(item.value for item in ValidationOwner) == (
        "EXECUTOR",
        "CERTIFICATION_BOUNDARY",
        "RELEASE_BOUNDARY",
    )
    with pytest.raises(ValueError):
        ValidationTier("T4")
    with pytest.raises(ValueError):
        ValidationOwner("CODEX")


def test_validation_profile_vocabulary_is_closed_and_distinct():
    assert tuple(item.value for item in ValidationProfile) == (
        "CONTROL_PLANE_STRICT_COMPAT",
        "CONTROL_PLANE_STRICT",
        "PRODUCT_DELIVERY_FAST",
    )
    assert len(set(ValidationProfile)) == 3
    with pytest.raises(ValueError):
        ValidationProfile("EXECUTOR_SELECTED")


def test_canonical_tier_ownership_has_exactly_one_t2_owner():
    assert validation_owner(ValidationTier.T0_MICRO) is ValidationOwner.EXECUTOR
    assert validation_owner(ValidationTier.T1_TARGETED_IMPACT) is ValidationOwner.EXECUTOR
    assert validation_owner(ValidationTier.T2_FULL_CANONICAL) is ValidationOwner.CERTIFICATION_BOUNDARY
    assert validation_owner(ValidationTier.T3_RELEASE) is ValidationOwner.RELEASE_BOUNDARY
    assert CONTROL_PLANE_STRICT_COMPAT_PLAN.certification_test_tiers == (
        ValidationTier.T2_FULL_CANONICAL,
    )


def test_validation_plan_is_immutable_machine_readable_and_round_trips():
    plan = CONTROL_PLANE_STRICT_COMPAT_PLAN
    assert ValidationPlan.from_dict(plan.to_dict()) == plan
    assert plan.expected_full_suite_execution_count == 1
    assert plan.diff_check_required is True
    with pytest.raises(FrozenInstanceError):
        plan.diff_check_required = False


def test_strict_plan_preserves_safety_but_not_compat_identity():
    assert CONTROL_PLANE_STRICT_COMPAT_PLAN.profile_id is (
        ValidationProfile.CONTROL_PLANE_STRICT_COMPAT
    )
    assert CONTROL_PLANE_STRICT_PLAN.profile_id is ValidationProfile.CONTROL_PLANE_STRICT
    assert CONTROL_PLANE_STRICT_PLAN is not CONTROL_PLANE_STRICT_COMPAT_PLAN
    assert (
        CONTROL_PLANE_STRICT_PLAN.executor_test_tiers
        == CONTROL_PLANE_STRICT_COMPAT_PLAN.executor_test_tiers
    )
    assert (
        CONTROL_PLANE_STRICT_PLAN.certification_test_tiers
        == CONTROL_PLANE_STRICT_COMPAT_PLAN.certification_test_tiers
        == (ValidationTier.T2_FULL_CANONICAL,)
    )
    assert CONTROL_PLANE_STRICT_PLAN.expected_full_suite_execution_count == 1
    assert CONTROL_PLANE_STRICT_PLAN.diff_check_required is True
    assert ValidationPlan.from_dict(CONTROL_PLANE_STRICT_PLAN.to_dict()) == (
        CONTROL_PLANE_STRICT_PLAN
    )


def test_ambiguous_or_duplicate_ownership_fails_conservatively():
    with pytest.raises(ContinuityStateValidationError, match="exactly one"):
        ValidationPlan(
            profile_id=ValidationProfile.CONTROL_PLANE_STRICT_COMPAT,
            executor_test_tiers=(
                ValidationTier.T0_MICRO,
                ValidationTier.T1_TARGETED_IMPACT,
                ValidationTier.T2_FULL_CANONICAL,
            ),
            certification_test_tiers=(ValidationTier.T2_FULL_CANONICAL,),
            diff_check_required=True,
            expected_full_suite_execution_count=1,
        )


def test_lean_roadmap_uses_plan_while_unbound_legacy_task_stays_legacy():
    assert validation_plan_for_task(LEAN_TASK) is CONTROL_PLANE_STRICT_COMPAT_PLAN
    assert validation_plan_for_task("pytest tests/ -q\n") is None


def test_explicit_strict_profile_resolves_without_rewriting_historical_tasks():
    assert validation_profile_for_task(LEAN_TASK) is (
        ValidationProfile.CONTROL_PLANE_STRICT_COMPAT
    )
    assert validation_profile_for_task(STRICT_TASK) is ValidationProfile.CONTROL_PLANE_STRICT
    assert validation_plan_for_task(STRICT_TASK) is CONTROL_PLANE_STRICT_PLAN
    assert validation_plan_for_task(LEAN_TASK) is CONTROL_PLANE_STRICT_COMPAT_PLAN


@pytest.mark.parametrize(
    ("marker", "message"),
    (
        ("VALIDATION_PROFILE: UNKNOWN\n", "Unknown VALIDATION_PROFILE"),
        ("VALIDATION_PROFILE:\n", "must not be empty"),
        ("VALIDATION_PROFILE CONTROL_PLANE_STRICT\n", "Malformed"),
        ("VALIDATION_PROFILE : CONTROL_PLANE_STRICT\n", "Malformed"),
        (
            "VALIDATION_PROFILE: CONTROL_PLANE_STRICT\n"
            "VALIDATION_PROFILE: CONTROL_PLANE_STRICT\n",
            "at most one",
        ),
    ),
)
def test_profile_marker_malformed_unknown_or_duplicate_fails_closed(marker, message):
    with pytest.raises(ContinuityStateValidationError, match=message):
        validation_plan_for_task(LEAN_TASK + marker)


def test_fenced_profile_marker_is_non_authoritative():
    task = LEAN_TASK + """````markdown
VALIDATION_PROFILE: PRODUCT_DELIVERY_FAST
```text
VALIDATION_PROFILE: CONTROL_PLANE_STRICT
```
````
"""
    assert validation_profile_for_task(task) is (
        ValidationProfile.CONTROL_PLANE_STRICT_COMPAT
    )
    assert validation_plan_for_task(task) is CONTROL_PLANE_STRICT_COMPAT_PLAN


def test_fast_profile_policy_is_closed_machine_readable_and_not_executable():
    assert validation_profile_for_task(FAST_TASK) is ValidationProfile.PRODUCT_DELIVERY_FAST
    assert validation_policy_for_profile(ValidationProfile.PRODUCT_DELIVERY_FAST) is (
        PRODUCT_DELIVERY_FAST_POLICY
    )
    policy = PRODUCT_DELIVERY_FAST_POLICY.to_dict()
    assert policy == {
        "capability_batch_authority_required": True,
        "capability_level_final_t2_required": True,
        "diff_check_required": True,
        "direct_task_main_merge_allowed": False,
        "executable_without_capability_authority": False,
        "integration_lane_authority_required": True,
        "known_impact_required": True,
        "profile_id": "PRODUCT_DELIVERY_FAST",
        "task_level_final_t2": False,
        "task_level_review_first_semantic_review_required": True,
        "task_level_t0_t1_required": True,
    }
    with pytest.raises(
        ContinuityStateValidationError,
        match="missing capability-batch/integration-lane authority",
    ):
        validation_plan_for_task(FAST_TASK)
    with pytest.raises(
        ContinuityStateValidationError,
        match="capability-batch/integration-lane authority",
    ):
        ValidationPlan(
            profile_id=ValidationProfile.PRODUCT_DELIVERY_FAST,
            executor_test_tiers=(
                ValidationTier.T0_MICRO,
                ValidationTier.T1_TARGETED_IMPACT,
            ),
            certification_test_tiers=(ValidationTier.T2_FULL_CANONICAL,),
            diff_check_required=True,
            expected_full_suite_execution_count=1,
        )


def test_fast_profile_requires_existing_known_impact_confidence():
    assert product_delivery_fast_impact_is_eligible(ImpactConfidence.KNOWN) is True
    assert product_delivery_fast_impact_is_eligible(ImpactConfidence.UNKNOWN) is False
    assert product_delivery_fast_impact_is_eligible("ESCAPED") is False
    assert product_delivery_fast_impact_is_eligible("UNPROVEN") is False
    assert PRODUCT_DELIVERY_FAST_POLICY.direct_task_main_merge_allowed is False
    assert PRODUCT_DELIVERY_FAST_POLICY.known_impact_required is True


def test_compat_policy_identity_and_behavior_remain_frozen():
    assert validation_policy_for_profile(
        ValidationProfile.CONTROL_PLANE_STRICT_COMPAT
    ) is CONTROL_PLANE_STRICT_COMPAT_POLICY
    assert CONTROL_PLANE_STRICT_COMPAT_POLICY.profile_id is (
        ValidationProfile.CONTROL_PLANE_STRICT_COMPAT
    )
    assert CONTROL_PLANE_STRICT_COMPAT_POLICY.task_level_final_t2 is True
    assert CONTROL_PLANE_STRICT_COMPAT_POLICY.capability_level_final_t2_required is False


@pytest.mark.parametrize(
    "command",
    (
        "pytest tests/ -q",
        "python -m pytest tests -q",
        r".\venv\Scripts\python.exe -m pytest tests/ -q",
    ),
)
def test_full_canonical_command_classification_is_provider_neutral(command):
    assert classify_validation_command(command) is ValidationTier.T2_FULL_CANONICAL


def test_legacy_full_suite_request_is_removed_from_executor_not_certification():
    commands = (
        "pytest tests/aios_bridge/test_validation.py -q",
        "pytest tests/ -q",
    )
    assert executor_commands_for_plan(commands, CONTROL_PLANE_STRICT_COMPAT_PLAN) == (
        commands[0],
    )
    assert CONTROL_PLANE_STRICT_COMPAT_PLAN.certification_test_tiers == (
        ValidationTier.T2_FULL_CANONICAL,
    )


def test_certification_schedules_exactly_one_aios_managed_t2():
    command = "pytest tests/ -q"
    assert certification_commands_for_plan(
        (command,), CONTROL_PLANE_STRICT_COMPAT_PLAN
    ) == (command,)
    with pytest.raises(
        ContinuityStateValidationError,
        match="AIOS_MANAGED_T2_DUPLICATION_DETECTED",
    ):
        certification_commands_for_plan(
            (command, command), CONTROL_PLANE_STRICT_COMPAT_PLAN
        )


def test_explicit_strict_schedules_one_final_t2_and_zero_candidate_t2():
    command = "pytest tests/ -q"
    assert certification_commands_for_plan((command,), CONTROL_PLANE_STRICT_PLAN) == (
        command,
    )
    assert review_first_candidate_test_command(command, CONTROL_PLANE_STRICT_PLAN) == (
        None,
        True,
    )
    candidate = evidence(
        validation_profile=ValidationProfile.CONTROL_PLANE_STRICT,
        full_suite_execution_count=0,
        full_suite_duration_seconds=None,
    )
    require_review_first_candidate_publication(CONTROL_PLANE_STRICT_PLAN, candidate)
    final = evidence(validation_profile=ValidationProfile.CONTROL_PLANE_STRICT)
    require_certification_for_publication(
        CONTROL_PLANE_STRICT_PLAN,
        final,
        full_suite_succeeded=True,
    )


@pytest.mark.parametrize("executor_id", ("antigravity", "codex", "claude-code"))
def test_evidence_contract_is_provider_neutral(executor_id):
    item = evidence(executor_id=executor_id)
    assert item.to_dict()["executor_id"] == executor_id
    assert item.validation_duplication_detected is False


@pytest.mark.parametrize("executor_id", ("antigravity", "codex"))
def test_explicit_strict_policy_is_identical_across_current_executors(executor_id):
    item = evidence(
        executor_id=executor_id,
        validation_profile=ValidationProfile.CONTROL_PLANE_STRICT,
    )
    require_certification_for_publication(
        CONTROL_PLANE_STRICT_PLAN,
        item,
        full_suite_succeeded=True,
    )
    assert item.to_dict()["validation_profile"] == "CONTROL_PLANE_STRICT"


def test_validation_count_and_duration_telemetry_is_bounded_and_machine_readable():
    item = evidence()
    payload = item.to_dict()
    assert payload["aios_managed_t2_execution_count"] == 1
    assert payload["expected_aios_managed_t2_execution_count"] == 1
    assert payload["aios_managed_t2_duplication_detected"] is False
    assert payload["targeted_test_execution_count"] == 2
    assert payload["full_suite_duration_seconds"] == 3.25
    assert payload["targeted_test_duration_seconds"] == 0.5
    assert payload["executor_ad_hoc_t2_observability"] == "UNAVAILABLE"
    assert payload["executor_ad_hoc_t2_execution_count"] == "UNKNOWN"
    assert payload["global_t2_execution_count"] == "UNKNOWN"
    assert "full_suite_execution_count" not in payload
    assert "expected_full_suite_execution_count" not in payload


def test_duplication_is_detected_and_cannot_manufacture_publication_pass():
    item = evidence(full_suite_execution_count=2)
    assert item.validation_duplication_detected is True
    with pytest.raises(
        ContinuityStateValidationError,
        match="AIOS_MANAGED_T2_DUPLICATION_DETECTED",
    ):
        require_certification_for_publication(
            CONTROL_PLANE_STRICT_COMPAT_PLAN,
            item,
            full_suite_succeeded=True,
        )


def test_failed_or_missing_t2_cannot_publish():
    with pytest.raises(ContinuityStateValidationError, match="failed T2"):
        require_certification_for_publication(
            CONTROL_PLANE_STRICT_COMPAT_PLAN,
            evidence(),
            full_suite_succeeded=False,
        )
    with pytest.raises(ContinuityStateValidationError, match="not executed exactly once"):
        require_certification_for_publication(
            CONTROL_PLANE_STRICT_COMPAT_PLAN,
            evidence(full_suite_execution_count=0),
            full_suite_succeeded=True,
        )


def test_unknown_duration_stays_unknown_without_quota_inference():
    payload = evidence(
        targeted_test_execution_count=None,
        full_suite_duration_seconds=None,
        targeted_test_duration_seconds=None,
    ).to_dict()
    assert payload["targeted_test_execution_count"] == "UNKNOWN"
    assert payload["full_suite_duration_seconds"] == "UNKNOWN"
    assert payload["targeted_test_duration_seconds"] == "UNKNOWN"
    assert not any("token" in key or "quota" in key for key in payload)


def test_unavailable_ad_hoc_observability_cannot_fabricate_counts():
    item = evidence(
        executor_ad_hoc_t2_observability=ExecutorAdHocT2Observability.UNAVAILABLE,
        executor_ad_hoc_t2_execution_count=None,
    )
    payload = item.to_dict()
    assert payload["executor_ad_hoc_t2_execution_count"] == "UNKNOWN"
    assert payload["global_t2_execution_count"] == "UNKNOWN"
    with pytest.raises(ContinuityStateValidationError, match="must remain UNKNOWN"):
        evidence(executor_ad_hoc_t2_execution_count=0)


def test_observed_executor_ad_hoc_t2_is_a_policy_violation():
    item = evidence(
        executor_ad_hoc_t2_observability=ExecutorAdHocT2Observability.OBSERVED,
        executor_ad_hoc_t2_execution_count=1,
    )
    assert item.to_dict()["global_t2_execution_count"] == 2
    with pytest.raises(ContinuityStateValidationError, match="VALIDATION_POLICY_VIOLATION"):
        require_certification_for_publication(
            CONTROL_PLANE_STRICT_COMPAT_PLAN,
            item,
            full_suite_succeeded=True,
        )


def test_review_first_candidate_publication_requires_zero_aios_managed_t2():
    candidate = evidence(
        full_suite_execution_count=0,
        full_suite_duration_seconds=None,
    )
    require_review_first_candidate_publication(
        CONTROL_PLANE_STRICT_COMPAT_PLAN,
        candidate,
    )
    with pytest.raises(ContinuityStateValidationError, match="execute zero"):
        require_review_first_candidate_publication(
            CONTROL_PLANE_STRICT_COMPAT_PLAN,
            evidence(),
        )


def test_review_first_candidate_rejects_observed_early_ad_hoc_t2():
    with pytest.raises(ContinuityStateValidationError, match="early ad-hoc T2"):
        require_review_first_candidate_publication(
            CONTROL_PLANE_STRICT_COMPAT_PLAN,
            evidence(
                full_suite_execution_count=0,
                full_suite_duration_seconds=None,
                executor_ad_hoc_t2_observability=ExecutorAdHocT2Observability.OBSERVED,
                executor_ad_hoc_t2_execution_count=1,
            ),
        )


def test_review_first_candidate_defers_full_t2_but_retains_targeted_command():
    full = "python -m pytest tests/ -q"
    targeted = "python -m pytest tests/aios_bridge/test_validation.py -q"
    assert review_first_candidate_test_command(
        full, CONTROL_PLANE_STRICT_COMPAT_PLAN
    ) == (None, True)
    assert review_first_candidate_test_command(
        targeted, CONTROL_PLANE_STRICT_COMPAT_PLAN
    ) == (targeted, False)
    compound = f"{targeted} && {full}"
    assert review_first_candidate_test_command(
        compound, CONTROL_PLANE_STRICT_COMPAT_PLAN
    ) == (None, True)
