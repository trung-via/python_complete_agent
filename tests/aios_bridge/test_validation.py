from dataclasses import FrozenInstanceError

import pytest

from src.aios_bridge.continuity.errors import ContinuityStateValidationError
from src.aios_bridge.validation import (
    CONTROL_PLANE_STRICT_COMPAT_PLAN,
    ValidationEvidence,
    ValidationOwner,
    ValidationPlan,
    ValidationProfile,
    ValidationTier,
    classify_validation_command,
    executor_commands_for_plan,
    require_certification_for_publication,
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


@pytest.mark.parametrize("executor_id", ("antigravity", "codex", "claude-code"))
def test_evidence_contract_is_provider_neutral(executor_id):
    item = evidence(executor_id=executor_id)
    assert item.to_dict()["executor_id"] == executor_id
    assert item.validation_duplication_detected is False


def test_validation_count_and_duration_telemetry_is_bounded_and_machine_readable():
    item = evidence()
    payload = item.to_dict()
    assert payload["full_suite_execution_count"] == 1
    assert payload["expected_full_suite_execution_count"] == 1
    assert payload["targeted_test_execution_count"] == 2
    assert payload["full_suite_duration_seconds"] == 3.25
    assert payload["targeted_test_duration_seconds"] == 0.5
    assert payload["validation_duplication_detected"] is False


def test_duplication_is_detected_and_cannot_manufacture_publication_pass():
    item = evidence(full_suite_execution_count=2)
    assert item.validation_duplication_detected is True
    with pytest.raises(ContinuityStateValidationError, match="VALIDATION_DUPLICATION_DETECTED"):
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
        full_suite_duration_seconds=None,
        targeted_test_duration_seconds=None,
    ).to_dict()
    assert payload["full_suite_duration_seconds"] is None
    assert payload["targeted_test_duration_seconds"] is None
    assert not any("token" in key or "quota" in key for key in payload)
