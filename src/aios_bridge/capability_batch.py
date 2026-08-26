"""Immutable P1 capability-batch authority contracts.

This module deliberately contains no persistence, Git, certification, or merge
operations.  A manifest groups separately-authorized tasks; it never replaces
the task artifacts that grant their implementation authority.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import hashlib
import json
import re
from typing import Any

from src.aios_bridge.continuity.errors import ContinuityStateValidationError


_BATCH_ID_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
_IDENTIFIER_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
_TASK_ID_RE = re.compile(r"\ATASK-\d+\Z")
_SHA_RE = re.compile(r"\A[0-9a-f]{40}\Z")
_FINGERPRINT_RE = re.compile(r"\A[0-9a-f]{64}\Z")
_REF_RE = re.compile(r"\A(?!/)(?!.*(?:\.\.|//))[A-Za-z0-9][A-Za-z0-9._/-]{0,254}\Z")
_MAX_MANIFEST_VERSION = 2_147_483_647
_MAX_MEMBERSHIP = 10_000


class CapabilityBatchContractError(ContinuityStateValidationError):
    """A malformed capability-batch contract or forbidden transition."""


def _error(message: str) -> CapabilityBatchContractError:
    return CapabilityBatchContractError(message)


def _require_text(value: object, name: str) -> str:
    if (
        type(value) is not str
        or _IDENTIFIER_RE.fullmatch(value) is None
    ):
        raise _error(f"{name} must be a canonical bounded identifier")
    return value


def _require_sha(value: object, name: str) -> str:
    if type(value) is not str or _SHA_RE.fullmatch(value) is None:
        raise _error(f"{name} must be an exact lowercase 40-hex SHA")
    return value


def _require_fingerprint(value: object, name: str) -> str:
    if type(value) is not str or _FINGERPRINT_RE.fullmatch(value) is None:
        raise _error(f"{name} must be an exact lowercase 64-hex fingerprint")
    return value


class CapabilityBatchStatus(str, Enum):
    OPEN = "OPEN"
    INTEGRATING = "INTEGRATING"
    READY_FOR_CAPABILITY_CERTIFICATION = "READY_FOR_CAPABILITY_CERTIFICATION"
    CERTIFICATION_PENDING = "CERTIFICATION_PENDING"
    CERTIFIED = "CERTIFIED"
    MERGED = "MERGED"
    CERTIFICATION_FAILED = "CERTIFICATION_FAILED"
    SUPERSEDED = "SUPERSEDED"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"


_TASK_094_TRANSITIONS: dict[
    CapabilityBatchStatus, frozenset[CapabilityBatchStatus]
] = {
    CapabilityBatchStatus.OPEN: frozenset(
        {
            CapabilityBatchStatus.INTEGRATING,
            CapabilityBatchStatus.SUPERSEDED,
            CapabilityBatchStatus.RECOVERY_REQUIRED,
        }
    ),
    CapabilityBatchStatus.INTEGRATING: frozenset(
        {
            CapabilityBatchStatus.READY_FOR_CAPABILITY_CERTIFICATION,
            CapabilityBatchStatus.SUPERSEDED,
            CapabilityBatchStatus.RECOVERY_REQUIRED,
        }
    ),
    CapabilityBatchStatus.READY_FOR_CAPABILITY_CERTIFICATION: frozenset(
        {
            CapabilityBatchStatus.SUPERSEDED,
            CapabilityBatchStatus.RECOVERY_REQUIRED,
        }
    ),
    CapabilityBatchStatus.CERTIFICATION_PENDING: frozenset(),
    CapabilityBatchStatus.CERTIFIED: frozenset(),
    CapabilityBatchStatus.MERGED: frozenset(),
    CapabilityBatchStatus.CERTIFICATION_FAILED: frozenset(),
    CapabilityBatchStatus.SUPERSEDED: frozenset(),
    CapabilityBatchStatus.RECOVERY_REQUIRED: frozenset(
        {CapabilityBatchStatus.SUPERSEDED}
    ),
}


@dataclass(frozen=True, slots=True)
class TaskMembershipBinding:
    """Exact task authority identity admitted into one manifest version."""

    task_id: str
    task_artifact_blob_sha: str
    bound_lane_base_sha: str
    expected_task_branch: str
    task_scope_fingerprint: str
    membership_position: int
    membership_version: int

    def __post_init__(self) -> None:
        if type(self.task_id) is not str or _TASK_ID_RE.fullmatch(self.task_id) is None:
            raise _error("task_id must match exact TASK-<digits>")
        _require_sha(self.task_artifact_blob_sha, "task_artifact_blob_sha")
        _require_sha(self.bound_lane_base_sha, "bound_lane_base_sha")
        if (
            type(self.expected_task_branch) is not str
            or _REF_RE.fullmatch(self.expected_task_branch) is None
        ):
            raise _error("expected_task_branch must be a canonical bounded ref")
        _require_fingerprint(self.task_scope_fingerprint, "task_scope_fingerprint")
        if type(self.membership_position) is not int or not (
            0 <= self.membership_position < _MAX_MEMBERSHIP
        ):
            raise _error("membership_position must be a bounded non-negative exact int")
        if type(self.membership_version) is not int or not (
            1 <= self.membership_version <= _MAX_MANIFEST_VERSION
        ):
            raise _error("membership_version must be a bounded positive exact int")

    def to_dict(self) -> dict[str, Any]:
        return {
            "bound_lane_base_sha": self.bound_lane_base_sha,
            "expected_task_branch": self.expected_task_branch,
            "membership_position": self.membership_position,
            "membership_version": self.membership_version,
            "task_artifact_blob_sha": self.task_artifact_blob_sha,
            "task_id": self.task_id,
            "task_scope_fingerprint": self.task_scope_fingerprint,
        }

    @classmethod
    def from_dict(cls, data: object) -> "TaskMembershipBinding":
        fields = {
            "bound_lane_base_sha",
            "expected_task_branch",
            "membership_position",
            "membership_version",
            "task_artifact_blob_sha",
            "task_id",
            "task_scope_fingerprint",
        }
        if type(data) is not dict or set(data) != fields:
            raise _error("TaskMembershipBinding must contain the exact bounded field set")
        return cls(**data)


@dataclass(frozen=True, slots=True)
class CapabilityBatchManifest:
    schema_version: str
    batch_id: str
    roadmap_id: str
    roadmap_version: str
    roadmap_fingerprint: str
    milestone: str
    capability_id: str
    base_main_sha: str
    integration_lane_ref: str
    manifest_version: int
    ordered_task_membership: tuple[TaskMembershipBinding, ...]
    status: CapabilityBatchStatus

    def __post_init__(self) -> None:
        if self.schema_version != "1" or type(self.schema_version) is not str:
            raise _error("schema_version must be exact supported value '1'")
        if type(self.batch_id) is not str or _BATCH_ID_RE.fullmatch(self.batch_id) is None:
            raise _error("batch_id must be canonical and bounded")
        for name in ("roadmap_id", "roadmap_version", "milestone", "capability_id"):
            _require_text(getattr(self, name), name)
        _require_fingerprint(self.roadmap_fingerprint, "roadmap_fingerprint")
        _require_sha(self.base_main_sha, "base_main_sha")
        if (
            type(self.integration_lane_ref) is not str
            or _REF_RE.fullmatch(self.integration_lane_ref) is None
        ):
            raise _error("integration_lane_ref must be a canonical bounded ref")
        if type(self.manifest_version) is not int or not (
            1 <= self.manifest_version <= _MAX_MANIFEST_VERSION
        ):
            raise _error("manifest_version must be a bounded positive exact int")
        if (
            type(self.ordered_task_membership) is not tuple
            or len(self.ordered_task_membership) > _MAX_MEMBERSHIP
            or any(type(item) is not TaskMembershipBinding for item in self.ordered_task_membership)
        ):
            raise _error("ordered_task_membership must be a bounded exact tuple")
        if type(self.status) is not CapabilityBatchStatus:
            raise _error("status must be an exact CapabilityBatchStatus")
        if self.status is not CapabilityBatchStatus.OPEN and not self.ordered_task_membership:
            raise _error("membership must be non-empty when integration begins")

        task_ids = tuple(item.task_id for item in self.ordered_task_membership)
        if len(set(task_ids)) != len(task_ids):
            raise _error("ordered task membership must be duplicate-free")
        for position, item in enumerate(self.ordered_task_membership):
            if item.membership_position != position:
                raise _error("membership positions must exactly match manifest order")
            if position == 0 and item.bound_lane_base_sha != self.base_main_sha:
                raise _error("first task must bind the exact batch base main SHA")

    def to_dict(self) -> dict[str, Any]:
        return {
            "base_main_sha": self.base_main_sha,
            "batch_id": self.batch_id,
            "capability_id": self.capability_id,
            "integration_lane_ref": self.integration_lane_ref,
            "manifest_version": self.manifest_version,
            "milestone": self.milestone,
            "ordered_task_membership": [
                item.to_dict() for item in self.ordered_task_membership
            ],
            "roadmap_fingerprint": self.roadmap_fingerprint,
            "roadmap_id": self.roadmap_id,
            "roadmap_version": self.roadmap_version,
            "schema_version": self.schema_version,
            "status": self.status.value,
        }

    def to_canonical_json(self) -> str:
        return json.dumps(
            self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )

    def fingerprint(self) -> str:
        return hashlib.sha256(self.to_canonical_json().encode("utf-8")).hexdigest()

    @classmethod
    def from_dict(cls, data: object) -> "CapabilityBatchManifest":
        fields = {
            "base_main_sha",
            "batch_id",
            "capability_id",
            "integration_lane_ref",
            "manifest_version",
            "milestone",
            "ordered_task_membership",
            "roadmap_fingerprint",
            "roadmap_id",
            "roadmap_version",
            "schema_version",
            "status",
        }
        if type(data) is not dict or set(data) != fields:
            raise _error("CapabilityBatchManifest must contain the exact bounded field set")
        membership = data["ordered_task_membership"]
        if type(membership) is not list:
            raise _error("serialized ordered_task_membership must be an exact list")
        try:
            return cls(
                schema_version=data["schema_version"],
                batch_id=data["batch_id"],
                roadmap_id=data["roadmap_id"],
                roadmap_version=data["roadmap_version"],
                roadmap_fingerprint=data["roadmap_fingerprint"],
                milestone=data["milestone"],
                capability_id=data["capability_id"],
                base_main_sha=data["base_main_sha"],
                integration_lane_ref=data["integration_lane_ref"],
                manifest_version=data["manifest_version"],
                ordered_task_membership=tuple(
                    TaskMembershipBinding.from_dict(item) for item in membership
                ),
                status=CapabilityBatchStatus(data["status"]),
            )
        except (TypeError, ValueError) as exc:
            raise _error(f"malformed CapabilityBatchManifest: {exc}") from exc


def require_current_task_authority(
    manifest: CapabilityBatchManifest,
    *,
    task_id: str,
    task_artifact_blob_sha: str,
    expected_task_branch: str,
    task_scope_fingerprint: str,
    membership_position: int,
) -> TaskMembershipBinding:
    """Require exact independent task authority; batch data cannot widen it."""
    if type(manifest) is not CapabilityBatchManifest:
        raise _error("manifest must be an exact CapabilityBatchManifest")
    if type(membership_position) is not int or not (
        0 <= membership_position < len(manifest.ordered_task_membership)
    ):
        raise _error("task is not explicitly present at the membership position")
    expected = manifest.ordered_task_membership[membership_position]
    supplied = (
        task_id,
        task_artifact_blob_sha,
        expected_task_branch,
        task_scope_fingerprint,
        membership_position,
    )
    exact = (
        expected.task_id,
        expected.task_artifact_blob_sha,
        expected.expected_task_branch,
        expected.task_scope_fingerprint,
        expected.membership_position,
    )
    if supplied != exact:
        raise _error("task authority does not exactly match current batch membership")
    return expected


def require_valid_membership_revision(
    previous: CapabilityBatchManifest,
    candidate: CapabilityBatchManifest,
) -> CapabilityBatchManifest:
    """Prove a membership authority change has a new exact manifest version.

    This is validation only; it performs no persistence and grants executors no
    authority to author or mutate batch membership.
    """
    if (
        type(previous) is not CapabilityBatchManifest
        or type(candidate) is not CapabilityBatchManifest
    ):
        raise _error("membership revision requires exact batch manifests")
    stable_identity = (
        "schema_version",
        "batch_id",
        "roadmap_id",
        "roadmap_version",
        "roadmap_fingerprint",
        "milestone",
        "capability_id",
        "base_main_sha",
        "integration_lane_ref",
        "status",
    )
    if any(getattr(previous, name) != getattr(candidate, name) for name in stable_identity):
        raise _error("membership revision may not alter other batch authority identity")
    if previous.ordered_task_membership == candidate.ordered_task_membership:
        raise _error("membership revision must change exact ordered membership")
    if candidate.manifest_version != previous.manifest_version + 1:
        raise _error("membership revision requires the next exact manifest version")
    if candidate.fingerprint() == previous.fingerprint():
        raise _error("membership revision requires a new manifest fingerprint")
    return candidate


def transition_batch_status(
    manifest: CapabilityBatchManifest,
    new_status: CapabilityBatchStatus,
) -> CapabilityBatchManifest:
    """Perform only TASK-094-owned lifecycle transitions through readiness."""
    if type(manifest) is not CapabilityBatchManifest:
        raise _error("manifest must be an exact CapabilityBatchManifest")
    if type(new_status) is not CapabilityBatchStatus:
        raise _error("new_status must be an exact CapabilityBatchStatus")
    if new_status not in _TASK_094_TRANSITIONS[manifest.status]:
        raise _error(
            f"forbidden or TASK-095-owned batch transition: "
            f"{manifest.status.value} -> {new_status.value}"
        )
    return replace(manifest, status=new_status)


__all__ = [
    "CapabilityBatchContractError",
    "CapabilityBatchManifest",
    "CapabilityBatchStatus",
    "TaskMembershipBinding",
    "require_current_task_authority",
    "require_valid_membership_revision",
    "transition_batch_status",
]
