"""Provider-neutral deterministic certification-job contracts."""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import hashlib
import json
import math
import re
from typing import Any

from src.aios_bridge.continuity.errors import ContinuityStateValidationError
from src.aios_bridge.validation import ValidationProfile


_IDENTIFIER_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
_TASK_ID_RE = re.compile(r"\ATASK-\d+\Z")
_SHA_RE = re.compile(r"\A[0-9a-f]{40}\Z")
_FINGERPRINT_RE = re.compile(r"\A[0-9a-f]{64}\Z")


class CertificationContractError(ContinuityStateValidationError):
    """A malformed certification contract or invalid transition."""


def _error(message: str) -> CertificationContractError:
    return CertificationContractError(message)


def _require_sha(value: object, name: str) -> str:
    if type(value) is not str or _SHA_RE.fullmatch(value) is None:
        raise _error(f"{name} must be an exact lowercase 40-hex SHA")
    return value


def _require_fingerprint(value: object, name: str) -> str:
    if type(value) is not str or _FINGERPRINT_RE.fullmatch(value) is None:
        raise _error(f"{name} must be an exact lowercase 64-hex fingerprint")
    return value


class CertificationJobStatus(str, Enum):
    CERTIFICATION_PENDING = "CERTIFICATION_PENDING"
    CERTIFICATION_RUNNING = "CERTIFICATION_RUNNING"
    CERTIFICATION_PASS = "CERTIFICATION_PASS"
    CERTIFICATION_FAILED = "CERTIFICATION_FAILED"
    SUPERSEDED = "SUPERSEDED"


_TERMINAL_STATUSES = frozenset(
    {
        CertificationJobStatus.CERTIFICATION_PASS,
        CertificationJobStatus.CERTIFICATION_FAILED,
        CertificationJobStatus.SUPERSEDED,
    }
)
_TRANSITIONS: dict[CertificationJobStatus, frozenset[CertificationJobStatus]] = {
    CertificationJobStatus.CERTIFICATION_PENDING: frozenset(
        {
            CertificationJobStatus.CERTIFICATION_RUNNING,
            CertificationJobStatus.SUPERSEDED,
        }
    ),
    CertificationJobStatus.CERTIFICATION_RUNNING: frozenset(
        {
            CertificationJobStatus.CERTIFICATION_PASS,
            CertificationJobStatus.CERTIFICATION_FAILED,
            CertificationJobStatus.SUPERSEDED,
        }
    ),
    CertificationJobStatus.CERTIFICATION_PASS: frozenset(),
    CertificationJobStatus.CERTIFICATION_FAILED: frozenset(),
    CertificationJobStatus.SUPERSEDED: frozenset(),
}


class LongRunningWaitOwner(str, Enum):
    CERTIFICATION_BOUNDARY = "CERTIFICATION_BOUNDARY"


@dataclass(frozen=True, slots=True)
class CertificationWaitContract:
    long_running_deterministic_wait_owner: LongRunningWaitOwner
    model_completion_polling_required: bool
    executor_completion_polling_required: bool
    provider_specific_semantics: bool
    future_executor_compatible: bool

    def __post_init__(self) -> None:
        if (
            type(self.long_running_deterministic_wait_owner) is not LongRunningWaitOwner
            or self.long_running_deterministic_wait_owner
            is not LongRunningWaitOwner.CERTIFICATION_BOUNDARY
        ):
            raise _error("long-running waits must be owned by the certification boundary")
        for name in (
            "model_completion_polling_required",
            "executor_completion_polling_required",
            "provider_specific_semantics",
            "future_executor_compatible",
        ):
            if type(getattr(self, name)) is not bool:
                raise _error(f"{name} must be an exact bool")
        if self.model_completion_polling_required:
            raise _error("model completion polling must not be required")
        if self.executor_completion_polling_required:
            raise _error("executor completion polling must not be required")
        if self.provider_specific_semantics:
            raise _error("certification waiting must remain provider-neutral")
        if not self.future_executor_compatible:
            raise _error("certification waiting must remain future-executor compatible")

    def to_dict(self) -> dict[str, Any]:
        return {
            "executor_completion_polling_required": self.executor_completion_polling_required,
            "future_executor_compatible": self.future_executor_compatible,
            "long_running_deterministic_wait_owner": (
                self.long_running_deterministic_wait_owner.value
            ),
            "model_completion_polling_required": self.model_completion_polling_required,
            "provider_specific_semantics": self.provider_specific_semantics,
        }


