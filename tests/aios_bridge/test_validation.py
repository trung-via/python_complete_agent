from dataclasses import FrozenInstanceError

import pytest

from src.aios_bridge.continuity.errors import ContinuityStateValidationError
from src.aios_bridge.validation import (
    CONTROL_PLANE_STRICT_COMPAT_PLAN,
    ExecutorAdHocT2Observability,
    ValidationEvidence,
    ValidationOwner,
    ValidationPlan,
    ValidationProfile,
    ValidationTier,
    certification_commands_for_plan,
    classify_validation_command,
    executor_commands_for_plan,
    require_certification_for_publication,
    require_review_first_candidate_publication,
    review_first_candidate_test_command,
    validation_owner,
    validation_plan_for_task,
)


LEAN_TASK = (
    'ROADMAP_BINDING_JSON: {"roadmap_id":"AIOS-BRIDGE-LEAN-EXECUTION",'
    '"roadmap_version":"1.1","milestone":"P0"}\n'
)


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


@pytest.mark.parametrize("executor_id", ("antigravity", "codex", "claude-code"))
def test_evidence_contract_is_provider_neutral(executor_id):
    item = evidence(executor_id=executor_id)
    assert item.to_dict()["executor_id"] == executor_id
    assert item.validation_duplication_detected is False


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
