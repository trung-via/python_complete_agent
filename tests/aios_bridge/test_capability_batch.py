from dataclasses import FrozenInstanceError, replace

import pytest

from src.aios_bridge.capability_batch import (
    CapabilityBatchContractError,
    CapabilityBatchManifest,
    CapabilityBatchStatus,
    TaskMembershipBinding,
    require_current_task_authority,
    require_valid_membership_revision,
    transition_batch_status,
)


BASE = "1" * 40
HEAD = "2" * 40
ROADMAP_FP = "a" * 64
SCOPE_A = "b" * 64
SCOPE_B = "c" * 64


def member(
    task_id="TASK-101",
    base=BASE,
    branch="ai/task-101",
    scope=SCOPE_A,
    position=0,
    version=1,
):
    return TaskMembershipBinding(
        task_id=task_id,
        task_artifact_blob_sha=("3" if position == 0 else "4") * 40,
        bound_lane_base_sha=base,
        expected_task_branch=branch,
        task_scope_fingerprint=scope,
        membership_position=position,
        membership_version=version,
    )


def manifest(**overrides):
    values = {
        "schema_version": "1",
        "batch_id": "python-agent-batch-1",
        "roadmap_id": "AIOS-BRIDGE-LEAN-EXECUTION",
        "roadmap_version": "1.2",
        "roadmap_fingerprint": ROADMAP_FP,
        "milestone": "P1",
        "capability_id": "P1_UNIFIED_VALIDATION_CAPABILITY_BATCH",
        "base_main_sha": BASE,
        "integration_lane_ref": "ai/capability/python-agent-batch-1",
        "manifest_version": 1,
        "ordered_task_membership": (member(),),
        "status": CapabilityBatchStatus.OPEN,
    }
    values.update(overrides)
    return CapabilityBatchManifest(**values)


def test_manifest_schema_is_closed_immutable_and_round_trips():
    item = manifest()
    assert CapabilityBatchManifest.from_dict(item.to_dict()) == item
    assert len(item.fingerprint()) == 64
    with pytest.raises(FrozenInstanceError):
        item.status = CapabilityBatchStatus.MERGED
    payload = item.to_dict()
    payload["unexpected_authority"] = True
    with pytest.raises(CapabilityBatchContractError, match="exact bounded field set"):
        CapabilityBatchManifest.from_dict(payload)


@pytest.mark.parametrize(
    ("change", "value"),
    (
        ("base_main_sha", "A" * 40),
        ("roadmap_fingerprint", "a" * 63),
        ("manifest_version", True),
        ("manifest_version", 0),
        ("batch_id", "not canonical/with/slash"),
    ),
)
def test_manifest_rejects_malformed_or_coerced_scalars(change, value):
    with pytest.raises(CapabilityBatchContractError):
        manifest(**{change: value})


def test_manifest_fingerprint_is_deterministic_and_binds_all_authority_identity():
    original = manifest()
    assert original.fingerprint() == CapabilityBatchManifest.from_dict(
        original.to_dict()
    ).fingerprint()
    assert replace(original, status=CapabilityBatchStatus.INTEGRATING).fingerprint() != (
        original.fingerprint()
    )
    changed_scope = replace(
        original,
        ordered_task_membership=(replace(member(), task_scope_fingerprint=SCOPE_B),),
    )
    assert changed_scope.fingerprint() != original.fingerprint()


def test_membership_is_ordered_duplicate_free_and_member_version_is_independent():
    second = member(
        task_id="TASK-102",
        base=HEAD,
        branch="ai/task-102",
        scope=SCOPE_B,
        position=1,
    )
    item = manifest(ordered_task_membership=(member(), second))
    assert [entry.task_id for entry in item.ordered_task_membership] == [
        "TASK-101",
        "TASK-102",
    ]
    with pytest.raises(CapabilityBatchContractError, match="duplicate-free"):
        manifest(ordered_task_membership=(member(), replace(second, task_id="TASK-101")))
    with pytest.raises(CapabilityBatchContractError, match="positions"):
        manifest(ordered_task_membership=(member(), replace(second, membership_position=2)))
    revised_envelope = manifest(manifest_version=2)
    assert revised_envelope.ordered_task_membership[0].membership_version == 1