CERTIFICATION_WAIT_CONTRACT = CertificationWaitContract(
    long_running_deterministic_wait_owner=LongRunningWaitOwner.CERTIFICATION_BOUNDARY,
    model_completion_polling_required=False,
    executor_completion_polling_required=False,
    provider_specific_semantics=False,
    future_executor_compatible=True,
)


@dataclass(frozen=True, slots=True)
class CertificationPreflightEvidence:
    task_exists: bool
    review_first_mode: bool
    review_status: str
    review_approved: bool
    auto_merge_eligible: bool
    reviewed_task_head_sha: str
    reviewed_base_main_sha: str
    remote_task_head_sha: str
    remote_main_sha: str
    local_branch: str
    expected_task_branch: str
    local_head_sha: str
    worktree_clean: bool
    merge_base_sha: str
    behind_by: int
    roadmap_valid: bool
    certification_owned_t2_count: int

    def __post_init__(self) -> None:
        for name in (
            "task_exists",
            "review_first_mode",
            "review_approved",
            "auto_merge_eligible",
            "worktree_clean",
            "roadmap_valid",
        ):
            if type(getattr(self, name)) is not bool:
                raise _error(f"{name} must be an exact bool")
        if type(self.review_status) is not str or not self.review_status:
            raise _error("review_status must be exact non-empty text")
        for name in (
            "reviewed_task_head_sha",
            "reviewed_base_main_sha",
            "remote_task_head_sha",
            "remote_main_sha",
            "local_head_sha",
            "merge_base_sha",
        ):
            _require_sha(getattr(self, name), name)
        for name in ("local_branch", "expected_task_branch"):
            value = getattr(self, name)
            if type(value) is not str or not value or value != value.strip():
                raise _error(f"{name} must be exact non-empty text")
        if type(self.behind_by) is not int or self.behind_by < 0:
            raise _error("behind_by must be a non-negative exact int")
        if type(self.certification_owned_t2_count) is not int:
            raise _error("certification_owned_t2_count must be an exact int")


def require_certification_preflight(evidence: CertificationPreflightEvidence) -> None:
    """Fail before T2 for every identity, authority, worktree, or plan drift."""
    if type(evidence) is not CertificationPreflightEvidence:
        raise _error("certification preflight evidence must be exact")
    if not evidence.task_exists or not evidence.review_first_mode:
        raise _error("task must exist in review-first mode")
    if evidence.review_status != "SEMANTICALLY_ACCEPTED_PENDING_T2":
        raise _error("review is not semantically accepted pending T2")
    if not evidence.review_approved or not evidence.auto_merge_eligible:
        raise _error("semantic acceptance lacks approval or auto-merge eligibility")
    if evidence.reviewed_task_head_sha != evidence.remote_task_head_sha:
        raise _error("reviewed task head drifted before T2")
    if evidence.reviewed_base_main_sha != evidence.remote_main_sha:
        raise _error("reviewed base main drifted before T2")
    if evidence.local_branch != evidence.expected_task_branch:
        raise _error("local branch is not the exact task branch")
    if evidence.local_head_sha != evidence.reviewed_task_head_sha:
        raise _error("local HEAD is not the exact reviewed task head")
    if not evidence.worktree_clean:
        raise _error("certification requires a clean worktree")
    if evidence.merge_base_sha != evidence.remote_main_sha or evidence.behind_by != 0:
        raise _error("candidate is behind or not based on current main")
    if not evidence.roadmap_valid:
        raise _error("roadmap binding or reviewed roadmap evidence drifted")
    if evidence.certification_owned_t2_count != 1:
        raise _error("validation plan must resolve exactly one certification-owned T2")


