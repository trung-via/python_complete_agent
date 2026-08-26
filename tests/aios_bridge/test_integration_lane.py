from dataclasses import FrozenInstanceError, replace

import pytest

from src.aios_bridge.capability_batch import (
    CapabilityBatchManifest,
    CapabilityBatchStatus,
    TaskMembershipBinding,
)
from src.aios_bridge.integration_lane import (
    CapabilityReadinessEvidence,
    ExecutorLeaseState,
    IntegrationLaneContractError,
    IntegrationLaneStatus,
    LaneIntegrationPreflightEvidence,
    LinearIntegrationLaneState,
    TaskLaneBinding,
    advance_lane,
    begin_lane_integration,
    initial_lane_state,
    mark_ready_for_capability_certification,
    rebind_lane_manifest,
    require_lane_integration_preflight,
)
from src.aios_bridge.review_pipeline import ImpactConfidence
from src.aios_bridge.continuity.errors import ContinuityStateValidationError


BASE = "1" * 40
REVIEWED = "2" * 40
ARTIFACT = "3" * 40
ROADMAP_FP = "a" * 64
SCOPE_FP = "b" * 64


def open_manifest():
    return CapabilityBatchManifest(
        schema_version="1",
        batch_id="batch-1",
        roadmap_id="AIOS-BRIDGE-LEAN-EXECUTION",
        roadmap_version="1.2",
        roadmap_fingerprint=ROADMAP_FP,
        milestone="P1",
        capability_id="P1_UNIFIED_VALIDATION_CAPABILITY_BATCH",
        base_main_sha=BASE,
        integration_lane_ref="ai/capability/batch-1",
        manifest_version=1,
        ordered_task_membership=(
            TaskMembershipBinding(
                task_id="TASK-201",
                task_artifact_blob_sha=ARTIFACT,
                bound_lane_base_sha=BASE,
                expected_task_branch="ai/task-201",
                task_scope_fingerprint=SCOPE_FP,
                membership_position=0,
                membership_version=1,
            ),
        ),
        status=CapabilityBatchStatus.OPEN,
    )


def integration_context():
    opened = open_manifest()
    lane = initial_lane_state(opened)
    manifest, lane = begin_lane_integration(opened, lane)
    binding = TaskLaneBinding.for_next_task(manifest, lane)
    return manifest, lane, binding


def preflight(**overrides):
    manifest, lane, binding = integration_context()
    values = {
        "manifest": manifest,
        "lane": lane,
        "task_binding": binding,
        "current_manifest_fingerprint": manifest.fingerprint(),
        "current_roadmap_id": manifest.roadmap_id,
        "current_roadmap_version": manifest.roadmap_version,
        "current_roadmap_fingerprint": manifest.roadmap_fingerprint,
        "semantic_acceptance_valid": True,
        "reviewed_task_head_sha": REVIEWED,
        "current_task_branch": "ai/task-201",
        "task_branch_head_sha": REVIEWED,
        "current_task_artifact_blob_sha": ARTIFACT,
        "candidate_aios_managed_t2_count": 0,
        "targeted_validation_passed": True,
        "targeted_validation_not_required": False,
        "policy_permits_validation_not_required": False,
        "impact_confidence": ImpactConfidence.KNOWN,
        "publication_trust_valid": True,
        "scope_valid": True,
        "current_task_scope_fingerprint": SCOPE_FP,
        "executor_lease_state": ExecutorLeaseState.NONE,
        "main_current_sha": BASE,
        "fast_forwardable": True,
    }
    values.update(overrides)
    return LaneIntegrationPreflightEvidence(**values)


def test_initial_lane_state_is_exact_immutable_and_machine_readable():
    manifest = open_manifest()
    lane = initial_lane_state(manifest)
    assert lane.base_main_sha == lane.current_lane_head_sha == BASE
    assert lane.integrated_task_ids == ()
    assert lane.status is IntegrationLaneStatus.OPEN
    assert LinearIntegrationLaneState.from_dict(lane.to_dict()) == lane
    with pytest.raises(FrozenInstanceError):
        lane.current_lane_head_sha = REVIEWED
    payload = lane.to_dict()
    payload["parallel_parents"] = []
    with pytest.raises(IntegrationLaneContractError, match="exact bounded field set"):
        LinearIntegrationLaneState.from_dict(payload)