def test_membership_change_requires_new_version_and_fingerprint():
    previous = manifest()
    added_member = member(
        task_id="TASK-102",
        base=HEAD,
        branch="ai/task-102",
        scope=SCOPE_B,
        position=1,
        version=2,
    )
    candidate = manifest(
        manifest_version=2,
        ordered_task_membership=(member(), added_member),
    )
    assert require_valid_membership_revision(previous, candidate) is candidate
    assert candidate.fingerprint() != previous.fingerprint()
    assert candidate.ordered_task_membership[0].membership_version == 1
    assert candidate.ordered_task_membership[1].membership_version == 2

    same_version_member = replace(member(), task_scope_fingerprint=SCOPE_B)
    same_version = manifest(ordered_task_membership=(same_version_member,))
    with pytest.raises(CapabilityBatchContractError, match="next exact"):
        require_valid_membership_revision(previous, same_version)


def test_membership_must_be_nonempty_when_integration_begins():
    assert manifest(ordered_task_membership=()).status is CapabilityBatchStatus.OPEN
    with pytest.raises(CapabilityBatchContractError, match="non-empty"):
        manifest(
            ordered_task_membership=(), status=CapabilityBatchStatus.INTEGRATING
        )


def test_task_authority_remains_exact_and_independent_of_batch_membership():
    item = manifest()
    binding = require_current_task_authority(
        item,
        task_id="TASK-101",
        task_artifact_blob_sha="3" * 40,
        expected_task_branch="ai/task-101",
        task_scope_fingerprint=SCOPE_A,
        membership_position=0,
    )
    assert binding == item.ordered_task_membership[0]
    for override in (
        {"task_artifact_blob_sha": "9" * 40},
        {"expected_task_branch": "ai/wider-branch"},
        {"task_scope_fingerprint": SCOPE_B},
        {"task_id": "TASK-999"},
    ):
        values = {
            "task_id": "TASK-101",
            "task_artifact_blob_sha": "3" * 40,
            "expected_task_branch": "ai/task-101",
            "task_scope_fingerprint": SCOPE_A,
            "membership_position": 0,
        }
        values.update(override)
        with pytest.raises(CapabilityBatchContractError, match="does not exactly match"):
            require_current_task_authority(item, **values)


def test_lifecycle_is_closed_and_task_095_authority_cannot_be_skipped_into():
    integrating = transition_batch_status(
        manifest(), CapabilityBatchStatus.INTEGRATING
    )
    ready = transition_batch_status(
        integrating, CapabilityBatchStatus.READY_FOR_CAPABILITY_CERTIFICATION
    )
    assert ready.status is CapabilityBatchStatus.READY_FOR_CAPABILITY_CERTIFICATION
    for source, target in (
        (manifest(), CapabilityBatchStatus.CERTIFIED),
        (integrating, CapabilityBatchStatus.MERGED),
        (ready, CapabilityBatchStatus.MERGED),
        (
            replace(manifest(), status=CapabilityBatchStatus.CERTIFICATION_FAILED),
            CapabilityBatchStatus.CERTIFIED,
        ),
    ):
        with pytest.raises(CapabilityBatchContractError, match="forbidden"):
            transition_batch_status(source, target)


def test_recovery_and_supersession_are_representable_without_certification_authority():
    recovery = transition_batch_status(
        manifest(), CapabilityBatchStatus.RECOVERY_REQUIRED
    )
    superseded = transition_batch_status(
        recovery, CapabilityBatchStatus.SUPERSEDED
    )
    assert superseded.status is CapabilityBatchStatus.SUPERSEDED