@dataclass(frozen=True, slots=True)
class CertificationJob:
    job_id: str
    task_id: str
    candidate_head_sha: str
    candidate_fingerprint: str
    validation_profile: ValidationProfile
    certification_command_identity: str
    status: CertificationJobStatus
    started_at: str | None = None
    completed_at: str | None = None
    terminal_result_digest: str | None = None
    aios_managed_t2_execution_count: int = 0
    t2_exit_status: int | None = None
    t2_succeeded: bool | None = None
    duration_seconds: float | None = None
    model_poll_count: int = 0
    executor_poll_count: int = 0

    def __post_init__(self) -> None:
        if type(self.job_id) is not str or _IDENTIFIER_RE.fullmatch(self.job_id) is None:
            raise _error("job_id must be a canonical bounded identifier")
        if type(self.task_id) is not str or _TASK_ID_RE.fullmatch(self.task_id) is None:
            raise _error("task_id must match exact TASK-<digits>")
        _require_sha(self.candidate_head_sha, "candidate_head_sha")
        _require_fingerprint(self.candidate_fingerprint, "candidate_fingerprint")
        if type(self.validation_profile) is not ValidationProfile:
            raise _error("validation_profile must be an exact ValidationProfile")
        if (
            type(self.certification_command_identity) is not str
            or not self.certification_command_identity
            or self.certification_command_identity
            != self.certification_command_identity.strip()
            or len(self.certification_command_identity) > 512
        ):
            raise _error("certification_command_identity must be bounded exact non-empty text")
        if type(self.status) is not CertificationJobStatus:
            raise _error("status must be an exact CertificationJobStatus")
        for name in ("started_at", "completed_at"):
            value = getattr(self, name)
            if value is not None and (
                type(value) is not str
                or not value
                or value != value.strip()
                or len(value) > 128
            ):
                raise _error(f"{name} must be bounded exact text or None")
        if type(self.aios_managed_t2_execution_count) is not int or (
            self.aios_managed_t2_execution_count < 0
            or self.aios_managed_t2_execution_count > 1
        ):
            raise _error("AIOS-managed T2 execution count must be exact 0 or 1")
        if self.t2_exit_status is not None and (
            type(self.t2_exit_status) is not int
            or not -65535 <= self.t2_exit_status <= 65535
        ):
            raise _error("t2_exit_status must be a bounded exact int or None")
        if self.t2_succeeded is not None and type(self.t2_succeeded) is not bool:
            raise _error("t2_succeeded must be an exact bool or None")
        if self.duration_seconds is not None and (
            type(self.duration_seconds) not in {int, float}
            or not math.isfinite(self.duration_seconds)
            or self.duration_seconds < 0
            or self.duration_seconds > 604800
        ):
            raise _error("duration_seconds must be bounded to seven days")
        if self.model_poll_count != 0 or type(self.model_poll_count) is not int:
            raise _error("certification jobs must record zero model polls")
        if self.executor_poll_count != 0 or type(self.executor_poll_count) is not int:
            raise _error("certification jobs must record zero executor polls")
        if self.status is CertificationJobStatus.CERTIFICATION_PENDING and self.started_at is not None:
            raise _error("pending certification cannot have started_at evidence")
        if self.status is CertificationJobStatus.CERTIFICATION_PENDING:
            if self.aios_managed_t2_execution_count != 0:
                raise _error("pending certification cannot record a T2 execution")
        if self.status is CertificationJobStatus.CERTIFICATION_RUNNING:
            if self.started_at is None or self.aios_managed_t2_execution_count != 1:
                raise _error("running certification requires started_at and one T2 execution")
        result_bearing_status = self.status in {
            CertificationJobStatus.CERTIFICATION_PASS,
            CertificationJobStatus.CERTIFICATION_FAILED,
        }
        if result_bearing_status and self.terminal_result_digest is None:
            raise _error("pass or failed certification requires terminal_result_digest")
        if not result_bearing_status and self.terminal_result_digest is not None:
            raise _error("terminal_result_digest is valid only for pass or failed status")
        if self.terminal_result_digest is not None:
            _require_fingerprint(self.terminal_result_digest, "terminal_result_digest")
        if result_bearing_status:
            if (
                self.started_at is None
                or self.completed_at is None
                or self.aios_managed_t2_execution_count != 1
                or self.t2_exit_status is None
                or self.t2_succeeded is None
                or self.duration_seconds is None
            ):
                raise _error("terminal certification requires complete bounded T2 evidence")
            if (
                self.status is CertificationJobStatus.CERTIFICATION_PASS
                and not self.t2_succeeded
            ):
                raise _error("passing certification requires successful T2 evidence")
            if (self.t2_exit_status == 0) is not self.t2_succeeded:
                raise _error("T2 exit status and success fact disagree")
        elif any(
            value is not None
            for value in (
                self.completed_at,
                self.t2_exit_status,
                self.t2_succeeded,
                self.duration_seconds,
            )
        ):
            raise _error("non-terminal certification cannot contain terminal T2 evidence")

    @property
    def creates_certification_authority(self) -> bool:
        return self.status is CertificationJobStatus.CERTIFICATION_PASS

    def to_dict(self) -> dict[str, Any]:
        return {
            "aios_managed_t2_execution_count": self.aios_managed_t2_execution_count,
            "candidate_fingerprint": self.candidate_fingerprint,
            "candidate_head_sha": self.candidate_head_sha,
            "certification_command_identity": self.certification_command_identity,
            "completed_at": self.completed_at,
            "duration_seconds": self.duration_seconds,
            "executor_poll_count": self.executor_poll_count,
            "job_id": self.job_id,
            "model_poll_count": self.model_poll_count,
            "started_at": self.started_at,
            "status": self.status.value,
            "task_id": self.task_id,
            "t2_exit_status": self.t2_exit_status,
            "t2_succeeded": self.t2_succeeded,
            "terminal_result_digest": self.terminal_result_digest,
            "validation_profile": self.validation_profile.value,
        }

    @classmethod
    def from_dict(cls, data: object) -> "CertificationJob":
        fields = {
            "aios_managed_t2_execution_count",
            "candidate_fingerprint",
            "candidate_head_sha",
            "certification_command_identity",
            "completed_at",
            "duration_seconds",
            "executor_poll_count",
            "job_id",
            "model_poll_count",
            "started_at",
            "status",
            "task_id",
            "t2_exit_status",
            "t2_succeeded",
            "terminal_result_digest",
            "validation_profile",
        }
        if type(data) is not dict or set(data) != fields:
            raise _error("CertificationJob must contain the exact bounded field set")
        try:
            job = cls(
                job_id=data["job_id"],
                task_id=data["task_id"],
                candidate_head_sha=data["candidate_head_sha"],
                candidate_fingerprint=data["candidate_fingerprint"],
                validation_profile=ValidationProfile(data["validation_profile"]),
                certification_command_identity=data["certification_command_identity"],
                status=CertificationJobStatus(data["status"]),
                started_at=data["started_at"],
                completed_at=data["completed_at"],
                terminal_result_digest=data["terminal_result_digest"],
                aios_managed_t2_execution_count=data[
                    "aios_managed_t2_execution_count"
                ],
                t2_exit_status=data["t2_exit_status"],
                t2_succeeded=data["t2_succeeded"],
                duration_seconds=data["duration_seconds"],
                model_poll_count=data["model_poll_count"],
                executor_poll_count=data["executor_poll_count"],
            )
            return require_valid_terminal_result_digest(job)
        except (TypeError, ValueError) as exc:
            raise _error(f"malformed CertificationJob: {exc}") from exc