def test_lane_advances_exactly_one_expected_task_to_exact_reviewed_head():
    evidence = preflight()
    assert LaneIntegrationPreflightEvidence.from_dict(evidence.to_dict()) == evidence
    assert TaskLaneBinding.from_dict(evidence.task_binding.to_dict()) == (
        evidence.task_binding
    )
    require_lane_integration_preflight(evidence)
    advanced = advance_lane(evidence)
    assert advanced.current_lane_head_sha == REVIEWED
    assert advanced.integrated_task_ids == ("TASK-201",)
    assert advanced.status is IntegrationLaneStatus.INTEGRATING
    assert advanced.creates_main_merge_authority is False
    assert advanced.creates_final_pass_authority is False


def test_semantic_acceptance_is_exact_boolean_and_fails_closed():
    with pytest.raises(IntegrationLaneContractError, match="semantic acceptance"):
        require_lane_integration_preflight(
            preflight(semantic_acceptance_valid=False)
        )
    for malformed in (None, "SEMANTICALLY_ACCEPTED_PENDING_INTEGRATION", 1):
        with pytest.raises(IntegrationLaneContractError, match="exact bool"):
            preflight(semantic_acceptance_valid=malformed)


def test_progressive_manifest_rebind_preserves_integrated_prefix_and_lane_head():
    first_evidence = preflight()
    advanced = advance_lane(first_evidence)
    previous = first_evidence.manifest
    second = TaskMembershipBinding(
        task_id="TASK-202",
        task_artifact_blob_sha="4" * 40,
        bound_lane_base_sha=REVIEWED,
        expected_task_branch="ai/task-202",
        task_scope_fingerprint="c" * 64,
        membership_position=1,
        membership_version=2,
    )
    candidate = replace(
        previous,
        manifest_version=2,
        ordered_task_membership=(*previous.ordered_task_membership, second),
    )
    rebound = rebind_lane_manifest(
        previous, candidate, advanced, main_current_sha=BASE
    )

    assert rebound.batch_manifest_fingerprint == candidate.fingerprint()
    assert rebound.current_lane_head_sha == advanced.current_lane_head_sha == REVIEWED
    assert rebound.integrated_task_ids == ("TASK-201",)
    assert candidate.ordered_task_membership[0].membership_version == 1
    assert TaskLaneBinding.for_next_task(candidate, rebound).task_id == "TASK-202"
    assert rebound.creates_final_pass_authority is False
    assert rebound.creates_main_merge_authority is False


def test_manifest_rebind_rejects_stale_mutated_or_misbound_revision():
    first_evidence = preflight()
    advanced = advance_lane(first_evidence)
    previous = first_evidence.manifest
    second = TaskMembershipBinding(
        task_id="TASK-202",
        task_artifact_blob_sha="4" * 40,
        bound_lane_base_sha=REVIEWED,
        expected_task_branch="ai/task-202",
        task_scope_fingerprint="c" * 64,
        membership_position=1,
        membership_version=2,
    )
    candidate = replace(
        previous,
        manifest_version=2,
        ordered_task_membership=(*previous.ordered_task_membership, second),
    )

    stale_lane = replace(advanced, batch_manifest_fingerprint="d" * 64)
    with pytest.raises(IntegrationLaneContractError, match="lane identity"):
        rebind_lane_manifest(previous, candidate, stale_lane, main_current_sha=BASE)

    mutated_prefix = replace(
        candidate,
        ordered_task_membership=(
            replace(previous.ordered_task_membership[0], task_scope_fingerprint="d" * 64),
            second,
        ),
    )
    with pytest.raises(IntegrationLaneContractError, match="integrated prefix"):
        rebind_lane_manifest(
            previous, mutated_prefix, advanced, main_current_sha=BASE
        )

    misbound = replace(
        candidate,
        ordered_task_membership=(
            previous.ordered_task_membership[0],
            replace(second, bound_lane_base_sha="5" * 40),
        ),
    )
    with pytest.raises(IntegrationLaneContractError, match="current lane head"):
        rebind_lane_manifest(previous, misbound, advanced, main_current_sha=BASE)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("current_manifest_fingerprint", "c" * 64, "manifest fingerprint"),
        ("reviewed_task_head_sha", "4" * 40, "reviewed task head"),
        ("current_task_branch", "ai/task-999", "task branch"),
        ("current_task_artifact_blob_sha", "9" * 40, "artifact blob"),
        ("candidate_aios_managed_t2_count", 1, "T2 count"),
        ("impact_confidence", ImpactConfidence.UNKNOWN, "must be KNOWN"),
        ("publication_trust_valid", False, "publication trust"),
        ("scope_valid", False, "task scope"),
        ("executor_lease_state", ExecutorLeaseState.ACTIVE, "lease"),
        ("executor_lease_state", ExecutorLeaseState.UNCERTAIN, "lease"),
        ("main_current_sha", "5" * 40, "main drifted"),
        ("fast_forwardable", False, "fast-forwardable"),
    ),
)
def test_integration_preflight_fails_closed_for_unknown_stale_or_unsafe_fact(
    field, value, message
):
    with pytest.raises(IntegrationLaneContractError, match=message):
        require_lane_integration_preflight(preflight(**{field: value}))


