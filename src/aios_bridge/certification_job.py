"""Provider-neutral deterministic certification-job contracts."""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
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
class CertificationJob:
    job_id: str
    task_id: str
    candidate_head_sha: str
    candidate_fingerprint: str
    validation_profile: ValidationProfile
    certification_command_identity: str
    status: CertificationJobStatus
    started_at: str | None = None
    terminal_result_digest: str | None = None

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
        if self.started_at is not None and (
            type(self.started_at) is not str
            or not self.started_at
            or self.started_at != self.started_at.strip()
            or len(self.started_at) > 128
        ):
            raise _error("started_at must be bounded exact text or None")
        if self.status is CertificationJobStatus.CERTIFICATION_PENDING and self.started_at is not None:
            raise _error("pending certification cannot have started_at evidence")
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

    @property
    def creates_certification_authority(self) -> bool:
        return self.status is CertificationJobStatus.CERTIFICATION_PASS

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_fingerprint": self.candidate_fingerprint,
            "candidate_head_sha": self.candidate_head_sha,
            "certification_command_identity": self.certification_command_identity,
            "job_id": self.job_id,
            "started_at": self.started_at,
            "status": self.status.value,
            "task_id": self.task_id,
            "terminal_result_digest": self.terminal_result_digest,
            "validation_profile": self.validation_profile.value,
        }

    @classmethod
    def from_dict(cls, data: object) -> "CertificationJob":
        fields = {
            "candidate_fingerprint",
            "candidate_head_sha",
            "certification_command_identity",
            "job_id",
            "started_at",
            "status",
            "task_id",
            "terminal_result_digest",
            "validation_profile",
        }
        if type(data) is not dict or set(data) != fields:
            raise _error("CertificationJob must contain the exact bounded field set")
        try:
            return cls(
                job_id=data["job_id"],
                task_id=data["task_id"],
                candidate_head_sha=data["candidate_head_sha"],
                candidate_fingerprint=data["candidate_fingerprint"],
                validation_profile=ValidationProfile(data["validation_profile"]),
                certification_command_identity=data["certification_command_identity"],
                status=CertificationJobStatus(data["status"]),
                started_at=data["started_at"],
                terminal_result_digest=data["terminal_result_digest"],
            )
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
    terminal_result_digest: str | None = None,
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
        terminal_result_digest=(
            job.terminal_result_digest
            if terminal_result_digest is None
            else terminal_result_digest
        ),
    )