def certification_candidate_matches(
    job: CertificationJob,
    candidate_head_sha: str,
    candidate_fingerprint: str,
) -> bool:
    """Check both exact candidate bindings; malformed identities fail closed."""
    if type(job) is not CertificationJob:
        raise _error("job must be an exact CertificationJob")
    _require_sha(candidate_head_sha, "candidate_head_sha")
    _require_fingerprint(candidate_fingerprint, "candidate_fingerprint")
    return (
        job.candidate_head_sha == candidate_head_sha
        and job.candidate_fingerprint == candidate_fingerprint
    )


def build_certification_command_identity(command: str) -> str:
    """Return a bounded identity for one exact deterministic command string."""
    if type(command) is not str or not command or command != command.strip():
        raise _error("certification command must be exact non-empty text")
    return "sha256:" + hashlib.sha256(command.encode("utf-8")).hexdigest()


def build_candidate_fingerprint(
    *,
    task_id: str,
    candidate_head_sha: str,
    base_main_sha: str,
    task_artifact_blob_sha: str,
    roadmap_fingerprint: str,
    validation_profile: ValidationProfile,
    certification_command_identity: str,
) -> str:
    """Bind certification authority solely to exact machine identity inputs."""
    if type(task_id) is not str or _TASK_ID_RE.fullmatch(task_id) is None:
        raise _error("task_id must match exact TASK-<digits>")
    _require_sha(candidate_head_sha, "candidate_head_sha")
    _require_sha(base_main_sha, "base_main_sha")
    _require_sha(task_artifact_blob_sha, "task_artifact_blob_sha")
    _require_fingerprint(roadmap_fingerprint, "roadmap_fingerprint")
    if type(validation_profile) is not ValidationProfile:
        raise _error("validation_profile must be an exact ValidationProfile")
    if (
        type(certification_command_identity) is not str
        or not certification_command_identity
        or certification_command_identity != certification_command_identity.strip()
    ):
        raise _error("certification_command_identity must be exact non-empty text")
    payload = {
        "base_main_sha": base_main_sha,
        "candidate_head_sha": candidate_head_sha,
        "certification_command_identity": certification_command_identity,
        "roadmap_fingerprint": roadmap_fingerprint,
        "task_artifact_blob_sha": task_artifact_blob_sha,
        "task_id": task_id,
        "validation_profile": validation_profile.value,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_terminal_result_digest(
    *,
    status: CertificationJobStatus,
    t2_exit_status: int,
    t2_succeeded: bool,
    duration_seconds: float,
    aios_managed_t2_execution_count: int,
) -> str:
    """Digest bounded terminal facts without accepting raw command output."""
    if status not in {
        CertificationJobStatus.CERTIFICATION_PASS,
        CertificationJobStatus.CERTIFICATION_FAILED,
    }:
        raise _error("terminal digest requires PASS or FAILED status")
    if type(t2_exit_status) is not int or not -65535 <= t2_exit_status <= 65535:
        raise _error("t2_exit_status must be a bounded exact int")
    if type(t2_succeeded) is not bool:
        raise _error("t2_succeeded must be an exact bool")
    if (
        type(duration_seconds) not in {int, float}
        or not math.isfinite(duration_seconds)
        or not 0 <= duration_seconds <= 604800
    ):
        raise _error("duration_seconds must be bounded to seven days")
    if aios_managed_t2_execution_count != 1:
        raise _error("terminal certification must record exactly one AIOS-managed T2")
    payload = {
        "aios_managed_t2_execution_count": aios_managed_t2_execution_count,
        "duration_seconds": round(float(duration_seconds), 6),
        "status": status.value,
        "t2_exit_status": t2_exit_status,
        "t2_succeeded": t2_succeeded,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def require_valid_terminal_result_digest(job: CertificationJob) -> CertificationJob:
    """Fail closed unless persisted terminal facts match their exact digest."""
    if type(job) is not CertificationJob:
        raise _error("job must be an exact CertificationJob")
    if job.status not in {
        CertificationJobStatus.CERTIFICATION_PASS,
        CertificationJobStatus.CERTIFICATION_FAILED,
    }:
        return job
    if (
        job.t2_exit_status is None
        or job.t2_succeeded is None
        or job.duration_seconds is None
    ):
        raise _error("terminal digest verification requires complete bounded facts")
    expected = build_terminal_result_digest(
        status=job.status,
        t2_exit_status=job.t2_exit_status,
        t2_succeeded=job.t2_succeeded,
        duration_seconds=job.duration_seconds,
        aios_managed_t2_execution_count=job.aios_managed_t2_execution_count,
    )
    if job.terminal_result_digest != expected:
        raise _error("terminal_result_digest does not match bounded terminal facts")
    return job


def require_exact_certification_candidate(
    job: CertificationJob,
    candidate_head_sha: str,
    candidate_fingerprint: str,
) -> CertificationJob:
    """Return the job only when both exact candidate identities match."""
    if not certification_candidate_matches(job, candidate_head_sha, candidate_fingerprint):
        raise _error("certification job candidate identity mismatch")
    return job


def transition_certification_job(
    job: CertificationJob,
    target: CertificationJobStatus,
    *,
    started_at: str | None = None,
    completed_at: str | None = None,
    terminal_result_digest: str | None = None,
    aios_managed_t2_execution_count: int | None = None,
    t2_exit_status: int | None = None,
    t2_succeeded: bool | None = None,
    duration_seconds: float | None = None,
) -> CertificationJob:
    """Pure state transition; all terminal states reject reentry."""
    if type(job) is not CertificationJob or type(target) is not CertificationJobStatus:
        raise _error("certification transitions require exact contract types")
    if target not in _TRANSITIONS[job.status]:
        raise _error(
            f"invalid certification transition: {job.status.value} -> {target.value}"
        )
    return replace(
        job,
        status=target,
        started_at=job.started_at if started_at is None else started_at,
        completed_at=job.completed_at if completed_at is None else completed_at,
        terminal_result_digest=(
            job.terminal_result_digest
            if terminal_result_digest is None
            else terminal_result_digest
        ),
        aios_managed_t2_execution_count=(
            aios_managed_t2_execution_count
            if aios_managed_t2_execution_count is not None
            else (
                1
                if target is CertificationJobStatus.CERTIFICATION_RUNNING
                else job.aios_managed_t2_execution_count
            )
        ),
        t2_exit_status=job.t2_exit_status if t2_exit_status is None else t2_exit_status,
        t2_succeeded=job.t2_succeeded if t2_succeeded is None else t2_succeeded,
        duration_seconds=(
            job.duration_seconds if duration_seconds is None else duration_seconds
        ),
    )