def test_stale_lane_base_and_wrong_membership_order_are_rejected():
    evidence = preflight()
    stale_binding = replace(evidence.task_binding, bound_lane_base_sha="6" * 40)
    with pytest.raises(IntegrationLaneContractError, match="expected membership item"):
        require_lane_integration_preflight(replace(evidence, task_binding=stale_binding))

    wrong_lane = replace(evidence.lane, integrated_task_ids=("TASK-999",))
    with pytest.raises(IntegrationLaneContractError, match="already integrated"):
        require_lane_integration_preflight(replace(evidence, lane=wrong_lane))


def test_validation_not_required_must_be_exactly_machine_policy_permitted():
    allowed = preflight(
        targeted_validation_passed=False,
        targeted_validation_not_required=True,
        policy_permits_validation_not_required=True,
    )
    require_lane_integration_preflight(allowed)
    for changes in (
        {
            "targeted_validation_passed": False,
            "targeted_validation_not_required": True,
            "policy_permits_validation_not_required": False,
        },
        {
            "targeted_validation_passed": True,
            "targeted_validation_not_required": True,
            "policy_permits_validation_not_required": True,
        },
    ):
        with pytest.raises(IntegrationLaneContractError, match="exactly PASSED"):
            require_lane_integration_preflight(preflight(**changes))


def test_all_tasks_integrated_reach_only_non_final_capability_readiness():
    evidence = preflight()
    advanced = advance_lane(evidence)
    ready_manifest, ready_lane = mark_ready_for_capability_certification(
        CapabilityReadinessEvidence(
            manifest=evidence.manifest,
            lane=advanced,
            current_manifest_fingerprint=evidence.manifest.fingerprint(),
            current_lane_head_sha=REVIEWED,
            main_current_sha=BASE,
            unresolved_recovery=False,
        )
    )
    assert ready_manifest.status is (
        CapabilityBatchStatus.READY_FOR_CAPABILITY_CERTIFICATION
    )
    assert ready_lane.status is IntegrationLaneStatus.READY_FOR_CAPABILITY_CERTIFICATION
    assert ready_lane.batch_manifest_fingerprint == ready_manifest.fingerprint()
    assert ready_lane.creates_main_merge_authority is False
    assert ready_lane.creates_final_pass_authority is False


def test_readiness_fails_closed_on_main_drift_head_drift_or_recovery():
    evidence = preflight()
    advanced = advance_lane(evidence)
    base = CapabilityReadinessEvidence(
        manifest=evidence.manifest,
        lane=advanced,
        current_manifest_fingerprint=evidence.manifest.fingerprint(),
        current_lane_head_sha=REVIEWED,
        main_current_sha=BASE,
        unresolved_recovery=False,
    )
    assert CapabilityReadinessEvidence.from_dict(base.to_dict()) == base
    for changes in (
        {"main_current_sha": "7" * 40},
        {"current_lane_head_sha": "8" * 40},
        {"unresolved_recovery": True},
    ):
        with pytest.raises(IntegrationLaneContractError):
            mark_ready_for_capability_certification(replace(base, **changes))


def test_product_fast_end_to_end_admission_remains_owned_by_task_095():
    from src.aios_bridge.validation import validation_plan_for_task

    task = (
        'ROADMAP_BINDING_JSON: {"roadmap_id":"AIOS-BRIDGE-LEAN-EXECUTION"}\n'
        "VALIDATION_PROFILE: PRODUCT_DELIVERY_FAST\n"
    )
    with pytest.raises(ContinuityStateValidationError, match="admission blocked"):
        validation_plan_for_task(task)
