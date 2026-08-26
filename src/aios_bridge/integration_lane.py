"""Pure P1 linear integration-lane contracts.

Git ancestry, publication trust, review, scope, and lease facts are supplied as
bounded machine evidence.  This module never runs Git and never grants task
PASS, capability certification, or main-merge authority.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import re
from typing import Any

from src.aios_bridge.capability_batch import (
    CapabilityBatchManifest,
    CapabilityBatchStatus,
    TaskMembershipBinding,
    require_valid_membership_revision,
    transition_batch_status,
)
from src.aios_bridge.continuity.errors import ContinuityStateValidationError
from src.aios_bridge.review_pipeline import ImpactConfidence


_TASK_ID_RE = re.compile(r"\ATASK-\d+\Z")
_SHA_RE = re.compile(r"\A[0-9a-f]{40}\Z")
_FINGERPRINT_RE = re.compile(r"\A[0-9a-f]{64}\Z")
_BATCH_ID_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
_REF_RE = re.compile(r"\A(?!/)(?!.*(?:\.\.|//))[A-Za-z0-9][A-Za-z0-9._/-]{0,254}\Z")
_MAX_MEMBERSHIP = 10_000


class IntegrationLaneContractError(ContinuityStateValidationError):
    """A malformed lane contract or failed deterministic gate."""


def _error(message: str) -> IntegrationLaneContractError:
    return IntegrationLaneContractError(message)


def _require_sha(value: object, name: str) -> str:
    if type(value) is not str or _SHA_RE.fullmatch(value) is None:
        raise _error(f"{name} must be an exact lowercase 40-hex SHA")
    return value


def _require_fingerprint(value: object, name: str) -> str:
    if type(value) is not str or _FINGERPRINT_RE.fullmatch(value) is None:
        raise _error(f"{name} must be an exact lowercase 64-hex fingerprint")
    return value


class IntegrationLaneStatus(str, Enum):
    OPEN = "OPEN"
    INTEGRATING = "INTEGRATING"
    READY_FOR_CAPABILITY_CERTIFICATION = "READY_FOR_CAPABILITY_CERTIFICATION"
    SUPERSEDED = "SUPERSEDED"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"


class ExecutorLeaseState(str, Enum):
    NONE = "NONE"
    ACTIVE = "ACTIVE"
    UNCERTAIN = "UNCERTAIN"


@dataclass(frozen=True, slots=True)
class LinearIntegrationLaneState:
    batch_id: str
    batch_manifest_fingerprint: str
    base_main_sha: str
    integration_lane_ref: str
    current_lane_head_sha: str
    integrated_task_ids: tuple[str, ...]
    status: IntegrationLaneStatus

    def __post_init__(self) -> None:
        if type(self.batch_id) is not str or _BATCH_ID_RE.fullmatch(self.batch_id) is None:
            raise _error("batch_id must be canonical and bounded")
        _require_fingerprint(
            self.batch_manifest_fingerprint, "batch_manifest_fingerprint"
        )
        _require_sha(self.base_main_sha, "base_main_sha")
        _require_sha(self.current_lane_head_sha, "current_lane_head_sha")
        if (
            type(self.integration_lane_ref) is not str
            or _REF_RE.fullmatch(self.integration_lane_ref) is None
        ):
            raise _error("integration_lane_ref must be a canonical bounded ref")
        if (
            type(self.integrated_task_ids) is not tuple
            or len(self.integrated_task_ids) > _MAX_MEMBERSHIP
            or any(
                type(task_id) is not str or _TASK_ID_RE.fullmatch(task_id) is None
                for task_id in self.integrated_task_ids
            )
        ):
            raise _error("integrated_task_ids must be an exact tuple of task IDs")
        if len(set(self.integrated_task_ids)) != len(self.integrated_task_ids):
            raise _error("integrated_task_ids must be duplicate-free")
        if type(self.status) is not IntegrationLaneStatus:
            raise _error("status must be an exact IntegrationLaneStatus")
        if self.status is IntegrationLaneStatus.OPEN:
            if self.current_lane_head_sha != self.base_main_sha:
                raise _error("initial lane head must equal exact base main SHA")
            if self.integrated_task_ids:
                raise _error("initial lane must contain zero integrated tasks")

    @property
    def creates_main_merge_authority(self) -> bool:
        return False

    @property
    def creates_final_pass_authority(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "base_main_sha": self.base_main_sha,
            "batch_id": self.batch_id,
            "batch_manifest_fingerprint": self.batch_manifest_fingerprint,
            "current_lane_head_sha": self.current_lane_head_sha,
            "integrated_task_ids": list(self.integrated_task_ids),
            "integration_lane_ref": self.integration_lane_ref,
            "status": self.status.value,
        }

    @classmethod
    def from_dict(cls, data: object) -> "LinearIntegrationLaneState":
        fields = {
            "base_main_sha",
            "batch_id",
            "batch_manifest_fingerprint",
            "current_lane_head_sha",
            "integrated_task_ids",
            "integration_lane_ref",
            "status",
        }
        if type(data) is not dict or set(data) != fields:
            raise _error("LinearIntegrationLaneState must contain the exact bounded field set")
        integrated = data["integrated_task_ids"]
        if type(integrated) is not list:
            raise _error("serialized integrated_task_ids must be an exact list")
        try:
            return cls(
                batch_id=data["batch_id"],
                batch_manifest_fingerprint=data["batch_manifest_fingerprint"],
                base_main_sha=data["base_main_sha"],
                integration_lane_ref=data["integration_lane_ref"],
                current_lane_head_sha=data["current_lane_head_sha"],
                integrated_task_ids=tuple(integrated),
                status=IntegrationLaneStatus(data["status"]),
            )
        except (TypeError, ValueError) as exc:
            raise _error(f"malformed LinearIntegrationLaneState: {exc}") from exc


@dataclass(frozen=True, slots=True)
class TaskLaneBinding:
    batch_id: str
    batch_manifest_fingerprint: str
    integration_lane_ref: str
    bound_lane_base_sha: str
    expected_task_branch: str
    task_id: str
    task_artifact_blob_sha: str
    task_scope_fingerprint: str
    membership_position: int
    membership_version: int

    def __post_init__(self) -> None:
        if type(self.batch_id) is not str or _BATCH_ID_RE.fullmatch(self.batch_id) is None:
            raise _error("batch_id must be canonical and bounded")
        _require_fingerprint(
            self.batch_manifest_fingerprint, "batch_manifest_fingerprint"
        )
        if (
            type(self.integration_lane_ref) is not str
            or _REF_RE.fullmatch(self.integration_lane_ref) is None
        ):
            raise _error("integration_lane_ref must be a canonical bounded ref")
        _require_sha(self.bound_lane_base_sha, "bound_lane_base_sha")
        if (
            type(self.expected_task_branch) is not str
            or _REF_RE.fullmatch(self.expected_task_branch) is None
        ):
            raise _error("expected_task_branch must be a canonical bounded ref")
        if type(self.task_id) is not str or _TASK_ID_RE.fullmatch(self.task_id) is None:
            raise _error("task_id must match exact TASK-<digits>")
        _require_sha(self.task_artifact_blob_sha, "task_artifact_blob_sha")
        _require_fingerprint(self.task_scope_fingerprint, "task_scope_fingerprint")
        if type(self.membership_position) is not int or self.membership_position < 0:
            raise _error("membership_position must be a non-negative exact int")
        if type(self.membership_version) is not int or self.membership_version < 1:
            raise _error("membership_version must be a positive exact int")

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "batch_manifest_fingerprint": self.batch_manifest_fingerprint,
            "bound_lane_base_sha": self.bound_lane_base_sha,
            "expected_task_branch": self.expected_task_branch,
            "integration_lane_ref": self.integration_lane_ref,
            "membership_position": self.membership_position,
            "membership_version": self.membership_version,
            "task_artifact_blob_sha": self.task_artifact_blob_sha,
            "task_id": self.task_id,
            "task_scope_fingerprint": self.task_scope_fingerprint,
        }

    @classmethod
    def from_dict(cls, data: object) -> "TaskLaneBinding":
        fields = {
            "batch_id",
            "batch_manifest_fingerprint",
            "bound_lane_base_sha",
            "expected_task_branch",
            "integration_lane_ref",
            "membership_position",
            "membership_version",
            "task_artifact_blob_sha",
            "task_id",
            "task_scope_fingerprint",
        }
        if type(data) is not dict or set(data) != fields:
            raise _error("TaskLaneBinding must contain the exact bounded field set")
        return cls(**data)

    @classmethod
    def for_next_task(
        cls,
        manifest: CapabilityBatchManifest,
        lane: LinearIntegrationLaneState,
    ) -> "TaskLaneBinding":
        _require_manifest_lane_identity(manifest, lane)
        position = len(lane.integrated_task_ids)
        if position >= len(manifest.ordered_task_membership):
            raise _error("no next manifest task remains for lane binding")
        member = manifest.ordered_task_membership[position]
        if member.bound_lane_base_sha != lane.current_lane_head_sha:
            raise _error("next task binding is stale against current lane head")
        return cls._from_member(manifest, member)

    @classmethod
    def _from_member(
        cls,
        manifest: CapabilityBatchManifest,
        member: TaskMembershipBinding,
    ) -> "TaskLaneBinding":
        return cls(
            batch_id=manifest.batch_id,
            batch_manifest_fingerprint=manifest.fingerprint(),
            integration_lane_ref=manifest.integration_lane_ref,
            bound_lane_base_sha=member.bound_lane_base_sha,
            expected_task_branch=member.expected_task_branch,
            task_id=member.task_id,
            task_artifact_blob_sha=member.task_artifact_blob_sha,
            task_scope_fingerprint=member.task_scope_fingerprint,
            membership_position=member.membership_position,
            membership_version=member.membership_version,
        )


def initial_lane_state(manifest: CapabilityBatchManifest) -> LinearIntegrationLaneState:
    if type(manifest) is not CapabilityBatchManifest:
        raise _error("manifest must be an exact CapabilityBatchManifest")
    if manifest.status is not CapabilityBatchStatus.OPEN:
        raise _error("initial lane requires an OPEN batch manifest")
    return LinearIntegrationLaneState(
        batch_id=manifest.batch_id,
        batch_manifest_fingerprint=manifest.fingerprint(),
        base_main_sha=manifest.base_main_sha,
        integration_lane_ref=manifest.integration_lane_ref,
        current_lane_head_sha=manifest.base_main_sha,
        integrated_task_ids=(),
        status=IntegrationLaneStatus.OPEN,
    )


def begin_lane_integration(
    manifest: CapabilityBatchManifest,
    lane: LinearIntegrationLaneState,
) -> tuple[CapabilityBatchManifest, LinearIntegrationLaneState]:
    _require_manifest_lane_identity(manifest, lane)
    if lane.status is not IntegrationLaneStatus.OPEN:
        raise _error("only an OPEN lane may begin integration")
    integrating_manifest = transition_batch_status(
        manifest, CapabilityBatchStatus.INTEGRATING
    )
    return integrating_manifest, replace(
        lane,
        batch_manifest_fingerprint=integrating_manifest.fingerprint(),
        status=IntegrationLaneStatus.INTEGRATING,
    )


def _require_manifest_lane_identity(
    manifest: CapabilityBatchManifest,
    lane: LinearIntegrationLaneState,
) -> None:
    if type(manifest) is not CapabilityBatchManifest:
        raise _error("manifest must be an exact CapabilityBatchManifest")
    if type(lane) is not LinearIntegrationLaneState:
        raise _error("lane must be an exact LinearIntegrationLaneState")
    if (
        lane.batch_id != manifest.batch_id
        or lane.batch_manifest_fingerprint != manifest.fingerprint()
        or lane.base_main_sha != manifest.base_main_sha
        or lane.integration_lane_ref != manifest.integration_lane_ref
    ):
        raise _error("lane identity does not exactly match current batch manifest")


def rebind_lane_manifest(
    previous_manifest: CapabilityBatchManifest,
    candidate_manifest: CapabilityBatchManifest,
    lane: LinearIntegrationLaneState,
    *,
    main_current_sha: str,
) -> LinearIntegrationLaneState:
    """Rebind only manifest authority after a progressive membership revision."""
    if type(previous_manifest) is not CapabilityBatchManifest:
        raise _error("previous manifest must be an exact CapabilityBatchManifest")
    if type(candidate_manifest) is not CapabilityBatchManifest:
        raise _error("candidate manifest must be an exact CapabilityBatchManifest")
    if type(lane) is not LinearIntegrationLaneState:
        raise _error("lane must be an exact LinearIntegrationLaneState")
    _require_sha(main_current_sha, "main_current_sha")
    _require_manifest_lane_identity(previous_manifest, lane)
    if lane.status is not IntegrationLaneStatus.INTEGRATING:
        raise _error("manifest rebind requires an integrating lane")
    if main_current_sha != previous_manifest.base_main_sha:
        raise _error("main drifted from exact batch base main SHA")

    try:
        require_valid_membership_revision(previous_manifest, candidate_manifest)
    except ContinuityStateValidationError as exc:
        raise _error(f"invalid manifest revision: {exc}") from exc

    integrated_count = len(lane.integrated_task_ids)
    previous_prefix = previous_manifest.ordered_task_membership[:integrated_count]
    candidate_prefix = candidate_manifest.ordered_task_membership[:integrated_count]
    if tuple(item.task_id for item in previous_prefix) != lane.integrated_task_ids:
        raise _error("lane integrated task IDs do not match the previous manifest prefix")
    if len(previous_prefix) != integrated_count or candidate_prefix != previous_prefix:
        raise _error("candidate manifest must preserve the exact integrated prefix")
    if integrated_count < len(candidate_manifest.ordered_task_membership):
        next_member = candidate_manifest.ordered_task_membership[integrated_count]
        if next_member.bound_lane_base_sha != lane.current_lane_head_sha:
            raise _error("next manifest member must bind the exact current lane head")

    return replace(
        lane,
        batch_manifest_fingerprint=candidate_manifest.fingerprint(),
    )


@dataclass(frozen=True, slots=True)
class LaneIntegrationPreflightEvidence:
    manifest: CapabilityBatchManifest
    lane: LinearIntegrationLaneState
    task_binding: TaskLaneBinding
    current_manifest_fingerprint: str
    current_roadmap_id: str
    current_roadmap_version: str
    current_roadmap_fingerprint: str
    semantic_acceptance_valid: bool
    reviewed_task_head_sha: str
    current_task_branch: str
    task_branch_head_sha: str
    current_task_artifact_blob_sha: str
    candidate_aios_managed_t2_count: int
    targeted_validation_passed: bool
    targeted_validation_not_required: bool
    policy_permits_validation_not_required: bool
    impact_confidence: ImpactConfidence
    publication_trust_valid: bool
    scope_valid: bool
    current_task_scope_fingerprint: str
    executor_lease_state: ExecutorLeaseState
    main_current_sha: str
    fast_forwardable: bool

    def __post_init__(self) -> None:
        if type(self.manifest) is not CapabilityBatchManifest:
            raise _error("manifest evidence must be exact")
        if type(self.lane) is not LinearIntegrationLaneState:
            raise _error("lane evidence must be exact")
        if type(self.task_binding) is not TaskLaneBinding:
            raise _error("task_binding evidence must be exact")
        _require_fingerprint(
            self.current_manifest_fingerprint, "current_manifest_fingerprint"
        )
        for name in ("current_roadmap_id", "current_roadmap_version"):
            value = getattr(self, name)
            if type(value) is not str or not value or value != value.strip() or len(value) > 128:
                raise _error(f"{name} must be bounded exact non-empty text")
        if type(self.semantic_acceptance_valid) is not bool:
            raise _error("semantic_acceptance_valid must be an exact bool")
        _require_fingerprint(
            self.current_roadmap_fingerprint, "current_roadmap_fingerprint"
        )
        _require_sha(self.reviewed_task_head_sha, "reviewed_task_head_sha")
        if (
            type(self.current_task_branch) is not str
            or _REF_RE.fullmatch(self.current_task_branch) is None
        ):
            raise _error("current_task_branch must be a canonical bounded ref")
        _require_sha(self.task_branch_head_sha, "task_branch_head_sha")
        _require_sha(
            self.current_task_artifact_blob_sha, "current_task_artifact_blob_sha"
        )
        if type(self.candidate_aios_managed_t2_count) is not int or not (
            0 <= self.candidate_aios_managed_t2_count <= 1
        ):
            raise _error("candidate AIOS-managed T2 count must be exact 0 or 1")
        for name in (
            "targeted_validation_passed",
            "targeted_validation_not_required",
            "policy_permits_validation_not_required",
            "publication_trust_valid",
            "scope_valid",
            "fast_forwardable",
        ):
            if type(getattr(self, name)) is not bool:
                raise _error(f"{name} must be an exact bool")
        if type(self.impact_confidence) is not ImpactConfidence:
            raise _error("impact_confidence must be an exact ImpactConfidence")
        _require_fingerprint(
            self.current_task_scope_fingerprint, "current_task_scope_fingerprint"
        )
        if type(self.executor_lease_state) is not ExecutorLeaseState:
            raise _error("executor_lease_state must be an exact ExecutorLeaseState")
        _require_sha(self.main_current_sha, "main_current_sha")

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_aios_managed_t2_count": self.candidate_aios_managed_t2_count,
            "current_manifest_fingerprint": self.current_manifest_fingerprint,
            "current_roadmap_fingerprint": self.current_roadmap_fingerprint,
            "current_roadmap_id": self.current_roadmap_id,
            "current_roadmap_version": self.current_roadmap_version,
            "current_task_artifact_blob_sha": self.current_task_artifact_blob_sha,
            "current_task_branch": self.current_task_branch,
            "current_task_scope_fingerprint": self.current_task_scope_fingerprint,
            "executor_lease_state": self.executor_lease_state.value,
            "fast_forwardable": self.fast_forwardable,
            "impact_confidence": self.impact_confidence.value,
            "lane": self.lane.to_dict(),
            "main_current_sha": self.main_current_sha,
            "manifest": self.manifest.to_dict(),
            "policy_permits_validation_not_required": (
                self.policy_permits_validation_not_required
            ),
            "publication_trust_valid": self.publication_trust_valid,
            "semantic_acceptance_valid": self.semantic_acceptance_valid,
            "reviewed_task_head_sha": self.reviewed_task_head_sha,
            "scope_valid": self.scope_valid,
            "targeted_validation_not_required": self.targeted_validation_not_required,
            "targeted_validation_passed": self.targeted_validation_passed,
            "task_binding": self.task_binding.to_dict(),
            "task_branch_head_sha": self.task_branch_head_sha,
        }

    @classmethod
    def from_dict(cls, data: object) -> "LaneIntegrationPreflightEvidence":
        fields = {
            "candidate_aios_managed_t2_count",
            "current_manifest_fingerprint",
            "current_roadmap_fingerprint",
            "current_roadmap_id",
            "current_roadmap_version",
            "current_task_artifact_blob_sha",
            "current_task_branch",
            "current_task_scope_fingerprint",
            "executor_lease_state",
            "fast_forwardable",
            "impact_confidence",
            "lane",
            "main_current_sha",
            "manifest",
            "policy_permits_validation_not_required",
            "publication_trust_valid",
            "semantic_acceptance_valid",
            "reviewed_task_head_sha",
            "scope_valid",
            "targeted_validation_not_required",
            "targeted_validation_passed",
            "task_binding",
            "task_branch_head_sha",
        }
        if type(data) is not dict or set(data) != fields:
            raise _error(
                "LaneIntegrationPreflightEvidence must contain the exact bounded field set"
            )
        try:
            return cls(
                manifest=CapabilityBatchManifest.from_dict(data["manifest"]),
                lane=LinearIntegrationLaneState.from_dict(data["lane"]),
                task_binding=TaskLaneBinding.from_dict(data["task_binding"]),
                current_manifest_fingerprint=data["current_manifest_fingerprint"],
                current_roadmap_id=data["current_roadmap_id"],
                current_roadmap_version=data["current_roadmap_version"],
                current_roadmap_fingerprint=data["current_roadmap_fingerprint"],
                semantic_acceptance_valid=data["semantic_acceptance_valid"],
                reviewed_task_head_sha=data["reviewed_task_head_sha"],
                current_task_branch=data["current_task_branch"],
                task_branch_head_sha=data["task_branch_head_sha"],
                current_task_artifact_blob_sha=data["current_task_artifact_blob_sha"],
                candidate_aios_managed_t2_count=data[
                    "candidate_aios_managed_t2_count"
                ],
                targeted_validation_passed=data["targeted_validation_passed"],
                targeted_validation_not_required=data[
                    "targeted_validation_not_required"
                ],
                policy_permits_validation_not_required=data[
                    "policy_permits_validation_not_required"
                ],
                impact_confidence=ImpactConfidence(data["impact_confidence"]),
                publication_trust_valid=data["publication_trust_valid"],
                scope_valid=data["scope_valid"],
                current_task_scope_fingerprint=data[
                    "current_task_scope_fingerprint"
                ],
                executor_lease_state=ExecutorLeaseState(data["executor_lease_state"]),
                main_current_sha=data["main_current_sha"],
                fast_forwardable=data["fast_forwardable"],
            )
        except (TypeError, ValueError) as exc:
            raise _error(f"malformed LaneIntegrationPreflightEvidence: {exc}") from exc


def require_lane_integration_preflight(
    evidence: LaneIntegrationPreflightEvidence,
) -> None:
    """Fail closed unless every exact-head lane advancement fact is proven."""
    if type(evidence) is not LaneIntegrationPreflightEvidence:
        raise _error("lane integration preflight evidence must be exact")
    manifest = evidence.manifest
    lane = evidence.lane
    binding = evidence.task_binding
    _require_manifest_lane_identity(manifest, lane)
    if (
        manifest.status is not CapabilityBatchStatus.INTEGRATING
        or lane.status is not IntegrationLaneStatus.INTEGRATING
    ):
        raise _error("batch and lane status do not permit integration")
    if evidence.current_manifest_fingerprint != manifest.fingerprint():
        raise _error("current manifest fingerprint is stale")
    if (
        evidence.current_roadmap_id != manifest.roadmap_id
        or evidence.current_roadmap_version != manifest.roadmap_version
        or evidence.current_roadmap_fingerprint != manifest.roadmap_fingerprint
    ):
        raise _error("roadmap identity or fingerprint drifted")

    position = len(lane.integrated_task_ids)
    if position >= len(manifest.ordered_task_membership):
        raise _error("all manifest tasks are already integrated")
    expected = manifest.ordered_task_membership[position]
    expected_binding = TaskLaneBinding._from_member(manifest, expected)
    if binding != expected_binding or binding.membership_position != position:
        raise _error("current task is not the exact expected membership item")
    if tuple(item.task_id for item in manifest.ordered_task_membership[:position]) != (
        lane.integrated_task_ids
    ):
        raise _error("integrated task history does not match exact manifest order")
    if binding.bound_lane_base_sha != lane.current_lane_head_sha:
        raise _error("task bound lane base is stale")
    if evidence.current_task_branch != binding.expected_task_branch:
        raise _error("current task branch does not match exact task authority")
    if evidence.current_task_artifact_blob_sha != binding.task_artifact_blob_sha:
        raise _error("current task artifact blob does not match exact task authority")
    if not evidence.semantic_acceptance_valid:
        raise _error("semantic acceptance is false or unknown")
    if evidence.reviewed_task_head_sha != evidence.task_branch_head_sha:
        raise _error("reviewed task head does not match task branch head")
    if evidence.reviewed_task_head_sha == lane.current_lane_head_sha:
        raise _error("reviewed task head must advance the lane head")
    if evidence.candidate_aios_managed_t2_count != 0:
        raise _error("candidate-stage AIOS-managed T2 count must be zero")
    validation_pass = evidence.targeted_validation_passed
    permitted_not_required = (
        evidence.targeted_validation_not_required
        and evidence.policy_permits_validation_not_required
    )
    if validation_pass == permitted_not_required:
        raise _error("validation must be exactly PASSED or policy-permitted NOT_REQUIRED")
    if evidence.impact_confidence is not ImpactConfidence.KNOWN:
        raise _error("PRODUCT_DELIVERY_FAST impact confidence must be KNOWN")
    if not evidence.publication_trust_valid:
        raise _error("publication trust is invalid or unknown")
    if (
        not evidence.scope_valid
        or evidence.current_task_scope_fingerprint != binding.task_scope_fingerprint
    ):
        raise _error("task scope is invalid or does not match independent task authority")
    if evidence.executor_lease_state is not ExecutorLeaseState.NONE:
        raise _error("active or uncertain executor lease blocks lane integration")
    if evidence.main_current_sha != manifest.base_main_sha:
        raise _error("main drifted from exact batch base main SHA")
    if not evidence.fast_forwardable:
        raise _error("reviewed task head is not proven fast-forwardable")


def advance_lane(
    evidence: LaneIntegrationPreflightEvidence,
) -> LinearIntegrationLaneState:
    """Append exactly one reviewed task and advance to its exact head."""
    require_lane_integration_preflight(evidence)
    return replace(
        evidence.lane,
        current_lane_head_sha=evidence.reviewed_task_head_sha,
        integrated_task_ids=(
            *evidence.lane.integrated_task_ids,
            evidence.task_binding.task_id,
        ),
    )


@dataclass(frozen=True, slots=True)
class CapabilityReadinessEvidence:
    manifest: CapabilityBatchManifest
    lane: LinearIntegrationLaneState
    current_manifest_fingerprint: str
    current_lane_head_sha: str
    main_current_sha: str
    unresolved_recovery: bool

    def __post_init__(self) -> None:
        if type(self.manifest) is not CapabilityBatchManifest:
            raise _error("manifest readiness evidence must be exact")
        if type(self.lane) is not LinearIntegrationLaneState:
            raise _error("lane readiness evidence must be exact")
        _require_fingerprint(
            self.current_manifest_fingerprint, "current_manifest_fingerprint"
        )
        _require_sha(self.current_lane_head_sha, "current_lane_head_sha")
        _require_sha(self.main_current_sha, "main_current_sha")
        if type(self.unresolved_recovery) is not bool:
            raise _error("unresolved_recovery must be an exact bool")

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_lane_head_sha": self.current_lane_head_sha,
            "current_manifest_fingerprint": self.current_manifest_fingerprint,
            "lane": self.lane.to_dict(),
            "main_current_sha": self.main_current_sha,
            "manifest": self.manifest.to_dict(),
            "unresolved_recovery": self.unresolved_recovery,
        }

    @classmethod
    def from_dict(cls, data: object) -> "CapabilityReadinessEvidence":
        fields = {
            "current_lane_head_sha",
            "current_manifest_fingerprint",
            "lane",
            "main_current_sha",
            "manifest",
            "unresolved_recovery",
        }
        if type(data) is not dict or set(data) != fields:
            raise _error(
                "CapabilityReadinessEvidence must contain the exact bounded field set"
            )
        return cls(
            manifest=CapabilityBatchManifest.from_dict(data["manifest"]),
            lane=LinearIntegrationLaneState.from_dict(data["lane"]),
            current_manifest_fingerprint=data["current_manifest_fingerprint"],
            current_lane_head_sha=data["current_lane_head_sha"],
            main_current_sha=data["main_current_sha"],
            unresolved_recovery=data["unresolved_recovery"],
        )


def mark_ready_for_capability_certification(
    evidence: CapabilityReadinessEvidence,
) -> tuple[CapabilityBatchManifest, LinearIntegrationLaneState]:
    """Create only the non-final TASK-094 readiness state."""
    if type(evidence) is not CapabilityReadinessEvidence:
        raise _error("capability readiness evidence must be exact")
    manifest = evidence.manifest
    lane = evidence.lane
    _require_manifest_lane_identity(manifest, lane)
    if (
        manifest.status is not CapabilityBatchStatus.INTEGRATING
        or lane.status is not IntegrationLaneStatus.INTEGRATING
    ):
        raise _error("only an integrating batch and lane may become ready")
    expected_ids = tuple(item.task_id for item in manifest.ordered_task_membership)
    if not expected_ids or lane.integrated_task_ids != expected_ids:
        raise _error("all membership items must be integrated exactly once and in order")
    if evidence.current_manifest_fingerprint != manifest.fingerprint():
        raise _error("readiness manifest fingerprint is stale")
    if (
        evidence.current_lane_head_sha != lane.current_lane_head_sha
        or evidence.main_current_sha != manifest.base_main_sha
    ):
        raise _error("lane head or main base identity drifted before readiness")
    if evidence.unresolved_recovery:
        raise _error("unresolved recovery blocks capability readiness")

    ready_manifest = transition_batch_status(
        manifest, CapabilityBatchStatus.READY_FOR_CAPABILITY_CERTIFICATION
    )
    ready_lane = replace(
        lane,
        batch_manifest_fingerprint=ready_manifest.fingerprint(),
        status=IntegrationLaneStatus.READY_FOR_CAPABILITY_CERTIFICATION,
    )
    return ready_manifest, ready_lane


__all__ = [
    "CapabilityReadinessEvidence",
    "ExecutorLeaseState",
    "IntegrationLaneContractError",
    "IntegrationLaneStatus",
    "LaneIntegrationPreflightEvidence",
    "LinearIntegrationLaneState",
    "TaskLaneBinding",
    "advance_lane",
    "begin_lane_integration",
    "initial_lane_state",
    "mark_ready_for_capability_certification",
    "rebind_lane_manifest",
    "require_lane_integration_preflight",
]
